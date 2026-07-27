# Mission Specification: Reliability Papercut Sweep

**Mission ID**: 01KWD0V560PCDYFGXYY8WNNJH0
**Slug**: reliability-papercut-sweep-01KWD0V5
**Type**: software-dev (bug-fix)
**Status**: Draft
**Parent epic**: #1878 (coordination placement / identity strangler)

## Purpose

Catfooding and PR review surfaced a cluster of small but real reliability defects in the
operator-facing workflow: a dirty-tree gate that blocks on unrelated debris, coordination
tooling that misclassifies a never-created branch and recommends recovery that cannot run,
and identity/branch resolvers that silently fall back to a slug or the default branch
instead of failing closed. Individually minor, together they erode operator trust. This
mission fixes six such issues in two cohesive lanes, each defect carrying a standing
regression test, while preserving the canonical-surface invariants the surface-resolution
and identity stranglers established.

## Scope

Closes eight issues across two lanes:

- **Lane A — operator coord/gate papercuts**: #2251, #2250, #2240, #2274, #2275
- **Lane B — identity / surface-resolution residuals**: #2138, #2139, #2091

(#2274 + #2275 folded after a post-tasks investigation — same coord/gate authority-split-brain
family, fixed fail-closed with red-first regressions, no ownership collision. #2267 was
considered and kept SEPARATE: it is a retrospect-classifier signal-quality bug in a distinct
subsystem, not a coord/gate authority defect.)

Out of scope (deferred / separate): #2157 (charter-gate prerequisite aggregation + freshness
deadlock — standalone, under #1619); the full long-term collapse of `target_branch` readers
beyond the fail-closed correctness fix is captured under #2139 here but its broader
architectural unification remains a follow-on if it proves larger than the adapter shape.

## User Scenarios & Testing

### Scenario 1 — record analysis with unrelated debris present (#2251)
- **Actor**: an operator (or agent) recording a mission analysis report.
- **Trigger**: `record-analysis` runs while the only dirty path is an unrelated orphan
  `kitty-ops/<ulid>.jsonl` Op record (self-bookkeeping debris), not mission-relevant dirt.
- **Happy path**: the command records the analysis; the orphan is recognized as
  self-bookkeeping and excluded from the dirty-tree gate.
- **Exception today**: it hard-fails with `DIRTY_WORKTREE`, pushing the operator toward
  `git stash`, which then reverts uncommitted work elsewhere — detonating Scenario 2.

### Scenario 2 — checkout of a flat mission whose coord branch was never created (#2250, #2240)
- **Actor**: an operator resuming a flat mission (authored directly on the target branch)
  whose `meta.json` declares a `coordination_branch` that was never materialized.
- **Trigger**: `context resolve` / `doctor coordination` / `doctor topology`.
- **Happy path**: tooling recognizes the declared-but-absent branch, leads the remediation
  with "flatten the mission", and recommends only commands that exist and perform the stated
  recovery.
- **Exception today**: hard-fails `COORDINATION_BRANCH_DELETED`; the topology classifier
  treats the absent branch as a healthy `coord` mission; and `doctor coordination` recommends
  a recovery path that does not recreate the worktree (a recurrence of the #1890 class).

### Scenario 3 — decision event written for a flat / un-backfilled mission (#2138, #2091)
- **Actor**: the runtime persisting a decision event.
- **Trigger**: a decision is logged for a mission reached via the flat / coord-less path,
  or a coordination branch is composed with an empty mid8.
- **Happy path**: the persisted `mission_id` is the canonical ULID (sourced from meta or
  minted once at the canonical boundary); a missing identity fails closed with a structured
  error.
- **Exception today**: the slug is silently substituted into the canonical `mission_id`
  field, corrupting the persisted identity of every decision event on that path.

### Scenario 4 — merge target resolved when meta read fails (#2139)
- **Actor**: the merge / branch-resolution path.
- **Trigger**: a coordination mission's `meta.json` is present but unreadable (corrupt JSON)
  or the `target_branch` field is absent.
- **Happy path**: a *field-absent* read returns the documented default; a *read-failure*
  surfaces a structured error (fail closed) rather than silently targeting the default branch.
- **Exception today**: all three readers silently fall back to the repository default
  (`main`) on read failure, so a mission can merge to the wrong branch with exit 0, no signal.

### Edge cases
- An orphan `kitty-ops/<ulid>.jsonl` AND genuine mission dirt both present → gate still blocks
  on the genuine dirt, excludes only the self-bookkeeping orphan.
- A coord mission whose branch *was* created then torn down vs *never* created — both lead with
  a safe remediation; the mission does not claim reflog-grade provenance it cannot prove.
- A flat mission that legitimately carries a ULID in meta but reaches `decision_log` via a
  legacy caller → sources the real ULID, does not regress to fail-closed-on-valid-data.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `record-analysis`'s dirty-tree preflight MUST treat an orphan `kitty-ops/<ulid>.jsonl` Op record as self-bookkeeping and exclude it from `DIRTY_WORKTREE`, while still blocking on genuine mission-relevant dirt. (#2251) | Draft |
| FR-002 | Coordination resolution MUST NOT classify a declared-but-never-created `coordination_branch` as a healthy `coord` topology, and its remediation MUST lead with "flatten the mission" for that state. The git-existence check lives at the backfill/resolver boundary. (#2250) | Draft |
| FR-003 | `doctor coordination` MUST recommend only recovery commands that exist and perform the stated recovery, and MUST handle a stale-behind-tip coordination worktree; a standing regression test MUST guard against recurrence of the #1890 dead-command class. (#2240) | Draft |
| FR-004 | The decision-event payload MUST persist a canonical ULID in `mission_id`; both fallback sites (`decision_log` and `runtime_bridge._resolve_mission_ulid`) MUST fail closed when no ULID is available; the flat / coord-less path MUST source a real ULID from meta (or mint) rather than substituting the slug. (#2138) | Draft |
| FR-005 | `target_branch` resolution MUST distinguish a field-absent read (documented default) from a read failure (structured error, no silent default-branch fallback), routed through one canonical read primitive with the existing readers reduced to thin adapters over it (call sites unchanged). (#2139) | Draft |
| FR-006 | A coordination-branch identity MUST be minted once at the canonical boundary; an empty-mid8 / malformed coordination branch MUST be prevented or fail closed rather than persisted. (#2091) | Draft |
| FR-007 | The lane-hygiene `kitty-specs`-on-lane guard MUST compare by **content** against the planning-branch tip, not by commit-history/merge-base diff, so a `kitty-specs/` file byte-identical to the planning tip is NOT flagged after a legitimate planning-branch rebase (no false-positive `--force`). (#2274) | Draft |
| FR-008 | `move-task --to approved` over a coord-latest `rejected` review artifact MUST persist an approved review-cycle artifact (or honored override) in the **coordination** worktree where the merge gate reads — so a genuinely-approved terminal WP is not blocked by `REJECTED_REVIEW_ARTIFACT_CONFLICT`. (#2275) | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Every fixed defect carries a standing regression test that fails on pre-fix code and passes after, exercised through the pre-existing operator entry point. | 8/8 issues have a red-first regression test | Draft |
| NFR-002 | No new silent fallback is introduced; identity and branch read failures surface a structured error or an explicitly logged default. | 0 silent slug-as-mission_id or silent default-branch substitutions on read failure | Draft |
| NFR-003 | New and boy-scout-touched code passes lint and type checks with zero issues, and stays within the complexity ceiling. | ruff + mypy clean; cyclomatic complexity ≤ 15 on touched functions | Draft |
| NFR-004 | The two lanes remain parallelizable by disjoint file ownership; intra-lane collisions are sequenced. | Lane A and Lane B edit disjoint files; #2250→#2240 sequenced within Lane A | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | `classify_topology` remains a pure `(str\|None, bool) → MissionTopology` mapper. Git-existence probing MUST be added at the backfill / surface-resolver boundary, NOT in the topology SSOT (it has 8 consumers; polluting it would ripple into `resolution.py` / `runtime_bridge` and collide across lanes). **Binding.** | Draft |
| C-002 | Within Lane A, #2250 and #2240 share `_coordination_doctor.py` and the recovery-hint surface; their work packages MUST be sequenced (#2250 → #2240), not run concurrently. Lane B (#2138/#2139 vs #2091) is file-disjoint. | Draft |
| C-003 | The stale `test_slug_fallback_when_no_mission_id` (which asserts the #2138 bug as correct) MUST be inverted, not preserved; the two doctor-hint tests (`test_doctor_coordination.py`, `test_doctor_cli_surface_golden.py`) MUST be re-pinned in the same change; the healthy self-bookkeeping-allowlist and orchestrator-merge-target tests MUST be extended, not replaced. | Draft |
| C-004 | Established precedent (#2102 dirty-tree allowlist, #1890 doctor-hint, #2219 backfill-topology, #2136 canonical handle, #2065 surface-resolver) is cited and reused; this mission does not re-fold their already-closed scope. | Draft |
| C-005 | #2139 keeps the three `target_branch` readers as thin adapters over the shared primitive — call sites are unchanged. This is NOT a bulk identifier rename. | Draft |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | An operator with only unrelated `kitty-ops` debris records an analysis report without a false dirty-tree block. |
| SC-002 | An operator on a flat mission with a never-created coordination branch receives a remediation that resolves the state on the first suggested action (lead-with-flatten), not a misleading multi-step chain. |
| SC-003 | Every recovery command `doctor coordination` recommends exists and performs the recovery it promises. |
| SC-004 | 100% of persisted decision-event `mission_id` values are canonical ULIDs; none is a slug. |
| SC-005 | A mission whose meta read fails never silently merges to the default branch — it surfaces an explicit error or logged default. |
| SC-006 | All eight issues have a regression test demonstrated red on pre-fix code and green after the fix. |
| SC-007 | A `kitty-specs/` file byte-identical to the planning tip is not flagged by the lane-hygiene guard after a planning-branch rebase (zero false-positive `--force`). |
| SC-008 | An approved-over-rejected terminal WP merges without `REJECTED_REVIEW_ARTIFACT_CONFLICT` (the coord worktree holds the approved/override artifact). |

## Key Entities

- **Self-bookkeeping path**: a repo path the dirty-tree gate treats as non-blocking debris
  (e.g. `meta.json`, encoding-provenance log, and — newly — `kitty-ops/<ulid>.jsonl`).
- **MissionTopology**: the `coord` / `single_branch` classification produced by the pure
  `classify_topology` SSOT from `(coordination_branch, has_coord)`.
- **Canonical mission identity**: the ULID `mission_id` (and its `mid8` prefix); the only
  runtime identity. The slug is a human handle, never persisted as `mission_id`.
- **target_branch read primitive**: the single canonical reader of `target_branch` from
  primary meta, distinguishing field-absent from read-failure.

## Assumptions

- "Never created" vs "torn down" coordination branches are not always distinguishable without
  reflog; #2250 scopes to "lead remediation with flatten + stop mis-classifying", not a
  reflog-grade provenance distinction.
- #2139's correctness fix (fail-closed primitive + thin adapters) is the committed scope; if
  converging the readers proves materially larger than the adapter shape, the residual
  unification is a tracked follow-on, not silently expanded here.
- Per-issue code-state, sizing, the C-001 cross-lane constraint, and the C-002 sequencing were
  verified by a pre-flight investigation + campsite/undersizing squad before this spec.
