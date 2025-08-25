# dev.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-Not (Test-Path .\.venv\Scripts\Activate.ps1)) {
  py -m venv .venv
}
.\.venv\Scripts\Activate.ps1

py -m pip install --upgrade pip
if (Test-Path .\requirements.txt) {
  py -m pip install -r requirements.txt
}
py -m pip install pytest pytest-cov pytest-watch black ruff pre-commit

Write-Host "Dev environment ready. Examples:"
Write-Host "  ptw -- -q --maxfail=1"
Write-Host "  py main.py"
