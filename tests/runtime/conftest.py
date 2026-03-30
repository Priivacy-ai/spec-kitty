"""Shared fixtures for runtime resolver tests.

Centralises the mock-patch targets for ``get_kittify_home`` and
``MissionTemplateRepository.default`` so that tests are insulated from
the canonical module path of the resolver.  If the resolver moves again,
only *this file* needs updating.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from doctrine.missions import MissionTemplateRepository

# Single source of truth for patch targets -- update here if the
# canonical module ever moves again.
_KITTIFY_HOME_TARGET = "doctrine.resolver.get_kittify_home"
_REPO_DEFAULT_TARGET = "doctrine.missions.MissionTemplateRepository.default"


@pytest.fixture()
def patch_kittify_home():
    """Return a context-manager factory that patches ``get_kittify_home``.

    Usage::

        def test_something(self, tmp_path, patch_kittify_home):
            home = tmp_path / "home"
            with patch_kittify_home(home):
                result = resolve_template(...)

    Pass ``side_effect=...`` to simulate errors::

        with patch_kittify_home(side_effect=RuntimeError("no home")):
            ...
    """

    def _patch(home: Path | None = None, *, side_effect: Any = None):
        if side_effect is not None:
            return patch(_KITTIFY_HOME_TARGET, side_effect=side_effect)
        return patch(_KITTIFY_HOME_TARGET, return_value=home)

    return _patch


@pytest.fixture()
def patch_repo_default():
    """Return a context-manager factory that patches ``MissionTemplateRepository.default()``.

    Usage::

        def test_something(self, tmp_path, patch_repo_default):
            with patch_repo_default(tmp_path / "pkg"):
                result = resolve_template(...)
    """

    def _patch(pkg_root: Path):
        return patch(
            _REPO_DEFAULT_TARGET,
            return_value=MissionTemplateRepository(pkg_root),
        )

    return _patch
