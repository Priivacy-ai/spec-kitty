"""Charter Synthesizer adapter seam.

Defines SynthesisAdapter (runtime-checkable Protocol) and AdapterOutput
(frozen dataclass) — the narrow, frozen boundary between deterministic
orchestration and model-driven generation.

This file is the frozen seam contract. Changes to SynthesisAdapter or
AdapterOutput require an ADR amendment (ADR-2026-04-17-1, KD-3, KD-6).

See also: kitty-specs/phase-3-charter-synthesizer-pipeline-01KPE222/contracts/adapter.py
The contract file and this module expose structurally identical shapes;
test_adapter_contract.py::test_contract_structural_equivalence verifies this.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from collections.abc import Mapping, Sequence

from .request import SynthesisRequest


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdapterOutput:
    """What an adapter returns from generate().

    See data-model.md §E-3 for full field documentation.

    adapter_id_override / adapter_version_override support long-lived adapters
    that rotate underlying models — the orchestrator records whichever identity
    was effective for the call (override-first, fallback to adapter.id / .version).
    """

    body: Mapping[str, Any]
    """Artifact body matching the shipped-layer Pydantic schema for the target kind."""

    generated_at: datetime
    """When the adapter produced this output. Must be timezone-aware UTC."""

    adapter_id_override: str | None = None
    """Optional per-call identity override (KD-3). None → use adapter.id."""

    adapter_version_override: str | None = None
    """Optional per-call version override (KD-3). None → use adapter.version."""

    notes: str | None = None
    """Optional human-readable adapter note; recorded in provenance verbatim."""


# ---------------------------------------------------------------------------
# The seam
# ---------------------------------------------------------------------------


@runtime_checkable
class SynthesisAdapter(Protocol):
    """Narrow, synchronous, provider-agnostic interface for artifact generation.

    Implementations MUST:
    - Expose `id` and `version` as string attributes.
    - Implement `generate(request) -> AdapterOutput` synchronously.
    - Be synchronous — no asyncio in this tranche (KD-3).

    Implementations MAY:
    - Implement `generate_batch(requests) -> Sequence[AdapterOutput]` for
      efficiency. Orchestration detects presence via hasattr at runtime and
      uses it when available.

    Implementations MUST NOT:
    - Carry prompt-engineering logic, retry policy, or model parameters into
      orchestration — those belong inside adapter implementations.
    - Accept or return anything not in this contract without an ADR amendment.
    """

    id: str
    """Stable adapter identifier (e.g. 'fixture', 'claude-3-7-sonnet')."""

    version: str
    """Adapter version string (e.g. '1.0.0', 'claude-3-7-sonnet-20250219')."""

    def generate(self, request: SynthesisRequest) -> AdapterOutput:
        """Produce a single artifact body for the given request.

        Fixture adapters MUST produce byte-identical output for byte-identical
        normalized input. Production adapters are not required to be
        byte-identical across calls, but MUST carry enough identity in
        AdapterOutput for provenance to be meaningful.
        """
        ...


# ---------------------------------------------------------------------------
# Optional batch-capable extension (documentation / static-analysis aid)
# ---------------------------------------------------------------------------


class BatchCapableSynthesisAdapter(SynthesisAdapter, Protocol):
    """Optional batch extension.

    Orchestration detects generate_batch via hasattr rather than type-narrowing,
    so adapters do NOT need to declare they implement this Protocol. This class
    exists purely as documentation / static analysis aid.
    """

    def generate_batch(
        self, requests: Sequence[SynthesisRequest]
    ) -> Sequence[AdapterOutput]:
        """Produce outputs for a batch of requests.

        Returned sequence MUST be the same length as the input sequence and
        element-aligned. If any one request cannot be satisfied, the adapter
        MUST raise rather than returning a partial sequence.
        """
        ...
