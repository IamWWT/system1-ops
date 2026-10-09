"""Fetch pinned inference sources and optional local weights; never starts a service."""

import argparse
import shutil
import subprocess
from typing import Any

from .common import ROOT

SOURCES = {
    "laya": ("https://github.com/NandhaKishorM/laya.git", "1adc59f7e371deb601fcfa18a14e25db238addcc"),
    "startlux": ("https://github.com/StartLuxLabs/StartLux-Decision.git", "0e7a2e81b9c92756e26d8edd843a44d50e362669"),
    "llama.cpp": ("https://github.com/ggml-org/llama.cpp.git", "89fe24240548456477870b2a627cd8021fea1e39"),
}
WEIGHTS = {
    "laya": "convaiinnovations/laya",
    "startlux-0.8b": "startlux-models/StartLux-Decision-0.8B",
    "startlux-4b": "startlux-models/StartLux-Decision-4B",
    "startlux-0.8b-q8": "startlux-models/StartLux-Decision-0.8B-Q8_0-GGUF",
    "startlux-4b-q8": "startlux-models/StartLux-Decision-4B-Q8_0-GGUF",
    "startlux-0.8b-q4": "startlux-models/StartLux-Decision-0.8B-Q4_K_M-GGUF",
    "startlux-4b-q4": "startlux-models/StartLux-Decision-4B-Q4_K_M-GGUF",
}


def source(name: Any) -> Any:
    url, revision = SOURCES[name]
    directory = ROOT / "vendor" / name
    created = not directory.exists()
    if created:
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", url, str(directory)], check=True)
    head = subprocess.run(["git", "-C", str(directory), "rev-parse", "HEAD"], capture_output=True, text=True)
    if not created and head.returncode == 0 and head.stdout.strip() == revision:
        return directory
    # Do not discard edits or move an existing checkout to a new revision silently.
    dirty = subprocess.run(
        ["git", "-C", str(directory), "status", "--porcelain"], capture_output=True, text=True, check=True
    )
    if not created and dirty.stdout.strip() and head.returncode == 0:
        raise RuntimeError(f"source checkout has local edits: {directory}")
    subprocess.run(["git", "-C", str(directory), "fetch", "origin", revision], check=True)
    subprocess.run(["git", "-C", str(directory), "checkout", "--detach", revision], check=True)
    return directory


def main() -> Any:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", action="store_true")
    parser.add_argument("--models", nargs="+", choices=tuple(WEIGHTS))
    parser.add_argument("--revision", default="main", help="model revision; use a reviewed SHA for reproducibility")
    parser.add_argument("--build-native", choices=("cpu", "cuda"))
    args = parser.parse_args()
    if args.sources:
        for name in ("laya", "startlux"):
            source(name)
    if args.models:
        hf = shutil.which("hf")
        if not hf:
            raise RuntimeError("hf CLI missing; install huggingface_hub in this runtime")
        for name in args.models:
            subprocess.run(
                [
                    hf,
                    "download",
                    WEIGHTS[name],
                    "--revision",
                    args.revision,
                    "--local-dir",
                    str(ROOT / "models" / name),
                ],
                check=True,
            )
    if args.build_native:
        directory = source("llama.cpp")
        build = directory / ("build-" + args.build_native)
        subprocess.run(
            [
                "cmake",
                "-S",
                str(directory),
                "-B",
                str(build),
                "-DCMAKE_BUILD_TYPE=Release",
                "-DGGML_NATIVE=OFF",
                "-DGGML_BACKEND_DL=ON",
                "-DGGML_CPU_ALL_VARIANTS=ON",
                "-DLLAMA_BUILD_TESTS=OFF",
                "-DLLAMA_BUILD_EXAMPLES=OFF",
                "-DLLAMA_BUILD_SERVER=ON",
                "-DGGML_CUDA=" + ("ON" if args.build_native == "cuda" else "OFF"),
            ],
            check=True,
        )
        subprocess.run(
            ["cmake", "--build", str(build), "--config", "Release", "--target", "llama-server", "-j", "4"], check=True
        )
        bridge = ROOT / ".native-build" / "bridge"
        subprocess.run(
            [
                "cmake",
                "-S",
                str(ROOT / "native"),
                "-B",
                str(bridge),
                "-DCMAKE_BUILD_TYPE=Release",
                "-DLLAMA_SOURCE_DIR=" + str(directory),
                "-DLLAMA_BUILD_DIR=" + str(build),
            ],
            check=True,
        )
        subprocess.run(["cmake", "--build", str(bridge), "--config", "Release", "-j", "4"], check=True)
    local = ROOT / "config.toml"
    if not local.exists():
        shutil.copyfile(ROOT / "configs" / "example.toml", local)


if __name__ == "__main__":
    main()
