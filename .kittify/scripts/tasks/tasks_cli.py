#!/usr/bin/env python3
"""CLI utilities for managing Spec Kitty work-package prompts and acceptance."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from task_helpers import (  # noqa: E402
    LANES,
    TaskCliError,
    WorkPackage,
    append_activity_log,
    activity_entries,
    build_document,
    ensure_lane,
    find_repo_root,
    get_lane_from_frontmatter,
    is_legacy_format,
    normalize_note,
    now_utc,
    run_git,
    set_scalar,
    split_frontmatter,
    locate_work_package,
)
from acceptance_support import (  # noqa: E402
    AcceptanceError,
    AcceptanceSummary,
    ArtifactEncodingError,
    choose_mode,
    collect_feature_summary,
    detect_feature_slug,
    normalize_feature_encoding,
    perform_acceptance,
)


def stage_update(
    repo_root: Path,
    wp: WorkPackage,
    target_lane: str,
    agent: str,
    shell_pid: str,
    note: str,
    timestamp: str,
    dry_run: bool = False,
) -> Path:
    """Update work package lane in frontmatter (no file movement).

    The frontmatter-only lane system keeps all WP files in a flat tasks/ directory.
    Lane changes update the `lane:` field in frontmatter without moving the file.
    """
    if dry_run:
        return wp.path

    wp.frontmatter = set_scalar(wp.frontmatter, "lane", target_lane)
    wp.frontmatter = set_scalar(wp.frontmatter, "agent", agent)
    if shell_pid:
        wp.frontmatter = set_scalar(wp.frontmatter, "shell_pid", shell_pid)
    log_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – lane={target_lane} – {note}"
    new_body = append_activity_log(wp.body, log_entry)

    new_content = build_document(wp.frontmatter, new_body, wp.padding)
    wp.path.write_text(new_content, encoding="utf-8")

    run_git(["add", str(wp.path.relative_to(repo_root))], cwd=repo_root, check=True)

    return wp.path


def _collect_summary_with_encoding(
    repo_root: Path,
    feature: str,
    *,
    strict_metadata: bool,
    normalize_encoding: bool,
) -> AcceptanceSummary:
    try:
        return collect_feature_summary(
            repo_root,
            feature,
            strict_metadata=strict_metadata,
        )
    except ArtifactEncodingError:
        if not normalize_encoding:
            raise
        cleaned = normalize_feature_encoding(repo_root, feature)
        if cleaned:
            print("[spec-kitty] Normalized artifact encoding for:", file=sys.stderr)
            for path in cleaned:
                try:
                    rel = path.relative_to(repo_root)
                except ValueError:
                    rel = path
                print(f"  - {rel}", file=sys.stderr)
        else:
            print(
                "[spec-kitty] normalize-encoding enabled but no files required updates.",
                file=sys.stderr,
            )
        return collect_feature_summary(
            repo_root,
            feature,
            strict_metadata=strict_metadata,
        )


def _handle_encoding_failure(exc: ArtifactEncodingError, attempted_fix: bool) -> None:
    print(f"Error: {exc}", file=sys.stderr)
    if attempted_fix:
        print(
            "Encoding issues persist after normalization attempt. Please correct the file manually.",
            file=sys.stderr,
        )
    else:
        print(
            "Re-run with --normalize-encoding to attempt automatic repair.",
            file=sys.stderr,
        )
    sys.exit(1)


_legacy_warning_shown = False


def _check_legacy_format(feature: str, repo_root: Path) -> bool:
    """Check for legacy format and warn once. Returns True if legacy format detected."""
    global _legacy_warning_shown
    feature_path = repo_root / "kitty-specs" / feature
    if is_legacy_format(feature_path):
        if not _legacy_warning_shown:
            print("\n" + "=" * 60, file=sys.stderr)
            print("Legacy directory-based lanes detected.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Your project uses the old lane structure (tasks/planned/, tasks/doing/, etc.).", file=sys.stderr)
            print("Run `spec-kitty upgrade` to migrate to frontmatter-only lanes.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Benefits of upgrading:", file=sys.stderr)
            print("  - No file conflicts during lane changes", file=sys.stderr)
            print("  - Direct editing of lane: field supported", file=sys.stderr)
            print("  - Better multi-agent compatibility", file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)
            _legacy_warning_shown = True
        return True
    return False


def update_command(args: argparse.Namespace) -> None:
    """Update a work package's lane in frontmatter (no file movement)."""
    # Validate lane value first
    try:
        validated_lane = ensure_lane(args.lane)
    except TaskCliError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    repo_root = find_repo_root()
    feature = args.feature

    # Check for legacy format and error out
    if _check_legacy_format(feature, repo_root):
        print("Error: Cannot use 'update' command on legacy format.", file=sys.stderr)
        print("Run 'spec-kitty upgrade' first, then retry.", file=sys.stderr)
        sys.exit(1)

    wp = locate_work_package(repo_root, feature, args.work_package)

    if wp.current_lane == validated_lane:
        raise TaskCliError(f"Work package already in lane '{validated_lane}'.")

    timestamp = args.timestamp or now_utc()
    agent = args.agent or wp.agent or "system"
    shell_pid = args.shell_pid or wp.shell_pid or ""
    note = normalize_note(args.note, validated_lane)

    # Stage the update (frontmatter only, no file movement)
    updated_path = stage_update(
        repo_root=repo_root,
        wp=wp,
        target_lane=validated_lane,
        agent=agent,
        shell_pid=shell_pid,
        note=note,
        timestamp=timestamp,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"[dry-run] Would update {wp.work_package_id or wp.path.name} to lane '{validated_lane}'")
        print(f"[dry-run] File stays at: {updated_path.relative_to(repo_root)}")
        return

    print(f"✅ Updated {wp.work_package_id or wp.path.name} → {validated_lane}")
    print(f"   {wp.path.relative_to(repo_root)}")
    print(
        f"   Logged: - {timestamp} – {agent} – shell_pid={shell_pid} – lane={validated_lane} – {note}"
    )


def history_command(args: argparse.Namespace) -> None:
    repo_root = find_repo_root()
    wp = locate_work_package(repo_root, args.feature, args.work_package)
    agent = args.agent or wp.agent or "system"
    shell_pid = args.shell_pid or wp.shell_pid or ""
    lane = ensure_lane(args.lane or wp.current_lane)
    timestamp = args.timestamp or now_utc()
    note = normalize_note(args.note, lane)

    if lane != wp.current_lane:
        wp.frontmatter = set_scalar(wp.frontmatter, "lane", lane)

    log_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – lane={lane} – {note}"
    updated_body = append_activity_log(wp.body, log_entry)

    if args.update_shell and shell_pid:
        wp.frontmatter = set_scalar(wp.frontmatter, "shell_pid", shell_pid)
    if args.assignee is not None:
        wp.frontmatter = set_scalar(wp.frontmatter, "assignee", args.assignee)
    if args.agent:
        wp.frontmatter = set_scalar(wp.frontmatter, "agent", agent)

    if args.dry_run:
        print(f"[dry-run] Would append activity entry: {log_entry}")
        return

    new_content = build_document(wp.frontmatter, updated_body, wp.padding)
    wp.path.write_text(new_content, encoding="utf-8")
    run_git(["add", str(wp.path.relative_to(repo_root))], cwd=repo_root, check=True)

    print(f"📝 Appended activity for {wp.work_package_id or wp.path.name}")
    print(f"   {log_entry}")


def list_command(args: argparse.Namespace) -> None:
    repo_root = find_repo_root()
    feature_path = repo_root / "kitty-specs" / args.feature
    feature_dir = feature_path / "tasks"
    if not feature_dir.exists():
        raise TaskCliError(f"Feature '{args.feature}' has no tasks directory at {feature_dir}.")

    # Check for legacy format and warn
    use_legacy = is_legacy_format(feature_path)
    if use_legacy:
        _check_legacy_format(args.feature, repo_root)

    rows = []

    if use_legacy:
        # Legacy format: scan lane subdirectories
        for lane in LANES:
            lane_dir = feature_dir / lane
            if not lane_dir.exists():
                continue
            for path in sorted(lane_dir.rglob("*.md")):
                text = path.read_text(encoding="utf-8-sig")
                front, body, padding = split_frontmatter(text)
                wp = WorkPackage(
                    feature=args.feature,
                    path=path,
                    current_lane=lane,
                    relative_subpath=path.relative_to(lane_dir),
                    frontmatter=front,
                    body=body,
                    padding=padding,
                )
                wp_id = wp.work_package_id or path.stem
                title = (wp.title or "").strip('"')
                assignee = (wp.assignee or "").strip()
                agent = (wp.agent or "").strip()
                rows.append(
                    {
                        "lane": lane,
                        "id": wp_id,
                        "title": title,
                        "assignee": assignee,
                        "agent": agent,
                        "path": str(path.relative_to(repo_root)),
                    }
                )
    else:
        # New format: scan flat tasks/ directory and group by frontmatter lane
        for path in sorted(feature_dir.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            text = path.read_text(encoding="utf-8-sig")
            front, body, padding = split_frontmatter(text)
            lane = get_lane_from_frontmatter(path, warn_on_missing=False)
            wp = WorkPackage(
                feature=args.feature,
                path=path,
                current_lane=lane,
                relative_subpath=path.relative_to(feature_dir),
                frontmatter=front,
                body=body,
                padding=padding,
            )
            wp_id = wp.work_package_id or path.stem
            title = (wp.title or "").strip('"')
            assignee = (wp.assignee or "").strip()
            agent = (wp.agent or "").strip()
            rows.append(
                {
                    "lane": lane,
                    "id": wp_id,
                    "title": title,
                    "assignee": assignee,
                    "agent": agent,
                    "path": str(path.relative_to(repo_root)),
                }
            )

    if not rows:
        print(f"No work packages found for feature '{args.feature}'.")
        return

    width_id = max(len(row["id"]) for row in rows)
    width_lane = max(len(row["lane"]) for row in rows)
    width_agent = max(len(row["agent"]) for row in rows) if any(row["agent"] for row in rows) else 5
    width_assignee = (
        max(len(row["assignee"]) for row in rows) if any(row["assignee"] for row in rows) else 8
    )

    header = (
        f"{'Lane'.ljust(width_lane)}  "
        f"{'WP'.ljust(width_id)}  "
        f"{'Agent'.ljust(width_agent)}  "
        f"{'Assignee'.ljust(width_assignee)}  "
        "Title"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['lane'].ljust(width_lane)}  "
            f"{row['id'].ljust(width_id)}  "
            f"{row['agent'].ljust(width_agent)}  "
            f"{row['assignee'].ljust(width_assignee)}  "
            f"{row['title']} ({row['path']})"
        )


def rollback_command(args: argparse.Namespace) -> None:
    repo_root = find_repo_root()
    wp = locate_work_package(repo_root, args.feature, args.work_package)
    entries = activity_entries(wp.body)
    if len(entries) < 2:
        raise TaskCliError("Not enough activity entries to determine the previous lane.")

    previous_lane = ensure_lane(entries[-2]["lane"])
    note = args.note or f"Rolled back to {previous_lane}"
    args_for_update = argparse.Namespace(
        feature=args.feature,
        work_package=args.work_package,
        lane=previous_lane,
        note=note,
        agent=args.agent or entries[-1]["agent"],
        assignee=args.assignee,
        shell_pid=args.shell_pid or entries[-1].get("shell_pid", ""),
        timestamp=args.timestamp or now_utc(),
        dry_run=args.dry_run,
        force=args.force,
    )
    update_command(args_for_update)


def _resolve_feature(repo_root: Path, requested: Optional[str]) -> str:
    if requested:
        return requested
    return detect_feature_slug(repo_root)


def _summary_to_text(summary: AcceptanceSummary) -> List[str]:
    lines: List[str] = []
    lines.append(f"Feature: {summary.feature}")
    lines.append(f"Branch: {summary.branch or 'N/A'}")
    lines.append(f"Worktree: {summary.worktree_root}")
    lines.append("")
    lines.append("Work packages by lane:")
    for lane in LANES:
        items = summary.lanes.get(lane, [])
        lines.append(f"  {lane} ({len(items)}): {', '.join(items) if items else '-'}")
    lines.append("")
    outstanding = summary.outstanding()
    if outstanding:
        lines.append("Outstanding items:")
        for key, values in outstanding.items():
            lines.append(f"  {key}:")
            for value in values:
                lines.append(f"    - {value}")
    else:
        lines.append("All acceptance checks passed.")
    if summary.optional_missing:
        lines.append("")
        lines.append("Optional artifacts missing: " + ", ".join(summary.optional_missing))
    return lines


def status_command(args: argparse.Namespace) -> None:
    repo_root = find_repo_root()
    feature = _resolve_feature(repo_root, args.feature)
    try:
        summary = _collect_summary_with_encoding(
            repo_root,
            feature,
            strict_metadata=not args.lenient,
            normalize_encoding=args.normalize_encoding,
        )
    except ArtifactEncodingError as exc:
        _handle_encoding_failure(exc, args.normalize_encoding)
        return
    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
        return
    for line in _summary_to_text(summary):
        print(line)


def verify_command(args: argparse.Namespace) -> None:
    repo_root = find_repo_root()
    feature = _resolve_feature(repo_root, args.feature)
    try:
        summary = _collect_summary_with_encoding(
            repo_root,
            feature,
            strict_metadata=not args.lenient,
            normalize_encoding=args.normalize_encoding,
        )
    except ArtifactEncodingError as exc:
        _handle_encoding_failure(exc, args.normalize_encoding)
        return
    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
        sys.exit(0 if summary.ok else 1)
    lines = _summary_to_text(summary)
    for line in lines:
        print(line)
    sys.exit(0 if summary.ok else 1)


def accept_command(args: argparse.Namespace) -> None:
    repo_root = find_repo_root()
    feature = _resolve_feature(repo_root, args.feature)
    try:
        summary = _collect_summary_with_encoding(
            repo_root,
            feature,
            strict_metadata=not args.lenient,
            normalize_encoding=args.normalize_encoding,
        )
    except ArtifactEncodingError as exc:
        _handle_encoding_failure(exc, args.normalize_encoding)
        return

    if args.mode == "checklist":
        if args.json:
            print(json.dumps(summary.to_dict(), indent=2))
        else:
            for line in _summary_to_text(summary):
                print(line)
        sys.exit(0 if summary.ok else 1)

    mode = choose_mode(args.mode, repo_root)
    tests = list(args.test or [])

    if not summary.ok and not args.allow_fail:
        for line in _summary_to_text(summary):
            print(line)
        print("\n❌ Outstanding items detected. Fix them or re-run with --allow-fail for checklist mode.")
        sys.exit(1)

    try:
        result = perform_acceptance(
            summary,
            mode=mode,
            actor=args.actor,
            tests=tests,
            auto_commit=not args.no_commit,
        )
    except AcceptanceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    print(f"✅ Feature '{feature}' accepted at {result.accepted_at} by {result.accepted_by}")
    if result.accept_commit:
        print(f"   Acceptance commit: {result.accept_commit}")
    if result.parent_commit:
        print(f"   Parent commit: {result.parent_commit}")
    if result.notes:
        print("\nNotes:")
        for note in result.notes:
            print(f"  {note}")
    print("\nNext steps:")
    for instruction in result.instructions:
        print(f"  - {instruction}")
    if result.cleanup_instructions:
        print("\nCleanup:")
        for instruction in result.cleanup_instructions:
            print(f"  - {instruction}")


def _merge_actor(repo_root: Path) -> str:
    configured = run_git(["config", "user.name"], cwd=repo_root, check=False)
    if configured.returncode == 0:
        name = configured.stdout.strip()
        if name:
            return name
    return os.getenv("GIT_AUTHOR_NAME") or os.getenv("USER") or os.getenv("USERNAME") or "system"


def _prepare_merge_metadata(
    repo_root: Path,
    feature: str,
    target: str,
    strategy: str,
    pushed: bool,
) -> Optional[Path]:
    feature_dir = repo_root / "kitty-specs" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_path = feature_dir / "meta.json"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    merged_by = _merge_actor(repo_root)

    entry: Dict[str, Any] = {
        "merged_at": timestamp,
        "merged_by": merged_by,
        "target": target,
        "strategy": strategy,
        "pushed": pushed,
        "merge_commit": None,
    }

    meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            meta = {}

    history = meta.get("merge_history", [])
    if not isinstance(history, list):
        history = []
    history.append(entry)
    if len(history) > 20:
        history = history[-20:]
    meta["merge_history"] = history

    meta["merged_at"] = timestamp
    meta["merged_by"] = merged_by
    meta["merged_into"] = target
    meta["merged_strategy"] = strategy
    meta["merged_push"] = pushed

    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta_path


def _finalize_merge_metadata(meta_path: Optional[Path], merge_commit: str) -> None:
    if not meta_path or not meta_path.exists():
        return

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        meta = {}

    history = meta.get("merge_history")
    if isinstance(history, list) and history:
        if isinstance(history[-1], dict):
            history[-1]["merge_commit"] = merge_commit
    meta["merged_commit"] = merge_commit

    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def merge_command(args: argparse.Namespace) -> None:
    # Capture the original working directory (may be a worktree) before
    # find_repo_root() resolves it back to the main repository root.
    # Branch detection must use the worktree cwd so that git returns the
    # worktree's checked-out branch rather than the main repo's branch.
    worktree_cwd = Path.cwd()
    repo_root = find_repo_root()
    feature = _resolve_feature(repo_root, args.feature)

    # Resolve target branch dynamically if not specified
    if args.target is None:
        from specify_cli.core.git_ops import resolve_primary_branch
        args.target = resolve_primary_branch(repo_root)

    current_branch = run_git([
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
    ], cwd=worktree_cwd, check=True).stdout.strip()

    if current_branch == args.target:
        raise TaskCliError(
            f"Already on target branch '{args.target}'. Switch to the feature branch before merging."
        )

    if current_branch != feature:
        raise TaskCliError(
            f"Current branch '{current_branch}' does not match detected feature '{feature}'."
            " Run this command from the feature worktree or specify --feature explicitly."
        )

    # Use the original worktree cwd for git-common-dir detection so that
    # we correctly identify whether we are inside a worktree.  find_repo_root()
    # already resolved to the main repo, so running git-common-dir there
    # would always report "not a worktree".
    try:
        git_common = run_git(["rev-parse", "--git-common-dir"], cwd=worktree_cwd, check=True).stdout.strip()
        primary_repo_root = Path(git_common).resolve().parent
    except TaskCliError:
        primary_repo_root = Path(repo_root).resolve()

    worktree_root = worktree_cwd.resolve()
    primary_repo_root = primary_repo_root.resolve()
    in_worktree = worktree_root != primary_repo_root

    def ensure_clean(cwd: Path) -> None:
        status = run_git(["status", "--porcelain"], cwd=cwd, check=True).stdout.strip()
        if status:
            raise TaskCliError(
                f"Working directory at {cwd} has uncommitted changes. Commit or stash before merging."
            )

    ensure_clean(worktree_root)
    if in_worktree:
        ensure_clean(primary_repo_root)

    if args.dry_run:
        steps = ["Planned actions:"]
        steps.append(f"  - Checkout {args.target} in {primary_repo_root}")
        steps.append("  - Fetch remote (if configured)")
        if args.strategy == "squash":
            steps.append(f"  - Merge {feature} with --squash and commit")
        elif args.strategy == "rebase":
            steps.append(
                f"  - Rebase {feature} onto {args.target} manually (command exits before merge)"
            )
        else:
            steps.append(f"  - Merge {feature} with --no-ff")
        if args.push:
            steps.append(f"  - Push {args.target} to origin (if upstream configured)")
        if in_worktree and args.remove_worktree:
            steps.append(f"  - Remove worktree at {worktree_root}")
        if args.delete_branch:
            steps.append(f"  - Delete branch {feature}")
        print("\n".join(steps))
        return

    def git(cmd: List[str], *, cwd: Path = primary_repo_root, check: bool = True) -> subprocess.CompletedProcess:
        return run_git(cmd, cwd=cwd, check=check)

    git(["checkout", args.target])

    remotes = run_git(["remote"], cwd=primary_repo_root, check=False)
    has_remote = remotes.returncode == 0 and bool(remotes.stdout.strip())
    if has_remote:
        git(["fetch"], check=False)
        pull = git(["pull", "--ff-only"], check=False)
        if pull.returncode != 0:
            raise TaskCliError(
                "Failed to fast-forward target branch. Resolve upstream changes and retry."
            )

    if args.strategy == "rebase":
        raise TaskCliError(
            "Rebase strategy requires manual steps. Run `git checkout {feature}` followed by `git rebase {args.target}`."
        )

    meta_path: Optional[Path] = None
    meta_rel: Optional[str] = None

    if args.strategy == "squash":
        merge_proc = git(["merge", "--squash", feature], check=False)
        if merge_proc.returncode != 0:
            raise TaskCliError(
                "Merge failed. Resolve conflicts manually, commit, then rerun with --keep-worktree --keep-branch."
            )
        meta_path = _prepare_merge_metadata(primary_repo_root, feature, args.target, args.strategy, args.push)
        if meta_path:
            meta_rel = str(meta_path.relative_to(primary_repo_root))
            git(["add", meta_rel])
        git(["commit", "-m", f"Merge feature {feature}"])
    else:
        merge_proc = git(["merge", "--no-ff", "--no-commit", feature], check=False)
        if merge_proc.returncode != 0:
            raise TaskCliError(
                "Merge failed. Resolve conflicts manually, commit, then rerun with --keep-worktree --keep-branch."
            )
        meta_path = _prepare_merge_metadata(primary_repo_root, feature, args.target, args.strategy, args.push)
        if meta_path:
            meta_rel = str(meta_path.relative_to(primary_repo_root))
            git(["add", meta_rel])
        git(["commit", "-m", f"Merge feature {feature}"])

    if meta_path:
        merge_commit = git(["rev-parse", "HEAD"]).stdout.strip()
        _finalize_merge_metadata(meta_path, merge_commit)
        meta_rel = meta_rel or str(meta_path.relative_to(primary_repo_root))
        git(["add", meta_rel])
        git(["commit", "--amend", "--no-edit"])

    if args.push and has_remote:
        push_result = git(["push", "origin", args.target], check=False)
        if push_result.returncode != 0:
            raise TaskCliError(f"Merge succeeded but push failed. Run `git push origin {args.target}` manually.")
    elif args.push and not has_remote:
        print("[spec-kitty] Skipping push: no remote configured.", file=sys.stderr)

    if in_worktree and args.remove_worktree:
        if worktree_root.exists():
            git(["worktree", "remove", str(worktree_root), "--force"])

    if args.delete_branch:
        delete = git(["branch", "-d", feature], check=False)
        if delete.returncode != 0:
            git(["branch", "-D", feature])

    print(f"Merge complete: {feature} -> {args.target}")
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spec Kitty task utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update = subparsers.add_parser("update", help="Update a work package's lane in frontmatter")
    update.add_argument("feature", help="Feature directory slug (e.g., 008-awesome-feature)")
    update.add_argument("work_package", help="Work package identifier (e.g., WP03)")
    update.add_argument("lane", help=f"Target lane ({', '.join(LANES)})")
    update.add_argument("--note", help="Activity note to record with the update")
    update.add_argument("--agent", help="Agent identifier to record (defaults to existing agent/system)")
    update.add_argument("--assignee", help="Friendly assignee name to store in frontmatter")
    update.add_argument("--shell-pid", help="Shell PID to capture in frontmatter/history")
    update.add_argument("--timestamp", help="Override UTC timestamp (YYYY-MM-DDTHH:mm:ssZ)")
    update.add_argument("--dry-run", action="store_true", help="Show what would happen without touching files or git")
    update.add_argument("--force", action="store_true", help="Ignore other staged work-package files")

    history = subparsers.add_parser("history", help="Append a history entry without changing lanes")
    history.add_argument("feature", help="Feature directory slug")
    history.add_argument("work_package", help="Work package identifier (e.g., WP03)")
    history.add_argument("--note", required=True, help="History note to append")
    history.add_argument("--lane", help="Lane to record (defaults to current lane)")
    history.add_argument("--agent", help="Agent identifier (defaults to frontmatter/system)")
    history.add_argument("--assignee", help="Assignee value to set/override")
    history.add_argument("--shell-pid", help="Shell PID to record")
    history.add_argument("--update-shell", action="store_true", help="Persist the provided shell PID to frontmatter")
    history.add_argument("--timestamp", help="Override UTC timestamp")
    history.add_argument("--dry-run", action="store_true", help="Show the log entry without updating files")

    list_parser = subparsers.add_parser("list", help="List work packages by lane")
    list_parser.add_argument("feature", help="Feature directory slug")

    rollback = subparsers.add_parser("rollback", help="Return a work package to its prior lane")
    rollback.add_argument("feature", help="Feature directory slug")
    rollback.add_argument("work_package", help="Work package identifier (e.g., WP03)")
    rollback.add_argument("--note", help="History note to record (default: Rolled back to <lane>)")
    rollback.add_argument("--agent", help="Agent identifier to record for the rollback entry")
    rollback.add_argument("--assignee", help="Assignee override to apply")
    rollback.add_argument("--shell-pid", help="Shell PID to capture")
    rollback.add_argument("--timestamp", help="Override UTC timestamp")
    rollback.add_argument("--dry-run", action="store_true", help="Report planned rollback without modifying files")
    rollback.add_argument("--force", action="store_true", help="Ignore other staged work-package files")

    status = subparsers.add_parser("status", help="Summarize work packages for a feature")
    status.add_argument("--feature", help="Feature directory slug (auto-detect by default)")
    status.add_argument("--json", action="store_true", help="Emit JSON summary")
    status.add_argument("--lenient", action="store_true", help="Skip strict metadata validation")
    status.add_argument(
        "--normalize-encoding",
        action="store_true",
        help="Automatically repair non-UTF-8 artifact files",
    )

    verify = subparsers.add_parser("verify", help="Run acceptance checks without committing")
    verify.add_argument("--feature", help="Feature directory slug (auto-detect by default)")
    verify.add_argument("--json", action="store_true", help="Emit JSON summary")
    verify.add_argument("--lenient", action="store_true", help="Skip strict metadata validation")
    verify.add_argument(
        "--normalize-encoding",
        action="store_true",
        help="Automatically repair non-UTF-8 artifact files",
    )

    accept = subparsers.add_parser("accept", help="Perform feature acceptance workflow")
    accept.add_argument("--feature", help="Feature directory slug (auto-detect by default)")
    accept.add_argument("--mode", choices=["auto", "pr", "local", "checklist"], default="auto")
    accept.add_argument("--actor", help="Override acceptance author (defaults to system/user)")
    accept.add_argument("--test", action="append", help="Record validation command executed (repeatable)")
    accept.add_argument("--json", action="store_true", help="Emit JSON result")
    accept.add_argument("--lenient", action="store_true", help="Skip strict metadata validation")
    accept.add_argument("--no-commit", action="store_true", help="Skip auto-commit (report only)")
    accept.add_argument("--allow-fail", action="store_true", help="Allow outstanding issues (for manual workflows)")
    accept.add_argument(
        "--normalize-encoding",
        action="store_true",
        help="Automatically repair non-UTF-8 artifact files before acceptance",
    )

    merge = subparsers.add_parser("merge", help="Merge a feature branch into the target branch")
    merge.add_argument("--feature", help="Feature directory slug (auto-detect by default)")
    merge.add_argument("--strategy", choices=["merge", "squash", "rebase"], default="merge")
    merge.add_argument("--target", default=None, help="Target branch to merge into (auto-detected)")
    merge.add_argument("--push", action="store_true", help="Push to origin after merging")
    merge.add_argument("--delete-branch", dest="delete_branch", action="store_true", default=True)
    merge.add_argument("--keep-branch", dest="delete_branch", action="store_false")
    merge.add_argument("--remove-worktree", dest="remove_worktree", action="store_true", default=True)
    merge.add_argument("--keep-worktree", dest="remove_worktree", action="store_false")
    merge.add_argument("--dry-run", action="store_true", help="Show actions without executing")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "update":
            update_command(args)
        elif args.command == "history":
            history_command(args)
        elif args.command == "list":
            list_command(args)
        elif args.command == "rollback":
            rollback_command(args)
        elif args.command == "status":
            status_command(args)
        elif args.command == "verify":
            verify_command(args)
        elif args.command == "merge":
            merge_command(args)
        elif args.command == "accept":
            accept_command(args)
        else:
            parser.error(f"Unknown command {args.command}")
            return 1
    except TaskCliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
