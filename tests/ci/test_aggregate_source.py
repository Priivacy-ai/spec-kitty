"""Aggregate coverage must score the source PR without executing its checkout."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.fast]
ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/aggregate_source.py"


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(cwd), *args], text=True).strip()


def source_fixture(tmp_path: Path) -> tuple[Path, dict, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    (repo / ".github").mkdir()
    (repo / ".github/ci-module-registry.yml").write_text("modules: []\n")
    (repo / "src/kernel").mkdir(parents=True)
    (repo / "src/kernel/example.py").write_text("value = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "src/kernel/example.py").write_text("value = 1\nnew_value = 2\n")
    (repo / ".github/ci-module-registry.yml").write_text("modules: [{module: kernel, tier: standard, shard_count: 1}]\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "source")
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    merge = git(repo, "commit-tree", tree, "-p", base, "-p", head, "-m", "synthetic PR merge")
    git(repo, "update-ref", "refs/pull/7/merge", merge)
    git(repo, "checkout", "-q", base)
    git(repo, "remote", "add", "origin", str(repo))
    run = {
        "id": 42,
        "run_attempt": 1,
        "path": ".github/workflows/ci-modules.yml",
        "event": "pull_request",
        "head_sha": head,
        "repository": {"full_name": "spec-kitty/spec-kitty"},
        "referenced_workflows": [{"path": f"spec-kitty/spec-kitty/.github/workflows/module-tests.yml@{merge}", "sha": merge, "ref": "refs/pull/7/merge"}],
        "pull_requests": [{"number": 7, "head": {"sha": head}, "base": {"sha": base, "repo": {"full_name": "spec-kitty/spec-kitty"}}}],
    }
    return repo, run, base


def run_source(repo: Path, run: dict) -> subprocess.CompletedProcess[str]:
    source = repo / "source-run.json"
    source.write_text(json.dumps(run))
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(source), "--repository", "spec-kitty/spec-kitty", "--run-id", "42", "--attempt", "1"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )


def test_source_registry_and_diff_are_from_pr_while_checkout_stays_trusted(tmp_path: Path) -> None:
    repo, run, trusted = source_fixture(tmp_path)
    result = run_source(repo, run)
    assert result.returncode == 0, result.stderr
    out = repo / "out/aggregate/source"
    assert "new_value = 2" in (out / "diff.patch").read_text()
    assert yaml.safe_load((out / "ci-module-registry.yml").read_text())["modules"][0]["module"] == "kernel"
    assert json.loads((out / "source.json").read_text())["head_sha"] == run["head_sha"]
    assert git(repo, "rev-parse", "HEAD") == trusted


@pytest.mark.parametrize("mutation", ["stale_attempt", "wrong_run", "wrong_repo", "wrong_workflow", "missing_reference", "bad_sha"])
def test_source_rejects_ambiguous_or_stale_evidence(tmp_path: Path, mutation: str) -> None:
    repo, run, trusted = source_fixture(tmp_path)
    if mutation == "stale_attempt":
        run["run_attempt"] = 2
    elif mutation == "wrong_run":
        run["id"] = 43
    elif mutation == "wrong_repo":
        run["repository"]["full_name"] = "other/repo"
    elif mutation == "wrong_workflow":
        run["path"] = ".github/workflows/untrusted.yml"
    elif mutation == "missing_reference":
        run["referenced_workflows"] = []
    else:
        run["head_sha"] = "--upload-pack=evil"
    result = run_source(repo, run)
    assert result.returncode != 0
    assert not (repo / "out/aggregate/source/source.json").exists()
    assert git(repo, "rev-parse", "HEAD") == trusted


def test_shipped_diff_cover_rejects_uncovered_pr_line_on_trusted_checkout(tmp_path: Path) -> None:
    repo, run, _trusted = source_fixture(tmp_path)
    assert run_source(repo, run).returncode == 0
    git(repo, "update-ref", "refs/remotes/origin/main", run["pull_requests"][0]["base"]["sha"])
    coverage = repo / "out/aggregate/coverage"
    coverage.mkdir(parents=True)
    (coverage / "coverage-standard-kernel-shard1-of-1.xml").write_text(
        '<coverage><sources><source>.</source></sources><packages><package name="kernel">'
        '<classes><class name="example" filename="src/kernel/example.py"><lines>'
        '<line number="1" hits="1"/><line number="2" hits="0"/>'
        "</lines></class></classes></package></packages></coverage>"
    )
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci-aggregate.yml").read_text())
    gate = next(s["run"] for s in workflow["jobs"]["diff-cover"]["steps"] if s.get("name", "").startswith("diff-cover —"))
    gate = gate.replace("${{ steps.census.outputs.exclude-flags }}", "").replace("${{ steps.base-ref.outputs.base }}", "main")
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
    result = subprocess.run(["bash", "-c", gate], cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "0%" in result.stdout, result.stdout + result.stderr


def test_base_line_insertions_use_tested_merge_line_numbers(tmp_path: Path) -> None:
    repo, run, _trusted = source_fixture(tmp_path)
    filename = repo / "src/kernel/example.py"
    original = "".join(f"value_{i} = {i}\n" for i in range(80))
    filename.write_text(original)
    git(repo, "add", "src/kernel/example.py")
    git(repo, "commit", "-qm", "common eighty line base")
    common = git(repo, "rev-parse", "HEAD")
    filename.write_text(original + "new_uncovered = 1\n")
    git(repo, "add", "src/kernel/example.py")
    git(repo, "commit", "-qm", "PR uncovered line")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", common)
    filename.write_text("base_prefix = 1\n" + original)
    git(repo, "add", "src/kernel/example.py")
    git(repo, "commit", "-qm", "base inserted line")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "merge", "--no-ff", "-qm", "synthetic merge", head)
    merged = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/pull/7/merge", merged)
    git(repo, "checkout", "-q", base)
    run["head_sha"] = run["pull_requests"][0]["head"]["sha"] = head
    run["pull_requests"][0]["base"]["sha"] = base
    run["referenced_workflows"][0].update(sha=merged, path=f"spec-kitty/spec-kitty/.github/workflows/module-tests.yml@{merged}")
    assert run_source(repo, run).returncode == 0
    diff = (repo / "out/aggregate/source/diff.patch").read_text()
    assert "+79,4" in diff, diff
    coverage = repo / "coverage.xml"
    coverage.write_text(
        '<coverage><packages><package name="kernel"><classes>'
        '<class filename="src/kernel/example.py"><lines>'
        '<line number="81" hits="1"/><line number="82" hits="0"/>'
        "</lines></class></classes></package></packages></coverage>"
    )
    result = subprocess.run(
        [str(Path(sys.executable).parent / "diff-cover"), str(coverage), "--diff-file=out/aggregate/source/diff.patch", "--fail-under=90"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "0%" in result.stdout
    assert json.loads((repo / "out/aggregate/source/source.json").read_text())["tested_sha"] == merged
    assert git(repo, "rev-parse", "HEAD") == base


def test_live_pr_and_merge_ref_movement_do_not_replace_immutable_tested_source(tmp_path: Path) -> None:
    repo, run, trusted = source_fixture(tmp_path)
    tested = run["referenced_workflows"][0]["sha"]
    git(repo, "update-ref", "refs/pull/7/merge", trusted)
    run["pull_requests"][0]["head"]["sha"] = "f" * 40
    result = run_source(repo, run)
    assert result.returncode == 0, result.stderr
    assert json.loads((repo / "out/aggregate/source/source.json").read_text())["tested_sha"] == tested


def test_immutable_reference_must_bind_the_source_head(tmp_path: Path) -> None:
    repo, run, trusted = source_fixture(tmp_path)
    run["referenced_workflows"][0].update(sha=trusted, path=f"spec-kitty/spec-kitty/.github/workflows/module-tests.yml@{trusted}")
    result = run_source(repo, run)
    assert result.returncode != 0
    assert "tested merge parents" in result.stderr
