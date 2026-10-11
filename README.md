# Blimppi

# ≤9B (pythia, gemma-1b/4b, llama-8b, qwen3-8b, xglm, bloom, salamandra, eurollm)
--nodelist=cn19,cn13,cn12          # or cn3,cn4,cn6 for pythia/xglm only

# 12–14B (gemma-12b, mGPT-13B, Qwen3-14B) — 24-28GB
--nodelist=cn19,cn12,cn13

# 27B/32B (gemma-27b, Qwen2.5-32B, Qwen3-32B) — 54-64GB, needs one 80GB card
--nodelist=cn11 --gres=gpu:1       # h100
# or shard across two 48GB l40s:
--nodelist=cn19 --gres=gpu:2       # + --shard

# 70B — 140GB
--nodelist=cn11 --gres=gpu:2       # 2× h100 = 160GB, tight but fits
# safer:
--nodelist=cn19 --gres=gpu:4       # 4× l40s = 192GB