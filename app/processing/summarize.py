"""Resumo extrativo, pontos principais, termos técnicos e impactos sinalizados por regras.

Sem IA paga: as frases do resumo são do próprio texto da fonte (nada é acrescentado).
Os "impactos" são sinalizações por regra, sempre rotuladas como interpretação automática.
"""
import json
import re
from collections import Counter
from functools import lru_cache

from .. import config
from .normalize import STOPWORDS, strip_accents

SENT_SPLIT = re.compile(r"(?<=[\.\!\?;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\"“])")
BOILERPLATE = re.compile(
    r"(cookies|inscreva-se|assine|newsletter|siga-nos|compartilhe|todos os direitos|leia tamb[eé]m|"
    r"clique aqui|subscribe|sign up|follow us|the post .* appeared first|continue lendo|saiba mais)", re.I)

IMPACT_RULES = [
    (r"nota tecnica|\bnt \d{4}|leiaute|layout|schema|xsd|regra de validacao",
     "Pode exigir atualização de leiaute, schemas e regras de validação no ERP/emissor de documentos fiscais.", "F"),
    (r"nf-?e|nfc-?e|ct-?e|mdf-?e|nfs-?e|documento fiscal eletronico|dfe",
     "Afeta a emissão de documentos fiscais eletrônicos: revisar emissor, contingência e integrações com a SEFAZ.", "F"),
    (r"\bibs\b|\bcbs\b|imposto seletivo|reforma tributaria",
     "Reforma tributária: avaliar parametrização de IBS/CBS/IS no ERP (cálculo, CST/cClassTrib, destaque em documentos).", "F"),
    (r"\bcfop\b|\bcst\b|csosn|\bncm\b|\bcest\b|cclasstrib",
     "Mudança em códigos fiscais: atualizar tabelas de CFOP/CST/NCM/CEST e regras de tributação no cadastro de produtos.", "F"),
    (r"sped|\befd\b|\becd\b|\becf\b|reinf|dctf|esocial|obrigacao acessoria|escrituracao",
     "Obrigação acessória: conferir geração de arquivos SPED/EFD, leiautes e prazos de entrega.", "F"),
    (r"\bicms\b|substituicao tributaria|difal|aliquota|fcp\b",
     "Alteração de ICMS/alíquotas: revisar tabelas de alíquotas por UF, ST/DIFAL e cálculo no faturamento.", "F"),
    (r"prazo|prorroga|cronograma|homologacao|producao|a partir de",
     "Há prazo ou cronograma envolvido: registrar a data de início e planejar testes em homologação.", "F"),
    (r"pis|cofins|irpj|csll|irpf|ipi\b|\biss\b",
     "Tributos federais/municipais: verificar impactos em apuração, retenções e parametrização fiscal.", "F"),
    (r"vulnerabilidade|cve-|zero-day|ataque|ransomware|falha de seguranca|patch",
     "Segurança: verificar se versões usadas na empresa estão afetadas e aplicar atualizações.", "T"),
    (r"end of support|fim do suporte|descontinu|deprecat|obsolet",
     "Fim de suporte/descontinuação: planejar migração de sistemas que dependem da tecnologia.", "T"),
]


@lru_cache(maxsize=1)
def glossary() -> list[dict]:
    path = config.CONFIG_DIR / "glossary.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    for it in items:
        pats = [it["term"]] + it.get("aliases", [])
        it["_rx"] = re.compile(r"(?<![\w])(" + "|".join(re.escape(strip_accents(p.lower())) for p in pats) + r")(?![\w])")
    return items


def find_terms(text: str, limit: int = 6) -> list[dict]:
    t = strip_accents((text or "").lower())
    out = []
    for g in glossary():
        if g["_rx"].search(t):
            out.append({"term": g["term"], "explanation": g["explanation"]})
            if len(out) >= limit:
                break
    return out


def sentences(text: str) -> list[str]:
    out = []
    for para in (text or "").split("\n"):
        for s in SENT_SPLIT.split(para.strip()):
            s = s.strip(" -•\t")
            if 40 <= len(s) <= 420 and not BOILERPLATE.search(s):
                out.append(s)
    return out


def _words(s: str) -> list[str]:
    return [w for w in re.findall(r"[\wçãõáéíóúâêô#+]+", strip_accents(s.lower())) if w not in STOPWORDS and len(w) > 2]


def extractive(title: str, text: str, max_sentences: int = 2) -> tuple[str, list[str]]:
    sents = sentences(text)
    if not sents:
        return "", []
    title_words = set(_words(title))
    freq = Counter(w for s in sents for w in _words(s))
    scored = []
    for i, s in enumerate(sents[:60]):
        ws = _words(s)
        if not ws:
            continue
        score = sum(freq[w] for w in ws) / (len(ws) ** 0.6)
        score += 3 * len(title_words & set(ws))
        score += 2.5 if re.search(r"\d", s) else 0
        score += max(0, 3 - i * 0.5)  # início do texto costuma ter o lide
        scored.append((score, i, s))
    best = sorted(scored, reverse=True)
    summary_idx = sorted(i for _, i, _ in best[:max_sentences])
    summary = " ".join(sents[i] for i in summary_idx)
    points = [s for _, i, s in best[max_sentences:max_sentences + 6] if i not in summary_idx]
    points = sorted(points, key=lambda s: sents.index(s))[:4]
    return summary[:700], points


def impacts(text: str, categories: list[str]) -> list[str]:
    cats = set(categories)
    scopes = set()
    if cats & {"fiscal", "reforma"}:
        scopes.add("F")
    if cats & {"programacao", "tecnologia", "ia"}:
        scopes.add("T")
    if not scopes:
        return []
    t = strip_accents((text or "").lower())
    out = []
    for rx, msg, scope in IMPACT_RULES:
        if scope in scopes and re.search(rx, t) and msg not in out:
            out.append(msg)
    return out[:3]
