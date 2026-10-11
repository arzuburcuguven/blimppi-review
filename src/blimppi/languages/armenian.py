from blimppi.pipeline import run_pipeline, save_output, LanguageConfig, tokens_to_string
from blimppi.modifiers import ConditionalRule
from src.config.paths import UD, FINAL_PAIRS

# ---- de-negation: auxiliary paradigm map (covers ~440 of ~470 AUX negations) ----
ARM_AUX_DENEG = {
    "չեմ": "եմ", "չես": "ես", "չի": "է", "չենք": "ենք", "չեք": "եք", "չեն": "են",
    "չէի": "էի", "չէիր": "էիր", "չէր": "էր", "չէինք": "էինք", "չէիք": "էիք", "չէին": "էին",
    "չէ": "է",
}

class ArmenianDeNegate:
    """Build the ungrammatical member by removing verbal negation.
       (A) negated AUX -> positive via paradigm map
       (B) prefixed synthetic VERB -> strip leading չ
    """
    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        neg_tok = token_dict.get(neg_id)
        if not neg_tok:
            return None, None, "condition_not_met"
        form = neg_tok["form"]
        low = form.lower()

        if low in ARM_AUX_DENEG:                      # case A
            pos = ARM_AUX_DENEG[low]
            new_form = pos.capitalize() if form[:1].isupper() else pos
        elif low.startswith("չ") and (neg_tok["feats"] or {}).get("Polarity") == "Neg":  # case B
            stripped = form[1:]
            new_form = stripped.capitalize() if form[:1].isupper() else stripped
        else:
            return None, None, "condition_not_met"

        # rebuild surface string with neg token's form replaced
        new_tokens = []
        for t in tree:
            if isinstance(t["id"], int) and t["id"] == neg_id:
                tt = dict(t); tt["form"] = new_form
                new_tokens.append(tt)
            else:
                new_tokens.append(t)
        modified_string = tokens_to_string(new_tokens)
        return new_tokens, modified_string, "success"

neg_lemmas = {"ոչ"}

npi_lemma_upos = {
    "ոչինչ": {"PRON"},
    "ոչ_ոք": {"PRON"},
    "ոչ_մի": {"DET"},
    "ոչ_մեկ": {"PRON", "DET"},
    "երբեք": {"ADV"},
}


config = LanguageConfig(
    language="Armenian",
    npi_lemmas=npi_lemma_upos,
    npi_environments={"neg"},
    neg_lemmas=neg_lemmas,
    threshold=0.00,
    min_freq=1,
    max_sent_len=60,
    bigrams = [
    ("ոչ", "ոք", "ոչ_ոք"),
    ("ոչ", "մի", "ոչ_մի"),
    ("ոչ", "մեկ", "ոչ_մեկ"),
],
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: (
                neg_tok.get("form","").lower() in ARM_AUX_DENEG
                or ((neg_tok.get("feats") or {}).get("Polarity") == "Neg"
                    and neg_tok.get("form","").lower().startswith("չ"))
            ),
            action=ArmenianDeNegate(), check="neg"
        ),
    ],

)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / "armenian")