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

**Reader rule (FR-039)**: The `and raw` guard is removed from **every** activation reader — `_read_activated_kinds`, `_read_activated_mission_types`, and all new per-kind readers. An empty YAML list `[]` maps to `frozenset()` (explicit empty restriction) for every activation field. There is no reader-side fallback to built-ins for any key. The three-state model (`None` = absent key = all built-ins; `frozenset()` = empty = nothing; non-empty frozenset = exactly those IDs) applies consistently across all activation fields without exception. The existing test `test_empty_activated_kinds_uses_builtin_fallback` encodes the old two-state behavior and must be deleted. Projects are protected from accidental empty activation sets by the upgrade command writing the default pack — not by reader-side fallbacks.

**Serialization**: YAML under `src/charter/packs/default.yaml`. Kind keys use plural snake_case matching `PackContext` existing keys. `None` / absent key is represented by absence of the YAML key (round-trip safe).

---

### PackContext (existing, extended)

Existing **stdlib `@dataclass(frozen=True)`** in `src/charter/pack_context.py` (not Pydantic — do not use `Field()`, `@validator`, or Pydantic APIs). Extended with per-kind activation fields.

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

**`mission_step_contract` naming bug**: `drg.py:592 _SINGULAR_TO_PLURAL` maps `"mission_step_contract"` → `"mission_steps"`, while `pack_context.py:58 _BUILTIN_ARTIFACT_KINDS` uses `"mission_step_contracts"`. These strings do not match, causing kind-level activation checks for ownerless MSC nodes to always fail. The implementer must fix the mismatch: the canonical plural is `"mission_step_contracts"` (per `_BUILTIN_ARTIFACT_KINDS`). Update `_SINGULAR_TO_PLURAL["mission_step_contract"]` to `"mission_step_contracts"`. Verify that `FR-028`'s test fix uses `"mission_step_contracts"` consistently.

---

### CascadeScope (value object)

Parsed from the `--cascade` CLI flag. The cascade token is the CLI kind name (hyphen form), not the Python identifier (underscore form).

| Value | Meaning |
|-------|---------|
| _(absent flag)_ | No cascade; warn user about cross-kind references |
| `all` | Cascade to all applicable artifact kinds |
| `directive` | Cascade to directive kind only |
| `tactic` | Cascade to tactic kind only |
| `styleguide` | Cascade to styleguide kind only |
| `toolguide` | Cascade to toolguide kind only |
| `paradigm` | Cascade to paradigm kind only |
| `procedure` | Cascade to procedure kind only |
| `agent-profile` | Cascade to agent-profile kind only |
| `mission-step-contract` | Cascade to mission-step-contract kind only |
| Comma-separated e.g. `agent-profile,tactic` | Cascade to the named subset |

**Note**: The `--cascade` flag accepts the CLI kind names (hyphen form, same as the `<kind>` argument). The shorthand aliases `profiles`, `directives`, `tactics` are removed — only the canonical CLI kind names and `all` are accepted, to maintain a single consistent set of tokens across the CLI surface.

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

Key methods (all take `ctx: ProjectContext` as first parameter):
```python
def activate(ctx: ProjectContext, kind: str, artifact_id: str, cascade: CascadeScope) -> ActivationResult: ...
def deactivate(ctx: ProjectContext, kind: str, artifact_id: str, cascade: CascadeScope) -> ActivationResult: ...
def list_activated(ctx: ProjectContext) -> dict[str, frozenset[str]]: ...
def list_available(ctx: ProjectContext, kind: str) -> frozenset[str]: ...
def merge_defaults(ctx: ProjectContext) -> MergeResult: ...
```

**`kind` parameter**: always the CLI kind name (hyphen form, e.g. `"agent-profile"`). The manager maps it to the config.yaml key internally. The special-case dispatch is:
```python
# mission-type maps to the Phase 1 key (not activated_mission_types)
YAML_KEY_MAP = {
    "mission-type": "mission_type_activations",
    "directive":    "activated_directives",
    "tactic":       "activated_tactics",
    "styleguide":   "activated_styleguides",
    "toolguide":    "activated_toolguides",
    "paradigm":     "activated_paradigms",
    "procedure":    "activated_procedures",
    "agent-profile":           "activated_agent_profiles",
    "mission-step-contract":   "activated_mission_step_contracts",
}
```
Do NOT use a generic `f"activated_{kind.replace('-', '_')}s"` formatter — `mission-type` is the outlier that requires explicit dispatch.

**Activation from `None` state**: When `activated_<kind>` is `None` (absent key — pre-upgrade project), `activate()` must first materialize the starting set. The source is `src/charter/packs/default.yaml` — the manager reads the default pack for that kind, writes all its artifact IDs as the initial explicit activation list, then adds the requested artifact. This is deterministic and independent of the live doctrine catalog (catalog changes do not retroactively alter an explicit activation list). **Warning required**: if the project has third-party doctrine artifacts of this kind that are absent from `default.yaml`, the materialized set will not include them and those artifacts will become unavailable. The manager must emit a visible warning: `"Warning: materialized activation set from default pack; any third-party <kind> artifacts not in the default pack are now excluded. Review 'charter list --show-available' to verify."` This warning should only fire when a third-party artifact would be lost (i.e., the doctrine catalog for this kind has entries not in `default.yaml`).

**Deactivation from `None` state**: `deactivate()` on a kind whose activation field is `None` (no explicit set) is an error. Exit with code 1 and message: `"Kind '<kind>' has no explicit activation set. Run 'spec-kitty upgrade' to initialize the default pack before modifying individual activations."` This prevents an implicit materialization step on a destructive path and guides the user to the correct remediation.

**Empty activation set**: A kind whose activation field is `frozenset()` (empty) has its entire DRG slice excluded from resolution — no artifact of that kind resolves, regardless of what the doctrine catalog contains. This is a valid intentional state reachable only by explicit user action (deactivating all artifacts one by one, or manual config.yaml edit). The default charter pack written by `spec-kitty upgrade` ensures this state is never reached accidentally.

---

### ActivationResult (value object)

Return type of `CharterPackManager.activate()` and `deactivate()`.

| Field | Type | Description |
|-------|------|-------------|
| `activated` | `list[str]` | IDs that were added to the activation set |
| `deactivated` | `list[str]` | IDs that were removed from the activation set |
| `cascade_activated` | `dict[str, list[str]]` | Kind → IDs cascade-activated (keyed by CLI kind name) |
| `cascade_deactivated` | `dict[str, list[str]]` | Kind → IDs cascade-deactivated |
| `skipped_shared` | `dict[str, list[str]]` | Kind → IDs skipped because referenced by another active artifact |
| `warnings` | `list[str]` | Human-readable warnings (cross-kind references not cascaded, third-party artifact loss) |

---

### MergeResult (value object)

Return type of `CharterPackManager.merge_defaults()`.

| Field | Type | Description |
|-------|------|-------------|
| `kinds_written` | `list[str]` | Per-kind keys written to config.yaml (CLI kind names) |
| `backup_path` | `Path \| None` | Path to charter.md backup if one was created |
| `warnings` | `list[str]` | Human-readable warnings |

---

### ProjectContext (value object)

Immutable snapshot of project-level runtime state. Defined in `src/charter/invocation_context.py`. Owned by the charter module; populated by `specify_cli.*`.

| Field | Type | Description |
|-------|------|-------------|
| `repo_root` | `Path \| None` | Absolute path to the repository root |
| `pack_context` | `PackContext \| None` | Charter activation state for this project |
| `org_root` | `Path \| None` | Absolute path to the org-level doctrine root, if any |
| `specs_dir` | `Path \| None` | Absolute path to the `kitty-specs/` directory |
| `architecture_dir` | `Path \| None` | Absolute path to the `architecture/` directory |

All fields are optional so the object can be constructed incrementally or partially in tests. Guard methods enforce presence at method-call boundaries.

**Factory**:
```python
@classmethod
def from_repo(cls, repo_root: Path) -> "ProjectContext":
    """Construct a fully-populated ProjectContext from a repository root."""
```

`from_repo()` field resolution rules:
- `repo_root`: the passed-in argument (always non-None after construction)
- `pack_context`: `PackContext.from_config(repo_root)` — always returns a populated instance (defaults if `.kittify/config.yaml` is absent); never `None` after construction via `from_repo()`
- `org_root`: from `doctrine.drg.org_pack_config.resolve_org_roots(repo_root)` first entry if non-empty, else `None`
- `specs_dir`: `repo_root / "kitty-specs"` if that directory exists, else `None`
- `architecture_dir`: `repo_root / "architecture"` if that directory exists, else `None`

**Missing `.kittify/` behavior**: `from_repo()` does NOT raise when `.kittify/config.yaml` is absent — `PackContext.from_config()` returns a default-filled instance silently. `require_pack_context()` therefore always passes for a context constructed via `from_repo()`. The guard is an assertion against mis-construction (e.g., partially-built instances in tests), not a "is this a kittify project?" check. CLI commands that need to validate project setup should check `(repo_root / ".kittify").is_dir()` explicitly before calling `from_repo()`.

**Guard methods** (raise `ContextPreconditionError` if the field is `None`):
```python
def require_repo_root(self) -> Path: ...
def require_pack_context(self) -> PackContext: ...
def require_org_root(self) -> Path: ...
```

`specs_dir` and `architecture_dir` have no corresponding guard methods — callers that use them must None-check directly. These fields are optional convenience paths; no mission-critical logic in this mission depends on them.

**Usage at method entry**:
```python
def activate(ctx: ProjectContext, kind: str, artifact_id: str, ...) -> ActivationResult:
    repo_root = ctx.require_repo_root()      # raises if absent
    pack_context = ctx.require_pack_context() # raises if absent
    ...
```

---

### OperationalContext (value object)

Immutable snapshot of agent-invocation-level runtime state. Defined in `src/charter/invocation_context.py`. Owned by the charter module; populated by `specify_cli.context` factories when an agent invocation is live.

| Field | Type | Description |
|-------|------|-------------|
| `active_model` | `str \| None` | LLM model identifier (e.g. `"claude-sonnet-4-6"`) |
| `active_profile` | `str \| None` | Agent profile ID currently in use (e.g. `"python-pedro"`) |
| `active_role` | `str \| None` | Role label (`"implementer"`, `"reviewer"`, `"planner"`) |
| `current_activity` | `str \| None` | Activity type (`"implement"`, `"review"`, `"specify"`, `"plan"`) |
| `tech_stack` | `frozenset[str]` | Active technology identifiers (e.g. `{"python", "pytest"}`) |

All fields default to `None` / empty frozenset. `OperationalContext` is **specced but not wired** in this mission — it is reserved for future context-aware activation filtering (e.g., profile-scoped activation, model-aware resolution). Wiring is deferred to a follow-on mission.

**Scope in this mission**: Define the class body and guard methods only. `build_operational_context()` is a stub returning `OperationalContext()` with all defaults. Zero production call sites are required or expected.

**Dead-symbol disposal**: The four `OperationalContext`-family symbols (`OperationalContext`, `build_operational_context`, `require_active_profile`, `require_active_role`) are added to `_CATEGORY_C_WP_IN_FLIGHT_CHARTER_SCOPE` in `tests/architectural/test_no_dead_symbols.py` with per-symbol justification `"specced, wiring deferred to follow-on mission"`. The `_baselines.yaml` entry for this category must be updated accordingly.

**Guard methods**:
```python
def require_active_profile(self) -> str: ...
def require_active_role(self) -> str: ...
```

---

### ContextPreconditionError (exception)

Raised by `require_*()` guard methods when a required context field is absent.

```python
class ContextPreconditionError(RuntimeError):
    field: str         # e.g. "repo_root"
    context_type: str  # e.g. "ProjectContext"
    # message: "Context precondition failed: 'repo_root' is required but absent in ProjectContext"
```

**When to use**: Any method that operates on repository state must call `ctx.require_repo_root()` at entry. Any method that filters by activation state must call `ctx.require_pack_context()` at entry. The guard replaces ad-hoc `if repo_root is None: raise ValueError(...)` patterns throughout the codebase.

---

### Module Ownership

| Module | Role |
|--------|------|
| `src/charter/invocation_context.py` | Defines `ProjectContext`, `OperationalContext`, `ContextPreconditionError`, and all guard methods — charter owns these types entirely |
| call sites in `specify_cli.*` | Import directly from `charter.invocation_context`; construct `ProjectContext.from_repo(repo_root)` inline at CLI entry points — no wrapper package or factory module needed |

`charter.*` functions import `ProjectContext` from `charter.invocation_context` (same-package, no violation). `specify_cli.*` functions import from `charter.invocation_context` directly — the `specify_cli → charter` direction is allowed by the layer rules. No new `specify_cli.*` package is created for this purpose; `src/specify_cli/context/` is an existing MissionContext identity package with unrelated semantics and must not be extended with charter types. `doctrine.*` defines a narrow `ProjectContextProtocol` matching only the fields it uses (resolves C-004 / A2 — no charter import needed in doctrine).

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
  → ctx = ProjectContext.from_repo(repo_root)
  → CharterPackManager.activate(ctx, "directive", "python-style-guide", CascadeScope.none)
  → read current activated_directives from config.yaml via ctx.pack_context
  → if None: initialize to all built-ins from default.yaml, warn if third-party loss, then add python-style-guide
  → if frozenset: add python-style-guide
  → write back to config.yaml via ruamel.yaml round-trip
  → if no cascade: warn "The following cross-references were not cascaded: ..."
  → emit success message
```

### charter deactivate flow with cascade

```
user: charter deactivate directive python-style-guide --cascade tactic
  → ctx = ProjectContext.from_repo(repo_root)
  → CharterPackManager.deactivate(ctx, "directive", "python-style-guide", CascadeScope({"tactic"}))
  → if activated_directives is None: exit 1 with upgrade guidance
  → remove python-style-guide from activated_directives
  → find all tactic IDs referenced by python-style-guide (DRG edges)
  → for each referenced tactic T:
      → if T is referenced by any OTHER currently-activated artifact of any kind: skip, warn "T is shared, not deactivated"
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
