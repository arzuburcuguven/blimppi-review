from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Drop, Swap, DropAndFixGenitive, ConditionalRule
from src.blimppi.base_detectors import get_clause_head_id

from src.multiblimp.unimorph import UnimorphInflector

import csv

from src.config.paths import UD, FINAL_PAIRS, RESOURCES

VERB_CLASSIFICATIONS_PATH = RESOURCES / "verb_classifications" / "verb_classifications_slovenian.csv"




biti_neg_to_pos = {
    "nisem": "sem",   # 1sg
    "nisi":  "si",    # 2sg
    "ni":    "je",    # 3sg  
    "nisva": "sva",   # 1du
    "nista": "sta",   # 2/3du
    "nismo": "smo",   # 1pl
    "niste": "ste",   # 2pl
    "niso":  "so",    # 3pl
}

neg_lemmas = {"ne"} | biti_neg_to_pos.keys()

extra_licensors = {
    frozenset({"brez"}): ("without_pp_licensor", 2),
}

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

INHERENTLY_GENITIVE_VERBS_SL = load_inherently_genitive_verbs(VERB_CLASSIFICATIONS_PATH)

def is_transitive(clause_head_id, token_dict):
    for tid, token in token_dict.items():
        if token["deprel"].startswith("obj"):
            return True
    return False


obj_inflector_sl = UnimorphInflector(
    langcode="Slovenian",
    inflection_map=("Case", {"Gen": "Acc"}),
    resource_dir=RESOURCES,
    filter_entries={"upos": ["N", "PRON", "ADJ", "DET"]},
    combine_um_ud=True
)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

config = LanguageConfig(
    language="Slovenian",
    npi_upos={"PRON", "ADV", "DET"},
    npi_environments={"neg", "without_pp_licensor"},
    neg_lemmas=neg_lemmas,
    extra_licensors=extra_licensors,
    interclause_licensor={"neg","without_pp_licensor"},
    skip_pair_environments={"question"},
    threshold=0.70,
    min_freq=5,
    max_sent_len=50,
    inflector=obj_inflector_sl,
    removal_rules=[
        ConditionalRule(
            condition=lambda tok, td: (
                tok.get("lemma") == "ne"
                and not is_transitive(get_clause_head_id(tok["id"], td), td)
            ),
            action=Drop({"ne"}), check="neg"
        ),
        ConditionalRule(
            condition=lambda tok, td: (
                tok.get("lemma") in biti_neg_to_pos.keys()
                and not is_transitive(get_clause_head_id(tok["id"], td), td)
            ),
            action=Swap(biti_neg_to_pos), check="neg"
        ),
        ConditionalRule(
            condition=lambda tok, td: (
                tok.get("lemma") == "ne"
                and is_transitive(get_clause_head_id(tok["id"], td), td)
            ),
            action=DropAndFixGenitive(
                lemmas={"ne"},
                neg_induced_verbs=INHERENTLY_GENITIVE_VERBS_SL,
                obj_inflector=obj_inflector_sl,
            ), check="neg"
        ),
    ],
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")