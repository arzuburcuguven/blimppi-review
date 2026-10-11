from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Inflect, ConditionalRule
from src.multiblimp.unimorph import UnimorphInflector

from src.config.paths import UD, FINAL_PAIRS, RESOURCES

inflector = UnimorphInflector(
    langcode="fas",
    inflection_map=("Polarity", None),
    resource_dir=RESOURCES,
    filter_entries={"upos": ["V"]},
    combine_um_ud=True
    )


config = LanguageConfig(
    language="Persian",
    npi_upos={"PRON", "ADV", "DET"},
    npi_environments={"neg"},
    exclude_lemmas={"اصلاً", "لزوماً"},
    bad_modified_substrings={"می‌توانی"},
    bad_modified_regexes=[r"می‌\S+ بود"],    
    threshold=0.60,
    max_sent_len=40,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: (neg_tok.get("feats") or {}).get("Polarity") == "Neg",
            action=Inflect(inflector), check="neg"
        ),
    ],
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config,
        FINAL_PAIRS / f"{config.lang.lower()}")