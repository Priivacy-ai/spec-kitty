# Mission Specification: Templates as Mission Configuration

**Mission ID**: `01KXMS1GZVEZ4TPWW9S8G9W9FD`  
**Mission Type**: `software-dev`  
**Status**: Ready for implementation
**Source**: [Priivacy-ai/spec-kitty issue 2658](https://github.com/Priivacy-ai/spec-kitty/issues/2658)  
**Parent Epic**: [Issue 2652](https://github.com/Priivacy-ai/spec-kitty/issues/2652)

## Purpose

Spec Kitty maintainers need each activated mission type to carry its own content-template configuration through the existing doctrine-to-charter-to-core authority chain. Today the doctrine mission-type artefact declares an artifact-key-to-filename mapping, but the resolved mission-type context leaves that mapping unavailable and template readers still rely on software-development defaults. This mission completes the reserved template configuration slot without expanding into the epic's later enumeration and mission-tree retirement work.

## User Scenarios & Testing

### Scenario 1 — Resolve templates declared by an activated mission type

**Primary actor**: A Spec Kitty maintainer or runtime flow resolving a mission artifact template.

**Trigger**: An activated mission type declares a template filename for the requested artifact kind.

**Expected outcome**: The resolved mission-type context exposes the exact declared mapping, and the template reader selects the declared file through that context.

**Acceptance scenarios**:

1. **Given** an activated mission type declares templates for `spec` and `plan`, **when** its mission-type context is resolved, **then** both keys and filenames match the doctrine artefact exactly.
2. **Given** the resolved mapping contains the requested artifact key, **when** a template reader requests that artifact, **then** it resolves the mapped filename while preserving the existing override precedence for that file.

### Scenario 2 — Refuse undeclared template inference

**Primary actor**: A maintainer authoring or activating a mission type without built-in content templates.

**Trigger**: A template-dependent flow requests an artifact whose activated mission type has no template mapping, or has no entry for that artifact kind.

**Expected outcome**: The flow reports the template as unavailable or fails with an actionable diagnostic; it never substitutes a software-development template.

**Acceptance scenarios**:

1. **Given** an activated mission type has no template mapping, **when** a content template is requested, **then** no template is inferred from `software-dev-default` or another mission type.
2. **Given** a mapping exists but omits the requested artifact key, **when** that artifact is requested, **then** the result identifies the mission type and missing artifact kind rather than selecting an unrelated file.

### Scenario 3 — Preserve current software-development behavior during the swap

**Primary actor**: Existing software-development mission users.

**Trigger**: Existing specification and planning flows resolve their content templates after the authority swap.

**Expected outcome**: The same effective template files and content are selected as before the swap, with no user-visible change.

**Acceptance scenarios**:

1. **Given** the shipped software-development mission type, **when** its specification and planning templates are resolved before and after the swap, **then** the effective results are identical.
2. **Given** a project-level or user-level file override that currently wins for a mapped filename, **when** resolution uses the mission-type mapping, **then** that override continues to win.

## Edge Cases

- An activated mission type declares `template_set: null`.
- A template mapping is present but does not contain the requested artifact kind.
- A mapping refers to a filename that cannot be found in any permitted resolution tier.
- An unactivated mission type exists on disk and declares templates.
- A project override supplies a file for a mapped filename but not for other mapped files.
- A typeless or legacy mission reaches a template reader; this slice must not introduce a new implicit mission-type inference while the separate fallback-removal issue remains pending.

## Domain Language

| Term | Meaning | Avoid |
|---|---|---|
| Mission type | The activated doctrine configuration defining a Mission's workflow and associated configuration | Feature type |
| Template mapping | The mission-type artefact's artifact-key-to-filename map | Template set string |
| Resolved mission-type context | The charter-mediated bundle consumed by core/runtime readers | Parallel template registry |
| Activated | Offered doctrine configuration selected by the charter and therefore available to runtime consumers | Present on disk |
| Transitional parity scaffold | Temporary migration proof that is deleted before merge | Permanent parity ratchet |

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | The system MUST populate the resolved mission-type context's template mapping from the activated doctrine `MissionType` artefact. | Confirmed |
| FR-002 | The resolved mapping MUST preserve the artefact's complete artifact-key-to-filename structure without converting it to, or sourcing it from, a profile-level default string. | Confirmed |
| FR-003 | Content-template readers in this slice MUST select the requested artifact's filename through the resolved mission-type context. | Confirmed |
| FR-004 | After a mapped filename is selected, the existing permitted file-override precedence MUST remain effective. | Confirmed |
| FR-005 | A mission type with no mapping, or no entry for the requested artifact kind, MUST NOT inherit or infer a software-development template. | Confirmed |
| FR-006 | An unresolved mapped filename MUST produce an unavailable result or actionable failure that identifies the mission type and requested artifact kind. | Confirmed |
| FR-007 | The shipped software-development mission MUST continue to resolve the same effective specification and planning templates throughout the authority swap. | Confirmed |
| FR-008 | The migration MUST use a temporary software-development parity scaffold to prove FR-007 and MUST remove that scaffold before merge. | Confirmed |
| FR-009 | Enduring doctrine-level and integration-level behavior checks MUST verify artefact-sourced mappings, missing-mapping behavior, and software-development outcomes after the transitional scaffold is removed. | Confirmed |

## Non-Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-001 | Resolving the eager mission-type context on the runtime hot path MUST remain within the existing 100 ms budget for a typical local project. | Confirmed |
| NFR-002 | Repeated resolution of the same activated mission type and configuration MUST produce identical ordered mapping content. | Confirmed |
| NFR-003 | The authority swap MUST produce zero user-visible changes to the shipped software-development specification and planning template content. | Confirmed |
| NFR-004 | Enduring verification MUST cover both the doctrine module boundary and at least one integration path that consumes the resolved mapping. | Confirmed |

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | Mission-type availability remains charter-activation-driven; filesystem presence alone MUST NOT make template configuration available. | Confirmed |
| C-002 | The doctrine `MissionType` artefact remains the single authority for the template mapping; this mission MUST NOT introduce a parallel registry or duplicate authored mapping. | Confirmed |
| C-003 | The legacy profile-level `template_set` string MUST NOT become the source for the resolved artefact mapping. | Confirmed |
| C-004 | The transitional parity scaffold MUST be absent from the merge-ready tree; only behavioral tests survive. | Confirmed |
| C-005 | Activation-driven enumeration, mission-runtime discovery, the meta-less mission fallback removal, copy-step removal, and deletion of the derived mission tree remain assigned to issues 2659–2661. | Confirmed |
| C-006 | No version or release-number commitment is part of this mission. | Confirmed |

## Dependencies

- Issue 2651, which completed and cleaned the shared resolver seam, is closed.
- Issue 2652 defines the retirement epic and its activation-driven availability acceptance criterion.
- The accepted doctrine-to-charter-to-core unification ADR defines the single resolver seam and transitional-parity testing posture.
- The doctrine-offers/charter-activates/runtime-consumes ADR defines templates as activated mission-type configuration and preserves the 100 ms hot-path budget.
- Issues 2659–2661 depend on this slice or follow it; their work is not pulled into this mission.

## Assumptions

- The shipped software-development mapping of `spec` to `spec-template.md` and `plan` to `plan-template.md` is the intended compatibility baseline.
- `template_set: null` means the mission type declares no built-in content templates; it is not permission to infer another mission type's templates.
- The mapping chooses the template filename, while the established per-file override precedence continues to determine which permitted copy of that filename wins.
- Issue 2658 and its governing ADRs provide sufficient product intent; implementation-specific reader inventory and sequencing belong in `/spec-kitty.plan`.

## Non-Goals

- Enumerating available mission types from charter activation state.
- Removing the legacy meta-less mission-type fallback assigned to issue 2660.
- Deleting the doctrine-to-project copy step or the derived mission directories.
- Redesigning command-template or workflow/DAG resolution beyond the content-template mapping required by issue 2658.
- Adding new template mappings for documentation, research, or plan mission types.

## Success Criteria

| ID | Outcome | Status |
|---|---|---|
| SC-001 | 100% of activated built-in mission types expose a resolved template mapping exactly equal to their doctrine artefact value, including explicit null mappings. | Confirmed |
| SC-002 | All content-template reader paths migrated in this slice make zero selections based on the `software-dev-default` magic string. | Confirmed |
| SC-003 | 100% of covered missing-mapping and missing-key scenarios select no software-development template. | Confirmed |
| SC-004 | The two shipped software-development content templates (`spec` and `plan`) resolve to behaviorally identical results before and after the swap. | Confirmed |
| SC-005 | The affected doctrine and integration test surfaces pass, and no `*parity_scaffold*` artifact remains in the merge-ready tree. | Confirmed |
