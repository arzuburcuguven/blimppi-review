import pandas as pd
import csv
from collections import defaultdict
import re
from src.config.paths import UD, FINAL_PAIRS, RESOURCES


input_file =  RESOURCES / "npu" / "npu.csv"

output_file = FINAL_PAIRS / "dutch" / "dutch_minimal_pairs.tsv"

NPUs = {
    "ook maar",
    "hoeven",
    "enig",
    "mals",
    "pluis",
    "hand voor ogen",
}

MAX_PER_NPU = 500
MIN_YEAR = 1960
MIN_LEN = 7

drop_triggers = {"niet"}

niets_to_indefinite_map = {
    "niemand": "iemand",
    "niets": "iets",
    "niks": "iets",
    "nergens": "ergens",
    "nooit": "ooit",
    "geen": "een",
}

swap_triggers = set(niets_to_indefinite_map)
triggers = drop_triggers | swap_triggers

extra_licensors = {
    "zonder", "geenszins", "alleen", "zelden", "nauwelijks", "weinig",
    "slechts", "voordat", "hoogstens", "evenmin", "allerminst",
    "amper", "ternauwernood",
}

negative_predicates = {
    "weigeren", "ontkennen", "onmogelijk", "ontbreken", "verbieden",
    "missen", "verliezen", "moeilijk", "vermijden",
}

all_licensors = triggers | extra_licensors | negative_predicates

conditional_markers = {"als", "indien", "tenzij", "mits", "alsof", "af"
                }
comparative_markers = {"dan"
                    }

independent_licensors = conditional_markers | comparative_markers

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
PUNCT = re.compile(r"^\W+$")


def clean(s):
    return _CTRL.sub("", str(s))


def norm(w):
    return w.lower().strip(".,!?;:\"'()")


def token_count(words):
    return sum(1 for w in words if not PUNCT.match(w))


df = pd.read_csv(input_file)
df["decade"] = pd.to_numeric(df["decade"], errors="coerce")
df = df[df["decade"] >= MIN_YEAR]

rows = []
npu_counts = defaultdict(int)
pair_seen = set()
excluded = 0

for row_idx, row in df.iterrows():
    sentence = str(row.get("zin", "")).strip()
    if any(bad in sentence for bad in ("\t", "   ")):
        excluded += 1
        continue
    year = int(row["decade"])
    words = sentence.split()

    if token_count(words) < MIN_LEN:
        continue

    normed = [norm(w) for w in words]

    if any(w in (independent_licensors | {"?"}) for w in normed):
        excluded += 1
        continue

    npu_col = str(row.get("npu", "")).lower()
    matched_npu = next((n for n in NPUs if n in npu_col), None)
    if matched_npu is None:
        continue
    if npu_counts[matched_npu] >= MAX_PER_NPU:
        continue

    lic_idxs = [i for i, w in enumerate(normed) if w in all_licensors]
    if len(lic_idxs) != 1:
        continue

    lic_idx = lic_idxs[0]
    lic = normed[lic_idx]
    if lic not in triggers:
        continue

    # build corrupted sentence
    if lic in drop_triggers:
        wrong_words = [w for i, w in enumerate(words) if i != lic_idx]
        if lic_idx == 0 and wrong_words:
            wrong_words[0] = wrong_words[0][:1].upper() + wrong_words[0][1:]
        swap_dir = "drop"
    else:
        repl = niets_to_indefinite_map[lic]
        if words[lic_idx][:1].isupper():
            repl = repl.capitalize()
        wrong_words = [repl if i == lic_idx else w for i, w in enumerate(words)]
        swap_dir = f"{lic}->{repl}"

    wrong_sentence = " ".join(wrong_words)

    pair_key = (clean(sentence), clean(wrong_sentence))
    if pair_key in pair_seen:
        continue
    pair_seen.add(pair_key)

    npu_idx = next((i for i, w in enumerate(normed) if matched_npu in w), None)
    distance = abs(npu_idx - lic_idx) if npu_idx is not None else None

    sent_id = f"dutch_{year}_{row_idx}"

    rows.append({
        "sen": clean(sentence),
        "wrong_sen": clean(wrong_sentence),
        "lemma": matched_npu,
        "swap_direction": swap_dir,
        "npi_to_neg_distance": distance,
        "sent_len": token_count(words),
        "env": lic,
        "multiple_npis": "unknown",
        "npi_count": "unknown",
        "year": year,
        "sent_id": sent_id,
    })

    npu_counts[matched_npu] += 1

out = pd.DataFrame(rows)
out = out.drop_duplicates(subset=["sen", "wrong_sen"])
out.to_csv(output_file, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)

# --- stats ---
if out.empty:
    print("no pairs")
else:
    print("\nby licensor (env):")
    print(out["env"].value_counts().to_string())

    print("\nby decade:")
    print(out["year"].value_counts().sort_index().to_string())

    print("\nby NPU lemma:")
    print(out["lemma"].value_counts().to_string())

    print("\nenv x decade:")
    print(pd.crosstab(out["env"], out["year"],
                      margins=True, margins_name="total").to_string())

    print("\nlemma x env:")
    print(pd.crosstab(out["lemma"], out["env"],
                      margins=True, margins_name="total").to_string())

    print("\nNPI-to-licensor distance by env:")
    print(out.groupby("env")["npi_to_neg_distance"]
             .describe()[["count", "mean", "min", "50%", "max"]]
             .round(2).to_string())

print(f"Written {len(out)} pairs")
print(dict(npu_counts))
print(f"exclude count: {excluded}")