/* Contador de acessos próprio (no servidor caseiro): só é incluído no site publicado quando o GitHub
   tem a variável CONTADOR_URL. Não usa cookies. Registra a abertura do site e cada troca de aba
   (#/c/fiscal, #/erp...), com a busca feita, tela, idioma, de onde veio e o tempo com a página aberta;
   o servidor guarda também o IP. Detalhes em #/privacidade. Se o contador estiver fora do ar, nada
   muda no site. Quem está logado no painel de acessos (aba Acessos) não é contado. */
(function () {
  "use strict";
  var me = document.currentScript;
  var url = me && me.getAttribute("data-contador-url");
  if (!url || !/^https:\/\/[a-z0-9.-]+(:\d+)?$/i.test(url)) return;

  function dono() {
    if (/^#\/?acessos/.test(location.hash)) return true; // a tela de login/painel não entra na conta
    try { return !!localStorage.getItem("radar-contador-token"); } catch (e) { return false; }
  }
  function rota() {
    return "#/" + location.hash.replace(/^#\/?/, "").split("?")[0];
  }

  // código aleatório deste navegador (reconhece quem volta mesmo trocando de rede); não sai do Radar
  function codigoNavegador() {
    try {
      var c = localStorage.getItem("radar-visitante");
      if (!c) {
        c = (crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2, 14));
        localStorage.setItem("radar-visitante", c);
      }
      return c;
    } catch (e) { return ""; }
  }
  function enviar(obj) {
    var dados = JSON.stringify(obj);
    try {
      // texto simples: o navegador envia sem consulta prévia (CORS) e não espera resposta
      if (!(navigator.sendBeacon && navigator.sendBeacon(url + "/hit", new Blob([dados], { type: "text/plain" })))) {
        fetch(url + "/hit", { method: "POST", body: dados, keepalive: true, mode: "no-cors" }).catch(function () {});
      }
    } catch (e) { /* contador fora do ar: o site segue normal */ }
  }

  // tempo com a página visível (enviado ao trocar de aba ou sair do site)
  var pv = null, visivelDesde = 0, acumulado = 0;
  function pausar() { if (visivelDesde) { acumulado += Date.now() - visivelDesde; visivelDesde = 0; } }
  function retomar() { if (!visivelDesde && document.visibilityState === "visible") visivelDesde = Date.now(); }
  function fecharPagina() {
    pausar();
    var s = Math.round(acumulado / 1000);
    if (pv && s > 0) enviar({ t: "fim", v: pv, s: s });
    acumulado = 0;
  }

  var ultimo = null;
  var primeira = true;
  function contar() {
    var p = rota();
    var qs = new URLSearchParams(location.hash.split("?")[1] || "");
    var chave = p + "|" + (qs.get("q") || "");  // uma busca nova na mesma aba também conta
    if (chave === ultimo) return;
    fecharPagina();
    pv = null;
    if (dono()) return;
    ultimo = chave;
    var utm = new URLSearchParams(location.search);
    var dados = {
      p: p, q: qs.get("q") || "", u: location.origin + "/",
      r: primeira && document.referrer.indexOf(location.origin) !== 0 ? document.referrer : "",
      w: screen.width || 0, h: screen.height || 0, vw: innerWidth || 0, vh: innerHeight || 0,
      tz: (window.Intl && Intl.DateTimeFormat().resolvedOptions().timeZone) || "",
      lang: (navigator.languages || [navigator.language]).slice(0, 3).join(","),
      c: (navigator.connection && navigator.connection.effectiveType) || "",
      cid: codigoNavegador(),
      v: Date.now().toString(36) + Math.random().toString(36).slice(2, 10),
    };
    if (primeira) { dados.us = utm.get("utm_source") || ""; dados.um = utm.get("utm_medium") || ""; dados.uc = utm.get("utm_campaign") || ""; }
    primeira = false;
    pv = dados.v;
    visivelDesde = 0;
    retomar();
    enviar(dados);
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") fecharPagina(); else retomar();
  });
  window.addEventListener("pagehide", fecharPagina);
  contar();
  window.addEventListener("hashchange", contar);
})();
