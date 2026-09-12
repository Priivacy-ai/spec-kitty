# Tasks: Coord Write-Placement Closure & Birth-Cutover

**Mission**: `coord-write-placement-closure-01KYCF83` | **Branch**: `feat/coord-write-placement-closure`
**Source**: [plan.md](plan.md) 9-IC map (folded post-plan squad) → 10 work packages, disjoint `owned_files`.

Decomposition partitions by **file ownership**, not 1:1 by IC, because several ICs co-edit the same file. Collisions resolved: `artifacts.py` (IC-03+IC-04-classify) → WP02; `status_transition.py` (IC-04-fallback+IC-07-claim) → WP04; `resolution.py` (IC-05 read authority + IC-03 :949 consumer) → WP07; `tests/architectural/` shared scanner → WP06 (WP07 consumes).

## Subtask Index

| T### | Description | WP | [P] |
|------|-------------|----|-----|
| T001 | Enumerate the drifted missions | WP01 |  |
| T002 | Run the backfill and commit the flips | WP01 |  |
| T003 | Author the idempotency regression (RED→green) | WP01 |  |
| T004 | Confirm the acceptance lock passes (initial green) | WP01 |  |
| T005 | Audit the `commit_target is None` sentinel consumers | WP02 | [P] |
| T006 | Flip `PRIMARY_METADATA.commit_target` to partition-aware | WP02 | [P] |
| T007 | Classify `decisions.events.jsonl` in the basename SSOT | WP02 | [P] |
| T008 | Classify `traces/` in the residue-dirs SSOT | WP02 | [P] |
| T009 | Pin the mapping + partition invariant (red-first unit test) | WP02 | [P] |
| T054 | Behavioral proof: `write_meta` lands meta on PRIMARY via the port | WP02 | [P] |
| T010 | Route `bookkeeping_projection` through the port | WP03 |  |
| T011 | Route `bookkeeping_commit` through the port | WP03 |  |
| T012 | Route `decision_log` + confirm decisions→COORD | WP03 |  |
| T013 | Residual-writer routing regression test | WP03 |  |
| T014 | RED-first: claim event carries `shell_pid`/`agent` | WP04 | [P] |
| T015 | Event-source the claim fields | WP04 | [P] |
| T016 | Event-source subtask completion | WP04 | [P] |
| T017 | Close the `_current_branch` HEAD fallback (#1716) | WP04 | [P] |
| T018 | Idempotency + dual-write parity | WP04 | [P] |
| T019 | Regression sweep for claim-liveness | WP04 | [P] |
| T020 | RED-first stale-sweep off the snapshot | WP05 |  |
| T021 | Migrate `stale_detection.py` reader | WP05 |  |
| T022 | Migrate `task_metadata_validation.py` reader | WP05 |  |
| T023 | Retire the frontmatter `shell_pid`/`agent` write | WP05 |  |
| T024 | Full liveness regression + parity | WP05 |  |
| T025 | Extract the shared whole-tree scan helper | WP06 |  |
| T026 | Replace the allowlist with a whole-tree scan | WP06 |  |
| T027 | def-vs-call discrimination for newly-scanned modules | WP06 |  |
| T028 | Extend `test_safe_commit_import_boundary` for `target=` | WP06 |  |
| T029 | Per-file sanctioned exclusions + meta-test rationale | WP06 |  |
| T030 | Synthetic-bypass proof + non-regression | WP06 |  |
| T031 | Enumerate every lenient read + build the whitelist | WP07 |  |
| T032 | Fail-loud `read_dir` authority | WP07 |  |
| T033 | Apply the `resolution.py:949` consumer adjustment | WP07 |  |
| T034 | Fold #2906 accept-time guards into the authority | WP07 |  |
| T035 | New read gate (reuse WP06 scanner) | WP07 |  |
| T036 | Red-first lenient-degrade regressions | WP07 |  |
| T055 | Close the `traces/` read leg (FR-006 read-side) | WP07 |  |
| T037 | Adjudicate distinctness vs `repair_repo` | WP08 | [P] |
| T038 | RED-first: FF and refuse paths | WP08 | [P] |
| T039 | Implement the repair command | WP08 | [P] |
| T040 | Register the subcommand | WP08 | [P] |
| T041 | Diff quality + no-mutation-on-refuse | WP08 | [P] |
| T042 | RED-first: create→implement→merge lands reconciled | WP09 |  |
| T043 | Resolve the pre-target timing decision | WP09 |  |
| T044 | Resolve the two-partition single-`feature_dir` split | WP09 |  |
| T045 | Two-write atomicity / resume-heal | WP09 |  |
| T046 | Idempotency with the one-time migration | WP09 |  |
| T047 | Coord vs flat topology | WP09 |  |
| T048 | Whole-tree gate + green | WP09 |  |
| T049 | RED-first: a born-un-reconciled mission must red | WP10 |  |
| T050 | Re-key `_eligible_runtime_missions` on event-log evidence | WP10 |  |
| T051 | Assert the birth invariant + preserve parity | WP10 |  |
| T052 | Migration-coexistence regression | WP10 |  |
| T053 | Durable-green confirmation | WP10 |  |

`[P]` marks subtasks parallelizable within their WP (no intra-WP ordering). Cross-WP order is governed by the dependency graph below.

## Dependency Graph

```
WP01 (front-load)      — independent, lands first
WP02 (artifacts port)  — independent (foundational)
WP04 (event-source)    — independent
WP08 (mission repair)  — independent
WP03 (route writers)   → WP02
WP05 (readers+retire)  → WP04
WP06 (write gate)      → WP02, WP03, WP04
WP07 (read enforce)    → WP02, WP06
WP09 (birth cutover)   → WP02, WP04, WP05, WP06
WP10 (re-key lock)     → WP05, WP09
```

Rationale: writers route first (WP02/03/04), THEN the whole-tree gate tightens (WP06) so it lands green; the read gate (WP07) consumes WP06's shared scanner; event-sourcing (WP04→WP05) precedes birth (WP09) and re-key (WP10) per C-001 (FR-008 before FR-009, FR-010 after FR-008).

---

## WP01 — Front-load the drifted corpus (unblock CI)

Prompt: [tasks/WP01-frontload-drifted-corpus.md](tasks/WP01-frontload-drifted-corpus.md)
**Deps**: none | **FRs**: FR-007, SC-001 (initial) | **Prompt size**: ~small (~150 lines)

- [ ] T001 Enumerate the drifted missions (WP01)
- [ ] T002 Run the backfill and commit the flips (WP01)
- [ ] T003 Author the idempotency regression RED→green (WP01)
- [ ] T004 Confirm the acceptance lock passes (WP01)

**Summary**: run `migrate backfill-runtime-state` over the 12 drifted missions, commit, add idempotency regression. **Risks**: wrong mission set flipped; self-mission flipped; non-deterministic seeds.

## WP02 — Artifacts port kind-mapping + classification

Prompt: [tasks/WP02-artifacts-port-kind-mapping.md](tasks/WP02-artifacts-port-kind-mapping.md)
**Deps**: none | **FRs**: FR-002, FR-003 (classify), FR-006 (classify) | **Prompt size**: ~medium

- [ ] T005 Audit the `commit_target is None` sentinel consumers (WP02)
- [ ] T006 Flip `PRIMARY_METADATA.commit_target` to partition-aware (WP02)
- [ ] T007 Classify `decisions.events.jsonl` in the basename SSOT (WP02)
- [ ] T008 Classify `traces/` in the residue-dirs SSOT (WP02)
- [ ] T009 Pin the mapping + partition invariant red-first unit test (WP02)
- [ ] T054 Behavioral proof: `write_meta` lands meta on PRIMARY via the port (WP02)

**Summary**: foundational — merges IC-03 (meta commit_target flip) + IC-04-classify into the single artifacts.py SSOT. **Risks**: sentinel not inert (hand `:949` to WP07); traces/ double-home; topology scope creep.

## WP03 — Route residual writers through the port

Prompt: [tasks/WP03-route-residual-writers.md](tasks/WP03-route-residual-writers.md)
**Deps**: WP02 | **FRs**: FR-003, FR-006 | **Prompt size**: ~medium

- [ ] T010 Route `bookkeeping_projection` through the port (WP03)
- [ ] T011 Route `bookkeeping_commit` through the port (WP03)
- [ ] T012 Route `decision_log` + confirm decisions→COORD (WP03)
- [ ] T013 Residual-writer routing regression test (WP03)

**Summary**: route the three residual writers via the classifier so the whole-tree gate lands green. **Risks**: emit fallback is WP04's; traces/ moved writes.

## WP04 — Event-source the claim + close the emit fork

Prompt: [tasks/WP04-event-source-claim-and-emit-fork.md](tasks/WP04-event-source-claim-and-emit-fork.md)
**Deps**: none | **FRs**: FR-003 (fallback), FR-008 (emit) | **Prompt size**: ~medium

- [ ] T014 RED-first: claim event carries `shell_pid`/`agent` (WP04)
- [ ] T015 Event-source the claim fields (WP04)
- [ ] T016 Event-source subtask completion (WP04)
- [ ] T017 Close the `_current_branch` HEAD fallback #1716 (WP04)
- [ ] T018 Idempotency + dual-write parity (WP04)
- [ ] T019 Regression sweep for claim-liveness (WP04)

**Summary**: adds claim/subtask event-sourcing (dual-write retained) + removes the HEAD fallback. **Retirement of the frontmatter write is WP05.** **Risks**: retire-before-migrate (forbidden); create-window deadlock; #1619 scope creep.

## WP05 — Migrate readers, retire the frontmatter write

Prompt: [tasks/WP05-migrate-readers-retire-frontmatter.md](tasks/WP05-migrate-readers-retire-frontmatter.md)
**Deps**: WP04 | **FRs**: FR-008 (readers + retire) | **Prompt size**: ~medium

- [ ] T020 RED-first stale-sweep off the snapshot (WP05)
- [ ] T021 Migrate `stale_detection.py` reader (WP05)
- [ ] T022 Migrate `task_metadata_validation.py` reader (WP05)
- [ ] T023 Retire the frontmatter `shell_pid`/`agent` write (WP05)
- [ ] T024 Full liveness regression + parity (WP05)

**Summary**: migrate both frontmatter readers to the snapshot, THEN retire the write. Order is load-bearing. **Risks**: retire-before-migrate; legacy frontmatter missions.

## WP06 — Whole-tree write gate + shared scanner

Prompt: [tasks/WP06-whole-tree-write-gate.md](tasks/WP06-whole-tree-write-gate.md)
**Deps**: WP02, WP03, WP04 | **FRs**: FR-001, NFR-001, NFR-004 | **Prompt size**: ~large

- [ ] T025 Extract the shared whole-tree scan helper (WP06)
- [ ] T026 Replace the allowlist with a whole-tree scan (WP06)
- [ ] T027 def-vs-call discrimination for newly-scanned modules (WP06)
- [ ] T028 Extend `test_safe_commit_import_boundary` for `target=` (WP06)
- [ ] T029 Per-file sanctioned exclusions + meta-test rationale (WP06)
- [ ] T030 Synthetic-bypass proof + non-regression (WP06)

**Summary**: replace the 17-module allowlist with a whole-tree AST gate; reuse `_BOUNDARY_SANCTIONED_MODULES`; build the shared scanner WP07 reuses. **Risks**: inverted-allowlist creep (forbid dir-prefix); def-site false-reds; real un-routed writer surfaces (fix in WP02-04).

## WP07 — Read-side enforcement + fold #2906 + read gate

Prompt: [tasks/WP07-read-side-enforcement.md](tasks/WP07-read-side-enforcement.md)
**Deps**: WP02, WP06 | **FRs**: FR-004, FR-006 (read leg), NFR-002 | **Prompt size**: ~large

- [ ] T031 Enumerate every lenient read + build the whitelist (WP07)
- [ ] T032 Fail-loud `read_dir` authority (WP07)
- [ ] T033 Apply the `resolution.py:949` consumer adjustment (WP07)
- [ ] T034 Fold #2906 accept-time guards into the authority (WP07)
- [ ] T035 New read gate reuse WP06 scanner (WP07)
- [ ] T036 Red-first lenient-degrade regressions (WP07)
- [ ] T055 Close the `traces/` read leg — FR-006 read-side (WP07)

**Summary**: highest blast radius (~68 read sites) — fail-loud read authority, fold #2906 guards (delegate), whitelist sanctioned degrades. **Risks**: breaking a degrade; double-guard drift; layering regression.

## WP08 — agent mission repair (Gap-2 cure)

Prompt: [tasks/WP08-agent-mission-repair.md](tasks/WP08-agent-mission-repair.md)
**Deps**: none | **FRs**: FR-005, NFR-005 | **Prompt size**: ~medium

- [ ] T037 Adjudicate distinctness vs `repair_repo` (WP08)
- [ ] T038 RED-first: FF and refuse paths (WP08)
- [ ] T039 Implement the repair command (WP08)
- [ ] T040 Register the subcommand (WP08)
- [ ] T041 Diff quality + no-mutation-on-refuse (WP08)

**Summary**: new forward-only repair command reusing `_is_ff_candidate`/`_fast_forward_finding`; adjudicate distinctness vs the third repair surface. **Risks**: overlap with `repair_repo`; force-overwrite on divergence.

## WP09 — Birth-time runtime cutover

Prompt: [tasks/WP09-birth-time-runtime-cutover.md](tasks/WP09-birth-time-runtime-cutover.md)
**Deps**: WP02, WP04, WP05, WP06 | **FRs**: FR-009, NFR-003, C-004 | **Prompt size**: ~large

- [ ] T042 RED-first: create→implement→merge lands reconciled (WP09)
- [ ] T043 Resolve the pre-target timing decision (WP09)
- [ ] T044 Resolve the two-partition single-`feature_dir` split (WP09)
- [ ] T045 Two-write atomicity / resume-heal (WP09)
- [ ] T046 Idempotency with the one-time migration (WP09)
- [ ] T047 Coord vs flat topology (WP09)
- [ ] T048 Whole-tree gate + green (WP09)

**Summary**: the plan's weakest seam — reuse `cutover_mission` at merge bake, resolve timing/two-partition/atomicity/idempotency. **Risks**: half-born mission on crash; forked writer; co-editing WP03's file (prefer two-target spine).

## WP10 — Re-key the acceptance lock + migration coexistence

Prompt: [tasks/WP10-rekey-acceptance-lock.md](tasks/WP10-rekey-acceptance-lock.md)
**Deps**: WP05, WP09 | **FRs**: FR-010, NFR-006, C-003, SC-001 (durable) | **Prompt size**: ~medium

- [ ] T049 RED-first: a born-un-reconciled mission must red (WP10)
- [ ] T050 Re-key `_eligible_runtime_missions` on event-log evidence (WP10)
- [ ] T051 Assert the birth invariant + preserve parity (WP10)
- [ ] T052 Migration-coexistence regression (WP10)
- [ ] T053 Durable-green confirmation (WP10)

**Summary**: highest silent-failure stakes — re-key eligibility on independent event-log evidence (hard-forbid `has_evictable_state()`/`status_phase`); preserve `verify_backfill` parity. **Risks**: vacuous pass; circular keying; green-wash.

---

## Requirement Coverage

| Requirement | WP(s) |
|-------------|-------|
| FR-001 | WP06 |
| FR-002 | WP02 |
| FR-003 | WP02, WP03, WP04 |
| FR-004 | WP07 |
| FR-005 | WP08 |
| FR-006 | WP02, WP03, WP07 |
| FR-007 | WP01 |
| FR-008 | WP04, WP05 |
| FR-009 | WP09 |
| FR-010 | WP10 |
| NFR-001 | WP06 |
| NFR-002 | WP07 |
| NFR-003 | WP09 |
| NFR-004 | WP06 |
| NFR-005 | WP08 |
| NFR-006 | WP10 |
| C-003 | WP10 |
| C-004 | WP09 |

C-001 (phase sequence A→B) and C-002 (scope boundary) are **enforced structurally via the dependency graph + per-WP scope** (not as `requirement_refs` on any WP): C-001's FR-008→FR-009→FR-010 order is the `WP04→WP05→WP09→WP10` edge chain, and C-002's scope boundary is each WP's `owned_files` + explicit "do NOT broaden" constraints. This intentional structural enforcement closes analyze finding **C2** (LOW).

## Success-Criteria Coverage

Each spec success criterion (SC-001..006) maps to the WP/subtask that proves it:

| SC | Criterion (abbrev.) | Proving WP → subtask(s) |
|----|---------------------|-------------------------|
| SC-001 | `test_dogfood_corpus_backfilled` green on main + stays green after ≥3 merges (no re-drift) | WP01 T003/T004 (initial) → **WP10 T052/T053 (durable)** |
| SC-002 | Synthetic non-seam write in **any** `src/` module reds the whole-tree gate | WP06 T030 (formerly-out-of-scope modules) + T026/T029 |
| SC-003 | Wrong-partition read fails loud with a typed error at 100% of routed sites | WP07 T032 (fail-loud authority) + T035/T036 (gate + degrades) |
| SC-004 | `agent mission repair` forward-only FF, zero data loss, refuses on divergence | WP08 T038/T039/T041 |
| SC-005 | create→implement→merge lands `status_phase>=1` + `verify_backfill().ok` + non-empty snapshot, no manual backfill | **WP09 T042 (red-first anchor) + strengthened T047 (resolved-partition split)** |
| SC-006 | `decisions.events.jsonl` + `traces/` classified in SSOT, route COORD via port; emit HEAD fallback removed | WP02 T007/T008 (classify) + WP03 T010–T013 (write route) + WP04 T017 (emit fallback) + **WP07 T055 (traces/ read leg)** |

**SC-005 is proven by WP09** (its functional owner) — the red-first anchor T042 (strengthened to assert the coord two-partition split) plus the exhaustive T047 partition-surface proof. This closes analyze finding **C1** (MEDIUM: SC-005 previously untraced).
