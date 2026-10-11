from blimppi.pipeline import run_pipeline, save_output, LanguageConfig
from blimppi.modifiers import Drop, ConditionalRule
from src.config.paths import UD, FINAL_PAIRS

# both Cyrillic and Latin negators so one list covers all three
neg_lemmas = {"не", "ne"}

LANGS = ["Bulgarian", "Serbian", "Croatian"]

def make_config(language):
    return LanguageConfig(
        language=language,
        npi_environments={"neg"},
        neg_lemmas=neg_lemmas,
        threshold=0.73,
        min_freq=6,
        max_sent_len=60,
        removal_rules=[
            ConditionalRule(
                condition=lambda neg_tok, td: neg_tok.get("lemma") in neg_lemmas,
                action=Drop(neg_lemmas), check="neg"
            ),
        ],
    )

if __name__ == "__main__":
    for language in LANGS:
        config = make_config(language)
        output = run_pipeline(config, UD)
        save_output(output, config,
                    FINAL_PAIRS / f"{config.lang.lower()}")
        print(f"done: {language}")

