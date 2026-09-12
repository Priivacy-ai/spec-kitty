"""Only endpoint-conclusive evaluation evidence may enter committed history."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.fast]


def document():
    counts = {"passCount": 0, "totalRuns": 5, "runsErrored": 0}
    return {
        "perProfile": {"profile": {"axis": counts.copy()}},
        "doctrineManifests": [],
        "controlManifest": {
            name: dict(counts, passed=passed) for name, passed in [("judgeControl", False), ("behavioralControl", False), ("judgePositiveControl", True)]
        },
    }


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("model_fail", "true"),
        ("endpoint_error", "false"),
        ("positive_fail", "false"),
        ("negative_pass", "false"),
        ("empty_profiles", "false"),
        ("empty_axes", "false"),
        ("malformed_count", "false"),
        ("doctrine_error", "false"),
    ],
)
def test_publication_discriminates_health(tmp_path, mutation, expected):
    doc = document()
    if mutation == "endpoint_error":
        doc["perProfile"]["profile"]["axis"]["runsErrored"] = 1
    if mutation == "positive_fail":
        doc["controlManifest"]["judgePositiveControl"]["passed"] = False
    if mutation == "negative_pass":
        doc["controlManifest"]["judgeControl"]["passed"] = True
    if mutation == "empty_profiles":
        doc["perProfile"] = {}
    if mutation == "empty_axes":
        doc["perProfile"] = {"profile": {}}
    if mutation == "malformed_count":
        doc["controlManifest"]["judgeControl"]["runsErrored"] = "0"
    if mutation == "doctrine_error":
        doc["doctrineManifests"] = [{"runsErrored": 1, "perCase": []}]
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(doc))
    result = subprocess.run(["node", str(ROOT / "conformance/scripts/evidence-publication.mjs"), str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_workflow_uploads_diagnostics_but_only_commits_conclusive():
    workflow = YAML(typ="safe").load((ROOT / ".github/workflows/behavioral.yml").read_text())
    steps = workflow["jobs"]["merge-evidence"]["steps"]
    commit = next(x for x in steps if x.get("name") == "Commit the gate artifact back to the branch")
    assert "steps.publication.outputs.conclusive == 'true'" in commit["if"]
    classifier = next(x for x in steps if x.get("id") == "publication")
    assert "node conformance/scripts/evidence-publication.mjs" in classifier["run"]
    merge = next(x for x in steps if x.get("id") == "merge")
    assert "--out-dir /tmp/behavioral-gate-evidence" in merge["run"]
    assert "--out-dir conformance/behavioral/evidence" not in merge["run"]
    upload = next(x for x in steps if x.get("uses", "").startswith("actions/upload-artifact"))
    assert "conclusive" not in upload["if"]


def test_workflows_use_current_muster_pin():
    for filename in ["conformance.yml", "crosslayer.yml", "skill-trigger-routing.yml", "behavioral.yml"]:
        workflow = YAML(typ="safe").load((ROOT / ".github/workflows" / filename).read_text())
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if step.get("uses", "").startswith("garrison-hq/muster-action@"):
                    assert step["with"]["version"] == "1.2.2"
                run = step.get("run", "")
                assert "@garrison-hq/muster@1.2.1" not in run
                assert "@garrison-hq/muster@1.1.0" not in run
