"""
Adapter interface for AI agents (Gemini, Cursor, etc.).

This package provides the ObserveDecideAdapter protocol and implementations
for normalizing agent output into canonical collaboration events.

S1/M1 Scope: Baseline stubs (Gemini, Cursor) with tested parsing for common scenarios.
Full production hardening continues post-S1/M1.
"""

from typing import Dict
from specify_cli.adapters.observe_decide import ObserveDecideAdapter
from specify_cli.adapters.gemini import GeminiObserveDecideAdapter
from specify_cli.adapters.cursor import CursorObserveDecideAdapter

__all__ = [
    "ObserveDecideAdapter",
    "GeminiObserveDecideAdapter",
    "CursorObserveDecideAdapter",
    "register_adapter",
    "get_adapter",
    "list_adapters",
]

_registry: Dict[str, ObserveDecideAdapter] = {}


def register_adapter(name: str, adapter: ObserveDecideAdapter) -> None:
    """Register adapter instance."""
    # Runtime protocol check (Python 3.11+)
    if not all(hasattr(adapter, method) for method in [
        "normalize_actor_identity", "parse_observation",
        "detect_decision_request", "format_decision_answer", "healthcheck"
    ]):
        raise TypeError(f"Adapter {name} does not implement ObserveDecideAdapter protocol")

    _registry[name] = adapter


def get_adapter(name: str) -> ObserveDecideAdapter:
    """Get registered adapter."""
    if name not in _registry:
        raise KeyError(f"Adapter not found: {name}. Available: {list_adapters()}")
    return _registry[name]


def list_adapters() -> list[str]:
    """List registered adapter names."""
    return sorted(_registry.keys())


# Pre-register adapters
register_adapter("gemini", GeminiObserveDecideAdapter())
register_adapter("cursor", CursorObserveDecideAdapter())
