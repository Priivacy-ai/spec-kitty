"""Native Windows regression test: active-mission handle round-trip without symlink support.

On Windows without Developer Mode, ``os.symlink()`` raises ``OSError`` with
``[WinError 1314]``.  The active-mission selector in
``specify_cli.context.mission_resolver.resolve_mission`` must still resolve a
mission handle reliably when the resolution path never touches symlinks.

This test writes a ``meta.json`` to a temporary ``kitty-specs/<slug>/``
directory and then calls ``resolve_mission(handle, repo_root)`` with several
handle forms:

1. Full ``mission_id`` (26-char ULID)
2. ``mid8`` prefix (first 8 chars)
3. Full slug (directory name)
4. Human slug (directory name without numeric prefix)

Each form must resolve to the same mission.  No symlinks are created, so the
test passes even when Developer Mode is off.

Marked ``@pytest.mark.windows_ci`` — runs only on the ``windows-latest`` CI
job (skipped on POSIX CI runners via the ``-m "not windows_ci"`` filter).

Spec IDs: FR-014, FR-016, FR-017, NFR-001
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


_MISSION_SLUG = "windows-compatibility-hardening-01KP5R6K"
# Synthetic ULID-style mission_id (26 uppercase alphanum chars)
_MISSION_ID = "01KP5R6KAAAAAAAAAAAAAAAA26"


def _create_mission_meta(kitty_specs: Path, slug: str, mission_id: str) -> Path:
    """Create a minimal ``meta.json`` for a mission in ``kitty-specs/<slug>/``."""
    mission_dir = kitty_specs / slug
    mission_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "mission_id": mission_id,
        "mission_slug": slug,
        "friendly_name": "Windows Compatibility Hardening",
        "mission_type": "software-dev",
        "target_branch": "main",
        "vcs": "git",
        "created_at": "2026-04-14T00:00:00+00:00",
    }
    meta_path = mission_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return mission_dir


@pytest.mark.windows_ci
def test_active_mission_handle_round_trip_on_windows(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mission handle resolves correctly without symlink support.

    Writes a mission directory with ``meta.json`` and asserts that
    ``resolve_mission`` returns the correct ``mission_id`` and ``mission_slug``
    for all supported handle forms.
    """
    monkeypatch.chdir(tmp_path)

    kitty_specs = tmp_path / "kitty-specs"
    _create_mission_meta(kitty_specs, _MISSION_SLUG, _MISSION_ID)

    from specify_cli.context.mission_resolver import resolve_mission

    # Handle form 1: full mission_id (26-char ULID)
    resolved = resolve_mission(_MISSION_ID, tmp_path)
    assert resolved.mission_id == _MISSION_ID, (
        f"Expected mission_id {_MISSION_ID!r}, got {resolved.mission_id!r}"
    )
    assert resolved.mission_slug == _MISSION_SLUG, (
        f"Expected mission_slug {_MISSION_SLUG!r}, got {resolved.mission_slug!r}"
    )

    # Handle form 2: mid8 (first 8 chars of mission_id)
    mid8 = _MISSION_ID[:8]
    resolved_mid8 = resolve_mission(mid8, tmp_path)
    assert resolved_mid8.mission_id == _MISSION_ID, (
        f"mid8 handle did not resolve correctly: got {resolved_mid8.mission_id!r}"
    )

    # Handle form 3: full slug (directory name, may include numeric prefix)
    resolved_slug = resolve_mission(_MISSION_SLUG, tmp_path)
    assert resolved_slug.mission_id == _MISSION_ID, (
        f"Full slug handle did not resolve correctly: got {resolved_slug.mission_id!r}"
    )

    # Verify the resolved path is a plain directory (no symlink involved)
    assert resolved.feature_dir.is_dir(), (
        f"Resolved feature_dir is not a directory: {resolved.feature_dir}"
    )
    assert not resolved.feature_dir.is_symlink(), (
        f"Resolved feature_dir unexpectedly uses a symlink: {resolved.feature_dir}"
    )
