"""
External negation in Malay/Indonesian  Paul Kroeger, Graduate Institute of Applied Linguistics & SIL Intl.

tidak
bukan - kinda like degil 
saja -- only
Barangsiapa - whoever         

ketidakdatangan ‘non-arrival’ - non arrival
ketidakberterimaan ‘unaacceptability´

terima --- tidak ber-terima (these extra stuff is going to be annoyng)

sama sekali ‘at all’, 
sedikitpun  ‘even a little’, 
apa-apa ‘anything’, and 
siapa-siapa ‘anyone’,
mana-mana "any"
pernah - ever



TAK ?? -- well its polarity neg so we will catch it
jangan - do not?

belum - not yet
TANPA -without

NEGATION IN FOUR LANGUAGES  OF INDONESIA by Marielle Butters
   """

from src.blimppi.pipeline import (
    run_pipeline, save_output, LanguageConfig,
)
from src.blimppi.modifiers import Drop, ConditionalRule



from src.config.paths import UD, FINAL_PAIRS

extra_licensors = {
    frozenset({"tanpa"}): ("without_pp_licensor",1),
    frozenset({"belum"}): ("belum_licensor",1)
}
neg_lemmas = {
    "tidak", 
    "bukan",
    "jangan", #do not
    "takkan", #will not
    "tak", #never
    "belum", #have not?
    "entah", #not know
    "bukanlah"
}

#Takkan Tak Kunjung Belum Jangan dulu Kurang Entah(lah) 
#Negative future NEVER Nondum Nondum [PROH first] Indirect negation NOT KNOW 

npi_lemmas = {"sedikitpun", "sama_sekali", "apa_apa", "apa-apa", "mana-mana", "mana_mana", "siapa_siapa", "siapa-siapa", "seorang_pun"}


config = LanguageConfig(
    language="Indonesian",
    npi_upos={"PRON", "ADV", "DET", "ADJ"},
    npi_environments={"neg", "belum_licensor", "without_pp_licensor"},
    exclude_lemmas={"dokud"},
    npi_lemmas=npi_lemmas,
    neg_lemmas=neg_lemmas,
    extra_licensors=extra_licensors,
    threshold=0.00,
        bigrams=[
        ("sama", "sekali", "sama_sekali"),
        ("apa", "apa", "apa_apa"),
        ("mana", "mana", "mana_mana"),
        ("siapa", "siapa", "siapa_siapa"),
        ("seorang", "pun", "seorang_pun")
    ],
    max_sent_len=60,
    removal_rules=[
        ConditionalRule(
            condition=lambda neg_tok, td: neg_tok.get("lemma") in neg_lemmas,
            action=Drop(neg_lemmas), check= "neg"
        ),
    ],

)

if __name__ == "__main__":
    output = run_pipeline(config, UD)
    save_output(output, config, FINAL_PAIRS / f"{config.lang.lower()}")