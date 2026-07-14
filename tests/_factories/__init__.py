"""Production-delegating test factories (FR-008 / E-06 / IC-07, issue #2074).

``make_mission()`` is a thin wrapper over
:func:`specify_cli.core.mission_creation.create_mission_core` -- the
documented programmatic mission-creation API (spec A-002) -- so tests get a
production-shaped ``meta.json`` from the single schema authority instead of
hand-rolling a meta dict per test module. Those hand-rolled fixtures (the
329-writer tail referenced in the mission spec) are NOT migrated here
(Directive 024); this factory is purely additive for new/updated tests that
want production-shaped fixtures without re-implementing meta assembly.

The parity invariant is asserted in ``test_make_mission_parity.py``: this
factory's ``meta.json`` output is byte-identical to a direct
``create_mission_core()`` call, after normalizing the auto-minted
``{mission_id, created_at}`` fields (and the ``mid8`` embedded in the
slug-derived fields), minus explicit overrides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mission_runtime import MissionTopology
from specify_cli.core.mission_creation import MissionCreationResult, create_mission_core

__all__ = ["make_mission"]


def make_mission(
    repo_root: Path,
    mission_slug: str,
    *,
    topology: MissionTopology = MissionTopology.SINGLE_BRANCH,
    **overrides: Any,
) -> MissionCreationResult:
    """Create a production-shaped test mission by delegating to ``create_mission_core()``.

    This does not fork the production schema: every field in the returned
    ``meta.json`` comes from ``create_mission_core()`` itself. Only
    test-ergonomic defaults are applied here, and only when the caller has
    not already supplied them via ``overrides``.

    Parameters
    ----------
    repo_root:
        Root of an initialized git repository (e.g. a ``tmp_path`` with
        ``git init`` run against it). ``create_mission_core()`` requires a
        resolvable current branch.
    mission_slug:
        Bare kebab-case mission slug (e.g. ``"my-test-mission"``).
    topology:
        Defaults to :attr:`MissionTopology.SINGLE_BRANCH` so no coordination
        branch is minted -- test fixtures overwhelmingly do not want that
        side effect. Pass an explicit ``topology`` override to opt back in.
    **overrides:
        Any keyword accepted by ``create_mission_core()`` (``mission``,
        ``target_branch``, ``friendly_name``, ``purpose_tldr``,
        ``purpose_context``, ``force_recreate_coordination_branch``,
        ``allow_worktree_context``). ``allow_worktree_context`` defaults to
        ``True`` here (unless overridden) since tests routinely execute from
        inside a lane worktree checkout, where the interactive/CLI guard
        would otherwise reject an in-repo-shaped ``repo_root``.

    Returns
    -------
    MissionCreationResult
        The same structured result ``create_mission_core()`` returns.
    """
    overrides.setdefault("allow_worktree_context", True)
    title = mission_slug.replace("-", " ").strip() or "test mission"
    overrides.setdefault("friendly_name", title.title())
    overrides.setdefault("purpose_tldr", f"Deliver {title} cleanly for the team.")
    overrides.setdefault(
        "purpose_context",
        f"This mission delivers {title} so product and engineering can move "
        "forward with a clear outcome and shared understanding.",
    )
    return create_mission_core(repo_root, mission_slug, topology=topology, **overrides)
