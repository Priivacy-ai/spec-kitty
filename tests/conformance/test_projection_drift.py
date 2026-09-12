"""Mutations prove body and sidecar guards reject stale or absent projections."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.fast]


@pytest.fixture(scope="module")
def checker():
    tools = ROOT / "conformance/behavioral/tools"
    sys.path.insert(0, str(tools))
    try:
        spec = importlib.util.spec_from_file_location("projection_check", tools / "check-projection-drift.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(tools))


@pytest.fixture
def project(tmp_path):
    name = "architect-alphonso"
    for relative in [
        f"packs/built-in/agent_profiles/{name}.agent.yaml",
        f"conformance/behavioral/profiles/{name}.yaml",
        f"conformance/behavioral/projected/{name}.md",
        f"conformance/behavioral/projected/{name}.md.sha256",
    ]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def test_current_projection_is_valid(checker, project):
    assert checker.check(project) == []


@pytest.mark.parametrize("mutation", ["body", "hash", "source", "missing_manifest"])
def test_drift_cannot_pass(checker, project, mutation):
    base = project / "conformance/behavioral"
    if mutation == "body":
        (base / "projected/architect-alphonso.md").write_text("stale")
    if mutation == "hash":
        (base / "projected/architect-alphonso.md.sha256").write_text("sha256:wrong\n")
    if mutation == "source":
        source = project / "packs/built-in/agent_profiles/architect-alphonso.agent.yaml"
        source.write_text(source.read_text() + "\n# source changed\n")
    if mutation == "missing_manifest":
        (base / "profiles/architect-alphonso.yaml").unlink()
    assert checker.check(project)
