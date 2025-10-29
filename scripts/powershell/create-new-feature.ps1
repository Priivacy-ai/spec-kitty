#!/usr/bin/env pwsh
# Create a new feature
[CmdletBinding()]
param(
    [switch]$Json,
    [string]$FeatureName,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$FeatureDescription
)
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot/common.ps1"

if (-not $FeatureDescription -or $FeatureDescription.Count -eq 0) {
    Write-Error "[spec-kitty] Error: Feature description missing.`nThis script must only run after discovery produces a confirmed intent summary. Return WAITING_FOR_DISCOVERY_INPUT, gather answers, then rerun with the finalized description."
    exit 1
}
$featureDesc = ($FeatureDescription -join ' ').Trim()

# Resolve repository root. Prefer git information when available, but fall back
# to searching for repository markers so the workflow still functions in repositories that
# were initialised with --no-git.
function Find-RepositoryRoot {
    param(
        [string]$StartDir,
        [string[]]$Markers = @('.git', '.kittify')
    )
    $current = Resolve-Path $StartDir
    while ($true) {
        foreach ($marker in $Markers) {
            if (Test-Path (Join-Path $current $marker)) {
                return $current
            }
        }
        $parent = Split-Path $current -Parent
        if ($parent -eq $current) {
            # Reached filesystem root without finding markers
            return $null
        }
        $current = $parent
    }
}
$fallbackRoot = (Find-RepositoryRoot -StartDir $PSScriptRoot)
if (-not $fallbackRoot) {
    Write-Error "Error: Could not determine repository root. Please run this script from within the repository."
    exit 1
}

try {
    $repoRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -eq 0) {
        $hasGit = $true
    } else {
        throw "Git not available"
    }
} catch {
    $repoRoot = $fallbackRoot
    $hasGit = $false
}

Set-Location $repoRoot

$specsDir = Join-Path $repoRoot 'kitty-specs'

$highest = 0
if (Test-Path $specsDir) {
    Get-ChildItem -Path $specsDir -Directory | ForEach-Object {
        if ($_.Name -match '^(\d{3})') {
            $num = [int]$matches[1]
            if ($num -gt $highest) { $highest = $num }
        }
    }
}
$next = $highest + 1
$featureNum = ('{0:000}' -f $next)

$friendlyName = if (![string]::IsNullOrWhiteSpace($FeatureName)) {
    $FeatureName.Trim()
} else {
    $featureDesc.Trim()
}

function ConvertTo-Slug {
    param([string]$InputText)
    $result = $InputText.ToLower() -replace '[^a-z0-9]', '-' -replace '-{2,}', '-' -replace '^-', '' -replace '-$', ''
    return $result
}

$slugSource = ConvertTo-Slug -InputText $friendlyName
if ([string]::IsNullOrWhiteSpace($slugSource)) {
    $slugSource = ConvertTo-Slug -InputText $featureDesc
}

$words = ($slugSource -split '-') | Where-Object { $_ } | Select-Object -First 3
if (-not $words -or $words.Count -eq 0) {
    $words = @('feature')
}
$branchName = "$featureNum-$([string]::Join('-', $words))"

$worktreePath = $null
$worktreeMessage = $null
$worktreeCreated = $false
$targetRoot = $repoRoot

if ($hasGit) {
    $skipWorktree = $repoRoot -like "*\.worktrees\*"
    if (-not $skipWorktree) {
        $worktreeSupported = $true
        try {
            git worktree list | Out-Null
        } catch {
            $worktreeSupported = $false
        }
        if ($worktreeSupported) {
            $gitCommonDir = git rev-parse --git-common-dir 2>$null
            if ($LASTEXITCODE -eq 0 -and $gitCommonDir) {
                $primaryRepoRoot = (Resolve-Path (Join-Path $gitCommonDir '..')).Path
            } else {
                $primaryRepoRoot = $repoRoot
            }
            $worktreeRoot = Join-Path $primaryRepoRoot '.worktrees'
            New-Item -ItemType Directory -Path $worktreeRoot -Force | Out-Null
            $worktreePath = Join-Path $worktreeRoot $branchName
            if (Test-Path $worktreePath) {
                try {
                    $currentWorktreeBranch = git -C $worktreePath rev-parse --abbrev-ref HEAD 2>$null
                    if ($LASTEXITCODE -eq 0 -and ($currentWorktreeBranch -eq $branchName -or $currentWorktreeBranch -eq 'HEAD')) {
                        $targetRoot = (Resolve-Path $worktreePath).Path
                        $worktreeCreated = $true
                        $worktreeMessage = $targetRoot
                        Write-Warning "[spec-kitty] Reusing existing worktree at $targetRoot for $branchName."
                    } else {
                        Write-Warning "[spec-kitty] Existing worktree at $worktreePath is checked out to $currentWorktreeBranch; skipping worktree creation."
                    }
                } catch {
                    Write-Warning "[spec-kitty] Worktree path $worktreePath exists but is not a git worktree; skipping worktree creation."
                }
            } else {
                try {
                    git worktree add $worktreePath -b $branchName | Out-Null
                    $targetRoot = (Resolve-Path $worktreePath).Path
                    $worktreeCreated = $true
                    $worktreeMessage = $targetRoot
                } catch {
                    Write-Warning "[spec-kitty] Unable to create git worktree for $branchName; falling back to in-place checkout."
                }
            }
        } else {
            Write-Warning "[spec-kitty] Git worktree command unavailable; falling back to in-place checkout."
        }
    }

    if (-not $worktreeCreated) {
        $branchExists = $false
        try {
            git show-ref --verify --quiet "refs/heads/$branchName"
            if ($LASTEXITCODE -eq 0) { $branchExists = $true }
        } catch {
            $branchExists = $false
        }
        try {
            if ($branchExists) {
                git checkout $branchName | Out-Null
            } else {
                git checkout -b $branchName | Out-Null
            }
        } catch {
            Write-Error "[spec-kitty] Error: Failed to check out branch $branchName"
            exit 1
        }
    }
} else {
    Write-Warning "[spec-kitty] Warning: Git repository not detected; skipped branch creation for $branchName"
}

$repoRoot = $targetRoot
Set-Location $repoRoot

$missionInfo = $null
try {
    $missionInfo = Get-ActiveMissionInfo -RepoRoot $repoRoot
} catch {
    Write-Warning ("[spec-kitty] " + $_.Exception.Message)
    $defaultMissionPath = Join-Path $repoRoot '.kittify/missions/software-dev'
    $missionInfo = [PSCustomObject]@{
        templates_dir  = Join-Path $defaultMissionPath 'templates'
        spec_template  = Join-Path $defaultMissionPath 'templates/spec-template.md'
    }
}

$specsDir = Join-Path $repoRoot 'kitty-specs'
New-Item -ItemType Directory -Path $specsDir -Force | Out-Null

$featureDir = Join-Path $specsDir $branchName
New-Item -ItemType Directory -Path $featureDir -Force | Out-Null

$specFile = Join-Path $featureDir 'spec.md'
$specTemplateCandidates = @()
if ($missionInfo.spec_template) { $specTemplateCandidates += $missionInfo.spec_template }
$specTemplateCandidates += (Join-Path $repoRoot '.kittify/templates/spec-template.md')
$specTemplateCandidates += (Join-Path $repoRoot 'templates/spec-template.md')

$specTemplateCopied = $false
foreach ($candidate in $specTemplateCandidates) {
    if ($candidate -and (Test-Path $candidate)) {
        Copy-Item $candidate $specFile -Force
        Write-Output "[spec-kitty] Copied spec template from $candidate"
        $specTemplateCopied = $true
        break
    }
}

if (-not $specTemplateCopied) {
    Write-Warning "[spec-kitty] Spec template not found for active mission; creating empty spec.md"
    New-Item -ItemType File -Path $specFile -Force | Out-Null
}

# Set the SPECIFY_FEATURE environment variable for the current session
$env:SPECIFY_FEATURE = $branchName
$env:SPECIFY_FEATURE_NAME = $friendlyName

$metaFile = Join-Path $featureDir 'meta.json'
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$meta = [ordered]@{
    feature_number     = $featureNum
    slug               = $branchName
    friendly_name      = $friendlyName
    source_description = $featureDesc
    created_at         = $timestamp
}
$meta | ConvertTo-Json | Set-Content -Path $metaFile -Encoding UTF8

if ($Json) {
    $obj = [PSCustomObject]@{ 
        BRANCH_NAME = $branchName
        SPEC_FILE = $specFile
        FEATURE_NUM = $featureNum
        FRIENDLY_NAME = $friendlyName
        HAS_GIT = $hasGit
        WORKTREE_PATH = $worktreeMessage
    }
    $obj | ConvertTo-Json -Compress
} else {
    Write-Output "BRANCH_NAME: $branchName"
    Write-Output "SPEC_FILE: $specFile"
    Write-Output "FEATURE_NUM: $featureNum"
    Write-Output "HAS_GIT: $hasGit"
    Write-Output "SPECIFY_FEATURE environment variable set to: $branchName"
    Write-Output "SPECIFY_FEATURE_NAME environment variable set to: $friendlyName"
    if ($worktreeMessage) {
        Write-Output "Git worktree created at: $worktreeMessage"
        Write-Output "Run: Set-Location '$worktreeMessage' before continuing with planning commands."
        Write-Output "Remove when finished: git worktree remove '$worktreeMessage'"
    }
}
