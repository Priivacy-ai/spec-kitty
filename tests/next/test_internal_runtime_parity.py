"""Parity tests for the internalized runtime against frozen upstream snapshots.

These tests load the JSON snapshots committed under
``tests/fixtures/runtime_parity/`` (captured from the upstream
``spec_kitty_runtime`` 0.4.x source) and re-run the equivalent scenarios
through the internalized runtime ``specify_cli.next._internal_runtime``.
The internalized output must match byte-for-byte modulo timestamp / path
normalization (handled inside the capture script).

WP01 acceptance gate: if any snapshot diffs, the internalized runtime is
not behaviorally identical to the upstream — fix the relevant sub-module.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "runtime_parity"


def _load_capture_module() -> ModuleType:
    """Import ``_capture_baselines.py`` from disk by file path.

    The fixtures directory is intentionally not a Python package, so we
    can't use a normal ``import`` statement. importlib's spec_from_file_location
    avoids the namespace-package vs. package ambiguity entirely.
    """
    spec = importlib.util.spec_from_file_location(
        "_capture_baselines",
        FIXTURE_DIR / "_capture_baselines.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SNAPSHOT_FILES = (
    "snapshot_start_mission_run.json",
    "snapshot_next_step_1.json",
    "snapshot_provide_decision_answer.json",
    "snapshot_next_step_2.json",
)


@pytest.fixture(scope="module")
def captured_snapshots() -> dict[str, dict]:
    """Run the internalized runtime against the reference fixture in-process."""
    capture_module = _load_capture_module()
    return capture_module.capture(target="internal", out_dir=None)


@pytest.fixture(scope="module")
def golden_baselines() -> dict[str, dict]:
    """Load the committed golden baselines from disk."""
    baselines: dict[str, dict] = {}
    for name in SNAPSHOT_FILES:
        path = FIXTURE_DIR / name
        baselines[name] = json.loads(path.read_text(encoding="utf-8"))
    return baselines


@pytest.mark.parametrize("snapshot_name", SNAPSHOT_FILES)
def test_internalized_runtime_matches_upstream_snapshot(
    snapshot_name: str,
    captured_snapshots: dict[str, dict],
    golden_baselines: dict[str, dict],
) -> None:
    """Each captured snapshot from the internalized runtime must equal the golden."""
    captured = captured_snapshots[snapshot_name]
    expected = golden_baselines[snapshot_name]

    # Byte-equal comparison via canonical JSON encoding (sort_keys, indent=2)
    captured_text = json.dumps(captured, sort_keys=True, indent=2)
    expected_text = json.dumps(expected, sort_keys=True, indent=2)

    assert captured_text == expected_text, f"Parity drift in {snapshot_name}:\n--- expected\n{expected_text}\n+++ captured\n{captured_text}"


def test_no_spec_kitty_runtime_imports_in_internal_package() -> None:
    """Forbidden-imports gate: independence is the entire point of WP01.

    Walks the ``_internal_runtime`` source files and asserts none of them
    import from ``spec_kitty_runtime`` (top-level, lazy, or conditional).
    """
    package_root = Path(__file__).resolve().parents[1].parent / "src" / "specify_cli" / "next" / "_internal_runtime"
    offenders: list[tuple[Path, int, str]] = []
    for py_file in package_root.rglob("*.py"):
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            # Match `import spec_kitty_runtime` and `from spec_kitty_runtime…`
            # but ignore any string/docstring mention (look only at top-of-line).
            if stripped.startswith("import spec_kitty_runtime") or stripped.startswith("from spec_kitty_runtime"):
                offenders.append((py_file, lineno, line))
    assert not offenders, "spec_kitty_runtime imports must not appear inside _internal_runtime/:\n" + "\n".join(f"  {p}:{n}: {ln}" for p, n, ln in offenders)


def test_no_rich_or_typer_imports_in_internal_package() -> None:
    """Layer-rule gate: presentation belongs in the CLI layer, not the runtime."""
    package_root = Path(__file__).resolve().parents[1].parent / "src" / "specify_cli" / "next" / "_internal_runtime"
    offenders: list[tuple[Path, int, str]] = []
    for py_file in package_root.rglob("*.py"):
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.lstrip()
            for forbidden in ("rich", "typer"):
                if stripped.startswith(f"import {forbidden}") or stripped.startswith(f"from {forbidden}"):
                    offenders.append((py_file, lineno, line))
    assert not offenders, "rich/typer imports must not appear inside _internal_runtime/:\n" + "\n".join(f"  {p}:{n}: {ln}" for p, n, ln in offenders)


def test_public_surface_matches_contract() -> None:
    """The package __all__ exposes exactly the symbols listed in the contract."""
    from specify_cli.next import _internal_runtime as ir

    expected_surface = {
        "DiscoveryContext",
        "MissionPolicySnapshot",
        "MissionRunRef",
        "NextDecision",
        "NullEmitter",
        "next_step",
        "provide_decision_answer",
        "start_mission_run",
    }
    assert set(ir.__all__) == expected_surface
    for name in expected_surface:
        assert hasattr(ir, name), f"Public surface missing: {name}"


def test_submodule_surface_matches_contract() -> None:
    """schema/engine/planner sub-modules expose their contract symbols."""
    from specify_cli.next._internal_runtime import engine, planner, schema

    assert hasattr(schema, "ActorIdentity")
    assert hasattr(schema, "load_mission_template_file")
    assert hasattr(schema, "MissionRuntimeError")
    assert hasattr(engine, "_read_snapshot")
    assert hasattr(planner, "plan_next")
