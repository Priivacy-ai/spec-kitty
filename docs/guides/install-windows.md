---
title: Install Spec Kitty on Windows
description: Install the Spec Kitty 3.2 CLI on Windows 10 or 11 with PowerShell, pipx, uv, or a virtual environment.
doc_status: active
updated: '2026-06-12'
type: how-to
related:
- docs/guides/install-linux.md
- docs/guides/install-macos.md
- docs/guides/non-interactive-init.md
- docs/guides/upgrade-cli.md
- docs/guides/worktrees-with-mcp-agents.md
audience: end-users
os: windows
---
# Install Spec Kitty on Windows

Install the `spec-kitty` CLI on Windows 10 or Windows 11. PowerShell is recommended; CMD works too.

> The PyPI distribution is named **`spec-kitty-cli`**; the binary it installs is **`spec-kitty`**. WSL is **not required**.

## Prerequisites

- Windows 10 21H2 or newer (Windows 11 preferred).
- **Python 3.11+** from [python.org](https://www.python.org/downloads/windows/) or the Microsoft Store. During install, tick **"Add Python to PATH"** and **"Install py launcher"**.
- Verify (in PowerShell or CMD):

  ```powershell
  py --version
  # or
  python --version
  ```

  On Windows the `py` launcher is the canonical way to invoke a specific Python:

  ```powershell
  py -3.12 --version
  py -3.11 -m pip --version
  ```

- Optional: install [Windows Terminal](https://aka.ms/terminal) for a nicer shell experience.

## Method 1: pipx (recommended for global tool install)

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
```

Open a **new** PowerShell window (so the updated PATH is picked up), then:

```powershell
pipx install spec-kitty-cli
spec-kitty --version
```

## Method 2: uv tool

Install `uv` via PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Open a new shell, then:

```powershell
uv tool install spec-kitty-cli
spec-kitty --version
```

## Method 3: pip in a venv (contributor path)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1     # PowerShell
# or:
.venv\Scripts\activate.bat     # CMD

pip install spec-kitty-cli
spec-kitty --version
```

If PowerShell refuses to run `Activate.ps1` due to execution policy:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Deactivate the venv with `deactivate`.

## Verification

```powershell
spec-kitty --version
# spec-kitty-cli version 3.2.x
```

```powershell
spec-kitty --help
spec-kitty doctor       # post-install health check (in an initialized project)
```

## PATH considerations on Windows

`pipx` and `uv tool` typically install shims into:

- `%USERPROFILE%\.local\bin`

If `spec-kitty` is "command not found":

**Option A — let pipx fix PATH for you:**

```powershell
pipx ensurepath
```

Then close and reopen PowerShell.

**Option B — add the directory manually:**

1. Open **Settings → System → About → Advanced system settings → Environment Variables**.
2. Under **User variables**, select `Path → Edit → New`.
3. Add `%USERPROFILE%\.local\bin`.
4. Open a new PowerShell window.

**Option C — temporary, for the current session only:**

```powershell
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
```

### PowerShell vs CMD

- **PowerShell** is the recommended shell. Use `Activate.ps1` for venvs and the install commands above as written.
- **CMD** works for invoking `spec-kitty` once installed, but use `Scripts\activate.bat` instead of `Activate.ps1` to enter a venv.

### `py` launcher vs `python`

The Windows `py` launcher picks the right Python version even when several are installed:

```powershell
py -3.12 -m pip install --upgrade pip
py -3.12 -m pipx install spec-kitty-cli
```

Plain `python` may resolve to a Microsoft Store stub on a fresh install; `py` always resolves to a real Python.

## Troubleshooting

**`spec-kitty` is "not recognized as the name of a cmdlet"** — PATH issue. Run `pipx ensurepath`, open a new PowerShell window, then `where.exe spec-kitty` to confirm where it lives.

**`SSL: CERTIFICATE_VERIFY_FAILED` during `pip install`** — Your Python install is too old. Reinstall Python 3.11+ from python.org.

**Microsoft Store Python stub opens instead of running pip** — Settings → Apps → Advanced app settings → App execution aliases → toggle off the App Installer entries for `python.exe` and `python3.exe`, then reopen your shell.

**Antivirus blocks installs** — Corporate antivirus sometimes quarantines Python wheels. Whitelist the cache directory pipx prints when it errors.

## Next steps

- [Initialize a project](non-interactive-init.md)
- [Upgrade the CLI](upgrade-cli.md)
- [Keep MCP Agents in the Worktree](worktrees-with-mcp-agents.md)
- [macOS install guide](install-macos.md)
- [Linux install guide](install-linux.md)
- [Pip vs pipx vs uv — which to choose](../architecture/pip-vs-pipx-vs-uv.md)
