<#
.SYNOPSIS
  Runs the whole FieldPilot planner pipeline on the Windows training machine (RTX 5060 Ti).

.DESCRIPTION
  1. Installs uv if it is missing (uv then installs Python 3.12 by itself).
  2. Creates the environment from uv.lock: PyTorch for CUDA 12.8, ONNX, rasterio.
  3. Runs the tests, including the leakage test, which needs torch.
  4. Keeps Windows awake while it runs (no system setting is changed).
  5. Runs every stage: env, download, clean, labels, tune, train, evaluate,
     holdout, export. A stage whose output exists is skipped, so after a power
     cut or a closed window, running the script again continues where it stopped.

  Logs: data\planner\logs\ | Runs: data\planner\runs\ | Bundle: planner\models\

.EXAMPLE
  # From the repository root (or double-click train_windows.bat):
  powershell -NoProfile -ExecutionPolicy Bypass -File planner\train_windows.ps1

.EXAMPLE
  # Only some stages, or re-run one:
  powershell -NoProfile -ExecutionPolicy Bypass -File planner\train_windows.ps1 -Stages train,evaluate -Force train
#>
param(
    [string[]]$Stages = @("all"),
    [string[]]$Force = @(),
    [string]$Run = "main"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PYTHONUTF8 = "1"   # municipality names have accents; keep the console and logs in UTF-8

function Step([string]$Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }

Step "Checking the NVIDIA driver"
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) { & nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv }
else { Write-Warning "nvidia-smi not found: install the NVIDIA driver 570 or newer before training." }

Step "Checking uv"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv 0.12.3 (https://docs.astral.sh/uv/)"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/0.12.3/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
uv --version

Step "Creating the environment from uv.lock (first time: several GB for PyTorch CUDA 12.8)"
uv sync --frozen --extra data --extra train
if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

Step "Running the planner's tests (includes the leakage test, which needs torch)"
uv run --frozen pytest -q
if ($LASTEXITCODE -ne 0) { throw "tests failed: do not train on a broken pipeline" }

Add-Type -Namespace FieldPilot -Name Power -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("kernel32.dll")]
public static extern uint SetThreadExecutionState(uint flags);
"@
$ES_CONTINUOUS = [uint32]"0x80000000"
$ES_SYSTEM_REQUIRED = [uint32]"0x00000001"

Step "Running the pipeline: $($Stages -join ', ')"
[FieldPilot.Power]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED) | Out-Null
try {
    $cliArgs = @($Stages) + @("--run", $Run)
    if ($Force.Count -gt 0) { $cliArgs += @("--force") + $Force }
    uv run --frozen python -m fieldpilot_planner @cliArgs
    if ($LASTEXITCODE -ne 0) { throw "the pipeline stopped with exit code $LASTEXITCODE; run the script again to continue" }
}
finally {
    [FieldPilot.Power]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
}

Step "Done"
Write-Host "Metrics:  ..\data\planner\runs\$Run\metrics.json"
Write-Host "Bundle:   models\ (commit it, with its MODEL_CARD.md)"
