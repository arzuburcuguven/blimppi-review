from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig
)
from src.blimppi.modifiers import Drop, Swap, LemmaSwapInflect, ConditionalRule

from src.multiblimp.unimorph import UnimorphInflector

from src.config.paths import UD, FINAL_PAIRS, RESOURCES

#From Brauchen paper (Richer & Soehn, 2006) + NPI Bank (Buschbom, Dirk and Hohmann, Pascal and Lamoure, Nicolas and Richter, Frank and Sailer, Manfred)
npi_lemma_upos = {
    "jemals":          {"ADV"},          # ever
    "beileibe":        {"ADV"},          # by no means
    "geheuer":         {"ADJ"},          # uncanny (nicht geheuer)
    "überhaupt":       {"ADV"},          # at all
    "sonderlich":      {"ADV", "ADJ"},   # particularly
    "im_geringsten":   {"ADV", "ADJ"},          # in the slightest (bigram)
    "scheren":         {"VERB"},         # care (nicht scheren) — the paper's own example
    "Menschenseele": {"NOUN"}, # in cin
    "verdenken": {"VERB"},
    "gar": {"ADV"},
}

NPI_ALLOWED_ENVS = {
    "gar":        {"neg", "n_series_neg"},
    "überhaupt":  {"neg", "n_series_neg", "neg_predicate"},
    "sonderlich": {"neg"},
    "geheuer":    {"neg"},
    "beileibe":   {"neg", "n_series_neg"},
    "brauchen":   {"neg", "n_series_neg", "only_licensor"},
    # lemmas left unset = no env restriction
}

no_lemmas_de = {
    "kein",       # determiner/pronoun negation: keine Ahnung, kein Mensch
    "nichts",     # nothing
    "niemand",    # nobody
    "nirgends",   # nowhere
    "nirgendwo",  # nowhere (variant)
    "nie",        # never
    "niemals",    # never (emphatic)
    "weder"
}


extra_licensors_de = {
    # 'ohne' = without; also 'ohne dass' / 'ohne zu' subordinator
    frozenset({"ohne"}): ("without_pp_licensor", 2),

    # 'nur' = only (focus/exclusive licensor, parallel to English 'only')
    frozenset({"nur"}): ("DE_licensor", 2),

    frozenset({
        "selten",      # seldom
        "kaum",        # hardly/barely  (strong, near anti-additive)
        "wenig",       # little/few
        "wenige",      # few
        "schwerlich",  
    }): ("DE_licensor", 2),

}

negative_predicates_de = {
    # verbs
    "bezweifeln",   # doubt
    "leugnen",      # deny
    "bestreiten",   # deny/dispute
    "vermeiden",    # avoid
    "ablehnen",     # reject/refuse
    "verweigern",   # refuse
    "verhindern",   # prevent
    "verbieten",    # prohibit
    "ausschließen", # exclude
    "bezweifeln",   # (dup ok, set dedupes)
    "scheitern",    # fail
    "zögern",       # hesitate
    "weigern",      # refuse (sich weigern)
    "fehlen",       # lack / be absent
    "abstreiten",   # deny
    # adjectives
    "unmöglich",    # impossible
    "unwahrscheinlich", # unlikely
    "skeptisch",    # skeptical
    "abwesend",     # absent
    "deaktivieren",
    "lahmlegen"
}


conditional_markers_de = {
    "wenn",    # if
    "falls",   # in case / if
    "ob",      # whether
}

comparative_markers_de = {
    "als",     # than
}

bigrams_de = [
    ("im", "Geringsten", "im_geringsten"),  # nicht im Geringsten
    ("auch", "nur", "auch_nur"),   
]



n_to_indefinite_map_de = {

    "kein":      "ein",        # keine Ahnung -> eine Ahnung   (agreement!)
    "nichts":    "etwas",      # nothing -> something
    "niemand":   "jemand",     # nobody -> somebody
    "nirgends":  "irgendwo",   # nowhere -> somewhere
    "nirgendwo": "irgendwo",
    "nie":       "manchmal",   # never -> sometimes
    "niemals":   "manchmal",

    # ---- DE verbs -> UE counterpart ----
    "bezweifeln":  "glauben",     # doubt -> believe
    "leugnen":     "zugeben",     # deny -> admit
    "bestreiten":  "zugeben",     # dispute -> admit
    "abstreiten":  "zugeben",
    "vermeiden":   "suchen",      # avoid -> seek (cleaner than 'face' in DE)
    "ablehnen":    "annehmen",    # reject -> accept
    "verweigern":  "gewähren",    # refuse -> grant
    "verhindern":  "ermöglichen", # prevent -> enable
    "verbieten":   "erlauben",    # prohibit -> permit
    "ausschließen":"einschließen",# exclude -> include
    "scheitern":   "gelingen",    # fail -> succeed  (NB: dative-subject verb!)
    "fehlen":      "vorhanden",   # lack/be absent -> present (see caveat 3)

    # ---- DE adjectives -> polar opposite ----
    "unmöglich":        "möglich",        # impossible -> possible
    "unwahrscheinlich": "wahrscheinlich", # unlikely -> likely
    "skeptisch":        "überzeugt",      # skeptical -> convinced
    "abwesend":         "anwesend",       # absent -> present
}

swap_nur_de     = {"nur": "sogar"}    # only -> even  
swap_de_adverbs = {
    "selten":      "oft",        # seldom -> often
    "schwerlich":  "leicht",     # scarcely -> easily
    "wenig":       "viel",       # little -> much
    "wenige":      "viele",      # few -> many
}

swap_neg_coord_de = {"weder": "entweder", "noch": "oder"}


n_to_indefinite_map_de_clean = {
    k: v for k, v in n_to_indefinite_map_de.items()
    if k not in {"kein", "scheitern", "fehlen"}
}

# DET inflector for kein
det_inflector_de = UnimorphInflector(
    langcode="deu",
    inflection_map=(None, None),   
    resource_dir=RESOURCES,
    filter_entries={"upos": ["DET"]},
    combine_um_ud=True
)


config = LanguageConfig(
    language="German",
    npi_upos={"ADV","VERB"},
    npi_environments={
        "neg", "n_series_neg", "comparative", "conditional", "question",
        "DE_licensor", "only_licensor", "without_pp_licensor",
        "neg_predicate", "superlative", "neg_coord", "multiple_licensors", "superlative"
    },
    # German sentential negator: 'nicht'; 'kein' handled via n_series
    npi_lemma_upos=npi_lemma_upos,
    npi_allowed_envs = NPI_ALLOWED_ENVS,     
    neg_lemmas={"nicht", "kein"},
    n_series=no_lemmas_de,
    conditional_markers=conditional_markers_de,
    comparative_markers=comparative_markers_de,
    extra_licensors=extra_licensors_de,
    negative_predicates=negative_predicates_de,
    interclause_licensor={"neg", "n_series", "without_pp_licensor", "n_series_neg"},
    inflector=det_inflector_de,
    threshold=0.00,
    min_freq=1,
    max_sent_len=70,
    bigrams=bigrams_de,
    neg_coord = {
    "paired":  {"initial": {"weder"}, "linker": {"noch"}, "min_markers": 2},
    # English: need BOTH a 'neither' and a 'nor'
},
    removal_rules=[
    ConditionalRule(
        condition=lambda neg_tok, td: neg_tok.get("lemma") in {"nicht", "kaum"},
        action=Drop({"nicht", "kaum"}), check="neg",
    ),

    ConditionalRule(
        condition=lambda neg_tok, td: neg_tok.get("lemma") == "kein",
        action=LemmaSwapInflect(
            det_inflector_de,
            {"kein": "ein"},
            feature_updates={},   # keep Case/Gender/Number as-is; only lemma changes
        ), check="neg",
    ),

    ConditionalRule(
        condition=lambda neg_tok, td: neg_tok.get("lemma") in n_to_indefinite_map_de_clean,
        action=Swap(n_to_indefinite_map_de_clean), check="neg",
    ),

    ConditionalRule(
        condition=lambda neg_tok, td: neg_tok.get("lemma") == "nur",
        action=Swap(swap_nur_de), check="neg",
    ),


    ConditionalRule(
        condition=lambda neg_tok, td: neg_tok.get("lemma") in swap_de_adverbs,
        action=Swap(swap_de_adverbs), check="neg",
    ),

    ConditionalRule(
        condition=lambda neg_tok, td: neg_tok.get("lemma") in {"weder", "noch"},
        action=Swap(swap_neg_coord_de), check="neg",
    ),
],
)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(
        output, config,
        FINAL_PAIRS / f"{config.lang.lower()}"
    )