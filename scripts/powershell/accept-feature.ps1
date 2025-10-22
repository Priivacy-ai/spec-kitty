#!/usr/bin/env pwsh
[CmdletBinding()]
param(
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

python3 $helper accept @Args
