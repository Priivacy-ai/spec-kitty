"""Only endpoint-conclusive evaluation evidence may enter committed history."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import subprocess

import pytest
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.fast]


def expected_inventory():
    path = ROOT / "conformance/behavioral/tools/evidence_inventory.py"
    spec = importlib.util.spec_from_file_location("evidence_inventory", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inventory(ROOT)


def document():
    counts = {"passCount": 0, "totalRuns": 5, "runsErrored": 0}
    expected = expected_inventory()
    return {
        "perProfile": {profile: {axis: counts.copy() for axis in axes} for profile, axes in expected["perProfile"].items()},
        "doctrineManifests": [
            {"manifest": path, "runsErrored": 0, "perCase": [dict(counts, ruleId=rule) for rule in rules]} for path, rules in expected["doctrineManifests"].items()
        ],
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
        ("missing_profile", "false"),
        ("missing_axis", "false"),
        ("missing_doctrine", "false"),
        ("missing_case", "false"),
        ("duplicate_case", "false"),
        ("renamed_axis", "false"),
    ],
)
def test_publication_discriminates_health(tmp_path, mutation, expected):
    doc = document()
    profile = next(iter(doc["perProfile"]))
    axes = doc["perProfile"][profile]
    axis = next(iter(axes))
    if mutation == "endpoint_error":
        axes[axis]["runsErrored"] = 1
    if mutation == "missing_profile":
        del doc["perProfile"][profile]
    if mutation == "missing_axis":
        del axes[axis]
    if mutation == "renamed_axis":
        axes["wrong"] = axes.pop(axis)
    if mutation == "missing_doctrine":
        doc["doctrineManifests"].pop()
    if mutation == "missing_case":
        doc["doctrineManifests"][0]["perCase"].pop()
    if mutation == "duplicate_case":
        cases = doc["doctrineManifests"][0]["perCase"]
        cases[-1] = cases[0].copy()
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
    inventory = tmp_path / "expected.json"
    inventory.write_text(json.dumps(expected_inventory()))
    result = subprocess.run(["node", str(ROOT / "conformance/scripts/evidence-publication.mjs"), str(path), str(inventory)], capture_output=True, text=True)
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


def test_runner_and_publication_share_nonvacuous_manifest_catalog():
    workflow = YAML(typ="safe").load((ROOT / ".github/workflows/behavioral.yml").read_text())
    main = workflow["jobs"]["main-suite"]["steps"]
    run = next(step["run"] for step in main if step.get("name", "").startswith("Run main-suite manifests"))
    assert "evidence_inventory.py --paths" in run
    assert "profile_manifests=(" not in run
    expected = expected_inventory()
    paths = subprocess.run(
        ["python3", str(ROOT / "conformance/behavioral/tools/evidence_inventory.py"), "--paths"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    assert len(paths) == len(expected["perProfile"]) + len(expected["doctrineManifests"])
    assert len(expected["perProfile"]) >= 5
    assert set(expected["doctrineManifests"]).issubset(paths)


def test_inventory_refuses_missing_profile_before_running(tmp_path):
    import shutil

    for path in [ROOT / "conformance/behavioral/suite.json", *(ROOT / "conformance/behavioral/profiles").glob("*.yaml")]:
        target = tmp_path / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    next((tmp_path / "conformance/behavioral/profiles").glob("*.yaml")).unlink()
    spec = importlib.util.spec_from_file_location("missing_inventory", ROOT / "conformance/behavioral/tools/evidence_inventory.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="floor"):
        module.inventory(tmp_path)
