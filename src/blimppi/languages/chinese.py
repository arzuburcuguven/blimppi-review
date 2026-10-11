# Mandarin Chinese NPI config
# 任何 (renhe) "any" — DET; licensed by neg, conditional, modals, want-verbs
# 什么 (shenme) "what" — PRON; NPI in non-interrogative contexts (Lin 1998, Li 1992)
# Negative Polarity Items in Chinese   Bo Xue, Haihua Pan

from blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from blimppi.modifiers import Drop, ConditionalRule
from src.config.paths import UD, FINAL_PAIRS


neg_lemmas = {"没",   # mei — sentential negation (没/没有)
              "没有",
              "不",   # bu
              "别", ## dont
              "莫" # old fashined neg
              }

npi_lemmas = {"任何",   # renhe — any (DET)
              "什么",   # shenme — what / NPI (PRON)
              "谁",     # shei — who / NPI (PRON)
              "怎么",   # zenme — how / wh-NPI (ADV)
              "多少",   # duoshao — how much/many / wh-NPI (ADV/DET)
              "从来",   # conglai — ever/never (ADV, strong NPI)
              "根本",   # genben — at all (ADV, strong NPI)
              }

# this is for counting the occurances as well, modal wont be used for pairs
NPI_ALLOWED_ENVS = {
    "什么": {"neg", "want_licensor", "neg_predicate", "epistemic_licensor", "conditional", "question", "modal_licensor"},  # shenme
    "谁":   {"neg", "want_licensor", "neg_predicate", "epistemic_licensor", "conditional", "question", "modal_licensor"},  # shei
    "怎么": {"neg", "want_licensor", "neg_predicate", "epistemic_licensor", "conditional", "question", "modal_licensor"},  # zenme
    "多少": {"neg", "want_licensor", "neg_predicate", "epistemic_licensor", "conditional", "question", "modal_licensor"},  # duoshao
    "任何": {"neg", "want_licensor", "modal_licensor", "conditional"},                                    # renhe
    "从来": {"neg"},   # conglai — negation only
    "根本": {"neg"},   # genben — negation only
    # lemmas left unset = no env restriction
}

extra_licensors = {
    frozenset({"想"}):   ("want_licensor", 2),       # xiang — want
    frozenset({"可以"}): ("modal_licensor",3),      # keyi — can
    frozenset({"认为"}): ("neg_predicate", 2),       # renwei — think
    frozenset({"可能"}): ("epistemic_licensor", 2),  # keneng — possibly
    frozenset({"好像"}): ("epistemic_licensor", 2),  # haoxiang — seem
    frozenset({"即使"}): ("conditional", 2),         # jishi — even if
    frozenset({"都"}):   ("dou_blocker", 1),         # dou — all (blocks licensing)
}
config = LanguageConfig(
    language="Chinese",
    npi_upos={"PRON", "DET", "ADV"},
    npi_environments={"neg", "conditional", "question",
         "neg_predicate", "modal_licensor", "epistemic_licensor", "want_licensor"},
        
    neg_lemmas=neg_lemmas,
    exclude_lemmas=set(),
    npi_lemmas=npi_lemmas,
    npi_allowed_envs = NPI_ALLOWED_ENVS,     
    conditional_markers={"如果", "即使"},   # ruguo, jishi
    skip_pair_environments={"dou_blocker", "modal_licensor"},
    extra_licensors=extra_licensors,
    negative_predicates=set(),
    interclause_licensor={"neg", "neg_predicate"},
    threshold=0.40,
    min_freq=10,
    max_sent_len=75,
    bigrams=[],
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"没", "没有", "不"},
            action=Drop({"没", "没有", "不"}), check="neg"  # mei / bu — sentential negation
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"想"},
            action=Drop({"想"}),      check="neg"         # xiang — want
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"可以"},
            action=Drop({"可以"}),       check="neg"      # keyi — can
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"可能"},
            action=Drop({"可能"}),     check="neg"        # keneng — possibly
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"好像"},
            action=Drop({"好像"}),     check="neg"        # haoxiang — seem
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"如果"},
            action=Drop({"如果"}),     check="neg"        # ruguo — if
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"即使"},
            action=Drop({"即使"}),    check="neg"         # jishi — even if
        ),
    ]
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")