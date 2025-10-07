#!/usr/bin/env pwsh
param(
    [Parameter(Mandatory=$true)] [string]$TaskId,
    [Parameter(Mandatory=$true)] [ValidateSet('done','pending')] [string]$Status,
    [string]$TasksFile
)

. "$PSScriptRoot/common.ps1"

$paths = Get-FeaturePathsEnv
if (-not $TasksFile) {
    $TasksFile = $paths.TASKS
}

if (-not (Test-Path -Path $TasksFile -PathType Leaf)) {
    Write-Error "tasks file not found: $TasksFile"
    exit 1
}

$content = Get-Content -Path $TasksFile -Raw
$escapedTaskId = [regex]::Escape($TaskId)
$pattern = "^(\s*-\s*)\[[ xX]\]\s+($escapedTaskId)(\b.*)$"
$box = if ($Status -eq 'done') { '[X]' } else { '[ ]' }

$replacement = [System.Func[System.Text.RegularExpressions.Match,string]]{
    param($match)
    return "{0}{1} {2}{3}" -f $match.Groups[1].Value, $box, $match.Groups[2].Value, $match.Groups[3].Value
}

$regex = [regex]::new($pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
$newContent = $regex.Replace($content, $replacement, 1)

if ($newContent -eq $content) {
    Write-Error "Task ID $TaskId not found in $TasksFile"
    exit 1
}

Set-Content -Path $TasksFile -Value $newContent
Write-Output "Updated $TaskId to $Status in $TasksFile"
