"""Evidence schema rejects malformed types/ranges through the shipped Node CLI."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "conformance/scripts/check-evidence-artifact-shape.mjs"
pytestmark = [pytest.mark.fast]


def valid_evidence():
    return {
        "timestamp": "2026-09-12T10:00:00Z",
        "model": "test-model",
        "endpointHost": "example.invalid",
        "cases": [
            {
                "id": "case",
                "isControl": False,
                "passed": True,
                "runsErrored": 0,
                "shouldTrigger": {"triggerRate": 1, "threshold": 0.5, "passed": True},
                "nearMiss": {"triggerRate": 0, "threshold": 0.5, "passed": True},
            }
        ],
    }


@pytest.mark.parametrize(
    "path,value",
    [
        (("timestamp",), 12),
        (("timestamp",), "2026-09-12T24:00:00Z"),
        (("timestamp",), "2026-02-30T10:00:00Z"),
        (("model",), False),
        (("model",), ""),
        (("endpointHost",), {}),
        (("cases",), []),
        (("cases", 0, "id"), 1),
        (("cases", 0, "id"), ""),
        (("cases", 0, "isControl"), "false"),
        (("cases", 0, "passed"), "true"),
        (("cases", 0, "runsErrored"), -1),
        (("cases", 0, "runsErrored"), 0.5),
        (("cases", 0, "runsErrored"), False),
        (("cases", 0, "shouldTrigger"), []),
        *[
            (("cases", 0, axis, field), value)
            for axis in ["shouldTrigger", "nearMiss"]
            for field in ["triggerRate", "threshold"]
            for value in ["0.5", None, False, -0.01, 1.01]
        ],
        *[(("cases", 0, axis, "passed"), "true") for axis in ["shouldTrigger", "nearMiss"]],
    ],
)
def test_invalid_field_is_rejected(tmp_path, path, value):
    doc = valid_evidence()
    target = doc
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    file = tmp_path / "evidence.json"
    file.write_text(json.dumps(doc))
    result = subprocess.run(["node", str(SCRIPT), str(file)], capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL" in result.stdout


@pytest.mark.parametrize("doc", [None, [], 1, True])
def test_non_object_is_rejected(tmp_path, doc):
    file = tmp_path / "evidence.json"
    file.write_text(json.dumps(doc))
    result = subprocess.run(["node", str(SCRIPT), str(file)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "FAIL" in result.stdout


def test_valid_boundary_values_are_accepted(tmp_path):
    file = tmp_path / "evidence.json"
    file.write_text(json.dumps(valid_evidence()))
    result = subprocess.run(["node", str(SCRIPT), str(file)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
