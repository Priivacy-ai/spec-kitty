"""Real CLI hard-parent-death evidence for pre-review lane integrity.

The test kills only the CLI parent with ``SIGKILL``.  Any validation process
cleanup below is bounded fixture teardown, not a product guarantee; #2762
continues to track orphan cleanup after uncatchable parent death.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

import pytest

from specify_cli.status.store import read_events
from tests.review import test_pre_review_gate_integration as helpers


pytestmark = [
    pytest.mark.integration,
    pytest.mark.git_repo,
    pytest.mark.skipif(os.name == "nt", reason="SIGKILL is a POSIX contract"),
]


def _wait_for_gate_pid(path: Path, parent: subprocess.Popen[str]) -> int:
    expires = time.monotonic() + 10.0
    while time.monotonic() < expires:
        if path.exists() and path.stat().st_size:
            return int(path.read_text(encoding="utf-8"))
        if parent.poll() is not None:
            stdout, stderr = parent.communicate()
            raise AssertionError(f"CLI exited before candidate-head readiness: {stdout=} {stderr=}")
        time.sleep(0.01)
    raise AssertionError("candidate-head validation never published readiness")


def _independent_authority_read(feature_dir: Path, wp_path: Path) -> dict[str, object]:
    script = """
import hashlib
import json
import sys
from pathlib import Path
from specify_cli.status.reducer import materialize
from specify_cli.status.store import read_events

feature_dir = Path(sys.argv[1])
wp_path = Path(sys.argv[2])
events = read_events(feature_dir)
snapshot = materialize(feature_dir)
print(json.dumps({
    "event_count": len(events),
    "event_ids": [event.event_id for event in events],
    "lane": snapshot.work_packages["WP01"]["lane"],
    "wp_sha256": hashlib.sha256(wp_path.read_bytes()).hexdigest(),
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(feature_dir), str(wp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return cast(dict[str, object], json.loads(completed.stdout))


def test_sigkill_of_cli_parent_preserves_lane_and_event_authority(tmp_path: Path) -> None:
    repo = helpers._build_base_repo(tmp_path)
    ready_path = tmp_path / "candidate-head-ready.txt"
    helpers._write_file(
        repo,
        "test_gate_block.py",
        "import os\n"
        "import time\n\n"
        "def test_hold_real_gate():\n"
        "    path = os.environ['GATE_READY_PATH']\n"
        "    with open(path, 'w', encoding='utf-8') as ready:\n"
        "        ready.write(str(os.getpid()))\n"
        "        ready.flush()\n"
        "        os.fsync(ready.fileno())\n"
        "    time.sleep(60)\n",
    )
    helpers._git_commit_all(repo, "add synchronized candidate-head target")
    feature_dir, wp_path = helpers._build_wp_file(
        tmp_path,
        helpers._MISSION,
        "WP01",
        extra_frontmatter="pre_review_test_scope: test_gate_block.py\n",
    )
    helpers._seed_wp_event(feature_dir, "WP01", "in_progress")
    events_before = read_events(feature_dir)
    wp_before = wp_path.read_bytes()

    command_script = f"""
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner
from specify_cli.cli.commands.agent.tasks import app
from specify_cli.cli.commands.agent import tasks_move_task
from tests.mocked_env import setup_mocked_env
from tests.review import test_pre_review_gate_integration as helpers

root = Path({str(tmp_path)!r})
repo = Path({str(repo)!r})
feature_dir = root / "kitty-specs" / helpers._MISSION
ports, _router = helpers._fake_ports(feature_dir)
with (
    setup_mocked_env(
        root,
        mission_slug=helpers._MISSION,
        target_branch="main",
        workspace_resolution=helpers._fixture_workspace(repo),
        extra_patches={{
            "_validate_ready_for_review": (True, []),
            "_check_unchecked_subtasks": [],
        }},
    ),
    patch.object(tasks_move_task, "_default_move_task_ports", return_value=ports),
):
    result = CliRunner().invoke(
        app,
        [
            "move-task", "WP01", "--to", "for_review",
            "--mission", helpers._MISSION, "--no-auto-commit", "--json",
        ],
    )
raise SystemExit(result.exit_code)
"""
    env = dict(os.environ)
    env["GATE_READY_PATH"] = str(ready_path)
    parent = subprocess.Popen(
        [sys.executable, "-c", command_script],
        cwd=Path.cwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    gate_pid: int | None = None
    gate_pgid: int | None = None
    try:
        gate_pid = _wait_for_gate_pid(ready_path, parent)
        gate_pgid = os.getpgid(gate_pid)

        # Product assertion: kill the CLI parent PID only, never its group.
        os.kill(parent.pid, signal.SIGKILL)
        parent.wait(timeout=5)

        # Product assertion: inspect durable authority from a separate process
        # while the orphaned candidate-head fixture is still alive.
        observed = _independent_authority_read(feature_dir, wp_path)
        assert observed == {
            "event_count": len(events_before),
            "event_ids": [event.event_id for event in events_before],
            "lane": "in_progress",
            # File-integrity check, not canonical charter content hashing.
            "wp_sha256": hashlib.sha256(wp_before).hexdigest(),  # noqa: TID251
        }
    finally:
        # Teardown only.  This is deliberately not an orphan-cleanup claim.
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=5)
        if gate_pgid is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(gate_pgid, signal.SIGKILL)
