---
work_package_id: WP03
title: Accept-gate multi-site split — planning reads → seam, KEEP status reads
dependencies:
- WP01
requirement_refs:
- FR-002
tracker_refs:
- '#2107'
- '#2085'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase 1 - Gate-read spine (Lane A) - HIGHEST RISK
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4089624"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/
create_intent:
- tests/specify_cli/acceptance/test_accept_gate_read_surface.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/acceptance/__init__.py
- tests/specify_cli/acceptance/test_accept_gate_read_surface.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Accept-gate multi-site split (HIGHEST RISK)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on
`authoritative_surface: src/specify_cli/acceptance/`.

---

## Objective

Split the accept gate's **single `status_feature_dir` variable per-partition**: move the
~9 **planning reads** (spec/plan/tasks/research/data-model) off the coord-aware
`status_feature_dir` onto the WP01 chokepoint (→ primary), while **KEEPING the STATUS /
acceptance reads** (`status.events.jsonl`, acceptance-matrix) on `status_feature_dir`
untouched.

**This is the mission's core complexity** (FR-002, #2085): the risk is splitting the one
variable into a planning-read dir and a status-read dir **without breaking the
STATUS_STATE/events read or the status leniency fallback**.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-002; Scenario 2; C-002 (status leniency survives), C-003 (KEEP
  transients).
- [plan.md](../plan.md) IC-03 (highest risk).
- [data-model.md](../data-model.md) site map rows 2-9 (planning, RESIDUAL) + the KEEP rows
  (accept STATUS reads `:1174,749`).
- [contracts/gate-read-seam.md](../contracts/gate-read-seam.md) G-1 (planning→primary),
  G-2 (status→placed surface, UNCHANGED).

The accept cluster (live-verified):
- `status_feature_dir` defined at `acceptance/__init__.py:1114` via
  `_status_read_feature_dir(repo_root, feature, feature_dir)`.
- `_status_read_feature_dir` at `:731-750` — leniency fallback at `:749`
  (`status_dir if status_dir.exists() else feature_dir`). **KEEP this for status reads.**
- Planning reads cluster at `:1179-1186` (spec.md, plan.md, quickstart.md, tasks.md,
  research.md, data-model.md) — currently off `status_feature_dir`. **MOVE → seam.**
- `_missing_artifacts` at `:596` — checks required/optional planning artifacts off the same
  dir. **MOVE the planning-kind checks → seam.**
- STATUS read at `:1174` (`_validate_wp_readiness` — status.events.jsonl). **KEEP coord.**

**The split rule:**
- **Planning kind** (spec/plan/tasks/research/data-model/quickstart) → resolve its read dir
  via `_planning_read_dir` (WP01) / `resolve_planning_read_dir(kind=...)` → primary.
- **STATUS/acceptance kind** (status.events.jsonl, acceptance-matrix) → stays on
  `status_feature_dir` with its existing leniency (C-002).

**Shared chokepoint**: import WP01's seam. `mission.py:_planning_read_dir` is in a
different module — either import it or call `resolve_planning_read_dir` from
`_read_path_resolver` directly with the kind (acceptance already lives outside
`mission.py`; calling the resolver seam directly here is canonical, NOT a parallel
resolver — C-001 forbids a NEW resolver, not consuming the existing one). Prefer the
direct `resolve_planning_read_dir(repo_root, slug, kind=...)` call here, mapping each
artifact to its `MissionArtifactKind`.

**Negative scope**: do NOT touch the status leniency (`:749`), the STATUS_STATE/events read
(`:1174`), or the acceptance-matrix read. No new resolver (C-001). No migration (C-004).

## Branch Strategy

- **Strategy**: `shared-lane` (Lane A; independent module — no `mission.py` overlap)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP03 OWNS `acceptance/__init__.py` exclusively (no overlap with the `mission.py` WPs).
> It depends on WP01 only for the chokepoint contract; it may call the underlying
> `resolve_planning_read_dir` seam directly.

## Subtasks & Detailed Guidance

### Subtask T009 – Introduce a `planning_read_dir` alongside `status_feature_dir`

- **Purpose**: Create the second resolved dir so the per-partition split has two named
  surfaces, not one overloaded variable.
- **Files**: `src/specify_cli/acceptance/__init__.py` (near `:1114`).
- **Steps**:
  1. Keep `status_feature_dir = _status_read_feature_dir(...)` exactly as-is (it carries the
     STATUS reads + leniency).
  2. Resolve a `planning_read_dir` helper for planning artifacts. Because the accept cluster
     reads SEVERAL planning artifacts of the SAME primary partition, resolve once per kind
     via `resolve_planning_read_dir(repo_root, slug, kind=...)`. If all the read planning
     kinds are PRIMARY-partition (they are — spec/plan/tasks/research/data-model), they share
     one resolved primary dir; resolve it once (e.g. via `kind=SPEC`) and reuse, OR resolve
     per artifact for clarity. Add a one-line comment citing FR-002 / data-model.md.
- **Notes**: Do NOT rename `status_feature_dir` — minimize blast radius. The split is
  additive: a NEW `planning_read_dir`, the OLD `status_feature_dir` retained for status.

### Subtask T010 – Re-point the ~6 planning reads (`:1179-1186`) onto `planning_read_dir`

- **Purpose**: The core re-point (FR-002).
- **Files**: `src/specify_cli/acceptance/__init__.py` (`:1179-1186`).
- **Steps**:
  1. For each of spec.md / plan.md / quickstart.md / tasks.md / research.md / data-model.md,
     change the base dir from `status_feature_dir` to `planning_read_dir` (the primary
     surface).
  2. `quickstart.md` — confirm its kind. If it is a planning-doc kind it moves to primary;
     if it is not in `_ARTIFACT_TYPE_TO_KIND`, resolve its kind explicitly (the map raises on
     unmapped — no silent default). Document the kind decision in a code comment.
- **Notes**: Leave the existence-check / substantive-check logic intact — only the BASE dir
  changes from coord to primary.

### Subtask T011 – Re-point `_missing_artifacts` planning checks (`:596`)

- **Purpose**: The second planning-read site in the cluster (data-model rows 8-9).
- **Files**: `src/specify_cli/acceptance/__init__.py` (`_missing_artifacts`, `:596`).
- **Steps**:
  1. Thread `planning_read_dir` (or resolve it inside `_missing_artifacts`) so its
     required/optional **planning** artifact existence checks read primary.
  2. If `_missing_artifacts` also checks a STATUS/acceptance artifact, leave THAT check on
     the status dir (per-partition split inside the function too).
- **Notes**: Be surgical — `_missing_artifacts` is called by the gate; a wrong dir here
  re-introduces the #2107 block class.

### Subtask T012 – Verify STATUS reads + leniency are UNTOUCHED (C-002 guard)

- **Purpose**: Prove the split did NOT break the status path — the core risk.
- **Files**: `src/specify_cli/acceptance/__init__.py` (audit, no logic change here).
- **Steps**:
  1. Confirm `_status_read_feature_dir` (`:731-750`) and its leniency (`:749`) are
     byte-unchanged.
  2. Confirm the STATUS_STATE/events read (`:1174`, `_validate_wp_readiness`) and the
     acceptance-matrix read still consume `status_feature_dir` (coord under coord topology).
  3. Record the audit in the activity log: which reads moved (planning) vs stayed (status).

### Subtask T013 – Red-first two-surface behavioral test (DIRECTIVE_034/041)

- **Purpose**: Prove planning→primary AND status→coord in ONE coord-topology fixture (kills
  both the "always coord" and "always primary" mutants — NFR-004).
- **Files**: new `tests/specify_cli/acceptance/test_accept_gate_read_surface.py`.
- **Steps (red-first)**:
  1. Build a **coord-topology** fixture (composed `<slug>-<mid8>` primary dir) where:
     - planning artifacts (spec/plan/tasks/research/data-model) live on **primary**.
     - status.events.jsonl + acceptance-matrix live on the **coord** surface.
  2. Drive the accept gate through its **pre-existing entry point** (the accept/acceptance
     function — NOT the resolver directly). Assert:
     - The gate finds the planning artifacts (reads primary) — does NOT mis-block as missing.
     - The STATUS read still resolves the coord surface (events/acceptance-matrix consulted).
  3. Prove red: against pre-WP03 `acceptance/__init__.py` (planning off `status_feature_dir`),
     the gate mis-blocks (planning artifacts "missing" because it read coord). Record evidence.
  4. Anti-mutant comment: reverting any planning read to `status_feature_dir` MUST turn the
     planning assertion RED; reverting the status read to the planning dir MUST turn the
     status assertion RED.
  5. Add a **flattened** fixture: both partitions resolve `target_branch` (NFR-001).
  6. Real ULID/mid8 fixtures (`01KVW9B0XFXPKTBE77QT3KRSW8` / `01kvw9b0`).

## Test Strategy

- `pytest tests/specify_cli/acceptance/test_accept_gate_read_surface.py -q`.
- Red-first evidence required (clean-checkout or revert run of `acceptance/__init__.py`).
- `ruff check src/specify_cli/acceptance/__init__.py` + `mypy` — zero issues, no suppressions.

## Definition of Done

- [ ] `planning_read_dir` introduced alongside `status_feature_dir`; the latter unchanged.
- [ ] The ~6 planning reads (`:1179-1186`) re-pointed to primary via the seam.
- [ ] `_missing_artifacts` (`:596`) planning checks re-pointed to primary; status checks kept.
- [ ] STATUS_STATE/events read (`:1174`), acceptance-matrix read, and the leniency (`:749`)
  proven UNTOUCHED (C-002 audit recorded).
- [ ] Red-first two-surface test: planning→primary AND status→coord in one coord fixture;
  RED pre-fix (mis-blocks); GREEN post-fix; composed `<slug>-<mid8>` (NFR-002/NFR-004).
- [ ] Flattened-regression test green (NFR-001).
- [ ] ruff + mypy clean; no suppressions.

## Risks & Mitigations

- **Breaking the status path (the core risk)**: a careless rename of `status_feature_dir`
  or a wrong dir on the events read re-blocks accept or loses status. Mitigation: ADDITIVE
  split (new `planning_read_dir`, keep `status_feature_dir`); T012 audit; the two-surface
  test asserts BOTH partitions.
- **Mis-classified artifact (quickstart)**: Mitigation: explicit kind decision via the map
  (no silent default).
- **False-green via bare-slug fixture**: Mitigation: composed `<slug>-<mid8>` dir (T013).

## Review Guidance

- Confirm `status_feature_dir`, `_status_read_feature_dir`, the leniency (`:749`), and the
  events/acceptance-matrix reads are byte-unchanged (the split is additive, not a rename).
- Confirm the two-surface test asserts planning==primary AND status==coord in ONE fixture
  (a single-partition test is vacuous here) and used a composed `<slug>-<mid8>` dir.
- Confirm red-run evidence shows pre-fix mis-block. Reject a false-green bare-slug fixture.
- Confirm quickstart's kind decision is explicit (no silent default).

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T15:37:25Z – claude:opus:python-pedro:implementer – shell_pid=4037630 – Assigned agent via action command
- 2026-06-24T15:57:45Z – claude:opus:python-pedro:implementer – shell_pid=4037630 – Accept-gate planning reads split onto WP01 kind-aware seam (primary); STATUS reads (events/acceptance-matrix) + leniency byte-unchanged on coord (C-002). Additive _planning_read_dir + explicit kind map (quickstart=CHECKLIST) + loud invariant guard (NFR-004). Red-first two-surface anti-mutant test on composed slug-mid8 coord fixture; both mutants killed. Remediated stale coord-read regression test to FR-002. ruff+mypy clean; acceptance suite green; lane rebased.
- 2026-06-24T15:59:00Z – claude:opus:python-pedro:implementer – shell_pid=4037630 – Lane-d code 2b63b7559; status from main
- 2026-06-24T15:59:01Z – claude:opus:reviewer-renata:reviewer – shell_pid=4089624 – Started review via action command
- 2026-06-24T16:05:10Z – user – shell_pid=4089624 – Review passed (reviewer-renata): FR-002 accept-gate multi-site split verified. STATUS reads byte-unchanged on coord (events _collect_snapshot_wps/_validate_wp_readiness=status_feature_dir, acceptance-matrix via _check_lane_gates=read_feature_dir, leniency :749) — C-002 held. Both anti-mutant reverts performed by reviewer: status-read->primary turned test_status_read_resolves_coord RED ('No canonical state'); planning-read(_missing_artifacts)->coord turned test_planning_reads_resolve_primary AND the remediated regression test RED — both mutants killed, partitions independent. Stale-test remediation legitimate (delete-the-assertion-not-the-test: coord-IS-planning drift inverted to primary-read contract, setup preserved, anti-false-green proven). _accept_planning_artifact_kinds explicit per-kind map (quickstart=CHECKLIST) + loud invariant guard, no silent default. ruff clean; mypy = 5 pre-existing baseline errors (205/478/728/898/1018), ZERO introduced. Full acceptance suite 56 passed.
