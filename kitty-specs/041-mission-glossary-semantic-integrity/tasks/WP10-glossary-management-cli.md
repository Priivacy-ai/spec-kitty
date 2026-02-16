---
work_package_id: WP10
title: Glossary Management CLI
lane: "done"
dependencies: []
base_branch: 041-mission-glossary-semantic-integrity-WP09
base_commit: 982caa3a76885020cadacef5107c105f50b42454
created_at: '2026-02-16T17:59:56.173426+00:00'
subtasks: [T044, T045, T046, T047]
shell_pid: "82698"
agent: "codex"
review_status: "acknowledged"
reviewed_by: "Robert Douglass"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package Prompt: WP10 -- Glossary Management CLI

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-16

**Issue 1**: Deprecated glossary senses are coerced to draft, so the CLI never shows or filters them as deprecated. In `src/specify_cli/glossary/scope.py:105-116` and `src/specify_cli/cli/commands/glossary.py:93-106`, any status other than "active" is forced to `SenseStatus.DRAFT`. This drops the `deprecated` state defined in `TermSense` and advertised in `--status` help, so a term marked `status: deprecated` (in seeds or `GlossarySenseUpdated` events) will render as `draft` and `--status deprecated` always returns empty. Please map status strings to all three enum values (`active`, `draft`, `deprecated`) for seeds and event replay, and add a regression test to ensure `glossary list --status deprecated` surfaces deprecated terms.


## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Implement CLI commands for glossary management that enable users to list terms across all scopes, view conflict history, resolve conflicts asynchronously, and inspect glossary state for debugging and auditing purposes.

**Success Criteria**:
1. `spec-kitty glossary list` displays all terms from all active scopes in a Rich table with scope, surface, definition, status, and confidence columns.
2. `spec-kitty glossary list --scope team_domain` filters output to show only terms from the specified scope.
3. `spec-kitty glossary conflicts` displays conflict history from event log with term, type, severity, status (unresolved/resolved), and timestamp columns.
4. `spec-kitty glossary conflicts --mission software-dev` filters conflicts to specific mission only.
5. `spec-kitty glossary resolve <conflict_id>` prompts user for resolution (same interactive flow as clarification middleware), updates glossary, and emits GlossaryClarificationResolved event.
6. All commands output Rich-formatted tables with proper alignment, colors (severity-based for conflicts), and column headers.
7. Command-line tests verify all CLI operations using CliRunner from Typer with mocked event log and glossary store.

## Context & Constraints

**Architecture References**:
- `plan.md` CLI commands section: glossary management operations
- `contracts/events.md` defines canonical events for conflict resolution
- `data-model.md` defines GlossaryScope, TermSense, SemanticConflict entities
- `spec.md` FR-009: System MUST allow users to defer conflict resolution to async mode

**Dependency Artifacts Available** (from completed WPs):
- WP01 provides `glossary/models.py` with entity classes (TermSurface, TermSense, SemanticConflict)
- WP02 provides `glossary/scope.py` with GlossaryStore for term lookup
- WP05 provides `glossary/strictness.py` with Strictness and Severity enums
- WP08 provides `glossary/events.py` with event emission helpers
- WP09 provides `glossary/pipeline.py` with full middleware integration

**Constraints**:
- Python 3.11+ only (per constitution requirement)
- Use typer for CLI commands (existing spec-kitty dependency)
- Use Rich for table formatting (existing spec-kitty dependency)
- No new external dependencies
- Commands must read from event log (no side-channel state)
- All output must be machine-parseable (consider --json flag for scripting)
- Performance: `glossary list` should execute < 500ms for 1000+ terms

**Implementation Command**: `spec-kitty implement WP10 --base WP09`

## Subtasks & Detailed Guidance

### T044: Implement `glossary list` Command

**Purpose**: Create a CLI command to list all terms across all active scopes with Rich table formatting.

**Steps**:
1. Create `src/specify_cli/cli/commands/glossary.py`:

2. Implement the `glossary list` command:
   ```python
   import typer
   from pathlib import Path
   from typing import Optional
   from rich.console import Console
   from rich.table import Table
   from specify_cli.glossary.scope import GlossaryStore, GlossaryScope
   from specify_cli.glossary.models import TermSense

   app = typer.Typer(help="Glossary management commands")
   console = Console()

   @app.command()
   def list(
       scope: Optional[str] = typer.Option(
           None,
           "--scope",
           help="Filter by scope (mission_local, team_domain, audience_domain, spec_kitty_core)",
       ),
       status: Optional[str] = typer.Option(
           None,
           "--status",
           help="Filter by status (active, deprecated, draft)",
       ),
       json: bool = typer.Option(
           False,
           "--json",
           help="Output as JSON (machine-parseable)",
       ),
   ):
       """List all terms in glossary."""
       repo_root = Path.cwd()

       # Load glossary store
       glossary_store = GlossaryStore.from_repo_root(repo_root)

       # Get all terms
       all_terms = glossary_store.get_all_terms(
           scope_filter=GlossaryScope(scope) if scope else None,
           status_filter=status,
       )

       # JSON output for scripting
       if json:
           import json as json_lib
           output = [
               {
                   "surface": term.surface.surface_text,
                   "scope": term.scope.value,
                   "definition": term.definition,
                   "status": term.status.value,
                   "confidence": term.confidence,
               }
               for term in all_terms
           ]
           console.print(json_lib.dumps(output, indent=2))
           return

       # Rich table output
       table = Table(title="Glossary Terms")
       table.add_column("Scope", style="cyan")
       table.add_column("Term", style="bold")
       table.add_column("Definition")
       table.add_column("Status", style="yellow")
       table.add_column("Confidence", justify="right")

       for term in all_terms:
           status_style = {
               "active": "green",
               "deprecated": "red",
               "draft": "yellow",
           }.get(term.status.value, "white")

           table.add_row(
               term.scope.value,
               term.surface.surface_text,
               term.definition[:60] + "..." if len(term.definition) > 60 else term.definition,
               f"[{status_style}]{term.status.value}[/{status_style}]",
               f"{term.confidence:.2f}",
           )

       console.print(table)
       console.print(f"\n[dim]Total: {len(all_terms)} term(s)[/dim]")
   ```

3. Add helper to GlossaryStore for retrieving all terms:
   ```python
   # In src/specify_cli/glossary/scope.py

   class GlossaryStore:
       # ... (existing methods)

       def get_all_terms(
           self,
           scope_filter: Optional[GlossaryScope] = None,
           status_filter: Optional[str] = None,
       ) -> List[TermSense]:
           """Retrieve all terms from active scopes.

           Args:
               scope_filter: Filter to specific scope (None = all scopes)
               status_filter: Filter by status (active/deprecated/draft)

           Returns:
               List of TermSense objects matching filters
           """
           terms = []

           # Determine scopes to query
           scopes = [scope_filter] if scope_filter else list(GlossaryScope)

           for scope in scopes:
               scope_terms = self._load_scope_terms(scope)

               # Apply status filter
               if status_filter:
                   scope_terms = [
                       t for t in scope_terms
                       if t.status.value == status_filter
                   ]

               terms.extend(scope_terms)

           # Sort by scope precedence, then alphabetically by surface
           terms.sort(key=lambda t: (t.scope.value, t.surface.surface_text))

           return terms
   ```

4. Register glossary command group in main CLI:
   ```python
   # In src/specify_cli/cli/main.py

   from specify_cli.cli.commands import glossary

   app.add_typer(glossary.app, name="glossary")
   ```

**Files**:
- `src/specify_cli/cli/commands/glossary.py` (new file, ~100 lines)
- `src/specify_cli/glossary/scope.py` (add get_all_terms method, ~30 lines)
- `src/specify_cli/cli/main.py` (register glossary command group, ~2 lines)

**Validation**:
- [ ] `spec-kitty glossary list` displays all terms from all scopes
- [ ] `--scope team_domain` filters to only team_domain terms
- [ ] `--status active` filters to only active terms
- [ ] `--json` flag outputs machine-parseable JSON
- [ ] Rich table has proper formatting (colors, alignment, truncation)
- [ ] Total count is displayed at bottom
- [ ] Command executes < 500ms for 1000+ terms

**Edge Cases**:
- No terms in glossary: display "No terms found" message
- Invalid --scope value: typer should reject with validation error
- Glossary store not initialized: display error message with setup instructions
- Definition > 60 chars: truncate with ellipsis in table (full definition in --json)
- Multiple terms with same surface in different scopes: all shown, sorted by scope precedence

---

### T045: Implement `glossary conflicts` Command

**Purpose**: Create a CLI command to display conflict history from the event log with filtering and Rich table formatting.

**Steps**:
1. Add `conflicts` command to `glossary.py`:
   ```python
   from specify_cli.glossary.events import read_events

   @app.command()
   def conflicts(
       mission: Optional[str] = typer.Option(
           None,
           "--mission",
           help="Filter conflicts by mission ID",
       ),
       unresolved_only: bool = typer.Option(
           False,
           "--unresolved",
           help="Show only unresolved conflicts",
       ),
       json: bool = typer.Option(
           False,
           "--json",
           help="Output as JSON (machine-parseable)",
       ),
   ):
       """Display conflict history from event log."""
       repo_root = Path.cwd()

       # Read events from log
       events = read_events(repo_root)

       # Extract conflict events
       conflict_events = []
       resolved_conflict_ids = set()

       for event in events:
           if event["event_type"] == "SemanticCheckEvaluated":
               # Extract conflicts from findings
               if event.get("blocked"):
                   for finding in event.get("findings", []):
                       conflict_events.append({
                           "conflict_id": event["step_id"] + "-" + finding["term"],
                           "term": finding["term"],
                           "type": finding["conflict_type"],
                           "severity": finding["severity"],
                           "mission_id": event.get("mission_id"),
                           "timestamp": event["timestamp"],
                           "status": "unresolved",
                       })

           elif event["event_type"] == "GlossaryClarificationResolved":
               resolved_conflict_ids.add(event["conflict_id"])

       # Mark resolved conflicts
       for conflict in conflict_events:
           if conflict["conflict_id"] in resolved_conflict_ids:
               conflict["status"] = "resolved"

       # Apply filters
       if mission:
           conflict_events = [c for c in conflict_events if c["mission_id"] == mission]

       if unresolved_only:
           conflict_events = [c for c in conflict_events if c["status"] == "unresolved"]

       # JSON output
       if json:
           import json as json_lib
           console.print(json_lib.dumps(conflict_events, indent=2, default=str))
           return

       # Rich table output
       table = Table(title="Conflict History")
       table.add_column("Conflict ID", style="dim")
       table.add_column("Term", style="bold")
       table.add_column("Type")
       table.add_column("Severity")
       table.add_column("Status")
       table.add_column("Mission", style="cyan")
       table.add_column("Timestamp")

       for conflict in conflict_events:
           severity_style = {
               "high": "red",
               "medium": "yellow",
               "low": "green",
           }.get(conflict["severity"], "white")

           status_style = {
               "resolved": "green",
               "unresolved": "red",
           }.get(conflict["status"], "white")

           table.add_row(
               conflict["conflict_id"][:20] + "..." if len(conflict["conflict_id"]) > 20 else conflict["conflict_id"],
               conflict["term"],
               conflict["type"],
               f"[{severity_style}]{conflict['severity']}[/{severity_style}]",
               f"[{status_style}]{conflict['status']}[/{status_style}]",
               conflict["mission_id"],
               conflict["timestamp"][:19],  # Truncate to YYYY-MM-DD HH:MM:SS
           )

       console.print(table)
       console.print(f"\n[dim]Total: {len(conflict_events)} conflict(s)[/dim]")

       # Summary statistics
       unresolved_count = len([c for c in conflict_events if c["status"] == "unresolved"])
       if unresolved_count > 0:
           console.print(f"[red]Unresolved: {unresolved_count}[/red]")
   ```

2. Add helper to events module for reading event log:
   ```python
   # In src/specify_cli/glossary/events.py

   from pathlib import Path
   import json

   def read_events(repo_root: Path) -> List[dict]:
       """Read all events from event log.

       Args:
           repo_root: Path to repository root

       Returns:
           List of event dicts (parsed from JSONL)
       """
       event_log = repo_root / ".kittify" / "events.jsonl"

       if not event_log.exists():
           return []

       events = []
       with event_log.open("r") as f:
           for line in f:
               if line.strip():
                   events.append(json.loads(line))

       return events
   ```

**Files**:
- `src/specify_cli/cli/commands/glossary.py` (add conflicts command, ~80 lines)
- `src/specify_cli/glossary/events.py` (add read_events helper, ~20 lines)

**Validation**:
- [ ] `spec-kitty glossary conflicts` displays all conflicts from event log
- [ ] `--mission software-dev` filters to specific mission
- [ ] `--unresolved` shows only unresolved conflicts
- [ ] `--json` outputs machine-parseable JSON
- [ ] Severity column has color coding (high=red, medium=yellow, low=green)
- [ ] Status column has color coding (resolved=green, unresolved=red)
- [ ] Summary shows total and unresolved count

**Edge Cases**:
- No conflicts in event log: display "No conflicts found" message
- Event log doesn't exist: display "No event log found" (graceful fallback)
- Malformed JSONL: skip invalid lines, log warning
- Conflict resolved multiple times: show latest resolution status
- Same term conflicts in different missions: all shown, grouped by mission_id

---

### T046: Implement `glossary resolve` Command

**Purpose**: Create a CLI command for asynchronous conflict resolution that prompts user interactively (reusing clarification middleware logic).

**Steps**:
1. Add `resolve` command to `glossary.py`:
   ```python
   from specify_cli.glossary.clarification import ClarificationMiddleware
   from specify_cli.glossary.models import SemanticConflict, ConflictType, Severity

   @app.command()
   def resolve(
       conflict_id: str = typer.Argument(..., help="Conflict ID to resolve"),
   ):
       """Resolve a conflict asynchronously."""
       repo_root = Path.cwd()

       # Read events to find conflict details
       events = read_events(repo_root)
       conflict_event = None

       for event in events:
           if event["event_type"] == "SemanticCheckEvaluated":
               if event.get("blocked"):
                   for finding in event.get("findings", []):
                       # Match conflict by ID
                       cid = event["step_id"] + "-" + finding["term"]
                       if cid == conflict_id:
                           conflict_event = finding
                           break

       if not conflict_event:
           console.print(f"[red]Error: Conflict {conflict_id} not found[/red]")
           raise typer.Exit(1)

       # Check if already resolved
       resolved = any(
           e["event_type"] == "GlossaryClarificationResolved" and e["conflict_id"] == conflict_id
           for e in events
       )

       if resolved:
           console.print(f"[yellow]Warning: Conflict {conflict_id} already resolved[/yellow]")
           if not typer.confirm("Resolve again?"):
               raise typer.Exit(0)

       # Reconstruct SemanticConflict object
       conflict = SemanticConflict(
           term=TermSurface(conflict_event["term"]),
           conflict_type=ConflictType(conflict_event["conflict_type"]),
           severity=Severity(conflict_event["severity"]),
           confidence=conflict_event["confidence"],
           candidate_senses=[
               # Convert candidate senses from event payload
               TermSense(
                   surface=TermSurface(cs["surface"]),
                   scope=GlossaryScope(cs["scope"]),
                   definition=cs["definition"],
                   confidence=cs["confidence"],
                   status=SenseStatus.ACTIVE,
                   provenance=None,  # Not needed for resolution
               )
               for cs in conflict_event.get("candidate_senses", [])
           ],
           context=conflict_event.get("context", ""),
       )

       # Use clarification middleware to prompt user
       clarification_mw = ClarificationMiddleware(interaction_mode="interactive")

       # Create minimal context
       from specify_cli.missions.primitives import PrimitiveExecutionContext
       context = PrimitiveExecutionContext(
           step_id="async-resolve",
           mission_id="glossary-cli",
           run_id="cli-session",
           inputs={},
           metadata={},
           config={},
       )
       context.conflicts = [conflict]

       try:
           # Process through clarification (will prompt user)
           result = clarification_mw.process(context)

           console.print("[green]✓ Conflict resolved successfully[/green]")

       except DeferredToAsync:
           console.print("[yellow]Conflict deferred (no resolution made)[/yellow]")
           raise typer.Exit(0)
   ```

**Files**:
- `src/specify_cli/cli/commands/glossary.py` (add resolve command, ~90 lines)

**Validation**:
- [ ] `spec-kitty glossary resolve <conflict_id>` prompts user interactively
- [ ] User can select candidate sense (1..N)
- [ ] User can provide custom sense (C)
- [ ] User can defer resolution (D)
- [ ] GlossaryClarificationResolved event is emitted on successful resolution
- [ ] GlossarySenseUpdated event is emitted if custom sense provided
- [ ] Already-resolved conflicts show warning and prompt for confirmation

**Edge Cases**:
- Conflict ID doesn't exist: display error message, exit 1
- Conflict already resolved: show warning, prompt to re-resolve
- No candidate senses available: prompt for custom sense only (no numbered options)
- Event log doesn't exist: display error with setup instructions
- User cancels prompt (Ctrl+C): clean exit, no partial state

---

### T047: CLI Command Tests

**Purpose**: Write comprehensive tests for all glossary CLI commands using CliRunner and mocked event log.

**Steps**:
1. Create `tests/specify_cli/cli/commands/test_glossary.py`:

2. Implement test fixtures:
   ```python
   import pytest
   from pathlib import Path
   from typer.testing import CliRunner
   from specify_cli.cli.main import app

   runner = CliRunner()

   @pytest.fixture
   def mock_glossary_store(tmp_path, monkeypatch):
       """Create mock glossary store with test data."""
       repo_root = tmp_path
       glossaries_dir = repo_root / ".kittify" / "glossaries"
       glossaries_dir.mkdir(parents=True)

       # Create team_domain seed file
       team_domain = glossaries_dir / "team_domain.yaml"
       team_domain.write_text("""
       terms:
         - surface: workspace
           senses:
             - definition: Git worktree directory
               confidence: 0.9
               status: active
         - surface: mission
           senses:
             - definition: Software development workflow
               confidence: 1.0
               status: active
       """)

       return repo_root

   @pytest.fixture
   def mock_event_log(tmp_path):
       """Create mock event log with conflict events."""
       repo_root = tmp_path
       event_log = repo_root / ".kittify" / "events.jsonl"
       event_log.parent.mkdir(exist_ok=True)

       # Write test events
       events = [
           {
               "event_type": "SemanticCheckEvaluated",
               "step_id": "test-001",
               "mission_id": "software-dev",
               "timestamp": "2026-02-16T12:00:00Z",
               "blocked": True,
               "findings": [
                   {
                       "term": "workspace",
                       "conflict_type": "ambiguous",
                       "severity": "high",
                       "confidence": 0.9,
                       "candidate_senses": [
                           {"surface": "workspace", "scope": "team_domain", "definition": "Git worktree", "confidence": 0.9},
                       ],
                       "context": "description field",
                   }
               ],
           },
           {
               "event_type": "GlossaryClarificationResolved",
               "conflict_id": "test-001-workspace",
               "term_surface": "workspace",
               "timestamp": "2026-02-16T12:05:00Z",
           },
       ]

       with event_log.open("w") as f:
           for event in events:
               f.write(json.dumps(event) + "\n")

       return repo_root
   ```

3. Write test cases:

   **Test: glossary list (all scopes)**:
   ```python
   def test_glossary_list_all_scopes(mock_glossary_store, monkeypatch):
       """Verify glossary list displays all terms."""
       monkeypatch.chdir(mock_glossary_store)

       result = runner.invoke(app, ["glossary", "list"])

       assert result.exit_code == 0
       assert "workspace" in result.stdout
       assert "mission" in result.stdout
       assert "team_domain" in result.stdout
       assert "Total: 2 term(s)" in result.stdout
   ```

   **Test: glossary list --scope filter**:
   ```python
   def test_glossary_list_scope_filter(mock_glossary_store, monkeypatch):
       """Verify --scope filter works."""
       monkeypatch.chdir(mock_glossary_store)

       result = runner.invoke(app, ["glossary", "list", "--scope", "team_domain"])

       assert result.exit_code == 0
       assert "workspace" in result.stdout
       assert "mission" in result.stdout
   ```

   **Test: glossary list --json output**:
   ```python
   def test_glossary_list_json_output(mock_glossary_store, monkeypatch):
       """Verify --json produces valid JSON."""
       monkeypatch.chdir(mock_glossary_store)

       result = runner.invoke(app, ["glossary", "list", "--json"])

       assert result.exit_code == 0
       import json
       data = json.loads(result.stdout)
       assert len(data) == 2
       assert data[0]["surface"] == "workspace"
   ```

   **Test: glossary conflicts (all)**:
   ```python
   def test_glossary_conflicts_all(mock_event_log, monkeypatch):
       """Verify conflicts command displays all conflicts."""
       monkeypatch.chdir(mock_event_log)

       result = runner.invoke(app, ["glossary", "conflicts"])

       assert result.exit_code == 0
       assert "workspace" in result.stdout
       assert "ambiguous" in result.stdout
       assert "high" in result.stdout
       assert "resolved" in result.stdout
   ```

   **Test: glossary conflicts --unresolved**:
   ```python
   def test_glossary_conflicts_unresolved_only(mock_event_log, monkeypatch):
       """Verify --unresolved filter works."""
       monkeypatch.chdir(mock_event_log)

       result = runner.invoke(app, ["glossary", "conflicts", "--unresolved"])

       assert result.exit_code == 0
       # Should be empty (all conflicts resolved in mock data)
       assert "Total: 0 conflict(s)" in result.stdout
   ```

   **Test: glossary resolve (interactive)**:
   ```python
   def test_glossary_resolve_interactive(mock_event_log, monkeypatch):
       """Verify resolve command prompts user."""
       monkeypatch.chdir(mock_event_log)

       # Mock typer.prompt to select candidate #1
       def mock_prompt(message, default=None):
           return "1"

       monkeypatch.setattr("typer.prompt", mock_prompt)

       result = runner.invoke(app, ["glossary", "resolve", "test-001-workspace"])

       assert result.exit_code == 0
       assert "resolved successfully" in result.stdout.lower()
   ```

   **Test: glossary resolve (not found)**:
   ```python
   def test_glossary_resolve_not_found(mock_event_log, monkeypatch):
       """Verify resolve handles missing conflict ID."""
       monkeypatch.chdir(mock_event_log)

       result = runner.invoke(app, ["glossary", "resolve", "invalid-id"])

       assert result.exit_code == 1
       assert "not found" in result.stdout.lower()
   ```

**Files**:
- `tests/specify_cli/cli/commands/test_glossary.py` (new file, ~250 lines)

**Validation**:
- [ ] All 7 test cases pass
- [ ] CliRunner successfully invokes all commands
- [ ] Rich table output is captured in result.stdout
- [ ] JSON output is valid and parseable
- [ ] Mocked event log is correctly read
- [ ] Interactive prompts are correctly mocked

**Edge Cases**:
- Empty glossary: "No terms found" message
- Empty event log: "No conflicts found" message
- Invalid --scope value: exit 1 with validation error
- Malformed event log: skip invalid lines gracefully
- Already resolved conflict: show warning, prompt for confirmation

---

## Test Strategy

**Unit Tests** (in `test_glossary.py`):
- Test each command with CliRunner
- Mock glossary store with test data
- Mock event log with conflict events
- Test all CLI flags (--scope, --mission, --unresolved, --json)

**Integration Tests** (manual verification recommended):
- Run commands against real `.kittify/` directory
- Verify Rich table formatting visually
- Test interactive resolve flow end-to-end

**Running Tests**:
```bash
# Unit tests
python -m pytest tests/specify_cli/cli/commands/test_glossary.py -v

# Full CLI test suite
python -m pytest tests/specify_cli/cli/ -v --cov=src/specify_cli/cli/commands/glossary
```

## Definition of Done

- [ ] 4 subtasks complete (T044-T047)
- [ ] `glossary.py`: list, conflicts, resolve commands implemented (~300 lines)
- [ ] `scope.py`: get_all_terms helper added (~30 lines)
- [ ] `events.py`: read_events helper added (~20 lines)
- [ ] CLI tests: ~250 lines covering all commands
- [ ] All tests pass with >90% coverage on glossary.py
- [ ] mypy --strict passes on all new code
- [ ] Rich table output is visually appealing (proper alignment, colors)
- [ ] JSON output is valid and machine-parseable
- [ ] All commands execute < 500ms for typical data

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Event log parsing is slow for large logs | Command execution exceeds 500ms budget | Implement pagination (--limit flag), cache event parsing, consider indexing |
| Rich table rendering breaks in non-TTY environments | Output garbled in CI/scripts | Auto-detect TTY, fallback to plain text, provide --no-color flag |
| Clarification middleware reuse causes coupling | Resolve command breaks when clarification changes | Encapsulate prompt logic in shared module, test CLI resolve independently |
| Conflict ID format is fragile | ID collisions or parsing failures | Use deterministic UUID generation, validate ID format in code |
| JSON output schema is undocumented | Breaking changes for scripts | Document schema in CLI help, consider --schema flag to print JSON schema |

## Review Guidance

When reviewing this WP, verify:
1. **Commands work correctly**:
   - `glossary list` displays all terms with proper filtering
   - `glossary conflicts` shows conflict history with status tracking
   - `glossary resolve` prompts user and updates glossary

2. **Rich table formatting is clean**:
   - Proper column alignment
   - Color coding for severity (high=red, medium=yellow, low=green)
   - Truncation for long text (definitions, conflict IDs)

3. **CLI flags work as expected**:
   - `--scope`, `--mission`, `--unresolved`, `--status` filters apply correctly
   - `--json` produces valid, parseable JSON
   - Invalid flag values trigger typer validation errors

4. **Event log integration is correct**:
   - read_events() correctly parses JSONL
   - Conflict status correctly tracks resolved/unresolved
   - Malformed events are skipped gracefully

5. **Interactive prompts are user-friendly**:
   - Clear instructions (1..N for candidates, C for custom, D for defer)
   - Confirmation prompts for already-resolved conflicts
   - Clean exit on Ctrl+C

6. **Test coverage is comprehensive**:
   - All commands tested with CliRunner
   - Edge cases covered (empty log, invalid IDs, already resolved)
   - JSON output validated

7. **No fallback mechanisms**:
   - If event log is malformed, fail clearly (don't silently skip all events)
   - If conflict ID is invalid, exit with error (don't guess)

## Activity Log

- 2026-02-16T00:00:00Z -- llm:claude-sonnet-4.5 -- lane=planned -- WP created with comprehensive guidance
- 2026-02-16T17:59:56Z – coordinator – shell_pid=63494 – lane=doing – Assigned agent via workflow command
- 2026-02-16T18:08:44Z – coordinator – shell_pid=63494 – lane=for_review – Ready for review: glossary list/conflicts/resolve commands with --strictness flag, 47 tests at 97% coverage
- 2026-02-16T18:09:15Z – codex – shell_pid=69247 – lane=doing – Started review via workflow command
- 2026-02-16T18:13:07Z – codex – shell_pid=69247 – lane=planned – Moved to planned
- 2026-02-16T18:13:38Z – coordinator – shell_pid=74163 – lane=doing – Started implementation via workflow command
- 2026-02-16T18:21:29Z – coordinator – shell_pid=74163 – lane=for_review – Fixed: event log replay in glossary list, real UUID conflict IDs, GlossarySenseUpdated emission for custom resolve. 57/57 tests pass, 8 regression tests added.
- 2026-02-16T18:22:03Z – codex – shell_pid=77836 – lane=doing – Started review via workflow command
- 2026-02-16T18:29:51Z – codex – shell_pid=77836 – lane=planned – Moved to planned
- 2026-02-16T18:31:44Z – coordinator – shell_pid=81443 – lane=doing – Started implementation via workflow command
- 2026-02-16T18:34:52Z – coordinator – shell_pid=81443 – lane=for_review – Cycle 3/3: Fixed deprecated status mapping in scope.py and glossary.py. Added _parse_sense_status() helper with explicit 3-way mapping. 4 regression tests added. 61/61 tests pass.
- 2026-02-16T18:35:16Z – codex – shell_pid=82698 – lane=doing – Started review via workflow command
- 2026-02-16T18:38:47Z – codex – shell_pid=82698 – lane=done – Review passed: deprecated status preserved; glossary CLI tests ok
