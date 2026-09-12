"""Prepare source data for coverage without checking out or executing PR code."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any


# Ordinary Git pathspecs match descendants without consulting the checkout.
# Keep the existing critical-path policy here, not in diff-cover's filesystem glob.
CRITICAL_PATHS = (
    "src/kernel/*",
    "src/charter/*",
    "src/specify_cli/status/*",
    "src/specify_cli/lanes/branch_naming.py",
    "src/specify_cli/dashboard/handlers/*",
    "src/specify_cli/dashboard/scanner.py",
    "src/specify_cli/merge/*",
    "src/runtime/next/*",
    "src/mission_runtime/*",
)


def prepare_source(run: dict[str, Any], repository: str, run_id: int, attempt: int) -> None:
    """Validate Actions source identity, then materialize its registry and diff."""
    if (run.get("id"), run.get("run_attempt"), run.get("repository", {}).get("full_name"), run.get("path")) != (
        run_id,
        attempt,
        repository,
        ".github/workflows/ci-modules.yml",
    ):
        raise ValueError("source run identity, attempt, repository or workflow does not match")
    if run.get("status") != "completed":
        raise ValueError("source run attempt has not completed")
    head = run.get("head_sha", "")
    if not isinstance(head, str) or not re.fullmatch("[0-9a-f]{40}", head):
        raise ValueError("source head is not a full commit SHA")
    tested, base, number = head, head, None
    if run.get("event") == "pull_request":
        # pull_requests[] is a LIVE PR projection: after a push its head/base
        # change even on old run records. referenced_workflows is the immutable
        # Actions resolution of the reusable shard workflow actually executed.
        references = run.get("referenced_workflows", [])
        matches = [
            (ref.get("sha"), re.fullmatch(r"refs/pull/([1-9][0-9]*)/merge", ref.get("ref", "")))
            for ref in references
            if isinstance(ref.get("sha"), str)
            and re.fullmatch("[0-9a-f]{40}", ref["sha"])
            and ref.get("path") == f"{repository}/.github/workflows/module-tests.yml@{ref['sha']}"
        ]
        if len(matches) != 1 or matches[0][1] is None:
            raise ValueError("source run lacks one immutable PR merge workflow reference")
        tested, match = matches[0]
        assert match is not None
        number = int(match.group(1))
    elif run.get("event") not in {"push", "workflow_dispatch"}:
        raise ValueError("unsupported source event")
    subprocess.run(["git", "fetch", "--no-tags", "--quiet", "origin", tested], check=True)
    if number is not None:
        parents = subprocess.check_output(["git", "show", "-s", "--format=%P", tested], text=True).split()
        if len(parents) != 2 or parents[1] != head:
            raise ValueError("tested merge parents do not bind the source run head")
        base = parents[0]
    registry = subprocess.check_output(["git", "show", f"{tested}:.github/ci-module-registry.yml"])
    diff = subprocess.check_output(["git", "diff", "--no-ext-diff", "--no-textconv", base, tested, "--"])
    critical = subprocess.check_output(["git", "diff", "--no-ext-diff", "--no-textconv", base, tested, "--", *CRITICAL_PATHS])
    paths = subprocess.check_output(["git", "diff", "--name-only", "-z", "--diff-filter=ACMRT", base, tested, "--", *CRITICAL_PATHS]).decode("utf-8").split("\0")
    sources = {path: base64.b64encode(subprocess.check_output(["git", "show", f"{tested}:{path}"])).decode("ascii") for path in paths if path.endswith(".py")}
    out = Path("out/aggregate/source")
    out.mkdir(parents=True, exist_ok=True)
    (out / "ci-module-registry.yml").write_bytes(registry)
    (out / "diff.patch").write_bytes(diff)
    (out / "critical.diff.patch").write_bytes(critical)
    (out / "critical-sources.json").write_text(json.dumps(sources) + "\n", encoding="utf-8")
    (out / "source.json").write_text(
        json.dumps(
            {
                "repository": repository,
                "run_id": run_id,
                "run_attempt": attempt,
                "head_sha": head,
                "base_sha": base,
                "tested_sha": tested,
                "pr_number": number,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_json", type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--attempt", required=True, type=int)
    args = parser.parse_args()
    prepare_source(json.loads(args.run_json.read_text(encoding="utf-8")), args.repository, args.run_id, args.attempt)


if __name__ == "__main__":
    main()
