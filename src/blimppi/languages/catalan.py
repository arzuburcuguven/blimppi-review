from blimppi.pipeline import LanguageConfig, run_pipeline, save_output
from blimppi.modifiers import Swap, Drop, ConditionalRule

from src.config.paths import UD, FINAL_PAIRS

# from Espinal & Llop NPIs in Catalan (2022)
npi_lemma_upos = {
    "ningú":          {"PRON"},          # anybody
    "mai":        {"ADV"},          # ever
    "enlloc":         {"ADV"},          # anywhere?
    "cap":       {"PRON","DET"},          # any
    "molla":      {"ADV", "ADJ"},   # crumb
    "pas":   {"ADV"},          # step, no pas -- strong or idiomatic?
    "gaire":         {"ADV"},         # much?
    "gens":       {"ADV"},         # not at all
    "res":     {"PRON", "DET"},         # anything, noe?
}

extra_licensors = {
    frozenset({"sense"}): ("without_pp_licensor", 3),              
}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
config = LanguageConfig(
    language="Catalan",
    npi_upos={"PRON", "ADV", "DET"}, 
    npi_lemmas = npi_lemma_upos,   # DET for "cap"
    npi_environments={
        "neg", "comparative", "conditional", "question", "without_pp_licensor"
    },
    neg_lemmas={"no"},                   
    skip_pair_environments={"question", "comparative", "conditional"},
    conditional_markers={"si"},          
    comparative_markers={"que"},         
    extra_licensors=extra_licensors,
    interclause_licensor={"neg", "without_pp_licensor"},
    threshold=0.00,                      
    min_freq=5,                          
    max_sent_len=60,
    removal_rules=[
        # Drop preverbal negation marker "no"
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") == "no",
            action=Drop({"no"}), check="neg"
        ),

        # without - with
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") == "sense",
            action=Swap({"sense": "amb"}),check="neg"
        ),
    ]
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config, FINAL_PAIRS / f"{config.lang.lower()}"
    )