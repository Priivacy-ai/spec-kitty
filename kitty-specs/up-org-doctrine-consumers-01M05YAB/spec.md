# Mission Specification: Org-Tier Doctrine Reaches Its Consumers

**Mission Branch**: `kitty/mission-up-org-doctrine-consumers-01M05YAB`
**Created**: 2026-08-16
**Status**: Draft
**Input**: User description: "Fix issue #3516 — four related defects, all the same shape: doctrine resolution stopping at project or built-in tier when a registered org tier exists (step-contract executor, DRG delegation, expected-artifacts manifest, and discarded delegation results)."

## Provenance

This mission answers GitHub issue [#3516](https://github.com/Priivacy-ai/spec-kitty/issues/3516)
("Org-tier doctrine never reaches its consumers: step contracts, expected-artifacts, and the
executor's DRG are all project-scoped or built-in-only"), filed against `Priivacy-ai/spec-kitty`,
open, no assignee, no labels. All source citations below were **re-verified in this checkout**
(`main` @ `2210e4c3f`, `spec-kitty-cli` 3.2.6rc2) during spec authoring on 2026-08-16, not
inherited from the issue text. Several claims in the issue and its accompanying operator brief
were found stale, imprecise, or mis-scoped during that re-verification — each is called out at
its point of use below and summarized in the Decisions Log (D-000).

## Decisions Log

The following are binding decision records made during spec authoring, each independently
verified against this checkout. They are not open questions for a reviewer to re-litigate.

### D-000 — Corrections to the operator brief and issue text, found during re-verification

1. **"Both step-contract consumers" undercounts the construction sites.** There are **six**
   `MissionStepContractRepository(` construction call sites, not two. See D-001 for the
   full per-site audit.
2. **The brief's "proven org-root-resolving helper… at `src/charter/doctrine_service_builder.py`"
   conflates two structurally different resolution shapes.** `MissionStepContractRepository`
   takes `org_dirs: list[Path]` (multiple org packs, declared order, later overrides earlier —
   `doctrine/base.py:93-102`); `load_validated_graph` takes `org_root: Path | None` — **a single
   path** (`charter/_drg_helpers.py:42`). No existing helper produces the list shape by calling
   into `doctrine_service_builder.py` directly for a single repository; the closest fits are:
   - **List shape** (`org_dirs`): `doctrine.drg.org_pack_config.resolve_org_roots(repo_root)`
     (returns one `Path` per configured org pack, in declared order — `org_pack_config.py:404-412`),
     filtered to existing paths and joined with the artifact-kind subdirectory name, exactly as
     `doctrine.service.DoctrineService._org_dirs` already does (`doctrine/service.py:47-52`) —
     this is the pattern site 1 (`doctrine/service.py:118`) already uses correctly.
   - **Single-path shape** (`org_root`): the *only* existing caller that supplies one,
     `charter/action_doctrine_bundle.py:_resolve_action_bundle` (lines 90-97), resolves it by
     taking the **first existing** candidate from
     `charter.org_pack_discovery._enumerate_org_pack_paths(repo_root)` — a first-match, not an
     all-packs-merged, resolution. This is a real, pre-existing architectural limitation
     (`load_validated_graph` cannot merge more than one org DRG root today) that this mission
     inherits rather than fixes (out of scope — see C-004).
   FR-002/FR-003 below name the correct helper for each shape explicitly, rather than the brief's
   single (and singly-shaped) citation.
3. **Defect (3) as stated in the issue ("`expected-artifacts.yaml` and
   `MissionTypeProfileRepository.for_project`") conflates two unrelated repository classes with
   different tiering capability.** Traced separately:
   - `MissionTypeProfileRepository` (`charter/mission_type_profile_repository.py:77-99`) **is** a
     `BaseDoctrineRepository` subclass and its `for_project()` classmethod **already accepts**
     `org_dirs` (line ~99). The gap is caller-side only, and it is a **live, reachable** gap — see
     D-004 for why (the brief's own cited line, `mission_type_profile_repository.py:99`, is the
     method *definition*, not a broken call site; the real call site is
     `charter/mission_type_profiles.py:1168`). This is cheap, and shaped exactly like defect (1).
   - `MissionTemplateRepository` (`doctrine/missions/repository.py:122-135`), the class that
     actually reads `<type>/expected-artifacts.yaml`, is **not** a `BaseDoctrineRepository`
     subclass at all — it is a bespoke single-root reader (`__init__(self, missions_root: Path)`,
     `.default()` always points at the built-in tree, no `org_dirs`/`project_dir` parameter
     exists anywhere on the class). There is no `ArtifactKind` entry for a mission-scoped asset
     family either. **No parameter already exists here to thread** — the issue's framing ("the
     parameters already exist on every repository involved") is false for this specific gap. Any
     fix here is net-new surface, not caller-side threading. See D-005, FR-008, C-003.
   These are treated as two separate defects below (D-004 governance-profile threading; D-005
   expected-artifacts org-tier read) rather than one, because their fix shapes and costs differ
   by an order of magnitude.
4. **The issue's own probe numbers (347 nodes without org root, 350 with) could not be
   reproduced** — the org pack used for that probe is not present in this checkout. A
   **first-hand, reproducible** substitute was measured instead in this exact checkout (see
   NFR-001, SC-001): `load_validated_graph(repo_root)` with no `org_root` returns **347** DRG
   nodes here too (this specific number *is* independently confirmed), and supplying a minimal
   one-node synthetic org pack (mirroring the shape used by
   `tests/charter/test_org_scan_dirs_activation_regression.py::_write_org_directive_fixture`) as
   `org_root` raises the count to **348**, with the probe node present by URN lookup. This
   confirms the mechanism the issue describes without asserting its specific (unreproducible)
   350 figure.
5. **This repository's own registered org pack (`packs/internal`, `.kittify/config.yaml:32-35`)
   is itself currently invisible to `load_validated_graph`'s default (no-`org_root`) call** — a
   live, in-repo instance of defect (2), not a hypothetical. (Separately, and out of this
   mission's scope: `packs/internal/drg/fragment.yaml` does not match the `*.graph.yaml` naming
   `doctrine.drg.loader.load_graph_or_dir` requires, so even a correctly-threaded `org_root`
   pointed at `packs/internal` would still raise `DRGLoadError` today. That naming mismatch is a
   pre-existing, unrelated defect in the internal pack's own layout — not fixed here, not blocking
   this mission, and not filed as part of #3516.)

### D-001 — Verdict on each of the six `MissionStepContractRepository(` construction sites

| # | Site | Verdict | Reasoning |
|---|------|---------|-----------|
| 1 | `src/doctrine/service.py:118` (`DoctrineService.mission_step_contracts` property) | **Correct as-is. No change.** | Already passes `org_dirs=self._org_dirs("mission_step_contracts")` and `project_dir=self._project_dir("mission_step_contracts")`. This is the reference implementation every other site should match. |
| 2 | `src/doctrine/missions/step_contracts.py:308` (bare `MissionStepContractRepository()`, the default inside `resolve_step_contract_ids`) | **Out of scope. No change.** | Its own docstring (lines 291-298) documents built-in-only as *deliberate*: "the pure artefact answer, never a project override." Its sole caller, `_resolve_step_contracts_slot` (`charter/mission_type_profiles.py:1061-1081`), does not even receive `repo_root` — widening this would require new plumbing through `resolve_mission_type_context`, not a one-line `org_root` add. More decisively: `ResolvedMissionType.step_contracts`, the field this populates, has **zero production consumers** anywhere under `src/` (verified: `grep -rn "\.step_contracts\b" src/` returns only the field's own definition/docstring; only `tests/charter/test_resolved_mission_type_context.py` reads it). Fixing this moves nothing observable today. See C-005. |
| 3 | `src/specify_cli/review/gate_bindings.py:168` (`_build_repository`) | **In scope. Fix.** | Docstring: "Construct the contract repository the way the executor does" — an explicit mirroring contract with site 6. `load_gate_bindings` (same file, ~line 180) states it uses "the same repository the executor uses." If site 6 becomes org-aware and this stays project-dir-only, an org-pack step contract's `gates:` block would resolve delegations correctly at dispatch time but silently never fire its review-transition gate (`tasks_move_task.py` consumes `load_gate_bindings`) — a new, mission-specific inconsistency this fix would otherwise introduce. Must move in lockstep with site 6. |
| 4 | `src/runtime/next/runtime_bridge_composition.py:284` (`_resolve_runtime_contract_for_step`) | **In scope. Fix.** | This resolves a custom mission step's `contract_ref` against the on-disk repository at **live `next` dispatch time** — confirmed reachable for any mission type, not just `software-dev`: `_should_dispatch_via_composition` (`runtime_bridge_composition.py:150-176`) is mission-generic (routes on `resolve_mission_type_context(...).action_sequence` membership or a non-empty `agent_profile`/`contract_ref` on the frozen template), contrary to a stale comment elsewhere in this module family claiming dispatch is hard-guarded to `mission == "software-dev"` (see D-002). An org-tier step contract referenced by `contract_ref` on a custom mission type would silently fail to resolve here today. |
| 5 | `src/specify_cli/mission_loader/command.py:237` (`_resolve_contract_refs`) | **In scope. Fix, in lockstep with site 4.** | Docstring (lines 213-224) states explicitly: "This keeps loader semantics aligned with the runtime so an id that resolves here will resolve at runtime too." If site 4 becomes org-aware and this validator does not, a legitimate org-tier `contract_ref` would be **accepted at runtime but rejected at mission-load/validation time** (`MISSION_CONTRACT_REF_UNRESOLVED`) — the exact false-negative the docstring's own stated contract exists to prevent. Must move in lockstep with site 4. |
| 6 | `src/specify_cli/mission_step_contracts/executor.py:160` (`StepContractExecutor.__init__`) | **In scope. The primary defect (FR-001).** | The issue's defect (1). |

**Net scope**: five of six sites change (1 is already correct; 2 is deliberately and currently
harmlessly out of scope). This is a larger caller set than the brief's "both … consumers" framing
suggested — a material input to the M-vs-L sizing call (C-006).

### D-002 — SK-46 (workspace ledger) is confirmed true and is directly relevant here

`SPEC-KITTY-LEDGER.md`'s SK-46 entry claims a comment in `runtime_bridge_composition.py`
overstates a `mission == "software-dev"` hard guard on composition dispatch. Re-verified directly
against this checkout: `runtime_bridge.py:1677`'s docstring says "C-008 hard-guards this on
`mission == "software-dev"`," but the actual dispatch predicate,
`_should_dispatch_via_composition` (`runtime_bridge_composition.py:150-176`), contains no such
guard — it is mission-generic. The only literal `mission == "software-dev"` test in this module
family is inside `_check_composed_action_guard` (`runtime_bridge_composition.py:477`), which
selects a **post-composition artifact-presence guard branch family**, not whether composition
dispatch itself is reachable. This matters directly for this mission: it confirms an org-tier
step contract on a **custom** mission type is a live, reachable path today, not a hypothetical —
which is why site 4/5 (D-001) are in scope rather than deferred as "software-dev only, low
priority."

### D-003 — Org-root resolution does not route through a full `DoctrineService`/`build_activation_aware_doctrine_service`

Considered and rejected: resolving org tier for sites 3-6 by constructing a full
`doctrine.service.DoctrineService` (or the activation-aware wrapper) and reading its
`.mission_step_contracts` property, rather than resolving `org_dirs`/`org_root` directly and
constructing `MissionStepContractRepository`/calling `load_validated_graph` as each site already
does. **Rejected**: none of the five call sites need any of `DoctrineService`'s other nine
repositories; constructing the full service is unnecessary coupling for a composer
(`StepContractExecutor`) and three CLI/runtime helper functions, adds an import of
`charter.context`/`charter.doctrine_service_builder` machinery documented as tuned for the
charter-context/bootstrap-render call path (docstring, `doctrine_service_builder.py:1-72`), and
no sole-door architectural gate forbids the direct construction these sites already perform
(verified: `grep -rn "MissionStepContractRepository" tests/architectural/` finds no sole-door
test naming this class — see the full list under D-001). Each site instead resolves
`org_dirs`/`org_root` directly per D-000(2) and constructs the same repository/loader call it
already makes, with the additional argument threaded through.

### D-004 — `MissionTypeProfileRepository.for_project` caller gap is live and cheap; fixed as FR-004

Traced precisely (correcting the brief's citation, D-000(3)): `_mission_type_profile_repository`
(`charter/mission_type_profiles.py:1148-1168`) has two call sites.

- `charter/action_grain.py:220` passes no `repo_root` (hits the built-in-only branch,
  `MissionTypeProfileRepository()`). This is **deliberate**, per the sibling mission
  `up-mission-type-seam-01KZY1JB`'s own binding constraint C-006: "`action_grain.py` deliberately
  stays built-in-only — it is a gate over shipped content, not a resolution path." **Not
  touched.**
- `_resolve_governance_slot` (`mission_type_profiles.py:807`) passes a real, non-`None`
  `repo_root` — sourced from `resolve_mission_type_context`'s own required `repo_root` parameter
  (line 567), and `_resolve_governance_slot` runs **eagerly** on every mission-type context
  resolution (its own docstring: "provenance reflects the winning layer… computed *eagerly*
  here," lines 785-788 — only the type/action-grain union (tracked as requirement 013 in the *sibling*
  mission `up-mission-type-seam-01KZY1JB`'s own spec, not a requirement of this mission) is
  deferred, not the profile load itself). This
  hits `MissionTypeProfileRepository.for_project(repo_root)` (`mission_type_profiles.py:1168`)
  — project tier, **no `org_dirs`**, even though `for_project` accepts it. This is a live,
  reachable gap: an org-tier `governance-profile.yaml` override for any activated mission type is
  silently invisible in the rendered governance text every mission-type resolution produces.
  **Fixed as FR-004** — identical shape and cost to FR-001.

### D-005 — Surface, not delete, the discarded delegation results (issue defect 4)

**Decision: SURFACE.** `StepContractExecutionResult`'s `resolved_delegations` /
`unresolved_candidates` (on each `StepContractStepResult`) are computed by
`StepContractExecutor._resolve_step_delegations` (`executor.py:284-313`) and already partially
leak into free text via `_build_request_text` (`executor.py:356-387`, lines 379-384: "Resolved
delegations: …" / "Unresolved delegation candidates: …" appended to the LLM-facing request).
Structurally, though, nothing reads the fields off the result object itself outside the
executor's own tests: `runtime_bridge_composition.py`'s `_dispatch_via_composition` — the sole
production consumer of `StepContractExecutionResult` — reads only `.invocation_ids`
(`runtime_bridge_composition.py:580`, comment: "forward the invocation_id chain… downstream…
event/trail writers"), confirmed by exhaustive grep: no other `src/` file reads
`resolved_delegations`/`unresolved_candidates`.

**Why surface, not delete:**
- The computation is not wasted work being removed for its own sake — it is already fully paid
  for (used to build the request text) and cheap to expose structurally; deleting it would save
  effectively zero LOC while destroying a signal that already exists.
- This repository's own charter and cross-mission precedent treat "computed but silently
  discarded" as the worst failure class, not a neutral one:
  `SPEC-KITTY-LEDGER.md`'s SK-04 entry names exactly this shape ("a tool that… reports success
  while measuring nothing") as its highest-severity entry; the sibling mission
  `up-mission-type-seam-01KZY1JB`'s NFR-002 states the standing expectation directly: "No silent
  success anywhere in the new seam… No new path may return `None` / an empty collection… and
  treat that as a successful result."
- The shipped built-in `software-dev/specify` contract is a live instance: re-counted directly
  against `packs/built-in/missions/built_in_step_contracts/specify.step-contract.yaml` in this
  session, it declares **7** `delegates_to` candidates across its `capture_intent`,
  `map_examples`, `validate_requirements`, `document_decisions`, and `commit_spec` steps (not the
  issue's cited "9" — another stale figure, corrected here; see D-000). Whatever the exact count,
  today none of it is reported if a candidate never resolves — a pack/contract author gets no
  signal a citation is dead.
- Deleting the fields would not remove the underlying risk (a dead citation), it would just make
  it permanently unobservable — the opposite of what this whole issue is about.

**Concrete fix (FR-007)**: add an aggregate read (e.g. a `has_unresolved_delegations` /
`all_unresolved_candidates` property on `StepContractExecutionResult`) — the shape is
illustrative, and task decomposition settled on inline iteration over `result.steps`
instead, to avoid a file collision; see WP03 — and have
`_dispatch_via_composition` (the one production reader) log a named `WARNING` per step with 1+
unresolved candidates, identifying the step id, contract id, and the unresolved candidate names —
mirroring the existing `logger.info(...)` treatment already given to `invocation_ids` two lines
below in the same function (`runtime_bridge_composition.py:585-591`). Non-blocking (a WARNING,
not a raise) — matches this repo's existing precedent of composition failures surfacing as
structured, non-crashing results (an existing, already-shipped contract in this same file,
tracked elsewhere as requirement 009 — pre-existing prior art this mission follows, not a requirement of
this mission) rather than a new hard failure mode
for a case that is not necessarily an authoring mistake (a candidate can legitimately be
activation-filtered out).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An org-tier step contract's delegations resolve at dispatch time (Priority: P1)

An organisation has registered an org-tier doctrine pack (`.kittify/config.yaml`'s
`doctrine.org.packs`) shipping both a `mission_step_contracts/*.step-contract.yaml` file and DRG
nodes for the directives/tactics it delegates to. Today, `StepContractExecutor` can see neither:
the contract itself is invisible (defect 1) and, even if it were visible via a duplicated
project-tier copy, its `delegates_to` candidates could never resolve against the org pack's own
DRG nodes (defect 2) — the two defects compound, per the issue's own framing ("fixing (1) without
(2) still leaves delegation dead").

**Why this priority**: This is the mission's core defect pair and the reason the issue exists.

**Independent Test**: Register a minimal org pack (mirroring
`tests/charter/test_org_scan_dirs_activation_regression.py`'s fixture shape) declaring one
`mission_step_contract` and one `directive` DRG node the contract's `delegates_to` cites. Run
`StepContractExecutor(repo_root=...).execute(...)` against a mission/action the org contract
declares, with no project-tier duplicate present. Confirm the contract is found and the
delegation resolves to the org-tier directive's URN.

**Acceptance Scenarios**:

1. **Given** an org pack shipping `mission_step_contracts/custom.step-contract.yaml` for
   `(mission="custom-org-mission", action="do-thing")` and no project-tier copy, **When**
   `StepContractExecutor.execute` is called for that mission/action, **Then** the contract is
   found (not `StepContractExecutionError: No step contract found`).
2. **Given** the same org pack also declaring a DRG node for a directive the contract's
   `delegates_to` cites, **When** the step executes, **Then**
   `StepContractStepResult.resolved_delegations` contains that directive's URN (not empty /
   `unresolved_candidates`).
3. **Given** the same setup with the org pack's DRG fragment **removed**, **When** the step
   executes, **Then** the same candidate appears in `unresolved_candidates` instead — the
   before/after contrast that proves the fix, not merely "the call doesn't crash."

---

### User Story 2 - An org-tier `contract_ref` resolves identically at mission-load validation and at runtime dispatch (Priority: P1)

A custom mission type's frozen template declares a step with `contract_ref` pointing at an
org-tier step contract. Today, `_resolve_contract_refs` (mission-load validation,
`mission_loader/command.py:237`) and `_resolve_runtime_contract_for_step` (runtime dispatch,
`runtime_bridge_composition.py:284`) both construct project-dir-only repositories — so an
org-tier `contract_ref` is invisible at **both** points, but the two call sites' docstrings each
promise consistency with the other, and only one of the two actually needs to change for the
promise to become **wrong** in a new, worse way (accepted at one point, rejected at the other).

**Why this priority**: A partial fix here (only site 4 or only site 5) is worse than no fix — it
converts a consistent "always invisible" into an inconsistent "sometimes invisible," which is
harder to diagnose.

**Independent Test**: Author a custom mission template with a step declaring
`contract_ref: "org:some-contract"` resolvable only via an org pack. Run the mission-load
validator and the runtime dispatch resolver against the same fixture in the same test. Confirm
both resolve it, or (as a regression guard) both would reject it identically if the org pack is
absent.

**Acceptance Scenarios**:

1. **Given** a custom mission template step with an org-tier `contract_ref`, **When**
   `spec-kitty mission run` validates the template (site 5), **Then** validation succeeds (no
   `MISSION_CONTRACT_REF_UNRESOLVED`).
2. **Given** the same template and the same org pack, **When** `next` dispatches that step (site
   4), **Then** `_resolve_runtime_contract_for_step` returns the org-tier contract (not `None`).
3. **Given** the org pack is not configured for the current project, **When** either surface is
   exercised, **Then** both fail identically (same `MISSION_CONTRACT_REF_UNRESOLVED` /
   dispatch-fallback outcome) — proving lockstep, not merely "both eventually work."

---

### User Story 3 - An org-tier step contract's `gates:` block fires at WP review-transition time (Priority: P2)

An org pack's step contract declares a `gates:` block on its `review` step. An operator attempts
to move a work package to `approved`. Today, `gate_bindings._build_repository` (site 3) cannot
see the org-tier contract even after site 6 (the executor) is fixed, so the gate binding is
silently absent and the transition proceeds ungated.

**Why this priority**: Lower than US1/US2 because gates are an additive safety mechanism, not the
core delegation path — but a silently-inert gate is exactly the silent-failure shape this whole
issue exists to close, so it cannot be left for a future mission once the underlying repository
construction pattern is being fixed everywhere else.

**Independent Test**: Register an org pack step contract with a `gates:` entry on an action. Call
`load_gate_bindings(repo_root, mission, action)` (the gate-bindings public entry point) with only
the org-tier contract present (no project-tier duplicate). Confirm the returned gate list is
non-empty and matches the org contract's declared gates.

**Acceptance Scenarios**:

1. **Given** an org-tier step contract with `gates: [{...}]` on `(mission, action)` and no
   project-tier duplicate, **When** `load_gate_bindings(repo_root, mission, action)` is called,
   **Then** it returns the org contract's gates (not `[]`).
2. **Given** the same fixture, **When** `_build_repository`'s construction is compared to site
   6's, **Then** both resolve `org_dirs` via the identical helper (regression-tested to prevent
   the two from drifting again in a future change).

---

### User Story 4 - A pack author sees which delegation candidates never resolved (Priority: P2)

A pack author writes a step contract whose `delegates_to.candidates` includes a directive id that
does not exist (typo, retired directive, or activation-filtered-out). Today nothing tells them —
`StepContractExecutionResult` computes `unresolved_candidates` and nothing reads it.

**Why this priority**: This is decision D-005's surfacing fix. It is P2, not P1, because it does
not block the delegation mechanism working correctly for candidates that *do* resolve — it closes
an observability gap, not a functional one.

**Independent Test**: Run `StepContractExecutor.execute` against a contract with one candidate
that cannot resolve (e.g. a nonexistent directive id). Capture logger output at `_dispatch_via_composition`. Confirm a WARNING is logged naming the step id and the unresolved
candidate.

**Acceptance Scenarios**:

1. **Given** a step contract with an unresolvable `delegates_to` candidate, **When** the
   composition bridge dispatches it, **Then** a WARNING-level log record is emitted naming the
   step id, contract id, and the unresolved candidate string(s).
2. **Given** a step contract where every candidate resolves, **When** dispatched, **Then** no such
   WARNING is emitted (no false positives).
3. **Given** the shipped built-in `software-dev/specify` contract run against a project with no
   org pack activating the directives it cites outside `action:software-dev/specify` scope,
   **When** dispatched, **Then** the WARNING (if any) accurately reflects the live
   resolved/unresolved split at that moment — not a hardcoded expectation, since activation scope
   affects which of the 7 declared candidates resolve.

---

### User Story 5 - An org pack's `expected-artifacts.yaml` augments the completeness gate for a mission type (Priority: P3)

An org pack ships an `expected-artifacts.yaml` override for a mission type (built-in or its own
custom type), declaring additional required artifacts (e.g. an org-mandated compliance document).
Today, `_resolve_expected_artifacts_slot` (`mission_type_profiles.py:971-996`) and
`ManifestRegistry.load_manifest` (`dossier/manifest.py`) both read exclusively through
`MissionTemplateRepository.default()` — a single-root, built-in-only reader with **no org or
project tier mechanism of any kind** (unlike every other consumer in this issue, this is not a
caller failing to pass an existing parameter — the parameter does not exist).

**Why this priority**: Lowest of the five, by design (D-000(3), D-005-adjacent reasoning): this is
new surface, not a caller-side fix, and the sibling mission `up-mission-type-seam-01KZY1JB`
explicitly deferred the analogous "reconcile `expected-artifacts.yaml` against layered mission
types" question (its C-005) as separate, harder work. This mission delivers a narrow, additive
version rather than re-deferring it a second time, but sequences it last so a time-constrained
implementation still lands US1-US4 first.

**Independent Test**: Configure an org pack with `<org_root>/<mission_type>/expected-artifacts.yaml`
declaring one additional `required_always` artifact. Load the manifest for that mission type via
both `_resolve_expected_artifacts_slot` and `ManifestRegistry.load_manifest`. Confirm the
additional artifact requirement is present in both.

**Acceptance Scenarios**:

1. **Given** an org pack with an `expected-artifacts.yaml` override for `software-dev` declaring
   one extra `required_always` artifact, **When** `ManifestRegistry.load_manifest("software-dev")`
   is called, **Then** the returned manifest includes that extra requirement.
2. **Given** no org override exists for a mission type, **When** the manifest is loaded, **Then**
   behavior is byte-identical to pre-mission (the built-in manifest, unchanged) — the additive
   guarantee.
3. **Given** both an org override and the built-in manifest declare `expected-artifacts.yaml` for
   the same mission type, **When** loaded, **Then** the org file **fully replaces** the built-in
   one for that mission type (whole-file precedence, not field-merge) — matching the precedent set
   for the structurally analogous non-`BaseDoctrineRepository` case in
   `up-mission-type-seam-01KZY1JB`'s Edge Cases section (full per-compound-key replacement, project
   > org > built-in).

### Edge Cases

- **Multiple org packs declaring the same step-contract id.** `MissionStepContractRepository`'s
  inherited `org_dirs` merge (`doctrine/base.py`) already resolves this — later `org_dirs` entries
  override earlier ones for the same id, matching `DoctrineService._org_dirs`'s documented
  contract. This mission does not change that merge semantic; it only makes sure `org_dirs` is
  populated at all five in-scope sites (FR-001, FR-004, FR-005, FR-006, FR-004a).
- **An org pack is configured but its directory does not exist on disk** (e.g. a stale
  `local_path` after a pack was removed). `resolve_org_roots`/`_enumerate_org_pack_paths` already
  return non-existent paths; every fix site MUST filter to `.exists()` before use (existing
  precedent: `charter.doctrine_service_builder._self_resolve_existing_org_roots`, lines 142-152)
  so a stale config entry degrades to "no org contribution" rather than raising.
- **More than one org pack is configured, but `load_validated_graph` only accepts one `org_root`.**
  This is the pre-existing, out-of-scope limitation named in D-000(2)/C-004: FR-002 uses the
  established first-match pattern (`_enumerate_org_pack_paths`), not an all-packs DRG merge. A
  second configured org pack's DRG nodes remain invisible to delegation resolution after this
  mission — documented as a known limitation, not silently left ambiguous.
- **A resolved delegation candidate is legitimately absent** because activation scoping
  (`filter_graph_by_activation`, already applied downstream of the graph load, unchanged by this
  mission) excludes it, not because it doesn't exist. FR-007's WARNING must not be mistaken for an
  authoring error in this case — its message names the candidate and step but does not assert the
  candidate is wrong, since a correctly-cited-but-deactivated candidate is a valid, if inert,
  state.
- **`expected-artifacts.yaml` org override references a mission type with no built-in manifest at
  all** (a wholly org-defined custom mission type). `_resolve_expected_artifacts_slot` must treat
  this as "no built-in baseline, org file is authoritative" rather than requiring a built-in file
  to exist first.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | `StepContractExecutor` threads `org_dirs` into `MissionStepContractRepository` | As an operator with a registered org pack, I want `StepContractExecutor.__init__` (`mission_step_contracts/executor.py:160-162`) to construct `MissionStepContractRepository(org_dirs=..., project_dir=...)` instead of `project_dir` only, so that org-tier step contracts are discoverable at all. | High | Open |
| FR-002 | `StepContractExecutor.execute` threads a resolved `org_root` into `load_validated_graph` | As an operator with a registered org pack, I want `StepContractExecutor.execute` (`executor.py:179`) to call `load_validated_graph(context.repo_root, org_root=<resolved>)` instead of the two-layer default, resolving `org_root` via the existing first-match pattern (`charter.org_pack_discovery._enumerate_org_pack_paths`, per D-000(2)), so that `_resolve_step_delegations` can resolve candidates against org-tier DRG nodes. | High | Open |
| FR-003 | Shared, single resolution helper for the list-shaped `org_dirs` argument | As a maintainer, I want the `org_dirs` resolution logic (existing-path-filtered `resolve_org_roots(repo_root)` joined with `"mission_step_contracts"`) written once and reused by FR-001, FR-004, FR-005, FR-006 — not duplicated four times — so the four sites cannot silently drift from each other the way sites 3/6 already had before this mission. | High | Open |
| FR-004 | `_mission_type_profile_repository`/`_resolve_governance_slot` threads `org_dirs` into `MissionTypeProfileRepository.for_project` | As an operator with a registered org pack, I want the live call at `mission_type_profiles.py:1168` (reached via `_resolve_governance_slot`, `:807`, on every `resolve_mission_type_context` call) to pass `org_dirs` to `for_project`, so that an org-tier `governance-profile.yaml` override is not silently invisible in rendered governance text. This is distinct from, and does not touch, the deliberately built-in-only `action_grain.py:220` call site (D-004). | High | Open |
| FR-005 | `gate_bindings._build_repository` threads `org_dirs` (site 3) | As an operator, I want `_build_repository` (`review/gate_bindings.py:165-168`) to construct `MissionStepContractRepository` with the same `org_dirs` FR-003 resolves, so that an org-tier contract's `gates:` block fires at WP review-transition time instead of resolving delegations correctly while never gating anything. | High | Open |
| FR-006 | `_resolve_runtime_contract_for_step` threads `org_dirs` (site 4) | As an operator, I want `_resolve_runtime_contract_for_step` (`runtime_bridge_composition.py:252-296`) to construct `MissionStepContractRepository` with FR-003's `org_dirs`, so a custom mission's org-tier `contract_ref` resolves at live dispatch time. | High | Open |
| FR-006a | `_resolve_contract_refs` threads `org_dirs` (site 5) | As an operator, I want `_resolve_contract_refs` (`mission_loader/command.py:204-249`) to construct `MissionStepContractRepository` with FR-003's `org_dirs`, so mission-load-time `contract_ref` validation matches FR-006's runtime resolution exactly (same org packs, same precedence) — closing the false-negative described in User Story 2. | High | Open |
| FR-007 | Surface unresolved delegation candidates as a named, non-blocking signal | As a pack author, I want `_dispatch_via_composition` (`runtime_bridge_composition.py`, the sole production reader of `StepContractExecutionResult`) to log a WARNING per step carrying 1+ unresolved `delegates_to` candidates — naming the step id, contract id, and the candidate string(s) — instead of the values being computed and read by nothing, so a dead citation is discoverable without reading source. Decision: surface, not delete (D-005). | High | Open |
| FR-008 | Org-tier `expected-artifacts.yaml` override, whole-file precedence | As an operator with a registered org pack, I want `_resolve_expected_artifacts_slot` (`mission_type_profiles.py:971-996`) and `ManifestRegistry.load_manifest` (`dossier/manifest.py:178-213`) to additionally check each configured, existing org root for `<org_root>/<mission_type>/expected-artifacts.yaml` (mirroring the built-in file's own `<missions_root>/<mission_type>/expected-artifacts.yaml` shape) and, when present, use it in place of (not merged with) the built-in manifest for that mission type, so an org pack can require additional mission-completeness artifacts. This establishes a new org-tier convention where none existed (D-000(3)) — it is not caller-side parameter threading. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Every defect fix is proven by a before/after measurement, not an assertion | Each of FR-001, FR-002, FR-004, FR-005, FR-006, FR-006a, FR-008 MUST have a committed regression test that fails (proving the pre-fix silent-scope-loss) before the fix and passes after, using a real synthetic org-pack fixture (mirroring `tests/charter/test_org_scan_dirs_activation_regression.py`'s shape) — not a mock that assumes the org layer is wired. For FR-002 specifically, the test MUST assert a DRG node-count delta (the 347→348 methodology verified live in this session, D-000(4)) in addition to URN presence, so the proof is a number that changes, not merely "no exception was raised." | Reliability | High | Open |
| NFR-002 | No silent success in the new/changed paths | None of FR-001 through FR-008 may introduce a path that degrades to built-in/project-only scope and reports success without any signal. Where a configured org root does not exist on disk, the code MUST proceed (existing-path filtering, per Edge Cases) but MUST NOT be indistinguishable, in a test, from "org tier was never consulted." | Reliability | High | Open |
| NFR-003 | Multi-org-pack declared-order precedence preserved | Every `org_dirs`-shaped fix (FR-001, FR-004, FR-005, FR-006, FR-006a) MUST preserve the existing "later configured org pack overrides an earlier one for the same id" contract already documented at `doctrine/service.py:47-52`, verified by a regression test with two org packs declaring the same step-contract id. | Reliability | Medium | Open |
| NFR-004 | Coverage floors held | `src/specify_cli/mission_loader/command.py` (FR-006a) keeps the existing `tests/unit/mission_loader/` + `tests/integration/test_mission_run_command.py` `--cov-fail-under=90` gate (`.github/workflows/ci-quality.yml:1450-1457`) green. Every changed line in `src/charter/*`, `src/doctrine/*`, and `src/runtime/next/*` (FR-001, FR-002, FR-004, FR-006, FR-007, FR-008) meets the critical-path `diff-cover --fail-under=90` gate (`ci-quality.yml:3333-3397`). No file under `src/kernel/` is touched by this mission (verified: none of the six-plus-one call sites live there), so the kernel 90% floor (`module-kernel.yml`) is unaffected, not merely "expected to pass." | Reliability | High | Open |
| NFR-005 | Architectural gates pass with zero new allowlist/suppression entries | `tests/architectural/test_layer_rules.py` and every `tests/architectural/test_charter_sole_door_*.py` gate MUST pass unmodified — no new exemption, no new allowlist row. Verified in this session: none of these gates currently constrain `MissionStepContractRepository` construction (D-003), so this is a negative assertion the plan phase must keep true, not one already guaranteed. | Architecture | High | Open |
| NFR-006 | Terminology guard passes | `pytest tests/architectural/test_no_legacy_terminology.py` passes on every changed file under `src/doctrine/` (per this repo's own pre-push guidance, `AGENTS.md` § Code Style) before the PR is opened. | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No change to activation filtering | `filter_graph_by_activation` and `PackContext.from_config` (already applied downstream of the graph load in `executor.py:182-186`) are unchanged by this mission. FR-002 only makes org-tier nodes *reachable*; whether a reachable node is *usable* remains governed by existing activation scoping. | Technical | High | Open |
| C-002 | Site 2 (`step_contracts.py:308`) is explicitly untouched | Per D-001 verdict #2: `resolve_step_contract_ids`'s bare-constructor default stays built-in-only. No change, no new test, no widened scope. | Technical | High | Open |
| C-003 | `MissionTemplateRepository` is not refactored into a `BaseDoctrineRepository` subclass | FR-008 adds a narrow, additive org-file check alongside the existing built-in-only reader; it does not restructure `MissionTemplateRepository`'s single-root design, add a new `ArtifactKind`, or change any of its other methods (`get_command_template`, `get_content_template`, `get_action_index`, etc.) — those stay exactly as they are. | Technical | High | Open |
| C-004 | `load_validated_graph`'s single-org-root limitation is inherited, not fixed | FR-002 uses the existing first-match-org-pack resolution (D-000(2)). Making `load_validated_graph` merge more than one org DRG root is out of scope — a separate, larger mission's territory. | Technical | Medium | Open |
| C-005 | `packs/internal/drg/fragment.yaml`'s naming mismatch is not fixed here | Per D-000(5): this repo's own internal org pack does not currently match `load_graph_or_dir`'s `*.graph.yaml` naming convention. Unrelated to #3516, not fixed by this mission, and does not block verification (the verification fixtures use correctly-named synthetic packs). | Technical | Low | Open |
| C-006 | Mission size is L, not M | Estimated ~170-210 production `src/` LOC (five call-site fixes at roughly 10-20 LOC each, plus FR-007's surfacing logic and FR-008's new org-file-check logic) and ~250-300 test LOC across the eight FRs' regression tests. The operator brief's "~80 LOC" estimate covered only defects (1)/(2)/(4) at "both consumers" (two sites); this spec's D-001 audit found five in-scope call sites (not two) plus the FR-004 governance-profile gap the brief's citation actually pointed at, plus FR-008's materially larger, novel-surface expected-artifacts fix. See the mission report for the full reconciliation. | Planning | High | Open |

### Key Entities

- **Org pack (`OrgPackConfig`)**: a registered organisation-tier doctrine source
  (`.kittify/config.yaml`'s `doctrine.org.packs`), resolved to an `effective_root` Path via
  `resolve_org_roots`/`_enumerate_org_pack_paths`. Zero, one, or many may be configured per
  project.
- **`org_dirs` (list shape)**: one `Path` per configured, existing org pack, each pointing at
  `<org_root>/<artifact-kind-plural>` (e.g. `mission_step_contracts`). Consumed by every
  `BaseDoctrineRepository` subclass constructor, including `MissionStepContractRepository` and
  `MissionTypeProfileRepository`.
- **`org_root` (single-path shape)**: exactly one `Path`, the first existing configured org pack
  root, consumed by `load_validated_graph`. Structurally distinct from `org_dirs` — see D-000(2).
- **Delegation candidate**: a string in a step contract's `delegates_to.candidates` list, resolved
  against the merged DRG's action-context URN set by `StepContractExecutor._resolve_step_delegations`
  into either a `ResolvedStepDelegation` or an entry in `unresolved_candidates`.
- **Expected-artifacts manifest**: the parsed `<mission_type>/expected-artifacts.yaml` mapping,
  currently sourced exclusively from `MissionTemplateRepository`'s single built-in root; FR-008
  adds an org-tier override read alongside it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a fixture project with a synthetic org pack (one directive node), the DRG node
  count returned by `load_validated_graph` increases from the project's built-in+project baseline
  to baseline+1 when `org_root` is supplied by FR-002's resolution — the exact mechanism verified
  live in this checkout during spec authoring (347→348, D-000(4)) — asserted as a count delta in
  a committed regression test, not merely "no exception."
- **SC-002**: In the same fixture, `MissionStepContractRepository.get_by_action(...)` for an
  org-only step contract returns `None` before FR-001 (regression test committed red) and the
  contract after (green) — the exact True/False mechanism verified live in this session.
- **SC-003**: `load_gate_bindings` (FR-005) and `_resolve_runtime_contract_for_step`/`_resolve_contract_refs`
  (FR-006/FR-006a) each resolve the identical org-tier fixture contract used for SC-002, proving
  lockstep rather than three independently-passing but potentially-divergent implementations —
  verified by a single shared fixture reused across all three tests (not three separate fixtures
  that could silently drift).
- **SC-004**: A step contract with one unresolvable `delegates_to` candidate produces exactly one
  WARNING-level log record naming the step id and candidate (FR-007), captured via `caplog` in a
  regression test; a step contract where every candidate resolves produces zero such records in
  the same test run (negative case, same test).
- **SC-005**: An org-tier `expected-artifacts.yaml` override (FR-008) changes
  `ManifestRegistry.load_manifest(...).get_step_ids()` / `required_always` count relative to the
  built-in-only baseline for the same mission type, in the same process, before and after the org
  file is added to the fixture — a count/content delta, not an assertion that the call succeeded.
- **SC-006**: `tests/architectural/test_charter_sole_door_*.py` and `tests/architectural/test_layer_rules.py`
  pass unmodified (zero new allowlist entries) after all eight FRs land (NFR-005).
- **SC-007**: The mission_loader coverage gate (`--cov=src/specify_cli/mission_loader --cov-fail-under=90`)
  and the critical-path diff-coverage gate (`--include src/charter/* src/doctrine/* src/runtime/next/* --fail-under=90`)
  both pass in CI on the mission's PR (NFR-004) — reported by CI, not self-asserted by the
  implementer.

## Out of Scope

Deliberately **not** part of this mission, so an implementer does not wander:

- Site 2 (`doctrine/missions/step_contracts.py:308`, `resolve_step_contract_ids`'s bare default)
  — stays built-in-only; see C-002, D-001 verdict #2.
- Making `load_validated_graph` merge more than one org DRG root — see C-004.
- Restructuring `MissionTemplateRepository` into a `BaseDoctrineRepository` subclass, or adding a
  new `ArtifactKind` for mission-scoped assets generally — see C-003. FR-008 is intentionally the
  narrowest additive slice, not a general redesign.
- `action_grain.py`'s deliberately built-in-only `MissionTypeProfileRepository` call — see D-004,
  matching the sibling mission's own C-006 precedent.
- Fixing `packs/internal/drg/fragment.yaml`'s naming mismatch against `load_graph_or_dir` — see
  C-005; unrelated pre-existing defect in this repo's own internal pack, not part of #3516.
- Any change to `filter_graph_by_activation` or `PackContext` activation semantics — see C-001.
- Widening `ALLOWED_MISSION_TYPES`, the mission-type roster layering seam, or anything already
  covered by the separate, prior mission `up-mission-type-seam-01KZY1JB` — that mission's own
  C-002/C-003/C-005 boundaries are inherited unchanged here, not reopened.

## Mission Sizing

**Size class: L.** See C-006 for the full reconciliation against the operator brief's "~80 LOC /
M-sized" estimate. The corrected estimate (~170-210 production LOC, ~250-300 test LOC) reflects
two findings this spec's investigation established that the brief did not have: (a) five in-scope
call sites, not two ("both consumers"), once `gate_bindings.py`, `runtime_bridge_composition.py`'s
`_resolve_runtime_contract_for_step`, and `mission_loader/command.py`'s `_resolve_contract_refs`
are correctly counted alongside the executor; and (b) the issue's defect (3) is actually two
defects of very different cost — a cheap caller-side fix (FR-004, governance-profile) and a
materially larger, novel-surface fix with no existing parameter to thread (FR-008,
expected-artifacts.yaml) — which the brief's single citation conflated into what looked like one
small item.

## Test Strategy

**What proves each fix, concretely:**

- **FR-001/FR-002 (executor)**: `tests/specify_cli/mission_step_contracts/test_executor.py` and
  `test_executor_activation.py` gain a fixture-driven org-pack scenario (mirroring
  `_write_org_directive_fixture`'s shape) asserting the SC-001/SC-002 count and True/False deltas.
  A reviewer confirms org-tier resolution actually works — not merely compiles — by checking out
  the fixture's pre-fix commit in isolation and confirming the new test is RED there (same
  red-first mechanical-falsifiability discipline the sibling mission's NFR-005 established), then
  GREEN on the fix commit.
- **FR-004 (governance profile)**: a new test in `tests/charter/test_mission_type_profiles.py`
  (or sibling) constructs an org-pack `governance-profile.yaml` override and asserts
  `resolve_mission_type_context(...).governance_text` reflects it — not the built-in baseline.
- **FR-005/FR-006/FR-006a (gate bindings, runtime dispatch, mission-load validation)**: one shared
  test fixture (SC-003) is exercised by three separate test functions in
  `tests/specify_cli/review/`, `tests/runtime/`, and `tests/unit/mission_loader/` respectively, so
  a future change that breaks lockstep between the three fails at least one of them without
  needing a fourth cross-cutting integration test to notice.
- **FR-007 (surface unresolved candidates)**: `caplog`-based assertion in
  `tests/runtime/test_bridge_composition.py`, both positive (WARNING present, correct content)
  and negative (no WARNING when everything resolves) cases in the same test, per SC-004.
- **FR-008 (expected-artifacts org tier)**: `tests/charter/test_mission_type_profiles.py` and
  `tests/dossier/` (wherever `ManifestRegistry` is currently tested) both gain an org-override
  fixture asserting the SC-005 count/content delta, plus a whole-file-precedence test (org file
  present alongside a built-in file for the same type → org wins entirely, not merged).
- **Coverage/architecture**: NFR-004/NFR-005/SC-006/SC-007 are enforced by existing CI gates
  (`ci-quality.yml`'s mission-loader and critical-path diff-coverage jobs, the sole-door and
  layer-rule architectural suites) — no new gate is introduced by this mission; the requirement is
  that the existing gates stay green with zero new suppressions or allowlist rows.
- **Reviewer verification checklist** (beyond "tests pass"): for each of FR-001, FR-002, FR-004,
  FR-005, FR-006, FR-006a, FR-008, a reviewer independently re-runs the specific before/after
  count or True/False assertion named in Success Criteria against the PR branch locally, not
  merely reads the CI checkmark — matching this mission's own Verification Bar (every defect must
  be proven by a number or boolean that changes, per the operator brief's own standard).

## Terminology Note

This mission is about **doctrine tier resolution** (built-in / org / project), not about renaming
or restructuring any existing artifact kind. No `feature*` alias is introduced by any requirement
above; "feature" does not appear as a domain term anywhere in this spec.
