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
from charter.kind_vocabulary import _scan_roots
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
