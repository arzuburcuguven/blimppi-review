import glob, pandas as pd, numpy as np
from analysis.bucket_map import BUCKET_MAP, DROP_ENVS   # single source of truth

def compute_entropy(stats_glob, K_total, *, gate=40, gate_on="total",
                    bucket_map=BUCKET_MAP, drop_envs=DROP_ENVS,
                    include_remainder=True, skip_langs=()):
    skip = {s.lower() for s in skip_langs}
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
        licensed_n = sum(vec.values())
        if include_remainder:
            rem = total - licensed_n
            if rem > 0: vec["undetected_other"] = rem
        c = np.array(list(vec.values()), dtype=float); N = c.sum()
        pool = {"total": total, "licensed": licensed_n}[gate_on]
        if pool < gate:
            continue
        p = c[c > 0] / N
        H = -(p * np.log2(p)).sum()
        out.append({"lang": lg, "lemma": lm, "total": total,
                    "licensed_n": licensed_n, "det_n": int(N),
                    "K_obs": int((c > 0).sum()), "H": H,
                    "H_norm": float(np.clip(H / np.log2(K_total), 0, 1))})
    return pd.DataFrame(out)