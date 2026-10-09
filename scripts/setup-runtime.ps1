param([ValidateSet("cpu", "cu130", "cu126")][string]$Backend = "cpu")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$env:UV_CACHE_DIR = Join-Path $ProjectRoot ".uv-cache"
$RuntimeDir = Join-Path $ProjectRoot ".venv-$Backend"
$RuntimePython = Join-Path $RuntimeDir "Scripts\python.exe"
if (-not (Test-Path $RuntimePython)) {
    & uv venv $RuntimeDir --python 3.12
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& uv pip install --python $RuntimePython "torch>=2.10,<2.15" torchvision --index-url "https://download.pytorch.org/whl/$Backend"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& uv pip install --python $RuntimePython "transformers==5.19.0" safetensors huggingface_hub pillow numpy -r (Join-Path $ProjectRoot "configs/requirements-http.txt")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $RuntimePython -c "import torch,fastapi,psutil; print('torch',torch.__version__,'CUDA',torch.cuda.is_available())"
exit $LASTEXITCODE
