"""Contract tests for the canonical version-comparison primitive (#2417).

Consolidates three independent "is this version newer" implementations that
previously lived in ``cli/commands/upgrade.py``, ``core/upgrade_probe.py``,
and ``session_presence/manager.py`` (the last one added by #2413's fix for
the bare-inequality bug: comparing ``avail != current`` instead of ordering
``avail > current``). This matrix mirrors
``tests/specify_cli/session_presence/test_manager.py::TestUpgradeIsAvailable``
plus the epoch/local-version-identifier cases flagged as an untested gap
during PR review.
"""

from __future__ import annotations

import pytest

from specify_cli.core.version_compare import is_version_newer, try_parse_version

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class TestIsVersionNewer:
    """Matrix for ``is_version_newer(candidate, current) -> bool``."""

    def test_newer_available(self) -> None:
        assert is_version_newer("3.3.0", "3.2.4") is True

    def test_equal_versions(self) -> None:
        assert is_version_newer("3.2.4", "3.2.4") is False

    def test_older_available_the_2413_bug(self) -> None:
        # A bare inequality would report this as "available"; ordering must not.
        assert is_version_newer("3.2.2", "3.2.4") is False

    def test_prerelease_ordering_rc_behind_release(self) -> None:
        # An installed rc ahead of the published release is NOT an upgrade to it.
        assert is_version_newer("3.2.5rc1", "3.2.5") is False

    def test_prerelease_ordering_release_ahead_of_its_own_rc(self) -> None:
        # A published release IS an upgrade over its own rc.
        assert is_version_newer("3.2.5", "3.2.4rc39") is True

    def test_none_candidate(self) -> None:
        assert is_version_newer(None, "3.2.4") is False

    def test_empty_candidate(self) -> None:
        assert is_version_newer("", "3.2.4") is False

    def test_unparseable_candidate(self) -> None:
        assert is_version_newer("not-a-version", "3.2.4") is False

    def test_unparseable_current(self) -> None:
        assert is_version_newer("3.3.0", "not-a-version") is False

    def test_both_unparseable(self) -> None:
        assert is_version_newer("also-not-a-version", "not-a-version") is False

    def test_epoch_version_newer(self) -> None:
        # PEP 440 epoch segment dominates the rest of the version.
        assert is_version_newer("1!1.0.0", "2024.1.1") is True

    def test_epoch_version_not_newer(self) -> None:
        assert is_version_newer("2024.1.1", "1!1.0.0") is False

    def test_epoch_versions_equal(self) -> None:
        assert is_version_newer("1!3.2.4", "1!3.2.4") is False

    def test_local_version_identifier_newer(self) -> None:
        # Local version identifiers (+local) sort after their base release.
        assert is_version_newer("3.2.4+local.1", "3.2.4") is True

    def test_local_version_identifier_not_newer_than_itself(self) -> None:
        assert is_version_newer("3.2.4+local.1", "3.2.4+local.1") is False

    def test_local_version_identifier_current_side(self) -> None:
        # A plain release is not newer than a local build of that same release.
        assert is_version_newer("3.2.4", "3.2.4+local.1") is False


class TestTryParseVersion:
    """Matrix for the shared parsing primitive used by ``is_version_newer``
    and by ``core.upgrade_probe._classify``'s richer state machine."""

    def test_parses_valid_version(self) -> None:
        from packaging.version import Version

        assert try_parse_version("3.2.4") == Version("3.2.4")

    def test_none_returns_none(self) -> None:
        assert try_parse_version(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert try_parse_version("") is None

    def test_unparseable_returns_none(self) -> None:
        assert try_parse_version("not-a-version") is None

    def test_epoch_and_local_parse(self) -> None:
        from packaging.version import Version

        assert try_parse_version("1!2.0.0+local") == Version("1!2.0.0+local")
