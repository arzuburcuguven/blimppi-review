from blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from blimppi.modifiers import Drop, DropAndFixGenitive, ConditionalRule
from blimppi.base_detectors import get_clause_head_id

from src.multiblimp.unimorph import UnimorphInflector

import csv
from src.config.paths import UD, FINAL_PAIRS, RESOURCES


VERB_CLASSIFICATIONS_PATH = RESOURCES / "verb_classifications" / "verb_classifications_belarusian.csv"


extra_licensors = {
    frozenset({"без"}): ("without_pp_licensor", 2),
}



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

INHERENTLY_GENITIVE_VERBS_PL = load_inherently_genitive_verbs(VERB_CLASSIFICATIONS_PATH)

def is_transitive(clause_head_id, token_dict):
    for tid, token in token_dict.items():
        if token["deprel"].startswith("obj"):
            return True
    return False


obj_inflector_bl = UnimorphInflector(
    langcode="Belarusian",
    inflection_map=("Case", {"Gen": "Acc"}),
    resource_dir=RESOURCES,
    filter_entries={"upos": ["N", "PRON", "ADJ", "DET"]},
    combine_um_ud=True
)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

config = LanguageConfig(
    language="Belarusian",
    npi_upos={"PRON", "ADV", "DET"},
    #npi_lemmas=NPI_pl,
    npi_environments={"neg", "extra_licensor"},
    neg_lemmas={"не"},
    #conditional_markers=conditional_markers,
    #comparative_markers=comparative_markers,
    extra_licensors=extra_licensors,
    interclause_licensor={"neg", "extra_licensor"},
    skip_pair_environments={"question"},
    threshold=0.70,
    min_freq=5,
    max_sent_len=50,
    inflector=obj_inflector_bl,
    removal_rules=[
        ConditionalRule(
            condition=lambda tok, td: (
                tok.get("lemma") == "не"
                and not is_transitive(get_clause_head_id(tok["id"], td), td)
            ),
            action=Drop({"не"}), check="neg"
        ),
        ConditionalRule(
            condition=lambda tok, td: (
                tok.get("lemma") == "не"
                and is_transitive(get_clause_head_id(tok["id"], td), td)
            ),
            action=DropAndFixGenitive(
                lemmas={"не"},
                neg_induced_verbs=INHERENTLY_GENITIVE_VERBS_PL,
                obj_inflector=obj_inflector_bl,
            ), check="neg"
        ),
    ],
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / "belarusian")