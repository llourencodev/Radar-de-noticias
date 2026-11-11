/* Radar Inteligente de Notícias — interface (JavaScript puro, sem build) */
(() => {
  "use strict";

  // ------------------------------------------------------------ ícones (SVG inline)
  const P = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const ICONS = {
    home: P('<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>'),
    receipt: P('<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6M9 16h3"/>'),
    scale: P('<path d="M12 3v18M5 21h14M6 7h12"/><path d="M6 7l-3 7a3 3 0 006 0zM18 7l-3 7a3 3 0 006 0z"/>'),
    sparkles: P('<path d="M12 3l1.8 4.7L18 9.5l-4.2 1.8L12 16l-1.8-4.7L6 9.5l4.2-1.8z"/><path d="M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>'),
    code: P('<path d="M8 6l-6 6 6 6M16 6l6 6-6 6M14 4l-4 16"/>'),
    cpu: P('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>'),
    briefcase: P('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2M3 13h18"/>'),
    layers: P('<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>'),
    radio: P('<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 010 8.4M7.8 16.2a6 6 0 010-8.4M19 5a10 10 0 010 14M5 19A10 10 0 015 5"/>'),
    search: P('<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>'),
    refresh: P('<path d="M20 11a8 8 0 10-2.3 5.7"/><path d="M20 4v7h-7"/>'),
    theme: P('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    menu: P('<path d="M4 6h16M4 12h16M4 18h16"/>'),
    external: P('<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/>'),
    close: P('<path d="M6 6l12 12M18 6L6 18"/>'),
  };
  const icon = (n) => `<span class="ico">${ICONS[n] || ""}</span>`;
  const hydrateIcons = (root = document) => root.querySelectorAll("[data-icon]").forEach((el) => { el.innerHTML = ICONS[el.dataset.icon] || ""; });

  // ------------------------------------------------------------ utilidades
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* sem armazenamento */ } },
  };
  const STATIC = !!window.RADAR_API; // versão publicada (GitHub Pages): dados em JSON, sem servidor
  async function api(path, opts = {}) {
    if (STATIC) return window.RADAR_API(path, opts);
    const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `Erro ${r.status}`);
    return data;
  }
  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 3500);
  }

  // datas: published_at é UTC ISO (com hora) ou AAAA-MM-DD (apenas dia, informado pela fonte)
  const fmtDT = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const fmtD = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  function pubDate(a) {
    if (!a.published_at || !a.date_confirmed) return `<span class="nodate" title="A fonte não informou a data de publicação">Data não confirmada</span>`;
    if (a.date_precision === "date" || a.published_at.length === 10) {
      const [y, m, d] = a.published_at.slice(0, 10).split("-");
      return `<time title="Data de publicação (a fonte informa apenas o dia)">${d}/${m}/${y}</time>`;
    }
    const dt = new Date(a.published_at);
    return `<time datetime="${esc(a.published_at)}" title="Data de publicação">${fmtDT.format(dt)}</time> <span>· ${rel(dt)}</span>`;
  }
  function rel(dt) {
    const s = (Date.now() - dt.getTime()) / 1000;
    if (s < 60) return "agora";
    if (s < 3600) return `há ${Math.floor(s / 60)} min`;
    if (s < 86400) return `há ${Math.floor(s / 3600)} h`;
    const d = Math.floor(s / 86400);
    return d === 1 ? "ontem" : `há ${d} dias`;
  }
  const fmtLocal = (iso) => (iso ? fmtDT.format(new Date(iso)) : "—");

  // ------------------------------------------------------------ estado
  const S = { meta: null, cats: {}, status: null, route: null };
  const STAGES = {
    nao_determinado: "Estágio não determinado", projeto_de_lei: "Projeto de lei", consulta_publica: "Consulta pública",
    norma_aprovada: "Norma aprovada", norma_publicada: "Norma publicada", norma_em_vigor: "Norma em vigor",
  };

  // ------------------------------------------------------------ componentes
  function catOf(slug) { return S.cats[slug] || { name: slug, color: "#64748b", icon: "layers" }; }

  function noImage(a, mini = false) {
    const c = catOf(a.primary_category);
    return `<div class="noimg" style="--c:${c.color}">${icon(c.icon)}${mini ? "" : `<span class="outlet">${esc(a.outlet)}</span><span class="note">Sem imagem da fonte</span>`}</div>`;
  }
  function imageBlock(a, mini = false) {
    if (!a.image_url) return noImage(a, mini);
    return `<img src="${esc(safeUrl(a.image_url))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fallback="1">`;
  }
  function badges(a, full = false) {
    const out = [];
    (a.categories.length ? a.categories : [a.primary_category]).forEach((slug, i) => {
      if (!full && i > 1) return;
      const c = catOf(slug);
      out.push(`<span class="badge cat" style="--c:${c.color}">${esc(c.name)}</span>`);
    });
    if (a.doc_type === "oficial" || (a.official && !a.doc_type)) out.push(`<span class="badge official" title="Publicado por órgão oficial ou pelo próprio fabricante">Publicação oficial</span>`);
    else if (a.doc_type === "jornalistica") out.push(`<span class="badge journal">Notícia jornalística</span>`);
    if (a.legal_stage) out.push(`<span class="badge stage ${esc(a.legal_stage)}" title="Classificação automática do estágio da norma">${esc(STAGES[a.legal_stage] || a.legal_stage)}</span>`);
    if (a.is_update) out.push(`<span class="badge update">Atualização</span>`);
    if (a.nature === "opiniao") out.push(`<span class="badge opinion">Opinião</span>`);
    if (a.via_aggregator) out.push(`<span class="badge warn" title="O endereço original não pôde ser confirmado; o link abre pelo Google Notícias">via Google Notícias</span>`);
    if (a.group_sources > 1) out.push(`<span class="badge" title="A mesma notícia foi publicada por outras fontes">${a.group_sources} fontes</span>`);
    return `<div class="badges">${out.join("")}</div>`;
  }
  function providerLabel(a) {
    if (a.provider && a.provider !== "regras") return `Resumo gerado por IA (${esc(a.provider)})`;
    return a.summary_lang === "en" ? "Trecho original (inglês)" : "Resumo automático com trechos da fonte";
  }
  function card(a) {
    const c = catOf(a.primary_category);
    return `<article class="card" style="--c:${c.color}">
      <div class="thumb">${imageBlock(a)}</div>
      <div class="card-body">
        ${badges(a)}
        <h3><a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">${esc(a.title)}</a></h3>
        <div class="meta"><span class="outlet">${esc(a.outlet)}</span>${pubDate(a)}</div>
        ${a.summary ? `<p class="summary">${esc(a.summary)}</p>` : ""}
      </div>
      <div class="card-foot">
        <button class="linkbtn" data-open="${a.id}">Detalhes e impactos</button>
        <a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">Abrir original ${icon("external")}</a>
      </div>
    </article>`;
  }
  function listItem(a) {
    return `<div class="list-item">
      <div class="mini" style="--c:${catOf(a.primary_category).color}">${imageBlock(a, true)}</div>
      <div>
        <h4><a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">${esc(a.title)}</a></h4>
        <div class="meta"><span class="outlet">${esc(a.outlet)}</span>${pubDate(a)}</div>
        <div style="margin-top:6px">${badges(a)}</div>
        <button class="linkbtn" data-open="${a.id}" style="margin-top:6px">Detalhes</button>
      </div>
    </div>`;
  }
  function fixImages(root) {
    root.querySelectorAll("img[data-fallback]").forEach((img) => {
      img.addEventListener("error", () => {
        const host = img.closest(".thumb, .mini, .hero");
        const id = img.closest("[data-aid]")?.dataset.aid;
        img.remove();
        if (host) host.insertAdjacentHTML("beforeend", `<div class="noimg" style="--c:var(--text-3)">${icon("layers")}<span class="note">Imagem da fonte indisponível</span></div>`);
      }, { once: true });
    });
  }

  // ------------------------------------------------------------ navegação
  function renderNav() {
    const counts = (S.dash && S.dash.by_category) || {};
    const items = [`<a class="nav-item" href="#/" data-route="dashboard">${icon("home")}<span>Painel</span></a>`, `<div class="nav-label">Categorias</div>`];
    S.meta.categories.forEach((c) => {
      items.push(`<a class="nav-item" href="#/c/${c.slug}" data-route="c/${c.slug}" style="--c:${c.color}">${icon(c.icon)}<span>${esc(c.name)}</span><span class="count">${counts[c.slug] ?? ""}</span></a>`);
    });
    items.push(`<a class="nav-item" href="#/todas" data-route="todas">${icon("layers")}<span>Todas as notícias</span><span class="count">${S.dash ? S.dash.total : ""}</span></a>`);
    $("#nav").innerHTML = items.join("");
    markActive();
  }
  function markActive() {
    const r = (location.hash.replace(/^#\/?/, "").split("?")[0]) || "dashboard";
    document.querySelectorAll(".nav-item").forEach((a) => a.classList.toggle("active", a.dataset.route === r));
  }
  function parseHash() {
    const h = location.hash.replace(/^#\/?/, "");
    const [path, qs] = h.split("?");
    return { path: path || "dashboard", params: new URLSearchParams(qs || "") };
  }
  async function router() {
    const { path, params } = parseHash();
    closeMenu();
    markActive();
    const view = $("#view");
    view.innerHTML = `<div class="grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>`;
    try {
      if (path === "dashboard") await viewDashboard(view);
      else if (path.startsWith("c/")) await viewList(view, path.slice(2), params);
      else if (path === "todas") await viewList(view, "todas", params);
      else if (path === "fontes") await viewSources(view);
      else await viewDashboard(view);
    } catch (e) {
      view.innerHTML = `<div class="empty">Não foi possível carregar: ${esc(e.message)}</div>`;
    }
    view.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  // ------------------------------------------------------------ painel
  async function viewDashboard(view) {
    const d = await api("/api/dashboard");
    S.dash = d; renderNav();
    const st = d.status;
    const last = st.last_finished;
    const healthTxt = { ok: "Coleta normal", parcial: "Algumas fontes com falha", falhas: "Muitas fontes com falha", parado: "Agendador parado" }[st.health];
    const section = (title, items, link, mode = "grid") => `
      <section class="section"><div class="section-head"><h2>${title}</h2>${link ? `<a href="${link}">Ver tudo →</a>` : ""}</div>
      ${items.length ? (mode === "list" ? `<div class="list">${items.map(listItem).join("")}</div>` : `<div class="grid ${mode === "lead" ? "lead" : ""}">${items.map(card).join("")}</div>`) : `<div class="empty">Nenhuma notícia ainda. A primeira coleta pode levar alguns minutos.</div>`}
      </section>`;
    view.innerHTML = `
      <div class="page-head"><div><div class="eyebrow">${new Intl.DateTimeFormat("pt-BR", { dateStyle: "full" }).format(new Date())}</div><h1>Painel de inteligência</h1>
      <p>Notícias reais coletadas de fontes oficiais, imprensa e buscadores, organizadas por assunto.</p></div></div>
      <div class="kpis">
        <div class="kpi"><div class="label">Notícias coletadas</div><div class="value">${d.total.toLocaleString("pt-BR")}</div><div class="sub">sem contar duplicadas</div></div>
        <div class="kpi"><div class="label">Publicadas hoje</div><div class="value">${d.today.toLocaleString("pt-BR")}</div><div class="sub">pela data de publicação da fonte</div></div>
        <div class="kpi"><div class="label">Última atualização</div><div class="value small">${last ? fmtLocal(last.finished_at) : "—"}</div><div class="sub">${last ? `${last.new_items} novas · a cada ${st.interval_min} min` : "aguardando a primeira coleta"}</div></div>
        <div class="kpi"><div class="label">Situação da coleta</div><div class="value small"><span class="dot ${st.running ? "running" : st.health}" style="display:inline-block;margin-right:8px"></span>${st.running ? "Coletando…" : healthTxt}</div><div class="sub">${d.sources_total} fontes ativas · ${d.sources_failing} com falha</div></div>
      </div>
      ${section("Mais relevantes", d.top, "#/todas?sort=relevance", "lead")}
      ${section("Oficiais em destaque", d.official, "#/todas?official=1")}
      <div class="cols">
        <div>${section("Últimas fiscais", d.fiscal, "#/c/fiscal", "list")}</div>
        <div>${section("Novidades de IA", d.ia, "#/c/ia", "list")}</div>
        <div>${section("Programação", d.programacao, "#/c/programacao", "list")}</div>
      </div>`;
    fixImages(view);
  }

  // ------------------------------------------------------------ listas (abas)
  const EXAMPLES = ["Nova Nota Técnica da NF-e", "Mudanças no IBS e CBS", "Atualização do C#", "Novo modelo da Anthropic", "Alterações no ICMS de Minas Gerais"];

  async function viewList(view, cat, params) {
    const isAll = cat === "todas";
    const c = isAll ? { name: "Todas as notícias", color: "#0b5cad" } : catOf(cat);
    const fiscal = cat === "fiscal" || cat === "reforma";
    const f = Object.fromEntries(params.entries());
    const q = f.q || "";
    $("#searchInput").value = q;
    const opt = (v, label, cur) => `<option value="${esc(v)}" ${String(cur ?? "") === String(v) ? "selected" : ""}>${esc(label)}</option>`;
    const outlets = S.meta.outlets.map((o) => opt(o.outlet, `${o.outlet} (${o.n})`, f.source)).join("");
    view.innerHTML = `
      <div class="page-head"><div><div class="eyebrow" style="color:${c.color}">${isAll ? "Visão geral" : "Categoria"}</div><h1>${esc(c.name)}</h1>
      ${cat === "reforma" ? "<p>Publicações oficiais têm prioridade. O estágio de cada norma é classificado de forma conservadora: uma proposta nunca aparece como norma vigente.</p>" : ""}
      ${cat === "fiscal" ? "<p>Separação entre publicação oficial e notícia jornalística, e estágio de cada norma (projeto, consulta, aprovada, publicada, em vigor).</p>" : ""}
      </div></div>
      ${isAll ? `<div class="chips">${EXAMPLES.map((e) => `<button class="chip" data-q="${esc(e)}">${esc(e)}</button>`).join("")}</div>` : ""}
      <form class="filters" id="filters">
        ${isAll ? `<select name="category" aria-label="Categoria">${opt("", "Todas as categorias", f.category)}${S.meta.categories.map((x) => opt(x.slug, x.name, f.category)).join("")}</select>` : ""}
        <select name="source" aria-label="Fonte">${opt("", "Todas as fontes", f.source)}${outlets}</select>
        <select name="period" aria-label="Período">${opt("", "Qualquer data", f.period)}${opt("1", "Hoje", f.period)}${opt("7", "Últimos 7 dias", f.period)}${opt("30", "Últimos 30 dias", f.period)}${opt("custom", "Intervalo…", f.period)}</select>
        <input type="date" name="from" value="${esc(f.from || "")}" aria-label="De" ${f.period === "custom" ? "" : "hidden"}>
        <input type="date" name="to" value="${esc(f.to || "")}" aria-label="Até" ${f.period === "custom" ? "" : "hidden"}>
        <select name="min_relevance" aria-label="Relevância">${opt("", "Qualquer relevância", f.min_relevance)}${opt("40", "Relevância média ou alta", f.min_relevance)}${opt("60", "Somente alta relevância", f.min_relevance)}</select>
        ${fiscal ? `<select name="doc_type" aria-label="Tipo">${opt("", "Oficial e jornalística", f.doc_type)}${opt("oficial", "Somente publicação oficial", f.doc_type)}${opt("jornalistica", "Somente notícia jornalística", f.doc_type)}</select>
        <select name="legal_stage" aria-label="Estágio">${opt("", "Qualquer estágio", f.legal_stage)}${Object.entries(STAGES).map(([k, v]) => opt(k, v, f.legal_stage)).join("")}</select>` : `<label class="check"><input type="checkbox" name="official" value="1" ${f.official ? "checked" : ""}> Somente oficiais</label>`}
        <span class="grow"></span>
        <select name="sort" aria-label="Ordenação">${q ? opt("auto", "Mais pertinentes à busca", f.sort || "auto") : ""}${opt("recent", "Mais recentes", f.sort)}${opt("relevance", "Mais relevantes", f.sort)}</select>
      </form>
      <p class="results-info" id="info"></p>
      <div class="grid" id="results"></div>
      <div class="more"><button class="btn" id="moreBtn" hidden>Carregar mais</button></div>`;

    const form = $("#filters");
    form.addEventListener("change", (ev) => {
      const data = new FormData(form);
      const p = new URLSearchParams();
      if (q) p.set("q", q);
      for (const [k, v] of data.entries()) if (v) p.set(k, v);
      if (ev.target.name === "period" && ev.target.value !== "custom") { p.delete("from"); p.delete("to"); }
      location.hash = `#/${isAll ? "todas" : "c/" + cat}${p.toString() ? "?" + p : ""}`;
    });
    view.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => { location.hash = `#/todas?q=${encodeURIComponent(b.dataset.q)}`; }));

    const apiParams = new URLSearchParams();
    if (q) apiParams.set("q", q);
    apiParams.set("category", isAll ? (f.category || "todas") : cat);
    ["source", "min_relevance", "doc_type", "legal_stage", "sort"].forEach((k) => f[k] && apiParams.set(k, f[k]));
    if (f.official) apiParams.set("official", "true");
    if (f.period && f.period !== "custom") {
      const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() - (Number(f.period) - 1));
      apiParams.set("from", d.toISOString());
    } else if (f.period === "custom") {
      if (f.from) apiParams.set("from", f.from);
      if (f.to) apiParams.set("to", f.to);
    }
    let offset = 0;
    const load = async () => {
      apiParams.set("offset", offset); apiParams.set("limit", 30);
      const res = await api(`/api/articles?${apiParams}`);
      const box = $("#results");
      if (!res.items.length && offset === 0) {
        box.outerHTML = `<div class="empty" id="results">Nenhuma notícia encontrada${q ? ` para “${esc(q)}”` : ""}. Tente outros termos ou amplie o período.</div>`;
      } else {
        box.insertAdjacentHTML("beforeend", res.items.map(card).join(""));
        fixImages(box);
      }
      offset += res.items.length;
      $("#info").textContent = `${res.total.toLocaleString("pt-BR")} notícia(s)${q ? ` para “${q}”` : ""} · ordenadas por ${f.sort === "relevance" ? "relevância" : f.sort === "recent" || !q ? "data de publicação" : "pertinência à busca"}`;
      $("#moreBtn").hidden = offset >= res.total;
    };
    $("#moreBtn").addEventListener("click", load);
    await load();
  }

  // ------------------------------------------------------------ detalhe
  async function openArticle(id) {
    const a = await api(`/api/articles/${id}`);
    const m = $("#modal");
    const list = (arr) => `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
    const aiTag = a.provider && a.provider !== "regras" ? `IA (${esc(a.provider)})` : "regras automáticas";
    $("#modalBody").innerHTML = `
      <div class="hero" data-aid="${a.id}"><button class="icon-btn close" id="closeModal" aria-label="Fechar">${icon("close")}</button>${imageBlock(a)}</div>
      <div class="inner">
        ${badges(a, true)}
        <h2>${esc(a.title)}</h2>
        <div class="meta"><span class="outlet">${esc(a.outlet)}</span>${pubDate(a)}<span>· coletada em ${fmtLocal(a.collected_at)}</span></div>
        ${a.stage_note ? `<div class="notice">${esc(a.stage_note)}</div>` : ""}
        ${a.legal_stage && a.legal_stage !== "norma_em_vigor" && a.legislative ? `<div class="notice">Classificação automática. Confirme a situação da norma na publicação oficial antes de aplicar.</div>` : ""}
        ${a.summary ? `<h4>Resumo <span class="tag">${providerLabel(a)}</span></h4><p>${esc(a.summary)}</p>` : ""}
        ${a.summary_lang === "en" && (!a.provider || a.provider === "regras") ? `<p class="hint">Texto da fonte em inglês. A tradução e o resumo em português ficam disponíveis ao ligar a IA (veja o arquivo .env).</p>` : ""}
        ${a.key_points.length ? `<h4>Principais pontos <span class="tag">${a.provider && a.provider !== "regras" ? "IA" : "frases da fonte"}</span></h4>${list(a.key_points)}` : ""}
        ${a.impacts.length ? `<h4>Possíveis impactos para empresas e ERP <span class="tag">interpretação · ${aiTag}</span></h4>${list(a.impacts)}` : ""}
        ${a.legal_refs.length ? `<h4>Normas citadas <span class="tag">extraídas do texto</span></h4>${list(a.legal_refs)}` : ""}
        ${a.terms.length ? `<h4>Termos técnicos</h4><dl class="terms">${a.terms.map((t) => `<dt>${esc(t.term)}</dt><dd>${esc(t.explanation)}</dd>`).join("")}</dl>` : ""}
        ${a.related.length ? `<h4>Mesma notícia e atualizações</h4><ul>${a.related.map((r) => `<li>${r.is_update ? "<strong>Atualização:</strong> " : ""}<a href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener noreferrer">${esc(r.title)}</a> — ${esc(r.outlet)}, ${r.published_at ? esc(r.published_at.length === 10 ? r.published_at.split("-").reverse().join("/") : fmtLocal(r.published_at)) : "data não confirmada"}</li>`).join("")}</ul>` : ""}
        <h4>Natureza do conteúdo</h4><p class="hint">${a.nature === "opiniao" ? "Opinião/coluna: reflete a visão do autor." : "Fato relatado pela fonte."} Resumo, pontos e impactos são interpretações automáticas e não substituem a leitura do original.</p>
        <p style="margin-top:18px"><a class="btn btn-primary" href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">Abrir publicação original ${icon("external")}</a></p>
        <p class="hint">Fonte: ${esc(a.source_name || a.outlet)} · status: ${esc(a.validation_status)}${a.via_aggregator ? " · link original não confirmado (abre pelo Google Notícias)" : ""}</p>
      </div>`;
    fixImages(m);
    $("#closeModal").addEventListener("click", () => m.close());
    m.showModal();
  }

  // ------------------------------------------------------------ fontes e coleta
  async function viewSources(view) {
    const [sources, runs] = await Promise.all([api("/api/sources"), api("/api/runs?limit=50")]);
    const typeName = { rss: "RSS", html: "Página", search: "Busca" };
    view.innerHTML = `
      <div class="page-head"><div><h1>Fontes e coleta</h1><p>${sources.filter((s) => s.enabled).length} fontes ativas. ${STATIC ? "Coleta automática a cada hora pelo GitHub Actions." : `Atualização automática a cada ${S.status?.interval_min ?? 60} minutos (configurável no arquivo .env).`}</p></div></div>
      ${STATIC ? `<div class="panel"><h3>Adicionar fonte</h3><p class="hint">Nesta versão publicada, as fontes ficam no arquivo ${S.meta.repo ? `<a href="https://github.com/${esc(S.meta.repo)}/edit/main/config/sources.json" target="_blank" rel="noopener noreferrer">config/sources.json</a>` : "config/sources.json"} do repositório no GitHub. Ao salvar uma alteração nele, uma nova coleta roda e o site é publicado de novo em alguns minutos.</p></div>` : `<div class="panel"><h3>Adicionar fonte</h3>
        <form id="addForm" class="form-grid">
          <label>Nome<input name="name" required placeholder="Ex.: SEFAZ-MG notícias"></label>
          <label>Tipo<select name="type"><option value="rss">RSS / Atom</option><option value="search">Busca (Google Notícias)</option><option value="search-bing">Busca (Bing Notícias)</option><option value="html">Página sem RSS</option></select></label>
          <label>URL ou termo de busca<input name="target" required placeholder="https://… ou ICMS Minas Gerais"></label>
          <label>Categoria<select name="category">${S.meta.categories.map((c) => `<option value="${c.slug}">${esc(c.name)}</option>`).join("")}</select></label>
          <label>Padrão dos links (somente página)<input name="link_pattern" placeholder="Ex.: /noticias/20\\d\\d/"></label>
          <label class="check" style="flex-direction:row;align-items:center;margin-top:22px"><input type="checkbox" name="official"> Fonte oficial</label>
          <div style="display:flex;align-items:flex-end"><button class="btn btn-primary" type="submit">Testar e adicionar</button></div>
        </form>
        <p class="hint">A fonte é testada antes de ser salva. Para páginas sem RSS, informe uma expressão regular que os links das publicações atendem.</p>
      </div>`}
      <h3>Fontes</h3>
      <div class="table-wrap"><table><thead><tr><th>Fonte</th><th>Tipo</th><th>Categoria</th><th>Última coleta</th><th>Status</th><th>Itens</th><th>Próxima</th>${STATIC ? "" : "<th></th>"}</tr></thead><tbody>
      ${sources.map((s) => `<tr>
        <td><strong>${esc(s.name)}</strong>${s.official ? ` <span class="badge official">oficial</span>` : ""}<div class="hint">${esc(s.url || s.query || "")}</div></td>
        <td>${typeName[s.type] || s.type}${s.type === "search" ? ` · ${esc(s.options.engine || "google")}` : ""}</td>
        <td>${esc(catOf(s.category).name)}</td>
        <td>${fmtLocal(s.last_run_at)}</td>
        <td><span class="st ${esc(s.last_status || "")}">${esc(s.last_status || "aguardando")}</span>${s.last_error ? `<div class="hint" style="color:var(--bad)">${esc(s.last_error)}</div>` : ""}${s.consecutive_failures > 1 ? `<div class="hint">${s.consecutive_failures} falhas seguidas</div>` : ""}</td>
        <td>${s.items_total || 0}</td>
        <td>${fmtLocal(s.next_run_at)}</td>
        ${STATIC ? "" : `<td style="white-space:nowrap"><button class="btn btn-sm" data-collect="${esc(s.id)}">Coletar</button> <button class="btn btn-sm" data-toggle="${esc(s.id)}" data-enabled="${s.enabled}">${s.enabled ? "Desativar" : "Ativar"}</button></td>`}
      </tr>`).join("")}
      </tbody></table></div>
      <h3 style="margin-top:24px">Histórico das últimas atualizações</h3>
      <div class="table-wrap"><table><thead><tr><th>#</th><th>Início</th><th>Fim</th><th>Origem</th><th>Status</th><th>Fontes ok</th><th>Inalteradas</th><th>Com falha</th><th>Novas</th><th></th></tr></thead><tbody>
      ${runs.map((r) => `<tr><td>${r.id}</td><td>${fmtLocal(r.started_at)}</td><td>${fmtLocal(r.finished_at)}</td><td>${esc(r.trigger)}</td><td><span class="st ${esc(r.status)}">${esc(r.status)}</span></td><td>${r.sources_ok}</td><td>${r.sources_unchanged}</td><td>${r.sources_failed}</td><td>${r.new_items}</td><td><button class="btn btn-sm" data-run="${r.id}">Detalhes</button></td></tr>`).join("") || `<tr><td colspan="10">Nenhuma coleta registrada ainda.</td></tr>`}
      </tbody></table></div>`;

    view.querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", async () => {
      await api(`/api/sources/${b.dataset.toggle}`, { method: "PATCH", body: JSON.stringify({ enabled: b.dataset.enabled !== "1" }) });
      router();
    }));
    view.querySelectorAll("[data-collect]").forEach((b) => b.addEventListener("click", async () => {
      const r = await api(`/api/refresh?source=${encodeURIComponent(b.dataset.collect)}`, { method: "POST" });
      toast(r.started ? "Coleta da fonte iniciada." : r.message); pollStatus();
    }));
    view.querySelectorAll("[data-run]").forEach((b) => b.addEventListener("click", async () => {
      const logs = await api(`/api/runs/${b.dataset.run}`);
      $("#modalBody").innerHTML = `<div class="inner" style="padding-top:20px"><button class="icon-btn close" id="closeModal" aria-label="Fechar">${icon("close")}</button><h2>Coleta #${b.dataset.run}</h2>
        <div class="table-wrap"><table><thead><tr><th>Fonte</th><th>Status</th><th>HTTP</th><th>Itens lidos</th><th>Novos</th><th>Tempo</th><th>Erro</th></tr></thead><tbody>
        ${logs.map((l) => `<tr><td>${esc(l.source_name || l.source_id)}</td><td><span class="st ${esc(l.status)}">${esc(l.status)}</span></td><td>${l.http_status ?? ""}</td><td>${l.fetched_items}</td><td>${l.new_items}</td><td>${(l.duration_ms / 1000).toFixed(1)} s</td><td class="err">${esc(l.error || "")}</td></tr>`).join("")}
        </tbody></table></div></div>`;
      $("#closeModal").addEventListener("click", () => $("#modal").close());
      $("#modal").showModal();
    }));
    $("#addForm")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(ev.target);
      let type = fd.get("type"); const target = fd.get("target").trim();
      const body = { name: fd.get("name"), category: fd.get("category"), official: fd.get("official") === "on", options: {} };
      if (type.startsWith("search")) { body.type = "search"; body.query = target; body.options.engine = type === "search-bing" ? "bing" : "google"; }
      else { body.type = type; body.url = target; }
      if (type === "html") body.options.link_pattern = fd.get("link_pattern");
      const btn = ev.target.querySelector("button[type=submit]"); btn.disabled = true; btn.textContent = "Testando…";
      try { const r = await api("/api/sources", { method: "POST", body: JSON.stringify(body) }); toast(`Fonte adicionada: ${r.items_found} itens encontrados no teste.`); await loadMeta(); router(); }
      catch (e) { toast(e.message); btn.disabled = false; btn.textContent = "Testar e adicionar"; }
    });
  }

  // ------------------------------------------------------------ status e atualização
  async function pollStatus() {
    clearTimeout(pollStatus._t);
    try {
      const st = await api("/api/status");
      const was = S.status && S.status.running;
      S.status = st;
      const dot = $("#statusDot");
      dot.className = "dot " + (st.running ? "running" : st.health);
      const last = st.last_finished;
      $("#statusText").textContent = st.running
        ? `Coletando ${st.progress ? `${st.progress.done}/${st.progress.total} fontes` : "…"}`
        : last ? `Atualizado ${fmtLocal(last.finished_at)}` : "Sem coletas ainda";
      $("#statusBox").title = st.failing_sources.length ? `Fontes com falha: ${st.failing_sources.map((s) => s.name).join(", ")}` : "Todas as fontes responderam na última coleta";
      const btn = $("#refreshBtn");
      btn.disabled = st.running; btn.classList.toggle("spin", st.running);
      if (was && !st.running) { toast(`Coleta concluída: ${last ? last.new_items : 0} notícia(s) nova(s).`); await loadMeta(); router(); }
      if (st.data_changed) { toast("Novas notícias publicadas. A página foi atualizada."); await loadMeta(); if (!$("#modal").open) router(); }
      pollStatus._t = setTimeout(pollStatus, STATIC ? 300000 : st.running ? 4000 : 60000);
    } catch {
      $("#statusDot").className = "dot falhas"; $("#statusText").textContent = STATIC ? "Sem conexão" : "Servidor indisponível";
      pollStatus._t = setTimeout(pollStatus, 15000);
    }
  }
  async function loadMeta() {
    S.meta = await api("/api/meta");
    S.cats = Object.fromEntries(S.meta.categories.map((c) => [c.slug, c]));
    renderNav();
  }

  // ------------------------------------------------------------ tema e menu
  function applyTheme(t) { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; }
  function closeMenu() { $("#sidebar").classList.remove("open"); $("#scrim").classList.remove("show"); }

  async function init() {
    hydrateIcons();
    applyTheme(store.get("radar-theme", ""));
    $("#themeBtn").addEventListener("click", () => {
      const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
      const next = dark ? "light" : "dark"; applyTheme(next); store.set("radar-theme", next);
    });
    $("#menuBtn").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#scrim").classList.add("show"); });
    $("#scrim").addEventListener("click", closeMenu);
    $("#statusBox").addEventListener("click", () => { location.hash = "#/fontes"; });
    $("#refreshBtn").addEventListener("click", async () => {
      const r = await api("/api/refresh", { method: "POST" });
      toast(r.started ? "Atualização iniciada. Só o que mudou nas fontes será baixado." : r.message);
      if (r.reloaded) { await loadMeta(); router(); }
      setTimeout(pollStatus, 800);
    });
    $("#searchForm").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const q = $("#searchInput").value.trim();
      const { path } = parseHash();
      const base = path.startsWith("c/") ? path : "todas";
      location.hash = `#/${base}${q ? "?q=" + encodeURIComponent(q) : ""}`;
    });
    document.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-open]");
      if (b) openArticle(b.dataset.open).catch((e) => toast(e.message));
    });
    $("#modal").addEventListener("click", (ev) => { if (ev.target.id === "modal") ev.target.close(); });
    window.addEventListener("hashchange", router);
    await loadMeta();
    pollStatus();
    router();
  }
  init();
})();
