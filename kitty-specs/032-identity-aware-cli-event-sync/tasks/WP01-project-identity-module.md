---
work_package_id: WP01
title: ProjectIdentity Module
lane: "done"
dependencies: []
base_branch: 2.x
base_commit: fe5dd26eb9160377ee55f83b072f5dc3db322843
created_at: '2026-02-07T07:23:14.221357+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 0 - Foundation
assignee: ''
agent: "codex"
shell_pid: "25757"
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-02-07T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – ProjectIdentity Module

## Implementation Command

```bash
spec-kitty implement WP01
```

No `--base` flag needed (this is the foundation WP).

---

## Objectives & Success Criteria

**Goal**: Create the `ProjectIdentity` dataclass with generation, atomic persistence, and graceful backfill.

**Success Criteria**:
- [ ] `spec-kitty init` creates config.yaml with valid `project_uuid`, `project_slug`, and `node_id`
- [ ] Existing projects without identity fields get them auto-generated on first access
- [ ] Read-only repos get in-memory identity with clear warning
- [ ] All unit tests pass with 90%+ coverage

---

## Context & Constraints

**Target Branch**: 2.x (all implementation on 2.x, not main)

**Supporting Documents**:
- [plan.md](../plan.md) - Architecture decisions AD-2 (Graceful Backfill)
- [data-model.md](../data-model.md) - ProjectIdentity entity definition
- [spec.md](../spec.md) - User Story 1 acceptance scenarios

**Key Constraints**:
- Python 3.11+ required (use type hints, `|` union syntax)
- mypy --strict must pass
- Atomic writes required (never corrupt config.yaml)
- Must handle read-only filesystems gracefully

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create ProjectIdentity dataclass

**Purpose**: Define the core data structure for project identity.

**Steps**:
1. Create new file `src/specify_cli/sync/project_identity.py`
2. Define `ProjectIdentity` as a dataclass with fields:
   ```python
   from dataclasses import dataclass
   from uuid import UUID
   
   @dataclass
   class ProjectIdentity:
       project_uuid: UUID | None = None
       project_slug: str | None = None
       node_id: str | None = None
       
       @property
       def is_complete(self) -> bool:
           return all([self.project_uuid, self.project_slug, self.node_id])
   ```
3. Add `with_defaults()` method that returns new instance with missing fields filled
4. Add `to_dict()` and `from_dict()` for serialization

**Files**:
- `src/specify_cli/sync/project_identity.py` (NEW, ~80 lines)

**Parallel?**: No (foundation for other subtasks)

---

### Subtask T002 – Implement identity generation helpers

**Purpose**: Provide functions to generate each identity field with appropriate logic.

**Steps**:
1. Add `generate_project_uuid()` function:
   ```python
   from uuid import uuid4
   
   def generate_project_uuid() -> UUID:
       return uuid4()
   ```

2. Add `derive_project_slug()` function:
   ```python
   import subprocess
   from pathlib import Path
   
   def derive_project_slug(repo_root: Path) -> str:
       # Try git remote origin first
       try:
           result = subprocess.run(
               ["git", "remote", "get-url", "origin"],
               cwd=repo_root,
               capture_output=True,
               text=True,
               check=True
           )
           # Parse repo name from URL (e.g., git@github.com:user/repo.git -> repo)
           url = result.stdout.strip()
           # Handle both SSH and HTTPS URLs
           if url.endswith(".git"):
               url = url[:-4]
           return url.split("/")[-1].lower().replace("_", "-")
       except subprocess.CalledProcessError:
           pass
       
       # Fallback to directory name
       return repo_root.name.lower().replace("_", "-")
   ```

3. Add `generate_node_id()` function:
   ```python
   from specify_cli.sync.clock import generate_node_id as generate_machine_node_id
   
   def generate_node_id() -> str:
       # Reuse LamportClock's stable machine ID for consistency
       return generate_machine_node_id()
   ```

**Files**:
- `src/specify_cli/sync/project_identity.py` (append, ~50 lines)

**Notes**:
- Slug derivation must handle SSH URLs (`git@github.com:user/repo.git`)
- Slug derivation must handle HTTPS URLs (`https://github.com/user/repo.git`)
- Node ID should be stable per machine (use existing LamportClock generator)

---

### Subtask T003 – Implement atomic config.yaml persistence

**Purpose**: Write identity to config.yaml atomically to prevent corruption.

**Steps**:
1. Add `atomic_write_config()` function:
   ```python
   import os
   import tempfile
   from pathlib import Path
   from ruamel.yaml import YAML
   
   def atomic_write_config(config_path: Path, identity: ProjectIdentity) -> None:
       """Atomically write identity to config.yaml (temp file + rename)."""
       yaml = YAML()
       yaml.preserve_quotes = True
       
       # Load existing config or create new
       if config_path.exists():
           with open(config_path) as f:
               config = yaml.load(f) or {}
       else:
           config = {}
       
       # Update project section
       config["project"] = identity.to_dict()
       
       # Write to temp file in same directory (ensures same filesystem)
       fd, tmp_path = tempfile.mkstemp(
           dir=config_path.parent,
           prefix=".config.yaml.",
           suffix=".tmp"
       )
       try:
           with os.fdopen(fd, "w") as f:
               yaml.dump(config, f)
           os.replace(tmp_path, config_path)  # Atomic on POSIX
       except Exception:
           if os.path.exists(tmp_path):
               os.unlink(tmp_path)
           raise
   ```

2. Ensure parent directory exists before writing

**Files**:
- `src/specify_cli/sync/project_identity.py` (append, ~40 lines)

**Notes**:
- Use `os.replace()` for atomic rename (POSIX-compliant)
- Temp file must be in same directory as target (ensures same filesystem)
- Clean up temp file on failure

---

### Subtask T004 – Implement graceful backfill via ensure_identity()

**Purpose**: Load identity from config, generating missing fields if needed.

**Steps**:
1. Add `load_identity()` function:
   ```python
   def load_identity(config_path: Path) -> ProjectIdentity:
       """Load identity from config.yaml, returning empty if not found."""
       if not config_path.exists():
           return ProjectIdentity()
       
       yaml = YAML()
       try:
           with open(config_path) as f:
               config = yaml.load(f) or {}
       except Exception as e:
           logger.warning(f"Invalid config.yaml; regenerating identity: {e}")
           config = {}
       
       project = config.get("project", {})
       return ProjectIdentity(
           project_uuid=UUID(project["uuid"]) if project.get("uuid") else None,
           project_slug=project.get("slug"),
           node_id=project.get("node_id"),
       )
   ```

2. Add `ensure_identity()` function:
   ```python
   def ensure_identity(repo_root: Path) -> ProjectIdentity:
       """Load or generate project identity. Atomic write if generating."""
       config_path = repo_root / ".kittify" / "config.yaml"
       
       identity = load_identity(config_path)
       if identity.is_complete:
           return identity
       
       # Generate missing fields
       identity = identity.with_defaults(repo_root)
       
       # Persist if writable
       if is_writable(config_path):
           atomic_write_config(config_path, identity)
       else:
           logger.warning("Config not writable; using in-memory identity")
       
       return identity
   ```

3. Update `ProjectIdentity.with_defaults()` to accept `repo_root` for slug derivation

**Files**:
- `src/specify_cli/sync/project_identity.py` (append, ~50 lines)

---

### Subtask T005 – Add read-only fallback

**Purpose**: Handle read-only repos gracefully with in-memory identity.

**Steps**:
1. Add `is_writable()` helper:
   ```python
   def is_writable(path: Path) -> bool:
       """Check if path (or its parent directory) is writable."""
       if path.exists():
           return os.access(path, os.W_OK)
       return os.access(path.parent, os.W_OK)
   ```

2. Update `ensure_identity()` to use `is_writable()` check
3. Log clear warning when falling back to in-memory:
   ```python
   from rich.console import Console
   console = Console(stderr=True)
   console.print("[yellow]Warning: Config not writable; using in-memory identity[/yellow]")
   ```

**Files**:
- `src/specify_cli/sync/project_identity.py` (append, ~20 lines)

**Notes**:
- Check parent directory writability if file doesn't exist yet
- Use rich console for consistent warning styling
- In-memory identity still works for event emission

---

### Subtask T006 – Write unit tests

**Purpose**: Comprehensive test coverage for project_identity module.

**Steps**:
1. Create `tests/sync/test_project_identity.py`
2. Add tests for:
   - `ProjectIdentity` dataclass creation and properties
   - `generate_project_uuid()` returns valid UUID4
   - `derive_project_slug()` from git remote
   - `derive_project_slug()` fallback to directory name
   - `generate_node_id()` format (stable 12-char hex)
   - malformed config.yaml handled gracefully (warn + regenerate identity)
   - `atomic_write_config()` creates valid YAML
   - `atomic_write_config()` cleans up on failure
   - `load_identity()` parses existing config
   - `ensure_identity()` generates missing fields
   - `ensure_identity()` handles read-only (mock os.access)

**Files**:
- `tests/sync/test_project_identity.py` (NEW, ~150 lines)

**Test Commands**:
```bash
pytest tests/sync/test_project_identity.py -v
mypy src/specify_cli/sync/project_identity.py --strict
```

**Parallel?**: Yes (can write tests once API is designed)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Config corruption on write failure | Atomic write pattern (temp + rename) |
| Race condition with concurrent processes | First-write-wins; subsequent reads use persisted value |
| Read-only filesystem | Fallback to in-memory identity with warning |
| Git remote parsing edge cases | Test both SSH and HTTPS URL formats |

---

## Review Guidance

**Reviewers should verify**:
1. Atomic write pattern is correct (temp file in same directory, os.replace)
2. All edge cases handled (no remote, read-only, missing .kittify dir)
3. Type annotations are complete (mypy --strict passes)
4. Tests cover all public functions

---

## Activity Log

- 2026-02-07T00:00:00Z – system – lane=planned – Prompt created.
- 2026-02-07T07:23:14Z – claude-opus – shell_pid=33592 – lane=doing – Assigned agent via workflow command
- 2026-02-07T07:27:21Z – claude-opus – shell_pid=33592 – lane=for_review – Ready for review: ProjectIdentity module complete with 36 passing tests
- 2026-02-07T07:27:56Z – codex – shell_pid=25757 – lane=doing – Started review via workflow command
- 2026-02-07T07:29:10Z – codex – shell_pid=25757 – lane=done – Review passed: ProjectIdentity module, atomic config writes, backfill + read-only handling, tests passing
