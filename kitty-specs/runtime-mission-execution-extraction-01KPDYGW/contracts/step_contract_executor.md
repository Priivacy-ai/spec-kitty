# Contract: StepContractExecutor Protocol

**Mission**: `runtime-mission-execution-extraction-01KPDYGW`
**FR**: FR-010
**Status**: Scaffolding seam — Phase 6 (#461) implements against this Protocol.

---

## Purpose

Runtime needs an execution-layer entry point that runs step contracts on behalf of profile invocations. This Protocol defines the typed interface Phase 6 (`StepContractExecutor`) will implement. This mission provides the scaffold only — no concrete implementation.

## Protocol Definition

```python
from __future__ import annotations
from typing import Any, Protocol


class StepContractExecutor(Protocol):
    """Execution-layer entry point for step contract execution.

    Phase 6 of #461 provides a concrete implementation.
    Runtime references this Protocol to describe the seam without
    depending on the implementation.

    Type aliases (Any) will be narrowed by Phase 6 once StepContract,
    ExecutionContext, and StepResult data models are defined.
    """

    def execute(
        self,
        step_contract: Any,   # Phase 6: StepContract
        context: Any,         # Phase 6: ExecutionContext
    ) -> Any:                 # Phase 6: StepResult
        """Execute the step contract and return its result.

        Args:
            step_contract: The step definition from mission artefacts.
            context: Runtime state at execution time (WP, lane, profile, etc.).

        Returns:
            The result of executing the step (structured per Phase 6 data model).
        """
        ...
```

## Minimal Type-Check Stub (validates SC-5)

The following stub proves the Protocol compiles and type-checks. WP02 T007 must include this as an inline check:

```python
from runtime.seams.step_contract_executor import StepContractExecutor
from typing import Any

class _Phase6StubExecutor:
    """Minimal stub proving the Protocol can be satisfied."""
    def execute(self, step_contract: Any, context: Any) -> Any:
        raise NotImplementedError("Phase 6 not yet implemented")

# If mypy --strict passes on this file, SC-5 is satisfied for this Protocol.
_stub: StepContractExecutor = _Phase6StubExecutor()
```

Running `mypy --strict` on the stub file is the SC-5 validation gate.

## Integration with Runtime

When Phase 6 is ready, it injects a concrete `StepContractExecutor` into the relevant runtime function. The injection point in `src/runtime/` (likely in `bridge/runtime_bridge.py`) should already accept the Protocol type so Phase 6 can plug in without a runtime refactor:

```python
# Example future call site in runtime_bridge.py
def execute_next_step(
    step_contract: Any,
    context: Any,
    executor: StepContractExecutor,
) -> Any:
    return executor.execute(step_contract, context)
```

## Scope Boundary

This mission **only** defines the Protocol stub. The `execute` method body is intentionally `...`. Phase 6 will:
1. Define `StepContract`, `ExecutionContext`, `StepResult` data classes
2. Implement `StepContractExecutor` concretely
3. Wire the implementation into `runtime_bridge.py` via the injection point
