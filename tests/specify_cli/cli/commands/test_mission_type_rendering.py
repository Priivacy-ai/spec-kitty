"""Rendering tests for mission-type command envelopes."""

from __future__ import annotations

from rich.panel import Panel

from specify_cli.cli.commands import mission_type


def test_render_human_success_includes_warning(monkeypatch) -> None:
    captured: list[Panel] = []
    monkeypatch.setattr(mission_type.console, "print", lambda panel: captured.append(panel))

    mission_type._render_human(
        {
            "result": "success",
            "mission_key": "software-dev",
            "mission_slug": "123-demo",
            "mission_id": "m-1",
            "feature_dir": "/tmp/feature",
            "run_dir": "/tmp/run",
            "warnings": [{"code": "W1", "message": "Heads up"}],
        }
    )

    assert len(captured) == 1
    panel = captured[0]
    assert panel.title == "Mission Run Started"
    assert "mission_key:  software-dev" in str(panel.renderable)
    assert "[warn] W1: Heads up" in str(panel.renderable)


def test_render_human_error_includes_details(monkeypatch) -> None:
    captured: list[Panel] = []
    monkeypatch.setattr(mission_type.console, "print", lambda panel: captured.append(panel))

    mission_type._render_human(
        {
            "result": "error",
            "error_code": "BROKEN",
            "message": "Nope",
            "details": {"path": "/tmp/demo"},
        }
    )

    assert len(captured) == 1
    panel = captured[0]
    assert panel.title == "BROKEN"
    assert "Nope" in str(panel.renderable)
    assert "path: /tmp/demo" in str(panel.renderable)
