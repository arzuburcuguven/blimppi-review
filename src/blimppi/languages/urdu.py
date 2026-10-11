"""
Follows hindi config
"""

from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig, 
)
from src.blimppi.modifiers import Drop, ConditionalRule



from src.config.paths import UD, FINAL_PAIRS

extra_licensors = {
    frozenset({"بغیر", "بنا"}): ("without_pp_licensor", 1),
    frozenset({"سکنا"}): ("modal_licensor", 1),
    frozenset({"پہلے"}): ("before_licensor", 1),
}

def progressive_detector(clause_head_id, token_dict):
    head = token_dict.get(clause_head_id)
    if not head:
        return (None, None)
    for t in token_dict.values():
        feats = t.get("feats") or {}
        if feats.get("Aspect") == "Prog" and t["head"] == clause_head_id:
            return ("prog", t["id"])
    return (None, None)

neg_lemmas = {
    "نہیں", 
}

URDU_NPIS = {
    "کوئی_بھی",   # any/anyone
    "کچھ_بھی",    # anything
    "کہیں_بھی",   # anywhere
    "کبھی_بھی",   # ever (bigram)
    "کبھی",       # ever (bare — NPI-active in Urdu)
    "ایک_بھی",    # even one (rare)
    "ہرگز",       # by no means / at all Herkes?? It is everyone in turkish
    "تاحال",    # yet/so far
}


negative_predicates = {"انکار", "خارج", "مخالفت", "منع"}




config = LanguageConfig(
    language="Urdu",
    npi_upos={"PRON", "ADV", "DET", "PART", "NUM", "NOUN"},
    npi_environments={"neg", "prog", "without_pp_licensor", "modal_licensor", "before_licensor", "neg_predicate"},
    exclude_lemmas={"dokud"},
    npi_lemmas=URDU_NPIS,
    neg_lemmas=neg_lemmas,
    conditional_markers={"अगर"},
    negative_predicates=negative_predicates,
    threshold=0.50,
    bigrams = [
    ("کوئی", "بھی", "کوئی_بھی"),
    ("کچھ", "بھی", "کچھ_بھی"),
    ("کبھی", "بھی", "کبھی_بھی"),
    ("ایک", "بھی", "ایک_بھی"),     # rare (ایک mostly NUM)
    ("کہیں", "بھی", "کہیں_بھی"),
    ("ذرا", "بھی", "ذرا_بھی"),     # near-absent (n=1)
    ],
    max_sent_len=60,
    extra_detectors=[progressive_detector],
    extra_licensors=extra_licensors,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"نہ", "نہیں"},
            action=Drop(neg_lemmas), check= "neg"
        ),
        ConditionalRule(
        condition=lambda lic_tok, td: lic_tok.get("lemma") in {"بغیر", "بنا"},
        action=Drop({"بغیر", "بنا"}), check="neg"
    ),
    ],

)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")