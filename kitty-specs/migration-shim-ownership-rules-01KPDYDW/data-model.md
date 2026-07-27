# Data Model — Migration and Shim Ownership Rules

**Mission**: `migration-shim-ownership-rules-01KPDYDW`
**Phase**: 1 (Design)
**Spec refs**: FR-003, FR-007, FR-008, FR-010

---

## Entity 1: Registry Entry

One YAML mapping per shim under the top-level `shims:` list in `architecture/2.x/shim-registry.yaml`.

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `legacy_path` | `string` | yes | Dotted import path of the shim, e.g. `specify_cli.charter`. Unique across the registry — acts as the entry's primary key for the FR-010 scanner's join. |
| `canonical_import` | `string \| list[string]` | yes | Target import. List form for umbrella shims that re-export from multiple canonicals (spec edge-case #3). |
| `introduced_in_release` | `string` (semver) | yes | Release version in which the shim was introduced. Matches regex `^\d+\.\d+\.\d+(?:[a-z]\d+)?$`. |
| `removal_target_release` | `string` (semver) | yes | Release in which the shim must be removed. Must be ≥ `introduced_in_release`. |
| `tracker_issue` | `string` | yes | GitHub issue reference: `#NNN` shorthand or `https://…` URL. |
| `grandfathered` | `bool` | yes | `true` iff the entry is a pre-existing non-conforming shim (FR-008). Default `false`. |
| `extension_rationale` | `string` | conditional | Required when `removal_target_release` has been extended beyond the original one-release deprecation window (FR-004, ADD-4). A non-empty string. |
| `notes` | `string` | optional | Free-text annotations. |

### Validation rules

1. All required fields present.
2. Field types match the table above.
3. Semver-shaped release strings match the regex.
4. `removal_target_release >= introduced_in_release` (semver-aware comparison via `packaging.version.Version`).
5. `canonical_import` when a list contains at least one string; each element is a valid dotted path (regex `^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$`).
6. `grandfathered` is a `bool`, not a string `"true"` / `"false"`.
7. `extension_rationale`, if present, is a non-empty string.
8. `tracker_issue` matches `^#\d+$` OR `^https?://`.

### State transitions

A registry entry has three logical states derived from current project version and filesystem:

```
 +------------+   release shipped   +-----------+
 |  pending   | ------------------> |  overdue  |
 +------------+                     +-----------+
       |                                  |
       | shim file deleted                | shim file deleted
       | (removal PR merged)              | (removal PR merged)
       v                                  v
 +------------+                    +-----------+
 |  removed   | <---------- (same) | removed   |
 +------------+                    +-----------+

 grandfathered=true  ->  advisory state, never `overdue`
```

States:
- **pending**: `current_version < removal_target_release` AND module file exists. Normal case during deprecation window.
- **overdue**: `current_version >= removal_target_release` AND module file exists. Doctor subcommand fails (exit 1).
- **removed**: module file absent. Doctor subcommand prints an advisory; operator may delete the entry in a follow-up PR.
- **grandfathered**: `grandfathered: true`. Doctor subcommand emits an advisory; never fails on this entry (FR-008, acceptance scenario 5).

### Example entries

**Single-target, standard lifecycle**:
```yaml
shims:
  - legacy_path: specify_cli.charter
    canonical_import: spec_kitty.charter
    introduced_in_release: "3.1.0"
    removal_target_release: "3.2.0"
    tracker_issue: "#610"
    grandfathered: false
    notes: "Re-export shim created by mission #610; auto-removed in 3.2.0."
```

**Umbrella shim, multiple canonical imports**:
```yaml
  - legacy_path: specify_cli.runtime
    canonical_import:
      - runtime.mission
      - runtime.executor
    introduced_in_release: "3.2.0"
    removal_target_release: "3.3.0"
    tracker_issue: "https://github.com/Priivacy-ai/spec-kitty/issues/612"
    grandfathered: false
```

**Grandfathered entry**:
```yaml
  - legacy_path: specify_cli.legacy_helper
    canonical_import: specify_cli.helpers.canonical_helper
    introduced_in_release: "2.8.0"
    removal_target_release: "4.0.0"
    tracker_issue: "#NNN"
    grandfathered: true
    notes: "Pre-#615 shim. Does not emit DeprecationWarning; scheduled for full rewrite in 4.0."
```

**Entry with extension**:
```yaml
  - legacy_path: specify_cli.glossary
    canonical_import: glossary.api
    introduced_in_release: "3.2.0"
    removal_target_release: "3.4.0"
    tracker_issue: "#613"
    grandfathered: false
    extension_rationale: "External downstream importers (2 known) need a full release of lead time; extended from 3.3.0 to 3.4.0 per review discussion in PR #NNN."
```

---

## Entity 2: Shim Module (the Python artefact on disk)

Every Python module under `src/specify_cli/` that is a compatibility shim MUST expose the following module-level attributes per FR-003.

### Required attributes

| Attribute | Type | Value semantics |
|-----------|------|-----------------|
| `__deprecated__` | `bool` | Always `True` on a shim module. The FR-010 scanner uses this to discover shims. |
| `__canonical_import__` | `str` or `list[str]` | Dotted path(s) of the canonical module(s). Must match the registry entry's `canonical_import`. |
| `__removal_release__` | `str` (semver) | Must match the registry entry's `removal_target_release`. |
| `__deprecation_message__` | `str` | The human-readable message emitted in the `DeprecationWarning`. Typically `"{legacy_path} is deprecated; import from {canonical_import}. Scheduled for removal in {removal_release}."` |

### Required behaviour on import

```python
import warnings
warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)
```

`stacklevel=2` is mandatory (FR-003) so the warning points at the user's import site rather than the shim itself.

### Scanner contract (FR-010)

The scanner test:
1. Walks `src/specify_cli/` for every `.py` file.
2. For each file, parses via `ast` (no import — side-effect-free) and checks for a module-level assignment `__deprecated__ = True`.
3. Builds a set of legacy paths from those modules (dotted path derived from file path).
4. Loads the registry YAML and builds a set of `legacy_path` values.
5. Asserts scanner-set ⊆ registry-set; emits a precise failure message listing any shim found on disk but missing from the registry.

**Why AST and not import**: importing a shim triggers its `DeprecationWarning`, which would pollute test output and could mask real failures. AST inspection is side-effect-free.

---

## Entity 3: Rulebook Rule Family

Structural description of `architecture/2.x/06_migration_and_shim_rules.md`. Each rule family is a top-level section in the rulebook.

| Family | Scope | Authoritative rule |
|--------|-------|-------------------|
| (a) schema/version gating | Project and bundle-level schema versioning | The rulebook describes current schema-version contract and names #461 Phase 7 as the follow-up that will extend coverage to doctrine artefacts (FR-013). |
| (b) bundle/runtime migration authoring contract | How a migration module must be authored | Migration module shape, idempotency, test expectations. Authoritative across future extraction PRs (#612, #613, #614). |
| (c) compatibility shim lifecycle | Shim module shape and lifecycle | Required module attributes (Entity 2), `DeprecationWarning` emission rules, one-release deprecation window with extension mechanism (FR-003, FR-004). |
| (d) removal plans and the registry contract | How removal is scheduled and enforced | Registry schema (Entity 1), removal-PR contract (FR-005), CI check behaviour (FR-009). |

---

## Entity 4: Doctor Check Output

Structured output of `spec-kitty doctor shim-registry`.

### Rich table rows

Each registry entry renders as one row with:
- `legacy_path` (string)
- `canonical_import` (string; list-form joined with `, `)
- `removal_target` (string)
- `status` (enum: `pending | overdue | grandfathered | removed`, color-coded)

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All entries pending OR removed OR grandfathered (advisories allowed). |
| 1 | At least one entry is overdue. |
| 2 | Configuration error (registry file missing/unparseable, `pyproject.toml` missing, etc.). |

### Summary footer

After the table:
- Count per status.
- If any `overdue`: repeated block per overdue entry with legacy path, canonical import, removal target, tracker issue, and suggested remediation (delete the shim OR update `removal_target_release` with `extension_rationale`).
