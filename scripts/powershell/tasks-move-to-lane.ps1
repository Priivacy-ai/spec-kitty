#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    # Spec-kitty style named parameters
    [string]$FeatureName,
    [string]$TaskId,
    [string]$TargetLane,
    [string]$Note,
    [string]$Agent,
    [string]$Assignee,
    [string]$ShellPid,
    [string]$Timestamp,
    [switch]$DryRun,
    [switch]$Force,

    # Any extra args we haven't modeled explicitly
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Error "python3 is required but was not found on PATH."
    exit 1
}

$scriptDir = Split-Path -Parent $PSCommandPath
$helper = Join-Path $scriptDir '..' | Join-Path -ChildPath 'tasks/tasks_cli.py'

if (-not (Test-Path $helper)) {
    Write-Error "tasks_cli helper not found at $helper"
    exit 1
}

# If called with named parameters (the spec-kitty pattern), build the proper
# CLI for tasks_cli.py:
#   python3 tasks_cli.py move <feature> <work_package> <lane> [--note ...]
$cliArgs = @()

if ($FeatureName -or $TaskId -or $TargetLane) {
    if (-not $FeatureName) {
        Write-Error "FeatureName is required when using named parameters."
        exit 1
    }
    if (-not $TaskId) {
        Write-Error "TaskId is required when using named parameters."
        exit 1
    }
    if (-not $TargetLane) {
        Write-Error "TargetLane is required when using named parameters."
        exit 1
    }

    # Positional args for the 'move' subcommand
    $cliArgs += @(
        "move",
        $FeatureName,
        $TaskId,
        $TargetLane
    )

    # Optional flags mapped to tasks_cli.py's expectations
    if ($Note)      { $cliArgs += @("--note",       $Note) }
    if ($Agent)     { $cliArgs += @("--agent",      $Agent) }
    if ($Assignee)  { $cliArgs += @("--assignee",   $Assignee) }
    if ($ShellPid)  { $cliArgs += @("--shell-pid",  $ShellPid) }
    if ($Timestamp) { $cliArgs += @("--timestamp",  $Timestamp) }
    if ($DryRun.IsPresent) { $cliArgs += "--dry-run" }
    if ($Force.IsPresent)  { $cliArgs += "--force" }

    # Pass through any additional arguments if present
    if ($Args) { $cliArgs += $Args }
}
else {
    # Fallback: if no named params were used, assume Args already contain
    # the correct CLI form for tasks_cli.py (feature, work_package, lane, etc.)
    $cliArgs = @("move") + $Args
}

python3 $helper @cliArgs
