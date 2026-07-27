# Mission Specification: Coord/Primary Partition Regression Lock

**Mission slug**: `coord-primary-partition-lock-01KWZ46V`
**Mission ID**: `01KWZ46VKW8D26H9WB940FH5PS`
**Mission type**: software-dev
**Status**: Draft (post-squad remediation)
**Roadmap**: 3.2.x · G2 (core-domain SSOT strangling) — the **placement-routing slice** of the #1878 write-side strangler
**Tracker**: reframes/closes #1716 · folds #2091, #2250 · authoritative over the #2160 sibling cluster on the shared placement seam · under #1619

> **Post-squad note.** A three-lens scope-check squad (architect-alphonso, paula-patterns,
> planner-priti) established that the placement **SSOT and its ratchet already exist**.
> This mission therefore **completes and locks** that SSOT — it does not build a parallel
> one — and, per operator decision, is **authoritative** over sibling missions where they
> touch the same seam/ratchet substrate (they rebase onto this). Evidence trail:
> `kitty-specs/coord-primary-partition-lock-01KWZ46V/research/` (squad findings, added at plan).

## Purpose (stakeholder-facing)

**TL;DR**: Make one topology-aware API the single place that decides where every
mission artifact is stored and read, route every remaining site through it, and
lock it against regression.

Mission artifacts are split across a **coordination branch** (lifecycle/bookkeeping)
and the **primary branch** (stable planning); no-coordination missions keep
everything on primary. A single topology-aware placement authority already exists
and the read side is ~90% routed through it, but several **write** sites — most
critically the one that commits the spec at `mission create` — still derive their
destination from the current checkout or inline topology guesses, which produces
create-time split-brain and misleading coordination errors that block operators
mid-mission. This mission routes **every** remaining read and write through the
single seam — even when the answer is "primary" — extends the existing
architectural ratchet to catch the grammar those bypasses use, and locks the
behaviour with an end-to-end regression test, so future work cannot reintroduce
the split.

## Context & Motivation

Issue #1716 originally proposed the *opposite* architecture (materialize the
coordination worktree at `mission create`; route planning writes to the
coordination branch). That "Locked Architecture Decision" was **superseded** by
PRs #2106 / #2113, which established the canonical partition below. This mission
**ratifies and locks** the shipped decision — it does not change which partition
an artifact kind belongs to.

**Canonical partition (binding, operator-confirmed):**

| Partition | Surface | Artifact kinds (the SSOT is the frozenset, see FR-002) |
|-----------|---------|--------------------------------------------------------|
| Coordination / lifecycle | coordination branch, under a coordination-routing topology | `STATUS_STATE`, `LANE_STATE`, `ACCEPTANCE_MATRIX`, `ANALYSIS_REPORT`, and self-bookkeeping (status transitions, move-task) |
| Stable planning | primary (target) branch | `SPEC`, `PLAN`, `TASKS_INDEX`, `WORK_PACKAGE_TASK`, `DATA_MODEL`, `RESEARCH`, `CHECKLIST`, `RETROSPECTIVE`, `PRIMARY_METADATA` |
| No-coordination topology | primary | **all** kinds |

**The existing SSOT this mission completes and locks:**

- **Kind → partition**: `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` and
  `artifact_home_for()` / `MissionArtifactHome` (`src/mission_runtime/artifacts.py:91,113,175`).
- **Placement derivation root**: `resolve_action_context` / `_assemble_artifact_placement_fragment`
  (`src/mission_runtime/resolution.py`), surfaced for writes as
  `resolve_placement_only(...) -> CommitTarget` (`resolution.py:1130`).
- **Read seam**: `resolve_planning_read_dir` / `resolve_mission_read_path` /
  `resolve_handle_to_read_path` (`src/specify_cli/missions/_read_path_resolver.py`)
  and the coordination-read authority `resolve_status_surface`
  (`src/specify_cli/coordination/surface_resolver.py:572`).
- **Topology model**: `MissionTopology` is a 2×2 grid — `SINGLE_BRANCH`, `LANES`,
  `COORD`, `LANES_WITH_COORD` — and coord-routing is the predicate
  `routes_through_coordination(topology)` over `{COORD, LANES_WITH_COORD}`
  (`src/mission_runtime/context.py:64-134`). `FLATTENED` is a provenance flag, not
  a topology value.
- **Ratchet**: `tests/architectural/test_no_write_side_rederivation.py` (adopted-module
  set + write-side line allow-list) and `tests/architectural/resolution_gate_allowlist.yaml`
  / `test_resolution_authority_gates.py` (baseline scalars).

The failures this mission removes are symptoms of write sites **not** consulting
the seam: the create-time split-brain root at `core/mission_creation.py:176`
(`_commit_feature_file` commits the spec via `CommitTarget(ref=current_branch)`),
a malformed coordination branch composed from an empty `mid8` (#2091), and a
misleading `COORDINATION_BRANCH_DELETED` on a mission that never had a
coordination branch (#2250).

## Domain Language

| Term | Canonical meaning | Avoid |
|------|-------------------|-------|
| Placement seam | The single authority answering "where do I write/read artifact kind K under topology T?" — the public face of `resolve_action_context`, exposing `write_target(kind)` and `read_dir(kind)`, classified by `artifact_home_for` / `MissionArtifactHome` | "the resolver" (there are several leaf resolvers; the seam is the one authority they delegate to) |
| Topology | `MissionTopology`: the 2×2 grid `SINGLE_BRANCH` / `LANES` / `COORD` / `LANES_WITH_COORD` | binary "coord vs single_branch" |
| Coord-routing predicate | `routes_through_coordination(topology)` over `{COORD, LANES_WITH_COORD}` — the ONLY sanctioned test for "does this topology use the coordination surface" | inline `topology == COORD`, `coordination_branch is not None` |
| Stored topology | The topology recorded in `meta.json` — the authoritative input to placement | the on-disk `-coord` worktree husk |
| Artifact kind | A `MissionArtifactKind` enum member whose partition is fixed by the two frozensets | free-form "file type" |
| `MissionArtifactHome` | The value object carrying `read_surface` + `write_surface` + `commit_target` for a `(kind, placement)` — the canonical partition output | re-deriving placement per call site |
| Coordination surface / Primary surface | The two physical destinations a placement decision selects between | "main" (the primary is not always `main`) |

## User Scenarios & Testing

### Primary — one authority from any working directory

1. A maintainer runs `mission create` for a coordination-routing mission, writes and
   commits a substantive `spec.md`.
2. They run `setup-plan`, then `agent tasks status`, then `agent decision verify`.
3. Every command resolves the same partition-correct authority through the seam:
   planning kinds → **primary**; lifecycle kinds → **coordination**.
4. The maintainer runs the same reads from an **unrelated CWD** and gets identical
   results.

### Primary — no-coordination mission

1. A maintainer runs a `SINGLE_BRANCH` or `LANES` mission.
2. Every kind — planning and lifecycle — resolves to **primary** through the same
   seam (via `routes_through_coordination` returning false), not a special-case bypass.

### Mutation through the seam (added post-squad)

1. A lifecycle mutation (`move-task`, a status transition) commits its bookkeeping
   through the seam's `write_target`, landing on the coordination surface for a
   coord-routing mission and on primary for a non-coord one — verified, not just the
   read paths.

### Exception — unresolved identity (#2091)

1. Coordination worktree composition runs where `mid8` is empty.
2. The composition seam (`CoordinationWorkspace`) itself fails loudly with an
   actionable diagnostic — it does not compose `kitty/mission-<slug>-` and hand a
   malformed ref to `git worktree add` (exit 128).

### Exception — coordination surface states (#2250 + edges)

1. A mission that never declared a `coordination_branch` does **not** report
   `COORDINATION_BRANCH_DELETED`; messaging reflects the actual topology.
2. The seam distinguishes `UNMATERIALIZED` (branch exists, worktree not yet created →
   resolve via branch ref), `DELETED` (worktree removed mid-mission), and
   `never-created` (no coordination branch ever) — each with correct, non-misleading
   behaviour.

### Exception — flatten transition & protected primary

1. A mission flattened mid-flight (coordination_branch removed from `meta.json`,
   lingering `-coord` husk on disk) re-resolves **all** kinds to primary from the
   **stored** topology, never the husk.
2. A planning write whose primary resolves to a protected target branch routes to the
   sanctioned lane/PR path or fails with an explicit destination diagnostic — never a
   silent protected-main commit.

### Rule that must always hold

No lifecycle or planning command may compute an artifact's read or write location
from raw strings, the current checkout, an inline topology test, or a
`CommitTarget(ref=<checkout>)` construction. The seam is the only source of that
decision — including when it returns the primary surface.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Formalize the placement **seam** as the public face of the existing `resolve_action_context` derivation root: one authority exposing kind-aware `write_target(kind) -> CommitTarget` and `read_dir(kind)` projections, classified by `artifact_home_for` / `MissionArtifactHome`. It is a **thin authority the existing leaf resolvers delegate to**, NOT a rewrite of the resolver set. Consolidate the four duplicate `_planning_read_dir` wrapper copies into one shared helper (behaviour-preserving). | Draft |
| FR-002 | The kind→partition mapping is the two frozensets `_PRIMARY_ARTIFACT_KINDS` / `_PLACEMENT_ARTIFACT_KINDS` in `mission_runtime/artifacts.py` (all 14 `MissionArtifactKind` members classified). The spec locks **membership** of these sets; `ACCEPTANCE_MATRIX` and `ANALYSIS_REPORT` are coordination-partition kinds. | Draft |
| FR-003 | Coordination routing is decided **only** by `routes_through_coordination(stored_topology)` over `{COORD, LANES_WITH_COORD}`. Under `SINGLE_BRANCH` / `LANES` / flattened topologies, the seam resolves **all** kinds to the **primary** surface. | Draft |
| FR-004 | All lifecycle/planning **write** sites obtain their commit destination from the seam; none constructs an artifact path, `CommitTarget(ref=<checkout>)`, or inline topology branch. Sites to strangle (named): `core/mission_creation.py:176` (`_commit_feature_file` — the create-time root), `cli/commands/implement.py:885` & `:1462`, `cli/commands/agent/workflow.py:487/503/549/1694`, and the `tasks.py` move-task/mark-status write cluster. **This mission is authoritative over these surfaces**; sibling missions rebase onto its routing (see C-005). | Draft |
| FR-005 | The **read** sites on the named write surfaces obtain locations from the seam; no command reads mission artifacts from a raw primary/coord path, except documented legacy/migration modules on the allow-list. The broad kind-blind `resolve_feature_dir_for_mission` read-site sweep (~71 call sites / 18 write-classified across ~20 files) is a **separate strangle → tracked in #2453**, not this mission (reads already return topology-correct dirs; lower risk). | Draft |
| FR-006 | The seam returns results independent of the caller's current working directory. | Draft |
| FR-007 | (#2091) Add an empty-`mid8` guard at the composition seam `CoordinationWorkspace` (`coordination/workspace.py:161-226`) so branch/worktree composition fails loudly instead of producing a malformed ref → `git worktree add` exit-128; verify the upstream `runtime_bridge` guard remains. Close #2091. | Draft |
| FR-008 | (#2250) Verify and regression-lock the shipped fix so a mission that never declared a `coordination_branch` does not emit `COORDINATION_BRANCH_DELETED`; distinguish `never-created` from `DELETED`/`UNMATERIALIZED`. Close #2250. | Draft |
| FR-009 | An end-to-end characterization test walks `mission create → commit spec → setup-plan → agent tasks status → agent decision verify`, includes at least one lifecycle **mutation** through the seam, and asserts identical, partition-correct authority resolution from the repo root **and** an unrelated CWD, across coord-routing and non-coord topologies. | Draft |
| FR-010 | Documentation/prompt truth-up: retire "planning happens in main" (AGENTS.md / CLAUDE.md), correct #1716's stale "Locked Architecture Decision" (issue body), and rewrite `docs/release-goals/3.2.x.md` to move the **entire** #1878 write-side strangler (placement-routing **and** commit/protected-branch durability) into 3.2.x/G2 (operator decision). Correct the spec's own inventory references (2×2 topology, 14 kinds, `resolve_feature_dir_for_mission`). | Draft |
| FR-011 | Extend the ratchet scanner (`tests/architectural/test_no_write_side_rederivation.py`) to detect the `CommitTarget(ref=<checkout>)` / current-checkout construction grammar — the current blind spot where the FR-004 bypasses live — so the strangle is verifiable. | Draft |
| FR-012 | Placement resolves from the **stored** `meta.json` topology; a lingering `-coord` worktree on a flattened (coord-less stored) mission is not an authoritative surface (guarded by `_husk_is_authoritative_surface`). | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | **Extend** the existing ratchet — do not build a parallel one. Pin the write-side line allow-list baseline and shrink it; expand the adopted-module set as each surface is strangled. | Write-side allow-list seed = **1** (`coordination/status_transition.py:343`); baseline is shrink-only toward the permanent-fixture floor; `coord_authority_baseline` in `resolution_gate_allowlist.yaml` shrinks from 7 toward its permanent floor; the new FR-011 grammar is covered. | Draft |
| NFR-002 | The golden-path characterization test is deterministic and CWD-independent in CI. | Passes on 3 consecutive CI runs; wall-clock < 30 s. | Draft |
| NFR-003 | Placement resolution reads only mission identity/config + **stored** topology. | No recursive worktree-tree scan and no on-disk husk probe per resolution (bounded to `meta.json` + config reads). | Draft |
| NFR-004 | New/changed code passes project quality gates. | `ruff` + `mypy` zero issues; per-function cyclomatic complexity ≤ 15; new branches/helpers carry focused tests. | Draft |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **(Binding, centerpiece)** The seam is the single access point for artifact placement. The seam returning `PRIMARY` is **not** grounds to bypass it. Both read and write route through the seam; coord-routing is decided only by `routes_through_coordination(stored_topology)`. Forbidden at call sites: inline `topology == COORD`, `coordination_branch is not None`, raw `repo_root/kitty-specs` or `.worktrees/*-coord` construction, and `CommitTarget(ref=<checkout>)`. No parallel/shadow placement derivation may be introduced. | Draft |
| C-002 | This mission **locks** the partition (the two frozensets); it does not change which partition a kind belongs to. | Draft |
| C-003 | Do **not** materialize the coordination worktree at `mission create` (superseded by flatten-not-materialize). | Draft |
| C-004 | Do **not** route `setup-plan`/`finalize-tasks` through `BookkeepingTransaction` (it owns coordination-branch writes; planning stays primary — #2106/#2113). | Draft |
| C-005 | **This mission is authoritative** over the placement/write-routing surface. Where sibling missions `coord-authority-gate-hardening-01KW4T2F` and `implement-loop-coord-authority-01KW2E7A` touch the same seam, ratchet substrate (`resolution_gate_allowlist.yaml`, floor scalars), or write sites (`implement.py`/`workflow.py`), **this mission's routing is canonical and the siblings rebase onto it** (operator directive; the operator sequences the merges). | Draft |
| C-006 | New guards/routing follow **red-first**: the #2091 composition-seam guard and each write-site re-route land behind a failing reproduction through the pre-existing entry point. (#2250 is verify-existing, not red-first — the fix already shipped.) | Draft |
| C-007 | The FR-009 characterization test pins against the current kind-aware `resolve_planning_read_dir` surface. The prior "wait for #2429" hold is **likely satisfied** — `resolve_planning_read_dir` is already kind-aware (post-#2119) and the session-reaper rebase did not touch it; **verify, do not hold indefinitely**. | Draft |

## Success Criteria

- **SC-001**: 100% of the **named checkout-derived write** sites (`mission_creation.py`,
  `implement.py`, `workflow.py`, `tasks_move_task.py`, `mission_record_analysis.py`)
  obtain their commit destination from the seam. Residual checkout-derived fallbacks on
  non-owned surfaces (`orchestrator_api/commands.py:1451`, `coordination/transaction.py`
  legacy override) are flagged **VISIBLE** by the new grammar and tracked in **#2453** —
  not silently passing. The broad `resolve_feature_dir_for_mission` read-site sweep is
  **#2453**, out of scope here.
- **SC-002**: A maintainer running the full lifecycle from any directory observes one
  consistent, partition-correct authority; the golden-path test (incl. a mutation)
  passes across coord and non-coord topologies.
- **SC-003**: The #2091 composition-seam guard and #2250 regression tests pass; both
  issues are closed.
- **SC-004**: No documentation states planning artifacts live on `main` for
  coordination-routing missions; the roadmap places the whole #1878 write-side
  strangler in 3.2.x.
- **SC-005**: The **write-side** ratchet allow-list shrinks from its seed toward the
  permanent-fixture floor and the FR-011 `CommitTarget(ref=<checkout>)` grammar is
  covered; the `coord_authority` read-side baseline drain (7→2) is deferred to **#2453**.
  No new shadow path is introduced for a full cycle.

## Key Entities

- **`MissionArtifactKind`** — 14-member enum; partition fixed by the two frozensets.
- **`MissionTopology`** — the 2×2 grid; coord-routing via `routes_through_coordination`.
- **`MissionArtifactHome`** — value object carrying `read_surface` + `write_surface` +
  `commit_target`; the seam's canonical output.
- **Coordination surface / Primary surface** — the two physical destinations.

## Assumptions

- The seam is the existing `resolve_action_context` root formalized with kind-aware
  projections (thin authority), NOT a new resolver stack (bounds FR-001 size — squad F5).
- PR #2429 (extends `resolve_planning_read_dir`) lands via the other session before
  FR-009 is implemented (C-007).
- The mission is a coordination-routing mission and dogfoods the partition it locks.

## Dependencies

- **Soft pre-req**: PR #2429 — gates FR-009 timing only.
- **Authoritative over (siblings rebase onto this)**: `coord-authority-gate-hardening-01KW4T2F`,
  `implement-loop-coord-authority-01KW2E7A` on the shared seam/ratchet substrate (C-005).
- **Supersedes**: #1716 original "Locked Architecture Decision"; **ratifies** #2106 / #2113.
- **Delivers**: the placement-routing slice of #1878 (whole #1878 strangler now 3.2.x per FR-010).

## Out of Scope

- Changing the kind→partition mapping (C-002).
- Materializing the coordination worktree at create (C-003).
- The #1878 **commit-durability** slice as a body of work (protected-branch commit
  durability semantics) — now 3.2.x per FR-010 but delivered as a **fast-follow
  mission**, not folded here; this mission does the placement-routing slice.
