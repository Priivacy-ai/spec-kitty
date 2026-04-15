"""Glossary runner protocol and registry.

This module defines the ``GlossaryRunnerProtocol`` — the abstract contract
that any concrete glossary-aware primitive runner must satisfy — and a
module-level registry so that ``doctrine`` can invoke the runner without
depending on ``specify_cli``.

Dependency direction
--------------------
::

    doctrine  →  kernel.glossary_runner  ←  specify_cli

``doctrine`` calls ``get_runner()`` to obtain whatever runner
``specify_cli`` has registered.  ``specify_cli`` calls ``register()`` at
import time to install the concrete ``GlossaryAwarePrimitiveRunner``.

If no runner has been registered, ``get_runner()`` returns ``None`` and
``doctrine`` falls back to calling the primitive directly (graceful
degradation when spec-kitty is not the host, e.g. in tests or third-party
integrations).

Usage — consumer (doctrine)::

    from kernel.glossary_runner import get_runner

    runner_cls = get_runner()
    if runner_cls is not None:
        runner = runner_cls(repo_root=repo_root, ...)
        return runner.execute(primitive_fn, context, *args, **kwargs)
    return primitive_fn(context, *args, **kwargs)

Usage — provider (specify_cli)::

    from kernel.glossary_runner import register
    from specify_cli.glossary.attachment import GlossaryAwarePrimitiveRunner

    register(GlossaryAwarePrimitiveRunner)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class GlossaryRunnerProtocol(Protocol):
    """Contract for a glossary-aware primitive runner.

    Any class registered via ``register()`` must satisfy this protocol.
    """

    def __init__(
        self,
        repo_root: Path,
        runtime_strictness: Any | None = None,
        interaction_mode: str = "interactive",
    ) -> None: ...

    def execute(
        self,
        primitive_fn: Any,
        context: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...


# Module-level registry slot — holds the concrete runner class or None.
_registry: type[GlossaryRunnerProtocol] | None = None


def register(runner_cls: type[GlossaryRunnerProtocol]) -> None:
    """Register the concrete glossary runner class.

    Called by ``specify_cli`` at import time.  Calling this more than once
    with the same class is a no-op.  Calling it with a different class
    raises ``RuntimeError`` to catch accidental double-registration.

    Args:
        runner_cls: A class satisfying ``GlossaryRunnerProtocol``.

    Raises:
        TypeError: If ``runner_cls`` does not satisfy the protocol.
        RuntimeError: If a *different* runner class is already registered.
    """
    global _registry  # noqa: PLW0603

    if not isinstance(runner_cls, type):
        raise TypeError(f"runner_cls must be a class, got {type(runner_cls)!r}")

    if _registry is runner_cls:
        # Idempotent: same class registered twice (e.g. re-import) is fine.
        return

    if _registry is not None:
        raise RuntimeError(f"A different glossary runner is already registered: {_registry!r}. Cannot register {runner_cls!r}.")

    _registry = runner_cls


def get_runner() -> type[GlossaryRunnerProtocol] | None:
    """Return the registered glossary runner class, or None if none registered.

    Returns:
        The registered runner class, or ``None``.
    """
    return _registry


def clear_registry() -> None:
    """Reset the registry to None.

    Intended for use in tests only.  Do not call in production code.
    """
    global _registry  # noqa: PLW0603
    _registry = None


__all__ = [
    "GlossaryRunnerProtocol",
    "register",
    "get_runner",
    "clear_registry",
]
