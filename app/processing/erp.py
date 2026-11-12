"""Marcação "Notas técnicas / ERP": publicações que exigem ajuste ou implementação em sistemas
(ERP, emissores de documentos fiscais, escrituração). Regras locais, sem custo.

Uma notícia é marcada quando fala de um documento/obrigação eletrônica (NF-e, CT-e, SPED, IBS/CBS...)
junto com uma mudança técnica (nota técnica, leiaute, schema, regra de validação, Ajuste SINIEF...),
ou de adequação de sistemas/ERP a uma mudança nesses documentos.
Para evitar falso positivo em textos longos, o título precisa citar o documento, a norma técnica ou os sistemas.
"""
import re

from .normalize import strip_accents

RULES_VERSION = 1  # aumente ao mudar as regras: as notícias já salvas são reavaliadas na próxima execução

# documentos e obrigações eletrônicas que vivem dentro do ERP: (rótulo, regex sobre texto sem acento/minúsculo)
DOCS = [
    ("NF-e", r"\bnf-?e\b|\bnota fiscal eletronica\b(?! de servico)|\bdanfe\b"),
    ("NFC-e", r"\bnfc-?e\b|nota fiscal de consumidor"),
    ("NFS-e", r"\bnfs-?e\b|nota fiscal (eletronica )?de servicos?\b"),
    ("CT-e", r"\bct-?e\b|\bct-?e os\b|conhecimento de transporte eletronico"),
    ("MDF-e", r"\bmdf-?e\b|manifesto (eletronico )?de documentos fiscais"),
    ("NF3e/NFCom", r"\bnf3-?e\b|\bnfcom\b|\bnfag\b|\bnfgas\b"),
    ("BP-e/GNRE", r"\bbp-?e\b|\bgnre\b|\bdc-?e\b|\bgtv-?e\b"),
    ("SPED/EFD", r"\bsped\b|\befd\b|efd[- ]icms|efd[- ]contribuic|\becd\b|\becf\b|bloco k"),
    ("EFD-Reinf", r"\breinf\b"),
    ("eSocial", r"\besocial\b"),
    ("DCTFWeb", r"\bdctf ?web\b"),
    ("IBS/CBS", r"\bibs\b|\bcbs\b|imposto seletivo|cclass ?trib|split payment"),
    ("Documentos fiscais", r"documentos? fisca(?:l|is) eletronicos?|\bdf-?e\b|documentos? fisca(?:l|is)"),
]
DOCS_RX = [(label, re.compile(rx)) for label, rx in DOCS]

# normas/documentos técnicos: por si só indicam mudança de leiaute, regra ou código
TECH = re.compile(
    r"nota tecnica|\bnt ?\d{4}[.\-/]\d{3}|ajuste sinief|ato cotepe|\bleiautes?\b|\blayouts?\b|\bschemas?\b|"
    r"regras? de validacao|\brejeic(?:ao|oes)\b|manual de orientacao|\bmoc\b|guia pratico|pacote de liberacao|"
    r"cclass ?trib|\bcbenef\b|codigo de beneficio|tabela de (?:codigos|cst|cfop|ncm|cest|classificacao)|"
    r"novos? campos?|novos? grupos?|novas? tags?|nova versao do (?:leiaute|schema|programa|pva)|\bpva\b|"
    r"\bweb ?services?\b|ambiente de (?:homologacao|producao|testes?)|\bhomologacao\b|emissor nacional|"
    r"padrao nacional|\bqr ?code\b")
NT_SHORT = re.compile(r"\bnts?\b")  # "NT" sozinho é ambíguo: só vale com um documento eletrônico no título
# normas que quase sempre mexem em documento fiscal, mesmo sem citar o documento
TECH_ALONE = re.compile(r"ajuste sinief|ato cotepe|\bnt ?\d{4}[.\-/]\d{3}|nota tecnica (?:n[oº.]? ?)?\d{4}[.\-/]\d{3}")
# sistemas que precisam ser adequados
SYSTEMS = re.compile(
    r"\berps?\b|sistemas? (?:de gestao|emissor(?:es)?|fiscais|de faturamento|contabeis|internos|empresariais)|"
    r"softwares?|software house|desenvolvedor(?:es)?|fornecedores de sistemas|adequacao (?:dos|de) sistemas|"
    r"(?:atualizar|adaptar|adequar|ajustar|preparar) (?:os |seus )?sistemas|parametriza")
# sinal de mudança/obrigação (necessário quando só "sistemas" aparece)
CHANGE = re.compile(
    r"obrigatori|prazo|vigencia|entra em vigor|passa(?:m)? a (?:valer|ser|exigir)|cronograma|implementa|implanta|"
    r"adequa|adapta|ajust|altera|destac|mudanc|nova|novo|exig|preparar|atualiza|inclu|substitu|teste")

# documento fiscal eletrônico citado no título junto com mudança de regra ("NFS-e terá novas regras em dezembro")
DFE_TITLE = re.compile(r"\bnf-?e\b|\bnfc-?e\b|\bnfs-?e\b|\bct-?e\b|\bmdf-?e\b|\bnf3-?e\b|\bnfcom\b|\bbp-?e\b|\bdanfe\b")
RULE_CHANGE = re.compile(
    r"novas? regras?|\bregras?\b|\bmuda|mudanc|\baltera|passa(?:m)? a|a partir de|\btera\b|\bterao\b|obrigatori|"
    r"\bfim d[aeo]|deixa(?:m)? de|\bexig|\bprazo|\bnovos?\b|\bnovas?\b|\bpreenchimento|\bvalida")

LABEL_REASON = {
    "dfe": "Mudança de regra em documento fiscal eletrônico",
    "tech": "Nota técnica, leiaute ou regra de validação",
    "sinief": "Ajuste SINIEF / Ato COTEPE",
    "systems": "Adequação de sistemas/ERP",
}


def _clean(s: str) -> str:
    return strip_accents((s or "").lower())


def analyze(title: str, text: str = "") -> dict:
    """Retorna {"erp_impact": bool, "erp_docs": [rótulos], "erp_reason": str|None}."""
    t = _clean(title)
    body = _clean((text or "")[:1500])
    full = f"{t} {body}"
    docs = [label for label, rx in DOCS_RX if rx.search(full)]
    # "Documentos fiscais" genérico só quando nenhum documento específico apareceu
    if len(docs) > 1 and "Documentos fiscais" in docs:
        docs.remove("Documentos fiscais")
    title_doc = any(rx.search(t) for _, rx in DOCS_RX)
    title_tech = bool(TECH.search(t))
    title_sys = bool(SYSTEMS.search(t))
    reason = None

    if TECH_ALONE.search(t) or (TECH_ALONE.search(body) and (title_doc or title_tech)):
        reason = "sinief" if re.search(r"ajuste sinief|ato cotepe", full) else "tech"
    elif docs and (title_doc or title_tech) and (TECH.search(full) or (title_doc and NT_SHORT.search(t))):
        reason = "tech"
    if not reason and docs and SYSTEMS.search(full) and CHANGE.search(full) and \
            (title_doc or title_sys or title_tech or re.search(r"\berps?\b", body)):
        reason = "systems"
    if not reason and DFE_TITLE.search(t) and RULE_CHANGE.search(t):
        reason = "dfe"
    if not reason:
        return {"erp_impact": False, "erp_docs": [], "erp_reason": None}
    return {"erp_impact": True, "erp_docs": docs[:4], "erp_reason": LABEL_REASON[reason]}
