"""Exercise metadata verdict decisions and publication via an in-memory API port."""

from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.ci.fleet_verdict import (
    AGGREGATE,
    MARKER,
    PR_WORKFLOWS,
    applicable_workflows,
    classify,
    comment_body,
    latest_run,
    report,
    snapshot,
)

pytestmark = pytest.mark.fast
ROOT = Path(__file__).resolve().parents[2]
REPO = "spec-kitty/spec-kitty"
HEAD = "a" * 40
IDS = {name: i for i, name in enumerate(sorted(PR_WORKFLOWS | {AGGREGATE}), start=1)}


def pull() -> dict[str, Any]:
    return {"number": 7, "state": "open", "head": {"sha": HEAD}, "base": {"ref": "main"}, "labels": [], "changed_files": 1}


def run(name: str, **updates: Any) -> dict[str, Any]:
    row = {
        "id": IDS[name] * 10,
        "created_at": "2026-09-08T10:00:00Z",
        "run_attempt": 1,
        "workflow_id": IDS[name],
        "path": f".github/workflows/{name}",
        "repository": {"full_name": REPO},
        "head_sha": HEAD,
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
        "pull_requests": [{"number": 7, "head": {"sha": HEAD}, "base": {"repo": {"url": f"https://api.github.com/repos/{REPO}"}}}],
        "html_url": f"https://github.com/{REPO}/actions/runs/{IDS[name] * 10}",
    }
    row.update(updates)
    return row


class API:
    repository = REPO

    def __init__(self) -> None:
        self.pr = pull()
        self.files = [{"filename": "src/kernel/example.py"}]
        self.runs = {name: [run(name)] for name in PR_WORKFLOWS}
        modules = self.runs["ci-modules.yml"][0]
        self.runs[AGGREGATE] = [run(AGGREGATE, event="workflow_run", head_sha="b" * 40, display_title=f"CI Aggregate source {modules['id']} attempt 1")]
        self.comments: list[dict[str, Any]] = []
        self.posts: list[dict[str, Any]] = []
        self.pr_reads = 0
        self.move_on_second_read = False

    def request(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        if payload is not None:
            self.posts.append(payload)
            return {"body": payload["body"]}
        if path.startswith("actions/runs/"):
            identity = int(path.rsplit("/", 1)[1])
            return copy.deepcopy(next(row for rows in self.runs.values() for row in rows if row["id"] == identity))
        assert path == "pulls/7"
        self.pr_reads += 1
        result = copy.deepcopy(self.pr)
        if self.move_on_second_read and self.pr_reads > 1:
            result["head"]["sha"] = "c" * 40
        return result

    def pages(self, path: str, field: str | None = None) -> list[dict[str, Any]]:
        if path == "pulls/7/files":
            return copy.deepcopy(self.files)
        if path == "issues/7/comments":
            return copy.deepcopy(self.comments)
        if path.startswith("actions/runs?"):
            return copy.deepcopy([row for name, rows in self.runs.items() if name != AGGREGATE for row in rows])
        workflow_id = int(path.split("/")[2])
        name = next(name for name, identity in IDS.items() if identity == workflow_id)
        return copy.deepcopy(self.runs[name])


def test_all_existing_pr_workflows_are_registered() -> None:
    expected = PR_WORKFLOWS
    assert applicable_workflows(ROOT, pull(), ["pyproject.toml"]) == expected
    assert applicable_workflows(ROOT, pull(), ["docs/example.md"]) == expected - {"release-readiness.yml", "check-spec-kitty-events-alignment.yml"}
    release = pull()
    release["base"]["ref"] = "release/3.2.6.x"
    assert applicable_workflows(ROOT, release, ["pyproject.toml"]) == {"ci-router.yml", "ci-modules.yml", "ci-quality.yml", "packs.yml"}


def test_new_pr_workflow_fails_closed(tmp_path: Path) -> None:
    directory = tmp_path / ".github/workflows"
    directory.mkdir(parents=True)
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        (directory / path.name).write_bytes(path.read_bytes())
    (directory / "new.yml").write_text("on: {pull_request: {}}\njobs: {}\n")
    with pytest.raises(ValueError, match="inventory changed"):
        applicable_workflows(tmp_path, pull(), ["docs/a.md"])


def test_reporter_trigger_covers_every_registered_workflow_and_reruns() -> None:
    workflows = ROOT / ".github/workflows"
    reporter = yaml.safe_load((workflows / "ci-fleet-verdict.yml").read_text())
    trigger = reporter[True]["workflow_run"]
    assert set(trigger["workflows"]) == {yaml.safe_load((workflows / name).read_text())["name"] for name in PR_WORKFLOWS | {AGGREGATE}}
    assert set(trigger["types"]) == {"requested", "in_progress", "completed"}
    assert "matrix.pr" in reporter["jobs"]["report"]["concurrency"]["group"]
    assert reporter["jobs"]["report"]["concurrency"]["cancel-in-progress"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("event", "push"),
        ("head_sha", "b" * 40),
        ("workflow_id", 999),
        ("path", ".github/workflows/fake.yml"),
        ("repository", {"full_name": "other/repo"}),
        ("pull_requests", []),
    ],
)
def test_spoofed_or_unassociated_run_cannot_supply_evidence(field: str, value: Any) -> None:
    name = "ci-modules.yml"
    candidate = run(name, **{field: value})
    assert latest_run([candidate], workflow_id=IDS[name], repository=REPO, head=HEAD, number=7, name=name) is None


@pytest.mark.parametrize(
    "status,conclusion,expected",
    [
        ("in_progress", None, "running"),
        ("queued", None, "running"),
        ("completed", "cancelled", "running"),
        ("completed", "skipped", "running"),
        ("completed", "failure", "red"),
        ("completed", "success", "green"),
    ],
)
def test_latest_attempt_dominates_older_green(status: str, conclusion: str | None, expected: str) -> None:
    api = API()
    name = "ci-modules.yml"
    old = api.runs[name][0]
    api.runs[name].append(run(name, run_attempt=2, status=status, conclusion=conclusion))
    api.runs[AGGREGATE][0]["display_title"] = f"CI Aggregate source {old['id']} attempt 2"
    _, evidence = snapshot(api, ROOT, 7, IDS)
    assert evidence["state"] == expected


def test_aggregate_from_wrong_source_or_attempt_cannot_green() -> None:
    api = API()
    api.runs[AGGREGATE][0]["display_title"] = "CI Aggregate source 99999 attempt 1"
    assert snapshot(api, ROOT, 7, IDS)[1]["state"] == "running"
    api.runs[AGGREGATE][0]["display_title"] = f"CI Aggregate source {api.runs['ci-modules.yml'][0]['id']} attempt 1"
    api.runs[AGGREGATE][0]["event"] = "workflow_dispatch"
    assert snapshot(api, ROOT, 7, IDS)[1]["state"] == "running"


def test_missing_path_applicable_gate_is_pending() -> None:
    api = API()
    api.files = [{"filename": "pyproject.toml"}]
    api.runs["release-readiness.yml"] = []
    assert snapshot(api, ROOT, 7, IDS)[1]["state"] == "running"


def test_truncated_files_and_deferred_pr_never_green() -> None:
    api = API()
    api.pr["changed_files"] = 3001
    with pytest.raises(ValueError, match="incomplete"):
        snapshot(api, ROOT, 7, IDS)
    assert classify({"gate": run("ci-modules.yml")}, {"pr:skip-ci"}) == "running"
    assert classify({}, set()) == "running"


def test_publication_rechecks_head_and_never_mutates_existing_comments() -> None:
    api = API()
    api.move_on_second_read = True
    with pytest.raises(ValueError, match="changed before publication"):
        report(api, ROOT, 7, IDS, 123, 1)
    assert api.posts == []
    api = API()
    report(api, ROOT, 7, IDS, 123, 1)
    assert len(api.posts) == 1
    assert api.posts[0]["body"].startswith(f"[ci] green @{HEAD}")
    assert "Verdict-Account-Class: bot" in api.posts[0]["body"]


def test_duplicate_latest_evidence_is_suppressed_but_newer_verdict_is_not() -> None:
    api = API()
    evidence = snapshot(api, ROOT, 7, IDS)[1]
    body = comment_body(REPO, evidence, 123, 1)
    api.comments = [{"body": body, "user": {"type": "Bot"}}]
    report(api, ROOT, 7, IDS, 123, 1)
    assert not api.posts
    api.comments.append({"body": f"[ci] red @{HEAD}", "user": {"type": "Bot"}})
    report(api, ROOT, 7, IDS, 123, 1)
    assert api.posts[0]["body"].startswith(f"[ci] green @{HEAD}")
    assert MARKER in api.posts[0]["body"]


def replay_fixture(tmp_path: Path) -> tuple[API, Path, dict[str, Any]]:
    checkout = tmp_path / "reviewed"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    workflows = checkout / ".github/workflows"
    workflows.mkdir(parents=True)
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        (workflows / path.name).write_bytes(path.read_bytes())
    subprocess.run(["git", "-C", str(checkout), "add", "."], check=True)
    subprocess.run(["git", "-C", str(checkout), "-c", "user.name=CI Test", "-c", "user.email=ci@example.invalid", "commit", "-qm", "reviewed reporter"], check=True)
    sha = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    api = API()
    aggregate = api.runs[AGGREGATE][0]
    aggregate.update(event="workflow_dispatch", head_sha=sha)
    replay = {"aggregate_run_id": aggregate["id"], "reporter_sha": sha, "host": "sk-dispatch", "session": "ci-replay-4032"}
    return api, checkout, replay


def test_explicit_reviewed_replay_posts_real_manual_aggregate_evidence(tmp_path: Path) -> None:
    api, checkout, replay = replay_fixture(tmp_path)
    # Automatic reconciliation must not trust branch-dispatched aggregates.
    assert snapshot(api, checkout, 7, IDS)[1]["state"] == "running"
    report(api, checkout, 7, IDS, 123, 1, replay=replay)
    body = api.posts[0]["body"]
    assert body.startswith(f"[ci] green @{HEAD} on sk-dispatch")
    assert "Verdict-Session: ci-replay-4032" in body
    assert "Verdict-Host: sk-dispatch" in body
    assert replay["reporter_sha"] in body


@pytest.mark.parametrize("field,value", [
    ("event", "push"), ("head_sha", "f" * 40), ("workflow_id", 999),
    ("path", ".github/workflows/wrong.yml"), ("repository", {"full_name": "other/repo"}),
    ("display_title", "CI Aggregate source 999999 attempt 1"),
])
def test_replay_refuses_wrong_aggregate_identity(tmp_path: Path, field: str, value: Any) -> None:
    api, checkout, replay = replay_fixture(tmp_path)
    api.runs[AGGREGATE][0][field] = value
    with pytest.raises(ValueError, match="manual aggregate"):
        report(api, checkout, 7, IDS, 123, 1, replay=replay)
    assert not api.posts


@pytest.mark.parametrize("change", ["dirty", "wrong_revision", "new_head", "new_source_attempt"])
def test_replay_refuses_unreviewed_or_superseded_evidence(tmp_path: Path, change: str) -> None:
    api, checkout, replay = replay_fixture(tmp_path)
    if change == "dirty":
        (checkout / "unreviewed.py").write_text("unreviewed = True\n")
    elif change == "wrong_revision":
        replay["reporter_sha"] = "f" * 40
    elif change == "new_head":
        api.move_on_second_read = True
    else:
        api.runs["ci-modules.yml"][0]["run_attempt"] = 2
    with pytest.raises(ValueError):
        report(api, checkout, 7, IDS, 123, 1, replay=replay)
    assert not api.posts


@pytest.mark.parametrize("state,expected", [("failure", "red"), ("cancelled", "running")])
def test_replay_preserves_other_required_gate_results(tmp_path: Path, state: str, expected: str) -> None:
    api, checkout, replay = replay_fixture(tmp_path)
    api.runs["ci-quality.yml"][0]["conclusion"] = state
    report(api, checkout, 7, IDS, 123, 1, replay=replay)
    assert api.posts[0]["body"].startswith(f"[ci] {expected} @{HEAD}")
