"""Classificação por categoria, natureza (fato/opinião) e relevância — regras locais, sem custo."""
import json
import re
from datetime import datetime, timezone
from functools import lru_cache

from .. import config
from .normalize import strip_accents

OFFICIAL_DOMAINS = re.compile(
    r"(\.gov\.br|\.leg\.br|\.jus\.br|^gov\.br|fazenda\.gov\.br|sefaz\.|planalto\.gov\.br|in\.gov\.br)$|"
    r"(^|\.)(gov\.br|leg\.br)$")
OPINION = re.compile(r"(/opiniao/|/opinion/|/coluna|/colunas/|/column|/artigos?/|/editorial|/blogs?/.*opini|/analise/)", re.I)
HOT_TERMS = [
    "lancamento", "lanca", "launch", "released", "nova versao", "release", "publicada", "publicado",
    "nota tecnica", "ajuste sinief", "convenio icms", "instrucao normativa", "lei complementar", "prazo",
    "obrigatorio", "obrigatoria", "vigencia", "entra em vigor", "cronograma", "regulamenta", "critica",
    "vulnerabilidade", "zero-day", "ataque", "breaking", "anuncia", "announces", "introducing",
    "disponivel", "general availability", "preview",
]


def _compile(keywords):
    """Palavra-chave em minúsculas casa sem diferenciar maiúsculas; com prefixo "=" diferencia
    (ex.: "=React" não casa com o verbo inglês "react", "=IA" não casa com o verbo "ia")."""
    out = []
    for k, w in _weighted(keywords):
        exact = k.startswith("=")
        word = strip_accents(k[1:] if exact else k.lower())
        rx = re.compile(r"(?<![\w])" + re.escape(word) + r"(?![\w])")
        out.append((rx, w, exact))
    return out


@lru_cache(maxsize=1)
def _categories() -> list[dict]:
    cats = json.loads((config.CONFIG_DIR / "categories.json").read_text(encoding="utf-8"))
    for c in cats:
        c["_rx"] = _compile(c.get("keywords", []))
        c["_req"] = _compile(c.get("requires_any", []))
    return cats


def _weighted(kws):
    for k in kws:
        if isinstance(k, list):
            yield k[0], float(k[1])
        else:
            yield k, 1.0


def _hit(rx, exact, low, orig):
    return rx.search(orig if exact else low)


def keyword_scores(title: str, excerpt: str) -> dict:
    """{categoria: (pontos no título, pontos totais)} — só categorias com contexto exigido presente."""
    t_orig = strip_accents(title)
    e_orig = strip_accents((excerpt or "")[:1500])
    t, e = t_orig.lower(), e_orig.lower()
    out = {}
    for c in _categories():
        if c["_req"] and not any(_hit(rx, ex, t + " " + e, t_orig + " " + e_orig) for rx, _, ex in c["_req"]):
            continue
        ts = es = 0.0
        for rx, w, exact in c["_rx"]:
            if _hit(rx, exact, t, t_orig):
                ts += 2 * w
            elif _hit(rx, exact, e, e_orig):
                es += w
        if ts or es:
            out[c["slug"]] = (ts, ts + es)
    return out


def classify(title: str, excerpt: str, source_category: str | None, source_type: str,
             require_title: bool = False) -> list[tuple]:
    """Retorna [(categoria, origem, confiança)], a primeira é a principal.

    Uma categoria diferente da categoria da fonte só entra com evidência forte: palavra-chave no
    título ou pontuação alta no texto. Com require_title=True (fontes generalistas), só o título conta.
    """
    kw = keyword_scores(title, excerpt)
    scores = {}
    for slug, (ts, total) in kw.items():
        if require_title:
            if ts >= 2:
                scores[slug] = total
        elif slug == source_category or ts >= 2 or total >= 4:
            scores[slug] = total
    if source_category:
        base = 3.0 if source_type == "search" else 2.0
        scores[source_category] = scores.get(source_category, 0) + base
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    result = []
    for slug, sc in ranked:
        if sc >= 2.0:
            origin = "fonte" if slug == source_category and kw.get(slug, (0, 0))[1] == 0 else "regra"
            result.append((slug, origin, round(min(1.0, sc / 8), 2)))
    slugs = [r[0] for r in result]
    if "reforma" in slugs and "fiscal" not in slugs and kw.get("fiscal", (0, 0))[1] >= 1:
        result.append(("fiscal", "regra", 0.4))
    return result[:3]


def is_official(domain: str, source_official: bool) -> bool:
    return bool(source_official or (domain and OFFICIAL_DOMAINS.search(domain)))


def nature(url: str, tags: list[str], section: str = "") -> str:
    blob = " ".join(tags + [section]).lower()
    if OPINION.search(url or "") or re.search(r"\b(opini[aã]o|opinion|coluna|editorial|artigo de opini)", blob):
        return "opiniao"
    return "fato"


def relevance(title: str, excerpt: str, official: bool, priority: int, published: datetime | None,
              legislative: bool, n_sources: int = 1) -> float:
    t = strip_accents((title + " " + (excerpt or "")[:400]).lower())
    score = 20.0
    if official:
        score += 25
    score += min(10, (priority - 1) * 5)
    score += min(20, sum(5 for k in HOT_TERMS if k in t))
    if legislative:
        score += 10
    if published:
        age_h = (datetime.now(timezone.utc) - published).total_seconds() / 3600
        score += max(0.0, 15 - age_h / 8)
    score += min(15, (n_sources - 1) * 5)
    return round(min(100.0, score), 1)
