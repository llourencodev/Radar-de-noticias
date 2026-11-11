"""Ciclo de coleta: decide quais fontes estão vencidas, coleta em paralelo, processa e grava histórico."""
import logging
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from . import config, db
from .collectors import html as html_collector
from .collectors import rss, search
from .collectors.base import FetchResult, RawItem
from .processing import classify, dedup, legal, llm, summarize
from .processing.normalize import canonical_url, clean_text, detect_lang, domain_of, norm_title, sanity_check_date
from .processing.page import fetch_page

log = logging.getLogger("radar.coleta")

COLLECTORS = {"rss": rss.fetch, "html": html_collector.fetch, "search": search.fetch}
FISCAL_CATS = {"fiscal", "reforma"}


class State:
    lock = threading.Lock()
    running = False
    run_id = None
    trigger = None
    total = 0
    done = 0
    started_monotonic = 0.0
    last_error = None
    scheduler_alive = False
    next_check = None


# ---------------------------------------------------------------- ciclo
def due_sources(force: bool, only: list[str] | None = None) -> list[dict]:
    now = db.iso(db.now_utc())
    out = []
    for s in db.list_sources():
        if not s["enabled"] and not only:
            continue
        if only and s["id"] not in only:
            continue
        if force or only or not s.get("next_run_at") or s["next_run_at"] <= now:
            out.append(s)
    return out


def run_cycle(trigger: str = "automatico", force: bool = False, only: list[str] | None = None) -> int | None:
    with State.lock:
        if State.running:
            return None
        sources = due_sources(force, only)
        if not sources:
            return None
        State.running, State.trigger, State.total, State.done = True, trigger, len(sources), 0
        State.started_monotonic = time.monotonic()
    started = db.iso(db.now_utc())
    with db.WRITE_LOCK, db.session() as c:
        run_id = c.execute("INSERT INTO collection_runs(started_at,trigger,status) VALUES(?,?,'em andamento')",
                           (started, trigger)).lastrowid
    State.run_id = run_id
    ctx = RunContext()
    ok = failed = unchanged = new_total = 0
    try:
        with ThreadPoolExecutor(max_workers=max(1, config.WORKERS)) as ex:
            for status, new in ex.map(lambda s: process_source(s, run_id, ctx), sources):
                State.done += 1
                new_total += new
                if status == "erro":
                    failed += 1
                elif status == "inalterado":
                    unchanged += 1
                else:
                    ok += 1
        if llm.enabled():
            backfill_llm(limit=max(0, config.LLM_MAX_PER_RUN - ctx.llm_used))
    except Exception as ex:  # nunca derruba o servidor
        State.last_error = f"{type(ex).__name__}: {ex}"
        log.exception("Falha no ciclo de coleta")
    finally:
        status = "ok" if failed == 0 else ("parcial" if ok + unchanged > 0 else "falhou")
        with db.WRITE_LOCK, db.session() as c:
            c.execute(
                """UPDATE collection_runs SET finished_at=?, status=?, sources_ok=?, sources_failed=?,
                   sources_unchanged=?, new_items=? WHERE id=?""",
                (db.iso(db.now_utc()), status, ok, failed, unchanged, new_total, run_id))
        with State.lock:
            State.running = False
        log.info("Coleta %s: %s fontes ok, %s inalteradas, %s com falha, %s novas", run_id, ok, unchanged, failed, new_total)
    return run_id


class RunContext:
    """Dados compartilhados entre as fontes de um mesmo ciclo (títulos recentes para duplicidade)."""

    def __init__(self):
        self.recent = db.recent_titles(days=10)
        self.lock = threading.Lock()
        self.llm_used = 0


def _next_run(source: dict, failures: int) -> str:
    interval = source.get("interval_min") or config.INTERVAL_MIN
    if failures >= 3:
        interval = min(interval * 2 ** (failures - 2), 24 * 60)
    return db.iso(db.now_utc() + timedelta(minutes=interval))


def process_source(source: dict, run_id: int, ctx: RunContext) -> tuple[str, int]:
    t0 = time.monotonic()
    started = db.iso(db.now_utc())
    new = 0
    try:
        res: FetchResult = COLLECTORS[source["type"]](source)
        if res.status == "ok":
            new = process_items(source, res.items, ctx)
    except Exception as ex:
        res = FetchResult("erro", error=f"{type(ex).__name__}: {ex}"[:300])
        log.debug(traceback.format_exc())
    failures = (source.get("consecutive_failures") or 0) + 1 if res.status == "erro" else 0
    fields = dict(last_run_at=started, last_status=res.status, consecutive_failures=failures,
                  next_run_at=_next_run(source, failures), last_error=res.error if res.status == "erro" else None)
    if res.status != "erro":
        fields.update(last_success_at=started, etag=res.etag, last_modified=res.last_modified,
                      items_total=(source.get("items_total") or 0) + new)
    db.update_source_state(source["id"], **fields)
    with db.WRITE_LOCK, db.session() as c:
        c.execute(
            """INSERT INTO collection_logs(run_id,source_id,started_at,duration_ms,status,http_status,
               fetched_items,new_items,error) VALUES(?,?,?,?,?,?,?,?,?)""",
            (run_id, source["id"], started, int((time.monotonic() - t0) * 1000), res.status, res.http_status,
             len(res.items), new, res.error))
    return res.status, new


def _max_age(source: dict) -> int:
    return config.FISCAL_MAX_AGE_DAYS if source.get("category") in FISCAL_CATS else config.MAX_AGE_DAYS


def process_items(source: dict, items: list[RawItem], ctx: RunContext) -> int:
    opts = source.get("options") or {}
    cutoff = db.now_utc() - timedelta(days=int(opts.get("max_age_days", _max_age(source))))
    candidates = []
    for it in items:
        it.published = sanity_check_date(it.published)
        if it.published and it.published < cutoff:
            continue  # antiga: não é apresentada como novidade
        candidates.append(it)
    known = db.known_urls([canonical_url(i.url) for i in candidates])
    candidates = [i for i in candidates if canonical_url(i.url) not in known]

    page_budget = config.PAGE_BUDGET_PER_SOURCE if config.FETCH_PAGES else 0
    decode_budget = config.GOOGLE_DECODE_BUDGET
    new = 0
    for it in candidates:
        try:
            aggregator_url = canonical_url(it.url) if it.via_aggregator else None
            if it.via_aggregator and "news.google.com" in it.url and decode_budget > 0:
                decode_budget -= 1
                resolved = search.resolve_google_url(it.url)
                if resolved:
                    it.url, it.via_aggregator = resolved, False
                    if canonical_url(resolved) in db.known_urls([canonical_url(resolved)]):
                        _remember_alias(aggregator_url, None)
                        continue
            info = None
            needs_page = (not it.image_url or not it.published or len(it.excerpt) < 250 or source.get("official")
                          or source["type"] == "html")
            if page_budget > 0 and not it.via_aggregator and needs_page:
                page_budget -= 1
                info = fetch_page(it.url, allow_text_date=bool(opts.get("date_from_text")))
            art_id = build_and_store(source, it, info, ctx)
            if art_id:
                new += 1
                if aggregator_url:
                    _remember_alias(aggregator_url, art_id)
        except Exception as ex:  # um item problemático não derruba a fonte
            log.warning("Item ignorado em %s (%s): %s", source['id'], it.url, ex)
    return new


def _remember_alias(url: str | None, article_id: int | None) -> None:
    if not url:
        return
    with db.WRITE_LOCK, db.session() as c:
        c.execute("INSERT OR IGNORE INTO seen_urls(url,article_id,seen_at) VALUES(?,?,?)",
                  (url, article_id, db.iso(db.now_utc())))


def build_and_store(source: dict, it: RawItem, info, ctx: RunContext) -> int | None:
    title = clean_text(it.title)
    if not title or not it.url:
        return None
    image, image_origin = it.image_url, it.image_origin
    published, precision = it.published, it.date_precision
    excerpt = it.excerpt or ""
    text = excerpt
    section = ""
    if info:
        if not image and info.image:
            image, image_origin = info.image, "pagina"
        if not published and info.published:
            published, precision = info.published, info.precision
        if len(excerpt) < 120 and info.description:
            excerpt = info.description
        if len(info.text) > len(text):
            text = info.text
        section = info.section
    published = sanity_check_date(published)
    opts = source.get("options") or {}
    cutoff = db.now_utc() - timedelta(days=int(opts.get("max_age_days", _max_age(source))))
    if published and published < cutoff:
        return None

    outlet = (it.outlet or source["name"] or "").strip()
    domain = domain_of(it.url) if not it.via_aggregator else domain_of(it.outlet_url or "") or None
    if not outlet:
        return None  # sem fonte identificável: não exibir
    lang = detect_lang(title + " " + excerpt[:400])
    blob_cls = excerpt + " " + text[:1500]
    if source["type"] == "search" and not classify.classify(title, blob_cls, None, "rss", require_title=True):
        return None  # resultado de busca sem relação clara com nenhuma aba do Radar
    keyword_only = opts.get("filter") == "keywords"
    cats = classify.classify(title, blob_cls, None if keyword_only else source.get("category"), source["type"],
                             require_title=keyword_only)
    if not cats:
        return None  # fonte generalista e assunto fora das abas do Radar
    cat_slugs = [c[0] for c in cats]
    official = classify.is_official(domain or "", bool(source.get("official")) and not it.via_aggregator)
    analysis_legal = {"doc_type": None, "legal_stage": None, "stage_note": None, "legal_refs": [],
                      "legislative": False}
    if set(cat_slugs) & FISCAL_CATS:
        analysis_legal = legal.analyze(title, excerpt + " " + text[:1500], official)

    summary, points = summarize.extractive(title, text)
    if not summary:
        summary = excerpt[:500]
    blob = f"{title}\n{excerpt}\n{text[:4000]}"
    analysis = {
        "summary": summary, "summary_lang": detect_lang(summary) if summary else lang,
        "key_points": points, "impacts": summarize.impacts(blob, cat_slugs),
        "terms": summarize.find_terms(f"{title} {excerpt} {summary}"),
        "legal_refs": analysis_legal["legal_refs"], "legislative": analysis_legal["legislative"],
        "stage_note": analysis_legal["stage_note"], "provider": "regras",
    }
    status = "link via agregador" if it.via_aggregator else ("verificada" if published else "data não confirmada")
    tnorm = norm_title(title)
    art = {
        "title": title, "title_norm": tnorm, "url": it.url, "canonical_url": canonical_url(it.url),
        "source_id": source["id"], "outlet": outlet, "outlet_domain": domain,
        "image_url": image, "image_origin": image_origin if image else "nenhuma",
        "published_at": db.iso(published) if precision != "date" else (published.astimezone(db.LOCAL_TZ).date().isoformat() if published else None),
        "date_precision": precision if published else None, "date_confirmed": int(bool(published)),
        "collected_at": db.iso(db.now_utc()), "excerpt": excerpt[:1500], "lang": lang,
        "primary_category": cat_slugs[0] if cat_slugs else source.get("category"),
        "official": int(official), "doc_type": analysis_legal["doc_type"],
        "legal_stage": analysis_legal["legal_stage"],
        "nature": classify.nature(it.url, it.tags, section), "validation_status": status,
        "via_aggregator": int(it.via_aggregator),
    }

    with ctx.lock, db.WRITE_LOCK, db.session() as c:
        if c.execute("SELECT 1 FROM articles WHERE canonical_url=?", (art["canonical_url"],)).fetchone():
            return None
        d = dedup.decide(tnorm, ctx.recent)
        group_id, n_sources = None, 1
        if d["match"] and d["match"].get("group_id"):
            group_id = d["match"]["group_id"]
            g = c.execute("SELECT n_sources FROM article_groups WHERE id=?", (group_id,)).fetchone()
            same_domain = d["match"].get("outlet_domain") == domain
            n_sources = (g[0] if g else 1) + (0 if same_domain else 1)
            c.execute("""UPDATE article_groups SET n_items=n_items+1, n_sources=?,
                         last_published=max(coalesce(last_published,''), coalesce(?,'')) WHERE id=?""",
                      (n_sources, art["published_at"], group_id))
        else:
            group_id = c.execute(
                "INSERT INTO article_groups(title,first_published,last_published) VALUES(?,?,?)",
                (title, art["published_at"], art["published_at"])).lastrowid
        art["group_id"] = group_id
        art["is_duplicate"] = int(d["is_duplicate"])
        art["is_update"] = int(d["is_update"])
        if d["is_duplicate"] and official:
            # a versão oficial passa a ser a principal do grupo
            c.execute("UPDATE articles SET is_duplicate=1 WHERE group_id=? AND official=0", (group_id,))
            art["is_duplicate"] = 0
        art["relevance"] = classify.relevance(title, excerpt, official, int(source.get("priority") or 1),
                                              published, bool(analysis_legal["legislative"]), n_sources)
        if n_sources > 1:
            c.execute("UPDATE articles SET relevance=min(100, relevance+5) WHERE group_id=? AND is_duplicate=0",
                      (group_id,))
        aid = db.insert_article(c, art, analysis, cats)
        ctx.recent.append({"id": aid, "title_norm": tnorm, "group_id": group_id, "outlet_domain": domain})

    if llm.enabled() and ctx.llm_used < config.LLM_MAX_PER_RUN and not art["is_duplicate"]:
        ctx.llm_used += 1
        apply_llm(aid, title, outlet, cat_slugs, text or excerpt, analysis)
    return aid


def apply_llm(aid: int, title: str, outlet: str, cats: list[str], text: str, base: dict) -> bool:
    res = llm.analyze(title, outlet, cats, text)
    if not res:
        return False
    merged = dict(base, summary=res["summary"] or base.get("summary"), summary_lang="pt",
                  key_points=res["key_points"] or base.get("key_points", []),
                  impacts=res["impacts"], provider=llm.provider_name())
    with db.WRITE_LOCK, db.session() as c:
        db.save_analysis(c, aid, merged)
        c.execute("UPDATE articles_fts SET summary=? WHERE rowid=?", (merged["summary"], aid))
        if res.get("opinion"):
            c.execute("UPDATE articles SET nature='opiniao' WHERE id=?", (aid,))
    return True


def backfill_llm(limit: int) -> None:
    """Quando a IA é ligada depois, processa as notícias recentes que só têm análise por regras."""
    if limit <= 0:
        return
    since = db.iso(db.now_utc() - timedelta(days=7))
    with db.session() as c:
        rows = c.execute(
            """SELECT a.id, a.title, a.outlet, a.excerpt, a.primary_category, an.summary, an.terms, an.legal_refs,
               an.legislative, an.stage_note FROM articles a JOIN article_analysis an ON an.article_id=a.id
               WHERE an.provider='regras' AND a.is_duplicate=0 AND a.collected_at>=?
               ORDER BY a.relevance DESC LIMIT ?""", (since, limit)).fetchall()
    import json
    for r in rows:
        text = f"{r['excerpt'] or ''}\n{r['summary'] or ''}"
        base = {"terms": json.loads(r["terms"] or "[]"), "legal_refs": json.loads(r["legal_refs"] or "[]"),
                "legislative": r["legislative"], "stage_note": r["stage_note"], "summary": r["summary"]}
        apply_llm(r["id"], r["title"], r["outlet"], [r["primary_category"]], text, base)


# ---------------------------------------------------------------- agendador
def scheduler_loop(stop: threading.Event) -> None:
    State.scheduler_alive = True
    first = True
    while not stop.is_set():
        try:
            if config.AUTO_UPDATE and (not first or config.COLLECT_ON_START):
                run_cycle("automatico" if not first else "inicial")
        except Exception:
            log.exception("Erro no agendador")
        first = False
        State.next_check = db.iso(db.now_utc() + timedelta(seconds=60))
        stop.wait(60)
    State.scheduler_alive = False


def start_manual(force: bool = True, only: list[str] | None = None) -> bool:
    if State.running:
        return False
    threading.Thread(target=run_cycle, args=("manual", force, only), daemon=True).start()
    return True
