"""Translate trusted Actions metadata into the fleet's exact-head comment protocol.

This reporter executes no PR code and never launches a test producer. Workflow
trigger declarations remain the authority for which existing gates apply.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

PR_WORKFLOWS = frozenset(
    {
        "ci-router.yml",
        "ci-modules.yml",
        "packs.yml",
        "ci-quality.yml",
        "ci-windows.yml",
        "release-readiness.yml",
        "check-spec-kitty-events-alignment.yml",
    }
)
AGGREGATE = "ci-aggregate.yml"
MARKER = "<!-- spec-kitty-actions-verdict-v1 -->"


def applicable_workflows(root: Path, pr: dict[str, Any], paths: list[str]) -> set[str]:
    """Derive the finite existing branch/path policy from trusted workflow YAML."""
    required = set()
    seen = set()
    for path in (root / ".github/workflows").glob("*.yml"):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        triggers = doc.get("on", doc.get(True, {}))
        if not isinstance(triggers, dict) or "pull_request" not in triggers:
            continue
        seen.add(path.name)
        trigger = triggers["pull_request"] or {}
        if set(trigger) - {"types", "branches", "paths"}:
            raise ValueError(f"unsupported PR trigger policy in {path.name}")
        branches = trigger.get("branches", ["*"])
        if not any(fnmatch.fnmatchcase(pr["base"]["ref"], p) for p in branches):
            continue
        patterns = trigger.get("paths")
        if patterns and not any(fnmatch.fnmatchcase(p, pattern) for p in paths for pattern in patterns):
            continue
        required.add(path.name)
    if seen != PR_WORKFLOWS:
        raise ValueError(f"PR workflow inventory changed: {sorted(seen ^ PR_WORKFLOWS)}")
    return required


def latest_run(runs: list[dict[str, Any]], *, workflow_id: int, repository: str, head: str, number: int, name: str) -> dict[str, Any] | None:
    valid = [
        r
        for r in runs
        if r.get("workflow_id") == workflow_id
        and r.get("repository", {}).get("full_name") == repository
        and r.get("head_sha") == head
        and r.get("event") == "pull_request"
        and r.get("path") == f".github/workflows/{name}"
        and any(
            p.get("number") == number
            and p.get("head", {}).get("sha") == head
            and p.get("base", {}).get("repo", {}).get("url") == f"https://api.github.com/repos/{repository}"
            for p in r.get("pull_requests", [])
        )
    ]
    return max(valid, key=lambda r: (r["id"], r["run_attempt"]), default=None)


def classify(runs: dict[str, dict[str, Any] | None], labels: set[str]) -> str:
    """Never turn absent, cancelled, skipped or incomplete evidence into green."""
    present = [r for r in runs.values() if r]
    if any(r.get("status") == "completed" and r.get("conclusion") in {"failure", "timed_out", "startup_failure", "action_required"} for r in present):
        return "red"
    if labels & {"pr:deferred", "pr:skip-ci"}:
        return "running"
    if not runs or len(present) != len(runs):
        return "running"
    return "green" if all(r.get("status") == "completed" and r.get("conclusion") == "success" for r in present) else "running"


class GitHub:
    """Small authenticated API boundary; errors never include credentials."""

    def __init__(self, repository: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("invalid repository")
        self.repository = repository

    def request(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repository}/{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def pages(self, path: str, field: str | None = None) -> list[dict[str, Any]]:
        rows = []
        for page in range(1, 101):
            separator = "&" if "?" in path else "?"
            result = self.request(f"{path}{separator}per_page=100&page={page}")
            batch = result[field] if field else result
            rows.extend(batch)
            if len(batch) < 100:
                return rows
        raise ValueError("API result exceeded bounded pagination; refusing incomplete evidence")


def snapshot(api: GitHub, root: Path, number: int, workflow_ids: dict[str, int]) -> tuple[dict[str, Any], dict[str, Any]]:
    pr = api.request(f"pulls/{number}")
    head = pr["head"]["sha"]
    if pr["state"] != "open" or not re.fullmatch("[0-9a-f]{40}", head):
        raise ValueError("PR is closed or has an invalid head")
    files = api.pages(f"pulls/{number}/files")
    if len({p["filename"] for p in files}) != pr["changed_files"]:
        raise ValueError("PR file list is incomplete; required gates cannot be determined")
    paths = [p["filename"] for p in files] + [p["previous_filename"] for p in files if "previous_filename" in p]
    required = applicable_workflows(root, pr, paths)
    runs: dict[str, Any] = {}
    found = api.pages(f"actions/runs?head_sha={head}&event=pull_request", "workflow_runs")
    for name in sorted(required):
        runs[name] = latest_run(found, workflow_id=workflow_ids[name], repository=api.repository, head=head, number=number, name=name)
    modules = runs.get("ci-modules.yml")
    runs[AGGREGATE] = None
    if modules:
        title = f"CI Aggregate source {modules['id']} attempt {modules['run_attempt']}"
        created = modules.get("created_at", "")
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", created):
            raise ValueError("source run creation time missing; cannot bound aggregate lookup")
        query = urllib.parse.urlencode({"event": "workflow_run", "created": ">=" + created})
        aggregates = api.pages(f"actions/workflows/{workflow_ids[AGGREGATE]}/runs?{query}", "workflow_runs")
        matching = [
            r
            for r in aggregates
            if r.get("display_title") == title
            and r.get("workflow_id") == workflow_ids[AGGREGATE]
            and r.get("path") == f".github/workflows/{AGGREGATE}"
            and r.get("event") == "workflow_run"
            and r.get("repository", {}).get("full_name") == api.repository
        ]
        runs[AGGREGATE] = max(matching, key=lambda r: (r["id"], r["run_attempt"]), default=None)
    labels = {label["name"] for label in pr["labels"]}
    state = classify(runs, labels)
    evidence = {name: ({k: run.get(k) for k in ("id", "run_attempt", "status", "conclusion", "html_url")} if run else None) for name, run in sorted(runs.items())}
    return pr, {"head": head, "state": state, "runs": evidence, "labels": sorted(labels)}


def comment_body(repository: str, evidence: dict[str, Any], reporter_id: int, attempt: int) -> str:
    state, head = evidence["state"], evidence["head"]
    lines = [f"[ci] {state} @{head} on github-actions", "", MARKER, "Existing Actions gates for this exact PR head; no additional test run.", ""]
    if state == "running":
        lines.append("Evidence is pending, incomplete, cancelled, or intentionally deferred; this is not a code failure verdict.")
    for name, run in evidence["runs"].items():
        lines.append(
            f"- {name}: {run['status']}/{run['conclusion']} ({run['html_url']}, attempt {run['run_attempt']})" if run else f"- {name}: awaiting matching run"
        )
    lines.extend(
        [
            "",
            "<!-- evidence: " + json.dumps(evidence, sort_keys=True) + " -->",
            "",
            "Verdict-Role: ci",
            "Verdict-Account-Class: bot",
            f"Verdict-Session: github-actions-{reporter_id}",
            f"Verdict-Repo: {repository}",
            f"Verdict-Head: {head}",
            "Verdict-Host: github-actions",
            f"Verdict-Attempt: {attempt}",
            "Verdict-Contract-Version: 1",
        ]
    )
    return "\n".join(lines) + "\n"


def report(api: GitHub, root: Path, number: int, workflow_ids: dict[str, int], reporter_id: int, attempt: int) -> None:
    pr, evidence = snapshot(api, root, number, workflow_ids)
    comments = api.pages(f"issues/{number}/comments")
    # Only identical latest evidence is suppressed. Append changes: editing an older
    # comment would preserve created_at and leave a newer stale terminal dominant.
    fingerprint = "<!-- evidence: " + json.dumps(evidence, sort_keys=True) + " -->"
    latest = next(
        (c for c in reversed(comments) if re.match(r"\[ci\] (?:green|red|running|infra-error|no suite) @" + evidence["head"] + r"\b", c.get("body", ""))), None
    )
    if (
        latest
        and latest.get("user", {}).get("type") == "Bot"
        and MARKER in latest.get("body", "")
        and (fingerprint in latest["body"] or (evidence["state"] == "running" and latest["body"].startswith("[ci] running @")))
    ):
        return
    final_pr, final_evidence = snapshot(api, root, number, workflow_ids)
    if final_evidence != evidence or final_pr["head"]["sha"] != pr["head"]["sha"]:
        raise ValueError("PR head or CI attempts changed before publication; later event will reconcile")
    api.request(f"issues/{number}/comments", {"body": comment_body(api.repository, evidence, reporter_id, attempt)})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path)
    parser.add_argument("--pr", type=int)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--reporter-id", type=int, required=True)
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    api = GitHub(args.repository)
    definitions = api.pages("actions/workflows", "workflows")
    ids = {Path(w["path"]).name: w["id"] for w in definitions if w["path"].startswith(".github/workflows/")}
    if not (PR_WORKFLOWS | {AGGREGATE}) <= ids.keys():
        raise ValueError("required Actions workflow definition missing")
    if args.pr:
        report(api, Path(__file__).resolve().parents[2], args.pr, ids, args.reporter_id, args.attempt)
        return
    event = json.loads(args.event.read_text(encoding="utf-8"))
    trigger = event["workflow_run"]
    name = Path(trigger["path"]).name
    if name not in PR_WORKFLOWS | {AGGREGATE} or trigger["workflow_id"] != ids[name]:
        raise ValueError("unrecognized triggering workflow")
    source = api.request(f"actions/runs/{trigger['id']}")
    if name == AGGREGATE:
        match = re.fullmatch(r"CI Aggregate source ([1-9][0-9]*) attempt ([1-9][0-9]*)", source["display_title"])
        if not match or source.get("event") != "workflow_run":
            return
        source = api.request(f"actions/runs/{match.group(1)}")
        if source.get("workflow_id") != ids["ci-modules.yml"]:
            raise ValueError("aggregate source is not CI Modules")
    if source.get("event") != "pull_request" or source.get("repository", {}).get("full_name") != api.repository:
        return
    references = source.get("pull_requests", [])
    if not references:
        # Fork workflow_run payloads can omit PR references. Discover recipients
        # only: latest_run still refuses to use unassociated runs as green proof.
        references = [
            pr
            for pr in api.pages(f"commits/{source['head_sha']}/pulls")
            if pr.get("head", {}).get("sha") == source["head_sha"] and pr.get("base", {}).get("repo", {}).get("full_name") == api.repository
        ]
    numbers = sorted({pr["number"] for pr in references})
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write("prs=" + json.dumps(numbers) + "\n")


if __name__ == "__main__":
    main()
