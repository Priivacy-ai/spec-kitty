"""Compatibility coverage for the dossier fan-out API retired after 3.2.6."""

from __future__ import annotations


def test_326_dossier_sync_imports_remain_safe_noops() -> None:
    from specify_cli.status import fire_dossier_sync, register_dossier_sync_handler

    assert fire_dossier_sync(None, "mission", None) is None
    assert register_dossier_sync_handler(lambda: None) is None
