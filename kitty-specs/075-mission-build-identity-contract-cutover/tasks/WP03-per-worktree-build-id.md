---
work_package_id: WP03
title: Per-Worktree Build Identity
dependencies: []
requirement_refs:
- FR-004
- FR-007
- FR-008
- FR-012
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
- T021
- T022
- T023
- T024
agent: opencode:opencode:reviewer:reviewer
shell_pid: '14396'
history:
- date: '2026-04-08'
  actor: planner
  action: created
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
mission_slug: 075-mission-build-identity-contract-cutover
owned_files:
- src/specify_cli/sync/project_identity.py
- tests/specify_cli/sync/test_project_identity.py
tags: []
---

# WP03 — Per-Worktree Build Identity

## Branch Strategy

- **Planning base**: `main`
- **Merge target**: `main`
- **Workspace**: allocated by `spec-kitty implement WP03` (lane-based worktree)
- **Command**: `spec-kitty implement WP03 --mission 075-mission-build-identity-contract-cutover`
- **Note**: Independent of WP01 and WP02 (different file). WP04 depends on this WP completing first.

## Objective

Move `build_id` from `.kittify/config.yaml` (committed, shared across all worktrees) to `{git-dir}/spec-kitty-build-id` (non-committed, per-worktree by construction). After this WP:
- Two git worktrees of the same repository emit different `build_id` values
- The same worktree emits the same `build_id` on every invocation (NFR-004)
- A one-time idempotent migration copies and removes `build_id` from `config.yaml` on first load (FR-016)
- Environments without a `.git` directory fail with `BuildIdentityError` — no silent fallback (fail-closed)

## Context

### Why `.git/spec-kitty-build-id` (not `.kittify/build_id.local`)

`git clean -fdx` removes untracked files including `.kittify/build_id.local`, causing a silent `build_id` regeneration. A new `build_id` produces orphaned `started` events with no matching `complete` in the SaaS event log — a correctness failure without a visible error. The `.git/` directory is never touched by `git clean`.

### How git worktrees work

In the main checkout: `.git/` is a directory → `git rev-parse --git-dir` returns `.git`.
In any worktree: `.git` is a file pointing to the main `.git/worktrees/<name>/` directory → `git rev-parse --git-dir` returns `.git/worktrees/<name>`.

Both are distinct paths, so `{git-dir}/spec-kitty-build-id` is naturally per-worktree.

### Current state

`sync/project_identity.py` currently:
- `load_identity(config_path)` reads `build_id` from `config.yaml["project"]["build_id"]`
- `ensure_identity(repo_root)` calls `load_identity` and falls back to `with_defaults`
- `atomic_write_config(config_path, identity)` writes `build_id` to `config.yaml["project"]["build_id"]`

After this WP, `build_id` no longer flows through config.yaml at all (except as migration source on first read).

## Subtask Guidance

### T016 — Add `_build_id_path() -> Path`

**File**: `src/specify_cli/sync/project_identity.py`

Add a module-level private function that resolves the per-worktree build_id file path:

```python
import subprocess
from specify_cli.core.errors import BuildIdentityError  # adjust import if class doesn't exist yet

def _build_id_path() -> Path:
    """Resolve the per-worktree build_id file path via git rev-parse --git-dir.

    Returns:
        Path to {git-dir}/spec-kitty-build-id

    Raises:
        BuildIdentityError: If git rev-parse fails (no git repository, bare clone, etc.)
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise BuildIdentityError(
            "No git repository found. spec-kitty requires a git checkout. "
            f"git rev-parse --git-dir failed: {exc.stderr.strip()}"
        ) from exc
    return Path(result.stdout.strip()) / "spec-kitty-build-id"
```

**Note on `BuildIdentityError`**: If this exception class doesn't exist, add it in `src/specify_cli/core/errors.py` (or wherever domain errors live). It should be a subclass of `RuntimeError`.

---

### T017 — Add `load_build_id(git_dir: Path) -> str`

**File**: `src/specify_cli/sync/project_identity.py`

```python
def load_build_id(git_dir_path: Path) -> str:
    """Load or generate-and-persist the build_id for this worktree.

    Args:
        git_dir_path: The resolved git-dir path (from _build_id_path()).

    Returns:
        A stable UUID4 string unique to this worktree.
    """
    build_id_file = git_dir_path
    if build_id_file.exists():
        value = build_id_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    # Generate fresh UUID4, persist it
    value = str(uuid4())
    build_id_file.write_text(value + "\n", encoding="utf-8")
    return value
```

Note: `git_dir_path` here is already the full path including the filename (`spec-kitty-build-id`). Or split into `git_dir: Path` and compute `git_dir / "spec-kitty-build-id"` internally — be consistent with T016's naming.

---

### T018 — Add `_migrate_build_id_from_config(config_path, git_dir_path)`

**File**: `src/specify_cli/sync/project_identity.py`

This function runs at startup and handles the one-time migration:

```python
def _migrate_build_id_from_config(config_path: Path, git_dir_path: Path) -> None:
    """One-time idempotent migration: copy build_id from config.yaml to git-dir.

    If build_id exists in config.yaml[project], copies it to git_dir_path
    (preserving the existing value if the git-dir file already exists),
    then removes it from config.yaml.

    Noop if build_id is absent from config.yaml.
    """
    if not config_path.exists():
        return

    yaml = YAML()
    data = yaml.load(config_path)
    if data is None:
        return

    project_section = data.get("project", {})
    build_id_value = project_section.get("build_id")
    if build_id_value is None:
        return  # already migrated or was never set

    # Copy to git-dir path only if it doesn't already have a value
    if not git_dir_path.exists():
        git_dir_path.write_text(str(build_id_value) + "\n", encoding="utf-8")

    # Remove from config.yaml
    project_section.pop("build_id", None)
    if not project_section:
        data.pop("project", None)
    else:
        data["project"] = project_section

    with atomic_write(config_path) as f:  # use the existing atomic write helper
        yaml.dump(data, f)
```

Use `ruamel.yaml` (already a project dependency) for round-trip YAML editing without destroying comments.

---

### T019 — Update `ensure_identity(repo_root)` to use new build.id functions

**File**: `src/specify_cli/sync/project_identity.py`

Locate `ensure_identity(repo_root: Path) -> ProjectIdentity`. Currently it reads `build_id` from config via `load_identity`. Change the flow:

```python
def ensure_identity(repo_root: Path) -> ProjectIdentity:
    config_path = repo_root / ".kittify" / "config.yaml"

    # Resolve per-worktree git-dir path (raises BuildIdentityError if no .git)
    git_dir_path = _build_id_path()  # returns {git-dir}/spec-kitty-build-id

    # One-time migration: copy build_id from config.yaml to git-dir, then remove from config
    _migrate_build_id_from_config(config_path, git_dir_path)

    # Load existing identity from config (build_id excluded — comes from git-dir)
    identity = load_identity(config_path)

    # Load or generate build_id from per-worktree file
    build_id = load_build_id(git_dir_path)

    # Merge and fill defaults
    return identity.with_defaults(repo_root).replace(build_id=build_id)
```

**Note**: `ProjectIdentity` may need a `.replace()` method (similar to `dataclasses.replace`) if it doesn't already have one. Check the existing API; use `dataclasses.replace(identity, build_id=build_id)` if it's a dataclass.

---

### T020 — Update `atomic_write_config` to exclude `build_id`

**File**: `src/specify_cli/sync/project_identity.py`

Locate `atomic_write_config(config_path: Path, identity: ProjectIdentity)`. Find where it writes `build_id` to the config dict:

```python
# Old
d["project"]["build_id"] = identity.build_id

# Remove this line entirely
```

After removal, `build_id` never enters `config.yaml`. The per-worktree file is the only persistent location.

Run `mypy --strict src/specify_cli/sync/project_identity.py` — must pass.

---

### T021 — Write test: two git-dir paths → distinct build_id values

**File**: `tests/specify_cli/sync/test_project_identity.py`

```python
from pathlib import Path
from unittest.mock import patch
from specify_cli.sync.project_identity import load_build_id

def test_different_git_dirs_produce_different_build_ids(tmp_path):
    """Two different git-dir paths produce different build_id values (Scenario 2)."""
    git_dir_a = tmp_path / "worktree-a" / "spec-kitty-build-id"
    git_dir_b = tmp_path / "worktree-b" / "spec-kitty-build-id"
    git_dir_a.parent.mkdir(parents=True)
    git_dir_b.parent.mkdir(parents=True)

    id_a = load_build_id(git_dir_a)
    id_b = load_build_id(git_dir_b)

    assert id_a != id_b, "Different worktrees must produce different build_id values"
    assert id_a  # non-empty
    assert id_b  # non-empty
```

---

### T022 — Write test: 100 invocations → stable build_id

**File**: `tests/specify_cli/sync/test_project_identity.py`

```python
def test_load_build_id_is_stable_across_invocations(tmp_path):
    """100 invocations on the same git-dir path return the same build_id (NFR-004)."""
    git_dir = tmp_path / "spec-kitty-build-id"

    first = load_build_id(git_dir)
    for _ in range(99):
        assert load_build_id(git_dir) == first, "build_id must be stable across invocations"
```

---

### T023 — Write test: migration idempotency

**File**: `tests/specify_cli/sync/test_project_identity.py`

```python
import yaml
from specify_cli.sync.project_identity import _migrate_build_id_from_config

def test_migrate_build_id_from_config_is_idempotent(tmp_path):
    """Migration copies build_id to git-dir, removes from config, and is a noop on second call."""
    config_path = tmp_path / "config.yaml"
    git_dir_path = tmp_path / "spec-kitty-build-id"
    legacy_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    # Set up config.yaml with build_id in project section
    config_path.write_text(f"project:\n  uuid: test-uuid\n  slug: test\n  build_id: {legacy_id}\n")

    # First call: copies and removes
    _migrate_build_id_from_config(config_path, git_dir_path)
    assert git_dir_path.read_text().strip() == legacy_id
    config_data = yaml.safe_load(config_path.read_text())
    assert "build_id" not in config_data.get("project", {})

    # Second call: noop (git-dir already has value, config already cleaned)
    _migrate_build_id_from_config(config_path, git_dir_path)
    assert git_dir_path.read_text().strip() == legacy_id  # unchanged

def test_migrate_build_id_from_config_noop_when_absent(tmp_path):
    """Migration is a noop when build_id is not in config.yaml."""
    config_path = tmp_path / "config.yaml"
    git_dir_path = tmp_path / "spec-kitty-build-id"
    config_path.write_text("project:\n  uuid: test-uuid\n  slug: test\n")

    _migrate_build_id_from_config(config_path, git_dir_path)
    assert not git_dir_path.exists()  # no file created
```

---

### T024 — Write test: BuildIdentityError when git rev-parse fails

**File**: `tests/specify_cli/sync/test_project_identity.py`

```python
import subprocess
from unittest.mock import patch
import pytest
from specify_cli.sync.project_identity import _build_id_path
from specify_cli.core.errors import BuildIdentityError  # adjust import

def test_build_id_path_raises_when_no_git_repo(tmp_path):
    """_build_id_path raises BuildIdentityError when git rev-parse --git-dir fails."""
    def raise_called_process_error(*args, **kwargs):
        raise subprocess.CalledProcessError(128, ["git", "rev-parse", "--git-dir"], stderr="not a git repo")

    with patch("subprocess.run", side_effect=raise_called_process_error):
        with pytest.raises(BuildIdentityError, match="No git repository found"):
            _build_id_path()
```

## Definition of Done

- [ ] `_build_id_path()` returns `{git-dir}/spec-kitty-build-id` (verified via test with monkeypatched subprocess)
- [ ] `load_build_id(path)` returns a stable UUID across 100 invocations on the same path
- [ ] Two different paths produce different `build_id` values
- [ ] `_migrate_build_id_from_config` copies and removes `build_id` from config in one idempotent call
- [ ] `ensure_identity()` no longer reads `build_id` from `config.yaml`
- [ ] `atomic_write_config()` no longer writes `build_id` to `config.yaml`
- [ ] `BuildIdentityError` raised when `git rev-parse --git-dir` exits non-zero
- [ ] `mypy --strict src/specify_cli/sync/project_identity.py` passes
- [ ] All tests green

## Risks

| Risk | Mitigation |
|------|-----------|
| `atomic_write_config` has multiple call sites that expect `build_id` in config | Audit all callers: `grep -r "atomic_write_config" src/` — none should pass `build_id` after this change |
| The `.kittify/config.yaml` in this repo currently has `project.build_id` | Migration runs on first `ensure_identity()` call — run the CLI once after merging to verify config is cleaned |
| `ensure_identity()` is called in tests with synthetic config fixtures that include `build_id` | Update test fixtures to remove `build_id` from config; tests should provide the git-dir file directly |

## Reviewer Guidance

- Confirm `config.yaml` no longer contains `project.build_id` after running `ensure_identity()` once
- Verify `{git-dir}/spec-kitty-build-id` is created and contains a UUID4 string
- Run `git worktree add /tmp/test-wt HEAD && cd /tmp/test-wt && spec-kitty agent tasks status` — confirm a different `build_id` than the main checkout's events
- Confirm `BuildIdentityError` is raised in a bare-repo or no-repo test environment

## Activity Log

- 2026-04-08T05:52:29Z – unknown – shell_pid=10307 – Per-worktree build_id via git rev-parse; migration idempotent; fail-closed on no git; 10 tests green; build_id excluded from to_dict/config.yaml
- 2026-04-08T05:53:01Z – opencode:opencode:reviewer:reviewer – shell_pid=13816 – Started review via action command
- 2026-04-08T05:54:11Z – opencode:opencode:reviewer:reviewer – shell_pid=13816 – Moved to planned
