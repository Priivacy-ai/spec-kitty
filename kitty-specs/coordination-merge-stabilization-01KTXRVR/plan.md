# Implementation Plan: Coordination and Merge Stabilization

**Branch**: `main` (planning base & merge target; lane branches `kitty/mission-coordination-merge-stabilization-01KTXRVR-lane-*` at implement time) | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/coordination-merge-stabilization-01KTXRVR/spec.md`

## Summary

Fix the three live root-cause classes from the validated 3.2.0 Coordination & Merge cluster — (B) coordination worktree left behind its own branch after merge-pipeline `update-ref` calls (#1826), (C) `finalize-tasks --validate-only` mutating the git checkout (#1861 Part 1), (D) husk directories under `.worktrees/` silently resolving as workspaces (#1833) — plus narrow residuals of two drained classes (A: finalize residue #1814, coord-unaware status reads #1735, baseline test gap #1827; F: merge-driver hardening #1736), and perform tracker hygiene closing seven stale-open fixed issues. Every fix is a small, localized guard or cleanup with a regression ratchet; architecture rework is explicitly out of scope (deferred to an umbrella under epic #1666). Authoritative defect locations with file:line evidence: [validation/cluster-validation-brief.md](validation/cluster-validation-brief.md), [validation/debbie-analysis.md](validation/debbie-analysis.md), [validation/paula-analysis.md](validation/paula-analysis.md).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (frontmatter), GitPython-free subprocess git plumbing (existing `specify_cli.git` helpers)
**Storage**: Git repository state (branches, worktrees, index); JSONL append-only event log (`status.events.jsonl`); JSON metadata (`meta.json`, `lanes.json`)
**Testing**: pytest (unit + integration with real temporary git repos, following existing `tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py` fixture patterns); architectural ratchet tests in `tests/architectural/`; mypy --strict; ruff; ≥90% coverage on changed lines
**Target Platform**: Developer workstations (macOS/Linux) running the `spec-kitty` CLI; CI (GitHub Actions, ci-quality.yml)
**Project Type**: single (existing `src/specify_cli` + `src/mission_runtime` package layout — no new packages)
**Performance Goals**: No regression in merge wall-clock; resync adds at most one `git reset --hard` + one `git status --porcelain` per ref-advance site (3 sites)
**Constraints**: C-001 stability-only (no architecture rework); C-002 three known ref-advance sites only; C-003 cleanup-at-source, no exclusion-list widening; C-004 ordering (hygiene first; except-narrowing and backstop wording land with/after resync); C-005 PR-only landing on origin/main, terminology guard pre-push
**Scale/Scope**: ~8 production files touched, ~10 new/extended test files, 13 GitHub issues dispositioned; 6 work-package shape

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **CLI framework typer / console rich / YAML ruamel.yaml**: PASS — no new dependencies introduced; all changes inside existing modules.
- **pytest with 90%+ coverage for new code**: PASS — plan mandates regression-test-first per class (NFR-004); every fix lands with its test.
- **mypy --strict must pass**: PASS — no suppressions planned (NFR-004); new error types are plain typed exceptions.
- **Integration tests for CLI commands**: PASS — end-to-end coordination-topology merge test (AC-B1), validate-only HEAD-stability test (AC-C1), husk-resolution test (AC-D1).
- **No architecture rework** (mission constraint C-001 reinforcing charter simplicity): PASS — guards and cleanups only; resolver APIs unchanged.

**Post-design re-check (Phase 1 complete)**: PASS — design artifacts introduce no new entities requiring storage, no new public APIs, no new dependencies. The only new public surface is one structured error type per guard (Class B refusal, Class D resolution failure), consistent with existing `error_code` patterns.

## Project Structure

### Documentation (this mission)

```
kitty-specs/coordination-merge-stabilization-01KTXRVR/
├── plan.md              # This file
├── research.md          # Phase 0 output — root-cause verification & fix-shape decisions
├── data-model.md        # Phase 1 output — state/invariant model for worktree & placement surfaces
├── quickstart.md        # Phase 1 output — how to reproduce, fix, verify each class
├── contracts/           # Phase 1 output — behavioral contracts per fix class
│   ├── class-b-ref-advance-resync.md
│   ├── class-c-validate-only-readonly.md
│   ├── class-d-workspace-resolution.md
│   ├── class-a-residual-cleanups.md
│   └── class-f-merge-driver-hardening.md
├── validation/          # Committed Debbie/Paula source analyses (specify phase)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — not created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── lanes/merge.py                      # Class B: update-ref sites :440,:474; Class F: _make_merge_env extraction
├── cli/commands/merge.py               # Class B: bake update-ref :993-998; resync helper call sites
├── coordination/
│   ├── workspace.py                    # Class B: resolve() staleness awareness (read-only reference)
│   ├── transaction.py                  # Class B alt: self-heal hook in BookkeepingTransaction (decision: research.md R1)
│   └── status_transition.py            # Class F: narrow except at :399-400
├── git/commit_helpers.py               # FR-012: backstop message names divergence cause :321-339
├── cli/commands/agent/mission.py       # Class C: validate-only guard :2462; Class A: finalize residue cleanup :99-131
├── cli/commands/agent/workflow.py      # Class D: lock-after-create, worktree-add hard error :2237,:2243,:2265
├── cli/commands/agent/tasks.py         # Class D: toplevel assertion before git calls :1346
├── workspace/context.py                # Class D: ResolvedWorkspace.exists requires .git marker :148-150
├── retrospective/gate.py               # Class A: route :597 through resolve_status_surface
├── cli/commands/agent_retrospect.py    # Class A: route :432 through resolve_status_surface
├── cli/commands/upgrade.py             # FR-013: dry-run message :987
└── doctor.py (or status/doctor.py)     # FR-007: husk detection check (follow existing doctor-check registration pattern)

tests/
├── specify_cli/cli/commands/
│   ├── test_merge_coord_worktree_resync_1826.py      # NEW — AC-B1/B2/B4
│   ├── test_finalize_tasks_validate_only_readonly.py # NEW — AC-C1/C2
│   ├── test_workspace_husk_resolution_1833.py        # NEW — AC-D1/D2
│   └── test_merge_coord_topology_1772.py             # EXTEND — AC-A3 baseline recording (unmock :224-225)
├── status/test_event_log_merge.py                    # EXTEND — AC-F2 mixed-timestamp ratchet
├── specify_cli/test_wp06_sc2_paused_mission_blockers.py  # EXTEND — AC-A1 residue
└── architectural/
    └── test_execution_context_parity.py              # EXTEND — AC-A2 read-surface ratchet; AC-B3 no-raw-update-ref ratchet; AC-F1 env-helper ratchet
```

**Structure Decision**: Single-project layout (existing). All changes are in-place guards/cleanups inside `src/specify_cli`; no new modules except possibly one small `git/ref_advance.py` helper if research R1 selects the shared-helper shape (decision recorded in research.md).

## Complexity Tracking

No charter violations. The only complexity decision is helper-vs-inline for the Class B resync (research.md R1) — both shapes respect C-001/C-002.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Tracker hygiene: close the stale-open fixed issues

- **Purpose**: Stop the tracker double-counting fixed defects; re-scope the four partially-fixed issues to residuals so triage reflects code reality.
- **Relevant requirements**: FR-011
- **Affected surfaces**: GitHub issues #1770, #1789, #1816, #1771, #1571, #1784, #1735 (close); #1814, #1736, #1833, #1861 (re-scope); file one follow-up umbrella issue under epic #1666 capturing the deferred non-goals (C-001 list).
- **Sequencing/depends-on**: none (do first — unblocks triage; per C-004)
- **Risks**: Closing requires citing the correct landed commits (8544012fa, 9c8bff06f, c5a10ce56, PR #1719); validation comments already posted 2026-06-12 carry the citations.

### IC-02 — Class C: validate-only must not mutate the checkout

- **Purpose**: `finalize-tasks --validate-only` is read-only; eliminates the operator-trust defect (#1861 Part 1).
- **Relevant requirements**: FR-002; AC-C1..C3
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission.py:2462` (`_ensure_branch_checked_out` call); new test `test_finalize_tasks_validate_only_readonly.py`
- **Sequencing/depends-on**: none (one-line guard + test; independent)
- **Risks**: Minimal. Must confirm no downstream validate-only step depends on being on the target branch (post-WP07 reads anchor on the primary feature dir — verified in debbie-analysis Class C section).

### IC-03 — Class B: coordination worktree resync after ref advance

- **Purpose**: Unattended coordination-topology merges complete; the safe-commit backstop never fires on self-inflicted divergence (#1826 — the only fully-valid blocker).
- **Relevant requirements**: FR-001, FR-012, NFR-001, NFR-002, NFR-003; AC-B1..B4
- **Affected surfaces**: `src/specify_cli/lanes/merge.py:440,:474`; `src/specify_cli/cli/commands/merge.py:993-998`; possibly `coordination/transaction.py` (self-heal alternative); `git/commit_helpers.py:321-339` (backstop message names the divergence — FR-012, lands with this concern per C-004); new test `test_merge_coord_worktree_resync_1826.py`; ratchet in `tests/architectural/` (no raw update-ref outside the chosen path — AC-B3).
- **Sequencing/depends-on**: IC-01 recommended first (hygiene); otherwise independent. IC-06's except-narrowing lands with/after this (C-004).
- **Risks**: `reset --hard` discards state — the guard MUST verify the coord worktree holds no unique uncommitted state and fail loudly otherwise (NFR-002, spec Assumption 2). Shape decision (per-site inline vs shared helper) is research R1.

### IC-04 — Class D: workspace resolution fall-through is failure

- **Purpose**: A directory that is not a real git worktree is never silently used as one; husk recovery is self-serve (#1833 residuals).
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-007, NFR-003; AC-D1..D3
- **Affected surfaces**: `workspace/context.py:148-150` (`.git`-marker existence); `cli/commands/agent/workflow.py:2237/2243/2265` (lock-after-create, hard error on worktree-add failure); `cli/commands/agent/tasks.py:1346` (toplevel assertion); doctor husk check (FR-007); new test `test_workspace_husk_resolution_1833.py`
- **Sequencing/depends-on**: none; ship the doctor check in the same release (edge-case risk below)
- **Risks**: Pre-existing husks on operator machines start erroring explicitly — intended, but the doctor check must land in the same release so recovery is one command (spec Edge Cases).

### IC-05 — Class A residuals: residue-free finalize + canonical read surfaces + baseline test

- **Purpose**: Coordination missions never deadlock on finalize residue (#1814); the last two coord-unaware status reads route through the canonical surface (#1735); the #1827 baseline-recording fix gets the regression test it lacks.
- **Relevant requirements**: FR-006, FR-009, FR-010; AC-A1..A3
- **Affected surfaces**: `cli/commands/agent/mission.py:99-131` (`_stage_finalize_artifacts_in_coord_worktree` cleanup-at-source — C-003 forbids widening `COORD_OWNED_STATUS_FILES`); `retrospective/gate.py:597`; `cli/commands/agent_retrospect.py:432`; extend `test_wp06_sc2_paused_mission_blockers.py`, `test_merge_coord_topology_1772.py` (unmock baseline helpers :224-225), `test_execution_context_parity.py` (AC10 read-surface ratchet)
- **Sequencing/depends-on**: none strictly; AC10 ratchet must land after the two read-sites are routed (else the ratchet fails on arrival)
- **Risks**: Cleanup-at-source must not delete operator-authored files — scope cleanup strictly to artifacts the stager itself wrote (assert by listing before/after in the test).

### IC-06 — Class F: merge-driver hardening

- **Purpose**: The JSONL merge driver's environment, exception discipline, and mixed-schema sorting are pinned by tests so the class cannot silently regress (#1736 residuals).
- **Relevant requirements**: FR-008(b,c,d); AC-F1..F3
- **Affected surfaces**: `lanes/merge.py` (`_make_merge_env()` extraction + all subprocess call sites); `coordination/status_transition.py:399-400` (narrow `except Exception` → `(ValueError, FileNotFoundError)` with documented GENESIS fallback); extend `tests/status/test_event_log_merge.py` (mixed `at`/`timestamp`/neither ratchet); env-helper ratchet test
- **Sequencing/depends-on**: lands with/after IC-03 (C-004: narrowing may surface previously-swallowed errors on stale-worktree reads)
- **Risks**: Newly-propagating exceptions in coordination status reads — mitigated by ordering and by the documented fallback for the two expected error types.

### IC-07 — Polish: honest messages (small, ride-along)

- **Purpose**: `upgrade --dry-run` no longer claims success; failure messages name the resolution used (#1784 P3 crumbs).
- **Relevant requirements**: FR-012 (message part, shipped inside IC-03), FR-013, NFR-003
- **Affected surfaces**: `cli/commands/upgrade.py:987`
- **Sequencing/depends-on**: FR-013 independent; FR-012 inside IC-03
- **Risks**: none material.

## Phase 2 Approach (executed by /spec-kitty.tasks — not here)

The IC map translates to the 6-WP shape hinted in the brief: WP01=IC-01, WP02=IC-02 (+IC-07 ride-along), WP03=IC-03, WP04=IC-04, WP05=IC-05, WP06=IC-06. WP02..WP05 are mutually independent; WP06 soft-depends on WP03 (C-004). Each WP is regression-test-first.

> **Errata (2026-06-12, post-tasks; analysis finding I1):** /spec-kitty.tasks collapsed this to **5 WPs** — the owned-files no-overlap rule forced IC-06 (Class F) into WP03 (both edit `src/specify_cli/lanes/merge.py`, which also satisfies C-004's ordering internally) and the #1814 residue fix (IC-05 part) into WP02 (shares `src/specify_cli/cli/commands/agent/mission.py` with the validate-only guard). tasks.md §WP Shaping Note is authoritative for execution.
