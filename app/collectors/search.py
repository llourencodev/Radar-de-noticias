"""Busca de notícias por tema: Google Notícias (RSS) e Bing Notícias (RSS). Ambos gratuitos, sem chave."""
import base64
import json
import re
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx

from .. import http
from . import rss
from .base import FetchResult

GOOGLE_LOCALES = {
    "pt": "hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "en": "hl=en-US&gl=US&ceid=US:en",
}


def google_url(query: str, days: int = 7, lang: str = "pt") -> str:
    q = f"{query} when:{days}d" if days else query
    return f"https://news.google.com/rss/search?q={quote_plus(q)}&{GOOGLE_LOCALES.get(lang, GOOGLE_LOCALES['pt'])}"


def bing_url(query: str, lang: str = "pt") -> str:
    loc = "setlang=pt-BR&cc=BR" if lang == "pt" else "setlang=en-US&cc=US"
    return f"https://www.bing.com/news/search?q={quote_plus(query)}&format=rss&{loc}&qft=sortbydate%3d%221%22"


def fetch(source: dict) -> FetchResult:
    opts = source.get("options") or {}
    engine = opts.get("engine", "google")
    lang = opts.get("lang", "pt")
    days = int(opts.get("days", 7))
    query = source.get("query") or ""
    url = google_url(query, days, lang) if engine == "google" else bing_url(query, lang)
    src = dict(source, url=url, etag=None, last_modified=None)  # buscas mudam sempre: sem cache condicional
    res = rss.fetch(src)
    if res.status != "ok":
        return res
    limit = int(opts.get("limit", 25))
    items = res.items[:limit]
    for it in items:
        it.via_aggregator = True
        if engine == "bing":
            original = bing_original_url(it.url)
            if original:
                it.url, it.via_aggregator = original, False
        else:
            # Google acrescenta " - Veículo" ao título; removemos só se coincidir com o veículo informado
            if it.outlet and it.title.endswith(" - " + it.outlet):
                it.title = it.title[: -len(" - " + it.outlet)].strip()
            it.image_url, it.image_origin = None, "nenhuma"  # miniaturas do Google não são da publicação
    res.items = items
    return res


def bing_original_url(url: str) -> str | None:
    try:
        p = urlparse(url)
        if "bing.com" in p.netloc:
            target = parse_qs(p.query).get("url", [None])[0]
            if target and target.startswith("http"):
                return target
    except ValueError:
        return None
    return None


# ---------------------------------------------------------------- Google News: link original
def _old_style_decode(article_id: str) -> str | None:
    try:
        raw = base64.urlsafe_b64decode(article_id + "=" * (-len(article_id) % 4))
    except (ValueError, TypeError):
        return None
    m = re.search(rb"(https?://[\x21-\x7e]+)", raw)
    if m and not raw.startswith(b"\x08\x13\x22\xae") and b"AU_yqL" not in raw[:10]:
        url = m.group(1).decode("ascii", "ignore")
        return url.split("\xd2")[0]
    return None


def resolve_google_url(url: str) -> str | None:
    """Descobre o endereço original de um link news.google.com. Retorna None se não for possível."""
    p = urlparse(url)
    if "news.google.com" not in p.netloc:
        return url
    m = re.search(r"/articles/([^/?#]+)", p.path)
    if not m:
        return None
    article_id = m.group(1)
    old = _old_style_decode(article_id)
    if old and "news.google.com" not in old:
        return old
    try:
        page = http.get(f"https://news.google.com/rss/articles/{article_id}", max_bytes=1_200_000)
        sig = re.search(r'data-n-a-sg="([^"]+)"', page.text)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page.text)
        if not (sig and ts):
            return None
        inner = (
            '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],'
            f'"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{article_id}",{ts.group(1)},"{sig.group(1)}"]'
        )
        payload = [[["Fbv4je", inner, None, "generic"]]]
        r = http.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            data={"f.req": json.dumps(payload)},
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        if r.status_code != 200:
            return None
        chunk = r.text.split("\n\n")[1]
        data = json.loads(chunk)
        decoded = json.loads(data[0][2])[1]
        return decoded if isinstance(decoded, str) and decoded.startswith("http") else None
    except (httpx.HTTPError, IndexError, ValueError, TypeError):
        return None
