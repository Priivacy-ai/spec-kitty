# Implementation Plan: Coord Commit-Surface Authority

**Branch**: `fix/coord-commit-surface-authority` | **Date**: 2026-09-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/coord-commit-surface-authority-01M1M553/spec.md`

## Summary

Make create-time topology selection, commit-time placement, and the three task commands agree on **one authoritative-surface rule** for coord-topology missions. Research (Phase 0, [research.md](./research.md)) established that the decision is fragmented across three unconnected code paths, that B16-clause-2 (concurrent write cross-contamination) does not reproduce and folds into #2533, and that #2300 has drifted to a three-way split. Technical approach: introduce one small pure helper that maps `{topology, primary_protected, current/start-branch}` → `(surface, non_committable_verdict)`, then re-home the three loci onto it via characterize-then-diff.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, ruamel.yaml (existing; **no new dependencies** — supply-chain section N/A)
**Storage**: git refs + `meta.json` (no schema change)
**Testing**: pytest (+ pytest-xdist); characterization/golden harness for behavior freezes
**Target Platform**: CLI (Linux/macOS)
**Project Type**: single project
**Performance Goals**: N/A (decision logic; no hot path)
**Constraints**: zero new `ruff`/`mypy` issues or suppressions; no regression across the shared spec-commit/commit-router/coordination surface (baseline ~4,862 tests, PR #3851); behavior changes frozen before/after (characterize-then-diff)
**Scale/Scope**: 3 source loci + one new shared helper; ~3 work packages

### Engineering Alignment — design decisions (REVISED post-squad 2026-09-03)

The post-plan brownfield squad (architect/debugger/reviewer/implementer) materially corrected the first cut. Revised decisions:

- **DD-1 (REVISED) — unify by consulting ONE kind-aware authoritative-surface helper; verdict follows from `{artifact_kind, topology, primary_protected}`.** The three task commands must share the *rule*, not an exit code. Under coord + protected primary: a **coordination/lifecycle-kind** artifact routes to the coord surface and the redundant direct-to-protected-primary commit is suppressed (`RouteToCoord`, exit 0) — this is `move-task`'s *correct* existing skip (per `_skip_target_branch_commit`'s documented invariant: the coord status transition is authoritative; it suppresses a commit protection would refuse anyway). A **primary/planning-kind** artifact refuses (exit 1) + remedy — this is `map-requirements`/`spec-commit`. A genuine no-op → typed `NoOp` (exit 0). The #2300 bug is that each command **hardcodes** its verdict instead of consulting the shared rule; `move-task`'s skip and `map-requirements`'s refuse are BOTH correct for their kinds. *(Squad: the original "force all three to refuse-exit-1" would have regressed move-task's working coord flow — NFR-004.)*
  - **mark-status is NOT a consumer.** It has been event-log-only since #2816; `_ms_commit` is dead (compat-shim + unit-test only — adjudicated from source: `_do_mark_status` never calls it). Freeze as no-commit; do **not** re-add a commit path.
- **DD-2 (REVISED) — key on primary-TARGET protection; insert into the `pr_bound` arm.** Mint `COORD` iff `pr_bound and (primary_protected or current_is_primary)`, where `primary_protected` is the protection of the resolved **primary target** (not the checkout). This is an insertion into `_resolve_default_topology_phase` at `mission_create.py:391`, preserving the `None`-guard and the non-pr-bound-on-primary→COORD arms. **Tripwire: freeze `test_mission_create.py:455` first** — it stays green under target-keying and would invert under checkout-keying. `--pr-bound --start-branch <unprotected target>` → `SINGLE_BRANCH`. *(Blast radius: this changes the default topology for the mainstream pr-bound-on-unprotected-primary flow — not a narrow edge. Merge/finalize gate on `coordination_branch` presence + target protection, not on `pr_bound⇒coord`, so `SINGLE_BRANCH` is coherent downstream — architect-verified.)*
- **DD-3 (REVISED) — fail-loud on ALL silent primary-fallback sites in `commit_router`, not just one.** Beyond `_resolve_mid8 → None` (`:700-701`), the twin `except Exception → primary` (`:705-711`) and the sibling pair in `_resolve_commit_worktree_for_kind` (`:939-940`, `:950-954`) must also fail loud (or be consciously excluded with rationale), else INV-3 / the DIR-043 "close the class" claim is overstated.
- **Helper home: `src/specify_cli/coordination/surface_authority.py`** (NOT `tasks_shared.py`). `coordination/` never imports `cli/`; homing it in `cli` would force a `coordination→cli` inversion when `commit_router` consumes it. Two pure functions: `coord_topology_reachable` (WP-A) and `resolve_surface_authority` (WP-B/WP-C). See [contracts/authoritative-surface.md](./contracts/authoritative-surface.md).

### The authoritative-surface rule (canonical decision table)

Full contract (kind-aware): [contracts/authoritative-surface.md](./contracts/authoritative-surface.md). Summary:

| artifact kind | topology | primary protected? | surface | verdict |
|---|---|---|---|---|
| coordination / lifecycle | COORD / LANES_WITH_COORD | yes | coordination | RouteToCoord, exit 0 (suppress redundant primary commit) |
| coordination | COORD | no | primary (coord routing inert) | commit directly |
| primary / planning | any | yes | — | Refuse, exit 1 + remedy |
| primary / planning | any | no | primary (that branch) | commit directly |
| any | any | any | genuine no-op → NoOp(`reason`), exit 0 · wrong-surface → Refuse, exit 1 |

Create-time (DD-2): mint COORD iff `pr_bound and (primary_protected(target) or current_is_primary)`.

## Constitution / Charter Check

*GATE: must pass before Phase 0 (passed) and re-check after Phase 1 (passed).*

- **DIR-034 test-first / ATDD-first**: every behavior change lands red-first (characterization freeze) then green. ✅ planned (WP-B especially).
- **DIR-040 recurring-bug structural intervention / DIR-043 close-defect-class-by-construction**: the unifying helper closes the divergence *class*, not three point-fixes. ✅ core of the plan.
- **DIR-044 canonical sources & unification**: reuse the extracted `tasks_transition_core.py`; no per-command re-derivation (C-001). ✅
- **DIR-024 locality-of-change / DIR-025 boy-scout**: changes localized to the three loci + one helper; no drive-by refactor. ✅
- **DIR-030 quality gate**: ruff+mypy clean, no suppressions (NFR-003). ✅
- **Supply-chain (051)**: no dependency change → N/A; recorded, not silent.
- **PRs-only (045)**: lands via PR; operator merges (C-005). ✅

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)
```
kitty-specs/coord-commit-surface-authority-01M1M553/
├── plan.md              # this file
├── research.md          # Phase 0 (done)
├── data-model.md        # Phase 1 (done)
├── quickstart.md        # Phase 1 (this commit)
├── contracts/
│   └── authoritative-surface.md   # the canonical decision-table contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)
```
src/specify_cli/
├── coordination/
│   ├── surface_authority.py       # WP-0 (NEW): coord_topology_reachable + resolve_surface_authority (pure)
│   └── commit_router.py           # WP-C: fail-loud ALL fallback sites (DD-3) + align refuse to helper
├── cli/commands/agent/
│   ├── mission_create.py          # WP-A: _resolve_default_topology_phase consumes coord_topology_reachable (DD-2)
│   ├── tasks_shared.py            # WP-B: _skip_target_branch_commit/_protected_branch_status_commit_error → helper
│   ├── tasks_move_task.py         # WP-B: lifecycle-kind → RouteToCoord via helper (behavior preserved)
│   ├── tasks_map_requirements.py  # WP-B: planning-kind → Refuse via helper (behavior preserved)
│   └── tasks_mark_status.py       # WP-B: FREEZE event-log-only no-commit (assert only; no change)
└── core/mission_creation.py       # WP-A: topology flows through create_mission_core

tests/
├── coordination/                  # WP-0 helper unit tests + golden harness; WP-C fail-loud-all-sites guard
├── specify_cli/cli/commands/      # WP-A topology (freeze test_mission_create.py:455) + WP-B command characterization (JSON-mode exit codes)
└── regression/                    # WP-A: pr-bound+unprotected mints no coord branch (absorbs B16-c2)
```

**Structure Decision**: single project; one new pure module (`coordination/surface_authority.py`, WP-0) is the canonical rule; the three loci align to it. `tasks_transition_core.py` is **NOT** touched (it is move-task-coupled by contract; the shared rule lives in the shell helpers).

## Parallel Work Analysis (REVISED post-squad — foundation-first)

The squad found that a literal "3 independent lanes each with their own copy of the rule" would either duplicate the reachability predicate (the exact divergence class we are killing) or create a hidden WP-A→WP-B edge. Resolution: land the shared pure helper as a **foundation WP-0 first**, then A/B/C consume it in parallel.

### Dependency Graph
```
WP-0 (coordination/surface_authority.py: coord_topology_reachable + resolve_surface_authority
      + unit tests + characterization goldens for the current arms)
        │  (must land first — the single canonical rule)
        ├── WP-A (create-time topology, DD-2)  — imports coord_topology_reachable
        ├── WP-B (task-command unification, DD-1) — imports resolve_surface_authority
        └── WP-C (commit_router: DD-3 fail-loud all sites + align to resolve_surface_authority)
      A / B / C run in parallel after WP-0 (disjoint files).
```
- WP-0: `coordination/surface_authority.py` (new file) + its tests.
- WP-A: `mission_create.py`, `core/mission_creation.py` (thread topology). Freeze `test_mission_create.py:455` tripwire.
- WP-B: `tasks_shared.py`, `tasks_move_task.py`, `tasks_map_requirements.py` (consume helper via shell helpers); `tasks_mark_status.py` **only** to freeze/assert its event-log-only no-commit contract (no behavior change).
- WP-C: `coordination/commit_router.py` (DD-3 all fallback sites; align refuse to helper).

### Work Distribution
- **Sequential**: WP-0 (the canonical rule) before A/B/C.
- **Parallel streams**: WP-A, WP-B, WP-C after WP-0 — files disjoint, no contention.
- **Agent assignments**: one implementer per WP in its own lane worktree; WP-0 by an implementer comfortable with pure-function + golden-harness design.

### Coordination Points
- WP-A authors the integration regression: a `--pr-bound --start-branch <unprotected>` mission mints **no** coordination branch (asserts the mint *decision*, not the absence of stranding — closes both #2533 and the B16-c2 appearance by construction).
- WP-0's golden harness freezes the current arms (move-task RouteToCoord/exit-0, map-requirements Refuse/exit-1, mark-status no-commit, genuine-no-op/exit-0, spec-commit `unchanged`/exit-0, wrong-surface/exit-1) before any consumer changes.

## Phase 1 outputs
- [data-model.md](./data-model.md) — decision inputs/outputs + INV-1..INV-4 (done).
- [contracts/authoritative-surface.md](./contracts/authoritative-surface.md) — the canonical decision table + verdict contract (this commit).
- [quickstart.md](./quickstart.md) — how to reproduce the three defects and verify the fixes (this commit).

## STOP — planning complete. Next: `/spec-kitty.tasks`.
