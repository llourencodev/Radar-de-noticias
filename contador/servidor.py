#!/usr/bin/env python3
"""Contador de acessos do Radar: um serviço pequeno, sem dependências (só a biblioteca padrão do Python).

Roda no servidor caseiro e guarda as visitas num arquivo SQLite. O site publicado (GitHub Pages)
avisa cada abertura de página; a aba "Acessos" do Radar lê os totais.

Privacidade (LGPD): não usa cookies e não guarda IP nem identificador do navegador. O visitante
é reconhecido só dentro do mesmo dia, por um código embaralhado (hash) de IP + navegador com uma
chave que é trocada todo dia e apagada em seguida; não dá para voltar ao IP nem ligar dias diferentes.

Endereços:
  POST /hit     registra uma visita (chamado pelo site; corpo JSON pequeno)
  POST /login   confere usuário e senha e devolve um código de sessão (válido por 30 dias)
  POST /logout  encerra a sessão
  GET  /stats   totais para o painel (só com sessão válida)
  GET  /saude   responde "ok" (para testar se o serviço está no ar)

Login: o usuário e a senha ficam no servidor (a senha só como hash PBKDF2). Para criar ou trocar:
  sudo python3 /opt/radar-contador/servidor.py --definir-senha

Configuração por variáveis de ambiente (veja contador/contador.env.exemplo).
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

HOST = os.environ.get("CONTADOR_HOST", "127.0.0.1")
PORT = int(os.environ.get("CONTADOR_PORTA", "8787"))
DB_PATH = os.environ.get("CONTADOR_BANCO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "acessos.db"))
# sites que podem enviar visitas e ler o painel (separados por vírgula)
ORIGENS = [o.strip().rstrip("/") for o in os.environ.get(
    "CONTADOR_ORIGENS", "https://llourencodev.github.io").split(",") if o.strip()]
USUARIO = os.environ.get("CONTADOR_USUARIO", "").strip()
SENHA_HASH = os.environ.get("CONTADOR_SENHA_HASH", "").strip()  # pbkdf2_sha256:iterações:sal:hash
SESSAO_DIAS = int(os.environ.get("CONTADOR_SESSAO_DIAS", "30"))
SESSOES_DESDE = int(os.environ.get("CONTADOR_SESSOES_DESDE", "0") or 0)  # trocar a senha derruba sessões anteriores
ENV_PATH = os.environ.get("CONTADOR_ENV", "/etc/radar-contador.env")
TENTATIVAS_MAX = 5          # tentativas de login erradas por IP...
TENTATIVAS_JANELA = 15 * 60  # ...a cada 15 minutos
DIAS_GUARDADOS = int(os.environ.get("CONTADOR_DIAS", "400"))  # visitas mais antigas são apagadas
TZ = ZoneInfo(os.environ.get("CONTADOR_FUSO", "America/Sao_Paulo"))
LIMITE_POR_HORA = 300                                          # visitas por visitante por hora (evita abuso)
MAX_CORPO = 2048

ONLINE_MIN = 5  # "agora no site" = visitas nos últimos 5 minutos

SCHEMA = """
CREATE TABLE IF NOT EXISTS hits (
  id INTEGER PRIMARY KEY,
  ts INTEGER NOT NULL,            -- segundos desde 1970 (UTC)
  dia TEXT NOT NULL,              -- AAAA-MM-DD no fuso configurado
  hora INTEGER NOT NULL,
  visitante TEXT NOT NULL,        -- hash diário (não identifica a pessoa)
  nova INTEGER NOT NULL,          -- 1 = primeira página do visitante no dia
  pagina TEXT NOT NULL,           -- aba aberta (#/c/fiscal...), sem texto de busca
  origem TEXT NOT NULL,           -- domínio de onde veio (google.com, whatsapp...)
  tipo_origem TEXT NOT NULL,      -- Busca, Rede social, Mensagens, Direto, Outros sites
  aparelho TEXT NOT NULL,         -- Computador, Celular, Tablet
  navegador TEXT NOT NULL,
  sistema TEXT NOT NULL,
  pais TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS hits_dia ON hits(dia);
CREATE INDEX IF NOT EXISTS hits_ts ON hits(ts);
CREATE TABLE IF NOT EXISTS sal (dia TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessoes (token_hash TEXT PRIMARY KEY, criada INTEGER NOT NULL, expira INTEGER NOT NULL);
"""

_lock = threading.Lock()
_db = None
_vistos = {}       # (dia, visitante) -> True, para marcar a 1ª página do dia sem consultar o banco
_contagem = {}     # (hora, visitante) -> visitas, para o limite por hora
_ultima_limpeza = ""
_falhas_login = {}  # ip -> [horários das tentativas erradas]


def conectar(path=None):
    global _db
    _db = sqlite3.connect(path or DB_PATH, check_same_thread=False, isolation_level=None)
    _db.execute("PRAGMA journal_mode=WAL")
    _db.executescript(SCHEMA)
    _vistos.clear()
    _contagem.clear()
    return _db


def agora():
    return datetime.now(TZ)


def _sal(dia):
    """Chave secreta do dia (fica só até o dia acabar)."""
    row = _db.execute("SELECT valor FROM sal WHERE dia=?", (dia,)).fetchone()
    if row:
        return row[0]
    valor = secrets.token_hex(16)
    _db.execute("INSERT OR IGNORE INTO sal(dia, valor) VALUES(?, ?)", (dia, valor))
    _db.execute("DELETE FROM sal WHERE dia <> ?", (dia,))
    return _db.execute("SELECT valor FROM sal WHERE dia=?", (dia,)).fetchone()[0]


def _limpar(dia):
    """Uma vez por dia: apaga visitas antigas e esquece os controles do dia anterior."""
    global _ultima_limpeza
    if _ultima_limpeza == dia:
        return
    _ultima_limpeza = dia
    limite = (agora() - timedelta(days=DIAS_GUARDADOS)).strftime("%Y-%m-%d")
    _db.execute("DELETE FROM hits WHERE dia < ?", (limite,))
    _db.execute("DELETE FROM sessoes WHERE expira < ?", (int(time.time()),))
    for k in [k for k in _vistos if k[0] != dia]:
        del _vistos[k]


# ------------------------------------------------------------------ classificação
BUSCAS = ("google.", "bing.com", "duckduckgo.", "yahoo.", "ecosia.", "yandex.", "search.brave", "startpage.")
SOCIAIS = {"facebook.com": "Facebook", "fb.com": "Facebook", "instagram.com": "Instagram", "t.co": "X (Twitter)",
           "twitter.com": "X (Twitter)", "x.com": "X (Twitter)", "linkedin.com": "LinkedIn", "lnkd.in": "LinkedIn",
           "reddit.com": "Reddit", "youtube.com": "YouTube", "threads.net": "Threads", "bsky.app": "Bluesky"}
MENSAGENS = {"whatsapp.com": "WhatsApp", "wa.me": "WhatsApp", "web.whatsapp.com": "WhatsApp",
             "t.me": "Telegram", "telegram.org": "Telegram", "teams.microsoft.com": "Teams",
             "slack.com": "Slack", "discord.com": "Discord", "mail.google.com": "E-mail", "outlook.live.com": "E-mail",
             "outlook.office.com": "E-mail"}

# fuso horário do navegador -> país (usado quando não há o cabeçalho de país da Cloudflare)
FUSOS_PAIS = {"Sao_Paulo": "BR", "Bahia": "BR", "Fortaleza": "BR", "Recife": "BR", "Belem": "BR", "Maceio": "BR",
              "Araguaina": "BR", "Manaus": "BR", "Cuiaba": "BR", "Campo_Grande": "BR", "Porto_Velho": "BR",
              "Boa_Vista": "BR", "Rio_Branco": "BR", "Eirunepe": "BR", "Santarem": "BR", "Noronha": "BR",
              "Lisbon": "PT", "Madeira": "PT", "Azores": "PT", "Buenos_Aires": "AR", "Montevideo": "UY",
              "Asuncion": "PY", "Santiago": "CL", "Bogota": "CO", "Lima": "PE", "Mexico_City": "MX",
              "New_York": "US", "Chicago": "US", "Denver": "US", "Los_Angeles": "US", "Phoenix": "US",
              "Toronto": "CA", "Vancouver": "CA", "London": "GB", "Madrid": "ES", "Paris": "FR", "Berlin": "DE",
              "Rome": "IT", "Amsterdam": "NL", "Dublin": "IE", "Zurich": "CH", "Luanda": "AO", "Maputo": "MZ",
              "Tokyo": "JP", "Shanghai": "CN", "Kolkata": "IN", "Sydney": "AU"}


def classificar_origem(ref, proprio_host=""):
    """Devolve (domínio, tipo) a partir do endereço de onde o visitante veio."""
    try:
        host = (urlparse(ref).hostname or "").lower() if ref else ""
    except ValueError:
        host = ""
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m.") or host.startswith("l.") or host.startswith("lm."):
        host = host.split(".", 1)[1]
    if not host or (proprio_host and host == proprio_host):
        return "Direto", "Direto"
    if host.startswith("android-app"):
        return host[:60], "Aplicativo"
    for nome, rotulo in MENSAGENS.items():
        if host == nome or host.endswith("." + nome):
            return rotulo, "Mensagens"
    for nome, rotulo in SOCIAIS.items():
        if host == nome or host.endswith("." + nome):
            return rotulo, "Rede social"
    if any(b in host for b in BUSCAS):
        return host.split(".")[0].capitalize() if "google." in host or "bing." in host or "yahoo." in host else host, "Busca"
    return host[:60], "Outros sites"


def classificar_ua(ua, tela=0):
    ua = ua or ""
    if re.search(r"iPad|Tablet|PlayBook|Silk|(Android(?!.*Mobile))", ua):
        aparelho = "Tablet"
    elif re.search(r"Mobi|iPhone|iPod|Android.*Mobile|Windows Phone", ua):
        aparelho = "Celular"
    else:
        aparelho = "Computador"
    # iPad novo se apresenta como Mac: a largura da tela desempata
    if aparelho == "Computador" and "Macintosh" in ua and 0 < tela <= 1366 and "Mobile/" in ua:
        aparelho = "Tablet"
    if "Edg/" in ua or "EdgA/" in ua or "EdgiOS" in ua:
        nav = "Edge"
    elif "OPR/" in ua or "Opera" in ua:
        nav = "Opera"
    elif "SamsungBrowser" in ua:
        nav = "Samsung Internet"
    elif "Firefox/" in ua or "FxiOS" in ua:
        nav = "Firefox"
    elif "Chrome/" in ua or "CriOS" in ua:
        nav = "Chrome"
    elif "Safari/" in ua:
        nav = "Safari"
    else:
        nav = "Outro"
    if "Windows" in ua:
        so = "Windows"
    elif "Android" in ua:
        so = "Android"
    elif re.search(r"iPhone|iPad|iPod", ua):
        so = "iOS"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        so = "macOS"
    elif "CrOS" in ua:
        so = "ChromeOS"
    elif "Linux" in ua:
        so = "Linux"
    else:
        so = "Outro"
    return aparelho, nav, so


def eh_robo(ua):
    return not ua or bool(re.search(r"bot|crawl|spider|slurp|headless|lighthouse|preview|facebookexternalhit|"
                                    r"python-|curl/|wget/|httpclient|monitor", ua, re.I))


def limpar_pagina(p):
    """Guarda só a aba (#/c/fiscal, #/eventos...), nunca o texto pesquisado."""
    p = str(p or "")
    rota = p.split("#", 1)[1] if "#" in p else ""
    rota = rota.lstrip("/").split("?")[0][:60]
    rota = re.sub(r"[^a-z0-9/_-]", "", rota.lower())
    return "#/" + rota if rota else "#/"


def pais_do_fuso(fuso):
    cidade = str(fuso or "").rsplit("/", 1)[-1]
    return FUSOS_PAIS.get(cidade, "")


# ------------------------------------------------------------------ registro e totais
def registrar(dados, ip, ua, pais_cf=""):
    """Grava uma visita. Devolve False quando ela é ignorada (robô ou excesso)."""
    if eh_robo(ua):
        return False
    momento = agora()
    dia = momento.strftime("%Y-%m-%d")
    with _lock:
        _limpar(dia)
        visitante = hmac.new(_sal(dia).encode(), f"{ip}|{ua}".encode(), hashlib.sha256).hexdigest()[:16]
        chave_hora = (momento.strftime("%Y-%m-%d %H"), visitante)
        if len(_contagem) > 50000:
            _contagem.clear()
        _contagem[chave_hora] = _contagem.get(chave_hora, 0) + 1
        if _contagem[chave_hora] > LIMITE_POR_HORA:
            return False
        nova = 0
        if (dia, visitante) not in _vistos:
            nova = 0 if _db.execute("SELECT 1 FROM hits WHERE dia=? AND visitante=? LIMIT 1",
                                    (dia, visitante)).fetchone() else 1
            _vistos[(dia, visitante)] = True
        try:
            tela = int(dados.get("w") or 0)
        except (TypeError, ValueError):
            tela = 0
        proprio = urlparse(str(dados.get("u") or "")).hostname or ""
        origem, tipo = classificar_origem(str(dados.get("r") or "")[:500], proprio.lower())
        aparelho, nav, so = classificar_ua(ua, tela)
        pais = (pais_cf or "").upper()
        if not re.fullmatch(r"[A-Z]{2}", pais) or pais in ("XX", "T1"):
            pais = pais_do_fuso(dados.get("tz")) or "??"
        _db.execute(
            "INSERT INTO hits(ts, dia, hora, visitante, nova, pagina, origem, tipo_origem, aparelho, navegador, sistema, pais)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (int(time.time()), dia, momento.hour, visitante, nova, limpar_pagina(dados.get("p")),
             origem, tipo, aparelho, nav, so, pais))
    return True


def _top(campo, desde, limite=10, contar="COUNT(*)"):
    rows = _db.execute(f"SELECT {campo}, {contar} AS n FROM hits WHERE dia >= ? GROUP BY {campo} HAVING n > 0 "
                       f"ORDER BY n DESC, {campo} LIMIT ?", (desde, limite)).fetchall()
    return [{"nome": r[0], "n": r[1]} for r in rows]


def totais(dias=30):
    dias = max(1, min(int(dias), DIAS_GUARDADOS))
    hoje = agora().date()
    desde = (hoje - timedelta(days=dias - 1)).isoformat()
    ontem = (hoje - timedelta(days=1)).isoformat()
    with _lock:
        q = _db.execute
        por_dia = {r[0]: {"dia": r[0], "visitas": r[1], "visitantes": r[2]} for r in q(
            "SELECT dia, COUNT(*), COUNT(DISTINCT visitante) FROM hits WHERE dia >= ? GROUP BY dia", (desde,))}
        serie = []
        for i in range(dias):
            d = (hoje - timedelta(days=dias - 1 - i)).isoformat()
            serie.append(por_dia.get(d, {"dia": d, "visitas": 0, "visitantes": 0}))
        horas = [0] * 24
        for h, n in q("SELECT hora, COUNT(*) FROM hits WHERE dia = ? GROUP BY hora", (hoje.isoformat(),)):
            horas[h] = n
        online = q("SELECT COUNT(DISTINCT visitante) FROM hits WHERE ts >= ?",
                   (int(time.time()) - ONLINE_MIN * 60,)).fetchone()[0]
        total_desde = q("SELECT COUNT(*), COALESCE(SUM(nova), 0) FROM hits WHERE dia >= ?", (desde,)).fetchone()
        primeira = q("SELECT MIN(dia) FROM hits").fetchone()[0]
        visitantes = "SUM(nova)"  # visitantes-dia: cada pessoa conta uma vez por dia
        return {
            "gerado_em": agora().isoformat(timespec="seconds"),
            "dias": dias,
            "desde": desde,
            "primeiro_registro": primeira,
            "agora": online,
            "hoje": por_dia.get(hoje.isoformat(), {"visitas": 0, "visitantes": 0}),
            "ontem": por_dia.get(ontem, {"visitas": 0, "visitantes": 0}),
            "periodo": {"visitas": total_desde[0], "visitantes": total_desde[1]},
            "por_dia": serie,
            "por_hora_hoje": horas,
            "paginas": _top("pagina", desde, 15),
            "origens": _top("origem", desde, 12, visitantes),
            "tipos_origem": _top("tipo_origem", desde, 8, visitantes),
            "aparelhos": _top("aparelho", desde, 5, visitantes),
            "navegadores": _top("navegador", desde, 8, visitantes),
            "sistemas": _top("sistema", desde, 8, visitantes),
            "paises": _top("pais", desde, 12, visitantes),
        }


# ------------------------------------------------------------------ login
PBKDF2_ITER = 600_000


def gerar_hash(senha, iteracoes=PBKDF2_ITER):
    sal = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), iteracoes).hex()
    return f"pbkdf2_sha256:{iteracoes}:{sal}:{h}"


def conferir_senha(senha, guardado):
    try:
        alg, it, sal, h = guardado.split(":")
        assert alg == "pbkdf2_sha256"
        calc = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), int(it)).hex()
    except (ValueError, AssertionError):
        return False
    return hmac.compare_digest(calc, h)


def _bloqueado(ip):
    limite = time.time() - TENTATIVAS_JANELA
    lista = [t for t in _falhas_login.get(ip, []) if t > limite]
    if lista:
        _falhas_login[ip] = lista
    else:
        _falhas_login.pop(ip, None)
    return len(lista) >= TENTATIVAS_MAX


def entrar(usuario, senha, ip):
    """Devolve (token, None) quando o login confere, ou (None, motivo)."""
    if not USUARIO or not SENHA_HASH:
        return None, "login ainda não configurado no servidor (rode servidor.py --definir-senha)"
    with _lock:
        if _bloqueado(ip):
            return None, "muitas tentativas erradas; espere 15 minutos"
    usuario_ok = hmac.compare_digest(str(usuario).strip().lower().encode(), USUARIO.lower().encode())
    senha_ok = conferir_senha(str(senha), SENHA_HASH)  # sempre calcula, para não revelar se o usuário existe
    if not (usuario_ok and senha_ok):
        with _lock:
            if len(_falhas_login) > 10000:
                _falhas_login.clear()
            _falhas_login.setdefault(ip, []).append(time.time())
        return None, "usuário ou senha incorretos"
    token = secrets.token_urlsafe(32)
    with _lock:
        _db.execute("INSERT INTO sessoes(token_hash, criada, expira) VALUES(?, ?, ?)",
                    (hashlib.sha256(token.encode()).hexdigest(), int(time.time()), int(time.time()) + SESSAO_DIAS * 86400))
    return token, None


def sessao_valida(token):
    if not token:
        return False
    with _lock:
        row = _db.execute("SELECT criada, expira FROM sessoes WHERE token_hash=?",
                          (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    return bool(row and row[1] > time.time() and row[0] >= SESSOES_DESDE)


def sair(token):
    if token:
        with _lock:
            _db.execute("DELETE FROM sessoes WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))


def definir_senha():
    """Pergunta usuário e senha no terminal e grava no arquivo de configuração (encerra as sessões abertas)."""
    import getpass
    usuario = input("Usuário do painel: ").strip()
    if not re.fullmatch(r"[A-Za-z0-9._@-]{3,60}", usuario):
        raise SystemExit("Usuário inválido (use 3 a 60 letras, números, ponto, hífen ou @).")
    senha = getpass.getpass("Senha (mínimo 10 caracteres): ")
    if len(senha) < 10:
        raise SystemExit("Senha curta demais.")
    if getpass.getpass("Repita a senha: ") != senha:
        raise SystemExit("As senhas não conferem.")
    linhas = open(ENV_PATH, encoding="utf-8").read().splitlines() if os.path.exists(ENV_PATH) else []
    linhas = [l for l in linhas if not l.startswith(("CONTADOR_USUARIO=", "CONTADOR_SENHA_HASH=", "CONTADOR_SESSOES_DESDE="))]
    linhas += [f"CONTADOR_USUARIO={usuario}", f"CONTADOR_SENHA_HASH={gerar_hash(senha)}",
               f"CONTADOR_SESSOES_DESDE={int(time.time())}"]
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    os.chmod(ENV_PATH, 0o600)
    print(f"Login salvo em {ENV_PATH}. Reinicie o serviço: sudo systemctl restart radar-contador")


# ------------------------------------------------------------------ HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "RadarContador/1.0"
    sys_version = ""

    def log_message(self, fmt, *args):  # sem log de IPs
        pass

    def _origem_ok(self):
        o = (self.headers.get("Origin") or "").rstrip("/")
        return o if o in ORIGENS or "*" in ORIGENS else ""

    def _cors(self):
        o = self._origem_ok()
        if o:
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Max-Age", "86400")

    def _resposta(self, codigo, corpo=b"", tipo="application/json; charset=utf-8"):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(codigo)
        self._cors()
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def _ip(self):
        # o serviço só escuta em 127.0.0.1: quem chega é o túnel (Cloudflare/Tailscale), que informa o IP real
        for h in ("CF-Connecting-IP", "X-Forwarded-For", "X-Real-IP"):
            v = self.headers.get(h)
            if v:
                return v.split(",")[0].strip()[:64]
        return self.client_address[0]

    def do_OPTIONS(self):
        self._resposta(204 if self._origem_ok() else 403)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/saude", "/"):
            return self._resposta(200, b"ok", "text/plain; charset=utf-8")
        if url.path == "/stats":
            if not self._origem_ok():
                return self._resposta(403, {"erro": "origem não permitida"})
            if not sessao_valida(self._token()):
                return self._resposta(401, {"erro": "entre com usuário e senha"})
            try:
                dias = int(parse_qs(url.query).get("dias", ["30"])[0])
            except ValueError:
                dias = 30
            return self._resposta(200, totais(dias))
        self._resposta(404, {"erro": "não encontrado"})

    def _token(self):
        return (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()[:100]

    def do_POST(self):
        rota = urlparse(self.path).path
        if rota not in ("/hit", "/login", "/logout"):
            return self._resposta(404, {"erro": "não encontrado"})
        # aceita só pedidos vindos do próprio site (o navegador sempre envia a origem)
        if not self._origem_ok():
            return self._resposta(403, {"erro": "origem não permitida"})
        if rota == "/logout":
            sair(self._token())
            return self._resposta(204)
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            tamanho = 0
        if tamanho <= 0 or tamanho > MAX_CORPO:
            return self._resposta(400, {"erro": "corpo inválido"})
        try:
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            if not isinstance(dados, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            return self._resposta(400, {"erro": "corpo inválido"})
        if rota == "/login":
            token, erro = entrar(dados.get("usuario", ""), dados.get("senha", ""), self._ip())
            if not token:
                return self._resposta(401, {"erro": erro})
            return self._resposta(200, {"token": token, "usuario": USUARIO, "dias": SESSAO_DIAS})
        registrar(dados, self._ip(), self.headers.get("User-Agent", "")[:400], self.headers.get("CF-IPCountry", ""))
        self._resposta(204)


def main():
    import sys
    if "--definir-senha" in sys.argv:
        return definir_senha()
    conectar()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    print(f"Contador de acessos em http://{HOST}:{PORT} (banco: {DB_PATH}; origens: {', '.join(ORIGENS)}; "
          f"login {'configurado' if USUARIO and SENHA_HASH else 'NÃO configurado: rode --definir-senha'})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
