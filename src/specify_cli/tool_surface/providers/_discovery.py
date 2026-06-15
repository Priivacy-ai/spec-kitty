"""Explicit provider discovery — imports all provider modules to fire their registrations.

Importing this module causes each provider module to execute its module-level
:meth:`~._registry.SurfaceProviderRegistry.register` call, populating
:class:`~._registry.SurfaceProviderRegistry` before any call to
``build_kind_tokens()``, ``build_providers()``, or ``build_registry()``.

This module must use an explicit import tuple, not ``pkgutil``, to remain
compatible with the project's dead-symbol static analysis gate (C-001).

Note: at WP03 stage, providers have not yet been updated to call
``SurfaceProviderRegistry.register()`` — that is WP04's job.  The imports
succeed because the modules exist; the registry remains empty until WP04 wires
the registration calls.  This is intentional and expected.
"""

from __future__ import annotations

from . import (
    agent_profiles,
    command_skills,
    managed_skills,
    native_config,
    plugin_bundle,
    session_presence,
    slash_commands,
)

# Explicit tuple ensures each module is referenced as a named symbol,
# keeping the dead-symbol gate (C-001) satisfied.
_PROVIDERS = (
    agent_profiles,
    command_skills,
    managed_skills,
    native_config,
    plugin_bundle,
    session_presence,
    slash_commands,
)
