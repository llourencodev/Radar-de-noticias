"""Integração opcional com IA (Claude, OpenAI ou Ollama local).

Desligada por padrão (LLM_PROVIDER=none). Para ligar, basta definir no .env, por exemplo:
  LLM_PROVIDER=anthropic   ANTHROPIC_API_KEY=...
  LLM_PROVIDER=ollama      OLLAMA_MODEL=llama3.1
Nada mais precisa mudar: o processamento por regras continua e a IA só substitui
resumo, pontos e impactos das notícias novas (resultado guardado no banco).
"""
import json
import logging
import re

import httpx

from .. import config
from ..http import ssl_context

log = logging.getLogger("radar.llm")

SYSTEM = (
    "Você é um analista de notícias para profissionais de TI e da área fiscal no Brasil. "
    "Use SOMENTE as informações do texto fornecido. Não acrescente fatos, datas, números ou nomes. "
    "Se o texto não trouxer informação suficiente, diga isso. Escreva em português do Brasil."
)
PROMPT = """Título original: {title}
Fonte: {outlet}
Categoria: {categories}
Texto da fonte:
\"\"\"{text}\"\"\"

Responda apenas com JSON válido, neste formato:
{{"resumo": "2 a 3 frases objetivas",
  "pontos": ["até 4 pontos principais, cada um com um fato do texto"],
  "impactos": ["impactos práticos para empresas e sistemas ERP, somente se o texto permitir inferir; senão lista vazia"],
  "e_opiniao": false}}"""


def enabled() -> bool:
    p = config.LLM_PROVIDER
    if p == "anthropic":
        return bool(config.ANTHROPIC_API_KEY)
    if p == "openai":
        return bool(config.OPENAI_API_KEY)
    return p == "ollama"


def provider_name() -> str:
    return config.LLM_PROVIDER if enabled() else "regras"


def _call(prompt: str) -> str:
    p = config.LLM_PROVIDER
    timeout = httpx.Timeout(90, connect=10)
    if p == "anthropic":
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": config.ANTHROPIC_MODEL, "max_tokens": 900, "system": SYSTEM,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=timeout, verify=ssl_context(),
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []))
    if p == "openai":
        r = httpx.post(
            config.OPENAI_BASE_URL.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={"model": config.OPENAI_MODEL, "temperature": 0.1,
                  "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]},
            timeout=timeout, verify=ssl_context(),
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    if p == "ollama":
        r = httpx.post(
            config.OLLAMA_URL.rstrip("/") + "/api/chat",
            json={"model": config.OLLAMA_MODEL, "stream": False, "format": "json",
                  "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]},
            timeout=httpx.Timeout(180, connect=10), verify=ssl_context(),
        )
        r.raise_for_status()
        return r.json()["message"]["content"]
    raise RuntimeError("Provedor de IA não configurado")


def analyze(title: str, outlet: str, categories: list[str], text: str) -> dict | None:
    """Retorna {'summary','key_points','impacts','opinion'} ou None se a IA estiver desligada/falhar."""
    if not enabled() or len(text or "") < 80:
        return None
    prompt = PROMPT.format(title=title, outlet=outlet, categories=", ".join(categories), text=text[:7000])
    try:
        raw = _call(prompt)
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {
            "summary": str(data.get("resumo", "")).strip()[:900],
            "key_points": [str(x) for x in data.get("pontos", [])][:5],
            "impacts": [str(x) for x in data.get("impactos", [])][:4],
            "opinion": bool(data.get("e_opiniao")),
        }
    except (httpx.HTTPError, ValueError, KeyError, AttributeError, RuntimeError) as ex:
        log.warning("IA indisponível (%s): %s", config.LLM_PROVIDER, ex)
        return None
