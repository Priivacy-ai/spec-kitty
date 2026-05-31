---
work_package_id: WP09
title: 'OrgCharterPolicy extends: field + chain resolver + error classes'
dependencies:
- WP06
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: b186987a67b1e884133b12de78e4a9b097c90e8c
created_at: '2026-05-30T19:52:36.669251+00:00'
subtasks:
- T053
- T054
- T055
- T056
- T057
- T058
- T059
- T060
- T061-sig
- T062-chain
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3198823"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/org_charter.py
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/org_charter.py
- tests/specify_cli/doctrine/test_org_charter.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP09 — OrgCharterPolicy extends: field + chain resolver + error classes

## Context

FR-001 requires `org-charter.yaml` to support an optional `extends: <pack-name>` key for hierarchical pack composition. Currently the `OrgCharterPolicy` loader performs a flat multi-pack union with no chain traversal. This WP adds the `extends:` field, the chain resolver, cycle detection, missing-base detection, and schema_version mismatch handling.

The `extends:` chain makes the union relationship explicit and named. Existing packs without `extends:` continue to work as before (backward compatible).

## Objective

Add `schema_version` and `extends` fields to `OrgCharterPolicy`. Implement `_resolve_chain()` with cycle detection and missing-base detection. Implement merge semantics per C-002. Add `OrgCharterExtensionError` and `OrgCharterCycleError` classes. Write comprehensive tests.

## Resolution Semantics (C-002)

| Field | Semantics |
|---|---|
| `required_directives` | **Union** — overlay adds, never removes (raises error if removal attempted) |
| `required_toolguides` | **Union** — overlay adds, never removes |
| `interview_defaults` | **Per-key replacement** — overlay key wins; unmentioned keys inherit from base |
| `schema_version` | **Must match** — mismatch raises structured error |

## Subtasks

### T053 — Add schema_version field

**Before touching anything**, read the existing `OrgCharterPolicy` definition in `src/specify_cli/doctrine/org_charter.py`. The field may already exist as `schema_version: str = "1"` (a string, not an integer).

If the field already exists as `str`:
- Do NOT simply change the type to `int` — this would break existing YAML files that have `schema_version: "1"` stored as a string.
- Add a Pydantic v2 `@field_validator('schema_version', mode='before')` that coerces string `"1"` (and other numeric strings) to `int` before validation:
  ```python
  @field_validator('schema_version', mode='before')
  @classmethod
  def _coerce_schema_version(cls, v: object) -> int:
      if isinstance(v, str):
          return int(v)
      return v  # type: ignore[return-value]
  ```
- Update the field annotation to `schema_version: int = 1`

If the field does not exist yet:
- Add `schema_version: int = 1` (no validator needed for a new field)

Either way, the result is `schema_version: int = 1` with backward-compatible YAML parsing.

### T054 — Add extends field

Add to `OrgCharterPolicy`:

```python
extends: str | None = None
```

This field names the base pack to extend. It is optional. Packs without `extends:` continue to be merged as before (flat union behavior preserved — backward compatible per FR-001).

Update `__all__` to include any new exported names.

### T055 — Implement _resolve_chain()

Add a private function `_resolve_chain(pack_name: str, pack_set: dict[str, OrgCharterPolicy]) -> list[OrgCharterPolicy]`:

```python
def _resolve_chain(
    pack_name: str,
    pack_set: dict[str, OrgCharterPolicy],
) -> list[OrgCharterPolicy]:
    """Resolve the extends: chain starting from pack_name.

    Returns [base, ..., overlay] in resolution order (base first).
    Raises OrgCharterCycleError on cycles.
    Raises OrgCharterExtensionError if a named base is not in pack_set.
    """
```

Algorithm:
1. Start at `pack_name`; walk `extends:` pointers depth-first
2. Maintain a `visited: set[str]` to detect cycles
3. If the current pack's `extends:` names a pack not in `pack_set`: raise `OrgCharterExtensionError`
4. If a cycle is detected (pack already in `visited`): raise `OrgCharterCycleError`
5. Return the chain in base-first order: `[root_base, ..., overlay]`

### T056 — Add OrgCharterCycleError

```python
class OrgCharterCycleError(Exception):
    """Raised when an extends: chain contains a cycle."""

    def __init__(self, cycle_path: list[str]) -> None:
        self.cycle_path = cycle_path
        super().__init__(
            f"Cycle detected in extends: chain: {' → '.join(cycle_path)}"
        )
```

### T057 — Add OrgCharterExtensionError

```python
class OrgCharterExtensionError(Exception):
    """Raised when the named base pack is not present in the loaded pack set."""

    def __init__(self, missing_pack: str, chain: list[str]) -> None:
        self.missing_pack = missing_pack
        self.chain = chain
        super().__init__(
            f"Base pack '{missing_pack}' not found. Chain: {' → '.join(chain)}"
        )
```

### T058 — Implement merge logic

Add `_merge_chain(chain: list[OrgCharterPolicy]) -> OrgCharterPolicy`:

```python
def _merge_chain(chain: list[OrgCharterPolicy]) -> OrgCharterPolicy:
    """Merge a chain [base, ..., overlay] into a single resolved policy.

    required_directives, required_toolguides: union (overlay adds, never removes).
    interview_defaults: per-key replacement (overlay wins per key).
    schema_version: must match across all entries.
    """
```

Union semantics for `required_directives` and `required_toolguides`: use `set.union()` — the result is the complete set from all layers.

Per-key replacement for `interview_defaults`: iterate from base to overlay, applying `dict.update()` — overlay key wins.

`extends:` field on the result: set to `None` (the merged result is the resolved policy, not a chain).

### T059 — Implement schema_version mismatch error

In `_merge_chain()`, before merging:

```python
versions = {p.schema_version for p in chain}
if len(versions) > 1:
    raise ValueError(
        f"schema_version mismatch in extends: chain. "
        f"Versions found: {sorted(versions)}. All packs in a chain must share the same schema_version."
    )
```

The error message includes the version values found and the chain context.

### T060 — Tests for extends chain, cycle detection, merge semantics

Extend `tests/specify_cli/doctrine/test_org_charter.py`:

Test cases:
- **Simple extends**: Pack B extends Pack A; merged `required_directives` = union of A and B
- **Depth-2 chain**: Pack C extends B extends A; directives are union of all three
- **Union semantics**: B adds `"NEW_DIR"` to A's directives; result includes both
- **Per-key interview_defaults**: B overrides key `foo` but inherits key `bar` from A
- **Cycle detection**: A extends B, B extends A → `OrgCharterCycleError` with cycle path
- **Self-reference**: A extends A → `OrgCharterCycleError`
- **Missing base**: A extends "nonexistent" → `OrgCharterExtensionError` with chain
- **Schema version mismatch**: A has `schema_version: 1`, B extends A with `schema_version: 2` → structured error
- **Backward compatibility**: Pack without `extends:` still merges as before; existing flat-union tests still pass

### T061-sig — Update load_org_charter_policies() signature

In `src/specify_cli/doctrine/org_charter.py`, update the `load_org_charter_policies()` function signature to accept an optional `PackContext`:

Before:
```python
def load_org_charter_policies(repo_root: Path) -> list[OrgCharterPolicy]:
```

After:
```python
def load_org_charter_policies(
    repo_root: Path,
    pack_context: "PackContext | None" = None,
) -> list[OrgCharterPolicy]:
```

Import `PackContext` from `charter.pack_context`. The import direction is valid per C-004: `specify_cli.doctrine.*` may import from `charter.*`.

The `PackContext | None` default maintains backward compatibility: when `None`, fall back to reading `.kittify/config.yaml` directly (existing behaviour). Callers are migrated in WP10.

### T062-chain — Wire _resolve_chain to use PackContext.pack_roots

When `pack_context` is not `None`, use `pack_context.pack_roots` to locate org-pack `org-charter.yaml` files instead of reading pack paths from `.kittify/config.yaml` directly.

Add a private helper `_build_pack_set(pack_context: PackContext) -> dict[str, OrgCharterPolicy]` that scans `pack_context.pack_roots` for `org-charter.yaml` files and loads them into a name-keyed dict. This replaces any existing direct `config.yaml` reads inside `_resolve_chain` when a `PackContext` is provided.

The pack name key is the directory name of the pack root (e.g., if `pack_root` is `.../org-packs/corp-baseline`, the key is `corp-baseline`). Use `pack_root.name` for the key.

## Acceptance Criteria

- [ ] `OrgCharterPolicy` has `schema_version: int = 1` and `extends: str | None = None`
- [ ] `_resolve_chain()` correctly resolves base-first chains
- [ ] `OrgCharterCycleError` includes the full cycle path
- [ ] `OrgCharterExtensionError` includes the chain that led to the failure
- [ ] Merge semantics: union for directives/toolguides; per-key for interview_defaults
- [ ] Schema version mismatch raises structured error with both version values
- [ ] Packs without `extends:` continue to work exactly as before
- [ ] All new tests pass; existing flat-union tests still pass
- [ ] `mypy --strict` clean

## References

- FR-001: extends: field requirement
- FR-002: OrgCharterExtensionError + OrgCharterCycleError
- FR-003: schema_version mismatch
- C-002: union-only semantics; interview_defaults exemption
- data-model.md §"OrgCharterPolicy (extended)"
- contracts/org-charter-extends-union-contract.md

## Activity Log

- 2026-05-30T19:52:37Z – claude:opus:python-pedro:implementer – shell_pid=3175824 – Assigned agent via action command
- 2026-05-30T20:00:41Z – claude:opus:python-pedro:implementer – shell_pid=3175824 – Ready for review: OrgCharterPolicy extends field, chain resolver with cycle detection, error classes, and PackContext signature. All 79 org_charter tests pass; mypy --strict clean.
- 2026-05-30T20:01:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=3198823 – Started review via action command
