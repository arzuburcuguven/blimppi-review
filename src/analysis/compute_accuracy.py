import glob, pandas as pd, numpy as np

def compute_accuracy(specs, resolve, *, gate=20, skip_langs=(),
                     lemma_col="lemma", delta_col="delta"):
    skip = {s.lower() for s in skip_langs}
    out = []
    for spec in specs:
        for p in glob.glob(spec["glob"], recursive=True):
            lg = resolve(p)
            if lg is None or lg.lower() in skip:
                print(f"[skip: no lang] {p}"); continue
            df = pd.read_csv(p, sep="\t")
            if delta_col not in df.columns:
                print(f"[skip: no delta] {p}"); continue
            df["_c"] = (df[delta_col] > 0).astype(int)
            for lm, gg in df.groupby(lemma_col):
                f = gg["_c"].to_numpy(); n = len(f)
                if n < gate: continue
                acc = float(f.mean())
                out.append({"lang": lg, "lemma": lm, "model": spec["model"],
                            "pair_n": n, "accuracy": acc,
                            "acc_se": float(np.sqrt(acc*(1-acc)/n))})
    return pd.DataFrame(out, columns=["lang","lemma","model","pair_n","accuracy","acc_se"])