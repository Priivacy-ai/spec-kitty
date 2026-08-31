#!/usr/bin/env python3
"""Report convergence dispositions for commits in the upstream catch-up range.

The map is deliberately cluster-based. Each cluster carries the census
classification, its normalized disposition, the exact upstream commits it
covers, and a link to the evidence comment. A commit in the current range that
is absent from every cluster is reported as ``PENDING``; after the configured
age threshold it is also marked for triage.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from kernel.clock import datetime, now_utc, parse_iso, timedelta
from pathlib import Path

ALLOWED_DISPOSITIONS = frozenset({"PORT", "SUPERSEDED", "FORBIDDEN", "PENDING"})
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class CensusStatusError(RuntimeError):
    """Raised when the map or Git range cannot be read safely."""


@dataclass(frozen=True)
class Cluster:
    id: str
    disposition: str
    commits: tuple[str, ...]


@dataclass(frozen=True)
class CensusMap:
    base_commit: str
    remote: str
    remote_branch: str
    clusters: tuple[Cluster, ...]


@dataclass(frozen=True)
class UpstreamCommit:
    sha: str
    timestamp: datetime
    subject: str


def _parse_cluster(
    raw_cluster: Mapping[str, object],
    seen_ids: set[str],
    seen_commits: set[str],
) -> Cluster:
    cluster_id = raw_cluster.get("id")
    disposition = raw_cluster.get("disposition")
    commits = raw_cluster.get("commits")
    if not isinstance(cluster_id, str) or not cluster_id:
        raise CensusStatusError("each map cluster needs a nonempty id")
    if not isinstance(disposition, str) or disposition not in ALLOWED_DISPOSITIONS:
        raise CensusStatusError(f"cluster {cluster_id} has invalid disposition {disposition!r}")
    if not isinstance(commits, list) or not all(isinstance(commit, str) for commit in commits):
        raise CensusStatusError(f"cluster {cluster_id} commits must be a list of SHAs")
    if cluster_id in seen_ids:
        raise CensusStatusError(f"duplicate cluster id: {cluster_id}")
    for commit in commits:
        if not _COMMIT_SHA.fullmatch(commit):
            raise CensusStatusError(f"cluster {cluster_id} has invalid commit SHA {commit!r}")
        if commit in seen_commits:
            raise CensusStatusError(f"commit {commit} appears in more than one cluster")
    seen_ids.add(cluster_id)
    seen_commits.update(commits)
    return Cluster(cluster_id, disposition, tuple(commits))


def load_map(path: Path) -> CensusMap:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CensusStatusError(f"cannot read map {path}: {error}") from error

    if not isinstance(document, Mapping):
        raise CensusStatusError("map must be a JSON object")
    if document.get("schema_version") != 1:
        raise CensusStatusError("map schema_version must be 1")

    base_commit = document.get("base_commit")
    remote = document.get("remote")
    remote_branch = document.get("remote_branch")
    if not isinstance(base_commit, str) or not _COMMIT_SHA.fullmatch(base_commit):
        raise CensusStatusError("map base_commit must be a full 40-character SHA")
    if not isinstance(remote, str) or not remote:
        raise CensusStatusError("map remote must be a nonempty string")
    if not isinstance(remote_branch, str) or not remote_branch:
        raise CensusStatusError("map remote_branch must be a nonempty string")

    raw_clusters = document.get("clusters")
    if not isinstance(raw_clusters, list):
        raise CensusStatusError("map clusters must be a list")

    clusters: list[Cluster] = []
    seen_ids: set[str] = set()
    seen_commits: set[str] = set()
    for raw_cluster in raw_clusters:
        if not isinstance(raw_cluster, Mapping):
            raise CensusStatusError("each map cluster must be an object")
        clusters.append(_parse_cluster(raw_cluster, seen_ids, seen_commits))

    return CensusMap(base_commit, remote, remote_branch, tuple(clusters))


def commit_lookup(census_map: CensusMap) -> dict[str, Cluster]:
    return {commit: cluster for cluster in census_map.clusters for commit in cluster.commits}


def _run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown Git error"
        raise CensusStatusError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout


def read_commits(repo: Path, base_commit: str, remote_ref: str) -> list[UpstreamCommit]:
    ref = _run_git(repo, "rev-parse", "--verify", f"{remote_ref}^{{commit}}").strip()
    base = _run_git(repo, "rev-parse", "--verify", f"{base_commit}^{{commit}}").strip()
    ancestor = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", base, ref],
        check=False,
    )
    if ancestor.returncode != 0:
        raise CensusStatusError(f"base commit {base} is not an ancestor of {remote_ref}")

    output = _run_git(
        repo,
        "log",
        "--format=%H%x09%cI%x09%s",
        f"{base}..{ref}",
    )
    commits: list[UpstreamCommit] = []
    for line in output.splitlines():
        if not line:
            continue
        sha, timestamp_text, subject = line.split("\t", maxsplit=2)
        try:
            timestamp = parse_iso(timestamp_text)
        except ValueError as error:
            raise CensusStatusError(f"commit {sha} has invalid timestamp {timestamp_text!r}") from error
        commits.append(UpstreamCommit(sha, timestamp, subject))
    return commits


def status_lines(
    commits: Sequence[UpstreamCommit],
    lookup: Mapping[str, Cluster],
    *,
    pending_only: bool,
    max_age_days: float,
    now: datetime,
) -> list[str]:
    counts = dict.fromkeys(sorted(ALLOWED_DISPOSITIONS), 0)
    pending_older = 0
    output: list[str] = []
    threshold = timedelta(days=max_age_days)

    for commit in commits:
        cluster = lookup.get(commit.sha)
        disposition = cluster.disposition if cluster is not None else "PENDING"
        counts[disposition] += 1
        if disposition != "PENDING":
            if not pending_only:
                output.append(f"{disposition} {commit.sha} {cluster.id}: {commit.subject}")
            continue

        is_older = now - commit.timestamp > threshold
        if is_older:
            pending_older += 1
        marker = " [triage: older than threshold]" if is_older else ""
        if pending_only:
            output.append(f"PENDING {commit.sha} {commit.subject}{marker}")
        else:
            output.append(f"PENDING {commit.sha} unmapped: {commit.subject}{marker}")

    summary = (
        f"checked={len(commits)} "
        + " ".join(f"{disposition}={counts[disposition]}" for disposition in sorted(ALLOWED_DISPOSITIONS))
        + f" pending-older-than-{max_age_days:g}-day={pending_older}"
    )
    return output + [summary]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."), help="Git repository to inspect")
    parser.add_argument("--map", type=Path, default=Path(".kittify/convergence-map.json"), help="Convergence map")
    parser.add_argument("--remote", help="Override the map's fetch-only remote name")
    parser.add_argument("--remote-branch", help="Override the map's remote branch")
    parser.add_argument("--base", help="Override the map's base commit")
    parser.add_argument("--pending-only", action="store_true", help="Print only unmapped commits")
    parser.add_argument(
        "--max-age-days",
        type=float,
        default=1.0,
        help="Age at which a PENDING commit is marked for triage (default: 1)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.max_age_days <= 0:
        print("census_status: error: --max-age-days must be positive", file=sys.stderr)
        return 2

    try:
        census_map = load_map(args.map)
        remote = args.remote or census_map.remote
        remote_branch = args.remote_branch or census_map.remote_branch
        base_commit = args.base or census_map.base_commit
        commits = read_commits(args.repo, base_commit, f"{remote}/{remote_branch}")
        lines = status_lines(
            commits,
            commit_lookup(census_map),
            pending_only=args.pending_only,
            max_age_days=args.max_age_days,
            now=now_utc(),
        )
    except CensusStatusError as error:
        print(f"census_status: error: {error}", file=sys.stderr)
        return 2

    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
