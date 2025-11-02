param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Remaining
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path (Join-Path $scriptDir '..') 'common.ps1'
if (Test-Path $common) {
    . $common
    if (-not $env:SPEC_KITTY_AUTORETRY) {
        $repoRoot = Get-RepoRoot
        $currentBranch = Get-CurrentBranch
        if ($currentBranch -notmatch '^[0-9]{3}-') {
            $latest = Find-LatestFeatureWorktree $repoRoot
            if ($latest) {
                Write-Error "[spec-kitty] Auto-running merge inside $latest (current branch: $currentBranch)" -ErrorAction SilentlyContinue
                $env:SPEC_KITTY_AUTORETRY = '1'
                Push-Location $latest
                try {
                    & $MyInvocation.MyCommand.Path @Remaining
                } finally {
                    Pop-Location
                    $env:SPEC_KITTY_AUTORETRY = $null
                }
                return
            }
        }
    }
}

$helper = Join-Path (Join-Path $scriptDir '..') 'tasks/tasks_cli.py'
if (-not (Test-Path $helper)) {
    Write-Error "tasks_cli.py not found at $helper"
    exit 1
}

$python = Get-Python3
& $python $helper merge @Remaining
