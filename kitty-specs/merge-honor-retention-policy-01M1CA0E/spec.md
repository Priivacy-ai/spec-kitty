# Mission Specification: Merge Honors Mission Retention Policy

**Mission Branch**: `fix/3131-merge-retention`
**Created**: 2026-08-31
**Status**: Draft
**Input**: Issue #3131 (P1, data-loss, milestone 3.2.6): `spec-kitty merge` applies default branch/worktree cleanup even when a mission requires retaining them.

## Problem Context

`spec-kitty merge`'s post-merge cleanup is driven entirely by two CLI flags —
`--delete-branch/--keep-branch` and `--remove-worktree/--keep-worktree` — both
defaulting to *delete*/*remove*. Nothing between a mission's stated intent and
the executor consults any persisted retention signal. On mission
`first-paid-checkout-01KYX0JQ` (SK-ERR-022) the accepted mission carried
constraint C-005 ("keep branches and worktrees after merge unless separately
directed"); merge nonetheless deleted all six lane worktrees, all six lane
branches, and the mission branch, with **no** preflight warning that the cleanup
contradicted the mission. The tips were reachable and reconstructed this time,
but this is a destructive **silent override** of an explicit mission-level
instruction — a data-loss defect.

The root cause is structural: a mission has **no machine-readable way** to
express "retain my branches/worktrees," so a human-authored prose constraint is
invisible to the merge machinery. This mission adds that machine-readable
authority and makes merge honor it, failing closed (retain + warn) when the
default would contradict it.

## Design Decisions (load-bearing)

### D-1 — Retention authority lives in mission `meta.json`

Three candidate authorities were evaluated:

1. **A parsed prose constraint (C-005 style)** — *Rejected.* Mission
   constraints are unstructured free prose; the only structured extraction that
   exists is requirement-ID token matching (`FR-`/`NFR-`/`C-\d+`), which
   captures the identifier, never a value or policy. Basing a data-loss-critical
   policy on regex-parsing prose is fragile, unvalidated, and violates the
   charter's "canonical sources, never improvise" rule.
2. **An explicit merge flag only** — *Rejected as the authority* (retained as
   the enforcement surface). The flags already exist but carry no persisted
   per-mission default, so a mission cannot express standing intent; the
   operator must remember to type `--keep-branch` every merge. That is exactly
   the failure mode #3131 reports.
3. **A machine-readable field in mission `meta.json`** — **Chosen.** `meta.json`
   is the single canonical per-mission policy store that merge *already reads*
   (`target_branch`, `coordination_branch`, `merged_push`, `topology`), with a
   validated single-writer API (`write_meta`) and a fail-closed reader
   (`load_meta_fail_closed`). It is minted at `mission create` and read at merge
   time. Adding `retain_branches` / `retain_worktrees` follows the exact
   precedent of `target_branch` (a merge-affecting per-mission policy resolved
   against a CLI flag with provenance).

**Single authority:** the two boolean fields `retain_branches` and
`retain_worktrees` in `meta.json` are the one canonical machine-readable
retention policy. They map 1:1 to the two existing cleanup flags, matching the
flat `meta.json` convention and keeping resolution independent per resource.

### D-2 — Fail direction: retain + warn; deletion needs an explicit override

When the cleanup default conflicts with a retention instruction, merge **fails
closed**: it **retains** the branch/worktree and emits an **operator-visible
warning**. Deletion of a mission that requests retention happens **only** when
the operator passes an explicit delete override on the command line; that
override is **recorded** as override evidence, never applied silently.

This requires distinguishing "operator explicitly chose delete" from "operator
said nothing." The cleanup flags become tri-state (unset / explicit-keep /
explicit-delete). Effective policy resolves as **explicit CLI flag > meta.json
retention > current default (delete/remove)**, mirroring
`resolve_merge_target_branch`'s precedence and `(value, source)` provenance.

### D-3 — Where the conflict is surfaced (correcting a stale doc)

The task framing and `CLAUDE.md`'s "Merge & Preflight Patterns" section assume a
merge `PreflightResult` with `.warnings`/`.errors`/`.wp_statuses` and a
`run_preflight()`. **That structure does not exist in the merge domain** — it
was removed in the #2057 merge-god-module decomposition and the doc is stale
(the only `PreflightResult` is the unrelated sync daemon-ownership preflight).
Rather than resurrect a dead structure, the retention conflict is surfaced
through the surfaces that DO exist and are already operator-visible: the
merge-gates render path and the dry-run forecast payload. The stale `CLAUDE.md`
doc is corrected in the same mission (trace the gap, don't silently work
around it).

### D-4 — Coordination topology is retained/torn-down as ONE coupled unit

The coordination branch, its worktree, and its `coordination_branch` marker in
`meta.json` are a single consistency triple, but today they are torn down by two
different gates: the marker-flatten runs under `delete_branch`
(`executor.py:1557`) and the coord-worktree destroy runs under `remove_worktree`
(`executor.py:1570`). If the two retention fields resolved *independently* for
the coordination topology, a partial retention (e.g. keep branches, remove
worktrees) would flatten the marker while destroying the worktree — or destroy
the worktree while keeping the branch — producing a half-torn `coord`-empty /
lingering-husk state that later resolves treat as corruption
(`CoordinationBranchDeleted`, the #2062 husk hazard). The retention feature must
not *manufacture* that hazard. Therefore the coordination-topology teardown is
driven by a **single coupled decision**: the coordination topology is retained
as a whole unless **both** `delete_branch` and `remove_worktree` resolve to
delete/remove; otherwise the marker, branch, and worktree are all retained
together. (Per-resource independence still applies to the *lane* branches and
*lane* worktrees, which carry no cross-consistency requirement.)

### D-5 — Read the PRIMARY partition; resolve once; fail closed on any ambiguity

Retention is a PRIMARY-partition per-mission policy exactly like `target_branch`.
The resolver reads `meta.json` from the **primary metadata dir**
(`primary_meta_dir`, `executor.py:1821`/`1849`), NOT the coord-aware STATUS dir
the locked merge driver receives (for a `coord`-topology mission that STATUS dir
is the `-coord` husk with no `meta.json`; reading retention there would find
nothing and silently fall back to delete — the exact partition trap
`resolve_merge_target_branch` was written to avoid). Resolution happens once, in
the unlocked `_run_lane_based_merge` after `resolve_mission_identity`, and the
already-resolved booleans are passed into the locked driver — so both the fresh
and `--resume` paths honor the policy exactly once, with no double-resolution.
The same pure resolver is reused by the dry-run forecast (which bypasses
`_run_lane_based_merge`). Ambiguity fails closed toward retention: a corrupt
`meta.json` aborts (typed `MissionMetaReadError`), and a present-but-non-boolean
retention value retains + warns rather than being truthiness-coerced to delete.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A retaining mission survives a default merge (Priority: P1)

An operator (or delegated agent) runs `spec-kitty merge` on a mission whose
`meta.json` declares `retain_branches: true` and `retain_worktrees: true`,
passing no cleanup flags. The merge consolidates the lanes as normal, and the
lane branches, the mission branch, and the lane worktrees **still exist**
afterward. The operator sees a warning naming the retention source.

**Why this priority**: This is the data-loss defect itself. Without it, an
explicit mission-level retention instruction is silently discarded.

**Independent Test**: Drive the real `_run_lane_based_merge` entry point on a
mission fixture whose `meta.json` sets the retention fields, with no explicit
delete override, and assert via `git branch --list` and `Path.exists()` that the
branches and worktrees survive. RED on current main; GREEN after the fix.

**Acceptance Scenarios**:

1. **Given** a mission with `retain_branches: true` / `retain_worktrees: true`
   in `meta.json`, **When** `spec-kitty merge` runs with no cleanup flags,
   **Then** all lane branches, the mission branch, and all lane worktrees remain
   present after a successful merge, and a warning is emitted naming the
   retention source.
2. **Given** the same mission (both fields true), **When** merge runs, **Then**
   the coordination branch, its worktree, and its `coordination_branch` marker
   are ALL retained together (coupled per D-4/FR-011), so no retained resource
   is half-torn-down and no later resolve sees a `coord`-empty or husk state.
3. **Given** a partial-retention mission (`retain_branches: true` only), **When**
   merge runs, **Then** lane branches are retained while lane worktrees follow
   the default, but the coordination topology is retained as a unit (the coord
   marker is NOT flattened while its worktree would be destroyed, and vice
   versa) — the coordination state is mutually consistent.

### User Story 2 - The operator can still delete, explicitly and on the record (Priority: P1)

An operator who genuinely wants to delete a retaining mission's branches passes
the explicit override. The deletion proceeds, and the override is recorded as
evidence — it is never applied silently against the mission's stated policy.

**Why this priority**: Fail-closed must not become a dead end. Deletion stays
possible, but only as a deliberate, recorded operator act.

**Independent Test**: Run merge on a retaining mission with the explicit delete
override; assert the branches are deleted AND that an override notice was
surfaced/recorded.

**Acceptance Scenarios**:

1. **Given** a mission with `retain_branches: true`, **When** merge runs with an
   explicit `--delete-branch` override, **Then** the lane/mission branches are
   deleted and an override notice is surfaced naming the contradicted policy.
2. **Given** a mission with retention set, **When** merge runs with explicit
   `--keep-branch`, **Then** branches are retained (flag agrees with policy; no
   warning needed beyond normal keep behavior).
3. **Given** a mission with `retain_worktrees: true`, **When** a started merge
   is rolled back with `spec-kitty merge --abort`, **Then** the coordination
   worktree the mission asked to keep survives the abort and a warning is
   emitted — the abort path is not a silent deletion bypass.

### User Story 3 - A mission declares retention at creation (Priority: P2)

An operator creating a mission that must preserve its workspaces declares
retention up front, so the policy is machine-readable from the start rather than
living as prose no tool reads.

**Why this priority**: Closes the loop that made #3131 possible — the observed
mission's retention lived only in prose. A create-time opt-in makes the intent
machine-readable at the moment it is decided.

**Independent Test**: Run `spec-kitty agent mission create` with the new
`--retain-branches`/`--retain-worktrees` flags; assert the resulting `meta.json`
carries the fields; run the specify interview path and assert the prompt records
the choice.

**Acceptance Scenarios**:

1. **Given** `mission create --retain-branches --retain-worktrees`, **When** the
   scaffold is written, **Then** `meta.json` contains `retain_branches: true`
   and `retain_worktrees: true`.
2. **Given** `mission create` with no retention flags, **When** the scaffold is
   written, **Then** the retention fields default to the non-retaining behavior
   (absent or `false`) so default cleanup is unchanged for missions that do not
   request retention.

### User Story 4 - The dry run forecasts the real outcome (Priority: P2)

An operator runs `spec-kitty merge --dry-run` on a retaining mission and the
forecast reflects the **resolved** cleanup decision (retain) and flags the
conflict, rather than merely echoing the default flag values.

**Why this priority**: The dry-run is the operator's pre-merge safety preview;
today it only echoes flags and cannot warn about the data loss.

**Acceptance Scenarios**:

1. **Given** a retaining mission, **When** `merge --dry-run` runs with no cleanup
   flags, **Then** the forecast payload shows `delete_branch: false` /
   `remove_worktree: false` (the resolved values) and a retention-conflict note.

### Edge Cases

- **Partial retention of LANE resources** — `retain_branches: true` but
  `retain_worktrees` unset: lane branches are retained, lane worktrees follow
  the default. The two fields resolve independently **for lane resources**,
  which have no cross-consistency requirement.
- **Partial retention and the COORDINATION topology (coupled)** — for the
  coordination branch/worktree/marker triple, the two fields do NOT resolve
  independently (see D-4). The coordination topology is retained as a unit
  unless both fields resolve to delete/remove. Concretely: `retain_branches:
  true` alone must NOT let the coord worktree be destroyed (which would strand a
  live marker → `coord`-empty), and `retain_worktrees: true` alone must NOT let
  the coord marker be flattened (which would strand a live coord worktree →
  husk). Each partial case ends in a mutually-consistent coordination state.
- **`merge --abort` on a retaining mission** — the abort-path coordination
  teardown (`_teardown_coordination_for_abort` →
  `_destroy_coordination_worktree`) honors the same resolved coordination
  retention: for a mission requesting worktree retention it skips the coord
  worktree destroy and warns, rather than silently destroying the very worktree
  the mission asked to keep.
- **Malformed retention value (readable meta)** — a retention field present but
  not a JSON boolean (`""`, `0`, `null`, `"false"`, `"true"`) MUST NOT be
  truthiness-coerced. It resolves fail-closed (retain + operator-visible warning
  naming the malformed value), never silently to delete.
- **Merge scratch worktree is NOT a retained resource** — retention covers the
  mission's lane worktrees, lane/mission branches, and coordination topology.
  The internal merge scratch worktree (`.kittify/runtime/merge/<id>/workspace`,
  removed by `cleanup_merge_workspace`) is plumbing, on a different path from
  lane worktrees; it continues to be cleaned unconditionally even under
  `retain_worktrees: true`.
- **Explicit flag agrees with policy** — operator passes `--keep-branch` on a
  retaining mission: retained, no conflict, no override notice.
- **Absent fields (legacy missions)** — `meta.json` with no retention fields
  behaves exactly as today (default cleanup). No migration is forced; absence
  means "no stated policy"; non-retaining missions never get the fields
  default-written.
- **Corrupt `meta.json`** — retention resolution uses the existing fail-closed
  reader; a corrupt `meta.json` surfaces the typed `MissionMetaReadError` and
  aborts the merge (as the target-branch resolution already does), never a
  silent fall-through to delete.
- **`--resume` path** — a resumed merge honors the same resolved retention as a
  fresh merge; resolution happens once in the unlocked driver against the
  primary partition (D-5), not in the CLI wrapper, so resume does not re-plumb
  flags around the policy.
- **Retrospective persistence** — persisting the retrospective must remain
  unconditional (it already runs at the outer command path, not only inside the
  `remove_worktree` teardown block); retaining worktrees must not strand the
  retrospective, and a later refactor must not move persistence back under the
  worktree gate.
- **Non-retaining missions** — unchanged: default cleanup stays the default;
  this mission only adds an honored opt-out.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Machine-readable retention fields in meta.json | As an operator, I want `retain_branches`/`retain_worktrees` recognized in `meta.json` so a mission can express standing retention intent that tools read. | High | Open |
| FR-002 | Merge honors retention (fail-closed) | As an operator, I want `spec-kitty merge` to retain branches/worktrees when the mission's `meta.json` requests it and no explicit delete override is given, so an explicit mission instruction is never silently overridden. | High | Open |
| FR-003 | Precedence resolver with provenance | As a maintainer, I want a resolver that computes effective cleanup as `explicit CLI flag > meta.json retention > default`, returning the value and its source, mirroring `resolve_merge_target_branch`. | High | Open |
| FR-004 | Tri-state cleanup flags | As an operator, I want the cleanup flags to distinguish "unset" from "explicit keep"/"explicit delete" so my explicit choice overrides mission policy while silence lets policy win. | High | Open |
| FR-005 | Operator-visible retention warning | As an operator, I want a visible warning when retention causes cleanup to be skipped, naming the source (`meta.json`), so the retention is transparent, not hidden. | High | Open |
| FR-006 | Recorded explicit-override notice | As an operator, I want an explicit delete override against a retaining mission to surface an override notice and be recorded as evidence, so deletion of a retaining mission is never silent. | High | Open |
| FR-007 | Resume honors retention | As an operator, I want a `--resume`d merge to honor the same resolved retention as a fresh merge, so an interrupted merge cannot lose retained resources. | Medium | Open |
| FR-008 | Dry-run forecasts resolved cleanup | As an operator, I want `merge --dry-run` to report the resolved cleanup decision and flag any retention conflict, not just echo flag defaults. | Medium | Open |
| FR-009 | Create-time retention opt-in | As an operator, I want `mission create --retain-branches/--retain-worktrees` (and a specify-interview prompt) to mint the retention fields into `meta.json` at creation. | Medium | Open |
| FR-010 | Non-retaining missions unchanged | As an operator of a mission that does not request retention, I want default cleanup behavior to remain exactly as before, so this change is a pure additive opt-out. | High | Open |
| FR-011 | Coordination topology coupled teardown | As an operator, I want the coordination branch/worktree/marker torn down or retained as one unit (retained unless both fields resolve to delete/remove), so partial retention never leaves a half-torn `coord`-empty or lingering-husk state. | High | Open |
| FR-012 | Abort path honors retention | As an operator, I want `spec-kitty merge --abort` on a retaining mission to skip destroying the coordination worktree it asked to keep (and warn), so the abort/rollback path is not a silent deletion bypass. | High | Open |
| FR-013 | Merge scratch worktree stays ungated | As a maintainer, I want retention to explicitly NOT gate `cleanup_merge_workspace`, so the internal merge scratch worktree is still cleaned even under `retain_worktrees: true` (no leaked registered worktree). | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Fail-closed on ambiguity | When retention intent cannot be safely determined, merge fails closed toward retention: a corrupt `meta.json` aborts with a typed error and non-zero exit; a present-but-non-boolean retention value retains + warns. Never truthiness-coerced to delete. 100% of corrupt-meta cases abort and 100% of malformed-value cases (`""`, `0`, `null`, `"false"`) retain. | Reliability | High | Open |
| NFR-002 | Red-first regression proof (non-vacuous) | An issue-pinned regression asserts, through the real `spec-kitty merge` entry point on a `coord`-topology retaining mission with NO cleanup flags, that the mission branch and a NON-planning lane branch/worktree (resources main actually deletes) SURVIVE — asserting on `.worktrees/<slug>-<mid8>-lane-<id>` paths, explicitly NOT the merge scratch worktree. RED on current main, GREEN after the fix. | Reliability | High | Open |
| NFR-003 | No silent deletion path (all cleanup paths) | Across BOTH the success cleanup phase and the `--abort` teardown, no code path deletes a lane/mission branch, lane worktree, or coordination worktree of a retaining mission without either an explicit operator override (recorded) or an emitted warning. Enforced by a regression a silent-override path can never pass green. | Reliability | High | Open |
| NFR-004 | Type & lint clean | New code passes `ruff` and `mypy --strict` with zero new issues; functions stay ≤15 cyclomatic complexity. | Maintainability | Medium | Open |
| NFR-005 | Targeted test surface | Validation targets `tests/merge/`, `tests/integration/test_merge_lane_planning_data_loss.py`, and mission-creation/meta tests; full suite reserved for post-merge sweep. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Do not touch consolidation algorithm | The lane-consolidation / conflict-resolution algorithm is out of scope; only post-merge cleanup policy and its preflight/forecast change. | Technical | High | Open |
| C-002 | Single authority, no config tier | `meta.json` retention fields are the single machine-readable authority; do not add a second authority (no prose-parsing, no project-level `config.yaml` retention default). Precedence is exactly `explicit CLI flag > meta.json retention > default`. A project-level default is deferred to a separate mission, not adopted here. | Technical | High | Open |
| C-003 | Canonical sources only | Follow the `resolve_merge_target_branch` precedent and `write_meta`/`load_meta_fail_closed` APIs; add `retain_branches: bool`/`retain_worktrees: bool` as flat fields on `MissionMetaOptional`; do not hand-roll meta I/O or a parallel resolver, and do not introduce a nested `retention` block. | Technical | High | Open |
| C-004 | Terminology canon + retain⇔keep mapping | Use `Mission`, `retain`/`retention`; add no `feature*` aliases; new flags use canonical naming. Do NOT rename the long-standing merge flags (`--keep-branch`/`--delete-branch`, `--keep-worktree`/`--remove-worktree`); document that `retain_branches` resolves to effective `--keep-branch` and `retain_worktrees` to effective `--keep-worktree`. | Business | Medium | Open |
| C-005 | Correct the stale preflight doc | The `CLAUDE.md` "Merge & Preflight Patterns" `PreflightResult`/`run_preflight`/`WPStatus` description is stale and must be corrected as part of this mission, not relied upon. | Technical | Medium | Open |
| C-006 | Retention scope excludes merge scratch worktree | Retention covers lane worktrees, lane/mission branches, and coordination topology only. `cleanup_merge_workspace` (the internal `.kittify/runtime/merge/<id>/workspace` scratch worktree) is out of scope and continues to run unconditionally; retention MUST NOT gate it. | Technical | Medium | Open |
| C-007 | Second merge entry audited | `orchestrator_api/commands.py` merge entry (`~:569`) hard-codes cleanup intent and is a latent second bypass of the new policy; it must be audited and either routed through the resolver or explicitly documented as out of scope with rationale. | Technical | Medium | Open |

### Key Entities

- **Retention policy**: the pair (`retain_branches`, `retain_worktrees`) — a
  per-mission, machine-readable declaration persisted in `meta.json` that merge
  reads to decide post-merge cleanup.
- **Effective cleanup decision**: the resolved (`delete_branch`,
  `remove_worktree`) booleans plus provenance (`source ∈ {cli, meta, default}`),
  computed by the retention resolver and consumed by the executor cleanup phase.
- **Override evidence**: the record emitted when an explicit CLI delete override
  contradicts a mission's retention policy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A `coord`-topology mission declaring retention in `meta.json`
  retains 100% of its non-planning lane branches, mission branch, lane
  worktrees, and coordination topology through a default `spec-kitty merge`
  (verified by the red-first regression through the real entry point, asserting
  on lane-worktree paths not the merge scratch worktree).
- **SC-002**: Zero silent deletions of a retaining mission's resources across
  BOTH the success cleanup and the `--abort` teardown: every deletion is
  preceded by either an explicit recorded operator override or a visible
  retention warning (verified by regressions on both paths that no silent path
  passes green).
- **SC-003**: `spec-kitty merge --dry-run` on a retaining mission reports the
  resolved retain decision and a conflict note in 100% of cases (no
  flag-echo-only output).
- **SC-004**: Missions that do not request retention exhibit byte-identical
  cleanup behavior to before the change (existing merge cleanup tests stay
  green unchanged).
