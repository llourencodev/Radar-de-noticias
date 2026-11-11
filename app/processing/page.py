"""Leitura da página original de uma publicação: imagem (og:image), data e texto para o resumo.

O texto é usado só para gerar o resumo; não é armazenado nem republicado.
"""
import json
import re

import httpx
from bs4 import BeautifulSoup

from .. import http
from .normalize import absolute, clean_text, parse_any_date, parse_pt_date, sanity_check_date

DATE_META = [
    ("property", "article:published_time"), ("name", "article:published_time"),
    ("itemprop", "datePublished"), ("name", "date"), ("name", "DC.date.issued"),
    ("name", "dcterms.created"), ("name", "pubdate"), ("name", "publish-date"),
    ("name", "parsely-pub-date"), ("name", "sailthru.date"), ("property", "og:published_time"),
]
PUBLISHED_TEXT = re.compile(
    r"(?:publicad[oa]\s*(?:em)?|publish(?:ed)?\s*(?:on)?|data de publica[cç][aã]o:?)\s*:?\s*"
    r"(\d{1,2}/\d{1,2}/\d{4}(?:\s*\d{1,2}[h:]\d{2})?)", re.I)
DOU_DATE = re.compile(r"publicad[oa] no d\.?o\.?u\.?\s+de\s+(\d{1,2})\.(\d{1,2})\.(\d{2,4})", re.I)
WRITTEN_DATE = re.compile(r"\b\d{1,2}(?:º|o)?\s+de\s+[A-Za-zçÇ]+\s+de\s+\d{4}", re.I)
BAD_IMG = re.compile(r"(logo|favicon|sprite|placeholder|default[-_]?(image|og)|blank\.)", re.I)


class PageInfo:
    def __init__(self):
        self.final_url = None
        self.image = None
        self.published = None
        self.precision = None
        self.description = ""
        self.text = ""
        self.section = ""


def _jsonld_dates(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if d.get("datePublished"):
                    yield d["datePublished"]
                stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
            elif isinstance(d, list):
                stack.extend(d)


def fetch_page(url: str, allow_text_date: bool = False) -> PageInfo | None:
    if not http.allowed_by_robots(url):
        return None
    try:
        r = http.get(url, max_bytes=1_500_000)
    except httpx.HTTPError:
        return None
    if r.status_code >= 400 or "html" not in r.headers.get("content-type", "html"):
        return None
    info = PageInfo()
    info.final_url = str(r.url)
    soup = BeautifulSoup(r.text, "html.parser")

    def meta(attr, name):
        tag = soup.find("meta", attrs={attr: name})
        return (tag.get("content") or "").strip() if tag else ""

    img = meta("property", "og:image") or meta("name", "twitter:image") or meta("property", "og:image:url")
    img = absolute(info.final_url, img)
    if img and not BAD_IMG.search(img):
        info.image = img

    for attr, name in DATE_META:
        v = meta(attr, name)
        if v:
            info.published, info.precision = parse_any_date(v)
            if info.published:
                break
    if not info.published:
        for v in _jsonld_dates(soup):
            info.published, info.precision = parse_any_date(v)
            if info.published:
                break
    if not info.published:
        tag = soup.find("time", attrs={"datetime": True})
        if tag:
            info.published, info.precision = parse_any_date(tag["datetime"])
    if not info.published:
        # Portais gov.br (Plone): <span class="documentPublished">publicado 06/11/2026 15h20</span>
        tag = soup.select_one(".documentPublished, .documentByLine, .data-publicacao")
        text = tag.get_text(" ") if tag else ""
        m = PUBLISHED_TEXT.search(text) or PUBLISHED_TEXT.search(soup.get_text(" ")[:20000])
        if m:
            info.published, info.precision = parse_pt_date(m.group(1))
        elif text:
            info.published, info.precision = parse_pt_date(text)
    content_root = soup.select_one("#content-core, #parent-fieldname-text, article, main")
    if not info.published and allow_text_date:
        # atos normativos (CONFAZ/Plone): "Publicado no DOU de 29.10.26" ou "Nº 131, DE 27 DE OUTUBRO DE 2026"
        body = (content_root or soup).get_text(" ")[:3000]
        m = DOU_DATE.search(body)
        if m:
            d, mo, y = int(m[1]), int(m[2]), int(m[3])
            info.published, info.precision = parse_pt_date(f"{d:02d}/{mo:02d}/{y + 2000 if y < 100 else y}")
        if not info.published:
            m = WRITTEN_DATE.search(body)
            if m:
                info.published, info.precision = parse_pt_date(m.group(0))
    info.published = sanity_check_date(info.published)

    info.description = clean_text(meta("property", "og:description") or meta("name", "description"))
    info.section = (meta("property", "article:section") or "").lower()
    for t in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        t.decompose()
    root = (soup.select_one("#content-core, #parent-fieldname-text, article, main")
            or soup.find(id=re.compile("content|conteudo", re.I)) or soup.body)
    if root:
        paras = [clean_text(p.get_text(" ")) for p in root.find_all(["p", "li"])]
        paras = [p for p in paras if len(p) > 60]
        if not paras:
            paras = [ln for ln in clean_text(root.get_text("\n")).split("\n") if len(ln) > 60]
        info.text = "\n".join(paras)[:12000]
    if not info.description:
        desc = soup.select_one(".documentDescription")
        info.description = clean_text(desc.get_text(" ")) if desc else ""
    return info
