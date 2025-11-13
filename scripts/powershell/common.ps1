#!/usr/bin/env pwsh
# Common PowerShell functions analogous to common.sh

function Get-RepoRoot {
    try {
        $result = git rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $result
        }
    } catch {
        # Git command failed
    }
    
    # Fall back to script location for non-git repos
    return (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
}

function Get-CurrentBranch {
    # First check if SPECIFY_FEATURE environment variable is set
    if ($env:SPECIFY_FEATURE) {
        return $env:SPECIFY_FEATURE
    }
    
    # Then check git if available
    try {
        $result = git rev-parse --abbrev-ref HEAD 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $result
        }
    } catch {
        # Git command failed
    }
    
    # For non-git repos, try to find the latest feature directory
    $repoRoot = Get-RepoRoot
    $specsDir = Join-Path $repoRoot "specs"
    
    if (Test-Path $specsDir) {
        $latestFeature = ""
        $highest = 0
        
        Get-ChildItem -Path $specsDir -Directory | ForEach-Object {
            if ($_.Name -match '^(\d{3})-') {
                $num = [int]$matches[1]
                if ($num -gt $highest) {
                    $highest = $num
                    $latestFeature = $_.Name
                }
            }
        }
        
        if ($latestFeature) {
            return $latestFeature
        }
    }
    
    # Final fallback
    return "main"
}

function Test-HasGit {
    try {
        git rev-parse --show-toplevel 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-FeatureBranch {
    param(
        [string]$Branch,
        [bool]$HasGit = $true
    )
    
    # For non-git repos, we can't enforce branch naming but still provide output
    if (-not $HasGit) {
        Write-Warning "[spec-kitty] Warning: Git repository not detected; skipped branch validation"
        return $true
    }
    
    if ($Branch -notmatch '^[0-9]{3}-') {
        Write-Output "ERROR: Not on a feature branch. Current branch: $Branch"
        Write-Output "Feature branches should be named like: 001-feature-name"
        return $false
    }
    return $true
}

function Get-FeatureDir {
    param([string]$RepoRoot, [string]$Branch)
    Join-Path $RepoRoot "kitty-specs/$Branch"
}

function Get-ActiveMissionInfo {
    param([string]$RepoRoot)

    $python = Get-Command python3 -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        throw "[spec-kitty] python interpreter not found; mission detection unavailable"
    }

    $script = @"
from pathlib import Path
import json
import sys

try:
    from specify_cli.mission import get_active_mission, MissionNotFoundError  # type: ignore
except Exception as exc:  # pragma: no cover - defensive
    print(json.dumps({'error': f'Unable to import mission module: {exc}'}))
    sys.exit(1)

repo_root = Path(sys.argv[1])
try:
    mission = get_active_mission(repo_root)
except MissionNotFoundError as exc:
    print(json.dumps({'error': str(exc)}))
    sys.exit(1)

templates_dir = mission.templates_dir
payload = {
    'key': mission.path.name,
    'path': str(mission.path),
    'name': mission.name,
    'templates_dir': str(templates_dir),
    'commands_dir': str(mission.commands_dir),
    'constitution_dir': str(mission.constitution_dir),
    'spec_template': str(templates_dir / 'spec-template.md'),
    'plan_template': str(templates_dir / 'plan-template.md'),
    'tasks_template': str(templates_dir / 'tasks-template.md'),
    'task_prompt_template': str(templates_dir / 'task-prompt-template.md'),
}
print(json.dumps(payload))
"@

    $output = & $python.Path -c $script $RepoRoot 2>&1
    if ($LASTEXITCODE -ne 0) {
        $message = ($output | Out-String).Trim()
        if (-not $message) {
            $message = "Unknown mission detection failure"
        }
        throw $message
    }

    $json = ($output | Out-String).Trim()
    if (-not $json) {
        throw "Mission detection returned empty output"
    }

    return $json | ConvertFrom-Json
}

function Get-FeaturePathsEnv {
    $repoRoot = Get-RepoRoot
    $currentBranch = Get-CurrentBranch
    $hasGit = Test-HasGit
    $featureDir = Get-FeatureDir -RepoRoot $repoRoot -Branch $currentBranch
    $missionInfo = $null

    try {
        $missionInfo = Get-ActiveMissionInfo -RepoRoot $repoRoot
    } catch {
        Write-Warning ("[spec-kitty] " + $_.Exception.Message)
        $defaultMissionPath = Join-Path $repoRoot ".kittify/missions/software-dev"
        $missionInfo = [PSCustomObject]@{
            key                 = "software-dev"
            path                = $defaultMissionPath
            name                = "Software Dev Kitty"
            templates_dir       = Join-Path $defaultMissionPath "templates"
            commands_dir        = Join-Path $defaultMissionPath "commands"
            constitution_dir    = Join-Path $defaultMissionPath "constitution"
            spec_template       = Join-Path $defaultMissionPath "templates/spec-template.md"
            plan_template       = Join-Path $defaultMissionPath "templates/plan-template.md"
            tasks_template      = Join-Path $defaultMissionPath "templates/tasks-template.md"
            task_prompt_template = Join-Path $defaultMissionPath "templates/task-prompt-template.md"
        }
    }
    
    [PSCustomObject]@{
        REPO_ROOT     = $repoRoot
        CURRENT_BRANCH = $currentBranch
        HAS_GIT       = $hasGit
        FEATURE_DIR   = $featureDir
        FEATURE_SPEC  = Join-Path $featureDir 'spec.md'
        IMPL_PLAN     = Join-Path $featureDir 'plan.md'
        TASKS         = Join-Path $featureDir 'tasks.md'
        RESEARCH      = Join-Path $featureDir 'research.md'
        DATA_MODEL    = Join-Path $featureDir 'data-model.md'
        QUICKSTART    = Join-Path $featureDir 'quickstart.md'
        CONTRACTS_DIR = Join-Path $featureDir 'contracts'
        MISSION_KEY   = $missionInfo.key
        MISSION_PATH  = $missionInfo.path
        MISSION_NAME  = $missionInfo.name
        MISSION_TEMPLATES_DIR = $missionInfo.templates_dir
        MISSION_COMMANDS_DIR = $missionInfo.commands_dir
        MISSION_CONSTITUTION_DIR = $missionInfo.constitution_dir
        MISSION_SPEC_TEMPLATE = $missionInfo.spec_template
        MISSION_PLAN_TEMPLATE = $missionInfo.plan_template
        MISSION_TASKS_TEMPLATE = $missionInfo.tasks_template
        MISSION_TASK_PROMPT_TEMPLATE = $missionInfo.task_prompt_template
    }
}

function Test-FileExists {
    param([string]$Path, [string]$Description)
    if (Test-Path -Path $Path -PathType Leaf) {
        Write-Output "  ✓ $Description"
        return $true
    } else {
        Write-Output "  ✗ $Description"
        return $false
    }
}

function Test-DirHasFiles {
    param([string]$Path, [string]$Description)
    if ((Test-Path -Path $Path -PathType Container) -and (Get-ChildItem -Path $Path -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer } | Select-Object -First 1)) {
        Write-Output "  ✓ $Description"
        return $true
    } else {
        Write-Output "  ✗ $Description"
        return $false
    }
}
