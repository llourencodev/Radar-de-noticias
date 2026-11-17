"""Testa cada fonte de eventos de config/events.json (sem gravar no banco) e mostra o que cada uma traria.

Uso:  .venv\\Scripts\\python.exe verificar_eventos.py              (todas)
      .venv\\Scripts\\python.exe verificar_eventos.py luma-ai      (uma fonte)
      .venv\\Scripts\\python.exe verificar_eventos.py --diagnostico (mostra o que há na página quando nada é encontrado)
"""
import sys
from collections import Counter
from datetime import datetime

from app import eventos, http
from app.processing.normalize import BRT


def diagnostico(src):
    try:
        r = http.get(src["url"], max_bytes=6_000_000)
        blobs = eventos.page_blobs(r.text)
        print(f"      HTTP {r.status_code}, {len(r.text)} caracteres, {len(blobs)} bloco(s) JSON;"
              f" ld+json={r.text.count('application/ld+json')} next_data={'__NEXT_DATA__' in r.text}")
        import re
        for key in ("start_at", "startDate", "start_date", "dateTime", "startTime", "data_inicio", "/evento/"):
            for m in list(re.finditer(re.escape(key), r.text))[:2]:
                print(f"      [{key}] ...{r.text[max(0, m.start() - 300):m.start() + 200]!r}...")
    except Exception as ex:  # noqa: BLE001
        print(f"      diagnóstico falhou: {ex}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    diag = "--diagnostico" in sys.argv
    cfg = eventos.load_config()
    today = datetime.now(BRT).date()
    total_ok = 0
    sources = [s for s in cfg["sources"] if not args or s["id"] in args]
    for src in sources:
        try:
            raw = eventos.FETCHERS[src["type"]](src)
        except Exception as ex:  # noqa: BLE001
            print(f"ERR {src['id']:<24} {type(ex).__name__}: {ex}")
            if diag and src["type"] == "page":
                diagnostico(src)
            continue
        kept = [e for e in (eventos.finalize(dict(r), src, cfg, today) for r in raw) if e]
        total_ok += bool(kept)
        fmts = Counter(e["format"] for e in kept)
        imgs = sum(1 for e in kept if e.get("image"))
        print(f"{'OK ' if kept else '-- '} {src['id']:<24} lidos={len(raw):<4} mantidos={len(kept):<4} com imagem={imgs:<4} {dict(fmts)}")
        for e in kept[:4]:
            print(f"      {e['start'][:16]} | {e['format']:<10} | {(e.get('city') or '-')[:18]:<18} | {','.join(e['themes'])[:30]:<30} | {e['title'][:70]}")
        if diag and kept and not imgs and src["type"] == "page":
            import re
            r = http.get(src["url"], max_bytes=6_000_000)
            for key in ("featuredEventPhoto", "highResUrl", "PhotoInfo"):
                for m in list(re.finditer(key, r.text))[:2]:
                    print(f"      [{key}] ...{r.text[max(0, m.start() - 150):m.start() + 200]!r}...")
        if not raw and diag and src["type"] == "page":
            diagnostico(src)
    print(f"\n{total_ok} de {len(sources)} fontes de eventos trouxeram eventos.")
