---
work_package_id: WP06
title: Interactive Clarification UI
lane: planned
dependencies: []
subtasks: [T025, T026, T027, T028, T029]
history:
- event: created
  timestamp: '2026-02-16T00:00:00Z'
  actor: llm:claude-sonnet-4.5
---

# Work Package: Interactive Clarification UI

**ID**: WP06 **Priority**: P2 **Estimated Effort**: 2-3 days

## Objective

Implement interactive clarification prompts using Typer + Rich, with ranked candidates and async defer option.

## Context

Clarification middleware handles user interaction when generation is blocked. It renders conflicts with Rich, prompts for choice (candidate/custom/defer), and updates glossary.

**Design ref**: [research.md](../research.md) Finding 5

## Implementation Command

```bash
spec-kitty implement WP06 --base WP05
```

Can run in parallel with WP07.

---

## Subtasks

### T025: Conflict rendering with Rich

Render conflicts as formatted tables (term | scope | definition | confidence).

**Implementation** (clarification.py):
```python
from rich.console import Console
from rich.table import Table

def render_conflict(conflict: SemanticConflict) -> None:
    console = Console()
    console.print(f"\n🔴 {conflict.severity.value.upper()}-severity conflict: \"{conflict.term.surface_text}\"")
    
    # Candidate table
    table = Table(title="Candidate Senses")
    table.add_column("#", justify="right")
    table.add_column("Scope")
    table.add_column("Definition")
    table.add_column("Confidence")
    
    for i, sense in enumerate(conflict.candidate_senses, 1):
        table.add_row(str(i), sense.scope, sense.definition, f"{sense.confidence:.1f}")
    
    console.print(table)
```

---

### T026: Typer prompts

Implement choice input: 1..N (candidate), C (custom), D (defer).

**Implementation**:
```python
import typer

def prompt_for_resolution(conflict: SemanticConflict) -> tuple[str, Optional[str]]:
    """Prompt user for conflict resolution."""
    render_conflict(conflict)
    
    choice = typer.prompt(
        "Select: 1-N (candidate), C (custom sense), D (defer to async)",
        type=str
    )
    
    if choice.upper() == "C":
        custom_sense = typer.prompt("Enter custom definition")
        return ("custom", custom_sense)
    elif choice.upper() == "D":
        return ("defer", None)
    elif choice.isdigit():
        return ("candidate", choice)
    else:
        typer.echo("Invalid choice")
        return prompt_for_resolution(conflict)  # Retry
```

---

### T027: Non-interactive mode

Auto-defer all conflicts if `sys.stdin.isatty()` is False.

**Implementation**:
```python
def is_interactive() -> bool:
    return sys.stdin.isatty() and not os.getenv("CI")

def handle_conflicts_non_interactive(conflicts: List[SemanticConflict]) -> None:
    # Emit GlossaryClarificationRequested for all
    # Exit with error code
    raise DeferredToAsync("non-interactive-auto-defer")
```

---

### T028: ClarificationMiddleware

Orchestrate rendering, prompting, glossary update, event emission.

---

### T029: Clarification tests

Mock typer.prompt, test all choices, non-interactive mode.

---

## Definition of Done

- [ ] 5 subtasks complete
- [ ] clarification.py: ~120 lines
- [ ] Tests >90% coverage (mocked typer)

---

## Testing

```bash
pytest tests/specify_cli/glossary/test_clarification.py -v
```

---

## Reviewer Guidance

**Focus**: Terminal rendering, choice handling, non-interactive behavior

**Acceptance**:
- [ ] Renders correctly in terminal
- [ ] All choices work (candidate/custom/defer)
- [ ] Non-interactive auto-defers
