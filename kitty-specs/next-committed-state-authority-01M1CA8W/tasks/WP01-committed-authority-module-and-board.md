---
work_package_id: WP01
title: Committed-authority module + status board
dependencies: []
requirement_refs:
- FR-004
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-002
- C-004
- C-005
planning_base_branch: fix/next-committed-state-authority
merge_target_branch: fix/next-committed-state-authority
branch_strategy: Planning artifacts for this mission were generated on fix/next-committed-state-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/next-committed-state-authority unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-next-committed-state-authority-01M1CA8W
base_commit: d4fc20d2663faa81fff4bb8f58a3508bcc471781
created_at: '2026-08-31T17:07:00.284635+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history: []
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/committed_authority.py
- tests/runtime/next/test_committed_authority.py
- tests/specify_cli/cli/commands/agent/test_tasks_status_committed_authority.py
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/runtime/next/committed_authority.py
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
- tests/runtime/next/test_committed_authority.py
- tests/specify_cli/cli/commands/agent/test_tasks_status_committed_authority.py
role: implementer
tags: []
tracker_refs: []
---

# WP01 — Committed-authority module + status board

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Build the single **committed-authority** module that both fixes in this mission consume, and fix the `agent tasks status` board so its lane rollup reads committed authority instead of a stale coordination checkout. This is the foundation layer (WP02 — the `next` loop — depends on it).

## Context

This mission (issues #2947, #3780) routes the `spec-kitty next` loop and the status board through the **committed status authority** + the shipped **operator-provenance authority** (`src/specify_cli/status_lanes.py` — `is_acceptable_ending` :42, `has_operator_provenance` :70), instead of a stale coordination worktree checkout or a lane-only predicate. **Read** `../spec.md`, `../plan.md`, and `../research.md` before starting — `research.md` is the file:line disambiguation map.

Load-bearing design decisions this WP implements (from `../tracer-design-decisions.md`):
- **D11 / IC-01** — factor the acceptable-ending fold ONCE so there is a single authority definition (FR-007, DIRECTIVE_044). Both the #3780 predicate and the #2947 terminal check consume it.
- **D6 / C-004 / C-003** — derive lane AND `reason_source` from a **single** status reduction per WP, fronted by an explicit `has_event_log`/`_require_event_log` gate that preserves the `CanonicalStatusNotFoundError` fail-loud contract. A naive `get_wp_lane`→`wp_snapshot_state` swap silently breaks fail-loud: `get_wp_lane` raises on an absent log via `_require_event_log` (`src/specify_cli/status/lane_reader.py:36`, called `:63`); `wp_snapshot_state` (`src/specify_cli/status/reducer.py:532`) returns `None` silently on an empty/absent log.
- **D9 / IC-02 / C-005** — the terminal verdict reads `mission_number` + committed status from the **PRIMARY/committed surface** (never the coord checkout), keyed on the committed `mission_number` ONLY (assigned at merge, `merge/ordering.py:135`; `None` pre-merge) — never transient merge-state / `MERGE_HEAD`. **Sanctioned primitives** (BLOCKER-1: the old `primary_feature_dir_for_mission` is DELETED and manual primary-path composition trips `tests/architectural/test_no_read_side_bypass.py`, which does NOT sanction `src/runtime/next/`): read `mission_number` via `read_primary_meta(repo_root, mission_slug)` (`_read_path_resolver.py:819`, returns `(primary_meta, declares_coordination)` → `primary_meta.get("mission_number")`); resolve the primary feature dir via `runtime.next.runtime_bridge_identity._primary_runtime_feature_dir(repo_root, mission_slug)` (the identity seam — it does NOT import `runtime_bridge`, so no import cycle; use a function-level import to be safe).
- **D10 / IC-04 / F2** — the `agent tasks status` board is NOT fixed "by construction" by the loop change; its lane read must be pointed at committed authority here, and the legacy stale fallback closed.

**Do NOT** modify `status_lanes.is_acceptable_ending` / `has_operator_provenance` (C-001), the lane state machine (C-002), or `runtime_bridge.py` (owned by WP02). **Do NOT** edit `_resolve_mission_read_path`'s pure-path behavior.

### Subtask T001: RED — board regression for the merged mission (#2947, FR-004)

**Purpose**: Land a failing, issue-pinned regression proving `agent tasks status` misreports a merged mission today, before the fix.

**Steps**:
1. In `tests/specify_cli/cli/commands/agent/test_tasks_status_committed_authority.py`, build a fixture mission with **two distinct on-disk surfaces** (this split IS the bug — a single-dir fixture would not exercise it, SHOULD-FIX-6):
   - **PRIMARY**: committed `meta.json` with `mission_number` assigned (a real int — copy the shape from `tests/fixtures/clean_install_fixture_mission/.../meta.json`), and a committed status event log showing every WP `done`/`approved`.
   - **stale COORD checkout**: a coord `feature_dir` whose event log shows the WPs still `planned` (or is missing the artifacts).
   - Add an explicit assertion that the two surfaces diverge (primary=accepted, coord=planned) so the stale-coord leg is genuinely under test.
2. Mark `@pytest.mark.regression` and reference `#2947` in the test name/docstring.
3. Assert `agent tasks status --mission <slug> --json` (through the real command entry) reports each WP in its committed accepted lane — NOT `planned`.
4. Confirm the test is **RED** on the current lane branch (`git stash` any fix; run it) and record the failure in `baseline-tests.json` context.

**Files**: `tests/specify_cli/cli/commands/agent/test_tasks_status_committed_authority.py` (new, ~120 lines). Reuse existing tasks-status test fixtures/helpers where available (grep `tests/specify_cli/cli/commands/agent/` for status fixtures; `_write_status_events` in `tests/specify_cli/next/test_runtime_bridge.py:84` writes a lane event log).
**Validation**: test fails on base for the documented reason (all-`planned` rollup), not a fixture error.

### Subtask T002: RED — unit contracts for `committed_authority` (FR-006, FR-007, FR-009, C-003, C-004)

**Purpose**: Pin the module's contract before implementing it.

**Steps**:
1. In `tests/runtime/next/test_committed_authority.py`, write unit tests for the two public functions (defined in T003/T004):
   - `wp_ending(feature_dir, wp_id)`: a canceled WP with `reason_source="operator"` → acceptable=True; a synthetic cancellation (`reason: None`, or `"Force move to "`/`"move-task: "` prefixes) → acceptable=False; `approved`/`done` → acceptable=True; other lanes → False. A genuinely-absent status log → **raises** `CanonicalStatusNotFoundError` (fail-loud, C-003).
   - `mission_terminal_verdict(repo_root, mission_slug)`: `mission_number` assigned + all-WP acceptable → `terminal`; `mission_number` assigned + some WP not acceptable → `blocked_conflict` (FR-009); `mission_number` absent → `none`; committed status log genuinely absent → `none` (NOT conflict — C-003).
2. Assert the single-reduction property (C-004): use a spy/counter on the reduce/read path to prove `wp_ending` performs exactly one reduction per WP (no `get_wp_lane` + `wp_snapshot_state` double read). Mark these `@pytest.mark.regression` where they pin issue behavior.
3. Confirm RED (module/functions do not exist yet).

**Files**: `tests/runtime/next/test_committed_authority.py` (new, ~140 lines).
**Validation**: tests fail because `committed_authority` is unimplemented.

### Subtask T003: Implement IC-01 — `wp_ending` acceptable-ending fold (FR-006, FR-007, C-003, C-004, NFR-002)

**Purpose**: The one authority atom, single reduction + fail-loud.

**Steps**:
1. Create `src/runtime/next/committed_authority.py`.
2. Implement `wp_ending(feature_dir, wp_id) -> WpEnding` (a small dataclass/NamedTuple with `lane: str`, `acceptable: bool`, `reason_source: str | None`):
   - Perform **one** status reduction that yields the per-WP snapshot (lane + `reason_source`). Front it with an explicit `has_event_log`/`_require_event_log` guard so an absent log raises `CanonicalStatusNotFoundError` (mirror `lane_reader.py:43`), NOT a silent empty read.
   - `acceptable = is_acceptable_ending(lane, has_provenance=has_operator_provenance(snapshot))` — consume the shipped authority; do not reimplement.
3. Keep it pure (no CLI/console side effects). Type-annotate for mypy --strict.

**Files**: `src/runtime/next/committed_authority.py` (new; IC-01 ≈ 40 lines).
**Validation**: T002 `wp_ending` cases + single-reduction assertion pass.

### Subtask T004: Implement IC-02 — `mission_terminal_verdict` from the PRIMARY surface (FR-009, C-005, C-003, D9)

**Purpose**: Terminal/conflict verdict from committed authority.

**Steps**:
1. In `committed_authority.py`, implement `mission_terminal_verdict(repo_root, mission_slug) -> TerminalVerdict` (enum/literal: `"terminal" | "blocked_conflict" | "none"`).
2. Read `mission_number` from the **primary** meta.json via `read_primary_meta(repo_root, mission_slug)` (`_read_path_resolver.py:819`, returns `(primary_meta, declares_coordination)` → `primary_meta.get("mission_number")`); resolve the committed status surface from `runtime_bridge_identity._primary_runtime_feature_dir(repo_root, mission_slug)` (function-level import) — the committed PRIMARY surface, NOT `mission_context_for`'s selection, and NOT the deleted `primary_feature_dir_for_mission` (BLOCKER-1). Do NOT hand-compose the primary path (trips `test_no_read_side_bypass`).
3. Fold every WP through `wp_ending` (IC-01). Decide:
   - `mission_number` present AND all WPs acceptable → `terminal`.
   - `mission_number` present AND not all acceptable → `blocked_conflict`.
   - `mission_number` absent → `none`.
   - Committed status log genuinely absent → `none` (fall through to today's behavior; do NOT read absence as conflict — C-003).
4. Merge signal is `mission_number` ONLY — never read merge-state.json / `MERGE_HEAD` (C-005).

**Files**: `src/runtime/next/committed_authority.py` (IC-02 ≈ 45 lines).
**Validation**: T002 `mission_terminal_verdict` cases pass.

### Subtask T005: Implement IC-04 — board reads committed lanes (FR-004, D10, F2)

**Purpose**: Fix the `agent tasks status` lane rollup and close the legacy stale route.

**Steps**:
1. In `src/specify_cli/cli/commands/agent/tasks_status_cmd.py`, trace `_st_resolve_dirs` (:152, resolve :178, legacy fallback :180–185) → `_st_runtime_row`→`reconstruct_wp_view` (imported :219, called :222). Point the WP lane/status read at committed authority (the primary/committed status surface), consistent with how `tasks/` is already read from PRIMARY (:193).
2. **Consume the WP01 module** for the committed lane (e.g. `committed_authority.wp_ending(...).lane`, or add a thin `committed_wp_lane` accessor to `committed_authority.py` if cleaner). This is deliberate (NICE-8): it gives `committed_authority.py` an in-WP01 importer so the module is not flagged as dead before WP02 wires its consumers.
3. Close the legacy fallback (:180–185) path so it cannot re-introduce a stale coord read (F2).
4. Keep the change minimal and localized; do not alter unrelated board columns.

**Files**: `src/specify_cli/cli/commands/agent/tasks_status_cmd.py` (modify; ~15–40 lines).
**Validation**: T001 board regression turns **GREEN**; existing tasks-status tests stay green (run `tests/specify_cli/cli/commands/agent/`).

### Subtask T006: Campsite tidy + scope/quality gate (DIRECTIVE_025, C-006)

**Purpose**: Leave touched surfaces clean and prove scope integrity.

**Steps**:
1. Ruff + mypy --strict clean on all owned files (no new `# noqa`/`# type: ignore`; complexity ≤15). Add docstrings for the public functions.
2. Terminology check on new prose/docstrings (committed status authority vs coordination worktree checkout; `spec-kitty agent`-facing text). Run `pytest tests/architectural/test_no_legacy_terminology.py`.
3. Confirm NO diff to `status_lanes.py` (C-001) or the lane state machine (C-002); confirm `_resolve_mission_read_path` pure-path behavior unchanged.
4. **Architectural gates for the NEW module (NICE-8)** — run `tests/architectural/test_no_dead_modules.py`, `test_no_dead_symbols.py`, `test_no_read_side_bypass.py`, and `test_arch_shard_marker_completeness.py`. Because `committed_authority.py` is consumed by the board (T005) within this WP, it should not read as dead; if a symbol still trips the dead-symbol gate, prefer no `__all__` export (the module is under `src/runtime/next/`, not `src/charter`/`src/kernel`, so `__all__` is not required) over adding an allowlist entry. Confirm `test_no_read_side_bypass` passes (you used the sanctioned `_primary_runtime_feature_dir`/`read_primary_meta`, not manual path composition).
5. Run targeted suites: `tests/runtime/next/test_committed_authority.py`, `tests/specify_cli/cli/commands/agent/`.

**Files**: touched files only.
**Validation**: ruff/mypy/terminology green; targeted tests green.

## Definition of Done

- T001 board regression (`@pytest.mark.regression`, #2947) was RED on the lane's `planning_base_branch` and is GREEN at final.
- `committed_authority.py` exposes `wp_ending` (IC-01, single reduction + fail-loud) and `mission_terminal_verdict` (IC-02, primary-surface, `mission_number`-keyed) with unit coverage (T002) including the single-reduction and fail-loud assertions.
- `agent tasks status` reports committed lanes for a merged mission; the legacy stale fallback is closed.
- No diff to `status_lanes.py`, the lane state machine, or `_resolve_mission_read_path`'s behavior.
- Ruff + mypy --strict + terminology-guard clean; per-subtask completion recorded via `spec-kitty agent tasks mark-status <Txxx> --status done`.
- Implementation command: `spec-kitty agent action implement WP01 --agent <name>`.

## Risks

- **Fail-loud regression (C-003)**: forgetting the explicit `has_event_log` gate turns a missing-authority error into a silent `none`. Mitigation: the T002 fail-loud test.
- **Double reduction (C-004)**: reusing both `get_wp_lane` and `wp_snapshot_state` per WP. Mitigation: the T002 single-reduction counter assertion.
- **Board legacy fallback (F2)**: the `:179–188` fallback silently re-deriving a stale path. Mitigation: T001 fixture includes the stale coord checkout; close the fallback.
- **Surface confusion (D9)**: reading `mission_number`/status from the coord surface instead of PRIMARY. Mitigation: use `read_primary_meta` / `primary_feature_dir_for_mission` explicitly.

## Reviewer Guidance

- Confirm exactly ONE reduction per WP in `wp_ending` and that the fail-loud path raises (not returns None).
- Confirm `mission_terminal_verdict` reads the PRIMARY surface only and keys on `mission_number` (never merge-state/`MERGE_HEAD`).
- Confirm the board reads committed lanes and the legacy fallback is closed — with the stale-coord fixture proving it.
- Confirm zero diff to the shipped `is_acceptable_ending`/`has_operator_provenance` authority and to `_resolve_mission_read_path` behavior.
