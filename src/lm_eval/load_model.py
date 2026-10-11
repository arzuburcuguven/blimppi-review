import tempfile
from typing import *

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from minicons import scorer


# todo: take script from the actual MultiBLiMP file, not in this order
SCRIPTS = [
    "arab",
    "beng",
    "cyrl",
    "ethi",
    "tibt",
    "thaa",
    "grek",
    "hebr",
    "deva",
    "armn",
    "cans",
    "latn",
]
SIZES = [
    "5mb",
    "10mb",
    "100mb",
    "1000mb",
]

# kwargs that belong to the model only, not the tokenizer
_MODEL_ONLY_KWARGS = {
    "device_map",
    "max_memory",
    "torch_dtype",
    "dtype",
    "low_cpu_mem_usage",
    "attn_implementation",
    "offload_folder",
    "quantization_config",
}


def _split_kwargs(kwargs):
    model_kwargs = dict(kwargs)
    tok_kwargs = {k: v for k, v in kwargs.items() if k not in _MODEL_ONLY_KWARGS}
    return model_kwargs, tok_kwargs


def _default_device():
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _freeze_dispatched(model):
    """
    If accelerate dispatched the model across devices, stop anything downstream
    (minicons calls .to(device) in its constructor) from collapsing it onto one
    GPU. Returns the device inputs should be placed on, or None if not sharded.
    """
    if getattr(model, "hf_device_map", None) is None:
        return None
    if len(set(model.hf_device_map.values())) < 2:
        return None

    model.to = lambda *a, **k: model
    model.cuda = lambda *a, **k: model
    return str(next(model.parameters()).device)


def load_hf_model(model_name: str, no_cache=False, device: Optional[str] = None, **kwargs):
    model = None
    tokenizer = None
    model_kwargs, tok_kwargs = _split_kwargs(kwargs)
    try:
        if no_cache:
            with tempfile.TemporaryDirectory() as tmpdirname:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name, cache_dir=tmpdirname, **model_kwargs
                )
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name, cache_dir=tmpdirname, **tok_kwargs
                )
        else:
            model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
            tokenizer = AutoTokenizer.from_pretrained(model_name, **tok_kwargs)
    except OSError as e:
        print(f"OSError loading {model_name}: {e}")
        # fallback: try loading TensorFlow weights
        try:
            model = AutoModelForCausalLM.from_pretrained(model_name, from_tf=True, **model_kwargs)
            tokenizer = AutoTokenizer.from_pretrained(model_name, **tok_kwargs)
            print(f"Loaded {model_name} from TF weights")
        except Exception as e2:
            print(f"TF fallback also failed: {e2}")

    if model is None:
        return None

    shard_device = _freeze_dispatched(model)
    if shard_device is not None:
        device = shard_device
        print(
            f"Model dispatched across {len(set(model.hf_device_map.values()))} devices; "
            f"inputs on {device}"
        )

    ilm_model = scorer.IncrementalLMScorer(
        model,
        device or _default_device(),
        tokenizer=tokenizer,
    )
    return ilm_model


def load_goldfish_model(
    langcode: str,
    size: str,
    script: Optional[str] = None,
    no_cache=False,
    device: Optional[str] = None,
    **kwargs,
):
    if script is not None:
        return load_goldfish(langcode, script, size, no_cache=no_cache)
    else:
        model = None

        for script in SCRIPTS:
            model_name = f"goldfish-models/{langcode}_{script}_{size}"
            model = load_hf_model(model_name, no_cache=no_cache, device=device, **kwargs)
            if model is not None:
                break

        return model