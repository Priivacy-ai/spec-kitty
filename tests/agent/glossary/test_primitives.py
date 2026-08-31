"""Compatibility guard for the historical mission-primitives import."""

from charter.offering.missions.primitives import PrimitiveExecutionContext as CanonicalContext
from specify_cli.missions import PrimitiveExecutionContext as CompatibilityContext


def test_compatibility_context_is_canonical_context() -> None:
    """Existing importers receive the doctrine class, not a copied wrapper."""
    assert CompatibilityContext is CanonicalContext
