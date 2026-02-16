---
work_package_id: WP02
title: Scope Management & Storage
lane: "planned"
dependencies: []
base_branch: 041-mission-glossary-semantic-integrity-WP01
base_commit: 38b22ebffcce1b3d0095c2fbec0713eb5c370948
created_at: '2026-02-16T13:17:43.185840+00:00'
subtasks: [T006, T007, T008, T009, T048]
shell_pid: "31580"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Scope Management & Storage

**ID**: WP02
**Priority**: P1 (blocking for WP03-WP05)
**Estimated Effort**: 2-3 days

## Objective

Implement glossary scope loading, seed file parsing (YAML), scope activation with event emission, and in-memory glossary storage backed by event log.

## Context

This WP establishes the glossary storage layer. It loads seed files from `.kittify/glossaries/` (team_domain.yaml, audience_domain.yaml, spec_kitty_core.yaml), activates scopes, and provides a queryable in-memory store backed by the event log.

**Design references**:
- [data-model.md](../data-model.md) - TermSense, GlossaryScope
- [research.md](../research.md) - Scope resolution strategy
- [quickstart.md](../quickstart.md) - Seed file format examples

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

**Dependencies**: WP01 (data models, GlossaryScope enum)

---

## Subtask Breakdown

### Subtask T006: Implement seed file loader

**Purpose**: Parse YAML seed files (team_domain.yaml, audience_domain.yaml) into TermSense objects.

**Steps**:

1. **Create loader in scope.py**:
   ```python
   from pathlib import Path
   from typing import List, Optional
   from ruamel.yaml import YAML
   from .models import TermSurface, TermSense, Provenance, SenseStatus

   def load_seed_file(scope: GlossaryScope, repo_root: Path) -> List[TermSense]:
       """Load seed file for a scope."""
       seed_path = repo_root / ".kittify" / "glossaries" / f"{scope.value}.yaml"

       if not seed_path.exists():
           return []  # Skip cleanly if not configured

       yaml = YAML()
       yaml.preserve_quotes = True
       data = yaml.load(seed_path)

       senses = []
       for term_data in data.get("terms", []):
           sense = TermSense(
               surface=TermSurface(term_data["surface"]),
               scope=scope.value,
               definition=term_data["definition"],
               provenance=Provenance(
                   actor_id="system:seed_file",
                   timestamp=datetime.now(),
                   source="seed_file",
               ),
               confidence=term_data.get("confidence", 1.0),
               status=SenseStatus.ACTIVE if term_data.get("status") == "active" else SenseStatus.DRAFT,
           )
           senses.append(sense)

       return senses
   ```

2. **Add validation** for seed file schema:
   ```python
   def validate_seed_file(data: dict) -> None:
       """Validate seed file schema."""
       if "terms" not in data:
           raise ValueError("Seed file must have 'terms' key")

       for term in data["terms"]:
           if "surface" not in term:
               raise ValueError("Term must have 'surface' key")
           if "definition" not in term:
               raise ValueError("Term must have 'definition' key")
   ```

3. **Write tests** (test_seed_loader.py):
   ```python
   def test_load_seed_file(sample_seed_file, tmp_path):
       """Can load seed file and parse terms."""
       senses = load_seed_file(GlossaryScope.TEAM_DOMAIN, tmp_path)

       assert len(senses) == 2
       assert senses[0].surface.surface_text == "workspace"
       assert senses[0].definition == "Git worktree directory for a work package"
       assert senses[0].confidence == 1.0
       assert senses[0].status == SenseStatus.ACTIVE

   def test_load_seed_file_missing(tmp_path):
       """Returns empty list if seed file missing."""
       senses = load_seed_file(GlossaryScope.TEAM_DOMAIN, tmp_path)
       assert senses == []
   ```

**Files modified**:
- `src/specify_cli/glossary/scope.py` (+60 lines)
- `tests/specify_cli/glossary/test_scope.py` (+40 lines)

**Validation**:
- [ ] Can parse valid seed file
- [ ] Returns empty list if file missing (no error)
- [ ] Validates required fields (surface, definition)
- [ ] Preserves YAML comments with ruamel.yaml

---

### Subtask T007: Implement scope activation

**Purpose**: Emit GlossaryScopeActivated events when mission starts.

**Steps**:

1. **Create activation function** in scope.py:
   ```python
   def activate_scope(
       scope: GlossaryScope,
       version_id: str,
       mission_id: str,
       run_id: str,
       event_emitter,
   ) -> None:
       """Activate a glossary scope and emit event."""
       event_emitter.emit(
           event_type="GlossaryScopeActivated",
           payload={
               "scope_id": scope.value,
               "glossary_version_id": version_id,
               "mission_id": mission_id,
               "run_id": run_id,
               "timestamp": datetime.now().isoformat(),
           }
       )
   ```

2. **Write activation tests**:
   ```python
   def test_activate_scope(mock_event_emitter):
       """Emits GlossaryScopeActivated event."""
       activate_scope(
           GlossaryScope.TEAM_DOMAIN,
           version_id="v3",
           mission_id="041-mission",
           run_id="run-001",
           event_emitter=mock_event_emitter,
       )

       mock_event_emitter.emit.assert_called_once()
       call_args = mock_event_emitter.emit.call_args
       assert call_args[1]["event_type"] == "GlossaryScopeActivated"
       assert call_args[1]["payload"]["scope_id"] == "team_domain"
   ```

**Files modified**:
- `src/specify_cli/glossary/scope.py` (+20 lines)
- `tests/specify_cli/glossary/test_scope.py` (+15 lines)

**Validation**:
- [ ] Emits event with correct payload
- [ ] Event includes mission_id, run_id, scope_id, version_id

---

### Subtask T008: Implement glossary store

**Purpose**: In-memory store for active glossary, backed by event log.

**Steps**:

1. **Create GlossaryStore class** in new file `store.py`:
   ```python
   from typing import Dict, List, Optional
   from functools import lru_cache

   class GlossaryStore:
       """In-memory glossary store backed by event log."""

       def __init__(self, event_log_path: Path):
           self.event_log_path = event_log_path
           self._cache: Dict[str, Dict[str, List[TermSense]]] = {}
           # Format: {scope: {surface: [senses]}}

       def load_from_events(self) -> None:
           """Rebuild glossary from event log."""
           # Read GlossarySenseUpdated events from log
           # Populate self._cache
           pass  # WP08 will implement event reading

       def add_sense(self, sense: TermSense) -> None:
           """Add a sense to the store."""
           scope = sense.scope
           surface = sense.surface.surface_text

           if scope not in self._cache:
               self._cache[scope] = {}
           if surface not in self._cache[scope]:
               self._cache[scope][surface] = []

           self._cache[scope][surface].append(sense)

       @lru_cache(maxsize=10000)
       def lookup(self, surface: str, scopes: tuple) -> List[TermSense]:
           """Look up term in scope hierarchy."""
           results = []
           for scope in scopes:
               if scope in self._cache and surface in self._cache[scope]:
                   results.extend(self._cache[scope][surface])
           return results
   ```

2. **Write store tests**:
   ```python
   def test_glossary_store_add_lookup(sample_term_sense):
       """Can add and look up senses."""
       store = GlossaryStore(Path("/tmp/events"))
       store.add_sense(sample_term_sense)

       results = store.lookup("workspace", ("team_domain",))
       assert len(results) == 1
       assert results[0].definition == "Git worktree directory for a work package"

   def test_glossary_store_scope_order(tmp_path):
       """Lookup respects scope order."""
       store = GlossaryStore(tmp_path)

       # Add sense in team_domain
       sense1 = TermSense(
           surface=TermSurface("workspace"),
           scope="team_domain",
           definition="Team domain definition",
           provenance=Provenance("user:alice", datetime.now(), "user"),
           confidence=0.9,
       )
       store.add_sense(sense1)

       # Add sense in spec_kitty_core
       sense2 = TermSense(
           surface=TermSurface("workspace"),
           scope="spec_kitty_core",
           definition="Spec Kitty core definition",
           provenance=Provenance("system", datetime.now(), "system"),
           confidence=1.0,
       )
       store.add_sense(sense2)

       # Lookup with team_domain first (higher precedence)
       results = store.lookup("workspace", ("team_domain", "spec_kitty_core"))
       assert len(results) == 2
       assert results[0].scope == "team_domain"  # Higher precedence first
   ```

**Files created**:
- `src/specify_cli/glossary/store.py` (~80 lines)
- `tests/specify_cli/glossary/test_store.py` (~60 lines)

**Validation**:
- [ ] Can add senses to store
- [ ] Lookup returns senses in scope order
- [ ] LRU cache works (performance)
- [ ] Returns empty list if term not found

---

### Subtask T009: Write scope resolution tests

**Purpose**: Test hierarchical lookup with fallback.

**Steps**:

1. **Create comprehensive resolution tests**:
   ```python
   def test_scope_resolution_hierarchy(tmp_path):
       """Resolution follows mission_local -> team_domain -> audience_domain -> spec_kitty_core."""
       store = GlossaryStore(tmp_path)

       # Add term in spec_kitty_core (lowest precedence)
       store.add_sense(TermSense(
           surface=TermSurface("workspace"),
           scope="spec_kitty_core",
           definition="Spec Kitty core definition",
           provenance=Provenance("system", datetime.now(), "system"),
           confidence=1.0,
       ))

       # Lookup with full hierarchy
       results = store.lookup("workspace", (
           "mission_local", "team_domain", "audience_domain", "spec_kitty_core"
       ))
       assert len(results) == 1
       assert results[0].scope == "spec_kitty_core"

       # Add term in team_domain (higher precedence)
       store.add_sense(TermSense(
           surface=TermSurface("workspace"),
           scope="team_domain",
           definition="Team domain definition",
           provenance=Provenance("user:alice", datetime.now(), "user"),
           confidence=0.9,
       ))

       # Now both are found, team_domain first
       results = store.lookup("workspace", (
           "mission_local", "team_domain", "audience_domain", "spec_kitty_core"
       ))
       assert len(results) == 2
       assert results[0].scope == "team_domain"
       assert results[1].scope == "spec_kitty_core"

   def test_scope_resolution_skip_missing(tmp_path):
       """Skips scopes cleanly if not configured."""
       store = GlossaryStore(tmp_path)

       # Only add to spec_kitty_core
       store.add_sense(TermSense(
           surface=TermSurface("workspace"),
           scope="spec_kitty_core",
           definition="Definition",
           provenance=Provenance("system", datetime.now(), "system"),
           confidence=1.0,
       ))

       # Lookup with team_domain missing - should still find spec_kitty_core
       results = store.lookup("workspace", ("team_domain", "spec_kitty_core"))
       assert len(results) == 1
   ```

**Files modified**:
- `tests/specify_cli/glossary/test_store.py` (+40 lines)

**Validation**:
- [ ] Resolution follows correct order
- [ ] Skips missing scopes without error
- [ ] Returns all matching senses across scopes

---

### Subtask T048: Create spec_kitty_core.yaml seed file

**Purpose**: Canonical Spec Kitty terms seed file.

**Steps**:

1. **Create spec_kitty_core.yaml** in repo root `.kittify/glossaries/`:
   ```yaml
   # Spec Kitty Canonical Terms
   # This file defines the authoritative meanings of Spec Kitty domain concepts.

   terms:
     - surface: workspace
       definition: Git worktree directory created for implementing a work package
       confidence: 1.0
       status: active

     - surface: work package
       definition: Execution slice inside a mission run, the unit of human/agent handoff
       confidence: 1.0
       status: active

     - surface: wp
       definition: Abbreviation for work package
       confidence: 1.0
       status: active

     - surface: mission
       definition: Purpose-specific workflow machine with defined inputs, process, outcomes, and states
       confidence: 1.0
       status: active

     - surface: primitive
       definition: Custom mission-defined executable operation or step unit
       confidence: 1.0
       status: active

     - surface: phase
       definition: Grouping container for mission primitives, not the enforcement unit
       confidence: 1.0
       status: active

     - surface: lane
       definition: Kanban status for work packages (planned, in_progress, for_review, done)
       confidence: 1.0
       status: active

     - surface: strictness
       definition: Glossary enforcement mode (off, medium, max)
       confidence: 1.0
       status: active

     - surface: semantic conflict
       definition: Mismatch or ambiguity in term usage with assigned severity score
       confidence: 1.0
       status: active

     - surface: scope
       definition: Bounded semantic scope (mission_local, team_domain, audience_domain, spec_kitty_core)
       confidence: 1.0
       status: active
   ```

2. **Add to .gitignore** (preserve user's glossaries):
   ```
   # User-managed glossaries (optional)
   .kittify/glossaries/team_domain.yaml
   .kittify/glossaries/audience_domain.yaml
   .kittify/glossaries/mission_local.yaml

   # Keep spec_kitty_core.yaml tracked (canonical terms)
   !.kittify/glossaries/spec_kitty_core.yaml
   ```

**Files created**:
- `.kittify/glossaries/spec_kitty_core.yaml` (~40 lines)
- `.gitignore` (updated)

**Validation**:
- [ ] File parses with load_seed_file()
- [ ] All terms have required fields
- [ ] Definitions are clear and unambiguous

---

## Definition of Done

- [ ] All 5 subtasks complete
- [ ] Seed file loader parses YAML
- [ ] Scope activation emits events
- [ ] GlossaryStore provides lookup
- [ ] spec_kitty_core.yaml created
- [ ] Tests pass: `pytest tests/specify_cli/glossary/test_scope.py test_store.py -v`
- [ ] Coverage >90%

---

## Testing Strategy

```bash
pytest tests/specify_cli/glossary/test_scope.py -v
pytest tests/specify_cli/glossary/test_store.py -v
pytest --cov=src/specify_cli/glossary/scope --cov=src/specify_cli/glossary/store
```

---

## Reviewer Guidance

**Focus**:
1. Seed file validation (schema, required fields)
2. Store lookup correctness (scope order, fallback)
3. Event emission (GlossaryScopeActivated payload)

**Acceptance**:
- [ ] Can load seed files
- [ ] Store returns correct senses
- [ ] Scope order respected

## Activity Log

- 2026-02-16T13:17:43Z – claude-sonnet – shell_pid=20675 – lane=doing – Assigned agent via workflow command
- 2026-02-16T13:28:57Z – claude-sonnet – shell_pid=20675 – lane=for_review – Ready for review: Scope management and storage complete. Seed file loader, scope activation, GlossaryStore with hierarchy lookup, spec_kitty_core.yaml. All 19 tests passing with 96% coverage.
- 2026-02-16T13:34:26Z – codex – shell_pid=31580 – lane=doing – Started review via workflow command
- 2026-02-16T13:36:24Z – codex – shell_pid=31580 – lane=planned – Moved to planned
