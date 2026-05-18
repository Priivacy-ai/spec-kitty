"""CLI logging bootstrap for Spec Kitty (FR-130, FR-131).

Installs a minimal but deterministic logging configuration at CLI entry so
that ``warnings.warn(...)`` calls — including ``CharterCatalogMissWarning``
emitted by ``charter._catalog_miss.emit_catalog_miss_warning`` — are routed
through Python's logging subsystem and appear in the operator's terminal.

Background (RISK-3 from Mission B post-merge review)
-----------------------------------------------------
Before this bootstrap existed, the call-stack in
``charter._catalog_miss.emit_catalog_miss_warning`` included two surfaces:

1. ``warnings.warn(message, CharterCatalogMissWarning, ...)``
   — Python's default warning machinery may print this to stderr as
   ``source_file:line: WarningClass: message``, but ONLY once per
   (message, category, module, lineno) combination within the process,
   and the format is not operator-friendly (no log-level label, no rich
   highlighting, no consistent timestamp).

2. ``_LOGGER.warning(message, extra=extra)``
   — Silently discarded when no handler is attached to the root logger,
   meaning the structured log entry with its ``kind / id / cause /
   suggestion`` extras never reached the operator.

``install_cli_logging_bootstrap()`` solves both problems:

* ``logging.captureWarnings(True)`` routes ``warnings.warn`` calls through
  the ``logging.warnings`` logger so they appear alongside ordinary log
  records rather than through Python's separate warnings machinery.
* A ``rich.logging.RichHandler`` (or a minimal stderr ``StreamHandler``
  fallback when Rich is not importable) is attached to the root logger so
  that WARNING-level records — from both the ``logging.warnings`` logger and
  module-level loggers like ``charter._catalog_miss._LOGGER`` — reach
  the terminal.

Idempotency / no double-printing
---------------------------------
``install_cli_logging_bootstrap()`` checks ``root.handlers`` before adding
the Spec Kitty handler.  If the root logger already has a handler (e.g.
because a command sets up its own handler, or a test installs one before
importing), the function does **not** add another one.  This prevents
double-printing when commands configure their own logging.

This function MUST be called before the Typer app runs, ideally as the
very first statement in ``specify_cli.__init__.main()`` — before any
import that might trigger a warning.

Usage
-----
Import from the entry point module only::

    from specify_cli.cli.logging_bootstrap import install_cli_logging_bootstrap
    install_cli_logging_bootstrap()

Public API
----------
- :func:`install_cli_logging_bootstrap` — idempotent bootstrap entry point.
- :data:`_HANDLER_SENTINEL` — module-level sentinel used by the idempotency
  guard; exposed for testing.
"""

from __future__ import annotations

import logging
import sys

__all__ = ["install_cli_logging_bootstrap"]

# Sentinel attribute name set on root handlers installed by this module so
# the idempotency guard can recognise them.  Do NOT use this as a public API
# beyond test inspection.
_HANDLER_SENTINEL = "_spec_kitty_bootstrap_handler"


def _build_handler() -> logging.Handler:
    """Construct the preferred WARNING handler.

    Tries ``rich.logging.RichHandler`` first.  Falls back to a plain
    ``logging.StreamHandler(sys.stderr)`` if Rich is unavailable (e.g.
    stripped or unavailable in minimal envs) so the bootstrap never crashes.

    The fallback handler uses a simple format that includes the level name
    so operators can distinguish WARNING from DEBUG output.
    """
    try:
        from rich.console import Console
        from rich.logging import RichHandler

        console = Console(stderr=True, highlight=False)
        handler: logging.Handler = RichHandler(
            console=console,
            show_time=False,
            show_path=False,
            markup=False,
        )
    except ImportError:  # pragma: no cover — Rich is always present in the CLI venv
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(levelname)s  %(message)s")
        )

    handler.setLevel(logging.WARNING)
    # Tag so the idempotency guard can recognise it.
    setattr(handler, _HANDLER_SENTINEL, True)
    return handler


def install_cli_logging_bootstrap() -> None:
    """Install the Spec Kitty CLI logging bootstrap (idempotent).

    Effect:
    * Calls ``logging.captureWarnings(True)`` so ``warnings.warn(...)``
      calls are routed through the ``logging.warnings`` logger instead of
      Python's raw warning machinery.
    * Attaches a Rich-aware (or plain stderr fallback) handler at WARNING
      level to the root logger when no handler is already present.

    The function is a **no-op** if the root logger already has at least one
    handler, preserving any logging configuration that a command or test has
    installed before the bootstrap runs.

    Idempotency is enforced by the ``root.handlers`` check, **not** by a
    module-level flag, so the function behaves correctly even if the
    logging state was cleared between calls (e.g. in tests that call
    ``logging.root.handlers.clear()``).

    Thread safety: CPython's logging module is thread-safe for handler
    mutation; this function does not need additional locking.
    """
    # Route warnings.warn() through the logging subsystem.
    logging.captureWarnings(True)

    root = logging.getLogger()

    # If the root logger already has handlers, adding another would cause
    # double-printing.  Respect existing configuration.
    if root.handlers:
        return

    handler = _build_handler()
    root.addHandler(handler)

    # Ensure the root logger's effective level is at most WARNING so records
    # from module-level loggers (which default to NOTSET / inherit root) are
    # not filtered before reaching the handler.  We only lower the root level
    # here — never raise it — so existing debug configs are preserved.
    if root.level == logging.NOTSET or root.level > logging.WARNING:
        root.setLevel(logging.WARNING)
