#!/usr/bin/env python3
"""Convert reviewed NPI Bank candidate CSV -> english_minimal_pairs.tsv rows."""
import csv, os, re, sys
from src.config.paths import FINAL_PAIRS, RESOURCES

OUT_COLS = ["sen", "wrong_sen", "lemma", "token_form", "swap_direction",
            "npi_to_neg_distance", "sent_len", "env", "npis_on_licensor",
            "sentence_npi_count", "sent_id", "quantity_level", "replacement"]

# lic_type (example_licenser_class_b05_2) -> env
ENV_MAP = {
    "NOT": "neg",
    "Scope-NOTHING": "n_series_neg",
    "Scope-NO": "n_series_neg",
    "Scope-NEVER": "n_series_neg",
    "Que-YN": "aux_inversion",
    "Sup-FIRST": "DE_licensor",
    "PREDICATE": "neg_predicate",
    "WITHOUT": "without_pp_licensor",
    "Restr-NOTHING": "n_series_neg",
    "Scope-HARDLY": "DE_licensor",
    "Scope-FEW": "DE_licensor",
    "Scope-ONLY": "DE_licensor",
}

# lic_types whose lic_surface is a class label, not a word in the sentence
PSEUDO_LICENSORS = {"Que-YN"}

TOK = re.compile(r"[^\W_]+(?:[-'\u2019][^\W_]+)*", re.UNICODE)

INFILE       = RESOURCES / "npi-bank" / "english_review.csv"
OUTFILE      = FINAL_PAIRS / "english" / "english_minimal_pairs.tsv"
ID_PREFIX    = "npibank-eng-"
SWAP_UNKNOWN = False
SKIP_REVIEW  = False     # most rows are flagged; set True only if flags are curated


def toks(s):
    return [m.group(0) for m in TOK.finditer(s)]


def norm(t):
    return t.lower().replace("\u2019", "'")


def clean(s):
    """Collapse all whitespace runs to single spaces (kills tabs/newlines)."""
    return " ".join((s or "").split())


def find_span(tokens, phrase):
    """Return list of 0-based start indices where phrase (1+ tokens) matches."""
    p = [norm(t) for t in toks(phrase)]
    if not p:
        return []
    n = [norm(t) for t in tokens]
    return [i for i in range(len(n) - len(p) + 1) if n[i:i + len(p)] == p]


def distance(sen, lic_surface, npi_surface):
    tokens = toks(sen)
    lic = find_span(tokens, lic_surface)
    npi = find_span(tokens, npi_surface)
    if not lic or not npi:
        return ""
    return min(abs(n - l) for l in lic for n in npi)


def diff_swap(sen, wrong):
    """Compare token streams; return (swap_direction, replacement)."""
    a, b = toks(sen), toks(wrong)
    i = 0
    while i < len(a) and i < len(b) and norm(a[i]) == norm(b[i]):
        i += 1
    j = 0
    while j < len(a) - i and j < len(b) - i and norm(a[-1 - j]) == norm(b[-1 - j]):
        j += 1
    da, db = a[i:len(a) - j], b[i:len(b) - j]
    if da and not db:
        return "deletion", "None"
    if da and db:
        return "substitution", " ".join(db)
    return "unknown", "None"


def main():
    with open(INFILE, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    existing = set()
    if os.path.exists(OUTFILE):
        with open(OUTFILE, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                existing.add(r["sen"])

    out, skipped = [], []
    for r in rows:
        rid = r.get("id", "?")

        if SKIP_REVIEW and (r.get("needs_review", "") or "").upper() == "TRUE":
            skipped.append((rid, "needs_review"))
            continue

        sen, wrong = clean(r["candidate"]), clean(r["wrong"])
        if not sen or not wrong:
            skipped.append((rid, "missing sen/wrong"))
            continue
        if sen == wrong:
            skipped.append((rid, "identical pair"))
            continue
        if sen in existing:
            skipped.append((rid, "duplicate sen"))
            continue

        try:
            n_npi = int(r.get("n_npi_matches") or 1)
        except ValueError:
            n_npi = 1
        if n_npi == 0:
            skipped.append((rid, "npi not matched in source"))
            continue

        lic_type = clean(r["lic_type"])
        env = ENV_MAP.get(lic_type)
        if env is None:
            skipped.append((rid, f"unmapped lic_type: {lic_type}"))
            continue

        # hyphenated surfaces (in-ages) are spaced in the sentence
        npi = clean(r["npi_surface"]).replace("-", " ")
        npi = clean(npi)
        npi_tokens = toks(npi)
        if not npi_tokens:
            skipped.append((rid, "empty npi_surface"))
            continue
        lemma = npi.lower().replace(" ", "_")
        token_form = npi_tokens[0].lower()

        lic_surface = clean(r["lic_surface"])
        if lic_type in PSEUDO_LICENSORS or lic_surface == lic_type:
            # no licensor word in the sentence; use NPI position from start
            hits = find_span(toks(sen), npi)
            dist = hits[0] if hits else ""
        else:
            dist = distance(sen, lic_surface, npi)
        if dist == "":
            skipped.append((rid, "licensor or NPI not found in candidate"))
            continue

        if SWAP_UNKNOWN:
            swap, repl = "unknown", "None"
        else:
            swap, repl = diff_swap(sen, wrong)

        out.append({
            "sen": sen,
            "wrong_sen": wrong,
            "lemma": lemma,
            "token_form": token_form,
            "swap_direction": swap,
            "npi_to_neg_distance": dist,
            "sent_len": len(toks(sen)),
            "env": env,
            "npis_on_licensor": n_npi,
            "sentence_npi_count": n_npi,
            "sent_id": f"{ID_PREFIX}{rid}",
            "quantity_level": "None",
            "replacement": repl,
        })
        existing.add(sen)

    new_file = not os.path.exists(OUTFILE) or os.path.getsize(OUTFILE) == 0
    with open(OUTFILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, delimiter="\t",
                           lineterminator="\n", quoting=csv.QUOTE_NONE,
                           escapechar=None)
        if new_file:
            w.writeheader()
        for row in out:
            try:
                w.writerow(row)
            except csv.Error as e:
                print(f"bad row {row['sent_id']}: {e}", file=sys.stderr)

    print(f"appended {len(out)} rows to {OUTFILE}", file=sys.stderr)
    print(f"skipped {len(skipped)} rows", file=sys.stderr)
    for sid, why in skipped:
        print(f"  {sid}: {why}", file=sys.stderr)


if __name__ == "__main__":
    main()