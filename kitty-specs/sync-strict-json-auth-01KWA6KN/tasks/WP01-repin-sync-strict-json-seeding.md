---
work_package_id: WP01
title: Re-pin sync strict-JSON test seeding + non-vacuous regression lock
dependencies: []
requirement_refs:
- C-002
- C-003
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-001
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: fix/sync-strict-json-auth
merge_target_branch: fix/sync-strict-json-auth
branch_strategy: Planning artifacts for this mission were generated on fix/sync-strict-json-auth. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-strict-json-auth unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Fix
assignee: ''
agent: "claude"
shell_pid: "397165"
history:
- at: '2026-06-29T17:56:52Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/sync/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/sync/test_strict_json_stdout.py
- src/specify_cli/sync/diagnostics.py
- tests/sync/test_final_sync_diagnostics.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Re-pin sync strict-JSON test seeding + non-vacuous regression lock

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Make `tests/sync/test_strict_json_stdout.py::test_mission_create_json_strict_when_sync_skips_ingress`
pass through its **genuine** direct-ingress-skip path. Do **not** weaken any existing assertion.

> **Scope updated (FR-005, user-approved 2026-06-29):** live verification proved the root cause is
> BOTH (a) test-seeding drift AND (b) a pre-existing production misclassification of the benign
> ingress skip as `sync.server_auth_failure`. The production fix (a new `SyncDiagnosticCode` +
> `classify_sync_error` branch in `src/specify_cli/sync/diagnostics.py`) is therefore IN SCOPE. See
> `research.md` → "Live-verification update". The only production change permitted is this
> classification fix; do NOT alter auth/path/session-resolution code (C-003).

**Done when:**
- The test passes via `PWHEADLESS=1 uv run pytest tests/sync/test_strict_json_stdout.py::test_mission_create_json_strict_when_sync_skips_ingress -n0`.
- stderr contains `direct ingress skipped` or `direct_ingress_missing_private_team` (the existing guard — preserved).
- stderr does **not** contain `no valid access token` / `Not authenticated` (the new negative pin).
- The seed directory is derived from the **production resolver**, not a reconstructed string.
- Full `tests/sync/` is green; `ruff` and `mypy` clean on the changed file; no new suppressions.

## Context & Constraints

- **Root cause** (see `kitty-specs/sync-strict-json-auth-01KWA6KN/research.md`): the test seeds the
  encrypted `StoredSession` at `fake_home/.spec-kitty/auth` (`test_strict_json_stdout.py:267`), but
  production reads `$SPEC_KITTY_HOME/auth` after commit `a75174917` (#2182) changed `default_store_dir()`
  in `src/specify_cli/auth/secure_storage/file_fallback.py` to `get_runtime_root().base / "auth"`
  (`get_runtime_root()` honors `SPEC_KITTY_HOME` verbatim — `src/specify_cli/paths/windows_paths.py:78`).
  The test sets `SPEC_KITTY_HOME=fake_home/.kittify`, so the seeded session is invisible → unauthenticated
  → `final_sync` `sync.server_auth_failure` → the skip diagnostic never fires.
- **This is the §4 "stale → re-pin" case.** Fix the test seeding; production is correct (intentional
  `SPEC_KITTY_HOME` isolation). Do NOT revert or alter production auth/path code (C-003).
- **C-002**: the diagnostic-fired assertion is the non-vacuous guard — never delete or weaken it.
- Supporting docs: `kitty-specs/sync-strict-json-auth-01KWA6KN/plan.md` (IC-01, IC-02),
  `research.md` (full file:line trace), `.kittify/charter/charter.md`.

## Branch Strategy

- **Strategy**: feature-branch
- **Planning base branch**: fix/sync-strict-json-auth
- **Merge target branch**: fix/sync-strict-json-auth (mission lands via PR into `main`)

> Populated by `spec-kitty agent mission tasks`. Do not change manually.

## Subtasks & Detailed Guidance

### Subtask T001 – Re-pin session seeding to the production resolver path

- **Purpose**: Seed the encrypted session into the directory production actually reads, so the
  subprocess authenticates and reaches the genuine ingress-skip path.
- **Steps**:
  1. In `_build_isolated_home` (around `test_strict_json_stdout.py:300-329`), the subprocess env sets
     `SPEC_KITTY_HOME = fake_kittify` (`fake_home/.kittify`). Compute the seed `auth_dir` from the
     **production resolver evaluated under that env**, not by hand-concatenating the string. Prefer
     importing the production function and calling it with `SPEC_KITTY_HOME` set, e.g. derive from
     `specify_cli.auth.secure_storage.file_fallback.default_store_dir()` (which returns
     `get_runtime_root().base / "auth"`). If invoking the resolver directly is awkward because it reads
     process env, set/patch `SPEC_KITTY_HOME` to `fake_kittify` for the resolver call (or use
     `get_runtime_root`), so the seed dir == the exact path the subprocess will read.
  2. Pass that resolver-derived `auth_dir` into `_seed_shared_only_session` (currently hardcodes
     `auth_dir = fake_home / ".spec-kitty" / "auth"` at `:267`). Seed via the same production
     `FileFallbackStorage(base_dir=auth_dir)` encryptor (keep AES-256-GCM / scrypt `hostname:uid` —
     same-machine decryptable).
  3. Keep the `StoredSession` shape identical (one non-private `Team(is_private_teamspace=False)`,
     `access_token="fake-access-token"`, `access_token_expires_at = now + 1h`). The `generation` field
     has a default and may be omitted (verified compatible).
- **Files**: `tests/sync/test_strict_json_stdout.py`.
- **Notes**: The durable property is "seed dir is whatever the production resolver returns under the
  subprocess env" — so a future `default_store_dir()` change the test fails to mirror surfaces as a RED
  seed-vs-read mismatch, not silent re-drift (IC-02 drift-class kill).

### Subtask T002 – Correct the stale seeding docstrings

- **Purpose**: Remove the now-false claim that resolution is via `Path.home()/".spec-kitty"/"auth"`.
- **Steps**: Update the docstrings around `test_strict_json_stdout.py:244-262` (and any sibling comment)
  to describe the `$SPEC_KITTY_HOME/auth` resolution and reference #2182 as the reason. Keep them accurate
  and concise.
- **Files**: `tests/sync/test_strict_json_stdout.py`.

### Subtask T003 – Add the non-vacuous negative auth pin assertion

- **Purpose**: Upgrade "a skip diagnostic appeared" into "the session loaded and that is *why* the genuine
  skip fired" — so a future regression that re-breaks session loading fails this test.
- **Steps**: In `test_mission_create_json_strict_when_sync_skips_ingress` (near the existing
  `diagnostic_present` assertion at `:804-812`), add an assertion that stderr does **not** contain
  `no valid access token` (and/or `Not authenticated`). Keep the existing positive `diagnostic_present`
  guard exactly as is.
  - Do **NOT** add a tautological path-equality assertion like
    `assert auth_dir == Path(env["SPEC_KITTY_HOME"]) / "auth"` — it is vacuous against its own
    construction and gives zero drift protection (post-plan squad finding).
- **Files**: `tests/sync/test_strict_json_stdout.py`.

### Subtask T004 – Live-verify the genuine ingress-skip path fires (logging-reachability residual)

- **Purpose**: §4 live-evidence. The fix's sufficiency rests on the `_team` WARNING reaching the
  subprocess stderr via the CLI's own logging config (this subprocess injects no logging handler, unlike
  the sibling `test_sync_diagnostic_emits_to_stderr…`). The static trace cannot fully close this link —
  prove it with a real run.
- **Steps**:
  1. Run `PWHEADLESS=1 uv run pytest tests/sync/test_strict_json_stdout.py::test_mission_create_json_strict_when_sync_skips_ingress -n0 -q`.
  2. Confirm it PASSES and that the captured stderr shows the genuine `direct ingress skipped` /
     `direct_ingress_missing_private_team` diagnostic (not a `server_auth_failure`). If it still fails for
     a *new* reason (e.g. the WARNING is suppressed/not routed to stderr), STOP — the re-pin is insufficient;
     escalate with the captured stderr so the logging route can be addressed (do not weaken the assertion to
     force green).
  3. Record the live evidence (command + key stderr lines) in the Activity Log and in
     `kitty-specs/sync-strict-json-auth-01KWA6KN/tracers/approach.md`.
- **Files**: none (verification); tracer + Activity Log updates.

### Subtask T005 – Regression + quality gates

- **Purpose**: No regressions; clean gates (NFR-002, NFR-003).
- **Steps**:
  1. `PWHEADLESS=1 uv run pytest tests/sync/test_strict_json_stdout.py -n0` (whole module green).
  2. `PWHEADLESS=1 uv run pytest tests/sync/ -n0 -q` (sync suite; serial — has real-port/daemon tests).
  3. `uv run ruff check tests/sync/test_strict_json_stdout.py` and
     `uv run mypy tests/sync/test_strict_json_stdout.py` (or the repo's canonical mypy invocation) — clean,
     no new `# noqa` / `# type: ignore`.
  4. Re-run the test ≥3× to confirm determinism (NFR-001).
- **Files**: `tests/sync/test_strict_json_stdout.py` (only if gate fixes needed).

## Test Strategy

This WP *is* a test fix. No new test file; modify the existing `test_strict_json_stdout.py`. The
acceptance oracle is the test passing via the genuine path plus the negative auth pin, the full
`tests/sync/` suite green, and clean ruff/mypy.

## Risks & Mitigations

- **Logging-reachability residual (primary risk)**: the WARNING may not reach subprocess stderr →
  test fails for a new reason. Mitigation: T004 live-verify before declaring done; escalate rather than
  weaken if it fails.
- **Coupling to internal path layout**: avoid asserting incidental path strings; anchor to the production
  resolver and contract-level behavior (session loaded → genuine diagnostic; auth-failure absent).
- **Determinism**: scrypt key is `hostname:uid` (stable same-machine); unique `tmp_path` per test; daemon
  stopped in `finally`. If `localhost:1` ever hangs instead of refusing on a CI runner, the in-process
  final-sync window could miss — note it, but port 1 normally refuses immediately on Linux.

## Review Guidance

- Confirm the **only** production change is the diagnostics classification (`git diff --name-only` shows exactly `src/specify_cli/sync/diagnostics.py`, `tests/sync/test_strict_json_stdout.py`, `tests/sync/test_final_sync_diagnostics.py`) — no auth/path/session-resolution code touched (C-003).
- Confirm the diagnostic-fired assertion is intact (C-002) and the new negative pin is present (T003).
- Confirm the seed dir is resolver-derived, not a hand-built string (IC-02 drift-class kill).
- Confirm live evidence is recorded (T004) — green exit alone is insufficient.
- Confirm the seeding docstrings are accurate (T002).

## Activity Log

> Append new entries at the END, chronological order, UTC timestamps.

- 2026-06-29T17:56:52Z – system – Prompt created.
- 2026-06-29T18:35:00Z – claude (python-pedro) – Implemented: re-pinned seeding via production resolver; added DIRECT_INGRESS_MISSING_PRIVATE_TEAM classifier branch (FR-005, user-approved scope expansion after live evidence); negative auth pin; classifier unit test + 6-member contract update. Live-verified target test green via genuine path, 3/3 deterministic; ruff/mypy clean; classifier-adjacent regression (batch, team-ingress, e2e clean-output, final-sync-diagnostics) all green. Commit 708fb8d97.
- 2026-06-29T18:40:00Z – reviewer-renata (independent) – APPROVE. Drove the subprocess directly: stderr emits diagnostic_code=sync.direct_ingress_missing_private_team, RC=0, no auth-failure text. Confirmed branch is genuinely exercised (removing it → test RED), negative pin non-vacuous, classifier scoping does not misfire on auth/network signals, only 3 files changed (no auth/path prod code), ruff/mypy clean. Non-blocking: _team.py:79 WARNING remains stderr-invisible (future cleanup).
- 2026-06-29T18:01:56Z – claude – shell_pid=397165 – Assigned agent via action command
- 2026-06-29T18:22:58Z – claude – shell_pid=397165 – Re-pin seeding + classify benign ingress skip; live-verified green, 3/3 deterministic, ruff/mypy clean, regression suites pass
- 2026-06-29T18:31:23Z – user – shell_pid=397165 – Independent reviewer-renata review in progress
- 2026-06-29T18:32:23Z – user – shell_pid=397165 – APPROVED by independent reviewer-renata: genuine path verified, non-vacuous assertions, classifier scoped, ruff/mypy clean
