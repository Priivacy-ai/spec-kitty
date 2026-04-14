"""CLI helpers exposed for other modules."""

# T046 — Enforce UTF-8 on Windows before any user-facing output.
# Must be the first import so non-ASCII path strings (emoji, accented
# characters) do not crash the process on code pages like cp1252.
from specify_cli.encoding import ensure_utf8_on_windows

ensure_utf8_on_windows()

from .step_tracker import StepTracker
from .ui import get_key, select_with_arrows, multi_select_with_arrows

__all__ = ["StepTracker", "get_key", "select_with_arrows", "multi_select_with_arrows"]
