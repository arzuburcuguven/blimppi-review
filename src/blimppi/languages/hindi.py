"""
UTPAL LAHIRI  Natural Language Semantics 6: 57–123, 1998.  1998 Kluwer Academic Publishers. Printed in the Netherlands.  
kisii-ko

ek bhii -any
kuch bhii #anything
zaraa bhii
kahiiN bhii #anywhere
kabhii bhii #anythime

#conditionals license
agar #if

predicates
aaScarya #surprised
prohibited manaa kiyaa

pahle #before
saktaa #can
sakte #may
legaa degii doge#will

#generic usage

#questions kyaa

koii bhii (anyone) → कोई भी
kisii-ko (to anyone/someone — dative) → किसी को
ek bhii (any/even one) → एक भी
kuch bhii (anything) → कुछ भी
zaraa bhii (even a little) → ज़रा भी
kahiiN bhii (anywhere) → कहीं भी
kabhii bhii (anytime) → कभी भी

Conditional licensor

agar (if) → अगर

Predicates

aaScarya (surprised) → आश्चर्य
pahle (before) → पहले
saktaa (can, masc.) → सकता
sakte (may, plural/oblique) → सकते

Questions

kyaa (what / question particle) → क्या

"""

from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Drop, ConditionalRule



from src.config.paths import UD, FINAL_PAIRS

extra_licensors = {
    frozenset({"बिना"}): ("without_pp_licensor",1),
    frozenset({"सकना"}): ("can_licensor",1),
    frozenset({"पहले"}): ("before_licensor",1),
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
    "नहीं", 
}

HINDI_NPIS = {
    "कोई_भी",    # anyone/any
    "कुछ_भी",    # anything
    "कहीं_भी",   # anywhere
    "कभी_भी",    # ever
    "एक_भी",     # even one
    "ज़रा_भी",   # even a little (minimizer)
    "कोई_को",    # to anyone (dative; thin, watch n)
    "कसर",       # spare-no-effort idiom (minimizer)
}

negative_predicates = {"विरोध", #oppose,
                       "आश्चर्य", #surprised
                       "इनकार", #refuse
                       "अस्वीकार", #deny
                       "शक", #doubt
                       "संदेह", #doubt
                       "इन्कार",
                        "इंकार",
                        "खारिज",
                        "वर्जित",
                        "पाबंदी"
                       }




config = LanguageConfig(
    language="Hindi",
    npi_upos={"PRON", "ADV", "DET", "PART", "NUM", "NOUN"},
    npi_environments={"neg", "prog", "without_pp_licensor", "can_licensor", "before_licensor", "neg_predicate", "non_pairable"},
    exclude_lemmas={"dokud"},
    npi_lemmas=HINDI_NPIS,
    neg_lemmas=neg_lemmas,
    conditional_markers={"अगर"},
    negative_predicates=negative_predicates,
    threshold=0.00,
    bigrams=[
        ("कोई", "भी", "कोई_भी"), #khoo bhii #156
        ("कोई", "को", "कोई_को"), #khoo ko # 25
        ("एक", "भी", "एक_भी"), #ek bhii
        ("कुछ", "भी", "कुछ_भी"), #khic bhii
        ("जरा", "भी", "जरा_भी"), # jara bhii
        ("कहीं", "भी", "कहीं_भी"), # kahiin bhii
        ("कभी", "भी", "कभी_भी"), # kabhi bhii
    ],
    max_sent_len=60,
    extra_detectors=[progressive_detector],
    extra_licensors=extra_licensors,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"न", "नहीं"},
            action=Drop(neg_lemmas), check= "neg"
        ),
    ConditionalRule(
        condition=lambda lic_tok, td: lic_tok.get("lemma") == "बिना",
        action=Drop({"बिना"}), check="without_pp_licensor"
    ),
    ],

)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")