# Phase 1 Data Model — Single-Authority Resolution Parity

This mission introduces **authorities** (single sources of truth) and a **gate**, not persisted data. The "entities" below are the conceptual objects those authorities govern and the invariants the gate enforces.

## Entities

### 1. Doctrine artifact
A governance unit discovered on the filesystem.

| Field | Type | Notes |
|-------|------|-------|
| `kind` | `ArtifactKind` | one of 12 canonical kinds |
| `id` | `str` | from the artifact's `id:` field (`profile-id` for agent profiles) |
| `tier` | `built-in` \| `org` \| `project` | discovery layer |
| `path` | `Path` | filesystem location, e.g. `<org>/tactics/testing/x.tactic.yaml` (nested) |

**Discovery rule (post-fix)**: a kind's artifacts are found by *recursive* scan of each tier's directory using the kind-specific glob (`ArtifactKind.glob_pattern`), for **all** tiers.

### 2. Recursion authority (`doctrine.discovery_recursion`) — NEW
The single policy both loader and resolver read to decide overlay-subdirectory scanning.

| Symbol | Type | Value |
|--------|------|-------|
| `overlay_scan_is_recursive(kind)` | `(ArtifactKind) -> bool` | `True` for every kind (C-001) |
| `RECURSIVE_OVERLAY_KINDS` | `frozenset[ArtifactKind]` | all members (derived) |

**Invariant R1 (parity)**: `{kinds the loader scans recursively for org/project} == {kinds the resolver returns recursive=True for org/project} == RECURSIVE_OVERLAY_KINDS`.
**Invariant R2 (kind-specific)**: recursion uses `ArtifactKind.glob_pattern` only; `.provenance/*.yaml` and `.md` never match (C-002).
**Invariant R3 (built-in parity)**: overlay recursion equals built-in recursion (already `rglob`) for every kind (NFR-001 load-completeness parity).

### 3. Charter-activatable kind-vocabulary authority (doctrine layer) — NEW
The derived plural↔singular map for the charter-activatable kind universe.

| Symbol | Type | Derivation |
|--------|------|-----------|
| `CHARTER_ACTIVATABLE_KINDS` | `frozenset[ArtifactKind]` | `set(ArtifactKind) − {TEMPLATE, ASSET}` → **10 kinds incl `ANTI_PATTERN`** |
| `CHARTER_ACTIVATABLE_SINGULAR_TO_PLURAL` | `dict[str, str]` | `{k.value: k.plural}` over the 10 |
| `CHARTER_ACTIVATABLE_PLURAL_TO_SINGULAR` | `dict[str, str]` | inverse |

**Invariant V1 (round-trip)**: for every activatable kind, `plural_to_singular[singular_to_plural[s]] == s`.
**Invariant V2 (10-kind, C-003/FR-005)**: `ANTI_PATTERN ∈ CHARTER_ACTIVATABLE_KINDS`; `TEMPLATE, ASSET ∉`.
**Invariant V3 (no restatement, FR-004)**: `charter.activations` and `charter._activation_render` import these; declare **no** local plural↔singular kind dict.

### 4. `--include` selector vocabulary (FR-006)
The set of kinds `charter context --include <kind>:<id>` recognizes.

**Invariant S1**: every `CHARTER_ACTIVATABLE_KINDS` member is a *recognized* selector kind — none returns the "Unsupported --include selector kind" error.
- `glossary_pack` → renders via `service.glossary_packs`.
- `anti_pattern` → recognized; resolves to a standard "No anti_pattern found" not-found (no artifact files exist) — **not** an unknown-kind error.

### 5. Parity/totality gate (`tests/doctrine/drg/test_kind_mapping_totality.py`, extended)
The automated check binding the invariants above.

| Check | Enforces |
|-------|----------|
| Enum-keyed totality (existing) | ArtifactKind/NodeKind-keyed dicts total-or-exempt |
| **String-keyed coverage (new)** | module-level string-keyed kind dicts have valid kind keys; drifted/typo keys fail (FR-007) |
| **Recursion parity (new)** | Invariant R1 by behavioral fixture — both loader and resolver discover a nested artifact for every kind |
| **C-002 negative (new)** | Invariant R2 — `.provenance/*.yaml` / `.md` not captured |
| **Falsifiability (new)** | reintroduced divergence reddens; restore greens (NFR-003, both directions) |

## Non-goals (C-004 boundary — explicitly out of the model)
- No new DRG nodes or edges; no cascade relation-set change; no golden-count movement.
- No conversion of `project_drg._KIND_TO_NODE_KIND` to enum-keyed (that is M6/#3038).
- No org `drg/fragment.yaml` → cascade bridge (that is M2/#3572).
