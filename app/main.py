"""Servidor web do Radar Inteligente de Notícias (API + interface)."""
import logging
import re
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, db, scheduler
from .collectors import html as html_collector
from .collectors import rss, search
from .processing import llm
from .processing.legal import STAGE_LABELS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
_stop = threading.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    t = threading.Thread(target=scheduler.scheduler_loop, args=(_stop,), daemon=True, name="agendador")
    t.start()
    yield
    _stop.set()


app = FastAPI(title="Radar Inteligente de Notícias", version="1.0", lifespan=lifespan)


# ---------------------------------------------------------------- notícias
@app.get("/api/articles")
def articles(q: str = "", category: str | None = None, source: str | None = None,
             date_from: str | None = Query(None, alias="from"), date_to: str | None = Query(None, alias="to"),
             min_relevance: float | None = None, official: bool | None = None, doc_type: str | None = None,
             legal_stage: str | None = None, sort: str = "auto", limit: int = Query(30, le=100),
             offset: int = 0, include_duplicates: bool = False):
    return db.search_articles(q, category, source, date_from, date_to, min_relevance, official, doc_type,
                              legal_stage, sort, limit, offset, include_duplicates)


@app.get("/api/articles/{aid}")
def article(aid: int):
    a = db.get_article(aid)
    if not a:
        raise HTTPException(404, "Notícia não encontrada")
    return a


@app.get("/api/dashboard")
def dashboard():
    d = db.dashboard()
    d["status"] = status()
    return d


@app.get("/api/meta")
def meta():
    return {
        "categories": db.categories(),
        "sources": [{"id": s["id"], "name": s["name"], "category": s["category"]} for s in db.list_sources()],
        "outlets": db.outlets(),
        "stages": STAGE_LABELS,
        "llm": llm.provider_name(),
        "interval_min": config.INTERVAL_MIN,
    }


# ---------------------------------------------------------------- coleta
@app.get("/api/status")
def status():
    runs = db.runs(1)
    last = runs[0] if runs else None
    last_done = next((r for r in db.runs(5) if r["finished_at"]), None)
    sources = db.list_sources()
    failing = [s for s in sources if s["enabled"] and (s.get("consecutive_failures") or 0) > 0]
    enabled = [s for s in sources if s["enabled"]]
    if not scheduler.State.scheduler_alive and config.AUTO_UPDATE:
        health = "parado"
    elif enabled and len(failing) >= max(3, len(enabled) // 2):
        health = "falhas"
    elif failing:
        health = "parcial"
    else:
        health = "ok"
    return {
        "running": scheduler.State.running,
        "progress": {"done": scheduler.State.done, "total": scheduler.State.total} if scheduler.State.running else None,
        "last_run": last,
        "last_finished": last_done,
        "health": health,
        "failing_sources": [{"id": s["id"], "name": s["name"], "error": s.get("last_error")} for s in failing],
        "auto_update": config.AUTO_UPDATE,
        "interval_min": config.INTERVAL_MIN,
        "scheduler_alive": scheduler.State.scheduler_alive,
        "llm": llm.provider_name(),
    }


@app.post("/api/refresh")
def refresh(source: str | None = None):
    started = scheduler.start_manual(force=True, only=[source] if source else None)
    if not started:
        return {"started": False, "message": "Já existe uma coleta em andamento."}
    return {"started": True}


@app.get("/api/runs")
def runs(limit: int = 50):
    return db.runs(limit)


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int):
    return db.run_logs(run_id)


# ---------------------------------------------------------------- fontes
@app.get("/api/sources")
def sources():
    return db.list_sources()


class NewSource(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    type: str = Field(pattern="^(rss|html|search)$")
    url: str | None = None
    query: str | None = None
    category: str
    official: bool = False
    priority: int = 1
    interval_min: int | None = None
    options: dict = {}


@app.post("/api/sources")
def create_source(s: NewSource):
    if s.type in ("rss", "html") and not (s.url or "").startswith("http"):
        raise HTTPException(400, "Informe a URL completa (http/https).")
    if s.type == "search" and not s.query:
        raise HTTPException(400, "Informe o termo de busca.")
    sid = re.sub(r"[^a-z0-9]+", "-", s.name.lower()).strip("-")[:40] or "fonte"
    if db.get_source(sid):
        sid = f"{sid}-{len(db.list_sources())}"
    data = s.model_dump()
    data["id"] = sid
    test = {"rss": rss.fetch, "html": html_collector.fetch, "search": search.fetch}[s.type](dict(data))
    if test.status == "erro":
        raise HTTPException(400, f"A fonte não respondeu como esperado: {test.error}")
    db.add_source(data)
    scheduler.start_manual(force=True, only=[sid])
    return {"id": sid, "items_found": len(test.items)}


class SourcePatch(BaseModel):
    enabled: bool | None = None
    interval_min: int | None = None
    priority: int | None = None


@app.patch("/api/sources/{sid}")
def patch_source(sid: str, p: SourcePatch):
    if not db.get_source(sid):
        raise HTTPException(404, "Fonte não encontrada")
    fields = {k: (int(v) if isinstance(v, bool) else v) for k, v in p.model_dump().items() if v is not None}
    db.update_source_state(sid, **fields)
    return db.get_source(sid)


# ---------------------------------------------------------------- interface
app.mount("/static", StaticFiles(directory=config.WEB_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(config.WEB_DIR / "index.html")
