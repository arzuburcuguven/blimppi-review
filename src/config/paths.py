from pathlib import Path


def _find_repo(start: Path) -> Path:
    d = start.resolve()
    for parent in (d, *d.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError(
        f"repo root not found: no pyproject.toml above {start}"
    )


REPO = _find_repo(Path(__file__))

# Tracked (code + config live at REPO root; these are data areas)
FINAL_PAIRS = REPO / "final_pairs" / "npi"     # benchmark pairs / derived stats

# Gitignored (regenerable / external) — see .gitignore
RESULTS = REPO / "results"             # eval + analysis outputs, figures
RESOURCES = REPO / "resources"         # treebanks, weights, tarballs
UD = RESOURCES / "ud" / "ud-treebanks-v2.18"


__all__ = ["REPO", "FINAL_PAIRS", "RESULTS", "RESOURCES", "UD"]