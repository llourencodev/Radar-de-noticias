"""Aba Eventos: workshops, meetups, conferências, feiras e webinars de tecnologia e IA.

Os eventos vêm de fontes reais listadas em config/events.json:
  devevents  RSS do dev.events (conferências e meetups de desenvolvimento no mundo todo)
  confstech  base aberta do confs.tech (JSON no GitHub, com cidade, país e se é online)
  page       página de agenda com dados estruturados (schema.org/JSON-LD ou JSON embutido do site:
             Eventbrite, Luma, Meetup, Sympla, dev.events...)
  ical       agenda .ics (ex.: grupos do Meetup)
Nada é inventado: só entram eventos com nome, data e link informados pela fonte. Eventos presenciais
fora do Brasil ficam de fora; os online entram de qualquer país. Eventos já encerrados não são exibidos.
"""
import json
import logging
import re
import threading
from datetime import date, datetime, timedelta, timezone
from hashlib import sha1
from urllib.parse import urljoin, urlparse

import feedparser
import httpx

from . import config, db, http
from .processing.normalize import BRT, canonical_url, clean_text, detect_lang, norm_title, parse_any_date, strip_accents

log = logging.getLogger("radar.eventos")
EVENTS_FILE = config.CONFIG_DIR / "events.json"
KEEP_PAST_DAYS = 30          # eventos encerrados há mais tempo saem do banco
MAX_AHEAD_DAYS = 550         # ignora datas absurdamente distantes (erro de cadastro)
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL, title_norm TEXT, start TEXT NOT NULL, end TEXT,
  all_day INTEGER DEFAULT 0, format TEXT, city TEXT, state TEXT, country TEXT, venue TEXT, organizer TEXT,
  description TEXT, tags TEXT, image TEXT, source_id TEXT, source_name TEXT, first_seen TEXT, last_seen TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_start ON events(start);
CREATE TABLE IF NOT EXISTS event_sources (
  id TEXT PRIMARY KEY, last_run_at TEXT, next_run_at TEXT, status TEXT, error TEXT,
  failures INTEGER DEFAULT 0, found INTEGER DEFAULT 0, kept INTEGER DEFAULT 0
);
"""

BR_STATES = {
    "AC": "acre", "AL": "alagoas", "AP": "amapa", "AM": "amazonas", "BA": "bahia", "CE": "ceara", "DF": "distrito federal",
    "ES": "espirito santo", "GO": "goias", "MA": "maranhao", "MT": "mato grosso", "MS": "mato grosso do sul",
    "MG": "minas gerais", "PA": "para", "PB": "paraiba", "PR": "parana", "PE": "pernambuco", "PI": "piaui",
    "RJ": "rio de janeiro", "RN": "rio grande do norte", "RS": "rio grande do sul", "RO": "rondonia", "RR": "roraima",
    "SC": "santa catarina", "SP": "sao paulo", "SE": "sergipe", "TO": "tocantins",
}
BR_STATE_BY_NAME = {v: k for k, v in BR_STATES.items()}
ONLINE_WORDS = re.compile(r"\b(online|on-line|virtual|webinar|webinario|live|ao vivo|remoto|zoom|google meet|youtube|streaming|transmissao)\b")
HYBRID_WORDS = re.compile(r"\b(hibrido|hibrida|hybrid|presencial e online|online e presencial)\b")


# ---------------------------------------------------------------- configuração
def load_config() -> dict:
    cfg = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    cfg["themes"] = [_compile_theme(t) for t in cfg.get("themes", [])]
    cfg["_exclude"] = [_kw_pattern(k) for k in cfg.get("exclude", [])]
    return cfg


def _kw_pattern(kw: str) -> tuple[re.Pattern, bool]:
    """'=Termo' casa a palavra exata (com maiúsculas) no texto original; o resto casa sem acento e em minúsculas."""
    if kw.startswith("="):
        return re.compile(rf"(?<![\w]){re.escape(kw[1:])}(?![\w])"), True
    return re.compile(rf"(?<![\w]){re.escape(strip_accents(kw.lower()))}(?![\w])"), False


def _compile_theme(t: dict) -> dict:
    t = dict(t)
    t["_kw"] = [_kw_pattern(k) for k in t.get("keywords", [])]
    return t


def _hits(patterns, raw: str, low: str) -> int:
    return sum(1 for p, exact in patterns if p.search(raw if exact else low))


def themes_for(ev: dict, cfg: dict) -> list[str]:
    raw = " ".join(str(ev.get(k) or "") for k in ("title", "description", "tags", "organizer"))
    low = strip_accents(raw.lower())
    title_raw = ev.get("title") or ""
    title_low = strip_accents(title_raw.lower())
    scored = []
    for t in cfg["themes"]:
        if t.get("fallback"):
            continue
        n = _hits(t["_kw"], raw, low) + 2 * _hits(t["_kw"], title_raw, title_low)  # o título pesa mais
        if n:
            scored.append((n, t["slug"]))
    out = [s for _, s in sorted(scored, key=lambda x: -x[0])]
    if not out:
        fb = next((t for t in cfg["themes"] if t.get("fallback")), None)
        if fb and _hits(fb["_kw"], raw, low):
            out = [fb["slug"]]
    return out


def excluded(ev: dict, cfg: dict) -> bool:
    raw = f"{ev.get('title') or ''} {ev.get('tags') or ''}"
    return _hits(cfg["_exclude"], raw, strip_accents(raw.lower())) > 0


# ---------------------------------------------------------------- utilidades
def _txt(v) -> str:
    if isinstance(v, dict):
        v = v.get("name") or v.get("text") or v.get("title") or ""
    if isinstance(v, list):
        v = ", ".join(_txt(x) for x in v if _txt(x))
    return clean_text(str(v)) if v not in (None, False) else ""


def _date(v) -> tuple[datetime | None, bool]:
    """Data de início/fim: aceita ISO, RFC 822 e números (epoch). Retorna (UTC, só o dia?)."""
    if v is None or v == "":
        return None, False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        ts = v / 1000 if v > 1e11 else v
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc), False
        except (OverflowError, OSError, ValueError):
            return None, False
    if not isinstance(v, str):
        return None, False
    v = v.strip()
    # "2026-12-03T00:00:00.000Z": várias agendas guardam só o dia como meia-noite UTC
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T00:00(?::00(?:\.0+)?)?(?:Z|[+-]00:?00)$", v)
    if m:
        v = m.group(1)
    dt, prec = parse_any_date(v)
    return dt, prec == "date"


def _iso(dt: datetime, all_day: bool) -> str:
    return dt.astimezone(BRT).strftime("%Y-%m-%d") if all_day else db.iso(dt)


def _country(v: str | None) -> str | None:
    if not v:
        return None
    s = strip_accents(str(v)).strip().lower()
    if s in ("br", "bra", "brasil", "brazil") or s.endswith("brasil") or s.endswith("brazil"):
        return "BR"
    return str(v).strip()[:60]


def _state(v: str | None) -> str | None:
    if not v:
        return None
    s = str(v).strip()
    if s.upper() in BR_STATES:
        return s.upper()
    return BR_STATE_BY_NAME.get(strip_accents(s.lower()))


def event_id(url: str) -> str:
    return sha1(canonical_url(url).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- extração genérica (JSON-LD e JSON embutido)
NAME_KEYS = ("name", "title", "eventName", "event_name")
START_KEYS = ("startDate", "start_at", "start_date", "startTime", "start_time", "dateTime", "starts_at", "startsAt",
              "start_datetime", "date_start", "data_inicio", "beginDate")
END_KEYS = ("endDate", "end_at", "end_date", "endTime", "end_time", "endDateTime", "ends_at", "endsAt", "end_datetime",
            "date_end", "data_fim")
URL_KEYS = ("url", "event_url", "eventUrl", "link", "permalink", "canonical_url", "absolute_url")


class _Refs(dict):
    """Resolve referências do tipo {"__ref": "Event:123"} (estado Apollo usado pelo Meetup)."""
    def get_ref(self, v):
        if isinstance(v, dict) and set(v) == {"__ref"}:
            return self.get(v["__ref"], {})
        return v


def _collect_refs(obj, refs: _Refs, depth=0) -> None:
    if depth > 12:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, dict) and re.match(r"^[A-Z]\w+:[\w\-]+$", str(k)):
                refs[k] = v
            _collect_refs(v, refs, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            _collect_refs(v, refs, depth + 1)


def _first(d: dict, keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def _location(d: dict, refs: _Refs) -> dict:
    out = {"city": None, "state": None, "country": None, "venue": None, "mode": None}
    mode = str(d.get("eventAttendanceMode") or "")
    if "Mixed" in mode:
        out["mode"] = "hibrido"
    elif "Online" in mode:
        out["mode"] = "online"
    elif "Offline" in mode:
        out["mode"] = "presencial"
    lt = str(d.get("location_type") or d.get("locationType") or d.get("eventType") or d.get("event_type") or "").lower()
    if lt in ("online", "zoom", "virtual", "meet", "google_meet", "online_event"):
        out["mode"] = out["mode"] or "online"
    elif lt in ("offline", "physical", "in_person", "presencial", "venue"):
        out["mode"] = out["mode"] or "presencial"
    elif lt == "hybrid":
        out["mode"] = "hibrido"
    for k in ("is_online_event", "isOnline", "online_event", "is_online", "online", "isVirtual"):
        if d.get(k) is True:
            out["mode"] = out["mode"] or "online"
    locs = d.get("location")
    locs = locs if isinstance(locs, list) else [locs]
    places = []
    for loc in locs:
        loc = refs.get_ref(loc)
        if isinstance(loc, dict):
            typ = str(loc.get("@type") or "")
            if typ == "VirtualLocation":
                out["mode"] = "hibrido" if out["mode"] == "presencial" or places else "online"
                continue
            places.append(loc)
        elif isinstance(loc, str) and loc.strip():
            places.append({"name": loc})
    for k in ("venue", "primary_venue", "geo_address_info", "address_info", "place", "local"):
        v = refs.get_ref(d.get(k))
        if isinstance(v, dict):
            places.append(v)
    for p in places:
        addr = refs.get_ref(p.get("address")) if isinstance(p.get("address"), (dict, str)) else None
        a = addr if isinstance(addr, dict) else {}
        out["venue"] = out["venue"] or _txt(p.get("name") or p.get("full_address") or (addr if isinstance(addr, str) else ""))[:160] or None
        out["city"] = out["city"] or _txt(p.get("city") or p.get("localized_city") or p.get("addressLocality") or a.get("addressLocality") or a.get("city"))[:80] or None
        out["state"] = out["state"] or _state(p.get("state") or p.get("region") or p.get("addressRegion") or a.get("addressRegion") or a.get("region") or a.get("state"))
        out["country"] = out["country"] or _country(_txt(p.get("country") or p.get("country_code") or p.get("addressCountry") or a.get("addressCountry") or a.get("country")))
    for k, dst in (("city", "city"), ("cidade", "city")):
        if not out[dst] and isinstance(d.get(k), str):
            out[dst] = d[k][:80]
    for k in ("state", "uf", "siglaEstado"):
        if not out["state"] and isinstance(d.get(k), str):
            out["state"] = _state(d[k])
    if not out["country"] and isinstance(d.get("country"), str):
        out["country"] = _country(d["country"])
    if out["venue"] and not out["mode"] and ONLINE_WORDS.search(strip_accents(out["venue"].lower())):
        out["mode"] = "online"
    return out


def _organizer(d: dict, parent: dict | None, refs: _Refs) -> str | None:
    for k in ("organizer", "primary_organizer", "group", "organization", "produtor", "host", "calendar"):
        v = refs.get_ref(d.get(k))
        if isinstance(v, list):
            v = refs.get_ref(v[0]) if v else None
        name = _txt(v)
        if name:
            return name[:120]
    if parent:
        for k in ("calendar", "organizer", "group"):
            name = _txt(refs.get_ref(parent.get(k)))
            if name:
                return name[:120]
        hosts = parent.get("hosts") or d.get("hosts")
        if isinstance(hosts, list) and hosts:
            name = _txt(refs.get_ref(hosts[0]))
            if name:
                return name[:120]
    return None


def _image(d: dict, refs: _Refs) -> str | None:
    for k in ("image", "cover_url", "image_url", "imageUrl", "logo", "featuredEventPhoto", "banner", "thumbnail"):
        v = refs.get_ref(d.get(k))
        if isinstance(v, list):
            v = v[0] if v else None
        if isinstance(v, dict):
            v = v.get("url") or v.get("highResUrl") or v.get("baseUrl") or v.get("original")
        if isinstance(v, str) and v.startswith("http"):
            return v
    return None


def _from_obj(d: dict, parent: dict | None, refs: _Refs, base: str) -> dict | None:
    name = _first(d, NAME_KEYS)
    start_v = _first(d, START_KEYS)
    if not isinstance(name, str) or start_v is None:
        return None
    typ = d.get("@type")
    typ = " ".join(typ) if isinstance(typ, list) else str(typ or "")
    if typ and "Event" not in typ and typ not in ("ListItem",):
        return None
    start, all_day = _date(start_v)
    if not start and isinstance(start_v, str) and isinstance(d.get("start_time"), str):
        start, all_day = _date(f"{start_v}T{d['start_time']}")
    # Eventbrite separa data e hora (start_date + start_time)
    if all_day and isinstance(d.get("start_time"), str) and re.match(r"^\d{2}:\d{2}", d["start_time"]):
        start2, _ = _date(f"{str(start_v)[:10]}T{d['start_time'][:5]}")
        if start2:
            start, all_day = start2, False
    if not start:
        return None
    end_v = _first(d, END_KEYS)
    end, end_all_day = _date(end_v) if end_v is not None else (None, False)
    url = _first(d, URL_KEYS)
    if isinstance(url, dict):
        url = url.get("href") or url.get("url")
    if not isinstance(url, str) or not url.strip():
        return None
    url = urljoin(base, url.strip())
    if not url.startswith("http"):
        return None
    loc = _location(d, refs)
    if not loc["mode"] and parent:
        loc_p = _location(parent, refs)
        loc = {k: loc[k] or loc_p[k] for k in loc}
    tags = d.get("keywords") or d.get("tags") or d.get("topics") or d.get("categories") or ""
    if isinstance(tags, list):
        tags = ", ".join(_txt(refs.get_ref(t)) for t in tags[:12])
    desc = d.get("description") or d.get("summary") or d.get("descricao") or ""
    return {
        "title": clean_text(name)[:220], "url": url, "start_dt": start, "all_day": all_day,
        "end_dt": end if end and end >= start else None, "end_all_day": end_all_day,
        "mode": loc["mode"], "city": loc["city"], "state": loc["state"], "country": loc["country"], "venue": loc["venue"],
        "organizer": _organizer(d, parent, refs), "description": _txt(desc)[:600], "tags": _txt(tags)[:300],
        "image": _image(d, refs),
    }


def extract_events(blobs: list, base: str) -> list[dict]:
    """Percorre JSON-LD e JSON embutido procurando objetos com cara de evento (nome + data + link)."""
    refs = _Refs()
    for b in blobs:
        _collect_refs(b, refs)
    out, seen = [], set()

    def walk(obj, parent=None, depth=0):
        if depth > 25:
            return
        if isinstance(obj, dict):
            ev = _from_obj(obj, parent, refs, base)
            if ev and ev["url"] not in seen:
                seen.add(ev["url"])
                out.append(ev)
            for k, v in obj.items():
                if isinstance(v, dict) and set(v) == {"__ref"}:
                    continue
                walk(v, obj, depth + 1)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, parent, depth + 1)

    for b in blobs:
        walk(b)
    return out


JSONLD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
NEXT_RE = re.compile(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', re.S | re.I)
ASSIGN_RE = re.compile(r"(?:window\.__SERVER_DATA__|window\.__APOLLO_STATE__|window\.__INITIAL_STATE__|window\.__NUXT__)\s*=\s*(\{.*?\})\s*;?\s*</script>", re.S)


def page_blobs(html: str) -> list:
    blobs = []
    for raw in JSONLD_RE.findall(html):
        try:
            blobs.append(json.loads(raw.strip()))
        except ValueError:
            try:
                blobs.append(json.loads(re.sub(r"[\x00-\x1f]", " ", raw.strip())))
            except ValueError:
                pass
    for raw in NEXT_RE.findall(html) + ASSIGN_RE.findall(html):
        try:
            blobs.append(json.loads(raw))
        except ValueError:
            pass
    blobs.extend(_rsc_blobs(html))
    return blobs


RSC_RE = re.compile(r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\]\)', re.S)


def _rsc_blobs(html: str) -> list:
    """Sites em Next.js (app router, ex.: Sympla) mandam os dados em pedaços self.__next_f.push([1,"..."]):
    junta os pedaços e lê cada linha "id:JSON"."""
    parts = []
    for lit in RSC_RE.findall(html):
        try:
            parts.append(json.loads(lit))
        except ValueError:
            pass
    out = []
    for line in "".join(parts).split("\n"):
        m = re.match(r"^[0-9a-zA-Z]{1,6}:(?=[\[{])", line)
        if not m:
            continue
        try:
            out.append(json.loads(line[m.end():]))
        except ValueError:
            pass
    return out


# ---------------------------------------------------------------- coletores
def _get(url: str) -> httpx.Response:
    if not http.allowed_by_robots(url):
        raise RuntimeError("bloqueado pelo robots.txt do site")
    r = http.get(url, max_bytes=6_000_000)
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}")
    return r


def fetch_page(src: dict) -> list[dict]:
    r = _get(src["url"])
    evs = extract_events(page_blobs(r.text), str(r.url))
    return evs


def fetch_ical(src: dict) -> list[dict]:
    r = _get(src["url"])
    text = re.sub(r"\r?\n[ \t]", "", r.text)  # desdobra linhas
    cal = re.search(r"^X-WR-CALNAME:(.*)$", text, re.M)
    out = []
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        f = {}
        for line in block.strip().splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            name, _, params = k.partition(";")
            f[name.upper()] = (v.strip(), params)
        if "SUMMARY" not in f or "DTSTART" not in f:
            continue
        unesc = lambda s: s.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")
        start, all_day = _ical_date(*f["DTSTART"])
        if not start:
            continue
        end, _ = _ical_date(*f["DTEND"]) if "DTEND" in f else (None, False)
        url = f.get("URL", ("", ""))[0] or None
        loc = unesc(f.get("LOCATION", ("", ""))[0])
        desc = unesc(f.get("DESCRIPTION", ("", ""))[0])
        if not url:
            m = re.search(r"https?://\S+", desc)
            url = m.group(0) if m else None
        if not url:
            continue
        loc_low = strip_accents(loc.lower())
        mode = "online" if (not loc or ONLINE_WORDS.search(loc_low) or loc.startswith("http")) else "presencial"
        city = None
        if mode == "presencial":
            parts = [p.strip() for p in loc.split(",") if p.strip()]
            idx = [i for i, p in enumerate(parts) if _state(p)]
            if idx and idx[-1] > 0:
                city = parts[idx[-1] - 1]  # "Rua X, 100, São Paulo, SP": a cidade vem antes do estado
        out.append({
            "title": unesc(f["SUMMARY"][0])[:220], "url": url, "start_dt": start, "all_day": all_day,
            "end_dt": end if end and end >= start else None, "end_all_day": False, "mode": mode, "city": city,
            "state": next((_state(p.strip()) for p in reversed(loc.split(",")) if _state(p.strip())), None),
            "country": None, "venue": None if mode == "online" else loc[:160] or None,
            "organizer": src.get("organizer") or (cal.group(1).strip() if cal else None),
            "description": clean_text(desc)[:600], "tags": "", "image": None,
        })
    return out


def _ical_date(value: str, params: str) -> tuple[datetime | None, bool]:
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})?(Z)?)?$", value)
    if not m:
        return None, False
    y, mo, d = int(m[1]), int(m[2]), int(m[3])
    if not m[4]:
        return datetime(y, mo, d, 12, tzinfo=BRT).astimezone(timezone.utc), True
    tz = timezone.utc
    if not m[7]:
        tzid = re.search(r"TZID=([^;:]+)", params or "")
        tz = BRT
        if tzid:
            try:
                from zoneinfo import ZoneInfo
                tz = ZoneInfo(tzid.group(1).strip('"'))
            except Exception:
                tz = BRT
    return datetime(y, mo, d, int(m[4]), int(m[5]), int(m[6] or 0), tzinfo=tz).astimezone(timezone.utc), False


EN_MONTHS = {m: i for i, m in enumerate(
    "january february march april may june july august september october november december".split(), 1)}
EN_DATE = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})"
                     r"(?:\s*[-–]\s*(?:(January|February|March|April|May|June|July|August|September|October|November|December)\s+)?(\d{1,2}))?,\s*(\d{4})")


def parse_devevents_desc(text: str) -> dict | None:
    """'X is happening on December 10, 2026, Online.' / '... on April 13, 2027 in Las Cruces, United States, North America.'"""
    t = clean_text(text)
    m = EN_DATE.search(t)
    if not m:
        return None
    y = int(m[5])
    mo = EN_MONTHS[m[1].lower()]
    start = datetime(y, mo, int(m[2]), 12, tzinfo=BRT)
    end = None
    if m[4]:
        mo2 = EN_MONTHS[m[3].lower()] if m[3] else mo
        try:
            end = datetime(y + (1 if mo2 < mo else 0), mo2, int(m[4]), 12, tzinfo=BRT)
        except ValueError:
            end = None
    rest = t[m.end():]
    out = {"start_dt": start.astimezone(timezone.utc), "end_dt": end.astimezone(timezone.utc) if end else None,
           "mode": None, "city": None, "country": None}
    if re.match(r"^[\s,]*online", rest, re.I) or re.search(r"\bonline\b", rest[:40], re.I):
        out["mode"] = "online"
    loc = re.match(r"^\s*(?:,\s*)?in\s+([^.]+)", rest)
    if loc:
        parts = [p.strip() for p in loc.group(1).split(",") if p.strip()]
        out["city"] = parts[0] if parts else None
        out["country"] = _country(parts[1]) if len(parts) > 1 else None
        out["mode"] = "hibrido" if out["mode"] == "online" else "presencial"
    return out


def fetch_devevents(src: dict) -> list[dict]:
    r = _get(src["url"])
    feed = feedparser.parse(r.content)
    out = []
    for e in feed.entries:
        info = parse_devevents_desc(e.get("summary") or e.get("description") or "")
        link = e.get("link")
        if not info or not link:
            continue
        tags = ", ".join(t.get("term", "") for t in e.get("tags", []) if t.get("term"))
        img = next((x.get("href") or x.get("url") for x in e.get("enclosures", []) if (x.get("type") or "").startswith("image")), None)
        out.append({
            "title": clean_text(e.get("title"))[:220], "url": link, "start_dt": info["start_dt"], "all_day": True,
            "end_dt": info["end_dt"], "end_all_day": True, "mode": info["mode"], "city": info["city"], "state": None,
            "country": info["country"], "venue": None, "organizer": None,
            "description": clean_text(e.get("summary"))[:600], "tags": tags, "image": img,
        })
    return out


# assuntos dos arquivos do confs.tech, em palavras que os temas reconhecem
CONFS_TAGS = {"data": "dados big data analytics", "devops": "devops cloud", "security": "cybersecurity", "sre": "sre devops",
              "iot": "iot", "leadership": "tech leadership", "product": "product management", "networking": "infraestrutura",
              "opensource": "open source", "api": "api", "general": "software developers", "dotnet": ".net"}


def fetch_confstech(src: dict) -> list[dict]:
    year = datetime.now(BRT).year
    out, errors, ok = [], [], 0
    for y in (year, year + 1):
        for topic in src.get("topics", ["general"]):
            url = src["url"].format(year=y, topic=topic)
            try:
                r = http.get(url)
            except httpx.HTTPError as e:
                errors.append(f"{topic}/{y}: {e.__class__.__name__}")
                continue
            if r.status_code == 404:
                continue
            if r.status_code >= 400:
                errors.append(f"{topic}/{y}: HTTP {r.status_code}")
                continue
            ok += 1
            try:
                items = r.json()
            except ValueError:
                continue
            for c in items:
                start, _ = _date(c.get("startDate"))
                if not start or not c.get("url") or not c.get("name"):
                    continue
                end, _ = _date(c.get("endDate"))
                city = c.get("city") or None
                online = bool(c.get("online"))
                if city and city.lower() == "online":
                    city = None
                mode = "hibrido" if online and city else "online" if online else "presencial"
                out.append({
                    "title": c["name"][:220], "url": c["url"], "start_dt": start, "all_day": True, "end_dt": end,
                    "end_all_day": True, "mode": mode, "city": city, "state": None, "country": _country(c.get("country")),
                    "venue": None, "organizer": None, "description": "", "tags": CONFS_TAGS.get(topic, topic), "image": None,
                })
    if not ok and errors:
        raise RuntimeError("; ".join(errors[:3]))
    return out


FETCHERS = {"page": fetch_page, "ical": fetch_ical, "devevents": fetch_devevents, "confstech": fetch_confstech}


# ---------------------------------------------------------------- normalização final
def finalize(raw: dict, src: dict, cfg: dict, today: date) -> dict | None:
    """Aplica formato, país, temas e filtros. Retorna None quando o evento não deve entrar."""
    ev = dict(raw)
    if not ev.get("title") or not ev.get("url", "").startswith("http"):
        return None
    start, end = ev.pop("start_dt"), ev.pop("end_dt", None)
    last_day = (end or start).astimezone(BRT).date()
    if last_day < today or start.astimezone(BRT).date() > today + timedelta(days=MAX_AHEAD_DAYS):
        return None
    low = strip_accents(f"{ev['title']} {ev.get('venue') or ''}".lower())
    mode = ev.get("mode")
    if HYBRID_WORDS.search(low):
        mode = "hibrido"
    if not mode:
        if "/evento-online/" in ev["url"] or (ONLINE_WORDS.search(low) and not ev.get("city")):
            mode = "online"
        elif ev.get("city") or ev.get("venue"):
            mode = "presencial"
        else:
            mode = "online" if ONLINE_WORDS.search(strip_accents((ev.get("description") or "").lower())) else None
    ev["format"] = mode or "nao_informado"
    country = ev.get("country") or (BR_STATES.get(ev.get("state") or "") and "BR")
    if not country and mode in ("presencial", "hibrido") and src.get("country"):
        country = src["country"]
    if ev["format"] == "presencial" and country and country != "BR":
        return None  # presencial fora do Brasil não interessa
    if ev["format"] in ("presencial", "nao_informado") and not country and not src.get("country"):
        return None  # sem saber onde é, um evento presencial pode ser em qualquer país
    ev["country"] = country
    if excluded(ev, cfg):
        return None
    themes = themes_for(ev, cfg)
    if not themes and src.get("require_topic"):
        return None
    ev["themes"] = themes or ["geral"]
    ev["start"] = _iso(start, ev.pop("all_day", False))
    ev["end"] = _iso(end, ev.pop("end_all_day", False)) if end else None
    ev.pop("mode", None)
    return ev


def scope_of(ev: dict) -> str:
    """Brasil quando é no Brasil ou é online em português; senão, internacional."""
    if ev.get("country") == "BR":
        return "brasil"
    if ev.get("country"):
        return "internacional"
    text = f"{ev.get('title') or ''}. {ev.get('description') or ''}"
    return "brasil" if detect_lang(text) == "pt" else "internacional"


# ---------------------------------------------------------------- banco e coleta
def init() -> None:
    with db.WRITE_LOCK, db.session() as c:
        c.executescript(SCHEMA)


def _save(events: list[dict], src: dict) -> int:
    now = db.iso(db.now_utc())
    saved = 0
    with db.WRITE_LOCK, db.session() as c:
        for ev in events:
            eid = event_id(ev["url"])
            tn = norm_title(ev["title"])
            dup = c.execute("SELECT id FROM events WHERE id<>? AND title_norm=? AND substr(start,1,10)=?",
                            (eid, tn, ev["start"][:10])).fetchone()
            if dup:
                continue  # o mesmo evento já veio por outra fonte
            c.execute(
                """INSERT INTO events (id,url,title,title_norm,start,end,all_day,format,city,state,country,venue,organizer,
                   description,tags,image,source_id,source_name,first_seen,last_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET title=excluded.title, title_norm=excluded.title_norm, start=excluded.start,
                   end=excluded.end, all_day=excluded.all_day, format=excluded.format,
                   city=coalesce(excluded.city, events.city), state=coalesce(excluded.state, events.state),
                   country=coalesce(excluded.country, events.country), venue=coalesce(excluded.venue, events.venue),
                   organizer=coalesce(excluded.organizer, events.organizer),
                   description=CASE WHEN excluded.description<>'' THEN excluded.description ELSE events.description END,
                   tags=excluded.tags, image=coalesce(excluded.image, events.image), last_seen=excluded.last_seen""",
                (eid, ev["url"], ev["title"], tn, ev["start"], ev["end"], int(len(ev["start"]) == 10), ev["format"],
                 ev.get("city"), ev.get("state"), ev.get("country"), ev.get("venue"), ev.get("organizer"),
                 ev.get("description") or "", ev.get("tags") or "", ev.get("image"), src["id"], src["name"], now, now))
            saved += 1
    return saved


def source_states() -> dict:
    with db.session() as c:
        return {r["id"]: dict(r) for r in c.execute("SELECT * FROM event_sources")}


def collect(force: bool = False, only: list[str] | None = None) -> dict:
    """Coleta as fontes de eventos vencidas. Falhas não interrompem nada: ficam registradas por fonte."""
    if not _lock.acquire(blocking=False):
        return {"skipped": True}
    try:
        init()
        cfg = load_config()
        states = source_states()
        now = db.now_utc()
        today = now.astimezone(BRT).date()
        summary = {}
        for src in cfg.get("sources", []):
            if not src.get("enabled", True) or (only and src["id"] not in only):
                continue
            st = states.get(src["id"]) or {}
            if not force and not only and st.get("next_run_at") and st["next_run_at"] > db.iso(now + timedelta(minutes=10)):
                continue
            interval = int(src.get("interval_min") or cfg.get("interval_min") or 360)
            try:
                raw = FETCHERS[src["type"]](src)
                kept = [e for e in (finalize(r, src, cfg, today) for r in raw) if e]
                saved = _save(kept, src)
                state = {"status": "ok", "error": None, "failures": 0, "found": len(raw), "kept": saved}
                log.info("Eventos %s: %s lidos, %s mantidos", src["id"], len(raw), saved)
            except Exception as e:  # noqa: BLE001 — uma fonte com problema não derruba a coleta
                fails = (st.get("failures") or 0) + 1
                state = {"status": "erro", "error": str(e)[:300] or e.__class__.__name__, "failures": fails,
                         "found": 0, "kept": 0}
                interval = min(interval * (2 ** min(fails - 1, 2)), 1440)
                log.warning("Eventos %s: falhou (%s)", src["id"], state["error"])
            state["next_run_at"] = db.iso(now + timedelta(minutes=interval))
            with db.WRITE_LOCK, db.session() as c:
                c.execute("""INSERT INTO event_sources (id,last_run_at,next_run_at,status,error,failures,found,kept)
                             VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_run_at=excluded.last_run_at,
                             next_run_at=excluded.next_run_at, status=excluded.status, error=excluded.error,
                             failures=excluded.failures, found=excluded.found, kept=excluded.kept""",
                          (src["id"], db.iso(now), state["next_run_at"], state["status"], state["error"],
                           state["failures"], state["found"], state["kept"]))
            summary[src["id"]] = state
        prune()
        return summary
    finally:
        _lock.release()


def prune() -> None:
    limit = (db.now_utc().astimezone(BRT).date() - timedelta(days=KEEP_PAST_DAYS)).isoformat()
    with db.WRITE_LOCK, db.session() as c:
        c.execute("DELETE FROM events WHERE substr(coalesce(end, start),1,10) < ?", (limit,))


def upcoming() -> dict:
    """Eventos que ainda não terminaram (pelo horário de Brasília), com temas recalculados pelas regras atuais."""
    init()
    cfg = load_config()
    today = db.now_utc().astimezone(BRT).date().isoformat()
    with db.session() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM events WHERE substr(coalesce(end, start),1,10) >= ? ORDER BY start", (today,))]
    srcs = {s["id"]: s for s in cfg.get("sources", [])}
    events = []
    for r in rows:
        src = srcs.get(r["source_id"], {})
        if src and not src.get("enabled", True):
            continue
        if excluded(r, cfg):
            continue
        themes = themes_for(r, cfg)
        if not themes and src.get("require_topic"):
            continue
        events.append({
            "id": r["id"], "title": r["title"], "url": r["url"], "start": r["start"], "end": r["end"],
            "all_day": bool(r["all_day"]), "format": r["format"], "city": r["city"], "state": r["state"],
            "country": r["country"], "venue": r["venue"], "organizer": r["organizer"],
            "description": (r["description"] or "")[:300], "image": r["image"], "themes": themes or ["geral"],
            "scope": scope_of(r), "source": r["source_name"], "source_id": r["source_id"],
        })
    states = source_states()
    sources = [{"id": s["id"], "name": s["name"], "type": s["type"], "url": s.get("url"),
                "enabled": s.get("enabled", True), **{k: states.get(s["id"], {}).get(k) for k in
                ("last_run_at", "status", "error", "found", "kept")}} for s in cfg.get("sources", [])]
    themes = [{"slug": t["slug"], "name": t["name"], "color": t["color"]} for t in cfg["themes"]]
    return {"generated_at": db.iso(db.now_utc()), "themes": themes, "sources": sources, "events": events}
