from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import LemmaSwapInflect, ConditionalRule
from src.multiblimp.unimorph import UnimorphInflector
from src.config.paths import UD, FINAL_PAIRS, RESOURCES



# --------------------------------------- Config -------------------------------------------------


npi_to_indefinite_map = {
    "niekas":   "kažkas",    # nobody/nothing - someone/something
    "niekur":   "kažkur",    # nowhere - somewhere
    "niekada":  "kažkada",   # never - sometime
    "niekaip":  "kažkaip",   # in no way - somehow
    "joks":     "kažkoks",   # no (det.) - some (det.)
}

indefinite_to_npi_map = {v: k for k, v in npi_to_indefinite_map.items()}


npi_to_indefinite_set = set(npi_to_indefinite_map.keys() | npi_to_indefinite_map.values())

inflector = UnimorphInflector(
    langcode="lit",
    inflection_map=(None, None),
    resource_dir=RESOURCES,
    filter_entries={"upos": ["PRON", "DET", "ADV"]},
    combine_um_ud=True
)

config = LanguageConfig(
    language="Lithuanian",
    npi_upos= {"PRON", "DET", "ADV"},
    npi_lemmas=npi_to_indefinite_set,
    npi_environments={"neg", "affirmative"},
    skip_pair_environments={"question"},
    direction_environments={
        "neg2ind": {"neg","negated_matrix_clause" }, 
        "ind2neg": {"affirmative"},
        },
    threshold=0.50,
    min_freq=5,
    max_sent_len=50,
    removal_rules=[
        # Direction 1: NPI in negative env → swap to indef
        ConditionalRule(
            condition=lambda tok, td: tok.get("lemma") in npi_to_indefinite_map,
            action=LemmaSwapInflect(
                inflector,
                npi_to_indefinite_map,
                feature_updates={"PronType": "Ind"},
                direction="neg2ind",
            ), check="npi",
        ),
        ConditionalRule(
            condition=lambda tok, td: tok.get("lemma") in indefinite_to_npi_map,
            action=LemmaSwapInflect(
                inflector,
                indefinite_to_npi_map,
            feature_updates={"PronType": "Neg"},
            direction="ind2neg",
            ), check="npi",
        ),
]
)



if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")

    print("kažkas" in inflector.unique_lemmas)
    print("visada" in inflector.unique_lemmas)
    print("kažkur" in inflector.unique_lemmas)
    print("kažkaip" in inflector.unique_lemmas)