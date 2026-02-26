---
title: Set Up a Codex Launcher for Spec Kitty
description: Configure a `kitty_cdx` launcher that uses repository-local `.codex` state and activates `.venv` when available.
---

# Set Up a Codex Launcher for Spec Kitty

Use this guide to launch `codex` with repository-local configuration by default:

- `CODEX_HOME` points at this repo's `.codex`
- local Python environments are activated when available
- tooling-specific setup scripts live under `scripts/tool_configs`

## Linux / Mac Instructions

### Prerequisites

- You are working in the `spec-kitty` repository root.
- `codex` is installed and available on your `PATH`.
- You have shell startup files (`~/.bash_aliases`, `~/.bashrc`, or `~/.zshrc`).

### 1. Add the shared Python environment helper

Create `scripts/tool_configs/python_environment.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

activate_python_environment() {
  local repo_root="${1:-$(pwd)}"
  local venv_dir="${repo_root}/.venv"
  local activate_script="${venv_dir}/bin/activate"

  if [[ -f "${activate_script}" ]]; then
    set +u
    . "${activate_script}"
    set -u
  fi
}
```

This function is reusable for other tooling launch scripts.

### 2. Configure the launcher

Create `scripts/tool_configs/kitty-cdx.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

export CODEX_HOME="${REPO_ROOT}/.codex"
CODEX_BIN="$(type -P codex || true)"

if [[ -z "${CODEX_BIN}" ]]; then
  echo "codex executable was not found in PATH" >&2
  exit 127
fi

. "${SCRIPT_DIR}/python_environment.sh"
activate_python_environment "${REPO_ROOT}"

exec "${CODEX_BIN}" "$@"
```

Make it executable:

```bash
chmod +x scripts/tool_configs/kitty-cdx.sh
```

### 3. Create a dedicated `kittyrc` alias file

Create `~/.kittyrc`:

```bash
# Kitty shell customizations
alias kitty_cdx='$CODE_DIRECTORY/spec-kitty/scripts/tool_configs/kitty-cdx.sh'
```

### 4. Source `kittyrc` from one startup file only

To avoid duplicate chain-loading, add this to exactly one file. In this setup, use `~/.bash_aliases`:

```bash
[ -f "$HOME/.kittyrc" ] && source "$HOME/.kittyrc"
```

If your `~/.zshrc` already sources `~/.bash_aliases`, this keeps the setup centralized.

### 5. Optional: Add short aliases for `prompts:spec-kitty.*`

Codex prompt files in `.codex/prompts` are surfaced with the `prompts:` namespace.
If you want shorter commands, add wrapper aliases in `~/.kittyrc`:

```bash
alias sk_spec='kitty_cdx "prompts:spec-kitty.specify"'
alias sk_plan='kitty_cdx "prompts:spec-kitty.plan"'
alias sk_tasks='kitty_cdx "prompts:spec-kitty.tasks"'
alias sk_impl='kitty_cdx "prompts:spec-kitty.implement"'
alias sk_review='kitty_cdx "prompts:spec-kitty.review"'
alias sk_merge='kitty_cdx "prompts:spec-kitty.merge"'
alias sk_status='kitty_cdx "prompts:spec-kitty.status"'
```

## Windows Instructions

### Prerequisites

- You are working in the `spec-kitty` repository root.
- `codex` is installed and available on your `PATH`.
- PowerShell is your active shell.

### 1. Add a PowerShell launcher script

Create `scripts/tool_configs/kitty-cdx.ps1`:

```powershell
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\\..")

$env:CODEX_HOME = Join-Path $RepoRoot ".codex"
$CodexCommand = Get-Command codex -CommandType Application -ErrorAction Stop
$CodexPath = $CodexCommand.Source

$activate = Join-Path $RepoRoot ".venv\\Scripts\\Activate.ps1"
if (Test-Path $activate) {
    . $activate
}

& $CodexPath @args
```

### 2. Add a `kitty_cdx` function in your PowerShell profile

Open your profile:

```powershell
if (!(Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }
notepad $PROFILE
```

Add this function (update the path for your machine):

```powershell
function kitty_cdx {
    & "C:\path\to\spec-kitty\scripts\tool_configs\kitty-cdx.ps1" @args
}
```

Reload your profile:

```powershell
. $PROFILE
```

### 3. If script execution is blocked

Run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Verification

Linux/macOS:

```bash
source ~/.bashrc 2>/dev/null || true
source ~/.zshrc 2>/dev/null || true
type kitty_cdx
kitty_cdx --help
```

Windows PowerShell:

```powershell
. $PROFILE
Get-Command kitty_cdx
kitty_cdx --help
```

Expected result:

- `kitty_cdx` resolves to the launcher script
- Codex launches with repo `.codex` state
- if a local `.venv` exists, environment activation is applied before launch

## Troubleshooting

### `kitty_cdx: command not found`

- **Symptoms**: shell does not recognize the alias or function.
- **Cause**: `~/.kittyrc`/profile is not sourced in the active shell.
- **Fix**:

```bash
grep -n 'source "$HOME/.kittyrc"' ~/.bash_aliases ~/.bashrc ~/.zshrc
```

On PowerShell, reload profile and verify function definition:

```powershell
. $PROFILE
Get-Command kitty_cdx
```

### `.venv` is ignored

- **Symptoms**: tool resolution does not come from local virtual environment.
- **Cause**: activation script is missing or invalid.
- **Fix (Linux/macOS)**:

```bash
ls -la .venv/bin/activate
```

- **Fix (Windows)**:

```powershell
Test-Path .venv\Scripts\Activate.ps1
```

## Command Reference

- [CLI Commands](../reference/cli-commands.md)

## See Also

- [Install & Upgrade](install-spec-kitty.md)
- [Manage Agents](manage-agents.md)

## Background

- [Spec-Driven Development](../explanation/spec-driven-development.md)
