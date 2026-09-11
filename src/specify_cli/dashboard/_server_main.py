"""Module entry point for the detached dashboard background process.

Run as ``python -m specify_cli.dashboard._server_main``.  This replaces the
former ``python -c "<codegen>"`` launch (#4125): a ``-c`` child has no
``__main__.__file__`` attribute, and a transitive import touched during
interpreter bootstrap on Windows reads it, crashing with
``AttributeError: module '__main__' has no attribute '__file__'`` before the
dashboard ever binds a socket.  Running as ``-m`` gives the child a real
module ``__main__`` with a genuine ``__file__``, so that crash cannot occur.

Kept intentionally tiny and import-light — the actual server implementation
lives in :mod:`specify_cli.dashboard.server` and is imported lazily inside
:func:`_main` so argument-parsing errors do not pay the cost (or risk the
import side effects) of loading the full CLI package.

The entry function is underscore-private: this module is a subprocess entry
point run via ``-m`` (and referenced by :mod:`specify_cli.dashboard.server`
through its ``__name__``), never a library whose ``main`` other code imports.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="specify_cli.dashboard._server_main")
    parser.add_argument("--project-dir", required=True, help="Project directory the dashboard serves.")
    parser.add_argument("--port", required=True, type=int, help="Port to bind (0 for an OS-assigned ephemeral port).")
    parser.add_argument("--token", default=None, help="Dashboard security token, if any.")
    parser.add_argument(
        "--port-report-file",
        default=None,
        help="Sidecar file to write the actually-bound port into, right after bind (ephemeral-port hand-off).",
    )
    return parser


def _main(argv: list[str] | None = None) -> int:
    """Parse argv and run the dashboard server forever. Returns a process exit code."""
    args = _build_arg_parser().parse_args(sys.argv[1:] if argv is None else argv)

    # Imported here (not at module scope) so `-m ... --help`/argument errors
    # never pay for importing the full dashboard router/handler graph.
    from specify_cli.dashboard.server import run_dashboard_server

    port_report_path = Path(args.port_report_file) if args.port_report_file else None
    run_dashboard_server(
        Path(args.project_dir),
        args.port,
        args.token,
        port_report_path=port_report_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
