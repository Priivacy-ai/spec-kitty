# Contract: `.kittify` protected-branch configuration + resolver

## Configuration schema (additive)

A new top-level `protection:` block in `.kittify/config.yaml`. Backward compatible: absent block ⇒
current default behavior.

```yaml
# round-trip: skip: operator-config shape sketch — resolved by the frozen ProtectionPolicy dataclass + raw-YAML protection_policy.resolve (fail-closes via ProtectionConfigError), no Pydantic model_validate payload (#2255)
# .kittify/config.yaml
protection:
  # Branches the safe-commit guard refuses direct commits to.
  # - key ABSENT entirely        -> default {main, master} (+ remote default branch) [unchanged behavior]
  # - key present, list NON-empty -> exactly this set is protected
  # - key present, list EMPTY ([]) -> NOTHING is protected (owner opts the primary out)
  protected_branches:
    - main
    - release/*        # exact names today; glob support is a possible future extension (out of scope)
```

### Resolution rules (normative)

| Config state | Resolved `protected_branches` |
|--------------|-------------------------------|
| no `protection:` block | `{main, master}` ∪ {remote default branch} — **byte-identical to today** (NFR-004) |
| `protection.protected_branches: [a, b]` | `{a, b}` (exactly; no name-default union) |
| `protection.protected_branches: []` | `frozenset()` — nothing protected (US2 edge case) |
| malformed value (non-list) | resolver raises a clear config error (fail-closed; no silent default) |

Operator hatch `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` is unchanged (FR-006) and is resolved onto
`ProtectionPolicy.operator_hatch_active` at the boundary; when active, `is_protected()` returns `False`.

## Resolver contract

```python
# src/specify_cli/git/protection_policy.py
@dataclass(frozen=True)
class ProtectionPolicy:
    protected_branches: frozenset[str]
    operator_hatch_active: bool

    @classmethod
    def resolve(cls, repo_root: Path) -> "ProtectionPolicy": ...   # SOLE producer; all I/O here
    def is_protected(self, ref: str) -> bool: ...                  # ref in set and not hatch
```

- `resolve()` is the **only** sanctioned function that reads the protection set from git/filesystem/env
  (FR-007, NFR-003). `git/commit_helpers.protected_branches()` is demoted to its private delegate.
- The FR-010 architectural guard allowlists exactly `protection_policy.resolve` (+ the demoted
  `commit_helpers.protected_branches`); any other module computing a protection decision from a raw
  `protected_branches(repo_root)` call or a literal `{"main", "master"}` set fails CI.

## safe_commit integration contract (pillar A boundary)

```python
# safe_commit gains an optional injected policy; resolves-if-None for back-compat.
def safe_commit(*, repo_root: Path, worktree_root: Path, target: CommitTarget,
                protection: ProtectionPolicy | None = None, ...) -> CommitResult: ...
```

- When `target` ref is protected (`protection.is_protected(ref)`), `safe_commit` (or its
  `safe_commit_cmd` caller) materializes the coordination worktree via `CoordinationWorkspace.resolve()`
  and routes the commit there — **materialize-then-retry**, idempotent if already materialized.
- When not protected, commit proceeds directly on the target (the documented runbook behavior, FR-005).
- The internal `protected_branches(repo_root)` + `protected_branches(worktree_root)` reads
  (`commit_helpers.py:1017-1020`) are replaced by `protection.is_protected(...)`.

## Compatibility

- No change to the wire/CLI surface for repos without the `protection:` block.
- No change to `core/commit_guard.evaluate` or `ProtectionState`.
- Coordination-worktree on-disk layout unchanged (reuses `CoordinationWorkspace`).
