---
work_package_id: WP01
title: MissionContext Core
lane: "doing"
dependencies: []
requirement_refs:
- FR-001
- FR-021
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: main
base_commit: c7b8bc8f48992e6d8af3871b07a367a9b6bccb92
created_at: '2026-03-27T17:59:15.490084+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase A - Foundation
assignee: ''
agent: ''
shell_pid: "2308"
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-27T17:23:39Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – MissionContext Core

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual worktree base may differ later**: `/spec-kitty.implement` populates frontmatter `base_branch` when the worktree is created.
- **If human instructions contradict these fields**: stop and resolve the intended landing branch before coding.

---

## Objectives & Success Criteria

- Build the foundational `context/` module with all dataclasses, persistence, resolution, and CLI middleware.
- After this WP, `MissionContext` objects can be created, persisted as opaque tokens, and loaded by the CLI middleware.
- Every field specified in the data model is present: `project_uuid`, `mission_id`, `work_package_id`, `wp_code`, `feature_slug`, `target_branch`, `authoritative_repo`, `authoritative_ref`, `owned_files`, `execution_mode`, `dependency_mode`, `completion_commands`.
- Context resolution completes in under 500ms (NFR-003).

## Context & Constraints

- **Spec**: `kitty-specs/057-canonical-context-architecture-cleanup/spec.md` — FR-001 (MissionContext object), FR-021 (immutable identity fields)
- **Data model**: `kitty-specs/057-canonical-context-architecture-cleanup/data-model.md` — MissionContext entity, ProjectIdentity, MissionIdentity, WorkPackage
- **Plan**: `kitty-specs/057-canonical-context-architecture-cleanup/plan.md` — Move 1 design
- **Constitution**: `.kittify/constitution/constitution.md` — Python 3.11+, mypy --strict, 90%+ coverage
- **Key constraint**: Token format is opaque ULID-based (`ctx-` prefix + ULID). Do NOT use semantic tokens.
- **Key constraint**: Resolver reads identity from `meta.json` (mission_id) and WP frontmatter (work_package_id). It does NOT use branch names, env vars, or directory walking.

## Subtasks & Detailed Guidance

### Subtask T001 – Create `context/__init__.py`

- **Purpose**: Package initialization with public API exports.
- **Steps**:
  1. Create `src/specify_cli/context/__init__.py`
  2. Export: `MissionContext`, `ContextToken`, `resolve_context`, `load_context`, `save_context`, `ContextMiddleware`
  3. Add `__all__` list
- **Files**: `src/specify_cli/context/__init__.py` (new, ~15 lines)

### Subtask T002 – Create `context/models.py`

- **Purpose**: Define the core dataclasses for bound identity and tokens.
- **Steps**:
  1. Create `src/specify_cli/context/models.py`
  2. Define `MissionContext` as a frozen dataclass with ALL fields from the data model:
     ```python
     @dataclass(frozen=True)
     class MissionContext:
         token: str                    # Opaque ULID: "ctx-01HV..."
         project_uuid: str             # From .kittify/metadata.yaml
         mission_id: str               # From meta.json
         work_package_id: str          # From WP frontmatter (immutable internal ID)
         wp_code: str                  # Display alias: "WP03"
         feature_slug: str             # Display alias: "057-canonical-context..."
         target_branch: str            # From meta.json
         authoritative_repo: str       # Absolute path to repo root
         authoritative_ref: str | None # Git ref (branch name) for code_change WPs; None for planning_artifact WPs that work in-repo
         owned_files: tuple[str, ...]  # Glob patterns from WP frontmatter
         execution_mode: str           # "code_change" or "planning_artifact"
         dependency_mode: str          # "independent" or "chained"
         created_at: str               # ISO 8601 UTC
         created_by: str               # Agent name
     ```
  3. Define `ContextToken` as a simple wrapper:
     ```python
     @dataclass(frozen=True)
     class ContextToken:
         token: str
         context_path: Path  # Absolute path to persisted JSON
     ```
  4. Add `to_dict()` and `from_dict()` methods on MissionContext for JSON serialization
  5. Use `tuple` (not `list`) for immutable fields
- **Files**: `src/specify_cli/context/models.py` (new, ~80 lines)
- **Notes**: Use `from __future__ import annotations` for forward refs. All fields are required — no optional fields.

### Subtask T003 – Create `context/store.py`

- **Purpose**: Persistence layer for context token JSON files.
- **Steps**:
  1. Create `src/specify_cli/context/store.py`
  2. Implement `save_context(context: MissionContext, repo_root: Path) -> ContextToken`:
     - Create `.kittify/runtime/contexts/` directory if not exists
     - Serialize `context.to_dict()` to JSON
     - Write to `.kittify/runtime/contexts/{context.token}.json`
     - Use atomic write (write to temp file, then `os.replace`)
     - Return `ContextToken` with token and path
  3. Implement `load_context(token: str, repo_root: Path) -> MissionContext`:
     - Read `.kittify/runtime/contexts/{token}.json`
     - Deserialize via `MissionContext.from_dict()`
     - Raise `ContextNotFoundError` if file doesn't exist
     - Raise `ContextCorruptedError` if JSON is invalid
  4. Implement `list_contexts(repo_root: Path) -> list[ContextToken]`:
     - List all `.json` files in `.kittify/runtime/contexts/`
     - Return as ContextToken list
  5. Implement `delete_context(token: str, repo_root: Path) -> None`:
     - Remove the context file
     - No error if already deleted
- **Files**: `src/specify_cli/context/store.py` (new, ~70 lines)
- **Notes**: All paths use `pathlib.Path`. JSON encoding uses `json.dumps(indent=2, sort_keys=True)`.

### Subtask T004 – Create `context/resolver.py`

- **Purpose**: Resolve context from raw arguments (wp_code, feature_slug, agent name) into a persisted MissionContext.
- **Steps**:
  1. Create `src/specify_cli/context/resolver.py`
  2. Implement `resolve_context(wp_code: str, feature_slug: str, agent: str, repo_root: Path) -> MissionContext`:
     - Both `wp_code` and `feature_slug` are REQUIRED. If either is missing, raise `ContextResolutionError` with an actionable message telling the caller to provide both. NO scanning, NO heuristic fallback, NO single-feature auto-detection. This is the core architectural constraint — the resolver must never re-discover identity.
     - Read `project_uuid` from `.kittify/metadata.yaml`
     - Read `mission_id` and `target_branch` from `kitty-specs/<feature_slug>/meta.json`
     - Find WP by `wp_code` in `kitty-specs/<feature_slug>/tasks/`
     - Read `work_package_id`, `execution_mode`, `owned_files`, `authoritative_surface`, `dependencies` from WP frontmatter
     - Compute `authoritative_ref` from feature slug + wp_code branch naming convention
     - Compute `dependency_mode` from dependencies list
     - Generate opaque token: `f"ctx-{ulid.new()}"`
     - Build `MissionContext` frozen dataclass
     - Persist via `store.save_context()`
     - Return the context
  3. Define error types:
     - `ContextResolutionError` — base class
     - `FeatureNotFoundError` — feature slug doesn't match any kitty-specs/ dir
     - `WorkPackageNotFoundError` — wp_code not found in tasks/
     - `MissingArgumentError` — wp_code or feature_slug not provided (fail-fast, no fallback)
     - `MissingIdentityError` — project_uuid or mission_id not assigned
  4. Implement `resolve_or_load(token: str | None, wp_code: str | None, feature_slug: str | None, agent: str, repo_root: Path) -> MissionContext`:
     - If `token` is provided: `load_context(token)` directly
     - If `token` is None but both `wp_code` and `feature_slug` are provided: `resolve_context(wp_code, feature_slug, agent, repo_root)`
     - If `token` is None and either `wp_code` or `feature_slug` is missing: raise `MissingArgumentError` — never scan or guess
     - This is the main entry point used by shim entrypoints
- **Files**: `src/specify_cli/context/resolver.py` (new, ~120 lines)
- **Notes**: Resolver reads frontmatter via `ruamel.yaml`. It does NOT use `detect_feature()`, branch parsing, env vars, or cwd walking. Those old paths are deleted in WP02.

### Subtask T005 – Create `context/middleware.py`

- **Purpose**: CLI middleware that loads context from `--context <token>` or fails fast.
- **Steps**:
  1. Create `src/specify_cli/context/middleware.py`
  2. Implement `context_callback(ctx: typer.Context, context: str | None)`:
     - If `context` is provided: `load_context(context, repo_root)` and store on `ctx.obj`
     - If `context` is None and command requires it: raise `typer.BadParameter` with actionable message:
       ```
       No context token provided. Run `spec-kitty agent context resolve --wp <WP> --feature <feature>` first,
       then pass the token: --context <token>
       ```
     - Some commands (e.g., `status`, `materialize`) may not require a WP context — use optional mode
  3. Implement `get_context(ctx: typer.Context) -> MissionContext`:
     - Extract context from `ctx.obj`
     - Raise if missing (should not happen if middleware ran)
  4. Implement `require_context` decorator for commands that need bound context:
     ```python
     def require_context(func):
         """Decorator that ensures MissionContext is available."""
         ...
     ```
- **Files**: `src/specify_cli/context/middleware.py` (new, ~60 lines)
- **Notes**: The middleware runs as a typer callback. Commands opt-in to requiring context via the decorator.

### Subtask T006 – Tests for context module

- **Purpose**: Achieve 90%+ coverage on all context module components.
- **Steps**:
  1. Create test directory: `tests/specify_cli/context/`
  2. `test_models.py`: Test MissionContext creation, immutability (frozen), to_dict/from_dict round-trip, all fields present
  3. `test_store.py`: Test save/load/list/delete cycle, atomic write, ContextNotFoundError, ContextCorruptedError
  4. `test_resolver.py`: Test resolve from wp_code + feature_slug, single-feature fallback, all error types (FeatureNotFoundError, WorkPackageNotFoundError, AmbiguousFeatureError, MissingIdentityError)
  5. `test_middleware.py`: Test context_callback with valid token, missing token (fail-fast), get_context extraction, require_context decorator
  6. All tests use real filesystem (tmp_path fixture), not mocks — per constitution
- **Files**:
  - `tests/specify_cli/context/__init__.py` (new)
  - `tests/specify_cli/context/test_models.py` (new, ~60 lines)
  - `tests/specify_cli/context/test_store.py` (new, ~80 lines)
  - `tests/specify_cli/context/test_resolver.py` (new, ~120 lines)
  - `tests/specify_cli/context/test_middleware.py` (new, ~60 lines)
- **Parallel?**: Yes — can be developed alongside T002-T005 using TDD

## Risks & Mitigations

- **ULID dependency**: If `ulid` library is not in dependencies, use `ulid-py` or generate manually from timestamp + random bytes.
- **Frontmatter format variation**: WP frontmatter may vary between legacy and new format. Resolver should handle both during transition.
- **Performance**: Context resolution reads meta.json + one WP file. Should easily meet 500ms target unless filesystem is very slow.

## Review Guidance

- Verify MissionContext is truly frozen (no mutable fields)
- Verify token is opaque (no parseable semantics in the string)
- Verify resolver does NOT use branch names, env vars, or cwd walking
- Verify store uses atomic writes (temp file + os.replace)
- Verify middleware fail-fast message is actionable
- Run `mypy --strict` on entire context/ module

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
