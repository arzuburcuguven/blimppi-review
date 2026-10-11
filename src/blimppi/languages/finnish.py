from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import LemmaSwapInflect, ConditionalRule

from src.multiblimp.unimorph import UnimorphInflector

from src.config.paths import UD, FINAL_PAIRS, RESOURCES


# -kO clitic question detector (Finnish yes/no questions). Same signature as
# every other extra_detector: (clause_head_id, token_dict) -> (env, nid).
def kO_question_detector(clause_head_id, token_dict):
    head = token_dict.get(clause_head_id)
    if head and (head.get("feats") or {}).get("Clitic") in ("Ko", "KO"):
        return ("question", None)
    return (None, None)


npi_to_indefinite_map = {
    "kukaan":       "joku",
    "mikään":       "jokin",
    "missään":      "jossakin",
    "milloinkaan":  "joskus",
    "mitenkään":    "jotenkin",
    "kumpikaan":    "jompikumpi",
}
indefinite_to_npi_map = {v: k for k, v in npi_to_indefinite_map.items()}
npi_to_indefinite_set = set(npi_to_indefinite_map.keys() | npi_to_indefinite_map.values())


inflector = UnimorphInflector(
    langcode="fin",
    inflection_map=(None, None),
    resource_dir=RESOURCES,
    filter_entries={"upos": ["PRON", "DET", "ADV"]},
    combine_um_ud=True,
)


config = LanguageConfig(
    language="Finnish",
    npi_upos={"PRON", "ADV", "DET"},
    npi_lemmas=npi_to_indefinite_set,
    neg_lemmas={"ei"},
    npi_environments={"neg", "negated_matrix_clause"},
    skip_pair_environments={"question"},
    extra_detectors=[kO_question_detector],
    direction_environments={
        "neg2ind": {"neg", "negated_matrix_clause"},
    },
    threshold=0.50,
    min_freq=5,
    max_sent_len=30,
    removal_rules=[
        ConditionalRule(
            condition=lambda tok, td: tok.get("lemma") in npi_to_indefinite_map,
            action=LemmaSwapInflect(
                inflector,
                npi_to_indefinite_map,
                feature_updates={"PronType": "Ind"},
                direction="neg2ind",
            ), check="npi"
        ),
    ],
)


if __name__ == "__main__":
    print("Checking inflector coverage:")
    for lemma in sorted(npi_to_indefinite_set):
        print(f"  {lemma}: {'✓' if lemma in inflector.unique_lemmas else '✗ MISSING'}")
    print()

    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")