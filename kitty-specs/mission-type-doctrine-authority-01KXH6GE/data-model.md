# Phase 1 Data Model — Mission-Type Doctrine Authority

Internal domain model (no persistence schema; these are doctrine artefacts and
in-memory value objects). Field names are indicative; final shapes are fixed in the
WPs against the live code.

## MissionType artefact (doctrine, load-bearing)

The single source of truth for a mission type. Declared in `src/doctrine/missions/`.

| Element | Source file | Role |
|---------|-------------|------|
| identity + action sequence | `mission_types/<type>.yaml` | the type's identity and ordered steps |
| type-grain governance | `<type>/governance-profile.yaml` (referenced, Q1) | `selected_*` doctrine for the whole type |
| action-grain governance | `<type>/actions/<action>/index.yaml` | doctrine scoped to one step |
| gates | `<type>/expected-artifacts.yaml` (doctrine tree) | artifacts the mission must produce |
| steps | step contracts (doctrine) | per-step I/O contracts |

**Invariants**
- Exactly one artefact per built-in mission type (`software-dev`, `documentation`, `research`, `plan`).
- No `governance_refs` field (retired, IC-01).
- Every referenced governance id resolves in the DRG (no danglers).
- An artifact URN appears in **at most one** grain (type or action) — double declaration is an error (FR-013).

## ResolvedMissionType (in-memory bundle)

Produced by `resolve_mission_type_context`; consumed by the core.

| Field | Type | Slice-1 state |
|-------|------|---------------|
| `mission_type` | `str` (canonicalized) | resolved from explicit arg → `meta.json`; hard error if unknown/typed; neutral for typeless callers |
| `governance` | `ResolvedGovernance` | **populated** |
| `action_sequence` | `list[str]` | **populated** (steps) |
| `expected_artifacts` | gate manifest \| None | **populated by IC-07** after the upward reconcile (so the bundle never reads an un-reconciled doctrine tree); detachable lane |
| `step_contracts` | resolved step contracts | **populated** |
| `template_set` | `str \| None` | reserved — populated in a later slice |
| `provenance` | `str` (builtin\|org\|project) | populated for the governance layer |

## ResolvedGovernance (structured, ordered)

| Field | Type | Notes |
|-------|------|-------|
| `selected_directives` | `list[URN]` | **ordered** (explicit tested sort — NFR-007), not a set |
| `selected_tactics` | `list[URN]` | ordered |
| `selected_paradigms` / `styleguides` / `toolguides` / `procedures` / `agent_profiles` | `list[URN]` | ordered |

- Rendered text (`GovernancePayload.text`) is a **rendering of** this ordered object → deterministic output.
- Built by unioning type-grain ∪ action-grain, de-conflicting on canonical URN (double-declaration forbidden).

## Per-type override (project layer)

- Location: `.kittify/doctrine/mission_types/<type>/governance-profile.yaml`.
- Resolved through the `doctrine/base.py` overlay: **builtin → org → project**, field-merge, `DoctrineLayerCollisionWarning`.
- Requires `id` on `MissionTypeProfile` + a `BaseDoctrineRepository[MissionTypeProfile]` subclass (IC-05).

## ExpectedArtifactManifest adapter (dossier)

- Today: `ManifestRegistry.load_manifest` returns `ExpectedArtifactManifest`; the doctrine reader `repository.get_expected_artifacts` returns `ConfigResult` (no `from_dict`).
- Adapter: `ExpectedArtifactManifest.model_validate(config_result.parsed)` + cache preservation (IC-07).

## State / lifecycle

No stateful entities or transitions are introduced. The only "state" is the swap
lifecycle per detachable lane: `reconcile-upward → parity-scaffold-green → flip → delete-copies → delete-scaffold`, with `flip` conditionally deferrable.
