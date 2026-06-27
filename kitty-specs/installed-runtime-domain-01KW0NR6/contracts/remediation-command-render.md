# Contract: RemediationCommand.render(platform)

**Module**: `src/specify_cli/compat/remediation.py`
**FR**: FR-005, NFR-002, C-005
**Consumers**: `review/__init__.py`, `upgrade_ux.py`, `upgrade_hint.py`, `version_checker.py`, `schema_version.py`

---

## Signature

```python
def render(self, platform: Literal["posix", "windows"]) -> str:
    """Return a CHK028-validated, env-prefixed, platform-quoted command string.

    Raises:
        ValueError: if `self.argv` is None (intent is MANUAL_GUIDANCE).
        ValueError: if the composed string does not match CHK028
                    (`^[A-Za-z0-9 .\\-+_/=:]{1,128}$`).

    The returned string is safe for copy-paste display. The same argv
    and env fields can be passed directly to subprocess.run() for
    programmatic execution.
    """
```

---

## Composition rules

### 1. Env prefix

Build the env prefix from `self.env` (an ordered `Mapping[str, str]`):

| Platform | Format per entry | Join |
|----------|-----------------|------|
| `"posix"` | `KEY=shlex.quote(value)` | space-separated, trailing space |
| `"windows"` | `$env:KEY='<powershell-quoted-value>';` | space-separated, trailing space |

PowerShell quoting: wrap value in single quotes; replace each `'` in value with `''`.

Example (posix, `UV_TOOL_DIR=/opt/tools`):
```
UV_TOOL_DIR=/opt/tools uv tool install --force spec-kitty-cli
```

Example (windows, `UV_TOOL_DIR=C:\tools`):
```
$env:UV_TOOL_DIR='C:\tools'; uv tool install --force spec-kitty-cli
```

### 2. Argv composition

Join `self.argv` elements with `shlex.quote()` for `"posix"`. For `"windows"`, join without additional quoting (Windows shell handles its own quoting; the PowerShell env prefix already uses safe quoting for the env values).

### 3. CHK028 validation

The final composed string (env_prefix + argv_string) MUST match:

```python
_COMMAND_RE = re.compile(r"^[A-Za-z0-9 .\-+_/=:]{1,128}$")
```

If validation fails, raise `ValueError` with a CHK028 violation message. The caller MUST catch this and fall back to a `MANUAL_GUIDANCE` remediation with a safe note.

---

## Acceptance scenarios

| Install method | Intent | Platform | Expected render() output |
|---------------|--------|---------|--------------------------|
| PIPX | UPGRADE | posix | `pipx upgrade spec-kitty-cli` |
| PIPX | UPGRADE | windows | `pipx upgrade spec-kitty-cli` |
| UV_TOOL (default tool dir, no python) | UPGRADE | posix | `uv tool install --force spec-kitty-cli` |
| UV_TOOL (custom `UV_TOOL_DIR=/opt`, python=3.11) | UPGRADE | posix | `UV_TOOL_DIR=/opt uv tool install --force --python 3.11 spec-kitty-cli` |
| UV_TOOL (custom dirs) | UPGRADE | windows | `$env:UV_TOOL_DIR='C:\tools'; uv tool install --force spec-kitty-cli` |
| BREW | UPGRADE | posix | `brew upgrade spec-kitty-cli` |
| PIP_USER | UPGRADE | posix | `pip install --user --upgrade spec-kitty-cli` |
| PIP_SYSTEM | UPGRADE | posix | `pip install --upgrade spec-kitty-cli` |
| UNKNOWN | UPGRADE | posix | raises or returns MANUAL_GUIDANCE note (no argv) |

---

## Backward compatibility with `UpgradeHint.command`

After WP03, `build_upgrade_hint()` reimplements by calling `plan_remediation().render(current_platform)`. The returned `UpgradeHint.command` value must equal the pre-migration value for every install method in `_HINT_TABLE`. Snapshot tests committed in WP03 enforce this invariant (SC-003, SC-006).

---

## Never-render contract for MANUAL_GUIDANCE

When `intent == MANUAL_GUIDANCE`, `argv` is None. Calling `render()` on a MANUAL_GUIDANCE command MUST raise `ValueError("cannot render MANUAL_GUIDANCE RemediationCommand — check intent before calling render()")`. The `note` field carries the human-readable message for these cases.
