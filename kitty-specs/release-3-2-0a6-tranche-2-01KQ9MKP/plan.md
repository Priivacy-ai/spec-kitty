# Implementation Plan: 3.2.0a6 Tranche 2 Bug Cleanup

**Branch**: `release/3.2.0a6-tranche-2`
**Date**: 2026-04-28
**Spec**: [/Users/robert/spec-kitty-dev/spec-kitty-20260428-103216-RwX3nK/spec-kitty/kitty-specs/release-3-2-0a6-tranche-2-01KQ9MKP/spec.md](spec.md)
**Mission ID**: `01KQ9MKPYMT1528C6VH6B8BT67` (slug `release-3-2-0a6-tranche-2-01KQ9MKP`)

## Branch Contract

- Current branch at plan start: `release/3.2.0a6-tranche-2`
- Planning/base branch: `release/3.2.0a6-tranche-2`
- Final merge target for completed work: `release/3.2.0a6-tranche-2`
- `branch_matches_target`: **true**

All work merges into `release/3.2.0a6-tranche-2`. No direct landing on `main` (per spec C-002).

## Summary

Seven bug fixes restoring the documented Spec Kitty golden path on fresh projects, eliminating non-strict-JSON output from `--json` commands, preserving full agent identity through WP resolution, ensuring review-cycle counters only advance on real rejections, and writing paired profile-invocation lifecycle records on `next`. Approach: each issue maps to one bounded code area; fixes are additive and ship together as a single tranche-2 PR. No new top-level dependencies. All changes type-check under `mypy --strict` and meet ≥ 90% coverage on touched modules. The two product forks in the spec (#841 auto-track, #839 public-CLI fresh-project synthesize) are committed and shape implementation.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console), ruamel.yaml (frontmatter), pytest (test), mypy (strict). External shared-package PyPI deps consumed via `spec_kitty_events.*` and `spec_kitty_tracker.*` only.
**Storage**: Filesystem only — `.kittify/metadata.yaml`, `.kittify/charter/`, `.kittify/doctrine/`, mission state in `kitty-specs/<mission>/{status.events.jsonl,...}`, local invocation records under the existing invocation store.
**Testing**: pytest unit + integration tests; `tests/e2e/test_charter_epic_golden_path.py` for the consolidated fresh-project E2E; `PWHEADLESS=1 pytest tests/` per CLAUDE.md headless guidance.
**Target Platform**: macOS / Linux developer machines and CI; Spec Kitty CLI (`spec-kitty` entrypoint).
**Project Type**: Single Python project (the spec-kitty-cli repository itself).
**Performance Goals**: Golden-path E2E completes < 120s on CI (NFR-007). Per-command overhead unaffected (no new I/O paths beyond existing filesystem writes).
**Constraints**:
- Strict JSON contract on covered `--json` commands (NFR-001).
- `mypy --strict` zero new errors (NFR-003).
- ≥ 90% line coverage on changed modules (NFR-002).
- No new top-level runtime dependencies (SC-008).
- Local SaaS-touching commands require `SPEC_KITTY_ENABLE_SAAS_SYNC=1` (C-003).
**Scale/Scope**: 7 bug fixes; ~6–10 modules touched; one consolidated tranche-2 PR.

## Charter Check

Charter present at `.kittify/charter/charter.md`. Plan-action context loaded; relevant policy summary:

| Charter requirement | Plan compliance |
|---|---|
| Tools: typer, rich, ruamel.yaml, pytest, mypy strict | ✅ No tool changes; reuse existing stack. |
| pytest with **90%+ test coverage** for new code | ✅ NFR-002 mirrors this. |
| **mypy --strict** must pass | ✅ NFR-003 mirrors this. |
| **Integration tests** for CLI commands | ✅ Per-issue integration tests planned in research.md; consolidated E2E for fresh-project flows. |
| DIRECTIVE_003 (Decision Documentation) | ✅ Two product forks (Assumptions A1, A2) documented in spec; plan and research.md restate them. |
| DIRECTIVE_010 (Specification Fidelity) | ✅ Each FR maps to a concrete change area; deviations would require spec amendment. |

**Gate**: PASS. No charter violations require Complexity Tracking entries.

## Project Structure

### Documentation (this mission)

```
kitty-specs/release-3-2-0a6-tranche-2-01KQ9MKP/
├── plan.md                        # This file
├── research.md                    # Phase 0 decisions per issue
├── data-model.md                  # Touched data shapes (metadata.yaml, resolved agent, lifecycle record)
├── contracts/
│   ├── json-envelope.md           # Strict-JSON contract for covered --json commands
│   └── invocation-lifecycle.md    # Profile-invocation lifecycle record schema
├── quickstart.md                  # Reproduce-the-fix walkthrough on a fresh project
├── spec.md                        # Mission specification
├── checklists/requirements.md     # Spec quality checklist
└── tasks.md                       # Phase 2 output of /spec-kitty.tasks (NOT created here)
```

### Source Code (repository root)

Touched areas (informational; final WP-to-file mapping decided in `/spec-kitty.tasks`):

```
src/specify_cli/
├── cli/commands/
│   ├── init.py                    # #840: stamp schema_version + schema_capabilities
│   ├── agent/                     # #676: review-cycle handling; idempotent reclaim
│   └── advise.py                  # #843: invocation lifecycle plumbing on next
├── migration/runner.py            # #840: stamp helper / version capability table
├── status/wp_metadata.py          # #833: resolved_agent() colon parser
├── sync/                          # #842: route diagnostics to stderr / envelope
├── auth/transport.py              # #842: ensure no stdout writes outside envelope
├── invocation/                    # #843: started/completed pair, action id matching
└── (charter package — generate / synthesize / bundle validate paths)  # #841, #839

tests/
├── unit/                          # per-issue unit tests (counter monotonicity, parser arities, etc.)
├── integration/                   # CLI integration tests (--json strictness matrix, init stamp)
└── e2e/
    └── test_charter_epic_golden_path.py  # consolidated fresh-project E2E (#839/#840/#841/#842/#843)
```

**Structure Decision**: Single Python project — existing `src/specify_cli/` and `tests/` layout. No new top-level packages. Final per-WP file partition is decided in `/spec-kitty.tasks` based on lane analysis. The 7 issues partition into independent lanes (see Risk Map below).

## Phase 0 — Research

See [research.md](research.md). One decision block per issue covers approach, rationale, alternatives rejected, and test strategy. No `[NEEDS CLARIFICATION]` markers — the two product forks resolved in the spec (Assumptions A1, A2) are restated as decisions.

## Phase 1 — Design Artifacts

- [data-model.md](data-model.md) — concrete shapes for `.kittify/metadata.yaml` schema fields, `ResolvedAgent` 4-tuple, `ReviewCycleCounter` invariants, `ProfileInvocationRecord` paired records, charter bundle validity surface.
- [contracts/json-envelope.md](contracts/json-envelope.md) — strict-JSON contract: stdout shape, diagnostics routing rules, four-state SaaS matrix.
- [contracts/invocation-lifecycle.md](contracts/invocation-lifecycle.md) — `started`/`completed` pairing schema, canonical action identifier rules, orphan-record observability.
- [quickstart.md](quickstart.md) — reproduce-the-fix walkthrough showing the fresh-project golden path now passes without manual seeding or `git add`.

## Risk Map (premortem-risk-identification tactic)

| Risk | Probability | Blast radius | Mitigation |
|---|---|---|---|
| `init` schema stamp overwrites operator's hand-edited `metadata.yaml` | Low | High (every existing project) | FR-002 makes stamp additive only; NFR-008 asserts zero diff on existing keys; idempotency test on second `init` run. |
| `charter generate` auto-track creates surprising git side effects | Medium | Medium (governance flow) | FR-014 fail-fast path in non-git environments with actionable error; documented in user-facing docs (FR-017). |
| `--json` envelope nesting changes break existing JSON consumers | Medium | High (external scripts) | Diagnostics go to **stderr by default**; if envelope nesting is needed, place under a new top-level key (`diagnostics`) without altering existing keys. Migration note in CHANGELOG. |
| `resolved_agent()` parser change shifts implicit defaults for partial strings | Medium | Medium (every WP run) | NFR-004 requires regression tests at all four arities; defaults documented in data-model.md. |
| Review-cycle counter desync after partial-fix deploy | Low | Medium (review pipeline) | NFR-005 requires ≥ 3 reclaim/regenerate runs without counter drift; counter advancement is gated solely on a real rejection event. |
| Lifecycle pair orphan flood from agent crashes | Medium | Low (observability) | NFR-006 asserts ≥ 95% pairing across ≥ 5 actions; orphans remain observable rather than silently overwritten. |
| Golden-path E2E becomes flaky from real charter doctrine seed work | Medium | Medium (CI signal) | E2E uses public CLI only (Assumption A2); test harness sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` per A4; runtime budget < 120s (NFR-007). |
| Public CLI `charter synthesize` requires unbounded scope creep into doctrine system | Medium | High (could blow tranche budget) | Bound the change to whatever the existing public CLI needs to succeed on a fresh project; do **not** introduce new doctrine subsystems. If scope expands, escalate before merging. |

## Issue → FR/NFR/SC Traceability

| Issue | Primary FRs | NFRs | Success Criteria |
|---|---|---|---|
| #840 init schema stamp | FR-001, FR-002 | NFR-008 | SC-001 |
| #842 --json strict | FR-003, FR-004 | NFR-001 | SC-002 |
| #833 agent identity | FR-005, FR-006, FR-007 | NFR-004 | SC-003 |
| #676 review-cycle counter | FR-008, FR-009, FR-010 | NFR-005 | SC-004 |
| #843 next lifecycle records | FR-011, FR-012 | NFR-006 | SC-005 |
| #841 charter generate parity | FR-013, FR-014, FR-017 | (covered by integration test) | SC-006, SC-007 |
| #839 charter synthesize fresh | FR-015, FR-016 | NFR-007 | SC-001, SC-007 |

Cross-cutting: NFR-002 (coverage), NFR-003 (mypy strict), C-001 (bug-only), C-006 (no new deps), SC-008 (zero new public CLI subcommands, zero new top-level deps).

## Sequencing Strategy (problem-decomposition tactic)

Two lanes are forced by data flow; the rest are parallelizable.

**Lane A — Foundation + Fresh-Project Chain (sequential)**
1. #840 init schema stamp — unblocks all fresh-project work
2. #841 charter generate auto-track — depends on #840
3. #839 charter synthesize on fresh project — depends on #840 and #841

**Lane B — Independent (parallelizable across each other and Lane A)**
- #842 `--json` strict
- #833 agent identity parser
- #676 review-cycle counter
- #843 next lifecycle records (independent at the data layer; integrates with #840 in the consolidated E2E)

The consolidated E2E that closes the loop on #839/#840/#841/#842/#843 is added last so all dependencies are in place.

Final lane assignment is decided in `/spec-kitty.tasks-finalize`.

## Phase Discipline

This command stops after Phase 1. Task generation and WP creation are owned by `/spec-kitty.tasks` and `/spec-kitty.tasks-finalize`.

## Branch Contract (2nd mandatory restatement)

- Current branch: `release/3.2.0a6-tranche-2`
- Planning/base branch: `release/3.2.0a6-tranche-2`
- Final merge target: `release/3.2.0a6-tranche-2`
- `branch_matches_target`: **true**

Next suggested command: `/spec-kitty.tasks` (user must invoke explicitly).

## Complexity Tracking

No charter violations. No entries required.
