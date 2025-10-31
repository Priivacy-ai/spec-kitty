#!/usr/bin/env python3
"""CLI utilities for managing Spec Kitty work-package prompts and acceptance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

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
    detect_conflicting_wp_status,
    ensure_lane,
    find_repo_root,
    git_status_lines,
    normalize_note,
    now_utc,
    run_git,
    set_scalar,
    split_frontmatter,
    locate_work_package,
)
from acceptance_support import (  # noqa: E402
    AcceptanceError,
    AcceptanceResult,
    AcceptanceSummary,
    choose_mode,
    collect_feature_summary,
    detect_feature_slug,
    perform_acceptance,
)


def stage_move(
    repo_root: Path,
    wp: WorkPackage,
    target_lane: str,
    agent: str,
    shell_pid: str,
    note: str,
    timestamp: str,
    dry_run: bool = False,
) -> Path:
    target_dir = repo_root / "kitty-specs" / wp.feature / "tasks" / target_lane
    new_path = (target_dir / wp.relative_subpath).resolve()

    if dry_run:
        return new_path

    target_dir.mkdir(parents=True, exist_ok=True)

    wp.frontmatter = set_scalar(wp.frontmatter, "lane", target_lane)
    wp.frontmatter = set_scalar(wp.frontmatter, "agent", agent)
    if shell_pid:
        wp.frontmatter = set_scalar(wp.frontmatter, "shell_pid", shell_pid)
    log_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – lane={target_lane} – {note}"
    new_body = append_activity_log(wp.body, log_entry)

    new_content = build_document(wp.frontmatter, new_body, wp.padding)
    new_path.write_text(new_content, encoding="utf-8")

    run_git(["add", str(new_path.relative_to(repo_root))], cwd=repo_root, check=True)
    if wp.path.resolve() != new_path.resolve():
        run_git(
            ["rm", "--quiet", str(wp.path.relative_to(repo_root))],
            cwd=repo_root,
            check=True,
        )

    return new_path


def move_command(args: argparse.Namespace) -> None:
    repo_root = find_repo_root()
    feature = args.feature
    wp = locate_work_package(repo_root, feature, args.work_package)

    if wp.current_lane == args.lane:
        raise TaskCliError(f"Work package already in lane '{args.lane}'.")

    timestamp = args.timestamp or now_utc()
    agent = args.agent or wp.agent or "system"
    shell_pid = args.shell_pid or wp.shell_pid or ""
    note = normalize_note(args.note, args.lane)

    status_lines = git_status_lines(repo_root)
    new_path = (
        repo_root
        / "kitty-specs"
        / feature
        / "tasks"
        / args.lane
        / wp.relative_subpath
    )
    conflicts = detect_conflicting_wp_status(
        status_lines,
        feature,
        wp.path.relative_to(repo_root),
        new_path.relative_to(repo_root),
    )
    if conflicts and not args.force:
        conflict_display = "\n".join(conflicts)
        raise TaskCliError(
            "Other work-package files are staged or modified:\n"
            f"{conflict_display}\n\nClear or commit these changes, or re-run with --force."
        )

    new_file_path = stage_move(
        repo_root=repo_root,
        wp=wp,
        target_lane=args.lane,
        agent=agent,
        shell_pid=shell_pid,
        note=note,
        timestamp=timestamp,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"[dry-run] Would move {wp.work_package_id or wp.path.name} to lane '{args.lane}'")
        print(f"[dry-run] New path: {new_file_path.relative_to(repo_root)}")
        return

    print(f"✅ Moved {wp.work_package_id or wp.path.name} → {args.lane}")
    print(f"   {wp.path.relative_to(repo_root)} → {new_file_path.relative_to(repo_root)}")
    print(
        f"   Logged: - {timestamp} – {agent} – shell_pid={shell_pid} – lane={args.lane} – {note}"
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
    feature_dir = repo_root / "kitty-specs" / args.feature / "tasks"
    if not feature_dir.exists():
        raise TaskCliError(f"Feature '{args.feature}' has no tasks directory at {feature_dir}.")

    rows = []
    for lane in LANES:
        lane_dir = feature_dir / lane
        if not lane_dir.exists():
            continue
        for path in sorted(lane_dir.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
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
    args_for_move = argparse.Namespace(
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
    move_command(args_for_move)


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
    summary = collect_feature_summary(
        repo_root,
        feature,
        strict_metadata=not args.lenient,
    )
    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
        return
    for line in _summary_to_text(summary):
        print(line)


def verify_command(args: argparse.Namespace) -> None:
    repo_root = find_repo_root()
    feature = _resolve_feature(repo_root, args.feature)
    summary = collect_feature_summary(
        repo_root,
        feature,
        strict_metadata=not args.lenient,
    )
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
    summary = collect_feature_summary(
        repo_root,
        feature,
        strict_metadata=not args.lenient,
    )

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spec Kitty task utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    move = subparsers.add_parser("move", help="Move a work package to the specified lane")
    move.add_argument("feature", help="Feature directory slug (e.g., 008-awesome-feature)")
    move.add_argument("work_package", help="Work package identifier (e.g., WP03)")
    move.add_argument("lane", help=f"Target lane ({', '.join(LANES)})")
    move.add_argument("--note", help="Activity note to record with the move")
    move.add_argument("--agent", help="Agent identifier to record (defaults to existing agent/system)")
    move.add_argument("--assignee", help="Friendly assignee name to store in frontmatter")
    move.add_argument("--shell-pid", help="Shell PID to capture in frontmatter/history")
    move.add_argument("--timestamp", help="Override UTC timestamp (YYYY-MM-DDTHH:mm:ssZ)")
    move.add_argument("--dry-run", action="store_true", help="Show what would happen without touching files or git")
    move.add_argument("--force", action="store_true", help="Ignore other staged work-package files")

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

    verify = subparsers.add_parser("verify", help="Run acceptance checks without committing")
    verify.add_argument("--feature", help="Feature directory slug (auto-detect by default)")
    verify.add_argument("--json", action="store_true", help="Emit JSON summary")
    verify.add_argument("--lenient", action="store_true", help="Skip strict metadata validation")

    accept = subparsers.add_parser("accept", help="Perform feature acceptance workflow")
    accept.add_argument("--feature", help="Feature directory slug (auto-detect by default)")
    accept.add_argument("--mode", choices=["auto", "pr", "local", "checklist"], default="auto")
    accept.add_argument("--actor", help="Override acceptance author (defaults to system/user)")
    accept.add_argument("--test", action="append", help="Record validation command executed (repeatable)")
    accept.add_argument("--json", action="store_true", help="Emit JSON result")
    accept.add_argument("--lenient", action="store_true", help="Skip strict metadata validation")
    accept.add_argument("--no-commit", action="store_true", help="Skip auto-commit (report only)")
    accept.add_argument("--allow-fail", action="store_true", help="Allow outstanding issues (for manual workflows)")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "move":
            move_command(args)
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
