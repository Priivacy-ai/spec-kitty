---
work_package_id: WP06
title: Interactive Clarification UI
lane: "planned"
dependencies: []
base_branch: 041-mission-glossary-semantic-integrity-WP05
base_commit: e123f4871b4da4d6bae8a55af3fd48f54c7d701e
created_at: '2026-02-16T15:55:53.271355+00:00'
subtasks: [T025, T026, T027, T028, T029]
shell_pid: "23165"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package Prompt: WP06 -- Interactive Clarification UI

## Review Feedback

**Reviewed by**: Robert Douglass
**Status**: ❌ Changes Requested
**Date**: 2026-02-16

**Issue 1**: Resolved conflicts stay in `context.conflicts` whenever only a subset is deferred. In `ClarificationMiddleware.process` (src/specify_cli/glossary/middleware.py:546-596) the list is only cleared when *all* conflicts are resolved; otherwise the original list (including already-resolved items) is returned. The spec says that after mixed outcomes, `context.conflicts` must contain only the remaining deferred conflicts. Keeping resolved conflicts means they will be re-rendered/re-prompted and double-counted in later middleware passes, and the deferred count no longer mirrors the actual pending set. **Fix**: Build an explicit `deferred_conflicts` list (includes beyond `max_questions` and any user-deferred) and set `context.conflicts = deferred_conflicts`; update `deferred_conflicts_count` to `len(deferred_conflicts)`, and adjust the mixed-resolution tests in `tests/specify_cli/glossary/test_clarification.py` to expect only deferred conflicts to remain.


## Review Feedback

*(No feedback yet -- this section will be populated if the WP is returned from review.)*

## Objectives & Success Criteria

**Primary Objective**: Implement the interactive clarification UI that renders ranked candidate senses with Rich formatting, prompts users with Typer for conflict resolution (select candidate, custom sense, or defer), supports non-interactive mode for CI environments, and orchestrates the full clarification flow via ClarificationMiddleware.

**Success Criteria**:
1. Conflicts are rendered as Rich tables with color-coded severity (red=high, yellow=medium, blue=low).
2. Ranked candidates are displayed in scope precedence order (mission_local → team_domain → audience_domain → spec_kitty_core), then by confidence.
3. Typer prompts accept 1-N (select candidate), C (custom sense), D (defer to async) with input validation.
4. Custom sense input captures full definition with provenance (actor, timestamp, source="user_clarification").
5. Non-interactive mode is detected via `sys.stdin.isatty()` and CI env vars (CI=true, GITHUB_ACTIONS, etc.) and auto-defers all conflicts.
6. ClarificationMiddleware orchestrates rendering, prompting, and event emission (GlossaryClarificationRequested, GlossaryClarificationResolved, GlossarySenseUpdated).
7. Integration tests verify all resolution paths (select candidate, custom sense, defer, non-interactive) with mocked Typer prompts.

## Context & Constraints

**Architecture References**:
- `spec.md` FR-008: System MUST show interactive clarification prompts with 1-3 questions maximum, prioritized by severity
- `spec.md` FR-009: System MUST allow users to defer conflict resolution to async mode
- `spec.md` FR-017: System MUST present ranked candidate senses during clarification (ordered by scope precedence, then confidence)
- `spec.md` FR-018: System MUST allow free-text custom sense input during clarification
- `plan.md` middleware pipeline architecture: ClarificationMiddleware is layer 4 of 5
- `data-model.md` defines SemanticConflict with severity (low/medium/high), candidate_senses (List[TermSense])
- `contracts/events.md` GlossaryClarificationRequested, GlossaryClarificationResolved, GlossarySenseUpdated event schemas

**Dependency Artifacts Available** (from completed WPs):
- WP01 provides `glossary/models.py` with SemanticConflict, TermSense, TermSurface, Severity enums
- WP04 provides `glossary/conflict.py` with conflict detection and candidate scoring
- WP05 provides `glossary/middleware.py` with GenerationGateMiddleware that raises `BlockedByConflict` exception

**Constraints**:
- Python 3.11+ only (per constitution requirement)
- Existing dependencies only: typer (CLI), rich (console output) - no new packages
- Prompts must be limited to 3 questions maximum per burst (spec.md SC-008)
- Non-interactive mode must never block waiting for user input (fail fast with clear error)
- Event emission must occur before glossary updates (ensure observability)
- Ranking must be deterministic (same conflicts → same candidate order every time)

**Implementation Command**: `spec-kitty implement WP06 --base WP05`

## Subtasks & Detailed Guidance

### T025: Conflict Rendering with Rich

**Purpose**: Build the Rich-based rendering system that displays semantic conflicts as formatted tables with color-coded severity, ranked candidate senses, and contextual usage information.

**Steps**:
1. Create `src/specify_cli/glossary/rendering.py`.

2. Define severity color mapping:
   ```python
   from rich.console import Console
   from rich.table import Table
   from rich.panel import Panel
   from specify_cli.glossary.models import Severity, SemanticConflict, TermSense

   SEVERITY_COLORS = {
       Severity.HIGH: "red",
       Severity.MEDIUM: "yellow",
       Severity.LOW: "blue",
   }

   SEVERITY_ICONS = {
       Severity.HIGH: "🔴",
       Severity.MEDIUM: "🟡",
       Severity.LOW: "🔵",
   }
   ```

3. Implement conflict rendering function:
   ```python
   def render_conflict(
       console: Console,
       conflict: SemanticConflict,
   ) -> None:
       """Render a single conflict with Rich formatting.

       Displays:
       - Severity icon and level (color-coded)
       - Term surface text
       - Context (usage location)
       - Ranked candidate senses (scope + definition + confidence)

       Args:
           console: Rich console instance
           conflict: Semantic conflict to render
       """
       severity_color = SEVERITY_COLORS[conflict.severity]
       severity_icon = SEVERITY_ICONS[conflict.severity]

       # Create title with severity
       title = f"{severity_icon} [{severity_color}]{conflict.severity.upper()}-severity conflict[/{severity_color}]: \"{conflict.term.surface_text}\""

       # Create table for candidates
       table = Table(show_header=True, header_style="bold magenta")
       table.add_column("#", style="cyan", width=3)
       table.add_column("Scope", style="green")
       table.add_column("Definition", style="white")
       table.add_column("Confidence", justify="right", style="yellow")

       # Add ranked candidates
       for idx, sense in enumerate(conflict.candidate_senses, start=1):
           table.add_row(
               str(idx),
               sense.scope.value,
               sense.definition,
               f"{sense.confidence:.2f}"
           )

       # Create panel with metadata
       metadata = (
           f"[bold]Term:[/bold] {conflict.term.surface_text}\n"
           f"[bold]Type:[/bold] {conflict.conflict_type.value}\n"
           f"[bold]Context:[/bold] {conflict.context}"
       )

       panel = Panel(
           table,
           title=title,
           subtitle=metadata,
           border_style=severity_color,
       )

       console.print(panel)
   ```

4. Implement batch rendering with question limit:
   ```python
   def render_conflict_batch(
       console: Console,
       conflicts: list[SemanticConflict],
       max_questions: int = 3,
   ) -> list[SemanticConflict]:
       """Render conflicts prioritized by severity, capped at max_questions.

       Args:
           console: Rich console instance
           conflicts: All conflicts detected
           max_questions: Maximum conflicts to show (default 3)

       Returns:
           List of conflicts to prompt for (sorted by severity, capped)
       """
       # Sort by severity (high → medium → low)
       severity_order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
       sorted_conflicts = sorted(
           conflicts,
           key=lambda c: (severity_order[c.severity], c.term.surface_text)
       )

       # Cap to max_questions
       to_prompt = sorted_conflicts[:max_questions]

       # Render summary if truncated
       if len(sorted_conflicts) > max_questions:
           remaining = len(sorted_conflicts) - max_questions
           console.print(
               f"\n[yellow]Note:[/yellow] Showing {max_questions} of {len(sorted_conflicts)} conflicts. "
               f"{remaining} lower-priority conflict(s) deferred to async resolution.\n"
           )

       # Render each conflict
       for conflict in to_prompt:
           render_conflict(console, conflict)
           console.print()  # Blank line between conflicts

       return to_prompt
   ```

5. Export from `glossary/__init__.py`: `render_conflict`, `render_conflict_batch`.

**Files**:
- `src/specify_cli/glossary/rendering.py` (new file, ~120 lines)
- `src/specify_cli/glossary/__init__.py` (update exports)

**Validation**:
- [ ] `render_conflict()` displays severity icon, color, term, context, and candidates
- [ ] Candidate table shows scope, definition, confidence in ranked order
- [ ] Panel border color matches severity (red=high, yellow=medium, blue=low)
- [ ] `render_conflict_batch()` sorts conflicts by severity (high first)
- [ ] Batch rendering caps at max_questions (default 3)
- [ ] Truncation message shows when conflicts exceed max_questions
- [ ] Rich output renders correctly in terminal (no formatting errors)

**Edge Cases**:
- Conflict has 0 candidates: render panel with "(No candidates available)" message
- Conflict has 1 candidate: render table with single row (valid for auto-resolution)
- Conflict has 10+ candidates: all are shown in table (no truncation at candidate level, only at conflict level)
- Candidate definition is very long (>100 chars): Rich table wraps correctly
- Console width is narrow (<80 cols): table adjusts with Rich auto-sizing
- Severity is unknown (not in enum): default to white color, "?" icon, log warning

---

### T026: Typer Prompts for User Input

**Purpose**: Implement the Typer-based prompt system that collects user clarification choices (select 1-N, custom sense, defer) with input validation and error handling.

**Steps**:
1. Create `src/specify_cli/glossary/prompts.py`.

2. Define prompt choice enum:
   ```python
   from enum import StrEnum
   import typer
   from specify_cli.glossary.models import SemanticConflict, TermSense

   class PromptChoice(StrEnum):
       SELECT_CANDIDATE = "select"
       CUSTOM_SENSE = "custom"
       DEFER = "defer"
   ```

3. Implement candidate selection prompt:
   ```python
   def prompt_conflict_resolution(
       conflict: SemanticConflict,
   ) -> tuple[PromptChoice, int | str | None]:
       """Prompt user to resolve a semantic conflict.

       Displays options:
       - 1-N: Select candidate sense (by number)
       - C: Provide custom sense definition
       - D: Defer to async resolution

       Args:
           conflict: The semantic conflict to resolve

       Returns:
           Tuple of (choice type, value):
           - (SELECT_CANDIDATE, candidate_index) if user selects 1-N
           - (CUSTOM_SENSE, custom_definition) if user enters C
           - (DEFER, None) if user enters D

       Raises:
           typer.Abort: If user cancels with Ctrl+C
       """
       num_candidates = len(conflict.candidate_senses)

       # Build prompt message
       if num_candidates > 0:
           prompt_msg = (
               f"\n[bold]Select resolution:[/bold]\n"
               f"  1-{num_candidates}: Choose candidate sense\n"
               f"  C: Provide custom definition\n"
               f"  D: Defer to async resolution\n"
               f"\nYour choice: "
           )
       else:
           prompt_msg = (
               f"\n[bold]Select resolution:[/bold]\n"
               f"  C: Provide custom definition\n"
               f"  D: Defer to async resolution\n"
               f"\nYour choice: "
           )

       while True:
           try:
               response = typer.prompt(prompt_msg).strip().upper()

               # Handle defer
               if response == "D":
                   return (PromptChoice.DEFER, None)

               # Handle custom sense
               if response == "C":
                   custom_def = typer.prompt(
                       "\nEnter custom definition",
                       type=str,
                   ).strip()

                   if not custom_def:
                       typer.echo("Error: Definition cannot be empty. Try again.")
                       continue

                   return (PromptChoice.CUSTOM_SENSE, custom_def)

               # Handle candidate selection
               if response.isdigit():
                   choice_num = int(response)
                   if 1 <= choice_num <= num_candidates:
                       # Return 0-indexed candidate index
                       return (PromptChoice.SELECT_CANDIDATE, choice_num - 1)
                   else:
                       typer.echo(
                           f"Error: Please enter a number between 1 and {num_candidates}, "
                           f"C for custom, or D to defer."
                       )
                       continue

               # Invalid input
               typer.echo(
                   f"Error: Invalid choice '{response}'. "
                   f"Enter 1-{num_candidates}, C, or D."
               )

           except typer.Abort:
               typer.echo("\n[red]Aborted by user.[/red]")
               raise
   ```

4. Add confirmation prompt for context changes:
   ```python
   def prompt_context_change_confirmation(
       old_hash: str,
       new_hash: str,
   ) -> bool:
       """Prompt user to confirm resumption if context has changed.

       Args:
           old_hash: Original input hash from checkpoint
           new_hash: Current input hash

       Returns:
           True if user confirms, False otherwise
       """
       typer.echo(
           f"\n[yellow]Warning:[/yellow] Step inputs have changed since checkpoint.\n"
           f"  Original hash: {old_hash[:16]}...\n"
           f"  Current hash:  {new_hash[:16]}...\n"
       )

       return typer.confirm(
           "Context may have changed. Proceed with resolution?",
           default=False,
       )
   ```

5. Export from `glossary/__init__.py`: `prompt_conflict_resolution`, `prompt_context_change_confirmation`.

**Files**:
- `src/specify_cli/glossary/prompts.py` (new file, ~100 lines)
- `src/specify_cli/glossary/__init__.py` (update exports)

**Validation**:
- [ ] Prompt displays all options (1-N, C, D) based on candidate count
- [ ] Selecting 1-N returns (SELECT_CANDIDATE, 0-indexed candidate index)
- [ ] Selecting C prompts for custom definition and returns (CUSTOM_SENSE, definition)
- [ ] Selecting D returns (DEFER, None)
- [ ] Empty custom definition is rejected with error message
- [ ] Invalid input (e.g., "X", "99") shows error and re-prompts
- [ ] Ctrl+C raises typer.Abort and displays abort message
- [ ] Context change confirmation shows hash comparison and prompts for yes/no

**Edge Cases**:
- User enters lowercase ("c", "d"): converted to uppercase before processing
- User enters whitespace around input ("  2  "): stripped before validation
- User enters "0" when candidates exist: rejected as out of range
- User enters candidate number > num_candidates: rejected with error
- User cancels custom definition prompt: raises typer.Abort
- Conflict has 0 candidates: prompt omits "1-N" option (only shows C and D)

---

### T027: Non-Interactive Mode Detection

**Purpose**: Implement detection for non-interactive environments (CI pipelines, automated scripts) and provide auto-defer behavior to prevent blocking.

**Steps**:
1. Add non-interactive detection to `prompts.py`:
   ```python
   import sys
   import os

   def is_interactive() -> bool:
       """Detect if running in an interactive terminal.

       Checks:
       1. sys.stdin.isatty() - True if connected to a terminal
       2. CI environment variables (CI, GITHUB_ACTIONS, JENKINS_HOME, etc.)

       Returns:
           True if interactive, False if non-interactive (CI, piped input, etc.)
       """
       # Check if stdin is a TTY
       if not sys.stdin.isatty():
           return False

       # Check common CI environment variables
       ci_env_vars = [
           "CI",
           "GITHUB_ACTIONS",
           "JENKINS_HOME",
           "GITLAB_CI",
           "CIRCLECI",
           "TRAVIS",
           "BUILDKITE",
       ]

       for var in ci_env_vars:
           if os.getenv(var):
               return False

       # Interactive by default
       return True
   ```

2. Add auto-defer function:
   ```python
   def auto_defer_conflicts(
       conflicts: list[SemanticConflict],
   ) -> list[tuple[SemanticConflict, PromptChoice, None]]:
       """Auto-defer all conflicts in non-interactive mode.

       Args:
           conflicts: List of semantic conflicts

       Returns:
           List of (conflict, DEFER, None) tuples for each conflict
       """
       return [
           (conflict, PromptChoice.DEFER, None)
           for conflict in conflicts
       ]
   ```

3. Update prompt function to check interactive mode:
   ```python
   def prompt_conflict_resolution_safe(
       conflict: SemanticConflict,
   ) -> tuple[PromptChoice, int | str | None]:
       """Safe prompt that auto-defers in non-interactive mode.

       Args:
           conflict: The semantic conflict to resolve

       Returns:
           (DEFER, None) if non-interactive, otherwise delegates to interactive prompt
       """
       if not is_interactive():
           typer.echo(
               f"[yellow]Non-interactive mode detected:[/yellow] "
               f"Auto-deferring conflict for '{conflict.term.surface_text}'"
           )
           return (PromptChoice.DEFER, None)

       return prompt_conflict_resolution(conflict)
   ```

4. Add logging for non-interactive detection:
   ```python
   import logging

   logger = logging.getLogger(__name__)

   def log_non_interactive_context() -> None:
       """Log details about non-interactive detection for debugging."""
       if not is_interactive():
           logger.info("Non-interactive mode detected")
           logger.info(f"  stdin.isatty(): {sys.stdin.isatty()}")
           logger.info(f"  CI env vars: {[k for k in ['CI', 'GITHUB_ACTIONS', 'JENKINS_HOME'] if os.getenv(k)]}")
   ```

**Files**:
- `src/specify_cli/glossary/prompts.py` (add ~60 lines)

**Validation**:
- [ ] `is_interactive()` returns False when stdin is not a TTY
- [ ] `is_interactive()` returns False when CI=true env var is set
- [ ] `is_interactive()` returns False when GITHUB_ACTIONS=true
- [ ] `is_interactive()` returns True in normal terminal
- [ ] `auto_defer_conflicts()` returns DEFER choices for all conflicts
- [ ] `prompt_conflict_resolution_safe()` calls interactive prompt when isatty=True
- [ ] `prompt_conflict_resolution_safe()` auto-defers when isatty=False
- [ ] Non-interactive message is displayed when auto-deferring

**Edge Cases**:
- Running in pytest (stdin is not a TTY): auto-defers (correct behavior)
- Running in Docker container with -it flags: interactive (stdin is TTY)
- Running in cron job: auto-defers (no TTY)
- Running with input piped from file (`cat input.txt | spec-kitty ...`): auto-defers
- Multiple CI env vars set: any one triggers non-interactive mode
- Unknown CI platform: still works if stdin.isatty() is False

---

### T028: ClarificationMiddleware Orchestration

**Purpose**: Create the ClarificationMiddleware component that orchestrates conflict rendering, user prompting, glossary updates, and event emission for the full clarification workflow.

**Steps**:
1. Add `ClarificationMiddleware` class to `src/specify_cli/glossary/middleware.py`:
   ```python
   from rich.console import Console
   from specify_cli.glossary.rendering import render_conflict_batch
   from specify_cli.glossary.prompts import (
       prompt_conflict_resolution_safe,
       PromptChoice,
   )
   from specify_cli.glossary.events import (
       emit_clarification_requested,
       emit_clarification_resolved,
       emit_sense_updated,
   )
   from specify_cli.glossary.models import (
       PrimitiveExecutionContext,
       SemanticConflict,
       TermSense,
       GlossaryScope,
       Provenance,
   )
   import uuid
   from datetime import datetime

   class ClarificationMiddleware:
       """Interactive conflict resolution middleware."""

       def __init__(
           self,
           console: Console | None = None,
           max_questions: int = 3,
       ):
           """Initialize clarification middleware.

           Args:
               console: Rich console instance (creates default if None)
               max_questions: Max conflicts to prompt per burst (default 3)
           """
           self.console = console or Console()
           self.max_questions = max_questions

       def process(
           self,
           context: PrimitiveExecutionContext,
       ) -> PrimitiveExecutionContext:
           """Process conflicts and prompt user for resolution.

           Pipeline position: Layer 4 (after generation gate raises BlockedByConflict)

           This middleware is called when generation is blocked. It:
           1. Renders conflicts with Rich formatting
           2. Prompts user for each conflict (select/custom/defer)
           3. Emits events for each resolution
           4. Updates glossary state in context
           5. Returns updated context for resume

           Args:
               context: Primitive execution context with conflicts

           Returns:
               Updated context with resolved conflicts (if interactive)
               or deferred conflicts (if non-interactive)
           """
           if not context.conflicts:
               # No conflicts to clarify
               return context

           # Render conflicts (capped at max_questions)
           to_prompt = render_conflict_batch(
               self.console,
               context.conflicts,
               max_questions=self.max_questions,
           )

           # Emit requested events for deferred conflicts
           deferred_conflicts = context.conflicts[len(to_prompt):]
           for conflict in deferred_conflicts:
               self._emit_deferred(context, conflict)

           # Process each conflict interactively
           resolved_count = 0
           for conflict in to_prompt:
               choice, value = prompt_conflict_resolution_safe(conflict)

               if choice == PromptChoice.SELECT_CANDIDATE:
                   # User selected candidate
                   candidate_idx = value
                   selected_sense = conflict.candidate_senses[candidate_idx]
                   self._handle_candidate_selection(
                       context, conflict, selected_sense
                   )
                   resolved_count += 1

               elif choice == PromptChoice.CUSTOM_SENSE:
                   # User provided custom definition
                   custom_definition = value
                   self._handle_custom_sense(
                       context, conflict, custom_definition
                   )
                   resolved_count += 1

               elif choice == PromptChoice.DEFER:
                   # User deferred to async
                   self._emit_deferred(context, conflict)

           # Update context with resolution stats
           context.resolved_conflicts_count = resolved_count
           context.deferred_conflicts_count = (
               len(context.conflicts) - resolved_count
           )

           # If all resolved, clear conflicts (allows generation to proceed)
           if resolved_count == len(context.conflicts):
               context.conflicts = []

           return context

       def _handle_candidate_selection(
           self,
           context: PrimitiveExecutionContext,
           conflict: SemanticConflict,
           selected_sense: TermSense,
       ) -> None:
           """Handle user selection of a candidate sense."""
           conflict_id = str(uuid.uuid4())

           # Emit resolution event
           emit_clarification_resolved(
               conflict_id=conflict_id,
               term_surface=conflict.term.surface_text,
               selected_sense=selected_sense,
               actor_id=context.actor_id,
               timestamp=datetime.utcnow(),
               resolution_mode="interactive",
           )

           # Update glossary in context (promote sense to active)
           self._update_glossary(context, selected_sense)

           self.console.print(
               f"[green]✓[/green] Resolved: {conflict.term.surface_text} = "
               f"{selected_sense.definition}"
           )

       def _handle_custom_sense(
           self,
           context: PrimitiveExecutionContext,
           conflict: SemanticConflict,
           custom_definition: str,
       ) -> None:
           """Handle user-provided custom sense definition."""
           # Create new sense with user definition
           new_sense = TermSense(
               surface=conflict.term,
               scope=GlossaryScope.TEAM_DOMAIN,  # Default to team_domain
               definition=custom_definition,
               provenance=Provenance(
                   actor_id=context.actor_id,
                   timestamp=datetime.utcnow(),
                   source="user_clarification",
               ),
               confidence=1.0,  # User-provided = high confidence
               status="active",
           )

           # Emit sense updated event
           emit_sense_updated(
               term_surface=conflict.term.surface_text,
               scope=GlossaryScope.TEAM_DOMAIN.value,
               new_sense=new_sense,
               actor_id=context.actor_id,
               timestamp=datetime.utcnow(),
               update_type="create",
           )

           # Update glossary in context
           self._update_glossary(context, new_sense)

           self.console.print(
               f"[green]✓[/green] Added custom sense: "
               f"{conflict.term.surface_text} = {custom_definition}"
           )

       def _emit_deferred(
           self,
           context: PrimitiveExecutionContext,
           conflict: SemanticConflict,
       ) -> None:
           """Emit clarification requested event for deferred conflict."""
           conflict_id = str(uuid.uuid4())

           # Build ranked options list
           options = [
               sense.definition
               for sense in conflict.candidate_senses
           ]

           emit_clarification_requested(
               conflict_id=conflict_id,
               question=f"What does '{conflict.term.surface_text}' mean in this context?",
               term=conflict.term.surface_text,
               options=options,
               urgency=conflict.severity.value,
               step_id=context.step_id,
               mission_id=context.mission_id,
               run_id=context.run_id,
               timestamp=datetime.utcnow(),
           )

       def _update_glossary(
           self,
           context: PrimitiveExecutionContext,
           sense: TermSense,
       ) -> None:
           """Update glossary state in context with new/updated sense."""
           # Add to context.resolved_senses (for downstream use)
           if not hasattr(context, "resolved_senses"):
               context.resolved_senses = []

           context.resolved_senses.append(sense)
   ```

2. Add event emission stubs to `events.py` (full implementation in WP08):
   ```python
   def emit_clarification_requested(
       conflict_id: str,
       question: str,
       term: str,
       options: list[str],
       urgency: str,
       step_id: str,
       mission_id: str,
       run_id: str,
       timestamp: datetime,
   ) -> None:
       """Emit GlossaryClarificationRequested event (stub for WP06)."""
       import logging
       logger = logging.getLogger(__name__)
       logger.info(
           f"Clarification requested: term={term}, urgency={urgency}, "
           f"options={len(options)}"
       )

   def emit_clarification_resolved(
       conflict_id: str,
       term_surface: str,
       selected_sense: TermSense,
       actor_id: str,
       timestamp: datetime,
       resolution_mode: str,
   ) -> None:
       """Emit GlossaryClarificationResolved event (stub for WP06)."""
       import logging
       logger = logging.getLogger(__name__)
       logger.info(
           f"Clarification resolved: term={term_surface}, "
           f"mode={resolution_mode}"
       )

   def emit_sense_updated(
       term_surface: str,
       scope: str,
       new_sense: TermSense,
       actor_id: str,
       timestamp: datetime,
       update_type: str,
   ) -> None:
       """Emit GlossarySenseUpdated event (stub for WP06)."""
       import logging
       logger = logging.getLogger(__name__)
       logger.info(
           f"Sense updated: term={term_surface}, scope={scope}, "
           f"type={update_type}"
       )
   ```

**Files**:
- `src/specify_cli/glossary/middleware.py` (add ~150 lines)
- `src/specify_cli/glossary/events.py` (add ~50 lines of stubs)

**Validation**:
- [ ] Middleware renders conflicts with `render_conflict_batch()`
- [ ] Prompts user for each conflict with `prompt_conflict_resolution_safe()`
- [ ] Handles SELECT_CANDIDATE: emits resolved event, updates glossary
- [ ] Handles CUSTOM_SENSE: emits sense updated event, creates new TermSense
- [ ] Handles DEFER: emits requested event, does not update glossary
- [ ] Truncates conflicts to max_questions (default 3)
- [ ] Defers excess conflicts beyond max_questions
- [ ] Updates context.resolved_conflicts_count and deferred_conflicts_count
- [ ] Clears context.conflicts if all resolved

**Edge Cases**:
- All conflicts deferred: context.conflicts remains populated (generation still blocked)
- Some resolved, some deferred: context.conflicts has remaining deferred conflicts
- User aborts (Ctrl+C) mid-batch: raises typer.Abort, no partial updates
- Custom sense with empty definition: rejected by prompt, re-prompts
- Conflict has no candidates: prompt only offers C (custom) and D (defer)
- Event emission fails: logs error but continues (don't block clarification)

---

### T029: Clarification Integration Tests

**Purpose**: Write comprehensive integration tests that verify the full clarification workflow with mocked Typer prompts and all resolution paths.

**Steps**:
1. Create `tests/specify_cli/glossary/test_clarification.py`:

2. Implement test fixtures:
   ```python
   import pytest
   from unittest.mock import MagicMock, patch
   from rich.console import Console
   from specify_cli.glossary.models import (
       PrimitiveExecutionContext,
       SemanticConflict,
       TermSense,
       TermSurface,
       GlossaryScope,
       Severity,
       ConflictType,
   )
   from specify_cli.glossary.middleware import ClarificationMiddleware
   from specify_cli.glossary.prompts import PromptChoice

   @pytest.fixture
   def mock_console():
       """Mock Rich console."""
       return MagicMock(spec=Console)

   @pytest.fixture
   def mock_context():
       """Mock primitive execution context."""
       return PrimitiveExecutionContext(
           step_id="step-001",
           mission_id="041-mission",
           run_id="run-001",
           actor_id="user:alice",
           conflicts=[],
       )

   @pytest.fixture
   def ambiguous_conflict():
       """Create ambiguous conflict with 2 candidates."""
       return SemanticConflict(
           term=TermSurface(surface_text="workspace"),
           conflict_type=ConflictType.AMBIGUOUS,
           severity=Severity.HIGH,
           confidence=0.9,
           candidate_senses=[
               TermSense(
                   surface=TermSurface("workspace"),
                   scope=GlossaryScope.TEAM_DOMAIN,
                   definition="Git worktree directory",
                   confidence=0.9,
                   status="active",
               ),
               TermSense(
                   surface=TermSurface("workspace"),
                   scope=GlossaryScope.TEAM_DOMAIN,
                   definition="VS Code workspace file",
                   confidence=0.7,
                   status="active",
               ),
           ],
           context="description field",
       )
   ```

3. Write test cases for all resolution paths:

   **Test: Select candidate**:
   ```python
   @patch("specify_cli.glossary.prompts.prompt_conflict_resolution_safe")
   @patch("specify_cli.glossary.events.emit_clarification_resolved")
   def test_select_candidate_resolves_conflict(
       mock_emit_resolved,
       mock_prompt,
       mock_console,
       mock_context,
       ambiguous_conflict,
   ):
       """User selects candidate sense from list."""
       # Mock user selects first candidate
       mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

       middleware = ClarificationMiddleware(console=mock_console)
       mock_context.conflicts = [ambiguous_conflict]

       result = middleware.process(mock_context)

       # Verify resolution event emitted
       assert mock_emit_resolved.call_count == 1
       call_kwargs = mock_emit_resolved.call_args.kwargs
       assert call_kwargs["term_surface"] == "workspace"
       assert call_kwargs["resolution_mode"] == "interactive"

       # Verify glossary updated
       assert hasattr(result, "resolved_senses")
       assert len(result.resolved_senses) == 1
       assert result.resolved_senses[0].definition == "Git worktree directory"

       # Verify conflicts cleared
       assert result.conflicts == []
       assert result.resolved_conflicts_count == 1
   ```

   **Test: Custom sense**:
   ```python
   @patch("specify_cli.glossary.prompts.prompt_conflict_resolution_safe")
   @patch("specify_cli.glossary.events.emit_sense_updated")
   def test_custom_sense_creates_new_entry(
       mock_emit_sense,
       mock_prompt,
       mock_console,
       mock_context,
       ambiguous_conflict,
   ):
       """User provides custom sense definition."""
       # Mock user provides custom definition
       mock_prompt.return_value = (
           PromptChoice.CUSTOM_SENSE,
           "Isolated directory for WP implementation"
       )

       middleware = ClarificationMiddleware(console=mock_console)
       mock_context.conflicts = [ambiguous_conflict]

       result = middleware.process(mock_context)

       # Verify sense updated event emitted
       assert mock_emit_sense.call_count == 1
       call_kwargs = mock_emit_sense.call_args.kwargs
       assert call_kwargs["term_surface"] == "workspace"
       assert call_kwargs["update_type"] == "create"
       assert call_kwargs["scope"] == "team_domain"

       # Verify custom sense in glossary
       assert len(result.resolved_senses) == 1
       assert result.resolved_senses[0].definition == "Isolated directory for WP implementation"
       assert result.resolved_senses[0].confidence == 1.0

       # Verify conflicts cleared
       assert result.conflicts == []
   ```

   **Test: Defer to async**:
   ```python
   @patch("specify_cli.glossary.prompts.prompt_conflict_resolution_safe")
   @patch("specify_cli.glossary.events.emit_clarification_requested")
   def test_defer_emits_requested_event(
       mock_emit_requested,
       mock_prompt,
       mock_console,
       mock_context,
       ambiguous_conflict,
   ):
       """User defers conflict resolution to async mode."""
       # Mock user defers
       mock_prompt.return_value = (PromptChoice.DEFER, None)

       middleware = ClarificationMiddleware(console=mock_console)
       mock_context.conflicts = [ambiguous_conflict]

       result = middleware.process(mock_context)

       # Verify requested event emitted
       assert mock_emit_requested.call_count == 1
       call_kwargs = mock_emit_requested.call_args.kwargs
       assert call_kwargs["term"] == "workspace"
       assert call_kwargs["urgency"] == "high"
       assert len(call_kwargs["options"]) == 2

       # Verify conflict NOT resolved (remains in context)
       assert result.conflicts == [ambiguous_conflict]
       assert result.deferred_conflicts_count == 1
   ```

   **Test: Non-interactive mode**:
   ```python
   @patch("specify_cli.glossary.prompts.is_interactive", return_value=False)
   @patch("specify_cli.glossary.events.emit_clarification_requested")
   def test_non_interactive_auto_defers(
       mock_emit_requested,
       mock_is_interactive,
       mock_console,
       mock_context,
       ambiguous_conflict,
   ):
       """Non-interactive mode auto-defers all conflicts."""
       middleware = ClarificationMiddleware(console=mock_console)
       mock_context.conflicts = [ambiguous_conflict]

       result = middleware.process(mock_context)

       # Verify auto-defer (requested event emitted)
       assert mock_emit_requested.call_count == 1

       # Verify conflicts remain (not resolved)
       assert result.conflicts == [ambiguous_conflict]
       assert result.deferred_conflicts_count == 1
   ```

   **Test: Max questions capping**:
   ```python
   @patch("specify_cli.glossary.prompts.prompt_conflict_resolution_safe")
   @patch("specify_cli.glossary.events.emit_clarification_requested")
   def test_max_questions_caps_prompts(
       mock_emit_requested,
       mock_prompt,
       mock_console,
       mock_context,
   ):
       """Clarification middleware caps at max_questions."""
       # Mock user resolves first 2, defers 3rd
       mock_prompt.return_value = (PromptChoice.SELECT_CANDIDATE, 0)

       # Create 5 conflicts
       conflicts = [
           SemanticConflict(
               term=TermSurface(f"term{i}"),
               conflict_type=ConflictType.AMBIGUOUS,
               severity=Severity.HIGH,
               confidence=0.9,
               candidate_senses=[
                   TermSense(
                       surface=TermSurface(f"term{i}"),
                       scope=GlossaryScope.TEAM_DOMAIN,
                       definition=f"Definition {i}",
                       confidence=0.9,
                       status="active",
                   ),
               ],
               context="test",
           )
           for i in range(5)
       ]

       middleware = ClarificationMiddleware(
           console=mock_console,
           max_questions=3,
       )
       mock_context.conflicts = conflicts

       result = middleware.process(mock_context)

       # Verify only 3 prompts shown
       assert mock_prompt.call_count == 3

       # Verify 2 auto-deferred (5 total - 3 prompted)
       assert mock_emit_requested.call_count == 2
   ```

4. Add edge case tests:
   - Empty conflicts list (no-op)
   - Conflict with 0 candidates (only C/D options)
   - All conflicts resolved (context.conflicts cleared)
   - Mixed resolutions (some select, some custom, some defer)
   - Event emission failure (logs error, continues)

**Files**:
- `tests/specify_cli/glossary/test_clarification.py` (new file, ~400 lines)

**Validation**:
- [ ] All resolution paths tested (select, custom, defer)
- [ ] Non-interactive mode tested (auto-defer)
- [ ] Max questions capping tested
- [ ] Event emission verified for each path
- [ ] Glossary updates verified
- [ ] Context.conflicts cleared when all resolved
- [ ] Context.conflicts remain when deferred
- [ ] Test coverage >95% on clarification.py

**Edge Cases**:
- User aborts (Ctrl+C): test with `side_effect=typer.Abort`
- Conflict with very long definition: rendering doesn't crash
- Multiple conflicts with same term: all are prompted
- No conflicts: middleware returns context unchanged
- Event emission raises exception: middleware continues (doesn't crash)

---

## Test Strategy

**Unit Tests** (in `tests/specify_cli/glossary/test_rendering.py`, `test_prompts.py`):
- Test `render_conflict()` with all severity levels
- Test `render_conflict_batch()` with various conflict counts
- Test `prompt_conflict_resolution()` with all input types (1-N, C, D)
- Test `is_interactive()` with different environment conditions
- Test `auto_defer_conflicts()` batch deferral

**Integration Tests** (in `tests/specify_cli/glossary/test_clarification.py`):
- Test full `ClarificationMiddleware.process()` workflow
- Mock Typer prompts to simulate user choices
- Verify event emission for all paths
- Test non-interactive mode end-to-end
- Test max_questions capping with 5+ conflicts

**Running Tests**:
```bash
# Unit tests
python -m pytest tests/specify_cli/glossary/test_rendering.py -v
python -m pytest tests/specify_cli/glossary/test_prompts.py -v

# Integration tests
python -m pytest tests/specify_cli/glossary/test_clarification.py -v

# Full glossary test suite
python -m pytest tests/specify_cli/glossary/ -v --cov=src/specify_cli/glossary
```

## Definition of Done

- [ ] 5 subtasks complete (T025-T029)
- [ ] `rendering.py`: ~120 lines (conflict rendering, batch capping, Rich tables)
- [ ] `prompts.py`: ~160 lines (prompt logic, validation, non-interactive detection)
- [ ] `middleware.py`: ClarificationMiddleware added (~150 lines)
- [ ] `events.py`: Event emission stubs added (~50 lines)
- [ ] Unit tests: ~200 lines covering rendering and prompts
- [ ] Integration tests: ~400 lines covering full clarification workflow
- [ ] All tests pass with >95% coverage on clarification modules
- [ ] mypy --strict passes on all new code
- [ ] Rich rendering works correctly in terminal (no formatting errors)
- [ ] Non-interactive mode auto-defers without blocking
- [ ] Max questions capping works (default 3, configurable)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Rich rendering breaks in narrow terminals | User can't see candidates clearly | Test with various terminal widths (80, 120, 160 cols), Rich auto-wraps tables |
| Typer prompts hang in CI | Blocks pipeline indefinitely | Auto-detect non-interactive mode via sys.stdin.isatty() and CI env vars |
| User provides malformed custom sense | Invalid glossary entry | Validate custom definition is non-empty, trim whitespace, reject empty input |
| Max questions too low (3) causes UX frustration | User must iterate multiple times to resolve all conflicts | Document that 3 is a starting point, configurable via constructor arg |
| Event emission fails silently | Loss of observability | Log errors, continue clarification (don't let event failure block user resolution) |
| Rendering shows too many candidates (10+) | Overwhelms user | No limit on candidates per conflict (all shown), rely on ranking to surface best options first |

## Review Guidance

When reviewing this WP, verify:
1. **Rendering is clear and usable**:
   - Severity color-coding is correct (red=high, yellow=medium, blue=low)
   - Candidates are ranked deterministically (scope precedence → confidence)
   - Rich tables render correctly in terminal (no formatting errors)

2. **Prompts validate input correctly**:
   - 1-N selection is 0-indexed internally but 1-indexed in UI
   - C (custom) prompts for definition and rejects empty input
   - D (defer) returns immediately without further prompts
   - Invalid input (X, 99, etc.) re-prompts with clear error

3. **Non-interactive mode works**:
   - `is_interactive()` detects CI environments correctly
   - Auto-defer happens when stdin is not a TTY
   - No blocking waiting for user input in CI

4. **ClarificationMiddleware orchestrates correctly**:
   - Calls render → prompt → event emission in order
   - Updates glossary state in context
   - Clears conflicts when all resolved
   - Preserves conflicts when deferred

5. **Event emission is comprehensive**:
   - GlossaryClarificationRequested for deferred conflicts
   - GlossaryClarificationResolved for selected candidates
   - GlossarySenseUpdated for custom senses
   - Events logged even if emission fails (stub in WP06)

6. **Test coverage is thorough**:
   - All resolution paths tested (select, custom, defer)
   - Non-interactive mode tested
   - Max questions capping tested
   - Edge cases covered (0 candidates, empty input, abort)

7. **No fallback mechanisms**:
   - If Typer raises exception, propagate it (don't silently continue)
   - If rendering fails, fail clearly (don't fall back to plain text)

## Activity Log

- 2026-02-16T00:00:00Z -- llm:claude-sonnet-4.5 -- lane=planned -- WP created with comprehensive guidance
- 2026-02-16T15:55:53Z – coordinator – shell_pid=13051 – lane=doing – Assigned agent via workflow command
- 2026-02-16T16:05:26Z – coordinator – shell_pid=13051 – lane=for_review – Ready for review: Implemented all subtasks T025-T029 -- Rich conflict rendering, Typer prompts, non-interactive detection, ClarificationMiddleware, 93 new tests all passing
- 2026-02-16T16:06:00Z – codex – shell_pid=17323 – lane=doing – Started review via workflow command
- 2026-02-16T16:09:51Z – codex – shell_pid=17323 – lane=planned – Moved to planned
- 2026-02-16T16:10:22Z – coordinator – shell_pid=20022 – lane=doing – Started implementation via workflow command
- 2026-02-16T16:14:19Z – coordinator – shell_pid=20022 – lane=for_review – Fixed: deterministic candidate ranking by scope precedence, updated severity icons to emoji circles. Added 16 regression tests.
- 2026-02-16T16:15:46Z – codex – shell_pid=23165 – lane=doing – Started review via workflow command
- 2026-02-16T16:18:44Z – codex – shell_pid=23165 – lane=planned – Moved to planned
