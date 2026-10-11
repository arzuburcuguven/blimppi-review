import glob, pandas as pd, numpy as np
from pathlib import Path




def sample_entropy(stats_glob, K_total, *, n_sample=100, gate=100, R=500, seed=0,
                   gate_on="total", bucket_map=None, drop_envs=(),
                   include_remainder=True, skip_langs=()):
    skip = {s.lower() for s in skip_langs}
    rng = np.random.default_rng(seed)
    df = pd.concat([pd.read_csv(p) for p in glob.glob(stats_glob, recursive=True)],
               ignore_index=True)    
    if bucket_map: df["env"] = df["env"].map(lambda e: bucket_map.get(e, e))
    if drop_envs:  df = df[~df["env"].isin(drop_envs)]
    out = []
    for (lg, lm), g in df.groupby(["lang", "lemma"]):
        if lg.lower() in skip:
            continue
        total = int(g["total"].iloc[0])
        vec = g.groupby("env")["env_count"].sum().astype(int).to_dict()
        if include_remainder:
            rem = total - sum(vec.values())
            if rem > 0: vec["undetected_other"] = rem
        colors = np.array(list(vec.values()), dtype=int)
        pool = total if gate_on == "total" else int(colors.sum())
        if pool < gate:
            continue
        n = min(n_sample, int(colors.sum()))
        draws = rng.multivariate_hypergeometric(colors, n, size=R)   # (R, K_obs)
        p = draws / n
        with np.errstate(divide="ignore", invalid="ignore"):
            terms = np.where(draws > 0, p * np.log2(p), 0.0)
        H = -terms.sum(axis=1)
        Hn = np.clip(H / np.log2(K_total), 0, 1)
        out.append({"lang": lg, "lemma": lm, "total": total, "det_n": int(colors.sum()),
                    "n": n, "K_obs": int((colors > 0).sum()),
                    "H_mean": H.mean(), "H_sd": H.std(),
                    "H_norm_mean": Hn.mean(), "H_norm_sd": Hn.std()})
    return pd.DataFrame(out)