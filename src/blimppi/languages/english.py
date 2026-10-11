from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Drop, Swap, ConditionalRule, find_subject_aux_inversion, UninvertAux


from src.config.paths import UD, FINAL_PAIRS

MODAL_LEMMAS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would"}

extra_licensors = {
    frozenset({"without"}): ("without_pp_licensor", 2),
    frozenset({"only"}): ("DE_licensor", 1),
    frozenset({"seldom", "hardly", "before", "few", "rarely", "before", "whether" }): ("DE_licensor", 2),
    frozenset(MODAL_LEMMAS): ("modal_licensor", 1),
}

##### picked from Cristian Danescu-Niculescu-Mizil (2009)

negative_predicates = {
    "doubt",
    "sorry",
    "deny",
    "avoid",
    "decline",
    "discourage",
    "exclude",
    "fail",
    "deter",
    "dismiss",
    "lack",
    "oppose",
    "prevent",
    "prohibit",
    "reject",
    "refuse",
    "resist",
    "minimize",
    "eliminate",
    "veto",
    "thwart",
    "suspend",
    "impossible",
    "unlikely",
    "unaware",
    "unable",
    "unwilling",
    "unclear",
    "skeptical",
    "absent",
    # DE nouns
    "absence",
    "refusal",
}
 
#no series as negation envrionment, from Haspelmath

no_lemmas = {"nobody", #nobody
                "nothing", #nothing
                "nowhere", #nowhere
                "no",
                "never",
                "none",
                "neither"
                }



# ---------------------------------------------------------------------------
# Swap maps
# ---------------------------------------------------------------------------

n_to_indefinite_map = {
    "nobody": "somebody",
    "nothing": "something",
    "nowhere": "somewhere",
    "none": "some",
    "no": "some",
    "doubt":   "think",
    "deny":    "confirm",
    "cannot":  "can",
    "unable":  "able",
    "hardly":  "easily",
    "rarely":  "often",
    "seldom":  "often",
    "doubt":     "think",
    "deny":      "confirm",
    "avoid":     "enjoy",
    "oppose":    "support",
    "reject":    "accept",
    "dismiss":   "accept",
    "resist":    "accept",
    "minimize":  "maximize",
    "eliminate": "retain",
    "veto":      "approve",
    "thwart":    "enable",
    "suspend":   "resume",
    "lack":      "support",
    "refuse":    "agree",
    "decline":   "agree",
    "impossible": "possible",
    "unlikely":   "likely",
    "unaware":    "aware",
    "unable":     "able",
    "unwilling":  "willing",
    "unclear":    "clear",
    "skeptical":  "convinced",
    "absent":     "present",
    "hardly":  "easily",
    "barely":  "easily",
    "rarely":  "often",
    "seldom":  "often",
    "absence": "presence",
    "refusal": "agreement",
}

NPI_ALLOWED_ENVS = {
    "ever":       {"neg", "n_series_neg", "question", "aux_inversion", "conditional",
                   "comparative", "superlative", "DE_licensor", "neg_predicate",
                   "without_pp_licensor", "neg_coord_licensor", "negated_matrix_clause"},
    "at_all":     {"neg", "n_series_neg", "question", "aux_inversion", "conditional",
                   "DE_licensor", "neg_predicate", "without_pp_licensor",
                   "neg_coord_licensor", "negated_matrix_clause"},

    "anything":   {"neg", "n_series_neg", "question", "aux_inversion", "conditional",
                   "comparative", "DE_licensor", "neg_predicate",
                   "without_pp_licensor", "neg_coord_licensor", "modal_licensor", "negated_matrix_clause"},
    "anywhere":   {"neg", "n_series_neg", "question", "aux_inversion", "conditional",
                   "comparative", "DE_licensor", "neg_predicate",
                   "without_pp_licensor", "neg_coord_licensor", "modal_licensor", "negated_matrix_clause"},

    "yet":        {"neg", "n_series_neg", "question", "aux_inversion", "neg_predicate"},
    "anymore":    {"neg", "n_series_neg", "question", "aux_inversion", "neg_predicate"},

    "whatsoever": {"neg", "n_series_neg", "without_pp_licensor", "neg_coord_licensor", "neg_predicate"},
    "either":     {"neg", "n_series_neg", "neg_coord_licensor", "negated_matrix_clause"},
    "in_years":   {"neg", "n_series_neg", "negated_matrix_clause", "negated_matrix_clause"},
    "in_ages":    {"neg", "n_series_neg", "negated_matrix_clause"},
    "one_bit":    {"neg", "n_series_neg", "negated_matrix_clause"},
}

npi_lemma_upos = {
    "ever":     {"ADV"},
    "yet":      {"ADV"},
    "anymore":  {"ADV"},
    "either":   {"ADV"},          # ADV only — blocks DET "either book" / CCONJ "either…or"
    "anything": {"PRON"},
    "anywhere": {"ADV"},
    "whatsoever": {"ADV"},
    "at_all":   {"ADV", "ADP", "DET"},
    "in_years":  {"ADV", "DET", "PRON", "ADP"},
    "in_ages": {"ADV", "DET", "PRON", "ADP"},      
}
 

def without_takes_np(neg_tok, td):
    # 'without' as case on an NP → safe to swap to 'with'
    # 'without' as mark on a gerund → breaks ('with seeing X'), skip
    #  Pointed out by Christian Hardmeier
    return (neg_tok.get("deprel") or "").split(":")[0] == "case"



# ---------------------------------------------------------------------------

config = LanguageConfig(
    language="English",
    npi_upos={"PRON", "ADV", "DET"},
    npi_environments={"neg", "n_series_neg", "comparative", "conditional", "question", 
           "DE_licensor", "without_pp_licensor", "neg_predicate", "superlative", "neg_coord_licensor", "aux_inversion"},
    neg_lemmas= {"not"},
    exclude_lemmas={"any", "anyone", "anybody"},
    n_series = no_lemmas,
    npi_lemma_upos= npi_lemma_upos,
    npi_allowed_envs = NPI_ALLOWED_ENVS,     
    conditional_markers =  {"if", "whether"},
    comparative_markers =  {"than", "better", "harder", "worse", "best", "biggest", "highest", "largest", "longest", "lowest", "smallest"}, ### added common superlatives as  fallback
    extra_licensors=extra_licensors,
    negative_predicates=negative_predicates,
    interclause_licensor = {"neg", "without_pp_licensor", "n_series_neg", "neg_coord_licensor"},
    threshold=0.00,
    min_freq=0,
    neg_coord = {
    "paired":  {"initial": {"neither"}, "linker": {"nor"}, "min_markers": 2},
},
    max_sent_len=60,
    bigrams=[
        ("in", "year", "in_years"),
        ("at", "all", "at_all"),
        ("in", "age", "in_ages"),
        ("one", "bit", "one_bit"),
    ],
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"not"},
            action=Drop({"not"}), check="neg"
        ),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in n_to_indefinite_map,
            action=Swap(
                n_to_indefinite_map,
            ), check="neg"),
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in {"only"},
            action=Drop(
                {"only"}
            ), check="neg"),
            ConditionalRule(
                condition=lambda neg_tok, td: neg_tok.get("lemma") == "without"
                                            and without_takes_np(neg_tok, td),
                action=Swap({"without": "with"}),
                check="neg",
            ),
            ConditionalRule(
                condition=lambda neg_tok, td: find_subject_aux_inversion(
                neg_tok.get("clause_head_id", neg_tok.get("id")), td
                ) is not None,
                 action=UninvertAux(), check="neg",
    ),
    ]
)


if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}"
    )
