# Mission Specification: Retrospective Summary NFR Investigation

**Mission Branch**: `fix/retro-summary-nfr-investigation`
**Created**: 2026-07-04
**Status**: Draft
**Input**: GitHub issue #2342 — `test_200_missions_under_5s` (NFR-003: `build_summary` over a 200-mission corpus < 5s) breached its budget twice on CI (5.10/5.11s) and was quarantined. Investigate real regression vs CI variance and deliver a verdict + disposition.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Maintainer gets a definitive regression-vs-variance verdict (Priority: P1)

A maintainer is stuck in a budget-bump dance: the test read 5.10/5.11s twice on unrelated diffs — too consistent for pure runner noise, too close to the line for an obvious algorithmic blow-up. They need a verdict backed by (a) a per-phase profile of `build_summary` over the 200-mission corpus and (b) a git bisection using the test as oracle, so the disposition is evidence-based, not another guess.

**Why this priority**: The whole point of the issue — replace the guess-and-tune loop with a real answer. Without the verdict the mission delivers nothing.

**Independent Test**: a committed report contains repeated-run profiling numbers (median + spread) with a per-phase breakdown, a bisection result, and a single stated verdict (real regression | CI variance | inconclusive).

**Acceptance Scenarios**:

1. **Given** the 200-mission corpus the test builds, **When** `build_summary` is profiled over N repeated local runs, **Then** the report records median/spread wall-time and a per-phase breakdown (filesystem scan, YAML parse, reduce).
2. **Given** the candidate regression windows (retrospective terminus wiring #1888/#2119, tolerance-category additions, YAML load paths), **When** a bisection is run with the test as oracle, **Then** the report records either a regressing commit SHA or a substantiated "no discrete regression found."

---

### User Story 2 - Maintainer gets a concrete recommended disposition (Priority: P1)

Given the verdict, the maintainer needs a single recommended path from the issue's disposition matrix, with rationale: **real regression** → fix at root + restore the test to the 5.0s blocking suite; **CI-flake / perf OK** → remove from blocking CI via either (a) a dedicated non-blocking perf pipeline slice, or (b) a `local_only` designation.

**Why this priority**: A verdict without a recommended action leaves the maintainer where they started. The recommendation is what unblocks removing the quarantine.

**Independent Test**: the report names one recommended disposition with rationale tied to the evidence, and describes the concrete follow-up (including the week-long CI-variance collection the maintainer should run).

**Acceptance Scenarios**:

1. **Given** the verdict, **When** the report concludes, **Then** it recommends exactly one disposition with evidence-based rationale and the concrete steps to enact it (and to lift the quarantine marker).

---

### User Story 3 - A clean root-cause fix, if found, is applied (Priority: P2)

If — and only if — the investigation surfaces a clean, low-risk root-cause regression, apply the fix and restore the test to the 5.0s blocking suite (removing the quarantine marker). If the fix is non-trivial or risky, do not ship it; recommend it.

**Why this priority**: Fixing a proven, cheap regression closes the issue outright; but a speculative or large fix belongs in its own governed mission, not bolted onto an investigation.

**Independent Test**: if a fix is applied, the test passes at the restored 5.0s budget and the quarantine marker is removed; if not, the quarantine stays with a documented reason.

**Acceptance Scenarios**:

1. **Given** a clean, evidence-backed root-cause regression, **When** it is fixed, **Then** `test_200_missions_under_5s` passes at 5.0s and the `quarantine` marker is removed.
2. **Given** no clean fix (variance, or a risky/large fix), **When** the mission concludes, **Then** no code change ships and the report states why the quarantine remains.

### Edge Cases

- **Bisection inconclusive** (no single regressing commit; gradual creep) → verdict leans variance/gradual-creep; recommend the perf-slice with trend tracking.
- **Profiling shows no dominant phase** near the budget → supports variance.
- **Local hardware is faster/slower than CI** → the local absolute time is not directly comparable; the report must lean on the per-phase *relative* breakdown and the bisection delta, not the raw local seconds.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Per-phase profile of build_summary | As a maintainer, I want a repeated-run profile of `build_summary` over the 200-mission corpus with a per-phase breakdown, so I can see where the time goes. | High | Open |
| FR-002 | Bisection with a flippable oracle | As a maintainer, I want a git bisection across the candidate windows using an oracle that is **proven to flip** — either the 5.0s test if a known-bad endpoint reads red on the measurement hardware, or a relative per-phase timing delta with an explicit bad/good threshold — so a real regression is located or credibly ruled out (not falsely marked all-GOOD by fast local hardware). | High | Open |
| FR-003 | Definitive verdict | As a maintainer, I want a single stated verdict (real regression / CI variance / inconclusive) backed by the profiling + bisection evidence. | High | Open |
| FR-004 | Recommended disposition | As a maintainer, I want exactly one recommended disposition (fix+restore / perf-slice / local_only) with rationale and enactment steps, so I can lift the quarantine. | High | Open |
| FR-005 | Conditional clean fix | As a maintainer, I want a clean, low-risk root-cause regression (if found) fixed with the test restored to 5.0s and the quarantine marker removed; otherwise no code ships. | Medium | Open |
| FR-006 | Committed report artifact | As a maintainer, I want the investigation captured in a committed report so the verdict and evidence are durable and reviewable. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Repeatable measurement | Profiling uses a repeatable local method (e.g. `cProfile` / repeated `pytest` timing) over at least 5 runs, reporting median and min–max spread — not a single reading. | Reliability | High | Open |
| NFR-002 | Quality gate on any code | Any shipped code (a fix, or a test/marker change) passes `mypy --strict` + `ruff` with zero new issues/suppressions and the affected tests. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Week-long CI variance is out of scope | The issue's week-long `quarantine-visibility` variance collection cannot run in-session; the report recommends it as a maintainer follow-up and uses local repeated runs (plus any already-available CI readings) for the in-mission characterization. | Scope | High | Open |
| C-002 | No budget-bump-to-green | Per the charter flakiness policy, the disposition must never be "just raise the budget"; a real regression is fixed at root, variance is relocated off blocking CI. | Process | High | Open |
| C-003 | Quarantine is tracking state | If the verdict lands with a fix, restore 5.0s and remove the `quarantine` marker; quarantine is not an end state. | Process | High | Open |
| C-004 | Canonical report location | The report is a committed artifact under a canonical path (e.g. `docs/plans/engineering-notes/…` following existing precedent), not an ad-hoc location. | Technical | Medium | Open |

### Key Entities

- **`build_summary`** (`src/specify_cli/retrospective/summary.py`): the retrospective summary reducer under test.
- **`test_200_missions_under_5s`** (`tests/retrospective/test_summary_tolerance.py`): the NFR-003 timing test, currently `@pytest.mark.quarantine`.
- **200-mission corpus**: the fixture the test builds; reused as the profiling workload.
- **Quarantine mechanism**: `tests/_support/quarantine.py` + `docs/guides/testing-flakiness.md` (Tier-3); the `quarantine-visibility` non-blocking job.
- **Investigation report**: the committed deliverable (verdict + evidence + recommended disposition).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: the report records `build_summary` timing over ≥5 repeated local runs (median + spread) with a per-phase breakdown (fs scan / YAML parse / reduce).
- **SC-002**: the report records a bisection outcome — a regressing commit SHA, or a "no discrete regression" ruling that is only valid if the oracle was demonstrated flippable (a known-bad endpoint read red, or a relative per-phase delta threshold was established); if the oracle could not be made to flip across the window, the verdict is **inconclusive**, not "no regression."
- **SC-003**: the report states exactly one verdict and one recommended disposition with evidence-based rationale and enactment steps (including the maintainer's week-long variance follow-up).
- **SC-004**: if a clean fix is applied, `test_200_missions_under_5s` passes at 5.0s and the `quarantine` marker is removed; otherwise the quarantine remains with a documented reason and no code ships.

## Assumptions

- Local hardware differs from GitHub runners; the in-session profile provides the per-phase *relative* breakdown and the bisection delta, while the absolute CI seconds and week-long variance are maintainer follow-ups (C-001). The GitHub-runner-class profiling in the issue's step 1 is best-effort/out-of-session.
- The 200-mission corpus fixture in the test is representative and reused as the workload rather than re-invented.
- The disposition choice among (fix / perf-slice / local_only) is a *recommendation*; the operator makes the final call (consistent with draft-PR-first delivery).
- **Investigation lead (from the post-spec squad's measurement, to verify not assume):** the dominant per-mission cost appears to be the `read_record` YAML parse ×200 (`summary.py:~421`), while per-mission `YAML()` object construction measured ~0.2% of budget (not a hotspot). The named candidate windows #1888/#2119 do **not** touch `summary.py` (the terminus-classification / record-path branches trace to #821/#1850 and are not exercised by the retrospective-only corpus). Profiling should focus on the YAML parse path; the bisection window should include the commits that actually touched `summary.py` / its YAML load path, and confirm the corpus exercises the branch under suspicion before trusting a flat delta.
