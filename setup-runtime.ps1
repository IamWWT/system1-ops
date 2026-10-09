param([ValidateSet("cpu", "cu130", "cu126")][string]$Backend = "cpu")
$ErrorActionPreference = "Stop"
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot ".uv-cache"
$RuntimeDir = Join-Path $PSScriptRoot ".venv"
$RuntimePython = Join-Path $RuntimeDir "Scripts\python.exe"
if (-not (Test-Path $RuntimePython)) {
    & uv venv $RuntimeDir --python 3.12
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& uv pip install --python $RuntimePython "torch>=2.13,<2.15" torchvision --index-url "https://download.pytorch.org/whl/$Backend"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& uv pip install --python $RuntimePython "transformers==5.19.0" safetensors huggingface_hub pillow numpy -r (Join-Path $PSScriptRoot "requirements-http.txt")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $RuntimePython -c "import torch,fastapi,psutil; print('torch',torch.__version__,'CUDA',torch.cuda.is_available())"
exit $LASTEXITCODE
