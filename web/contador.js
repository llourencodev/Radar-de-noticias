/* Contador de acessos (GoatCounter): só é incluído no site publicado quando a variável
   GOATCOUNTER_CODE está configurada no GitHub. Não usa cookies nem guarda dados pessoais.
   Conta a abertura do site e cada troca de aba (#/c/fiscal, #/erp...), sem o texto das buscas. */
(function () {
  "use strict";
  var me = document.currentScript;
  var code = me && me.getAttribute("data-goatcounter-code");
  if (!code || !/^[a-z0-9-]+$/.test(code)) return;

  // o painel do GoatCounter ignora os acessos do próprio dono quando ele marca "ignorar este navegador"
  window.goatcounter = { endpoint: "https://" + code + ".goatcounter.com/count", no_onload: true };

  var last = null;
  function path() {
    var route = location.hash.replace(/^#\/?/, "").split("?")[0];
    return location.pathname + (route ? "#/" + route : "");
  }
  function count() {
    var p = path();
    if (p === last || !window.goatcounter || typeof window.goatcounter.count !== "function") return;
    last = p;
    window.goatcounter.count({ path: p, title: document.title });
  }

  var s = document.createElement("script");
  s.async = true;
  s.src = "https://gc.zgo.at/count.js";
  s.onload = function () {
    count();
    window.addEventListener("hashchange", count);
  };
  document.head.appendChild(s);
})();
