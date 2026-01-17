---
work_package_id: "WP02"
title: "VCS Detection and Factory"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
phase: "Phase 1 - Abstraction Layer"
lane: "planned"
priority: "P0"
dependencies: ["WP01"]
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-17T10:38:23Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – VCS Detection and Factory

## Objectives & Success Criteria

**Goal**: Implement tool detection and the get_vcs() factory function.

**Success Criteria**:
- `is_jj_available()` returns True when jj is installed, False otherwise
- `is_git_available()` returns True when git is installed, False otherwise
- `get_vcs()` returns GitVCS when git only, JujutsuVCS when jj available (with prefer_jj=True)
- Factory respects locked VCS in meta.json for features
- Detection results are cached within a session

**User Stories Addressed**: US1 (P1), US2 (P1)
**Requirements**: FR-002, FR-003, FR-004

## Context & Constraints

**Reference Documents**:
- `kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py` - Factory function signature
- `kitty-specs/015-first-class-jujutsu-vcs-integration/plan.md` - Detection logic

**Architecture Decisions**:
- Stateless factory function (not a class)
- Cache detection results to avoid repeated subprocess calls
- Factory reads meta.json for locked VCS when in feature context

**Constraints**:
- Use `shutil.which()` for tool detection (cross-platform)
- Version parsing must handle edge cases gracefully
- Must work when only git OR only jj is installed

## Subtasks & Detailed Guidance

### Subtask T006 – Implement detection.py with tool detection functions

**Purpose**: Detect which VCS tools are available on the system.

**Steps**:
1. Create `src/specify_cli/core/vcs/detection.py`
2. Implement detection functions:
   ```python
   def is_jj_available() -> bool:
       """Check if jj is installed and working."""

   def is_git_available() -> bool:
       """Check if git is installed and working."""

   def get_jj_version() -> str | None:
       """Get installed jj version, or None if not installed."""

   def get_git_version() -> str | None:
       """Get installed git version, or None if not installed."""

   def detect_available_backends() -> list[VCSBackend]:
       """Detect which VCS tools are installed, in preference order."""
   ```
3. Implement caching:
   - Use module-level cache dict
   - Cache results after first call
   - Optional `_clear_cache()` for testing

**Files**:
- Create: `src/specify_cli/core/vcs/detection.py`

**Implementation Details**:
```python
import shutil
import subprocess
from functools import lru_cache

@lru_cache(maxsize=1)
def is_jj_available() -> bool:
    if shutil.which("jj") is None:
        return False
    try:
        result = subprocess.run(
            ["jj", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
```

**Notes**:
- jj version format: `jj 0.23.0`
- git version format: `git version 2.43.0`
- Handle both Unix and Windows paths

---

### Subtask T007 – Implement get_vcs() factory function

**Purpose**: Create factory function that returns appropriate VCS implementation.

**Steps**:
1. Add to `src/specify_cli/core/vcs/detection.py`:
   ```python
   def get_vcs(
       path: Path,
       backend: VCSBackend | None = None,
       prefer_jj: bool = True,
   ) -> VCSProtocol:
       """Factory function to get appropriate VCS implementation."""
   ```
2. Implement detection logic:
   - If `backend` specified, use that (validate available)
   - If path is in a feature, read meta.json for locked VCS
   - If jj available and `prefer_jj=True`, use jj
   - If git available, use git
   - Raise `VCSNotFoundError` if neither available
3. Add helper for meta.json reading:
   ```python
   def _get_locked_vcs_from_feature(path: Path) -> VCSBackend | None:
       """Read VCS from feature meta.json if exists."""
   ```

**Files**:
- Modify: `src/specify_cli/core/vcs/detection.py`

**Implementation Details**:
```python
def get_vcs(
    path: Path,
    backend: VCSBackend | None = None,
    prefer_jj: bool = True,
) -> VCSProtocol:
    # 1. If explicit backend, use that
    if backend is not None:
        return _instantiate_backend(backend)

    # 2. Check for locked VCS in feature meta.json
    locked = _get_locked_vcs_from_feature(path)
    if locked is not None:
        return _instantiate_backend(locked)

    # 3. Auto-detect
    if prefer_jj and is_jj_available():
        from .jujutsu import JujutsuVCS
        return JujutsuVCS()
    if is_git_available():
        from .git import GitVCS
        return GitVCS()

    raise VCSNotFoundError("Neither jj nor git is available")
```

**Notes**:
- Import implementations lazily to avoid circular imports
- Validate backend is actually available before returning
- Handle case where locked VCS is not available (error with helpful message)

---

### Subtask T008 – Add detection exports to __init__.py

**Purpose**: Export detection functions in public API.

**Steps**:
1. Update `src/specify_cli/core/vcs/__init__.py`
2. Add exports:
   - `is_jj_available`
   - `is_git_available`
   - `get_jj_version`
   - `get_git_version`
   - `detect_available_backends`
   - `get_vcs`
3. Update `__all__` list

**Files**:
- Modify: `src/specify_cli/core/vcs/__init__.py`

**Notes**: get_vcs is the primary public API for obtaining a VCS instance.

---

### Subtask T009 – Create test_detection.py [P]

**Purpose**: Test detection functions work correctly.

**Steps**:
1. Create `tests/specify_cli/core/vcs/test_detection.py`
2. Test detection functions:
   - Test `is_git_available()` (git should always be available in dev)
   - Test `is_jj_available()` (mark with `@pytest.mark.jj` if requires jj)
   - Test version parsing for both
3. Test factory function:
   - Test returns GitVCS when only git available
   - Test returns JujutsuVCS when jj available and preferred
   - Test respects explicit backend parameter
   - Test raises VCSNotFoundError appropriately

**Files**:
- Create: `tests/specify_cli/core/vcs/test_detection.py`
- Create: `tests/specify_cli/core/vcs/__init__.py` (empty)

**Test Examples**:
```python
def test_is_git_available():
    # Git should be available in any dev environment
    assert is_git_available() is True

def test_get_git_version():
    version = get_git_version()
    assert version is not None
    assert "." in version  # e.g., "2.43.0"

@pytest.mark.jj
def test_is_jj_available_when_installed():
    assert is_jj_available() is True

def test_get_vcs_prefers_jj_when_available():
    vcs = get_vcs(Path("."), prefer_jj=True)
    # If jj installed, should be JujutsuVCS
    # If not, should be GitVCS
    assert isinstance(vcs, VCSProtocol)

def test_get_vcs_with_explicit_git():
    vcs = get_vcs(Path("."), backend=VCSBackend.GIT)
    assert vcs.backend == VCSBackend.GIT
```

**Parallel?**: Yes - can start once T006-T007 scaffolded

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| jj not installed on CI | Use @pytest.mark.jj to skip jj tests |
| Version output format changes | Graceful parsing, fallback to "unknown" |
| Circular imports with implementations | Lazy import inside get_vcs |

## Definition of Done Checklist

- [ ] T006: detection.py with is_jj_available, is_git_available, version functions
- [ ] T007: get_vcs() factory function with meta.json lookup
- [ ] T008: Detection functions exported from __init__.py
- [ ] T009: Tests for detection and factory
- [ ] `is_git_available()` returns True in dev environment
- [ ] `get_vcs()` returns appropriate backend based on availability
- [ ] Caching works (repeated calls don't spawn new processes)

## Review Guidance

**Key Checkpoints**:
1. Verify detection uses shutil.which (not subprocess for existence check)
2. Verify caching is implemented (lru_cache or module-level)
3. Verify lazy import pattern for implementations
4. Verify meta.json reading handles missing file gracefully
5. Run detection tests in environment with and without jj

## Activity Log

- 2026-01-17T10:38:23Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
