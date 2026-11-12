"""Acesso ao SQLite: esquema, gravação e consultas (inclui busca FTS5)."""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from . import config
from .processing.normalize import fts_terms

WRITE_LOCK = threading.RLock()

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS categories (
  slug TEXT PRIMARY KEY, name TEXT NOT NULL, color TEXT, icon TEXT,
  sort INTEGER DEFAULT 0, keywords TEXT DEFAULT '[]', max_age_days INTEGER
);
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL, url TEXT, query TEXT,
  category TEXT, official INTEGER DEFAULT 0, priority INTEGER DEFAULT 1,
  interval_min INTEGER, enabled INTEGER DEFAULT 1, options TEXT DEFAULT '{}',
  origin TEXT DEFAULT 'config', notes TEXT,
  etag TEXT, last_modified TEXT, last_run_at TEXT, last_success_at TEXT,
  last_status TEXT, last_error TEXT, consecutive_failures INTEGER DEFAULT 0,
  next_run_at TEXT, items_total INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS article_groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, first_published TEXT,
  last_published TEXT, n_items INTEGER DEFAULT 1, n_sources INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL, title_norm TEXT, url TEXT NOT NULL, canonical_url TEXT UNIQUE,
  source_id TEXT REFERENCES sources(id), outlet TEXT, outlet_domain TEXT,
  image_url TEXT, image_origin TEXT DEFAULT 'nenhuma',
  published_at TEXT, date_precision TEXT, date_confirmed INTEGER DEFAULT 0,
  collected_at TEXT NOT NULL, excerpt TEXT, lang TEXT,
  primary_category TEXT, relevance REAL DEFAULT 0, official INTEGER DEFAULT 0,
  doc_type TEXT, legal_stage TEXT, nature TEXT,
  validation_status TEXT, via_aggregator INTEGER DEFAULT 0,
  group_id INTEGER REFERENCES article_groups(id), is_duplicate INTEGER DEFAULT 0,
  is_update INTEGER DEFAULT 0,
  erp_impact INTEGER DEFAULT 0, erp_docs TEXT DEFAULT '[]', erp_reason TEXT
);
CREATE INDEX IF NOT EXISTS ix_articles_pub ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS ix_articles_cat ON articles(primary_category);
CREATE INDEX IF NOT EXISTS ix_articles_group ON articles(group_id);
CREATE TABLE IF NOT EXISTS article_categories (
  article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE, category TEXT,
  origin TEXT, confidence REAL, PRIMARY KEY (article_id, category)
);
CREATE INDEX IF NOT EXISTS ix_ac_cat ON article_categories(category);
CREATE TABLE IF NOT EXISTS article_analysis (
  article_id INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
  summary TEXT, summary_lang TEXT, key_points TEXT DEFAULT '[]', impacts TEXT DEFAULT '[]',
  terms TEXT DEFAULT '[]', legal_refs TEXT DEFAULT '[]', legislative INTEGER DEFAULT 0,
  stage_note TEXT, provider TEXT, generated_at TEXT
);
CREATE TABLE IF NOT EXISTS collection_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, finished_at TEXT, trigger TEXT,
  status TEXT, sources_ok INTEGER DEFAULT 0, sources_failed INTEGER DEFAULT 0,
  sources_unchanged INTEGER DEFAULT 0, new_items INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS collection_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER REFERENCES collection_runs(id),
  source_id TEXT, started_at TEXT, duration_ms INTEGER, status TEXT, http_status INTEGER,
  fetched_items INTEGER DEFAULT 0, new_items INTEGER DEFAULT 0, error TEXT
);
CREATE INDEX IF NOT EXISTS ix_logs_run ON collection_logs(run_id);
CREATE TABLE IF NOT EXISTS seen_urls (
  url TEXT PRIMARY KEY, article_id INTEGER, seen_at TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
  title, excerpt, summary, outlet,
  tokenize = "unicode61 remove_diacritics 2 tokenchars '#+'"
);
"""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@contextmanager
def session():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with WRITE_LOCK, session() as c:
        c.executescript(SCHEMA)
        _migrate(c)
    seed_config()
    with WRITE_LOCK, session() as c:
        _fix_commit_excerpts(c)


def _migrate(c: sqlite3.Connection) -> None:
    """Bancos criados antes da marcação "Notas técnicas / ERP" ganham as colunas novas, e as notícias
    já salvas são reavaliadas sempre que as regras mudam (versão guardada em PRAGMA user_version)."""
    from .processing import erp
    cols = {r[1] for r in c.execute("PRAGMA table_info(articles)")}
    for col, ddl in (("erp_impact", "INTEGER DEFAULT 0"), ("erp_docs", "TEXT DEFAULT '[]'"), ("erp_reason", "TEXT")):
        if col not in cols:
            c.execute(f"ALTER TABLE articles ADD COLUMN {col} {ddl}")
    c.execute("CREATE INDEX IF NOT EXISTS ix_articles_erp ON articles(erp_impact)")
    if c.execute("PRAGMA user_version").fetchone()[0] >= erp.RULES_VERSION:
        return
    rows = c.execute(
        """SELECT a.id, a.title, a.excerpt, an.summary, s.options FROM articles a
           LEFT JOIN article_analysis an ON an.article_id=a.id
           LEFT JOIN sources s ON s.id=a.source_id""").fetchall()
    for r in rows:
        try:
            flag = json.loads(r[4] or "{}").get("erp_flag", True)
        except ValueError:
            flag = True
        e = erp.analyze(r[1], f"{r[2] or ''} {r[3] or ''}") if flag else {"erp_impact": False, "erp_docs": [], "erp_reason": None}
        c.execute("UPDATE articles SET erp_impact=?, erp_docs=?, erp_reason=? WHERE id=?",
                  (int(e["erp_impact"]), json.dumps(e["erp_docs"], ensure_ascii=False), e["erp_reason"], r[0]))
    c.execute(f"PRAGMA user_version={int(erp.RULES_VERSION)}")


def seed_config() -> None:
    """Carrega categorias e fontes dos arquivos JSON (novas entram, existentes são atualizadas)."""
    cats = json.loads((config.CONFIG_DIR / "categories.json").read_text(encoding="utf-8"))
    srcs = json.loads((config.CONFIG_DIR / "sources.json").read_text(encoding="utf-8"))
    with WRITE_LOCK, session() as c:
        for i, cat in enumerate(cats):
            c.execute(
                """INSERT INTO categories(slug,name,color,icon,sort,keywords,max_age_days)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(slug) DO UPDATE SET name=excluded.name, color=excluded.color,
                   icon=excluded.icon, sort=excluded.sort, keywords=excluded.keywords,
                   max_age_days=excluded.max_age_days""",
                (cat["slug"], cat["name"], cat.get("color"), cat.get("icon"), i,
                 json.dumps(cat.get("keywords", []), ensure_ascii=False), cat.get("max_age_days")),
            )
        for s in srcs:
            c.execute(
                """INSERT INTO sources(id,name,type,url,query,category,official,priority,interval_min,
                   enabled,options,origin,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,'config',?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, type=excluded.type, url=excluded.url,
                   query=excluded.query, category=excluded.category, official=excluded.official,
                   priority=excluded.priority, interval_min=excluded.interval_min,
                   options=excluded.options, notes=excluded.notes""",
                (s["id"], s["name"], s["type"], s.get("url"), s.get("query"), s.get("category"),
                 int(s.get("official", False)), s.get("priority", 1), s.get("interval_min"),
                 int(s.get("enabled", True)), json.dumps(s.get("options", {}), ensure_ascii=False),
                 s.get("notes")),
            )


def _fix_commit_excerpts(c: sqlite3.Connection) -> None:
    """Itens de feeds de commits salvos antes do resumo curto repetiam a mensagem do título no card."""
    from .collectors.rss import commit_excerpt
    srcs = [r[0] for r in c.execute("SELECT id, options FROM sources")
            if '"commits": true' in (r[1] or "")]
    if not srcs:
        return
    marks = ",".join("?" * len(srcs))
    rows = c.execute(
        f"""SELECT id, url, excerpt FROM articles WHERE source_id IN ({marks})
            AND excerpt NOT LIKE 'Revisão %' AND excerpt NOT LIKE 'Alteração no repositório%'""", srcs).fetchall()
    for aid, url, excerpt in rows:
        new = commit_excerpt(excerpt or "", url)
        c.execute("UPDATE articles SET excerpt=? WHERE id=?", (new, aid))
        c.execute("UPDATE article_analysis SET summary=?, key_points='[]' WHERE article_id=?", (new, aid))
        c.execute("UPDATE articles_fts SET excerpt=?, summary=? WHERE rowid=?", (new, new, aid))


# ---------------------------------------------------------------- fontes
def list_sources(conn=None) -> list[dict]:
    with session() as c:
        rows = c.execute("SELECT * FROM sources ORDER BY category, priority DESC, name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["options"] = json.loads(d.get("options") or "{}")
        out.append(d)
    return out


def get_source(source_id: str) -> dict | None:
    with session() as c:
        r = c.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["options"] = json.loads(d.get("options") or "{}")
    return d


def update_source_state(source_id: str, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with WRITE_LOCK, session() as c:
        c.execute(f"UPDATE sources SET {cols} WHERE id=?", (*fields.values(), source_id))


def add_source(s: dict) -> None:
    with WRITE_LOCK, session() as c:
        c.execute(
            """INSERT INTO sources(id,name,type,url,query,category,official,priority,interval_min,enabled,options,origin)
               VALUES(?,?,?,?,?,?,?,?,?,1,?,'ui')""",
            (s["id"], s["name"], s["type"], s.get("url"), s.get("query"), s.get("category"),
             int(s.get("official", False)), s.get("priority", 1), s.get("interval_min"),
             json.dumps(s.get("options", {}), ensure_ascii=False)),
        )


# ---------------------------------------------------------------- artigos
def known_urls(urls: list[str]) -> set[str]:
    if not urls:
        return set()
    with session() as c:
        found = set()
        for i in range(0, len(urls), 500):
            chunk = urls[i:i + 500]
            marks = ','.join('?' * len(chunk))
            found.update(r[0] for r in c.execute(
                f"SELECT canonical_url FROM articles WHERE canonical_url IN ({marks})", chunk))
            found.update(r[0] for r in c.execute(f"SELECT url FROM seen_urls WHERE url IN ({marks})", chunk))
    return found


def recent_titles(days: int = 10) -> list[dict]:
    since = iso(now_utc() - timedelta(days=days))
    with session() as c:
        rows = c.execute(
            """SELECT id, title_norm, group_id, published_at, source_id, outlet_domain
               FROM articles WHERE collected_at >= ? OR published_at >= ?""",
            (since, since),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_article(c: sqlite3.Connection, art: dict, analysis: dict, categories: list[tuple]) -> int:
    cols = [
        "title", "title_norm", "url", "canonical_url", "source_id", "outlet", "outlet_domain",
        "image_url", "image_origin", "published_at", "date_precision", "date_confirmed",
        "collected_at", "excerpt", "lang", "primary_category", "relevance", "official", "doc_type",
        "legal_stage", "nature", "validation_status", "via_aggregator", "group_id", "is_duplicate",
        "is_update", "erp_impact", "erp_docs", "erp_reason",
    ]
    cur = c.execute(
        f"INSERT INTO articles({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
        [art.get(k) for k in cols],
    )
    aid = cur.lastrowid
    for cat, origin, conf in categories:
        c.execute(
            "INSERT OR IGNORE INTO article_categories(article_id,category,origin,confidence) VALUES(?,?,?,?)",
            (aid, cat, origin, conf),
        )
    save_analysis(c, aid, analysis)
    c.execute(
        "INSERT INTO articles_fts(rowid,title,excerpt,summary,outlet) VALUES(?,?,?,?,?)",
        (aid, art["title"], art.get("excerpt") or "", analysis.get("summary") or "", art.get("outlet") or ""),
    )
    return aid


def save_analysis(c: sqlite3.Connection, aid: int, a: dict) -> None:
    c.execute(
        """INSERT INTO article_analysis(article_id,summary,summary_lang,key_points,impacts,terms,legal_refs,
           legislative,stage_note,provider,generated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(article_id) DO UPDATE SET summary=excluded.summary, summary_lang=excluded.summary_lang,
           key_points=excluded.key_points, impacts=excluded.impacts, terms=excluded.terms,
           legal_refs=excluded.legal_refs, legislative=excluded.legislative, stage_note=excluded.stage_note,
           provider=excluded.provider, generated_at=excluded.generated_at""",
        (aid, a.get("summary"), a.get("summary_lang"), json.dumps(a.get("key_points", []), ensure_ascii=False),
         json.dumps(a.get("impacts", []), ensure_ascii=False), json.dumps(a.get("terms", []), ensure_ascii=False),
         json.dumps(a.get("legal_refs", []), ensure_ascii=False), int(a.get("legislative", 0)),
         a.get("stage_note"), a.get("provider", "regras"), iso(now_utc())),
    )


ARTICLE_SELECT = """
SELECT a.*, s.name AS source_name, s.type AS source_type,
       an.summary, an.summary_lang, an.key_points, an.impacts, an.terms, an.legal_refs,
       an.legislative, an.stage_note, an.provider,
       (SELECT group_concat(category) FROM article_categories ac WHERE ac.article_id=a.id) AS categories,
       g.n_sources AS group_sources, g.n_items AS group_items
FROM articles a
LEFT JOIN sources s ON s.id = a.source_id
LEFT JOIN article_analysis an ON an.article_id = a.id
LEFT JOIN article_groups g ON g.id = a.group_id
"""


def _row_to_article(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("key_points", "impacts", "terms", "legal_refs", "erp_docs"):
        try:
            d[k] = json.loads(d.get(k) or "[]")
        except ValueError:
            d[k] = []
    d["categories"] = (d.get("categories") or "").split(",") if d.get("categories") else []
    d.pop("title_norm", None)
    return d


def search_articles(q: str = "", category: str | None = None, source: str | None = None,
                    date_from: str | None = None, date_to: str | None = None,
                    min_relevance: float | None = None, official: bool | None = None,
                    doc_type: str | None = None, legal_stage: str | None = None,
                    sort: str = "auto", limit: int = 30, offset: int = 0,
                    include_duplicates: bool = False, erp: bool | None = None,
                    erp_doc: str | None = None) -> dict:
    where, params = ["1=1"], []
    if not include_duplicates:
        where.append("a.is_duplicate=0")
    if category and category != "todas":
        where.append("a.id IN (SELECT article_id FROM article_categories WHERE category=?)")
        params.append(category)
    if source:
        where.append("(a.source_id=? OR a.outlet LIKE ?)")
        params += [source, f"%{source}%"]
    if date_from:
        where.append("a.published_at >= ?")
        params.append(date_from)
    if date_to:
        where.append("a.published_at <= ?")
        params.append(date_to + "T23:59:59Z" if len(date_to) == 10 else date_to)
    if min_relevance is not None:
        where.append("a.relevance >= ?")
        params.append(min_relevance)
    if official is not None:
        where.append("a.official=?")
        params.append(int(official))
    if doc_type:
        where.append("a.doc_type=?")
        params.append(doc_type)
    if legal_stage:
        where.append("a.legal_stage=?")
        params.append(legal_stage)
    if erp is not None:
        where.append("a.erp_impact=?")
        params.append(int(erp))
    if erp_doc:
        where.append("a.erp_docs LIKE ?")
        params.append('%' + json.dumps(erp_doc, ensure_ascii=False) + '%')

    order = "a.published_at IS NULL, a.published_at DESC, a.id DESC"
    if sort == "relevance" and not q.strip():
        order = "a.relevance DESC, a.published_at DESC"

    with session() as c:
        rank_join = ""
        if q.strip():
            match = _best_match(c, fts_terms(q), where, params)
            if not match:
                return {"total": 0, "items": []}
            rank_join = "JOIN (SELECT rowid AS rid, bm25(articles_fts, 10.0, 3.0, 3.0, 1.0) AS rank FROM articles_fts WHERE articles_fts MATCH ?) f ON f.rid = a.id"
            params = [match] + params
            if sort in ("relevance", "match", "auto"):
                order = "f.rank ASC, a.published_at DESC"
        total = c.execute(
            f"SELECT count(*) FROM articles a {rank_join} WHERE {' AND '.join(where)}", params
        ).fetchone()[0]
        sql = ARTICLE_SELECT.replace("FROM articles a", f"FROM articles a {rank_join}") + \
            f" WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?"
        rows = c.execute(sql, (*params, limit, offset)).fetchall()
    return {"total": total, "items": [_row_to_article(r) for r in rows]}


_TOPIC_TERMS: set[str] | None = None


def topic_terms() -> set[str]:
    """Termos de assunto (palavras-chave das abas e glossário), em formato FTS. São os últimos a sair da busca."""
    global _TOPIC_TERMS
    if _TOPIC_TERMS is None:
        words = []
        try:
            for cat in json.loads((config.CONFIG_DIR / "categories.json").read_text(encoding="utf-8")):
                for kw in cat.get("keywords", []):
                    words.append((kw[0] if isinstance(kw, list) else kw).lstrip("="))
            for g in json.loads((config.CONFIG_DIR / "glossary.json").read_text(encoding="utf-8")):
                words += [g["term"], *g.get("aliases", [])]
        except (OSError, ValueError, KeyError):
            pass
        _TOPIC_TERMS = {t for w in words for t in fts_terms(w)}
    return _TOPIC_TERMS


def _best_match(c, terms: list[str], where: list[str], params: list) -> str | None:
    """Busca com todos os termos; se nada for encontrado, retira um a um os termos menos importantes:
    primeiro as palavras comuns, por último os assuntos (ICMS, NF-e, C#...). Ex.: "Alterações no ICMS
    de Minas Gerais" acaba em ICMS + Minas Gerais ou só ICMS, nunca em "Minas Gerais" sem ICMS."""
    def count(expr):
        return c.execute(
            f"SELECT count(*) FROM articles a WHERE {' AND '.join(where)} AND a.id IN "
            f"(SELECT rowid FROM articles_fts WHERE articles_fts MATCH ?)", (*params, expr)).fetchone()[0]
    topics = topic_terms()
    terms = list(terms)
    while terms:
        expr = " AND ".join(terms)
        if count(expr) > 0:
            return expr
        if len(terms) == 1:
            return None
        freq = {t: c.execute("SELECT count(*) FROM articles_fts WHERE articles_fts MATCH ?", (t,)).fetchone()[0]
                for t in terms}
        terms.remove(max(terms, key=lambda t: (t not in topics, freq[t])))
    return None


def get_article(aid: int) -> dict | None:
    with session() as c:
        r = c.execute(ARTICLE_SELECT + " WHERE a.id=?", (aid,)).fetchone()
        if not r:
            return None
        art = _row_to_article(r)
        related = []
        if art.get("group_id"):
            rows = c.execute(
                """SELECT a.id, a.title, a.url, a.outlet, a.published_at, a.date_precision, a.is_update,
                   a.is_duplicate FROM articles a WHERE a.group_id=? AND a.id<>?
                   ORDER BY a.published_at DESC""", (art["group_id"], aid)
            ).fetchall()
            related = [dict(x) for x in rows]
        art["related"] = related
    return art


def dashboard() -> dict:
    today_start = now_utc().astimezone(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    with session() as c:
        total = c.execute("SELECT count(*) FROM articles WHERE is_duplicate=0").fetchone()[0]
        today = c.execute(
            """SELECT count(*) FROM articles WHERE is_duplicate=0 AND date_confirmed=1
               AND (published_at >= ? OR published_at = ?)""",
            (iso(today_start), today_start.date().isoformat()),
        ).fetchone()[0]
        by_cat = {r[0]: r[1] for r in c.execute(
            """SELECT ac.category, count(*) FROM article_categories ac JOIN articles a ON a.id=ac.article_id
               WHERE a.is_duplicate=0 GROUP BY ac.category""")}
        sources_total = c.execute("SELECT count(*) FROM sources WHERE enabled=1").fetchone()[0]
        sources_failing = c.execute(
            "SELECT count(*) FROM sources WHERE enabled=1 AND consecutive_failures>0").fetchone()[0]
    since = iso(now_utc() - timedelta(days=3))
    week = iso(now_utc() - timedelta(days=7))
    return {
        "total": total,
        "today": today,
        "by_category": by_cat,
        "sources_total": sources_total,
        "sources_failing": sources_failing,
        "top": search_articles(date_from=since, sort="relevance", limit=6)["items"],
        "official": search_articles(official=True, date_from=week, sort="recent", limit=6)["items"],
        "erp": search_articles(erp=True, sort="recent", limit=6)["items"],
        "erp_total": search_articles(erp=True, limit=1)["total"],
        "fiscal": _latest_multi(["fiscal", "reforma"], 6),
        "ia": search_articles(category="ia", limit=6)["items"],
        "programacao": search_articles(category="programacao", limit=6)["items"],
    }


def _latest_multi(cats: list[str], limit: int) -> list[dict]:
    with session() as c:
        rows = c.execute(
            ARTICLE_SELECT + f""" WHERE a.is_duplicate=0 AND a.id IN (SELECT article_id FROM article_categories
            WHERE category IN ({','.join('?' * len(cats))}))
            ORDER BY a.published_at IS NULL, a.published_at DESC LIMIT ?""", (*cats, limit)
        ).fetchall()
    return [_row_to_article(r) for r in rows]


def categories() -> list[dict]:
    with session() as c:
        rows = c.execute("SELECT slug,name,color,icon FROM categories ORDER BY sort").fetchall()
    return [dict(r) for r in rows]


def runs(limit: int = 50) -> list[dict]:
    with session() as c:
        rows = c.execute("SELECT * FROM collection_runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def run_logs(run_id: int) -> list[dict]:
    with session() as c:
        rows = c.execute(
            """SELECT l.*, s.name AS source_name FROM collection_logs l LEFT JOIN sources s ON s.id=l.source_id
               WHERE run_id=? ORDER BY l.status, s.name""", (run_id,)).fetchall()
    return [dict(r) for r in rows]


def outlets() -> list[dict]:
    with session() as c:
        rows = c.execute(
            """SELECT outlet, count(*) n FROM articles WHERE is_duplicate=0 AND outlet IS NOT NULL
               GROUP BY outlet ORDER BY n DESC LIMIT 300""").fetchall()
    return [dict(r) for r in rows]


try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("America/Sao_Paulo")
except Exception:  # Windows sem tzdata: usa UTC-3 fixo
    LOCAL_TZ = timezone(timedelta(hours=-3))
