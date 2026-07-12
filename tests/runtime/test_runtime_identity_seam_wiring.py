"""Seam-wiring regression guards for the identity trio -- the residual
delegates forward to the seam, and intra-seam calls resolve
``_primary_runtime_feature_dir`` via a LIVE lookup through ``runtime_bridge``
so the pre-existing monkeypatch-based tests in
``tests/runtime/test_runtime_bridge_identity.py`` stay effective.

(Pure-shape checks -- seam-defines-symbol and the native-delegate
``__module__`` assertion -- were intentionally dropped: they are covered
family-wide by ``tests/runtime/test_bridge_compat_surface.py``.)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.next import runtime_bridge as rb
from runtime.next import runtime_bridge_identity as identity

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_thin_delegates_forward_to_the_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """The residual delegates must actually call through to the seam's real
    implementation (not merely share a name) -- a behavioral, not just
    structural, forwarding check."""
    calls: list[str] = []
    real_primary = identity._primary_runtime_feature_dir

    def _spy_primary(repo_root: Path, mission_slug: str) -> Path:
        calls.append("primary")
        return real_primary(repo_root, mission_slug)

    monkeypatch.setattr(identity, "_primary_runtime_feature_dir", _spy_primary)
    # Non-shared-temp-dir absolute sentinel (category B, test_no_tmp_paths_in_tests):
    # the spy short-circuits before any real filesystem access happens.
    rb._primary_runtime_feature_dir(Path("/fake-repo"), "some-slug")

    assert calls == ["primary"], "runtime_bridge._primary_runtime_feature_dir did not forward to the seam"


def test_resolve_coordination_branch_uses_live_lookup_for_primary_runtime_feature_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``_resolve_coordination_branch`` must resolve
    ``_primary_runtime_feature_dir`` via a live lookup through
    ``runtime_bridge`` -- a bare intra-seam call to this module's own
    function would silently bypass a patch applied to
    ``runtime_bridge._primary_runtime_feature_dir`` (the exact false-green
    mechanism research.md §Compat names, patched 6x in
    ``tests/runtime/test_runtime_bridge_identity.py``)."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission-01KWDABC"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"coordination_branch": "kitty/mission-my-mission-01KWDABC-lane-a"}),
        encoding="utf-8",
    )
    calls: list[str] = []

    def _spy(repo_root: Path, mission_slug: str) -> Path:
        calls.append("primary")
        return feature_dir

    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", _spy)

    identity._resolve_coordination_branch("my-mission-01KWDABC", tmp_path)

    assert calls == ["primary"], (
        "_resolve_coordination_branch did not observe the patch on "
        "runtime_bridge._primary_runtime_feature_dir -- an intra-seam bare "
        "call is bypassing the live lookup (false-green regression)."
    )


def test_resolve_mission_ulid_uses_live_lookup_for_primary_runtime_feature_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same live-lookup regression as above, for ``_resolve_mission_ulid``."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission-01KWDABC"
    feature_dir.mkdir(parents=True)
    ulid = "01KWDABC1234567890ABCDEFGH"
    (feature_dir / "meta.json").write_text(json.dumps({"mission_id": ulid}), encoding="utf-8")
    calls: list[str] = []

    def _spy(repo_root: Path, mission_slug: str) -> Path:
        calls.append("primary")
        return feature_dir

    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", _spy)

    result = identity._resolve_mission_ulid("my-mission-01KWDABC", tmp_path)

    assert result == ulid
    assert calls == ["primary"], (
        "_resolve_mission_ulid did not observe the patch on "
        "runtime_bridge._primary_runtime_feature_dir -- an intra-seam bare "
        "call is bypassing the live lookup (false-green regression)."
    )
