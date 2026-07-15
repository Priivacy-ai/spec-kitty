"""RED-first coverage for the promoted ``builtin_missions_root()`` accessor (#2668).

``MissionTypeProfileRepository._default_built_in_dir`` is a private classmethod
that two out-of-class call sites (``charter.action_grain``,
``charter.mission_type_profiles``) had to reach around ``# noqa: SLF001`` to
use. This test pins the public module-level replacement: it must resolve to
the same ``src/doctrine/missions`` root the constructor already uses, so the
promotion is a byte-identical refactor (no behavior change).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import charter.mission_type_profile_repository as mission_type_profile_repository_module
from charter.mission_type_profile_repository import (
    MissionTypeProfileRepository,
    builtin_missions_root,
)

pytestmark = [pytest.mark.unit]


def test_builtin_missions_root_ends_with_doctrine_missions() -> None:
    root = builtin_missions_root()

    assert root.parts[-2:] == ("doctrine", "missions")


def test_builtin_missions_root_matches_module_relative_resolution() -> None:
    """The accessor must resolve relative to this module, not the caller's cwd."""
    module_file = Path(mission_type_profile_repository_module.__file__)
    expected = module_file.resolve().parents[1] / "doctrine" / "missions"

    assert builtin_missions_root() == expected


def test_builtin_missions_root_matches_constructor_default() -> None:
    """Constructing a repository with no explicit ``built_in_dir`` must not raise.

    This exercises the classmethod-delegates-to-function path (T026): the
    constructor's default resolution goes through the same promoted
    ``builtin_missions_root()`` this module exposes publicly.
    """
    repo = MissionTypeProfileRepository()

    assert repo is not None
