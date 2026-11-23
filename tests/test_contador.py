"""Testes do contador de acessos próprio (contador/servidor.py) e da ligação com o site estático."""
import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = "https://llourencodev.github.io"
UA_CEL = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"
UA_PC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def carregar_servidor():
    spec = importlib.util.spec_from_file_location("contador_servidor", RAIZ / "contador" / "servidor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ContadorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.srv = carregar_servidor()
        cls.srv.ORIGENS = [ORIGEM]
        cls.srv.USUARIO = "leandro"
        cls.srv.SENHA_HASH = cls.srv.gerar_hash("senha-de-teste-123", iteracoes=1000)
        cls.srv.conectar(os.path.join(cls.tmp.name, "acessos.db"))
        cls.http = cls.srv.ThreadingHTTPServer(("127.0.0.1", 0), cls.srv.Handler)
        cls.base = f"http://127.0.0.1:{cls.http.server_address[1]}"
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.srv._db.close()
        cls.tmp.cleanup()

    def setUp(self):
        self.srv._db.execute("DELETE FROM hits")
        self.srv._vistos.clear()
        self.srv._falhas_login.clear()

    def pedir(self, caminho, corpo=None, origem=ORIGEM, ua=UA_PC, headers=None, metodo=None):
        h = {"User-Agent": ua, **(headers or {})}
        if origem:
            h["Origin"] = origem
        data = json.dumps(corpo).encode() if corpo is not None else None
        if data is not None:
            h.setdefault("Content-Type", "text/plain")
        req = urllib.request.Request(self.base + caminho, data=data, headers=h, method=metodo)
        try:
            with urllib.request.urlopen(req) as r:
                txt = r.read().decode()
                return r.status, (json.loads(txt) if txt.startswith("{") else txt), r.headers
        except urllib.error.HTTPError as e:
            txt = e.read().decode()
            return e.code, (json.loads(txt) if txt.startswith("{") else txt), e.headers

    def visita(self, pagina="#/", ref="", ua=UA_PC, ip="200.1.1.1", pais="BR"):
        return self.pedir("/hit", {"p": pagina, "u": ORIGEM + "/", "r": ref, "w": 1920, "tz": "America/Sao_Paulo"},
                          ua=ua, headers={"CF-Connecting-IP": ip, "CF-IPCountry": pais})

    def login(self, senha="senha-de-teste-123", usuario="leandro", ip="1.1.1.1"):
        return self.pedir("/login", {"usuario": usuario, "senha": senha}, headers={"CF-Connecting-IP": ip})

    def test_registra_visitas_e_mostra_totais_com_login(self):
        self.assertEqual(self.visita("#/c/fiscal?q=segredo", ref="https://www.google.com/")[0], 204)
        self.visita("#/erp")
        self.visita("#/", ref="https://web.whatsapp.com/", ua=UA_CEL, ip="200.2.2.2")
        self.visita("#/", ua="Googlebot/2.1 (+http://www.google.com/bot.html)")  # robô não conta
        cod, dados, _ = self.login()
        self.assertEqual(cod, 200)
        cod, st, _ = self.pedir("/stats?dias=7", headers={"Authorization": "Bearer " + dados["token"]})
        self.assertEqual(cod, 200)
        self.assertEqual(st["hoje"], {"dia": st["por_dia"][-1]["dia"], "visitas": 3, "visitantes": 2})
        self.assertEqual(len(st["por_dia"]), 7)
        paginas = {p["nome"]: p["n"] for p in st["paginas"]}
        self.assertEqual(paginas, {"#/c/fiscal": 1, "#/erp": 1, "#/": 1})  # sem o texto da busca
        self.assertEqual({o["nome"] for o in st["origens"]}, {"Google", "WhatsApp"})
        self.assertEqual({a["nome"]: a["n"] for a in st["aparelhos"]}, {"Computador": 1, "Celular": 1})
        self.assertEqual(st["paises"], [{"nome": "BR", "n": 2}])
        self.assertEqual(st["agora"], 2)

    def test_nao_guarda_ip(self):
        self.visita(ip="203.0.113.77")
        linhas = self.srv._db.execute("SELECT * FROM hits").fetchall()
        self.assertEqual(len(linhas), 1)
        self.assertNotIn("203.0.113.77", json.dumps(linhas))

    def test_recusa_outros_sites(self):
        self.assertEqual(self.pedir("/hit", {"p": "#/"}, origem="https://malicioso.example")[0], 403)
        self.assertEqual(self.pedir("/hit", {"p": "#/"}, origem=None)[0], 403)
        self.assertEqual(self.srv._db.execute("SELECT COUNT(*) FROM hits").fetchone()[0], 0)

    def test_cors_so_para_o_site(self):
        _, _, h = self.pedir("/saude")
        self.assertEqual(h["Access-Control-Allow-Origin"], ORIGEM)
        _, _, h = self.pedir("/saude", origem="https://malicioso.example")
        self.assertIsNone(h["Access-Control-Allow-Origin"])

    def test_painel_exige_login(self):
        self.assertEqual(self.pedir("/stats")[0], 401)
        self.assertEqual(self.pedir("/stats", headers={"Authorization": "Bearer inventado"})[0], 401)
        self.assertEqual(self.login(senha="errada-errada")[0], 401)
        self.assertEqual(self.login(usuario="outro")[0], 401)

    def test_bloqueia_apos_tentativas_erradas(self):
        for _ in range(self.srv.TENTATIVAS_MAX):
            self.login(senha="errada-errada", ip="9.9.9.9")
        cod, dados, _ = self.login(ip="9.9.9.9")  # até a senha certa é recusada por 15 min
        self.assertEqual(cod, 401)
        self.assertIn("tentativas", dados["erro"])
        self.assertEqual(self.login(ip="8.8.8.8")[0], 200)  # outro IP segue normal

    def test_sair_encerra_a_sessao(self):
        token = self.login()[1]["token"]
        auth = {"Authorization": "Bearer " + token}
        self.assertEqual(self.pedir("/stats", headers=auth)[0], 200)
        self.assertEqual(self.pedir("/logout", {}, headers=auth)[0], 204)
        self.assertEqual(self.pedir("/stats", headers=auth)[0], 401)

    def test_trocar_senha_derruba_sessoes_antigas(self):
        token = self.login()[1]["token"]
        with mock.patch.object(self.srv, "SESSOES_DESDE", 2 ** 40):
            self.assertFalse(self.srv.sessao_valida(token))
        self.assertTrue(self.srv.sessao_valida(token))

    def test_hash_de_senha(self):
        h = self.srv.gerar_hash("abc", iteracoes=1000)
        self.assertNotIn("abc", h.split(":")[2:])
        self.assertTrue(self.srv.conferir_senha("abc", h))
        self.assertFalse(self.srv.conferir_senha("abd", h))
        self.assertFalse(self.srv.conferir_senha("abc", "lixo"))

    def test_classificacoes(self):
        c = self.srv.classificar_origem
        self.assertEqual(c("https://www.google.com.br/"), ("Google", "Busca"))
        self.assertEqual(c("https://l.instagram.com/"), ("Instagram", "Rede social"))
        self.assertEqual(c("https://t.co/abc"), ("X (Twitter)", "Rede social"))
        self.assertEqual(c(""), ("Direto", "Direto"))
        self.assertEqual(c("https://blog.exemplo.com.br/post"), ("blog.exemplo.com.br", "Outros sites"))
        self.assertEqual(self.srv.classificar_ua(UA_CEL)[:2], ("Celular", "Chrome"))
        self.assertEqual(self.srv.limpar_pagina("https://x/#/c/fiscal?q=icms"), "#/c/fiscal")
        self.assertEqual(self.srv.limpar_pagina("<script>"), "#/")
        self.assertEqual(self.srv.pais_do_fuso("America/Manaus"), "BR")


class SiteComContadorTest(unittest.TestCase):
    def test_contador_url(self):
        from app import static_site
        with mock.patch.dict(os.environ, {"CONTADOR_URL": "https://Contador.Exemplo.com.br/"}):
            self.assertEqual(static_site._contador_url(), "https://contador.exemplo.com.br")
        for ruim in ("http://inseguro.com", "https://x.com/caminho", "javascript:alert(1)", "https://a\"b.com"):
            with mock.patch.dict(os.environ, {"CONTADOR_URL": ruim}):
                self.assertEqual(static_site._contador_url(), "", ruim)


if __name__ == "__main__":
    unittest.main()
