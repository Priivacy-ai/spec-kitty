"""Intake security & atomic-write surface (mission stability-and-hygiene-hardening WP02).

This package centralises the boundary helpers used by ``spec-kitty intake``:

* :mod:`provenance` — escape strings before writing them into provenance
  comments / YAML so untrusted source paths cannot break out of the
  comment context or smuggle markdown into the brief.
* :mod:`scanner` — path-canonicalising read helpers with an explicit
  size cap and missing-vs-corrupt distinction.
* :mod:`brief_writer` — atomic write helpers (open + fsync + replace)
  for the brief and provenance sidecar.
* :mod:`errors` — structured error codes shared across the package.

The legacy modules ``specify_cli.intake_sources`` and
``specify_cli.mission_brief`` continue to expose the user-facing API and
delegate to this package for the security-critical paths.
"""

from __future__ import annotations

from .errors import (
    INTAKE_FILE_MISSING,
    INTAKE_FILE_UNREADABLE,
    INTAKE_PATH_ESCAPE,
    INTAKE_ROOT_INCONSISTENT,
    INTAKE_TOO_LARGE,
    IntakeError,
    IntakeFileMissingError,
    IntakeFileUnreadableError,
    IntakePathEscapeError,
    IntakeRootInconsistentError,
    IntakeTooLargeError,
)
from .provenance import escape_for_comment
from .scanner import (
    DEFAULT_MAX_BRIEF_BYTES,
    assert_under_root,
    load_max_brief_bytes,
    read_brief,
    read_stdin_capped,
)

__all__ = [
    "DEFAULT_MAX_BRIEF_BYTES",
    "INTAKE_FILE_MISSING",
    "INTAKE_FILE_UNREADABLE",
    "INTAKE_PATH_ESCAPE",
    "INTAKE_ROOT_INCONSISTENT",
    "INTAKE_TOO_LARGE",
    "IntakeError",
    "IntakeFileMissingError",
    "IntakeFileUnreadableError",
    "IntakePathEscapeError",
    "IntakeRootInconsistentError",
    "IntakeTooLargeError",
    "assert_under_root",
    "escape_for_comment",
    "load_max_brief_bytes",
    "read_brief",
    "read_stdin_capped",
]
