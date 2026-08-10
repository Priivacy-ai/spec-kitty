"""Coverage for ``kind_vocabulary._scan_roots``' fail-soft built-in branch.

The built-in doctrine relocation (mission
doctrine-built-in-seam-consolidation-01KYW3TX) routed ``_scan_roots`` through the
shared :func:`doctrine.pack_paths.built_in_dir` seam and wrapped it in a
best-effort ``try/except``: if the built-in root cannot be resolved
(:class:`~doctrine.pack_paths.PackRootNotFound`) or the kind has no shipped
content dir (:class:`~doctrine.pack_paths.BuiltInContentDirNotAvailable`), the
charter-catalog *render* path degrades to the org/project roots instead of
raising. (The authoritative *load* path in ``doctrine.base`` fails closed on
``PackRootNotFound`` instead -- see ``tests/doctrine/test_loader_fail_closed.py``;
this render path is intentionally the softer sibling.)

This pins that fail-soft branch, which is otherwise only exercised on a broken
install and so was invisible to the rest of the suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter import kind_vocabulary
from charter.kind_vocabulary import (
    _built_in_scan_dir,
    _layer_candidate_dir,
    _layer_scan_dirs,
    _org_scan_dirs,
    _scan_roots,
)
from doctrine.artifact_kinds import ArtifactKind
from doctrine.pack_paths import BuiltInContentDirNotAvailable, PackRootNotFound

pytestmark = [pytest.mark.unit, pytest.mark.fast]


@pytest.mark.parametrize(
    "exc",
    [
        PackRootNotFound("built-in"),
        BuiltInContentDirNotAvailable(ArtifactKind.TACTIC),
    ],
    ids=["pack-root-not-found", "no-content-dir"],
)
def test_scan_roots_degrades_when_built_in_dir_unresolvable(
    monkeypatch: pytest.MonkeyPatch, exc: Exception
) -> None:
    """``built_in_dir`` raising must be swallowed, not propagated.

    With no org/layer roots supplied, the result is empty -- the built-in dir
    was dropped rather than crashing the render path.
    """

    def _raise(_kind: ArtifactKind) -> Path:
        raise exc

    monkeypatch.setattr(kind_vocabulary, "built_in_dir", _raise)

    result = _scan_roots(
        ArtifactKind.TACTIC,
        _doctrine_root=Path("/nonexistent"),
        org_roots=None,
        layer_roots=None,
    )

    assert result == []


def test_scan_roots_still_returns_org_root_when_built_in_unresolvable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fail-soft on built-in must not discard a legitimate org root."""

    def _raise(_kind: ArtifactKind) -> Path:
        raise PackRootNotFound("built-in")

    monkeypatch.setattr(kind_vocabulary, "built_in_dir", _raise)

    org_built_in = tmp_path / ArtifactKind.TACTIC.plural / "built-in"
    org_built_in.mkdir(parents=True)

    result = _scan_roots(
        ArtifactKind.TACTIC,
        _doctrine_root=Path("/nonexistent"),
        org_roots=[tmp_path],
        layer_roots=None,
    )

    assert (org_built_in, True) in result


# ---------------------------------------------------------------------------
# Direct coverage for the helpers extracted from ``_scan_roots`` during Sonar
# S3776 cognitive-complexity remediation (WP03).
# ---------------------------------------------------------------------------


class TestBuiltInScanDirHelper:
    def test_returns_none_when_built_in_dir_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(_kind: ArtifactKind) -> Path:
            raise PackRootNotFound("built-in")

        monkeypatch.setattr(kind_vocabulary, "built_in_dir", _raise)
        assert _built_in_scan_dir(ArtifactKind.TACTIC) is None

    def test_returns_none_when_resolved_dir_does_not_exist(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        missing = tmp_path / "does-not-exist"
        monkeypatch.setattr(kind_vocabulary, "built_in_dir", lambda _kind: missing)
        assert _built_in_scan_dir(ArtifactKind.TACTIC) is None

    def test_returns_recursive_pair_when_dir_exists(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        present = tmp_path / "built-in"
        present.mkdir()
        monkeypatch.setattr(kind_vocabulary, "built_in_dir", lambda _kind: present)
        assert _built_in_scan_dir(ArtifactKind.TACTIC) == (present, True)


class TestOrgScanDirsHelper:
    def test_none_org_roots_returns_empty_list(self) -> None:
        assert _org_scan_dirs(ArtifactKind.TACTIC, None) == []

    def test_missing_org_built_in_dir_skipped(self, tmp_path: Path) -> None:
        assert _org_scan_dirs(ArtifactKind.TACTIC, [tmp_path]) == []

    def test_existing_org_built_in_dir_returned(self, tmp_path: Path) -> None:
        candidate = tmp_path / ArtifactKind.TACTIC.plural / "built-in"
        candidate.mkdir(parents=True)
        assert _org_scan_dirs(ArtifactKind.TACTIC, [tmp_path]) == [(candidate, True)]


class TestLayerCandidateDirHelper:
    def test_project_layer_uses_project_kind_dirs_mapping(self, tmp_path: Path) -> None:
        expected = tmp_path / "doctrine" / kind_vocabulary.PROJECT_KIND_DIRS.get(
            ArtifactKind.TACTIC, ArtifactKind.TACTIC.plural
        )
        assert _layer_candidate_dir(ArtifactKind.TACTIC, "project", tmp_path) == expected

    def test_non_project_layer_uses_plural_subdir(self, tmp_path: Path) -> None:
        expected = tmp_path / "doctrine" / ArtifactKind.TACTIC.plural / "org"
        assert _layer_candidate_dir(ArtifactKind.TACTIC, "org", tmp_path) == expected


class TestLayerScanDirsHelper:
    def test_none_layer_roots_returns_empty_list(self) -> None:
        assert _layer_scan_dirs(ArtifactKind.TACTIC, None) == []

    def test_missing_layer_dir_skipped(self, tmp_path: Path) -> None:
        assert _layer_scan_dirs(ArtifactKind.TACTIC, {"org": tmp_path}) == []

    def test_existing_layer_dir_returned_as_non_recursive(self, tmp_path: Path) -> None:
        candidate = tmp_path / "doctrine" / ArtifactKind.TACTIC.plural / "org"
        candidate.mkdir(parents=True)
        assert _layer_scan_dirs(ArtifactKind.TACTIC, {"org": tmp_path}) == [
            (candidate, False)
        ]
