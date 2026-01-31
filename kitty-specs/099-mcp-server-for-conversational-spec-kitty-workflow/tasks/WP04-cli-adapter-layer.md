---
work_package_id: WP04
title: CLI Adapter Layer
lane: "done"
dependencies: [WP02]
base_branch: 099-mcp-server-for-conversational-spec-kitty-workflow-WP02
base_commit: c5d5653835011f41dbe9ee1c90550912e84bde53
created_at: '2026-01-31T12:40:12.093882+00:00'
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase 1 - Foundation
assignee: 'cursor'
agent: "cursor"
shell_pid: "83706"
review_status: "approved"
reviewed_by: "Rodrigo Leven"
history:
- timestamp: '2026-01-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – CLI Adapter Layer

## Objectives & Success Criteria

**Goal**: Create thin adapter layer that wraps existing CLI modules, providing consistent interface for MCP tools without duplicating business logic.

**Success Criteria**:
- OperationResult dataclass created with all required fields
- CLIAdapter class skeleton implemented with ProjectContext dependency
- Feature operations adapter methods working (create_feature, setup_plan, create_tasks)
- Task operations adapter methods working (list_tasks, move_task, add_history)
- Workspace operations adapter methods working (create_worktree, list_worktrees)
- System operations adapter methods working (validate_project, get_missions)
- All CLI exceptions caught and converted to OperationResult with errors
- Contract tests verify adapter calls existing CLI code (no duplication)

---

## Context & Constraints

**Prerequisites**:
- Review `plan.md` section: CLI Adapter Interface
- Review `data-model.md` section: CLIAdapter, OperationResult entities
- WP02 completed (ProjectContext provides project state)

**Architectural Constraints**:
- AC-001: Wrap existing CLI code, do NOT duplicate business logic
- AC-002: MCP implementation architecturally independent from CLI
- Use direct Python imports (NOT subprocess calls)
- Standardized OperationResult return format for all methods

**Key Design Principles**:
- Each adapter method maps 1:1 to existing CLI function
- CLI exceptions → structured errors in OperationResult
- No business logic in adapter (only parameter translation and error handling)

---

## Subtasks & Detailed Guidance

### Subtask T020 – Create OperationResult dataclass

**Purpose**: Define standardized result format for all MCP tool operations.

**Steps**:
1. Create `src/specify_cli/mcp/adapters/__init__.py`
2. Implement OperationResult:
   ```python
   from dataclasses import dataclass, field
   from pathlib import Path
   from typing import Optional, Dict, Any, List
   
   @dataclass
   class OperationResult:
       """Standardized result format for MCP tool operations."""
       
       success: bool
       message: str
       data: Optional[Dict[str, Any]] = None
       artifacts: List[Path] = field(default_factory=list)
       errors: List[str] = field(default_factory=list)
       warnings: List[str] = field(default_factory=list)
       
       def to_dict(self) -> Dict[str, Any]:
           """Serialize to dictionary for MCP response."""
           return {
               "success": self.success,
               "message": self.message,
               "data": self.data,
               "artifacts": [str(p) for p in self.artifacts],
               "errors": self.errors,
               "warnings": self.warnings
           }
       
       @classmethod
       def success_result(
           cls,
           message: str,
           data: Optional[Dict[str, Any]] = None,
           artifacts: Optional[List[Path]] = None
       ) -> "OperationResult":
           """Create success result."""
           return cls(
               success=True,
               message=message,
               data=data,
               artifacts=artifacts or []
           )
       
       @classmethod
       def error_result(
           cls,
           message: str,
           errors: Optional[List[str]] = None
       ) -> "OperationResult":
           """Create error result."""
           return cls(
               success=False,
               message=message,
               errors=errors or [message]
           )
   ```

**Files**:
- `src/specify_cli/mcp/adapters/__init__.py` (new, ~60 lines)

**Validation**:
- [ ] OperationResult can be created with required fields
- [ ] `to_dict()` serializes all fields correctly
- [ ] Paths converted to strings in serialization
- [ ] Factory methods work (success_result, error_result)

---

### Subtask T021 – Create CLIAdapter class skeleton

**Purpose**: Establish adapter class structure with ProjectContext dependency.

**Steps**:
1. Create `src/specify_cli/mcp/adapters/cli_adapter.py`
2. Implement CLIAdapter skeleton:
   ```python
   from typing import Optional, List
   from pathlib import Path
   from specify_cli.mcp.session.context import ProjectContext
   from . import OperationResult
   
   class CLIAdapter:
       """Wraps existing CLI modules for MCP tool invocation."""
       
       def __init__(self, project_context: ProjectContext):
           """Initialize adapter with project context."""
           self.project_context = project_context
           self.project_path = project_context.project_path
           self.kittify_dir = project_context.kittify_dir
       
       # Feature operations (T022)
       def create_feature(self, slug: str, description: str) -> OperationResult:
           """Create new feature specification."""
           raise NotImplementedError("Implemented in T022")
       
       def setup_plan(self, feature_slug: str) -> OperationResult:
           """Generate technical plan for feature."""
           raise NotImplementedError("Implemented in T022")
       
       def create_tasks(self, feature_slug: str) -> OperationResult:
           """Generate work package breakdown."""
           raise NotImplementedError("Implemented in T022")
       
       # Task operations (T023)
       def list_tasks(
           self,
           feature_slug: str,
           lane: Optional[str] = None
       ) -> OperationResult:
           """List tasks for feature, optionally filtered by lane."""
           raise NotImplementedError("Implemented in T023")
       
       def move_task(
           self,
           feature_slug: str,
           task_id: str,
           lane: str,
           note: Optional[str] = None
       ) -> OperationResult:
           """Move task between lanes."""
           raise NotImplementedError("Implemented in T023")
       
       def add_history(
           self,
           feature_slug: str,
           task_id: str,
           note: str
       ) -> OperationResult:
           """Add activity log entry to task."""
           raise NotImplementedError("Implemented in T023")
       
       # Workspace operations (T024)
       def create_worktree(
           self,
           feature_slug: str,
           wp_id: str,
           base_wp: Optional[str] = None
       ) -> OperationResult:
           """Create git worktree for work package."""
           raise NotImplementedError("Implemented in T024")
       
       def list_worktrees(self) -> OperationResult:
           """List all active worktrees."""
           raise NotImplementedError("Implemented in T024")
       
       # System operations (T025)
       def validate_project(self) -> OperationResult:
           """Validate project structure."""
           raise NotImplementedError("Implemented in T025")
       
       def get_missions(self) -> OperationResult:
           """List available missions."""
           raise NotImplementedError("Implemented in T025")
   ```

**Files**:
- `src/specify_cli/mcp/adapters/cli_adapter.py` (new, ~80 lines)

**Validation**:
- [ ] CLIAdapter can be instantiated with ProjectContext
- [ ] All method signatures match plan.md specification
- [ ] Methods raise NotImplementedError (to be implemented in T022-T025)

---

### Subtask T022 – Implement feature operation adapters

**Purpose**: Wrap existing feature CLI functions for MCP tool access.

**Steps**:
1. In `cli_adapter.py`, implement feature methods by importing existing CLI code:
   ```python
   def create_feature(self, slug: str, description: str) -> OperationResult:
       """Create new feature specification."""
       try:
           from specify_cli.agent_utils.features import create_feature_directory
           
           # Call existing CLI function
           feature_dir = create_feature_directory(
               project_path=self.project_path,
               feature_slug=slug,
               description=description
           )
           
           spec_file = feature_dir / "spec.md"
           
           return OperationResult.success_result(
               message=f"Feature {slug} created successfully",
               data={
                   "feature_slug": slug,
                   "feature_dir": str(feature_dir),
                   "spec_file": str(spec_file)
               },
               artifacts=[spec_file]
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to create feature: {str(e)}",
               errors=[str(e)]
           )
   
   def setup_plan(self, feature_slug: str) -> OperationResult:
       """Generate technical plan for feature."""
       try:
           from specify_cli.agent_utils.planning import generate_plan
           
           feature_dir = self.project_context.get_feature_dir(feature_slug)
           plan_file = generate_plan(feature_dir)
           
           return OperationResult.success_result(
               message=f"Plan generated for {feature_slug}",
               data={"plan_file": str(plan_file)},
               artifacts=[plan_file]
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to generate plan: {str(e)}",
               errors=[str(e)]
           )
   
   def create_tasks(self, feature_slug: str) -> OperationResult:
       """Generate work package breakdown."""
       try:
           from specify_cli.agent_utils.tasks import generate_work_packages
           
           feature_dir = self.project_context.get_feature_dir(feature_slug)
           tasks_file, wp_files = generate_work_packages(feature_dir)
           
           return OperationResult.success_result(
               message=f"Tasks generated for {feature_slug}",
               data={
                   "tasks_file": str(tasks_file),
                   "work_packages": [str(f) for f in wp_files]
               },
               artifacts=[tasks_file] + wp_files
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to generate tasks: {str(e)}",
               errors=[str(e)]
           )
   ```
2. Note: The actual CLI function names may differ; check existing codebase and adjust imports accordingly

**Files**:
- `src/specify_cli/mcp/adapters/cli_adapter.py` (implement methods, ~80 lines)

**Parallel?**: Yes (independent from T023-T025)

**Validation**:
- [ ] create_feature calls existing CLI code (no duplication)
- [ ] setup_plan reuses existing planning logic
- [ ] create_tasks reuses existing task generation
- [ ] All exceptions caught and converted to OperationResult
- [ ] Success results include artifacts (created files)

**Notes**:
- Check `src/specify_cli/agent_utils/` and `src/specify_cli/cli/commands/` for existing functions
- If exact functions don't exist, adapt the closest equivalent
- Ensure NO business logic duplication

---

### Subtask T023 – Implement task operation adapters

**Purpose**: Wrap existing task management CLI functions.

**Steps**:
1. Implement task methods:
   ```python
   def list_tasks(
       self,
       feature_slug: str,
       lane: Optional[str] = None
   ) -> OperationResult:
       """List tasks for feature, optionally filtered by lane."""
       try:
           from specify_cli.agent_utils.tasks import list_work_packages
           
           feature_dir = self.project_context.get_feature_dir(feature_slug)
           tasks = list_work_packages(feature_dir, lane=lane)
           
           return OperationResult.success_result(
               message=f"Found {len(tasks)} tasks",
               data={"tasks": tasks}
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to list tasks: {str(e)}",
               errors=[str(e)]
           )
   
   def move_task(
       self,
       feature_slug: str,
       task_id: str,
       lane: str,
       note: Optional[str] = None
   ) -> OperationResult:
       """Move task between lanes."""
       try:
           from specify_cli.agent_utils.tasks import move_work_package
           
           feature_dir = self.project_context.get_feature_dir(feature_slug)
           updated_file = move_work_package(
               feature_dir, task_id, lane, note
           )
           
           return OperationResult.success_result(
               message=f"Task {task_id} moved to {lane}",
               data={"task_id": task_id, "lane": lane},
               artifacts=[updated_file]
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to move task: {str(e)}",
               errors=[str(e)]
           )
   
   def add_history(
       self,
       feature_slug: str,
       task_id: str,
       note: str
   ) -> OperationResult:
       """Add activity log entry to task."""
       try:
           from specify_cli.agent_utils.tasks import add_task_history
           
           feature_dir = self.project_context.get_feature_dir(feature_slug)
           updated_file = add_task_history(feature_dir, task_id, note)
           
           return OperationResult.success_result(
               message=f"History added to {task_id}",
               data={"task_id": task_id},
               artifacts=[updated_file]
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to add history: {str(e)}",
               errors=[str(e)]
           )
   ```

**Files**:
- `src/specify_cli/mcp/adapters/cli_adapter.py` (implement methods, ~70 lines)

**Parallel?**: Yes (independent from T022, T024, T025)

**Validation**:
- [ ] list_tasks calls existing task listing code
- [ ] move_task updates frontmatter and activity log
- [ ] add_history appends to activity log
- [ ] All methods return OperationResult

---

### Subtask T024 – Implement workspace operation adapters

**Purpose**: Wrap existing worktree management CLI functions.

**Steps**:
1. Implement workspace methods:
   ```python
   def create_worktree(
       self,
       feature_slug: str,
       wp_id: str,
       base_wp: Optional[str] = None
   ) -> OperationResult:
       """Create git worktree for work package."""
       try:
           from specify_cli.agent_utils.workspace import create_wp_worktree
           
           worktree_path = create_wp_worktree(
               project_path=self.project_path,
               feature_slug=feature_slug,
               wp_id=wp_id,
               base_wp=base_wp
           )
           
           return OperationResult.success_result(
               message=f"Worktree created for {wp_id}",
               data={
                   "wp_id": wp_id,
                   "worktree_path": str(worktree_path),
                   "base_wp": base_wp
               }
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to create worktree: {str(e)}",
               errors=[str(e)]
           )
   
   def list_worktrees(self) -> OperationResult:
       """List all active worktrees."""
       try:
           from specify_cli.agent_utils.workspace import list_all_worktrees
           
           worktrees = list_all_worktrees(self.project_path)
           
           return OperationResult.success_result(
               message=f"Found {len(worktrees)} worktrees",
               data={"worktrees": worktrees}
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to list worktrees: {str(e)}",
               errors=[str(e)]
           )
   ```

**Files**:
- `src/specify_cli/mcp/adapters/cli_adapter.py` (implement methods, ~50 lines)

**Parallel?**: Yes (independent from T022, T023, T025)

**Validation**:
- [ ] create_worktree calls existing worktree creation code
- [ ] list_worktrees scans .worktrees/ directory
- [ ] base_wp parameter passed correctly for dependency-based branching

---

### Subtask T025 – Implement system operation adapters

**Purpose**: Wrap existing system/validation CLI functions.

**Steps**:
1. Implement system methods:
   ```python
   def validate_project(self) -> OperationResult:
       """Validate project structure."""
       try:
           errors = self.project_context.validate_project_structure()
           
           if errors:
               return OperationResult.error_result(
                   message="Project validation failed",
                   errors=errors
               )
           
           return OperationResult.success_result(
               message="Project structure is valid"
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Validation error: {str(e)}",
               errors=[str(e)]
           )
   
   def get_missions(self) -> OperationResult:
       """List available missions."""
       try:
           missions_dir = self.kittify_dir / "missions"
           
           if not missions_dir.exists():
               return OperationResult.success_result(
                   message="No missions configured",
                   data={"missions": []}
               )
           
           missions = [
               d.name for d in missions_dir.iterdir()
               if d.is_dir() and not d.name.startswith(".")
           ]
           
           return OperationResult.success_result(
               message=f"Found {len(missions)} missions",
               data={"missions": missions}
           )
       except Exception as e:
           return OperationResult.error_result(
               message=f"Failed to list missions: {str(e)}",
               errors=[str(e)]
           )
   ```

**Files**:
- `src/specify_cli/mcp/adapters/cli_adapter.py` (implement methods, ~50 lines)

**Parallel?**: Yes (independent from T022-T024)

**Validation**:
- [ ] validate_project uses ProjectContext validation
- [ ] get_missions scans missions directory
- [ ] Empty results handled gracefully

---

### Subtask T026 – Add error handling wrapper

**Purpose**: Centralize exception handling for all adapter methods.

**Steps**:
1. Add error handling decorator:
   ```python
   from functools import wraps
   
   def handle_cli_errors(method):
       """Decorator to catch CLI exceptions and convert to OperationResult."""
       @wraps(method)
       def wrapper(*args, **kwargs):
           try:
               return method(*args, **kwargs)
           except Exception as e:
               # Log full exception for debugging
               import logging
               logging.exception(f"CLI adapter error in {method.__name__}")
               
               # Return structured error
               return OperationResult.error_result(
                   message=f"Operation failed: {str(e)}",
                   errors=[
                       str(e),
                       f"Method: {method.__name__}",
                       f"See logs for full traceback"
                   ]
               )
       return wrapper
   ```
2. Apply decorator to all methods (optional, methods already have try/except)
3. Add test for error handling:
   ```python
   def test_cli_adapter_handles_exceptions(tmp_path, monkeypatch):
       """Test that exceptions are caught and converted to errors."""
       ctx = ProjectContext.from_path(tmp_path)
       adapter = CLIAdapter(ctx)
       
       # Force an exception
       monkeypatch.setattr(
           "specify_cli.agent_utils.features.create_feature_directory",
           lambda *args, **kwargs: 1/0  # ZeroDivisionError
       )
       
       result = adapter.create_feature("test", "desc")
       
       assert not result.success
       assert "division by zero" in result.message.lower()
   ```

**Files**:
- `src/specify_cli/mcp/adapters/cli_adapter.py` (add decorator, ~20 lines)
- `tests/mcp/test_cli_adapter.py` (new, ~100 lines with contract tests)

**Validation**:
- [ ] All exceptions caught and logged
- [ ] OperationResult.error_result always returned on exception
- [ ] Error messages are actionable
- [ ] Tracebacks logged for debugging

---

## Test Strategy

**Contract Tests** (`tests/mcp/test_cli_adapter.py`):
- Verify each adapter method calls existing CLI code (not duplicating logic)
- Use mocks to detect CLI function calls
- Test exception handling

**Integration Tests** (WP10):
- End-to-end adapter calls with real project fixtures
- Verify artifacts created on disk

**Example Contract Test**:
```python
def test_create_feature_calls_existing_cli(monkeypatch):
    """Verify adapter delegates to existing CLI code."""
    called = []
    
    def mock_create_feature(*args, **kwargs):
        called.append((args, kwargs))
        return Path("/fake/feature")
    
    monkeypatch.setattr(
        "specify_cli.agent_utils.features.create_feature_directory",
        mock_create_feature
    )
    
    ctx = ProjectContext.from_path(Path("/fake"))
    adapter = CLIAdapter(ctx)
    result = adapter.create_feature("test", "desc")
    
    assert len(called) == 1  # CLI function was called
    assert result.success
```

---

## Risks & Mitigations

**Risk 1: CLI function signatures change**
- **Mitigation**: Contract tests detect breakage immediately

**Risk 2: Adapter accidentally duplicates business logic**
- **Mitigation**: Code review checklist, contract tests verify delegation

**Risk 3: Exceptions leak to MCP clients without structure**
- **Mitigation**: Global exception handler, all methods return OperationResult

**Risk 4: CLI imports fail (missing modules)**
- **Mitigation**: ImportError caught and converted to OperationResult.error

---

## Review Guidance

**Key Checkpoints**:
- [ ] OperationResult matches data-model.md specification
- [ ] CLIAdapter methods delegate to existing CLI code (NO duplication)
- [ ] All exceptions caught and converted to OperationResult
- [ ] Success results include artifacts when files created
- [ ] Error results include actionable messages
- [ ] Contract tests verify delegation (not mocking too much)

**Acceptance Criteria**:
- Adapter can invoke all planned operations
- No business logic duplicated from CLI
- Consistent OperationResult format across all methods
- Error handling prevents crashes

---

## Activity Log

- 2026-01-31T00:00:00Z – system – lane=planned – Prompt generated via /spec-kitty.tasks

---

**Implementation Command**:
```bash
spec-kitty implement WP04 --base WP02
```
- 2026-01-31T12:49:51Z – unknown – shell_pid=71674 – lane=for_review – Ready for review: CLI adapter layer complete with OperationResult, CLIAdapter class, feature/task/workspace/system operations, error handling, contract tests, integration tests, and documentation
- 2026-01-31T12:51:12Z – cursor – shell_pid=83706 – lane=doing – Started review via workflow command
- 2026-01-31T12:53:12Z – cursor – shell_pid=83706 – lane=done – Review passed: CLI adapter layer fully implemented with OperationResult, CLIAdapter with all operations (feature/task/workspace/system), comprehensive error handling, contract and integration tests, excellent documentation. Pragmatic trade-offs documented for future CLI refactoring.
