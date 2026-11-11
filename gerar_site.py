"""Coleta as fontes vencidas e gera o site estático em site/ (usado pelo GitHub Actions).

Uso:
  python gerar_site.py              coleta e gera o site
  python gerar_site.py --sem-coleta só gera o site com o que já está no banco
  python gerar_site.py --saida pasta
"""
import argparse
import json
import logging
import os
import sqlite3
import sys
from datetime import timedelta

from app import config, db, scheduler, static_site

# fontes que vencem até 10 minutos depois desta execução já entram nela (o agendamento é de hora em hora)
TOLERANCIA_MIN = 10
# não publica um site com menos notícias que isso (evita trocar o site bom por um vazio se tudo falhar)
MINIMO_NOTICIAS = int(os.environ.get("RADAR_SITE_MIN", "1"))


def sincronizar_fontes() -> None:
    """No GitHub, config/sources.json é a única forma de controlar as fontes: o campo "enabled"
    vale sempre, e fontes apagadas do arquivo deixam de ser coletadas (o histórico continua no banco)."""
    srcs = json.loads((config.CONFIG_DIR / "sources.json").read_text(encoding="utf-8"))
    ativos = {s["id"]: int(s.get("enabled", True)) for s in srcs}
    with db.WRITE_LOCK, db.session() as c:
        for sid, en in ativos.items():
            c.execute("UPDATE sources SET enabled=? WHERE id=?", (en, sid))
        marks = ",".join("?" * len(ativos)) or "''"
        c.execute(f"UPDATE sources SET enabled=0 WHERE origin='config' AND id NOT IN ({marks})", list(ativos))


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
    sincronizar_fontes()
    try:
        if not args.sem_coleta:
            ids = fontes_vencidas()
            log.info("%s fonte(s) vencida(s) para coletar", len(ids))
            if ids:
                scheduler.run_cycle("agendado (GitHub)", force=True, only=ids)
        static_site.prune()
        info = static_site.export(config.BASE_DIR / args.saida)
        log.info("Site gerado em %s: %s notícias", args.saida, info["articles"])
    finally:
        con = sqlite3.connect(config.DB_PATH)  # grava tudo no arquivo principal antes de guardar o banco
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.close()

    if info["articles"] < MINIMO_NOTICIAS:
        log.error("Só %s notícia(s) no site gerado: a publicação foi cancelada e o site atual continua no ar.",
                  info["articles"])
        sys.exit(1)


if __name__ == "__main__":
    main()
