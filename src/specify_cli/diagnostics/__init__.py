"""Public diagnostics surface."""

from specify_cli.diagnostics.dedup import (
    invocation_succeeded,
    mark_invocation_succeeded,
    report_once,
    reset_for_invocation,
)

__all__ = [
    "invocation_succeeded",
    "mark_invocation_succeeded",
    "report_once",
    "reset_for_invocation",
]
