# Data Model — Slice F: Multi-Context Extensibility + Strategic Remediations

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Companion: [plan.md](plan.md) | [contracts/](contracts/)

This document defines the new and extended data shapes introduced by the mission. All schemas are Pydantic v2 (matching the existing codebase conventions). Field defaults preserve NFR-001 backward compatibility — every new field defaults so existing fixtures parse unchanged.

Cross-mission reuse: this mission **reuses, does not redefine**, the following shapes from Mission B (per C-009):

- `DoctrineSelectionConfig.selected_<kind>` (8 kinds, plural naming, union semantics) — [Mission B data-model §1](../charter-mediated-doctrine-selection-01KRTZCA/data-model.md#1-doctrineselectionconfig--extension-fr-001).
- `OrgCharterPolicy.required_<kind>` (8 kinds, plural naming, union semantics) — [Mission B data-model §2](../charter-mediated-doctrine-selection-01KRTZCA/data-model.md#2-orgcharterpolicy--extension-fr-002-fr-008).
- `ActivationEntry` (activation registry surface) — [Mission B data-model §3](../charter-mediated-doctrine-selection-01KRTZCA/data-model.md#3-activationentry--new-fr-006).
- `MissionTypeProfile` — [Mission B data-model](../charter-mediated-doctrine-selection-01KRTZCA/data-model.md). The org-DRG schema does NOT re-implement the kind set; it inherits the 8-kind universe by reference.

---

## 1. New data shapes — summary table

| # | Shape | Location | FR | Purpose |
|---|---|---|---|---|
| 2 | `OrgDRGFragment` | `src/charter/drg.py` | FR-001 | One loaded organisation-tier DRG fragment with provenance metadata |
| 3 | `OrgDRGConflict` | `src/charter/drg.py` | FR-004, FR-005 | Typed conflict report when shipped/org/project layers disagree |
| 4 | `CharterScope` | `src/charter/scope.py` | FR-009, FR-010 | Runtime resolver for "which charter applies to this filesystem path" |
| 5 | `WorkflowSequence` | `src/specify_cli/next/_internal_runtime/workflow_schema.py` | FR-012 | First-class artifact for a mission's action sequence |
| 6 | `ActionStep` | `src/specify_cli/next/_internal_runtime/workflow_schema.py` | FR-012 | One step within a `WorkflowSequence` |
| 7 | `RatchetBaseline` (YAML schema, not Pydantic) | `tests/architectural/_baselines.yaml` | FR-110 | Per-test, per-category baseline sizes for every mutable allowlist |
| 8 | `CatalogMissEvent` (logging payload extension) | `src/charter/_catalog_miss.py` (no new module) | FR-131 | Structured-log `extra=` dict fields for the FR-131 Rich-aware handler |
| 9 | `Mission.meta_json.workflow_id` | `kitty-specs/<mission>/meta.json` (operator-facing) | FR-013 | Optional field selecting the active workflow; `None` ⇒ `software-dev-default` |

---

## 2. `OrgDRGFragment` (FR-001)

Location: `src/charter/drg.py`

A loaded organisation-tier DRG fragment with provenance metadata. The loader produces one instance per configured org pack.

### Fields

| Field | Type | Required | Purpose |
|---|---|---|---|
| `pack_name` | `str` | yes | Organisation pack identifier (e.g. `acme-compliance`). Must match the `org_name` in the pack's `org-charter.yaml` |
| `source_kind` | `Literal["local_path", "url", "package"]` | yes | Source mechanism. **This mission ships `local_path` only** (NEW-1 resolution); `url` and `package` are reserved for follow-up |
| `source_ref` | `str` | yes | The configured reference: filesystem path for `local_path`; URL for `url`; package name for `package` |
| `layer_index` | `int` | yes | Merge order index. `0` = shipped (built-in); `1..N` = org fragments in `.kittify/config.yaml` declaration order; `N+1` = project layer |
| `nodes` | `list[DRGNode]` | yes | DRG nodes contributed by this fragment (reuses `doctrine.drg.models.DRGNode`) |
| `edges` | `list[DRGEdge]` | yes | DRG edges contributed by this fragment (reuses `doctrine.drg.models.DRGEdge`) |
| `provenance_marker` | `Literal["org"]` | yes | Constant marker; every node/edge from this fragment is tagged `source: org:<pack_name>` in the resolved DRG |

### Invariants

- `source_kind == "local_path"` AND `Path(source_ref).is_dir()` MUST hold at load time. Missing path raises `OrgPackMissingError` per FR-004 (mirrors Mission B FR-015 missing-pack hard-fail).
- Every kind appearing in `nodes` MUST be one of the 8 canonical kinds inherited from Mission B (C-009 binding). Unknown kinds raise `pydantic.ValidationError`.
- `layer_index` MUST be unique within a single load operation. Duplicate layer indices indicate a programming error in the loader, not an operator error.

### Provenance threading

When `charter.context.build_charter_context` renders an artifact stanza, the `source` field on each contributing node is one of:

- `built-in` (shipped layer, no org/project override)
- `org:<pack_name>` (contributed by an `OrgDRGFragment`)
- `project` (contributed by the project's `.kittify/doctrine/graph.yaml`)

This is FR-001's "preserves per-artefact provenance" surface and is reachable to AC-1.

---

## 3. `OrgDRGConflict` (FR-004, FR-005)

Location: `src/charter/drg.py`

A typed exception (and accompanying report dataclass) for when shipped/org/project layers disagree.

### Fields (`OrgDRGConflict` dataclass)

| Field | Type | Required | Purpose |
|---|---|---|---|
| `kind` | `Literal["edge_override", "node_override", "kind_mismatch", "layer_rule_violation"]` | yes | The conflict category |
| `conflicting_layers` | `list[str]` | yes | Source markers involved (e.g. `["built-in", "org:acme-compliance"]`) |
| `target_id` | `str` | yes | The artifact/node/edge ID at the centre of the conflict |
| `shipped_value` | `Any` | yes (may be `None` for `node_override` where shipped omitted the node) | Shipped layer's contribution |
| `org_value` | `Any` | yes | Org layer's contribution |
| `project_value` | `Any \| None` | yes | Project layer's contribution (`None` if project did not override) |
| `resolution_applied` | `Literal["hard_fail", "shipped_wins", "project_wins"]` | yes | Resolution per the merge policy. Shipped invariants always win (`shipped_wins`); other conflicts hard-fail |

### Resolution rules

- **`kind == "layer_rule_violation"`** (FR-005): an org pack imports across the layer boundary (e.g. its DRG fragment declares a node that imports from `specify_cli.*`). ALWAYS hard-fails. `resolution_applied = "hard_fail"`.
- **`kind == "edge_override"` or `"node_override"` against a shipped invariant**: shipped wins; the org override is silently discarded but the conflict IS logged via the FR-131 handler so the operator sees it.
- **`kind == "kind_mismatch"`**: org fragment uses an unknown kind. Hard-fails at load (per C-009).

### Exception shape

```python
class OrgDRGConflictError(Exception):
    """Raised when an org-DRG fragment violates the layer rule or
    overrides a shipped invariant in a non-recoverable way."""

    def __init__(self, conflicts: list[OrgDRGConflict]):
        self.conflicts = conflicts
        super().__init__(self._format_message(conflicts))
```

---

## 4. `CharterScope` (FR-009, FR-010)

Location: `src/charter/scope.py`

The runtime abstraction that resolves "which charter applies to this filesystem path" given an optional monorepo layout.

### Fields

| Field | Type | Required | Purpose |
|---|---|---|---|
| `root` | `pathlib.Path` | yes | Absolute path to the charter root (the directory containing `.kittify/charter/`) |
| `name` | `str \| None` | no | Optional human-readable scope name (e.g. `auth`, `web`). `None` for the default single-project scope |
| `config_source` | `Literal["repo_root_default", "monorepo_config"]` | yes | How this scope was resolved |

### Constructors

- `CharterScope.default(repo_root: Path) -> CharterScope` — the single-project default. `root = repo_root`, `name = None`, `config_source = "repo_root_default"`. **Behaviour byte-identical to today's repo-root-only resolution** (FR-011, NFR-001).
- `CharterScope.resolve(repo_root: Path, feature_dir: Path) -> CharterScope` — reads `.kittify/config.yaml`'s optional `charter_scopes:` list. If absent, returns `CharterScope.default(repo_root)`. If present, walks upward from `feature_dir` and returns the nearest enclosing configured scope.

### Failure modes

- `CharterScopeConflict` — raised when two `.kittify/charter/` directories at incompatible nesting depths are configured (Scenario 2 exception path). The exception names both paths.
- `CharterScopeNotFound` — raised when `charter_scopes:` is configured but `feature_dir` is not under any scope's `root`. Operator-actionable error message names the scope roots present.

### Monorepo config shape (`.kittify/config.yaml`)

```yaml
charter_scopes:
  - root: packages/auth
    name: auth
  - root: packages/web
    name: web
```

Single-project repos OMIT `charter_scopes:` entirely and behave identically to today (FR-011 / NFR-001 binding).

---

## 5. `WorkflowSequence` (FR-012)

Location: `src/specify_cli/next/_internal_runtime/workflow_schema.py`

A first-class artifact representing a mission's action sequence.

### Fields

| Field | Type | Required | Purpose |
|---|---|---|---|
| `workflow_id` | `str` | yes | Unique identifier within `src/doctrine/workflows/`. Convention: kebab-case (`software-dev-default`, `our-team-design-first`) |
| `description` | `str` | yes | One-paragraph human-readable description shown in `spec-kitty workflow list` (future-mission CLI surface) |
| `actions` | `list[ActionStep]` | yes | The action graph. Must be acyclic and connected from the `initial` action |
| `initial` | `str` | yes | The starting action's `action_name`. Must match one entry in `actions` |
| `version` | `int` | yes | Workflow schema version. `1` for this mission; future workflow schema extensions bump this and the registry routes by version |

### Invariants

- `actions[*].action_name` MUST be unique within a workflow.
- `actions[*].next[*]` MUST reference an existing `action_name` (no dangling references).
- The action graph rooted at `initial` MUST be acyclic.
- For `workflow_id == "software-dev-default"`, the action sequence MUST produce the same `(current, next)` transitions as today's hardcoded sequence (`specify → plan → tasks → implement → review → merge`). This is the C-008 byte-stability contract, pinned by `tests/specify_cli/next/test_workflow_software_dev_default_is_byte_stable.py`.

---

## 6. `ActionStep` (FR-012)

Location: `src/specify_cli/next/_internal_runtime/workflow_schema.py` (within `WorkflowSequence`)

One step within a workflow.

### Fields

| Field | Type | Required | Purpose |
|---|---|---|---|
| `action_name` | `str` | yes | The action identifier (must match an entry in `ALLOWED_ACTIONS` from Mission B's vocabulary OR be a freeform team-defined action). Example: `specify`, `plan`, `design-review`, `tasks`, `implement`, `review`, `merge` |
| `next` | `list[str]` | yes | List of action_names that may follow this one. Single-element list = linear; multi-element = the runtime selects based on contextual signals (out of scope for this mission; reserved for future) |
| `description` | `str` | yes | One-line description shown in `spec-kitty next` output |
| `terminal` | `bool` | no, default `False` | If `True`, this step is a workflow terminus (`merge`-equivalent). `next` MUST be empty when `terminal: True` |

### Invariants

- For Mission C scope, `next` is treated as linear (first element wins). Multi-element semantics (branching) are reserved for follow-up missions.
- Freeform action names (e.g. `design-review`, not in `ALLOWED_ACTIONS`) are permitted — the runtime treats them as user-defined steps that emit the `description` text and advance to `next[0]`. Mission B's activation registry vocabulary is NOT extended by this mission (FR-012 explicit scope).

---

## 7. `RatchetBaseline` (FR-110, FR-141)

Location: `tests/architectural/_baselines.yaml`

YAML schema (NOT a Pydantic model — the meta-test reads it directly). Per-test, per-category baseline sizes for every mutable allowlist.

### Schema

```yaml
# Architectural ratchet baselines. Each entry is the maximum allowlist
# size the corresponding gate is permitted to have. A PR that wants
# to grow a ratchet MUST edit this file explicitly -- making growth
# reviewable as a one-line diff. Shrinkage is encouraged: a current
# size below baseline produces a warning (informational, non-fatal)
# that the next PR should shrink the baseline.

test_no_dead_modules:
  # Per-category to make growth visible:
  category_1_auto_discovered: <int>           # auto-discovered migrations
  category_2_schema_generators: <int>         # build-script schema generators
  category_3_external_entry_points: <int>     # external CLI / hook entry points
  category_4_compat_shims: <int>              # documented backward-compat shims
  category_5_slot_holders: <int>              # WP-in-flight slot-holder adapters
  category_6_internal_runtime: <int>          # frozen-contract internal re-exports
  category_7_grandfathered: <int>             # MUST SHRINK -- target 0 by 4.0 (C-006)

test_migration_chain_integrity:
  known_line_jumps: <int>
  known_patch_skips: <int>                    # NEW with Gap-A8 (optional extension)

test_runtime_charter_doctrine_boundary:
  baseline_allowlist: <int>                   # capped at 2 per C-004

test_auth_transport_singleton:
  allowed_direct_httpx_files: <int>           # NO CHANGE this mission (C-005 binds)

test_compat_shims:
  pure_shim_files: <int>                      # MUST SHRINK -- target 0 by 4.0 (C-006)

test_example_round_trip:
  legacy_contract_allowlist: <int>            # FR-141: shrinks as legacy contracts get frontmatter

test_all_declarations_required:
  charter_without_all: <int>                  # MUST SHRINK as src/charter/ migrates (FR-121)
  kernel_without_all: <int>                   # MUST SHRINK as src/kernel/ migrates (FR-121)
```

### Initial values for this mission

To be determined by WP01 implementer from HEAD-of-mission-branch readings. Initial Cat-7 baseline lands at `10`; WP01's same-PR shrinkage drops it to `7` (FR-113). The legacy contract allowlist baseline is determined by `test_example_round_trip.py`'s initial discovery sweep (RR-7).

### Meta-test semantics (FR-111)

- Current allowlist size > baseline ⇒ **FAIL** with a message naming the test, the category (if applicable), the baseline, the current size, and remediation hint (`Either remove the new entry OR edit _baselines.yaml from <baseline> to <current> with a justification comment`).
- Current allowlist size < baseline ⇒ **WARN** (pytest warning) with a message encouraging the operator to shrink the baseline.
- Current allowlist size == baseline ⇒ **PASS** silently.

---

## 8. `CatalogMissEvent` — logging payload extension (FR-131)

Location: `src/charter/_catalog_miss.py` (no new module; extends existing `_LOGGER.warning(extra=...)` payload)

When the FR-131 Rich-aware handler emits a catalog-miss warning, the log record's `extra=` dict MUST carry the following fields. The handler reads these to format the operator-facing message.

### Fields

| Field | Type | Required | Purpose |
|---|---|---|---|
| `kind` | `str` | yes | The artifact kind that missed (e.g. `styleguide`, `directive`) |
| `id` | `str` | yes | The artifact ID that didn't resolve |
| `cause` | `Literal["typo", "missing", "schema_validation_suspected"]` | yes | Inferred cause classification |
| `suggestion` | `str \| None` | no | Closest-match suggestion (e.g. `caveman-comments` for typo `caveman-comemnts`). `None` if no suggestion can be computed |
| `mission_id` | `str \| None` | no | The mission ULID at the time of the miss (for cross-referencing) |
| `scope` | `str \| None` | no | The `CharterScope.name` if a monorepo scope is active; `None` otherwise |

### Output format (rendered by the Rich-aware handler)

```
[WARNING] Catalog miss: <kind>=<id> (cause=<cause>). <suggestion?> [mission=<mission_id>, scope=<scope>]
```

See [`contracts/catalog-miss-cli-visibility.md`](contracts/catalog-miss-cli-visibility.md) for the full handler contract.

---

## 9. `Mission.meta_json.workflow_id` — meta.json extension (FR-013)

Location: `kitty-specs/<mission>/meta.json` (operator-facing)

A mission's `meta.json` gains an optional `workflow_id: str | None` field.

### Semantics

| Value | Behaviour |
|---|---|
| `null` (or absent) | Resolves to `software-dev-default`. Byte-identical to today's hardcoded sequence (C-008). **Pre-Slice-F missions continue to work unchanged** (NEW-2: permanent default, opt-in workflow selection) |
| `"<known-id>"` | Resolves via the registry to the named workflow YAML. Used by AC-4 fixture mission |
| `"<unknown-id>"` | **Hard-fail** at `spec-kitty next` time with a message naming the unknown id and listing the directory of available workflows (FR-015) |

### Backward compatibility

This mission does NOT retrofit historical missions to populate `workflow_id` (C-002 forward-only). The field is purely opt-in.

---

## 10. Reuse from Mission B (cited, not redefined per C-009)

| Mission B shape | Reuse semantics in Slice F |
|---|---|
| `DoctrineSelectionConfig.selected_<kind>` | The org-DRG schema's `nodes` MUST use the same 8 kinds; no new kind universe is introduced |
| `OrgCharterPolicy.required_<kind>` | Org packs continue to declare `required_<kind>` for selection-layer pre-fills; the new org-DRG fragment ships alongside, not replacing |
| `ActivationEntry` | Context-scoped activations (Mission B FR-006) continue to work; org-DRG additions are global-mode rules per FR-001 |
| `MissionTypeProfile` | Mission-type profiles are the runtime consumer of the union (selected ∪ required ∪ org-DRG); Slice F threads the org-DRG layer into the existing resolver |
| `_OPTIONAL_EMPTY_OMIT_KEYS` | The new `workflow_id` field participates in the byte-stability allow-list when `None` so legacy missions' `meta.json` is unchanged |

---

## 11. Compatibility matrix at mission close

| Surface | Pre-Slice-F | Post-Slice-F (no opt-in) | Post-Slice-F (opt-in to all three axes) |
|---|---|---|---|
| `build_charter_context(repo_root, feature_dir)` | renders shipped + project | renders shipped + project (unchanged) | renders shipped + org + project with provenance |
| `spec-kitty next --mission <handle>` | uses hardcoded sequence | uses `software-dev-default` workflow (byte-stable) | uses the workflow named in `meta.json.workflow_id` |
| `.kittify/charter/charter.md` | repo-root resolution | repo-root resolution (unchanged) | nearest-enclosing monorepo scope |
| Catalog miss with typo | invisible to operator | **visible on stderr via the Rich-aware handler** | (same — bootstrap improvement is global) |
| `from charter import resolve_governance` | works | **ImportError** (FR-103) | **ImportError** |

The single non-back-compat behaviour change is the catalog-miss visibility (intentional and operator-positive per FR-131) and the alias deletion (binding per HiC §5a.1 / C-003).
