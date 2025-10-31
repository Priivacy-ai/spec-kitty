from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = REPO_ROOT / "scripts" / "tasks"

if str(TASKS_DIR) not in sys.path:
    sys.path.insert(0, str(TASKS_DIR))


def run(cmd: list[str], *, cwd: Path, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    result = subprocess.run(cmd, cwd=cwd, env=process_env, text=True, capture_output=True)
    result.check_returncode()
    return result


def run_python_script(script: Path, args: list[str], *, cwd: Path, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    command = [sys.executable, str(script), *args]
    return subprocess.run(command, cwd=cwd, env=process_env, text=True, capture_output=True)


def run_tasks_cli(args: list[str], *, cwd: Path, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess:
    return run_python_script(TASKS_DIR / "tasks_cli.py", args, cwd=cwd, env=env)


def write_wp(
    repo_root: Path,
    feature: str,
    lane: str,
    wp_id: str,
    *,
    agent: str = "system",
    assignee: str = "Owner",
    shell_pid: str = "1234",
    note: str = "Created",
    timestamp: str = "2025-01-01T00:00:00Z",
) -> Path:
    from task_helpers import append_activity_log, build_document, set_scalar, split_frontmatter

    lane_dir = repo_root / "kitty-specs" / feature / "tasks" / lane
    lane_dir.mkdir(parents=True, exist_ok=True)
    path = lane_dir / f"{wp_id}.md"

    frontmatter = "\n".join(
        [
            f'work_package_id: "{wp_id}"',
            f'lane: "{lane}"',
            f'agent: "{agent}"',
            f'assignee: "{assignee}"',
            f'shell_pid: "{shell_pid}"',
        ]
    )
    document = build_document(frontmatter, "", "\n")
    path.write_text(document, encoding="utf-8")

    front, body, padding = split_frontmatter(path.read_text(encoding="utf-8"))
    updated_body = append_activity_log(
        body,
        f"- {timestamp} – {agent} – shell_pid={shell_pid} – lane={lane} – {note}",
    )
    updated_front = set_scalar(set_scalar(set_scalar(set_scalar(front, "lane", lane), "agent", agent), "assignee", assignee), "shell_pid", shell_pid)
    path.write_text(build_document(updated_front, updated_body, padding), encoding="utf-8")
    return path
