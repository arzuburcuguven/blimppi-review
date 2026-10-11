# ANASTASIA GIANNAKIDOU & JOSEP QUER 1997 in LONG-DISTANCE LICENSING OF NEGATIVE INDEFINITES
# kanénas/KANENAS "anyone, anybody"/"no one, nobody"  
# típota/ΤΙΡΟΤΑ "anything"/"nothing" NEG
# poté/POTE "ever"/"never" puthená/PUTHENA "anywhere/"nowhere"

from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Drop, ConditionalRule

from src.config.paths import UD, FINAL_PAIRS


neg_lemmas = {"δεν", # dhen -- not
              "min" #min do not?
              }

npi_lemmas = {"τίποτα", # tipota, nothing 
               "κανείς", # kaneis, nobody 
                "κανένας", # kanennas none
                "ποτέ", # pote, never
                "πουθενά" #pouthena nowhere"
                "καθόλου" #at all
                }

extra_licensors = {
    frozenset({"χωρίς"}): ("without_pp_licensor", 2),
    frozenset({"ελάχιστο"}): ("DE_licensor", 2),
}


config = LanguageConfig(
    language="Greek",
    npi_upos={"PRON", "ADV", "DET"},
    npi_environments={"neg", "without_pp_licensor", "DE_licensor"},
    neg_lemmas=neg_lemmas,
    exclude_lemmas=set(),
    npi_lemmas=npi_lemmas,
    conditional_markers={"αν"},
    extra_licensors=extra_licensors,
    negative_predicates=set(),
    interclause_licensor={"neg", "without_pp_licensor"},
    threshold=0.00,
    min_freq=0,
    max_sent_len=60,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"δεν", "μην"},
            action=Drop({"δεν", "μην"}), check="neg",
        ),
    ]
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}"
    )