"""Run a persisted WP04 live-authority fault campaign and write its receipt."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time

from defusedxml import ElementTree as ET


HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "wp04-replay-spec.json"
PLUGIN_PATH = HERE / "wp04_fault_plugin.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 - evidence integrity hash


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    spec = json.loads(SPEC_PATH.read_text())
    if args.campaign not in spec["campaigns"]:
        parser.error(f"unknown campaign {args.campaign!r}")
    entries = spec["campaigns"][args.campaign]
    nodeids = [entry["nodeid"] for entry in entries]
    if len(nodeids) != len(set(nodeids)):
        raise SystemExit("duplicate selected nodeid in replay spec")
    for entry in entries:
        for key in ("nodeid", "kind", "authority", "fault", "contract"):
            if not entry.get(key):
                raise SystemExit(f"incomplete replay entry {entry!r}: missing {key}")
    if args.verify_only:
        print(json.dumps({"campaign": args.campaign, "entries": len(entries), "valid": True}, sort_keys=True))
        return 0

    env = os.environ.copy()
    env["WP04_REPLAY_CAMPAIGN"] = args.campaign
    env["PYTHONPATH"] = os.pathsep.join([HERE.as_posix(), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    with tempfile.TemporaryDirectory(prefix="wp04-replay-") as tmp:
        junit = Path(tmp) / "junit.xml"
        command = [
            ".venv/bin/python",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "wp04_fault_plugin",
            f"--junitxml={junit}",
            *nodeids,
        ]
        started = dt.datetime.now(dt.UTC)
        tick = time.monotonic()
        timed_out = False
        try:
            proc = subprocess.run(
                command,
                env=env,
                text=True,
                capture_output=True,
                timeout=args.timeout,
                check=False,
            )
            exit_code = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        elapsed = time.monotonic() - tick
        failures: list[str] = []
        passes: list[str] = []
        if junit.exists():
            for case in ET.parse(junit).iter("testcase"):
                nodeid = f"{case.attrib.get('file')}::{case.attrib.get('classname')}::{case.attrib.get('name')}"
                nodeid = nodeid.replace("::None::", "::").replace(".py::::", ".py::")
                if case.find("failure") is not None or case.find("error") is not None:
                    failures.append(nodeid)
                elif case.find("skipped") is None:
                    passes.append(nodeid)
        receipt = {
            "schema_version": "wp04-replay-receipt/v1",
            "campaign": args.campaign,
            "runner_path": PLUGIN_PATH.relative_to(Path.cwd()).as_posix(),
            "runner_sha256": _sha(PLUGIN_PATH),
            "orchestrator_path": Path(__file__).resolve().relative_to(Path.cwd()).as_posix(),
            "orchestrator_sha256": _sha(Path(__file__).resolve()),
            "spec_path": SPEC_PATH.relative_to(Path.cwd()).as_posix(),
            "spec_sha256": _sha(SPEC_PATH),
            "argv": command,
            "environment": {
                "WP04_REPLAY_CAMPAIGN": args.campaign,
                "PYTHONPATH_prefix": HERE.as_posix(),
                "platform": platform.platform(),
                "python": platform.python_version(),
            },
            "configured_timeout_seconds": args.timeout,
            "started_at": started.isoformat(),
            "ended_at": dt.datetime.now(dt.UTC).isoformat(),
            "elapsed_seconds": round(elapsed, 3),
            "timed_out": timed_out,
            "exit_code": exit_code,
            "selected_nodeids": nodeids,
            "materialized_faults": entries,
            "failed_nodeids": failures,
            "passed_nodeids": passes,
            "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),  # noqa: TID251 - receipt integrity
            "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),  # noqa: TID251 - receipt integrity
            "stdout": stdout,
            "stderr": stderr,
        }
        args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "campaign": args.campaign,
                "selected": len(nodeids),
                "failed": len(failures),
                "passed": len(passes),
                "exit_code": exit_code,
                "timed_out": timed_out,
            },
            sort_keys=True,
        )
    )
    return 0 if not timed_out and exit_code == 1 and failures and not passes else 2


if __name__ == "__main__":
    raise SystemExit(main())
