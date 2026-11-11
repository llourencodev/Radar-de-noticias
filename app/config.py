"""Configuração central: lê variáveis de ambiente e o arquivo .env (sem dependências extras)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
WEB_DIR = BASE_DIR / "web"


def _load_dotenv() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "sim", "yes", "on")


HOST = os.environ.get("RADAR_HOST", "127.0.0.1")
PORT = _int("RADAR_PORT", 8000)
DB_PATH = Path(os.environ.get("RADAR_DB", str(DATA_DIR / "radar.db")))

# Atualização automática
INTERVAL_MIN = _int("RADAR_INTERVAL_MIN", 60)          # intervalo padrão de cada fonte
AUTO_UPDATE = _bool("RADAR_AUTO_UPDATE", True)         # liga/desliga o agendador
COLLECT_ON_START = _bool("RADAR_COLLECT_ON_START", True)
WORKERS = _int("RADAR_WORKERS", 6)                     # fontes coletadas em paralelo

# Janela de recência (itens mais antigos não são armazenados como novidade)
MAX_AGE_DAYS = _int("RADAR_MAX_AGE_DAYS", 30)
FISCAL_MAX_AGE_DAYS = _int("RADAR_FISCAL_MAX_AGE_DAYS", 120)

# Leitura de páginas originais (imagem, data, texto para resumo)
FETCH_PAGES = _bool("RADAR_FETCH_PAGES", True)
PAGE_BUDGET_PER_SOURCE = _int("RADAR_PAGE_BUDGET", 15)
GOOGLE_DECODE_BUDGET = _int("RADAR_GOOGLE_DECODE_BUDGET", 12)
HTTP_TIMEOUT = _int("RADAR_HTTP_TIMEOUT", 20)
HOST_MIN_INTERVAL = float(os.environ.get("RADAR_HOST_MIN_INTERVAL", "1.0"))
USER_AGENT = os.environ.get(
    "RADAR_USER_AGENT",
    "Mozilla/5.0 (compatible; RadarInteligenteNoticias/1.0; leitor pessoal de noticias)",
)

# IA opcional: none | anthropic | openai | ollama
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "none").strip().lower()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
LLM_MAX_PER_RUN = _int("LLM_MAX_PER_RUN", 40)
