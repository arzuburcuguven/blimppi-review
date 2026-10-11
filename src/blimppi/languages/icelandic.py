""" 
aldrei #never
ekki #not
engum #nobody


alltaf #always


Negative Object Movement or Negative  Scrambling?


neinar #any
engar #no
neinn #any
neitt #anything
neinum # anybody
"""

from src.blimppi.pipeline import run_pipeline, save_output, LanguageConfig
from src.blimppi.modifiers import Drop, Swap, ConditionalRule

from src.config.paths import UD, FINAL_PAIRS



n_series = {
    "enginn", #No - N
    "engin",
    "engum", #Nobody
    "ekkert", #nothing
    "hvergi", #nowhere
    "aldrei", #never
    "engan" # also nobody? just no?
    }


npi_lemma_upos = {
"neinn":  {"DET", "PRON"},   #
"neitt": {"PRON"},
}

extra_licensors = {
    frozenset({"án"}): ("without_pp_licensor",1),
    frozenset({"varla", "naumast"}):            ("DE_licensor", 2),   # hardly / scarcely
    frozenset({"aðeins", "einungis", "bara"}):  ("DE_licensor", 2),   # only
    frozenset({"hvorki"}):                      ("DE_licensor", 2),   # neither (…né)
    frozenset({"fár"}):                         ("DE_licensor", 2),   # few
}

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

comparative_markers = {"en"}
conditional_markers = {"ef"}


ingen_to_indefinite_map = {
    "enginn":      "ein-hver", # how
    "engum":  "eitt-hvað",
    "ekkert":      "eitt-hvað",
    "hvergi": "einhvers",
    "aldrei":         "alltaf",
}


config = LanguageConfig(
    language="Icelandic",
    npi_upos={"PRON", "ADV", "DET"},
    npi_environments={
        "neg", "comparative", "conditional", "question",
        "aux_inversion", "DE_licensor", "without_pp_licensor"
    },
    skip_pair_environments={
        "comparative", "conditional",
    },
    npi_lemmas=npi_lemma_upos,
    neg_lemmas={"ekki"},
    n_series=n_series,
    conditional_markers=conditional_markers,
    comparative_markers=comparative_markers,
    extra_licensors=extra_licensors,
    interclause_licensor={"neg", "n_series_neg",},
    threshold=0.00,
    min_freq=0,
    max_sent_len=65,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"ekki", "icke", "ej", "bara", "varken"},
            action=Drop({"ekki", "icke", "ej", "bara", "varken"}),  check="neg"
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") == "enginn" and neg_tok.get("UPOS") == "DET" ,
            action=Swap({"enginn": "einhver" }),  check="neg"
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in n_series ,
            action=Swap(ingen_to_indefinite_map),  check="neg"
        ),
    ],
)


if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}"
    )