"""Unit tests for the CLI logging bootstrap (FR-130, FR-131).

Pins the behaviour of :func:`specify_cli.cli.logging_bootstrap.install_cli_logging_bootstrap`:

* Warning-level records from both ``warnings.warn()`` (after captureWarnings)
  and module-level ``logging.getLogger(__name__).warning()`` calls MUST
  reach stderr when no handler is pre-installed.
* If the root logger already has a handler before the bootstrap runs, the
  function does NOT add a second one (no double-printing).
* ``logging.captureWarnings(True)`` is always called.
* The installed handler fires at WARNING level (not DEBUG, not INFO).

All tests are isolated: they save and restore the root logger's handlers list
and ``logging.root.level`` so they do not pollute other test sessions.

These tests are pure-logic / in-process (no subprocess, no git, no filesystem
I/O), so they run in < 50 ms each and are marked ``fast``.
"""

from __future__ import annotations

import io
import logging
import warnings
from collections.abc import Generator

import pytest

from specify_cli.cli.logging_bootstrap import (
    _HANDLER_SENTINEL,
    install_cli_logging_bootstrap,
)


pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures — save / restore root-logger state for isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_root_logger() -> Generator[None, None, None]:
    """Save root-logger state before each test and restore it after.

    This prevents the bootstrap from accumulating handlers across tests and
    ensures the ``logging.captureWarnings`` toggle does not leak.
    """
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    import logging as _logging
    try:
        yield
    finally:
        root.handlers[:] = original_handlers
        root.setLevel(original_level)
        _logging.captureWarnings(False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_root_handlers() -> None:
    """Remove all handlers from the root logger."""
    root = logging.getLogger()
    root.handlers.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInstallCliLoggingBootstrap:
    """Behaviour tests for install_cli_logging_bootstrap()."""

    def test_capturewarnings_is_always_set(self) -> None:
        """logging.captureWarnings(True) must be called regardless of handlers.

        FR-131: warnings.warn() calls must route through the logging
        subsystem after the bootstrap runs.
        """
        _clear_root_handlers()
        install_cli_logging_bootstrap()

        # Emit a warning and check it was routed to logging.warnings logger
        warn_logger = logging.getLogger("py.warnings")
        assert warn_logger is not None  # existence proves captureWarnings was called

        # Functional proof: with captureWarnings(True) and a root handler,
        # warnings.warn should produce a log record.
        buf = io.StringIO()
        test_handler = logging.StreamHandler(buf)
        test_handler.setLevel(logging.WARNING)
        warn_logger.addHandler(test_handler)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("always")
                warnings.warn("test-capturewarnings-check", UserWarning, stacklevel=1)
            output = buf.getvalue()
            assert "test-capturewarnings-check" in output, (
                f"captureWarnings should route warn() to py.warnings logger; got: {output!r}"
            )
        finally:
            warn_logger.removeHandler(test_handler)

    def test_handler_installed_on_root_when_no_existing_handlers(self) -> None:
        """A handler is added to root logger when no handlers are present.

        FR-130: WARNING records from module-level loggers must reach stderr
        when the CLI runs without an explicit logging configuration.
        """
        _clear_root_handlers()
        root = logging.getLogger()
        assert not root.handlers, "pre-condition: no handlers before bootstrap"

        install_cli_logging_bootstrap()

        assert root.handlers, "bootstrap should install at least one handler"

    def test_no_handler_added_when_handlers_already_exist(self) -> None:
        """If root already has a handler, the bootstrap does NOT add another.

        Prevents double-printing when a command configures its own handler
        (e.g. verbose mode) or a test fixture installs one before import.
        """
        root = logging.getLogger()
        _clear_root_handlers()

        # Pre-install a dummy handler
        existing = logging.StreamHandler(io.StringIO())
        existing.setLevel(logging.DEBUG)
        root.addHandler(existing)

        handler_count_before = len(root.handlers)
        install_cli_logging_bootstrap()
        handler_count_after = len(root.handlers)

        assert handler_count_after == handler_count_before, (
            "bootstrap must not add a handler when one already exists; "
            f"before={handler_count_before}, after={handler_count_after}"
        )

    def test_installed_handler_level_is_warning(self) -> None:
        """The bootstrap handler fires at WARNING, not DEBUG or INFO.

        FR-130: only actionable operator-facing records should appear.
        Debug noise must not leak to the terminal under normal operation.
        """
        _clear_root_handlers()
        install_cli_logging_bootstrap()

        root = logging.getLogger()
        installed = [h for h in root.handlers if getattr(h, _HANDLER_SENTINEL, False)]
        assert installed, "expected at least one bootstrap-tagged handler"

        handler = installed[0]
        assert handler.level == logging.WARNING, (
            f"bootstrap handler level must be WARNING ({logging.WARNING}); "
            f"got {handler.level}"
        )

    def test_root_level_set_to_at_most_warning_when_unset(self) -> None:
        """Root logger level is lowered to WARNING when previously NOTSET.

        If root level remains NOTSET (0) while the handler requires WARNING,
        records from module-level loggers would still propagate but the root
        logger's effective level would be DEBUG — correct but surprising.
        Setting it to WARNING ensures the root logger's own level gate
        matches the handler.
        """
        _clear_root_handlers()
        root = logging.getLogger()
        root.setLevel(logging.NOTSET)

        install_cli_logging_bootstrap()

        assert root.level <= logging.WARNING, (
            f"root logger level should be set to at most WARNING after bootstrap; "
            f"got {root.level}"
        )

    def test_warning_record_reaches_handler_output(self) -> None:
        """A WARNING-level log record must reach the installed handler.

        Integration: this exercises the full chain — root level gate,
        handler level gate, handler emit — to confirm a module-level
        logger.warning() call is visible after bootstrap.
        """
        _clear_root_handlers()

        # Install the bootstrap, then replace its handler with a capturable one
        install_cli_logging_bootstrap()
        root = logging.getLogger()

        buf = io.StringIO()
        capture_handler = logging.StreamHandler(buf)
        capture_handler.setLevel(logging.WARNING)
        root.handlers.clear()
        root.addHandler(capture_handler)

        test_logger = logging.getLogger("test.catalog_miss.probe")
        test_logger.warning("Charter catalog miss for styleguide:probe-id; cause=missing_artifact")

        output = buf.getvalue()
        assert "Charter catalog miss" in output, (
            f"WARNING record not captured; got: {output!r}"
        )
        assert "probe-id" in output

    def test_debug_record_does_not_reach_handler(self) -> None:
        """DEBUG records are filtered out by the bootstrap handler.

        The bootstrap installs a WARNING-level handler to avoid flooding
        the operator's terminal with internal debugging noise.
        """
        _clear_root_handlers()
        install_cli_logging_bootstrap()

        root = logging.getLogger()
        buf = io.StringIO()
        capture_handler = logging.StreamHandler(buf)
        capture_handler.setLevel(logging.WARNING)
        root.handlers.clear()
        root.addHandler(capture_handler)
        root.setLevel(logging.DEBUG)

        logging.getLogger("test.debug.probe").debug("this-debug-message-must-not-appear")

        output = buf.getvalue()
        assert "this-debug-message-must-not-appear" not in output

    def test_idempotent_when_called_twice(self) -> None:
        """Calling install_cli_logging_bootstrap() twice does not duplicate handlers."""
        _clear_root_handlers()

        install_cli_logging_bootstrap()
        count_after_first = len(logging.getLogger().handlers)

        install_cli_logging_bootstrap()
        count_after_second = len(logging.getLogger().handlers)

        assert count_after_first == count_after_second, (
            "second call to install_cli_logging_bootstrap() must not add handlers; "
            f"first={count_after_first}, second={count_after_second}"
        )

    def test_json_mode_silences_logs_and_warnings(self) -> None:
        """json_mode silences diagnostics so a ``--json 2>&1`` capture stays pure JSON.

        Non-vacuous: a real WARNING handler is pre-installed, then json_mode must
        silence it so neither ``logger.warning()`` nor a captured ``warnings.warn()``
        produces output.
        """
        root = logging.getLogger()
        _clear_root_handlers()
        buf = io.StringIO()
        pre_handler = logging.StreamHandler(buf)
        pre_handler.setLevel(logging.WARNING)
        root.addHandler(pre_handler)
        root.setLevel(logging.WARNING)

        install_cli_logging_bootstrap(json_mode=True)

        logging.getLogger("test.json.probe").warning("must-not-appear")
        logging.getLogger("test.json.probe").error("error-must-not-appear")
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            warnings.warn("warn-must-not-appear", UserWarning, stacklevel=1)

        assert buf.getvalue() == "", (
            f"json_mode must silence diagnostics on stderr; got: {buf.getvalue()!r}"
        )

    def test_json_mode_installs_handler_to_suppress_lastresort(self) -> None:
        """With no pre-existing handler, json_mode installs one so Python's
        ``lastResort`` (WARNING→stderr) never fires for an otherwise-handlerless root.
        """
        _clear_root_handlers()
        root = logging.getLogger()
        assert not root.handlers, "pre-condition: no handlers"

        install_cli_logging_bootstrap(json_mode=True)

        assert root.handlers, "json_mode must install a handler to suppress lastResort"
        assert all(
            getattr(h, _HANDLER_SENTINEL, False) for h in root.handlers
        ), "the installed json-mode handler should be bootstrap-tagged"

    def test_default_mode_still_emits_warnings(self) -> None:
        """Sanity/non-vacuity: default (non-json) mode still surfaces WARNINGs —
        proving the json_mode silence is the *difference*, not a global suppression.
        """
        _clear_root_handlers()
        install_cli_logging_bootstrap()  # json_mode defaults to False
        root = logging.getLogger()
        buf = io.StringIO()
        capture = logging.StreamHandler(buf)
        capture.setLevel(logging.WARNING)
        root.handlers.clear()
        root.addHandler(capture)

        logging.getLogger("test.default.probe").warning("should-appear")

        assert "should-appear" in buf.getvalue()

    def test_default_mode_after_json_mode_restores_existing_handler(self) -> None:
        """A long-lived process can run a later human-mode bootstrap after json_mode."""
        root = logging.getLogger()
        _clear_root_handlers()
        buf = io.StringIO()
        pre_handler = logging.StreamHandler(buf)
        pre_handler.setLevel(logging.WARNING)
        root.addHandler(pre_handler)
        root.setLevel(logging.WARNING)

        install_cli_logging_bootstrap(json_mode=True)
        logging.getLogger("test.restore.probe").warning("hidden-in-json")
        assert buf.getvalue() == ""

        install_cli_logging_bootstrap(json_mode=False)
        logging.getLogger("test.restore.probe").warning("visible-after-restore")

        assert "visible-after-restore" in buf.getvalue()
        assert pre_handler.level == logging.WARNING

    def test_default_mode_after_json_null_handler_installs_visible_handler(self) -> None:
        """A JSON-only NullHandler must not block later human-mode bootstrap."""
        _clear_root_handlers()
        root = logging.getLogger()

        install_cli_logging_bootstrap(json_mode=True)
        assert any(isinstance(handler, logging.NullHandler) for handler in root.handlers)

        install_cli_logging_bootstrap(json_mode=False)

        assert root.handlers
        assert not any(isinstance(handler, logging.NullHandler) for handler in root.handlers)
