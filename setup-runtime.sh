#!/usr/bin/env bash
# 创建独立运行环境，不替换原有 CPU 环境。显式运行本脚本才联网安装。
# ./setup-runtime.sh cpu|cu130|cu126 [--fast-kernels]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="${1:-cpu}"
case "$BACKEND" in cpu|cu130|cu126) ;; *) echo '用法: setup-runtime.sh cpu|cu130|cu126 [--fast-kernels]' >&2; exit 2 ;; esac
export UV_CACHE_DIR="$SCRIPT_DIR/.uv-cache"
RUNTIME_DIR="$SCRIPT_DIR/.venv-$BACKEND"
if [[ ! -x "$RUNTIME_DIR/bin/python" ]]; then uv venv "$RUNTIME_DIR" --python 3.12; fi
uv pip install --python "$RUNTIME_DIR/bin/python" 'torch>=2.10,<2.15' torchvision \
  --index-url "https://download.pytorch.org/whl/$BACKEND"
uv pip install --python "$RUNTIME_DIR/bin/python" 'transformers==5.19.0' safetensors \
  huggingface_hub pillow numpy -r "$SCRIPT_DIR/requirements-http.txt"
if [[ "${2:-}" == "--fast-kernels" ]]; then
  uv pip install --python "$RUNTIME_DIR/bin/python" packaging ninja
  uv pip install --python "$RUNTIME_DIR/bin/python" flash-linear-attention causal-conv1d --no-build-isolation
fi
"$RUNTIME_DIR/bin/python" -c 'import torch,fastapi; print("torch",torch.__version__,"CUDA",torch.cuda.is_available(),"FastAPI",fastapi.__version__)'
echo "请在 config.toml 的模型配置中将 python 改为 $RUNTIME_DIR/bin/python，并删除 dependency_paths 项。"
