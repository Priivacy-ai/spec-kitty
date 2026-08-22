# Tasks: Worktree-Aware Root Resolution & Verdict Parity

**Mission**: `worktree-root-resolution-01M0B59R` · **Branch**: `fix/worktree-root-resolution` · **Topology**: coord
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contracts**: [contracts/](./contracts/resolver-and-verdict-contracts.md)

11 work packages. Two independent streams: **resolver/write-path** (WP01 foundation → WP02–WP07 adopters) and **verdict/audit** (WP08–WP11). Every release-blocking slice ships an issue-pinned `@pytest.mark.regression` test authored-and-shown-failing on base (NFR-001); already-fixed code ships green sentinels (NFR-004); all write-refusals route through one seam (NFR-003).

> **Post-tasks squad adjustment (2026-08-18):** WP12 (coordination-key writer, #3461-writer) was **dropped** — three lenses confirmed the coord-key `UNKNOWN_SHAPE` residual was already fixed by #2696 (`META_COORDINATION_KEYS` ⊆ meta.json known-keys); FR-018 dropped, recommend tracker wontfix on #3461-writer. WP11 (#3563) was **narrowed** — an in-code disclosure (`review/cycle.py:106-158`) shows flipping the write-side default is not yet safe (breaks `test_analysis_report_rehome`); WP11 now opts a safe consumer into `kind=REVIEW_CYCLE` and verifies the already-repointed reader, deferring the full default-flip.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Create `core/checkout_identity.py` — `resolve_checkout_identity(cwd, intent)` + `CheckoutIdentity`/`FailClosedRefusal` | WP01 | |
| T002 | Ownership decision from worktree-pointer topology + ownership claim (decidable, no clone guess) | WP01 | |
| T003 | `PRIMARY_READ` intent returns canonical_target unchanged | WP01 | |
| T004 | Unit tests for the guard (owner / foreign-lane / nested-clone × WRITE/PRIMARY_READ) | WP01 | [P] |
| T005 | Must-not-flip characterization tests pinning #2320/#3328 anchors GREEN | WP01 | [P] |
| T006 | NFR-003 architectural test — no write-refusal outside the FailClosedRefusal seam | WP01 | [P] |
| T007 | intake: red-first regression — lane invocation clobbers primary slot (RED on base) | WP02 | [P] |
| T008 | intake: adopt identity guard; fail-closed identity check before shared-slot write | WP02 | |
| T009 | intake `--force`: identity-check before overwriting a foreign-owned slot | WP02 | |
| T010 | tool-surfaces `--fix`: red-first regression — lane invocation mutates primary manifest (RED) | WP03 | [P] |
| T011 | tool-surfaces `--fix`: adopt guard; fail-closed refusal naming primary | WP03 | |
| T012 | mission-state: red-first — lane invocation silent primary canonicalization / audit false-green (RED) | WP04 | [P] |
| T013 | mission-state: preserve #2320 target + add identity awareness (refuse/announce lane invocation) | WP04 | |
| T014 | mission-state: repair manifest enumerates every touched field incl. removed (FR-009) | WP04 | |
| T015 | Green sentinel pinning `bec7c25273` repair preservation (NFR-004) | WP04 | [P] |
| T016 | backfill: red-first — cutover guard passes against redirected path from a lane (RED) | WP05 | [P] |
| T017 | backfill: make cutover guard (`verify_backfill`) invoking-checkout-aware | WP05 | |
| T018 | setup-plan: red-first — branch_matches_target:true from primary HEAD in a lane (RED) | WP06 | [P] |
| T019 | setup-plan: compute branch_matches_target from invoking checkout / meta.json | WP06 | |
| T020 | find_repo_root: red-first — nested clone re-anchored to outer primary (RED, disagrees w/ resolve_canonical_root) | WP07 | [P] |
| T021 | find_repo_root: stop at nested-clone `.git`-dir boundary, aligning with resolve_canonical_root | WP07 | |
| T022 | Hoist `_parse_review_result_json` → `status/review_result_parse.py` (co-located w/ ReviewResult) | WP08 | |
| T023 | Hoist `_enforce_for_review_commit_gate` → `lanes/for_review_gate.py`, surface-neutral error contract | WP08 | |
| T024 | orchestrator-api transition delegates to the hoisted parser + gate | WP08 | |
| T025 | for_review gate red-first — both directions (clone satisfied=pass, unsatisfied=fail) on both surfaces | WP08 | [P] |
| T026 | emit: red-first — WP cannot exit in_review via emit alone (RED on base) | WP09 | [P] |
| T027 | emit: add `--review-result-json`, validate via hoisted parser, thread into TransitionRequest | WP09 | |
| T028 | emit: correct the misleading `--help` `in_review`/`--evidence-json` verdict example | WP09 | |
| T029 | in_review→approved: admit ReviewResult path on emit (parity w/ transition) | WP09 | |
| T030 | shape_registry: red-first — review_result row emits UNKNOWN_SHAPE (RED, key absent) | WP10 | [P] |
| T031 | Register `review_result` in `status_event_row` shape | WP10 | |
| T032 | NEW `status_event_row`-scoped drift test (fails on unregistered persisted shape) | WP10 | [P] |
| T033 | Value-equality round-trip property + non-vacuous generator (≥1 review_result event) | WP10 | [P] |
| T034 | Green sentinel pinning `407ea376c4` reducer projection (NFR-004) | WP10 | [P] |
| T035 | review/cycle: red-first — write-side default is WORK_PACKAGE_TASK today (RED for the narrow opt-in) | WP11 | [P] |
| T036 | review/cycle: opt the safe consumer(s) into `kind=REVIEW_CYCLE` (NO global default flip — blocked, see WP11) | WP11 | |
| T037 | Read-tolerance verification: event-authority reader (`event_sourced_review_result`) is unaffected by write-side kind | WP11 | |
| T038 | Re-verify `test_analysis_report_rehome` stays green under the narrow opt-in | WP11 | |

---

## WP01 — Checkout-identity guard foundation *(P1, no deps)*

**Goal**: One additive identity guard (owns-vs-foreign, read/write intent) that in-scope commands adopt; preserve deliberate primary anchors; establish the single refusal seam. FR-001, FR-008; NFR-003.
**Independent Test**: unit tests for the guard across {owner, foreign-lane, nested-clone}×{WRITE, PRIMARY_READ}; characterization tests keep #2320/#3328 anchors green; architectural test forbids ad-hoc refusals.
**Subtasks**: T001 T002 T003 T004 T005 T006
**Risks**: touching the `get_main_repo_root` primitive would blast ~130 callers — WP01 is ADDITIVE only, it does not edit `core/paths.py` (that boundary belongs to WP07). Est. ~380 lines.

## WP02 — intake fail-closed identity check *(P1, dep WP01, #3540)*

**Goal**: intake performs a fail-closed identity check before writing the shared untracked brief slot from a foreign checkout; `--force` still identity-checks. FR-002.
**Independent Test**: red-first — from a lane worktree intake clobbers the primary slot on base; green after it refuses naming the slot.
**Subtasks**: T007 T008 T009 · Est. ~250 lines.

## WP03 — doctor tool-surfaces --fix fail-closed refusal *(P1, dep WP01, #2613)*

**Goal**: from a lane worktree, `doctor tool-surfaces --fix` refuses (naming primary) instead of silently repairing the primary's per-checkout agent-surface manifest. FR-003. **Cleanest confirmed defect.**
**Independent Test**: red-first — lane invocation repairs primary's `.claude/commands/*` on base; green after it refuses.
**Subtasks**: T010 T011 · Est. ~240 lines.

## WP04 — doctor mission-state reconciliation *(P1, dep WP01, #3051/#3541)*

**Goal**: preserve the deliberate #2320 primary status-home AND add identity awareness so a lane invocation is not a silent primary canonicalization; audit reports no false-green; manifest enumerates every touched field. FR-004, FR-009; green sentinel for `bec7c25273` (NFR-004).
**Independent Test**: red-first lane-invocation surfacing + audit honesty; manifest completeness; sentinel stays green.
**Subtasks**: T012 T013 T014 T015 · Est. ~320 lines.

## WP05 — backfill cutover guard false-green fix *(P1, dep WP01, #3049)*

**Goal**: `migrate backfill-runtime-state`'s cutover guard is invoking-checkout-aware — it does not pass merely by verifying the same redirected path it wrote. FR-005. (Write target stays deliberate per C-003.)
**Independent Test**: red-first — from a lane the verify passes against the redirected path on base; green after lane-aware / refuses.
**Subtasks**: T016 T017 · Est. ~240 lines.

## WP06 — setup-plan branch-match honesty *(P1, dep WP01, #3124)*

**Goal**: `branch_matches_target` computed from the invoking checkout / mission `meta.json`, not primary HEAD. FR-006. (Target-branch resolution stays primary-anchored — deliberate.)
**Independent Test**: red-first — lane on a lane branch reports `branch_matches_target: true` (primary HEAD) on base; green after reflects invoking checkout.
**Subtasks**: T018 T019 · Est. ~230 lines.

## WP07 — find_repo_root nested-clone boundary *(P1, dep WP01 — same core/paths.py, #2610)*

**Goal**: `find_repo_root` stops at a nested-clone `.git`-dir boundary consistently with `resolve_canonical_root`. FR-007. **Sequences after WP01** (shares `core/paths.py`).
**Independent Test**: red-first — nested clone re-anchored to outer primary by find_repo_root on base; green after both resolvers agree.
**Subtasks**: T020 T021 · Est. ~200 lines.

## WP08 — verdict parser + for_review gate hoist *(P1, no deps, #3547/#1734)*

**Goal**: hoist `_parse_review_result_json` → `status`, `_enforce_for_review_commit_gate` → a `lanes`-side leaf with a surface-neutral error contract; orchestrator-api delegates; gate topology-aware in **both** directions. FR-011.
**Independent Test**: both-surface, both-direction gate parity (clone satisfied=pass, unsatisfied=fail).
**Subtasks**: T022 T023 T024 T025 · Est. ~360 lines.

## WP09 — emit --review-result-json + --help + parity *(P1, dep WP08, #3547/#1734)*

**Goal**: `agent status emit` accepts `--review-result-json` (hoisted parser), threads into TransitionRequest, walks in_review→approved→done; correct the `--help` trap; parity on the in_review→approved guard. FR-010, FR-012, FR-013.
**Independent Test**: red-first emit-only lifecycle walk to done; `--help` snapshot has no non-functional example.
**Subtasks**: T026 T027 T028 T029 · Est. ~320 lines.

## WP10 — audit registration + value round-trip *(P1, no deps, #3543/#3461-registry)*

**Goal**: register `review_result` in `status_event_row`; NEW artifact-scoped drift test; value-equality round-trip + non-vacuous generator; green sentinel for `407ea376c4`. FR-014, FR-015, FR-016; NFR-004.
**Independent Test**: red-first UNKNOWN_SHAPE on base; value round-trip fails on corrupted-value replay; drift test fails on unregistered shape.
**Subtasks**: T030 T031 T032 T033 T034 · Est. ~340 lines.

## WP11 — review-cycle kind opt-in (narrowed) *(P2, no deps, #3563)*

**Goal**: opt the safe consumer(s) into `kind=REVIEW_CYCLE` where the physical write does NOT move; verify the already-repointed event-authority reader; keep `test_analysis_report_rehome` green. FR-017. **Does NOT flip the global write-side default** — that is blocked on the disclosed physical-write/git-staging separation rework (`review/cycle.py:106-158` "WP13 finding") + 3 unrouted sites, tracked separately.
**Independent Test**: red-first (default kind is WORK_PACKAGE_TASK) for the narrow opt-in; green after the safe consumer emits REVIEW_CYCLE, the reader is unaffected, and rehome stays green.
**Subtasks**: T035 T036 T037 T038 · Est. ~280 lines.

---

## Dependency Summary

```
WP01 ──┬── WP02  WP03  WP04  WP05  WP06        (fail-closed adopters)
       └── WP07                                (core/paths.py — after WP01)
WP08 ── WP09                                   (verdict CLI)
WP10                                           (audit registration + round-trip)
WP11                                           (review-cycle, independent)
```

**MVP**: WP01 + WP03 (cleanest confirmed defect) demonstrates the fail-closed pattern end-to-end. The verdict half (WP08+WP09) is the strongest independently-shippable slice.

## Requirement Coverage

FR-001→WP01 · FR-002→WP02 · FR-003→WP03 · FR-004/009→WP04 · FR-005→WP05 · FR-006→WP06 · FR-007→WP07 · FR-008→WP01 · FR-010/012/013→WP09 · FR-011→WP08 · FR-014/015/016→WP10 · FR-017→WP11.

*(FR-018 / WP12 dropped post-tasks — #3461-writer coordination-key residual already fixed by #2696; recommend tracker wontfix.)*
