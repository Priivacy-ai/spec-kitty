"""``MissionResolver`` port: handle -> mission identity resolution (#2173 Phase-2).

This module defines the *shell-side* seam for resolving a user-supplied mission
handle (ULID / mid8 / numbered slug / human slug / numeric prefix) to a
:class:`ResolvedMissionLike` value, without depending on any concrete
filesystem walk. It is the Protocol half of the port; the real adapter
(``FsMissionResolver``, wrapping the existing ``kitty-specs/`` walk) and the
in-memory stub (``FakeMissionResolver``) live in
``specify_cli.context.mission_resolver`` beside the walk they wrap.

Why this Protocol lives in ``mission_runtime`` and not beside its adapters
(D-Q2, revised post-squad): the shell (``mission_runtime.resolution``) needs a
local type to type its ``resolver`` parameters against without creating a new
``mission_runtime -> specify_cli.context`` import edge — ``"context"`` is not
in the ``_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI`` ledger
(``tests/architectural/test_layer_rules.py``), and that ledger's AST scan walks
*every* import (including lazy, function-scoped, and ``TYPE_CHECKING``-guarded
ones), so there is no way to import the concrete ``ResolvedMission`` dataclass
here without adding a new ledger entry. Instead, ``ResolvedMissionLike`` below
is a *structural* mirror of ``specify_cli.context.mission_resolver.ResolvedMission``
(``mission_id`` / ``mission_slug`` / ``feature_dir`` / ``mid8``): the concrete
dataclass satisfies it by shape alone (mypy structural typing), with no
inheritance and no runtime import required in either direction.

Adapters import this Protocol via the allowed, opposite-direction edge
(``specify_cli -> mission_runtime``, through the package root
``from mission_runtime import MissionResolver``) — the same direction already
used by ``specify_cli.context.resolver``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

__all__ = ["MissionResolver"]
# ResolvedMissionLike is intentionally NOT in __all__: it exists only to type
# MissionResolver's own method signatures within this module. No other src/
# file needs to import it directly (tests/architectural/test_no_dead_symbols.py
# FR-303 flags exported-but-unimported symbols as dead).


class ResolvedMissionLike(Protocol):
    """Structural shape mirroring ``context.mission_resolver.ResolvedMission``.

    Any object with these four **read-only** attributes satisfies this
    Protocol — the concrete frozen dataclass in
    ``specify_cli.context.mission_resolver`` does so without inheriting from
    it. Members are declared via ``@property`` (not plain class-level
    annotations) because a plain annotation declares a *settable* Protocol
    member, which a frozen dataclass's read-only fields do not structurally
    satisfy; a property-only getter matches read-only attributes.
    """

    @property
    def mission_id(self) -> str: ...

    @property
    def mission_slug(self) -> str: ...

    @property
    def feature_dir(self) -> Path: ...

    @property
    def mid8(self) -> str: ...


class MissionResolver(Protocol):
    """Handle -> mission identity resolution, injectable at the shell.

    Implementations MUST be fail-closed-loud (FR-005): an ambiguous handle
    raises rather than picking a first match, and a cold-miss (no match at any
    priority level) raises a structured not-found error naming
    ``spec-kitty migrate backfill-identity`` — never a silent
    ``is None`` / ``or slug`` fallback.

    Implementations MUST be request-scoped: no ``@lru_cache`` or module/process
    -level cache of the underlying walk (C-005). Instance-lifetime memoization
    is permitted.
    """

    def resolve(self, handle: str) -> ResolvedMissionLike:
        """Resolve ``handle`` to the single mission it identifies.

        Raises:
            Implementation-defined ambiguity error when ``handle`` matches more
                than one mission.
            Implementation-defined not-found error when ``handle`` matches no
                mission at any priority level.
        """
        ...

    def all_missions(self) -> Sequence[ResolvedMissionLike]:
        """Return every resolvable mission (identity-bearing missions only).

        Missions without a resolvable identity (e.g. legacy missions missing
        ``mission_id``) are silently omitted here — the same contract as the
        existing ``_build_index`` walk — so ``status/identity_audit.py``'s
        separate, non-routed walk remains the only surface that sees them.

        Typed as ``Sequence`` rather than ``list``: ``list`` is invariant, so
        an adapter returning ``list[ResolvedMission]`` (the concrete subtype)
        would not structurally satisfy a ``list[ResolvedMissionLike]``-typed
        member; ``Sequence`` is covariant and accepts it.
        """
        ...
