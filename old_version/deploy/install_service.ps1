<#
.SYNOPSIS
    Register ShadBotTrader as a scheduled Windows task (Phase 24, §37).

.DESCRIPTION
    Windows Task Scheduler is used rather than a true Windows Service.
    A real service needs a service wrapper (nssm / pywin32) and runs in
    session 0, where the MetaTrader 5 terminal is NOT reachable — MT5
    talks over a local IPC channel to a terminal running in the user's
    interactive session. A scheduled task in that session can reach it;
    a session-0 service cannot. This is a deliberate choice, not a
    shortcut.

    Two tasks are registered:
      ShadBotTrader-Live    every 5 minutes   the decision loop
      ShadBotTrader-Weekly  Sunday 02:00      dataset refresh + retrain

.EXAMPLE
    .\deploy\install_service.ps1 -WhatIf
    .\deploy\install_service.ps1
    .\deploy\install_service.ps1 -Remove
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Symbol = "XAUUSD",
    [int]$IntervalMinutes = 5,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$LiveTask   = "ShadBotTrader-Live"
$WeeklyTask = "ShadBotTrader-Weekly"

function Write-Step($message) { Write-Host "  $message" -ForegroundColor Cyan }
function Write-Ok($message)   { Write-Host "  [ok] $message" -ForegroundColor Green }
function Write-Warn($message) { Write-Host "  [!] $message" -ForegroundColor Yellow }
function Write-Err($message)  { Write-Host "  [X] $message" -ForegroundColor Red }

Write-Host ""
Write-Host "=== ShadBotTrader — Windows task installation ===" -ForegroundColor White
Write-Host ""

# ---------------------------------------------------------------- removal --
if ($Remove) {
    foreach ($name in @($LiveTask, $WeeklyTask)) {
        $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        if ($existing) {
            if ($PSCmdlet.ShouldProcess($name, "Unregister scheduled task")) {
                Unregister-ScheduledTask -TaskName $name -Confirm:$false
                Write-Ok "removed $name"
            }
        }
        else {
            Write-Step "$name was not registered"
        }
    }
    Write-Host ""
    exit 0
}

# ------------------------------------------------------------ validation --
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Err "Virtual environment not found at $python"
    Write-Host ""
    Write-Host "  Create it first:"
    Write-Host "      py -3.12 -m venv .venv"
    Write-Host "      .\.venv\Scripts\Activate.ps1"
    Write-Host "      pip install -r requirements-dev.txt; pip install -e ."
    exit 1
}
Write-Ok "python: $python"

# The release gate must pass before anything is scheduled. Registering a
# task that cannot run just moves the failure somewhere less visible.
Write-Step "running pre-flight checks ..."
& $python -m ShadBotTrader.deploy_cli preflight --environment production
if ($LASTEXITCODE -ne 0) {
    Write-Err "Pre-flight failed. Fix the problems above before installing."
    exit 1
}
Write-Ok "pre-flight passed"

# ------------------------------------------------------------- live task --
$liveAction = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "scripts\run_service.py --demo --interval $($IntervalMinutes * 60) --symbol $Symbol" `
    -WorkingDirectory $ProjectRoot

$liveTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)

# RestartCount/RestartInterval give the "process management" of §37:
# a crashed run is retried, but not forever.
$liveSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 23)

if ($PSCmdlet.ShouldProcess($LiveTask, "Register scheduled task")) {
    Register-ScheduledTask -TaskName $LiveTask `
        -Action $liveAction -Trigger $liveTrigger -Settings $liveSettings `
        -Description "ShadBotTrader live decision loop (every $IntervalMinutes minutes)" `
        -Force | Out-Null
    Write-Ok "registered $LiveTask (every $IntervalMinutes minutes)"
}

# ----------------------------------------------------------- weekly task --
$weeklyAction = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "scripts\run_weekly_update.py --symbol $Symbol" `
    -WorkingDirectory $ProjectRoot

$weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "02:00"

$weeklySettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6)

if ($PSCmdlet.ShouldProcess($WeeklyTask, "Register scheduled task")) {
    Register-ScheduledTask -TaskName $WeeklyTask `
        -Action $weeklyAction -Trigger $weeklyTrigger -Settings $weeklySettings `
        -Description "ShadBotTrader weekly dataset refresh and model retraining" `
        -Force | Out-Null
    Write-Ok "registered $WeeklyTask (Sundays 02:00)"
}

Write-Host ""
Write-Host "=== Installed ===" -ForegroundColor White
Write-Host ""
Write-Host "  Inspect :  Get-ScheduledTask -TaskName ShadBotTrader-*"
Write-Host "  Run now :  Start-ScheduledTask -TaskName $LiveTask"
Write-Host "  History :  Get-ScheduledTaskInfo -TaskName $LiveTask"
Write-Host "  Remove  :  .\deploy\install_service.ps1 -Remove"
Write-Host ""
Write-Warn "MetaTrader 5 must be running and logged in for live data."
Write-Host ""
