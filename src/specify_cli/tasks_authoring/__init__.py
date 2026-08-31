"""Authoring-time advisory tooling for work-package task prose.

This package hosts *advisory* (never-blocking) analyzers that run while a
mission's work packages are being authored. The first analyzer is the
un-terminable-work detector (:mod:`post_integration_warning`), which warns when
a work package's acceptance criteria can only be satisfied *post-integration*
(the #3590 trap). It is deliberately I/O-free and side-effect-free so it can be
exercised against a fixed labeled corpus (the measurement oracle, SC-003).

Nothing in this package may fail or block authoring (FR-008).
"""

from __future__ import annotations

from specify_cli.tasks_authoring.post_integration_warning import (
    TRIGGER_SET_VERSION,
    PostIntegrationWarning,
    scan_work_package,
    trigger_phrases,
)

__all__ = [
    "TRIGGER_SET_VERSION",
    "PostIntegrationWarning",
    "scan_work_package",
    "trigger_phrases",
]
