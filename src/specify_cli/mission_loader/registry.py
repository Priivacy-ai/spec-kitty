"""In-memory runtime contract registry (R-004, FR-006, FR-008).

Provides a per-process shadow that overlays the on-disk
:class:`MissionStepContractRepository` for the lifetime of a custom
mission run. Inside the
:func:`registered_runtime_contracts` ``with`` block, contract lookups
resolve against the shadow first and fall through to the on-disk
repository only when the shadow does not contain the id. Outside the
``with`` block the shadow is empty and every lookup goes straight to
the repository.

The registry is intentionally simple:

* It is a process-local singleton; the CLI is single-threaded so we do
  not introduce locking. If the runtime ever grows a thread/async
  worker pool, this module should grow a lock at the same time.
* The on-disk repository is never mutated. Synthesized contracts live
  only in memory and disappear when the outermost ``with`` block exits.
* Nested ``with`` blocks compose via a stack-of-snapshots model: each
  ``__enter__`` snapshots the current shadow before registering its
  contracts, and ``__exit__`` restores that snapshot. So an inner block
  that registers ``B`` over an outer block that registered ``A`` sees
  both ``A`` and ``B`` while inside; on inner exit only ``B`` is
  removed and ``A`` remains visible until the outer block exits.

WP03 only provides the façade :func:`lookup_contract`. WP04 owns the
wiring change that routes
:class:`~doctrine.mission_step_contracts.executor.StepContractExecutor`
through this façade. Until WP04 lands, the executor still calls
``repository.get(...)`` directly and the shadow is unused at runtime.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable, Iterator

from doctrine.mission_step_contracts.models import MissionStepContract
from doctrine.mission_step_contracts.repository import MissionStepContractRepository

from specify_cli.mission_loader.contract_synthesis import synthesize_contracts
from specify_cli.next._internal_runtime.schema import MissionTemplate


class RuntimeContractRegistry:
    """In-memory overlay over :class:`MissionStepContractRepository`.

    Lifetime is bounded by the
    :func:`registered_runtime_contracts` ``with`` block. Lookups inside
    the block are shadow-first; lookups outside the block hit only the
    repository (the shadow is empty).

    The CLI is single-threaded, so this registry is not thread-safe. If
    a future caller spawns concurrent runtime tasks they MUST add their
    own synchronization or rework this module to be thread-safe.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, MissionStepContract] = {}

    def register(self, contracts: Iterable[MissionStepContract]) -> None:
        """Add ``contracts`` to the in-memory shadow keyed by ``contract.id``.

        Re-registering the same id overwrites the prior entry. Callers
        typically pass the result of
        :func:`specify_cli.mission_loader.contract_synthesis.synthesize_contracts`.
        """
        for contract in contracts:
            self._contracts[contract.id] = contract

    def lookup(self, contract_id: str) -> MissionStepContract | None:
        """Return the shadowed contract for ``contract_id`` or ``None``."""
        return self._contracts.get(contract_id)

    def clear(self) -> None:
        """Drop every entry from the shadow."""
        self._contracts.clear()

    def snapshot(self) -> dict[str, MissionStepContract]:
        """Return a shallow copy of the current shadow.

        Used by :func:`registered_runtime_contracts` to stash state
        before each nested ``with`` block so it can be restored on exit.
        """
        return dict(self._contracts)

    def restore(self, snapshot: dict[str, MissionStepContract]) -> None:
        """Replace the shadow with ``snapshot`` (a previous ``snapshot()``)."""
        self._contracts = dict(snapshot)


# Module-level singleton. Created lazily so import-time side effects stay
# minimal; ``get_runtime_contract_registry`` is the only sanctioned
# accessor and the only place this name is read or written.
_REGISTRY: RuntimeContractRegistry | None = None


def get_runtime_contract_registry() -> RuntimeContractRegistry:
    """Return the process-local :class:`RuntimeContractRegistry` singleton."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = RuntimeContractRegistry()
    return _REGISTRY


@contextlib.contextmanager
def registered_runtime_contracts(
    template: MissionTemplate,
) -> Iterator[RuntimeContractRegistry]:
    """Register synthesized contracts for ``template`` for the block lifetime.

    On enter:
      * snapshots the current shadow,
      * synthesizes contracts via :func:`synthesize_contracts`,
      * registers them in the singleton registry.

    On exit:
      * restores the snapshot, which removes only the contracts this
        block added (a stack-of-snapshots model that nests cleanly).

    Yields the singleton registry for ergonomic use inside the block.
    """
    registry = get_runtime_contract_registry()
    snapshot = registry.snapshot()
    registry.register(synthesize_contracts(template))
    try:
        yield registry
    finally:
        registry.restore(snapshot)


def lookup_contract(
    contract_id: str,
    repository: MissionStepContractRepository,
) -> MissionStepContract | None:
    """Resolve ``contract_id`` against the runtime registry, then ``repository``.

    Resolution order:

    1. The runtime registry shadow (precedence inside a
       :func:`registered_runtime_contracts` block).
    2. ``repository.get(contract_id)`` -- the on-disk record.

    :class:`MissionStepContractRepository.get` returns ``None`` on miss
    (it is implemented over ``dict.get``); but we still wrap the call
    in a defensive ``try/except`` so that any exotic repository
    implementation that raises on miss does not propagate through this
    façade. WP04 will route ``StepContractExecutor`` lookups through
    here so callers do not need to know about the registry.
    """
    registry = get_runtime_contract_registry()
    hit = registry.lookup(contract_id)
    if hit is not None:
        return hit
    try:
        return repository.get(contract_id)
    except Exception:  # noqa: BLE001 -- repository may raise on unknown id
        return None


__all__ = [
    "RuntimeContractRegistry",
    "get_runtime_contract_registry",
    "lookup_contract",
    "registered_runtime_contracts",
]
