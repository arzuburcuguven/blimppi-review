"""
Model registry loader + shared analysis paths.

The list of models lives in config/models.toml (data, hand-edited). This module
turns those facts into the `model_specs` structure the analysis functions expect,
assembling path against the real RESULTS root so nothing hardcodes an absolute
path. Import from here everywhere instead of duplicating the model list.

    from multiblimp.config import load_models, STATS_GLOB, GRID_OUT
    specs = load_models()                    # all models
    specs = load_models(families={"Qwen"})   # just one family
"""

import tomllib

from config.paths import REPO, RESULTS, FINAL_PAIRS

_CFG = REPO / "src"/ "config" / "models.toml"

# eval .tsv outputs and where analysis figures/csvs are written
MODEL_RESULTS = RESULTS / "model_results"
GRID_OUT = RESULTS / "grid"
STATS_GLOB = str(FINAL_PAIRS / "**" / "*_stats.csv")


def load_models(families=None, skip=()):
    """Read models.toml -> list of {"specs": [...], "model": name, "family": fam}.

    families: optional set of family names to keep (None = all).
    skip:     optional set of model names to drop.
    """
    with open(_CFG, "rb") as f:
        data = tomllib.load(f)

    skip = {s for s in skip}
    specs = []
    for m in data["model"]:
        if families is not None and m["family"] not in families:
            continue
        if m["name"] in skip:
            continue
        glob = str(MODEL_RESULTS / m["path"])
        specs.append({
            "specs": [{"glob": glob, "model": m["name"]}],
            "model": m["name"],
            "family": m["family"],
        })
    return specs


def families(model_specs):
    """{family: [model_name, ...]} from a loaded spec list — for family panels."""
    out = {}
    for ms in model_specs:
        out.setdefault(ms["family"], []).append(ms["model"])
    return out