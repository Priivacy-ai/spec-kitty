# Mission Specification: Read-Side Placement-Seam Migration

**Mission Branch**: `fix/read-side-placement-seam-migration`
**Created**: 2026-07-27
**Status**: Draft
**Input**: #2922 (read-side "whack-a-read", parent #1878) + #2921 (repair_lane_mismatch frontmatter corruption). The read-side twin of the write-side placement port that #2963/#2917 closed.

## Context & Background

Mission artifacts live on partitioned branches (PRIMARY = planning; COORD =
lifecycle). A read must resolve the correct partition **and artifact kind**
through a single seam: `PlacementSeam.read_dir(kind)` (`mission_runtime`), which
is kind-aware and **fail-loud** (raises `CoordinationBranchDeleted` when a coord
partition is required but its branch is gone). PR #2920 hardened that seam.

But **~60 production modules still bypass it**, calling the lower-level resolvers
directly:
- `resolve_planning_read_dir(...)` — kind-aware but **lenient** (~44 caller files):
  silently returns the primary dir where the seam would fail loud.
- `candidate_feature_dir_for_mission(...)` — **kind-blind** (~33 caller files):
  no kind discrimination at all.

This is the read-side of the split-brain the write-side already made
unrepresentable (whole-tree write gate). The write path can no longer drift; the
read path is still hardened one call site at a time. This mission (a) routes the
bypassing reads through the seam **where fail-loud is appropriate**, (b)
deliberately keeps diagnostic/audit paths lenient (classified + allow-listed,
not silently migrated), and (c) adds a **structural read-side arch gate**
symmetric to the write-side AST ratchet so new bypasses cannot land. It also
folds in the #2921 bugfix.

## Domain Language *(canonical terms)*

- **Read seam**: `PlacementSeam.read_dir(kind)` — the one kind-aware, fail-loud read authority.
- **Kind-blind bypass**: a direct call to `candidate_feature_dir_for_mission` (no kind).
- **Lenient bypass**: a direct call to `resolve_planning_read_dir` (kind-aware but never raises).
- **Fail-loud-appropriate vs must-stay-lenient**: per-call-site classification of whether routing through the seam (which can raise `CoordinationBranchDeleted`) is correct, or whether the caller is a diagnostic/audit/corpus-walk path that must tolerate half-materialized missions and therefore stays lenient by design (allow-listed with rationale).
- **Read-side gate**: a structural AST ratchet (mirror of `test_no_write_side_rederivation.py`) reusing the shared whole-tree scanner, that reds on any *new* direct kind-blind/lenient read outside the seam.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bypassing reads route through the seam with the right kind and fail-loud behavior (Priority: P1)

Each of the ~60 bypassing modules is migrated to `PlacementSeam.read_dir(kind)`
with the correct artifact kind, so a read resolves the correct partition and
fails loud when a required coord partition is missing — **except** call sites
classified must-stay-lenient, which are deliberately left on the lenient
resolver and recorded as sanctioned.

**Why this priority**: The core debt — one read authority, no silent
partition/kind drift.

**Independent Test**: For a migrated caller, a required-coord read against a
deleted coord branch raises `CoordinationBranchDeleted` (was: silent primary);
the resolved dir matches the seam for the declared kind.

**Acceptance Scenarios**:
1. **Given** a kind-aware bypass (`resolve_planning_read_dir(...,kind=K)`) classified fail-loud-appropriate, **When** migrated to `read_dir(K)`, **Then** it resolves identically for the healthy case and raises `CoordinationBranchDeleted` for the deleted-coord case.
2. **Given** a kind-blind bypass (`candidate_feature_dir_for_mission`), **When** migrated, **Then** the caller declares the correct `MissionArtifactKind` and resolves the correct partition dir.
3. **Given** resolution *infrastructure* that legitimately consumes the primitive (`surface_resolver.py`, `write_target_degrade.py`, `_read_path_resolver.py`), **When** the migration runs, **Then** it is **sanctioned** (kept as-is with recorded rationale), not migrated.

### User Story 2 - New read-side bypasses cannot land (Priority: P1)

A structural arch gate, symmetric to the write-side AST ratchet and reusing the
shared whole-tree scanner, reds when any non-sanctioned `src/` module makes a
direct kind-blind/lenient read call. Genuinely-deferred residuals sit in a
shrink-only content-descriptor allow-list with a staleness twin-guard.

**Why this priority**: Without the gate, the migration is whack-a-read — new
bypasses reappear. The gate makes the invariant enforceable.

**Independent Test**: A planted `candidate_feature_dir_for_mission(...)` call in
a fixture reds the gate; a prose/docstring mention does not; routing a listed
site forces deletion of its allow-list entry (shrink-only).

**Acceptance Scenarios**:
1. **Given** the gate, **When** a new direct kind-blind read is added to a non-sanctioned module, **Then** the gate reds.
2. **Given** an allow-list entry whose site has been routed, **When** the staleness twin-guard runs, **Then** it reds until the entry is deleted (no vacuous rule).
3. **Given** the read gate and the write gate, **When** the symmetry meta-test runs, **Then** both consume the same shared `scan_scope()`.

### User Story 3 - Diagnostic/audit paths stay lenient by design (Priority: P2)

Corpus-walk/diagnostic readers (doctor, dashboard, cutover audit, status
aggregation) that must tolerate half-materialized or broken missions are
classified must-stay-lenient and recorded as sanctioned allow-list entries with
rationale — not migrated to fail-loud (which would break audit tooling).

**Why this priority**: Prevents the migration from introducing crashes in
audit/recovery paths — a correctness regression disguised as cleanup.

**Independent Test**: A diagnostic reader still returns (does not raise) against
a deleted/half-materialized coord branch; its allow-list entry carries a
rationale.

### User Story 4 - repair_lane_mismatch no longer corrupts frontmatter (#2921) (Priority: P2)

`repair_lane_mismatch` writes a single well-formed frontmatter block with the
corrected `lane`, a clean closing fence, and the body intact — no duplicated
frontmatter, no broken delimiter.

**Why this priority**: A live corruption bug in the lane-mismatch repair path;
small, independent, file-disjoint from the read-side set.

**Independent Test**: Repair a WP file whose `lane` mismatches its directory;
the repaired file round-trips cleanly (one frontmatter block, correct lane, body
not duplicated) and passes `validate_task_metadata`.

### Edge Cases

- **Lenient→fail-loud is a behavior change**: every migrated `resolve_planning_read_dir` site can now raise `CoordinationBranchDeleted`. Each site must be classified fail-loud-appropriate vs must-stay-lenient *before* migration.
- **Kind-blind callers reading multiple kinds** from one resolved dir: the seam is per-kind; such a caller must be split or given a documented single-kind anchor.
- **Retrospective reads**: the seam special-cases `RETROSPECTIVE` → `resolve_retrospective_home`; callers reading retrospective artifacts route there, not to `resolve_artifact_surface`.
- **Primary-tree enumeration** (e.g. the Mission-E cutover files `cutover_eligibility.py`/`_cutover_doctor.py` walking `corpus.iterdir()`): a *third* read pattern that is neither a bypass nor a gate offender — explicitly declared out of scope.
- **Gate-vs-migration ordering**: the gate must land seeded-red with a shrinking allow-list (or last), or it blocks its own migration.
- **Shared-package boundary**: `src/runtime/next/runtime_bridge_identity.py` is in the `src/` walk; confirm the shared-package-boundary rules permit routing it through the seam vs public-import-only.
- **`validate_tasks.py` overlap**: appears in both the #2921 path (calls `repair_lane_mismatch`) and the #2922 read census — different concerns; coordinate line-ranges but lanes stay disjoint.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Classify every bypass call site | As a maintainer, I want each of the ~60 bypass sites classified fail-loud-appropriate vs must-stay-lenient (and infra-sanction), so migration decisions are explicit, not blind. | High | Open |
| FR-002 | Migrate fail-loud-appropriate reads to the seam | As a maintainer, I want fail-loud-appropriate callers routed through `PlacementSeam.read_dir(kind)` with the correct kind, so reads have one kind-aware authority. | High | Open |
| FR-003 | Sanction resolution infrastructure | As a maintainer, I want the read-primitive authority modules (`_read_path_resolver.py`, `surface_resolver.py`, `write_target_degrade.py`) sanctioned rather than migrated, so the seam's own implementation is not self-referentially broken. | High | Open |
| FR-004 | Keep diagnostic/audit paths lenient by design | As a maintainer, I want must-stay-lenient callers left on the lenient resolver and recorded as sanctioned allow-list entries with rationale, so audit tooling does not start crashing on half-materialized missions. | High | Open |
| FR-005 | Structural read-side arch gate | As a maintainer, I want a whole-tree AST gate that reds on any new direct kind-blind/lenient read in a non-sanctioned `src/` module, reusing the shared scanner. | High | Open |
| FR-006 | Shrink-only allow-list with staleness twin-guard | As a maintainer, I want deferred/lenient residuals in a content-descriptor allow-list (via `_ratchet_keys`) that forces entry deletion once a site is routed, so the rule never goes vacuous. | High | Open |
| FR-007 | Fix repair_lane_mismatch frontmatter corruption (#2921) | As a maintainer, I want `repair_lane_mismatch` to stop feeding raw frontmatter text into the padding slot, so repaired files are not corrupted. | Medium | Open |
| FR-008 | Route `_mission_id` to the PRIMARY leg (#2966 part-1 remainder) | As a maintainer, I want `backfill_runtime_state._mission_id` to read `meta.json` from the PRIMARY `read_dir` leg (not the COORD `feature_dir`), so deterministic seed ULIDs namespace on the mission ULID instead of the coord directory name. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No audit-path regressions | Diagnostic/audit/corpus-walk readers (doctor, dashboard, cutover audit, status aggregation) do not raise on half-materialized/deleted coord branches after the mission — verified by tests. | Reliability | High | Open |
| NFR-002 | Behavior-preserving for healthy case | For every migrated site, the resolved dir is identical to the pre-migration result in the healthy (materialized) case. | Reliability | High | Open |
| NFR-003 | Single scanner authority | The read gate reuses the shared `_placement_whole_tree_scan.scan_scope()`; it does not fork a second tree walk (asserted by a symmetry meta-test). | Maintainability | High | Open |
| NFR-004 | Gate bite + non-vacuity | The gate reds on a planted synthetic bypass and stays green on a prose mention; every allow-list entry is proven live by a staleness twin-guard. | Safety | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Reuse, do not duplicate | Migrate onto the existing `PlacementSeam`/`resolve_artifact_surface`; reuse `CoordinationBranchDeleted` (no new exception) and the shared scanner. No second read authority. | Technical | High | Open |
| C-002 | Gate lands last / seeded-red | The gate is introduced with a shrinking allow-list (or after the migration), so it never blocks its own migration. | Technical | High | Open |
| C-003 | File-scoped blanket exemptions forbidden | Use content-descriptor (site-level) allow-list entries with rationale, not a blanket file-scoped escape. | Technical | Medium | Open |
| C-004 | Scope boundary | Out of scope: write-side (done), #2966 write-target consolidation **except part-1's `_mission_id` PRIMARY-leg fix folded here as FR-008** (its `_synthesize_claim_anchor` half was already done by Mission E), #2964 terminology, and collapsing `resolve_planning_read_dir` into the seam (Directive-044 unification is separate). Primary-tree enumeration reads are out of scope. | Business | Medium | Open |
| C-005 | Lane disjointness | #2921 (`task_metadata_validation.py`) and #2922 (read-side set) are separate WPs with disjoint `owned_files`. | Technical | Medium | Open |

### Key Entities

- **PlacementSeam.read_dir(kind)** — the kind-aware, fail-loud read authority.
- **Kind-blind / lenient primitives** — `candidate_feature_dir_for_mission`, `resolve_planning_read_dir` (in `_read_path_resolver.py`).
- **Classification ledger** — per-site verdict: migrate-fail-loud / stay-lenient / sanction-infra.
- **Read-side gate + allow-list** — the AST ratchet + shrink-only content-descriptor entries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the ~60 bypass sites are classified (migrate / stay-lenient / sanction) with no un-triaged site remaining.
- **SC-002**: All fail-loud-appropriate sites route through the seam; the read gate is green with a documented, shrink-only allow-list.
- **SC-003**: A newly-added direct kind-blind read in a non-sanctioned module reds the gate (bite test).
- **SC-004**: 0 audit/diagnostic-path regressions (doctor/dashboard/cutover/status readers still tolerate half-materialized missions).
- **SC-005**: `repair_lane_mismatch` produces a clean single-frontmatter round-trip (no duplication/broken fence).

## Assumptions

- Confirmed scope (operator, 2026-07-27): #2922 read-side migration + structural read-side gate, with #2921 riding as its own WP.
- The read gate mirrors `test_no_write_side_rederivation.py` and reuses `_placement_whole_tree_scan.py` + `_ratchet_keys.py`.
- Sequencing (plan-phase detail): sanction infra self-consumers → migrate kind-aware (fail-loud-appropriate) callers → adjudicate kind-blind callers in batches → land the gate seeded-red/last. #2921 is independent and can land any time.
- The ~60-file scope is large; the plan decomposes migration into batched WPs, not one sweep.
