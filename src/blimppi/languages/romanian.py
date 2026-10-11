from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import ContractedDrop, ConditionalRule
from src.multiblimp.unimorph import UnimorphInflector

from src.config.paths import UD, FINAL_PAIRS, RESOURCES

# nu numai ... ci și conj: not only but also

extra_licensors = {
    frozenset({"fără"}): ("without_pp_licensor", 2),
}


inflector = UnimorphInflector(
    langcode="ron",
    inflection_map=("Variant", None),
    resource_dir=RESOURCES,
    combine_um_ud=True,
)


# --------------------------------------- Config -------------------------------------------------

config = LanguageConfig(
    language="Romanian",
    npi_upos= {"PRON", "ADV", "DET"},
    npi_lemmas={"vreun", "nimeni", "nici","niciodată", "nimic", "nici_un", "deloc"},
    npi_environments={"neg", "without_pp_licensor"},
    neg_lemmas={"nu"},
    comparative_markers={"decât"},
    conditional_markers={"dacă", "de"},
    extra_licensors=extra_licensors,
    min_freq=0,
    threshold=0.00,
    max_sent_len=50,
    inflector=inflector,
    bigrams=[
        ("nici", "un", "nici_un"),
    ],
    removal_rules=[
    ConditionalRule(
        condition=lambda neg_tok, td: neg_tok.get("lemma") == "nu",
        action=ContractedDrop({"nu"}, inflector), check="neg"
    ),
]
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")

