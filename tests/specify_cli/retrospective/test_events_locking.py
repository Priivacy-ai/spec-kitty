"""Locking + atomicity pins for ``retrospective/events.py`` (WP01 T003).

Family 4 of the writer census: the superseded ``emit_retrospective_event``
appender ("do not add new callers" -- still present, so still a writer the
WP03 gate would otherwise have to allowlist). After WP01 the append runs
through the atomic store primitive while the mission status lock keyed on
``feature_dir.name`` is held.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

import specify_cli.retrospective.events as retro_events
import specify_cli.status.store as status_store
from specify_cli.retrospective.events import FailedPayload, emit_retrospective_event
from specify_cli.retrospective.schema import ActorRef
from specify_cli.status.locking import _get_thread_locks, feature_status_lock_path
from specify_cli.workspace.root_resolver import resolve_status_lock_root

pytestmark = [pytest.mark.unit, pytest.mark.fast]

MISSION_ID = "01KQ6YEG0000000000000000AA"
MISSION_SLUG = "retro-events-locking-01KQ6YEG"


@pytest.fixture
def feature_dir(tmp_path: Path) -> Path:
    fd = tmp_path / "kitty-specs" / MISSION_SLUG
    fd.mkdir(parents=True)
    return fd


def _emit(feature_dir: Path) -> str:
    return emit_retrospective_event(
        feature_dir=feature_dir,
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        mid8=MISSION_ID[:8],
        actor=ActorRef(kind="runtime", id="spec-kitty-test"),
        event_name="retrospective.failed",
        payload=FailedPayload(failure_code="test", message="boom"),
    )


def _rows(feature_dir: Path) -> list[dict[str, Any]]:
    path = feature_dir / "status.events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_append_runs_while_mission_lock_is_held(feature_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    held_at_write: list[set[str]] = []
    original = status_store._fsync_directory

    def _record(directory: Path) -> None:
        held_at_write.append(set(_get_thread_locks()))
        original(directory)

    monkeypatch.setattr(status_store, "_fsync_directory", _record)
    event_id = _emit(feature_dir)

    expected = feature_status_lock_path(resolve_status_lock_root(feature_dir), feature_dir.name)
    assert held_at_write, "the atomic primitive never wrote"
    assert str(expected) in held_at_write[0]
    assert [row["event_id"] for row in _rows(feature_dir)] == [event_id]
    # Lock released once the append is durable.
    assert str(expected) not in _get_thread_locks()


def test_materialize_runs_after_the_append_outside_the_critical_section(
    feature_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The critical section is the append only; ``materialize`` follows it."""
    import specify_cli.status as status_facade

    order: list[str] = []
    original_fsync = status_store._fsync_directory
    original_materialize = status_facade.materialize

    def _record_fsync(directory: Path) -> None:
        order.append("append")
        original_fsync(directory)

    def _record_materialize(fd: Path) -> Any:
        order.append("materialize")
        return original_materialize(fd)

    monkeypatch.setattr(status_store, "_fsync_directory", _record_fsync)
    monkeypatch.setattr(status_facade, "materialize", _record_materialize)
    _emit(feature_dir)
    assert order[0] == "append"
    assert "materialize" in order


def test_module_has_no_raw_append_open() -> None:
    source = Path(retro_events.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name != "open":
            continue
        modes = [arg.value for arg in node.args[1:2] if isinstance(arg, ast.Constant)]
        modes += [kw.value.value for kw in node.keywords if kw.arg == "mode" and isinstance(kw.value, ast.Constant)]
        assert not any("a" in str(mode) for mode in modes), f"raw append open at line {node.lineno}"
    assert "append_raw_rows_atomic" in source
    assert "do not add new callers" in source
