"""Shared infrastructure for the ``spec-kitty doctor`` command surface.

This module is the **single canonical home (H1, I-3)** for the cross-cutting
infrastructure every ``doctor`` sibling needs: the shared Rich ``console``
singleton, the ``--json`` output guards, and the module constants. Extracting
it first (WP02, #2059) gives WP03–WP10 a stable surface to import, and removes
the dominant circular-import hazard: every module that emits output MUST use the
SAME :class:`rich.console.Console` instance, never re-instantiate one (a
per-module ``Console()`` breaks ``--json`` stdout cleanliness and the byte-pinned
doctrine-selections snapshot).

Import discipline (one-way graph, I-2): this module imports only the standard
library, :mod:`rich`, and :mod:`._profile_health_render` (for the ``console``
singleton). It must NEVER import a cluster sibling or ``doctor.py``.

Canonical console direction: ``console`` is instantiated exactly once in
:mod:`._profile_health_render` and re-exported here. ``doctor.py`` and every
extracted sibling import ``console`` from this module, so a single
:class:`~rich.console.Console` instance backs the whole surface.
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from collections.abc import Generator
from contextlib import contextmanager

# The single Console() instance lives in _profile_health_render; re-export it so
# this module is the one import site for siblings while preserving one instance.
from ._profile_health_render import console as console

__all__ = [
    "console",
    "_CI_ENV_VARS",
    "_STARTED_AT_COLUMN",
    "_NOT_IN_PROJECT_MESSAGE",
    "_is_interactive_environment",
    "_json_output_guard",
    "_json_error",
]

# CI env-vars that should force non-interactive behaviour even when stdin
# happens to be a TTY. Conservative list per WP04 Risks: a false positive
# here would block an operator from remediating in a real local shell, so
# only well-known names are included.
_CI_ENV_VARS = (
    "CI",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "BUILDKITE",
    "JENKINS_URL",
    "CIRCLECI",
)

#: Column header for the invocation/op start timestamp, reused across the
#: orphan/open/closed invocation tables rendered by ``spec-kitty doctor``.
_STARTED_AT_COLUMN = "Started At"
_NOT_IN_PROJECT_MESSAGE = "Not in a spec-kitty project"


def _is_interactive_environment() -> bool:
    """Return True iff stdin is a TTY AND no common CI env var is set.

    Matches the FR-023 contract: in CI / non-interactive environments,
    ``doctor sparse-checkout --fix`` must print a remediation pointer and
    exit non-zero rather than prompting.
    """
    if not sys.stdin.isatty():
        return False
    return all(
        os.environ.get(var, "").lower() not in ("true", "1", "yes")
        for var in _CI_ENV_VARS
    )


@contextmanager
def _json_output_guard(enabled: bool) -> Generator[None, None, None]:
    """Keep ``--json`` stdout/stderr machine-clean."""
    if not enabled:
        yield
        return

    previous_disable = logging.root.manager.disable
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.CRITICAL)
        try:
            yield
        finally:
            logging.disable(previous_disable)


def _json_error(code: str, message: str) -> dict[str, object]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
