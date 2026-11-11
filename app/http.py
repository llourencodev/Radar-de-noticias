"""Cliente HTTP compartilhado: limite de requisições por site, robots.txt e cache condicional."""
import ssl
import threading
import time
from urllib import robotparser
from urllib.parse import urlparse

import httpx

from . import config

_client: httpx.Client | None = None
_client_lock = threading.Lock()
_host_locks: dict[str, threading.Lock] = {}
_host_last: dict[str, float] = {}
_host_guard = threading.Lock()
_robots: dict[str, tuple[float, robotparser.RobotFileParser | None]] = {}
ROBOTS_UA = "RadarInteligenteNoticias"


def ssl_context() -> ssl.SSLContext:
    """Usa os certificados do sistema operacional (Windows inclui os da rede/antivírus corporativo)."""
    try:
        import truststore  # opcional: mesma cadeia de confiança do navegador
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        ctx = ssl.create_default_context()
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
        return ctx


def client() -> httpx.Client:
    global _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(
                headers={
                    "User-Agent": config.USER_AGENT,
                    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml,*/*;q=0.8",
                },
                follow_redirects=True,
                verify=ssl_context(),
                timeout=httpx.Timeout(config.HTTP_TIMEOUT, connect=10),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return _client


def _throttle(url: str) -> None:
    host = urlparse(url).netloc.lower()
    with _host_guard:
        lock = _host_locks.setdefault(host, threading.Lock())
    with lock:
        wait = _host_last.get(host, 0) + config.HOST_MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _host_last[host] = time.monotonic()


def allowed_by_robots(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    cached = _robots.get(base)
    if cached and time.time() - cached[0] < 86400:
        rp = cached[1]
    else:
        rp = None
        try:
            _throttle(base)
            r = client().get(base + "/robots.txt", timeout=10)
            if r.status_code == 200 and "text" in r.headers.get("content-type", "text"):
                rp = robotparser.RobotFileParser()
                rp.parse(r.text.splitlines())
        except httpx.HTTPError:
            rp = None
        _robots[base] = (time.time(), rp)
    if rp is None:
        return True
    return rp.can_fetch(ROBOTS_UA, url)


def ascii_url(url: str) -> str:
    """Codifica caracteres não ASCII da URL (alguns sites publicam links com acentos)."""
    from urllib.parse import quote
    return url if url.isascii() else quote(url, safe=":/?#[]@!$&'()*+,;=%~")


def get(url: str, etag: str | None = None, last_modified: str | None = None,
        max_bytes: int = 3_000_000, **kw) -> httpx.Response:
    """GET com limite por site e cabeçalhos de cache condicional."""
    headers = kw.pop("headers", {}) or {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    url = ascii_url(url)
    _throttle(url)
    with client().stream("GET", url, headers=headers, **kw) as r:
        chunks, size = [], 0
        for chunk in r.iter_bytes():
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                break
        r._content = b"".join(chunks)
    return r


def post(url: str, **kw) -> httpx.Response:
    url = ascii_url(url)
    _throttle(url)
    return client().post(url, **kw)
