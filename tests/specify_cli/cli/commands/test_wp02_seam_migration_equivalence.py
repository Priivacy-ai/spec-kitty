"""WP02 / T009 (FR-002, NFR-002) — behaviour-preserving seam migration.

The four read-CLI raw-join bootstraps (``agent/context.py`` ``_find_feature_directory``,
``agent/mission.py`` ``_find_feature_directory`` + the primary-anchored existence
probe, and ``decision.py`` ``cmd_verify``) were collapsed onto the single guarded
read-side seam ``resolve_handle_to_read_path`` (WP01).  These tests pin the
behaviour-preserving contract: a ``<slug>-<mid8>`` handle and the full ``mission_id``
handle MUST resolve to the SAME on-disk mission directory for every migrated CLI —
exactly as the hand-rolled ``load_meta`` → ``resolve_mid8`` blocks did before.

Production-shaped identity only (real 26-char Crockford ULID, ``<human>-<mid8>``
slug) so the equivalence is proven against the true resolver grammar, not a
short hand-crafted placeholder.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.context import (
    _find_feature_directory as context_find_feature_directory,
)
from specify_cli.cli.commands.agent.mission import (
    _find_feature_directory as mission_find_feature_directory,
    _resolve_mission_dir_name_primary_anchored,
)
from specify_cli.cli.commands.decision import cmd_verify

pytestmark = [pytest.mark.fast]

# Production-shaped identity: a real 26-char Crockford-base32 ULID and the
# canonical ``<human>-<mid8>`` slug that embeds its mid8.
MISSION_ID = "01KVJPEQWP02SEAMMIGRATE001"
MID8 = MISSION_ID[:8]  # "01KVJPEQ"
SLUG = f"read-side-surface-resolver-adoption-{MID8.lower()}"


def _seed_primary_mission(repo_root: Path) -> Path:
    """Create a primary-checkout mission dir with a topology-true meta.json."""
    mission_dir = repo_root / "kitty-specs" / SLUG
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": MISSION_ID, "mission_slug": SLUG}),
        encoding="utf-8",
    )
    return mission_dir


# ---------------------------------------------------------------------------
# T009-a — context.py: ``<slug>-<mid8>`` ≡ full mission_id
# ---------------------------------------------------------------------------


def test_context_slug_mid8_equals_full_mission_id(tmp_path: Path) -> None:
    expected = _seed_primary_mission(tmp_path)

    via_slug_mid8 = context_find_feature_directory(
        tmp_path, tmp_path, explicit_mission=SLUG
    )
    via_full_id = context_find_feature_directory(
        tmp_path, tmp_path, explicit_mission=MISSION_ID
    )

    assert via_slug_mid8 == expected
    assert via_full_id == expected
    assert via_slug_mid8 == via_full_id


# ---------------------------------------------------------------------------
# T009-b — mission.py: ``<slug>-<mid8>`` ≡ full mission_id (both helpers)
# ---------------------------------------------------------------------------


def test_mission_find_feature_directory_slug_mid8_equals_full_mission_id(
    tmp_path: Path,
) -> None:
    expected = _seed_primary_mission(tmp_path)

    via_slug_mid8 = mission_find_feature_directory(
        tmp_path, tmp_path, explicit_feature=SLUG
    )
    via_full_id = mission_find_feature_directory(
        tmp_path, tmp_path, explicit_feature=MISSION_ID
    )

    assert via_slug_mid8 == expected
    assert via_full_id == expected
    assert via_slug_mid8 == via_full_id


def test_mission_primary_anchored_probe_resolves_via_seam_primitive(
    tmp_path: Path,
) -> None:
    """The migrated ``.is_dir()`` probe (now routed through the topology-blind
    ``primary_feature_dir_for_mission`` primitive) still returns the on-disk dir
    NAME for a literal ``<slug>-<mid8>`` handle, and ``None`` for an unknown one.
    """
    _seed_primary_mission(tmp_path)

    assert (
        _resolve_mission_dir_name_primary_anchored(tmp_path, SLUG) == SLUG
    )
    assert (
        _resolve_mission_dir_name_primary_anchored(tmp_path, "no-such-handle")
        is None
    )


def test_mission_primary_anchored_probe_rejects_traversal(tmp_path: Path) -> None:
    """The seam primitive adds the ``assert_safe_path_segment`` guard (FR-004)
    the raw ``KITTY_SPECS_DIR / raw_handle`` probe lacked — a traversal handle now
    raises rather than statting an escaped path."""
    (tmp_path / "kitty-specs").mkdir()
    with pytest.raises(ValueError):
        _resolve_mission_dir_name_primary_anchored(tmp_path, "../escape")


# ---------------------------------------------------------------------------
# T009-c — decision.py cmd_verify: ``<slug>-<mid8>`` ≡ full mission_id
# ---------------------------------------------------------------------------


def _run_verify(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, handle: str) -> Path:
    """Invoke ``cmd_verify`` and capture the mission dir it resolved.

    ``cmd_verify`` has no return value (it echoes JSON), so we intercept the
    resolved ``mission_dir`` it hands to ``_verify_decisions`` — the single
    observable product of the migrated seam call. ``_resolve_repo_root_and_slug``
    is left REAL (it canonicalises the handle and anchors on
    ``locate_project_root``); we only point that root at ``tmp_path`` so the whole
    real flow — including the migrated ``resolve_handle_to_read_path`` call —
    runs end to end.
    """
    captured: dict[str, Path] = {}

    def _fake_verify(mission_dir: Path, mission_slug: str):  # type: ignore[no-untyped-def]
        captured["mission_dir"] = mission_dir
        return _empty_result()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "specify_cli.cli.commands.decision.locate_project_root",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.decision._verify_decisions", _fake_verify
    )

    cmd_verify(mission=handle, fail_on_stale=False, json_out=True)
    return captured["mission_dir"]


def _empty_result():  # type: ignore[no-untyped-def]
    from types import SimpleNamespace

    return SimpleNamespace(
        status="clean", deferred_count=0, marker_count=0, findings=[]
    )


def test_decision_verify_slug_mid8_equals_full_mission_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = _seed_primary_mission(tmp_path)

    via_slug_mid8 = _run_verify(monkeypatch, tmp_path, SLUG)
    via_full_id = _run_verify(monkeypatch, tmp_path, MISSION_ID)

    assert via_slug_mid8 == expected
    assert via_full_id == expected
    assert via_slug_mid8 == via_full_id
