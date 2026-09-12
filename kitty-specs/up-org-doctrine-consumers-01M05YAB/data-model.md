# Phase 1 Data Model: Org-Tier Doctrine Reaches Its Consumers

This mission has no new persistent entities or database schema — it is caller-side threading of an
existing resolution shape (four/five sites) plus one new additive file-read convention (FR-008) and
one new structural read on an already-computed result (FR-007). This document captures the shapes
that change, refined from the spec's own "Key Entities" section with the concrete Python types this
plan's investigation confirmed.

## Existing shapes threaded through (no change to their own definition)

### `org_dirs` (list shape)

```python
org_dirs: list[Path]  # one Path per configured, existing org pack: <org_root>/<subdir>
```

Consumed by every `BaseDoctrineRepository` subclass constructor
(`doctrine/base.py`), including `MissionStepContractRepository` and `MissionTypeProfileRepository`.
Declaration order matters: later entries override earlier ones for the same artifact id
(NFR-003, unchanged by this mission).

### `org_root` (single-path shape)

```python
org_root: Path | None  # exactly one path, or None (no org contribution)
```

Consumed by `charter._drg_helpers.load_validated_graph(repo_root, org_root=None)`. Structurally
distinct from `org_dirs` — see spec D-000(2) and `research.md` R-02.

## New function signature: `IC-01`'s shared `org_dirs` helper

```python
# src/doctrine/drg/org_pack_config.py

def resolve_org_dirs(repo_root: Path, subdir: str) -> list[Path]:
    """Existing-path-filtered, declaration-ordered org directories for *subdir*.

    Filters non-existent org-pack roots before joining *subdir* (mirrors
    charter.doctrine_service_builder._self_resolve_existing_org_roots), so a
    stale local_path config entry degrades to "no org contribution" cleanly.
    """
```

- Input: `repo_root` (project root), `subdir` (artifact-plural or convention-owned name — e.g.
  `"mission_step_contracts"`, `"mission_types"`).
- Output: `list[Path]`, each existing on disk, in declared-pack order.
- Invariant: `resolve_org_dirs(repo_root, subdir) == [root / subdir for root in resolve_org_roots(repo_root) if root.exists()]`.

## New/changed shape: `StepContractExecutionResult` (FR-007)

```python
# src/specify_cli/mission_step_contracts/executor.py — additive properties only

@dataclass(frozen=True)
class StepContractExecutionResult:
    contract_id: str
    mission: str
    action: str
    profile_hint: str
    resolution_source: str
    steps: tuple[StepContractStepResult, ...]

    @property
    def invocation_ids(self) -> tuple[str, ...]: ...  # unchanged

```

**Superseded during task decomposition — no properties are added here.** This section originally
specified `has_unresolved_delegations` and `all_unresolved_candidates` as new aggregate properties
on `StepContractExecutionResult`. That type lives in `executor.py`, which WP02 owns; adding to it
from WP03 would have created a third file collision the plan never declared, and WP02/WP03 are
meant to run in parallel.

FR-007 instead iterates `result.steps` inline at the point of use, inside
`_dispatch_via_composition`. `StepContractStepResult` already carries `resolved_delegations` and
`unresolved_candidates` (lines 109-110), so the data is reachable without touching `executor.py`
at all. WP03's prompt carries the authoritative instruction; this note exists so the artifact does
not contradict it.

## New shape: FR-008's org-file-check helper

```python
# src/charter/org_expected_artifacts.py (new module)

def resolve_org_expected_artifacts(
    org_roots: list[Path], mission_type: str
) -> Mapping[str, object] | None:
    """Return the parsed org-tier expected-artifacts.yaml for *mission_type*, or None.

    Checks each *org_roots* entry (already existence-filtered by the caller,
    per R-01's pattern) for <org_root>/<mission_type>/expected-artifacts.yaml,
    later entries overriding earlier ones (same NFR-003 declared-order
    contract as every other org_dirs consumer). Whole-file: a present org
    file fully replaces the built-in manifest for that mission type — it is
    never field-merged with it.
    """
```

Two call sites adapt this into their own return shape:
- `charter/mission_type_profiles.py:_resolve_expected_artifacts_slot` — org result takes precedence
  over `MissionTemplateRepository.default().get_expected_artifacts(mission_type).parsed` when
  present.
- `specify_cli/dossier/manifest.py:ManifestRegistry.load_manifest` — same precedence, adapted into
  `ExpectedArtifactManifest.model_validate(...)`.

## Changed shape: `ManifestRegistry.load_manifest` (FR-008, cache-key fix per R-05)

```python
# src/specify_cli/dossier/manifest.py

class ManifestRegistry:
    _cache: dict[tuple[str, tuple[str, ...]], ExpectedArtifactManifest | None] = {}

    @staticmethod
    def load_manifest(
        mission_type: str, repo_root: Path | None = None
    ) -> ExpectedArtifactManifest | None:
        ...
```

Cache key becomes `(mission_type, org_roots_fingerprint)` where `org_roots_fingerprint` is an empty
tuple when `repo_root is None` (today's exact call shape from
`specify_cli/sync/namespace.py:resolve_manifest_version`, unchanged) or when no org pack resolves to
an existing path for that project. This is the only signature change in the mission that touches an
existing public call shape; its sole production caller is unaffected because it never passes
`repo_root`.

## Entity relationship (informal)

```
OrgPackConfig (.kittify/config.yaml doctrine.org.packs)
    │  resolve_org_roots(repo_root)
    ▼
list[Path] org roots (existence-unfiltered)
    │  resolve_org_dirs(repo_root, subdir)  [IC-01, existence-filtered + subdir-joined]
    ▼                                            │  first-match [IC-02, inline]
list[Path] org_dirs ──────► BaseDoctrineRepository   Path org_root ──────► load_validated_graph
    (FR-001/004/005/006/006a)   subclasses                (FR-002)            (DRG merge)
                                     │
                                     ▼
                         MissionStepContractRepository.get_by_action(...)
                                     │
                          delegates_to candidates resolved against DRG
                                     │
                     resolved / unresolved  ──► StepContractExecutionResult
                                                  .has_unresolved_delegations   [FR-007]
                                                  .all_unresolved_candidates
                                                       │
                                          _dispatch_via_composition WARNING [IC-03]

[r for r in resolve_org_roots(repo_root) if r.exists()]   (raw org roots, NOT subdir-joined —
    │                                                        FR-008 joins <mission_type> per root,
    │                                                        which varies per call, so it does not
    │                                                        reuse IC-01's fixed-subdir helper)
    ▼
org_expected_artifacts.resolve_org_expected_artifacts(org_roots, mission_type)  [FR-008]
    │  overrides (whole-file) ▼
MissionTemplateRepository.default().get_expected_artifacts(mission_type)  (built-in fallback)
```
