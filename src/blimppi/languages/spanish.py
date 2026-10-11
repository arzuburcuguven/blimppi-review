from src.blimppi.pipeline import (
    LanguageConfig,
    run_pipeline, save_output,
)
from src.blimppi.modifiers import Swap, Drop, ConditionalRule

from src.config.paths import UD, FINAL_PAIRS

## Negative polarity and scalar semantics in Spanish
# Raúl Aranovich
# University of California Davis
#Lucia Gomez
#Tampoco - tambien
# nada ‘nothing’, nadie ‘no one’, nunca ‘never’, and ningún N ‘


npi_lemma_upos = {
    "nada":          {"PRON"},          # ‘nothing’
    "nadie":        {"PRON"},          #  no one
    "nunca":         {"ADV"},          # never
    "ninguno":       {"PRON"},          # no N
    "ni":      {"PRON", "DET"},   # particularly
}


negative_predicates = {
    # verbs
    "dudo",   # doubt
    "negar",      # deny
    "disputar",   # deny/dispute
    "evitar",    # avoid
    "rechazar",     # reject/refuse
    "rehusar",   # refuse
    "impedir",   # prevent
    "prohibido",    # prohibit
    "excluir", # exclude
    "dudar",   # (dup ok, set dedupes)
    "fracasar",    # fail
    "vacilar",       # hesitate
    "negarse",      # refuse (sich weigern)
    "faltar",       # lack / be absent
    "desmentir",   # deny
    "denegar",
    "prevenir"
    "carecer"
    # adjectives
    "imposible",    # impossible
    "improbable", # unlikely

}


extra_licensors = {
    frozenset({"sin"}): ("without_pp_licensor", 2), 
    frozenset({"antes"}): ("before_licensor", 2), 

}



# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
config = LanguageConfig(
    language="Spanish",
    npi_upos={"PRON", "ADV", "DET"},   
    npi_environments={
        "neg", "without_pp_licensor", "question",
         "negated_matrix_clause"
    },
    npi_lemmas=npi_lemma_upos,
    neg_lemmas={"no"},                  
    conditional_markers={"si"},         
    comparative_markers={"que"},        
    extra_licensors=extra_licensors,
    interclause_licensor={"neg", "n_series", "without_pp_licensor"},
    threshold=0.00,
    min_freq=10,
    max_sent_len=60,
    negative_predicates=negative_predicates,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"no"},
            action=Drop({"no"}), check="neg",
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"solo", "sólo", "solamente"},
            action=Swap({"solo": "realmente", "sólo": "realmente", "solamente": "realmente"}),check="neg",
        ),
    ]
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}"
    )