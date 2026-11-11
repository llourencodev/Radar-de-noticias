"""Normalização: texto, URLs canônicas, datas e consultas de busca."""
import html
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

STOPWORDS = set("""
a o as os um uma uns umas de do da dos das no na nos nas em ao aos à às e é ou que se por para pra com sem
sobre entre como mais menos já não sim seu sua seus suas este esta isso essa esse aquele foi ser são está
the of and to in for on with at by from is are was be as an it its this that new nova novo novas novos
ultimas últimas ultimo último noticias notícias noticia notícia
""".split())

TRACKING_PARAMS = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$|ref_src|cmpid|ncid|ocid|amp$|output$|__)", re.I)

PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10,
    "nov": 11, "dez": 12,
}
BRT = timezone(timedelta(hours=-3))


def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def clean_text(s: str | None) -> str:
    """Remove HTML e espaços extras de um trecho."""
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?s)<br\s*/?>|</p>", "\n", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v ]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def norm_title(title: str) -> str:
    t = strip_accents(title.lower())
    t = re.sub(r"[^\w#+\s\.]", " ", t)
    words = [w for w in t.split() if w not in STOPWORDS and len(w) > 1]
    return " ".join(words)


def canonical_url(url: str) -> str:
    """URL sem parâmetros de rastreamento, sem fragmento e com host em minúsculas."""
    try:
        p = urlparse(url.strip())
    except ValueError:
        return url.strip()
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not TRACKING_PARAMS.match(k)]
    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = p.path.rstrip("/") or "/"
    return urlunparse(("https" if p.scheme in ("http", "https") else p.scheme, netloc, path, "", urlencode(query), ""))


def domain_of(url: str) -> str:
    try:
        d = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return d[4:] if d.startswith("www.") else d


def absolute(base: str, href: str | None) -> str | None:
    if not href:
        return None
    href = href.strip()
    if href.startswith("data:") or href.startswith("javascript:"):
        return None
    u = urljoin(base, href)
    return u if u.startswith("http") else None


# ---------------------------------------------------------------- datas
def parse_any_date(value) -> tuple[datetime | None, str | None]:
    """Converte string/struct em datetime UTC. Retorna (data, precisão: 'datetime' | 'date')."""
    if value is None or value == "":
        return None, None
    if hasattr(value, "tm_year"):
        try:
            return datetime(*value[:6], tzinfo=timezone.utc), "datetime"
        except (TypeError, ValueError):
            return None, None
    s = str(value).strip()
    # ISO 8601
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?)?", s)
    if m:
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        if m[4] is None:
            return _safe(y, mo, d, 12, 0, 0, BRT), "date"
        tz = timezone.utc
        if m[7] and m[7] != "Z":
            sign = 1 if m[7][0] == "+" else -1
            hh, mm = int(m[7][1:3]), int(m[7][-2:])
            tz = timezone(sign * timedelta(hours=hh, minutes=mm))
        elif not m[7]:
            tz = BRT
        return _safe(y, mo, d, int(m[4]), int(m[5]), int(m[6] or 0), tz), "datetime"
    # RFC 822 (RSS)
    try:
        dt = parsedate_to_datetime(s)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc), "datetime"
    except (TypeError, ValueError, IndexError):
        pass
    return parse_pt_date(s)


def _safe(y, mo, d, h, mi, se, tz):
    try:
        return datetime(y, mo, d, h, mi, se, tzinfo=tz).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_pt_date(text: str) -> tuple[datetime | None, str | None]:
    """Datas em português: 30/10/2026, 30/10/2026 15h20, 30.10.2026, '10 de outubro de 2026'."""
    if not text:
        return None, None
    t = strip_accents(text.lower())
    m = re.search(r"\b(\d{1,2})[/\.](\d{1,2})[/\.](\d{4})(?:\D{1,8}(\d{1,2})[h:](\d{2}))?", t)
    if m:
        d, mo, y = int(m[1]), int(m[2]), int(m[3])
        if m[4]:
            return _safe(y, mo, d, int(m[4]), int(m[5]), 0, BRT), "datetime"
        return _safe(y, mo, d, 12, 0, 0, BRT), "date"
    m = re.search(r"\b(\d{1,2})(?:º|o)?\s+de\s+([a-z]+)\s+de\s+(\d{4})", t)
    if m and m[2] in PT_MONTHS:
        return _safe(int(m[3]), PT_MONTHS[m[2]], int(m[1]), 12, 0, 0, BRT), "date"
    return None, None


def sanity_check_date(dt: datetime | None) -> datetime | None:
    """Datas no futuro (mais de 1 dia) ou absurdas são tratadas como não confirmadas."""
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if dt > now + timedelta(days=1) or dt.year < 1995:
        return None
    return dt


# ---------------------------------------------------------------- idioma
_PT = set("de da do das dos que para com uma não são pelo pela também sobre foi após entre mais nova novo".split())
_EN = set("the and for with that this from are was has have will new into about after more its their".split())


def detect_lang(text: str) -> str:
    words = re.findall(r"[a-záéíóúãõçâêô]+", (text or "").lower())
    pt = sum(w in _PT for w in words)
    en = sum(w in _EN for w in words)
    if pt == en == 0:
        return "pt" if re.search(r"[ãõç]", text or "") else "?"
    return "pt" if pt >= en else "en"


# ---------------------------------------------------------------- busca
def _fts_term(tok: str) -> str | None:
    tok = strip_accents(tok.lower()).strip(".-")
    if not tok:
        return None
    if "-" in tok or "." in tok:
        parts = [p for p in re.split(r"[-\.]", tok) if p]
        return '"' + " ".join(parts) + '"' if parts else None
    if tok in STOPWORDS:
        return None
    if re.search(r"[#+]", tok):
        return '"' + tok + '"'
    if len(tok) >= 6 and tok.isalpha():
        return tok[: max(4, len(tok) - 3)] + "*"
    if len(tok) == 1 and tok.isalpha():
        return None
    return '"' + tok + '"'


def fts_terms(q: str) -> list[str]:
    toks = re.findall(r"[\w][\w#+\-\.]*[\w#+]|[\w]", q, flags=re.UNICODE)
    terms = []
    for t in toks:
        ft = _fts_term(t)
        if ft and ft not in terms:
            terms.append(ft)
    return terms


def fts_query(q: str) -> tuple[str, str]:
    """Gera (consulta AND, consulta OR) para FTS5 a partir do texto livre do usuário."""
    toks = re.findall(r"[\w][\w#+\-\.]*[\w#+]|[\w]", q, flags=re.UNICODE)
    terms = []
    for t in toks:
        ft = _fts_term(t)
        if ft and ft not in terms:
            terms.append(ft)
    if not terms:
        return "", ""
    return " AND ".join(terms), " OR ".join(terms)
