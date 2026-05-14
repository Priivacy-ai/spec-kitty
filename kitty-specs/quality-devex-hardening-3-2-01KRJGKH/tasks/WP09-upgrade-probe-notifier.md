---
work_package_id: WP09
title: No-upgrade notification UX — probe + notifier
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
subtasks:
- T047
- T048
- T049
- T050
- T051
- T052
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "33482"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- src/specify_cli/core/upgrade_probe.py
- src/specify_cli/core/upgrade_notifier.py
- src/specify_cli/core/version_checker.py
- tests/core/test_upgrade_probe_and_notifier.py
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP09.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Add the "no-upgrade available" UX notification (issue #740). Two new contained modules:

- `src/specify_cli/core/upgrade_probe.py` — PyPI probe with four-channel classification.
- `src/specify_cli/core/upgrade_notifier.py` — cache-aware notice emitter with opt-out env var.

Constraints (binding):

- Never blocks the CLI on network IO (2 s probe timeout; swallow all errors).
- 24 h cache for successful probes; 1 h cache for `UNKNOWN`.
- `SPEC_KITTY_NO_UPGRADE_CHECK=1` disables the probe entirely.
- ≤ 100 ms wall-clock budget on the cache-warm hot path (NFR-004).
- Reuses `version_checker.should_check_version()` — does NOT introduce a parallel gate.

## Context

### Design artifacts (already authored)

- `data-model.md` §2 — `UpgradeProbeResult`, `UpgradeChannel` enum, cache schema.
- `contracts/upgrade-probe-and-notifier.md` — full external surface contract including PyPI endpoint, channel classification rules, cache TTLs, opt-out behavior, notice messages, security review (per `secure-design-checklist`).
- `research.md` §5 — failure-mode taxonomy for the probe.

### Current code (do not modify beyond extension)

`src/specify_cli/core/version_checker.py` already provides:

- `get_cli_version()`, `get_project_version()`, `compare_versions()`.
- `format_version_error()` — for hard CLI/project mismatch (this is UNCHANGED; the new notifier is a separate concern).
- `should_check_version(command_name)` — the existing gate; the new notifier reuses it.

## Doctrine Citations

This WP applies:

- [`secure-design-checklist`](../../../src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml) — new external surface (PyPI probe). Already applied at design time in `contracts/upgrade-probe-and-notifier.md` § Security considerations.
- [`function-over-form-testing`](../../../src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml) — every test.

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.

## Subtasks

### T047 — Create `core/upgrade_probe.py`

**Purpose**: PyPI probe + channel classification per `contracts/upgrade-probe-and-notifier.md`.

**Steps**:

1. Create `src/specify_cli/core/upgrade_probe.py`:
   - Define `UpgradeChannel` StrEnum (`ALREADY_CURRENT`, `AHEAD_OF_PYPI`, `NO_UPGRADE_PATH`, `UNKNOWN`).
   - Define `UpgradeProbeResult` frozen dataclass (`installed_version`, `latest_pypi_version`, `channel`, `probed_at`, `error`).
   - Define `probe_pypi(cli_version, *, timeout_s: float = 2.0) -> UpgradeProbeResult`:
     - GET `https://pypi.org/pypi/spec-kitty-cli/json` with `User-Agent: spec-kitty-cli/<version> (https://github.com/Priivacy-ai/spec-kitty)`.
     - Parse `info.version` and `releases.keys()`.
     - Classify per the rules in `contracts/upgrade-probe-and-notifier.md` § Channel classification.
     - On ANY exception (timeout, HTTP error, parse error), catch and return `UpgradeProbeResult(channel=UNKNOWN, error=str(exc))`.
2. Use `httpx` (already a project dep). Do NOT introduce a new HTTP client dependency.
3. Add module-level docstring citing `secure-design-checklist` for the new external surface.

**Files**: `src/specify_cli/core/upgrade_probe.py` (new, ~120 lines).

**Validation**:

- `mypy --strict` passes.
- Module imports cleanly without side effects.

### T048 — Create `core/upgrade_notifier.py`

**Purpose**: Cache-aware emitter with opt-out.

**Steps**:

1. Create `src/specify_cli/core/upgrade_notifier.py`:
   - Define `_cache_path() -> Path`:
     - POSIX: `~/.cache/spec-kitty/upgrade-check.json`.
     - Windows: `%LOCALAPPDATA%\spec-kitty\upgrade-check.json`.
   - Define `_load_cache(cache_path) -> UpgradeProbeResult | None` and `_save_cache(cache_path, result, ttl_seconds)`.
   - Define cache-freshness predicate: `now - probed_at < ttl_seconds AND installed_version == get_cli_version()`.
   - Implement `maybe_emit_upgrade_notice(cli_version, *, console=None, now=None, cache_path=None) -> bool`:
     - Return `False` if `SPEC_KITTY_NO_UPGRADE_CHECK=1` is set.
     - Load cache; if fresh, use it. Else probe.
     - If channel is `ALREADY_CURRENT` AND previous cache entry was also `ALREADY_CURRENT` within TTL, suppress notice (return `False`).
     - Render the channel-appropriate notice via `console.print(...)`.
     - Persist result to cache (best-effort; ignore write failures).
     - Return `True` if a notice was emitted.
2. TTL: successful → 24 h; `UNKNOWN` → 1 h (per research §5).
3. Notice templates per `contracts/upgrade-probe-and-notifier.md` § Notice messages.

**Files**: `src/specify_cli/core/upgrade_notifier.py` (new, ~180 lines).

**Validation**:

- `mypy --strict` passes.
- Module imports cleanly.

### T049 — Wire notifier into CLI hot path via `should_check_version()`

**Purpose**: Integrate the new UX without introducing a parallel gate.

**Steps**:

1. Extend `src/specify_cli/core/version_checker.py`:
   - Locate `should_check_version(command_name)`. Reuse it as-is — do NOT modify its semantics.
   - Add a new helper `maybe_emit_no_upgrade_notice(command_name)` that gates on `should_check_version(command_name)` and calls `upgrade_notifier.maybe_emit_upgrade_notice(...)`.
2. Wire into the CLI entry point (top-level `cli/main.py` or `specify_cli/__init__.py` entry):
   - After argument parsing, before command dispatch, call `maybe_emit_no_upgrade_notice(command_name)`.
   - Wrap in `try/except Exception: pass` — the notifier must never block the CLI.

**Files**:

- `src/specify_cli/core/version_checker.py` (modified, ~10 lines added).
- `src/specify_cli/__init__.py` or wherever the CLI entry point lives (modified, ~5 lines added).

**Validation**:

- Existing hard CLI/project mismatch error path is unchanged.
- The notifier runs after successful command parsing.

### T050 — [P] Behavior tests in `tests/core/test_upgrade_probe_and_notifier.py`

**Purpose**: Lock the four channels + cache behavior + opt-out + failure handling.

**Steps**:

1. Create `tests/core/test_upgrade_probe_and_notifier.py`.
2. Mock the network boundary using **`respx`** (httpx-native mock library) or `httpx.MockTransport`. **Do NOT use `requests_mock`** — the project uses `httpx`, not `requests`; `requests_mock` does not intercept httpx calls.
   - Add `respx` to the dev dependency group in pyproject.toml if not already present.
   - Stub PyPI responses for:
     - 200 with `info.version == cli_version` → `ALREADY_CURRENT`.
     - 200 with `info.version > cli_version` → `AHEAD_OF_PYPI`.
     - 200 with `cli_version NOT IN releases.keys()` → `NO_UPGRADE_PATH`.
     - 404 / 500 / connection error / timeout → `UNKNOWN` with `error` populated.
3. Use `freezegun` to advance time; assert cache freshness boundary at TTL.
4. Test cache invalidation when `installed_version` changes mid-cache-window.
5. Test `SPEC_KITTY_NO_UPGRADE_CHECK=1` returns `False` and emits no notice.
6. Test identical-channel-within-TTL suppression: two consecutive `ALREADY_CURRENT` notices result in only one emit.
7. Test that probe exceptions never bubble up — `maybe_emit_upgrade_notice` returns `False` or `True` cleanly.

**Files**: `tests/core/test_upgrade_probe_and_notifier.py` (new, ~300 lines).

**Validation**:

- All tests pass.
- No `mock.call_count` assertions (function-over-form-testing).

### T051 — [P] Wall-clock test asserting ≤ 100 ms cache-warm budget

**Purpose**: NFR-004 contract verification.

**Steps**:

1. Add a wall-clock test in the same file or a sibling `test_upgrade_probe_performance.py`:
   - Warm the cache by calling `maybe_emit_upgrade_notice(...)` once.
   - Measure 10 subsequent invocations:
     ```python
     start = time.perf_counter()
     for _ in range(10):
         maybe_emit_upgrade_notice(cli_version, ...)
     elapsed_per_call = (time.perf_counter() - start) / 10
     assert elapsed_per_call < 0.1, f"cache-warm path took {elapsed_per_call*1000:.1f}ms — should be <100ms"
     ```
2. Mark the test `@pytest.mark.performance` if a marker exists; otherwise leave unmarked but with a clear name.

**Files**: same file or new sibling (~30 additional lines).

**Validation**:

- Test passes locally; tune budget upward only with documented rationale.

### T052 — Document opt-out env var in `--help` + glossary fragment

**Purpose**: Surface the opt-out to users; record the glossary fragment.

**Steps**:

1. Update the relevant typer command's `--help` text (or the top-level CLI help) to mention `SPEC_KITTY_NO_UPGRADE_CHECK=1`. Keep the wording minimal:
   ```
   Set SPEC_KITTY_NO_UPGRADE_CHECK=1 to disable the upgrade-check notice.
   ```
2. Author `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP09.md`:
   - WP09 introduces no new canonical terms (the relevant terms — "no upgrade path", "cache-warm path" — are domain-internal). Record `# WP09 introduces no new canonical terms; reinforces secure-design-checklist application on the PyPI probe surface.`

**Files**:

- CLI help text in the appropriate typer command file.
- `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP09.md` (new).

## Test Strategy

- **Behavior tests** for the four channels + cache + opt-out + failure (T050).
- **Wall-clock test** for the 100 ms cache-warm budget (T051).
- No structural tests; no `mock.call_count` assertions.

## Definition of Done

- [ ] `src/specify_cli/core/upgrade_probe.py` exists with `probe_pypi`, `UpgradeProbeResult`, `UpgradeChannel`.
- [ ] `src/specify_cli/core/upgrade_notifier.py` exists with `maybe_emit_upgrade_notice`, cache, opt-out.
- [ ] `version_checker.py` extended (existing `should_check_version` unchanged).
- [ ] CLI entry point invokes the notifier post-parsing, pre-dispatch.
- [ ] All four channels are tested with stubbed PyPI responses.
- [ ] Cache TTL boundary tested with `freezegun`.
- [ ] Opt-out env var tested.
- [ ] Wall-clock test passes (≤ 100 ms cache-warm).
- [ ] `--help` mentions the opt-out env var.
- [ ] `glossary-fragments/WP09.md` exists.
- [ ] mypy strict passes on the new modules.

## Risks

- **`httpx` request leaks file descriptors** in tests. Use the `httpx.MockTransport` pattern (or `requests_mock` if `httpx` test transport is unwieldy). Ensure client is closed in a `with` block.
- **PyPI rate limits the probe in production**. Mitigated by 24 h cache (one probe per user per day).
- **`os.environ` mutation in tests leaks to other tests**. Use `monkeypatch.setenv` / `monkeypatch.delenv` exclusively.
- **Wall-clock test flakes on slow CI runners**. If a flake materializes, loosen the budget to 200 ms and document. Don't remove the test.

## Reviewer Guidance

When reviewing this WP, check:

1. The probe swallows ALL exceptions and returns `UpgradeChannel.UNKNOWN` — no exception bubbles to the CLI hot path.
2. The cache file path uses platformdirs-style conventions (`~/.cache/spec-kitty/` on POSIX; `%LOCALAPPDATA%` on Windows).
3. The opt-out env var is checked on EVERY invocation (not cached).
4. The notifier reuses `should_check_version()` — no parallel gate.
5. The wall-clock test budget is reasonable.
6. No tests on `requests`/`httpx` internals — mocks are at the network boundary.

## Implementation command

```bash
spec-kitty agent action implement WP09 --agent claude
```

## Activity Log

- 2026-05-14T13:31:32Z – claude:sonnet:python-pedro:implementer – shell_pid=29206 – Started implementation via action command
- 2026-05-14T13:40:15Z – claude:sonnet:python-pedro:implementer – shell_pid=29206 – Ready for review: probe + notifier with 32 tests, 100ms cache-warm budget verified, opt-out wired into --help, callback gated by should_check_version
- 2026-05-14T13:40:37Z – claude:opus:reviewer-renata:reviewer – shell_pid=33482 – Started review via action command
- 2026-05-14T13:42:31Z – claude:opus:reviewer-renata:reviewer – shell_pid=33482 – Review passed: 4-channel probe with 2s timeout swallows all exceptions; notifier honours XDG/LOCALAPPDATA cache with 24h/1h TTL and SPEC_KITTY_NO_UPGRADE_CHECK opt-out (re-checked each call); identical-channel suppression for ALREADY_CURRENT verified; live caller in cli/helpers.py callback reuses should_check_version (no parallel gate); 32 tests pass covering four channels, TTL boundary, version-change invalidation, opt-out truthy/falsy, suppression, failure containment, NFR-004 100ms cache-warm budget; glossary fragment present; mypy --strict clean.
