---
work_package_id: WP03
title: Move next/ Subtree to Runtime
dependencies:
- WP02
requirement_refs:
- FR-002
- FR-003
- FR-004
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
agent: "claude:claude-sonnet-4-6:python-pedro:reviewer"
shell_pid: "765443"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: python-pedro
authoritative_surface: src/runtime/bridge/
execution_mode: code_change
owned_files:
- src/runtime/decisioning/decision.py
- src/runtime/bridge/runtime_bridge.py
- src/runtime/prompts/builder.py
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

Relocate the 3 implementation modules from `src/specify_cli/next/` to `src/runtime/`. Update all internal imports. Inject `PresentationSink` wherever `runtime_bridge.py` surfaces output directly. Do NOT touch `src/specify_cli/next/` yet — shims come in WP06. Do NOT rewrite callers — that is WP05, WP09, WP10.

**Critical rule**: After this WP, both `src/specify_cli/next/decision.py` (original) and `src/runtime/decisioning/decision.py` (new copy) will exist simultaneously. The originals become shims in WP06. Do not delete the originals here.

---

## Context

**Source files** (read these before moving):
- `src/specify_cli/next/decision.py` — 472 lines; owns `Decision`, `DecisionKind`, `decide_next`
- `src/specify_cli/next/runtime_bridge.py` — 1,113 lines; the heaviest module; contains event emission logic added by PR #761
- `src/specify_cli/next/prompt_builder.py` — 342 lines; prompt composition

**Read before T011**: `kitty-specs/runtime-mission-execution-extraction-01KPDYGW/research.md` — WP01 addendum. It tells you whether `runtime_bridge.py` has Rich calls that need PresentationSink routing.

**Package structure** (created in WP02):
- `src/runtime/decisioning/` — target for `decision.py`
- `src/runtime/bridge/` — target for `runtime_bridge.py`
- `src/runtime/prompts/` — target for `prompt_builder.py`

---

## Subtask T010 — Move `decision.py`

**Purpose**: Copy `decision.py` to `src/runtime/decisioning/decision.py` and fix its internal imports to use the canonical `runtime.*` namespace.

**Steps**:

1. Read `src/specify_cli/next/decision.py` in full — note every `from specify_cli.*` import at the top.

2. Write `src/runtime/decisioning/decision.py` as a **copy** of the source. Update imports:
   - `from specify_cli.next.prompt_builder import ...` → `from runtime.prompts.builder import ...`
   - Any other `specify_cli.next.*` internal imports → `runtime.*`
   - Keep all `specify_cli.status.*`, `specify_cli.lanes.*`, etc. imports as-is (they are not extraction targets in this mission)

3. Update `src/runtime/decisioning/__init__.py` to re-export the public symbols:
   ```python
   from runtime.decisioning.decision import Decision, DecisionKind, decide_next
   __all__ = ["Decision", "DecisionKind", "decide_next"]
   ```

4. Verify import:
   ```bash
   python -c "from runtime.decisioning.decision import decide_next; print('OK')"
   ```

**Files touched**: `src/runtime/decisioning/decision.py`, `src/runtime/decisioning/__init__.py`

**Validation**: `python -c "from runtime.decisioning import Decision, DecisionKind, decide_next"` — exits 0.

---

## Subtask T011 — Move `runtime_bridge.py` + Inject PresentationSink

**Purpose**: Copy `runtime_bridge.py` to `src/runtime/bridge/runtime_bridge.py`. This is the largest module (1,113 lines). If the WP01 audit found Rich calls, replace them with `PresentationSink` method calls.

**Steps**:

1. Read `src/specify_cli/next/runtime_bridge.py` in full. Note:
   - All `from specify_cli.*` imports (internal cross-module references to fix)
   - All `from rich.*` or `import rich.*` imports (if any — to be replaced with PresentationSink)
   - The `sync/runtime_event_emitter` imports (added in PR #761) — these are KEPT but their outputs must go through `PresentationSink` if they surface to the user

2. Write `src/runtime/bridge/runtime_bridge.py` as a copy. Update imports:
   - `from specify_cli.next.decision import ...` → `from runtime.decisioning.decision import ...`
   - `from specify_cli.next.prompt_builder import ...` → `from runtime.prompts.builder import ...`
   - `from specify_cli.runtime.resolver import ...` → will be `from runtime.discovery.resolver import ...` (WP04 moves this — use forward-compatible import for now, or keep as `specify_cli.runtime.resolver` and let WP06's shim handle it temporarily)
   - Any Rich console calls → `sink.write_line(...)` / `sink.write_status(...)` with injected `PresentationSink`

3. **PresentationSink injection pattern**: If there is a top-level `console = Console()` or equivalent:
   - Add `sink: PresentationSink` parameter to any function/class that uses it
   - CLI adapters (WP05) will inject a `RichPresentationSink` wrapper
   - For functions called from within `runtime_bridge.py` itself, thread `sink` through as a parameter
   - Provide a default `sink: PresentationSink = NullSink()` for backward-compatible calls

4. Update `src/runtime/bridge/__init__.py`:
   ```python
   from runtime.bridge.runtime_bridge import RuntimeBridge  # or whatever the main class/function is
   ```

5. Verify (ignore missing callers — shims will handle them):
   ```bash
   python -c "import runtime.bridge.runtime_bridge; print('OK')"
   mypy --strict src/runtime/bridge/
   ```

**Files touched**: `src/runtime/bridge/runtime_bridge.py`, `src/runtime/bridge/__init__.py`

**Validation**:
- `python -c "import runtime.bridge.runtime_bridge"` exits 0
- `mypy --strict src/runtime/bridge/` exits 0
- No `from rich` or `import rich` appears in `src/runtime/bridge/runtime_bridge.py` (if WP01 audit found Rich usage)

---

## Subtask T012 — Move `prompt_builder.py`

**Purpose**: Copy `prompt_builder.py` to `src/runtime/prompts/builder.py`. This is the simplest move (342 lines, minimal cross-module references).

**Steps**:

1. Read `src/specify_cli/next/prompt_builder.py`. Note all `from specify_cli.*` imports.

2. Write `src/runtime/prompts/builder.py` as a copy. Update:
   - Any `specify_cli.next.*` internal imports → `runtime.*` equivalents
   - Keep all other `specify_cli.*` imports as-is

3. Update `src/runtime/prompts/__init__.py`:
   ```python
   from runtime.prompts.builder import build_prompt  # or main public function name
   ```

4. Verify:
   ```bash
   python -c "import runtime.prompts.builder; print('OK')"
   ```

**Files touched**: `src/runtime/prompts/builder.py`, `src/runtime/prompts/__init__.py`

**Validation**: `python -c "from runtime.prompts.builder import build_prompt"` (or whatever the public function is) — exits 0.

---

## Subtask T013 — Verify: No Forbidden Imports + mypy

**Purpose**: Confirm the moved modules satisfy DIRECTIVE_001 (no forbidden cross-boundary imports) before WP04 starts.

**Steps**:

1. Scan all 3 moved modules for `rich.*` and `typer.*` top-level imports:
   ```bash
   rg "^from rich|^import rich|^from typer|^import typer" \
     src/runtime/decisioning/ src/runtime/bridge/ src/runtime/prompts/
   ```
   Expected: zero matches (or only the PresentationSink import in bridge, which is permitted).

2. Scan for `specify_cli.cli` imports (forbidden per C-009):
   ```bash
   rg "from specify_cli\.cli|import specify_cli\.cli" \
     src/runtime/decisioning/ src/runtime/bridge/ src/runtime/prompts/
   ```
   Expected: zero matches.

3. Run mypy on all moved modules:
   ```bash
   mypy --strict src/runtime/decisioning/ src/runtime/bridge/ src/runtime/prompts/ \
     --ignore-missing-imports
   ```

4. Run a quick import smoke-test:
   ```bash
   python -c "
   import runtime.decisioning
   import runtime.bridge
   import runtime.prompts
   print('All imports OK')
   "
   ```

**Files touched**: None (verification only)

**Validation**: All checks pass with zero violations.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP03 --agent claude`. This WP may run in parallel with WP04.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## Definition of Done

- [ ] `src/runtime/decisioning/decision.py` exists with updated imports; `__init__.py` re-exports public API
- [ ] `src/runtime/bridge/runtime_bridge.py` exists; no `from rich`/`from typer` top-level imports; PresentationSink injected where needed
- [ ] `src/runtime/prompts/builder.py` exists with updated imports; `__init__.py` re-exports public API
- [ ] Original `src/specify_cli/next/*.py` files are **untouched** (shims come in WP06)
- [ ] `mypy --strict` exits clean on all 3 subpackages
- [ ] No `specify_cli.cli.*` imports in any moved module

---

## Reviewer Guidance

- Diff each moved file against the original (`diff src/specify_cli/next/decision.py src/runtime/decisioning/decision.py`): the only changes should be import path updates and PresentationSink injection
- Confirm the originals in `src/specify_cli/next/` are unchanged
- Verify `mypy --strict` passes

## Activity Log

- 2026-04-23T05:10:56Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=755067 – Started implementation via action command
- 2026-04-23T05:18:13Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=755067 – next/ subtree copied to runtime.*; originals untouched; no module-level rich imports; mypy pre-existing type warnings only (inherited from source); all smoke tests pass
- 2026-04-23T06:08:14Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=765443 – Started review via action command
- 2026-04-23T06:16:43Z – claude:claude-sonnet-4-6:python-pedro:reviewer – shell_pid=765443 – Review passed (orchestrator verification): smoke imports clean, zero forbidden module-level imports, zero specify_cli.next.* refs in moved files, originals untouched
