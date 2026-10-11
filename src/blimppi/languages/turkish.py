from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Swap, Inflect, ConditionalRule
from src.multiblimp.unimorph import UnimorphInflector

from src.config.paths import UD, FINAL_PAIRS, RESOURCES



# "ne X ne Y" = neither-nor: ne hiç birşey yedi ne hiç birşey içti
def has_ne_ne_coordination(clause_head_id, token_dict):
    clause_tokens = {tid for tid, t in token_dict.items() if t["head"] == clause_head_id}
    clause_tokens.update({tid for tid, t in token_dict.items() if t["head"] in clause_tokens})
    clause_tokens.add(clause_head_id)
    ne_count = sum(
        1 for t in token_dict.values()
        if t["lemma"] == "ne" and t["upos"] == "CCONJ" and t["head"] in clause_tokens
    )
    if ne_count >= 2:
        return ("neg", clause_head_id)
    return (None, None)


bigrams_tr = [
    ("hiç", "kimse", "hiç_kimse"),  
]

inflector = UnimorphInflector(
    langcode="tur",
    inflection_map=("Polarity", {"NEG": "POS"}),
    resource_dir=RESOURCES,
    filter_entries={"upos": ["V"]},
    combine_um_ud=True,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

config = LanguageConfig(
    language="Turkish",
    npi_upos={"PRON", "ADV", "DET"},
    npi_environments={"neg", "question"},
    skip_pair_environments={"question"},
    extra_detectors=[has_ne_ne_coordination],
    inflector=inflector,
    neg_lemmas={"yok", "değil"},
    exclude_lemmas={"kolay"},
    threshold=0.60,
    min_freq=20,
    max_sent_len=50,
    bigrams= bigrams_tr,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: (
                neg_tok.get("lemma") == "yok" and
                any(t["head"] == neg_tok["id"] and t["deprel"] == "cop" for t in td.values())
            ),
            action=lambda tree, token_dict, neg_id, npi_id=None: (None, None, "skip_yok_cop"), check="neg"
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") == "yok",
            action=Swap({"yok": "var", "yoktu": "vardı", "yokmuş": "varmış", "yoktur": "vardır"}), check="neg"
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") == "değil",
            action=lambda tree, token_dict, neg_id, npi_id=None: (None, None, "skip_degil"), check="neg"
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: (neg_tok.get("feats") or {}).get("Polarity") == "Neg",
            action=Inflect(inflector, default_features={"VerbForm": "Fin"}), check="neg"
        ),
    ],
)


if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}"
    )