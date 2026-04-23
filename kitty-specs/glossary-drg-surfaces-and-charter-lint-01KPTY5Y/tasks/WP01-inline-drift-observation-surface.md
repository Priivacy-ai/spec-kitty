---
work_package_id: WP01
title: Inline Drift Observation Surface
dependencies: []
requirement_refs:
- C-001
- C-004
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-001
planning_base_branch: feat/glossary-save-seed-file-and-core-terms
merge_target_branch: feat/glossary-save-seed-file-and-core-terms
branch_strategy: Planning artifacts for this feature were generated on feat/glossary-save-seed-file-and-core-terms. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/glossary-save-seed-file-and-core-terms unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- date: '2026-04-23'
  event: created
authoritative_surface: src/specify_cli/glossary/
execution_mode: code_change
mission_slug: glossary-drg-surfaces-and-charter-lint-01KPTY5Y
owned_files:
- src/specify_cli/glossary/observation.py
- src/specify_cli/cli/commands/do_cmd.py
- src/specify_cli/cli/commands/advise.py
- tests/specify_cli/glossary/test_observation.py
tags: []
---

# WP01 — Inline Drift Observation Surface

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Branch**: `main` (planning base) → `main` (merge target)  
**Execute**: `spec-kitty agent action implement WP01 --agent <name>`

## Objective

After a `spec-kitty do`, `ask`, or `advise` invocation, if the glossary chokepoint (WP5.2 — external dependency) recorded **high-severity** or **critical-severity** drift events in the current invocation window, append a compact inline notice to the CLI output before returning. Low/medium severity events are logged only and never surfaced.

**Key invariants**:
- The entire surface adds ≤50ms p95 overhead (C-001 / NFR-001).
- Any read failure returns an empty list silently — agent output is never blocked or errored by this surface (C-001).
- This WP does NOT re-implement chokepoint logic (C-004). It only reads events written by WP5.2.

## Context

### External dependency: WP5.2 chokepoint

WP5.2 emits `SemanticCheckEvaluated` events to `.kittify/events/glossary/_cli.events.jsonl` (and per-mission JSONL) during every `ProfileInvocationExecutor.invoke()` call. Each event has:
```json
{
  "event_type": "semantic_check_evaluated",
  "invocation_id": "01JXYZ...",
  "term": "deployment-target",
  "term_id": "glossary:deployment-target",
  "severity": "high",
  "conflict_type": "scope_mismatch",
  "conflicting_senses": ["infrastructure context", "application context"],
  "checked_at": "2026-04-23T05:00:00Z"
}
```

This WP reads those events after `invoke()` returns — it does not touch the invocation executor.

### Existing CLI entry points

- `src/specify_cli/cli/commands/do_cmd.py` — the `do` command; calls `executor.invoke()`
- `src/specify_cli/cli/commands/advise.py` — the `advise` command; same pattern

The `ask` command may also need wiring if it uses the same executor pattern — check during implementation. Add it if it does; leave it alone if it uses a different path.

### Event log path

```python
_CLI_EVENT_LOG = repo_root / ".kittify" / "events" / "glossary" / "_cli.events.jsonl"
```

---

## Subtask T001 — `InlineNotice` Dataclass

**File**: `src/specify_cli/glossary/observation.py` (new)

**Purpose**: Define the value object that carries one drift notice.

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class InlineNotice:
    term: str                        # human-readable term surface
    term_id: str                     # glossary URN, e.g. "glossary:deployment-target"
    severity: str                    # "high" | "critical"
    conflict_type: str               # e.g. "scope_mismatch"
    conflicting_senses: list[str]    # two or more sense texts
    suggested_action: str            # rendered command hint
```

`suggested_action` is derived during collection:
```python
f"run `spec-kitty glossary resolve {term}`"
```

---

## Subtask T002 — `ObservationSurface.collect_notices()`

**File**: `src/specify_cli/glossary/observation.py`

**Purpose**: Read `_cli.events.jsonl`, filter to high/critical severity events from the current invocation, and return one `InlineNotice` per affected term (deduplicated by `term_id`).

**Contract**:
```python
class ObservationSurface:
    def collect_notices(
        self,
        repo_root: Path,
        invocation_id: str | None = None,
    ) -> list[InlineNotice]:
        ...
```

**Algorithm**:
1. Build path: `repo_root / ".kittify" / "events" / "glossary" / "_cli.events.jsonl"`
2. If file does not exist → return `[]`
3. Read all lines; parse JSON per line; skip malformed lines silently
4. Filter: `event_type == "semantic_check_evaluated"` AND `severity in {"high", "critical"}`
5. If `invocation_id` is provided, also filter `event["invocation_id"] == invocation_id` — only events from the current call
6. Deduplicate by `term_id` (last-seen wins if multiple events for same term)
7. Return list of `InlineNotice` objects

**Wrap entire method**:
```python
try:
    ...
except Exception:
    return []
```

**Performance**: JSONL read for typical log (<5000 events) completes in <5ms. No network, no LLM.

---

## Subtask T003 — `ObservationSurface.render_notices()`

**File**: `src/specify_cli/glossary/observation.py`

**Purpose**: Render a compact notice block to the terminal. No-op if the list is empty.

**Contract**:
```python
def render_notices(self, notices: list[InlineNotice], console: Console) -> None:
    ...
```

**Render format** (5 lines max per notice, prefer 2):
```
⚠ Glossary drift [high]: "deployment-target" — scope_mismatch detected
  Suggest: run `spec-kitty glossary resolve deployment-target`
```

If multiple notices: render each separated by a blank line.

**Implementation**:
```python
from rich.text import Text

def render_notices(self, notices: list[InlineNotice], console: Console) -> None:
    if not notices:
        return
    console.print()  # blank line separator
    for notice in notices:
        line1 = Text()
        line1.append("⚠ Glossary drift ", style="yellow bold")
        line1.append(f"[{notice.severity}]", style="yellow")
        line1.append(f': "{notice.term}" — {notice.conflict_type} detected')
        line2 = Text(f"  Suggest: {notice.suggested_action}", style="dim")
        console.print(line1)
        console.print(line2)
```

Wrap in `try/except` — any render failure is silently ignored.

---

## Subtask T004 — Wire into `do_cmd.py`

**File**: `src/specify_cli/cli/commands/do_cmd.py`

**Purpose**: After `executor.invoke()` returns (and the agent response has been rendered), call `ObservationSurface().collect_notices()` and `render_notices()`.

**Steps**:
1. Import `ObservationSurface` from `specify_cli.glossary.observation`
2. Locate the point after `invoke()` completes and the response is rendered
3. Add:
```python
surface = ObservationSurface()
notices = surface.collect_notices(repo_root, invocation_id=payload.invocation_id)
surface.render_notices(notices, console)
```

The `invocation_id` comes from `payload.invocation_id` (the `InvocationPayload` returned by `invoke()`).

Do not change the return value or exit code of the command — the notice is purely additive output.

---

## Subtask T005 — Wire into `advise.py`

**File**: `src/specify_cli/cli/commands/advise.py`

**Purpose**: Same pattern as T004.

Apply the identical change to `advise.py`. If `ask.py` or similar commands use the same `ProfileInvocationExecutor.invoke()` pattern, apply the same wiring there too. If they use a different path (no `InvocationPayload`), skip them and document the skip in the WP review.

---

## Subtask T006 — Tests

**File**: `tests/specify_cli/glossary/test_observation.py` (new)

**Scenarios to cover**:

1. **High severity → notice returned**  
   Fixture `_cli.events.jsonl` with one `semantic_check_evaluated` event, `severity: "high"`.  
   Assert `collect_notices()` returns list of length 1 with correct `InlineNotice` fields.

2. **Medium severity → filtered out**  
   Same fixture but `severity: "medium"`.  
   Assert returns `[]`.

3. **Multiple terms → multiple notices (deduplicated)**  
   Two events for different terms, both high severity.  
   Assert returns list of length 2.

4. **Same term twice → deduplicated**  
   Two high-severity events for the same `term_id`.  
   Assert returns list of length 1 (last-seen wins).

5. **Missing log file → empty list, no exception**  
   Pass a `repo_root` with no events directory.  
   Assert returns `[]`.

6. **Malformed JSON line → skip, no exception**  
   Insert a corrupt line in the fixture log.  
   Assert still returns correct notices for valid lines.

7. **`invocation_id` filter**  
   Mix events from two different `invocation_id` values.  
   Assert only events from the specified ID are returned.

8. **`render_notices([]) → no output`**  
   Assert `console.print()` is not called when list is empty.  
   (Use `unittest.mock.patch` or a `StringIO`-backed Console.)

**Run**: `cd src && pytest tests/specify_cli/glossary/test_observation.py -v`

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP01 --agent <name>`. The workspace is lane-based — do not guess the branch name. The implement command resolves and enters the correct worktree.

---

## Definition of Done

- [ ] `observation.py` exists with `InlineNotice` dataclass and `ObservationSurface` class
- [ ] `collect_notices()` correctly filters high/critical and deduplicates by `term_id`
- [ ] `collect_notices()` returns `[]` on any file read error — never raises
- [ ] `render_notices([])` produces no output
- [ ] `do_cmd.py` and `advise.py` both call the surface after `invoke()` returns
- [ ] All 8 test scenarios pass: `pytest tests/specify_cli/glossary/test_observation.py`
- [ ] `ruff check src/specify_cli/glossary/observation.py` passes
- [ ] Running `spec-kitty do "hello"` with an empty event log produces no visible change to output

---

## Reviewer Guidance

1. Confirm `try/except` wraps `collect_notices()` at the outer method level, not per-line.
2. Confirm `render_notices()` is also wrapped — a Rich formatting error must never crash the CLI.
3. Confirm the wiring in `do_cmd.py` is after the agent response is rendered, not before.
4. Confirm `invocation_id` is passed to `collect_notices()` so only events from the current call window are shown.
5. Check that no changes were made to `ProfileInvocationExecutor` — this WP only reads events, it does not modify the chokepoint.
