# Tasks — Post-Consolidation Write Surface and Authoring Finish

**Mission**: `post-merge-write-authoring-finish-01KYRRM5`
**Planning/base branch**: `feat/post-merge-write-authoring-finish` · **Merge target**: `feat/post-merge-write-authoring-finish`

Work packages honor C-010 sequencing: WP01 terminology foundation (tidy-first) → WP02 #3033 red-first → WP03 phase-aware CONSOLIDATED resolution → WP04 write-seam thunk + off-checkout refuse + fix-green → {WP05 acceptance authoring, WP06 issue-ref URL+provenance}. Every behavioural change is red-first (NFR-002). Not a bulk-edit mission (the `consolidate` rename foundation is additive; the full rename is #3080).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author ADR 2026-07-30-1 (CONSOLIDATED wiring + consolidate canonical) | WP01 | |
| T002 | Glossary canonicalization in orchestration.md (consolidate canonical + guards) | WP01 | |
| T003 | Drift-ratchet guard: curated forbidden lane-consolidation phrasings + baseline | WP01 | |
| T004 | Red-first bite fixture + green-on-git-merge/publish for the guard | WP01 | |
| T005 | E2 fixture builder (consolidated mission, deleted Target Ref, content on Primary Branch) | WP02 | |
| T006 | Red-first safe-commit test on the E2 mission (PRIMARY kind) | WP02 | |
| T007 | Red-first sibling arm: write_seam coord-kind refused in E2 | WP02 | |
| T008 | lifecycle_phase reader (PRE/E1/E2 + C-003 disambiguation) | WP03 | |
| T009 | Internal phase derivation in resolve_placement_only (no threaded param) | WP03 | |
| T010 | Populate SurfaceLocations.consolidated per phase | WP03 | |
| T011 | Content-presence predicate (squash-robust, D1) | WP03 | |
| T012 | translate/resolve_artifact_surface consumes CONSOLIDATED | WP03 | |
| T013 | Phase + resolution unit tests incl. STATUS_STATE/DECISION_LOG non-regression | WP03 | |
| T014 | Staging-thunk API in write_artifact (probe-before-stage) | WP04 | |
| T015 | tracer_writer passes a thunk (no pre-stage) | WP04 | |
| T016 | Off-checkout refuse-with-recovery (FR-006) | WP04 | |
| T017 | Flip #3033 green: SC-001 safe-commit + SC-002 coord write committed | WP04 | |
| T018 | No-residue (SC-003) + off-checkout (SC-004) + review --mode post-merge (SC-009) regressions | WP04 | |
| T019 | acceptance-verdict: register a negative invariant (correct shape) | WP05 | [P] |
| T020 | acceptance-verdict: execute the invariant via existing engine | WP05 | [P] |
| T021 | accept --diagnose hardening (report malformed, not raise) | WP05 | [P] |
| T022 | Persist fresh overall_verdict on all-pass/no-invariant (samuelgoff) | WP05 | [P] |
| T023 | Rewire accept mission-step prompt (SOURCE only) to drive the CLI | WP05 | [P] |
| T024 | acceptance/matrix.py write path passes the write-seam thunk | WP05 | [P] |
| T025 | Tests SC-006 (accept pass + malformed) / SC-007 (fresh verdict) | WP05 | [P] |
| T026 | Widen single _GH_ISSUE_PATTERN for same-repo issue URLs (no 2nd matcher) | WP06 | [P] |
| T027 | IssueReference + source_file + to_dict/from_dict round-trip | WP06 | [P] |
| T028 | Multi-file dedup preserves first-occurrence provenance | WP06 | [P] |
| T029 | issue_matrix.py write path passes the write-seam thunk | WP06 | [P] |
| T030 | Tests SC-008 (same-repo URL discovered; cross-repo not blocking; provenance) | WP06 | [P] |

## Work Packages

### WP01 — Terminology foundation (tidy-first) · [WP01-terminology-foundation.md](./tasks/WP01-terminology-foundation.md)
- **Goal**: Land the #3080 "do not make it worse" foundation before any functional work — ADR, glossary canonicalization, drift-ratchet guard.
- **Priority**: P1 (tidy-first enabler, C-010). **Independent test**: guard fails on a new forbidden phrasing, green on git-merge/publish.
- **Subtasks**: T001 T002 T003 T004 · **Deps**: none · ~180 lines

### WP02 — #3033 red-first repro · [WP02-3033-red-first-repro.md](./tasks/WP02-3033-red-first-repro.md)
- **Goal**: Author the failing-first `safe-commit` regression evidencing the #3033 P0 through the pre-existing entry point (NFR-002), independently mergeable.
- **Priority**: P1. **Independent test**: the red assertions fail on today's main, will pass after WP03/WP04.
- **Subtasks**: T005 T006 T007 · **Deps**: WP01 · ~150 lines

### WP03 — Phase-aware CONSOLIDATED resolution · [WP03-phase-aware-consolidated-resolution.md](./tasks/WP03-phase-aware-consolidated-resolution.md)
- **Goal**: Derive lifecycle phase internally and wire `SurfaceLocations.consolidated` (squash-robust content-presence) — the resolver core of the #3033 fix.
- **Priority**: P1. **Independent test**: unit tests for phase + consolidated resolution; STATUS_STATE/DECISION_LOG non-regression.
- **Subtasks**: T008 T009 T010 T011 T012 T013 · **Deps**: WP01, WP02 · ~260 lines

### WP04 — Write-seam thunk + off-checkout refuse + fix-green · [WP04-write-seam-thunk-and-fix-green.md](./tasks/WP04-write-seam-thunk-and-fix-green.md)
- **Goal**: No-residue staging thunk (#3073), off-checkout refuse-with-recovery (FR-006), and flip the #3033 regressions green.
- **Priority**: P1. **Independent test**: SC-001/002/003/004/009 green.
- **Subtasks**: T014 T015 T016 T017 T018 · **Deps**: WP03 · ~220 lines

### WP05 — Acceptance authoring (#2318) · [WP05-acceptance-authoring.md](./tasks/WP05-acceptance-authoring.md)
- **Goal**: Register/execute negative invariants via `acceptance-verdict`; harden `--diagnose`; persist a fresh verdict; rewire the accept prompt.
- **Priority**: P2 (Lane D). **Independent test**: SC-006/007.
- **Subtasks**: T019 T020 T021 T022 T023 T024 T025 · **Deps**: WP01, WP04 · ~320 lines

### WP06 — Issue-ref URL + provenance (#1738) · [WP06-issue-ref-url-provenance.md](./tasks/WP06-issue-ref-url-provenance.md)
- **Goal**: Recognize same-repo GitHub-URL issue refs (single regex) + `source_file` provenance with a defined dedup rule.
- **Priority**: P3 (Lane D). **Independent test**: SC-008.
- **Subtasks**: T026 T027 T028 T029 T030 · **Deps**: WP01, WP04 · ~200 lines

## Dependencies

```
WP01 → WP02 → WP03 → WP04 → { WP05, WP06 }
WP05, WP06 also depend on WP01.
```

Critical path: WP01→WP02→WP03→WP04 (the resolver core is sequential by nature). WP05 and WP06 run in parallel after WP04.

## MVP

WP01+WP02+WP03+WP04 = the #3033 P0 (post-consolidation writes succeed, no residue) + the terminology foundation. WP05/WP06 are the authoring quick-wins.
