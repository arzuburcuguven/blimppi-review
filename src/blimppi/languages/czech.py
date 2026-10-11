from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig, tokens_to_string
)
from src.blimppi.modifiers import ConditionalRule

import copy


from src.config.paths import UD, FINAL_PAIRS

extra_licensors = {
    frozenset({"bez"}): ("without_pp_licensor",1),
    frozenset({"aniž"}): ("neg_coord_licensor",1)
}


class CzechDeNegateVerb:
    """Strip ne- prefix from negated verb. Special case: není -> je."""
    IRREGULAR = {"není": "je"}

    def __call__(self, tree, token_dict,  neg_id, npi_id=None):
        int_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], int)]
        range_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], tuple)]
        token_dict_copy = {t["id"]: t for t in int_tokens}

        neg_token = token_dict_copy.get(neg_id)
        if neg_token is None:
            return None, None, "no_neg_token"

        form = neg_token["form"]
        if form.lower() in self.IRREGULAR:
            pos_form = self.IRREGULAR[form.lower()]
            if form[0].isupper():
                pos_form = pos_form.capitalize()
        elif form.lower().startswith("ne"):
            pos_form = form[2:]
            if form[0].isupper():
                pos_form = pos_form.capitalize()
        else:
            return None, None, "no_ne_prefix"

        modified_int = []
        for t in int_tokens:
            if t["id"] == neg_id:
                t["form"] = pos_form
                if t.get("feats"):
                    t["feats"]["Polarity"] = "Pos"
            modified_int.append(t)

        modified_tree = modified_int + range_tokens
        return modified_tree, tokens_to_string(modified_tree), "success"


config = LanguageConfig(
    language="Czech",
    npi_upos={"PRON", "ADV", "DET"},
    extra_licensors=extra_licensors,
    npi_environments={"neg", "negated_matrix_clause", "neg_coord_licensor", "without_pp_licensor"},
    neg_lemmas={"ne"},
    exclude_lemmas={"dokud"},
    threshold=0.70,
    max_sent_len=30,
    inflector=CzechDeNegateVerb(),
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: (neg_tok.get("feats") or {}).get("Polarity") == "Neg",
            action=CzechDeNegateVerb(), check= "neg"
        ),
    ],
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")