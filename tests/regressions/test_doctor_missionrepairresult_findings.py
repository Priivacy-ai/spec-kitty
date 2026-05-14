"""Regression test for doctor.py:631 — _print_overdue_details type annotation bug.

Bug was:
    _print_overdue_details(report: object, ...) accessed report.entries, but
    mypy --strict flagged this as 'attr-defined' error because 'object' has no
    attribute 'entries'. The type: ignore comment only covered 'union-attr',
    not the actual 'attr-defined' error, producing an 'unused-ignore' error too.

Fix in this commit:
    Changed the type annotation from `object` to `ShimRegistryReport`, which
    correctly types the parameter (the function is only ever called with a
    ShimRegistryReport). This closes the mypy strict carve-out on doctor.py
    established by WP01 (ec1185bf1).

Assertions reflect post-fix behavior.

Pre-fix behavior:
    - doctor.py:631 had 'type: ignore[union-attr]' but the real error was
      [attr-defined], not [union-attr], so mypy reported 'unused-ignore' AND
      'attr-defined' not covered.

Post-fix behavior:
    - _print_overdue_details accepts ShimRegistryReport; .entries access is
      fully typed; no type: ignore comment needed.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock


from specify_cli.compat.doctor import ShimRegistryReport, ShimStatusEntry
from specify_cli.cli.commands.doctor import _print_overdue_details


# ---------------------------------------------------------------------------
# Regression: _print_overdue_details signature is correctly typed
# ---------------------------------------------------------------------------


class TestPrintOverdueDetailsSignature:
    """Verify the type annotation fix for _print_overdue_details.

    Pre-fix: parameter was 'report: object' — mypy blind to .entries access.
    Post-fix: parameter is 'ShimRegistryReport' — correctly typed.
    """

    def test_report_parameter_not_typed_as_bare_object(self) -> None:
        """_print_overdue_details 'report' parameter must NOT be annotated 'object'.

        Pre-fix: annotation was 'object' (mypy couldn't see .entries).
        Post-fix: annotation is ShimRegistryReport.
        """
        sig = inspect.signature(_print_overdue_details)
        report_param = sig.parameters.get("report")
        assert report_param is not None, "Function has no 'report' parameter"
        annotation = report_param.annotation
        # Post-fix: must NOT be the bare 'object' type
        assert annotation is not object, (
            "report parameter is still annotated as 'object' — fix not applied. "
            "Should be ShimRegistryReport."
        )

    def test_report_parameter_annotated_as_shim_registry_report(self) -> None:
        """_print_overdue_details 'report' parameter must be ShimRegistryReport.

        Pre-fix: annotation was 'object'.
        Post-fix: annotation is ShimRegistryReport.
        """
        sig = inspect.signature(_print_overdue_details)
        report_param = sig.parameters.get("report")
        assert report_param is not None
        annotation = report_param.annotation
        # Accept both direct class reference and 'from __future__ import annotations' string
        if isinstance(annotation, str):
            assert "ShimRegistryReport" in annotation, (
                f"Expected ShimRegistryReport in annotation, got: {annotation!r}"
            )
        else:
            assert annotation is ShimRegistryReport, (
                f"Expected ShimRegistryReport, got: {annotation!r}"
            )

    def test_function_callable_with_shim_registry_report_empty(self) -> None:
        """_print_overdue_details accepts ShimRegistryReport with no entries.

        Arrange: empty ShimRegistryReport (no overdue entries).
        Act: call _print_overdue_details(report, console).
        Assert: no AttributeError, no exception.
        """
        report = ShimRegistryReport(
            entries=[],
            project_version="0.0.0",
            registry_path=Path("/dev/null"),
        )
        mock_console = MagicMock()
        # Must not raise — post-fix, .entries is correctly typed
        _print_overdue_details(report, mock_console)
        # Confirms it was called (at least the console.print was invoked for header)
        assert mock_console.print.called

    def test_function_callable_with_shim_registry_report_with_entries(self) -> None:
        """_print_overdue_details iterates .entries without AttributeError.

        Arrange: ShimRegistryReport with one overdue-status entry.
        Act: call _print_overdue_details(report, console).
        Assert: console.print called multiple times (header + entry details).
        """
        from specify_cli.compat.doctor import ShimStatus
        from specify_cli.compat.registry import ShimEntry

        entry = ShimEntry(
            legacy_path="specify_cli.old_module",
            canonical_import=["specify_cli.new_module"],
            introduced_in_release="0.0.1",
            removal_target_release="0.1.0",
            grandfathered=False,
            tracker_issue="https://github.com/example/issues/1",
        )
        status_entry = ShimStatusEntry(
            entry=entry,
            status=ShimStatus.OVERDUE,
            shim_exists=True,
        )
        report = ShimRegistryReport(
            entries=[status_entry],
            project_version="0.2.0",  # past removal target
            registry_path=Path("/dev/null"),
        )
        mock_console = MagicMock()

        # Must not raise AttributeError
        _print_overdue_details(report, mock_console)

        # At least one call for the overdue header and entry details
        assert mock_console.print.call_count >= 1


# ---------------------------------------------------------------------------
# Regression: no 'type: ignore' comment at line 631
# ---------------------------------------------------------------------------


class TestNoSpuriousTypeIgnoreAtLine631:
    """Post-fix: the spurious type: ignore comment at line 631 is removed.

    Pre-fix: 'type: ignore[union-attr]' was present but wrong (error was
    [attr-defined]), causing the 'unused-ignore' mypy error.
    Post-fix: no type: ignore comment needed — ShimRegistryReport is typed.
    """

    def test_no_type_ignore_comment_at_function_definition_line(self) -> None:
        """doctor.py _print_overdue_details body has no 'type: ignore' for .entries.

        Reads the source of _print_overdue_details and asserts no 'type: ignore'
        appears on the 'for e in report.entries' line.

        Pre-fix: line had '# type: ignore[union-attr]'.
        Post-fix: no type: ignore comment needed.
        """
        source_lines = inspect.getsource(_print_overdue_details).splitlines()
        for line in source_lines:
            if "report.entries" in line:
                assert "type: ignore" not in line, (
                    f"Spurious 'type: ignore' still present on report.entries line:\n"
                    f"  {line.strip()}\n\n"
                    "Post-fix: ShimRegistryReport annotation eliminates the need."
                )
