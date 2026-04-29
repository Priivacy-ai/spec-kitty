# Tasks: Charter #828 Implementation Sprint

**Mission**: `charter-828-implementation-sprint-01KQD7VB`  
**Branch**: `docs/charter-end-user-docs-828` → PR → `main`  
**Generated**: 2026-04-29

---

## Summary

4 work packages, 12 subtasks. Each WP orchestrates one phase of the source mission (`charter-end-user-docs-828-01KQCSYD`) via `spec-kitty next`. WPs are strictly sequential: WP01 → WP02 → WP03 → WP04. No parallelism at the sprint level (parallelism within source WP02–WP08 is handled by `spec-kitty next` internally).

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Run pre-flight checks (git status, pull, version, check-prerequisites) | WP01 | — | [D] |
| T002 | Execute source mission WP01 via `spec-kitty next` (gap analysis + nav + docfx.json) | WP01 | — | [D] |
| T003 | Verify WP01 deliverables (gap-analysis.md, toc files, docfx.json updated) | WP01 | — | [D] |
| T004 | Execute source mission WP02–WP08 via `spec-kitty next` (content generation) | WP02 | — |
| T005 | Verify page count (14 new + 5 updated) and spot-check CLI flag accuracy | WP02 | — |
| T006 | Grep for stale command names and TODO markers across all changed docs | WP02 | — |
| T007 | Execute source mission WP09 via `spec-kitty next` (validation pass) | WP03 | — |
| T008 | Review validation-report.md for completeness and evidence coverage | WP03 | — |
| T009 | Triage validation failures — stop and report any product bugs (FR-007) | WP03 | — |
| T010 | Execute source mission WP10 via `spec-kitty next` (release handoff) | WP04 | — |
| T011 | Verify release-handoff.md completeness (all required sections filled) | WP04 | — |
| T012 | Verify branch cleanliness and PR #885 merge-readiness | WP04 | — |

---

## Work Packages

---

**Phase 1: Foundation**

## WP01 — Pre-Flight and Foundation (WP01)

**Goal**: Run pre-flight checks, execute source WP01, verify navigation and docfx.json outputs.  
**Priority**: P0 — All content WPs blocked on this.  
**Prompt**: [WP01-pre-flight-and-foundation.md](tasks/WP01-pre-flight-and-foundation.md)  
**Estimated size**: ~280 lines

**Subtasks**:

- [x] T001 Run pre-flight checks (git status, pull, version, check-prerequisites) (WP01)
- [x] T002 Execute source WP01 via `spec-kitty next` (gap analysis + nav + docfx.json) (WP01)
- [x] T003 Verify WP01 deliverables (gap-analysis.md, toc files, docfx.json updated) (WP01)

**Dependencies**: none  
**Parallelization**: none; WP02–WP04 are blocked on this.

---

**Phase 2: Content Generation**

## WP02 — Content Generation (WP02–WP08)

**Goal**: Drive source WP02–WP08 via `spec-kitty next` to produce all 14 new and 5 updated docs pages.  
**Priority**: P0  
**Prompt**: [WP02-content-generation.md](tasks/WP02-content-generation.md)  
**Estimated size**: ~320 lines

**Subtasks**:

- [ ] T004 Execute source WP02–WP08 via `spec-kitty next` (content generation) (WP02)
- [ ] T005 Verify page count (14 new + 5 updated) and spot-check CLI flag accuracy (WP02)
- [ ] T006 Grep for stale command names and TODO markers across all changed docs (WP02)

**Dependencies**: WP01  
**Parallelization**: none (internal parallelism within source WP02–WP08 handled by `spec-kitty next`)

---

**Phase 3: Quality Gate**

## WP03 — Validation Pass (WP09)

**Goal**: Drive source WP09 via `spec-kitty next`; review validation-report.md; triage failures.  
**Priority**: P0 — Required before PR.  
**Prompt**: [WP03-validation.md](tasks/WP03-validation.md)  
**Estimated size**: ~260 lines

**Subtasks**:

- [ ] T007 Execute source WP09 via `spec-kitty next` (validation pass) (WP03)
- [ ] T008 Review validation-report.md for completeness and evidence coverage (WP03)
- [ ] T009 Triage validation failures — stop and report any product bugs (FR-007) (WP03)

**Dependencies**: WP02

---

**Phase 4: Ship**

## WP04 — Release Handoff and PR (WP10)

**Goal**: Drive source WP10 via `spec-kitty next`; verify release-handoff.md; confirm PR is ready.  
**Priority**: P0 — Required to close the sprint.  
**Prompt**: [WP04-release-and-ship.md](tasks/WP04-release-and-ship.md)  
**Estimated size**: ~260 lines

**Subtasks**:

- [ ] T010 Execute source WP10 via `spec-kitty next` (release handoff) (WP04)
- [ ] T011 Verify release-handoff.md completeness (all required sections filled) (WP04)
- [ ] T012 Verify branch cleanliness and PR #885 merge-readiness (WP04)

**Dependencies**: WP03
