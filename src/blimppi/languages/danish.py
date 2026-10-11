from src.blimppi.pipeline import run_pipeline, save_output, LanguageConfig
from src.blimppi.modifiers import Drop, Swap, ConditionalRule

from src.config.paths import UD, FINAL_PAIRS

# Danish NPIs from NuDansk Ordbog (Appel et al. 2002), as reported in Sten Vikner*
#Trees and Fields and Negative Polarity

n_series = {"ingen", "intet", "ingenting", "ingensteds", "aldrig"}

npi_lemma_upos = {
    "nogensinde":   {"ADV"},          
    "endnu":        {"ADV"},          
    "overhovedet":  {"ADV"},          # at all
    "synderlig":    {"ADV"},   # notably/particularly (inte synderligt)
    "nævneværdig":  {"ADJ", "ADV"},   # noteworthy (ikke nævneværdig)
    "døje":         {"VERB"},         # endure (kan ikke døje)
    "orke":         {"VERB"},         # be bothered to (orker ikke)
    "heller":       {"ADV"},          
    "noget_somhelst": {"DET"},        
    "spor":         {"NOUN", "ADV"}, 
    "fordrage":         {"PRON"}, 
    "det_mindste": {"ADJ", "DET"}, #least bit
    "nogetsteds": {"ADV"}, #nowhere
    "nogen_steder": {"DET"}, # no where?,
    "som_helst": {"ADP"},

}

# n-series -> indefinite counterpart (consumed by the Swap rule below).
# Must cover every key in n_series or the Swap silently no-ops.
ingen_to_indefinite_map = {
    "ingen":      "nogen",
    "intet":      "noget",
    "ingenting":  "noget",
    "ingensteds": "nogensteds",
    "aldrig":     "altid",
}

# DE predicates 
predicate_to_positive_map = {
    "tvivle":   "tror",      # doubt -> think
    "nægte":    "bekræfte",  # deny -> confirm
    "undgå":    "møde",      # avoid -> meet
    "afvise":   "acceptere", # reject -> accept
    "mangle":   "have",      # lack -> have
}

# DE adverbs
de_word_to_positive_map = {
    "næppe":   "let",   # hardly -> easily
    "knap":    "let",   # barely -> easily
    "sjældent": "ofte", # rarely -> often
    "uden": "med"
}

extra_licensors = {
    frozenset({"uden"}):           ("without_pp_licensor", 2),
    frozenset({"næppe", "knap", "sjældent"}):  ("DE_licensor", 3),
    frozenset({"hverken"}):        ("neg_coord_licensor", 2),  # neither...nor (cf. Swedish varken)
    frozenset({"få"}):             ("DE_licensor", 2),
}

comparative_markers = {"end"}
conditional_markers = {"hvis", "om"}

config = LanguageConfig(
    language="Danish",
    npi_upos={"PRON", "ADV", "DET", "ADJ", "NOUN", "VERB"},  
    npi_environments={
        "neg", "comparative", "conditional", "question",
        "n_series_neg", "is_få", "neg_coord_licensor",
        "aux_inversion", "DE_licensor", "without_pp_licensor", "neg_predicate",
    },
    npi_lemma_upos=npi_lemma_upos,
    neg_lemmas={"ikke", "ej"},
    n_series=n_series,
    negative_predicates=set(predicate_to_positive_map),
    conditional_markers=conditional_markers,
    comparative_markers=comparative_markers,
    extra_licensors=extra_licensors,
    interclause_licensor={"neg", "n_series_neg", "nrg_coorg_licensor"},
    threshold=0.00,
    min_freq=1,
    max_sent_len=60,
    bigrams=[("nogen", "steder","nogen_steder"), ("nogen", "somhelst", "noget_somhelst"), ("som", "helst", "som_helst")],
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"ikke", "ej", "hverken"},
            action=Drop({"ikke", "ej", "hverken"}), check="neg",
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in n_series | {"få"},
            action=Swap(ingen_to_indefinite_map), check="neg",
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in set(predicate_to_positive_map) | set(de_word_to_positive_map),
            action=Swap(predicate_to_positive_map | de_word_to_positive_map), check="neg",
        ),
    ],
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}",
    )