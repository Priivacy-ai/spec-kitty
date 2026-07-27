# Closeout adversarial review — Debugger Debbie (live, end-to-end)

**Mission:** gate-read-surface-completion-01KVW9B0 (draft PR #2113)
**Branch:** feat/gate-read-surface-completion @ HEAD (8cf711428), editable install active
**Lens:** Does the read/write surface split ACTUALLY close, end-to-end, on a REAL
coord-topology mission? Driven via the real CLI + real resolvers, not unit tests.

**Directives applied (debugger-debbie):** 001 (Architectural Integrity — hunt the
structural fork, found one); 003 (persist the falsified-hypothesis catalog below);
030 (verified the producer-conformance gate / partition); 032 (Conceptual Alignment
— the coord/primary divergence matrix is the lens). LIVE evidence over static throughout.

**Verdict: SPLIT CLOSES for the commands the mission scoped (setup-plan, accept's
planning-DOC reads, map-requirements, record-analysis, finalize target-branch) —
BUT a LIVE RESIDUAL MISRESOLUTION remains in the accept gate's WP-task iteration.**

---

## Fixture — a REAL coord-topology mission (production-shaped)

`/tmp/debbie-coord-sandbox`, real git repo with `.kittify/`:
- PRIMARY `target_branch` = `feat/gate-read-demo`; composed dir
  `kitty-specs/gate-read-demo-01KVW9B0/` (real 26-char ULID `01KVW9B0XFXPKTBE77QT3KRSW8`,
  mid8 `01KVW9B0`) carrying meta.json (`topology: coord`, `target_branch`, `coordination_branch`),
  spec.md (FR rows), plan.md, data-model.md, research.md, tasks.md, tasks/WP01-demo.md.
- Materialized COORD worktree `.worktrees/gate-read-demo-01KVW9B0-coord/` on branch
  `kitty/mission-gate-read-demo-01KVW9B0`, carrying ONLY status.events.jsonl + meta.json
  (target_branch STRIPPED — mirrors the real sparse split). Planning + WP tasks NOT on coord.
- Also a FLATTENED mission `flat-demo-01KVW9B0` (topology single_branch, no coord).

## 1. Live end-to-end runs (commands + RESOLVED paths)

| Command | Resolved planning/spec path | target_branch | Result |
|---|---|---|---|
| `agent context resolve --action plan` | feature_dir=coord (general ctx) | **feat/gate-read-demo** | success |
| `agent mission setup-plan` | spec_file=**PRIMARY** `/kitty-specs/.../spec.md`, spec_committed=**true** | **feat/gate-read-demo** | reads spec on PRIMARY (past spec gate → plan-substantive block) |
| `agent mission check-prerequisites` | feature_dir=**PRIMARY** | **feat/gate-read-demo** | correct (`_primary_anchored_feature_dir`) |
| `agent tasks map-requirements --wp WP01 --refs` | WP tasks read=**PRIMARY** (kind-aware) | — | **success** (found WP01 on primary, validated vs primary spec) |
| `agent mission finalize-tasks` | reads spec FRs from **PRIMARY** | — | reached requirement-mapping validation (read primary spec) |

Read-surface split (live resolver, coord mission):
- SPEC / TASKS_INDEX / LANE_STATE / WORK_PACKAGE_TASK → **PRIMARY** `kitty-specs/gate-read-demo-01KVW9B0`
- STATUS_STATE / ACCEPTANCE_MATRIX → **COORD** `.worktrees/...-coord/kitty-specs/...`
- topology-blind candidate → coord (the husk). Kind-aware seam correctly diverges.

**The dogfood bug is fixed end-to-end:** pre-fix, setup-plan read coord (no spec) →
"spec not committed" mis-block. Live now: setup-plan finds spec on PRIMARY, spec_committed=true.

## 2. WP00 dogfood fix is LOAD-BEARING (revert proof)

`get_feature_target_branch` / `resolve_target_branch` / `resolve_merge_target_branch`
anchor the meta read on `primary_feature_dir_for_mission` (NOT the topology-aware candidate).

Revert proof (anchor-substitution against the live coord fixture, coord meta has target_branch STRIPPED):
- FIXED anchor (`primary_feature_dir_for_mission`) → reads PRIMARY meta → `target_branch=feat/gate-read-demo` ✓
- REVERTED anchor (pre-WP00 `candidate_feature_dir_for_mission`) → reads COORD meta →
  `target_branch=<ABSENT>` → **falls back to `resolve_primary_branch`**, which on a
  real protected/main checkout returns **`main`** — the exact implement-loop refusal-to-main bug.

The fix is load-bearing. (Read-only; the repo fix was NOT mutated — proof done via
in-process anchor substitution against the sandbox.)

## 3. RESIDUAL MISRESOLUTION FOUND (highest-value output)

**`_iter_work_packages` (src/specify_cli/acceptance/__init__.py:402) reads the WP
`tasks/` directory via the coord-aware `resolve_feature_dir_for_mission` — it lands
on the materialized `-coord` worktree, whose `tasks/` is ABSENT (WORK_PACKAGE_TASK is
a PRIMARY-partition kind, so WP tasks live on PRIMARY). The REAL accept gate raises
`AcceptanceError: Feature '...' has no tasks directory`.**

Live repro through the real gate entry point:
```
collect_feature_summary(repo, "gate-read-demo-01KVW9B0")   # acceptance/__init__.py:1194
  → _iter_work_packages → resolve_feature_dir_for_mission   # :402 (coord-aware)
  → reads .worktrees/...-coord/kitty-specs/.../tasks  (DOES NOT EXIST)
  → AcceptanceError: has no tasks directory at .../-coord/.../tasks
```
- `_iter_work_packages` reads tasks from: `.../-coord/.../tasks` exists? **False**
- kind-aware (CORRECT) WORK_PACKAGE_TASK read: `/kitty-specs/.../tasks` exists? **True**

Why the mission's tests are green anyway (the masking, directive-001 structural fork):
- `_iter_work_packages` was **NOT modified** by this mission (`git diff main...HEAD` of
  acceptance/__init__.py shows no change to this region).
- The mission's behavioral fixture **plants the WP task on coord too**
  (`tests/missions/test_gate_read_two_surface_behavioral.py:190`: *"WP-task read on coord
  too (out-of-WP03-scope path) so the accept gate can run"*) and the WP03 suite
  (`test_accept_gate_read_surface.py:106`: *"it stays on the coord-resolved surface where
  `_iter_work_packages`"*). Both tests ACKNOWLEDGE this read lands on coord and paper over
  it by duplicating the WP file onto coord — a production-inaccurate fixture (a real coord
  mission carries WP tasks ONLY on primary). This is a false-green: the gate breaks live.

**Scope assessment:** This is the SAME class the mission fixed for `map-requirements`
(WP04 re-pointed map-requirements' `tasks_dir` glob onto `resolve_planning_read_dir(WORK_PACKAGE_TASK)`
— see tasks.py:3787, comment "research.md Decision 3"). The accept gate's WP-task iteration
was left on the old coord-aware resolver — the squad fixed the sibling site but missed this one.

**Fix shape (one line, mirrors the WP04 map-requirements fix):** route
`_iter_work_packages` (acceptance/__init__.py:402) — and likely
`_collect_artifact_dossier`'s tasks/research/checklists scan (:631, same coord-aware
resolver) — through `resolve_planning_read_dir(kind=MissionArtifactKind.WORK_PACKAGE_TASK)`
for the WP-task partition. Add a behavioral test that plants WP tasks ONLY on primary
(remove the coord-side duplication that masks the bug).

**Severity:** MEDIUM-HIGH. The accept gate is the merge-blocking gate; a coord-topology
mission whose WP tasks live (correctly) only on primary cannot be accepted — it errors with
"no tasks directory". Whether it bites in practice depends on whether real coord missions
ever leave a stale WP-task copy on coord; the partition says they should NOT, so this is a
latent break the fixtures hide.

## 4. Flattened path — genuinely behavior-neutral (live)

Flattened mission `flat-demo-01KVW9B0` (topology single_branch, no coord):
- candidate(coord-aware) == primary dir (no coord surface exists).
- ALL kinds — SPEC, WORK_PACKAGE_TASK, STATUS_STATE, ACCEPTANCE_MATRIX — resolve PRIMARY.
- Live: `setup-plan` → feature_dir/spec_file PRIMARY, target_branch correct; `map-requirements`
  → success. The kind split is a no-op when there is no coord. Confirmed at the command layer,
  not just unit-asserted.

EMPTY-coord edge (coord root materialized, mission dir removed — #1716): both setup-plan
and map-requirements fall back to PRIMARY with a loud warning (Option B) and continue. Robust.

## Falsified-hypothesis catalog (directive 003 — prevents re-litigation)

- H: "map-requirements still reads WP tasks off coord (residual)." FALSE — WP04 re-pointed
  the `tasks_dir` glob to `resolve_planning_read_dir(WORK_PACKAGE_TASK)` → primary; live success.
- H: "check-prerequisites resolves coord for planning." FALSE — uses `_primary_anchored_feature_dir`,
  live feature_dir=PRIMARY.
- H: "setup-plan/accept planning-DOC reads (spec/plan/tasks.md) still hit coord." FALSE —
  routed through `_planning_read_dir` → `resolve_planning_read_dir`; live spec on PRIMARY.
- H: "flattened path has a behavioral delta." FALSE — all kinds resolve the single primary surface.
- H (CONFIRMED, not falsified): "accept gate's WP-task *iteration* (`_iter_work_packages`)
  still resolves coord." TRUE — live AcceptanceError; see §3.

## Divergence matrix (coord topology, conceptual-alignment lens — directive 032)

| Surface consumer | Reads | Resolves to (live) | Correct? |
|---|---|---|---|
| setup-plan spec gate | SPEC | PRIMARY | ✓ |
| check-prerequisites | feature_dir | PRIMARY | ✓ |
| accept planning DOCs | spec/plan/tasks.md | PRIMARY | ✓ |
| accept STATUS | status.events / matrix | COORD | ✓ |
| **accept `_iter_work_packages`** | **tasks/WP*.md** | **COORD** | **✗ RESIDUAL — tasks live on PRIMARY** |
| map-requirements WP read | tasks/WP*.md | PRIMARY | ✓ |
| record-analysis spec read | SPEC | PRIMARY | ✓ |
| finalize/target-branch | meta.json | PRIMARY | ✓ |
