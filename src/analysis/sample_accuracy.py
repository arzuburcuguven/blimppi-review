import glob, pandas as pd, numpy as np
from pathlib import Path

def lang_resolver(stats_glob, extra=None):
    s = pd.concat([pd.read_csv(p) for p in glob.glob(stats_glob, recursive=True)],
              ignore_index=True)
    names = {n.lower(): n for n in s["lang"].unique()}      # 'dutch'->'Dutch', 'belarusian'->'Belarusian'
    if extra: names.update({k.lower(): v for k, v in extra.items()})  # multiword: {'bokmal':'Norwegian_Bokmal'}
    def resolve(path):
        p = Path(path)
        for tok in [t.lower() for t in p.stem.split("_")] + [par.name.lower() for par in p.parents]:
            if tok in names:
                return names[tok]
        return None
    return resolve

def sample_accuracy(specs, resolve, *, m_sample=100, gate=100, R=500, seed=0,
                    lemma_col="lemma", delta_col="delta",  skip_langs=()):
    # specs: list of {"glob": "...recursive pattern...", "model": "label"}
    rng = np.random.default_rng(seed); out = []
    for spec in specs:
        for p in glob.glob(spec["glob"], recursive=True):
            lg = resolve(p)
            if lg is None:
                print(f"[skip: no lang] {p}"); continue
            df = pd.read_csv(p, sep="\t")
            if delta_col not in df.columns:
                print(f"[skip: no delta] {p}"); continue
            df["_c"] = (df[delta_col] > 0).astype(int)
            for lm, g in df.groupby(lemma_col):
                f = g["_c"].to_numpy(); N = len(f)
                if N < gate: continue
                m = min(m_sample, N)
                acc = np.array([f[rng.choice(N, m, replace=False)].mean() for _ in range(R)])
                out.append({"lang": lg, "lemma": lm, "model": spec["model"],
                            "pair_n": N, "m": m, "acc_mean": acc.mean(),
                            "acc_sd": acc.std(), "acc_full": f.mean()})
    return pd.DataFrame(out)