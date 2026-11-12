/* Radar Inteligente de Notícias — API estática (GitHub Pages).
   Responde no navegador às mesmas rotas /api/... do servidor local, a partir de data/radar.json,
   gerado a cada coleta pelo GitHub Actions. Busca, filtros e painel funcionam sem servidor. */
(() => {
  "use strict";
  const D = { loaded: null, generated: null, meta: null, status: null, all: [], byId: new Map(), list: [], df: new Map(), fontes: null };

  // ------------------------------------------------------------ carga dos dados
  async function getJSON(path) {
    const r = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`Não foi possível ler ${path} (erro ${r.status})`);
    return r.json();
  }
  async function load() {
    const data = await getJSON("data/radar.json");
    D.generated = data.generated_at;
    D.meta = data.meta;
    D.status = data.status;
    D.all = data.articles;
    D.byId = new Map(D.all.map((a) => [a.id, a]));
    D.list = D.all.filter((a) => !a.is_duplicate);
    D.fontes = null;
    D.stop = new Set(D.meta.stopwords || []);
    D.topics = new Set(D.meta.topic_terms || []);
    indexAll();
  }
  const ready = () => (D.loaded ||= load().catch((e) => { D.loaded = null; throw e; }));

  // ------------------------------------------------------------ busca (equivalente ao FTS5 do servidor)
  const strip = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
  const tokens = (s) => strip(s).match(/[\p{L}\p{N}#+]+/gu) || [];
  const FIELDS = [["title", 10], ["excerpt", 3], ["summary", 3], ["outlet", 1]];
  let AVG = {};

  function indexAll() {
    const tot = {};
    D.all.forEach((a) => {
      a._t = {};
      FIELDS.forEach(([f]) => { a._t[f] = tokens(a[f]); tot[f] = (tot[f] || 0) + a._t[f].length; });
    });
    FIELDS.forEach(([f]) => { AVG[f] = (tot[f] || 0) / Math.max(1, D.all.length) || 1; });
    D.df = new Map();
  }

  // mesmas regras de app/processing/normalize.py (_fts_term)
  function ftsTerm(tok) {
    tok = strip(tok).replace(/^[.\-]+|[.\-]+$/g, "");
    if (!tok) return null;
    if (/[-.]/.test(tok)) {
      const parts = tok.split(/[-.]/).filter(Boolean);
      return parts.length ? { key: `"${parts.join(" ")}"`, seq: parts, prefix: false } : null;
    }
    if (D.stop.has(tok)) return null;
    if (/[#+]/.test(tok)) return { key: `"${tok}"`, seq: [tok], prefix: false };
    if (tok.length >= 6 && /^\p{L}+$/u.test(tok)) {
      const p = tok.slice(0, Math.max(4, tok.length - 3));
      return { key: `${p}*`, seq: [p], prefix: true };
    }
    if (tok.length === 1 && /^\p{L}$/u.test(tok)) return null;
    return { key: `"${tok}"`, seq: [tok], prefix: false };
  }
  function ftsTerms(q) {
    const toks = String(q).match(/[\p{L}\p{N}_][\p{L}\p{N}_#+\-.]*[\p{L}\p{N}_#+]|[\p{L}\p{N}_]/gu) || [];
    const out = [];
    toks.forEach((t) => { const ft = ftsTerm(t); if (ft && !out.some((o) => o.key === ft.key)) out.push(ft); });
    return out;
  }
  function countIn(toks, term) {
    const n = term.seq.length; let c = 0;
    for (let i = 0; i + n <= toks.length; i++) {
      let ok = true;
      for (let j = 0; j < n; j++) {
        const t = toks[i + j], s = term.seq[j];
        if (term.prefix && j === n - 1 ? !t.startsWith(s) : t !== s) { ok = false; break; }
      }
      if (ok) c++;
    }
    return c;
  }
  const matches = (a, term) => FIELDS.some(([f]) => countIn(a._t[f], term) > 0);
  function df(term) {
    if (!D.df.has(term.key)) D.df.set(term.key, D.all.reduce((n, a) => n + (matches(a, term) ? 1 : 0), 0));
    return D.df.get(term.key);
  }
  function score(a, terms) {
    const N = D.all.length; let s = 0;
    terms.forEach((t) => {
      const idf = Math.log(1 + (N - df(t) + 0.5) / (df(t) + 0.5));
      FIELDS.forEach(([f, w]) => {
        const tf = countIn(a._t[f], t);
        if (tf) s += w * idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * a._t[f].length / AVG[f]));
      });
    });
    return s;
  }
  // como db._best_match: retira primeiro as palavras comuns, por último os assuntos (ICMS, NF-e, C#...)
  function bestMatch(pool, terms) {
    terms = [...terms];
    while (terms.length) {
      const hit = pool.filter((a) => terms.every((t) => matches(a, t)));
      if (hit.length) return { hit, terms };
      if (terms.length === 1) return null;
      const weight = (t) => [D.topics.has(t.key) ? 0 : 1, df(t)];
      let worst = terms[0];
      terms.forEach((t) => { const [a1, b1] = weight(t), [a2, b2] = weight(worst); if (a1 > a2 || (a1 === a2 && b1 > b2)) worst = t; });
      terms = terms.filter((t) => t !== worst);
    }
    return null;
  }

  // ------------------------------------------------------------ consultas
  const pubDesc = (a, b) => (!a.published_at) - (!b.published_at) || (b.published_at || "").localeCompare(a.published_at || "") || b.id - a.id;
  const clean = (a) => { const { _t, _s, ...rest } = a; return rest; };

  function search(p) {
    const q = (p.q || "").trim();
    let pool = p.include_duplicates ? D.all : D.list;
    const cat = p.category;
    if (cat && cat !== "todas") pool = pool.filter((a) => a.categories.includes(cat));
    if (p.cats) pool = pool.filter((a) => a.categories.some((c) => p.cats.includes(c)));
    if (p.source) { const s = p.source.toLowerCase(); pool = pool.filter((a) => a.source_id === p.source || (a.outlet || "").toLowerCase().includes(s)); }
    if (p.from) pool = pool.filter((a) => a.published_at && a.published_at >= p.from);
    if (p.to) { const to = p.to.length === 10 ? p.to + "T23:59:59Z" : p.to; pool = pool.filter((a) => a.published_at && a.published_at <= to); }
    if (p.min_relevance != null && p.min_relevance !== "") pool = pool.filter((a) => a.relevance >= Number(p.min_relevance));
    if (p.official != null && p.official !== "") { const o = p.official === true || p.official === "true" ? 1 : 0; pool = pool.filter((a) => Number(a.official) === o); }
    if (p.doc_type) pool = pool.filter((a) => a.doc_type === p.doc_type);
    if (p.legal_stage) pool = pool.filter((a) => a.legal_stage === p.legal_stage);
    if (p.erp != null && p.erp !== "") { const e = p.erp === true || p.erp === "true" || p.erp === "1" ? 1 : 0; pool = pool.filter((a) => Number(a.erp_impact || 0) === e); }
    if (p.erp_doc) pool = pool.filter((a) => (a.erp_docs || []).includes(p.erp_doc));
    const sort = p.sort || "auto";
    let items;
    if (q) {
      const terms = ftsTerms(q);
      const m = terms.length ? bestMatch(pool, terms) : null;
      if (!m) return { total: 0, items: [] };
      items = m.hit;
      if (["relevance", "match", "auto"].includes(sort)) {
        items.forEach((a) => { a._s = score(a, m.terms); });
        items.sort((a, b) => b._s - a._s || pubDesc(a, b));
      } else items.sort(pubDesc);
    } else if (sort === "relevance") {
      items = [...pool].sort((a, b) => b.relevance - a.relevance || (b.published_at || "").localeCompare(a.published_at || ""));
    } else items = [...pool].sort(pubDesc);
    const off = Number(p.offset || 0), lim = Math.min(Number(p.limit || 30), 100);
    return { total: items.length, items: items.slice(off, off + lim).map(clean) };
  }

  function dashboard() {
    const now = new Date();
    const start = new Date(now); start.setHours(0, 0, 0, 0);
    const pad = (n) => String(n).padStart(2, "0");
    const todayDate = `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}`;
    const startIso = start.toISOString().replace(/\.\d+Z$/, "Z");
    const byCat = {};
    D.list.forEach((a) => a.categories.forEach((c) => { byCat[c] = (byCat[c] || 0) + 1; }));
    const ago = (d) => new Date(now.getTime() - d * 86400000).toISOString().replace(/\.\d+Z$/, "Z");
    return {
      total: D.list.length,
      today: D.list.filter((a) => a.date_confirmed && a.published_at && (a.published_at >= startIso || a.published_at === todayDate)).length,
      by_category: byCat,
      sources_total: D.meta.sources_total,
      sources_failing: D.meta.sources_failing,
      top: search({ from: ago(3), sort: "relevance", limit: 6 }).items,
      official: search({ official: true, from: ago(7), sort: "recent", limit: 6 }).items,
      erp: search({ erp: true, sort: "recent", limit: 6 }).items,
      erp_total: D.list.filter((a) => a.erp_impact).length,
      fiscal: search({ cats: ["fiscal", "reforma"], limit: 6 }).items,
      ia: search({ category: "ia", limit: 6 }).items,
      programacao: search({ category: "programacao", limit: 6 }).items,
      status: status(),
    };
  }
  const status = () => ({ ...D.status, static: true, generated_at: D.generated });

  function article(id) {
    const a = D.byId.get(Number(id));
    if (!a) throw new Error("Notícia não encontrada");
    const related = a.group_id ? D.all.filter((x) => x.group_id === a.group_id && x.id !== a.id).sort(pubDesc)
      .map(({ id, title, url, outlet, published_at, date_precision, is_update, is_duplicate }) => ({ id, title, url, outlet, published_at, date_precision, is_update, is_duplicate })) : [];
    return { ...clean(a), related };
  }
  async function fontes() { return (D.fontes ||= await getJSON("data/fontes.json")); }

  // verifica se o GitHub publicou uma coleta mais nova e, se sim, recarrega os dados
  async function checkNew() {
    const s = await getJSON("data/status.json");
    if (s.generated_at && s.generated_at !== D.generated) { D.loaded = null; await ready(); return true; }
    return false;
  }

  // ------------------------------------------------------------ roteador
  window.RADAR_STATIC = true;
  window.RADAR_API = async (path, opts = {}) => {
    const url = new URL(path, location.href);
    const p = Object.fromEntries(url.searchParams.entries());
    const route = url.pathname.replace(/^.*\/api\//, "");
    const method = (opts.method || "GET").toUpperCase();
    await ready();
    if (method === "POST" && route === "refresh") {
      const changed = await checkNew().catch(() => false);
      return { started: false, reloaded: changed, message: changed
        ? "Notícias atualizadas com a coleta mais recente."
        : `Você já está vendo a coleta mais recente (${new Date(D.generated).toLocaleString("pt-BR")}). A coleta roda sozinha a cada hora.` };
    }
    if (method !== "GET") throw new Error("Na versão publicada, as fontes são alteradas no arquivo config/sources.json do GitHub.");
    if (route === "meta") return { ...D.meta };
    if (route === "status") { const changed = await checkNew().catch(() => false); return { ...status(), data_changed: changed }; }
    if (route === "dashboard") return dashboard();
    if (route === "articles") {
      if (p.from && /^\d{4}-\d{2}-\d{2}T/.test(p.from)) p.from = p.from.replace(/\.\d+Z$/, "Z");
      return search(p);
    }
    let m = route.match(/^articles\/(\d+)$/);
    if (m) return article(m[1]);
    if (route === "sources") return (await fontes()).sources;
    if (route === "runs") return (await fontes()).runs.slice(0, Number(p.limit || 50));
    m = route.match(/^runs\/(\d+)$/);
    if (m) { const r = (await fontes()).runs.find((x) => x.id === Number(m[1])); return (r && r.logs) || []; }
    throw new Error("Rota não disponível na versão publicada");
  };
})();
