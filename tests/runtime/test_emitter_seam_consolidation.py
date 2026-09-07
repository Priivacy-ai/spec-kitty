"""Pins for the consolidated ``RuntimeEventEmitter`` seam.

ADR ``docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md``
(Accepted 2026-09-06, PR #3898), executed by mission
``dead-port-disposition-01M1TZVN`` WP05. The ADR's Confirmation section:

1. exactly one class named ``RuntimeEventEmitter`` exists under
   ``src/runtime/next/`` -- the Protocol in ``_internal_runtime/events.py``;
   the duplicate concrete ``runtime/next/event_emitter.py`` is deleted;
2. the bridge constructs the seam via a factory returning ``NullEmitter`` by
   default (and under ``SPEC_KITTY_SYNC_MINIMAL_IMPORT``), with the promoted
   constructor (``for_mission``) and ``seed_from_snapshot`` intact;
4. ``_BufferingRuntimeEmitter`` stays (C-006).

Structural pins are grep/AST-level so they cannot go vacuous when the
concrete module is gone; the seam's behaviour is pinned through the real
factory, registry, and wrapper.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from runtime.next import runtime_bridge as rb
from runtime.next import runtime_bridge_retrospective as _retrospective_seam
from runtime.next._internal_runtime import events as events_mod
from runtime.next._internal_runtime.events import (
    NullEmitter,
    RuntimeEventEmitter,
    RuntimeEventEmitterRegistry,
    runtime_event_emitter_for_mission,
)
from specify_cli.events.decision_log import DecisionGitLog

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_TESTS = _REPO_ROOT / "tests"
_RUNTIME_NEXT = _SRC / "runtime" / "next"
_CANONICAL_HOME = _RUNTIME_NEXT / "_internal_runtime" / "events.py"
_RETIRED_CONCRETE_MODULE = _RUNTIME_NEXT / "event_emitter.py"
#: An import statement or a quoted patch target binding the retired module.
_RETIRED_IMPORT_BINDING = re.compile(r"(^\s*from\s+runtime\.next\.event_emitter\b|^\s*import\s+runtime\.next\.event_emitter\b|[\"']runtime\.next\.event_emitter\b)")
_MINIMAL_IMPORT_ENV = "SPEC_KITTY_SYNC_MINIMAL_IMPORT"
_ULID = "01KT3YBDABCDEFGHIJKLMNOP"


@pytest.fixture(autouse=True)
def _pristine_registry(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """No test may leak a registered producer or the env gate into another."""
    monkeypatch.delenv(_MINIMAL_IMPORT_ENV, raising=False)
    RuntimeEventEmitterRegistry.reset()
    yield
    RuntimeEventEmitterRegistry.reset()


def _runtime_event_emitter_class_sites() -> list[Path]:
    sites: list[Path] = []
    for path in sorted(_RUNTIME_NEXT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        sites.extend(path for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "RuntimeEventEmitter")
    return sites


def _mission_dir(tmp_path: Path, *, mission_id: str | None) -> Path:
    mission_dir = tmp_path / "kitty-specs" / "042-mission"
    mission_dir.mkdir(parents=True)
    meta: dict[str, Any] = {"mission_slug": "042-mission", "mission_type": "software-dev"}
    if mission_id is not None:
        meta["mission_id"] = mission_id
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return mission_dir


class _FakeProducer:
    """A Protocol-conforming stand-in for an E3 producer (structural)."""

    def __init__(self, **identity: Any) -> None:
        self.identity = identity

    def seed_from_snapshot(self, snapshot: Any) -> None:
        del snapshot

    def emit_mission_run_started(self, payload: Any) -> None:
        del payload

    def emit_next_step_issued(self, payload: Any) -> None:
        del payload

    def emit_next_step_auto_completed(self, payload: Any) -> None:
        del payload

    def emit_decision_input_requested(self, payload: Any) -> None:
        del payload

    def emit_decision_input_answered(self, payload: Any) -> None:
        del payload

    def emit_mission_run_completed(self, payload: Any) -> None:
        del payload

    def emit_significance_evaluated(self, payload: Any) -> None:
        del payload

    def emit_decision_timeout_expired(self, payload: Any) -> None:
        del payload


# ---------------------------------------------------------------------------
# Confirmation (1): one class, one name
# ---------------------------------------------------------------------------


def test_exactly_one_runtime_event_emitter_class_under_runtime_next() -> None:
    sites = _runtime_event_emitter_class_sites()
    assert sites == [_CANONICAL_HOME], (
        "the ADR requires exactly ONE class named RuntimeEventEmitter under src/runtime/next/ "
        f"(the Protocol in {_CANONICAL_HOME.relative_to(_REPO_ROOT)}); found: "
        f"{[str(p.relative_to(_REPO_ROOT)) for p in sites]}"
    )


def test_concrete_event_emitter_module_is_deleted() -> None:
    assert not _RETIRED_CONCRETE_MODULE.exists(), (
        f"{_RETIRED_CONCRETE_MODULE.relative_to(_REPO_ROOT)} is the duplicate concrete class the ADR "
        "merges into the _internal_runtime Protocol/NullEmitter (Decision Outcome (d))"
    )


def test_no_live_importer_of_the_retired_concrete_module() -> None:
    """No import statement and no string patch target may bind the retired
    module; historical prose (docstrings, docs/, ADRs) may still name it."""
    offenders: list[str] = []
    for root in (_SRC, _TESTS):
        for path in sorted(root.rglob("*.py")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if _RETIRED_IMPORT_BINDING.search(line):
                    offenders.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, "live bindings of the retired concrete module:\n" + "\n".join(offenders)


def test_bridge_and_engine_bind_the_protocol_and_the_factory_only() -> None:
    """ADR (a): the bridge depends on the Protocol and the factory, never on a
    concrete class import; the engine's annotation import is TYPE_CHECKING-only."""
    assert rb.RuntimeEventEmitter is RuntimeEventEmitter
    assert rb.runtime_event_emitter_for_mission is runtime_event_emitter_for_mission
    engine_source = (_RUNTIME_NEXT / "runtime_bridge_engine.py").read_text(encoding="utf-8")
    assert "from runtime.next._internal_runtime.events import RuntimeEventEmitter" in engine_source
    assert "for_feature" not in engine_source
    assert "for_feature" not in (_RUNTIME_NEXT / "runtime_bridge.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Confirmation (2): factory, env gate, registry, promoted constructor, seed
# ---------------------------------------------------------------------------


def test_factory_returns_null_emitter_by_default(tmp_path: Path) -> None:
    emitter = runtime_event_emitter_for_mission(
        mission_dir=_mission_dir(tmp_path, mission_id=_ULID),
        mission_slug="042-mission",
        mission_type="software-dev",
    )
    assert type(emitter) is NullEmitter
    assert (emitter.mission_slug, emitter.mission_type, emitter.mission_id) == ("042-mission", "software-dev", _ULID)


def test_factory_returns_registered_producer_with_resolved_identity(tmp_path: Path) -> None:
    RuntimeEventEmitterRegistry.register(lambda **identity: _FakeProducer(**identity))
    mission_dir = _mission_dir(tmp_path, mission_id=_ULID)

    emitter = runtime_event_emitter_for_mission(mission_dir=mission_dir, mission_slug="042-mission", mission_type="software-dev")

    assert isinstance(emitter, _FakeProducer)
    assert emitter.identity == {
        "mission_dir": mission_dir,
        "mission_slug": "042-mission",
        "mission_type": "software-dev",
        "mission_id": _ULID,
    }


@pytest.mark.parametrize("value", ["1", "true", "yes"])
def test_factory_ignores_registered_producer_under_minimal_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    RuntimeEventEmitterRegistry.register(lambda **identity: _FakeProducer(**identity))
    monkeypatch.setenv(_MINIMAL_IMPORT_ENV, value)

    emitter = runtime_event_emitter_for_mission(
        mission_dir=_mission_dir(tmp_path, mission_id=_ULID),
        mission_slug="042-mission",
        mission_type="software-dev",
    )

    assert type(emitter) is NullEmitter


def test_registry_reset_restores_the_null_default(tmp_path: Path) -> None:
    RuntimeEventEmitterRegistry.register(lambda **identity: _FakeProducer(**identity))
    assert RuntimeEventEmitterRegistry.registered() is not None
    RuntimeEventEmitterRegistry.reset()
    assert RuntimeEventEmitterRegistry.registered() is None
    emitter = runtime_event_emitter_for_mission(
        mission_dir=_mission_dir(tmp_path, mission_id=None),
        mission_slug="042-mission",
        mission_type="software-dev",
    )
    assert type(emitter) is NullEmitter


def test_no_producer_is_registered_in_tree() -> None:
    """ADR: NOT in scope -- wiring a live producer is E3 work. A fresh import of
    the seam module must leave the registry empty."""
    assert RuntimeEventEmitterRegistry.registered() is None
    assert events_mod.RuntimeEventEmitterRegistry is RuntimeEventEmitterRegistry


def test_for_mission_resolves_identity_like_the_retired_for_feature(tmp_path: Path) -> None:
    """Ported behaviour: ``mission_id`` from the mission's ``meta.json``; a
    missing / identity-less / unreadable mission degrades to ``None`` and
    never raises (the retired ``for_feature``'s try/except contract)."""
    resolved = NullEmitter.for_mission(mission_dir=_mission_dir(tmp_path, mission_id=_ULID), mission_slug="042-mission", mission_type="software-dev")
    assert resolved.mission_id == _ULID
    assert (resolved.mission_slug, resolved.mission_type) == ("042-mission", "software-dev")

    anonymous = NullEmitter.for_mission(mission_dir=tmp_path / "nowhere", mission_slug="043-mission", mission_type="research")
    assert anonymous.mission_id is None
    assert (anonymous.mission_slug, anonymous.mission_type) == ("043-mission", "research")

    corrupt_dir = tmp_path / "kitty-specs" / "044-mission"
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "meta.json").write_text("{not json", encoding="utf-8")
    assert NullEmitter.for_mission(mission_dir=corrupt_dir, mission_slug="044-mission", mission_type="software-dev").mission_id is None


def test_null_emitter_seed_from_snapshot_is_a_noop() -> None:
    emitter = NullEmitter(mission_slug="042-mission", mission_type="software-dev", mission_id=_ULID)
    before = dict(vars(emitter))
    assert emitter.seed_from_snapshot(object()) is None
    assert vars(emitter) == before


def test_null_emitter_positional_correlation_id_is_preserved() -> None:
    """The pre-existing ``NullEmitter(correlation_id)`` construction keeps working."""
    emitter = NullEmitter("corr-1")
    assert emitter.correlation_id == "corr-1"
    assert (emitter.mission_slug, emitter.mission_type, emitter.mission_id) == ("", "", None)


def test_decision_git_log_passes_seed_through_to_inner(tmp_path: Path) -> None:
    """The wrapper satisfies the seam surface so it can be handed to the
    composition-path engine adapter (which seeds first) -- ADR (b)/(c)."""
    inner = MagicMock(spec=RuntimeEventEmitter)
    log = DecisionGitLog(
        repo_root=tmp_path,
        worktree_root=tmp_path,
        destination_ref="kitty/mission-042-mission",
        mission_slug="042-mission",
        inner=inner,
    )
    snapshot = object()
    log.seed_from_snapshot(snapshot)
    inner.seed_from_snapshot.assert_called_once_with(snapshot)
    assert not (tmp_path / "kitty-specs" / "042-mission" / "decisions.events.jsonl").exists()


# ---------------------------------------------------------------------------
# Confirmation (4): rollback machinery stays (C-006)
# ---------------------------------------------------------------------------


def test_buffering_runtime_emitter_is_retained() -> None:
    buffer = _retrospective_seam._BufferingRuntimeEmitter()
    assert rb._BufferingRuntimeEmitter.__mro__[1] is _retrospective_seam._BufferingRuntimeEmitter
    for name in ("seed_from_snapshot", "flush", "discard", "call_count"):
        assert callable(getattr(buffer, name))
