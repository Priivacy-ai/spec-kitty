$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")

$env:CODEX_HOME = Join-Path $RepoRoot ".codex"
$CodexCommand = Get-Command codex -CommandType Application -ErrorAction Stop
$CodexPath = $CodexCommand.Source

$activate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    . $activate
}

& $CodexPath @args
