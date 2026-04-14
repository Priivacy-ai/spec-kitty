# Data Model: Unified Charter Bundle and Read Chokepoint

**Mission**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Companion**: [plan.md](plan.md), [contracts/](contracts/)

This feature introduces two new typed entities (`CharterBundleManifest`, `MigrationReport`), extends one existing entity (`SyncResult`), and adds two new exception types. No existing schema is retyped or renamed. All models are Pydantic (the project's existing typed-config standard).

**v1.0.0 scope**: the manifest and chokepoint cover the three files `src/charter/sync.py` materializes — `governance.yaml`, `directives.yaml`, `metadata.yaml`. `references.yaml` (compiler pipeline) and `context-state.json` (runtime state) are explicitly out of v1.0.0 scope and belong to different pipelines. Expanding scope requires a new manifest schema version and its own migration.

---

## Entity: `CharterBundleManifest`

**Module**: `src/charter/bundle.py` (new — introduced in WP2.1).
**Pattern**: Pydantic `BaseModel`.
**External contract**: [`contracts/bundle-manifest.schema.yaml`](contracts/bundle-manifest.schema.yaml) (JSON Schema draft-7).
**Schema version**: `"1.0.0"` — independent of the `spec-kitty` package version per D-1 / Q3=A.

### Purpose

Declares the files that `src/charter/sync.py` materializes as the project's governance bundle. Consumed by:

- `ensure_charter_bundle_fresh()` (the chokepoint) — for the "what files must exist" completeness check.
- `m_3_2_3_unified_bundle.py` (the migration) — for bundle validation on upgrade.
- `tests/charter/test_bundle_contract.py` — for the end-to-end manifest-vs-disk assertion.
- `spec-kitty charter bundle validate` — for the operator-facing validation CLI.

### Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `schema_version` | `str` | Yes | Semver string describing the manifest schema version. Starts at `"1.0.0"`. Bumped only when manifest shape or scope changes. |
| `tracked_files` | `list[Path]` | Yes | Every path (relative to the project root) that must be tracked in git. For v1.0.0: `[Path(".kittify/charter/charter.md")]`. |
| `derived_files` | `list[Path]` | Yes | Every path (relative to the project root) that is produced by `src/charter/sync.py` and must be gitignored. For v1.0.0: exactly the three files in `_SYNC_OUTPUT_FILES` at `src/charter/sync.py:32-36` — `governance.yaml`, `directives.yaml`, `metadata.yaml`. |
| `derivation_sources` | `dict[Path, Path]` | Yes | Maps each derived file to the source file it is derived from. For v1.0.0 every mapping is `<derived> → Path(".kittify/charter/charter.md")`. |
| `gitignore_required_entries` | `list[str]` | Yes | The exact strings that must appear in `.gitignore` for the derived files to be correctly ignored. For v1.0.0 the three entries matching `derived_files`. The project `.gitignore` MAY contain additional entries (e.g., for `context-state.json`, `references.yaml`) — the manifest's set is a "must include" floor, not an "only these" ceiling. |

### Validation rules

- `schema_version` must match the semver regex `^\d+\.\d+\.\d+$`.
- `tracked_files` must be non-empty (at minimum, `charter.md` is always tracked).
- No path may appear in both `tracked_files` and `derived_files` (enforced by a Pydantic model-level validator).
- Every key in `derivation_sources` must appear in `derived_files`.
- Every value in `derivation_sources` must appear in `tracked_files`.
- `gitignore_required_entries` entries are exact-match strings (no glob semantics implied by the manifest itself; the strings happen to be globs because `.gitignore` interprets them as such).

### State transitions

None. The manifest is immutable at the module level (instantiated once as `CANONICAL_MANIFEST` and frozen). Schema changes bump `schema_version` and ship with a new migration.

### Example (v1.0.0)

```python
from pathlib import Path

CANONICAL_MANIFEST = CharterBundleManifest(
    schema_version="1.0.0",
    tracked_files=[Path(".kittify/charter/charter.md")],
    derived_files=[
        Path(".kittify/charter/governance.yaml"),
        Path(".kittify/charter/directives.yaml"),
        Path(".kittify/charter/metadata.yaml"),
    ],
    derivation_sources={
        Path(".kittify/charter/governance.yaml"): Path(".kittify/charter/charter.md"),
        Path(".kittify/charter/directives.yaml"): Path(".kittify/charter/charter.md"),
        Path(".kittify/charter/metadata.yaml"):   Path(".kittify/charter/charter.md"),
    },
    gitignore_required_entries=[
        ".kittify/charter/directives.yaml",
        ".kittify/charter/governance.yaml",
        ".kittify/charter/metadata.yaml",
    ],
)
```

### Explicitly out of v1.0.0 scope

- `.kittify/charter/references.yaml` — produced by `src/charter/compiler.py :: write_compiled_charter` (lines 169-196), a different pipeline invoked by `spec-kitty charter generate`.
- `.kittify/charter/context-state.json` — written lazily by `src/charter/context.py :: build_charter_context` (lines 385-398) as runtime first-load state.
- `.kittify/charter/interview/answers.yaml` — interview answer cache.
- `.kittify/charter/library/*.md` — user-authored local support docs when the charter was generated interactively.

The project `.gitignore` continues to ignore these files as it does today; the manifest simply does not take ownership of them.

---

## Entity: `SyncResult` (extended)

**Module**: `src/charter/sync.py` (existing — extended in WP2.2).
**Pattern**: `@dataclass` (current shape; preserved).
**Extension**: one new field `canonical_root: Path`.
**External contract**: [`contracts/chokepoint.contract.md`](contracts/chokepoint.contract.md).

### Purpose

Return value from `ensure_charter_bundle_fresh()` and `sync()`. Tells the caller what happened on this invocation of the chokepoint.

### Fields (post-WP2.2)

| Field | Type | Existing / new | Description |
| --- | --- | --- | --- |
| `synced` | `bool` | Existing | Whether a sync was triggered on this call. |
| `stale_before` | `bool` | Existing | Whether the bundle was stale (hash mismatch or missing derivatives) before this call. |
| `files_written` | `list[Path]` | Existing | Paths of files written during the sync, **relative to `canonical_root`**. For v1.0.0 manifest: a subset of `[governance.yaml, directives.yaml, metadata.yaml]`. |
| `extraction_mode` | `str` | Existing | Extraction mode used by the extractor. |
| `error` | `str \| None` | Existing | Error message if sync failed; `None` on success. |
| `canonical_root` | `Path` | **New (WP2.2)** | Absolute path to the canonical (main-checkout) project root. Anchor for every path in `files_written`. Callers reconstruct absolute paths as `canonical_root / p`. |

### Validation rules

- `canonical_root` is always absolute.
- Every entry in `files_written` is relative (not absolute).
- If `error is not None`, `files_written` may be empty and `synced` may be `True` (partial writes recoverable on next call).

### State transitions

Not stateful. Snapshot returned on each call.

### Caller update rule (per D-3 / R-3)

Every existing reader of `SyncResult` is edited in WP2.2 to:

1. Read `canonical_root` alongside `files_written`.
2. When formatting absolute paths for display or subsequent reads, anchor against `canonical_root`.

No shim is shipped; callers are directly updated per C-001.

---

## Entity: `MigrationReport` (structured JSON output)

**Module**: emitted by `m_3_2_3_unified_bundle.py` (new — introduced in WP2.4). Represented as a `TypedDict` for internal typing; serialized as JSON for the external contract.
**External contract**: [`contracts/migration-report.schema.json`](contracts/migration-report.schema.json) (JSON Schema draft-7).

### Purpose

Structured output of `m_3_2_3_unified_bundle.py` so operators can audit exactly what the migration did. Consumed by:

- `spec-kitty upgrade` when run with `--json` (the standard `spec-kitty` CLI convention).
- `tests/upgrade/test_unified_bundle_migration.py` for fixture-matrix assertions (FR-013).

### Fields

| Field | Type | Description |
| --- | --- | --- |
| `migration_id` | `str` | Literal `"m_3_2_3_unified_bundle"`. |
| `target_version` | `str` | Literal `"3.2.3"`. |
| `applied` | `bool` | Whether the migration changed anything on disk. `False` means the bundle was already complete and fresh (expected outcome for most upgrades, because the chokepoint's on-read auto-refresh usually keeps the bundle current). |
| `charter_present` | `bool` | Whether `.kittify/charter/charter.md` exists at migration time. When `false`, the migration is a no-op and every subsequent field is empty/default. |
| `bundle_validation` | `dict[str, Any]` | Result of validating the main-checkout bundle against `CharterBundleManifest` v1.0.0. Keys: `passed: bool`, `missing_tracked: list[Path]`, `missing_derived: list[Path]`, `unexpected: list[Path]`. `unexpected` lists files under `.kittify/charter/` that are not v1.0.0 manifest files (e.g., `references.yaml`, `context-state.json`) — informational, not a failure. |
| `chokepoint_refreshed` | `bool` | Whether invoking `ensure_charter_bundle_fresh()` during the migration actually triggered a sync. `False` if the bundle was already complete and fresh. |
| `errors` | `list[str]` | Any non-fatal errors encountered. Fatal errors raise and do not produce a report. |
| `duration_ms` | `int` | Wall time of the migration in milliseconds. Must be ≤2000 on the FR-013 reference fixture (NFR-006). |

### Validation rules

- `migration_id` and `target_version` are literal strings; validated by the registry.
- On idempotent re-apply: `applied` is `False`, `bundle_validation.passed` is `True`, `chokepoint_refreshed` is `False`, `errors` is `[]`.
- When `charter_present == false`: `applied == false`; `bundle_validation.passed == true` (trivially); `chokepoint_refreshed == false`.

### Explicitly not in v1.0.0 migration scope

The migration does NOT scan worktrees, does NOT remove any symlinks, does NOT touch `.kittify/memory/` or `.kittify/AGENTS.md` (those are documented-intentional sharing per `src/specify_cli/templates/AGENTS.md:168-179` and are not part of the charter bundle), and does NOT reconcile `.gitignore` (v1.0.0 manifest's required entries match the current project `.gitignore` verbatim). Operator-visible upgrade work on v1.0.0 is minimal by design — the real behavior change is at the reader/chokepoint layer and is inherent to the code upgrade, not to the filesystem migration.

### State transitions

Not stateful. One report per migration invocation.

---

## Exception types

### `NotInsideRepositoryError`

**Module**: `src/charter/resolution.py` (new — introduced in WP2.2).
**Parent**: `RuntimeError`.
**Raised by**: `resolve_canonical_repo_root(path)` when `path` is not inside any git repository (i.e., `git rev-parse --git-common-dir` exits non-zero with a "not a git repository" signal, **or** when the resolved input path is inside a `.git/` directory per R-2 edge case).

**Fields**:

- `path: Path` — the invocation path that triggered the error.

**Message shape**: `"Path {path!r} is not inside a git repository. Charter resolution requires a git-tracked project root."`

### `GitCommonDirUnavailableError`

**Module**: `src/charter/resolution.py` (new — introduced in WP2.2).
**Parent**: `RuntimeError`.
**Raised by**: `resolve_canonical_repo_root(path)` when the `git` binary is not on PATH, or when `git rev-parse --git-common-dir` fails for a reason other than "not a git repo" (permission errors, corrupt `.git`, etc.).

**Fields**:

- `path: Path` — the invocation path.
- `detail: str` — the underlying error message from `subprocess` or `git`.

**Message shape**: `"git rev-parse --git-common-dir failed for {path!r}: {detail}. Install a supported git binary and retry."`

Per C-001, neither exception has a fallback handler in the chokepoint; both propagate to the caller and surface as loud failures.

---

## Relationships

```
                                ┌─────────────────────────┐
                                │  CharterBundleManifest  │
                                │  (v1.0.0 — 3 derived)   │
                                │  src/charter/bundle.py  │
                                └─────────────┬───────────┘
                                              │ consulted by
                   ┌──────────────────────────┼───────────────────────────────┐
                   │                          │                               │
                   ▼                          ▼                               ▼
   ensure_charter_bundle_fresh()    m_3_2_3_unified_bundle.py   spec-kitty charter bundle validate
   (src/charter/sync.py)            (upgrade migration)         (src/specify_cli/cli/commands/charter.py)
                   │
                   │ calls first, caches path
                   ▼
      resolve_canonical_repo_root()
      (src/charter/resolution.py)
                   │
                   │ produces absolute root path
                   ▼
      SyncResult (extended with canonical_root)
                   │
                   │ returned to every reader in FR-004
                   ▼
    every sync-output reader
    (build_charter_context, dashboard,
     CLI handlers, prompt builders, ...)
```

- Manifest is the **static contract** for which files `sync()` owns.
- Resolver is the **dynamic contract** for "where is the bundle anchored".
- Chokepoint is the **execution contract** that composes manifest + resolver and produces a freshness-guaranteed view of the `sync()`-produced files.
- `SyncResult` is the **data contract** returned to every caller.
- `MigrationReport` is the **upgrade contract** for operator-visible audit trail.

---

## What is explicitly NOT a data-model change

- `Charter`, `Governance`, `Directive`, `Reference` (the data types loaded from YAML derivatives): **unchanged**. Phase 2 is about where and how those YAMLs are read, not what they contain.
- DRG types (`DRGGraph`, `Node`, `Relation`, etc. in `src/doctrine/drg/`): **unchanged**. Phase 0 baseline per C-005.
- Dashboard typed contracts (`WPState`, `Lane` in `#361`): **unchanged shape** — only routed differently. C-010 preserves byte-identity.
- Mission / WP identity model (`mission_id`, `mid8`, `mission_slug`): **unchanged**. Orthogonal to Phase 2.
- **Worktree `.kittify/memory/` and `.kittify/AGENTS.md` symlinks (`src/specify_cli/core/worktree.py:478-532`)**: **unchanged**. Documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179`. Not part of the charter bundle.
- Compiler pipeline output (`references.yaml` via `compiler.py:169-196`): **unchanged**. Out of v1.0.0 manifest scope.
- Context-state file (`context-state.json` via `context.py:385-398`): **unchanged**. Out of v1.0.0 manifest scope.
