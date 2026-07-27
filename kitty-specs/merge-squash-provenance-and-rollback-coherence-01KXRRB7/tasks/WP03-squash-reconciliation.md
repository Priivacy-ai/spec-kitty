---
work_package_id: WP03
title: 'Squash artifact reconciliation (#2709): meta.json field-driver, traces union, projection union + status.json'
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-005
- NFR-001
- C-006
tracker_refs:
- '2709'
planning_base_branch: fix/red-handling-policy-and-drg-regression-marks
merge_target_branch: fix/red-handling-policy-and-drg-regression-marks
branch_strategy: Planning artifacts for this mission were generated on fix/red-handling-policy-and-drg-regression-marks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/red-handling-policy-and-drg-regression-marks unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - Fix (#2709 chain)
assignee: ''
agent: "claude"
shell_pid: "3872736"
shell_pid_created_at: "1784354321.61"
history:
- timestamp: '2026-07-17T20:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent:
- src/specify_cli/upgrade/migrations/m_3_2_x_meta_traces_merge_drivers.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/lanes/merge.py
- src/specify_cli/cli/commands/merge_driver.py
- src/specify_cli/cli/commands/__init__.py
- src/specify_cli/cli/commands/init.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/merge/bookkeeping_projection.py
- src/specify_cli/upgrade/migrations/m_3_2_x_meta_traces_merge_drivers.py
- .gitattributes
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Squash artifact reconciliation (#2709)

## Objective
Make WP01 green: the squash merge must reconcile mission artifacts with target-newer
canonical state instead of `-X theirs` wholesale replacement, and the coord→target
projection must union (not blind-copy) the event log **and** rematerialize `status.json`.
Preserve planning-artifact authority (#1732).

## Sequenced subtasks
- **T005 — FR-004 meta.json field-driver SPIKE (do FIRST; top mission risk).** A custom
  `.gitattributes` merge driver for `kitty-specs/**/meta.json` that field-merges acceptance/VCS
  keys **target-authoritative** with `acceptance_history` unioned, planning keys mission-authoritative.
  Empirically confirmed: a custom driver fires under `git merge --squash -X theirs` when both sides
  diverge. If the driver proves unfit, fall back to a post-squash reconcile pass. **Fail fast here**
  so a spike failure does not block T006–T008.
- **T006 — FR-003 traces union.** A driver for `kitty-specs/**/traces/*.md` with a CONCRETE
  markdown-union contract (append-only, stable section delimiter, line-level dedup — traces have
  no natural key). Or descope traces to a post-merge reconcile if the union contract is unsound.
- **T007 — FR-005 projection union + status.json rematerialization (red-first WITHIN this WP).**
  Commit the FR-005 witnessing RED **first** as a distinct commit (US2-S4: a target-newer event
  on the projected `status.events.jsonl` AND a target-newer `status.json` field survive the
  projection) — RED on the WP base — **then** the fix commit.
  `merge/bookkeeping_projection.py::_project_status_bookkeeping_to_target` currently blind-writes
  two artifacts (`:306` events, `:308` status.json). Replace with: union `source ∪ original`
  (both byte-sets already captured at `:302-303`) via `merge_event_payloads` → write the
  `trusted_*` events path; rematerialize `status.json = reduce(union)` → write the `trusted_*`
  status path (from `_target_bookkeeping_status_paths`; compose NO new path). Extract
  `_union_event_logs` / `_rematerialize_status_snapshot` helpers (CC ≤ 15).
- **T008 — C-006 driver wiring.** Register both new drivers across ALL canonical surfaces:
  root `.gitattributes`; the init-time seed in **`src/specify_cli/cli/commands/init.py`**
  (`_EVENT_LOG_GITATTRIBUTES_ENTRY` / `required_entries` — NOT `src/specify_cli/__init__.py`);
  a new migration under `src/specify_cli/upgrade/migrations/` (sibling of
  `m_3_1_1_event_log_merge_driver.py`) — **mint a real version tag at implement time**
  (the `m_3_2_x_...` filename is a placeholder; use the next concrete tag and keep
  `create_intent`/`owned_files` in sync; migrations self-register via `@MigrationRegistry.register`
  + pkgutil auto-discovery, no central-list edit); the self-heal `_ensure_event_log_merge_driver_config`
  (**generalize/parametrize name+command — do NOT clone it**, DIRECTIVE_044); CLI registration.
  `_make_merge_env` PATH pin already covers new drivers.

## Acceptance criteria
- WP01's `tests/regression/test_issue_2709_squash_provenance.py` flips RED → GREEN.
- FR-005's own RED (US2-S4, a target-newer `status.json`/event survives the projection) — committed RED-first in T007 — flips GREEN; assert `snapshot == reduce(union)`.
- **Traces union contract (bind it, not "a section survives"):** (a) a target-newer trace section survives; (b) a section present on BOTH sides is **not duplicated** (line-level dedup); (c) the defined section delimiter is preserved. A naive `cat`-concat must FAIL these.
- **No #1732 regression:** a divergent planning artifact stays mission-authoritative (companion assertion).
- **NFR-001:** a squash with no target-side divergence is byte-identical to pre-fix.
- **Idempotency:** field-merge survives the post-merge baseline `meta.json` write and `--resume` (`allow_noop_squash`); pin a test that `write_meta(validate=False)` never drops an unknown key.

## Validation
- `PWHEADLESS=1 uv run pytest tests/regression/test_issue_2709_squash_provenance.py -n0 -q` (GREEN)
- `PWHEADLESS=1 uv run pytest tests/integration/test_merge_* tests/merge/ tests/specify_cli/cli/commands/test_merge_* -q`
- `ruff check` + `mypy` clean on touched files.

## Ownership
Owns the **whole** `src/specify_cli/merge/bookkeeping_projection.py`, plus `src/specify_cli/lanes/merge.py`, `cli/commands/merge_driver.py` (+ new driver cmd), `cli/commands/__init__.py`, `cli/commands/init.py`, root `.gitattributes`, the driver migration, `acceptance/__init__.py`. WP04 (the #2711 chain) edits ONLY `executor.py`/`done_bookkeeping.py`/`state.py` and consumes `bookkeeping_projection.py`'s capture/restore functions read-only — no file-level overlap. Campsite: the stale `_project_status_bookkeeping_to_target` shadow re-export in `cli/commands/merge.py.__all__`.

## Notes
Rebase-first (C-003); re-resolve symbols. This is the release-blocking chain.

**DIRECTIVE-003 decision — spike NOT split into its own WP (deliberate, overriding the plan's isolate-the-spike note).** The FR-004 meta.json driver, the FR-003 traces driver, and the C-006 wiring all mutate the SAME file set (`lanes/merge.py` self-heal, `merge_driver.py`, `.gitattributes`, `cli/commands/init.py`, the migration), so a file-level split into spike vs wiring WPs would create unavoidable `owned_files` overlap. The spike risk is instead isolated **temporally**: T005 runs FIRST and fails fast, and its failure path is a specified **fallback** (post-squash reconcile pass) — so a spike failure *pivots the approach within this WP*, it does not re-plan the WP. This preserves the isolate-the-spike intent without the ownership clash.

## Activity Log

- 2026-07-18T07:07:42Z – claude – shell_pid=3872736 – Moved to for_review
- 2026-07-18T07:08:10Z – claude – shell_pid=3872736 – reviewer-renata APPROVE: FR-003/004/005 spec-faithful; driver self-heal generalized to registry (not cloned); #1732 preserved; red integrity intact; #2709 set green under correct install. Gate skipped: pre-review gate confounded by driver-subprocess needing up-to-date install (env artifact), independently reviewed green.
