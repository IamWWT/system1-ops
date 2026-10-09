"""Per-worker CPU precision policy for the pinned upstream StartLux implementation.

Upstream hard-codes BF16 loading/autocast. Only that module's torch reference and
load_model boundary are adapted; the global torch module and upstream files are
unchanged. A worker owns one engine, so precision cannot race with another model.
"""
from contextlib import nullcontext

from portable import cpu_flags


def cpu_dtype(name):
    if name == "auto":
        return "bf16" if {"avx512_bf16", "amx_bf16"}.intersection(cpu_flags()) else "fp32"
    if name not in ("fp32", "bf16"):
        raise ValueError("cpu_dtype must be auto, fp32 or bf16")
    return name


def apply(dtype, attention="sdpa"):
    import torch
    import transformers
    from startlux_decision import model as upstream

    class TorchPolicy:
        def __getattr__(self, name):
            return getattr(torch, name)

        def autocast(self, device_type, *args, **kwargs):
            if device_type == "cpu" and dtype == "fp32":
                return nullcontext()
            return torch.autocast(device_type, *args, **kwargs)

    def load_model(path, device):
        cfg = transformers.AutoConfig.from_pretrained(path, local_files_only=True)
        extra = {"experts_implementation": "grouped_mm"} if getattr(cfg.get_text_config(), "num_experts", 0) else {}
        chosen = torch.float32 if device.type == "cpu" and dtype == "fp32" else torch.bfloat16
        loaded = getattr(transformers, cfg.architectures[0]).from_pretrained(
            path, dtype=chosen, device_map={"": device}, local_files_only=True,
            attn_implementation=attention, **extra)
        return loaded, getattr(loaded.model, "language_model", loaded.model)

    upstream.torch = TorchPolicy()
    upstream.load_model = load_model
