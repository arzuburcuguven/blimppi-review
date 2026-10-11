# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
from src.blimppi.blacklist import BLOCKED_NPI_PHRASES

import os
import pandas as pd
def write_stats(output, config, output_dir):
    rows = []
    for lemma, c in output["lemma_counts"].items():
        total = c["total"]
        for env, n in c["environments"].items():
            rows.append({
                "lang": config.lang, "lemma": lemma,
                "total": total, "licensed": c["licensed"],
                "licensing_ratio": c["licensing_ratio"],
                "env": env, "env_count": n,
                "env_share": round(n / total, 3) if total else 0,
                "min_freq": config.min_freq, "threshold": config.threshold,
            })
    path = os.path.join(output_dir, f"{config.lang.lower()}_stats.csv")
    pd.DataFrame(rows).to_csv(path, index=False)   # overwrite, no append

def gar_is_npi(tok, td):
    ids = sorted(td)
    pos = {t: i for i, t in enumerate(ids)}
    i = pos[tok["id"]]
    nxt = ids[i + 1] if i + 1 < len(ids) else None
    nxt_lemma = (td.get(nxt, {}).get("lemma") or "").lower() if nxt else ""
    return nxt_lemma in {"nicht", "nichts"}



def in_blocked_phrase(npi_id, token_dict, blocked=BLOCKED_NPI_PHRASES):
    npi = token_dict.get(npi_id)
    if not npi:
        return False
    lemma = (npi.get("lemma") or "").lower()
    phrases = blocked.get(lemma)
    if not phrases:
        return False

    ids = sorted(token_dict)
    pos = {tid: i for i, tid in enumerate(ids)}   # id -> sorted index
    npi_pos = pos[npi_id]

    for phrase in phrases:
        for off, w in enumerate(phrase):
            if w.lower() != lemma:
                continue
            start = npi_pos - off
            if start < 0 or start + len(phrase) > len(ids):
                continue
            window = ids[start:start + len(phrase)]
            if all((token_dict[t].get("lemma") or "").lower() == pw.lower()
                   for t, pw in zip(window, phrase)):
                return True
    return False

def is_verbless_fragment(token_dict):
    return not any(t["upos"] in {"VERB", "AUX"} for t in token_dict.values())

def apply_bigrams(token_dict, bigrams):
    consumed = set()
    out = {}
    for tid in sorted(token_dict):
        if tid in consumed:
            continue
        tok = dict(token_dict[tid])
        for first_lemma, second_lemma, output_lemma in bigrams:
            nxt = token_dict.get(tid + 1)
            if tok.get("lemma") == first_lemma and nxt and nxt.get("lemma") == second_lemma:
                tok["lemma"] = output_lemma          # keep first token's id/head/deprel/upos
                consumed.add(tid + 1)                # drop the particle entirely
                break
        out[tok["id"]] = tok
    # reparent anything that pointed at a consumed particle onto its surviving head
    for t in out.values():
        if t["head"] in consumed:
            t["head"] = token_dict[t["head"]]["head"]   # or the merge head; see caveat
    return out

def get_clause_head_id(token_id, token_dict):
    def is_clause_head(tid):
        tok = token_dict[tid]
        if tok["upos"] in ("VERB", "AUX", "PART"):
            return True
        if tok["head"] == 0:                      # root nominal/adjectival predicate
            return True
        # copular clause: nominal/adj head with a cop dependent
        if any(d["head"] == tid and d.get("deprel") == "cop" for d in token_dict.values()):
            return True
        return False

    current_id = token_dict[token_id]["head"]
    while current_id != 0 and not is_clause_head(current_id):
        current_id = token_dict[current_id]["head"]
    return current_id


def get_root(token_dict):
    for tid, token in token_dict.items():
        if token["head"] == 0:
            return tid, token
    return None, None

def has_fixed_relation(token, token_dict, bigrams=None):
    if bigrams:
        bigram_lemmas = {output_lemma for _, _, output_lemma in bigrams}
        if token.get("lemma") in bigram_lemmas:
            return False
    if token.get("deprel") == "fixed":
        return True
    for other in token_dict.values():
        if other.get("head") == token["id"] and other.get("deprel") == "fixed":
            return True
    return False