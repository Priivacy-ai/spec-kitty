---
work_package_id: WP02
title: Reaper scope authority (startup)
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-006
- FR-007
- FR-008
- NFR-005
tracker_refs: []
planning_base_branch: fix/sync-daemon-orphan-cleanup
merge_target_branch: fix/sync-daemon-orphan-cleanup
branch_strategy: Planning artifacts for this mission were generated on fix/sync-daemon-orphan-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-daemon-orphan-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Cleanup authority
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "85545"
history:
- at: '2026-06-30T11:18:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/owner.py
create_intent:
- tests/sync/test_daemon_reaper_scope_authority.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/owner.py
- tests/sync/test_daemon_reaper_scope_authority.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Reaper scope authority (startup)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter **before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is set, run `spec-kitty agent profile list` and pick the best match for `task_type: implement` on `authoritative_surface: src/specify_cli/sync/owner.py`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objective

Rewire the **startup** reaper `reap_orphan_daemons` (`sync/owner.py:707-789`) so the **daemon-root scope marker is the primary kill authority** and executable/version mismatch is **stale-version evidence, not a skip gate** (FR-008). This is the direct fix for the 18-orphan leak: today the reaper requires the orphan's executable identity to match the foreground (skip-condition 3, `owner.py:767-777`), so old-version daemons are `skipped_out_of_scope` and pile up.

After this WP, the reaper consumes the WP01 classifier and reaps **only `safe_auto`** same-scope daemons (including older versions), while `operator_required` (pre-marker / cross-root / ambiguous) and `never_touch` are left strictly alone.

## Context & Constraints

Read before editing:
- [research.md](../research.md) — root-cause analysis + DD-01; [plan.md](../plan.md) IC-01/IC-03; [data-model.md](../data-model.md) decision table; [spec.md](../spec.md) FR-003, FR-006, FR-007, FR-008.
- WP01 gives you `classify_candidate`, `CandidateProbe`, `ForegroundScope`, `DaemonIdentityRecord` in `sync/classification.py` — **import and use them**; do not re-implement classification logic.

Current code (`sync/owner.py`):
- `reap_orphan_daemons(*, executable_scope=None, dry_run=False) -> ReapResult` (`:707-789`) — the 3-part AND-filter. **Skip-condition 3** (`:767-777`) is the one to demote.
- `ReapResult` (`:544-559`): `reaped`, `failed`, `skipped_out_of_scope`.
- Pure cmdline helpers to reuse for extraction: `_cmdline_daemon_root_marker` (`:613-624`), `_cmdline_has_daemon_spawn_signature` (`:627-641`), `_process_executable_scopes` (`:573-610`), `canonical_executable_scope` (near `:752`).
- Kill escalation: `_sweep_daemon_process` (`:644-705`) — keep using it; do not change its signature.
- `read_owner_record`/`redact_token` (`:242-302`) — reporting only; **never** kill authority (FR-003).

**Negative scope**: do NOT touch `daemon.py`/`orphan_sweep.py`/`classification.py` (other WPs). Preserve the existing cross-root and pre-marker safety — those must remain **non-reaped** (`operator_required`), exactly as the conservative reaper already protects them. The only behavior that changes is: a *same-scope* daemon with a *different version/executable* flips from skipped → reaped.

## Branch Strategy

- **Strategy**: lane-per-WP (from `lanes.json`)
- **Planning base branch**: `fix/sync-daemon-orphan-cleanup`
- **Merge target branch**: `fix/sync-daemon-orphan-cleanup`

> Depends on WP01 — branch from the dependency-aware base the implement command resolves.

## Subtasks & Detailed Guidance

### Subtask T006 – Thread the classifier into the reaper

- **Purpose**: Make the reaper produce `DaemonIdentityRecord`s instead of an opaque 3-way skip.
- **Files**: `src/specify_cli/sync/owner.py`.
- **Steps**:
  1. For each discovered candidate process, extract primitives with the existing helpers: `singleton_scope_id` via `_cmdline_daemon_root_marker`, `spawn_shape_ok` via `_cmdline_has_daemon_spawn_signature`, `executable_summary` via `_process_executable_scopes`.
  2. Build a `CandidateProbe`/`ForegroundScope` and call `classify_candidate`. For the startup reaper, the health self-report may be unavailable (it scans by cmdline, not by port) — pass `health=None` where you cannot cheaply self-report, which keeps non-provable candidates `operator_required` (consistent with D-01). Where the recorded singleton's port/health is known, populate `SingletonRef`.
- **Notes**: This is the reaper's discovery loop — keep it readable; extract a `_classify_orphan(proc, foreground)` helper (testable) to stay under complexity 15.

### Subtask T007 – Demote executable-identity skip to stale-version evidence (FR-008)

- **Purpose**: The core fix.
- **Files**: `src/specify_cli/sync/owner.py`.
- **Steps**:
  1. Remove skip-condition 3's behavior of dropping a candidate to `skipped_out_of_scope` purely because `_process_executable_scopes` does not contain the foreground scope. Executable mismatch is now *evidence*, recorded in `executable_summary`, not a gate.
  2. Keep skip-conditions 1 (daemon-root marker present + matches scope) and 2 (spawn-shape) as the **authority**: marker missing → `operator_required/pre_marker`; marker ≠ scope → `operator_required/cross_root`.
- **Notes**: Net effect — a same-scope daemon from a prior version (different executable) now classifies `safe_auto` and is reaped. Add a one-line comment citing FR-008 next to the removed gate so the rationale is discoverable (DIRECTIVE_003).

### Subtask T008 – Reap only safe_auto; structured skip_reason

- **Purpose**: Bound automatic action to provably-safe candidates.
- **Files**: `src/specify_cli/sync/owner.py`.
- **Steps**:
  1. Reap (`_sweep_daemon_process`) only candidates whose `cleanup_class == safe_auto`.
  2. Extend/augment `ReapResult` so skipped candidates carry their structured `skip_reason` and `cleanup_class` (not just a bare pid list). Keep backward-compatible fields if other callers read `reaped`/`failed`/`skipped_out_of_scope` — add the richer detail alongside (grep callers first).
- **Notes**: `never_touch` candidates are not reaped and need not be retained in the skip list unless already surfaced.

### Subtask T009 – Preserve singleton + cross-root safety; owner.json never authority

- **Purpose**: No regression in the conservative protections.
- **Files**: `src/specify_cli/sync/owner.py`.
- **Steps**:
  1. The current recorded singleton is never reaped (it is `is_recorded_singleton`).
  2. Cross-root / different-`$HOME` daemons stay `operator_required` and are never reaped at startup (only `auth doctor --reset --force` may touch them — WP05).
  3. Confirm no code path consults `read_owner_record()` to *decide* a kill (FR-003); it may only enrich reporting.
- **Notes**: This subtask is mostly assertions-in-tests + a careful read of the final diff.

### Subtask T010 – Reaper scope-authority tests

- **Purpose**: Prove FR-008 and the preserved safety.
- **Files**: `tests/sync/test_daemon_reaper_scope_authority.py` (new).
- **Steps**: Use the existing `_FakeProc` double pattern (`tests/sync/test_daemon_singleton_reaper_consolidation.py:67-80`) — no real subprocess needed here. Assert: (a) same-scope, different-version proc → reaped (FR-008); (b) cross-root proc → skipped `operator_required/cross_root`; (c) pre-marker proc → skipped `operator_required/pre_marker`; (d) recorded singleton → never reaped; (e) owner.json present but no marker → still not reaped (FR-003). Mark `@pytest.mark.unit`/`@pytest.mark.fast`.
- **Notes**: Live-subprocess coverage of this path lives in WP06 — keep WP02's tests fast/deterministic with doubles.

## Test Strategy

- `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_reaper_scope_authority.py -q`.
- Re-run the existing reaper consolidation suite to catch regressions: `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_singleton_reaper_consolidation.py -q`.
- `.venv/bin/ruff check src/specify_cli/sync/owner.py tests/sync/test_daemon_reaper_scope_authority.py` and `.venv/bin/mypy --strict src/specify_cli/sync/owner.py` — zero issues.

## Risks & Mitigations

- **Over-broad reaping**: the whole point is to reap *more* (same-scope stale) — but only `safe_auto`. Mitigation: the classifier gates on `singleton_scope_id == foreground.scope_id`; cross-root stays untouched. The WP06 live matrix + WP07 boundary matrix are the safety net.
- **Hidden callers of `ReapResult`**: grep for `skipped_out_of_scope`/`reaped` before changing the dataclass; keep existing fields populated.
- **Complexity**: extract `_classify_orphan` so `reap_orphan_daemons` stays ≤15.

## Review Guidance

- Confirm the executable-identity **gate** is gone and is now evidence only (FR-008) — the "same-scope, older version → reaped" test must prove it.
- Confirm cross-root/pre-marker are still **never** reaped (the conservative safety is intact).
- Confirm no kill decision reads `owner.json` (FR-003).
- Confirm only `safe_auto` is swept; `operator_required` is reported, not killed.

## Activity Log

- 2026-06-30T11:18:31Z – system – Prompt created.
- 2026-06-30T12:07:49Z – claude:sonnet:python-pedro:implementer – shell_pid=13697 – Assigned agent via action command
- 2026-06-30T12:36:19Z – claude:sonnet:python-pedro:implementer – shell_pid=13697 – Reaper uses _classify_orphan()+classify_candidate(); FR-008 exe-identity gate removed; same-scope daemons from prior versions now reaped; cross-root/pre-marker/singleton safety preserved; skipped_details carries DaemonIdentityRecord for each skipped candidate; ruff+mypy clean on src AND test (pre-existing owner.py mypy error not introduced by WP02). NOTE: 2 consolidation tests fail as expected FR-008 behavior change — test_reaper_skips_other_interpreter_daemons and test_reaper_skips_fully_rewritten_daemon_without_exec_marker need updating in review to reflect new reaped behavior.
- 2026-06-30T12:38:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=19008 – Started review via action command
- 2026-06-30T12:44:38Z – user – shell_pid=19008 – Moved to planned
- 2026-06-30T12:45:56Z – claude:sonnet:python-pedro:implementer – shell_pid=78096 – Started implementation via action command
- 2026-06-30T12:49:52Z – claude:sonnet:python-pedro:implementer – shell_pid=78096 – Cycle 1: updated 2 stale same-scope consolidation tests to assert reaped (FR-008); cross-root/pre-marker guards unchanged; both reaper suites green (31 passed); _sync_root mypy error confirmed pre-existing (present at stash/no-local-changes state); ruff + mypy clean on all modified files
- 2026-06-30T12:50:31Z – claude:opus:reviewer-renata:reviewer – shell_pid=85545 – Started review via action command
- 2026-06-30T12:54:34Z – user – shell_pid=85545 – Cycle 1 re-review passed: 2 stale same-scope assertions corrected to reaped (FR-008), cross-root/pre-marker/non-spawn safety tests unchanged+green, both suites green, ruff+mypy clean (pre-existing _sync_root noted separately)
