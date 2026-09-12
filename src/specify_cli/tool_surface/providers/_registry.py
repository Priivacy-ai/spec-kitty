"""Self-registration registry for tool-surface providers.

Each provider module calls :func:`SurfaceProviderRegistry.register` at module
scope with a :class:`SurfaceRegistration` describing its provider class,
surface definitions, and operator-facing kind tokens.  Importing
``providers._discovery`` fires all registrations so callers in ``service.py``
receive a fully populated registry.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..enums import ToolSurfaceKind
    from ..model import SurfaceDefinition
    from ..registry import ToolSurfaceRegistry
    from .protocol import ReportingSurfaceProvider


@dataclass(frozen=True)
class SurfaceRegistration:
    """Declaration unit produced by each provider module at import time.

    Attributes:
        provider_class: The provider implementation class.
        definitions: Pre-built :class:`SurfaceDefinition` instances declared by
            this provider.  Stored as a tuple so the dataclass remains hashable.
        kind_tokens: Operator-facing ``--kind`` token strings mapped to their
            :class:`ToolSurfaceKind` values.  A single provider may declare multiple
            tokens (e.g. both ``"context-file"`` and ``"context_file"``).
        synthetic_key: When set, definitions are registered once under this key
            instead of being fanned out across every configured tool key.  Used
            by the ``plugin_bundle`` provider which aggregates across all tools.
        order: Tie-breaking integer that determines provider ordering within the
            registry.  Each registration must declare a unique order value.
    """

    provider_class: type[ReportingSurfaceProvider]
    definitions: tuple[SurfaceDefinition, ...]
    kind_tokens: dict[str, ToolSurfaceKind]
    synthetic_key: str | None = None
    order: int = 0


class SurfaceProviderRegistry:
    """Aggregates :class:`SurfaceRegistration` instances at import time.

    Provider modules call :meth:`register` at module scope so importing them
    is sufficient to populate the registry.  :mod:`providers._discovery` holds
    the explicit import tuple that fires all registrations.
    """

    _registrations: list[SurfaceRegistration] = []

    @classmethod
    def register(cls, reg: SurfaceRegistration) -> None:
        """Add *reg* to the registry.

        Raises:
            ValueError: If another registration already claims the same
                ``order`` value (prevents silent ordering collisions).
        """
        orders = {r.order for r in cls._registrations}
        if reg.order in orders:
            raise ValueError(
                f"Duplicate SurfaceRegistration order: {reg.order}. "
                f"Each provider must declare a unique order."
            )
        cls._registrations.append(reg)

    @classmethod
    def _sorted(cls) -> list[SurfaceRegistration]:
        """Return registrations sorted ascending by ``order``."""
        return sorted(cls._registrations, key=lambda r: r.order)

    @classmethod
    def build_kind_tokens(cls) -> dict[str, ToolSurfaceKind]:
        """Merge all provider kind-token dicts, sorted by registration order.

        Later registrations (higher ``order``) overwrite earlier ones for
        any token key they share.
        """
        result: dict[str, ToolSurfaceKind] = {}
        for reg in cls._sorted():
            result.update(reg.kind_tokens)
        return result

    @classmethod
    def build_providers(cls) -> list[ReportingSurfaceProvider]:
        """Instantiate one provider per registration, sorted by order."""
        return [reg.provider_class() for reg in cls._sorted()]

    @classmethod
    def build_registry(cls, tool_keys: Sequence[str]) -> ToolSurfaceRegistry:
        """Build a :class:`ToolSurfaceRegistry` populated with built-in definitions.

        For providers **without** a ``synthetic_key``: each definition is
        registered once per entry in *tool_keys*.

        For providers **with** a ``synthetic_key`` (``plugin_bundle``): all
        definitions are registered once under the synthetic key,
        unconditionally — regardless of membership in *tool_keys*.

        Args:
            tool_keys: The set of configured tool identifiers for the current
                session (e.g. ``["codex", "claude"]``).

        Returns:
            A populated :class:`ToolSurfaceRegistry`.
        """
        from ..registry import ToolSurfaceRegistry  # local to avoid top-level cycle

        registry = ToolSurfaceRegistry()
        for reg in cls._sorted():
            if reg.synthetic_key is not None:
                # Unconditional: register once under the synthetic key.
                for defn in reg.definitions:
                    registry.register_definition(reg.synthetic_key, defn)
            else:
                for tool_key in tool_keys:
                    for defn in reg.definitions:
                        registry.register_definition(tool_key, defn)
        return registry
