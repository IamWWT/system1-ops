"""Configuration and offline checkpoint preflight. No torch imports here."""

import json
import os
import pathlib
import sys
import tomllib
from typing import Any

ROOT = pathlib.Path(os.environ.get("SYSTEM1_HOME", pathlib.Path(__file__).resolve().parents[2]))
DEFAULT_CONFIG = ROOT / "config.toml" if (ROOT / "config.toml").exists() else ROOT / "configs" / "example.toml"


def load_local_environment() -> None:
    """Optional local credentials; caller environment wins, no shell evaluation."""
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() in ("SYSTEM1_ADMIN_KEY", "SYSTEM1_API_KEY"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def prepare_runtime(item: dict[str, Any]) -> None:
    sys.path.insert(0, item["source"])
    sys.path.extend(item.get("dependency_paths", []))
    os.environ.update(
        OMP_NUM_THREADS=str(item["threads"]),
        MKL_NUM_THREADS=str(item["threads"]),
        TOKENIZERS_PARALLELISM="false",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        USE_TF="0",
        STARTLUX_GRAPHS="1" if item["cuda_graphs"] else "0",
        STARTLUX_ALLOW_SLOW="1" if item["allow_slow_cuda"] else "0",
    )


def add_overrides(parser: Any) -> Any:
    parser.add_argument("--port", type=int)
    parser.add_argument("--device", help="cpu, auto or cuda:N")
    parser.add_argument("--context-length", type=int)


def apply_overrides(item: Any, args: Any) -> Any:
    for key in ("port", "device", "context_length"):
        value = getattr(args, key, None)
        if value is not None:
            item[key] = value
    if not 1 <= item["port"] <= 65535 or item["context_length"] < 256:
        raise ValueError("invalid port or context length")
    if item["device"] not in ("auto", "cpu"):
        prefix, _, index = item["device"].partition(":")
        if prefix != "cuda" or not index.isdigit():
            raise ValueError("device must be auto, cpu or cuda:N")
    return item


def config(path: str | pathlib.Path) -> dict[str, dict[str, Any]]:
    path = pathlib.Path(path).resolve()
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    result: dict[str, dict[str, Any]] = {}
    ports = set()
    for name, overrides in raw["models"].items():
        item: dict[str, Any] = dict(
            cpu_dtype="auto",
            cpu_quantization="none",
            laya_backend="eager",
            cpu_affinity=[],
            laya_gpu_dtype="fp32",
            laya_gpu_tf32=False,
            serialize_inference=False,
            unload_after_request=False,
            attention="sdpa",
            fallback_eager=True,
            preload=True,
            torch_interop_threads=1,
            startlux_backend="torch",
            gguf_file="",
            llama_server="",
            native_binary="",
            llama_port=18883,
            llama_gpu_layers=0,
            llama_cache_type="f16",
        )
        item.update(raw["defaults"])
        item.update(overrides)
        item["name"] = name
        for key in ("python", "source", "path"):
            if key == "python" and item[key] == "auto":
                item[key] = sys.executable
                continue
            value = pathlib.Path(os.path.expandvars(item[key])).expanduser()
            # Keep the venv Python symlink path: resolving it loses pyvenv.cfg.
            item[key] = os.path.abspath(path.parent / value)
        for key in ("gguf_file", "llama_server", "native_binary"):
            if item[key]:
                item[key] = os.path.abspath(path.parent / pathlib.Path(os.path.expandvars(item[key])).expanduser())
        item["dependency_paths"] = [
            str((path.parent / pathlib.Path(p).expanduser()).resolve()) for p in item.get("dependency_paths", [])
        ]
        if item["kind"] not in ("laya", "startlux"):
            raise ValueError(f"{name}: unknown kind")
        if item["device"] not in ("auto", "cpu") and not item["device"].startswith("cuda:"):
            raise ValueError(f"{name}: device must be auto, cpu or cuda:N")
        apply_overrides(item, None)
        if item["cpu_dtype"] not in ("auto", "fp32", "bf16") or item["cpu_quantization"] not in ("none", "int8"):
            raise ValueError(f"{name}: invalid CPU precision / quantization")
        if item["laya_backend"] not in ("eager", "auto", "compile", "tilelang"):
            raise ValueError(f"{name}: invalid Laya backend")
        if item["laya_gpu_dtype"] not in ("fp32", "bf16", "fp16"):
            raise ValueError(f"{name}: invalid Laya GPU precision")
        if item["attention"] not in ("sdpa", "eager"):
            raise ValueError(f"{name}: invalid attention")
        if item["startlux_backend"] not in ("torch", "gguf", "gguf-stdio"):
            raise ValueError(f"{name}: invalid StartLux backend")
        if item["startlux_backend"].startswith("gguf") and (item["images"] or item["kind"] != "startlux"):
            raise ValueError(f"{name}: GGUF supports StartLux text only")
        if any(type(value) is not int or value < 0 for value in item["cpu_affinity"]):
            raise ValueError(f"{name}: invalid cpu_affinity")
        for key in (
            "threads",
            "context_length",
            "max_batch_tokens",
            "prefill_chunk",
            "max_body_bytes",
            "max_questions",
            "startup_timeout",
            "socket_timeout",
            "inference_timeout",
            "log_max_bytes",
            "log_backups",
            "gpu_required_mb",
        ):
            if type(item[key]) is not int or item[key] <= 0:
                raise ValueError(f"{name}: {key} must be a positive integer")
        if item["idle_unload_seconds"] < 0 or item["gpu_reserve_mb"] < 0:
            raise ValueError(f"{name}: negative idle timeout / GPU reserve")
        if type(item["port"]) is not int or not 1 <= item["port"] <= 65535 or item["port"] in ports:
            raise ValueError(f"{name}: invalid or duplicate port")
        ports.add(item["port"])
        if item["kind"] == "laya":
            if item["long_input"] not in ("window", "reject"):
                raise ValueError(f"{name}: long_input must be window or reject")
            if not 256 <= item["window_length"] <= item["context_length"]:
                raise ValueError(f"{name}: window_length must be 256..context_length")
            if not 1 <= item["head_max_length"] < item["window_length"]:
                raise ValueError(f"{name}: head_max_length must be smaller than window_length")
        result[name] = item
    return result


def preflight(item: dict[str, Any]) -> int:
    root = pathlib.Path(item["path"])
    missing = []
    required = ["config.json"]
    if item["kind"] == "startlux":
        required += ["decision_config.json", "tokenizer.json"]
        index = root / "model.safetensors.index.json"
        if item.get("startlux_backend", "torch").startswith("gguf"):
            for key in ("gguf_file", "native_binary" if item["startlux_backend"] == "gguf-stdio" else "llama_server"):
                if not item.get(key) or not pathlib.Path(item[key]).is_file():
                    raise ValueError(f"GGUF {key} missing: {item.get(key)}")
        else:
            required.append("model.safetensors.index.json")
        if not item.get("startlux_backend", "torch").startswith("gguf") and index.is_file():
            required += sorted(set(json.loads(index.read_text())["weight_map"].values()))
        cfg = root / "config.json"
    else:
        required += ["rl_agent_config.json", "model.safetensors", "encoder/config.json", "tokenizer/tokenizer.json"]
        cfg = root / "encoder/config.json"
    for filename in required:
        if not (root / filename).is_file() or (root / filename).stat().st_size == 0:
            missing.append(str(root / filename))
    if missing:
        raise ValueError("checkpoint incomplete; missing: " + ", ".join(missing))
    raw = json.loads(cfg.read_text())
    native = raw.get("text_config", raw).get("max_position_embeddings")
    if native and item["context_length"] > native:
        raise ValueError(f"context_length={item['context_length']} exceeds native limit {native}")
    if not pathlib.Path(item["python"]).is_file():
        raise ValueError("Python runtime missing: " + item["python"])
    package = "laya" if item["kind"] == "laya" else "startlux_decision"
    if not (pathlib.Path(item["source"]) / package).is_dir():
        raise ValueError("source package missing: " + item["source"])
    return native
