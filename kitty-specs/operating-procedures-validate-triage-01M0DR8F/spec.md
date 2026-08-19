# Mission Specification: Operating-Procedures Validate, Triage, Data-Drive

**Mission Branch**: `feat/operating-procedures-validate-triage`
**Created**: 2026-08-19
**Status**: Draft
**Input**: charter-resolution program M3 — seed `docs/plans/charter-resolution/seeds/seed-m3-operating-procedures.md`. Closes #2994, #3352, and the operating-procedures channel of #3488.

## Context & Problem

An agent profile's `collaboration.operating-procedures` is a schema-validated `list[str]`, but its **values are never checked against real doctrine nodes**. Measured across the 16 built-in profiles that declare the field (upstream/main @ `1f89ac01f`):

- **50** declarations total.
- **6** resolve to a real **procedure** node.
- **8** resolve to a **wrong-kind** node (every one of them a `tactic`, not a procedure).
- **36** resolve to **no node at all** (fictional / prose-only names).

Because the DRG edge-extractor (`doctrine/drg/migration/extractor.py::extract_artifact_edges`) ignores the field entirely, the real `agent_profile → procedure` edges are hand-pinned one profile at a time in `_CURATED_ARTIFACT_EDGES`. So authored procedure references are **silently inert**, and the data-drive fix (#3352) cannot be done by blind emission because it would mint 36 dangling edges → `assert_valid` failure. Even today, **4 of the 6 legitimately-authored refs never become edges** because no one hand-pinned them (only `doctrine-daphne` and `researcher-robbie` are curated).

This is one face of the charter-resolution meta-cause (#3530/#3410): authored governance loads healthy, validates green, and then reaches no consumer because a divergence fails silently.

## User Scenarios & Testing *(mandatory)*

The "users" here are **doctrine authors** (who write agent profiles) and the **doctrine graph build** (which must reflect authored intent honestly).

### User Story 1 - A fictional operating-procedure fails loud (Priority: P1)

A doctrine author writes `operating-procedures: [code-review-checklist]` on a profile, but no `procedure:code-review-checklist` node exists. Today this loads clean and the reference vanishes. After this mission, the build fails with a message naming the profile, the dead entry, and the fact that it resolves to no procedure node.

**Why this priority**: This is the load-bearing "validate loud" step and the precondition for everything else. It converts 44 silent divergences into loud, actionable failures at the cheapest point.

**Independent Test**: Add a fictional `operating-procedures` entry to a built-in profile fixture → the validator/gate reddens naming that entry; remove it → green. Fully testable without any extractor change.

**Acceptance Scenarios**:

1. **Given** a built-in profile whose `operating-procedures` names an id with no matching procedure node, **When** the operating-procedures validator runs, **Then** it reports that entry as unresolved (profile id + entry + reason) and the gate fails.
2. **Given** a built-in profile whose `operating-procedures` names a real *tactic* id (wrong kind), **When** the validator runs, **Then** it reports that entry as unresolved-for-kind (it must be a procedure), not as valid.
3. **Given** every `operating-procedures` entry across built-in profiles resolves to a real procedure node, **When** the validator runs, **Then** the unresolved set is empty and the gate passes.

### User Story 2 - The 44 dead references are triaged to zero (Priority: P1)

Each of the 36 fictional and 8 wrong-kind entries gets a per-entry disposition — delete (drop the dead entry), repoint (to a real procedure that matches the intent), or migrate (a wrong-kind tactic moves to the profile's `tactic-references` channel where it belongs). After triage, the built-in population is 100% resolvable and the User Story 1 gate is green.

**Why this priority**: Triage MUST precede data-drive. Emitting edges from an un-triaged field mints dangling edges and fails `assert_valid`. The order is load-bearing.

**Independent Test**: Run the US1 gate before triage (red, 44 unresolved) and after triage (green, 0 unresolved); the disposition table accounts for every one of the 44 entries.

**Acceptance Scenarios**:

1. **Given** the 44 non-resolving entries, **When** triage is complete, **Then** a disposition table records author/repoint/delete/migrate for each of the 44, and no entry is left unaccounted.
2. **Given** a wrong-kind tactic already duplicated in the profile's `tactic-references`, **When** triaged, **Then** the redundant `operating-procedures` entry is deleted (no data loss — the tactic channel already carries it).
3. **Given** triage is complete, **When** the US1 gate runs over all built-in profiles, **Then** the unresolved set is empty.

### User Story 3 - Profile→procedure edges are data-driven, guarded (Priority: P1)

The extractor emits `agent_profile --requires--> procedure` from the `operating-procedures` field, guarded so it only emits when the target resolves to an existing **procedure** node. The operating-procedures-sourced hand-pins in `_CURATED_ARTIFACT_EDGES` are retired (now derived). The shipped graph gains the 4 previously-inert real refs and loses no valid edge.

**Why this priority**: This is the #3352 payoff — authored governance finally reaches the graph, and the per-profile hand-maintenance is retired. It must land only after US1+US2 guarantee resolvability.

**Independent Test**: A synthetic profile whose `operating-procedures` names a real procedure emits exactly one `requires` edge to that procedure; a synthetic profile naming a non-procedure/absent id emits **no** such edge (guard holds). `assert_valid` passes on the regenerated graph.

**Acceptance Scenarios**:

1. **Given** a profile with a resolvable `operating-procedures` procedure ref, **When** `extract_artifact_edges` runs, **Then** exactly one `agent_profile:<id> --requires--> procedure:<target>` edge is emitted.
2. **Given** a profile whose `operating-procedures` entry does not resolve to a procedure node, **When** the extractor runs, **Then** no procedure edge is emitted for it (guarded — belt-and-suspenders against org/project-tier profiles the built-in gate does not cover).
3. **Given** the operating-procedures-sourced hand-pins (`researcher-robbie→spike-timebox-policy`, `doctrine-daphne→onboard-external-agent-to-pack`) are removed from `_CURATED_ARTIFACT_EDGES`, **When** the graph is regenerated, **Then** those edges still exist (now data-driven) and the graph still passes `assert_valid`.
4. **Given** the regenerated graph, **When** compared to the pre-mission graph, **Then** every removed edge is re-derived and the only net-new profile→procedure edges are the 4 previously-inert real refs (plus any repoints from triage) — no dangling edges.

### User Story 4 - The RECONCILE third trigger edge is completed (Priority: P2)

`RECONCILE_CHANGE_SCOPE_TENSIONS` declares three triggers in its `scope:` — `DIRECTIVE_024`, `DIRECTIVE_025`, and `tactic:change-apply-smallest-viable-diff`. The first two have inbound `suggests` edges; the tactic one is unwired. This mission completes the third edge so all three triggers reach the reconciler.

**Why this priority**: A small, traced correctness fix in the same extractor-curation surface, explicitly named in the seed. Lower priority than the operating-procedures spine but rides the same change.

**Independent Test**: After the change, `tactic:change-apply-smallest-viable-diff --suggests--> directive:RECONCILE_CHANGE_SCOPE_TENSIONS` is present in the graph and `assert_valid` passes.

**Acceptance Scenarios**:

1. **Given** the reconciler's scope names three triggers, **When** the graph is generated, **Then** all three trigger→RECONCILE edges exist (the tactic edge being the one this mission adds).

### Edge Cases

- **Alias collision**: two procedures with ids differing only by kebab spelling — resolution is by exact id against the procedure node set; no fuzzy matching (fail-closed).
- **Org/project-tier profiles**: the built-in load-time gate covers built-in profiles only; the extractor emission guard (procedure-kind check) still protects the graph from an unresolvable org/project ref (no dangling edge, silent skip is acceptable *there* because the gate is built-in-scoped — see C-006).
- **Duplicate emission**: a procedure named in both `operating-procedures` and a hand-pin must dedupe to one edge (existing `_add_edge` triple-dedup covers this).
- **Empty field**: a profile with no `operating-procedures` emits nothing and passes the gate (default `[]`).
- **Repoint creates a new real edge**: if a fictional entry is repointed to a real procedure, that becomes a data-driven edge — accounted for in the graph-delta review (US3 scenario 4).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Operating-procedures resolution validator | As a doctrine author, I want a validator that flags every `operating-procedures` entry that does not resolve to a real procedure node, so fictional references fail loud instead of vanishing. | High | Open |
| FR-002 | Wrong-kind detected as unresolved | As a doctrine author, I want an `operating-procedures` entry that names a non-procedure node (e.g. a tactic) to be reported as unresolved-for-kind, so a wrong-kind ref is not silently dropped by the downstream emission guard. | High | Open |
| FR-003 | Empty-set gate over built-in profiles | As a maintainer, I want an architectural gate asserting the built-in unresolved set is empty (WP09 empty-set-gate precedent), so a regression that reintroduces a dead entry fails CI. | High | Open |
| FR-004 | Doctor surface for the diagnostic | As a maintainer, I want the unresolved set surfaced in `doctor doctrine` output, so the diagnostic is discoverable outside the test suite. | Medium | Open |
| FR-005 | Triage the 44 dead references | As a doctrine author, I want each of the 36 fictional + 8 wrong-kind entries dispositioned (delete / repoint / migrate / author) in a recorded table, so the built-in population becomes 100% resolvable. | High | Open |
| FR-006 | Migrate wrong-kind tactics to the tactic channel | As a doctrine author, I want a wrong-kind tactic ref moved to the profile's `tactic-references` (or deleted if already present), so the authored intent is preserved in the correct channel. | Medium | Open |
| FR-007 | Data-drive profile→procedure edges (guarded) | As the graph build, I want `extract_artifact_edges` to emit `agent_profile --requires--> procedure` from `operating-procedures`, only when the target resolves to an existing procedure node, so authored refs become real edges without minting dangling ones. | High | Open |
| FR-008 | Retire operating-procedures-sourced hand-pins | As a maintainer, I want the op-proc-sourced `_CURATED_ARTIFACT_EDGES` entries (`researcher-robbie→spike-timebox-policy`, `doctrine-daphne→onboard-external-agent-to-pack`) removed, so those edges are derived, not hand-maintained. Prose-sourced pins (lexical-larry, minutes-maker-mahad) stay. | High | Open |
| FR-009 | Complete the RECONCILE third trigger edge | As a doctrine author, I want `tactic:change-apply-smallest-viable-diff --suggests--> directive:RECONCILE_CHANGE_SCOPE_TENSIONS` wired, so all three triggers named in the reconciler's scope reach it. | Medium | Open |
| FR-010 | Regenerate committed graph fragments | As the graph build, I want the shipped `*.graph.yaml` fragments regenerated to reflect the new derived edges, so the committed graph and the extractor agree (freshness). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Type + lint cleanliness | All new/changed code passes `ruff` and `mypy --strict` with zero issues and zero suppressions (no `# noqa`, no `# type: ignore`, no per-file ignore additions). | Maintainability | High | Open |
| NFR-002 | Graph-delta accountability | The regenerated graph's edge/node delta versus pre-mission is fully accounted for: every removed hand-pin re-derived, every net-new edge traced to a real authored ref or a triage repoint; zero dangling edges (`assert_valid` passes). | Correctness | High | Open |
| NFR-003 | Fail-closed resolution | Resolution is exact-id against the procedure node set — no fuzzy/nearest-match inference; an unrecognised id is unresolved, never guessed. | Correctness | High | Open |
| NFR-004 | Complexity ceiling | `extract_artifact_edges` stays at or below the mccabe/C901 ceiling of 15; new logic is factored into helpers (the function is already at `# noqa: C901` — do not raise it). | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Hard internal order | Ship in order: validate (loud) → triage (to ∅ unresolved) → data-drive (guarded emission + retire hand-pins). Data-driving before triage mints 36+ dangling edges → `assert_valid` failure. | Technical | High | Open |
| C-002 | No cascade change | Do NOT touch `REFERENCE_RELATIONS` / the kind-complete cascade (#2829 = M5). This mission wires edges; it does not expand cascade traversal. | Technical | High | Open |
| C-003 | No delivery/render change | Do NOT touch the delivery-table/renderer that ships procedures to the agent (#3488 render half = M4). This mission owns edge wiring only. | Technical | High | Open |
| C-004 | Single-authority discipline | `charter` must not import `specify_cli`; the validator/emission logic lives under `doctrine/`, read by the graph build. | Technical | High | Open |
| C-005 | ATDD red-first | Every implementation WP commits its failing-first test before the fix; the reviewer verifies RED on `planning_base_branch` and GREEN at the final commit (charter C-011). | Process | High | Open |
| C-006 | Built-in-scoped gate | The load-time empty-set gate covers built-in profiles only. Org/project-tier profiles are protected by the extractor's procedure-kind emission guard (no dangling edge), not by a hard load failure — those tiers are out of scope for the gate. | Technical | Medium | Open |
| C-007 | No new procedure content | Authoring net-new procedure nodes for fictional refs is OUT of scope. Triage dispositions are delete / repoint-to-existing / migrate-to-tactic-channel. Authoring is deferred to a doctrine-content mission. | Scope | Medium | Open |

### Key Entities

- **operating-procedures entry**: a `list[str]` id on `CollaborationContract.operating_procedures`; intended to name a procedure the profile runs.
- **procedure node**: a `procedure:<id>` DRG node emitted from `packs/built-in/procedures/*.procedure.yaml`.
- **resolution**: exact-id membership of an operating-procedures entry in the procedure node set.
- **disposition**: the per-entry triage outcome — delete / repoint / migrate / (author, out of scope).
- **`_CURATED_ARTIFACT_EDGES`**: the hand-pinned edge tuple in the extractor; op-proc-sourced pins are retired, prose-sourced pins stay.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every `operating-procedures` entry across all 16 built-in profiles resolves to a real procedure node — the validator's unresolved set is **0** (down from 44).
- **SC-002**: Adding a single fictional `operating-procedures` entry to any built-in profile reddens the empty-set gate; removing it greens it (non-vacuous gate).
- **SC-003**: The regenerated graph derives `agent_profile → procedure` edges from the field, including the **4** previously-inert real refs, with **zero** dangling edges (`assert_valid` passes).
- **SC-004**: The **2** operating-procedures-sourced hand-pins are removed from `_CURATED_ARTIFACT_EDGES` and their edges are still present (data-driven); the 2 prose-sourced pins remain.
- **SC-005**: All three triggers named in the RECONCILE reconciler's scope have inbound edges (the tactic trigger edge is added).
- **SC-006**: No change to cascade traversal (`REFERENCE_RELATIONS`) or the procedure delivery/render surface — those remain byte-identical (M5/M4 scope).

## Assumptions & Resolved Decisions

The seed flagged two open operator decisions; the operator delegated resolution to this session. Resolved with fresh context (grounding: the census above):

- **Wire vs deprecate → WIRE.** `operating-procedures` becomes a first-class data-driven edge source (not deprecated/renamed). Deprecating would strand the 6 legitimately-authored refs; #3352 is explicitly "data-drive those edges". The dead-entry diagnostic ships either way.
- **Validator contract → must resolve to a real *procedure* node** (not merely "any real node"). This makes both the 36 fictional and the 8 wrong-kind loud (44 total), rather than passing the 8 at load and letting the emission guard silently drop them — which would reintroduce exactly the silent-drop this program exists to kill. (The seed's "36 → loud" is the fictional subset; the 8 wrong-kind are the seed's separately-named bucket and are also invalid under a procedure-kind contract.)
- **Triage dispositions**: 6 real kept; 8 wrong-kind → delete-if-redundant / migrate-to-`tactic-references`; 36 fictional → per-entry delete (default) / repoint-to-existing-procedure; authoring new procedures is out of scope (C-007). Full 44-row table produced during plan/tasks.
- **Hand-pin retirement**: `researcher-robbie→spike-timebox-policy` and `doctrine-daphne→onboard-external-agent-to-pack` are op-proc-sourced → retired. `lexical-larry→glossary-maintenance-workflow` and `minutes-maker-mahad→meeting-minutes-pipeline` are prose-sourced (those profiles carry no `operating-procedures` field) → kept.

## Out of Scope

- Kind-complete cascade / `REFERENCE_RELATIONS` expansion (#2829 = M5).
- Delivery/render of procedures to the dispatched agent (#3488 render half, `procedures[]` array = M4).
- Authoring net-new procedure nodes for fictional references (doctrine-content work).
- Org/project-tier `operating-procedures` hard load-failure gate (built-in-scoped here; org/project protected by the emission guard).
