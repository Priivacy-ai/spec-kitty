# Tasks: Charter Preflight Remediation Authority

**Mission**: `charter-preflight-remediation-01KYG9WK` · **Branch**: `fix/charter-preflight-remediation`
**Planning base**: `fix/charter-preflight-remediation` · **Merge target**: `fix/charter-preflight-remediation`
**Inputs**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/remediation-effectiveness.md](./contracts/remediation-effectiveness.md)

## Execution shape

**Strictly linear spine.** WP01 → WP02 → WP03 → WP04 → WP05 → WP06. Every WP depends on its
predecessor. This is deliberate: the ordering carries the NFR-002 red-first obligation (WP01 must
land red before WP02 corrects anything), and WP04's consolidation touches surfaces WP02 and WP03
have already stabilised. There are no parallel lanes.

**The one ordering that is not negotiable**: WP01 before WP02. WP01's red *is* the red-first
evidence for FR-002. Landing them together, or WP02 first, destroys the evidence and violates
NFR-002 and ADR `2026-07-17-1`.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Extend `_fixtures.py` with the four fixture shapes (F1–F4) as named builders | WP01 | |
| T002 | Enumerate the preflight check registry and declare the exemption set | WP01 | |
| T003 | Build the effectiveness driver: drive state → execute remediation → re-evaluate | WP01 | |
| T004 | Assert against the operator-visible composed output, not check return values | WP01 | |
| T005 | Pin the floors: 7 remediation-emitting states, 3 producers, exemption-set size | WP01 | |
| T006 | Prove non-vacuity — a deliberately ineffective remediation turns it red | WP01 | |
| T007 | Capture and commit the RED run as the NFR-002 red-first evidence | WP01 | |
| T008 | Determine the effective remediation for each `charter sync` state | WP02 | |
| T009 | Replace the ineffective remediation on `_compute_charter_source` (2 states) | WP02 | |
| T010 | Replace the ineffective remediation on `_compute_synced_bundle` (2 states) | WP02 | |
| T011 | Verify WP01 goes red → green with its floors unchanged | WP02 | |
| T012 | Walk the legacy-bundle fixture end to end; record the SC-002 step count | WP02 | |
| T013 | Remove the `runner.py:245` remediation backfill | WP03 | |
| T014 | Wire the explicit exemption set into the runner's output path | WP03 | |
| T015 | Extend WP01's assertions to cover the runner's composed output | WP03 | |
| T016 | Verify an exempt check yields operator output containing no command | WP03 | |
| T017 | Establish the canonical presence API over `first_missing_bundle_file` | WP04 | |
| T018 | Route the non-mutating CLI resolvers (sites 3, 4, 5) | WP04 | |
| T019 | Route the remaining non-mutating resolvers (sites 7, 8) | WP04 | |
| T020 | Route `build_charter_context` (site 2, mutating) | WP04 | |
| T021 | Route `_project_charter_json_block` (site 9, mutating, gate-caught) | WP04 | |
| T031 | Route `build_charter_context_include` (site 10) and convert its raise to a reported state | WP04 | |
| T022 | Pin the resolver census by criterion, not by list (currently 10 / 3) | WP04 | |
| T023 | Verify one operator-reachable answer and a non-mutating seam | WP04 | |
| T024 | Determine whether the state vocabulary already distinguishes absent from unusable | WP05 | |
| T025 | Surface the distinction on the operator-facing preflight output | WP05 | |
| T026 | Verify absent and unusable are distinguishable on every surface | WP05 | |
| T027 | Build the four-shape blocking-state matrix, measured before and after | WP06 | |
| T028 | Assert the blocking count is same-or-lower, never higher | WP06 | |
| T029 | Assert greenfield (no charter at all) keeps advisory, non-blocking treatment | WP06 | |
| T030 | Assert zero new uncaught exception paths on any diagnostic surface | WP06 | |

---

## WP01 — Remediation-effectiveness enforcement (lands RED)

**Prompt**: [tasks/WP01-remediation-effectiveness-enforcement.md](./tasks/WP01-remediation-effectiveness-enforcement.md)
**Priority**: P1 (foundation) · **Dependencies**: none · **Estimated prompt size**: ~420 lines
**Requirements**: FR-001, FR-003, NFR-001, NFR-002, C-001, SC-001, SC-005

**Goal**: Build the structural mechanism that holds every preflight check to the rule *executing a
check's remediation changes that check's state*. It must land **red**, because the current tree
genuinely violates the rule.

**Independent test**: Run the mechanism on the unmodified tree. It fails on the four
`spec-kitty charter sync` states. That failure is the deliverable.

**Subtasks**: T001, T002, T003, T004, T005, T006, T007

**Risks**: authoring a parallel fixture mechanism instead of extending the existing one
(DIRECTIVE_044 violation); asserting on check return values rather than operator-visible output,
which would measure the wrong surface and pass while the operator is still misled.

---

## WP02 — Correct the charter-source remediation (turns WP01 green)

**Prompt**: [tasks/WP02-correct-charter-source-remediation.md](./tasks/WP02-correct-charter-source-remediation.md)
**Priority**: P1 · **Dependencies**: WP01 · **Estimated prompt size**: ~330 lines
**Requirements**: FR-002, C-004, SC-002

**Goal**: Replace the four ineffective `spec-kitty charter sync` remediations with instructions that
actually clear the states that emit them. This is the P0 fix.

**Independent test**: WP01's mechanism goes from red to green for these states, with its pinned
floors unchanged. An operator on a legacy-bundle fixture reaches an unblocked implement step
following only emitted instructions.

**Subtasks**: T008, T009, T010, T011, T012

**Risks**: reimplementing or altering the consolidation migration (C-004 violation); "fixing" the
gate by lowering the floor rather than correcting the remediation.

---

## WP03 — Close the runner's remediation backfill

**Prompt**: [tasks/WP03-close-runner-remediation-backfill.md](./tasks/WP03-close-runner-remediation-backfill.md)
**Priority**: P1 · **Dependencies**: WP02 · **Estimated prompt size**: ~300 lines
**Requirements**: FR-001, FR-003, C-001

**Goal**: `runner.py:245` substitutes `spec-kitty charter status` whenever a check emits no
remediation, so the operator is always shown a command — including one that cannot help. This is the
same defect class as the P0, sitting on the default path, and it makes the spec's exemption path
unreachable.

**Independent test**: an exempt check produces operator-visible output containing no command, and
WP01's assertions now cover the composed output.

**Subtasks**: T013, T014, T015, T016

**Risks**: deleting the fallback without giving the operator anything, degrading a merely-confusing
message into a silent one.

---

## WP04 — Converge charter-presence resolution onto the canonical seam

**Prompt**: [tasks/WP04-converge-charter-presence-resolution.md](./tasks/WP04-converge-charter-presence-resolution.md)
**Priority**: P1 · **Dependencies**: WP03 · **Estimated prompt size**: ~470 lines
**Requirements**: FR-004, C-002, C-003, NFR-004, SC-003

**Goal**: Route the ten operator-reachable charter-presence resolvers through
`charter.bundle.first_missing_bundle_file`. The gate is the convergence *target* — it already
resolves the authoritative artifact — not a site to be changed.

**Independent test**: with the charter in a state one surface previously called present and another
called missing, every operator-reachable surface returns the same answer.

**Subtasks**: T017, T018, T019, T020, T021, T031, T022, T023

**Risks**: the direction-of-fix inversion (converging onto `charter.md` would re-open a closed
decision — see R-001); making a mutating path the canonical seam; **a fourth enumeration miss** — the
count has been wrong three times running (2 → 8 → 9 → 10), which is why T022 derives the census from
the R-007 criterion instead of asserting a hand-written list.

---

## WP05 — Distinguish absent from present-but-unusable

**Prompt**: [tasks/WP05-distinguish-absent-from-unusable.md](./tasks/WP05-distinguish-absent-from-unusable.md)
**Priority**: P2 · **Dependencies**: WP04 · **Estimated prompt size**: ~230 lines
**Requirements**: FR-005

**Goal**: Report "no charter at all" differently from "charter present but not in the required form".

**Independent test**: the two states produce distinguishable operator output on every surface.

**Subtasks**: T024, T025, T026

**Risks**: adding a new state vocabulary when the existing `missing`/`invalid` distinction already
carries the information and only the reporting conflates it — T024 exists to prevent this.

---

## WP06 — Regression envelope: no new blocking states

**Prompt**: [tasks/WP06-regression-envelope.md](./tasks/WP06-regression-envelope.md)
**Priority**: P1 · **Dependencies**: WP05 · **Estimated prompt size**: ~260 lines
**Requirements**: FR-006, NFR-003, NFR-004, SC-004

**Goal**: Prove the mission introduced zero new blocking project states.

**Independent test**: the four-shape matrix shows a blocking count same-or-lower than the
pre-mission baseline, never higher.

**Subtasks**: T027, T028, T029, T030

**Risks**: measuring only after the change, which cannot prove "no new blocking states" — the
baseline must be captured against the pre-mission commit.

---

## Requirement coverage

| Requirement | WP |
|---|---|
| FR-001 | WP01, WP03 |
| FR-002 | WP02 |
| FR-003 | WP01, WP03 |
| FR-004 | WP04 |
| FR-005 | WP05 |
| FR-006 | WP06 |
| NFR-001 | WP01 |
| NFR-002 | WP01 → WP02 ordering |
| NFR-003 | WP06 |
| NFR-004 | WP04, WP06 |
| C-001 | WP01, WP03 |
| C-002 | WP04 |
| C-003 | WP04 |
| C-004 | WP02 |
| C-005 | mission-level |

## MVP scope

**WP01 + WP02 together are the P0 fix.** WP01 proves the defect structurally and WP02 clears it. If
the mission had to stop early, that pair delivers the unblocking. WP03 is required for charter
compliance (C-001 — the class is not closed while the runner backfill stands), and WP04 delivers the
diagnosability half of the issue.
