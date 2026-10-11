#!/usr/bin/env python3
import kenlm, glob, os
import pandas as pd
from pathlib import Path
import re

_CJK = re.compile(
    r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]'
    r'|[^\s\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+'
)

NGRAM_DIR = Path.home() / "NPI/n-grams/kenlm_bp"
PAIRS_DIR = Path.home() / "blimppi/final_pairs/npi"
OUT_DIR   = Path.home() / "blimppi/results/model_results/kenlm/goldfish_5gram/main"

GF = {
    "armenian": "hye_armn",           "belarusian": "bel_cyrl",   "bulgarian": "bul_cyrl",
    "catalan": "cat_latn",            "croatian": "hrv_latn",     "czech": "ces_latn",
    "danish": "dan_latn",             "english": "eng_latn",      "finnish": "fin_latn",
    "german": "deu_latn",             "greek": "ell_grek",        "hebrew": "heb_hebr",
    "hindi": "hin_deva",              "hungarian": "hun_latn",    "icelandic": "isl_latn",
    "indonesian": "ind_latn",         "lithuanian": "lit_latn",   "persian": "pes_arab",
    "polish": "pol_latn",             "romanian": "ron_latn",     "russian": "rus_cyrl",
    "serbian": "srp_latn",            "slovak": "slk_latn",       "slovenian": "slv_latn",
    "spanish": "spa_latn",            "swedish": "swe_latn",      "turkish": "tur_latn",
    "ukrainian": "ukr_cyrl",          "urdu": "urd_arab",         "dutch": "nld_latn",
    "norwegian-bokmaal": "nob_latn",  "norwegian-nynorsk": "nor_latn",
    "chinese": "zho_hans",
}
LANG_MAP = {v: k for k, v in GF.items()}    # code -> pairs dir name

def normalize(s, code=None):
    s = str(s).strip()
    if code and code.startswith("zho_"):
        return " ".join(_CJK.findall(s))
    return " ".join(s.split())

def find_models():
    m = {}
    for ext in ("arpa", "binary"):
        for p in glob.glob(str(NGRAM_DIR / ext / f"*.{ext}")):
            m[Path(p).stem] = p        # binary overwrites arpa; both fine
    return m

OUT_DIR.mkdir(parents=True, exist_ok=True)
rows = []
for code, mpath in sorted(find_models().items()):
    name = LANG_MAP.get(code)
    if name is None:
        print(f"NO MAPPING  {code}")
        continue
    tsv = PAIRS_DIR / name / f"{name}_minimal_pairs.tsv"
    if not tsv.exists():
        print(f"NO PAIRS    {code} -> {tsv}")
        continue

    m = kenlm.Model(mpath)
    df = pd.read_csv(tsv, sep="\t")
    df["sen_nll"]   = df["sen"].map(lambda s: -m.score(normalize(s, code), bos=True, eos=True))
    df["wrong_nll"] = df["wrong_sen"].map(lambda s: -m.score(normalize(s, code), bos=True, eos=True))
    df["delta"]   = df["wrong_nll"] - df["sen_nll"]
    df["oov_good"] = df["sen"].map(lambda s: sum(t not in m for t in normalize(s, code).split()))
    df["oov_bad"]  = df["wrong_sen"].map(lambda s: sum(t not in m for t in normalize(s, code).split()))
    df["correct"] = (df["delta"] > 0).astype(int)
    df["lang"]  = code
    df["model"] = f"kenlm-{m.order}gram"
    df.to_csv(OUT_DIR / f"{code}_minimal_pairs.tsv", sep="\t", index=False)

    rows.append(dict(lang=code, n=len(df), acc=df.correct.mean(),
                     ties=(df.delta == 0).mean(),
                     oov=df.oov_good.mean(),
                     oov_asym=(df.oov_good != df.oov_bad).mean()))
    print(f"{code:10s} n={len(df):5d} acc={df.correct.mean():.3f} "
          f"ties={(df.delta==0).mean():.3f} oov={df.oov_good.mean():.2f}")

s = pd.DataFrame(rows).sort_values("acc")
s.to_csv(OUT_DIR.parent / "kenlm_summary.tsv", sep="\t", index=False)
print("\n", s.round(3).to_string(index=False))