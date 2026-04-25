"""StepContractExecutor seam — #461 Phase 6 implementation target.

Runtime exposes this Protocol as the execution-layer entry point.
Phase 6 (StepContractExecutor) wires a concrete implementation here.
Runtime itself never implements this Protocol.
"""
from __future__ import annotations
from typing import Any, Protocol, TYPE_CHECKING


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


# SC-5 validation stub (TYPE_CHECKING guard keeps it out of runtime)
if TYPE_CHECKING:
    class _Phase6StubExecutor:
        def execute(self, step_contract: Any, context: Any) -> Any: ...

    _stub: StepContractExecutor = _Phase6StubExecutor()
