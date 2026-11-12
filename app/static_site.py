"""Gera a versão estática do Radar (para o GitHub Pages): copia a interface e exporta os dados em JSON.

A busca, os filtros e o painel passam a ser calculados no navegador (web/static-api.js),
com o mesmo comportamento da API do servidor local.
"""
import json
import os
import shutil
from datetime import timedelta
from pathlib import Path

from . import config, db
from .processing import llm
from .processing.legal import STAGE_LABELS
from .processing.normalize import STOPWORDS

SITE_DAYS = int(os.environ.get("RADAR_SITE_DAYS", "90"))        # janela de notícias publicadas no site
SITE_MAX_ITEMS = int(os.environ.get("RADAR_SITE_MAX", "4000"))  # limite de notícias (sem contar duplicadas); ~2 KB cada no JSON
KEEP_DAYS = int(os.environ.get("RADAR_KEEP_DAYS", "200"))       # notícias mais antigas saem do banco

# o site só carrega os próprios arquivos; imagens das notícias podem vir de qualquer site https
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' https: data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'")

DROP = {"canonical_url", "title_norm", "image_origin", "outlet_domain", "source_type", "group_items", "lang"}


def _articles() -> list[dict]:
    since = db.iso(db.now_utc() - timedelta(days=SITE_DAYS))
    with db.session() as c:
        ids = [r[0] for r in c.execute(
            """SELECT id FROM articles WHERE is_duplicate=0 AND coalesce(published_at, collected_at) >= ?
               ORDER BY coalesce(published_at, collected_at) DESC LIMIT ?""", (since[:10], SITE_MAX_ITEMS))]
        if not ids:
            return []
        marks = ",".join("?" * len(ids))
        # duplicadas dos mesmos grupos entram para a lista "Mesma notícia e atualizações"
        rows = c.execute(
            db.ARTICLE_SELECT + f""" WHERE a.id IN ({marks}) OR (a.is_duplicate=1 AND a.group_id IN
            (SELECT group_id FROM articles WHERE id IN ({marks})))""", (*ids, *ids)).fetchall()
    out = []
    for r in rows:
        d = db._row_to_article(r)
        for k in DROP:
            d.pop(k, None)
        d["excerpt"] = (d.get("excerpt") or "")[:400]
        if not d.get("erp_impact"):  # só as marcadas levam os detalhes (deixa o JSON menor)
            for k in ("erp_impact", "erp_docs", "erp_reason"):
                d.pop(k, None)
        out.append(d)
    return out


def _status(sources: list[dict]) -> dict:
    runs = db.runs(5)
    last_done = next((r for r in runs if r["finished_at"]), None)
    enabled = [s for s in sources if s["enabled"]]
    failing = [s for s in enabled if (s.get("consecutive_failures") or 0) > 0]
    if enabled and len(failing) >= max(3, len(enabled) // 2):
        health = "falhas"
    elif failing:
        health = "parcial"
    else:
        health = "ok"
    return {
        "running": False, "progress": None, "last_run": runs[0] if runs else None, "last_finished": last_done,
        "health": health,
        "failing_sources": [{"id": s["id"], "name": s["name"], "error": s.get("last_error")} for s in failing],
        "auto_update": True, "interval_min": config.INTERVAL_MIN, "scheduler_alive": True,
        "llm": llm.provider_name(),
    }


def export(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "data").mkdir(parents=True)

    # interface: os mesmos arquivos do servidor local, com caminhos relativos e a API estática
    for f in ("app.js", "styles.css", "static-api.js"):
        shutil.copy2(config.WEB_DIR / f, out_dir / f)
    html = (config.WEB_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace('href="/static/styles.css"', 'href="styles.css"')
    html = html.replace('<script src="/static/app.js"></script>',
                        '<script src="static-api.js"></script>\n<script src="app.js"></script>')
    html = html.replace('<meta charset="utf-8">',
                        f'<meta charset="utf-8">\n  <meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
                        '  <meta name="referrer" content="strict-origin-when-cross-origin">', 1)
    if "static-api.js" not in html or "Content-Security-Policy" not in html:
        raise RuntimeError("web/index.html mudou: não foi possível adaptar a página para a versão estática")
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    sources = db.list_sources()
    generated = db.iso(db.now_utc())
    status = _status(sources)
    meta = {
        "categories": db.categories(),
        "sources": [{"id": s["id"], "name": s["name"], "category": s["category"]} for s in sources],
        "outlets": db.outlets(),
        "stages": STAGE_LABELS,
        "llm": llm.provider_name(),
        "interval_min": config.INTERVAL_MIN,
        "topic_terms": sorted(db.topic_terms()),
        "stopwords": sorted(STOPWORDS),
        "repo": os.environ.get("GITHUB_REPOSITORY", ""),
        "sources_total": sum(1 for s in sources if s["enabled"]),
        "sources_failing": sum(1 for s in sources if s["enabled"] and (s.get("consecutive_failures") or 0) > 0),
    }
    articles = _articles()
    _write(out_dir / "data" / "radar.json",
           {"generated_at": generated, "meta": meta, "status": status, "articles": articles})

    public_sources = [{k: v for k, v in s.items() if k not in ("etag", "last_modified")} for s in sources]
    runs = db.runs(50)
    for r in runs[:20]:
        r["logs"] = db.run_logs(r["id"])
    _write(out_dir / "data" / "fontes.json", {"generated_at": generated, "sources": public_sources, "runs": runs})
    _write(out_dir / "data" / "status.json", {"generated_at": generated})
    return {"articles": len(articles), "generated_at": generated}


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def prune() -> None:
    """Mantém o banco enxuto entre execuções: notícias antigas e logs antigos saem.
    Itens velhos não voltam como novidade porque a coleta já descarta o que passou da janela de recência."""
    old = db.iso(db.now_utc() - timedelta(days=KEEP_DAYS))
    old_logs = db.iso(db.now_utc() - timedelta(days=30))
    with db.WRITE_LOCK, db.session() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM articles WHERE collected_at < ?", (old,))]
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            marks = ",".join("?" * len(chunk))
            c.execute(f"DELETE FROM articles_fts WHERE rowid IN ({marks})", chunk)
            c.execute(f"DELETE FROM article_analysis WHERE article_id IN ({marks})", chunk)
            c.execute(f"DELETE FROM article_categories WHERE article_id IN ({marks})", chunk)
            c.execute(f"DELETE FROM articles WHERE id IN ({marks})", chunk)
        c.execute("DELETE FROM article_groups WHERE id NOT IN (SELECT DISTINCT group_id FROM articles WHERE group_id IS NOT NULL)")
        c.execute("DELETE FROM seen_urls WHERE seen_at < ?", (old,))
        c.execute("DELETE FROM collection_logs WHERE started_at < ?", (old_logs,))
        c.execute("DELETE FROM collection_runs WHERE started_at < ? AND id NOT IN (SELECT DISTINCT run_id FROM collection_logs)", (old_logs,))
