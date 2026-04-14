# Implementation Plan: Legacy Sparse-Checkout Cleanup and Review-Lock Hardening

**Branch**: `main` (planning on main, merging to main — see branch contract below)
**Date**: 2026-04-14
**Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/legacy-sparse-and-review-lock-hardening-01KP54ZW/spec.md`

## Branch Contract

- **Current branch at plan start**: `main`
- **Planning / base branch**: `main`
- **Final merge target**: `main`
- **`branch_matches_target`**: true

All planning artifacts commit to `main`. Lane worktrees for implementation will be materialized later by `spec-kitty agent action implement` per the 3.x execution-workspace strategy.

## Summary

Consolidate two post-v3.0.0 regressions — silent data loss during mission merge on legacy-sparse repositories (Priivacy-ai/spec-kitty#588) and a review-lock self-collision in the uncommitted-changes guard (Priivacy-ai/spec-kitty#589) — into a single mission that ships three cooperating defences plus a review-lock fix:

1. A canonical sparse-checkout detection primitive.
2. A doctor-offered remediation that repairs the primary and all lane worktrees.
3. A commit-layer backstop inside `safe_commit` that prevents silent data loss regardless of how the working tree got out of sync with `HEAD`.
4. A hard-block preflight on `mission merge` and `agent action implement`.
5. A non-blocking, once-per-process warning at other state-mutating CLI surfaces.
6. A review-lock fix with a filtered dirty-tree guard, per-worktree ignore on creation, correct retry-guidance text, and a lock release that cleans up an empty `.spec-kitty/`.

A durable cross-repo audit event for `--allow-sparse-checkout` use is deferred to Priivacy-ai/spec-kitty#617.

## Technical Context

- **Language / Version**: Python 3.11+ (matches existing spec-kitty codebase; `pyproject.toml`).
- **Primary Dependencies**: `typer`, `rich`, `ruamel.yaml`, `pytest`, `mypy --strict`. No new runtime dependencies.
- **Storage**: Filesystem. Git repository metadata, `.kittify/` config, `kitty-specs/<mission>/` artifacts. No database changes.
- **Testing**: `pytest` with 90%+ coverage for new code (charter requirement); integration tests for CLI commands; both sparse-affected and clean-3.x fixtures.
- **Target Platform**: macOS and Linux (matches existing spec-kitty support surface). Windows is not in charter scope.
- **Project Type**: Single project (existing CLI codebase).
- **Performance Goals**: Detection adds ≤20 ms wall-clock per CLI command (NFR-001). Commit-layer backstop adds ≤200 ms on a typical merge (NFR-002).
- **Constraints**: Four-layer defence; detection primitive is pure; remediation is doctor-offered only (C-002); commit-layer backstop is not bypassable by `--force` (FR-012, C-007).
- **Scale / Scope**: Affects ~10 code files directly, new 2 modules and 1 ADR, ~15 integration tests.

## Charter Check

Charter source: `/Users/robert/spec-kitty-dev/kentonium/spec-kitty/.kittify/charter/charter.md`
Action doctrine (plan): DIRECTIVE_003 (decision documentation), DIRECTIVE_010 (specification fidelity), tactics `requirements-validation-workflow` and `adr-drafting-workflow`.

| Check | Verdict | Notes |
|---|---|---|
| Policy: typer / rich / ruamel.yaml / pytest / mypy --strict stack | **Pass** | No new dependencies introduced. |
| Policy: 90%+ coverage on new code | **Pass (committed)** | Integration and unit tests accompany every new module. |
| Policy: integration tests for CLI commands | **Pass (committed)** | Five integration test files planned (see quickstart.md test map). |
| DIRECTIVE_003 (decision documentation) | **Pass** | Decision Log in spec.md + ADR `architecture/1.x/adr/2026-04-14-1-sparse-checkout-defense-in-depth.md` planned in the implementation. |
| DIRECTIVE_010 (specification fidelity) | **Pass** | Plan and design artifacts trace back 1:1 to FRs / NFRs / Cs in spec.md. |
| `requirements-validation-workflow` | **Pass** | Requirements checklist at `checklists/requirements.md` — all items pass. |
| `adr-drafting-workflow` | **Pass (planned)** | Implementation WPs include ADR draft; see Phase 2 preview below. |

No violations. Complexity Tracking table is empty for this mission.

## Project Structure

### Documentation (this feature)

```
kitty-specs/legacy-sparse-and-review-lock-hardening-01KP54ZW/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Requirements-quality checklist
├── spec.md              # Feature specification
├── meta.json            # Canonical mission identity
└── tasks/               # Created by /spec-kitty.tasks (not this command)
```

### Source Code (repository root) — paths touched by this mission

```
src/specify_cli/
├── git/
│   ├── commit_helpers.py                      # MODIFY — add FR-011 backstop inline in safe_commit
│   ├── sparse_checkout.py                     # NEW    — detection primitive + session warning (FR-001, FR-010)
│   └── sparse_checkout_remediation.py         # NEW    — primary + worktrees remediation (FR-003, FR-004, FR-005)
├── status/
│   └── doctor.py                              # MODIFY — new finding + remediation action (FR-002, FR-023)
├── cli/commands/
│   ├── merge.py                               # MODIFY — merge preflight (FR-006), post-merge refresh (FR-013), invariant (FR-014)
│   ├── agent/
│   │   ├── workflow.py or implement entrypoint # MODIFY — implement preflight (FR-007, FR-008, FR-009)
│   │   └── tasks.py                           # MODIFY — guard filter (FR-015), retry text (FR-017),
│   │                                          #          lock release on approve/reject (FR-018, FR-019),
│   │                                          #          approve-output anomaly investigation + fix (FR-020)
├── core/
│   └── worktree.py                            # MODIFY — write per-worktree exclude (FR-016)
├── review/
│   └── lock.py                                # MODIFY — enhance release() to remove empty .spec-kitty/ (FR-018)
└── (entry-point modules)                      # MODIFY — invoke warn_if_sparse_once (FR-010) at common CLI surfaces

architecture/1.x/adr/
└── 2026-04-14-1-sparse-checkout-defense-in-depth.md  # NEW — records the four-layer architecture (DIRECTIVE_003, adr-drafting-workflow)

CHANGELOG.md                                    # MODIFY — FR-021 entry + recovery recipe

tests/
├── integration/
│   ├── sparse_checkout/
│   │   ├── test_detection.py                  # NEW — FR-001 scan primitive
│   │   ├── test_remediation_primary.py        # NEW — FR-003
│   │   ├── test_remediation_primary_and_worktrees.py  # NEW — FR-004, SC-001
│   │   ├── test_remediation_refuses_on_dirty.py       # NEW — FR-005
│   │   ├── test_doctor_finding.py             # NEW — FR-002
│   │   ├── test_doctor_non_interactive.py     # NEW — FR-023
│   │   ├── test_merge_preflight_blocks.py     # NEW — FR-006, SC-002
│   │   ├── test_merge_with_allow_override.py  # NEW — FR-008, FR-009, logging of override use
│   │   ├── test_implement_preflight_blocks.py # NEW — FR-007
│   │   └── test_session_warning_once.py       # NEW — FR-010, NFR-005
│   ├── git/
│   │   └── test_safe_commit_backstop.py       # NEW — FR-011, FR-012, SC-005
│   └── review/
│       ├── test_approve_without_force.py      # NEW — FR-015, FR-017, FR-018, SC-003
│       ├── test_reject_without_force.py       # NEW — FR-019, SC-004
│       └── test_approve_output_from_lane.py   # NEW — FR-020
└── unit/
    └── git/
        ├── test_sparse_checkout_detection.py  # NEW — FR-001 state invariants, R6 rule
        ├── test_sparse_checkout_remediation.py # NEW — per-step outcome reporting
        └── test_commit_helpers_backstop.py    # NEW — UnexpectedStagedPath diff logic
```

**Structure Decision**: This is an internal CLI hardening mission, not a new product. No new top-level packages. Two new modules under `src/specify_cli/git/` plus targeted edits to existing files. One ADR and one CHANGELOG update.

## Phase 0 — Research (completed)

See [research.md](research.md). Nine investigations (R1–R9) resolved every planning ambiguity. Summary of outcomes:

- R1: doctor-offered remediation (not automatic upgrade).
- R2: three-layer defence (preflight, merge-path refresh, commit-layer backstop).
- R3: structured log record for `--allow-sparse-checkout`; durable audit deferred to Priivacy-ai/spec-kitty#617.
- R4: new module `src/specify_cli/git/sparse_checkout.py` + companion remediation module.
- R5: module-level flag for once-per-process warning.
- R6: `core.sparseCheckout=true` ⇒ active, irrespective of pattern contents.
- R7: `isatty` AND no common CI env var for non-interactive detection.
- R8: five-step per-worktree remediation, aggregated report.
- R9: ADR draft in `architecture/1.x/adr/2026-04-14-1-sparse-checkout-defense-in-depth.md`.

Post-research Charter Check re-evaluated: still passing (no new violations surfaced).

## Phase 1 — Design (completed)

Design artifacts:
- [data-model.md](data-model.md) — new types (`SparseCheckoutState`, `SparseCheckoutScanReport`, `SparseCheckoutRemediationResult`, `UnexpectedStagedPath`, `SafeCommitBackstopError`), modified on-disk state, function-level contracts for detection, remediation, preflight, backstop, session warning, and review-lock release.
- [quickstart.md](quickstart.md) — five user-facing flows with acceptance-test equivalents.

No HTTP / GraphQL contracts (internal CLI hardening; see data-model.md).

Agent context file update: spec-kitty has no `update-agent-context.sh` or equivalent script; agent context is driven by `CLAUDE.md` and mission metadata, which already reflect the new feature once this plan commits. No manual update required.

## Phase 2 — Task Decomposition (preview only; to be authored by `/spec-kitty.tasks`)

The preferred decomposition splits along the four architectural layers and the two independent bug tracks so the mission parallelizes cleanly:

**Lane A — Data-loss defences (highest priority; ships earliest per spec sequencing)**
- WP: `safe_commit` staging-area backstop (FR-011, FR-012, C-005) + unit tests
- WP: Post-merge working-tree refresh + invariant assertion (FR-013, FR-014) + integration tests
- WP: Regression test for the exact #588 cascade (SC-005)

**Lane B — Detection and doctor surface (shared dependency for Lane C preflights)**
- WP: Detection primitive (`src/specify_cli/git/sparse_checkout.py`; FR-001) + unit tests
- WP: Remediation logic (FR-003, FR-004, FR-005) + unit tests
- WP: Doctor finding + `--fix sparse-checkout` action (FR-002) + interactive/non-interactive handling (FR-023) + integration tests

**Lane C — Preflights and warning hook (depends on Lane B detection primitive)**
- WP: Merge preflight (FR-006) + `--allow-sparse-checkout` wiring (FR-008, FR-009) + structured log record + integration tests
- WP: Implement preflight (FR-007) + integration tests
- WP: Session-scoped warning at other state-mutating CLI commands (FR-010, NFR-005) + integration tests

**Lane D — Review-lock track (fully independent of A/B/C; can run in parallel)**
- WP: Dirty-tree guard filter (FR-015) + retry-text parameterization (FR-017) + unit/integration tests
- WP: Per-worktree exclude writer at worktree creation (FR-016) + integration test
- WP: Lock release on approve/reject (FR-018) + empty-dir cleanup + reject-path fix (FR-019) + integration tests
- WP: Investigate the approve-output source-lane anomaly; implement whichever of "fix the report" or "document why the current behaviour is correct" the investigation concludes (FR-020)

**Lane E — Documentation + coordination (late cycle; depends on Lanes A–D for authoritative content)**
- WP: ADR in `architecture/1.x/adr/` per DIRECTIVE_003 and `adr-drafting-workflow` (R9)
- WP: CHANGELOG entry with recovery recipe (FR-021)
- WP: Post diagnostic comment on Priivacy-ai/spec-kitty#588 asking Kent to confirm origin of sparse-checkout state (FR-022) — scheduled early as a courtesy; non-blocking

Lane A, Lane B, and Lane D can begin simultaneously. Lane C cannot start until Lane B's detection primitive lands. Lane E starts once A–D have material outputs.

Final WP ordering, dependency graph, and acceptance criteria will be authored by `/spec-kitty.tasks` and validated by `spec-kitty agent mission finalize-tasks`.

## Complexity Tracking

*No charter violations to justify. Table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|

## Progress Tracking

- [x] Branch contract captured
- [x] Charter context loaded (bootstrap mode; DIRECTIVE_003, DIRECTIVE_010 active; `requirements-validation-workflow`, `adr-drafting-workflow` in scope)
- [x] Planning interrogation complete (Q1 resolved: hybrid architecture with structured-log override record; cross-repo audit deferred to Priivacy-ai/spec-kitty#617)
- [x] Technical Context filled
- [x] Charter Check evaluated (all pass)
- [x] Phase 0 research completed (research.md)
- [x] Phase 1 design completed (data-model.md, quickstart.md)
- [x] Agent context update (N/A — no script in this repo; metadata driven)
- [x] Post-design Charter Check re-evaluated (still pass)

## Branch Contract (restated per command requirement)

- Current branch: `main`
- Planning / base: `main`
- Merge target: `main`
- `branch_matches_target`: true

## Next Command

`/spec-kitty.tasks` to decompose into work packages.
