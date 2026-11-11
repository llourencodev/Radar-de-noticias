"""Tipo e estágio de publicações fiscais. Regra de segurança: na dúvida, o estágio menos avançado.

Tipos:   oficial | jornalistica
Estágios (do menos ao mais avançado):
  nao_determinado, projeto_de_lei, consulta_publica, norma_aprovada, norma_publicada, norma_em_vigor
"""
import re

from .normalize import strip_accents

STAGE_LABELS = {
    "nao_determinado": "Não determinado",
    "projeto_de_lei": "Projeto de lei",
    "consulta_publica": "Consulta pública",
    "norma_aprovada": "Norma aprovada",
    "norma_publicada": "Norma publicada",
    "norma_em_vigor": "Norma em vigor",
}

NORM = (r"(lei complementar|lei ordinaria|\blei\b|decreto|instrucao normativa|\bin rfb\b|portaria|resolucao|"
        r"ajuste sinief|convenio icms|ato cotepe|nota tecnica|\bnt\b|medida provisoria|ato declaratorio|"
        r"ato tecnico|emenda constitucional|solucao de consulta|parecer normativo)")

REFS = [
    r"Lei Complementar n?º?\s*\d+(?:/\d{2,4})?", r"\bLC\s*\d+/\d{2,4}", r"\bLei n?º?\s*\d[\d\.]*(?:/\d{2,4})?",
    r"Decreto n?º?\s*\d[\d\.]*(?:/\d{2,4})?", r"Instrução Normativa (?:RFB )?n?º?\s*\d[\d\.]*(?:/\d{2,4})?",
    r"\bIN RFB n?º?\s*\d[\d\.]*(?:/\d{2,4})?", r"Ajuste SINIEF n?º?\s*\d+(?:/\d{2,4})?",
    r"Convênio ICMS n?º?\s*\d+(?:/\d{2,4})?", r"Ato COTEPE(?:/ICMS)? n?º?\s*\d+(?:/\d{2,4})?",
    r"Nota Técnica (?:n?º?\s*)?\d{4}\.\d{3}(?:\s*v?\d+\.\d+)?", r"\bNT\s*\d{4}\.\d{3}(?:\s*v?\d+\.\d+)?",
    r"Medida Provisória n?º?\s*\d[\d\.]*(?:/\d{2,4})?", r"\bPLP\s*n?º?\s*\d+(?:/\d{2,4})?",
    r"\bPL\s*n?º?\s*\d[\d\.]*(?:/\d{2,4})", r"\bPEC\s*n?º?\s*\d+(?:/\d{2,4})?",
    r"Emenda Constitucional n?º?\s*\d+", r"Ato Técnico Conjunto [A-Z/]+ n?º?\s*\d+(?:,? de \d{4})?",
    r"Portaria [A-Z/]+ n?º?\s*\d[\d\.]*(?:/\d{2,4})?",
]
REFS_RX = re.compile("|".join(REFS), re.I)


def legal_refs(text: str) -> list[str]:
    seen, out = set(), []
    for m in REFS_RX.finditer(text or ""):
        ref = re.sub(r"\s+", " ", m.group(0)).strip()
        key = ref.lower()
        if key not in seen:
            seen.add(key)
            out.append(ref)
    return out[:8]


def analyze(title: str, excerpt: str, official: bool) -> dict:
    """Retorna doc_type, legal_stage, stage_note, legal_refs e legislative."""
    raw = f"{title}. {excerpt or ''}"
    t = strip_accents(raw.lower())
    doc_type = "oficial" if official else "jornalistica"
    refs = legal_refs(raw)
    has_norm = bool(re.search(NORM, t))
    stage, note = "nao_determinado", None

    if re.search(r"consulta publica|tomada de subsidios|audiencia publica", t):
        stage = "consulta_publica"
    elif re.search(r"\b(projeto de lei|plp|pl \d|pec\b|proposta de emenda|anteprojeto|minuta)", t) or \
            re.search(r"\b(tramita|em discussao|relator|comissao aprova|aprovad[oa] (na|pela) comissao)", t):
        stage = "projeto_de_lei"
        if re.search(r"(vai a sancao|segue (para|a) sancao|enviad[oa] a sancao|aprovad[oa] em definitivo|"
                     r"promulgad)", t):
            stage, note = "norma_aprovada", "Aprovada pelo Legislativo; ainda depende de sanção/publicação."
    if stage == "nao_determinado" and re.search(r"(sancion|promulg)", t):
        stage = "norma_aprovada"
    publish_rx = (r"(publicad[oa]|publica\b|divulga|edita|institui|altera|aprova (o|a) |disponibiliza|"
                  r"diario oficial|dou\b|\bnova versao|versao \d)") if official else \
        r"(publicad[oa]|publica\b|diario oficial|\bdou\b|sancionad|nova versao|versao \d)"
    if stage in ("nao_determinado", "norma_aprovada") and has_norm and re.search(publish_rx, t):
        stage = "norma_publicada"
    if stage == "nao_determinado" and has_norm and re.search(r"(confaz aprova|aprovad[oa] pelo confaz|"
                                                            r"conselho aprova)", t):
        stage = "norma_aprovada"
    if stage in ("nao_determinado", "norma_publicada") and re.search(
            r"(entrou em vigor|ja esta em vigor|esta em vigor|passou a valer|ja vigora|em vigor desde)", t):
        if official:
            stage = "norma_em_vigor"
        else:
            stage = "norma_publicada"
            note = "Vigência informada por fonte jornalística; confirme na publicação oficial."
    if stage == "nao_determinado" and re.search(r"(entra em vigor|passa a valer|produzira efeitos|vigencia a partir)", t):
        stage = "norma_publicada" if has_norm else "nao_determinado"
        note = "Vigência futura: verifique a data de início na norma."
    if stage == "nao_determinado" and official and refs and has_norm:
        stage = "norma_publicada"
    if doc_type == "jornalistica" and stage == "norma_em_vigor":
        stage = "norma_publicada"
    legislative = stage != "nao_determinado" or bool(refs)
    return {"doc_type": doc_type, "legal_stage": stage, "stage_note": note, "legal_refs": refs,
            "legislative": legislative}
