/* Contador de acessos próprio (no servidor caseiro): só é incluído no site publicado quando o GitHub
   tem a variável CONTADOR_URL. Não usa cookies nem guarda dados pessoais. Conta a abertura do site e
   cada troca de aba (#/c/fiscal, #/erp...), sem o texto das buscas. Se o contador estiver fora do ar,
   nada muda no site. Quem está logado no painel de acessos (aba Acessos) não é contado. */
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

  var ultimo = null;
  var primeira = true;
  function contar() {
    var p = rota();
    if (p === ultimo || dono()) return;
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

  contar();
  window.addEventListener("hashchange", contar);
})();
