from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.feature_meta import build_baseline_feature_meta


def test_build_baseline_feature_meta_replaces_blank_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank metadata values are repaired, not preserved."""
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / "023-repair-me"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

    monkeypatch.setattr(
        "specify_cli.upgrade.feature_meta.resolve_primary_branch",
        lambda _repo_root: "2.x",
    )

    meta = build_baseline_feature_meta(
        feature_dir,
        repo_root,
        existing_meta={
            "feature_number": "",
            "slug": "",
            "feature_slug": "",
            "friendly_name": "",
            "mission": "",
            "target_branch": "",
            "created_at": "",
        },
    )

    assert meta["feature_number"] == "023"
    assert meta["slug"] == "023-repair-me"
    assert meta["feature_slug"] == "023-repair-me"
    assert meta["friendly_name"] == "repair me"
    assert meta["mission"] == "software-dev"
    assert meta["target_branch"] == "2.x"
    assert meta["created_at"]
