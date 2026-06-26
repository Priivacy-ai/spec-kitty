# Contract: No-Selector Error (FR-003, FR-004, SC-003)

**Mission**: `feature-alias-removal-01KW0N87`
**Authority**: spec.md FR-003, FR-004, SC-003

---

## Purpose

After removing the `--feature` alias, each in-scope command MUST produce a clean, user-readable
error when no mission selector is supplied. This contract defines the required error shape so that
FR-008 regression tests can assert it precisely.

---

## Contract Specification

### Trigger Conditions

| Condition | Example invocation |
|-----------|-------------------|
| No `--mission` flag provided | `spec-kitty research` |
| `--mission` provided with whitespace-only value | `spec-kitty research --mission "   "` |

### Required Behavior

| Property | Required value |
|----------|---------------|
| Exit code | **2** |
| stderr/stdout | Contains a human-readable error string (not a Python traceback) |
| Exception type | Must NOT be `TypeError` or any unhandled exception |
| Message must include | Any of: `"--mission"`, `"required"`, `"Error"`, `"No mission handle"` |

### Acceptable Message Shapes

Commands using the inline `typer.BadParameter` guard produce:

```
Error: Invalid value for '--mission': --mission <slug> is required
```

Commands using explicit `console.print` + `typer.Exit(2)` produce:

```
[Error] --mission <slug> is required
```

Both forms satisfy the contract. The test in FR-008 should assert:
1. `result.exit_code == 2` (or `result.exit_code != 0`)
2. `"--mission" in result.output or "required" in result.output.lower()`
3. `not isinstance(result.exception, TypeError)`

---

## Per-Command Conformance Table

| Command | Invocation | Guard mechanism | Exit code |
|---------|-----------|-----------------|-----------|
| `spec-kitty implement <WP>` | no `--mission` | `detect_feature_context` raises `typer.BadParameter` | 2 |
| `spec-kitty merge` | no `--mission` | `_resolve_slug_or_exit` → `if not resolved_mission` → `typer.Exit(2)` | 2 |
| `spec-kitty next` | no `--mission` | `_resolve_mission_slug` raises `typer.BadParameter` | 2 |
| `spec-kitty research` | no `--mission` | inline guard raises `typer.BadParameter` (or emits error + `Exit(2)`) | 2 |
| `spec-kitty context mission-resolve` | no `--mission` | inline guard raises `typer.BadParameter` | 2 |
| `spec-kitty accept` | no `--mission` | inline guard + `typer.Exit(2)` | 2 |
| `spec-kitty lifecycle plan` | no `--mission` | inline guard raises `typer.BadParameter` | 2 |
| `spec-kitty lifecycle tasks` | no `--mission` | inline guard + `typer.Exit(2)` (or `typer.BadParameter`) | 2 |
| `spec-kitty mission-type current` | no `--mission` (auto-detect also None) | inline guard → `typer.Exit(2)` | 2 |

---

## Out-of-Scope / Unchanged

- Passing `--feature` to any in-scope command after this mission: CLI exits with code 2
  and "No such option: --feature" (standard Typer unknown-option error). This is the
  FR-001 acceptance criterion, not the no-selector guard.
- Out-of-scope callers (`charter/interview.py`, `charter/generate.py`, `agent/mission_create.py`,
  `lifecycle.specify`) retain their existing error handling unchanged.

---

## Regression Test Shape (FR-008)

```python
def test_<command>_no_mission_exits_cleanly(runner, tmp_path):
    result = runner.invoke(app, ["<command>", ...])  # no --mission
    assert result.exit_code != 0
    assert not isinstance(result.exception, TypeError)
    assert "--mission" in result.output or "required" in result.output.lower()
```

One test per command, eight tests total. Tests may be grouped in a single new file
`tests/contract/test_no_selector_guard.py` or added to the nearest existing per-command
test file.
