"""Coletor para páginas sem RSS: lê a lista de links da página oficial.

Configuração por fonte (campo "options" em sources.json):
  link_pattern  expressão regular que o link da publicação deve atender (obrigatório)
  order         "first" (mais recentes no topo, padrão) ou "last" (mais recentes no fim da lista)
  limit         quantidade máxima de itens por coleta (padrão 15)
  min_title     tamanho mínimo do título (padrão 12)
  exclude_pattern  links que atendem a esta expressão são ignorados
  list_dates    false = não usar datas impressas na listagem (a data vem da página da publicação)
A URL pode conter {year}, substituído pelo ano corrente.
"""
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .. import http
from ..processing.normalize import absolute, clean_text, parse_pt_date
from .base import FetchResult, RawItem

EN_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
SKIP_TEXT = re.compile(r"^(leia mais|\.\.\.\(leia mais\)|saiba mais|read more|ver mais|mais)$", re.I)


def parse_en_date(text: str):
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}),\s+(\d{4})", text, re.I)
    if not m:
        return None, None
    try:
        from ..processing.normalize import BRT
        return datetime(int(m[3]), EN_MONTHS[m[1].lower()[:3]], int(m[2]), 12, tzinfo=BRT), "date"
    except ValueError:
        return None, None


def _title_of(a) -> tuple[str, bool]:
    """Título do link e se veio de um cabeçalho (h1–h5), que tem preferência."""
    h = a.find(["h1", "h2", "h3", "h4", "h5"])
    if h:
        return clean_text(h.get_text(" ")), True
    for s in a.find_all(string=True):
        t = clean_text(str(s))
        if len(t) >= 6:
            return t, False
    return clean_text(a.get("title") or a.get("aria-label") or ""), False


def _date_near(a, rx, base):
    """Procura a data no próprio link e nos elementos pais que contenham apenas esta publicação."""
    texts = [a.get_text(" ")]
    node = a
    own = absolute(base, a["href"])
    for _ in range(3):
        node = node.parent
        if node is None:
            break
        others = {absolute(base, x["href"]) for x in node.find_all("a", href=True)}
        others = {u for u in others if u and u != own and rx.search(u)}
        if others:
            break
        texts.append(node.get_text(" ")[:600])
    for t in texts:
        dt, prec = parse_pt_date(t)
        if not dt:
            dt, prec = parse_en_date(t)
        if dt:
            return dt, prec
    return None, None


def fetch(source: dict) -> FetchResult:
    opts = source.get("options") or {}
    url = (source.get("url") or "").replace("{year}", str(datetime.now().year))
    pattern = opts.get("link_pattern")
    if not pattern:
        return FetchResult("erro", error="Fonte HTML sem 'link_pattern' configurado")
    if not http.allowed_by_robots(url):
        return FetchResult("erro", error="Leitura não permitida pelo robots.txt do site")
    try:
        r = http.get(url)
    except httpx.HTTPError as ex:
        return FetchResult("erro", error=f"{type(ex).__name__}: {ex}"[:300])
    if r.status_code >= 400:
        return FetchResult("erro", r.status_code, error=f"HTTP {r.status_code}")

    soup = BeautifulSoup(r.text, "html.parser")
    rx = re.compile(pattern, re.I)
    exclude = re.compile(opts["exclude_pattern"], re.I) if opts.get("exclude_pattern") else None
    use_list_dates = opts.get("list_dates", True)
    min_title = int(opts.get("min_title", 12))
    found: dict[str, RawItem] = {}
    order: list[str] = []
    for a in soup.find_all("a", href=True):
        link = absolute(str(r.url), a["href"])
        if not link or not rx.search(link) or (exclude and exclude.search(link)):
            continue
        title, from_heading = _title_of(a)
        if SKIP_TEXT.match(title) or re.fullmatch(r"[\d/\.\s]+", title or ""):
            title = ""
        dt, prec = _date_near(a, rx, str(r.url)) if use_list_dates else (None, None)
        if link not in found:
            found[link] = RawItem(title=title, url=link, outlet=source["name"], published=dt,
                                  date_precision=prec)
            found[link].tags = ["h"] if from_heading and title else []
            order.append(link)
        else:
            it = found[link]
            # o primeiro texto do link é o título; um cabeçalho (h1–h5) tem preferência sobre descrições
            if title and (not it.title or (from_heading and "h" not in it.tags)):
                it.title = title
                it.tags = ["h"] if from_heading else it.tags
            if not it.published and dt:
                it.published, it.date_precision = dt, prec
    items = [found[u] for u in order if len(found[u].title) >= min_title]
    for it in items:
        it.tags = []
    limit = int(opts.get("limit", 15))
    items = items[-limit:][::-1] if opts.get("order") == "last" else items[:limit]
    if not items:
        return FetchResult("erro", r.status_code, error="Nenhum link encontrado: o layout da página pode ter mudado")
    return FetchResult("ok", r.status_code, items)
