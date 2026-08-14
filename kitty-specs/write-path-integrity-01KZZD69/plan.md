# Implementation Plan: Mission-Artifact Write-Path Integrity

**Branch**: `mission/write-path-integrity` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/write-path-integrity-01KZZD69/spec.md`
**Status**: Tasks-ready (folded post-plan adversarial review: 6 MF + 7 SF + OD-1/OD-2/OD-3).

## Summary

Fix the coord/topology write-path cluster (#3371 P0, #2549, #3128, #3373) by installing fail-closed
refusals at **two mandatory write chokepoints**, plus unifying the git-topology primitive as substrate:

- **Seam A — partition purity.** NOTE (verified): there are **two mirrored partition classifiers /
  commit mechanisms**. (1) The kind-aware `commit_router.commit_for_mission` →
  `_group_files_by_partition` path **already** carries the guard `PrimaryKindReachedCoordStagingError`
  (`commit_router.py:46`). (2) The P0 path — `implement.py::_commit_planning_artifacts_transaction` →
  `_run_planning_artifact_commit` → `BookkeepingTransaction.commit` — is **kind-agnostic and unguarded**.
  This mission (a) makes the P0 path *partition-aware* (the `_partition_files_for_commit` split, which
  already exists on the legacy arm), and (b) adds the guard to the `BookkeepingTransaction` seam so a
  mis-route on that path fails loud.
- **Seam B — checkout-identity.** Refuse a WP-execution write when the invoking checkout ≠ the mission's
  declared execution workspace (`workspace_path`), keyed on write-intent at the **WP mutation
  chokepoint** (operator decision OD-1: structural, at `resolve_workspace_for_wp` / the WP-claim path
  that `implement`/`review` funnel through — NOT `resolve_action_context`, which is a read vehicle).

#3373 (unify the git-topology primitive) lands first as **drift-reduction** substrate. **Out of scope**
(fixed during authoring): #3372 (shipped by #3383) and #2702 (confirmed closed; ticket closed).

## Technical Context

**Language/Version**: Python 3.11+ (spec-kitty CLI internals).
**Primary Dependencies**: `typer`, `rich`, `ruamel.yaml`, git via `subprocess`; internal `mission_runtime`
(resolution/artifacts), `specify_cli.coordination` (commit_router/coherence/transaction),
`specify_cli.lanes` (worktree_allocator), `specify_cli.cli.commands.{implement,agent.tasks_move_task}`.
**Storage**: git (one object store shared across primary/coord/lane), `meta.json`, `lanes.json`,
`status.events.jsonl`.
**Testing**: `pytest` (unit + integration + `tests/architectural/` + real-git fixtures); ATDD-first /
red-first; parallel `-n auto --dist loadfile`, real-port/daemon serial.
**Base**: mission **#3383** is the merge-base (`a76fb64dc` is an ancestor of HEAD) — NOT a pending
collision; its adjacent file `task_utils/support.py` is imported, not co-edited.
**Constraints**: no topology redesign (#1878 non-goal); preserve coord-descent Assert A'
(ADR 2026-07-29-1); read from stored `meta.json`, no live re-derivation (2026-06-22-1);
`meta.json`/`target_branch` from repository-root checkout (2026-06-24-2).

## Charter Check

*GATE: must pass before design; re-check after design.*

- **Single canonical authority**: placement stays a **kind partition**; the P0 fix reuses the existing
  `_partition_files_for_commit` split (residue-kind classification) rather than a new resolver. ⚠️
  **Honest note**: Seam A spans **two** mirrored classifiers — the guard currently lives only on the
  `commit_for_mission` mechanism; IC-03 *adds* a guard at the `BookkeepingTransaction` seam (it is not
  "already routed through `_group_files_by_partition`"). This is a bounded second-seam guard, not a new
  write-only resolver, so C-006 (ADR 2026-06-24-1) holds. ✅ (with the two-classifier caveat stated)
- **ATDD-first / red-first**: every FR gets a failing test first; SC-001's RED is made **non-vacuous**
  (see Test Strategy). ✅
- **Architectural gate discipline**: FR-011 static call-shape gate + NFR-003 "no new arch regressions vs
  merge-base" (baseline-red manifest pinned before red-first work). ✅
- **Terminology adherence**: Mission (not feature). ✅

No charter violations → Complexity Tracking not required.

## Project Structure

### Source Code (repository root — real paths, verified)

```
src/specify_cli/cli/commands/
├── implement.py                       # FR-001 partition-aware auto-commit (:890 arm); FR-011 flat arm :909
├── implement_cores.py                 # FR-005 swallow-site audit (except ActionContextError: return None :635)
└── agent/
    ├── tasks_move_task.py             # FR-003 #2549 — the two commit paths (see IC-03 reproduction)
    ├── tasks.py                       # move_task command entry
    └── mission_record_analysis.py     # FR-005 swallow-site audit (:125; suppress(Exception) :347) [read path]
src/specify_cli/coordination/
├── commit_router.py                   # guarded classifier: _group_files_by_partition, PrimaryKindReachedCoordStagingError :46
├── coherence.py                       # is_coord_residue_churn (:89, split predicate) + is_self_bookkeeping_churn (:82, guard/scan exemption)
└── transaction.py                     # BookkeepingTransaction.commit (:764) / commit_idempotent (:710)
src/specify_cli/lanes/worktree_allocator.py       # FR-004: _merge_recorded_planning_commit conflict-free
src/mission_runtime/resolution.py                 # build_execution_context; workspace_path :662; resolve_workspace_for_wp; read_dir_for (#3373)
src/specify_cli/core/checkout_ownership.py        # #3373 probe (non-authoritative fast-path for Seam B)
src/specify_cli/git/commit_helpers.py             # #3373 probe
src/specify_cli/workspace/context.py              # #3373 probe
src/charter/resolution.py                         # #3373 probe: cached canonical resolver (hot path, ~20 callers — preserve contract)

tests/
├── architectural/    # FR-011 static call-shape gate; NFR-003 baseline-red manifest
├── integration/      # SC-001 P0 repro (real finalize→implement composition); SC-004 two-mission fixture
└── coordination/ lanes/ specify_cli/…    # unit + parity + pinned-test rewrites
```

**Structure Decision**: single-project CLI; surgical edits at named seams. The #3373 primitive's new
home is a small shared module consumed by the four probe sites (name decided in IC-01).

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Unify the git-topology primitive (substrate)

- **Purpose**: One primitive + one symlink-canonicalization contract behind the four re-implementations,
  so Seam B's path comparison and the nested classifier have one authority.
- **Requirements**: FR-008, FR-009, FR-010; SC-005, SC-007, SC-008.
- **Affected surfaces**: `charter/resolution.py` (cached canonical resolver — **hot path, ~20 callers**;
  preserve caching + not-a-repo classification + `.git`-interior detection + its repo-root return shape),
  `core/checkout_ownership.py`, `git/commit_helpers.py`, `workspace/context.py`; the
  `effective_root ? legacy : compose_meta_json_path` fork (~12×) in `resolution.py` → one `read_dir_for`.
- **Depends-on**: none.
- **Risks**: unify the *primitive*, not the four *semantics* (root vs is-worktree vs linkage vs
  ownership) — preserve each call site's error contract. `charter/resolution.py` already `.resolve()`s;
  unify the contract, do not re-add. Behavior-parity tests MUST stay green (SC-005).

### IC-02 — Partition-correct the P0 planning-artifact auto-commit

- **Purpose**: Stop `implement.py`'s verbatim `placement_ref` arm (`:890-902`) from committing a mixed
  PRIMARY+COORD batch to one (coord) ref; route each file to its kind's partition; never commit an empty
  group; recover a crash between commits by idempotent re-drive.
- **Requirements**: FR-001, FR-004; NFR-001; SC-001, SC-002; C-004, C-006, C-008.
- **Affected surfaces**: `implement.py` (`:890` arm; the split `_partition_files_for_commit :714` already
  used by the legacy `else` arm `:947-961`), `transaction.py`, `worktree_allocator.py` (proves add/add
  gone). **Staging-half note (SF-7):** the staging decision (`verbatim_ref = placement_ref.ref if … else
  None`, which files enter `files_to_commit`) is partition-neutral — only the *commit* half changes.
- **Depends-on**: IC-01 **(soft / merge-ordering only** on shared `implement.py`/`coherence.py` imports —
  `is_coord_residue_churn` is pure path-string classification and consumes nothing from IC-01).
- **Mechanism corrections (verified)**:
  - **skip-empty** is **already** a caller guard on the legacy arm (`if primary_files:` `:948` / `if
    coord_files:` `:961`) — copy that pattern; **no `transaction.py` change** needed. (The R-D framing
    "`commit_idempotent` raises on empty" mis-named the mechanism — the P0 path calls `txn.commit()`
    `:772`, not `commit_idempotent`.)
  - **idempotent re-drive** (US1 scenario 5 crash-recovery) is a *separate*, deliberate change:
    switching `commit()`→`commit_idempotent()` affects **all four arms** sharing
    `_run_planning_artifact_commit` and re-baselines their tests — scope it explicitly.
  - **C-008 (corrected)**: the split routes by `is_coord_residue_churn`; `meta.json` resolves PRIMARY
    *through* kind classification (kind `PRIMARY_METADATA`), so the split needs **no** self-bookkeeping
    call. `is_self_bookkeeping_churn` is used by the IC-03 **guard** exemption + the SC-002 scan only.
  - **Pinned tests to rewrite (SF-5)** in `tests/…/test_implement_placement_routing.py`:
    `test_effective_destination_ref_is_placement_ref_verbatim`, `test_resolved_placement_ref_is_used_verbatim`,
    the sibling structured-error/forbidden-ternary guards — the verbatim capture is last-write-wins, so a
    two-commit split needs a **list-capture + mixed-kind fixture** to assert both refs.
  - **#2570 (OD-2, decided): do NOT fold.** Its serialization point is `_validate_worktree_clean`
    reacting to the runtime's `tasks/WP##.md` self-write (`implement_cores.py::_is_self_write_only_diff`)
    — a **disjoint** seam FR-001 never touches. WP02's #2570 deliverable = a one-paragraph impact
    analysis concluding "no perturbation; sanctioned follow-on."

### IC-03 — Seam-A guard on the `BookkeepingTransaction` seam + #2549 routing

- **Purpose**: Add `PrimaryKindReachedCoordStagingError` (or equivalent) to the P0 commit seam so a
  PRIMARY→coord / COORD→lane mis-route fails loud there; fix the residual #2549 lane-status leak.
- **Requirements**: FR-002, FR-003; NFR-001; SC-002, SC-006.
- **#2549 current-code reproduction (MF-2 — WP03 entry gate).** `move-task` has **two** status-commit
  mechanisms and the plan must name which leaks before rerouting:
  1. `tasks_move_task.py::_mt_commit_lane_deliverables` (~`:506-565`) commits via **raw `safe_commit` on
     the lane branch** (docstring `:513`: "the tool … on the lane branch") — **bypasses**
     `commit_for_mission`/Seam A entirely. **This is the suspected residual `--force` leak surface.**
  2. The port-based `commit_status`/`commit_artifact` seam **does** wrap `commit_for_mission`
     (`agent_tasks_ports.py:329`) → already reaches the guard.
  WP03's first task is a failing reproduction (branch/commit + path trace) proving whether `status.*`
  from `move-task --force` lands on the **lane** ref via path (1); if the reproduction is GREEN (path (2)
  already routes correctly on the #3383 base), FR-003 reduces to a regression pin, not a reroute.
- **Affected surfaces**: `commit_router.py` / `_run_planning_artifact_commit` (guard reach),
  `tasks_move_task.py` (the leaking mechanism named by the reproduction), `coherence.py`
  (`is_self_bookkeeping_churn` exemption — a coord status commit co-traveling `meta.json` must NOT trip
  the `PRIMARY_METADATA`→coord guard; apply the exemption first; add a positive test).
- **Depends-on**: IC-01, IC-02.
- **Risks**: the guard classifies staged *paths* by kind at commit time (the kind-agnostic
  `BookkeepingTransaction.commit` cannot); exclude self-bookkeeping first. Respect withdrawn Trigger A.

### IC-04 — Seam-B checkout-identity refusal at the WP mutation chokepoint (OD-1: structural)

- **Purpose**: Refuse a WP-execution write when `current_cwd` ≠ the mission's declared execution
  workspace, without false-refusing reads or planning.
- **Requirements**: FR-005; NFR-004; SC-004; C-001, C-007.
- **Chokepoint (OD-1, decided: structural).** The refusal lives at the **WP mutation chokepoint** —
  `resolve_workspace_for_wp` / the WP-claim path that `implement`/`review` both funnel through
  (`workspace_path` is populated there, `resolution.py:662`). It is **not** placed on
  `resolve_action_context` (a read vehicle reused by ~20 callers) nor on the swallowed placement read in
  `implement_cores.py`.
- **MF-3 write-intent marker table (spec-mandated).** WP04 MUST produce this table before implementation:

  | Site | file:line | carries write-intent? | notes |
  |------|-----------|----------------------|-------|
  | WP workspace resolution for `implement`/`review` | `resolution.py::resolve_workspace_for_wp` (caller in `implement.py`/review) | **YES** — the chokepoint | compares canonical `current_cwd` vs `workspace_path` |
  | placement read in implement | `implement_cores.py::_resolve_placement_ref` (`:635` swallow) | **NO** | read-shaped; must stay unrefused |
  | `resolve_action_context(action="tasks")` read vehicle | `_read_path_resolver.py:1622` + ~20 callers | **NO** | pure reads |
  | planning commit (specify/plan/tasks) | planning paths resolving to `primary_root` | **NO** | compare `primary_root`, not `workspace_path` |
  | `record-analysis` | `mission_record_analysis.py:347` `suppress(Exception)` | **NO** (out of Seam-B scope) | broad suppress must be **physically narrowed** so it cannot swallow a refusal if one ever reaches it |

- **Affected surfaces**: `resolution.py` (chokepoint + write-intent signal), `implement.py`/
  `implement_cores.py` (narrow swallow `:635`), `mission_record_analysis.py` (narrow suppress `:347`).
- **Depends-on**: IC-01 (symlink canonicalization on both compared sides — else `/var`→`/private/var`
  false-refusal).
- **Risks**: distinct refusal exception **NOT** subclassing `ActionContextError` (MF-4/R2); the broad
  `suppress(Exception)` is immune to that defense and MUST be narrowed. `resolve_ownership_claim` is a
  non-authoritative fast-path only (classifies same-repo foreign lanes OWNED, MF-8) — compare the
  mission's own `workspace_path`.

### IC-05 — Architectural gate + regression pins (split static/runtime — MF-4)

- **Purpose**: Make the P0 class hard to reintroduce; pin the crash-recovery + false-refusal invariants.
- **Requirements**: FR-011; NFR-001, NFR-003; SC-006.
- **Static gate (AST)**: every **coord-topology** `_run_planning_artifact_commit` batch traces through
  `_partition_files_for_commit`, with an explicit **route-through/carve-out for the flat/legacy arm**
  (`implement.py:909`, verbatim by design — no coord partition on a flat mission). **OD-3 (decided):
  route the flat arm through `_partition_files_for_commit` too** (harmless — zero coord residue on a flat
  mission) so the gate needs no special-case whitelist.
- **Runtime property** ("no `lanes.json` on any coord ref") is NOT statically detectable → owned by the
  **SC-002 real-git repo scan**, not the AST gate.
- **Depends-on**: IC-02, IC-03.

## Design Decisions (key, corrected)

1. **Two seams, two mechanisms.** Partition purity spans two mirrored classifiers; the P0 path
   (`BookkeepingTransaction`) is unguarded and gets both the split (IC-02) and a new guard (IC-03).
2. **Reverse the C-004 verbatim deferral** — sanctioned; rewrite the pinned tests with list-capture.
3. **Keep `BookkeepingTransaction`.** skip-empty = existing caller guard (no `transaction.py` change);
   idempotent re-drive = a deliberate `commit()`→`commit_idempotent()` 4-arm change.
4. **Self-bookkeeping exemption** (`is_self_bookkeeping_churn`) at the IC-03 guard + SC-002 scan; the
   split routes by residue-kind (`meta.json` already PRIMARY).
5. **Seam-B at the WP mutation chokepoint** (`resolve_workspace_for_wp`), write-intent-gated; distinct
   exception outside `ActionContextError`; narrow the swallow sites.

## Risks & Mitigations (from the adversarial reviews)

| Risk | Mitigation | IC |
|------|------------|----|
| Empty COORD group hard-fails | existing caller guard (`if coord_files:`) — no txn change | IC-02 |
| Crash between commits strands residue (#2702 shape) | `commit_idempotent` re-drive (deliberate 4-arm change); pin | IC-02/IC-05 |
| `meta.json` co-travel false-refused at guard | `is_self_bookkeeping_churn` exemption first; positive test | IC-03 |
| Seam B false-refuses reads/planning | write-intent at the WP chokepoint; compare `primary_root` for planning | IC-04 |
| Refusal swallowed by `except ActionContextError`/`suppress` | distinct exception; narrow `:635`/`:347` | IC-04 |
| `resolve_ownership_claim` OWNED for foreign same-repo lane | compare mission's own `workspace_path` | IC-04 |
| Symlink false-refusal | IC-01 first; one canonicalization contract | IC-01→IC-04 |
| `move-task` reroute is a no-op / false-green (#2549 already routed) | current-code reproduction as WP03 entry gate | IC-03 |
| Static gate condemns the flat arm | route flat arm `:909` through the split (OD-3) | IC-05 |
| SC-001 RED vacuous / false-green | real finalize→implement composition + `lanes.json`-on-both-sides pre-assertions | IC-05 |

## Test Strategy (ATDD, red-first)

- **SC-001 P0 acceptance (non-vacuous — MF-5).** The named `tests/integration/coord_topology_fixture.py`
  is a static read-routing fixture that never drives finalize/implement — **do not** reuse it. Instead
  compose the **real** path: real `_ensure_planning_artifacts_committed_git` → real
  `allocate_lane_worktree`, on a coord-topology + PR-bound `--start-branch` mission. Before asserting,
  pin two **non-vacuity pre-assertions**: (a) `git ls-tree -r <coord_ref>` shows `lanes.json` present on
  coord (proves the mis-route occurred); (b) the tree of `planning_commit_sha` **also** contains
  `lanes.json`. Only then assert the specific `PlanningCommitMergeConflictError` (never a generic
  non-zero). State why `--start-branch`/PR-bound is load-bearing (it makes the coord base and the
  recorded planning tip genuinely diverge). RED against current code, GREEN after IC-02.
- **SC-002 cross-partition scan.** Real-git lifecycle fixture; enumerate via `_PRIMARY_ARTIFACT_KINDS` /
  `is_coord_residue_churn`: zero PRIMARY files on coord, zero COORD files on lane (`meta.json` excluded),
  across `implement` and `move-task --force`.
- **SC-004 foreign-checkout refusal.** Local two-mission fixture (two missions, one registry, distinct
  lanes); assert refuse-from-foreign-lane, proceed-from-own-lane, proceed-for-planning-from-root,
  proceed-for-pure-reads. No `spec-kitty-saas` dependency.
- **SC-005/007/008 primitive parity.** Existing charter-caching / not-a-repo / NESTED-refusal suite
  stays green; add one-copy static gates.
- **Baseline-red manifest (SF-6, NFR-003).** Before red-first work, pin the honest-red set for
  `tests/architectural/`, `tests/integration/test_coord_*`, `tests/{,specify_cli/}lanes/*` in the
  mission dir. Verified GREEN on merge-base (so a regression is ours): `test_write_surface_placement_guard`,
  `test_read_surface_placement_guard`, `test_no_write_side_rederivation`.
- **Guardrail**: run `pytest tests/architectural/test_no_legacy_terminology.py` before push; full arch
  suite via CI. Honor the baseline-red gotcha (attribute failures to merge-base first).

## Post-implementation corrections (folded from the implement-review loop)

Two facts the implementation surfaced that the plan got wrong or under-specified — recorded here so the plan matches shipped reality:

1. **IC-02 keystone (WP02): the P0 fix required a transaction-layer change, not just the commit-site partition.** `BookkeepingTransaction.acquire` (`coordination/transaction.py`) *unconditionally* redirected every write to the coord worktree under coord topology — so partitioning `files_to_commit` and passing a PRIMARY group with `destination_ref=<target_branch>` was insufficient; the file still landed on coord. The fix adds an opt-in `commit_to_primary_target: bool = False` to `acquire`; only the PRIMARY planning-commit callers pass `True`, committing from the primary checkout to the caller's ref. All status/coord callers keep the default → zero regression to coord routing. Behavior change flagged: a coord mission targeting a *protected* branch now fails loud on implement (correct trade-off vs. silent mis-route).

2. **IC-04 chokepoint (WP03): the real chokepoint is `specify_cli/workspace/context.py::resolve_workspace_for_wp`, NOT `mission_runtime/resolution.py`.** There are two functions of that name; the plan named the wrong one (the `mission_runtime` one is reached only via the read-vehicle `resolve_action_context`, and a guard there is inert; `review`'s write path never touches it). Both `implement` and `review` funnel through `workspace/context.py::resolve_workspace_for_wp`; it gained a `write_intent` param set `True` only at the three true write sites (`implement.py:1859`, `workflow.py:1263`, `workflow_executor.py:1543`). The refusal is `CheckoutIdentityError` (subclasses `Exception` directly, not `ActionContextError`) with a pure-path comparator (no git subprocess — NFR-004).

3. **IC-05 gate (WP04): OD-3's premise was wrong** — WP02 did NOT route the flat/legacy arm through `_partition_files_for_commit` (the flat arm legitimately commits verbatim to the *primary target* ref, which is safe on a flat mission with no coord). The static gate therefore classifies by *destination ref* (raw batch legal only to the primary target, never a coord ref) rather than asserting a uniform split — no line-number whitelist, refactor-safe.
