# Partition-Aware Implement-Claim Precondition

**Mission**: `implement-claim-precondition-partition-01KXGWSP`
**Type**: software-dev · **Kind**: Bug · **Priority**: P1 · **Milestone**: 3.2.x
**Tracker**: fixes [#2533](https://github.com/Priivacy-ai/spec-kitty/issues/2533) · parent epic [#2624](https://github.com/Priivacy-ai/spec-kitty/issues/2624) · cross-linked [#2160](https://github.com/Priivacy-ai/spec-kitty/issues/2160)

## Purpose

When a solo, pull-request-bound mission runs on its own feature branch, an agent
cannot claim a work package: `spec-kitty agent action implement WP##` aborts with
**"Planning artifacts not committed"** even though the spec, plan, and tasks are
already committed on that feature branch. The operator's only workaround is to
hand-edit `meta.json` (flatten the mission) or force-stage files onto the wrong
branch. This mission removes that blocker by making the claim precondition aware
of **where each planning artifact actually lives**, so PR-bound missions can move
from planning into implementation without manual git surgery.

This is the **write/claim-side twin** of the already-shipped read-side fix
(WP08, commit `52211737b`, which routed the empty-coord *status surface* cleanly
to primary). The read resolver now treats a solo coord mission's surface as
PRIMARY; the claim precondition has not yet been reconciled with the same
kind-based artifact partition, and that inconsistency is the defect.

## Background & Domain Model

Artifact placement is **kind-based**, defined in one authority
(`src/mission_runtime/artifacts.py`):

- **PRIMARY kinds** — `spec.md`, `plan.md`, `tasks.md`, `tasks/WP*.md`,
  `data-model.md`, `research.md`, checklists, `lanes.json`, `meta.json`,
  retrospective — author, read, and commit on the **primary target branch for
  every topology**. They never transit coordination.
- **COORD kinds** — `status.events.jsonl`, `status.json`, `acceptance-matrix`,
  `issue-matrix`, `analysis-report` — route to the **coordination branch** under
  coord / lanes-with-coord topologies.

The defect is a single-ref conflation (`C-PLACE-1`): the implement-claim
precondition compares **every** feature-directory file against **one** collapsed
ref — the *coordination* branch — for its idempotency check. Because PRIMARY
planning artifacts live on the feature branch and are absent on the coordination
branch, they all read as "changed", the staging set is non-empty, and the claim
aborts. The write path (`commit_router`) and the read resolver (`surface_resolver`,
WP08) already honor the per-kind partition; the claim precondition is the lone
remaining consumer on the collapsed single ref.

## Domain Language

| Canonical term | Meaning | Avoid |
|----------------|---------|-------|
| PRIMARY partition | Artifact kinds that live on the primary/target branch for every topology | "feature files" (ambiguous) |
| COORD partition | Artifact kinds that route to the coordination branch | "shared files" |
| Placement ref | The `CommitTarget` an artifact resolves to for commit/diff | "the branch" (which branch?) |
| Topology derivation | How a mission is classified `single_branch` / `lanes` / `coord` / `lanes_with_coord` | conflating with placement |

## User Scenarios & Testing

**Primary actor**: an implementing agent (or the operator) claiming a work
package during the implement loop.

### Acceptance Scenarios

1. **Solo PR-bound coord mission — claim succeeds.**
   *Given* a solo PR-bound mission with `topology: coord` whose `spec.md`,
   `plan.md`, `tasks.md`, and `lanes.json` are committed on the feature/target
   branch (and absent on the empty coordination branch),
   *When* an agent runs `spec-kitty agent action implement WP01`,
   *Then* the claim proceeds, no "Planning artifacts not committed" message is
   emitted, no manual `git add -f` is required, and the mission topology is
   unchanged.

2. **Coord-with-lanes mission — no coordination regression.**
   *Given* a `lanes_with_coord` mission,
   *When* the claim precondition runs,
   *Then* COORD-partition artifacts (`status.events.jsonl`, `status.json`,
   matrices, analysis report) are still compared against and routed to the
   coordination ref, exactly as before.

3. **Move-task staging — unchanged.**
   *Given* the move-task path that reuses the shared staging core,
   *When* it stages planning artifacts,
   *Then* its behavior is unchanged (guarded by a test-only regression).

4. **Write-side: dirty PRIMARY on coord lands on primary.**
   *Given* a coord mission with a genuinely-dirty PRIMARY artifact (e.g. `spec.md`)
   that must be committed,
   *When* the planning-artifact commit runs,
   *Then* the PRIMARY artifact is committed to the primary/target ref (never the
   coordination branch), while a dirty COORD status file still commits to the coord ref.

### Edge Cases

- A PRIMARY artifact with genuine uncommitted working-tree changes on the
  feature branch is still correctly detected as needing a commit (the fix must
  not blind the check — it must compare against the *correct* ref, not skip it).
- A flattened mission (`coordination_branch` removed) continues to work (the
  precondition short-circuits when the mission does not route through
  coordination).

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The implement-claim precondition MUST classify each candidate planning artifact by its canonical kind and compare it against the ref for that kind's partition — PRIMARY kinds against the primary/target branch, COORD kinds against the coordination ref — instead of comparing all files against a single collapsed coordination ref. | Planned |
| FR-002 | For a solo PR-bound `coord`-topology mission whose `spec.md`/`plan.md`/`tasks.md`/`tasks/WP*.md`/`lanes.json` are committed on the feature/target branch, `spec-kitty agent action implement WP##` MUST succeed: no "Planning artifacts not committed" abort and no manual staging instruction. | Planned |
| FR-003 | The write-side commit path that persists any residual planning-artifact changes MUST route PRIMARY kinds to the primary/target ref and never onto the coordination branch (the write-side twin of the comparison fix). | Planned |
| FR-004 | The defect MUST be reproduced by a red-first regression exercised through the pre-existing precondition entry point (`_ensure_planning_artifacts_committed_git`, reached via `agent action implement`): the test asserts a non-empty planning-artifact staging set before the fix and an empty one after, with topology unchanged. | Planned |
| FR-005 | The move-task planning-artifact staging path that reuses the same staging core MUST retain correct behavior, guarded by a focused (test-only) regression. | Planned |
| FR-006 | Architecture documentation that still describes the retired single-ref placement model (`docs/architecture/branch-target-routing.md`, `docs/architecture/execution-lanes.md` See-Also) MUST be corrected to the kind-based partition. | Planned |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The fix MUST NOT alter mission topology derivation. | The existing test `test_create_pr_bound_on_non_primary_branch_still_defaults_to_coord` remains green and unmodified; no change under `mission_create.py`. | Planned |
| NFR-002 | No regression to coordination-routed artifacts. | A regression test for a `lanes_with_coord` mission passes; status/matrix/analysis artifacts still diff against and commit to the coordination ref. | Planned |
| NFR-003 | New and changed code meets the repo quality bar. | `ruff` and `mypy --strict` report zero new issues; each touched function has cyclomatic complexity ≤ 15; every new branch/helper has a focused test in the same change. | Planned |
| NFR-004 | The fix reuses the single per-kind partition authority. | No new artifact-kind→partition mapping literal is introduced outside `src/mission_runtime/artifacts.py`; classification goes through `kind_for_mission_file` / `is_primary_artifact_kind`. | Planned |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Boundary guard: `_resolve_claim_commit_target` and status-event placement MUST remain coord-targeted. Only the planning-artifact comparison/destination is corrected; the planning→primary / status→coord asymmetry is preserved. | Active |
| C-002 | Boundary guard: the single-ref placement mint (`_assemble_artifact_placement_fragment` / `ArtifactPlacementFragment`, `mission_runtime/*`) MUST NOT be modified. The fix lives in the consumer (implement-claim). `mission_runtime/*` stays read-only for this mission. | Active |
| C-003 | Out of scope: the `pr_bound ⇒ coord` topology derivation (`mission_create.py:216-217`) — owned by [#2602](https://github.com/Priivacy-ai/spec-kitty/issues/2602). | Active |
| C-004 | Deferred (record as a follow-up per Directive 003; do NOT implement here): retiring the bespoke `resolve_planning_artifact_staging` path into `commit_router.commit_for_mission`, and correcting the now-false `C-PLACE-1` docstring — owned by the [#2160](https://github.com/Priivacy-ai/spec-kitty/issues/2160) placement-seam SSOT cluster. | Active |
| C-005 | This mission itself runs under **LANES** topology, coord-free (single primary ref for its own artifacts). | Active |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A dogfooding PR-bound mission can claim and implement a work package end-to-end with zero manual git intervention. |
| SC-002 | Zero occurrences of the false "Planning artifacts not committed" abort across the reproduction scenarios. |
| SC-003 | The new red-first regression fails before the change and passes after; the existing implement, move-task, and coordination test suites remain green. |
| SC-004 | Architecture docs describe only the kind-based partition — no reader can find the retired single-ref placement claim. |

## Key Entities

- **MissionArtifactKind partition** — the PRIMARY vs COORD split in
  `mission_runtime/artifacts.py`; the single authority the fix consumes.
- **Placement ref (`CommitTarget`)** — the branch an artifact resolves to for
  commit/diff; PRIMARY → target branch, COORD → coordination branch.
- **Implement-claim precondition** — the gate
  (`_ensure_planning_artifacts_committed_git` → `resolve_planning_artifact_staging`
  → `_files_changed_vs_ref`) that this mission makes partition-aware.

## Assumptions

- The per-kind partition sets in `mission_runtime/artifacts.py` are correct and
  authoritative; this mission consumes them rather than redefining any mapping.
- WP08 (`52211737b`) has landed on the base branch, so the read-side surface fix
  is present and only the write/claim side remains inconsistent.
- The mission lands via a manually opened pull request at completion (operator
  merges); the mission is intentionally created coord-free to avoid the very
  topology it fixes.

## Out of Scope / Deferred

- **Out of scope** — changing the `pr_bound ⇒ coord` topology derivation (#2602).
- **Deferred follow-up** (to be filed, not implemented) — consolidating the
  implement-claim staging onto `commit_router.commit_for_mission` and fixing the
  false `C-PLACE-1` docstring (#2160 cluster).
