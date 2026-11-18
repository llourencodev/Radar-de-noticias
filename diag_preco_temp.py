"""Temporário: mostra como cada fonte informa preço/gratuidade e certificado."""
import json, re, sys
from app import eventos, http

URLS = ["https://www.sympla.com.br/eventos/tecnologia", "https://luma.com/sao-paulo",
        "https://www.meetup.com/find/?keywords=tecnologia&location=br--S%C3%A3o%20Paulo",
        "https://dev.events/SA/BR", "https://www.meetup.com/aidev-saopaulo/events/ical/"]
KEY = re.compile(r"price|free|fee|ticket|offer|gratu|pago|paid|cost|valor|certif", re.I)

def walk(o, path, out, depth=0):
    if depth > 20: return
    if isinstance(o, dict):
        for k, v in o.items():
            if KEY.search(str(k)):
                s = json.dumps(v, ensure_ascii=False)[:200]
                out.setdefault(f"{path}.{k}" if len(path) < 1 else re.sub(r"\[\d+\]", "[]", f"{path}.{k}"), []).append(s)
            walk(v, f"{path}.{k}", out, depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:40]): walk(v, f"{path}[{i}]", out, depth + 1)

for u in URLS:
    print("=" * 20, u)
    try:
        r = http.get(u, max_bytes=6_000_000)
    except Exception as e:
        print("erro", e); continue
    t = r.text
    print("HTTP", r.status_code, len(t))
    if "ical" in u:
        for w in ("certific", "gratu", "free", "R$"):
            for m in list(re.finditer(w, t, re.I))[:3]: print(f"  [{w}]", repr(t[max(0, m.start()-120):m.start()+120]))
        continue
    blobs = eventos.page_blobs(t)
    out = {}
    for i, b in enumerate(blobs): walk(b, f"b{i}", out)
    for k, v in list(out.items())[:60]:
        print(f"  {k}  ({len(v)}x)  ex: {v[:3]}")
    evs = eventos.extract_events(blobs, str(r.url))
    print("  eventos:", len(evs), "| com 'certific' na descrição:", sum("certific" in (e['description'] or '').lower() for e in evs),
          "| com 'grat' na descrição/título:", sum("grat" in ((e['description'] or '') + e['title']).lower() for e in evs))
    for w in ("certificado", "certificate", "Gratuito", "Grátis", "isFree", "is_free"):
        for m in list(re.finditer(w, t))[:2]: print(f"  [{w}]", repr(t[max(0, m.start()-150):m.start()+150]))
