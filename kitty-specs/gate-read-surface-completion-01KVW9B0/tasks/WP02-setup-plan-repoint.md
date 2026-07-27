---
work_package_id: WP02
title: setup-plan re-point onto the kind-aware seam
dependencies:
- WP01
requirement_refs:
- FR-001
tracker_refs:
- '#2107'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
phase: Phase 1 - Gate-read spine (Lane A)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4061379"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – setup-plan re-point onto the kind-aware seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on
`authoritative_surface: tests/specify_cli/cli/commands/agent/`.

---

## Objective

Re-point `setup_plan` so it reads `spec.md` (and any planning artifact it consults) via
the **WP01 chokepoint** (`_planning_read_dir`, `kind=SPEC`) instead of the topology-aware
`_find_feature_directory` → `resolve_handle_to_read_path` (→ coord). This is **the
driver bug** (#2107): on a coord-topology / protected-primary mission, `setup_plan`
currently reads `coord/spec.md`, which does not exist (spec.md moved to primary in #2106),
and blocks with `SPEC_FILE_MISSING`.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-001; Scenario 1 (the driver); NFR-002, NFR-004.
- [plan.md](../plan.md) IC-02.
- [data-model.md](../data-model.md) site map row 1 (`mission.py:2224`, SPEC, RESIDUAL).
- [contracts/gate-read-seam.md](../contracts/gate-read-seam.md) G-1, the anti-mutant
  assertions.

The residual (live-verified):
- `setup_plan` defined at `mission.py:2044`.
- `mission.py:2203` — `feature_dir = _find_feature_directory(...)` (coord-aware resolver).
- `mission.py:2224` — `spec_file = feature_dir / "spec.md"` (reads the coord-resolved dir).

The fix: where `setup_plan` reads `spec.md` (and any other planning artifact), resolve the
read dir via WP01's `_planning_read_dir(repo_root, mission_slug, artifact_type="spec")`
instead of the coord-aware `feature_dir`. Keep any STATUS/non-planning use of `feature_dir`
unchanged (only the PLANNING reads move — C-002).

**Shared-`mission.py` serialization**: WP01 OWNS `mission.py`. This WP edits the
`setup_plan` region only. It depends on WP01 (the chokepoint must exist first) and its
`mission.py` edit is a well-justified out-of-map edit recorded with a one-line rationale
(`setup_plan` re-point onto WP01's `_planning_read_dir`). This WP OWNS only its test file.

**Negative scope**: no new resolver (C-001); no migration (C-004); no new CLI surface
(NFR-003 — `kind` is internal).

## Branch Strategy

- **Strategy**: `shared-lane` (Lane A; sequential on `mission.py` behind WP01)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> `lanes.json` governs the lane. WP02 serializes behind WP01 (dependency edge); the
> `setup_plan` `mission.py` edit is an out-of-map edit (WP01 owns the file).

## Subtasks & Detailed Guidance

### Subtask T006 – Red-first setup-plan repro via the PRE-EXISTING entry point

- **Purpose**: Drive the exact #2107 failure through the real `setup_plan` command before
  fixing — prove the coord/primary divergence (NFR-002/NFR-004).
- **Files**: new `tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py`.
- **Steps (red-first — DIRECTIVE_034)**:
  1. Seed `kitty-specs/gate-read-surface-completion-01KVW9B0/research/repro_2107_setupplan.py`
     (the triage repro is the seed — reuse its fixture shape). Build a **coord-topology**
     mission fixture where:
     - `spec.md` lives in the **primary** `target_branch` dir named `<slug>-<mid8>`.
     - The coordination worktree dir has NO `spec.md` (or a stale/empty one).
  2. Invoke the **pre-existing entry point** — `setup_plan(...)` (the command function),
     NOT `resolve_planning_read_dir` directly. Assert:
     - PRE-FIX: `setup_plan` blocks with `SPEC_FILE_MISSING` (reads coord). This is the RED.
     - POST-FIX: `setup_plan` reads the primary spec.md, finds it substantive, and advances
       the plan phase.
  3. **Composed-`<slug>-<mid8>` hazard (NFR-002)**: the primary dir MUST be
     `<slug>-<mid8>` (e.g. `gate-read-surface-completion-01kvw9b0`). A bare-slug dir is
     canonicalized and masks the divergence → false green. Use a real 26-char ULID
     `mission_id="01KVW9B0XFXPKTBE77QT3KRSW8"` and `mid8="01kvw9b0"`.
  4. Prove red: run the test against pre-WP02 `mission.py` (the coord-reading version) and
     confirm it goes RED with `SPEC_FILE_MISSING`. Record the red-run evidence in the log.

### Subtask T007 – Re-point the setup_plan spec.md read onto the seam

- **Purpose**: The actual fix (FR-001).
- **Files**: `src/specify_cli/cli/commands/agent/mission.py` (`setup_plan`, region ~2044-2230;
  out-of-map edit — WP01 owns the file).
- **Steps**:
  1. At `mission.py:2224` (`spec_file = feature_dir / "spec.md"`), resolve the read dir via
     the WP01 chokepoint:
     ```python
     spec_read_dir = _planning_read_dir(repo_root, mission_slug, artifact_type="spec")
     spec_file = spec_read_dir / "spec.md"
     ```
     using the `mission_slug` already in scope (or the handle `setup_plan` resolved).
  2. Audit `setup_plan` for ANY other planning-artifact read off `feature_dir` (e.g. plan.md
     scaffolding checks) and route each through `_planning_read_dir` with its artifact_type.
  3. Leave the coord-aware `feature_dir` (`:2203`) in place for any STATUS/non-planning use
     (e.g. status writes, worktree resolution). Only the PLANNING reads move (C-002).
- **Notes**: Record this as a one-line out-of-map rationale (WP01 owns `mission.py`). Do not
  touch the helper-pair internals — WP01 already retired those; this WP only consumes the
  chokepoint.

### Subtask T008 – Anti-mutant + flattened-regression assertions

- **Purpose**: Make the guard non-vacuous (NFR-004) and prove flattened-neutrality (NFR-001).
- **Files**: `tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py`.
- **Steps**:
  1. Anti-mutant: assert `setup_plan`'s PLANNING read resolves to `target_branch` for the
     coord-topology fixture (kills the "always coord" mutant). Add a comment: reverting the
     read to `resolve_handle_to_read_path`/`_find_feature_directory` MUST turn this RED.
  2. Flattened regression: a single-branch fixture (no coordination branch) — `setup_plan`
     reads `target_branch/spec.md`, behavior identical to today (NFR-001).
  3. Keep fixtures production-shaped (real ULID/mid8, composed dir name).

## Test Strategy

- `pytest tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py -q`.
- Red-first evidence required (revert+restore or clean-checkout run).
- `ruff check` + `mypy` on the touched `mission.py` region — zero issues, no suppressions.

## Definition of Done

- [ ] `setup_plan` spec.md read (and any other planning read) routed through
  `_planning_read_dir` (`kind=SPEC`); coord-aware `feature_dir` kept only for
  STATUS/non-planning use.
- [ ] Red-first test drives the real `setup_plan` command; RED pre-fix with
  `SPEC_FILE_MISSING`; GREEN post-fix; composed `<slug>-<mid8>` fixture (NFR-002).
- [ ] Anti-mutant assertion: planning read == `target_branch` for coord topology (NFR-004).
- [ ] Flattened-regression test green (NFR-001).
- [ ] ruff + mypy clean; out-of-map `mission.py` edit recorded with rationale.

## Risks & Mitigations

- **False-green via bare-slug fixture**: the single biggest hazard. Mitigation: composed
  `<slug>-<mid8>` primary dir, asserted explicitly (T006/T008).
- **Missed sibling read**: setup_plan may read more than spec.md. Mitigation: T007 step 2
  audits all planning reads in the function.
- **Shared `mission.py`**: serialized behind WP01 via dependency.

## Review Guidance

- Confirm the red-first test used a composed `<slug>-<mid8>` dir (ask for red-run evidence);
  a bare-slug fixture is a false-green and must be rejected.
- Confirm only PLANNING reads moved — STATUS/worktree uses of `feature_dir` are untouched
  (C-002).
- Confirm the anti-mutant assertion would go RED if the read reverted to the coord resolver.

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T15:37:21Z – claude:opus:python-pedro:implementer – shell_pid=4036986 – Assigned agent via action command
- 2026-06-24T15:48:12Z – claude:opus:python-pedro:implementer – shell_pid=4036986 – Lane-c code 7c311f275; status from main
- 2026-06-24T15:48:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=4061379 – Started review via action command
- 2026-06-24T15:52:25Z – user – shell_pid=4061379 – Review passed: setup_plan PLANNING reads (spec.md/plan.md) re-pointed to WP01 chokepoint _planning_read_dir(kind=SPEC/plan)->PRIMARY; feature_dir KEPT for emit_artifact_phase status/lifecycle (C-002 no over-reach). Reviewer-verified red-first: reverting the fix turns test_setup_plan_reads_primary_spec_for_coord_topology RED with SPEC_FILE_MISSING resolving the -coord husk; composed <slug>-<mid8> fixture + SAAS_SYNC unset confirmed (no false-green); anti-mutant guard (monkeypatch _planning_read_dir->candidate_feature_dir_for_mission) real; drives real setup-plan CLI via CliRunner. ruff clean; 3 mypy no-any-return at 1025/2646/4185 pre-existing on lane base (zero introduced). 4/4 tests pass.
