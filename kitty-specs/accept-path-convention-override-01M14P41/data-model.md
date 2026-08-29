# Data Model: Accept path-convention portability

## Entities

### ProjectPathConventions (new)
The project-declared layout override.

| Field | Type | Notes |
|-------|------|-------|
| `workspace` | `str \| absent` | Source root (e.g. `apps/`, `internal/`). Optional. |
| `tests` | `str \| absent` | Test root. Optional. |
| `deliverables` | `str \| absent` | Deliverables root. Artifact-routed key — see invariant I3. Optional. |
| `documentation` | `str \| absent` | Docs root. Optional. |
| `data` | `str \| absent` | Data root. Optional. |

- **Source**: `.kittify/config.yaml` → `project.path_conventions`.
- **Loader**: `load_project_path_conventions(repo_root) -> dict[str, str]` (typed section reader).
- **Validation**: keys ⊆ `valid_path_keys` (shared constant extracted from `MissionConfig`); unknown key
  → warn/reject consistent with existing `MissionConfig` behavior (FR-007). Empty/non-string/malformed →
  fail closed with actionable message (FR-008).
- **Absence**: no `project.path_conventions` key ⇒ empty map ⇒ zero behavior change (NFR-004).

### MissionPathConvention (existing doctrine default)
`mission.config.paths` (from `mission.yaml`), keyed by the same vocabulary. Fallback when a key is not
overridden.

### ResolvedRequiredPaths (existing, now composed)
The `declared` map inside `validate_mission_paths`, after composition, evaluated against the repo.

## Composition (precedence) — remap-only

```
# WP01, at paths.py:199 — BEFORE the `required_paths` comprehension AND the artifact-token check.
for key in declared:                       # iterate DOCTRINE-declared keys only (remap-only)
    if key in project_override and key not in ARTIFACT_ROUTED_KEYS:
        declared[key] = project_override[key]
# override keys not declared by the mission, or artifact-routed keys → warn/ignore (never added)
# then, unchanged downstream:
#   - research path_prefix is applied via _prefix_required_path                (I4)
#   - artifact-token membership check decides feature_dir vs project_root arm  (I3)
```

Order: **doctrine default ← project override ← research prefix**. The override merge happens once, at
`paths.py:199`, upstream of both the prefix step and the artifact-token check (C-008). Insertion **must**
be line 199 (before the comprehension), or overridden keys miss `_prefix_required_path`.

## Invariants

- **I1 (value channel)**: composition changes only *which directory* an already-declared key expects; it
  never changes the strict/lenient blocking decision (C-001) and never adds a new required path
  (remap-only). A declared-but-absent directory still blocks (SC-006).
- **I2 (backward compatible)**: empty override ⇒ `declared` identical to today (NFR-004).
- **I3 (artifact routing untouched)**: artifact-routed keys (`deliverables`, value = a mission artifact
  token) are **excluded** from the override vocabulary (C-010), so the `feature_dir` vs `project_root`
  routing at `paths.py:~224` is never flipped by an override.
- **I4 (single seam)**: `validate_mission_paths` retains exactly one production caller
  (`evaluate_path_conventions`) — guarded by a test placed OUTSIDE `tests/architectural/` (NFR-004b).

### OptionalArtifactSet (#3785, WP04)
`_missing_artifacts` derives the optional-artifact set from `mission.config.artifacts.optional`
(token→file/dir resolved) rather than the hardcoded `[quickstart, data-model, research, contracts]`.

- **Invariant**: `contracts/` severity unchanged (C-003). `mission is None` ⇒ safe fallback.
- **Consequence**: software-dev's declared `checklists/` (omitted by the old list) is now considered.
