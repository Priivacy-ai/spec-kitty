#!/usr/bin/env python3
"""Sync All Contributors entries from GitHub repo activity."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_DENY_REGEX = r"(?:^|[-_])(claude|codex)(?:$|[-_])"
DEFAULT_EXACT_DENYLIST = {
    "actions-user",
    "github-actions",
    "github-actions[bot]",
    "dependabot",
    "dependabot[bot]",
    "copilot-swe-agent",
    "copilot-swe-agent[bot]",
    # Regnology contributor: attributed to the Regnology org account, not the individual
    "regnology-stijn",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill and sync .all-contributorsrc from GitHub contributors and "
            "merged PR authors."
        )
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="GitHub repository in owner/name form. Defaults to GITHUB_REPOSITORY.",
    )
    parser.add_argument(
        "--config",
        default=".all-contributorsrc",
        help="Path to the All Contributors config file.",
    )
    parser.add_argument(
        "--contribution",
        default="code",
        help="Contribution type to assign to discovered users.",
    )
    parser.add_argument(
        "--deny-regex",
        default=DEFAULT_DENY_REGEX,
        help="Case-insensitive regex for usernames to exclude.",
    )
    parser.add_argument(
        "--pr-limit",
        type=int,
        default=500,
        help="Maximum merged PRs to inspect via gh pr list.",
    )
    parser.add_argument(
        "--skip-pr-authors",
        action="store_true",
        help="Only use the contributors API, not merged PR authors.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report planned additions without mutating files.",
    )
    args = parser.parse_args(argv)
    if not args.repo:
        parser.error("--repo is required when GITHUB_REPOSITORY is not set")
    return args


def run_json(cmd: list[str]) -> object:
    completed = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return json.loads(completed.stdout)


def run_text(cmd: list[str]) -> str:
    completed = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


def require_tools() -> None:
    missing = [tool for tool in ("gh", "npx") if shutil.which(tool) is None]
    if missing:
        raise SystemExit(f"Missing required tools: {', '.join(missing)}")


def is_excluded(login: str, deny_pattern: re.Pattern[str]) -> bool:
    lowered = login.lower()
    if lowered in DEFAULT_EXACT_DENYLIST:
        return True
    if lowered.endswith("[bot]") or lowered.endswith("-bot"):
        return True
    if "[bot]" in lowered:
        return True
    return bool(deny_pattern.search(login))


def load_contributors_api(repo: str, deny_pattern: re.Pattern[str]) -> set[str]:
    rows = run_text(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/{repo}/contributors?per_page=100",
            "--jq",
            '.[] | select(.type != "Bot") | .login',
        ]
    )
    result: set[str] = set()
    for raw in rows.splitlines():
        login = raw.strip()
        if login and not is_excluded(login, deny_pattern):
            result.add(login)
    return result


def load_merged_pr_authors(
    repo: str, pr_limit: int, deny_pattern: re.Pattern[str]
) -> set[str]:
    payload = run_json(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "merged",
            "--limit",
            str(pr_limit),
            "--json",
            "author",
        ]
    )
    result: set[str] = set()
    for item in payload:
        author = item.get("author") or {}
        login = author.get("login")
        if login and not is_excluded(login, deny_pattern):
            result.add(login)
    return result


def load_existing_logins(config_path: Path) -> set[str]:
    payload = json.loads(config_path.read_text())
    return {entry["login"] for entry in payload.get("contributors", []) if entry.get("login")}


def add_contributor(config_path: Path, login: str, contribution: str) -> None:
    env = os.environ.copy()
    token = env.get("PRIVATE_TOKEN") or env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if token:
        env["PRIVATE_TOKEN"] = token
    subprocess.run(
        [
            "npx",
            "--no-install",
            "all-contributors-cli",
            "add",
            login,
            contribution,
            "--config",
            str(config_path),
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )


def generate_readme(config_path: Path) -> None:
    env = os.environ.copy()
    token = env.get("PRIVATE_TOKEN") or env.get("GH_TOKEN") or env.get("GITHUB_TOKEN")
    if token:
        env["PRIVATE_TOKEN"] = token
    subprocess.run(
        [
            "npx",
            "--no-install",
            "all-contributors-cli",
            "generate",
            "--config",
            str(config_path),
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        env=env,
    )


def sorted_logins(logins: Iterable[str]) -> list[str]:
    return sorted(logins, key=lambda value: value.lower())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_tools()

    config_path = Path(args.config)
    deny_pattern = re.compile(args.deny_regex, re.IGNORECASE)

    contributor_logins = load_contributors_api(args.repo, deny_pattern)
    pr_author_logins: set[str] = set()
    if not args.skip_pr_authors:
        pr_author_logins = load_merged_pr_authors(args.repo, args.pr_limit, deny_pattern)

    discovered_logins = contributor_logins | pr_author_logins
    existing_logins = load_existing_logins(config_path)
    missing_logins = sorted_logins(discovered_logins - existing_logins)

    print(f"repo={args.repo}")
    print(f"contributors_api={len(contributor_logins)}")
    print(f"merged_pr_authors={len(pr_author_logins)}")
    print(f"existing={len(existing_logins)}")
    print(f"missing={len(missing_logins)}")
    if missing_logins:
        print("to_add=" + ",".join(missing_logins))

    if args.dry_run or not missing_logins:
        return 0

    for login in missing_logins:
        print(f"adding={login}")
        add_contributor(config_path, login, args.contribution)

    generate_readme(config_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
