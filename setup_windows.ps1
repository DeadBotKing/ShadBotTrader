# ShadBotTrader - Windows setup (PowerShell)
#
# Usage:
#   cd C:\Users\DeadBotKing\Desktop\ShadBotTrader
#   .\setup_windows.ps1
#
# Fixes the classic "did not find executable at 'C:\Python314\python.exe'"
# error, which happens when an OLD venv (built with a now-uninstalled Python)
# is still active. Rebuilds cleanly on Python 3.12 and installs TensorFlow.
#
# Note: native Windows has no TF GPU support since TF 2.11 -> use WSL2 for GPU.

$ErrorActionPreference = "Stop"
$PyVer = "3.12"

Write-Host "=== ShadBotTrader Windows Setup ===" -ForegroundColor Cyan

# --- 0. Detect that we are running INSIDE a virtualenv ----------------------
if ($env:VIRTUAL_ENV) {
    Write-Host "`n[!] A virtual environment is currently ACTIVE:" -ForegroundColor Red
    Write-Host "      $env:VIRTUAL_ENV" -ForegroundColor Red
    Write-Host @"

    This is the cause of the 'did not find executable at C:\Python314\python.exe'
    error: inside an active venv, 'python' resolves to that venv's shim, which
    points at its (now deleted) base interpreter.

    Fix - run this first, then re-run the script:

        deactivate

    If 'deactivate' errors out, just close this PowerShell window and open a
    fresh one, then re-run:  .\setup_windows.ps1

"@ -ForegroundColor Yellow
    exit 1
}

# --- 1. Locate a real Python 3.12 via the py launcher -----------------------
Write-Host "`n[1/6] Locating Python $PyVer ..." -ForegroundColor Yellow
try {
    $null = & py "-$PyVer" --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "py -$PyVer failed" }
} catch {
    Write-Host "ERROR: Python $PyVer not found via the 'py' launcher." -ForegroundColor Red
    Write-Host "Installed versions:" -ForegroundColor Red
    try { & py -0p } catch { Write-Host "  (py launcher not available at all)" -ForegroundColor Red }
    Write-Host "`nInstall Python $PyVer (64-bit) from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
$PyPath = (& py "-$PyVer" -c "import sys; print(sys.executable)").Trim()
$PyBits = (& py "-$PyVer" -c "import struct; print(struct.calcsize('P')*8)").Trim()
$PyFull = (& py "-$PyVer" -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
Write-Host "  Found Python $PyFull ($PyBits-bit)" -ForegroundColor Green
Write-Host "  at $PyPath" -ForegroundColor DarkGray

if ($PyBits -ne "64") {
    Write-Host "ERROR: TensorFlow requires 64-bit Python. Yours is $PyBits-bit." -ForegroundColor Red
    exit 1
}

# --- 2. Remove stale/broken virtual environments ----------------------------
Write-Host "`n[2/6] Removing stale virtual environments ..." -ForegroundColor Yellow
$removed = $false
foreach ($dir in @(".venv", "Venv", "venv", "env")) {
    if (Test-Path $dir) {
        Write-Host "  Deleting '$dir' ..." -ForegroundColor DarkGray
        Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
        $removed = $true
    }
}
if (-not $removed) { Write-Host "  None found." -ForegroundColor DarkGray }
Write-Host "  Done." -ForegroundColor Green

# --- 3. Create a fresh venv -------------------------------------------------
Write-Host "`n[3/6] Creating .venv with Python $PyFull ..." -ForegroundColor Yellow
& py "-$PyVer" -m venv .venv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "ERROR: venv creation failed." -ForegroundColor Red
    exit 1
}
$VPy = ".\.venv\Scripts\python.exe"
Write-Host "  Created: $((& $VPy --version) -join '')" -ForegroundColor Green

# --- 4. Upgrade the packaging toolchain -------------------------------------
Write-Host "`n[4/6] Upgrading pip / setuptools / wheel ..." -ForegroundColor Yellow
& $VPy -m pip install --upgrade pip setuptools wheel --quiet
Write-Host "  Done." -ForegroundColor Green

# --- 5. Install the project (editable) + dev tools --------------------------
Write-Host "`n[5/6] Installing ShadBotTrader + dev extras ..." -ForegroundColor Yellow
& $VPy -m pip install -e ".[dev]"
Write-Host "  Done." -ForegroundColor Green

# --- 6. TensorFlow (CPU build - the correct choice on native Windows) -------
Write-Host "`n[6/6] Installing TensorFlow (CPU, ~350 MB, be patient) ..." -ForegroundColor Yellow
Write-Host "  Native Windows has no GPU support since TF 2.11; use WSL2 for GPU." -ForegroundColor DarkGray
& $VPy -m pip install "tensorflow-cpu>=2.16"
Write-Host "  Done." -ForegroundColor Green

# --- Verify -----------------------------------------------------------------
Write-Host "`n=== Verification ===" -ForegroundColor Cyan
& $VPy -c @"
import sys, tensorflow as tf, numpy, pandas, pyarrow, pywt, ShadBotTrader
print(f'Python       : {sys.version.split()[0]}')
print(f'TensorFlow   : {tf.__version__}')
print(f'NumPy        : {numpy.__version__}')
print(f'pandas       : {pandas.__version__}')
print(f'pyarrow      : {pyarrow.__version__}')
print(f'PyWavelets   : {pywt.__version__}')
print('ShadBotTrader: import OK')
"@

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host ""
Write-Host "  Activate  :  .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  Run tests :  python -m pytest" -ForegroundColor Cyan
Write-Host "  With TF   :  `$env:RUN_TF=1; python -m pytest" -ForegroundColor Cyan
