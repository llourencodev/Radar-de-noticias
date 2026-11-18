"""Temporário: preço e certificado nas páginas de cada evento."""
import json, re
from app import eventos, http

def show(t, words, n=2, w=200):
    for x in words:
        for m in list(re.finditer(x, t))[:n]:
            print(f"  [{x}]", repr(t[max(0, m.start()-w):m.start()+w]))

# 1) Sympla: chaves de um evento da listagem e link "Grátis"
r = http.get("https://www.sympla.com.br/eventos/tecnologia", max_bytes=6_000_000)
t = r.text
for m in re.finditer(r'href="([^"]+)"[^>]*>Grátis<', t): print("link gratis:", m.group(1))
for m in re.finditer(r'href="([^"]+)"[^>]*>Pago<', t): print("link pago:", m.group(1))
blobs = eventos.page_blobs(t)
found = []
def walk(o, d=0):
    if d > 25 or len(found) > 1: return
    if isinstance(o, dict):
        if eventos._from_obj(o, None, eventos._Refs(), "https://www.sympla.com.br/"):
            found.append(o); return
        for v in o.values(): walk(v, d+1)
    elif isinstance(o, list):
        for v in o: walk(v, d+1)
for b in blobs: walk(b)
for o in found: print("SYMPLA OBJ:", json.dumps(o, ensure_ascii=False)[:2500])
evs = eventos.extract_events(blobs, str(r.url))
urls = [e["url"] for e in evs[:6]]
# 2) páginas de eventos
lu = eventos.extract_events(eventos.page_blobs(http.get("https://luma.com/sao-paulo", max_bytes=6_000_000).text), "https://luma.com/")
mu = eventos.extract_events(eventos.page_blobs(http.get("https://www.meetup.com/find/?keywords=tecnologia&location=br--S%C3%A3o%20Paulo", max_bytes=6_000_000).text), "https://www.meetup.com/")
for u in urls[:4] + [e["url"] for e in lu[:2]] + [e["url"] for e in mu[:2]]:
    print("=" * 10, u)
    try:
        p = http.get(u, max_bytes=6_000_000)
    except Exception as ex:
        print("erro", ex); continue
    pt = p.text
    print("HTTP", p.status_code, len(pt))
    pe = eventos.extract_events(eventos.page_blobs(pt), str(p.url))
    me = [e for e in pe if eventos.canonical_url(e["url"]) == eventos.canonical_url(u)] or pe[:1]
    if me: print("  desc extraída:", len(me[0]["description"]), repr(me[0]["description"][:300]))
    show(pt, ["certificad", "Certificad", "isAccessibleForFree", '"price"', "lowPrice", "is_free", "feeSettings", "Gratuito", "Grátis", "R\\$ ?\\d"], n=2, w=160)
