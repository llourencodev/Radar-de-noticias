"""Coletor RSS/Atom com cache condicional (ETag / Last-Modified)."""
import re

import feedparser
import httpx

from .. import http
from ..processing.normalize import absolute, clean_text, parse_any_date
from .base import FetchResult, RawItem

NOT_ARTICLE = re.compile(r"\.(png|jpe?g|gif|webp|svg)(/view)?$", re.I)
IMG_IN_HTML = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.I)


COMMIT_MARKS = {"+": "Novo: ", "-": "Removido: ", "*": "", "!": ""}


def commit_title(text: str) -> str:
    """Feeds de commits (ex.: SVN do ACBr) trazem só a data como título; o título vira a mensagem do commit:
    "12/11/2026 -- ACBrNFe.Classes -- [*] Alterado o tipo... Por: Fulano" -> "ACBrNFe.Classes: Alterado o tipo..."."""
    t = re.sub(r"\s+", " ", (text or "").replace("View Changes", " ")).strip()
    t = re.sub(r"^(?:data:?\s*)?\d{1,2}/\d{1,2}/\d{2,4}\s*", "", t, flags=re.I)
    t = re.sub(r"\s*\bpor:?\s+[^.]{2,80}$", "", t, flags=re.I).strip()
    unit = ""
    m = re.match(r"^--\s*(.+?)\s*(?:--|(?=\[[+\-*!]\]))\s*", t)
    if m:
        unit, t = m.group(1).strip(), t[m.end():]
    mark = ""
    m = re.match(r"^\[([+\-*!])\]\s*", t)
    if m:
        mark, t = COMMIT_MARKS.get(m.group(1), ""), t[m.end():]
    t = t.strip(" -.;")
    out = f"{unit}: {mark}{t}" if unit else f"{mark}{t}"
    return out[:180].rstrip() + ("…" if len(out) > 180 else "")


def commit_excerpt(text: str, link: str, author: str | None = None) -> str:
    """Resumo curto do commit (revisão e autor), para o card não repetir a mensagem que já é o título."""
    m = re.search(r"\bpor:?\s+([^.\n]{2,80}?)\s*(?:View Changes|$)", text or "", re.I)
    who = (m.group(1).strip() if m else None) or author
    rev = re.search(r"/(\d+)/?$", link or "")
    out = f"Revisão {rev.group(1)} do repositório SVN" if rev else "Alteração no repositório SVN"
    return out + (f", por {who}." if who else ".")


def _image_from_entry(e, base: str) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for m in e.get(key) or []:
            url = m.get("url")
            medium = (m.get("medium") or m.get("type") or "image").lower()
            if url and ("image" in medium or re.search(r"\.(jpe?g|png|webp|gif)(\?|$)", url, re.I)):
                return absolute(base, url)
    for enc in e.get("enclosures") or []:
        if (enc.get("type") or "").startswith("image") and enc.get("href"):
            return absolute(base, enc["href"])
    for link in e.get("links") or []:
        if link.get("rel") == "enclosure" and (link.get("type") or "").startswith("image"):
            return absolute(base, link.get("href"))
    html_blobs = [c.get("value", "") for c in e.get("content") or []] + [e.get("summary", "")]
    for blob in html_blobs:
        m = IMG_IN_HTML.search(blob or "")
        if m:
            u = absolute(base, m.group(1))
            if u and not re.search(r"(pixel|tracker|feeds\.feedburner|1x1|spacer)", u, re.I):
                return u
    return None


def parse_feed(content: bytes, base_url: str, default_outlet: str, commits: bool = False) -> list[RawItem]:
    feed = feedparser.parse(content)
    items = []
    for e in feed.entries:
        title = clean_text(e.get("title"))
        link = e.get("link") or ""
        if not title or not link:
            continue  # sem título ou link não há fonte identificável
        if NOT_ARTICLE.search(link):
            continue  # anexos (imagens) publicados no feed não são notícias
        published, precision = None, None
        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            if e.get(key):
                published, precision = parse_any_date(e.get(key))
                if published:
                    break
        if not published:
            for key in ("published", "updated", "dc_date"):
                if e.get(key):
                    published, precision = parse_any_date(e.get(key))
                    if published:
                        break
        body = ""
        if e.get("content"):
            body = max((c.get("value", "") for c in e["content"]), key=len)
        excerpt = clean_text(e.get("summary") or body)
        if len(excerpt) < 120 and body:
            excerpt = clean_text(body)
        if commits:
            title = commit_title(excerpt) or title
            if len(title) < 8:
                continue
            excerpt = commit_excerpt(excerpt, link, e.get("author"))
        img = _image_from_entry(e, link)
        src = e.get("source") or {}
        tags = [t.get("term", "") for t in e.get("tags") or [] if t.get("term")]
        items.append(RawItem(
            title=title, url=absolute(base_url, link) or link,
            outlet=(src.get("title") if src else None) or default_outlet,
            outlet_url=src.get("href") if src else None,
            published=published, date_precision=precision, excerpt=excerpt[:4000],
            image_url=img, image_origin="feed" if img else "nenhuma", tags=tags,
        ))
    return items


def fetch(source: dict) -> FetchResult:
    url = source["url"]
    try:
        r = http.get(url, etag=source.get("etag"), last_modified=source.get("last_modified"))
    except httpx.HTTPError as ex:
        return FetchResult("erro", error=f"{type(ex).__name__}: {ex}"[:300])
    if r.status_code == 304:
        return FetchResult("inalterado", 304, etag=source.get("etag"), last_modified=source.get("last_modified"))
    if r.status_code >= 400:
        return FetchResult("erro", r.status_code, error=f"HTTP {r.status_code}")
    commits = bool((source.get("options") or {}).get("commits"))
    items = parse_feed(r.content, str(r.url), source["name"], commits)
    prefix = (source.get("options") or {}).get("title_prefix")
    if prefix:  # ex.: "ACBr" — deixa claro o assunto quando a mensagem do commit não cita o projeto
        for it in items:
            if prefix.lower() not in it.title.lower():
                it.title = f"{prefix}: {it.title}"
    if not items and b"<rss" not in r.content[:2000] and b"<feed" not in r.content[:2000]:
        return FetchResult("erro", r.status_code, error="Resposta não é um feed RSS/Atom válido")
    return FetchResult("ok", r.status_code, items, r.headers.get("etag"), r.headers.get("last-modified"))
