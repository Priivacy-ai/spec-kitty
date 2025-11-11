from specify_cli.cli import StepTracker, multi_select_with_arrows, select_with_arrows
from specify_cli.cli import ui as ui_module


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
    tracker = StepTracker("Demo")
    tracker.add("setup", "Setup")
    tracker.start("setup", "running")
    tracker.complete("setup", "done")

    assert tracker.steps[0]["status"] == "done"
    assert tracker.steps[0]["detail"] == "done"
    tree = tracker.render()
    assert hasattr(tree, "children")


def test_select_with_arrows_uses_default_selection(monkeypatch):
    fake_console = DummyConsole()
    monkeypatch.setattr(ui_module, "get_key", lambda: "enter")
    monkeypatch.setattr(ui_module, "Live", DummyLive)

    result = select_with_arrows(
        {"a": "Option A", "b": "Option B"},
        "Prompt",
        console=fake_console,
    )
    assert result == "a"


def test_multi_select_with_arrows_toggles_selection(monkeypatch):
    fake_console = DummyConsole()
    sequence = iter([" ", "down", " ", "enter"])
    monkeypatch.setattr(ui_module, "get_key", lambda: next(sequence))
    monkeypatch.setattr(ui_module, "Live", DummyLive)

    result = multi_select_with_arrows(
        {"a": "Option A", "b": "Option B"},
        console=fake_console,
    )
    assert result == ["b"]
