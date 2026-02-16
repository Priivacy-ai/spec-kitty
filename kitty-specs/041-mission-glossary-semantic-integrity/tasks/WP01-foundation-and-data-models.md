---
work_package_id: WP01
title: Foundation & Data Models
lane: "for_review"
dependencies: []
base_branch: 2.x
base_commit: c60760d595370200d1f4c30554b18a380b702a6d
created_at: '2026-02-16T13:12:59.865818+00:00'
subtasks: [T001, T002, T003, T004, T005]
shell_pid: "36474"
agent: "claude-sonnet"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Foundation & Data Models

**ID**: WP01
**Priority**: P1 (blocking for all other WPs)
**Estimated Effort**: 1-2 days

## Objective

Establish the foundational package structure, core data models, exception hierarchy, and test infrastructure for the glossary semantic integrity runtime.

## Context

This is the foundational work package for the glossary feature. It creates the basic building blocks that all other components depend on: data models (TermSurface, TermSense, SemanticConflict), exceptions (BlockedByConflict, DeferredToAsync), and the GlossaryScope enum.

**Design references**:
- [data-model.md](../data-model.md) - Complete entity definitions
- [plan.md](../plan.md) - Architecture and technical context

**Key architectural decisions**:
- Event sourcing: All state in event log, no side-channel files
- Python 3.11+ dataclasses with type annotations
- GlossaryScope resolution order: mission_local → team_domain → audience_domain → spec_kitty_core

## Implementation Command

```bash
spec-kitty implement WP01
```

**No dependencies** - this is the foundational WP.

---

## Subtask Breakdown

### Subtask T001: Create glossary package structure

**Purpose**: Set up the Python package structure for `src/specify_cli/glossary/`.

**Steps**:

1. Create package directory:
   ```bash
   mkdir -p src/specify_cli/glossary
   touch src/specify_cli/glossary/__init__.py
   ```

2. Create module files:
   ```
   src/specify_cli/glossary/
   ├── __init__.py          # Public API exports
   ├── models.py            # Core data models (TermSurface, TermSense, etc.)
   ├── exceptions.py        # Exception hierarchy
   ├── scope.py             # GlossaryScope enum and utilities
   ├── extraction.py        # Term extraction (WP03)
   ├── resolution.py        # Scope resolution (WP04)
   ├── conflict.py          # Conflict detection (WP04)
   ├── middleware.py        # Middleware components (WP03-WP07)
   ├── clarification.py     # Interactive prompts (WP06)
   ├── checkpoint.py        # Checkpoint/resume (WP07)
   ├── events.py            # Event emission (WP08)
   └── strictness.py        # Strictness policy (WP05)
   ```

3. Add public API exports to `__init__.py`:
   ```python
   """Glossary semantic integrity runtime for mission framework."""

   from .models import (
       TermSurface,
       TermSense,
       SemanticConflict,
       SenseStatus,
       ConflictType,
       Severity,
   )
   from .exceptions import (
       GlossaryError,
       BlockedByConflict,
       DeferredToAsync,
       AbortResume,
   )
   from .scope import GlossaryScope

   __all__ = [
       "TermSurface",
       "TermSense",
       "SemanticConflict",
       "SenseStatus",
       "ConflictType",
       "Severity",
       "GlossaryError",
       "BlockedByConflict",
       "DeferredToAsync",
       "AbortResume",
       "GlossaryScope",
   ]

   __version__ = "0.1.0"
   ```

4. Create test directory:
   ```bash
   mkdir -p tests/specify_cli/glossary
   touch tests/specify_cli/glossary/__init__.py
   touch tests/specify_cli/glossary/conftest.py
   ```

**Files created**:
- `src/specify_cli/glossary/__init__.py` (~30 lines)
- `src/specify_cli/glossary/models.py` (stub, filled in T002)
- `src/specify_cli/glossary/exceptions.py` (stub, filled in T003)
- `src/specify_cli/glossary/scope.py` (stub, filled in T005)
- `tests/specify_cli/glossary/conftest.py` (stub, filled in T004)
- 8 other module stubs (filled in later WPs)

**Validation**:
- [ ] Package imports successfully: `python -c "import specify_cli.glossary"`
- [ ] No import errors
- [ ] __version__ is accessible

---

### Subtask T002: Define core data models

**Purpose**: Implement TermSurface, TermSense, SemanticConflict, and supporting enums as Python dataclasses.

**Steps**:

1. **Create models.py** with core data structures:

   ```python
   """Core data models for glossary semantic integrity."""

   from dataclasses import dataclass, field
   from datetime import datetime
   from enum import Enum
   from typing import List, Optional


   @dataclass(frozen=True)
   class TermSurface:
       """Raw string representation of a term."""
       surface_text: str  # e.g., "workspace"

       def __post_init__(self):
           # Validate: must be normalized (lowercase, trimmed)
           if self.surface_text != self.surface_text.lower().strip():
               raise ValueError(f"TermSurface must be normalized: {self.surface_text}")


   class SenseStatus(Enum):
       """Status of a TermSense."""
       DRAFT = "draft"          # Auto-extracted, low confidence
       ACTIVE = "active"        # Promoted by user or high confidence
       DEPRECATED = "deprecated"  # Kept in history, not in active resolution


   @dataclass
   class Provenance:
       """Provenance metadata for a TermSense."""
       actor_id: str      # e.g., "user:alice" or "llm:claude-sonnet-4"
       timestamp: datetime
       source: str        # e.g., "user_clarification", "metadata_hint", "auto_extraction"


   @dataclass
   class TermSense:
       """Meaning of a TermSurface within a specific GlossaryScope."""
       surface: TermSurface
       scope: str  # GlossaryScope enum value (defined in scope.py)
       definition: str
       provenance: Provenance
       confidence: float  # 0.0-1.0
       status: SenseStatus = SenseStatus.DRAFT

       def __post_init__(self):
           # Validate confidence range
           if not 0.0 <= self.confidence <= 1.0:
               raise ValueError(f"Confidence must be 0.0-1.0: {self.confidence}")
           # Validate definition not empty
           if not self.definition.strip():
               raise ValueError("Definition cannot be empty")


   class ConflictType(Enum):
       """Type of semantic conflict."""
       UNKNOWN = "unknown"                      # No match in any scope
       AMBIGUOUS = "ambiguous"                  # Multiple active senses, unqualified usage
       INCONSISTENT = "inconsistent"            # LLM output contradicts active glossary
       UNRESOLVED_CRITICAL = "unresolved_critical"  # Unknown critical term, low confidence


   class Severity(Enum):
       """Severity level of a semantic conflict."""
       LOW = "low"
       MEDIUM = "medium"
       HIGH = "high"


   @dataclass
   class SenseRef:
       """Reference to a TermSense (used in conflict candidates)."""
       surface: str
       scope: str
       definition: str
       confidence: float


   @dataclass
   class SemanticConflict:
       """Classification of a term conflict."""
       term: TermSurface
       conflict_type: ConflictType
       severity: Severity
       confidence: float  # 0.0-1.0 (confidence in conflict detection)
       candidate_senses: List[SenseRef] = field(default_factory=list)
       context: str = ""  # Usage location (e.g., "step input: description field")

       def __post_init__(self):
           # Validate: AMBIGUOUS type must have candidates
           if self.conflict_type == ConflictType.AMBIGUOUS and not self.candidate_senses:
               raise ValueError("AMBIGUOUS conflict must have candidate_senses")
   ```

2. **Add serialization helpers** (for event emission):

   ```python
   def term_surface_to_dict(ts: TermSurface) -> dict:
       """Serialize TermSurface to dict."""
       return {"surface_text": ts.surface_text}

   def term_sense_to_dict(ts: TermSense) -> dict:
       """Serialize TermSense to dict."""
       return {
           "surface": term_surface_to_dict(ts.surface),
           "scope": ts.scope,
           "definition": ts.definition,
           "provenance": {
               "actor_id": ts.provenance.actor_id,
               "timestamp": ts.provenance.timestamp.isoformat(),
               "source": ts.provenance.source,
           },
           "confidence": ts.confidence,
           "status": ts.status.value,
       }

   def semantic_conflict_to_dict(sc: SemanticConflict) -> dict:
       """Serialize SemanticConflict to dict."""
       return {
           "term": term_surface_to_dict(sc.term),
           "conflict_type": sc.conflict_type.value,
           "severity": sc.severity.value,
           "confidence": sc.confidence,
           "candidate_senses": [
               {
                   "surface": c.surface,
                   "scope": c.scope,
                   "definition": c.definition,
                   "confidence": c.confidence,
               }
               for c in sc.candidate_senses
           ],
           "context": sc.context,
       }
   ```

3. **Add basic tests** (in `tests/specify_cli/glossary/test_models.py`):

   ```python
   import pytest
   from datetime import datetime
   from specify_cli.glossary.models import (
       TermSurface, TermSense, SemanticConflict, Provenance,
       SenseStatus, ConflictType, Severity, SenseRef,
   )

   def test_term_surface_normalized():
       """TermSurface must be lowercase and trimmed."""
       ts = TermSurface("workspace")
       assert ts.surface_text == "workspace"

       with pytest.raises(ValueError, match="must be normalized"):
           TermSurface("Workspace")  # Not lowercase

       with pytest.raises(ValueError, match="must be normalized"):
           TermSurface(" workspace ")  # Not trimmed

   def test_term_sense_validation():
       """TermSense validates confidence range and definition."""
       prov = Provenance("user:alice", datetime.now(), "user_clarification")

       # Valid
       ts = TermSense(
           surface=TermSurface("workspace"),
           scope="team_domain",
           definition="Git worktree directory",
           provenance=prov,
           confidence=0.9,
       )
       assert ts.confidence == 0.9

       # Invalid confidence
       with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
           TermSense(
               surface=TermSurface("workspace"),
               scope="team_domain",
               definition="Git worktree directory",
               provenance=prov,
               confidence=1.5,  # Out of range
           )

       # Empty definition
       with pytest.raises(ValueError, match="Definition cannot be empty"):
           TermSense(
               surface=TermSurface("workspace"),
               scope="team_domain",
               definition="",  # Empty
               provenance=prov,
               confidence=0.9,
           )

   def test_semantic_conflict_validation():
       """SemanticConflict validates AMBIGUOUS must have candidates."""
       ts = TermSurface("workspace")

       # Valid AMBIGUOUS with candidates
       sc = SemanticConflict(
           term=ts,
           conflict_type=ConflictType.AMBIGUOUS,
           severity=Severity.HIGH,
           confidence=0.9,
           candidate_senses=[
               SenseRef("workspace", "team_domain", "Git worktree", 0.9),
               SenseRef("workspace", "team_domain", "VS Code workspace", 0.7),
           ],
       )
       assert len(sc.candidate_senses) == 2

       # Invalid: AMBIGUOUS without candidates
       with pytest.raises(ValueError, match="AMBIGUOUS conflict must have candidate_senses"):
           SemanticConflict(
               term=ts,
               conflict_type=ConflictType.AMBIGUOUS,
               severity=Severity.HIGH,
               confidence=0.9,
               candidate_senses=[],  # Empty
           )

       # UNKNOWN without candidates is OK
       sc2 = SemanticConflict(
           term=ts,
           conflict_type=ConflictType.UNKNOWN,
           severity=Severity.MEDIUM,
           confidence=0.7,
           candidate_senses=[],
       )
       assert len(sc2.candidate_senses) == 0
   ```

**Files modified**:
- `src/specify_cli/glossary/models.py` (~150 lines)
- `tests/specify_cli/glossary/test_models.py` (~80 lines)

**Validation**:
- [ ] Can create TermSurface with normalized text
- [ ] TermSurface rejects non-normalized text
- [ ] TermSense validates confidence range (0.0-1.0)
- [ ] TermSense validates definition not empty
- [ ] SemanticConflict validates AMBIGUOUS has candidates
- [ ] Serialization helpers produce valid dicts
- [ ] All tests pass: `pytest tests/specify_cli/glossary/test_models.py -v`

---

### Subtask T003: Define exception hierarchy

**Purpose**: Create GlossaryError base class with specific exceptions for blocking, deferral, and abort scenarios.

**Steps**:

1. **Create exceptions.py**:

   ```python
   """Exception hierarchy for glossary semantic integrity."""

   from typing import List, TYPE_CHECKING

   if TYPE_CHECKING:
       from .models import SemanticConflict


   class GlossaryError(Exception):
       """Base exception for glossary errors."""
       pass


   class BlockedByConflict(GlossaryError):
       """Generation blocked by unresolved high-severity conflict."""

       def __init__(self, conflicts: List["SemanticConflict"]):
           self.conflicts = conflicts
           conflict_count = len(conflicts)
           super().__init__(
               f"Generation blocked by {conflict_count} semantic conflict(s). "
               f"Resolve conflicts or use --strictness off to bypass."
           )


   class DeferredToAsync(GlossaryError):
       """User deferred conflict resolution to async mode."""

       def __init__(self, conflict_id: str):
           self.conflict_id = conflict_id
           super().__init__(
               f"Conflict {conflict_id} deferred to async resolution. "
               f"Generation remains blocked. Resolve via CLI or SaaS decision inbox."
           )


   class AbortResume(GlossaryError):
       """User aborted resume (context changed)."""

       def __init__(self, reason: str):
           self.reason = reason
           super().__init__(f"Resume aborted: {reason}")
   ```

2. **Add exception tests** (in `tests/specify_cli/glossary/test_exceptions.py`):

   ```python
   import pytest
   from specify_cli.glossary.exceptions import (
       GlossaryError,
       BlockedByConflict,
       DeferredToAsync,
       AbortResume,
   )
   from specify_cli.glossary.models import (
       SemanticConflict, TermSurface, ConflictType, Severity,
   )

   def test_blocked_by_conflict():
       """BlockedByConflict stores conflicts and formats message."""
       conflicts = [
           SemanticConflict(
               term=TermSurface("workspace"),
               conflict_type=ConflictType.AMBIGUOUS,
               severity=Severity.HIGH,
               confidence=0.9,
           ),
       ]

       exc = BlockedByConflict(conflicts)
       assert exc.conflicts == conflicts
       assert "1 semantic conflict" in str(exc)
       assert "--strictness off" in str(exc)

   def test_deferred_to_async():
       """DeferredToAsync stores conflict_id."""
       exc = DeferredToAsync("uuid-1234-5678")
       assert exc.conflict_id == "uuid-1234-5678"
       assert "uuid-1234-5678" in str(exc)
       assert "deferred to async" in str(exc)

   def test_abort_resume():
       """AbortResume stores reason."""
       exc = AbortResume("Input hash mismatch")
       assert exc.reason == "Input hash mismatch"
       assert "Input hash mismatch" in str(exc)

   def test_exception_hierarchy():
       """All glossary exceptions inherit from GlossaryError."""
       assert issubclass(BlockedByConflict, GlossaryError)
       assert issubclass(DeferredToAsync, GlossaryError)
       assert issubclass(AbortResume, GlossaryError)
   ```

**Files created**:
- `src/specify_cli/glossary/exceptions.py` (~40 lines)
- `tests/specify_cli/glossary/test_exceptions.py` (~50 lines)

**Validation**:
- [ ] BlockedByConflict stores conflicts list
- [ ] DeferredToAsync stores conflict_id
- [ ] AbortResume stores reason
- [ ] All exceptions inherit from GlossaryError
- [ ] Error messages are actionable
- [ ] All tests pass: `pytest tests/specify_cli/glossary/test_exceptions.py -v`

---

### Subtask T004: Set up test infrastructure

**Purpose**: Create pytest fixtures and mocks for common test scenarios (PrimitiveExecutionContext, event log, etc.).

**Steps**:

1. **Create conftest.py** with shared fixtures:

   ```python
   """Pytest fixtures for glossary tests."""

   import pytest
   from unittest.mock import MagicMock
   from datetime import datetime
   from specify_cli.glossary.models import (
       TermSurface, TermSense, Provenance, SenseStatus,
   )


   @pytest.fixture
   def sample_term_surface():
       """Sample TermSurface for testing."""
       return TermSurface("workspace")


   @pytest.fixture
   def sample_provenance():
       """Sample Provenance for testing."""
       return Provenance(
           actor_id="user:alice",
           timestamp=datetime(2026, 2, 16, 12, 0, 0),
           source="user_clarification",
       )


   @pytest.fixture
   def sample_term_sense(sample_term_surface, sample_provenance):
       """Sample TermSense for testing."""
       return TermSense(
           surface=sample_term_surface,
           scope="team_domain",
           definition="Git worktree directory for a work package",
           provenance=sample_provenance,
           confidence=0.9,
           status=SenseStatus.ACTIVE,
       )


   @pytest.fixture
   def mock_primitive_context():
       """Mock PrimitiveExecutionContext for testing."""
       context = MagicMock()
       context.inputs = {"description": "The workspace contains files"}
       context.metadata = {
           "glossary_check": "enabled",
           "glossary_watch_terms": ["workspace", "mission"],
       }
       context.strictness = "medium"
       context.extracted_terms = []
       context.conflicts = []
       return context


   @pytest.fixture
   def mock_event_log(tmp_path):
       """Mock event log directory for testing."""
       event_log_path = tmp_path / "events"
       event_log_path.mkdir()
       return event_log_path


   @pytest.fixture
   def sample_seed_file(tmp_path):
       """Sample team_domain.yaml seed file for testing."""
       glossaries_path = tmp_path / ".kittify" / "glossaries"
       glossaries_path.mkdir(parents=True)

       seed_content = """
   terms:
     - surface: workspace
       definition: Git worktree directory for a work package
       confidence: 1.0
       status: active

     - surface: mission
       definition: Purpose-specific workflow machine
       confidence: 1.0
       status: active
   """
       seed_file = glossaries_path / "team_domain.yaml"
       seed_file.write_text(seed_content)
       return seed_file
   ```

2. **Add helper functions** for test data generation:

   ```python
   from typing import List
   from specify_cli.glossary.models import (
       SemanticConflict, ConflictType, Severity, SenseRef,
   )


   def make_conflict(
       surface_text: str,
       conflict_type: ConflictType = ConflictType.AMBIGUOUS,
       severity: Severity = Severity.HIGH,
       candidates: List[SenseRef] = None,
   ) -> SemanticConflict:
       """Helper to create SemanticConflict for testing."""
       if candidates is None and conflict_type == ConflictType.AMBIGUOUS:
           # Default candidates for ambiguous conflicts
           candidates = [
               SenseRef(surface_text, "team_domain", f"Definition 1 of {surface_text}", 0.9),
               SenseRef(surface_text, "team_domain", f"Definition 2 of {surface_text}", 0.7),
           ]

       return SemanticConflict(
           term=TermSurface(surface_text),
           conflict_type=conflict_type,
           severity=severity,
           confidence=0.9,
           candidate_senses=candidates or [],
           context="test context",
       )
   ```

**Files modified**:
- `tests/specify_cli/glossary/conftest.py` (~80 lines)

**Validation**:
- [ ] Fixtures import successfully
- [ ] sample_term_surface creates valid TermSurface
- [ ] mock_primitive_context has expected attributes
- [ ] sample_seed_file creates valid YAML file
- [ ] make_conflict helper works for all conflict types

---

### Subtask T005: Implement GlossaryScope enum with resolution order

**Purpose**: Create GlossaryScope enum and helper functions for scope precedence.

**Steps**:

1. **Create scope.py**:

   ```python
   """GlossaryScope enum and scope resolution utilities."""

   from enum import Enum
   from typing import List


   class GlossaryScope(Enum):
       """Glossary scope levels in the hierarchy."""
       MISSION_LOCAL = "mission_local"
       TEAM_DOMAIN = "team_domain"
       AUDIENCE_DOMAIN = "audience_domain"
       SPEC_KITTY_CORE = "spec_kitty_core"


   # Resolution order (highest to lowest precedence)
   SCOPE_RESOLUTION_ORDER: List[GlossaryScope] = [
       GlossaryScope.MISSION_LOCAL,
       GlossaryScope.TEAM_DOMAIN,
       GlossaryScope.AUDIENCE_DOMAIN,
       GlossaryScope.SPEC_KITTY_CORE,
   ]


   def get_scope_precedence(scope: GlossaryScope) -> int:
       """
       Get numeric precedence for a scope (lower number = higher precedence).

       Args:
           scope: GlossaryScope enum value

       Returns:
           Precedence integer (0 = highest precedence)
       """
       try:
           return SCOPE_RESOLUTION_ORDER.index(scope)
       except ValueError:
           # Unknown scope defaults to lowest precedence
           return len(SCOPE_RESOLUTION_ORDER)


   def should_use_scope(scope: GlossaryScope, configured_scopes: List[GlossaryScope]) -> bool:
       """
       Check if a scope should be used in resolution.

       Args:
           scope: Scope to check
           configured_scopes: List of active scopes

       Returns:
           True if scope is configured and should be used
       """
       return scope in configured_scopes
   ```

2. **Add scope tests** (in `tests/specify_cli/glossary/test_scope.py`):

   ```python
   import pytest
   from specify_cli.glossary.scope import (
       GlossaryScope,
       SCOPE_RESOLUTION_ORDER,
       get_scope_precedence,
       should_use_scope,
   )

   def test_scope_resolution_order():
       """SCOPE_RESOLUTION_ORDER is correct."""
       assert SCOPE_RESOLUTION_ORDER == [
           GlossaryScope.MISSION_LOCAL,
           GlossaryScope.TEAM_DOMAIN,
           GlossaryScope.AUDIENCE_DOMAIN,
           GlossaryScope.SPEC_KITTY_CORE,
       ]

   def test_get_scope_precedence():
       """get_scope_precedence returns correct precedence."""
       assert get_scope_precedence(GlossaryScope.MISSION_LOCAL) == 0  # Highest
       assert get_scope_precedence(GlossaryScope.TEAM_DOMAIN) == 1
       assert get_scope_precedence(GlossaryScope.AUDIENCE_DOMAIN) == 2
       assert get_scope_precedence(GlossaryScope.SPEC_KITTY_CORE) == 3  # Lowest

   def test_should_use_scope():
       """should_use_scope checks if scope is configured."""
       configured = [GlossaryScope.MISSION_LOCAL, GlossaryScope.SPEC_KITTY_CORE]

       assert should_use_scope(GlossaryScope.MISSION_LOCAL, configured) is True
       assert should_use_scope(GlossaryScope.SPEC_KITTY_CORE, configured) is True
       assert should_use_scope(GlossaryScope.TEAM_DOMAIN, configured) is False
       assert should_use_scope(GlossaryScope.AUDIENCE_DOMAIN, configured) is False
   ```

**Files created**:
- `src/specify_cli/glossary/scope.py` (~40 lines)
- `tests/specify_cli/glossary/test_scope.py` (~30 lines)

**Validation**:
- [ ] GlossaryScope has 4 enum values
- [ ] SCOPE_RESOLUTION_ORDER is correct
- [ ] get_scope_precedence returns 0-3
- [ ] should_use_scope filters correctly
- [ ] All tests pass: `pytest tests/specify_cli/glossary/test_scope.py -v`

---

## Definition of Done

**Code Complete**:
- [ ] All 5 subtasks implemented (T001-T005)
- [ ] Package structure created with 12 module files
- [ ] Core data models defined (TermSurface, TermSense, SemanticConflict)
- [ ] Exception hierarchy implemented (GlossaryError + 3 subclasses)
- [ ] GlossaryScope enum with resolution order
- [ ] Test infrastructure with fixtures and mocks

**Tests**:
- [ ] test_models.py: 3 tests passing (TermSurface, TermSense, SemanticConflict validation)
- [ ] test_exceptions.py: 4 tests passing (exception behavior)
- [ ] test_scope.py: 3 tests passing (scope precedence)
- [ ] All tests pass: `pytest tests/specify_cli/glossary/ -v`
- [ ] mypy --strict passes for all glossary modules

**Documentation**:
- [ ] Docstrings on all public classes and functions
- [ ] Type annotations on all functions (mypy --strict compliant)
- [ ] README.md in glossary package (optional)

**Integration**:
- [ ] Package imports successfully: `python -c "import specify_cli.glossary"`
- [ ] No circular import errors
- [ ] pytest-cov reports >90% coverage for this WP's code

---

## Testing Strategy

**Unit tests**:
- Data model validation (normalization, ranges, required fields)
- Exception behavior (message formatting, attribute storage)
- Scope precedence calculation

**No integration tests yet** (no dependencies on other components).

**Test commands**:
```bash
# Run all glossary tests
pytest tests/specify_cli/glossary/ -v

# Run specific test files
pytest tests/specify_cli/glossary/test_models.py -v
pytest tests/specify_cli/glossary/test_exceptions.py -v
pytest tests/specify_cli/glossary/test_scope.py -v

# Check coverage
pytest tests/specify_cli/glossary/ --cov=src/specify_cli/glossary --cov-report=term-missing

# Type check
mypy src/specify_cli/glossary/ --strict
```

---

## Risks & Mitigations

**Risk**: None (data model definitions are straightforward)

**Risk**: Type annotation complexity with TYPE_CHECKING imports
**Mitigation**: Use TYPE_CHECKING block for circular imports (see exceptions.py example)

---

## Reviewer Guidance

**Focus areas**:
1. **Data model validation**: Verify TermSurface rejects non-normalized text, TermSense validates confidence/definition
2. **Exception messages**: Ensure error messages are actionable (include next steps)
3. **Type annotations**: Check all functions have complete type hints (mypy --strict compliant)
4. **Test fixtures**: Verify fixtures are reusable and don't couple tests

**How to verify**:
1. Run tests: `pytest tests/specify_cli/glossary/ -v` (all should pass)
2. Run type check: `mypy src/specify_cli/glossary/ --strict` (no errors)
3. Check coverage: `pytest --cov=src/specify_cli/glossary --cov-report=html` (>90%)
4. Import test: `python -c "from specify_cli.glossary import TermSurface, SemanticConflict"` (no errors)

**Acceptance checklist**:
- [ ] All 10 tests pass
- [ ] mypy --strict passes
- [ ] Coverage >90%
- [ ] No circular imports
- [ ] Docstrings present on all public APIs

---

## Next Steps

After WP01 completion:
- **WP02**: Scope Management & Storage (depends on WP01 models)
- **WP03**: Term Extraction (depends on WP01 models, can run parallel with WP02)

## Activity Log

- 2026-02-16T13:13:00Z – claude-sonnet – shell_pid=16885 – lane=doing – Assigned agent via workflow command
- 2026-02-16T13:17:03Z – claude-sonnet – shell_pid=16885 – lane=for_review – Ready for review: Foundation and data models complete. All 10 tests passing with 94% coverage. Core models (TermSurface, TermSense, SemanticConflict), exceptions, and GlossaryScope implemented.
- 2026-02-16T13:31:57Z – codex – shell_pid=29815 – lane=doing – Started review via workflow command
- 2026-02-16T13:33:41Z – codex – shell_pid=29815 – lane=planned – Moved to planned
- 2026-02-16T13:42:22Z – claude-sonnet – shell_pid=36474 – lane=doing – Started implementation via workflow command
- 2026-02-16T13:45:31Z – claude-sonnet – shell_pid=36474 – lane=for_review – Fixed Codex feedback: Added dict[str, Any] type annotations and serialization helper tests. All 13 tests passing, mypy --strict clean.
