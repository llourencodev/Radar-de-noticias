"""Origem da notícia: brasileira ou estrangeira (filtro "Notícias Brasil").

Regras, na ordem:
1. Domínio do veículo terminado em .br (gov.br, leg.br, com.br...) -> brasileira.
2. Domínio de outro país de língua portuguesa (.pt, .ao, .mz, .cv...) -> estrangeira.
3. Fonte cadastrada com "country" em config/sources.json -> vale o país da fonte
   (ex.: JOTA e InfoMoney são "BR"; TechCrunch e OpenAI não são).
4. Sem país definido (buscas no Google/Bing, fontes novas): texto em português -> brasileira.
"""
import json
import re
from functools import lru_cache

from .. import config

_LUSO_FOREIGN = re.compile(r"\.(pt|ao|mz|cv|gw|st|tl|mo)$")


@lru_cache(maxsize=1)
def source_countries() -> dict[str, str]:
    try:
        sources = json.loads((config.CONFIG_DIR / "sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {s["id"]: str(s["country"]).upper() for s in sources if s.get("id") and s.get("country")}


def is_brazilian(domain: str | None, lang: str | None, source_id: str | None = None) -> bool:
    d = (domain or "").lower().rstrip(".")
    if d.endswith(".br") or d == "br":
        return True
    if _LUSO_FOREIGN.search(d):
        return False
    country = source_countries().get(source_id or "")
    if country:
        return country == "BR"
    return lang == "pt"
