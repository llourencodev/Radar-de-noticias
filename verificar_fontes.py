"""Testa cada fonte configurada (sem gravar no banco) e mostra quantos itens cada uma retorna.

Uso:  .venv\\Scripts\\python.exe verificar_fontes.py            (todas)
      .venv\\Scripts\\python.exe verificar_fontes.py anthropic  (uma fonte)
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from app import config
from app.collectors import html, rss, search

COLLECTORS = {"rss": rss.fetch, "html": html.fetch, "search": search.fetch}


def check(s):
    try:
        r = COLLECTORS[s["type"]](dict(s, etag=None, last_modified=None))
    except Exception as ex:  # noqa: BLE001
        return s, "erro", 0, f"{type(ex).__name__}: {ex}", None
    dated = sum(1 for i in r.items if i.published)
    imgs = sum(1 for i in r.items if i.image_url)
    first = r.items[0] if r.items else None
    return s, r.status, len(r.items), r.error or f"{dated} com data, {imgs} com imagem", first


if __name__ == "__main__":
    sources = json.loads((config.CONFIG_DIR / "sources.json").read_text(encoding="utf-8"))
    if len(sys.argv) > 1:
        sources = [s for s in sources if s["id"] in sys.argv[1:]]
    ok = 0
    with ThreadPoolExecutor(8) as ex:
        for s, status, n, info, first in ex.map(check, sources):
            ok += status == "ok" and n > 0
            print(f"{'OK ' if status == 'ok' and n else 'ERR'} {s['id']:<26} {s['type']:<6} itens={n:<3} {info}")
            if first:
                print(f"      ex.: {first.title[:90]} | {first.published} | {first.url[:90]}")
    print(f"\n{ok} de {len(sources)} fontes responderam com itens.")
