# Tasks: Retrospective Summary NFR Investigation (#2342)

**Mission**: `retro-summary-nfr-investigation-01KWQARM`
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

One cohesive, sequential investigation WP: profile → flippable-oracle bisect → verdict + disposition report (+ conditional clean fix). The phases share context, so a single agent holds them end-to-end.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Profile `build_summary` over the 200-mission corpus (≥5 runs, per-phase breakdown, reader.py/schema.py focus) | WP01 | |
| T002 | Establish a proven-flippable bisection oracle | WP01 | |
| T003 | `git bisect` over the reader.py/schema.py/summary.py window (incl. #1778) with that oracle | WP01 | |
| T004 | Synthesize the verdict + one recommended disposition; write the committed report | WP01 | |
| T005 | Conditional clean fix: apply + restore 5.0s + lift quarantine, else document why it remains | WP01 | |

---

## WP01 — Retro-summary NFR investigation + report

- **Goal**: a committed report delivering a definitive verdict (real regression | CI variance | inconclusive) on `test_200_missions_under_5s` and one recommended disposition, backed by per-phase profiling and a flippable-oracle bisection. Ship code only if a clean, low-risk regression falls out.
- **Priority**: P1 (single WP = whole mission).
- **Independent test**: the report exists with ≥5-run profiling (median + spread, per-phase), a bisection outcome (SHA or substantiated "no discrete regression"/"inconclusive"), one verdict, and one recommended disposition with enactment + quarantine-lift steps.
- **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006.
- **Prompt**: [tasks/WP01-retro-summary-nfr-investigation.md](./tasks/WP01-retro-summary-nfr-investigation.md)

### Subtasks
- [ ] T001 Profile `build_summary` over the test's 200-mission corpus, ≥5 runs, report median + min–max spread and a per-phase breakdown; confirm/refute the reader.py/schema.py parse+validate hot path (WP01)
- [ ] T002 Establish a **proven-flippable** oracle (known-bad endpoint reads red on this hardware, or a relative per-phase-delta threshold) — else the verdict is inconclusive (WP01)
- [ ] T003 `git bisect` over `git log -- reader.py schema.py summary.py` (include `0818c7590` #1778) with the flippable oracle → regressing SHA or substantiated "no discrete regression" (WP01)
- [ ] T004 Write `docs/plans/engineering-notes/2342-retro-summary-nfr/report.md`: verdict + evidence + one recommended disposition (fix+restore 5.0s / non-blocking perf slice / local_only) with enactment + quarantine-lift + week-long-variance follow-up (WP01)
- [ ] T005 If a clean low-risk root-cause fix is found: apply the minimal reader.py/schema.py fix, restore the test to 5.0s, remove the `quarantine` marker, prove green; else no code ships and the report states why quarantine remains (WP01)

### Dependencies
None (single WP).

---

## MVP
WP01 is the whole mission — the committed verdict + disposition report is the deliverable.
