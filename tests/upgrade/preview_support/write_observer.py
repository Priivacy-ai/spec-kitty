"""Test-only Python audit observer installed before the real CLI import.

Covers Python-audited open/mkdir/remove/rename/chmod/utime/link/symlink/rmdir.
Does not trace native extension syscalls, child programs, mmap writes, or network.
Recording mode permits operations; denying mode rejects every covered attempt.
The observer log is opened before measurement outside the audited roots.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

EVENTS = frozenset({"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.chmod", "os.utime", "os.link", "os.symlink", "os.truncate"})


def _probe_event(event: str, root: Path) -> None:
    """Exercise one supported Python event against caller-prepared local nodes."""
    path = root / "file"
    operations: dict[str, Callable[[], object]] = {
        "os.mkdir": lambda: (root / "new-dir").mkdir(),
        "os.remove": path.unlink,
        "os.rmdir": lambda: (root / "empty").rmdir(),
        "os.rename": lambda: path.rename(root / "renamed"),
        "os.chmod": lambda: path.chmod(0o700),
        "os.utime": lambda: os.utime(path, ns=(1_000_000_000, 1_000_000_000)),
        "os.link": lambda: os.link(path, root / "hardlink"),
        "os.symlink": lambda: (root / "symlink").symlink_to("file"),
        "os.truncate": lambda: os.truncate(path, 0),
    }
    operations[event]()


def main() -> None:
    """Run ``LOG record|deny cli ARGS...`` or ``LOG record|deny probe PATH``."""
    log, policy, operation, *args = sys.argv[1:]
    assert policy in {"record", "deny"}, "Unknown observer policy"
    assert "specify_cli" not in sys.modules, "CLI imported before audit hook"
    with open(log, "w", encoding="utf-8") as stream:
        descriptor = stream.fileno()

        def record(event: str, values: tuple[Any, ...]) -> None:
            write_open = event == "open" and (
                (isinstance(values[1], str) and any(flag in values[1] for flag in "wax+"))
                or (isinstance(values[2], int) and bool(values[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
            )
            if event not in EVENTS and not write_open:
                return
            row = {"event": event, "args": [str(value) for value in values], "denied": policy == "deny"}
            os.write(descriptor, (json.dumps(row) + "\n").encode())
            if policy == "deny":
                raise PermissionError(f"Observed write attempt: {event}")

        sys.addaudithook(record)
        os.write(descriptor, (json.dumps({"installed_before_cli": "specify_cli" not in sys.modules}) + "\n").encode())
        if operation == "probe":
            path = Path(args[0])
            path.write_bytes(b"transient")
            path.unlink()
            print("write-delete control completed")
        elif operation == "probe-event":
            _probe_event(args[0], Path(args[1]))
        else:
            assert operation == "cli", "Unknown observer operation"
            from specify_cli import main as cli_main

            sys.argv = ["spec-kitty", *args]
            cli_main()


if __name__ == "__main__":
    main()
