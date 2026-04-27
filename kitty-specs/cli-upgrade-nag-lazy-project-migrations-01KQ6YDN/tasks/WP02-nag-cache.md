---
work_package_id: WP02
title: NagCache with security properties
dependencies: []
requirement_refs:
- FR-004
- FR-025
- NFR-001
- NFR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Worktree branch derived from lanes.json by spec-kitty implement; final merge target is main.
subtasks:
- T006
- T007
- T008
- T009
- T010
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks
authoritative_surface: src/specify_cli/compat/
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/compat/cache.py
- src/specify_cli/compat/config.py
- tests/specify_cli/compat/test_cache.py
- tests/specify_cli/compat/test_config.py
priority: P0
tags: []
---

# WP02 — NagCache with security properties

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP02 --agent <name>` from `lanes.json`.

## Objective

Implement the per-user `NagCache` that throttles the upgrade nag, invalidates on installed-CLI version change, and resists symlink / permission-based attacks. Also implement the small config loader that reads the throttle window from env / YAML / default.

## Context

- Spec: FR-004 (throttled), FR-025 (invalidate on CLI version change), NFR-001 (<100ms when fresh), NFR-009 (configurable throttle).
- Plan: §"Engineering Alignment" Q3-A; §"Risks" RP-07.
- Research: [`research.md`](../research.md) §R-02 (cache location), §R-06 (throttle config), §R-07 (CI predicate).
- Data model: [`data-model.md`](../data-model.md) §1.10 (`NagCacheRecord`), §3 (Configuration surface).
- Security checklist: CHK006 (file perms 0o600), CHK007 (no PII in cache), CHK008 (overly-wide perms), CHK009 (symlink resistance), CHK010 (cache dir symlink), CHK023 (ownership), CHK025 (range validation), CHK044 (clock skew), CHK045 (read-only home).
- Charter: typer + rich + ruamel.yaml + pytest + mypy --strict + 90%+ coverage.

## Subtasks

### T006 — `NagCacheRecord` dataclass + `NagCache` class

**Steps**:
1. In `src/specify_cli/compat/cache.py`:
   - `NagCacheRecord` — frozen dataclass with `cli_version_key: str`, `latest_version: str | None`, `latest_source: Literal["pypi","none"]`, `fetched_at: datetime`, `last_shown_at: datetime | None`. ISO-8601 UTC strings on disk.
   - `NagCache` class with `default()` classmethod and `read() -> NagCacheRecord | None` / `write(record: NagCacheRecord) -> None` instance methods.
2. `NagCache.default()` resolves the cache directory:
   - Try `platformdirs.user_cache_dir("spec-kitty")` if importable (it likely is — transitive of `rich` or `httpx`).
   - Fall back to `os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")) + "/spec-kitty"` on Linux/WSL; `~/Library/Caches/spec-kitty` on macOS; `%LOCALAPPDATA%\spec-kitty\Cache` on Windows.
   - File name: `upgrade-nag.json`.
3. JSON serialisation: use stdlib `json` with `sort_keys=True` for deterministic output (helps testing).

**Files**: `src/specify_cli/compat/cache.py`.

**Validation**: round-trip a record through `write` then `read` and confirm equality.

### T007 — File-mode + symlink-resistant I/O

**Steps**:
1. **Write path**:
   - Ensure parent dir exists with `path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)`.
   - Refuse to write if `path.parent` is a symlink: `os.lstat(parent)` and check `not stat.S_ISLNK(...)`.
   - Write atomically: open with `os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)` on POSIX; use `Path.open("w")` + `os.chmod(path, 0o600)` on Windows (best-effort).
   - Refuse to write if `path` exists and is a symlink (lstat check).
2. **Read path**:
   - Refuse to read if `path` is a symlink (lstat check).
   - Refuse to read if `path` size > 64 KB (defensive bound).
   - Refuse to read if file ownership ≠ `os.geteuid()` on POSIX (CHK023). Skip ownership check on Windows.
   - On any refusal, return `None` (treat as "no cache record"), NOT raise.

**Files**: `src/specify_cli/compat/cache.py` (extend).

**Validation**:
- Test that pre-creating the cache file as a symlink causes `read()` to return None and a subsequent `write()` to refuse.
- Test that pre-creating the cache file with mode 0o644 causes `read()` to return None on POSIX (perm refusal).

### T008 — Throttle predicate with clock-skew + version-key invalidation

**Steps**:
1. `NagCache.is_fresh(record, *, throttle_seconds: int, now: datetime, current_cli_version: str) -> bool`:
   - If `record is None`: return `False`.
   - If `record.cli_version_key != current_cli_version`: return `False` (FR-025 — version changed, cache invalid).
   - If `record.last_shown_at is None`: return `False` (never shown — eligible).
   - Compute `delta = (now - record.last_shown_at).total_seconds()`.
   - If `delta < 0`: clock moved backward (CHK044). Treat as expired: return `False`.
   - If `delta > throttle_seconds`: return `False`.
   - Else `True` (fresh — suppress nag).
2. Pure function: no I/O. Inject `now` for testability.

**Files**: `src/specify_cli/compat/cache.py` (extend).

**Validation**: unit table tests over (last_shown_at, now, throttle, version_key) tuples.

### T009 — Config loader (env > YAML > default; range-validated)

**Steps**:
1. In `src/specify_cli/compat/config.py`:
   - `UpgradeConfig` dataclass: `throttle_seconds: int`, `nag_enabled: bool`.
   - `load() -> UpgradeConfig` classmethod resolves:
     - `throttle_seconds`: env `SPEC_KITTY_NAG_THROTTLE_SECONDS` (cast int) > YAML key `nag.throttle_seconds` > default `86400`.
     - `nag_enabled`: env `SPEC_KITTY_NO_NAG` truthy → `False` > YAML key `nag.enabled` > default `True`.
   - YAML path: `os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")) + "/spec-kitty/upgrade.yaml"` on POSIX; analogous platformdirs config dir elsewhere.
2. **Range validation** (CHK025): `60 ≤ throttle_seconds ≤ 31_536_000`. Out-of-range or non-integer values silently fall back to default `86400`. Optionally log at debug level.
3. YAML loading: use ruamel.yaml safe-load (already a project dep). If file is missing, just use defaults — don't error.

**Files**: `src/specify_cli/compat/config.py` (new), `tests/specify_cli/compat/test_config.py` (new).

**Validation**: unit tests cover env-overrides-file, file-overrides-default, out-of-range falls back, missing file is fine, malformed YAML is fine (returns defaults).

### T010 — Cache + config tests

**Steps**:
1. `tests/specify_cli/compat/test_cache.py`:
   - Round-trip a record (write then read).
   - Symlink at file path → write refuses.
   - Symlink at parent dir → write refuses.
   - Pre-existing file with 0o644 perms → read returns None on POSIX.
   - Oversized file (65 KB JSON) → read returns None.
   - Foreign-uid file → read returns None on POSIX (mock `os.lstat` to return foreign uid). Skip on Windows.
   - Throttle table: cases for never-shown, just-shown, expired, far-past, far-future (clock skew), version-key-mismatch.
   - Use `tmp_path` fixture for isolation; never touch the real user cache.
2. `tests/specify_cli/compat/test_config.py`:
   - env-only, file-only, env+file (env wins), missing file, malformed YAML, out-of-range throttle, `SPEC_KITTY_NO_NAG=1`.
   - Use `monkeypatch` for env vars; `tmp_path` for config files.

**Files**: `tests/specify_cli/compat/test_cache.py`, `tests/specify_cli/compat/test_config.py`.

**Validation**: `pytest tests/specify_cli/compat/test_cache.py tests/specify_cli/compat/test_config.py -v` green; coverage ≥ 90% on `cache.py` and `config.py`.

## Definition of Done

- [ ] `compat/cache.py` and `compat/config.py` exist with the public surface described above.
- [ ] All security properties (file perms, symlinks, ownership, oversized files, clock skew, range validation) enforced in code.
- [ ] No test touches the real user cache directory.
- [ ] `mypy --strict` clean.
- [ ] `ruff check` clean.
- [ ] `pytest tests/specify_cli/compat/test_cache.py tests/specify_cli/compat/test_config.py` green.
- [ ] Coverage on `cache.py` and `config.py` ≥ 90%.

## Risks

- Windows POSIX-perm semantics: documented; perms still set best-effort. Test for the POSIX path is the gate.
- `platformdirs` may not be available — fall back to manual XDG resolution. Don't introduce it as a new mandatory dep (C-009).
- ruamel.yaml safe-load semantics differ slightly from PyYAML — use the project's existing pattern (look at `migration.schema_version`).

## Reviewer Guidance

1. **Symlink resistance**: every file open must be preceded by an `os.lstat`. No `os.stat` (follows symlinks).
2. **Mode bits**: literally `0o600` — not `0o660`, not `0o644`.
3. **Range validation**: out-of-range throttle is silent — no exception, no banner.
4. **Determinism**: tests inject `now`; the cache code accepts `now` as a parameter rather than calling `datetime.now()` directly.
5. **No PII**: confirm the `NagCacheRecord` schema does not include user paths, project slugs, hostnames, or anything user-identifying (CHK007, CHK048, CHK050).

## Implementation command

```bash
spec-kitty agent action implement WP02 --agent <name>
```
