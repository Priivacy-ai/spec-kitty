# Org Doctrine Profile Integrity Activation Closure

**Mission ID**: `01KT1TV1KPRFH00FMPBM4JWGHZ`
**Mission slug**: `org-doctrine-profile-integrity-activation-closure-01KT1TV1`
**Mission type**: software-dev
**Planning / merge target**: `mission/org-doctrine-profile-integrity-activation-closure`
**Parent epic**: Priivacy-ai/spec-kitty#1111 - 3.2.0 release work: Charter / Doctrine enhancement and remediation
**Primary source issues**: #1583, #1584, #1557
**Additional findings**: agent-profile context selector + charter catalog visibility (see Scenarios 8-9, FR-022..FR-026)

---

## Overview

This mission closes the next release-critical slice of the charter and doctrine work after the charter activation layer landed. The new activation model depends on a trustworthy doctrine catalog: profile inheritance must be represented with the right graph relation, invalid org-pack profiles must be visible instead of silently disappearing, and activation commands must validate, warn, cascade, and gate runtime use consistently.

The slice intentionally starts with the org-pack profile integrity issues:

1. #1583 - add a DRG relation for agent profile lineage, so org packs can express profile specialization without abusing runtime delegation edges.
2. #1584 - retain and surface agent profile load failures, so `doctor doctrine` cannot report a pack as healthy while invalid profiles are missing from repository results.
3. #1557 - finish the charter activation follow-on deferred from PR #1535: artifact ID validation, no-cascade warnings, cascade activation, shared-safe cascade deactivation, OperationalContext production wiring, and cleanup of known dead-code/bookkeeping findings.

Template discoverability (#1333) remains important but is not in this mission. It adds a new artifact surface and should follow after the current activation/catalog integrity path is dependable.

---

## User Scenarios and Testing

### Scenario 1 - Org pack profile lineage validates

An organisation pack author defines a domain-specific agent profile that inherits from a built-in analyst profile. The pack declares a profile lineage relation in its DRG fragment. Validation accepts the relation as structural profile inheritance, and consumers do not confuse it with runtime work delegation.

**Acceptance signal**: a fixture pack with an agent profile lineage edge validates, and traversal that asks for runtime delegation targets does not return lineage-only targets.

### Scenario 2 - Invalid profiles are visible

An operator upgrades Spec Kitty and configures an org pack whose agent profiles were authored against an older schema. Some profile YAML files now fail validation. The operator runs profile listing and doctrine diagnostics.

**Acceptance signal**: valid profiles are still returned, invalid profile files are retained in a diagnostic list with layer/path/error details, and `spec-kitty doctor doctrine` human and JSON output report the invalid profiles.

### Scenario 3 - Unknown activation IDs fail before mutation

An operator runs `charter activate directive nonexistent-directive`. The command checks the active doctrine catalog before writing activation state.

**Acceptance signal**: the command exits non-zero, names the missing ID and kind, lists or points to available IDs, and leaves configuration unchanged.

### Scenario 4 - No-cascade warning points to skipped references

An operator activates an artifact that references other doctrine artifacts without passing `--cascade`. The command completes the requested direct activation but warns that referenced artifacts were not cascaded.

**Acceptance signal**: output names the target, the skipped reference kinds, and the next command or consistency check to resolve coherence.

### Scenario 5 - Cascade activation follows selected reference kinds

An operator runs `charter activate mission-type research --cascade agent-profile,tactic`. Only referenced agent profiles and tactics are activated alongside the mission type.

**Acceptance signal**: the command reports activated and skipped artifacts by kind, and subsequent `charter list` reflects exactly the selected cascade scope.

### Scenario 6 - Cascade deactivation protects shared references

An operator deactivates an artifact with cascade enabled. Referenced artifacts that are exclusively owned by the deactivated artifact are removed, but artifacts still referenced by other active artifacts remain active and are reported as shared.

**Acceptance signal**: no shared artifact is silently removed; skipped entries include the active artifact that still references them.

### Scenario 7 - Runtime context is populated at lifecycle boundaries

A work package claim or `next` runtime decision needs active model, profile, role, activity, or technology context. The runtime builds an OperationalContext at the entry point instead of returning an all-empty stub.

**Acceptance signal**: production call sites populate the context, guard methods raise actionable errors when required fields are absent, and the previously allowlisted symbols have live callers.

### Scenario 8 - Agent profiles are reachable through the charter context selector

An operator (or agent prompt) wants to inline a specific agent profile into workflow context and runs `spec-kitty charter context --include agent-profile:<id>`, using the same hyphenated kind name accepted by `charter activate`. Today this fails with `Unsupported --include selector kind 'agent-profile'` because the selector renderer only matches the underscore form `agent_profile` and the kind name is not normalized; profiles are reachable only through the Python API or by reading the YAML files directly.

**Acceptance signal**: `charter context --include agent-profile:<id>` renders the named profile (in both human and `--json` output), the `--include` help advertises the agent-profile kind, and hyphenated kind names resolve consistently with `charter activate`.

### Scenario 9 - Operators can see every available artifact, built-in or packaged

An operator wants a complete inventory of what they could activate, not just what ships built-in. They run `spec-kitty charter list --all`. Today only `--show-available` exists, and its availability scan reads built-in doctrine alone (org-pack and project layers are ignored), so packaged artifacts are invisible in the catalog.

**Acceptance signal**: `charter list --all` lists every artifact per kind across built-in, organisation-pack, and project layers with its source layer, and the availability computation no longer silently drops non-built-in artifacts.

### Scenario 10 - Org packs can augment every doctrine kind, including workflow topology

An org-pack author declares `enhances: <built-in-id>` on a mission step contract (and separately on a directive, a toolguide, and a mission type) to field-merge into the shipped artifact. Today these are rejected: the step-contract, directive, toolguide, and mission-type schemas use `extra="forbid"` and never gained the `enhances`/`overrides` fields, so the augmentation vocabulary covers only five of the doctrine kinds. The author expects the same authoring contract that already works for tactics and profiles.

**Acceptance signal**: a fixture pack that declares `enhances`/`overrides` on a directive, toolguide, mission step contract, and mission type validates without the same-ID override advisory, the DRG auto-emits the corresponding `enhances`/`overrides` edge for the DRG-resident kinds, and for topology-bearing kinds (step contracts, mission types) the merged result preserves action-sequence ordering and step I/O contracts rather than silently corrupting them.

---

## Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-001 | The DRG relation vocabulary SHALL include a relation for structural profile lineage, named `specializes_from` unless implementation research finds `extends` is materially better and documents the choice. | Must | Proposed |
| FR-002 | The profile-lineage relation SHALL be distinct from runtime delegation; consumers that interpret `delegates_to` as work handoff must not receive profile lineage edges as delegation edges. Per C-009, lineage consumers (incl. the agent-profile hierarchy resolver) SHALL resolve via DRG traversal rather than re-reading the `specializes_from` field, subject to the R-012 layering decision (OQ-2). | Must | Proposed |
| FR-003 | DRG validation SHALL accept profile-to-profile lineage edges from shipped, organisation, and project graph fragments. | Must | Proposed |
| FR-004 | DRG documentation and fixtures SHALL explain the semantics of profile lineage and its difference from delegation, enhancement, override, and replacement. | Should | Proposed |
| FR-005 | Agent profile loading SHALL retain structured diagnostics for skipped profile files, including source layer, filesystem path, discovered profile ID when available, and validation or parse error summary. | Must | Proposed |
| FR-006 | `AgentProfileRepository.list_all()` SHALL continue to return valid loaded profiles only, while a dedicated diagnostic surface exposes skipped profiles without requiring callers to rescan the filesystem. | Must | Proposed |
| FR-007 | `DoctrineService.agent_profiles` SHALL preserve profile load diagnostics for all configured layers so diagnostics remain available after repository construction. | Must | Proposed |
| FR-008 | `spec-kitty doctor doctrine` human output SHALL report invalid or skipped agent profiles per source layer and pack. | Must | Proposed |
| FR-009 | `spec-kitty doctor doctrine --json` SHALL include machine-readable invalid-profile diagnostics with stable fields for layer, path, profile ID if known, and error summary. | Must | Proposed |
| FR-010 | A pack with invalid agent profiles SHALL NOT be presented as fully healthy by doctrine diagnostics when its DRG node and edge counts are otherwise valid. | Must | Proposed |
| FR-011 | `charter activate <kind> <id>` SHALL validate that the artifact ID exists for the requested kind before mutating activation state. | Must | Proposed |
| FR-012 | Unknown activation IDs SHALL fail with an actionable message naming the kind, missing ID, and recovery path; no configuration write may occur on failure. | Must | Proposed |
| FR-013 | Running `charter activate` without `--cascade` SHALL warn about referenced artifacts that were not cascaded, per the #1557 FR-006 contract. | Must | Proposed |
| FR-014 | `charter activate <kind> <id> --cascade <scope>` SHALL preserve the requested cascade scope and activate referenced artifacts only for selected kinds, with `all` as the explicit all-kind shorthand. | Must | Proposed |
| FR-015 | `charter deactivate <kind> <id> --cascade <scope>` SHALL deactivate only exclusively referenced artifacts and SHALL skip shared artifacts with a reason. | Must | Proposed |
| FR-016 | Cascade activation and deactivation SHALL use the active DRG/catalog reference model rather than hardcoded per-kind special cases where a graph relation exists. | Must | Proposed |
| FR-017 | `build_operational_context()` SHALL return populated OperationalContext values at work package claim and runtime decision entry points when those values are known. | Must | Proposed |
| FR-018 | `require_active_profile()` and `require_active_role()` SHALL raise ContextPreconditionError with actionable messages when required fields are absent. | Must | Proposed |
| FR-019 | OperationalContext symbols currently allowlisted as deferred work SHALL be removed from dead-symbol allowlists after production wiring lands. | Must | Proposed |
| FR-020 | Known cleanup items from #1557 SHALL be resolved: delete obsolete activation override code, remove orphaned dead-symbol categories, remove stale `activate_cmd` export, and correct FR-008 comment misattribution. | Must | Proposed |
| FR-021 | Existing charter activation behavior from PR #1535 SHALL remain backward compatible for projects with no explicit activation restrictions. | Must | Proposed |
| FR-022 | `charter context --include agent-profile:<id>` SHALL resolve and render the named agent profile in both human and `--json` output, instead of failing with an unsupported-selector-kind error. | Must | Proposed |
| FR-023 | The `--include` selector parser SHALL normalize hyphenated kind names to their canonical doctrine kind (e.g. `agent-profile` -> `agent_profile`, `mission-step-contract` -> `mission_step_contract`) so kind names are consistent with `charter activate`/`deactivate`. | Must | Proposed |
| FR-024 | The `charter context --include` help text SHALL advertise the agent-profile selector (alongside the existing directive/styleguide/section examples) so the supported kinds are discoverable. | Should | Proposed |
| FR-025 | `charter list --all` SHALL list every available artifact per kind across built-in, organisation-pack, and project layers, annotated by source layer; `--all` implies and supersedes `--show-available`. | Must | Proposed |
| FR-026 | `CharterPackManager.list_available()` SHALL include organisation-pack and project doctrine artifacts in addition to built-in artifacts, removing the built-in-only scan, so availability is not understated for packaged artifacts. | Must | Proposed |
| FR-027 | The operator-facing kind vocabulary used by `charter context --include`, `activate`, `deactivate`, and `list` SHALL resolve through a single canonical kind mapping (building on `doctrine.artifact_kinds.ArtifactKind`) rather than re-declaring the kind set per command, so hyphenated kind tokens normalize consistently and FR-022/FR-023/FR-025/FR-026 are not per-kind special cases. See research R-009 (CL-1..CL-5). | Should | Proposed |
| FR-028 | Augmentation/lineage relationships (`overrides`/`enhances`, and `specializes_from`) SHALL be expressible for the `Directive`, `Toolguide`, mission step contract, and mission type kinds so an org-pack artifact declaring them against a built-in of the same kind validates instead of being rejected. Per C-009, the relationship is canonically a DRG edge; any per-artifact field added to these models (and mirrored JSON Schemas) is an authoring projection that emits the edge, not a second authority. See research R-010 and R-012. | Must | Proposed |
| FR-029 | Field-merge semantics for topology-bearing kinds (mission step contracts and mission types) under `enhances` SHALL be explicitly defined and consistent with ADR `2026-05-16-1-doctrine-layer-merge-semantics.md`: it MUST specify which fields field-merge versus replace, and MUST NOT silently corrupt action-sequence ordering or step input/output contracts; `overrides` remains a full replacement. | Must | Proposed |
| FR-030 | The DRG auto-emit table (`_AUGMENTATION_PLURAL_TO_KIND`) and the pack-validator augmentation set (`_AUGMENTATION_PLURAL_KINDS`) SHALL cover all augmentation-eligible kinds and SHALL derive from a single shared source rather than two hand-synced copies. | Must | Proposed |
| FR-031 | The pack validator SHALL apply the existing intent-aware collision behavior (suppress the same-ID advisory when intent is declared, hard-error on unknown `enhances`/`overrides` target, `intent_conflict` when both are declared) uniformly to the newly-covered kinds, at parity with the original five. | Must | Proposed |
| FR-032 | Mission-type augmentation SHALL be resolved per research R-010: either the org-pack DRG canonical kind universe (`_ORG_DRG_CANONICAL_KINDS`) is expanded to include mission types as a C-009-binding change with the contract-test sweep updated, or a separate mission-type augmentation path is defined; mission types MUST NOT be silently dropped from augmentation coverage. | Must | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Doctrine diagnostics for profile load errors SHALL remain cheap enough for normal operator use. | `spec-kitty doctor doctrine` completes in <= 2 seconds on built-in doctrine plus a representative one-pack org fixture. | Proposed |
| NFR-002 | Profile load diagnostics SHALL be deterministic. | Re-running the same repository load over the same files yields the same sorted diagnostic records. | Proposed |
| NFR-003 | Activation failure paths SHALL be non-mutating. | Tests prove configuration bytes are unchanged after unknown-ID activation failure. | Proposed |
| NFR-004 | Runtime lifecycle precondition checks SHALL not create worktrees or emit status transitions before failure. | Inactive-profile and missing-context precondition tests observe zero new worktree paths and zero new status events. | Proposed |
| NFR-005 | Existing shipped profile loading SHALL remain healthy. | All built-in agent profiles load with zero diagnostic errors. | Proposed |
| NFR-006 | Architectural boundaries SHALL remain intact. | Existing layer-rule and dead-symbol architectural suites pass after the mission. | Proposed |
| NFR-007 | Adding the `overrides`/`enhances` augmentation fields SHALL NOT regress loading of existing artifacts. | Zero fixture failures loading every existing directive, toolguide, mission step contract, and mission type YAML in the repo (mirrors #1291 NFR-004). | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The term `delegates_to` remains reserved for runtime work handoff; it must not be used to encode profile inheritance. | Binding |
| C-002 | Invalid agent profiles must not be silently dropped from operator diagnostics, even if valid profiles from the same pack load successfully. | Binding |
| C-003 | The profile repository may expose degraded diagnostics, but invalid profiles must not be treated as runnable/assignable profiles unless a future mission defines a typed degraded state. | Binding |
| C-004 | `charter activate` and `charter deactivate` must not mutate configuration after validation or cascade precondition failure. | Binding |
| C-005 | Cascade deactivation must never remove an artifact still referenced by another active artifact. | Binding |
| C-006 | Runtime OperationalContext wiring must not introduce a dependency from doctrine modules to charter or specify_cli modules. | Binding |
| C-007 | The mission branch `mission/org-doctrine-profile-integrity-activation-closure` is the planning/base/merge target for this mission. | Binding |
| C-008 | Org-pack/project root resolution for `list_available()` and the context selector MUST stay in the `specify_cli` layer and be passed as data into `charter`; `charter` must not import `specify_cli` (ADR 2026-03-27-1), consistent with how `charter context` already injects `org_root`. | Binding |
| C-009 | The DRG is the canonical source of truth for doctrine relationships. Relationship consumers SHALL resolve via DRG traversal; per-artifact relationship fields (`enhances`/`overrides`/`specializes_from`) are authoring projections that emit DRG edges, not independent authorities. New relationship types SHALL be added to the DRG relation vocabulary rather than as per-kind schema fields. See research R-012 (incl. layering OQ-2). | Binding |

---

## Success Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-001 | Org-pack authors can model profile inheritance without corrupting delegation semantics. | A fixture with `specializes_from` profile edges validates and delegation traversal remains unchanged. |
| SC-002 | Operators can identify profile files broken by schema changes without bespoke diff scripts. | `doctor doctrine --json` reports every planted invalid profile file with path/layer/error fields. |
| SC-003 | A mixed-validity org pack is visibly degraded rather than falsely healthy. | Human doctor output includes an invalid-profile section for the pack while still listing valid profiles. |
| SC-004 | Unknown activation IDs cannot enter charter activation state. | Unknown-ID CLI test exits non-zero and verifies unchanged config bytes. |
| SC-005 | Activation without cascade gives enough guidance to preserve pack coherence. | No-cascade CLI test asserts skipped-reference warning and suggested recovery command. |
| SC-006 | Cascade activation and deactivation honor explicit scope and shared-reference safety. | CLI or service tests cover selected-kind activation, `all`, exclusive deactivation, and shared skip reporting. |
| SC-007 | OperationalContext is no longer a dead extension point. | Production call-site tests prove active profile/role/activity are populated where available and guard methods fail loudly when absent. |
| SC-008 | The mission clears inherited cleanup debt from #1557. | Dead-symbol and layer-rule tests pass without the deferred allowlist entries targeted by this mission. |
| SC-009 | Agent profiles are reachable through the documented context selector. | A CLI test asserts `charter context --include agent-profile:<id>` renders the profile in human and JSON output, and the unsupported-kind path is no longer reached for hyphenated kinds. |
| SC-010 | The charter catalog reflects the full activatable surface. | A `charter list --all` test asserts built-in, org-pack, and project artifacts all appear with their source layer for at least one fixture pack. |
| SC-011 | Augmentation vocabulary covers every doctrine kind. | Fixture packs declaring `enhances`/`overrides` on a directive, toolguide, mission step contract, and mission type validate, auto-emit the augmentation edge for DRG-resident kinds, and pass the topology-integrity assertion for step contracts and mission types. |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| DRG relation | The typed edge relation used to describe how doctrine artifacts relate to each other. |
| Agent profile lineage | A structural relationship where one agent profile inherits from or specializes another. |
| Agent profile load diagnostic | A retained record explaining why a profile file was skipped during repository loading. |
| Activation kind | A user-facing doctrine artifact category accepted by charter activation commands, such as `directive`, `tactic`, or `agent-profile`. |
| Cascade scope | The explicit set of artifact kinds to include when cascading activation or deactivation. |
| OperationalContext | Runtime invocation context describing the active model, profile, role, activity, and technology signals available at an agent boundary. |

---

## Dependencies and Assumptions

- The mission starts from upstream `main` at `518997ddd`, which includes PR #1576 transactional status emits.
- PR #1535 delivered the base charter activation layer and explicitly deferred the #1557 follow-on scope.
- #1583 and #1584 are treated as prerequisites for trustworthy org-pack activation because activation validation depends on accurate graph and profile catalog state.
- #1333 is deferred to a later template-resolution mission.

---

## Out of Scope

- Adding a full ADR primitive (#1040), beyond preserving any existing ADR-enabler notes.
- Adding doctrine template listing/resolution (#1333).
- Changing profile schema compatibility rules beyond making failures observable.
- Allowing invalid profiles to participate in runtime assignment.
- Redesigning the full workflow sequence model, already closed separately under #682.
