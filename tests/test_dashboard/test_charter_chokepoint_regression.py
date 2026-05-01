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

pytestmark = pytest.mark.fast


_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_DIR = _REPO_ROOT / "kitty-specs" / "unified-charter-bundle-chokepoint-01KP5Q2G" / "baseline"
_BASELINE_SCRIPT = _BASELINE_DIR / "capture.py"
_BASELINE_JSON = _BASELINE_DIR / "pre-wp23-dashboard-typed.json"


def _run_capture() -> str:
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
        cwd=str(_REPO_ROOT),
    )
    return result.stdout


def _normalize(raw: str) -> str:
    """Load -> re-dump with sort_keys to paper over any whitespace drift
    that doesn't affect JSON semantics."""
    data = json.loads(raw)
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def test_dashboard_typed_contracts_are_byte_identical_to_baseline() -> None:
    """Byte-identical assertion against the committed baseline.

    On failure, a unified diff of the canonical JSON representation is
    included so the diagnostician can see exactly which key(s) drifted.
    """
    assert _BASELINE_SCRIPT.exists(), f"baseline capture script missing: {_BASELINE_SCRIPT}"
    assert _BASELINE_JSON.exists(), f"baseline JSON anchor missing: {_BASELINE_JSON}"

    expected = _normalize(_BASELINE_JSON.read_text(encoding="utf-8"))
    actual = _normalize(_run_capture())

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
