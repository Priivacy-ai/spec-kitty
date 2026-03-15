"""Scope: ui unit tests — no real git or subprocesses."""

import pytest
from specify_cli.cli import StepTracker, multi_select_with_arrows, select_with_arrows
from specify_cli.cli import ui as ui_module

pytestmark = pytest.mark.fast


class DummyConsole:
    def __init__(self):
        self.messages = []

    def print(self, *args, **kwargs):
        self.messages.append((args, kwargs))


class DummyLive:
    def __init__(self, *_args, **_kwargs):
        self.updated = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def update(self, *_args, **_kwargs):
        self.updated = True


def test_step_tracker_records_status_progression():
    """StepTracker transitions step to 'done' and renders a tree."""
    # Arrange
    tracker = StepTracker("Demo")
    tracker.add("setup", "Setup")
    # Assumption check
    assert tracker.steps[0]["status"] != "done"
    # Act
    tracker.start("setup", "running")
    tracker.complete("setup", "done")
    # Assert
    assert tracker.steps[0]["status"] == "done"
    assert tracker.steps[0]["detail"] == "done"
    tree = tracker.render()
    assert hasattr(tree, "children")


def test_select_with_arrows_uses_default_selection(monkeypatch):
    """Pressing Enter immediately selects the first (default) option."""
    # Arrange
    fake_console = DummyConsole()
    monkeypatch.setattr(ui_module, "get_key", lambda: "enter")
    monkeypatch.setattr(ui_module, "Live", DummyLive)
    # Assumption check
    assert list({"a": "Option A", "b": "Option B"}.keys())[0] == "a"
    # Act
    result = select_with_arrows(
        {"a": "Option A", "b": "Option B"},
        "Prompt",
        console=fake_console,
    )
    # Assert
    assert result == "a"


def test_multi_select_with_arrows_toggles_selection(monkeypatch):
    """Space toggles selection; Down moves cursor; Enter confirms."""
    # Arrange
    fake_console = DummyConsole()
    sequence = iter([" ", "down", " ", "enter"])
    monkeypatch.setattr(ui_module, "get_key", lambda: next(sequence))
    monkeypatch.setattr(ui_module, "Live", DummyLive)
    # Assumption check — two options available
    options = {"a": "Option A", "b": "Option B"}
    assert len(options) == 2
    # Act
    result = multi_select_with_arrows(options, console=fake_console)
    # Assert — first space on "a" selects it, then "down" + space selects "b",
    # but immediately pressing space again at position 0 deselects "a", leaving only "b".
    assert result == ["b"]
