"""Execute the shipped collector with a partial rerun's Actions API evidence."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml

from tests.ci.test_aggregate_source import ROOT, source_fixture

pytestmark = pytest.mark.fast


def artifact(module: str, attempt: int, artifact_id: int) -> dict:
    return {
        "id": artifact_id,
        "name": f"module-tests-{module}-shard-1-of-1-attempt-{attempt}-reports",
        "expired": False,
        "created_at": f"2026-09-09T0{attempt}:05:00Z",
        "workflow_run": {"id": 42},
    }


def job(module: str, execution_attempt: int) -> dict:
    leaf = f"module-tests ({module} shard 1/1)"
    return {
        "run_id": 42,
        # GitHub projects inherited jobs onto the requested attempt, keeping
        # their original execution timestamps (observed on run 34302853928/2).
        "run_attempt": 2,
        "name": f"{leaf} / {leaf}",
        "status": "completed",
        "conclusion": "success",
        "started_at": f"2026-09-09T0{execution_attempt}:00:00Z",
        "completed_at": f"2026-09-09T0{execution_attempt}:10:00Z",
    }


def collect(tmp_path: Path, artifacts: list[dict], jobs: list[dict], *, latest: int = 2, event: str = "workflow_run") -> subprocess.CompletedProcess[str]:
    repo, run, _ = source_fixture(tmp_path)
    run.update(run_attempt=2, status="completed", conclusion="success")
    for record in artifacts:
        record["workflow_run"].setdefault("head_sha", run["head_sha"])
    for record in jobs:
        record.setdefault("head_sha", run["head_sha"])
    api = tmp_path / "api.json"
    api.write_text(
        json.dumps(
            {
                "repos/spec-kitty/spec-kitty/actions/runs/42": dict(run, run_attempt=latest),
                "repos/spec-kitty/spec-kitty/actions/runs/42/attempts/2": run,
                "repos/spec-kitty/spec-kitty/actions/runs/42/attempts/2/jobs?per_page=100": [{"jobs": jobs[:1]}, {"jobs": jobs[1:]}],
                "repos/spec-kitty/spec-kitty/actions/runs/42/artifacts?per_page=100": [{"artifacts": artifacts[:1]}, {"artifacts": artifacts[1:]}],
            }
        )
    )
    bindir = tmp_path / "bin"
    bindir.mkdir()
    gh = bindir / "gh"
    gh.write_text(
        f"#!{sys.executable}\nimport json, os, sys\nendpoint = next(a for a in sys.argv if a.startswith('repos/'))\nprint(json.dumps(json.load(open(os.environ['FAKE_API']))[endpoint]))\n"
    )
    gh.chmod(0o755)
    (repo / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
    output = tmp_path / "outputs"
    env = dict(
        os.environ,
        PATH=f"{bindir}:{Path(sys.executable).parent}:{os.environ['PATH']}",
        FAKE_API=str(api),
        SOURCE_RUN_ID="42",
        SOURCE_RUN_ATTEMPT="2",
        SOURCE_REPOSITORY="spec-kitty/spec-kitty",
        RUNNER_TEMP=str(tmp_path),
        GITHUB_OUTPUT=str(output),
    )
    steps = yaml.safe_load((ROOT / ".github/workflows/ci-aggregate.yml").read_text())["jobs"]["collect"]["steps"]
    prepare = next(s for s in steps if s.get("name", "").startswith("Prepare exact source"))
    result = subprocess.run(["bash", "-c", prepare["run"]], cwd=repo, env=env, capture_output=True, text=True)
    if result.returncode:
        return result
    # The pre-existing reconcile entrypoint consumes the verified registry.
    (repo / "out/aggregate/source/ci-module-registry.yml").write_text(
        "modules:\n- {module: kernel, tier: standard, shard_count: 1}\n- {module: charter, tier: standard, shard_count: 1}\n"
    )
    selection = next((s for s in steps if s.get("id") == "select-current"), None)
    if selection:
        result = subprocess.run(["bash", "-c", selection["run"]], cwd=repo, env=env, capture_output=True, text=True)
        if result.returncode:
            return result
    context = {
        "github.event.workflow_run.run_attempt": "2" if event == "workflow_run" else "",
        "inputs.source_run_attempt": "2" if event == "workflow_dispatch" else "",
    }
    if output.exists():
        context.update({f"steps.select-current.outputs.{k}": v for k, v in (line.split("=", 1) for line in output.read_text().splitlines())})
    download = next(s for s in steps if s.get("id") == "download-current")
    pattern = re.sub(r"\$\{\{\s*(.*?)\s*\}\}", lambda m: next(context[k.strip()] for k in m[1].split("||") if context.get(k.strip())), download["with"]["pattern"])
    # Model download-artifact's minimatch against returned names, including
    # brace alternatives. Only this remote action boundary is substituted.
    patterns = pattern[1:-1].split(",") if pattern.startswith("{") else [pattern]
    for record in artifacts:
        if any(fnmatchcase(record["name"], p) for p in patterns):
            module = record["name"].split("-shard-")[0].removeprefix("module-tests-")
            directory = repo / "out/aggregate/current" / record["name"]
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"coverage-standard-{module}-shard1-of-1.xml").write_text("<coverage/>")
    reconcile = next(s for s in steps if s.get("id") == "reconcile")
    return subprocess.run(["bash", "-c", reconcile["run"]], cwd=repo, env=env, capture_output=True, text=True)


@pytest.mark.parametrize("event", ["workflow_run", "workflow_dispatch"])
def test_partial_rerun_collects_carried_forward_shard_and_latest_replacement(tmp_path: Path, event: str) -> None:
    result = collect(tmp_path, [artifact("kernel", 1, 1), artifact("charter", 1, 2), artifact("charter", 2, 3)], [job("kernel", 1), job("charter", 2)], event=event)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "resolved 2/2" in result.stdout


def test_manual_replay_uses_requested_attempt_after_a_newer_rerun(tmp_path: Path) -> None:
    result = collect(
        tmp_path,
        [artifact("kernel", 1, 1), artifact("charter", 2, 2), artifact("kernel", 3, 3), artifact("charter", 3, 4)],
        [job("kernel", 1), job("charter", 2)],
        latest=3,
        event="workflow_dispatch",
    )
    assert result.returncode == 0, result.stdout + result.stderr
