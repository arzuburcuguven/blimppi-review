from src.blimppi.pipeline import run_pipeline, save_output, LanguageConfig
from src.blimppi.modifiers import Drop, Swap, ConditionalRule

from src.config.paths import UD, FINAL_PAIRS



n_series = {"ingen", "ingenting", "indet", "ingenstans", "aldrig"}


npi_lemma_upos = {
    "någonsin": {"ADV"},   
    "alls":     {"ADV"},
    "ens":      {"ADV"},
    "heller":   {"ADV"},
    "förrän":   {"ADV", "SCONJ"},   
}
extra_licensors = {
    frozenset({"utan", }): ("without_pp_licensor", 2),
    frozenset({"bara"}):             ("DE_licensor", 3),
    frozenset({"varken", "knappast"}):           ("DE_licensor", 2),
    frozenset({"få"}):               ("DE_licensor", 2),
}


comparative_markers = {"än"}
conditional_markers = {"om"}


ingen_to_indefinite_map = {
    "ingen":      "någon",
    "ingenting":  "någonting",
    "intet":      "något",
    "ingenstans": "någonstans",
    "få":         "några",
    "inga":       "några",
}


config = LanguageConfig(
    language="Swedish",
    npi_upos={"PRON", "ADV", "DET"},
    npi_environments={
        "neg", "comparative", "conditional", "question",
        "extra_licensor", "n_series_neg", "DE_licensor", "aux_inversion", "without_pp_licensor", "superlative"
    },
    npi_lemmas=npi_lemma_upos,
    neg_lemmas={"inte", "ej", "icke"},
    n_series=n_series,
    exclude_lemmas={"än", "knappast", "varför", "överens"},
    conditional_markers=conditional_markers,
    comparative_markers=comparative_markers,
    extra_licensors=extra_licensors,
    interclause_licensor={"neg", "n_series_neg", "is_varken"},
    threshold=0.00,
    min_freq=5,
    max_sent_len=40,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"inte", "icke", "ej"},
            action=Drop({"inte", "icke", "ej"}),  check="neg"
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in n_series | {"få"},
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