# Implementation Plan: Charter Preflight Remediation Authority

**Branch**: `fix/charter-preflight-remediation` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/charter-preflight-remediation-01KYG9WK/spec.md`
**Research**: [research.md](./research.md) — discharges the two questions the spec deferred to plan

## Summary

An operator on a legacy-bundle project is blocked by the implement preflight gate and told to run
`spec-kitty charter sync`. That command is a documented pure staleness reporter, so it clears
nothing; re-running the gate reproduces the identical message. There is no exit (BC-2, the P0).
Meanwhile every operator-facing charter diagnostic reports healthy, because they resolve
`charter.md` while the gate resolves `charter.yaml` (BC-3), so every investigative step confirms the
wrong conclusion.

The response is structural, not a corrected string (C-001). A remediation-effectiveness enforcement
mechanism over the preflight check registry lands first and lands **red** — that red is
simultaneously the FR-003 gate and the NFR-002 red-first evidence for FR-002. The bad remediation is
then corrected, turning it green. Research surfaced a second instance of the same defect class on
the runner's *default* path, which is folded in rather than deferred. Finally the diagnostics are
converged onto the authoritative source via an existing non-mutating seam.

**Direction correction carried from research** (R-001): the gate reads the authoritative artifact;
the diagnostics read the retired one. Consolidation moves the diagnostics onto `charter.yaml`, never
the reverse. The spec's User Story 2 narrative implies the opposite reading and is corrected here.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, pydantic, ruamel.yaml, pytest, ruff, mypy
**Storage**: Filesystem — `.kittify/charter/` bundle artifacts (`charter.yaml`, `charter.md`); no database
**Testing**: pytest; architectural enforcement tests under `tests/architectural/`; red-first per ADR `2026-07-17-1`
**Target Platform**: Linux, macOS, Windows 10+ (cross-platform CLI)
**Project Type**: single
**Performance Goals**: Preflight gate stays interactive — no measurable added latency; the canonical presence seam is a pure existence check (no content read, no hashing)
**Constraints**: Zero new blocking project states (NFR-003); diagnostics degrade to a reported state, never raise (NFR-004); the surviving canonical resolver must answer without mutating the project
**Scale/Scope**: 3 preflight check producers, 7 remediation-emitting states, 10 operator-reachable charter-presence resolvers (3 of which mutate while answering), 3 migration-local resolvers pinned but out of scope

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Standing Order | Assessment |
|---|---|
| **DIRECTIVE_043** — close defect classes by construction | Satisfied by IC-01. Correcting only the one bad string is explicitly non-compliant (C-001), and R-006 proves the class has a second live instance that a string fix would leave open. |
| **DIRECTIVE_044** — canonical sources, never improvise | Satisfied by IC-04 routing through the existing `charter.bundle` seam (R-004) instead of authoring a new resolver or patching parity into each surface. |
| **ATDD-first / red-first** | Satisfied by NFR-002: IC-01 lands red before IC-02 corrects the remediation. The red is live evidence, not a narrative claim. |
| **Non-vacuous self-testing gates** | Satisfied by NFR-001: a concrete floor (7 remediation-emitting states) plus a pinned exemption-set size, so the enforcement cannot pass by finding nothing nor by reclassification. |
| **Tiered rigour** | This is a P0 operator-blocking defect on a governance surface — highest tier. Every IC carries explicit acceptance evidence. |
| **Campsite cleaning** | R-006's runner backfill is folded into this mission rather than deferred to a self-created follow-up issue. |

**Post-design re-check**: no new gaps. The one direction-of-fix risk (R-001) was identified and
settled before any design was committed.

## Project Structure

### Documentation (this mission)

```
kitty-specs/charter-preflight-remediation-01KYG9WK/
├── spec.md
├── plan.md                  # this file
├── research.md              # R-001..R-006
├── data-model.md
├── contracts/
│   └── remediation-effectiveness.md
├── checklists/requirements.md
└── tasks.md                 # created by /spec-kitty.tasks — NOT by this command
```

### Source Code (repository root)

```
src/specify_cli/charter_runtime/
├── freshness/computer.py       # the 3 check producers; BC-2 defect site (:309,:318,:348,:357)
└── preflight/
    ├── runner.py               # composes blocked_reason; backfill defect (:245)
    └── result.py               # PreflightCheck shape (remediation: str | None)

src/charter/
├── bundle.py                   # canonical non-mutating presence seam (first_missing_bundle_file)
├── context.py                  # mutating diagnostic read (:198-200)
└── sync.py                     # pure staleness reporter — the ineffective remediation target

src/specify_cli/cli/commands/charter/   # operator-facing diagnostic surfaces

tests/architectural/            # home for the FR-003 enforcement
tests/charter/                  # existing seam coverage (first_missing_bundle_file)
tests/specify_cli/charter_preflight/
├── _fixtures.py                # EXTEND, do not re-author: init_git_repo, seed_charter_yaml(valid=),
│                               #   seed_bundle_files, seed_manifest, seed_graph, make_fresh_repo
│                               #   — already the isolated-fixture-project machinery C-EFF-5 requires
└── test_runner.py              # 346 lines; already exercises missing/invalid/blocked + remediation
tests/specify_cli/charter_freshness/
└── test_computer.py            # 667 lines; already covers all three check producers' states
```

## Complexity Tracking

| Concern | Risk | Mitigation |
|---|---|---|
| Consolidating presence resolution touches 10 operator-reachable sites | Regression across diagnostics | IC-04 lands late, after the effectiveness gate is green, and is bounded by the NFR-003 fixture matrix. |
| The resolver set has been undercounted three times running | A fourth miss ships a surface still disagreeing with the gate | R-007: the census is derived from a stated criterion and scans for the pattern, rather than asserting a hand-written list. |
| `charter context` mutates while reading | Consolidation could spread the side effect | The canonical seam is a pure existence check by construction (R-004); the mutating path is not eligible to be the seam. |
| The enforcement must execute remediations to prove effectiveness | Slow or side-effecting test suite | Effectiveness is proven against isolated fixture projects, never the developer's repo. Contract in `contracts/remediation-effectiveness.md`. |
| `charter synthesize` effectiveness unadjudicated | Could surface more red than expected | Deliberate — the mechanism adjudicates empirically. If it reveals further ineffective remediations, they are folded, not deferred. |

## Implementation Concern Map

Ordering is a strictly linear spine. IC-01 is the foundation: it is the FR-003 deliverable **and**
the red-first evidence for FR-002, so it must land before IC-02 corrects anything.

### IC-01 — Remediation-effectiveness enforcement (lands RED)

**Requirements**: FR-001, FR-003, NFR-001, NFR-002, C-001, SC-001, SC-005

Build the structural mechanism that holds every preflight check to the rule *executing a check's
remediation changes that check's state*. It enumerates the check registry, drives each
remediation-emitting state in an isolated fixture project, executes the emitted remediation, and
re-evaluates. Carries a floor of **7** remediation-emitting states across **3** producers, and pins
the size of the exemption set so a check cannot escape by reclassification.

**Acceptance**: lands red on the four `spec-kitty charter sync` states, demonstrating BC-2 from the
enforcement itself rather than from prose. Introducing a deliberately ineffective remediation keeps
it red (SC-005).

### IC-02 — Correct the charter-source remediation (turns IC-01 green)

**Requirements**: FR-002, C-004, SC-002

Replace the ineffective `spec-kitty charter sync` remediation on the charter-source states with one
that actually clears them. Per R-004 the intended instruction was always *run the migration /
charter generate*; the consolidation migration is inherited and must not be reimplemented (C-004).

**Acceptance**: IC-01 goes from red to green for these states with no change to IC-01's floor. An
operator on a legacy-bundle fixture reaches an unblocked implement step following only emitted
instructions.

**SC-002 measured: 1 step.** On the F2 legacy-bundle fixture both emitted commands
(`charter generate --no-from-interview` and `charter synthesize`) appear in a single
`blocked_reason`; executing them once fully unblocks. Verified by
`tests/specify_cli/charter_freshness/test_sc002_walkthrough.py`, which an independent reviewer
mutation-tested (reverting the remediation to `charter sync` correctly turns it red, so it walks the
real gate→execute→re-run loop rather than asserting a constant). This replaces the spec's deliberate
"bounded number of steps" and closes analysis finding C1.

**Delivered scope note**: only 2 of the 4 charter-sync states were correctable. The `invalid`
charter.yaml state (`:318`) and its cascading `stale` state (`:357`) have **no** effective
self-service remediation — every write path round-trips the YAML through
`charter_yaml_io.update_charter_yaml_section` (INV-9, the sole writer), so all require the file to
already parse. Independently refuted-and-survived. Those two are handled by IC-03 as exemption-set
members rather than by a corrected string.

### IC-03 — Close the runner's backfill (second instance of the same class)

**Requirements**: FR-001, FR-003, C-001, and the spec's US1 Acceptance Scenario 3

`runner.py:245` substitutes `spec-kitty charter status` whenever a check emits no remediation,
guaranteeing the operator is always shown an instruction — including one that cannot help. This is
the BC-2 defect class on the default path, and it makes the spec's exemption path unreachable.
Repair it so "no remediation" reaches the operator as *no remediation*, backed by the explicit
exemption set.

**Acceptance**: IC-01's coverage extends to the runner's composed output, not just check return
values. An exempt check produces operator output containing no command.

### IC-04 — Converge charter-presence resolution onto the canonical seam

**Requirements**: FR-004, C-002, C-003, NFR-004, SC-003

Route the operator-reachable resolvers (R-003, 10 sites after the site-6 exclusion and the dashboard addition) through
`charter.bundle.first_missing_bundle_file`. The gate already resolves the authoritative artifact and
is the convergence *target*, not a site to be changed. No charter artifact moves or is renamed
(C-003). Migration-local resolvers are pinned, not converged.

**Sites 9 and 10 (both in `charter context`) are explicitly in scope.** Both reach presence through
`_bundle_root_for_json`, which short-circuits exactly when `charter.yaml` is missing — so both are
structurally guaranteed to disagree with the gate in the mission's own trigger state. Site 10
additionally **raises** rather than degrading, which NFR-004 forbids. Three of the ten sites mutate
while answering; none may become the seam.

**The census is criterion-derived, not list-asserted (R-007).** Three successive hand enumerations
were wrong (2 → 8 → 9 → 10). T022 must scan for the pattern — an existence check on a charter
artifact that gates an operator-visible answer — so a new hand-rolled resolver turns it red. `10` is
the criterion's current output, not the criterion.

**Acceptance**: one operator-reachable answer to "does the charter exist"; the pinned count cannot
grow silently. The surviving resolver answers without mutating the project.

### IC-05 — Distinguish absent from present-but-unusable

**Requirements**: FR-005

Surface "no charter at all" separately from "charter present but not in the required form". Per the
spec's own checklist this may already exist in the underlying state vocabulary
(`missing` / `invalid` / `fresh`) with only the reporting conflating them — verify before adding
anything new.

**Acceptance**: the two states are distinguishable on every operator-facing surface.

### IC-06 — Regression envelope: no new blocking states

**Requirements**: FR-006, NFR-003, NFR-004, SC-004

Evaluate all four fixture shapes (no charter; legacy bundle without `charter.yaml`; valid
`charter.yaml`; unparseable `charter.yaml`) before and after, asserting the count of
implementation-blocking states is the same or lower — never higher. Greenfield projects with no
charter keep their advisory, non-blocking treatment.

**Acceptance**: blocking-state count is same-or-lower across all four shapes; zero new uncaught
exception paths on any diagnostic surface.

---

## Requirement → IC coverage

| Requirement | IC |
|---|---|
| FR-001 | IC-01, IC-03 |
| FR-002 | IC-02 |
| FR-003 | IC-01, IC-03 |
| FR-004 | IC-04 |
| FR-005 | IC-05 |
| FR-006 | IC-06 |
| NFR-001 | IC-01 |
| NFR-002 | IC-01 → IC-02 ordering |
| NFR-003 | IC-06 |
| NFR-004 | IC-04, IC-06 |
| C-001 | IC-01, IC-03 |
| C-002 | IC-04 |
| C-003 | IC-04 |
| C-004 | IC-02 |
| C-005 | mission-level (closes #2831 only) |
| SC-001 | IC-01 |
| SC-002 | IC-02 |
| SC-003 | IC-04 |
| SC-004 | IC-06 |
| SC-005 | IC-01 |

Every requirement in the spec maps to at least one IC, and every IC carries at least one
requirement. No orphans in either direction.
