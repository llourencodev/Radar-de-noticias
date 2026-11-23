/* Contador de acessos: só é incluído no site publicado quando o GitHub tem a variável CONTADOR_URL
   (contador próprio, no servidor caseiro) e/ou GOATCOUNTER_CODE (GoatCounter, reserva).
   Não usa cookies nem guarda dados pessoais. Conta a abertura do site e cada troca de aba
   (#/c/fiscal, #/erp...), sem o texto das buscas. Se o contador estiver fora do ar, nada muda no site.
   Quem está logado no painel de acessos (aba Acessos) não é contado. */
(function () {
  "use strict";
  var me = document.currentScript;
  var url = me && me.getAttribute("data-contador-url");
  var code = me && me.getAttribute("data-goatcounter-code");
  if (url && !/^https:\/\/[a-z0-9.-]+(:\d+)?$/i.test(url)) url = null;
  if (code && !/^[a-z0-9-]+$/.test(code)) code = null;
  if (!url && !code) return;

  function dono() {
    if (/^#\/?acessos/.test(location.hash)) return true; // a tela de login/painel não entra na conta
    try { return !!localStorage.getItem("radar-contador-token"); } catch (e) { return false; }
  }
  function rota() {
    return "#/" + location.hash.replace(/^#\/?/, "").split("?")[0];
  }

  // contador próprio
  var ultimo = null;
  var primeira = true;
  function contarProprio() {
    var p = rota();
    if (!url || p === ultimo || dono()) return;
    ultimo = p;
    var ref = primeira && document.referrer.indexOf(location.origin) !== 0 ? document.referrer : "";
    primeira = false;
    var dados = JSON.stringify({
      p: p, u: location.origin + "/", r: ref, w: screen.width || 0,
      tz: (window.Intl && Intl.DateTimeFormat().resolvedOptions().timeZone) || "",
    });
    try {
      // texto simples: o navegador envia sem consulta prévia (CORS) e não espera resposta
      if (!(navigator.sendBeacon && navigator.sendBeacon(url + "/hit", new Blob([dados], { type: "text/plain" })))) {
        fetch(url + "/hit", { method: "POST", body: dados, keepalive: true, mode: "no-cors" }).catch(function () {});
      }
    } catch (e) { /* contador fora do ar: o site segue normal */ }
  }

  // GoatCounter (reserva)
  var ultimoGc = null;
  function contarGc() {
    var p = rota();
    if (!code || p === ultimoGc || dono() || !window.goatcounter || typeof window.goatcounter.count !== "function") return;
    ultimoGc = p;
    window.goatcounter.count({ path: location.pathname + (p === "#/" ? "" : p), title: document.title });
  }
  if (code) {
    window.goatcounter = { endpoint: "https://" + code + ".goatcounter.com/count", no_onload: true };
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://gc.zgo.at/count.js";
    s.onload = contarGc;
    document.head.appendChild(s);
  }

  contarProprio();
  window.addEventListener("hashchange", function () { contarProprio(); contarGc(); });
})();
