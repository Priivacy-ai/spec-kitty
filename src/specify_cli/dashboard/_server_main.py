"""Module entry point for the detached dashboard server child process.

``dashboard.server.start_dashboard(background_process=True)`` spawns this
module (``python -m specify_cli.dashboard._server_main <project_dir> <port>
[<token>]``) rather than piping a generated script through ``python -c``.
``-c`` leaves ``__main__`` without a ``__file__`` attribute, and a
Windows-platform transitive import in the server import chain reads it, so
the child died with ``AttributeError: module '__main__' has no attribute
'__file__'`` before ever binding — invisibly, because its output was sent to
DEVNULL (#4125). ``-m`` gives ``__main__`` a real ``__file__``, which is the
stdlib-blessed way to spawn package code, so no platform bootstrap can trip
on it.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .server import run_dashboard_server

# The entry function is underscore-private and unexported, exactly like
# ``specify_cli.completion._main``: it is reached only through ``python -m``
# module execution (the ``if __name__ == "__main__"`` block below), never
# imported by name, so a public ``main`` in ``__all__`` would be an orphan
# under the symbol-level dead-code gate (tests/architectural/
# test_no_dead_symbols.py, #470) with no possible static caller.
_USAGE = "usage: python -m specify_cli.dashboard._server_main <project_dir> <port> [<token>]"


def _main(argv: list[str] | None = None) -> int:
    """Run the dashboard server forever for ``<project_dir>`` on ``<port>``.

    ``<token>`` is optional; when omitted the dashboard serves without a
    project token. Returns only on an unhandled server error; the parent's
    readiness probe treats any early return as a spawn failure. Usage and
    argument-parsing errors print the usage line to stderr and return 2.
    """
    args = list(sys.argv[1:] if argv is None else argv)

    if len(args) not in (2, 3):
        print(_USAGE, file=sys.stderr)
        return 2
    try:
        port = int(args[1])
    except ValueError:
        print(_USAGE, file=sys.stderr)
        return 2
    project_dir = Path(args[0])
    token = args[2] if len(args) == 3 else None
    run_dashboard_server(project_dir, port, token)
    return 0


if __name__ == "__main__":  # pragma: no cover — exercised via real spawn tests
    raise SystemExit(_main())
