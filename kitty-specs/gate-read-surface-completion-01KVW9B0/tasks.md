# Tasks: Gate-command Read-surface Completion

**Mission**: gate-read-surface-completion-01KVW9B0
**Branch**: `feat/gate-read-surface-completion`
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [data-model.md](./data-model.md) · [contracts/gate-read-seam.md](./contracts/gate-read-seam.md) · [research.md](./research.md)

Complete the **read side** of #2106's write re-partition: every planning-lifecycle
GATE/verify command resolves planning-artifact reads through the single kind-aware seam
(`resolve_planning_read_dir`) instead of the topology-aware resolver (→ coord) or a bespoke
per-command workaround. Brownfield consolidation (~13-15 planning-read sites, 4 bespoke
workarounds retired onto one seam, FR-009) fenced by a literal-ban ratchet (FR-010). Two
lanes: **A** (gate-read spine + consolidation + ratchet, sequential on `mission.py`) and
**B** (lock the 3 already-landed #1716 residual fixes with scenario-driving guards, fully
parallel from base). Forward-only (C-004); behavior-neutral for flattened missions (NFR-001);
build on #2106's seam, no new resolver (C-001/C-006).

## IC → WP mapping

| IC | WP | Lane |
|----|----|------|
| IC-00 write-surface resolver foundation (write twin; unblocks the implement loop) | WP00 | Foundation |
| IC-01 chokepoint seam + retire helper pair | WP01 | A |
| IC-02 setup-plan re-point | WP02 | A |
| IC-03 accept-gate multi-site split (highest risk) | WP03 | A |
| IC-04 map-requirements + record-analysis collapse | WP04 | A |
| IC-05/IC-06 bookkeeping allowlist + meta-reader sweep | WP05 | A |
| IC-07 literal-ban ratchet | WP06 | A |
| IC-08 #2091 next mid8 guard | WP07 | B |
| IC-09 #2088 ownership-overlap guard | WP08 | B |
| IC-10 #2074 fixture re-pin | WP09 | B |
| IC-11 behavioral verification + closeout | WP10 | A+B |

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T000a | Red-first: drive `get_feature_target_branch`/`resolve_target_branch` (RED→`main`) | WP00 | — |
| T000b | Fix both write-side resolvers onto `primary_feature_dir_for_mission` | WP00 | — |
| T000c | Fix the finalize-tasks COMMIT (site #14) onto the primary write seam | WP00 | — |
| T000d | Red-first regression: finalize-tasks COMMIT → `target_branch` (not `main`) | WP00 | — |
| T000e | FR-004/FR-009(e) write-side audit (no `candidate_feature_dir` write-branch) | WP00 | — |
| T001 | Add the `_planning_read_dir` chokepoint helper (wraps `_artifact_kind_for` + seam) | WP01 | — |
| T002 | Retire `_primary_anchored_feature_dir` onto the seam | WP01 | — |
| T003 | Retire `_resolve_mission_dir_name_primary_anchored` planning-read callers | WP01 | — |
| T004 | FR-009 audit: no parallel primary-anchor planning-read survives | WP01 | — |
| T005 | Red-first chokepoint behavioral test (composed `<slug>-<mid8>`) | WP01 | — |
| T006 | Red-first setup-plan repro via the real `setup_plan` entry point | WP02 | — |
| T007 | Re-point `setup_plan` spec.md read onto the seam (`kind=SPEC`) | WP02 | — |
| T008 | Anti-mutant + flattened-regression assertions for setup-plan | WP02 | — |
| T009 | Introduce `planning_read_dir` alongside `status_feature_dir` (accept) | WP03 | — |
| T010 | Re-point the ~6 planning reads (`:1179-1186`) → primary | WP03 | — |
| T011 | Re-point `_missing_artifacts` planning checks (`:596`) → primary | WP03 | — |
| T012 | Verify STATUS reads + leniency UNTOUCHED (C-002 guard) | WP03 | — |
| T013 | Red-first two-surface accept test (planning→primary AND status→coord) | WP03 | — |
| T014 | Red-first map-requirements repro via the entry point | WP04 | — |
| T015 | Re-point map-requirements WP-tasks read (`kind=WORK_PACKAGE_TASK`) | WP04 | — |
| T016 | Collapse record-analysis planning-read double-resolution onto the seam | WP04 | — |
| T017 | Record-analysis collapse: AST dedup guard (NOT a behavioral red-first) | WP04 | — |
| T018 | Add the self-bookkeeping allowlist (DISTINCT from coord-residue) | WP05 | — |
| T019 | Wire the allowlist into the dirty-tree preflight classification | WP05 | — |
| T020 | In-mission meta-reader sweep (touched modules only) | WP05 | — |
| T021 | Red-first allowlist + sweep tests (stale-spec-is-dirt invariant) | WP05 | — |
| T022 | Build the literal-ban AST/source scan | WP06 | — |
| T023 | Assert consolidated state GREEN + allow-list the KEEPs | WP06 | — |
| T024 | Anti-mutant proof: re-introduce a violation → RED | WP06 | — |
| T025 | Red-first #2091 empty-mid8 guard via the `next` entry point | WP07 | [P] |
| T026 | Prove RED by reverting the `runtime_bridge.py` guard | WP07 | [P] |
| T027 | Red-first #2088 dep-exemption guard via finalize-tasks --validate-only | WP08 | [P] |
| T028 | Prove RED by reverting the `validation.py` exemption | WP08 | [P] |
| T029 | Re-pin #2074 fixture to production-shaped `meta.json` (canonical factory) | WP09 | [P] |
| T030 | Prove the re-pin exercises the real `resolve_mid8` routing | WP09 | [P] |
| T031 | Two-surface behavioral guard across gate commands (NFR-004) | WP10 | — |
| T032 | Flattened-mission regression (NFR-001) | WP10 | — |
| T033 | Full tests/architectural/ arch-gate sweep (post-merge adjudication) | WP10 | — |
| T034 | Issue-matrix terminal verdicts + epic advancement | WP10 | — |

---

## WP00 — Write-surface resolver foundation (implemented FIRST; unblocks the implement loop)

**Prompt**: [tasks/WP00-write-surface-resolver-foundation.md](tasks/WP00-write-surface-resolver-foundation.md)

**Summary**
- **Goal**: Re-point the write-side surface resolution onto the primary/kind-aware seam — the consolidation's WRITE twin. Fix `get_feature_target_branch` (`core/paths.py:617`) and `resolve_target_branch` (`core/git_ops.py:371`) — both resolve `meta.json` via `candidate_feature_dir_for_mission` (→ coord, no meta.json → fallback `resolve_primary_branch()` → `main`) — onto `primary_feature_dir_for_mission` (mirroring the already-proven `resolve_merge_target_branch:665`). ALSO fix the finalize-tasks COMMIT (site #14, FR-009(e)) in `mission.py`. **This fixes the editable CLI so the implement loop runs** — a chicken-and-egg blocker (debbie post-tasks): `implement WP##` and `finalize-tasks` both misresolve their commit/planning branch to protected `main` and refuse to proceed until this lands.
- **Priority**: P0 — foundation; lands FIRST. WP01/WP07/WP08/WP09 depend on it.
- **Independent test**: `get_feature_target_branch`/`resolve_target_branch`/`finalize_tasks` on a coord-topology composed-`<slug>-<mid8>` fixture resolve `target_branch`, not `main`; RED on unfixed code.

**Tracking**
- [ ] T000a Red-first: drive the real write-resolution entry points (RED→`main`) (WP00)
- [ ] T000b Fix `get_feature_target_branch` + `resolve_target_branch` (WP00)
- [ ] T000c Fix the finalize-tasks COMMIT (site #14) (WP00)
- [ ] T000d Red-first regression: finalize-tasks COMMIT → `target_branch` (WP00)
- [ ] T000e FR-004/FR-009(e) write-side audit (WP00)

**Dependencies**: none (foundation; lands FIRST so the editable CLI is correct before any other WP's implement loop runs).
**Owned files**: `src/specify_cli/core/paths.py`, `src/specify_cli/core/git_ops.py`, `tests/specify_cli/core/test_write_surface_resolver_foundation.py`, `tests/specify_cli/cli/commands/agent/test_finalize_tasks_commit_surface.py`. **Out-of-map**: the finalize-tasks COMMIT fix edits `mission.py` (WP01-owned) — disjoint functions (`_resolve_feature_target_branch:482` / `_resolve_planning_branch:981` / `finalize_tasks:2806+` vs WP01's `~1106-1357`); WP00 lands before WP01, so WP01 branches from a base already containing the edit (serialized via the WP01→WP00 dep edge).
**Estimated prompt size**: ~230 lines.

---

## WP01 — Chokepoint seam adoption + retire bespoke primary-anchor helper pair

**Prompt**: [tasks/WP01-chokepoint-seam-retire-helpers.md](tasks/WP01-chokepoint-seam-retire-helpers.md)

**Summary**
- **Goal**: Establish the single kind-aware read chokepoint (`_planning_read_dir` wrapping the existing `resolve_planning_read_dir`) and retire the bespoke primary-anchor helper pair (`mission.py:1288-1325`, `:1327-1357`) onto it. Foundation of Lane A; no new resolver (C-001).
- **Priority**: P0 — foundation; WP02-06 converge onto this chokepoint.
- **Independent test**: `_planning_read_dir(repo, slug, artifact_type="spec")` on a coord-topology composed-`<slug>-<mid8>` fixture → primary `target_branch`; STATUS kind → placed surface; flattened → `target_branch`.

**Tracking**
- [x] T001 Add the `_planning_read_dir` chokepoint helper (WP01)
- [x] T002 Retire `_primary_anchored_feature_dir` onto the seam (WP01)
- [x] T003 Retire `_resolve_mission_dir_name_primary_anchored` planning-read callers (WP01)
- [x] T004 FR-009 audit: no parallel primary-anchor planning-read survives (WP01)
- [x] T005 Red-first chokepoint behavioral test (composed `<slug>-<mid8>`) (WP01)

**Dependencies**: WP00 (write-surface foundation — fixes the editable CLI; lands the finalize-tasks COMMIT `mission.py` edit before WP01 branches).
**Owned files**: `src/specify_cli/cli/commands/agent/mission.py`, `tests/specify_cli/cli/commands/agent/test_gate_read_chokepoint.py`.
**Estimated prompt size**: ~210 lines.

---

## WP02 — setup-plan re-point onto the kind-aware seam

**Prompt**: [tasks/WP02-setup-plan-repoint.md](tasks/WP02-setup-plan-repoint.md)

**Summary**
- **Goal**: Re-point `setup_plan` (`mission.py:2224`) so it reads spec.md via `_planning_read_dir` (`kind=SPEC`) → primary, not the coord-aware `_find_feature_directory`. The driver bug (#2107).
- **Priority**: P0 — the driver.
- **Independent test**: `setup_plan` on a coord-topology composed-`<slug>-<mid8>` fixture reads primary spec.md and advances (does NOT block `SPEC_FILE_MISSING`).

**Tracking**
- [x] T006 Red-first setup-plan repro via the real `setup_plan` entry point (WP02)
- [x] T007 Re-point `setup_plan` spec.md read onto the seam (`kind=SPEC`) (WP02)
- [x] T008 Anti-mutant + flattened-regression assertions for setup-plan (WP02)

**Dependencies**: WP01 (the chokepoint). Serializes behind WP01 on `mission.py` (out-of-map setup_plan edit).
**Owned files**: `tests/specify_cli/cli/commands/agent/test_setup_plan_read_surface.py`.
**Estimated prompt size**: ~180 lines.

---

## WP03 — Accept-gate multi-site split (HIGHEST RISK)

**Prompt**: [tasks/WP03-accept-gate-multisite-split.md](tasks/WP03-accept-gate-multisite-split.md)

**Summary**
- **Goal**: Split the accept gate's single `status_feature_dir` per-partition: move the ~9 planning reads (`acceptance/__init__.py:1179-1186`, `_missing_artifacts:596`) → primary via the seam; KEEP the STATUS/acceptance reads (`:1174`, leniency `:749`) on `status_feature_dir`. The mission's core complexity (FR-002, #2085).
- **Priority**: P0 — highest risk.
- **Independent test**: In ONE coord-topology fixture, the accept gate finds planning artifacts on primary AND consults status on coord; reverting either turns the respective assertion RED.

**Tracking**
- [x] T009 Introduce `planning_read_dir` alongside `status_feature_dir` (WP03)
- [x] T010 Re-point the ~6 planning reads (`:1179-1186`) → primary (WP03)
- [x] T011 Re-point `_missing_artifacts` planning checks (`:596`) → primary (WP03)
- [x] T012 Verify STATUS reads + leniency UNTOUCHED (C-002 guard) (WP03)
- [x] T013 Red-first two-surface accept test (planning→primary AND status→coord) (WP03)

**Dependencies**: WP01 (the chokepoint; may call `resolve_planning_read_dir` directly).
**Owned files**: `src/specify_cli/acceptance/__init__.py`, `tests/specify_cli/acceptance/test_accept_gate_read_surface.py`.
**Estimated prompt size**: ~210 lines.

---

## WP04 — map-requirements re-point + record-analysis double-resolution collapse

**Prompt**: [tasks/WP04-maprequirements-recordanalysis-collapse.md](tasks/WP04-maprequirements-recordanalysis-collapse.md)

**Summary**
- **Goal**: Re-point map-requirements WP `tasks/*.md` read (`tasks.py:3727` → coord) onto the seam (`kind=WORK_PACKAGE_TASK` → primary, the squad-found missed site); collapse record-analysis's coord-then-primary double-resolution (`mission.py:1980`) onto the seam. FR-004/FR-009.
- **Priority**: P0.
- **Independent test**: map-requirements reads WP tasks/*.md from primary on a coord fixture; record-analysis resolves the planning read via the seam (one resolution), write target unchanged.

**Tracking**
- [x] T014 Red-first map-requirements repro via the entry point (WP04)
- [x] T015 Re-point map-requirements WP-tasks read (`kind=WORK_PACKAGE_TASK`) (WP04)
- [x] T016 Collapse record-analysis planning-read double-resolution onto the seam (WP04)
- [x] T017 Red-first record-analysis collapse test (WP04)

**Dependencies**: WP01 (chokepoint). Coordinates with WP05 on the shared `record_analysis` function (WP04 read-leg collapse first; WP05 allowlist after — WP05 depends on WP04).
**Owned files**: `src/specify_cli/cli/commands/agent/tasks.py`, `tests/specify_cli/cli/commands/agent/test_map_requirements_read_surface.py`, `tests/specify_cli/cli/commands/agent/test_record_analysis_double_resolution.py`.
**Estimated prompt size**: ~210 lines.

---

## WP05 — record-analysis self-bookkeeping allowlist + in-mission meta-reader sweep

**Prompt**: [tasks/WP05-bookkeeping-allowlist-meta-sweep.md](tasks/WP05-bookkeeping-allowlist-meta-sweep.md)

**Summary**
- **Goal**: Add a self-bookkeeping allowlist (`meta.json`, `.kittify/encoding-provenance/global.jsonl`) at `artifacts.py:113`, kept SEPARATE from the coord-residue partition (G-5 — stale primary spec.md stays "real dirt"), so the record-analysis dirty-tree preflight stops falsely blocking (FR-003, #2102); route the residual inline meta reads in the touched modules through `load_meta` (FR-005, #2100 in-mission only).
- **Priority**: P1.
- **Independent test**: record-analysis preflight does NOT block on `meta.json`/provenance but STILL blocks on a stale primary spec.md; touched modules use `load_meta`.

**Tracking**
- [ ] T018 Add the self-bookkeeping allowlist (DISTINCT from coord-residue) (WP05)
- [ ] T019 Wire the allowlist into the dirty-tree preflight classification (WP05)
- [ ] T020 In-mission meta-reader sweep (touched modules only) (WP05)
- [ ] T021 Red-first allowlist + sweep tests (stale-spec-is-dirt invariant) (WP05)

**Dependencies**: WP02, WP03, WP04 (defines the touched-module set for the sweep; serializes the shared `record_analysis` function behind WP04).
**Owned files**: `src/mission_runtime/artifacts.py`, `tests/mission_runtime/test_self_bookkeeping_allowlist.py`, `tests/specify_cli/test_meta_reader_sweep.py`.
**Estimated prompt size**: ~230 lines.

---

## WP06 — Literal-ban architectural ratchet

**Prompt**: [tasks/WP06-literal-ban-ratchet.md](tasks/WP06-literal-ban-ratchet.md)

**Summary**
- **Goal**: An architectural test forbidding any gate-command entry function from directly joining `<feature_dir>/{spec,plan,tasks,research,data-model}.md` or topology-routing a planning read — makes FR-004 enforceable, prevents regrowth (FR-010, C-005). Allows the seam, STATUS reads, the self-bookkeeping allowlist, and already-primary KEEPs.
- **Priority**: P1 — the cluster cannot regrow without it.
- **Independent test**: ratchet GREEN on the consolidated tree; re-introducing a direct spec.md join or a topology-routed planning read turns it RED.

**Tracking**
- [ ] T022 Build the literal-ban AST/source scan (WP06)
- [ ] T023 Assert consolidated state GREEN + allow-list the KEEPs (WP06)
- [ ] T024 Anti-mutant proof: re-introduce a violation → RED (WP06)

**Dependencies**: WP00, WP01, WP02, WP03, WP04, WP05 (ratchets the consolidated read+write state — WP00 is the write arm; runs last in Lane A).
**Owned files**: `tests/architectural/test_gate_read_literal_ban.py`.
**Estimated prompt size**: ~180 lines.

---

## WP07 — #2091 next-command empty-mid8 regression guard (Lane B)

**Prompt**: [tasks/WP07-next-mid8-guard.md](tasks/WP07-next-mid8-guard.md)

**Summary**
- **Goal**: A red-first guard driving the empty-mid8 → malformed coord branch (`git worktree add` 128) failure through the `next` entry point (fix exists at `runtime/next/runtime_bridge.py:224-229`); lock the fix, close #2091 (FR-006).
- **Priority**: P1 (Lane B, parallel).
- **Independent test**: `next` on an empty-mid8 coord fixture refuses to build a malformed branch; a normal mission builds `kitty/mission-<slug>-<mid8>-lane-<id>`; reverting the guard → RED.

**Tracking**
- [x] T025 Red-first #2091 empty-mid8 guard via the `next` entry point (WP07)
- [x] T026 Prove RED by reverting the `runtime_bridge.py` guard (WP07)

**Dependencies**: WP00 (write-surface foundation — fixes the editable CLI so this Lane-B WP's implement loop runs; WP00 is shared by every lane, not part of Lane A's spine).
**Owned files**: `tests/runtime/next/test_next_coord_branch_mid8_guard.py`.
**Estimated prompt size**: ~150 lines.

---

## WP08 — #2088 ownership-overlap dependency-exemption regression guard (Lane B)

**Prompt**: [tasks/WP08-ownership-overlap-guard.md](tasks/WP08-ownership-overlap-guard.md)

**Summary**
- **Goal**: A red-first guard driving the dep-ordered shared-`owned_files` exemption through `finalize-tasks --validate-only` (fix exists at `ownership/validation.py:127`); lock the fix, close #2088 (FR-007).
- **Priority**: P1 (Lane B, parallel).
- **Independent test**: a dep-ordered overlapping WP pair PASSES validate-only; an independent overlapping pair STILL ERRORS; reverting the exemption → RED.

**Tracking**
- [x] T027 Red-first #2088 dep-exemption guard via finalize-tasks --validate-only (WP08)
- [x] T028 Prove RED by reverting the `validation.py` exemption (WP08)

**Dependencies**: WP00 (write-surface foundation — fixes the editable CLI so this Lane-B WP's implement loop runs; WP00 is shared by every lane, not part of Lane A's spine).
**Owned files**: `tests/specify_cli/ownership/test_dependency_overlap_exemption.py`.
**Estimated prompt size**: ~150 lines.

---

## WP09 — #2074 test_mid8_direct_routing fixture re-pin (Lane B)

**Prompt**: [tasks/WP09-mid8-fixture-repin.md](tasks/WP09-mid8-fixture-repin.md)

**Summary**
- **Goal**: Re-pin the stale `test_mid8_direct_routing.py::test_mission_type_read_mid8_truncates_then_declines` fixture (writes `full.json`/`explicit.json`/`bare.json`) to a production-shaped `meta.json` (canonical factory) so it exercises the real `_read_mission_mid8`→`load_meta`→`resolve_mid8` routing. The product is correct; the test drifted (FR-008).
- **Priority**: P1 (Lane B, parallel).
- **Independent test**: the re-pinned test passes by genuinely reading `meta.json` and asserting the mid8 values (full→truncate, explicit→accept, bare→decline); no product change.

**Tracking**
- [x] T029 Re-pin #2074 fixture to production-shaped `meta.json` (canonical factory) (WP09)
- [x] T030 Prove the re-pin exercises the real `resolve_mid8` routing (WP09)

**Dependencies**: WP00 (write-surface foundation — fixes the editable CLI so this Lane-B WP's implement loop runs; WP00 is shared by every lane, not part of Lane A's spine).
**Owned files**: `tests/specify_cli/test_mid8_direct_routing.py`.
**Estimated prompt size**: ~140 lines.

---

## WP10 — Behavioral verification + closeout

**Prompt**: [tasks/WP10-behavioral-verification-closeout.md](tasks/WP10-behavioral-verification-closeout.md)

**Summary**
- **Goal**: Two-surface behavioral guard (planning→primary AND status→coord per gate command, NFR-004); flattened regression (NFR-001); full `tests/architectural/` arch-gate sweep (post-merge adjudication); issue-matrix terminal verdicts (#2107/#2085/#2102 fixed; #2091/#2088 guarded; #2074 instance-fixed; #2100 partial; #1716/#1868/#1878 advanced).
- **Priority**: P0 — mission acceptance gate.
- **Independent test**: the two-surface + flattened suites pass; the full arch-gate suite is green or adjudicated; verdicts recorded.

**Tracking**
- [ ] T031 Two-surface behavioral guard across gate commands (NFR-004) (WP10)
- [ ] T032 Flattened-mission regression (NFR-001) (WP10)
- [ ] T033 Full tests/architectural/ arch-gate sweep (post-merge adjudication) (WP10)
- [ ] T034 Issue-matrix terminal verdicts + epic advancement (WP10)

**Dependencies**: WP00, WP01-WP09 (all lanes).
**Owned files**: `tests/missions/test_gate_read_two_surface_behavioral.py`, `tests/missions/test_gate_read_flattened_regression.py`.
**Estimated prompt size**: ~200 lines.

---

## Lane / Dependency Summary

**Foundation (lands FIRST — unblocks the implement loop):**
WP00 (write-surface resolver foundation, `dependencies: []`). Every lane root depends on it:
WP01, WP07, WP08, WP09 ← WP00. The editable CLI is broken (commit/branch misresolves to
protected `main`) until WP00 lands; no other WP can run its implement loop before it.

**Lane A (spine — sequential on shared `mission.py`):**
WP00 → WP01 → WP02, WP03, WP04 (all depend on WP01) → WP05 (depends WP02/03/04) →
WP06 (depends WP00 + WP01-05 — read arm + write arm).

**Lane B (lock-the-fix — parallel with Lane A's spine, after WP00):**
WP07, WP08, WP09 (depend only on WP00; independent of the Lane A re-points).

**Closeout:** WP10 depends on ALL (WP00 + WP01-09).

**Shared-`mission.py` serialization note**: WP01 OWNS `mission.py` (4125 LOC). WP00
(finalize-tasks COMMIT region: `_resolve_feature_target_branch:482` /
`_resolve_planning_branch:981` / `finalize_tasks:2806+`), WP02 (setup_plan region), WP04
(record-analysis region), WP05 (meta-sweep) also edit distinct `mission.py` regions as
well-justified out-of-map edits, serialized via the dependency chain (WP00 → WP01 →
WP02/04 → WP05). All regions are non-adjacent (hundreds of lines apart on different
functions) → git 3-way auto-merge is safe; the no-overlap `owned_files` rule guards parallel
collisions; the dependency edges serialize the shared file so each region-edit lands on a
base that already contains the prior. WP00 lands FIRST, so its finalize-tasks edit is in
WP01's base.

## MVP / Parallelization

- **MVP**: WP00 (unblock the loop) + WP01 (read foundation) + WP02 (the driver bug #2107)
  deliver the headline fix.
- **Parallel after WP00**: WP07, WP08, WP09 (Lane B) run alongside WP01 once WP00 has landed.
- **Critical path**: WP00 → WP01 → {WP02|WP03|WP04} → WP05 → WP06 → WP10.
