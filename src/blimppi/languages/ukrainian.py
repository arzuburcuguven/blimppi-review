from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Drop, DropAndFixGenitive, ConditionalRule
from src.blimppi.base_detectors import get_clause_head_id
from src.multiblimp.unimorph import UnimorphInflector

import csv


from src.config.paths import UD, FINAL_PAIRS, RESOURCES

VERB_CLASSIFICATIONS_PATH = RESOURCES / "verb_classifications" / "verb_classifications_ukrainian.csv"


# ---------------------------------------------------------------------------
# LOAD VERB CLASSIFICATIONS
# ---------------------------------------------------------------------------

def load_inherently_genitive_verbs(path):
    inherently_genitive = set()
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            print(f"[DEBUG] Total rows in CSV: {len(rows)}")
            print(f"[DEBUG] Labels found: {set(r['label'] for r in rows)}")
            for row in rows:
                if row["label"] == "inherently_genitive":
                    inherently_genitive.add(row["verb"])
        print(f"[INFO] Loaded {len(inherently_genitive)} negation-induced verbs from {path}")
    except FileNotFoundError:
        print(f"[WARN] Verb classifications file not found: {path}")
    except KeyError as e:
        print(f"[ERROR] Missing column in CSV: {e} — columns are: {rows[0].keys() if rows else 'empty'}")
    return inherently_genitive

INHERENTLY_GENITIVE_VERBS_UK = load_inherently_genitive_verbs(VERB_CLASSIFICATIONS_PATH)



# ---------------------------------------------------------------------------
# SKIP TRANSITIVE
# ---------------------------------------------------------------------------

def is_transitive(clause_head_id, token_dict):
    for tid, token in token_dict.items():
        if token["deprel"].startswith("obj"):
            return True
    return False

extra_licensors = {
    frozenset({"без"}): ("without_pp_licensor", 2),
}





# ---------------------------------------------------------------------------
# INFLECTORS
# ---------------------------------------------------------------------------

obj_inflector_uk = UnimorphInflector(
    langcode="ukr",
    inflection_map=("Case", {"Gen": "Acc"}),
    resource_dir=RESOURCES,
    filter_entries={"upos": ["N", "PRON", "ADJ", "DET"]},
    combine_um_ud=True
)

verb_inflector_uk = UnimorphInflector(
    langcode="ukr",
    inflection_map=("Polarity", {"NEG": "POS"}),
    resource_dir=RESOURCES,
    filter_entries={"upos": ["V"]},
    combine_um_ud=True
)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

config = LanguageConfig(
    language="Ukrainian",
    npi_upos={"PRON", "ADV", "DET"},
    skip_pair_environments={"question", "comparative", "conditional"},
    npi_environments={"neg", "without_pp_licensor"},
    neg_lemmas={"не"},
    threshold=0.60,
    max_sent_len=50,
    min_freq=17,
    comparative_markers={"ніж", "аніж"},
    conditional_markers={"якщо", "якби", "коли", "раз"},
    extra_licensors=extra_licensors,
    inflector=verb_inflector_uk,
    removal_rules=[
        ConditionalRule(
            condition=lambda tok, td: (
                tok.get("lemma") == "не"
                and not is_transitive(get_clause_head_id(tok["id"], td), td)
            ),
            action=Drop({"не"}),  check="neg"
        ),
        ConditionalRule(
            condition=lambda tok, td: (
                tok.get("lemma") == "не"
                and is_transitive(get_clause_head_id(tok["id"], td), td)
            ),
            action=DropAndFixGenitive(
                lemmas={"не"},
                neg_induced_verbs=INHERENTLY_GENITIVE_VERBS_UK,
                obj_inflector=obj_inflector_uk,
            ),  check="neg"
        ),
    ]
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")