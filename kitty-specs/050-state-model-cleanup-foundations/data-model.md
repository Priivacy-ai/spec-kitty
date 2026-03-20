# Data Model: State Model Cleanup Foundations

## Entities

### StateRoot (Enum)

Classifies where a state surface lives on the filesystem.

| Value | Description | Resolved Path |
|---|---|---|
| `PROJECT` | Project-local config and workflow state | `<repo>/.kittify/` |
| `FEATURE` | Per-feature spec, status, and task state | `<repo>/kitty-specs/<feature>/` |
| `GLOBAL_RUNTIME` | User-global runtime assets and bootstrap cache | `~/.kittify/` (or `$SPEC_KITTY_HOME`) |
| `GLOBAL_SYNC` | User-global sync, auth, queue, and tracker state | `~/.spec-kitty/` |
| `GIT_INTERNAL` | State stored under `.git` common-dir | `<repo>/.git/spec-kitty/` |

### AuthorityClass (Enum)

Classifies the ownership and trust model for a state surface.

| Value | Description |
|---|---|
| `AUTHORITATIVE` | Single source of truth for its domain. Loss means data loss. |
| `DERIVED` | Can be regenerated from authoritative sources. Safe to delete. |
| `COMPATIBILITY` | Written for backward compatibility. Not read as authority by canonical paths. |
| `LOCAL_RUNTIME` | Machine-local operational state. Never commit. |
| `SECRET` | Contains credentials or tokens. Must be outside repo. |
| `GIT_INTERNAL` | Stored under `.git/`, not in working tree. |
| `DEPRECATED` | Kept for migration but should be removed in a future version. |

### GitClass (Enum)

Classifies the Git boundary for a state surface.

| Value | Description |
|---|---|
| `TRACKED` | Part of the intended project record. Committed to Git. |
| `IGNORED` | Matched by `.gitignore`. Will not appear as untracked. |
| `INSIDE_REPO_NOT_IGNORED` | In the working tree but not ignored. Can be accidentally committed. |
| `GIT_INTERNAL` | Under `.git/` common-dir. Not in commits. |
| `OUTSIDE_REPO` | In user home directory. Never in project repo. |

### StateFormat (Enum)

Serialization format of the state surface.

| Value | Description |
|---|---|
| `JSON` | `.json` files |
| `YAML` | `.yaml` / `.yml` files |
| `TOML` | `.toml` files |
| `JSONL` | Append-only JSON Lines (`.jsonl`) |
| `SQLITE` | SQLite database files (`.db`) |
| `MARKDOWN` | `.md` files (with or without YAML frontmatter) |
| `TEXT` | Plain text (version stamps, PID files, scope markers) |
| `LOCKFILE` | File-based locks (`.lock`) |
| `DIRECTORY` | Directory presence is the state |
| `SYMLINK` | Symlink target is the state |

### StateSurface (Frozen Dataclass)

A single entry in the state contract registry.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Unique identifier (e.g., `"project_config"`) |
| `path_pattern` | `str` | Path template (e.g., `".kittify/config.yaml"`, `"kitty-specs/<feature>/meta.json"`) |
| `root` | `StateRoot` | Which filesystem root this surface belongs to |
| `format` | `StateFormat` | Serialization format |
| `authority` | `AuthorityClass` | Trust/ownership classification |
| `git_class` | `GitClass` | Git boundary classification |
| `owner_module` | `str` | Python module that owns writes to this surface |
| `creation_trigger` | `str` | What command/action creates this surface |
| `deprecated` | `bool` | Whether this surface is deprecated (default `False`) |
| `notes` | `str` | Free-text notes (e.g., "Git boundary decision deferred") |

**Constraints**:
- `name` must be unique across all surfaces
- Frozen (immutable after creation)
- No side effects at construction time

### StateRootInfo (Dataclass)

Doctor output: information about a resolved state root.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Root identifier (e.g., `"project"`) |
| `label` | `str` | Human-readable label (e.g., `"Project-local state"`) |
| `resolved_path` | `Path` | Actual filesystem path |
| `exists` | `bool` | Whether the directory exists on disk |

### SurfaceCheckResult (Dataclass)

Doctor output: check result for a single state surface.

| Field | Type | Description |
|---|---|---|
| `surface` | `StateSurface` | The surface being checked |
| `present` | `bool` | Whether the surface exists on disk |
| `gitignore_covered` | `bool` | Whether `.gitignore` covers this path (repo-local only) |
| `warning` | `str \| None` | Warning message if unsafe state detected |

### StateRootsReport (Dataclass)

Doctor output: aggregate report from `check_state_roots()`.

| Field | Type | Description |
|---|---|---|
| `roots` | `list[StateRootInfo]` | Info for each state root |
| `surfaces` | `list[SurfaceCheckResult]` | Check results per surface |
| `warnings` | `list[str]` | Aggregate warnings |
| `healthy` | `bool` (property) | `True` if no warnings |

## Relationships

```
StateRoot  ←──  StateSurface.root
AuthorityClass  ←──  StateSurface.authority
GitClass  ←──  StateSurface.git_class
StateFormat  ←──  StateSurface.format

STATE_SURFACES (tuple)  ──contains──►  StateSurface (many)

check_state_roots()  ──reads──►  STATE_SURFACES
                     ──produces──►  StateRootsReport
                                   ├── StateRootInfo (per root)
                                   └── SurfaceCheckResult (per surface)

GitignoreManager  ──derives──►  get_runtime_gitignore_entries()
                               ──reads──►  STATE_SURFACES
```

## State Transitions

None. This feature defines a static contract and read-only diagnostics. No mutable state transitions are introduced.
