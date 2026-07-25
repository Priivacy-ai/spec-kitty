# Mission Specification: Coord Write-Placement Closure & Birth-Cutover

**Mission Branch**: `coord-write-placement-closure-01KYCF83`
**Created**: 2026-07-25
**Status**: Draft
**Input**: Follow-on to #2841/#2874 (coord-trust) closing the write-placement residual, with #2917 (runtime-state birth-cutover) as Part B. Closes #2917; under the #1619/#2816 runtime-state epic. Grounding: `docs/plans/engineering-notes/2841-residual-2917-mission-scope.md`, `docs/plans/engineering-notes/2917-runtime-state-birth-cutover-research.md`.

## User Scenarios & Testing *(mandatory)*

The "user" here is the Spec Kitty framework itself and the maintainer/operator who relies on coordination/primary artifacts being trustworthy. Each story is an independently testable slice.

### User Story 1 - Unblock the mission corpus (Priority: P1)

The dogfood mission corpus fails CI (`test_dogfood_corpus_backfilled`) because 12 recently-merged missions were never runtime-cut-over. A maintainer runs a one-time backfill over the drifted missions and commits the result, turning the acceptance lock green and unblocking the 3.2.6 release gate.

**Why this priority**: it is the sole remaining CI Quality red blocking 3.2.6; low-risk, deterministic, and independent of the structural work.

**Independent Test**: run the backfill over the drifted corpus, commit, and observe `test_dogfood_corpus_backfilled` pass with no other change.

**Acceptance Scenarios**:

1. **Given** 12 eligible missions with `status_phase` unset and no deterministic seed events, **When** the runtime-state backfill runs over the corpus, **Then** each gains its seed events + `status_phase=1`, `verify_backfill().ok` is true, and the acceptance lock passes.
2. **Given** the backfill has already run, **When** it runs again, **Then** it seeds zero new events and leaves `status_phase` and the event log byte-identical.

### User Story 2 - New missions are born runtime-reconciled (Priority: P1)

A mission taken through create → implement → merge lands already runtime-reconciled (`status_phase` stamped, snapshot non-empty, parity verified) with no manual backfill — so the corpus never re-drifts, and the acceptance lock stays green as new missions merge.

**Why this priority**: without it the corpus re-reds on every merge wave; this is the durable root fix (Option C).

**Independent Test**: create a mission through the real entry points, claim a WP and complete a subtask, merge it, and assert it lands `status_phase>=1` + `verify_backfill().ok` + non-empty snapshot without any migration invocation.

**Acceptance Scenarios**:

1. **Given** the runtime-authoring dual-write is event-sourced, **When** a mission is merged, **Then** the birth-cutover stamps `status_phase` and reconciles any residual runtime through the placement port, one routed write.
2. **Given** a merged mission whose event log carries runtime, **When** the re-keyed acceptance lock runs, **Then** it requires `status_phase>=1` and a non-empty snapshot (event-log-keyed), and would red if a future mission merged un-reconciled.
3. **Given** a **coord-topology** mission at land, **When** the birth-cutover runs, **Then** `meta.json`/`status_phase` lands on the PRIMARY surface and the seed events on the COORD surface, each resolved through the placement port — without conflating a single `feature_dir`. *(FR-009 coord/flat two-partition write; depends on FR-002.)*

### User Story 3 - Split-brain writes are unrepresentable everywhere (Priority: P1)

Any mission-artifact write in the codebase that bypasses the placement port is rejected by an architectural gate — regardless of which module it lives in — so the coord/primary split-brain cannot reappear through a new, unlisted writer.

**Why this priority**: #2874 enforced write routing only within a 17-module allowlist (`_CHECKOUT_GRAMMAR_MODULES`); a new writer elsewhere silently recreates the bug. This closes the write side completely.

**Independent Test**: add a synthetic mission-artifact write (`safe_commit`/`CommitTarget`/`write_meta`) that bypasses the port to a module outside the former allowlist; the whole-tree gate must red.

**Acceptance Scenarios**:

1. **Given** the whole-tree enforcement gate, **When** a non-seam-derived mission-artifact write is added to any `src/` module, **Then** the gate fails and names the offending site.
2. **Given** meta.json / `PRIMARY_METADATA` writes, **When** they run, **Then** they resolve their partition through the placement port (enabling a coord/primary two-partition write), not a single ambient `feature_dir`.
3. **Given** the `emit` HEAD-derived current-branch fallback (`_current_branch`, deferred #1716), **When** a status write resolves its target, **Then** it routes through the placement port and no longer falls back to the ambient checkout HEAD. *(FR-003)*
4. **Given** `decisions.events.jsonl` and `traces/` are classified in the partition SSOT, **When** they are written or read, **Then** each resolves to its classified partition (coord) via the port rather than an ambient `feature_dir`. *(FR-003, FR-006)*

### User Story 4 - Reads are partition-safe (Priority: P2)

Every mission-artifact read routes through the read-surface authority; a read from the wrong partition fails loud instead of silently returning a substituted surface — the symmetric completion of #2874's write routing.

**Why this priority**: writes are enforced but reads are still fixed one-at-a-time (whack-a-read); a general read authority closes the loop.

**Independent Test**: drive a read for a coord-homed kind against a primary substitute; assert a typed fail-loud error, not a silent fallback.

**Acceptance Scenarios**:

1. **Given** a mission-artifact read for a coord-homed kind, **When** the resolved surface is primary (substituted), **Then** the read raises a typed partition-mismatch error.

### User Story 5 - Pre-existing split-brain is curable (Priority: P2)

A maintainer can detect and safely repair a mission whose bookkeeping content has already diverged across partitions, via a dedicated `agent mission repair` command — prevention (#2874) plus cure.

**Why this priority**: prevention cannot retroactively fix corpora that already drifted; a forward-only, fail-loud repair is the missing Gap-2 tool.

**Independent Test**: inject a pre-existing content split-brain into a fixture mission; run `agent mission repair`; assert it forwards safely under strict-ancestor + clean worktree, and fails loud with a diff otherwise.

**Acceptance Scenarios**:

1. **Given** a mission with stale bookkeeping content on one partition, **When** `agent mission repair` runs and the target is a strict ancestor with a clean worktree, **Then** it fast-forwards the content with zero loss.
2. **Given** a genuinely divergent (non-ancestor) split-brain, **When** repair runs, **Then** it refuses and emits a specific diff rather than overwriting.

### Edge Cases

- A mission with no evictable runtime state (never claimed): not eligible; must NOT be flipped or fail the lock.
- A merged/archived mission carrying historical runtime: ruled explicitly (see FR-010) — the lock's eligibility is event-log-keyed, not corpus-membership-keyed.
- The self-referential cutover mission (event-sourcing itself mid-flight): excluded from the lock.
- Coord vs flat topology: the two-partition write must place `meta.json` on PRIMARY and seed events on COORD without conflating a single `feature_dir`.
- A cold upgrade (pre-3.0 → 3.2.6) where strip precedes the runtime backfill: pre-existing ordering caveat; noted, not owned here.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Whole-tree write-placement enforcement | As the framework, I want any mission-artifact write that bypasses the placement port to be rejected anywhere in `src/`, so the split-brain cannot reappear through a new unlisted writer. | High | Open |
| FR-002 | Partition-aware meta.json routing | As the framework, I want `meta.json` / `PRIMARY_METADATA` writes (`write_meta`, `_flip_phase`, `_bake_mission_number`) to resolve their partition through the placement port, so a coord/primary two-partition write is expressible. This **extends the existing port kind-mapping** (gives `PRIMARY_METADATA` a partition-aware write target); it is NOT a `MissionArtifactHome`/topology re-architecture (see C-002). | High | Open |
| FR-003 | Close the emit fork + unscanned writers | As the framework, I want the `emit` **HEAD-derived current-branch fallback** (`status_transition.py::_current_branch`, deferred #1716) closed and `bookkeeping_projection`/`bookkeeping_commit`/`decision_log` routed through the port, with `decisions.events.jsonl` classified in the partition SSOT. | High | Open |
| FR-004 | Read-side placement enforcement | As the framework, I want every mission-artifact read routed through the read-surface authority and failing loud on a partition mismatch, so reads are symmetric with writes. | Medium | Open |
| FR-005 | Repair pre-existing split-brain | As a maintainer, I want an `agent mission repair` command that detects and forward-only repairs a diverged mission (fail-loud with a diff otherwise), so an already-split corpus can be cured. | Medium | Open |
| FR-006 | Correct `traces/` classification | As the framework, I want `traces/` classified to its doctrine-correct partition (COORD) in the SSOT, with writers/readers routed accordingly. | Low | Open |
| FR-007 | Front-load the drifted corpus | As a maintainer, I want the runtime-state backfill run over the currently-drifted missions and committed, so `test_dogfood_corpus_backfilled` passes and 3.2.6 is unblocked. | High | Open |
| FR-008 | Event-source the runtime authoring | As the framework, I want **exactly two** runtime-authoring dual-writes event-sourced — the claim fields (`shell_pid`/`agent`) written to WP frontmatter, and subtask-completion written to `tasks.md` checkboxes (#2684) — so nothing un-seeded accrues. No other frontmatter/`tasks.md` authoring is in scope (see C-002). | High | Open |
| FR-009 | Birth-time runtime cutover | As the framework, I want a mission stamped `status_phase` and runtime-reconciled at land (mission-number bake hook), routed through the placement port (FR-002), so it is born reconciled. | High | Open |
| FR-010 | Event-log-keyed acceptance lock | As the framework, I want `test_dogfood_corpus_backfilled` re-keyed so every mission whose event log carries runtime (excluding the self-referential cutover mission) must be `status_phase>=1` with a non-empty snapshot, so the lock survives authoring retirement (no green-wash). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Whole-tree coverage | The write-placement enforcement scans 100% of `src/` Python modules with no module-level allowlist, except three retained sanctioned SUBTREE carve-outs (`src/mission_runtime/` — the placement port cannot be scanned by its own gate; `src/specify_cli/upgrade/migrations/` and `src/specify_cli/migration/` — one-time migration code); a synthetic bypass added to any non-carve-out module reds the gate. Per-primitive exclusions are individually justified inline; narrowing the two `migration*` subtrees to per-file entries is deferred (follow-up — see PR #2920). | Coverage | High | Open |
| NFR-002 | Fail-loud on mismatch | A read or write to the wrong partition raises a typed error; zero advisory-only mismatch paths remain for routed sites. | Correctness | High | Open |
| NFR-003 | Idempotency | The birth-cutover and the one-time backfill are idempotent: a second run seeds 0 events and leaves `status_phase` and the event log byte-identical (deterministic seed IDs namespaced on immutable `mission_id`). | Reliability | High | Open |
| NFR-004 | No write-side regression | The existing coord-trust write-side gates (`test_no_write_side_rederivation`, `test_safe_commit_import_boundary`, `test_write_surface_placement_guard`) remain green. | Reliability | High | Open |
| NFR-005 | Repair safety | `agent mission repair` forwards only under strict-ancestor + clean worktree; otherwise it fails loud with a specific diff and never force-overwrites divergent content. | Safety | High | Open |
| NFR-006 | Migration coexistence | After FR-008 retires the two authoring paths, the one-time backward-flow migration (`migrate backfill-runtime-state` / `m_zz_runtime_state_backfill`) still cuts over a legacy corpus green — its path retains a regression test. | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Phase sequence A→B | FR-009 (birth-write) depends on FR-002 (meta routing). Within Part B, FR-008 (event-source the two authoring paths) precedes FR-009 (birth-stamp) — else a flipped-but-unseeded mission recurs (the "12's shape") — and FR-010 (re-key the lock) follows FR-008. FR-007 (front-load) is independent and lands first. | Technical | High | Open |
| C-002 | Scope boundary vs #1619 | OUT: any frontmatter/`tasks.md` dual-write retirement beyond the **two paths enumerated in FR-008** (claim `shell_pid`/`agent` + subtask-completion checkboxes); topology / `MissionArtifactHome` re-architecture; growing `doctor coordination --fix` into arbitrary-drift repair (FR-005 is a distinct `agent mission repair` command per #2874 C-003); loop-friction siblings #2803/#2853. All remain #1619. | Technical | High | Open |
| C-003 | No green-wash | The lock's `verify_backfill` parity assertion is preserved or strengthened; the fix genuinely closes the drift and must not relax the predicate to pass (failing-test-remediation discipline). | Technical | High | Open |
| C-004 | Canonical single writer | The birth seam reuses `runtime_state_cutover.cutover_mission` as the sole `status_phase` writer (a 3rd call site), not a parallel writer. | Technical | Medium | Open |

### Key Entities

- **Placement port / `MissionArtifactHome`**: maps a `MissionArtifactKind` to its `read_surface` and `write_surface` (coord vs primary); the single routing authority.
- **Coord/primary partition**: coord = lifecycle surfaces (status/notes/trace/issue-matrix/acceptance-matrix); primary = planning + `meta.json`.
- **Runtime-state cutover**: `status_phase="1"` + deterministic seed events that reconcile a mission's runtime into the event log.
- **Dogfood acceptance lock**: `test_dogfood_corpus_backfilled` — the durable guard that every eligible mission is cut over.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `test_dogfood_corpus_backfilled` passes on `main` and **stays green after at least 3 subsequent mission merges** with no manual backfill (no re-drift).
- **SC-002**: A synthetic non-seam-derived mission-artifact write added to any `src/` module **outside the three sanctioned subtree carve-outs** (see NFR-001) reds the whole-tree enforcement gate (previously invisible outside the 17-module allowlist). *(FR-001, and FR-002/FR-003's now-routed writers fall under the same whole-tree gate.)*
- **SC-003**: A mission-artifact read from the wrong partition fails loud with a typed error in **100% of routed read sites** (zero silent substitutions).
- **SC-004**: `agent mission repair` detects and repairs a synthetically-injected pre-existing content split-brain forward-only with **zero data loss**, and refuses (with a diff) on genuine divergence.
- **SC-005**: A mission taken create→implement→merge lands `status_phase>=1` + `verify_backfill().ok` + non-empty snapshot with **no manual backfill invocation**.
- **SC-006**: `decisions.events.jsonl` and `traces/` are classified in the partition SSOT and route to their COORD surface via the port; the `emit` HEAD-derived fallback is removed. Verified by 0 residual unclassified mission-artifact writers in the whole-tree scan for these paths. *(FR-003, FR-006.)*

## Assumptions

- `status_phase`'s only current live effect is gating the legacy `lane` mirror (inert for new missions); the mission does not add new `status_phase` readers.
- #2874 (coord-trust) is merged and its write-side gates are the baseline to extend, not replace.
- The one-time migration (`migrate backfill-runtime-state` / `m_zz_runtime_state_backfill`) is retained for legacy/consumer-upgrade backward flow; the birth seam owns forward flow.

## Domain Language

- **Parallel / split-brain write**: a mission-artifact write that lands on (or is trusted from) the wrong partition, or on both inconsistently.
- **Birth-cutover / born-reconciled**: a mission that carries its runtime cutover (seed events + `status_phase`) at land time, without a separate migration.
- **Whack-a-read**: fixing read-partition bugs one site at a time instead of through one enforced read authority.
