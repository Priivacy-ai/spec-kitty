"""Directive-030 conformance tests for tool-surface provider self-registration.

These tests assert two structural invariants that guard the self-registration
seam established in WP03/WP04:

1. **Registration completeness** — importing :mod:`_discovery` fires exactly one
   :class:`SurfaceRegistration` per provider module (7 total), and every
   registration carries at least one definition and one kind token.
2. **Directive-030** — ``service.py`` delegates provider assembly to the
   registry and contains no central provider literal list (a hardcoded
   ``[AgentProfilesProvider(), ...]`` would defeat self-registration).

The completeness test reads the live, module-scoped registrations populated by
importing the production ``_discovery`` module; it does not mutate
:data:`SurfaceProviderRegistry._registrations`, so no ``monkeypatch`` restore is
required.  (Tests that *mutate* the shared registry — see
``providers/test_registry.py`` — use ``monkeypatch`` to isolate state.)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import specify_cli.tool_surface.service as service_module

# Importing ``_discovery`` fires every provider module's module-scoped
# ``SurfaceProviderRegistry.register(...)`` call.  Import it explicitly (rather
# than relying on transitive imports) so the completeness assertions below run
# against the fully populated registry regardless of import ordering.
from specify_cli.tool_surface.providers import _discovery  # noqa: F401
from specify_cli.tool_surface.providers._registry import SurfaceProviderRegistry

pytestmark = [pytest.mark.unit, pytest.mark.fast]

EXPECTED_PROVIDER_COUNT = 7


def test_all_providers_registered() -> None:
    """Every provider module contributes exactly one well-formed registration."""
    registrations = SurfaceProviderRegistry._registrations

    assert len(registrations) == EXPECTED_PROVIDER_COUNT, (
        f"Expected {EXPECTED_PROVIDER_COUNT} provider registrations, "
        f"found {len(registrations)}: "
        f"{sorted(r.provider_class.__name__ for r in registrations)}"
    )

    # Each registration maps to a distinct provider class.
    classes = {reg.provider_class for reg in registrations}
    assert len(classes) == EXPECTED_PROVIDER_COUNT, (
        "Duplicate provider classes registered: "
        f"{sorted(c.__name__ for c in classes)}"
    )

    for reg in registrations:
        assert len(reg.definitions) >= 1, (
            f"{reg.provider_class.__name__} registered with no definitions"
        )
        assert len(reg.kind_tokens) >= 1, (
            f"{reg.provider_class.__name__} registered with no kind_tokens"
        )


def test_registration_orders_are_unique() -> None:
    """Order values must be unique so provider sequencing is deterministic."""
    orders = [reg.order for reg in SurfaceProviderRegistry._registrations]
    assert len(orders) == len(set(orders)), (
        f"Duplicate registration order values detected: {sorted(orders)}"
    )


def _service_source() -> str:
    """Return ``service.py`` source, resolved from the imported module path.

    Resolving via ``service_module.__file__`` keeps the check correct regardless
    of the working directory pytest is invoked from.
    """
    service_path = Path(service_module.__file__)
    return service_path.read_text(encoding="utf-8")


def _list_with_provider_calls(node: ast.AST) -> ast.List | None:
    """Return the first list literal whose elements call ``*Provider(...)``.

    Detects the pre-refactor pattern ``[AgentProfilesProvider(), ...]`` — a list
    literal whose elements are calls to a name ending in ``Provider``.
    """
    for child in ast.walk(node):
        if not isinstance(child, ast.List) or not child.elts:
            continue
        for elt in child.elts:
            if (
                isinstance(elt, ast.Call)
                and isinstance(elt.func, ast.Name)
                and elt.func.id.endswith("Provider")
            ):
                return child
    return None


def test_service_py_has_no_central_provider_literals() -> None:
    """``service.py`` must delegate provider assembly to the registry (Directive-030)."""
    tree = ast.parse(_service_source())

    build_providers = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "build_providers"
        ),
        None,
    )
    assert build_providers is not None, (
        "service.py no longer defines build_providers(); update this conformance "
        "test if the delegation surface was intentionally renamed."
    )

    offending = _list_with_provider_calls(build_providers)
    assert offending is None, (
        "service.py build_providers() contains a central provider list literal "
        f"(line {offending.lineno}) — registry self-registration not used "
        "(Directive-030)."
    )
