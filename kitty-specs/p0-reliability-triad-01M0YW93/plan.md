# Implementation Plan: 3.2.6 P0 reliability triad

**Branch**: `fix/p0-reliability-triad` | **Date**: 2026-08-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/p0-reliability-triad-01M0YW93/spec.md`

## Summary

Fix three confirmed, release-blocking P0 defects in the spec-kitty CLI as one mission of three **independent, file-disjoint** work packages, each with a red-first regression test through its pre-existing public entry point:

- **WP01 (#3282)** — `upgrade` provisions mission-type activations to the *effective* activation authority (pointer projects read from `charter.yaml`, not `config.yaml`), by routing the existing upgrade finalizer through the already-present pointer-aware writer. No new migration; additive/idempotent/authored-empty semantics preserved.
- **WP02 (#3579)** — the `merge` stale-lane halt remediation names the tool's own recovery (`spec-kitty agent status materialize`) instead of a dead-end raw-`git` route; **no** `status.json` merge driver is introduced.
- **WP03 (#3281)** — lane allocation retry re-enters the idempotent self-heal (re-run planning-commit + dependency-tip merges) instead of short-circuiting on `workspace.exists`; fresh-path allocation becomes atomic; the claim gate becomes ancestry-aware.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing only — typer, rich, ruamel.yaml, GitPython/subprocess git. **No new dependency is added, upgraded, or removed** (supply-chain gate: N/A).
**Storage**: filesystem — `.kittify/config.yaml`, pointer `charter.yaml`, `kitty-specs/<mission>/status.events.jsonl` + derived `status.json`, `.worktrees/<slug>-<mid8>-lane-*`; git as VCS.
**Testing**: pytest (+ `typer.testing.CliRunner` for CLI entry points; real temp git repos for lane/merge paths). Red-first: each WP adds a test that fails on pre-fix code and passes after.
**Target Platform**: Linux/macOS developer CLI (`spec-kitty`).
**Project Type**: single (CLI tool + library).
**Performance Goals**: N/A — correctness/reliability fixes, no hot path changed.
**Constraints**: cyclomatic complexity ≤ 15; zero new `# noqa` / `# type: ignore` / per-file ignores; `ruff` + `mypy` clean; **no new migration** (WP01); **no `status.json` merge driver / `.gitattributes` change** (WP02); scope-fenced allocator/gate change coordinated with #3432 and assignee robertDouglass (WP03).
**Scale/Scope**: 3 WPs, ~6–8 source files touched across disjoint owned-file sets, plus their focused tests.

## Constitution Check (Charter)

Charter present (`.kittify/charter/charter.md`, template set `software-dev-default`). No violations; the mission is directly aligned:

- **Single canonical authority** — WP01 makes the activation *write* target resolve to the same authority as the *read* target; it does not add a competing source. ✅
- **ATDD-first / red-first** — every WP ships a RED regression test through the pre-existing entry point before the fix (NFR-001). ✅
- **Canonical sources, no improvisation** — fixes route through existing helpers (`charter.compiler.provision_mission_type_activations`, `status materialize`, the allocator reuse-path self-heal). ✅
- **Tiered rigour** — these are core surfaces (upgrade, merge, lane allocation); full rigour applies. ✅
- **Campsite / small-diff tension** — each WP is scope-fenced; WP03 explicitly does not absorb adjacent runtime-selection symptoms (C-003). ✅
- **Not a bulk edit** — no shared identifier renamed across files; `change_mode` stays normal. ✅

No entries required in Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/p0-reliability-triad-01M0YW93/
├── plan.md              # This file
├── research.md          # Phase 0 — fix-approach decisions + rejected alternatives
├── data-model.md        # Phase 1 — the three domain entities/invariants
├── quickstart.md        # Phase 1 — how to reproduce (RED) and verify (GREEN) each fix
├── contracts/           # Phase 1 — behavioral contracts per WP
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root) — owned-file sets (disjoint)

```
WP01 (#3282) — upgrade / charter activation
  src/specify_cli/cli/commands/upgrade.py        # _provision_missing_mission_type_activations, _mission_type_activation_provisioning_pending
  (read-only reference: src/charter/compiler.py, src/charter/pack_manager.py, src/charter/pack_context.py)
  tests/specify_cli/upgrade/test_upgrade_provisions_mission_type_activations.py

WP02 (#3579) — merge stale-lane recovery
  src/specify_cli/lanes/stale_check.py           # _stale_remediation (planning-lane branch)
  src/specify_cli/lanes/merge.py                 # (only if the "incorporate + rematerialize" variant is chosen)
  tests/lanes/test_stale_check.py
  tests/lanes/test_merge.py                       # LOCKSTEP: asserts the remediation substring via consolidate_lane_into_mission (post-plan squad)

WP03 (#3281) — lane allocation retry + ancestry gate
  src/specify_cli/lanes/worktree_allocator.py    # atomic fresh-path allocation (targeted `git worktree remove` on planning-merge raise — NOT heavy rollback; helpers already abort+clean)
  src/specify_cli/cli/commands/agent/workflow_executor.py  # exists-branch idempotent self-heal re-entry; POST-materialize ancestry check
  src/specify_cli/cli/commands/agent/workflow.py           # claim ordering: status-lane gate (:1263, fail-fast) → materialize/self-heal (:1297) → POST-materialize ancestry → claim
  src/specify_cli/lanes/implement_support.py     # create_lane_workspace
  src/specify_cli/orchestrator_api/commands.py   # EXPLICIT ancestry-parity task (both claim paths cross the ancestry seam — not a mirror-check)
  tests/specify_cli/cli/commands/agent/test_implement_single_resolution.py   # reconcile #1832/#1833 invariant with rationale (C-006)
  tests/lanes/test_worktree_allocator_atomicity.py                            # + fresh-path planning-commit atomicity (FR-006)
  tests/specify_cli/cli/commands/agent/ (focused unit for the ancestry refusal at the post-materialize seam — FR-007)
  tests/integration/test_wp_integrity_p0_repro.py                             # end-to-end retry-then-claim (backup, not primary FR-007 proof)
```

**Structure Decision**: Single project. WP02 and WP03 both live under `src/specify_cli/lanes/` but touch **different files with no cross-import** (verified in investigation) — package adjacency only, not a file-overlap hazard. WP01 is fully disjoint (upgrade/charter). No two WPs share an owned file.

## Complexity Tracking

*No Constitution Check violations — table intentionally empty.*

## Parallel Work Analysis

### Dependency Graph

```
No cross-WP dependencies. All three run concurrently.

  WP01 (#3282)  ─┐
  WP02 (#3579)  ─┼─►  pre-merge aggregate squad  ─►  accept  ─►  merge (local main)
  WP03 (#3281)  ─┘
```

### Work Distribution

- **Sequential work**: none. There is no foundation phase; the three WPs are independent.
- **Parallel streams**: WP01, WP02, WP03 implemented concurrently in separate lanes/worktrees.
- **Agent assignments**: one implementer per WP (python-pedro profile); reviewer-renata reviews each WP. WP03 coordinates with assignee robertDouglass and the #3432 lane-compute work (compute vs allocator split, C-003).

### Coordination Points

- **Owned-file overlap**: none at the source level — enforced by the disjoint owned-file sets above (C-001). The only cross-WP file is the shared test `tests/lanes/test_merge.py` (WP02 lockstep, post-plan squad).
- **Soft review coupling**: WP02 and WP03 both concern `status.json` merge behavior; the reviewer confirms WP02's remediation choice does not change what WP03's dependency-tip merge observes.
- **Integration verification**: FR-007's primary proof is a focused unit test at the post-materialize ancestry seam; `tests/integration/test_wp_integrity_p0_repro.py` is end-to-end backup (today it is a #3371 lanes.json test — do not overload it as the sole proof).

### Post-plan squad — accepted design corrections (see research.md for full dispositions)

- **WP03 ancestry seam (C-005, HIGH)**: the ancestry check runs POST-materialize (after self-heal), keyed on the merged tip, at a seam BOTH the CLI and `orchestrator_api` claim paths cross — never at the pre-materialize status-lane gate (which would deadlock approved same-mission dependencies). FR-005 + FR-007 land together.
- **WP03 invariant reconciliation (C-006)**: exists-branch re-entry uses a dedicated idempotent self-heal; the #1832/#1833 single-resolution test is updated with rationale, not silently inverted.
- **WP03 exists-branch decision tree**: ancestry-correct → no-op resume (Acceptance Scenario 4); stale → self-heal (needs main-repo context, not worktree cwd).
- **WP02 remedy dependency (#3531)**: reviewer confirms `status materialize` holds for the same-schema conflict WP02 targets; cross-schema all-zeros (#3531) is out of scope, flagged.
- **WP01 predicate contract (C-004)**: dry-run predicate keeps a defined non-crashing contract on a dangling `charter:` pointer; stale docstring updated for the intentional init/upgrade divergence.
- **Deferred (tracking candidate)**: #3579 + #3281 share a "lane-reconciliation" root; unified seam deferred to protect release blast-radius — surface to operator, do not auto-file.

## Supply-Chain Security (Planning)

No dependency is added, upgraded, or removed by any WP. The `supply_chain_security_check` step is **N/A** for this mission; recorded here explicitly (silence is not compliance).
