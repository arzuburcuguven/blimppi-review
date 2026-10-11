from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Drop, LemmaSwapInflect, ConditionalRule

from src.multiblimp.unimorph import UnimorphInflector
from src.config.paths import UD, FINAL_PAIRS, RESOURCES

verb_inflector_hu = UnimorphInflector(
    langcode="hun",
    resource_dir=RESOURCES,
    inflection_map=(None, None),
    filter_entries={"upos": ["V"]},
    combine_um_ud=True,
)


nincs_to_van_map = {
    "nincs":  "van",       
    "sincs":  "van",
}

config = LanguageConfig(
    language="Hungarian",
    npi_environments={"neg", "negated_matrix_clause"},
    skip_pair_environments={
        "question", "conditional",
    },
    npi_lemmas={"semmi", "soha", "senki", "semmilyen", "sehol", "semmikor", "sehogyan", "sehány", "semennyi"},
    npi_upos={"ADV", "PRON", "DET", "ADJ"},
    neg_lemmas={"nem", "ne", "nincs", "sincs", "se", "sem"},
    conditional_markers={("ha", "hogyha")},
    threshold=0.00,
    min_freq=0,
    max_sent_len=40,
    inflector=verb_inflector_hu,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"nem", "ne", "sem"},
            action=Drop({"nem", "ne", "sem"}), check="neg"
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in nincs_to_van_map,
            action=LemmaSwapInflect(
                verb_inflector_hu,
                nincs_to_van_map,
                feature_updates={"Polarity": "Pos"},
            ), check="neg"
        ),
    ]
)


if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}"
    )