"""Invocation context module for the ``charter.*`` package.

Defines three dataclasses: ``ContextPreconditionError``, ``ProjectContext``,
and ``OperationalContext``.  ``ProjectContext`` provides a ``from_repo()``
factory that produces fully-populated instances from a repository root path.
Guard methods on both context types raise ``ContextPreconditionError``
(not ``ValueError``) when a required field is absent.

``OperationalContext`` is specced here but not wired to any production call
site — it is an in-flight stub whose symbols are explicitly allowlisted in
the dead-symbol architectural test so the ratchet does not reject them.

Layer rule
----------
This module MUST NOT import from ``specify_cli`` (C-001, hard ratchet pinned
by ``tests/architectural/test_layer_rules.py``).  ``PackContext`` is imported
only under ``TYPE_CHECKING`` at the module level and via a runtime import
inside ``from_repo()`` to avoid circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from charter.pack_context import PackContext


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextPreconditionError(RuntimeError):
    """Raised by context guard methods when a required field is absent."""

    field: str
    context_type: str

    def __str__(self) -> str:
        return (
            f"Context precondition failed: '{self.field}' is required "
            f"but absent in {self.context_type}"
        )

    def __post_init__(self) -> None:
        # Ensure the RuntimeError base receives the message string so that
        # callers catching RuntimeError and calling str(exc) get a useful message.
        super().__init__(str(self))


# ---------------------------------------------------------------------------
# ProjectContext
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectContext:
    """Resolved context for a spec-kitty project.

    All fields are optional so instances can be constructed partially
    in tests and in partial-discovery scenarios.
    ``from_repo()`` always returns a fully-populated instance.
    """

    repo_root: Path | None = None
    pack_context: PackContext | None = None
    org_root: Path | None = None
    specs_dir: Path | None = None
    architecture_dir: Path | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_repo(cls, repo_root: Path) -> ProjectContext:
        """Construct a fully-populated ProjectContext from a repository root.

        Resolves PackContext via ``PackContext.from_config()``.
        Resolves ``org_root`` as the first entry from ``resolve_org_roots()``
        if any are found; ``None`` otherwise.
        ``specs_dir`` and ``architecture_dir`` are set only when the
        corresponding directories exist on disk.
        """
        from charter.pack_context import PackContext  # runtime import — avoids circular

        try:
            from doctrine.drg.org_pack_config import resolve_org_roots  # noqa: PLC0415

            org_roots = resolve_org_roots(repo_root)
            org_root: Path | None = org_roots[0] if org_roots else None
        except Exception:
            org_root = None

        pack_ctx = PackContext.from_config(repo_root)

        specs_path = repo_root / "kitty-specs"
        arch_path = repo_root / "architecture"

        return cls(
            repo_root=repo_root,
            pack_context=pack_ctx,
            org_root=org_root,
            specs_dir=specs_path if specs_path.is_dir() else None,
            architecture_dir=arch_path if arch_path.is_dir() else None,
        )

    # ------------------------------------------------------------------
    # Guard methods
    # ------------------------------------------------------------------

    def require_repo_root(self) -> Path:
        """Return ``repo_root`` or raise ``ContextPreconditionError``."""
        if self.repo_root is None:
            raise ContextPreconditionError(
                field="repo_root", context_type="ProjectContext"
            )
        return self.repo_root

    def require_pack_context(self) -> PackContext:
        """Return ``pack_context`` or raise ``ContextPreconditionError``."""
        if self.pack_context is None:
            raise ContextPreconditionError(
                field="pack_context", context_type="ProjectContext"
            )
        return self.pack_context

    def require_org_root(self) -> Path:
        """Return ``org_root`` or raise ``ContextPreconditionError``."""
        if self.org_root is None:
            raise ContextPreconditionError(
                field="org_root", context_type="ProjectContext"
            )
        return self.org_root


# ---------------------------------------------------------------------------
# OperationalContext
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperationalContext:
    """Runtime context about the active agent session.

    Stub — wiring to a live resolver is deferred to a follow-on mission
    (charter-pack-activation-layer WP03).
    """

    active_model: str | None = None
    active_profile: str | None = None
    active_role: str | None = None
    current_activity: str | None = None
    tech_stack: frozenset[str] = field(default_factory=frozenset)

    # ------------------------------------------------------------------
    # Guard methods
    # ------------------------------------------------------------------

    def require_active_profile(self) -> str:
        """Return ``active_profile`` or raise ``ContextPreconditionError``."""
        if self.active_profile is None:
            raise ContextPreconditionError(
                field="active_profile", context_type="OperationalContext"
            )
        return self.active_profile

    def require_active_role(self) -> str:
        """Return ``active_role`` or raise ``ContextPreconditionError``."""
        if self.active_role is None:
            raise ContextPreconditionError(
                field="active_role", context_type="OperationalContext"
            )
        return self.active_role


# ---------------------------------------------------------------------------
# Module-level stub factory
# ---------------------------------------------------------------------------


def build_operational_context() -> OperationalContext:
    """Stub factory — wiring to a live resolver is deferred to a follow-on mission."""
    return OperationalContext()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "ContextPreconditionError",
    "OperationalContext",
    "ProjectContext",
    "build_operational_context",
]
