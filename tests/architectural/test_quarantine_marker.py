"""The quarantine mechanism is wired correctly end-to-end.

Quarantine is the sanctioned handling for an irreducible *environmental* (Tier 3)
flake: hold it out of every normal/blocking run so it can never turn main red or
block an unrelated PR, while keeping it visible in a dedicated non-blocking CI
job. This pins the three load-bearing facts of that wiring so it cannot silently
rot:

1. the ``quarantine`` marker is registered in ``pytest.ini`` (the single source
   of truth for the marker registry — see #2034);
2. the opt-in gate is strict (only ``"1"`` runs quarantined tests — fail-closed
   to *skip*); and
3. CI runs ``-m quarantine`` in a job that is **non-blocking** (absent from the
   ``quality-gate`` aggregation) and tolerates an empty quarantine set.

See ``docs/development/testing/testing-flakiness.md``.

Retired (planning#57): point 3 above (``test_ci_runs_quarantine_in_a_nonblocking_visible_job``)
was verified LIVE against the real ``.github/workflows/ci-quality.yml`` — the
leftover pre-programme GitHub Actions YAML deleted per PROGRAM.md §2. With no
workflow YAML left to parse, that check has no remaining subject matter and was
removed with the file. Points 1-2 (the marker registry and the opt-in gate's
fail-closed-to-skip semantics) never read a workflow file and stay.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from tests._support.quarantine import (
    QUARANTINE_MARKER,
    RUN_QUARANTINE_ENV_VAR,
    quarantine_opted_in,
)

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _registered_markers() -> list[str]:
    """Marker entries from ``pytest.ini`` — the single source of truth (#2034).

    ``pytest.ini`` (not ``pyproject.toml``) is the live marker registry: pytest
    reads one config file and prefers ``pytest.ini``, so a ``[tool.pytest.ini_options]``
    markers list would be dead config (guarded by
    ``test_marker_registry_single_source.py``).
    """
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(_REPO_ROOT / "pytest.ini", encoding="utf-8")
    raw = parser.get("pytest", "markers", fallback="")
    return [entry.strip() for entry in raw.splitlines() if entry.strip()]


def test_quarantine_marker_is_registered() -> None:
    names = {entry.split(":", 1)[0] for entry in _registered_markers()}
    assert QUARANTINE_MARKER in names, (
        "The `quarantine` marker must be registered in pytest.ini's `markers` "
        "block (the single source of truth, #2034) — see "
        "docs/development/testing/testing-flakiness.md"
    )


def test_opt_in_is_strict_and_fails_closed_to_skip() -> None:
    assert quarantine_opted_in({RUN_QUARANTINE_ENV_VAR: "1"}) is True
    # Anything that is not exactly "1" keeps the test quarantined (skipped).
    assert quarantine_opted_in({}) is False
    assert quarantine_opted_in({RUN_QUARANTINE_ENV_VAR: "0"}) is False
    assert quarantine_opted_in({RUN_QUARANTINE_ENV_VAR: ""}) is False
    assert quarantine_opted_in({RUN_QUARANTINE_ENV_VAR: "true"}) is False
