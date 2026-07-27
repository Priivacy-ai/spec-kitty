---
work_package_id: WP10
title: Behavioral verification, flattened regression, arch-gate sweep, issue-matrix closeout
dependencies:
- WP00
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
requirement_refs:
- FR-001
- FR-002
- FR-004
- FR-009
tracker_refs:
- '#2107'
- '#2085'
- '#1716'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
phase: Phase 3 - Closeout (verifies both lanes)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4172565"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: tests/missions/
create_intent:
- tests/missions/test_gate_read_two_surface_behavioral.py
- tests/missions/test_gate_read_flattened_regression.py
execution_mode: code_change
model: ''
owned_files:
- tests/missions/test_gate_read_two_surface_behavioral.py
- tests/missions/test_gate_read_flattened_regression.py
role: reviewer
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – Behavioral verification + closeout

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `reviewer-renata`
- **Role**: `reviewer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: tests/missions/`.

---

## Objective

Prove the whole mission behaviorally and close it out:
1. **Two-surface behavioral guard** (NFR-004): for a coord-topology mission, each gate
   command's PLANNING read resolves PRIMARY **AND** its STATUS read resolves COORD — in ONE
   fixture (kills both "always coord" and "always primary" mutants).
2. **Flattened regression** (NFR-001): every gate command behaves identically on a
   single-branch mission (planning + status both on `target_branch`).
3. **Full `tests/architectural/` arch-gate sweep** on the merged lane state (post-merge
   architectural-gate adjudication — per the standing memory).
4. **Issue-matrix terminal verdicts** for #2107/#2085/#2102/#2091/#2088/#2074/#2100; advance
   #1716/#1868/#1878.

This WP depends on ALL others (Lane A + Lane B).

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) NFR-001, NFR-002, NFR-004; the GitHub Issues Addressed table
  (intended verdicts).
- [plan.md](../plan.md) IC-11.
- [contracts/gate-read-seam.md](../contracts/gate-read-seam.md) the anti-mutant assertions.
- [data-model.md](../data-model.md) the full site map (the M-of-N checklist to verify).

## Branch Strategy

- **Strategy**: `closeout` (depends on all lanes; verifies the merged state)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP10 OWNS its two behavioral test files exclusively. The arch-gate sweep (T033) and
> issue-matrix closeout (T034) are verification/adjudication actions, not file edits to a
> third party's surface.

## Subtasks & Detailed Guidance

### Subtask T031 – Two-surface behavioral guard (NFR-004)

- **Purpose**: The anti-mutant proof across the gate commands in one coord fixture.
- **Files**: new `tests/missions/test_gate_read_two_surface_behavioral.py`.
- **Steps**:
  1. Build ONE coord-topology fixture (composed `<slug>-<mid8>` primary dir; real ULID
     `01KVW9B0XFXPKTBE77QT3KRSW8` / `01kvw9b0`) with planning artifacts on primary and
     status.events.jsonl + acceptance-matrix on coord.
  2. For each gate command with a **real, observable PLANNING read** — `setup_plan`, the
     accept gate, `map_requirements` — drive the PRE-EXISTING entry point and assert:
     - the PLANNING read ref == `target_branch` (primary), AND
     - where the command also reads STATUS, that read ref == coord.
  3. **`record_analysis` — remediation (reviewer-renata post-tasks):** do NOT assert
     "planning==primary" for `record_analysis`. After WP04's behavior-neutral double-
     resolution collapse, `record_analysis` has **no observable planning-read behavior delta**
     to assert — a "planning==primary" cell here is **vacuous**. Instead assert its
     **STATUS / self-bookkeeping ALLOWLIST** behavior: on the coord fixture, the
     record-analysis dirty-tree preflight does NOT block on `meta.json` / provenance (WP05
     allowlist) but STILL blocks on a stale primary `spec.md` (the G-5 "real dirt"
     invariant), and the analysis-report write targets primary. (The structural collapse
     itself is fenced by WP04's AST dedup guard + WP06's ratchet, not by a behavioral cell
     here.)
  4. Encode the mutant-kill comments: reverting any planning read (setup_plan / accept /
     map_requirements) to the topology resolver turns the planning assertion RED; reverting a
     status read turns the status assertion RED; over-allowlisting (`spec.md` allowlisted)
     turns the record_analysis G-5 assertion RED.
- **Notes**: This is the cross-command behavioral net that the per-WP tests prove
  individually; here it is asserted as ONE coherent two-surface contract — with
  record_analysis scoped to its observable STATUS/allowlist behavior, NOT a vacuous
  planning cell.

### Subtask T032 – Flattened-mission regression (NFR-001)

- **Purpose**: Prove behavior-neutrality for single-branch missions.
- **Files**: new `tests/missions/test_gate_read_flattened_regression.py`.
- **Steps**:
  1. Build a flattened/single-branch mission fixture (no coordination branch). Drive each gate
     command; assert every planning AND status read resolves `target_branch` — identical to
     pre-mission behavior.
  2. If a pre-mission golden snapshot exists, compare; otherwise assert the resolved dirs equal
     `target_branch` for both partitions.

### Subtask T033 – Full tests/architectural/ arch-gate sweep (post-merge adjudication)

- **Purpose**: Catch cumulative architectural-gate debt across the merged lane (per the
  standing post-merge arch-gate memory — per-WP review misses cumulative debt).
- **Files**: none (a verification action; record findings in the activity log + mission matrix).
- **Steps**:
  1. Run the FULL `tests/architectural/` suite on the consolidated lane state (after all WPs
     are on the lane base): `pytest tests/architectural/ -q`.
  2. Include the new FR-010 ratchet (WP06) and the terminology guard
     (`tests/architectural/test_no_legacy_terminology.py`) — both are CI-gating.
  3. For any failure: verify "pre-existing" claims via a cross-base diff (lane base ≠ mission
     base). Fix conservatively in-mission if caused by this mission's diff; file a burn-down
     ticket for genuinely pre-existing debt. Record the adjudication.

### Subtask T034 – Issue-matrix terminal verdicts + epic advancement

- **Purpose**: Close the mission's issues with evidence-backed verdicts.
- **Files**: the mission issue-matrix (in `kitty-specs/.../` per the mission convention) +
  tracker comments.
- **Steps**:
  1. Assign terminal verdicts per the spec's GitHub Issues table:
     - #2107 fixed (driver — setup-plan + accept reads on primary, behavioral proof).
     - #2085 fixed (acceptance-matrix accept facet).
     - #2102 fixed (record-analysis allowlist + bookkeeping).
     - #2091 regression-guarded (WP07).
     - #2088 regression-guarded (WP08).
     - #2074 instance-fixed (WP09; broader factory work stays with #2074).
     - #2100 partial / deferred-with-followup (touched modules only; log deferred 62-site
       backlog).
     - #1716 / #1868 / #1878 advanced.
  2. Use the in-mission issue-matrix verdict where a per-WP `approved`-but-not-`done` state
     applies (per the in-mission verdict convention).
  3. `unset GITHUB_TOKEN` before any `gh` call; comment on each issue naming the mission.

## Test Strategy

- `PWHEADLESS=1 pytest tests/missions/test_gate_read_two_surface_behavioral.py tests/missions/test_gate_read_flattened_regression.py -q`.
- `pytest tests/architectural/ -q` (full sweep, T033).
- `pytest tests/architectural/test_no_legacy_terminology.py -q` (terminology guard).
- `ruff check` + `mypy` on the new test files — zero issues, no suppressions.

## Definition of Done

- [ ] Two-surface behavioral guard green: planning→primary AND status→coord for the gate
  commands with an observable planning read (`setup_plan`, accept, `map_requirements`) in one
  coord fixture (NFR-004); composed `<slug>-<mid8>`.
- [ ] `record_analysis` asserted via its **STATUS/allowlist** behavior (no block on
  meta.json/provenance; STILL blocks on stale primary spec.md — G-5), NOT a vacuous
  planning==primary cell.
- [ ] WP00 write-twin verified: the finalize-tasks COMMIT resolves `target_branch` (not
  `main`) on the coord fixture — the FR-004/FR-009(e) write-side closeout.
- [ ] Flattened-regression green: all gate reads → `target_branch` on a single-branch mission
  (NFR-001).
- [ ] Full `tests/architectural/` sweep run on the consolidated lane; failures adjudicated
  (in-mission fix or burn-down ticket with cross-base diff evidence).
- [ ] FR-010 ratchet (WP06) + terminology guard pass.
- [ ] Issue-matrix terminal verdicts assigned with evidence; #2107/#2085/#2102 fixed;
  #2091/#2088 regression-guarded; #2074 instance-fixed; #2100 partial; #1716/#1868/#1878
  advanced.
- [ ] ruff + mypy clean; no suppressions.

## Risks & Mitigations

- **Cumulative arch-gate debt surfacing only at the merged state**: Mitigation: T033 full sweep
  + cross-base diff for "pre-existing" claims (the gate-unmask-cannot-self-validate lesson).
- **Single-partition behavioral test (vacuous)**: Mitigation: T031 asserts BOTH partitions in
  one fixture.
- **False-green bare-slug fixture**: Mitigation: composed `<slug>-<mid8>` (NFR-002).

## Review Guidance

- Confirm the two-surface test asserts BOTH planning==primary AND status==coord in ONE fixture
  for the commands with an observable planning read (setup_plan / accept / map_requirements).
- Confirm `record_analysis` is asserted via its STATUS/allowlist behavior, NOT a vacuous
  planning==primary cell (post-WP04 collapse it has no observable planning-read delta).
- Confirm the flattened regression covers all gate commands.
- Confirm the arch-gate sweep was run on the CONSOLIDATED state (not per-WP) and "pre-existing"
  claims were verified via cross-base diff.
- Confirm issue verdicts cite behavioral evidence, not just "code looks fixed".

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T16:45:40Z – user – Direct-on-feat closeout
- 2026-06-24T16:45:42Z – user – Closeout: verification + arch-gate + issue-matrix
- 2026-06-24T17:10:45Z – claude – WP10 closeout db436d23e on feat; arch-sweep 489/0; status from main
- 2026-06-24T17:10:46Z – claude:opus:reviewer-renata:reviewer – shell_pid=4172565 – Started review via action command
- 2026-06-24T17:20:39Z – user – shell_pid=4172565 – Moved to planned
- 2026-06-24T17:21:29Z – user – shell_pid=4172565 – cycle 2: format fix
- 2026-06-24T17:21:31Z – user – shell_pid=4172565 – cycle 2: reformat 2nd table to prose
- 2026-06-24T17:22:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=4172565 – cycle 2: single-table issue-matrix; arch-sweep 489/0 unchanged
- 2026-06-24T17:25:45Z – user – shell_pid=4172565 – Arbiter approve: substance validated cycle-1; format+verdict-vocabulary+follow-up-handles fixed
