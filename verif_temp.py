"""Temporário: coleta real num banco vazio e mostra quantos eventos ficam grátis / com certificado."""
import logging
from collections import Counter
from app import eventos
logging.basicConfig(level=logging.INFO)
eventos.DETAILS_PER_RUN = 120
orig = eventos.enrich
eventos.enrich = lambda cfg, limit=0: orig(cfg, 150)
print(eventos.collect(force=True))
evs = eventos.upcoming()["events"]
print("total", len(evs), "gratis", sum(1 for e in evs if e["free"]), "pagos", sum(1 for e in evs if e["free"] is False),
      "certificado", sum(1 for e in evs if e["certificate"]))
print(Counter((e["source_id"], e["free"]) for e in evs))
for e in evs:
    if e["certificate"] or e["free"]:
        print(f"  {'G' if e['free'] else ' '}{'C' if e['certificate'] else ' '} {e['source_id']:<28} {e['title'][:80]}")
