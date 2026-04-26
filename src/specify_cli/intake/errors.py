"""Structured error codes for the intake security surface (WP02).

Each error carries a stable string code (``INTAKE_*``) so the CLI surface
and downstream callers can distinguish failure modes without parsing
human-readable messages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# Stable string codes — these are what the contract document references.
INTAKE_PATH_ESCAPE: str = "INTAKE_PATH_ESCAPE"
INTAKE_TOO_LARGE: str = "INTAKE_TOO_LARGE"
INTAKE_FILE_MISSING: str = "INTAKE_FILE_MISSING"
INTAKE_FILE_UNREADABLE: str = "INTAKE_FILE_UNREADABLE"
INTAKE_ROOT_INCONSISTENT: str = "INTAKE_ROOT_INCONSISTENT"


class IntakeError(Exception):
    """Base class for structured intake errors.

    Subclasses set :attr:`code` and accept structured ``detail`` data so
    callers can render rich error messages without regex-parsing the
    string form.
    """

    code: str = "INTAKE_ERROR"

    def __init__(self, message: str, **detail: Any) -> None:
        super().__init__(message)
        self.detail: dict[str, Any] = dict(detail)


class IntakePathEscapeError(IntakeError):
    """Raised when a candidate path resolves outside the intake root."""

    code = INTAKE_PATH_ESCAPE

    def __init__(self, *, candidate: Path, intake_root: Path) -> None:
        super().__init__(
            f"{INTAKE_PATH_ESCAPE}: candidate {candidate} resolves outside intake root {intake_root}",
            candidate=str(candidate),
            intake_root=str(intake_root),
        )


class IntakeTooLargeError(IntakeError):
    """Raised when a candidate exceeds the configured size cap."""

    code = INTAKE_TOO_LARGE

    def __init__(self, *, path: Path | str, size: int | None, cap: int) -> None:
        size_str = f"{size}" if size is not None else "unknown"
        super().__init__(
            f"{INTAKE_TOO_LARGE}: {path} ({size_str} bytes) exceeds cap {cap} bytes",
            path=str(path),
            size=size,
            cap=cap,
        )


class IntakeFileMissingError(IntakeError):
    """Raised when ``stat()`` reports the candidate is missing."""

    code = INTAKE_FILE_MISSING

    def __init__(self, *, path: Path | str) -> None:
        super().__init__(
            f"{INTAKE_FILE_MISSING}: {path} does not exist",
            path=str(path),
        )


class IntakeFileUnreadableError(IntakeError):
    """Raised when an existing candidate cannot be read (permissions / IO / decode)."""

    code = INTAKE_FILE_UNREADABLE

    def __init__(self, *, path: Path | str, cause: BaseException) -> None:
        super().__init__(
            f"{INTAKE_FILE_UNREADABLE}: {path} could not be read ({cause.__class__.__name__}: {cause})",
            path=str(path),
            cause=cause.__class__.__name__,
        )
        self.__cause__ = cause


class IntakeRootInconsistentError(IntakeError):
    """Raised when the scanner root does not match the writer root."""

    code = INTAKE_ROOT_INCONSISTENT

    def __init__(self, *, scanner_root: Path, writer_root: Path) -> None:
        super().__init__(
            f"{INTAKE_ROOT_INCONSISTENT}: scanner_root={scanner_root} writer_root={writer_root}",
            scanner_root=str(scanner_root),
            writer_root=str(writer_root),
        )
