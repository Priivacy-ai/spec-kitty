# Contract — Shared Recursion Authority

**Module**: `src/doctrine/discovery_recursion.py` (NEW, doctrine layer)
**Consumers**: `doctrine.base.BaseDoctrineRepository`, `doctrine.agent_profiles.repository`, `charter.kind_vocabulary`
**Governs**: FR-001, FR-002, C-001, C-002, C-006

## Public surface
```python
def overlay_scan_is_recursive(kind: ArtifactKind) -> bool: ...   # True for every kind (C-001)
RECURSIVE_OVERLAY_KINDS: frozenset[ArtifactKind]                  # derived: all members
```

## Semantics
- **Overlay = org and project tiers.** Built-in already scans recursively (`_load_built_in_items` uses `rglob`); the authority documents/derives that overlays match it.
- **Unconditional (C-001)**: `overlay_scan_is_recursive` returns `True` for all kinds. It is a *policy surface for parity/derivation*, not a per-kind toggle — no kind is ever configured `False`.
- **Layer (C-006)**: lives in `doctrine`; `charter` imports *down*. Zero `specify_cli` import.
- **Kind-specific (C-002)**: the authority governs *whether* to recurse; the *pattern* is always `ArtifactKind.glob_pattern`, so `.provenance/*.yaml` and `.md` are never matched.

## Consumer obligations
| Consumer | Before | After |
|----------|--------|-------|
| `base.BaseDoctrineRepository._project_scan` | `project_dir.glob(self._glob)` | recursive scan gated by the authority |
| `styleguides.repository._project_scan` override | `rglob` override | **deleted** (redundant) |
| `assets.repository._project_scan` override | `rglob` override | **deleted** (redundant) |
| `agent_profiles.repository._load` | org `recursive=False`, project `recursive=False` | both `True` via authority (built-in already `True`) |
| `kind_vocabulary._org_scan_dirs` | flat `(dir, False)` | flat recursive from authority |
| `kind_vocabulary._layer_scan_dirs` | `(dir, False)` | recursive from authority |

## Invariants (gate-enforced)
- **R1**: loader-recursive kind set == resolver-recursive kind set == `RECURSIVE_OVERLAY_KINDS`.
- **R2**: nested `.provenance/*.yaml` / `.md` never captured.
- **R3**: overlay discovery completeness == built-in for every kind (NFR-001; tactic undercount 71%→0%).

## Non-regression (NFR-002)
`rglob` over a directory with no subdirectories yields the identical file set as `glob`; flat-layout discovery and activation output are byte-identical. Verified by a flat-layout golden assertion.
