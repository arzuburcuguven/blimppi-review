from blimppi.pipeline import run_pipeline, save_output, LanguageConfig
from blimppi.modifiers import Drop, Swap, ConditionalRule

from config.paths import UD, FINAL_PAIRS
LANGS = ["Norwegian-Bokmaal", "Norwegian-Nynorsk"]

comparative_markers = {"enn"}
conditional_markers = {"hvis", "om", "dersom"}

predicate_to_positive_map = {
    "tvile":  "tror",       # doubt -> think
    "nekte":  "bekrefte",   # deny -> confirm
    "unngå":  "møte",       # avoid -> meet
    "avvise": "akseptere",  # reject -> accept
    "mangle": "ha",         # lack -> have
}
de_word_to_positive_map = {
    "neppe":   "lett",   # hardly -> easily
    "knapt":   "lett",   # barely -> easily
    "sjelden": "ofte",   # rarely -> often
}

npi_lemma_upos_shared = {
    "noensinne":   {"ADV"},          # ever — weakest, also OK in Q/conditional
    "overhodet":   {"ADV"},          # at all
    "heller":      {"ADV"},          # nor/either — negated clauses
    "ennå":        {"ADV"},          # yet
    "synderlig":   {"ADJ", "ADV"},   # particularly (ikke synderlig)
    "nevneverdig": {"ADJ", "ADV"},   # noteworthy (ikke nevneverdig)
    "spor":        {"NOUN", "ADV"},  # a trace/at all (ikke spor)

}

PARADIGMS = {
    "Norwegian-Bokmaal": {
        "neg_lemmas":  {"ikke", "ei"},
        "n_series":    {"ingen", "inga", "inget", "intet", "ingenting", "aldri"},
        "neither":     {"verken", "hverken"},
        "n_series_map": {
            "ingen": "noen", "inga": "noen",
            "inget": "noe",  "intet": "noe",
            "ingenting": "noe", "aldri": "alltid",
        },
    },
    "Norwegian-Nynorsk": {
        "neg_lemmas":  {"ikkje", "ei"},
        "n_series":    {"ingen", "inga", "inkje", "ingenting", "aldri"},
        "neither":     {"korkje", "verken"},
        "n_series_map": {
            "ingen": "nokon", "inga": "noka",
            "inkje": "noko",  "ingenting": "noko",
            "aldri": "alltid",
        },
    },
}


def make_config(language):
    p = PARADIGMS[language]
    neg_lemmas    = p["neg_lemmas"]
    n_series      = p["n_series"]
    n_series_map  = p["n_series_map"]
    npi_lemma_upos = {**npi_lemma_upos_shared}

    droppers = neg_lemmas | {"bare"} | p["neither"]

    extra_licensors = {
        frozenset({"uten"}):                              ("without_pp_licensor", 2),
        frozenset({"bare", "neppe", "knapt", "sjelden", "langtfra"}): ("DE_licensor", 3),
        frozenset(p["neither"]):                          ("is_verken", 2),
        frozenset({"få"}):                                ("is_få", 2),
        frozenset({"før"}):                               ("before_licensor", 2),  # was "føt" (typo)
    }

    return LanguageConfig(
        language=language,
        npi_upos={"PRON", "ADV", "DET", "ADJ", "NOUN", "VERB"},
        npi_environments={
            "neg", "comparative", "conditional", "question",
            "n_series_neg", "is_få", "is_verken",
            "aux_inversion", "DE_licensor", "without_pp_licensor", "neg_predicate",
        },
        npi_lemma_upos=npi_lemma_upos,
        neg_lemmas=neg_lemmas,
        n_series=n_series,
        negative_predicates=set(predicate_to_positive_map),
        conditional_markers=conditional_markers,
        comparative_markers=comparative_markers,
        extra_licensors=extra_licensors,
        interclause_licensor={"neg", "n_series_neg", "is_verken"},
        bigrams=[],
        exclude_lemmas={"enn", "hvorfor"},
        threshold=0.00,
        min_freq=0,
        max_sent_len=60,
        removal_rules=[
            ConditionalRule(
                condition=lambda neg_tok, td, dd=droppers: neg_tok.get("lemma") in dd,
                action=Drop(droppers),
                check="neg",
            ),
            ConditionalRule(
                condition=lambda neg_tok, td, ns=n_series: neg_tok.get("lemma") in ns | {"få"},
                action=Swap(n_series_map),
                check="neg",
            ),
            ConditionalRule(
                condition=lambda neg_tok, td: neg_tok.get("lemma") in set(predicate_to_positive_map) | set(de_word_to_positive_map),
                action=Swap(predicate_to_positive_map | de_word_to_positive_map),
                check="neg",
            ),
        ],
    )


if __name__ == "__main__":
    for language in LANGS:
        config = make_config(language)
        output = run_pipeline(config, UD)
        save_output(output, config,
                    FINAL_PAIRS / f"{config.lang.lower()}")
        print(f"done: {language}")