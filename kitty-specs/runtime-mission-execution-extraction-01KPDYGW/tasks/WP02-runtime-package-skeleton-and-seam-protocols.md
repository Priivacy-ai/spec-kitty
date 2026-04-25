---
work_package_id: WP02
title: Runtime Package Skeleton + Seam Protocols
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-009
- FR-010
- FR-013
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: "claude:claude-sonnet-4-6:architect-alphonso:reviewer"
shell_pid: "753969"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: architect-alphonso
authoritative_surface: src/runtime/seams/
execution_mode: code_change
owned_files:
- src/runtime/__init__.py
- src/runtime/decisioning/__init__.py
- src/runtime/bridge/__init__.py
- src/runtime/prompts/__init__.py
- src/runtime/discovery/__init__.py
- src/runtime/agents/__init__.py
- src/runtime/orchestration/__init__.py
- src/runtime/seams/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading further, load the assigned agent profile for this session:

```
/ad-hoc-profile-load architect-alphonso
```

This is design work. Apply DIRECTIVE_001 (Architectural Integrity) and DIRECTIVE_003 (Decision Documentation) throughout. Do not begin implementation until the profile is active.

---

## Objective

Create the empty `src/runtime/` package tree and define the three seam Protocols that gate the rest of the extraction. No implementation code moves in this WP — only scaffolding and interface definitions.

**Why before the moves**: WP03 and WP04 cannot start without knowing the target package structure and the PresentationSink API shape. WP02 outputs are the single source of truth for both.

---

## Context

**Read before starting**: `kitty-specs/runtime-mission-execution-extraction-01KPDYGW/research.md` — specifically the WP01 addendum on the sync import audit. The `PresentationSink` protocol shape depends on that finding.

**Architectural constraint (DIRECTIVE_001)**: `src/runtime/` must not import from `specify_cli.cli.*`, `rich.*`, or `typer.*`. Every Protocol defined here must be expressible without those dependencies.

**Existing pattern**: `src/charter/`, `src/doctrine/`, `src/kernel/` are the peer top-level packages. Follow their `__init__.py` style.

---

## Subtask T005 — Create `src/runtime/` Package Skeleton

**Purpose**: Create the target directory tree with one empty `__init__.py` per subpackage. WP03 and WP04 move modules into these directories.

**Steps**:

1. Create the following directories and their `__init__.py` files (keep all `__init__.py` empty for now — T009 wires the public API):
   ```
   src/runtime/__init__.py
   src/runtime/decisioning/__init__.py
   src/runtime/bridge/__init__.py
   src/runtime/prompts/__init__.py
   src/runtime/discovery/__init__.py
   src/runtime/agents/__init__.py
   src/runtime/orchestration/__init__.py
   src/runtime/seams/__init__.py
   ```

2. Verify Python can import the empty skeleton:
   ```bash
   python -c "import runtime; import runtime.decisioning; import runtime.seams; print('OK')"
   ```

3. Verify `tests/architectural/test_layer_rules.py` will not reject the new package: the test's `_DEFINED_LAYERS` will be extended in WP07. For now, the scan-based `test_no_unregistered_src_packages` test will fail because `runtime` is not yet in `_DEFINED_LAYERS`. Add `runtime` to the `_EXCLUDED_FROM_LAYER_ENFORCEMENT` frozenset in `test_layer_rules.py` with a comment: `# Transitional: runtime layer added to _DEFINED_LAYERS in WP07`. This is a temporary measure; WP07 moves it to the proper layer.

**Files touched**: `src/runtime/**/__init__.py` (8 files), `tests/architectural/test_layer_rules.py` (temporary exclusion)

**Validation**: `pytest tests/architectural/test_layer_rules.py::TestLayerCoverage::test_no_unregistered_src_packages -v` passes.

---

## Subtask T006 — Define `PresentationSink` Protocol

**Purpose**: Runtime must surface output (progress messages, status lines) without importing `rich.*`. `PresentationSink` is the abstract interface CLI adapters implement with Rich; runtime accepts a `PresentationSink` and never calls Rich directly.

**Steps**:

1. Read the WP01 research addendum to understand which specific Rich calls appear in `runtime_bridge.py`. Common patterns: `console.print(...)`, `console.status(...)`, progress bars.

2. Write `src/runtime/seams/presentation_sink.py`:

   ```python
   """PresentationSink — runtime output abstraction (FR-013).
   
   Runtime surfaces output through this Protocol; CLI adapters inject
   a Rich-backed implementation. Runtime must never import rich.* directly.
   """
   from __future__ import annotations
   from typing import Protocol, runtime_checkable
   
   
   @runtime_checkable
   class PresentationSink(Protocol):
       """Abstract output surface injected into runtime services."""
   
       def write_line(self, text: str) -> None:
           """Emit a single line of text output."""
           ...
   
       def write_status(self, message: str) -> None:
           """Emit a transient status message (e.g. spinner label)."""
           ...
   
       def write_json(self, data: object) -> None:
           """Emit structured JSON output (for --json mode)."""
           ...
   ```

   Extend with additional methods if the WP01 audit found more Rich call patterns.

3. Write `src/runtime/seams/_null_sink.py` — a no-op implementation for tests:
   ```python
   from runtime.seams.presentation_sink import PresentationSink
   
   class NullSink:
       """No-op PresentationSink for use in tests and offline contexts."""
       def write_line(self, text: str) -> None: pass
       def write_status(self, message: str) -> None: pass
       def write_json(self, data: object) -> None: pass
   
   assert isinstance(NullSink(), PresentationSink)  # structural check
   ```

**Files touched**: `src/runtime/seams/presentation_sink.py`, `src/runtime/seams/_null_sink.py`

**Validation**: `python -c "from runtime.seams.presentation_sink import PresentationSink; from runtime.seams._null_sink import NullSink; assert isinstance(NullSink(), PresentationSink)"` — exits 0.

---

## Subtask T007 — Define `StepContractExecutor` Protocol

**Purpose**: #461 Phase 6 will implement `StepContractExecutor`. This WP only defines the typed interface (scaffolding seam per C-002). No implementation.

**Steps**:

1. Write `src/runtime/seams/step_contract_executor.py`:

   ```python
   """StepContractExecutor seam — #461 Phase 6 implementation target.
   
   Runtime exposes this Protocol as the execution-layer entry point.
   Phase 6 (StepContractExecutor) wires a concrete implementation here.
   Runtime itself never implements this Protocol.
   """
   from __future__ import annotations
   from typing import Any, Protocol
   
   
   class StepContractExecutor(Protocol):
       """Executes a step contract on behalf of a profile invocation.
   
       Phase 6 of #461 implements this against the mission template system.
       """
   
       def execute(
           self,
           step_contract: Any,   # Typed in Phase 6 as StepContract
           context: Any,         # Typed in Phase 6 as ExecutionContext
       ) -> Any:                 # Typed in Phase 6 as StepResult
           """Execute the step contract and return its result."""
           ...
   ```

   Note: `Any` types are intentional placeholders. Phase 6 will narrow them once `StepContract` and `ExecutionContext` data models are defined.

**Files touched**: `src/runtime/seams/step_contract_executor.py`

**Validation (SC-5)**: After writing the Protocol, add this inline type-check stub directly in `step_contract_executor.py` (guarded so it only runs under type checking):

```python
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    class _Phase6StubExecutor:
        def execute(self, step_contract: Any, context: Any) -> Any: ...
    _stub: StepContractExecutor = _Phase6StubExecutor()  # mypy must not error here
```

Run `mypy --strict src/runtime/seams/step_contract_executor.py` — exits 0 = SC-5 satisfied.

Also run: `python -c "from runtime.seams.step_contract_executor import StepContractExecutor; print('OK')"` — prints without error.

---

## Subtask T008 — Document `ProfileInvocationExecutor` Boundary

**Purpose**: FR-009 originally planned a new Protocol seam here. Phase 4 already shipped `ProfileInvocationExecutor` at `src/specify_cli/invocation/executor.py`. This WP documents the canonical import path in the `seams/` package so `src/runtime/` code has a single place to discover the boundary.

**Steps**:

1. Write `src/runtime/seams/profile_invocation_executor.py`:

   ```python
   """ProfileInvocationExecutor — canonical boundary reference (FR-009).
   
   Phase 4 of #461 shipped ProfileInvocationExecutor at:
       specify_cli.invocation.executor.ProfileInvocationExecutor
   
   Runtime code that needs to call into profile-governed invocations
   imports from this module so the dependency is documented here.
   
   Do NOT move or re-implement the executor — it lives in invocation/.
   """
   from __future__ import annotations
   
   from specify_cli.invocation.executor import ProfileInvocationExecutor
   
   __all__ = ["ProfileInvocationExecutor"]
   ```

2. Confirm `specify_cli.invocation.executor` is importable (it was merged in the profile-invocation-runtime-audit-trail mission):
   ```bash
   python -c "from specify_cli.invocation.executor import ProfileInvocationExecutor; print('OK')"
   ```

**Files touched**: `src/runtime/seams/profile_invocation_executor.py`

**Validation**: `python -c "from runtime.seams.profile_invocation_executor import ProfileInvocationExecutor; print('OK')"` — exits 0.

---

## Subtask T009 — Wire `src/runtime/__init__.py` Public API

**Purpose**: Expose the key public symbols that CLI adapters (WP05) and callers (WP09/WP10) will import from `runtime` after the extraction. This is the package's public face.

**Steps**:

1. Read the current public exports from `src/specify_cli/next/__init__.py` and `src/specify_cli/runtime/__init__.py` to understand what symbols are currently public.

2. Write `src/runtime/__init__.py`:

   ```python
   """runtime — Spec Kitty execution core.
   
   Canonical top-level package for mission discovery, state-transition
   decisioning, execution sequencing, profile/action invocation,
   active-mode handling (HiC vs autonomous), and charter-artefact retrieval.
   
   Mission: runtime-mission-execution-extraction-01KPDYGW
   Extracted from: specify_cli.next, specify_cli.runtime (3.2.x)
   """
   from __future__ import annotations
   
   # Seam protocols (importable before WP03/WP04 move the implementations)
   from runtime.seams.presentation_sink import PresentationSink
   from runtime.seams.step_contract_executor import StepContractExecutor
   from runtime.seams.profile_invocation_executor import ProfileInvocationExecutor
   
   # NOTE: The following symbols will be re-exported once WP03/WP04 complete
   # the module moves. Uncomment as each move lands:
   #
   # from runtime.decisioning.decision import Decision, DecisionKind, decide_next
   # from runtime.bridge.runtime_bridge import RuntimeBridge
   # from runtime.discovery.resolver import resolve_mission, ResolutionResult, ResolutionTier
   # from runtime.discovery.home import get_kittify_home, get_package_asset_root
   
   __all__ = [
       "PresentationSink",
       "StepContractExecutor",
       "ProfileInvocationExecutor",
   ]
   ```

3. Verify mypy is happy with the skeleton:
   ```bash
   mypy --strict src/runtime/ --ignore-missing-imports
   ```

**Files touched**: `src/runtime/__init__.py`

**Validation**: `python -c "from runtime import PresentationSink, StepContractExecutor, ProfileInvocationExecutor; print('OK')"` — exits 0.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP02 --agent claude`.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## Definition of Done

- [ ] `src/runtime/` package tree exists with 8 empty `__init__.py` files
- [ ] `PresentationSink` Protocol defined with `write_line`, `write_status`, `write_json`; `NullSink` passes structural check
- [ ] `StepContractExecutor` Protocol defined with `execute` stub
- [ ] `profile_invocation_executor.py` re-exports `ProfileInvocationExecutor` from `invocation.executor`
- [ ] `src/runtime/__init__.py` exports the 3 seam types
- [ ] Temporary `_EXCLUDED_FROM_LAYER_ENFORCEMENT` entry added for `runtime` in `test_layer_rules.py`
- [ ] `pytest tests/architectural/test_layer_rules.py::TestLayerCoverage` passes
- [ ] `mypy --strict src/runtime/` exits clean

---

## Reviewer Guidance

- Confirm `PresentationSink` has no `rich` or `typer` imports
- Confirm `StepContractExecutor` has no implementation (Protocol stub only)
- Confirm `profile_invocation_executor.py` references `specify_cli.invocation.executor` (the shipped Phase 4 location) — not any old `specify_cli.next` path
- Confirm the `_EXCLUDED_FROM_LAYER_ENFORCEMENT` entry has a comment naming WP07 as the cleanup

## Activity Log

- 2026-04-22T21:14:12Z – claude:claude-sonnet-4-6:architect-alphonso:implementer – shell_pid=685569 – Started implementation via action command
- 2026-04-23T05:08:23Z – claude:claude-sonnet-4-6:architect-alphonso:implementer – shell_pid=685569 – Package skeleton + 3 seam Protocols: mypy --strict clean on 12 files, NullSink structural check passes, SC-5 stub in place
- 2026-04-23T05:08:59Z – claude:claude-sonnet-4-6:architect-alphonso:reviewer – shell_pid=753969 – Started review via action command
- 2026-04-23T05:10:33Z – claude:claude-sonnet-4-6:architect-alphonso:reviewer – shell_pid=753969 – Review passed: 8-package skeleton, 3 seam Protocols, mypy clean, no forbidden imports
