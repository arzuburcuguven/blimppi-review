def analyze(df, model_name="model"):
    import numpy as np
    import pandas as pd
    from scipy import stats as scipy_stats

    df = df.copy()
    df["correct"] = df["delta"] > 0
    df["sent_len"] = pd.to_numeric(df["sent_len"], errors="coerce")

    results = {"model": model_name}

    print("\n" + "#" * 60)
    print(f"# AGGREGATE (all directions)")
    print("#" * 60)
    results["aggregate"] = _analyze_subset(df, f"{model_name} (aggregate)")

    if "swap_direction" in df.columns:
        for direction in sorted(df["swap_direction"].dropna().unique()):
            subset = df[df["swap_direction"] == direction]
            if len(subset) == 0:
                continue
            print("\n" + "#" * 60)
            print(f"# DIRECTION: {direction}")
            print("#" * 60)
            results[direction] = _analyze_subset(subset, f"{model_name} ({direction})")
    else:
        print("\n[Warning] No 'swap_direction' column found — only aggregate analysis reported.")

    return results


def _analyze_subset(df, label):
    import numpy as np
    import pandas as pd
    from scipy import stats as scipy_stats

    results = {}
    sep = "=" * 55

    if len(df) == 0:
        print(f"\n{sep}\n{label}: no data")
        return {"n": 0}

    accuracy = df["correct"].mean()
    results["overall"] = {
        "accuracy": round(accuracy, 3),
        "n": len(df),
        "n_correct": int(df["correct"].sum()),
        "mean_delta": round(df["delta"].mean(), 3),
        "median_delta": round(df["delta"].median(), 3),
        "std_delta": round(df["delta"].std(), 3),
    }
    print(f"\n{sep}")
    print(f"Subset: {label}")
    print(f"Overall accuracy : {accuracy:.3f}  ({df['correct'].sum()}/{len(df)})")
    print(f"Mean delta       : {df['delta'].mean():.3f}")
    print(f"Median delta     : {df['delta'].median():.3f}")
    print(f"Std delta        : {df['delta'].std():.3f}")

    if "multiple_npis" in df.columns:
        multi_stats = (df.groupby("multiple_npis")
                      .agg(n=("delta", "count"), accuracy=("correct", "mean"),
                           mean_delta=("delta", "mean")).round(3))
        results["by_multiple_npis"] = multi_stats.reset_index().to_dict(orient="records")
        print(f"\n{sep}\nAccuracy by Multiple NPIs:")
        for is_multi, row in multi_stats.iterrows():
            tag = "Multiple NPIs" if is_multi else "Single NPI"
            print(f"  {tag:<15} {row['n']:>4} ({row['accuracy']:.3f}) mean_delta={row['mean_delta']:.3f}")

    if "lemma" in df.columns:
        lemma_stats = (
            df.groupby("lemma")
            .agg(n=("delta", "count"), accuracy=("correct", "mean"),
                 mean_delta=("delta", "mean"), median_delta=("delta", "median"),
                 std_delta=("delta", "std"))
            .sort_values("accuracy", ascending=False).round(3)
        )
        results["by_lemma"] = lemma_stats.reset_index().to_dict(orient="records")
        print(f"\n{sep}\nAccuracy by NPI lemma:\n{lemma_stats.to_string()}")

    if "sent_len" in df.columns:
        df = df.copy()
        df["len_bucket"] = pd.cut(df["sent_len"],
            bins=[0, 10, 20, 30, 40, np.inf], labels=["1-10", "11-20", "21-30", "31-40", "40+"])
        len_stats = (df.groupby("len_bucket", observed=True)
                     .agg(n=("delta", "count"), accuracy=("correct", "mean"),
                          mean_delta=("delta", "mean")).round(3))
        if df["sent_len"].notna().any():
            corr, pval = scipy_stats.pointbiserialr(
                df["sent_len"].dropna(),
                df.loc[df["sent_len"].notna(), "correct"]
            )
            results["by_sent_len"] = {
                "stats": len_stats.reset_index().to_dict(orient="records"),
                "corr": round(corr, 3),
                "pval": round(pval, 3),
            }
            print(f"\n{sep}\nAccuracy by sentence length bucket:\n{len_stats.to_string()}")
            print(f"\n  Correlation (sent_len vs correct): r={corr:.3f}, p={pval:.3f}")

    if "npi_to_neg_distance" in df.columns and df["npi_to_neg_distance"].notna().any():
        single_npi_df = df[df.get("multiple_npis", False) == False] if "multiple_npis" in df.columns else df
        single_npi_df = single_npi_df[
            single_npi_df["npi_to_neg_distance"].notna()
            & (single_npi_df["npi_to_neg_distance"] >= 0)
        ]

        if len(single_npi_df) > 1:
            dist_stats = (single_npi_df.groupby("npi_to_neg_distance")
                          .agg(n=("delta", "count"), accuracy=("correct", "mean"),
                               mean_delta=("delta", "mean")).round(3))
            corr_bin, pval_bin = scipy_stats.pointbiserialr(
                single_npi_df["npi_to_neg_distance"], single_npi_df["correct"]
            )
            corr_delta, pval_delta = scipy_stats.pearsonr(
                single_npi_df["npi_to_neg_distance"], single_npi_df["delta"]
            )
            n_excl = int((df["npi_to_neg_distance"] < 0).sum())
            results["by_distance"] = {
                "stats": dist_stats.reset_index().to_dict(orient="records"),
                "corr_binary": round(corr_bin, 3),
                "pval_binary": round(pval_bin, 3),
                "corr_delta": round(corr_delta, 3),
                "pval_delta": round(pval_delta, 3),
                "n_excluded_no_head": n_excl,
            }
            print(f"\n{sep}\nAccuracy by NPI-to-neg distance (Single NPI only, excl. no-head):\n{dist_stats.to_string()}")
            print(f"\n  Correlation (distance vs correct): r={corr_bin:.3f}, p={pval_bin:.3f}")
            print(f"  Correlation (distance vs delta):  r={corr_delta:.3f}, p={pval_delta:.3f}")
            print(f"  Excluded (no clause head, dist<0): {n_excl}")

    if "sentence_npi_count" in df.columns:
        print(f"\n{sep}\nDistance analysis by NPI count:")
        for is_multi in [False, True]:
            subset = df[df["sentence_npi_count"] == is_multi]
            if len(subset) > 0:
                tag = "Multiple NPIs" if is_multi else "Single NPI"
                valid_subset = subset[
                    subset["npi_to_neg_distance"].notna()
                    & (subset["npi_to_neg_distance"] >= 0)
                ] if "npi_to_neg_distance" in subset.columns else subset.iloc[0:0]
                if len(valid_subset) > 5:
                    corr_bin, pval_bin = scipy_stats.pointbiserialr(
                        valid_subset["npi_to_neg_distance"], valid_subset["correct"]
                    )
                    corr_delta, pval_delta = scipy_stats.pearsonr(
                        valid_subset["npi_to_neg_distance"], valid_subset["delta"]
                    )
                    print(f"  {tag}: r_binary={corr_bin:.3f} p={pval_bin:.3f} | r_delta={corr_delta:.3f} p={pval_delta:.3f} (n={len(valid_subset)})")

    if "npis_on_licensor" in df.columns:
        count_stats = (df.groupby("npis_on_licensor")
                      .agg(n=("delta", "count"), accuracy=("correct", "mean"),
                           mean_delta=("delta", "mean")).round(3))
        results["by_npi_count"] = count_stats.reset_index().to_dict(orient="records")
        print(f"\n{sep}\nAccuracy by NPI count:\n{count_stats.to_string()}")

    bins = [-np.inf, -10, -5, -2, 0, 2, 5, 10, np.inf]
    labels = ["<-10", "-10:-5", "-5:-2", "-2:0", "0:2", "2:5", "5:10", ">10"]
    df = df.copy()
    df["delta_bin"] = pd.cut(df["delta"], bins=bins, labels=labels)
    bin_counts = df["delta_bin"].value_counts().reindex(labels)
    results["delta_distribution"] = {lb: int(c) for lb, c in bin_counts.items()}
    print(f"\n{sep}\nDelta distribution:")
    for lb, count in bin_counts.items():
        pct = count / len(df) * 100
        marker = "✓" if lb in ["0:2", "2:5", "5:10", ">10"] else "✗"
        print(f"  {marker} {lb:<10} {count:>4} ({pct:>5.1f}%)  {'█' * int(pct / 2)}")

    return results