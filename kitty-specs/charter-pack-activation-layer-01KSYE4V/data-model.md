# Data Model: Charter Pack Activation Layer

**Date**: 2026-05-31  
**Mission**: charter-pack-activation-layer-01KSYE4V

---

## Core Entities

### CharterPack (value object)

Immutable snapshot of a full activation configuration. Loaded from `src/charter/packs/default.yaml` (shipped pack) or assembled from config.yaml state.

| Field | Type | Description |
|-------|------|-------------|
| `activated_mission_types` | `frozenset[str]` | Mission type IDs that are active (e.g., `{"software-dev", "research"}`) |
| `activated_directives` | `frozenset[str] \| None` | Directive IDs; `None` = all built-ins available |
| `activated_tactics` | `frozenset[str] \| None` | Tactic IDs; `None` = all built-ins available |
| `activated_styleguides` | `frozenset[str] \| None` | Styleguide IDs; `None` = all built-ins available |
| `activated_toolguides` | `frozenset[str] \| None` | Toolguide IDs; `None` = all built-ins available |
| `activated_paradigms` | `frozenset[str] \| None` | Paradigm IDs; `None` = all built-ins available |
| `activated_procedures` | `frozenset[str] \| None` | Procedure IDs; `None` = all built-ins available |
| `activated_agent_profiles` | `frozenset[str] \| None` | Agent profile IDs; `None` = all built-ins available |
| `activated_mission_step_contracts` | `frozenset[str] \| None` | MSC IDs; `None` = all built-ins available |

**Invariant**: Absence of a key in config.yaml means "all built-ins available" (backward-compat for pre-upgrade projects — `None` in Python). An empty list `[]` / empty frozenset means "nothing available for this kind" (explicit restriction). A non-empty frozenset means "only these IDs are available." These three states are distinct and all legitimate.

**Reader rule (FR-039)**: The `from_config()` reader must NOT apply a silent fallback when it encounters an empty list `[]`. An empty YAML list maps to `frozenset()`, not to the default built-in set. The existing `and raw` guard in `_read_activated_kinds` (which collapses `[]` to all built-ins) must be removed from all per-kind readers. Projects are protected from an empty-set state by the upgrade command writing the default pack — not by a silent reader fallback.

**Serialization**: YAML under `src/charter/packs/default.yaml`. Kind keys use plural snake_case matching `PackContext` existing keys. `None` / absent key is represented by absence of the YAML key (round-trip safe).

---

### PackContext (existing, extended)

Existing Pydantic dataclass in `src/charter/pack_context.py`. Extended with per-kind activation fields.

| Field | Type | Source in config.yaml |
|-------|------|----------------------|
| `activated_kinds` | `frozenset[str]` | `activated_kinds` key (8-element set of plural kind names) |
| `activated_mission_types` | `frozenset[str]` | `mission_type_activations` key |
| `activated_directives` *(new)* | `frozenset[str] \| None` | `activated_directives` key |
| `activated_tactics` *(new)* | `frozenset[str] \| None` | `activated_tactics` key |
| `activated_styleguides` *(new)* | `frozenset[str] \| None` | `activated_styleguides` key |
| `activated_toolguides` *(new)* | `frozenset[str] \| None` | `activated_toolguides` key |
| `activated_paradigms` *(new)* | `frozenset[str] \| None` | `activated_paradigms` key |
| `activated_procedures` *(new)* | `frozenset[str] \| None` | `activated_procedures` key |
| `activated_agent_profiles` *(new)* | `frozenset[str] \| None` | `activated_agent_profiles` key |
| `activated_mission_step_contracts` *(new)* | `frozenset[str] \| None` | `activated_mission_step_contracts` key |

**Read logic**: `from_config()` classmethod reads config.yaml. Absent key → `None` (all built-ins). Present key → parse into `frozenset[str]`.

**Hard restriction invariant**: When a key is present, the returned frozenset is the ONLY available set. The resolver MUST NOT fall back to the full catalog when `activated_X` is a non-None frozenset.

---

### ActivationKind (enum / Literal)

Maps CLI kind names (singular) to `PackContext` field names (plural).

| CLI kind (singular) | PackContext field | YAML key |
|---------------------|-----------------|----------|
| `mission-type` | `activated_mission_types` | `mission_type_activations` |
| `directive` | `activated_directives` | `activated_directives` |
| `tactic` | `activated_tactics` | `activated_tactics` |
| `styleguide` | `activated_styleguides` | `activated_styleguides` |
| `toolguide` | `activated_toolguides` | `activated_toolguides` |
| `paradigm` | `activated_paradigms` | `activated_paradigms` |
| `procedure` | `activated_procedures` | `activated_procedures` |
| `agent-profile` | `activated_agent_profiles` | `activated_agent_profiles` |
| `mission-step-contract` | `activated_mission_step_contracts` | `activated_mission_step_contracts` |

---

### CascadeScope (value object)

Parsed from the `--cascade` CLI flag.

| Value | Meaning |
|-------|---------|
| `none` (default, absent flag) | No cascade; warn user about cross-kind references |
| `all` | Cascade to all applicable artifact kinds |
| `profiles` | Cascade to agent-profile kind only |
| `directives` | Cascade to directive kind only |
| `tactics` | Cascade to tactic kind only |
| Comma-separated e.g. `profiles,directives` | Cascade to the named subset |

**Activation cascade semantics**: When activating artifact X with `--cascade K`, also activate all artifacts of kind K that X references (follows DRG edges or flat-catalog cross-references from X).

**Deactivation cascade semantics**: When deactivating artifact X with `--cascade K`, also deactivate artifacts of kind K that are referenced EXCLUSIVELY by X (i.e., no other activated artifact of any kind references them). Artifacts referenced by ≥2 activated artifacts are skipped with a warning.

---

### CharterPackManager (service)

New module: `src/charter/pack_manager.py`

Responsibilities:
- Load `CharterPack` from `src/charter/packs/default.yaml`
- Read current activation state from config.yaml via `PackContext.from_config()`
- Write activation changes to config.yaml (ruamel.yaml round-trip, comment-preserving)
- Merge default pack into existing config.yaml state (upgrade path)
- Compute cascade targets for activate/deactivate operations
- Emit warnings for skipped shared artifacts during deactivation cascade

Key methods:
```
activate(repo_root, kind, artifact_id, cascade) -> ActivationResult
deactivate(repo_root, kind, artifact_id, cascade) -> ActivationResult
list_activated(repo_root) -> dict[str, frozenset[str]]
list_available(repo_root, kind) -> frozenset[str]
merge_defaults(repo_root) -> MergeResult
```

**Activation from `None` state**: When `activated_<kind>` is `None` (absent key — pre-upgrade project), `activate()` must first materialize the starting set. The source is `src/charter/packs/default.yaml` — the manager reads the default pack for that kind, writes all its artifact IDs as the initial explicit activation list, then adds the requested artifact. This is deterministic and independent of the live doctrine catalog (catalog changes do not retroactively alter an explicit activation list).

**Deactivation from `None` state**: `deactivate()` on a kind whose activation field is `None` (no explicit set) is an error. Exit with code 1 and message: `"Kind '<kind>' has no explicit activation set. Run 'spec-kitty upgrade' to initialize the default pack before modifying individual activations."` This prevents an implicit materialization step on a destructive path and guides the user to the correct remediation.

**Empty activation set**: A kind whose activation field is `frozenset()` (empty) has its entire DRG slice excluded from resolution — no artifact of that kind resolves, regardless of what the doctrine catalog contains. This is a valid intentional state reachable only by explicit user action (deactivating all artifacts one by one, or manual config.yaml edit). The default charter pack written by `spec-kitty upgrade` ensures this state is never reached accidentally.

---

### ConsistencyReport (value object)

Result of `charter pack consistency-check`.

| Field | Type | Description |
|-------|------|-------------|
| `coherent` | `bool` | True when all checks pass |
| `unknown_references` | `list[str]` | Artifact IDs in pack that don't exist in doctrine |
| `missing_from_doctrine` | `list[str]` | IDs referenced in charter that doctrine no longer has |
| `kind_violations` | `list[str]` | Artifacts activated under the wrong kind |
| `suggestions` | `list[str]` | Human-readable guidance for each incoherence |

---

### CharterBackup (metadata)

Written alongside `.kittify/charter/backups/charter-{timestamp}.md`.

| Field | Type | Description |
|-------|------|-------------|
| `original_path` | `Path` | `.kittify/charter/charter.md` |
| `backup_path` | `Path` | `.kittify/charter/backups/charter-{timestamp}.md` |
| `timestamp` | `str` | ISO 8601 |
| `trigger` | `str` | `"upgrade"` or `"manual"` |
| `spec_kitty_version` | `str` | Version that created the backup |

---

## State Transitions

### Activation lifecycle for a single artifact kind

```
[absent from config.yaml]    →  from_config() returns None  →  all built-ins available
[key present, non-empty set] →  from_config() returns frozenset  →  only listed IDs available
[key present, empty set]     →  from_config() returns frozenset{}  →  nothing available (explicit restriction)
```

### charter activate flow

```
user: charter activate directive python-style-guide
  → CharterPackManager.activate(repo_root, "directive", "python-style-guide", CascadeScope.none)
  → read current activated_directives from config.yaml
  → if None: initialize to all built-ins, then add python-style-guide
  → if frozenset: add python-style-guide
  → write back to config.yaml via ruamel.yaml round-trip
  → if no cascade: warn "The following cross-references were not cascaded: ..."
  → emit success message
```

### charter deactivate flow with cascade

```
user: charter deactivate directive python-style-guide --cascade tactics
  → CharterPackManager.deactivate(repo_root, "directive", "python-style-guide", CascadeScope({"tactics"}))
  → remove python-style-guide from activated_directives
  → find all tactic IDs referenced by python-style-guide (DRG edges)
  → for each referenced tactic T:
      → if T is referenced by any OTHER activated directive: skip, warn "T is shared, not deactivated"
      → else: remove T from activated_tactics
  → write back to config.yaml
  → emit result: deactivated, skipped (shared), warnings
```

---

## config.yaml Schema Extension

New keys added under root level of `.kittify/config.yaml`:

```yaml
# Added by charter activate/deactivate or upgrade migration
activated_directives:
  - python-style-guide
  - clean-code
activated_tactics:
  - test-driven-development
# ... other kinds follow same pattern
# Absent key = all built-ins available (backward compat)
```

`mission_type_activations` key already exists (Phase 1). `activated_kinds` key already exists. No breaking changes to existing config.yaml structure.
