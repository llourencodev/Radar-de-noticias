"""Temporário: Sympla — URL de gratuitos e preço na página do evento."""
import re
from app import eventos, http

def evs(u):
    try:
        r = http.get(u, max_bytes=6_000_000)
        e = eventos.extract_events(eventos.page_blobs(r.text), str(r.url))
        return r.status_code, str(r.url), e
    except Exception as ex:
        return "erro", str(ex), []

base = {e["url"] for e in evs("https://www.sympla.com.br/eventos/tecnologia")[2]}
for u in ["https://www.sympla.com.br/eventos/gratis", "https://www.sympla.com.br/eventos/tecnologia/gratis",
          "https://www.sympla.com.br/eventos/gratis/tecnologia", "https://www.sympla.com.br/eventos/tecnologia?gratis=true",
          "https://www.sympla.com.br/eventos/sao-paulo-sp/tecnologia/gratis", "https://www.sympla.com.br/eventos/online/tecnologia/gratis"]:
    st, fu, e = evs(u)
    print(u, "->", st, fu, len(e), "novos vs tecnologia:", len({x["url"] for x in e} - base), [x["title"][:50] for x in e[:4]])

st, fu, free_evs = evs("https://www.sympla.com.br/eventos/gratis")
paid = list(base)[:2]
for u in [x["url"] for x in free_evs[:2]] + paid:
    print("=" * 10, u)
    t = http.get(u, max_bytes=6_000_000).text
    for w in ["Gratuito", "gratuito", "Grátis", "R\\$", "price", "preco", "valor", "ticket", "Ingresso"]:
        hits = [m.start() for m in re.finditer(w, t)]
        print(f" [{w}] {len(hits)}x")
        for h in hits[:3]:
            print("    ", repr(t[max(0, h-140):h+140]))
