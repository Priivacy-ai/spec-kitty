---
work_package_id: WP05
title: CLI Adapter Conversion
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "780370"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/cli/commands/agent/workflow.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading further, load the assigned agent profile for this session:

```
/ad-hoc-profile-load python-pedro
```

Do not begin implementation until the profile is active.

---

## Objective

Rewrite the 4 primary CLI command modules to import from `runtime.*` instead of `specify_cli.next.*` / `specify_cli.runtime.*`. The module paths (`specify_cli.cli.commands.*`) stay unchanged — only the import bodies change. Confirm each command is a thin adapter: argument parsing → runtime call → Rich/JSON rendering → exit code. No state-machine decisioning inline.

---

## Context

**Acceptance criterion (SC-3)**: A code-review walkthrough confirms no CLI command module embeds state-transition decisioning. Every command must be a thin adapter.

**Key distinction**: These files are NOT becoming shims. They stay at `specify_cli.cli.commands.*` permanently. Only their import targets change.

**Run this before touching any file**:
```bash
spec-kitty agent mission check-prerequisites --json --mission runtime-mission-execution-extraction-01KPDYGW
```
Confirm WP03 and WP04 are in `done` or `approved` lane before starting.

---

## Subtask T018 — Rewrite `next_cmd.py`

**Purpose**: The `next_cmd.py` is the primary CLI entry point for `spec-kitty next`. It currently imports from `specify_cli.next.*`.

**Steps**:

1. Read `src/specify_cli/cli/commands/next_cmd.py` in full. Note every `from specify_cli.next.*` import.

2. Replace each import with its `runtime.*` equivalent per the occurrence_map.yaml:
   - `from specify_cli.next.decision import decide_next, Decision, DecisionKind` → `from runtime.decisioning.decision import decide_next, Decision, DecisionKind`
   - `from specify_cli.next.prompt_builder import build_prompt` → `from runtime.prompts.builder import build_prompt`
   - `from specify_cli.next.runtime_bridge import RuntimeBridge` → `from runtime.bridge.runtime_bridge import RuntimeBridge` (or equivalent)
   - Inject `RichPresentationSink` from the CLI layer if `RuntimeBridge` now requires a `PresentationSink`:
     ```python
     from specify_cli.cli._rich_sink import RichPresentationSink  # new file in WP05 if needed
     sink = RichPresentationSink()
     bridge = RuntimeBridge(sink=sink)
     ```

3. Scan the remaining function bodies for any inline state-transition logic (if/elif chains on lane values, decisioning beyond a single runtime call). If found, extract to `runtime.decisioning` — that is out-of-scope for this WP but must be flagged in the PR.

4. Verify the command still works:
   ```bash
   spec-kitty next --help
   spec-kitty next --agent claude --mission runtime-regression-reference-01KPDYGW --json
   ```

**Files touched**: `src/specify_cli/cli/commands/next_cmd.py`

**Validation**: `spec-kitty next --help` exits 0 and shows expected options.

---

## Subtask T019 — Rewrite `implement.py`

**Purpose**: The `implement.py` CLI entry point sets up the workspace and delegates to runtime for lane resolution.

**Steps**:

1. Read `src/specify_cli/cli/commands/implement.py`. Note all `specify_cli.runtime.*` imports.

2. Replace imports:
   - `from specify_cli.runtime.resolver import resolve_mission, ResolutionResult` → `from runtime.discovery.resolver import resolve_mission, ResolutionResult`
   - `from specify_cli.runtime.home import get_kittify_home` → `from runtime.discovery.home import get_kittify_home`
   - Any other `specify_cli.runtime.*` or `specify_cli.next.*` imports → `runtime.*` equivalents

3. Verify:
   ```bash
   spec-kitty agent action implement --help
   ```

**Files touched**: `src/specify_cli/cli/commands/implement.py`

---

## Subtask T020 — Rewrite `merge.py` (CLI)

**Purpose**: The CLI `merge.py` entry point delegates to the orchestration layer.

**Important**: Do not confuse `src/specify_cli/cli/commands/merge.py` with `src/runtime/orchestration/merge.py`. This task is the CLI entry point only.

**Steps**:

1. Read `src/specify_cli/cli/commands/merge.py`. Note `specify_cli.runtime.*` imports.

2. Replace imports with `runtime.orchestration.*` or `runtime.discovery.*` equivalents.

3. Verify:
   ```bash
   spec-kitty merge --help
   ```

**Files touched**: `src/specify_cli/cli/commands/merge.py`

---

## Subtask T021 — Rewrite `agent/workflow.py`

**Purpose**: `workflow.py` is the review/action dispatch adapter — it handles `spec-kitty agent action implement/review`.

**Steps**:

1. Read `src/specify_cli/cli/commands/agent/workflow.py`. Note `specify_cli.next.*` and `specify_cli.runtime.*` imports.

2. Replace imports with `runtime.*` equivalents. If `workflow.py` calls `decide_next` directly, replace with `from runtime.decisioning.decision import decide_next`.

3. If `workflow.py` constructs a `RuntimeBridge`, inject `RichPresentationSink` as in T018.

4. Verify:
   ```bash
   spec-kitty agent action implement --help
   spec-kitty agent action review --help
   ```

**Files touched**: `src/specify_cli/cli/commands/agent/workflow.py`

---

## Subtask T022 — Audit Phase 4 CLI Additions

**Purpose**: `advise.py` and `do_cmd.py` were added by the profile-invocation-runtime-audit-trail mission (Phase 4). Confirm they import from `specify_cli.invocation.*` only (not from `specify_cli.next.*` or `specify_cli.runtime.*`). If they do import from the extraction surface, add them to the occurrence_map.yaml under `cli_adapter` and rewrite.

**Steps**:

1. Scan:
   ```bash
   rg "specify_cli\.next|specify_cli\.runtime" \
     src/specify_cli/cli/commands/advise.py \
     src/specify_cli/cli/commands/do_cmd.py \
     src/specify_cli/cli/commands/invocations_cmd.py \
     src/specify_cli/cli/commands/profiles_cmd.py
   ```

2. If any matches: add the file to occurrence_map.yaml `cli_adapter` category with the replacement mappings, then rewrite.

3. If no matches: add a note in the PR description confirming Phase 4 additions are clean.

**Files touched**: occurrence_map.yaml (amendment if needed); Phase 4 CLI files (only if they import from extraction surface)

---

## `RichPresentationSink` (create if needed by T018/T021)

If `RuntimeBridge` was modified in WP03 to require a `PresentationSink`, create the Rich-backed implementation in the CLI layer:

```python
# src/specify_cli/cli/_rich_sink.py
from __future__ import annotations
import json
from rich.console import Console
from runtime.seams.presentation_sink import PresentationSink

class RichPresentationSink:
    """Rich-backed PresentationSink for CLI command modules."""
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def write_line(self, text: str) -> None:
        self._console.print(text)

    def write_status(self, message: str) -> None:
        self._console.print(f"[dim]{message}[/dim]")

    def write_json(self, data: object) -> None:
        self._console.print_json(json.dumps(data))

assert isinstance(RichPresentationSink(), PresentationSink)
```

This file lives in `src/specify_cli/cli/` — it is NOT in `src/runtime/` (correct: runtime must not import Rich).

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP05 --agent claude`.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## Definition of Done

- [ ] All 4 CLI command modules import from `runtime.*` (no `specify_cli.next.*` or `specify_cli.runtime.*` imports)
- [ ] `spec-kitty next --help`, `spec-kitty merge --help`, `spec-kitty agent action implement --help`, `spec-kitty agent action review --help` all exit 0
- [ ] `spec-kitty next --json` produces valid JSON against the reference fixture
- [ ] Phase 4 additions audited; occurrence_map.yaml amended if needed
- [ ] `RichPresentationSink` created if WP03 required PresentationSink injection

---

## Reviewer Guidance

- For each command module: confirm the only external imports are from `runtime.*`, `typer`, `rich`, and `specify_cli.cli.*`
- Confirm no inline lane/state-transition logic (no bare `if lane == "..."` chains outside a runtime function call)
- Run `spec-kitty next --agent claude --mission <any-real-mission> --json` end-to-end to verify behavior

## Activity Log

- 2026-04-23T07:00:47Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=780370 – Started implementation via action command
- 2026-04-23T07:45:35Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=780370 – Approved (orchestrator): only next_cmd.py needed rewrites (3 import lines). implement.py, merge.py, workflow.py and Phase 4 additions already clean. No remaining specify_cli.next/runtime refs in CLI commands.
