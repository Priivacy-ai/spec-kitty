---
work_package_id: WP02
title: Project Context & State Management
lane: "done"
dependencies: [WP01]
base_branch: 099-mcp-server-for-conversational-spec-kitty-workflow-WP01
base_commit: 6d338e9910233b389f632378137e89e5ddaeee5d
created_at: '2026-01-31T12:20:27.469457+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 1 - Foundation
assignee: 'cursor'
agent: "cursor"
shell_pid: "60166"
review_status: "approved"
reviewed_by: "Rodrigo Leven"
history:
- timestamp: '2026-01-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Project Context & State Management

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged`.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[Empty initially. Reviewers populate this section if changes are requested.]*

---

## Objectives & Success Criteria

**Goal**: Implement ProjectContext entity for managing individual Spec Kitty projects and ConversationState for persisting multi-turn discovery interviews.

**Success Criteria**:
- ProjectContext dataclass created with path validation and .kittify/ directory checking
- ConversationState dataclass created with complete workflow state tracking
- JSON serialization/deserialization working for ConversationState
- Atomic file writes implemented (write to .tmp, then rename)
- Session directory `.kittify/mcp-sessions/` created automatically if missing
- State resumption works (load from session_id)
- All state operations tested with edge cases (missing files, corrupt JSON, invalid paths)

---

## Context & Constraints

**Prerequisites**:
- Review `data-model.md` sections: ProjectContext entity, ConversationState entity
- Review `plan.md` section: State Management (JSON storage, indefinite retention)
- WP01 completed (MCP server infrastructure exists)

**Architectural Constraints**:
- FR-003: All state stored in project-local `.kittify/` directories
- FR-011: Conversation state persisted indefinitely (not limited to 24 hours)
- Storage: Filesystem only (no database)
- Format: JSON for human-readability and portability

**Key Decisions**:
- Session files: `.kittify/mcp-sessions/{session_id}.json`
- Atomic writes to prevent corruption during crashes
- Project validation on every operation (detect manual config changes)

---

## Subtasks & Detailed Guidance

### Subtask T007 – Create ProjectContext dataclass

**Purpose**: Define the entity that represents a single Spec Kitty project with path validation and cached state.

**Steps**:
1. Create `src/specify_cli/mcp/session/context.py`
2. Implement ProjectContext dataclass:
   ```python
   from dataclasses import dataclass
   from pathlib import Path
   from typing import Optional, Dict, Any, List
   import yaml
   
   @dataclass
   class ProjectContext:
       """Represents a single Spec Kitty project managed by MCP server."""
       
       project_path: Path
       kittify_dir: Path
       session_dir: Path
       lock_dir: Path
       config: Dict[str, Any]
       active_feature: Optional[str] = None
       mission: Optional[str] = None
       
       def __post_init__(self):
           """Validate paths are absolute."""
           if not self.project_path.is_absolute():
               raise ValueError(f"project_path must be absolute: {self.project_path}")
       
       @classmethod
       def from_path(cls, project_path: Path) -> "ProjectContext":
           """Create ProjectContext from project root path with validation."""
           project_path = project_path.resolve()  # Convert to absolute
           kittify_dir = project_path / ".kittify"
           
           # Validation happens in T008
           if not kittify_dir.exists():
               raise ValueError(
                   f"Not a Spec Kitty project: {project_path} "
                   f"(missing .kittify/ directory)"
               )
           
           config_file = kittify_dir / "config.yaml"
           if not config_file.exists():
               raise ValueError(f"Missing .kittify/config.yaml in {project_path}")
           
           with open(config_file) as f:
               config = yaml.safe_load(f) or {}
           
           session_dir = kittify_dir / "mcp-sessions"
           lock_dir = kittify_dir  # Locks stored directly in .kittify/
           
           # Create session_dir if needed (T009)
           session_dir.mkdir(exist_ok=True)
           
           return cls(
               project_path=project_path,
               kittify_dir=kittify_dir,
               session_dir=session_dir,
               lock_dir=lock_dir,
               config=config
           )
       
       def get_feature_dir(self, feature_slug: str) -> Path:
           """Get path to feature directory."""
           return self.project_path / "kitty-specs" / feature_slug
       
       def list_features(self) -> List[str]:
           """List all feature slugs in kitty-specs/ directory."""
           specs_dir = self.project_path / "kitty-specs"
           if not specs_dir.exists():
               return []
           
           return [
               d.name for d in specs_dir.iterdir()
               if d.is_dir() and not d.name.startswith(".")
           ]
       
       def get_active_feature(self) -> Optional[str]:
           """Detect active feature from git branch or metadata."""
           # Simple implementation: check current git branch
           import subprocess
           
           try:
               result = subprocess.run(
                   ["git", "branch", "--show-current"],
                   cwd=self.project_path,
                   capture_output=True,
                   text=True,
                   check=True
               )
               branch = result.stdout.strip()
               
               # Feature branches typically: NNN-feature-name
               if branch and branch[0].isdigit():
                   return branch
               
               return None
           except (subprocess.CalledProcessError, FileNotFoundError):
               return None
   ```

**Files**:
- `src/specify_cli/mcp/session/context.py` (new, ~100 lines)

**Validation**:
- [ ] ProjectContext can be created from valid project path
- [ ] `from_path()` raises ValueError for non-Spec Kitty projects
- [ ] `from_path()` raises ValueError for missing config.yaml
- [ ] `get_feature_dir()` returns correct path
- [ ] `list_features()` returns all feature directories
- [ ] `get_active_feature()` detects current feature from git branch

**Notes**:
- Use `Path.resolve()` to ensure absolute paths
- Validation logic will be expanded in T008
- Session directory creation happens automatically (no manual setup needed)

---

### Subtask T008 – Implement project path validation

**Purpose**: Add comprehensive validation for Spec Kitty project structure before operations.

**Steps**:
1. In `context.py`, add validation method:
   ```python
   def validate_project_structure(self) -> List[str]:
       """Validate project structure, return list of errors."""
       errors = []
       
       # Check .kittify/ directory
       if not self.kittify_dir.exists():
           errors.append(f"Missing .kittify/ directory in {self.project_path}")
           return errors  # Can't continue without .kittify/
       
       # Check config.yaml
       config_file = self.kittify_dir / "config.yaml"
       if not config_file.exists():
           errors.append("Missing .kittify/config.yaml")
       
       # Check kitty-specs/ directory
       specs_dir = self.project_path / "kitty-specs"
       if not specs_dir.exists():
           errors.append("Missing kitty-specs/ directory")
       
       # Check missions directory
       missions_dir = self.kittify_dir / "missions"
       if not missions_dir.exists():
           errors.append("Missing .kittify/missions/ directory")
       
       return errors
   ```
2. Update `from_path()` to call validation:
   ```python
   # In from_path(), after creating context:
   errors = ctx.validate_project_structure()
   if errors:
       raise ValueError(
           f"Invalid Spec Kitty project structure:\n" +
           "\n".join(f"  - {e}" for e in errors)
       )
   ```
3. Add test in `tests/mcp/test_context.py`:
   ```python
   def test_validation_rejects_invalid_projects(tmp_path):
       """Test that validation catches missing directories."""
       # Create project without .kittify/
       with pytest.raises(ValueError, match="missing .kittify"):
           ProjectContext.from_path(tmp_path)
   ```

**Files**:
- `src/specify_cli/mcp/session/context.py` (add validate_project_structure, ~30 lines)
- `tests/mcp/test_context.py` (new, ~50 lines with multiple test cases)

**Validation**:
- [ ] Validation catches missing .kittify/ directory
- [ ] Validation catches missing config.yaml
- [ ] Validation catches missing kitty-specs/
- [ ] Error messages are actionable (suggest running `spec-kitty init`)

**Notes**:
- Validation runs every time `from_path()` is called (detects manual changes)
- Return all errors at once (not just first) for better UX

---

### Subtask T009 – Implement session directory creation

**Purpose**: Automatically create `.kittify/mcp-sessions/` directory if it doesn't exist.

**Steps**:
1. In `context.py`, in `from_path()` method (already partially done in T007):
   ```python
   session_dir = kittify_dir / "mcp-sessions"
   
   # Create if doesn't exist
   session_dir.mkdir(exist_ok=True, parents=False)
   ```
2. Add test to verify creation:
   ```python
   def test_session_dir_created_automatically(tmp_path):
       """Test that mcp-sessions/ is created if missing."""
       # Setup valid project without mcp-sessions/
       kittify = tmp_path / ".kittify"
       kittify.mkdir()
       (kittify / "config.yaml").write_text("mission: software-dev\n")
       (tmp_path / "kitty-specs").mkdir()
       (kittify / "missions").mkdir()
       
       ctx = ProjectContext.from_path(tmp_path)
       
       assert ctx.session_dir.exists()
       assert ctx.session_dir == kittify / "mcp-sessions"
   ```

**Files**:
- `src/specify_cli/mcp/session/context.py` (modify from_path, ~2 lines)
- `tests/mcp/test_context.py` (add test, ~15 lines)

**Validation**:
- [ ] Session directory created if missing
- [ ] No error if directory already exists (exist_ok=True)
- [ ] Directory owned by user running MCP server

**Notes**:
- Use `mkdir(exist_ok=True)` to handle concurrent creation (race condition safe)
- `parents=False` because `.kittify/` must already exist

---

### Subtask T010 – Create ConversationState dataclass

**Purpose**: Define the entity that tracks multi-turn discovery interviews and workflow state.

**Steps**:
1. Create `src/specify_cli/mcp/session/state.py`
2. Implement ConversationState dataclass:
   ```python
   from dataclasses import dataclass, field
   from pathlib import Path
   from typing import Dict, Any, List, Optional
   from datetime import datetime, timezone
   import uuid
   
   @dataclass
   class ConversationState:
       """Tracks multi-turn discovery interviews for Spec Kitty workflows."""
       
       session_id: str
       project_path: Path
       workflow: str  # "specify", "plan", "tasks", "implement", "review", "accept"
       phase: str  # "discovery", "clarification", "generation", "complete"
       questions_answered: Dict[str, Any] = field(default_factory=dict)
       questions_pending: List[str] = field(default_factory=list)
       accumulated_context: Dict[str, Any] = field(default_factory=dict)
       created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
       updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
       
       @classmethod
       def create(cls, project_path: Path, workflow: str) -> "ConversationState":
           """Create new conversation state with generated session ID."""
           return cls(
               session_id=str(uuid.uuid4()),
               project_path=project_path,
               workflow=workflow,
               phase="discovery"
           )
       
       def answer_question(self, question_id: str, answer: Any):
           """Record answer to a question."""
           self.questions_answered[question_id] = answer
           
           # Remove from pending if present
           if question_id in self.questions_pending:
               self.questions_pending.remove(question_id)
           
           self.updated_at = datetime.now(timezone.utc).isoformat()
       
       def add_pending_question(self, question_id: str):
           """Add a question to pending list."""
           if question_id not in self.questions_pending:
               self.questions_pending.append(question_id)
           
           self.updated_at = datetime.now(timezone.utc).isoformat()
       
       def update_context(self, key: str, value: Any):
           """Update accumulated context."""
           self.accumulated_context[key] = value
           self.updated_at = datetime.now(timezone.utc).isoformat()
       
       def is_complete(self) -> bool:
           """Check if workflow is complete."""
           return self.phase == "complete"
       
       def transition_phase(self, new_phase: str):
           """Transition to new workflow phase."""
           valid_phases = ["discovery", "clarification", "generation", "complete"]
           if new_phase not in valid_phases:
               raise ValueError(f"Invalid phase: {new_phase}")
           
           self.phase = new_phase
           self.updated_at = datetime.now(timezone.utc).isoformat()
   ```

**Files**:
- `src/specify_cli/mcp/session/state.py` (new, ~80 lines)

**Validation**:
- [ ] ConversationState can be created with required fields
- [ ] Session ID is valid UUID v4
- [ ] Timestamps are ISO 8601 format in UTC
- [ ] answer_question() updates both questions_answered and questions_pending
- [ ] is_complete() returns True only when phase="complete"

---

### Subtask T011 – Implement JSON serialization/deserialization

**Purpose**: Enable ConversationState to be saved to and loaded from JSON files.

**Steps**:
1. In `state.py`, add serialization methods:
   ```python
   import json
   
   def to_json(self) -> str:
       """Serialize to JSON string."""
       data = {
           "session_id": self.session_id,
           "project_path": str(self.project_path),
           "workflow": self.workflow,
           "phase": self.phase,
           "questions_answered": self.questions_answered,
           "questions_pending": self.questions_pending,
           "accumulated_context": self.accumulated_context,
           "created_at": self.created_at,
           "updated_at": self.updated_at
       }
       return json.dumps(data, indent=2)
   
   @classmethod
   def from_json(cls, json_str: str) -> "ConversationState":
       """Deserialize from JSON string."""
       data = json.loads(json_str)
       
       return cls(
           session_id=data["session_id"],
           project_path=Path(data["project_path"]),
           workflow=data["workflow"],
           phase=data["phase"],
           questions_answered=data.get("questions_answered", {}),
           questions_pending=data.get("questions_pending", []),
           accumulated_context=data.get("accumulated_context", {}),
           created_at=data["created_at"],
           updated_at=data["updated_at"]
       )
   
   def save_to_file(self, session_dir: Path):
       """Save state to JSON file (uses atomic write from T012)."""
       from .persistence import atomic_write
       
       file_path = session_dir / f"{self.session_id}.json"
       atomic_write(file_path, self.to_json())
   
   @classmethod
   def load_from_file(cls, session_dir: Path, session_id: str) -> Optional["ConversationState"]:
       """Load state from JSON file."""
       file_path = session_dir / f"{session_id}.json"
       
       if not file_path.exists():
           return None
       
       try:
           with open(file_path, "r") as f:
               json_str = f.read()
           
           return cls.from_json(json_str)
       except (json.JSONDecodeError, KeyError) as e:
           # Log error but don't crash
           print(f"Warning: Failed to load session {session_id}: {e}")
           return None
   ```

**Files**:
- `src/specify_cli/mcp/session/state.py` (add serialization methods, ~60 lines)

**Validation**:
- [ ] `to_json()` produces valid JSON
- [ ] `from_json()` reconstructs ConversationState correctly
- [ ] Round-trip serialization preserves all fields
- [ ] Path converted to string in JSON (not object)
- [ ] Corrupt JSON handled gracefully (returns None, logs warning)

---

### Subtask T012 – Implement atomic file write

**Purpose**: Prevent corruption of state files during crashes by writing to temporary file first.

**Steps**:
1. Create `src/specify_cli/mcp/session/persistence.py`
2. Implement atomic write function:
   ```python
   from pathlib import Path
   import tempfile
   import os
   
   def atomic_write(file_path: Path, content: str):
       """
       Write content to file atomically.
       
       Strategy:
       1. Write to temporary file in same directory
       2. fsync to ensure data on disk
       3. Rename to target filename (atomic operation)
       
       This prevents corruption if process crashes during write.
       """
       # Create temp file in same directory (ensures same filesystem)
       temp_fd, temp_path = tempfile.mkstemp(
           dir=file_path.parent,
           prefix=f".{file_path.name}.tmp."
       )
       
       try:
           # Write content
           os.write(temp_fd, content.encode("utf-8"))
           
           # Ensure data written to disk
           os.fsync(temp_fd)
           
           # Close file descriptor
           os.close(temp_fd)
           
           # Atomic rename
           os.replace(temp_path, file_path)
       except Exception:
           # Clean up temp file on error
           try:
               os.close(temp_fd)
           except Exception:
               pass
           
           try:
               os.unlink(temp_path)
           except Exception:
               pass
           
           raise
   ```

**Files**:
- `src/specify_cli/mcp/session/persistence.py` (new, ~50 lines)

**Validation**:
- [ ] Atomic write creates temp file in same directory
- [ ] Temp file renamed to target (not copied)
- [ ] Process crash during write doesn't corrupt existing file
- [ ] Cleanup happens on error (no orphaned temp files)

**Notes**:
- Use `os.replace()` (atomic on POSIX and Windows)
- `fsync()` ensures data on disk before rename
- Temp file in same directory ensures same filesystem (atomic rename requirement)

---

### Subtask T013 – Add state resumption logic

**Purpose**: Enable MCP clients to resume interrupted discovery interviews by providing session_id.

**Steps**:
1. In `state.py`, add resumption helper:
   ```python
   @classmethod
   def resume_or_create(
       cls,
       session_dir: Path,
       project_path: Path,
       workflow: str,
       session_id: Optional[str] = None
   ) -> "ConversationState":
       """Resume existing session or create new one."""
       if session_id:
           # Try to load existing session
           state = cls.load_from_file(session_dir, session_id)
           
           if state:
               # Validate workflow matches
               if state.workflow != workflow:
                   raise ValueError(
                       f"Session {session_id} is for workflow '{state.workflow}', "
                       f"not '{workflow}'"
                   )
               
               return state
           
           # Session ID provided but file not found
           raise FileNotFoundError(
               f"Session {session_id} not found in {session_dir}"
           )
       
       # No session ID provided, create new session
       return cls.create(project_path, workflow)
   ```
2. Add test for resumption:
   ```python
   def test_resume_existing_session(tmp_path):
       """Test resuming a saved session."""
       session_dir = tmp_path / "sessions"
       session_dir.mkdir()
       
       # Create and save initial state
       state1 = ConversationState.create(tmp_path / "project", "specify")
       state1.answer_question("q1", "answer1")
       state1.save_to_file(session_dir)
       
       # Resume session
       state2 = ConversationState.resume_or_create(
           session_dir, tmp_path / "project", "specify", state1.session_id
       )
       
       assert state2.session_id == state1.session_id
       assert state2.questions_answered == {"q1": "answer1"}
   ```

**Files**:
- `src/specify_cli/mcp/session/state.py` (add resume_or_create, ~30 lines)
- `tests/mcp/test_state.py` (new, ~80 lines with multiple test cases)

**Validation**:
- [ ] Resumption loads existing session correctly
- [ ] Resumption validates workflow matches
- [ ] Missing session raises FileNotFoundError with clear message
- [ ] New session created if no session_id provided

---

## Test Strategy

**Unit Tests**:
- `tests/mcp/test_context.py`: ProjectContext creation, validation, feature listing
- `tests/mcp/test_state.py`: ConversationState creation, serialization, resumption
- `tests/mcp/test_persistence.py`: Atomic writes, error handling

**Test Fixtures**:
Create `tests/fixtures/valid-spec-kitty-project/`:
- `.kittify/config.yaml`
- `.kittify/missions/`
- `kitty-specs/001-test-feature/`

**Edge Cases to Test**:
- Invalid project paths (non-existent, not absolute)
- Missing .kittify/ directory
- Corrupt JSON in session files
- Concurrent writes (race conditions)
- Session resumption with mismatched workflow

---

## Risks & Mitigations

**Risk 1: Corrupt JSON files**
- **Mitigation**: Atomic writes (T012), try/except during load, log warnings

**Risk 2: Concurrent writes to same session**
- **Mitigation**: File locking (WP03 will add locking layer)

**Risk 3: Path validation fails to detect all issues**
- **Mitigation**: Comprehensive validation checklist, actionable error messages

**Risk 4: Session files accumulate forever (no cleanup)**
- **Mitigation**: Document manual cleanup process; consider TTL in future feature

---

## Review Guidance

**Key Checkpoints**:
- [ ] ProjectContext matches data-model.md specification
- [ ] ConversationState matches data-model.md specification
- [ ] All validation errors are actionable (tell user what to fix)
- [ ] JSON serialization preserves all fields correctly
- [ ] Atomic writes prevent file corruption
- [ ] Session resumption works across server restarts
- [ ] Tests cover edge cases (invalid paths, corrupt JSON, missing files)

**Acceptance Criteria**:
- ProjectContext can be created for any valid Spec Kitty project
- ConversationState can be saved, loaded, and resumed
- No data loss during crashes (atomic writes)
- Clear error messages for invalid projects

---

## Activity Log

> **CRITICAL**: Entries MUST be in chronological order (oldest first, newest last).

- 2026-01-31T00:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

### Updating Lane Status

**Implementation Command**:
```bash
spec-kitty implement WP02 --base WP01
```
(Depends on WP01, so branch from WP01's branch)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-31T12:28:02Z – unknown – shell_pid=48672 – lane=for_review – Ready for review: Project context & state management fully implemented with comprehensive test suite (43 tests). All success criteria met including ProjectContext, ConversationState, atomic writes, JSON serialization, and state resumption. See WP02_IMPLEMENTATION_SUMMARY.md for details.
- 2026-01-31T12:30:32Z – cursor – shell_pid=60166 – lane=doing – Started review via workflow command
- 2026-01-31T12:32:40Z – cursor – shell_pid=60166 – lane=done – Review passed: Excellent implementation of project context and state management. All success criteria met including ProjectContext with comprehensive validation, ConversationState with JSON serialization, atomic writes for crash safety, and state resumption. 43 tests provide thorough coverage of happy paths, edge cases, and error conditions. Code quality is high with clear docstrings, type hints, and proper error handling. Implementation matches data-model.md specification exactly. Ready for WP03 and WP04 to begin.
