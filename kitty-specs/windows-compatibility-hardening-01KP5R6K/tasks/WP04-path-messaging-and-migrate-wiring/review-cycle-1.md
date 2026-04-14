# WP04 Review Cycle 1 — Feedback

Reviewer: claude:opus-4.6:reviewer  
Commit: f667c4f1  
Date: 2026-04-14

## Verdict: REQUEST CHANGES

Two issues must be fixed before approval. Both are in the audit test (T024).

---

## Issue 1 — BLOCKER: `CliRunner(mix_stderr=False)` crashes on Typer 0.24.x

**File**: `tests/cli/test_migrate_cmd_messaging.py` (lines 37, 82) and `tests/cli/test_agent_status_messaging.py` (line 23)

**Symptom**: All three `windows_ci`-marked tests raise `TypeError: CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'` on the installed Typer version (0.24.1). The `CliRunner` in this version of Typer only accepts `charset`, `env`, `echo_stdin`, and `catch_exceptions`.

**Impact**: These tests would fail immediately on `windows-latest` CI, defeating the entire purpose of T022 and T023. The WP definition-of-done check `pytest tests/cli/ tests/audit/ -v -m "not windows_ci"` passes only because the `windows_ci` marker causes them to be deselected on POSIX — but they are broken on the platform they are meant to protect.

**Fix**: Remove `mix_stderr=False` from all three `CliRunner()` instantiations. The test bodies already read `result.stdout` and `result.stderr` separately, so no logic change is needed. Replace:

```python
runner = CliRunner(mix_stderr=False)
```

with:

```python
runner = CliRunner()
```

in:
- `tests/cli/test_migrate_cmd_messaging.py` (line 37)
- `tests/cli/test_migrate_cmd_messaging.py` (line 82)
- `tests/cli/test_agent_status_messaging.py` (line 23)

---

## Issue 2 — BLOCKER: Audit test pattern is too narrow — misses user-facing labels in `doctor.py`

**File**: `tests/audit/test_no_legacy_path_literals.py`

**Symptom**: The regex `r'["\'](~/\.kittify|~/\.spec-kitty)[/"\' ]'` requires the tilde to appear *immediately after* a quote character. This catches simple string literals like `"~/.kittify"` but silently misses path references embedded inside longer strings, specifically:

```python
# src/specify_cli/cli/commands/doctor.py lines 181-182
StateRoot.GLOBAL_RUNTIME: "Global Runtime (~/.kittify/)",
StateRoot.GLOBAL_SYNC:    "Global Sync (~/.spec-kitty/)",
```

These are user-facing display labels rendered in CLI output and are exactly the kind of legacy literals the audit test is meant to block.

The acceptance criterion (AC-5 from the review prompt) explicitly calls out: "grep pattern is too narrow (misses `.config/spec-kitty` or `~/.kittify/...`)".

**Fix**: Broaden the pattern to match `~/\.kittify` or `~/\.spec-kitty` anywhere inside a string literal. One approach that avoids false positives on comments:

```python
# Match the tilde-path anywhere within a quoted string value.
# The negative lookbehind (?<=#) excludes pure comment lines.
legacy_pattern = re.compile(
    r'(?<!")(?<!#\s{0,20}).*["\'].*?(~/\.kittify|~/\.spec-kitty)'
)
```

A simpler, equally effective approach: drop the quote-prefix requirement and instead skip lines that are pure code comments (start with optional whitespace then `#`):

```python
legacy_pattern = re.compile(r'~/\.kittify|~/\.spec-kitty')
comment_pattern = re.compile(r'^\s*#')
...
for i, line in enumerate(text.splitlines(), start=1):
    if comment_pattern.match(line):
        continue  # skip pure comments; they are not user-facing output
    if legacy_pattern.search(line):
        violations.append(...)
```

With this fix the audit would catch `doctor.py:181-182`. Whether those two lines should be fixed as part of WP04 (they are in `src/specify_cli/cli/`) or deferred to WP09 (repo-wide audit) is implementer's discretion, but the audit test must at minimum *detect* them.

Note: after broadening the pattern, `tests/audit/test_no_legacy_path_literals.py` will itself fail until either (a) `doctor.py` lines 181–182 are also fixed, or (b) they are added to an explicit allowlist with a justification comment.

---

## What passed

- Legacy literals in `migrate_cmd.py` and `agent/status.py`: clean (grep confirms zero hits).
- Migration call ordering: `migrate_windows_state()` executes before `locate_project_root()`, `ensure_runtime()`, and `execute_migration()` — correct.
- Exit code 69 for lock contention (`TimeoutError`): implemented correctly at the call site.
- Exit code 78 for unresolvable `%LOCALAPPDATA%`: implemented correctly inside `_render_windows_migration_summary`.
- `_render_windows_migration_summary` uses `render_runtime_path` for every displayed path — no tilde-forms in output code.
- Static audit test runs without `windows_ci` marker — correct, it is platform-independent.
- Commit message references FR-006, FR-012, FR-013, NFR-005, SC-002, WP04, T019–T024.
- Ownership: exactly the 6 declared files changed, no extras.
- `mypy --strict` passes on both source files.
- Pre-existing `tests/cli/commands/test_auth_login.py` failures (3 tests) are confirmed pre-existing before this commit and are not a WP04 regression.

---

## Polish notes for WP05 / WP08 / WP09

- **WP09** should adopt the broader audit pattern (skip-comment approach) when it extends coverage to the full `src/` tree. The `init.py` docstrings and the `upgrade.py` comment referencing `~/.kittify` are not user-facing output, but the `doctor.py` display labels are.
- **WP05** consumers: note that `render_runtime_path` from WP01 is confirmed importable and type-clean; no additional integration work needed from WP04.
