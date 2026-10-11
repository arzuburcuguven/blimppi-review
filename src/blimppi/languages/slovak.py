from src.blimppi.pipeline import run_pipeline, save_output, LanguageConfig, tokens_to_string
from src.blimppi.modifiers import ConditionalRule
import copy

from src.config.paths import UD, FINAL_PAIRS

class SlovakDeNegateVerb:

    IRREGULAR = {"niet": "je", "nieto": "je"}   # existential 'there is no' -> positive
    def __call__(self, tree, token_dict, neg_id, npi_id=None):
        int_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], int)]
        range_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], tuple)]
        token_dict_copy = {t["id"]: t for t in int_tokens}
        neg_token = token_dict_copy.get(neg_id)
        if neg_token is None:
            return None, None, "no_neg_token"
        form = neg_token["form"]
        low = form.lower()
        if low in self.IRREGULAR:
            pos_form = self.IRREGULAR[low]
        elif low.startswith("ne"):
            pos_form = form[2:]
        else:
            return None, None, "no_ne_prefix"
        if form[:1].isupper():
            pos_form = pos_form.capitalize()
        modified_int = []
        for t in int_tokens:
            if t["id"] == neg_id:
                t["form"] = pos_form
                if t.get("feats"):
                    t["feats"]["Polarity"] = "Pos"
            modified_int.append(t)         # <-- note: append ALL tokens, not only the match
        modified_tree = modified_int + range_tokens
        return modified_tree, tokens_to_string(modified_tree), "success"


config = LanguageConfig(
    language="Slovak",
    npi_environments={"neg"},
    threshold=0.73,
    min_freq=6,
    max_sent_len=60,
    inflector=SlovakDeNegateVerb,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: (neg_tok.get("feats") or {}).get("Polarity") == "Neg",
            action=SlovakDeNegateVerb(), check= "neg"
        ),
    ],
)


if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")