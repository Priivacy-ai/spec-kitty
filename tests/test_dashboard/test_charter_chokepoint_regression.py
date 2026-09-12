"""FR-014 dashboard-typed-contracts regression test.

Runs the committed ``baseline/capture.py`` script against the current tree
(post-WP03 code) and asserts byte-identical JSON against the committed
``baseline/pre-wp23-dashboard-typed.json`` anchor.

If this test fails, WP03's T019 dashboard rewire changed typed-contract
semantics. The bar is byte-identical; do NOT loosen the comparison.
Fix the rewire instead.
"""

from __future__ import annotations

import difflib
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_DIR = (
    _REPO_ROOT
    / "kitty-specs"
    / "unified-charter-bundle-chokepoint-01KP5Q2G"
    / "baseline"
)
_BASELINE_SCRIPT = _BASELINE_DIR / "capture.py"
_BASELINE_JSON = _BASELINE_DIR / "pre-wp23-dashboard-typed.json"


def _run_capture(cwd: Path) -> str:
    """Execute ``baseline/capture.py`` with the repo ``src/`` on sys.path.

    The capture script itself inserts ``src/`` onto ``sys.path``; we just
    run it as a subprocess so no module state leaks between the test
    process and the capture run.
    """
    result = subprocess.run(
        [sys.executable, str(_BASELINE_SCRIPT)],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    return result.stdout


def _normalize(raw: str) -> str:
    """Load -> re-dump with sort_keys to paper over any whitespace drift
    that doesn't affect JSON semantics."""
    data = json.loads(raw)
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _remove_dashboard_extensions(data: dict[str, object]) -> dict[str, object]:
    """Remove the explicitly versioned fields added after the frozen baseline."""
    features = data.get("features")
    if not isinstance(features, list):
        return data

    for feature in features:
        if not isinstance(feature, dict):
            continue
        assert feature["mission_status"] in {"active", "planned", "done", "draft"}
        assert feature["next_action"] is None or isinstance(feature["next_action"], str)
        feature.pop("mission_status")
        feature.pop("next_action")
    return data


def test_dashboard_typed_contracts_are_byte_identical_to_baseline(tmp_path: Path) -> None:
    """Byte-identical historical contract assertion against the baseline.

    The archived baseline predates ``mission_status`` and ``next_action``.
    Those two fields are checked for presence and type, then removed before
    comparing every historical field byte-for-byte in canonical JSON form. On
    failure, a unified diff shows exactly which pre-existing key(s) drifted.
    """
    assert _BASELINE_SCRIPT.exists(), f"baseline capture script missing: {_BASELINE_SCRIPT}"
    assert _BASELINE_JSON.exists(), f"baseline JSON anchor missing: {_BASELINE_JSON}"

    expected_data = json.loads(_BASELINE_JSON.read_text(encoding="utf-8"))
    actual_data = _remove_dashboard_extensions(json.loads(_run_capture(tmp_path)))
    expected = _normalize(json.dumps(expected_data))
    actual = _normalize(json.dumps(actual_data))

    if expected == actual:
        return

    diff = "\n".join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile="baseline/pre-wp23-dashboard-typed.json",
            tofile="post-WP03 capture",
            lineterm="",
        )
    )
    pytest.fail(
        "Dashboard typed-contract JSON has drifted from the pre-WP03 baseline.\n"
        "The WP03 dashboard reader cutover must preserve WPState/Lane typed "
        "contracts byte-identically. Fix the rewire; do not loosen this "
        "assertion.\n\nUnified diff:\n" + diff
    )
