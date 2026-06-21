"""The quarantine mechanism is wired correctly end-to-end.

Quarantine is the sanctioned handling for an irreducible *environmental* (Tier 3)
flake: hold it out of every normal/blocking run so it can never turn main red or
block an unrelated PR, while keeping it visible in a dedicated non-blocking CI
job. This pins the three load-bearing facts of that wiring so it cannot silently
rot:

1. the ``quarantine`` marker is registered in ``pyproject.toml``;
2. the opt-in gate is strict (only ``"1"`` runs quarantined tests — fail-closed
   to *skip*); and
3. CI runs ``-m quarantine`` in a job that is **non-blocking** (absent from the
   ``quality-gate`` aggregation) and tolerates an empty quarantine set.

See ``docs/development/testing-flakiness.md``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from tests._support.quarantine import (
    QUARANTINE_MARKER,
    RUN_QUARANTINE_ENV_VAR,
    quarantine_opted_in,
)

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"


def _registered_markers() -> list[str]:
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["pytest"]["ini_options"]["markers"]


def test_quarantine_marker_is_registered() -> None:
    names = {entry.split(":", 1)[0] for entry in _registered_markers()}
    assert QUARANTINE_MARKER in names, (
        "The `quarantine` marker must be registered in "
        "[tool.pytest.ini_options].markers — see docs/development/testing-flakiness.md"
    )


def test_opt_in_is_strict_and_fails_closed_to_skip() -> None:
    assert quarantine_opted_in({RUN_QUARANTINE_ENV_VAR: "1"}) is True
    # Anything that is not exactly "1" keeps the test quarantined (skipped).
    assert quarantine_opted_in({}) is False
    assert quarantine_opted_in({RUN_QUARANTINE_ENV_VAR: "0"}) is False
    assert quarantine_opted_in({RUN_QUARANTINE_ENV_VAR: ""}) is False
    assert quarantine_opted_in({RUN_QUARANTINE_ENV_VAR: "true"}) is False


def test_ci_runs_quarantine_in_a_nonblocking_visible_job() -> None:
    ci = _CI_WORKFLOW.read_text(encoding="utf-8")

    # A dedicated job exists and actually opts in + selects the marker.
    assert "quarantine-visibility:" in ci
    assert f"{RUN_QUARANTINE_ENV_VAR}: " in ci
    assert "-m quarantine" in ci

    # It tolerates an empty quarantine set (pytest exit code 5) rather than
    # going red when no test is currently quarantined.
    assert 'ec" -eq 5' in ci

    # Non-blocking: it MUST NOT be wired into the blocking aggregation gate.
    gate = ci.split("quality-gate:", 1)
    assert len(gate) == 2, "expected a `quality-gate:` aggregation job in the workflow"
    assert "quarantine-visibility.result" not in gate[1], (
        "quarantine-visibility must stay OUT of the quality-gate aggregation so a "
        "quarantined flake can never block a merge"
    )
