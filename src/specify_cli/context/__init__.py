"""Canonical context module for bound identity resolution.

Public API
----------
- ``MissionContext`` -- Frozen dataclass binding project/mission/WP identity.
- ``ContextToken`` -- Lightweight reference to a persisted context file.
- ``resolve_context`` -- Build context from explicit wp_code + feature_slug.
- ``resolve_or_load`` -- Load from token or resolve from arguments.
- ``load_context`` -- Load a persisted context by token.
- ``save_context`` -- Persist a MissionContext to disk.
- ``context_callback`` -- Typer callback for ``--context <token>``.
- ``get_context`` -- Extract MissionContext from typer.Context.obj.
- ``require_context`` -- Decorator enforcing context availability.
"""

from specify_cli.context.errors import (
    ContextCorruptedError,
    ContextNotFoundError,
    ContextResolutionError,
    FeatureNotFoundError,
    MissingArgumentError,
    MissingIdentityError,
    WorkPackageNotFoundError,
)
from specify_cli.context.middleware import (
    context_callback,
    get_context,
    require_context,
)
from specify_cli.context.models import ContextToken, MissionContext
from specify_cli.context.resolver import resolve_context, resolve_or_load
from specify_cli.context.store import (
    delete_context,
    list_contexts,
    load_context,
    save_context,
)

__all__ = [
    "ContextCorruptedError",
    "ContextNotFoundError",
    "ContextResolutionError",
    "ContextToken",
    "FeatureNotFoundError",
    "MissingArgumentError",
    "MissingIdentityError",
    "MissionContext",
    "WorkPackageNotFoundError",
    "context_callback",
    "delete_context",
    "get_context",
    "list_contexts",
    "load_context",
    "require_context",
    "resolve_context",
    "resolve_or_load",
    "save_context",
]
