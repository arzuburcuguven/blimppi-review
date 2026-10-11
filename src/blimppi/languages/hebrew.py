# Indefinites and Negative Polarity Items in Modern Hebrew  Keren C. Tonciulescu + haspelmath
# Lo matsati shum/af iparon #any
# Af ehad. no one
# af lo davar ehad - nothing at all
# klum # anything
# she-lo that not?

from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Drop, ConditionalRule

from src.config.paths import UD, FINAL_PAIRS

neg_lemmas = {"לא", "אין"}

# מעולם never

## אף אחד ehad

##  דבר אחד one thing
 
npi_lemmas = {"שום", #shum
                "כלום", # klum
                "מעולם", #never
                "לעולם", #never
                "אף_אחד", #at all
    "אף_פעם",
    "אף_דבר",
    "שום_דבר",
    "מאומה",   # me'uma — nothing/anything (literary)
                }


bigrams_hebrew = [
    ("אף", "אחד", "אף_אחד"),     # af ehad — no one
    ("אף", "פעם", "אף_פעם"),     # af pa'am — ever / never
    ("אף", "דבר", "אף_דבר"),     # af davar — nothing
    ("שום", "דבר", "שום_דבר")  # sum davar
]

extra_licensors = {frozenset({"ללא"}): ("without_pp_licensor",2)}


config = LanguageConfig(
    language="Hebrew",
    npi_upos={"PRON", "DET", "CCONJ", "ADV"},
    npi_environments={"neg", "without_pp_licensor"},
    neg_lemmas=neg_lemmas,
    exclude_lemmas=set(),
    npi_lemmas=npi_lemmas,
    #conditional_markers={"αν"},
    extra_licensors=extra_licensors,
    negative_predicates=set(),
    interclause_licensor={"neg", "without_pp_licensor"},
    threshold=0.00,
    min_freq=0,
    max_sent_len=100,
    bigrams=bigrams_hebrew,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in neg_lemmas,
            action=Drop(neg_lemmas), check="neg",
        ),
    ]
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}"
    )