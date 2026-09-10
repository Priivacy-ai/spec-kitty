"""Reconcile main-push CI into the fleet's existing P0 issue intake.

The reporter consumes metadata only. It uses the existing main-push CI gates,
not the nightly/full release acceptance suite. PROGRAM.md section 9 and planning
agents/ci.md step 6 own the red-main P0 policy; groom/controller consume the
from:ci + status:triage queue. An open incident gets subsequent observations,
including recovery, but only the fleet closes or changes its priority.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
from pathlib import Path
from typing import Any

import yaml

from scripts.ci.fleet_verdict import AGGREGATE, PR_WORKFLOWS, GitHub, automatic_aggregate, classify, comment_body

INCIDENT = "<!-- spec-kitty-main-ci-incident-v1 -->"


def main_workflows(root: Path) -> tuple[set[str], set[str]]:
    """Read unconditional and conditional main-push gates from trusted YAML."""
    required: set[str] = set()
    conditional: set[str] = set()
    for name in PR_WORKFLOWS:
        document = yaml.safe_load((root / ".github/workflows" / name).read_text(encoding="utf-8"))
        trigger = document.get("on", document.get(True, {})).get("push")
        if trigger is None:
            continue
        if set(trigger) - {"branches", "paths"}:
            raise ValueError(f"unsupported main push policy in {name}")
        if not any(fnmatch.fnmatchcase("main", pattern) for pattern in trigger.get("branches", [])):
            continue
        (conditional if trigger.get("paths") else required).add(name)
    if not {"ci-router.yml", "ci-modules.yml", "ci-quality.yml", "packs.yml", "ci-windows.yml"} <= required:
        raise ValueError("continuous main-push CI inventory changed")
    return required, conditional


def snapshot(api: GitHub, root: Path, workflow_ids: dict[str, int]) -> dict[str, Any]:
    head = api.request("git/ref/heads/main")["object"]["sha"]
    if not isinstance(head, str) or not re.fullmatch("[0-9a-f]{40}", head):
        raise ValueError("main has an invalid head")
    required, conditional = main_workflows(root)
    found = api.pages(f"actions/runs?head_sha={head}&event=push&branch=main", "workflow_runs")
    runs: dict[str, Any] = {}
    for name in sorted(required | conditional):
        matching = [
            run
            for run in found
            if run.get("workflow_id") == workflow_ids[name]
            and run.get("repository", {}).get("full_name") == api.repository
            and run.get("head_repository", {}).get("full_name") == api.repository
            and run.get("head_sha") == head
            and run.get("head_branch") == "main"
            and run.get("event") == "push"
            and run.get("path") == f".github/workflows/{name}"
            and type(run.get("id")) is int
            and run["id"] > 0
            and type(run.get("run_attempt")) is int
            and run["run_attempt"] > 0
        ]
        latest = max(matching, key=lambda run: (run["id"], run["run_attempt"]), default=None)
        if name in required or latest:
            runs[name] = latest
    modules = runs.get("ci-modules.yml")
    runs[AGGREGATE] = (
        automatic_aggregate(
            api, workflow_ids, modules, f"CI Aggregate source {modules['id']} attempt {modules['run_attempt']}", source_event="push", source_head=head
        )
        if modules
        else None
    )
    evidence = {
        name: ({key: run.get(key) for key in ("id", "run_attempt", "head_sha", "event", "status", "conclusion", "html_url")} if run else None)
        for name, run in sorted(runs.items())
    }
    return {
        "head": head,
        "state": classify(runs, set()),
        "runs": evidence,
        "scope": "continuous-main-push",
        "conditional_gates_not_observed": sorted(conditional - runs.keys()),
    }


def body(repository: str, evidence: dict[str, Any], reporter_id: int, attempt: int) -> str:
    report = comment_body(repository, evidence, reporter_id, attempt)
    return report + (
        "\nThis observes the current main head, not nightly/full-suite release acceptance. "
        "Path-filtered gates are included when a matching push run exists; absent conditional gates are listed in the evidence.\n"
        "\nRed main is P0 under PROGRAM.md section 9 and agents/ci.md step 6. "
        "The fleet should investigate the named failing gates; this report does not attribute a culprit PR or test node. "
        "A later green observation is recovery evidence for the fleet to assess, not automatic closure.\n"
    )


def report(api: GitHub, root: Path, ids: dict[str, int], reporter_id: int, attempt: int, *, dry_run: bool = False) -> None:
    evidence = snapshot(api, root, ids)
    text = body(api.repository, evidence, reporter_id, attempt)
    if dry_run:
        print(text, end="")
        return
    incidents = [
        issue
        for issue in api.pages("issues?state=open&labels=from%3Aci")
        if not issue.get("pull_request") and issue.get("user", {}).get("type") == "Bot" and INCIDENT in (issue.get("body") or "")
    ]
    if len(incidents) > 1:
        raise ValueError("multiple active main CI incidents; fleet must reconcile ownership")
    incident = incidents[0] if incidents else None
    fingerprint = "<!-- evidence: " + json.dumps(evidence, sort_keys=True) + " -->"
    if incident:
        comments = api.pages(f"issues/{incident['number']}/comments")
        latest = next(
            (comment for comment in reversed(comments) if comment.get("user", {}).get("type") == "Bot" and "<!-- evidence:" in comment.get("body", "")), incident
        )
        if fingerprint in latest.get("body", ""):
            return
    elif evidence["state"] != "red":
        print(text, end="")
        return
    if snapshot(api, root, ids) != evidence:
        raise ValueError("main head or CI attempts changed before publication; later event will reconcile")
    if incident:
        if api.request(f"issues/{incident['number']}")["state"] != "open":
            raise ValueError("main CI incident closed before publication; later event will reconcile")
        api.request(f"issues/{incident['number']}/comments", {"body": text})
    else:
        api.request(
            "issues",
            {
                "title": f"main-push CI is red at {evidence['head'][:12]}",
                "body": INCIDENT + "\n\n" + text,
                "labels": ["type:fix", "priority:P0", "from:ci", "status:triage"],
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--reporter-id", type=int, required=True)
    parser.add_argument("--attempt", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    api = GitHub(args.repository)
    definitions = api.pages("actions/workflows", "workflows")
    ids = {Path(row["path"]).name: row["id"] for row in definitions if row["path"].startswith(".github/workflows/")}
    if not (PR_WORKFLOWS | {AGGREGATE}) <= ids.keys():
        raise ValueError("required Actions workflow definition missing")
    report(api, Path(__file__).resolve().parents[2], ids, args.reporter_id, args.attempt, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
