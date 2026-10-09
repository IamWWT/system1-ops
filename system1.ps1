$Arguments = @($args)
$ErrorActionPreference = "Stop"
$RuntimePython = $env:SYSTEM1_PYTHON
if (-not $RuntimePython) {
    $LocalPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path $LocalPython) { $RuntimePython = $LocalPython }
    else { $RuntimePython = "python" }
}
& $RuntimePython (Join-Path $PSScriptRoot "manage.py") @Arguments
exit $LASTEXITCODE
