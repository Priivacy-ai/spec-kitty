# Quickstart: State Model Cleanup Foundations

## What This Feature Does

Adds a machine-readable state contract, aligns Git boundaries for runtime state, and provides a diagnostic command to inspect state roots.

## Using the Doctor Command

```bash
# Show state roots, surface classifications, and safety warnings
spec-kitty doctor state-roots

# Machine-readable output
spec-kitty doctor state-roots --json
```

### Example Output

```
State Roots
───────────────────────────────────────────────────────
  project         .kittify/              ✓ exists
  global_runtime  ~/.kittify/            ✓ exists
  global_sync     ~/.spec-kitty/         ✗ absent

Project Surfaces (.kittify/)
───────────────────────────────────────────────────────
  Name                  Authority       Git Policy    Present
  project_config        authoritative   tracked       ✓
  project_metadata      authoritative   tracked       ✓
  dashboard_control     local_runtime   ignored       ✗
  workspace_context     local_runtime   ignored       ✗
  merge_resume_state    local_runtime   ignored       ✗
  runtime_feature_index local_runtime   ignored       ✗
  ...

Warnings
───────────────────────────────────────────────────────
  ⚠ None — all runtime surfaces are properly ignored.
```

## Using the State Contract in Code

```python
from specify_cli.state_contract import (
    STATE_SURFACES,
    StateRoot,
    AuthorityClass,
    GitClass,
    get_surfaces_by_root,
    get_runtime_gitignore_entries,
)

# List all project-local surfaces
for s in get_surfaces_by_root(StateRoot.PROJECT):
    print(f"{s.name}: {s.authority.value} / {s.git_class.value}")

# Get gitignore patterns for runtime state
patterns = get_runtime_gitignore_entries()
# ['.kittify/.dashboard', '.kittify/runtime/', '.kittify/merge-state.json', ...]
```

## Three State Roots

| Root | Path | Contains |
|------|------|----------|
| **project** | `<repo>/.kittify/` | Project config, workspace context, runtime caches |
| **global_runtime** | `~/.kittify/` | Package assets, version lock, bootstrap cache |
| **global_sync** | `~/.spec-kitty/` | Sync config, credentials, queue DBs, tracker cache |

Plus two non-directory roots:
- **feature**: `kitty-specs/<feature>/` — per-feature spec, status, task state
- **git_internal**: `.git/spec-kitty/` — review feedback artifacts

## After Upgrade

If upgrading from a version before this feature, run `spec-kitty upgrade` to add the missing `.gitignore` entries for runtime state. Then verify:

```bash
spec-kitty doctor state-roots
```
