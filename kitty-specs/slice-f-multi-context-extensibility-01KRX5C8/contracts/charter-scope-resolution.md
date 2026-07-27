# Contract — Charter Scope Resolution

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Closes: FR-008, FR-009, FR-010, FR-011 | Companions: [org-drg-schema.md](org-drg-schema.md)
> Data model: [../data-model.md §4](../data-model.md#4-charterscope-fr-009-fr-010)

`CharterScope` is the runtime resolver for "which charter applies to this filesystem path" in optional monorepo configurations. Single-project repositories behave identically to today.

---

## Input Contract

### Operator-facing surface — `.kittify/config.yaml` (optional)

For monorepos that want per-package charter scoping:

```yaml
# pydantic_model: charter.scope.CharterScopeConfig
# expect: valid
charter_scopes:
  - root: packages/auth
    name: auth
  - root: packages/web
    name: web
```

Single-project repositories OMIT this key entirely. The CharterScope resolver defaults to repo-root (FR-011, NFR-001).

### API surface — `charter/scope.py`

```python
from pathlib import Path
from charter.scope import CharterScope

# Default (single-project) — behaviour byte-identical to today
scope = CharterScope.default(repo_root)

# Resolve from a feature directory (monorepo-aware)
scope = CharterScope.resolve(repo_root, feature_dir)
```

### API surface — `charter/context.py`

```python
from charter.context import build_charter_context

# Single-project (no scope passed) — byte-identical to today's call site
result = build_charter_context(repo_root, action="implement")

# Monorepo (scope passed explicitly)
scope = CharterScope.resolve(repo_root, feature_dir)
result = build_charter_context(repo_root, action="implement", scope=scope)
```

When `scope=None` (the default), `build_charter_context` internally constructs `CharterScope.default(repo_root)`. **No behaviour change for the 23 existing governance-contract fixtures** (NFR-001 binding).

---

## Output Contract

### Resolution algorithm

`CharterScope.resolve(repo_root, feature_dir)`:

1. Read `.kittify/config.yaml`'s optional `charter_scopes` list. If absent, return `CharterScope.default(repo_root)`.
2. Compute the absolute path of `feature_dir`.
3. For each configured scope, compute the absolute path of `repo_root / scope.root`.
4. Find the configured scope whose `root` is the **nearest enclosing ancestor** of `feature_dir`. Tie-breaking: deepest match wins.
5. If no scope encloses `feature_dir`, raise `CharterScopeNotFound`.
6. If two scopes have incompatible nesting depths (e.g. `packages/auth` and `packages/auth/inner` both configured, and `feature_dir` is inside `packages/auth/inner/sub`), raise `CharterScopeConflict` naming both paths.

### Returned `CharterScope` fields

| Field | Default-case value | Monorepo-case value |
|---|---|---|
| `root` | `repo_root` (absolute) | `repo_root / scope.root` (absolute) |
| `name` | `None` | The configured `name` string |
| `config_source` | `"repo_root_default"` | `"monorepo_config"` |

### Threading into `build_charter_context`

When a non-default scope is active, `build_charter_context` reads the charter from `scope.root / .kittify/charter/charter.md` and threads the scope name into the rendered prompt's provenance metadata. Catalog-miss warnings include the scope name in their `extra=` dict (see [`catalog-miss-cli-visibility.md` §`scope` field](catalog-miss-cli-visibility.md#cataloggmissevent-extra-fields)).

---

## Failure modes

| Trigger | Exception | Operator message |
|---|---|---|
| `charter_scopes:` configured but `feature_dir` is not under any scope's `root` | `CharterScopeNotFound` | "No charter scope encloses `<feature_dir>`. Configured scopes: `<list>`. Either run from inside one of the configured scopes or add an entry to `.kittify/config.yaml`." |
| Two nested configured scopes claim the same `feature_dir` ambiguously | `CharterScopeConflict` | "Charter scope configuration is malformed: `<path_a>` and `<path_b>` both claim `<feature_dir>`. Reorganise the configuration so each path belongs to exactly one scope." (Scenario 2 exception path) |
| Configured `root` does not exist on disk | `CharterScopeConflict` | "Charter scope `<name>` configured at `<root>` does not exist. Remove the entry or create the directory." |
| The configured scope's `root` does not contain `.kittify/charter/` | `CharterScopeNotFound` | "Charter scope `<name>` at `<root>` does not contain `.kittify/charter/`. Run `spec-kitty charter scaffold` inside that directory or remove the scope entry." |

---

## Backward compatibility guarantee

- **NFR-001 binding**: repositories without `charter_scopes:` configured behave identically to today. The 23 `test_wp_prompt_governance_contract.py` fixtures pass unchanged.
- `build_charter_context(repo_root, action=...)` (no `scope=` keyword) constructs `CharterScope.default(repo_root)` internally; output is byte-identical to today.
- `CharterScope.default(repo_root)` is the only constructor used internally by Mission A / Mission B test fixtures and CLI flows — no migration required for any historical mission.

---

## Sample malformed configuration — round-trip frontmatter

```yaml
# pydantic_model: charter.scope.CharterScopeConfig
# expect: invalid
charter_scopes:
  - root: packages/auth
  # name field missing? Not required (Optional); this is still valid.
  # The invalid case below is empty root:
  - root: ""
```

Empty `root` is rejected by the validator.

---

## ATDD anchors

- `tests/integration/test_monorepo_charter_scope.py` (Scenario 2 happy + exception paths; AC-3)
- `tests/charter/test_charter_scope.py` (unit; default + resolve + conflict + not-found)
- `tests/specify_cli/next/test_wp_prompt_governance_contract.py` (regression; 23/23 unchanged; NFR-001)
