from glob import glob
import argparse
import sys
import os
import json
import torch


_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src",
)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from config.paths import RESULTS, FINAL_PAIRS

results_dir = RESULTS / "model_results"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", help="LM to evaluate")
    parser.add_argument("--revision", default=None, help="HF revision / checkpoint, e.g. step16000")
    parser.add_argument("--data_dir", help="Minimal pair directory", default=FINAL_PAIRS)
    parser.add_argument("--src_dir", help="Source directory", default="./src")
    parser.add_argument("--results_dir", help="Base dir to write results to", default=results_dir)
    parser.add_argument("--cache_dir", help="(optional) HF cache dir", default="")
    parser.add_argument("--hf_token", help="Huggingface token (file or token itself)", default=os.environ.get("HF_TOKEN", "hf_token.txt"))
    parser.add_argument("--lang", default=None, help="Filter to a specific language")
    parser.add_argument("--shard", action="store_true",
                        help="Shard across all visible GPUs with device_map='auto'")
    parser.add_argument("--gpu_mem_frac", type=float, default=0.85,
                        help="Fraction of each GPU's VRAM to budget for weights")
    args = parser.parse_args()

    sys.path.append(args.src_dir)
    from lm_eval.load_model import load_hf_model
    from lm_eval.score import score_tse
    from lm_eval.analyze_result import analyze

    if args.hf_token and os.path.exists(args.hf_token):
        with open(args.hf_token) as f:
            hf_token = f.read().strip()
    else:
        hf_token = args.hf_token or None

    load_kwargs = {}
    if hf_token:
        load_kwargs["token"] = hf_token
    if args.cache_dir:
        load_kwargs["cache_dir"] = args.cache_dir
    if args.revision:
        load_kwargs["revision"] = args.revision

    if args.shard:
        n_gpu = torch.cuda.device_count()
        if n_gpu < 2:
            sys.exit(f"--shard passed but only {n_gpu} GPU(s) visible")
        per_gpu = torch.cuda.get_device_properties(0).total_memory // 2**30
        budget = f"{int(per_gpu * args.gpu_mem_frac)}GiB"
        load_kwargs["device_map"] = "auto"
        load_kwargs["max_memory"] = {i: budget for i in range(n_gpu)}
        load_kwargs["max_memory"]["cpu"] = "0GiB"
        load_kwargs["torch_dtype"] = torch.bfloat16
        load_kwargs["low_cpu_mem_usage"] = True
        print(f"Sharding across {n_gpu} GPUs, {budget} budgeted each", flush=True)

    lm = load_hf_model(args.model_name, no_cache=False, **load_kwargs)
    if lm is None:
        sys.exit(f"Failed to load {args.model_name} @ {args.revision or 'main'}")

    if args.shard:
        inner = getattr(lm, "model", lm)          # minicons wraps the HF model
        dmap = getattr(inner, "hf_device_map", None)
        if dmap is None:
            sys.exit("device_map='auto' did not take effect — check that "
                     "load_hf_model forwards **kwargs to from_pretrained")
        offloaded = {k: v for k, v in dmap.items() if v in ("cpu", "disk")}
        if offloaded:
            sys.exit(f"{len(offloaded)} modules offloaded off-GPU: "
                     f"{list(offloaded)[:5]} — lower --gpu_mem_frac or add a GPU")
        print(f"Device map OK: {len(dmap)} modules across "
              f"{len(set(dmap.values()))} devices", flush=True)

    # model_results/<org>/<model>/<revision>/
    rev_tag = args.revision or "main"
    results_dir = os.path.join(args.results_dir, args.model_name, rev_tag)
    os.makedirs(results_dir, exist_ok=True)

    pair_files = glob(os.path.join(args.data_dir, "*/*/*.tsv"))
    if args.lang:
        pair_files = [f for f in pair_files if args.lang in f]

    all_results = []
    for fn in sorted(pair_files):
        phenomenon, lang, condition = os.path.relpath(fn, args.data_dir).split(os.sep)
        condition = condition.replace(".tsv", "")

        df = score_tse(lm, fn=fn)

        score_fn = os.path.join(results_dir, f"{phenomenon}_{lang}_{condition}.tsv")
        df.to_csv(score_fn, sep="\t")

        result = analyze(df, model_name=args.model_name)
        result["phenomenon"] = phenomenon
        result["lang"] = lang
        result["condition"] = condition
        result["revision"] = rev_tag
        all_results.append(result)

    summary_path = os.path.join(results_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSummary saved to {summary_path}")