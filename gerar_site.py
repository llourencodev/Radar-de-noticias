"""Coleta as fontes vencidas e gera o site estático em site/ (usado pelo GitHub Actions).

Uso:
  python gerar_site.py              coleta e gera o site
  python gerar_site.py --sem-coleta só gera o site com o que já está no banco
  python gerar_site.py --saida pasta
"""
import argparse
import logging
import sqlite3
from datetime import timedelta

from app import config, db, scheduler, static_site

# fontes que vencem até 10 minutos depois desta execução já entram nela (o agendamento é de hora em hora)
TOLERANCIA_MIN = 10


def fontes_vencidas() -> list[str]:
    limite = db.iso(db.now_utc() + timedelta(minutes=TOLERANCIA_MIN))
    return [s["id"] for s in db.list_sources()
            if s["enabled"] and (not s.get("next_run_at") or s["next_run_at"] <= limite)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-coleta", action="store_true")
    ap.add_argument("--saida", default="site")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("radar.site")

    db.init_db()
    if not args.sem_coleta:
        ids = fontes_vencidas()
        log.info("%s fonte(s) vencida(s) para coletar", len(ids))
        if ids:
            scheduler.run_cycle("agendado (GitHub)", force=True, only=ids)
    static_site.prune()
    info = static_site.export(config.BASE_DIR / args.saida)
    log.info("Site gerado em %s: %s notícias", args.saida, info["articles"])

    con = sqlite3.connect(config.DB_PATH)  # grava tudo no arquivo principal antes de guardar o banco
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()


if __name__ == "__main__":
    main()
