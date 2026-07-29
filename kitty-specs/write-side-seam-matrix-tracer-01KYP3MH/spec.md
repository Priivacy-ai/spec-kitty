# Mission Specification: Write-Side Seam: Matrix & Tracer Writers

**Mission Branch**: `feat/write-side-seam-matrix-tracer`
**Created**: 2026-07-29
**Status**: Draft
**Input**: Follow-up to PR #3060 (read-side placement-seam closure, **MERGED** `e6806f184`). Close the write/gate side of the same seam, make the acceptance/issue matrices structured and deterministically writable, and give lanes a writable findings surface — so consumer missions stop losing matrix/tracer state and stop burning inference to hand-edit matrices.

> **Grounding note (2026-07-29):** Two profile-loaded squads (pre-planning + post-spec) surveyed the code on the merged base. Full findings, the write-bypass census, the merge-driver refutation, the coord-authority-gate ratchet, and the recommended lane shape live in [`pre-planning-ledger.md`](./pre-planning-ledger.md). Headline: the write **seam** already exists (`write_target`) — this is an **adoption** mission for the seam, plus deterministic **matrix tooling** (structured schema + writers + row-aware merge) and the **tracer** writer.

## Context & Motivation *(informative)*

PR #3060 unified the **read** side of the placement seam and deleted the `primary_feature_dir_for_mission` wrapper. The write seam already exists and predates it: `PlacementSeam.write_target(kind)` (`resolution.py:1430`), landed in ADR `2026-06-24-1`, which **explicitly rejects a second write-only resolver (C-006)**. This mission catches the *write call sites*, the *matrix artifacts*, and the *tracer* up to that seam.

Consumer-facing pains addressed:

1. **Matrix editing is inference-heavy and the artifacts are semi-structured.** The acceptance-matrix is JSON but has no writing *command* (agents hand-edit it and even canonical acceptance can leave a stale `overall_verdict`); the issue-matrix is free markdown, so per-item state cannot be merged or tooled deterministically.
2. **Issue-reference completeness is blind.** Reference discovery scans only `spec.md`, missing refs in `tasks/`/`plan.md`/etc., and there is no merge-time completeness gate; conversely a zero-reference mission is hard-failed for a matrix it should not need.
3. **Lanes cannot cleanly record findings.** `TRACER_FILE` is coord-classified but has only a reader; lane appends trip the warn-then-block guards.
4. **Consolidation drops writes.** Lanes branch off a base minted before planning artifacts exist (no common ancestor), and the matrix merge drivers are whole-file "keep-more-filled-side," so concurrent disjoint-row edits clobber.

The unifying move: **structured matrix artifacts + deterministic write commands + one write-surface seam adoption + row-aware merge + a lane-safe tracer writer**, all routing lane-origin writes to the correct partition through the existing `write_target`/`commit_for_mission` authority.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record an acceptance-matrix verdict deterministically, and have canonical acceptance persist it (Priority: P1)

A reviewing agent finishes a work package and records the acceptance-matrix outcome with one command that fronts the existing writer and routes through the seam. Separately, when a mission is canonically accepted with all criteria `pass`, the persisted `overall_verdict` must become `pass` — today it can stay stale `pending` because the writer is only called when negative invariants exist.

**Why this priority**: Headline token-burn win (#2318) plus a live correctness bug (#2318 comment 5102989064) that misleads PR/readiness tooling.

**Independent Test**: Run the verdict command on a scaffolded matrix and assert deterministic update with zero product-source reads. Separately, accept an all-pass/no-negative-invariant mission and assert `acceptance-matrix.json` persists `overall_verdict: "pass"`.

**Acceptance Scenarios**:
1. **Given** a scaffolded acceptance-matrix row, **When** the agent runs the acceptance-verdict command, **Then** the row is updated deterministically via `write_target(ACCEPTANCE_MATRIX)`, derived fields recompute, negative-invariant provenance is preserved, and the computed verdict remains authoritative (never a hand-stored duplicate).
2. **Given** an all-pass matrix with no negative invariants, **When** the mission is canonically accepted, **Then** the persisted `overall_verdict` is `pass` (regression for #2318 comment).
3. **Given** a verdict already recorded, **When** the command re-runs with identical inputs, **Then** it is a no-op.

---

### User Story 2 - A structured, complete, correctly-gated issue-matrix (Priority: P1)

An agent works with the issue-matrix as **structured data with per-item statuses** (not free markdown), discovers issue references across *all* mission artifacts (not just `spec.md`), and is neither blocked by a completeness gate that scans too little nor failed for a matrix a zero-reference mission does not need.

**Why this priority**: Makes the issue-matrix deterministically tooled/mergeable and closes three real gaps (#1738 discovery + missing merge gate; #3035 zero-reference hard-fail).

**Independent Test**: Reference an issue only in `tasks/WP01.md`; assert discovery finds it and the structured matrix carries a row. Run post-merge review on a zero-reference mission; assert Gate 4 is `not_applicable`, not a hard fail. Set a per-item status via the command; assert `issue-matrix.json` updates (single canonical artifact, no markdown render).

**Acceptance Scenarios**:
1. **Given** an issue referenced only in `tasks/`, `plan.md`, or `contracts/`, **When** completeness is checked (approval and merge time), **Then** the reference is discovered (multi-file) and a merge-time gate enforces it (#1738).
2. **Given** a spec with no canonical issue references, **When** post-merge review runs, **Then** Gate 4 is recorded `not_applicable` and the verdict is decided by applicable gates — no fabricated matrix required (#3035).
3. **Given** the structured `issue-matrix.json`, **When** an agent sets a row's per-item status via the command, **Then** the JSON artifact updates deterministically (routed via `write_target(ISSUE_MATRIX)`) — a single canonical artifact, no separate markdown render.

---

### User Story 3 - Capture a finding on a lane without blocking the lane (Priority: P1)

An implementing agent on a lane worktree records a tooling-friction / approach / design-decision finding via a command that routes it to the coordination surface, leaving the lane branch unblocked.

**Why this priority**: The tracer writer is the one genuine must-build; without it findings remain uncapturable on-lane (#2980/#2549).

**Independent Test**: From a lane, append a finding; assert it lands on the coordination surface, the lane branch has no new `kitty-specs/` commit, and a later `move-task` is not blocked.

**Acceptance Scenarios**:
1. **Given** an agent on a lane, **When** it appends a finding, **Then** the entry is recorded on the coordination surface with correct actor attribution and no `kitty-specs/` commit lands on the lane branch.
2. **Given** a finding recorded from a lane, **When** the lane later runs `move-task`, **Then** the transition is not blocked by a `kitty-specs/` divergence.
3. **Given** identical finding content submitted twice, **When** the command re-runs, **Then** no duplicate entry is created.

---

### User Story 4 - Writes land on the right surface and survive consolidation (Priority: P2)

An operator consolidates several lanes; matrix, tracer, and status writes recorded during implementation are all present and correct after merge — not reverted, not clobbered, even when two lanes edited disjoint rows of the same matrix.

**Why this priority**: The durability guarantee that makes Stories 1–3 trustworthy; depends on a common ancestor and row-aware merge.

**Acceptance Scenarios**:
1. **Given** an execution lane created at implement time, **When** the lane is created, **Then** it branches from the recorded planning-artifact commit so it shares a common ancestor with the consolidation base.
2. **Given** matrix/tracer writes on a lane, **When** the mission consolidates, **Then** those writes survive with zero silent reversions.
3. **Given** two lanes writing disjoint rows of the same structured matrix, **When** they consolidate, **Then** the rows union with no clobber (row-aware merge driver).

### Edge Cases

- **Target surface absent** (deleted `target_branch` post-merge, missing coordination worktree): the write **refuses with a structured, recoverable result that discloses #3033 as the deferred fix** — never a fallback write to any surface, never a consolidation abort.
- **Unknown target**: a verdict/finding command for an unknown WP returns an actionable error, not a silent no-write.
- **Zero issue references**: completeness/review record `not_applicable`; the structured matrix is not fabricated.
- **Coord-authority gate**: routing a COORD write must satisfy the coord-authority gate; teaching the gate the seam idiom (FR-010) is in scope, not a bypass allow-list.
- **Structured-matrix compatibility**: every **migrated** issue-matrix consumer (doctor, post-merge review, move-task/approval, finalize-lint, the recognition-map consumers, doctrine skills) reads `issue-matrix.json`; a mission with only a legacy `issue-matrix.md` is still readable via failover-read until migrated (FR-013). The dashboard JSON panel is a net-new follow-up (#3068), not part of this migration; `merge_gates` gains a net-new JSON reader via FR-004.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Acceptance-matrix verdict command + persist-on-accept | As a reviewing agent, I want a command that fronts `write_acceptance_matrix` via `write_target(ACCEPTANCE_MATRIX)` keeping the computed verdict authoritative, AND canonical acceptance to persist the recomputed `overall_verdict` (not only when negative invariants exist), so the JSON is never stale (#2318 + comment 5102989064). | High | Open |
| FR-002 | Structured matrix schema (acceptance + issue) | As a maintainer, I want both matrices as structured **JSON** artifacts with a clear schema and accepted per-item statuses — the issue-matrix migrated from free markdown to `issue-matrix.json` as the **single canonical artifact** (NO `issue-matrix.md` render), and every **live** downstream reader (doctor, post-merge review, move-task/approval, finalize-lint, the `kind_for_mission_file` recognition consumers, the merge-driver + its registration, and the doctrine skills) migrated to the JSON form — so the tooling is deterministic and testable in isolation. The dashboard JSON panel and the `merge_gates` completeness reader are **net-new** (dashboard = follow-up #3068; the gate arrives via FR-004), not migration targets. | High | Open |
| FR-003 | Deterministic issue-matrix verdict command | As an agent, I want a command that sets an issue-matrix row's per-item status/verdict on the structured `issue-matrix.json`, routed through `write_target(ISSUE_MATRIX)`. | High | Open |
| FR-004 | Multi-file issue-reference discovery + merge-time gate | As a maintainer, I want `detect_issue_references` generalized from single-`spec.md` to scan `spec.md`+`tasks/`+`plan.md`+`research.md`+`analysis-report.md`+`contracts/` (updating the three enforcement sites), and a missing issue-matrix completeness gate added to `merge_gates.py`, so load-bearing references are never invisible (#1738). | High | Open |
| FR-005 | Zero-reference gate = not_applicable | As a maintainer, I want post-merge review + gates to record Gate 4 `not_applicable` when the spec declares no canonical issue references (same definition as finalization), retaining fail-closed when references exist, with regression for both branches (#3035). | High | Open |
| FR-006 | Lane findings (tracer) append routed to coordination surface | As an agent on a lane, I want to append a dated, attributed finding routed to the coordination surface via `commit_for_mission` without a lane-branch `kitty-specs/` commit, so findings are captured without blocking the lane (#2980/#2549; attribution guard #2960). | High | Open |
| FR-007 | Adopt the write-side seam across the TRUE bypass set | As a maintainer, I want the actual bypasses — caller-resolved-`feature_dir` matrix writers, the tracer writer, **only `decisions/emit.py:71`** of the coord-authority-gate write sites (the other three — `widen/state.py`, `agent_tasks_ports.py`, `lanes/recovery.py` — stay **by-design** on the kind-blind resolver so the coord-authority gate's floor stays non-vacuous; see B1) — converged onto `write_target`/`commit_for_mission`, NOT the seam's own engine (the raw `resolve_placement_only` census is not the target). **DEFERRED (2026-07-29, → #3071):** the #2663 implement-claim partition split and the `status/emit.py` write (#2966 slice) are **out of this mission**. WP03 rediscovered red-first that routing #2663 through the seam breaks two pinned prior-mission invariants (the #2160/C-004 verbatim-commit deferral pinned by `test_implement_coord_idempotency.py`, and the literal `_commit_target_ref_for` unification pinned by `test_precondition_ref_unification.py`), and that `status/emit.py` has **no git-commit to route** (pure path-I/O via `canonicalize_feature_dir`; #2966 flagged for its own spec). Both are the very #2160/#2966 clusters C-006 marks out-of-scope; delivered here = the seam-adoption **core helper** (`coordination/write_seam.py`) + the tracer/matrix writers that consume it. | High | Core delivered; #2663/#2966 → #3071 |
| FR-008 | Row-aware matrix merge driver | As an operator, I want the whole-file "more-filled-side" acceptance/issue-matrix merge drivers replaced by row-aware drivers over the structured schema, so concurrent disjoint-row writes union without clobber (covers #2482 AND the disjoint-row gap grounding refuted). | High | Open |
| FR-009 | Lane branches from the recorded planning-artifact commit | As an operator, I want an execution lane's worktree to branch from the recorded finalize-tasks tip (captured in `lanes.json`/`meta.json`), not the pre-planning coord tip nor a moving target tip, so **planning-artifact (PRIMARY-partition) writes** share a common ancestor with the consolidation base and are not reverted at merge (#2993). (Matrix/tracer are COORD-partitioned and serialize onto the coord surface — they do not traverse lane branches, so their durability is orthogonal to this base; FR-008's `%O` is topology-resolved, see C-007 + FR-008.) ADR-gated (C-007); own WP with merge/ancestor tests; no consolidation abort path. | High | Open |
| FR-010 | Teach the coord-authority gate the write-side seam idiom | As a maintainer, I want `decisions/emit.py` routed off the gate allow-list (Move A, strengthening) and — only if seam-routed writers still resolve via the kind-blind resolver — the gate widened to recognize `write_target(<COORD kind>)` by def-use with an alias-bite non-vacuity test (Move B), re-pinning the census floor (4→3), so routing COORD writes is unblocked (#3055). | High | Open |
| FR-011 | Zero-write refusal + actionable errors on unroutable writes | As an agent, I want an unroutable write (missing coord surface, deleted `target_branch`, unknown target) to return a structured, recoverable **zero-write refusal** disclosing #3033 as the deferred real fix — never a fallback write, never a consolidation abort — so I recover deterministically. | Medium | Open |
| FR-012 | Idempotent, structured-result write commands | As an orchestrator, I want every write command to be idempotent (re-run = no-op) and to emit structured output naming the row/entry and destination surface, so retries are safe and results are machine-consumable. | Medium | Open |
| FR-013 | Issue-matrix migration (on-write + failover-read + bulk command) | As a maintainer, I want a shared migration sub-module that (a) failover-reads a legacy `issue-matrix.md` when `issue-matrix.json` is absent, (b) migrates a mission to JSON on the first structured write, and (c) backs a dedicated bulk-migration command for one-shot swap-over — so no in-flight consumer mission breaks on the format change. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero-inference writes | A matrix or tracer write requires zero product-source reads by the agent: the workflow is fully specified by CLI arguments and current mission state (0 "read module X to learn the shape" steps). | Usability | High | Open |
| NFR-002 | Responsive commands | Each write command completes in under 3 seconds (p95) on a representative mission. | Performance | Medium | Open |
| NFR-003 | Lane-safe and idempotent | Any write command run from a lane leaves zero `kitty-specs/` commits on the lane branch and no blocked/dirty state; re-running any command is a no-op. | Reliability | High | Open |
| NFR-004 | Coverage and complexity | Every new command branch, converged call site, structured-schema path, merge driver, and gate change has focused unit tests executed directly; no new/modified function exceeds cyclomatic complexity 15. | Maintainability | High | Open |
| NFR-005 | No regression of shipped invariants | The read-side seam census, the C-008 architectural gates, the coord-authority gate (`test_resolution_authority_gates.py`), and every migrated issue-matrix consumer remain green; event-log status remains the sole authority for lane state. | Reliability | High | Open |
| NFR-006 | Back-compat via failover-read | A mission that still has only a legacy `issue-matrix.md` remains fully readable via failover-read until its first structured write migrates it; no consumer mission breaks on the format change. | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Extend the seam, never allow-list a bypass | The write path MUST reuse/extend `write_target`/`commit_for_mission`. A per-command exception to the `kitty-specs/` guards, or hand-deriving a destination, is prohibited (ADR `2026-06-24-1` C-006: no parallel write resolver). | Technical | High | Open |
| C-002 | Tracer classification unchanged | `TRACER_FILE` remains coord-partition; lane findings reach the coordination surface via routing, not lane-branch commits. | Technical | High | Open |
| C-003 | Do not rebuild the status engine | Status transitions stay event-log-authoritative; this mission only **routes** status writes (incl. the `status/emit.py` slice of #2966) through the seam — no transition-logic re-implementation. | Technical | High | Open |
| C-004 | Terminology canon | New command names/flags/prose use canonical Mission terminology; no `feature*` aliases; name the `primary`/`merge`/`routing` sense. | Business | Medium | Open |
| C-005 | Built on merged PR #3060 | Coord topology; consolidates into `feat/write-side-seam-matrix-tracer`; PR into `upstream/main` post-consolidation. Rebased onto PR #3060 (MERGED `e6806f184`); must not reference the deleted `primary_feature_dir_for_mission` wrapper. | Technical | High | Open |
| C-006 | Explicit out-of-scope boundary | OUT of core, filed as fast-follows: finalize-tasks commit-destination bugs (#2938/#2937/#2930/#2802/#2643); status-writer *behavioural* unification (#2300/#3029/#1734 — only #3027's mark-status-roster campsite is in-core); review-verdict integrity P0s (#2996/#2939, #3044); post-merge write mode **#3033** (FR-011 guards only); mission-card-as-alternative-issue-source **#1742/#1740** (`at_tension_with` — this mission commits to the scanner + structured-artifact path); the **dashboard JSON matrix panel #3068** (net-new build parented to UI/UX epic #650 — this mission migrates the data producers/consumers, not the dashboard reader). | Business | Medium | Open |
| C-007 | ADR + contracts scope | Exactly **one new ADR** (FR-009 lane-base: amends `2026-04-03-1`, cites `2026-06-24-1/-2`+`2026-07-23-2`, MUST pin a recorded base SHA — never a moving tip — and resolve whether the base carries coord-status lineage in light of `2026-06-24-1` §5 + FR-007 routing; no consolidation abort path). **Three `contracts/` docs** (FR-007 write-seam-adoption; FR-010 gate predicate-widen with an alias-bite non-vacuity proof, citing the ADR by slug `2026-06-26-1-single-authority-seam-and-call-site-gate`; FR-008 merge-driver algorithm — 3-way base-aware `%O`/`%A`/`%B`, row-key canonicalization, delete-vs-stale disambiguation). FR-007/FR-010/FR-008 contracts are NOT new ADRs — they implement decisions already made (a Move B gate-predicate widen, if triggered, is an amendment of `2026-06-26-1`, not a contract-only change). | Technical | High | Open |
| C-008 | Structured-matrix migration completeness | The issue-matrix migration MUST move every **live** downstream consumer to `issue-matrix.json` in this mission — no consumer left parsing markdown. The live consumer set is: **doctor, post-merge review, move-task/approval blocker, finalize-lint, the `kind_for_mission_file` recognition consumers (`auto_rebase`/`commit_router`/coherence), the merge-driver + registration (`merge.py`/`init.py`/forward migration), and the doctrine skills.** The **dashboard** (net-new build, follow-up #3068) and **`merge_gates`** (net-new reader via FR-004) are explicitly NOT migration targets. NO `issue-matrix.md` is emitted going forward; back-compat is via failover-read + migrate-on-write (FR-013), not a dual-format render. | Technical | High | Open |

### Key Entities

- **Acceptance-matrix**: structured (JSON) per-requirement/DoD verdicts; `overall_verdict` is a computed property (never hand-stored) and must be persisted on canonical acceptance.
- **Issue-matrix**: migrated to a single **structured JSON artifact (`issue-matrix.json`) with per-item statuses**; no markdown render (the dashboard parses JSON); rows are keyed by tracked-issue reference discovered across all mission artifacts.
- **Tracer finding entry**: a dated, actor-attributed note (tooling-friction / approach / design-decision), routed to the coord surface.
- **Placement seam (write path)**: the **existing** `write_target(kind)` → `resolve_placement_only` authority; this mission adopts it at bypassing call sites — it does not build a new one.
- **Row-aware merge driver**: a merge driver operating on structured matrix rows so disjoint concurrent edits union.
- **Execution lane**: a per-lane worktree/branch; FR-009 bases it on the recorded planning-artifact commit.

## Domain Language *(canonical terms)*

- **Placement seam** — `write_target` (writes) / `read_dir` (reads); do not build a second write-only resolver.
- **Coordination vs primary partition** — coord = lifecycle surfaces (status, notes, trace, issue-matrix, acceptance-matrix, move-task); primary = stable planning. Name the sense.
- **`TRACER_FILE`** — the coord-partition artifact kind for lane findings; unchanged here.
- **Acceptance-matrix vs issue-matrix** — distinct structured artifacts; never conflate.
- **Lane-origin write routing** — a lane-invoked write materialized to the coordination surface by `commit_for_mission`, not committed to the lane branch.
- **Structured matrix** — a schema'd JSON/YAML artifact with per-item statuses, rendered to markdown for humans.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent records an acceptance-matrix verdict with a single command and **zero product-source reads**; canonical acceptance of an all-pass mission persists `overall_verdict: pass`.
- **SC-002**: **100%** of lane finding writes succeed with **zero** lane-branch `kitty-specs/` commits and without tripping the `move-task` block.
- **SC-003**: Across a representative multi-lane consolidation, matrix and tracer writes survive with **zero silent reversions**, including two lanes editing disjoint rows of the same matrix (**zero clobber**).
- **SC-004**: The "record a verdict / finding / issue-status" procedure is a **fixed, bounded command sequence** whose length does not grow with mission size.
- **SC-005**: Issue-reference completeness detects references across `spec.md`+`tasks/`+`plan.md`+`research.md`+`analysis-report.md`+`contracts/`; a zero-reference mission records Gate 4 `not_applicable` (no hard fail).
- **SC-006**: **No regression** — the read-side seam census, the C-008 architectural gates, the coord-authority gate, and every migrated issue-matrix consumer remain green.

## Dependencies & Traceability *(informative)*

**Built on**: PR #3060 (read-side placement-seam closure — **MERGED** `e6806f184`, closed **#2886**; **#3014 resolved independently, not by #3060**).

| Ticket | Maps to | Note |
|--------|---------|------|
| #2318 (+ comment 5102989064) | FR-001 | Acceptance-matrix marking CLI + stale-`pending`-on-accept fix. Campsite #2743 (negative-invariant integrity). |
| (structured schema) | FR-002 | Issue-matrix markdown → structured JSON/YAML + per-item statuses + rendered view + reader migration. |
| #2583 | FR-003 | Deterministic issue-matrix verdict/per-item write (adopted from the deferred slice into core). |
| #1738 | FR-004 | Multi-file reference discovery + missing merge-time completeness gate. |
| #3035 | FR-005 | Zero-reference Gate 4 `not_applicable`. **Folded from samuelgoff (coordinated, reassigned); their work reused downstream.** |
| #2980, #2549, #2960 | FR-006 | Lane-write barrier resolved by routing; attribution guard. Tracer writer is the one genuine must-build. |
| #2663, #2966 (status/emit.py slice) | FR-007 | Fold the implement-claim partition split + route `status/emit.py`; converge the true bypass set onto `write_target`. |
| #2482 | FR-008 | Stale-residue clobber + disjoint-row union via row-aware driver. |
| #2970 | FR-008 | Merge-driver path-injection hardening (5 S2083 BLOCKERs in `merge_driver.py`) — folded into the row-aware-driver rewrite (IC-08); red-first repro before the fix; must not regress the driver contract (Sonar attack-vector-campsite doctrine). |
| #2993 | FR-009 | No-common-ancestor lane snapshot — P0, ADR-gated, own WP. Blast radius: `auto_rebase`, `merge/executor`, `merge/ordering`, dependent-lane invariant #1684. |
| #3055 | FR-010 | Coord-authority gate seam idiom (routing prerequisite). |
| #3027 (campsite) | FR-003/FR-006 | mark-status roster placement dependency — in-mission campsite only (behavioural unification stays out, C-006). |

**Adjacent / coordinate (do not collide)**: #2465 (read-side resolver proliferation in `workflow.py` — read axis, coordinate with FR-007's write convergence in the same module), #3065 (post-#3060 read-side follow-up).

**Governance attach points** (link via `blocks`/`blocked_by`, do NOT spawn a new epic): #2160 (coord artifact authority), #1746 (Mission Clarity Layer — home of the issue-matrix/traceability domain, where #1738 lives; add `at_tension_with #1742` for the mission-card source alternative), #1676 (deterministic authoring), #3044 (review-verdict integrity — parents the fast-follow P0s), #2017 (block-class guards).

## Assumptions

- Rebased onto merged PR #3060 (`e6806f184`); the wrapper is gone, `write_target`/`write_acceptance_matrix` intact (verified).
- The four artifact merge drivers today are `spec-kitty-{acceptance-matrix,issue-matrix,traces,event-log}`; the matrix ones are whole-file "more-filled-side" (grounding-refuted as row-aware) — FR-008 replaces them with row-aware drivers over the FR-002 structured schema.
- Event-log status remains the sole authority for lane state (#2684 shipped); this mission routes status writes, it does not re-derive them.
- Lane→coordination routing follows the existing `commit_for_mission` materialization; the tracer writer sits beneath the `read_dir(RETROSPECTIVE)` short-circuit and must call the leaf/`write_target` directly (Ledger-M16 recursion guard).
- Governance epics #2160 / #1746 / #1676 / #3044 exist; this mission attaches to them rather than creating a new epic.
- The canonical tracer directory literal is `"traces"`; confirm no `traces/`-vs-`ln/` drift with a `Read` during plan.
