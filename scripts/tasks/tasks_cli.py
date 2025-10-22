#!/usr/bin/env python3
"""Helper utilities for managing Spec Kitty work-package prompts.

This script is invoked by shell wrappers to move work packages between Kanban lanes,
append history entries, list current assignments, and roll back a mistaken transition.

It intentionally avoids `git mv` usage so the staging area only reflects the new file
location and history entry, reducing merge conflicts when AI agents shuffle prompts.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Dict


LANES = ("planned", "doing", "for_review", "done")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TaskCliError(RuntimeError):
    """Raised when operations cannot be completed safely."""


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Walk upward until a Git or .specify root is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / ".specify").exists():
            return candidate
    raise TaskCliError("Unable to locate repository root (missing .git or .specify).")


def run_git(args: List[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command inside the repository."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=check,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise TaskCliError("git is not available on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        if check:
            message = exc.stderr.strip() or exc.stdout.strip() or "Unknown git error"
            raise TaskCliError(message)
        return exc


def ensure_lane(value: str) -> str:
    lane = value.strip().lower()
    if lane not in LANES:
        raise TaskCliError(f"Invalid lane '{value}'. Expected one of {', '.join(LANES)}.")
    return lane


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def git_status_lines(repo_root: Path) -> List[str]:
    result = run_git(["status", "--porcelain"], cwd=repo_root, check=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def normalize_note(note: Optional[str], target_lane: str) -> str:
    default = f"Moved to {target_lane}"
    cleaned = (note or default).strip()
    return cleaned or default


def detect_conflicting_wp_status(
    status_lines: List[str], feature: str, old_path: Path, new_path: Path
) -> List[str]:
    """Return staged work-package entries unrelated to the requested move."""
    prefix = f"specs/{feature}/tasks/"
    allowed = {
        str(old_path).lstrip("./"),
        str(new_path).lstrip("./"),
    }
    conflicts = []
    for line in status_lines:
        path = line[3:] if len(line) > 3 else ""
        if not path.startswith(prefix):
            continue
        clean = path.strip()
        if clean not in allowed:
            conflicts.append(line)
    return conflicts


def match_frontmatter_line(frontmatter: str, key: str) -> Optional[re.Match]:
    pattern = re.compile(
        rf"^({re.escape(key)}:\s*)(\".*?\"|'.*?'|[^#\n]*)(.*)$",
        flags=re.MULTILINE,
    )
    return pattern.search(frontmatter)


def extract_scalar(frontmatter: str, key: str) -> Optional[str]:
    match = match_frontmatter_line(frontmatter, key)
    if not match:
        return None
    raw_value = match.group(2).strip()
    if raw_value.startswith('"') and raw_value.endswith('"'):
        return raw_value[1:-1]
    if raw_value.startswith("'") and raw_value.endswith("'"):
        return raw_value[1:-1]
    return raw_value.strip() or None


def set_scalar(frontmatter: str, key: str, value: str) -> str:
    """Replace or insert a scalar value while preserving trailing comments."""
    match = match_frontmatter_line(frontmatter, key)
    replacement_line = f'{key}: "{value}"'
    if match:
        prefix = match.group(1)
        comment = match.group(3)
        comment_suffix = f"{comment}" if comment else ""
        return (
            frontmatter[: match.start()]
            + f'{prefix}"{value}"{comment_suffix}'
            + frontmatter[match.end() :]
        )

    insertion = f'{replacement_line}\n'
    history_match = re.search(r"^\s*history:\s*$", frontmatter, flags=re.MULTILINE)
    if history_match:
        idx = history_match.start()
        return frontmatter[:idx] + insertion + frontmatter[idx:]

    if frontmatter and not frontmatter.endswith("\n"):
        frontmatter += "\n"
    return frontmatter + insertion


def split_frontmatter(text: str) -> Tuple[str, str, str]:
    """Return (frontmatter, body, padding) where padding preserves spacing after frontmatter."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return "", normalized, ""

    closing_idx = normalized.find("\n---", 4)
    if closing_idx == -1:
        return "", normalized, ""

    front = normalized[4:closing_idx]
    tail = normalized[closing_idx + 4 :]
    padding = ""
    while tail.startswith("\n"):
        padding += "\n"
        tail = tail[1:]
    return front, tail, padding


def build_document(frontmatter: str, body: str, padding: str) -> str:
    frontmatter = frontmatter.rstrip("\n")
    doc = f"---\n{frontmatter}\n---"
    if padding or body:
        doc += padding or "\n"
    doc += body
    if not doc.endswith("\n"):
        doc += "\n"
    return doc


def append_activity_log(body: str, entry: str) -> str:
    header = "## Activity Log"
    if header not in body:
        block = f"{header}\n\n{entry}\n"
        if body and not body.endswith("\n\n"):
            return body.rstrip() + "\n\n" + block
        return body + "\n" + block if body else block

    # Locate the Activity Log section and append before the next heading
    pattern = re.compile(r"(## Activity Log.*?)(?=\n## |\Z)", flags=re.DOTALL)
    match = pattern.search(body)
    if not match:
        return body + ("\n" if not body.endswith("\n") else "") + entry + "\n"

    section = match.group(1).rstrip()
    if not section.endswith("\n"):
        section += "\n"
    section += f"{entry}\n"
    return body[: match.start(1)] + section + body[match.end(1) :]


def activity_entries(body: str) -> List[Dict[str, str]]:
    pattern = re.compile(
        r"^\s*-\s*"
        r"(?P<timestamp>[0-9T:-]+Z)\s*[–-]\s*"
        r"(?P<agent>[^–-]+?)\s*[–-]\s*"
        r"(?:shell_pid=(?P<shell>[^–-]*?)\s*[–-]\s*)?"
        r"lane=(?P<lane>[a-z_]+)\s*[–-]\s*"
        r"(?P<note>.*)$",
        flags=re.MULTILINE,
    )
    entries: List[Dict[str, str]] = []
    for match in pattern.finditer(body):
        entries.append(
            {
                "timestamp": match.group("timestamp").strip(),
                "agent": match.group("agent").strip(),
                "lane": match.group("lane").strip(),
                "note": match.group("note").strip(),
                "shell_pid": (match.group("shell") or "").strip(),
            }
        )
    return entries


@dataclass
class WorkPackage:
    feature: str
    path: Path
    current_lane: str
    relative_subpath: Path
    frontmatter: str
    body: str
    padding: str

    @property
    def work_package_id(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "work_package_id")

    @property
    def title(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "title")

    @property
    def assignee(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "assignee")

    @property
    def agent(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "agent")

    @property
    def shell_pid(self) -> Optional[str]:
        return extract_scalar(self.frontmatter, "shell_pid")


def locate_work_package(repo_root: Path, feature: str, wp_id: str) -> WorkPackage:
    tasks_root = repo_root / "specs" / feature / "tasks"
    if not tasks_root.exists():
        raise TaskCliError(f"Feature '{feature}' has no tasks directory at {tasks_root}.")

    candidates = []
    for lane_dir in tasks_root.iterdir():
        if not lane_dir.is_dir():
            continue
        lane = lane_dir.name
        lane_path = tasks_root / lane
        for path in lane_path.rglob("*.md"):
            if path.name.startswith(wp_id):
                candidates.append((lane, path, lane_path))

    if not candidates:
        raise TaskCliError(f"Work package '{wp_id}' not found under specs/{feature}/tasks.")
    if len(candidates) > 1:
        joined = "\n".join(str(item[1].relative_to(repo_root)) for item in candidates)
        raise TaskCliError(
            f"Multiple files matched '{wp_id}'. Refine the ID or clean duplicates:\n{joined}"
        )

    lane, path, lane_path = candidates[0]
    text = path.read_text(encoding="utf-8")
    front, body, padding = split_frontmatter(text)
    relative = path.relative_to(lane_path)
    return WorkPackage(
        feature=feature,
        path=path,
        current_lane=lane,
        relative_subpath=relative,
        frontmatter=front,
        body=body,
        padding=padding,
    )


def stage_move(
    repo_root: Path,
    wp: WorkPackage,
    new_lane: str,
    new_frontmatter: str,
    new_body: str,
    dry_run: bool,
) -> Path:
    target_dir = (
        repo_root
        / "specs"
        / wp.feature
        / "tasks"
        / new_lane
    )
    new_path = (target_dir / wp.relative_subpath).resolve()

    if dry_run:
        return new_path

    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_content = build_document(new_frontmatter, new_body, wp.padding)
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
    target_lane = ensure_lane(args.lane)
    wp = locate_work_package(repo_root, args.feature, args.work_package)

    if wp.current_lane == target_lane:
        raise TaskCliError(f"Work package already in lane '{target_lane}'.")

    note = normalize_note(args.note, target_lane)
    agent = args.agent or wp.agent or "system"
    shell_pid = args.shell_pid or wp.shell_pid or ""
    if args.shell_pid:
        wp.frontmatter = set_scalar(wp.frontmatter, "shell_pid", args.shell_pid)
    elif not wp.shell_pid:
        # ensure the key exists for consistency
        wp.frontmatter = set_scalar(wp.frontmatter, "shell_pid", shell_pid)

    wp.frontmatter = set_scalar(wp.frontmatter, "lane", target_lane)
    wp.frontmatter = set_scalar(wp.frontmatter, "agent", agent)
    if args.assignee is not None:
        wp.frontmatter = set_scalar(wp.frontmatter, "assignee", args.assignee)

    timestamp = args.timestamp or now_utc()
    log_entry = f"- {timestamp} – {agent} – shell_pid={shell_pid} – lane={target_lane} – {note}"
    updated_body = append_activity_log(wp.body, log_entry)

    new_path = (
        repo_root
        / "specs"
        / wp.feature
        / "tasks"
        / target_lane
        / wp.relative_subpath
    )

    status_lines = git_status_lines(repo_root)
    conflicts = detect_conflicting_wp_status(status_lines, wp.feature, wp.path.relative_to(repo_root), new_path.relative_to(repo_root))
    if conflicts and not args.force:
        conflict_display = "\n".join(conflicts)
        raise TaskCliError(
            "Other work-package files are staged or modified:\n"
            f"{conflict_display}\n\nClear or commit these changes, or re-run with --force."
        )

    new_file_path = stage_move(
        repo_root=repo_root,
        wp=wp,
        new_lane=target_lane,
        new_frontmatter=wp.frontmatter,
        new_body=updated_body,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"[dry-run] Would move {wp.work_package_id or wp.path.name} to lane '{target_lane}'")
        print(f"[dry-run] New path: {new_file_path.relative_to(repo_root)}")
        print(f"[dry-run] Activity log entry: {log_entry}")
        return

    print(f"✅ Moved {wp.work_package_id or wp.path.name} → {target_lane}")
    print(f"   {wp.path.relative_to(repo_root)} → {new_file_path.relative_to(repo_root)}")
    print(f"   Logged: {log_entry}")


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
    feature_dir = repo_root / "specs" / args.feature / "tasks"
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
    width_assignee = max(len(row["assignee"]) for row in rows) if any(row["assignee"] for row in rows) else 8

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spec Kitty task lane utilities")
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
        else:
            parser.error(f"Unknown command {args.command}")
            return 1
    except TaskCliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
