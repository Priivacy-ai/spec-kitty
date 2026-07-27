# Implementation Plan: Spec Kitty Stability & Hygiene Hardening (April 2026)

**Mission slug**: `stability-and-hygiene-hardening-2026-04-01KQ4ARB`
**Mission ID**: `01KQ4ARB0P4SFB0KCDMVZ6BXC8`
**Date**: 2026-04-26
**Spec**: [spec.md](spec.md)
**Branch contract**: starts on `main`; planning artifacts commit to `main`; final merge target is `main`.

## Summary

A six-theme cross-repo hardening pass landed as eight dependency-aware work
packages. The plan splits on subsystem ownership (merge/lane → intake → repo
authority → runtime → cross-repo packages → sync/auth → governance hygiene → e2e
gates) and on what depends on what. Each WP carries its own test obligations
(unit + contract + integration + relevant e2e) so that the implement-review loop
can converge per WP without waiting on the final e2e gate. The final WP wires the
cross-repo end-to-end suite as a hard pass/fail gate for mission acceptance.

## Technical Context

**Language/Version**: Python 3.11+ (the version pinned by `.python-version` and
`pyproject.toml`).
**Primary Dependencies**:
- `typer`, `rich`, `ruamel.yaml`, `pytest`, `pytest-xdist`, `mypy --strict`
  (charter-enforced toolchain).
- `spec-kitty-events` (external PyPI; consumed via `spec_kitty_events.*`).
- `spec-kitty-tracker` (external PyPI; consumed via `spec_kitty_tracker.*`).
- `spec-kitty-runtime` is treated as retired-from-production; CLI uses
  `src/specify_cli/next/_internal_runtime/`.
**Storage**:
- Filesystem only for missions: `kitty-specs/<slug>/{spec,plan,tasks}.md`,
  `kitty-specs/<slug>/status.events.jsonl` (append-only event log; sole
  authority for WP lane state in Phase 2).
- `.kittify/charter/`, `.kittify/config.yaml`, `.kittify/merge-state.json`,
  `.kittify/runtime/`, `.kittify/events/`.
- SQLite for the offline sync queue (existing `OfflineQueue` DB file).
**Testing**:
- `pytest tests/contract/` — hard mission-review gate (FR-022, FR-023).
- `pytest tests/architectural/` — boundary tests (already covers shared-package
  boundary; extend to cover new invariants).
- `pytest tests/integration/` — CLI integration coverage.
- Cross-repo end-to-end tests live in `spec-kitty-end-to-end-testing/` and are
  exercised by orchestrated harness scripts.
**Target Platform**: macOS / Linux developer laptops; CI on GitHub Actions
(matrix already in place).
**Project Type**: Cross-repo (multi-repo workspace at
`/Users/robert/spec-kitty-dev/spec-kitty-20260426-091819-hxH6lN/`).
**Performance Goals**:
- `spec-kitty --version` cold start ≤ 1.5 s (NFR-009; matches current `main`).
- `spec-kitty merge --resume` ≤ 30 s for 10-lane mission (NFR-005).
- E2E suite ≤ 20 min wall-clock (NFR-006).
**Constraints**:
- `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is required for any SaaS / hosted-auth /
  tracker / sync work on this machine (C-002).
- Phase 2 status model (event log sole authority) — no frontmatter `lane`
  reads or writes (C-006).
- ULID-based mission identity — no `mission_number` selectors (C-007).
- No reintroduction of `spec-kitty-runtime` as a production shared dep (C-003).
**Scale/Scope**: ~50 GitHub issues across 6 repos, ~8 work packages, ~20
modules touched in `spec-kitty`, plus targeted patches in events / tracker /
saas / e2e repos.

## Charter Check

The charter at
`/Users/robert/spec-kitty-dev/spec-kitty-20260426-091819-hxH6lN/spec-kitty/.kittify/charter/charter.md`
exists. The plan-action context bootstrap surfaced the following directives and
tactics; this section maps them to mission decisions.

### Directives

- **DIRECTIVE_003 (Decision Documentation Requirement)** — Material decisions in
  this mission are recorded in `research.md` and (where appropriate) in new
  ADRs under `architecture/2.x/adr/`. Specifically:
  - WP05 must record an ADR on the contract-test → resolved-version pinning
    mechanism.
  - WP06 must record an ADR on centralized auth-transport boundaries.
  - WP08 must record an ADR on cross-repo e2e as a hard mission-review gate.
- **DIRECTIVE_010 (Specification Fidelity Requirement)** — The mission spec
  (`spec.md`) is the contract. Any deviation discovered during implementation
  (e.g., a requirement that turns out to be infeasible without scope creep) is
  documented in `research.md` and explicitly approved via mission-review notes
  before merge.

### Tactics applied during planning

- **Problem Decomposition** — The 41 FRs are decomposed by subsystem ownership
  into 8 WPs, each with its own test obligations.
- **Premortem Risk Identification** — See `research.md` § "Premortem". Failure
  modes considered include: silent data loss in merge, lane scheduling
  collisions on shared test DB, cache poisoning of intake briefs, runtime
  returning stale events from a worktree, contract drift between events
  package and the resolved version, sync queue overflow without operator
  signal, charter compact view shedding required directives.
- **Eisenhower Prioritisation** — The WP ordering reflects "important +
  urgent" first: merge/lane safety and intake security ship before package /
  governance hygiene.
- **Stakeholder Alignment** — Operators, maintainers, and downstream consumers
  are the explicit stakeholders. The success criteria (SC-001..SC-012) name
  each stakeholder's view of "done".
- **Requirements Validation Workflow** — Each FR maps to at least one SC and
  one acceptance test (see `research.md` § "FR → test mapping").

### Gates (must pass before Phase 0 research, and re-checked after Phase 1)

- **G1 — Branch contract is explicit and matches operator intent**: PASS
  (current=main, planning_base=main, merge_target=main, branch_matches_target).
- **G2 — Spec is complete with no `[NEEDS CLARIFICATION]`**: PASS (see
  `checklists/requirements.md`).
- **G3 — All FR/NFR/C IDs unique with non-empty Status**: PASS.
- **G4 — Phase 2 status model preserved**: PASS by construction; the plan
  changes only event-log emission logic, not the model.
- **G5 — Mission identity model preserved**: PASS; no selector reverts to
  `mission_number`.
- **G6 — Cross-repo package boundary preserved**: PASS; no reintroduction of
  `spec-kitty-runtime`. Bug fixes in `spec-kitty-events` /
  `spec-kitty-tracker` are scoped to internal modules; public imports stay
  stable (C-008).
- **G7 — `SPEC_KITTY_ENABLE_SAAS_SYNC=1` enforced for SaaS work**: PASS at the
  plan level; enforced again at WP06 / WP08 implementation.

Re-check after Phase 1: PASS — design artifacts (data-model, quickstart) make
no decisions that violate any gate.

## Project Structure

### Documentation (this feature)

```
kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/
├── spec.md              # Mission specification (committed)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── events-envelope.md
│   ├── tracker-public-imports.md
│   ├── runtime-decision-output.md
│   └── intake-source-provenance.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (passing)
├── tasks.md             # /spec-kitty.tasks output (next phase)
├── tasks/               # /spec-kitty.tasks output (per-WP files)
└── status.events.jsonl  # Append-only WP status (created by tasks-finalize)
```

### Source code touched (cross-repo overview)

```
spec-kitty/
├── src/specify_cli/
│   ├── merge/                         # WP01 — merge / lane safety
│   ├── lanes/                         # WP01 — dependent-WP scheduling
│   ├── intake/                        # WP02 — intake security
│   ├── workspace/                     # WP03 — repo authority / canonical root
│   ├── status/                        # WP03 / WP04 — status emit & transitions
│   ├── next/                          # WP04 — runtime correctness
│   │   └── _internal_runtime/
│   ├── auth/                          # WP06 — centralized auth transport
│   ├── sync/                          # WP06 — offline queue + replay
│   ├── charter/                       # WP07 — compact context fidelity
│   └── cli/commands/                  # WP07 — fail-loud uninitialized repo
├── tests/
│   ├── contract/                      # WP05 / WP08 — hard mission-review gate
│   ├── architectural/                 # WP05 — boundary invariants
│   └── integration/                   # all WPs
└── architecture/2.x/adr/              # WP05, WP06, WP08 — ADR records

spec-kitty-events/
└── src/spec_kitty_events/             # WP05 — internal fixes only; public imports unchanged

spec-kitty-tracker/
└── src/spec_kitty_tracker/            # WP05 / WP06 — auth transport adoption + sync semantics

spec-kitty-saas/
└── (sync / materialization / token refresh paths) # WP06

spec-kitty-end-to-end-testing/
└── scenarios/                         # WP08 — new and updated scenarios
```

**Structure Decision**: Multi-repo (Option 4 — cross-repo). The plan explicitly
calls out which repo owns which FR; the tasks phase encodes the cross-repo
dependency edges that block WP08 until WPs 01..07 land.

## FR → repo / component mapping

| FR | Theme | Owning repo / component |
|----|-------|-------------------------|
| FR-001..FR-006 | Merge / lane safety | spec-kitty `src/specify_cli/merge/`, `src/specify_cli/lanes/` |
| FR-007..FR-012 | Intake security | spec-kitty `src/specify_cli/intake/` |
| FR-013..FR-014 | Worktree → canonical repo writes | spec-kitty `src/specify_cli/workspace/`, `src/specify_cli/status/emit.py` |
| FR-015 | Planning-artifact WP execution | spec-kitty `src/specify_cli/next/`, `src/specify_cli/lanes/planner.py` |
| FR-016..FR-018 | Status transitions / dashboard | spec-kitty `src/specify_cli/status/`, dashboard counters |
| FR-019..FR-021 | Runtime `next` correctness | spec-kitty `src/specify_cli/next/`, mission YAML schema |
| FR-022..FR-026 | Cross-repo package contracts | spec-kitty `tests/contract/`, `tests/architectural/`; spec-kitty-events; spec-kitty-tracker; CI |
| FR-027..FR-031 | Sync / tracker / SaaS stability | spec-kitty `src/specify_cli/sync/`, `src/specify_cli/auth/`; spec-kitty-saas; spec-kitty-tracker |
| FR-032..FR-036 | Repo context / governance | spec-kitty `src/specify_cli/cli/commands/`, `src/specify_cli/charter/` |
| FR-037 | Issue traceability matrix | mission artifacts (`research.md` + `tasks.md`) |
| FR-038..FR-041 | E2E coverage | spec-kitty-end-to-end-testing |

## Work-package decomposition (informational; finalized in /spec-kitty.tasks)

The `/spec-kitty.tasks` phase will materialize this into actual WP files. The
plan-level shape is:

| WP | Focus | Key FRs | Repos | Depends on |
|----|-------|---------|-------|------------|
| WP01 | Merge & lane dependency safety | FR-001..FR-006 | spec-kitty | — |
| WP02 | Intake security & atomic writes | FR-007..FR-012, NFR-003, NFR-004 | spec-kitty | — |
| WP03 | Repo / worktree root authority + status emit correctness | FR-013, FR-014 | spec-kitty | — |
| WP04 | Runtime `next` correctness, planning-artifact execution, transition fixes | FR-015..FR-021 | spec-kitty | WP03 |
| WP05 | Cross-repo package contracts + release gates | FR-022..FR-026 | spec-kitty, spec-kitty-events, spec-kitty-tracker | — |
| WP06 | Sync / offline queue / centralized auth transport | FR-027..FR-031 | spec-kitty, spec-kitty-saas, spec-kitty-tracker | WP05 |
| WP07 | Governance / context / branch guard hygiene | FR-032..FR-036 | spec-kitty | — |
| WP08 | Issue traceability + cross-repo e2e gates | FR-037..FR-041 | spec-kitty, spec-kitty-end-to-end-testing | WP01..WP07 |

Lane planning expectations (so WP05 / FR-005 has a working example):

- WP01..WP07 fan out across ≥2 lanes where source files do not overlap.
- WP04 runs sequentially after WP03 because WP04's runtime-emit changes depend
  on WP03's canonical-root resolver landing first.
- WP06 runs after WP05 because the centralized auth transport needs the
  cross-repo package boundary to be stable first.
- WP08 runs last; its lane base must include every other WP's branch (the
  finalize-tasks step encodes that as `depends_on`, not as a parallel lane).

## Phase 0 — Outline & Research (this command)

Output: `research.md` documenting:

- Premortem and failure-mode catalog.
- FR → test mapping.
- Decisions on ambiguous corners (e.g. how `mark-status` should accept WP IDs;
  how `charter context --mode compact` selects content).
- The verdict-tracking shape for the FR-037 issue traceability matrix.
- ADR seeds for WP05 (contract pinning), WP06 (auth transport boundary),
  WP08 (e2e as hard gate).

No `[NEEDS CLARIFICATION]` markers remain in the spec; Phase 0 produces no new
ones. The mission was authored autonomously per operator direction; the
operator will perform final review at `/spec-kitty-mission-review`.

## Phase 1 — Design & Contracts (this command)

Outputs:

- `data-model.md` — entities and state machines that the mission touches:
  Mission (ULID identity), WP (9-lane state machine, append-only event log),
  Mission Brief (intake artifact), Charter Context (compact vs bootstrap),
  Sync Queue (offline events + replay), Auth Transport (token refresh state
  machine).
- `contracts/` — four contract surface descriptions:
  - `events-envelope.md` — required envelope fields, version expectations,
    test-suite pinning rule.
  - `tracker-public-imports.md` — frozen public surface of
    `spec_kitty_tracker.*`.
  - `runtime-decision-output.md` — invariants for `spec-kitty next` JSON
    output (non-`unknown` mission state, no implicit success).
  - `intake-source-provenance.md` — escape rules and size cap semantics for
    intake provenance lines.
- `quickstart.md` — operator runbook to verify the mission's claims (recreate
  Scenarios 1, 2, 3, 4, 6, 7, 8 from `spec.md`).

After Phase 1, gates re-evaluated → still PASS.

## Complexity Tracking

No charter check violations; nothing to justify.

## Branch contract restated (final report)

- Current branch at planning start: `main`
- Planning / base branch for this mission: `main`
- Final merge target for completed changes: `main`
- `branch_matches_target`: `true`

## Stop point

This command ends after Phase 1. Next: operator (or autonomous loop) runs
`/spec-kitty.tasks` to materialize WP files and the issue traceability matrix.
