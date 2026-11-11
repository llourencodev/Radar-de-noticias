"""Duplicidade e atualizações: mesma história em várias fontes ou nova versão de uma publicação."""
import re
from difflib import SequenceMatcher

DUP_THRESHOLD = 0.82
UPDATE_THRESHOLD = 0.6
UPDATE_CUES = re.compile(
    r"\b(atualiza|atualizad|atualizacao|retifica|republica|nova versao|versao|altera|prorroga|adia|"
    r"update|updated|v\d+\.\d+|errata|corrig)", re.I)
VERSION = re.compile(r"\bv?(\d+\.\d+(?:\.\d+)?)\b")


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    sa, sb = set(a.split()), set(b.split())
    jac = len(sa & sb) / max(1, len(sa | sb))
    ratio = SequenceMatcher(None, a, b).ratio()
    return max(jac, ratio * 0.95)


def find_match(title_norm: str, recent: list[dict]) -> tuple[dict | None, float]:
    best, best_s = None, 0.0
    for r in recent:
        s = similarity(title_norm, r.get("title_norm") or "")
        if s > best_s:
            best, best_s = r, s
    return best, best_s


def decide(title_norm: str, recent: list[dict]) -> dict:
    """Retorna {'match': registro|None, 'is_duplicate': bool, 'is_update': bool, 'score': float}."""
    match, score = find_match(title_norm, recent)
    out = {"match": None, "is_duplicate": False, "is_update": False, "score": round(score, 3)}
    if not match or score < UPDATE_THRESHOLD:
        return out
    v_new = set(VERSION.findall(title_norm))
    v_old = set(VERSION.findall(match.get("title_norm") or ""))
    version_changed = bool(v_new and v_old and v_new != v_old)
    cue = bool(UPDATE_CUES.search(title_norm))
    if score >= DUP_THRESHOLD and not version_changed:
        out.update(match=match, is_duplicate=True)
    elif version_changed or (cue and score >= UPDATE_THRESHOLD):
        out.update(match=match, is_update=True)
    elif score >= DUP_THRESHOLD:
        out.update(match=match, is_duplicate=True)
    return out
