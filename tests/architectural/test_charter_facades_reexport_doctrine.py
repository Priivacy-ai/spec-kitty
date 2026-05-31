"""Architectural guard — charter facades re-export doctrine symbols by identity.

Each facade module under ``src/charter/`` that exists to proxy a doctrine
surface MUST re-export the exact doctrine object (object identity), not a
custom wrapper. This prevents a future PR from silently replacing a
re-export with a sneaky shim that drifts from doctrine.

Mission: ``charter-mediated-doctrine-selection-01KRTZCA``.
Contract: ``kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/charter-facade-modules.md``.

The table below mirrors the contract's "Symbol tables" section. When a
facade gains a new re-export, add the (symbol, doctrine-module) tuple here.
The parametrised test then asserts (a) the symbol exists on both modules
and (b) ``facade.SYMBOL is doctrine.SYMBOL`` (object identity).
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.architectural


# Mapping: charter facade module -> list of (symbol, doctrine source module).
# Keep in sync with contracts/charter-facade-modules.md "Symbol tables".
_FACADE_TABLE: dict[str, list[tuple[str, str]]] = {
    "charter.profiles": [
        ("AgentProfile", "doctrine.agent_profiles.profile"),
        ("Role", "doctrine.agent_profiles.profile"),
        ("AgentProfileRepository", "doctrine.agent_profiles.repository"),
        ("DEFAULT_ROLE_CAPABILITIES", "doctrine.agent_profiles.capabilities"),
    ],
    "charter.mission_steps": [
        ("MissionStep", "doctrine.missions.models"),
        ("MissionStepContract", "doctrine.missions.step_contracts"),
        ("MissionStepContractRepository", "doctrine.missions.step_contracts"),
        ("MissionStepContractStep", "doctrine.missions.step_contracts"),
    ],
    "charter.drg": [
        ("ArtifactKind", "doctrine.artifact_kinds"),
        ("DRGEdge", "doctrine.drg.models"),
        ("DRGGraph", "doctrine.drg.models"),
        ("DRGNode", "doctrine.drg.models"),
        ("NodeKind", "doctrine.drg.models"),
        ("Relation", "doctrine.drg.models"),
        ("load_graph", "doctrine.drg"),
        ("merge_layers", "doctrine.drg"),
        ("resolve_context", "doctrine.drg.query"),
        ("ResolvedContext", "doctrine.drg.query"),
    ],
    "charter.primitives": [
        ("PrimitiveExecutionContext", "doctrine.missions"),
        ("execute_with_glossary", "doctrine.missions"),
    ],
    "charter.resolution": [
        ("ResolutionResult", "doctrine.resolver"),
        ("ResolutionTier", "doctrine.resolver"),
    ],
    "charter.versioning": [
        ("BundleCompatibilityStatus", "doctrine.versioning"),
        ("CURRENT_BUNDLE_SCHEMA_VERSION", "doctrine.versioning"),
        ("check_bundle_compatibility", "doctrine.versioning"),
        ("get_bundle_schema_version", "doctrine.versioning"),
        ("run_migration", "doctrine.versioning"),
    ],
}


def _flat_cases() -> list[tuple[str, str, str]]:
    """Flatten the facade table into a list of (facade, symbol, doctrine) tuples."""
    return [
        (facade, symbol, doctrine)
        for facade, items in _FACADE_TABLE.items()
        for symbol, doctrine in items
    ]


@pytest.mark.parametrize(
    ("facade_module", "symbol", "doctrine_module"),
    _flat_cases(),
    ids=[f"{facade}.{symbol}" for facade, symbol, _ in _flat_cases()],
)
def test_facade_reexports_doctrine_symbol_by_identity(
    facade_module: str, symbol: str, doctrine_module: str
) -> None:
    """Each facade symbol MUST be the same object as its doctrine source.

    Identity (``is``) — not equality (``==``) — is the invariant. A facade
    that wraps, aliases, or copies a doctrine symbol is a contract violation.
    """
    facade = importlib.import_module(facade_module)
    doctrine = importlib.import_module(doctrine_module)
    facade_obj = getattr(facade, symbol)
    doctrine_obj = getattr(doctrine, symbol)
    assert facade_obj is doctrine_obj, (
        f"{facade_module}.{symbol} must be the same object as "
        f"{doctrine_module}.{symbol}. Facade modules are pure re-exports — "
        "no wrappers, no aliases, no shims. "
        f"Got facade={facade_obj!r}, doctrine={doctrine_obj!r}."
    )


@pytest.mark.parametrize("facade_module", sorted(_FACADE_TABLE.keys()))
def test_facade_all_lists_every_reexport(facade_module: str) -> None:
    """Every contract symbol MUST appear in the facade's ``__all__``.

    This catches the case where a future edit imports a new doctrine symbol
    into a facade but forgets to advertise it in ``__all__``, which would
    silently break ``from charter.<facade> import *`` callers and leave the
    public surface ambiguous.
    """
    facade = importlib.import_module(facade_module)
    all_ = getattr(facade, "__all__", None)
    assert all_ is not None, f"{facade_module} must define __all__"
    expected_symbols = {symbol for symbol, _ in _FACADE_TABLE[facade_module]}
    missing = expected_symbols - set(all_)
    assert not missing, (
        f"{facade_module}.__all__ is missing contract symbols: {sorted(missing)}. "
        f"Add them to __all__ or update the contract table."
    )
