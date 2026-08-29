"""CR-07 compat shim: ``.kittify/doctrine/`` -> ``.kittify/charter-packs/``
dual-root READER (mission ``charter-code-topology-01M152G1`` S4).

M2 introduces the reader only (canonical-preferred, legacy-fallback with a
warn-once notice); M3 performs the actual data move and write-side cutover.
Precedent for the read-both/canonical-wins/warn-once shape: ``charter.activation.sync``
CR-01 (``src/charter/sync.py:245-311``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kernel.doctrine_root import (
    CANONICAL_DOCTRINE_DIRNAME,
    LEGACY_DOCTRINE_DIRNAME,
    LegacyDoctrineRootWarning,
    _warn_legacy_doctrine_root_once,
    resolve_doctrine_read_root,
)

pytestmark = [pytest.mark.fast]


@pytest.fixture(autouse=True)
def _reset_warn_once_gate() -> None:
    _warn_legacy_doctrine_root_once.cache_clear()


class TestNeitherRootExists:
    def test_returns_canonical_path_without_warning(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        """A fresh project with no doctrine data anywhere yet resolves to the
        canonical path -- nothing to migrate, nothing to warn about."""
        result = resolve_doctrine_read_root(tmp_path)

        assert result == tmp_path / ".kittify" / CANONICAL_DOCTRINE_DIRNAME
        assert not any(
            issubclass(w.category, LegacyDoctrineRootWarning) for w in recwarn.list
        )


class TestCanonicalRootExists:
    def test_canonical_wins_without_warning(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        canonical = tmp_path / ".kittify" / CANONICAL_DOCTRINE_DIRNAME
        canonical.mkdir(parents=True)

        result = resolve_doctrine_read_root(tmp_path)

        assert result == canonical
        assert not any(
            issubclass(w.category, LegacyDoctrineRootWarning) for w in recwarn.list
        )

    def test_canonical_wins_even_when_legacy_also_exists(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        canonical = tmp_path / ".kittify" / CANONICAL_DOCTRINE_DIRNAME
        canonical.mkdir(parents=True)
        legacy = tmp_path / ".kittify" / LEGACY_DOCTRINE_DIRNAME
        legacy.mkdir(parents=True)

        result = resolve_doctrine_read_root(tmp_path)

        assert result == canonical
        assert not any(
            issubclass(w.category, LegacyDoctrineRootWarning) for w in recwarn.list
        )


class TestLegacyRootOnlyExists:
    def test_old_root_read_warns_and_migrates(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        """The named CR-07 reader test: a project that only has the legacy
        ``.kittify/doctrine/`` tree reads from it (nothing is lost -- the
        reader "migrates" onto the legacy root rather than reporting empty),
        with a one-shot deprecation notice pointing at the future move."""
        legacy = tmp_path / ".kittify" / LEGACY_DOCTRINE_DIRNAME
        legacy.mkdir(parents=True)

        result = resolve_doctrine_read_root(tmp_path)

        assert result == legacy
        assert any(
            issubclass(w.category, LegacyDoctrineRootWarning) for w in recwarn.list
        )

    def test_warns_only_once_per_process(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        legacy = tmp_path / ".kittify" / LEGACY_DOCTRINE_DIRNAME
        legacy.mkdir(parents=True)

        resolve_doctrine_read_root(tmp_path)
        resolve_doctrine_read_root(tmp_path)
        resolve_doctrine_read_root(tmp_path)

        warnings_seen = [
            w for w in recwarn.list if issubclass(w.category, LegacyDoctrineRootWarning)
        ]
        assert len(warnings_seen) == 1

    def test_quiet_suppresses_the_warning(
        self, tmp_path: Path, recwarn: pytest.WarningsRecorder
    ) -> None:
        legacy = tmp_path / ".kittify" / LEGACY_DOCTRINE_DIRNAME
        legacy.mkdir(parents=True)

        result = resolve_doctrine_read_root(tmp_path, quiet=True)

        assert result == legacy
        assert not any(
            issubclass(w.category, LegacyDoctrineRootWarning) for w in recwarn.list
        )
