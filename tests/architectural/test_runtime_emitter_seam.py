"""Guard the consolidated runtime emitter seam (ADR 2026-09-06-2).

Three regressions mission ``dead-port-disposition-01M1VRA2`` closed must stay
closed by construction (contracts ``emitter-seam.md`` S7-S8 and
``decision-log-flush.md`` F7):

1. a second class named ``RuntimeEventEmitter`` under ``src/runtime/next/``
   (the concrete duplicate that shadowed the canonical Protocol);
2. any import of the deleted ``runtime.next.event_emitter`` module;
3. an engine-facing reference to the plain seam in the bridge -- handing the
   flush target or the composition emitter ``ctx.sync_emitter`` instead of
   ``ctx.emitter_for_engine`` bypasses the decision-log wrapper and silently
   drops decision events.

The guard reads source text only; it must never import the runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_ADR = "docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_NEXT = _REPO_ROOT / "src" / "runtime" / "next"
_BRIDGE = _RUNTIME_NEXT / "runtime_bridge.py"
_CANONICAL_SEAM = "src/runtime/next/_internal_runtime/events.py"
_THIS_FILE = Path(__file__).resolve()

_SEAM_CLASS_RE = re.compile(r"^class RuntimeEventEmitter\b", re.MULTILINE)
_DELETED_MODULE_IMPORT_RE = re.compile(r"runtime\.next\.event_emitter\b|from runtime\.next import event_emitter\b")

# Engine-facing bridge call sites that must receive the decision-log-wrapping
# ``ctx.emitter_for_engine``; passing the plain seam reintroduces the bypass.
_BRIDGE_BYPASS_NEEDLES = ("flush(ctx.sync_emitter)", "sync_emitter=ctx.sync_emitter")


def _py_files(root: Path) -> list[Path]:
    """Every ``.py`` file under ``root``, skipping virtualenvs and this guard."""
    return [p for p in sorted(root.rglob("*.py")) if ".venv" not in p.parts and p.resolve() != _THIS_FILE]


def _relative(path: Path) -> str:
    """Repo-relative posix path; falls back to the absolute path for a file outside the repo (a scratch copy)."""
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _seam_class_definitions(root: Path) -> list[str]:
    return [_relative(p) for p in _py_files(root) if _SEAM_CLASS_RE.search(p.read_text(encoding="utf-8"))]


def _deleted_module_importers(*roots: Path) -> list[str]:
    files = [p for root in roots for p in _py_files(root)]
    return [_relative(p) for p in files if _DELETED_MODULE_IMPORT_RE.search(p.read_text(encoding="utf-8"))]


def _bridge_bypass_hits(bridge_source: str, needle: str) -> list[int]:
    return [number for number, line in enumerate(bridge_source.splitlines(), start=1) if needle in line]


def test_exactly_one_runtime_event_emitter_class() -> None:
    """S7: exactly one ``RuntimeEventEmitter`` lives under ``src/runtime/next/``."""
    assert _seam_class_definitions(_RUNTIME_NEXT) == [_CANONICAL_SEAM], f"one canonical seam class only ({_CANONICAL_SEAM}); see {_ADR}"


def test_deleted_event_emitter_module_is_not_imported() -> None:
    """S7: ``runtime.next.event_emitter`` was deleted and must not be referenced."""
    offenders = _deleted_module_importers(_REPO_ROOT / "src", _REPO_ROOT / "tests")
    assert offenders == [], f"runtime.next.event_emitter was deleted; see {_ADR}: {offenders}"


def test_bridge_obtains_seam_only_through_factory() -> None:
    """S8: the bridge imports ``runtime_emitter_for_mission`` by name and never constructs a concrete class."""
    source = _BRIDGE.read_text(encoding="utf-8")
    assert "runtime_emitter_for_mission" in source, f"bridge must obtain the seam via runtime_emitter_for_mission; see {_ADR}"
    assert "RuntimeEventEmitter(" not in source, f"bridge must not construct a concrete RuntimeEventEmitter; see {_ADR}"


@pytest.mark.parametrize("needle", _BRIDGE_BYPASS_NEEDLES)
def test_bridge_never_hands_engine_paths_the_plain_seam(needle: str) -> None:
    """F7: no engine-facing bridge call site receives the plain ``ctx.sync_emitter``."""
    hits = _bridge_bypass_hits(_BRIDGE.read_text(encoding="utf-8"), needle)
    assert hits == [], (
        f"{needle!r} at {_relative(_BRIDGE)}:{hits} reintroduces the decision-log bypass fixed by {_ADR}; engine-facing calls must use ctx.emitter_for_engine"
    )


# --- helper self-checks (the guard's own branches, exercised on synthetic trees) ---


def test_seam_class_scan_reports_duplicates(tmp_path: Path) -> None:
    canonical = tmp_path / "src/runtime/next/_internal_runtime/events.py"
    duplicate = tmp_path / "src/runtime/next/event_emitter.py"
    for path in (canonical, duplicate):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("class RuntimeEventEmitter:\n    pass\n", encoding="utf-8")
    (tmp_path / "src/runtime/next/other.py").write_text("class RuntimeEventEmitterSpy:\n    pass\n", encoding="utf-8")
    hits = [p.relative_to(tmp_path).as_posix() for p in _py_files(tmp_path) if _SEAM_CLASS_RE.search(p.read_text(encoding="utf-8"))]
    assert hits == [_CANONICAL_SEAM, "src/runtime/next/event_emitter.py"]


def test_relative_falls_back_to_absolute_outside_repo(tmp_path: Path) -> None:
    outside = tmp_path / "runtime_bridge.py"
    assert _relative(_BRIDGE) == "src/runtime/next/runtime_bridge.py"
    assert _relative(outside) == outside.as_posix()


def test_deleted_module_regex_matches_both_import_forms() -> None:
    assert _DELETED_MODULE_IMPORT_RE.search("from runtime.next.event_emitter import RuntimeEventEmitter")
    assert _DELETED_MODULE_IMPORT_RE.search("from runtime.next import event_emitter")
    assert _DELETED_MODULE_IMPORT_RE.search("from runtime.next._internal_runtime.events import RuntimeEventEmitter") is None


@pytest.mark.parametrize("needle", _BRIDGE_BYPASS_NEEDLES)
def test_bridge_bypass_scan_locates_reintroduced_lines(needle: str) -> None:
    fixed = "def run(ctx):\n    buffer.flush(ctx.emitter_for_engine)\n    dispatch(sync_emitter=ctx.emitter_for_engine)\n"
    assert _bridge_bypass_hits(fixed, needle) == []
    reintroduced = fixed.replace("ctx.emitter_for_engine", "ctx.sync_emitter")
    assert _bridge_bypass_hits(reintroduced, needle) == [2 if needle.startswith("flush") else 3]
