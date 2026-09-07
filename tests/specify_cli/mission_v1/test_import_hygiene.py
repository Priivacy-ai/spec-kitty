"""Import-hygiene ratchet for :mod:`specify_cli.mission_v1` (FR-004 / SC-001).

Mission ``dead-port-disposition-01M1TZVN`` (WP01) retired the mission-DSL v1
runtime (``compat`` / ``runner`` / ``guards`` / ``schema``) and dropped the
``transitions`` dependency. ``mission_v1.events`` is the surviving module; it
sits on a hot path (``runtime/next/next_invocation_lifecycle.py`` emits the
``MissionNextInvoked`` observability event through it), so importing it must
never drag the retired state-machine stack -- or its transitive ``six`` --
back into the process.

These are permanent negative invariants, checked in an isolated subprocess so
the test cannot be satisfied by modules another test already imported. They
were RED on the base commit (the package ``__init__`` eagerly imported the
DSL modules, which imported ``transitions``) and GREEN after the retirement.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_DIR = _REPO_ROOT / "src"

_FORBIDDEN_MODULES_PROBE = (
    "import sys, specify_cli.mission_v1.events as e; "
    "bad = sorted(m for m in sys.modules if m == 'transitions' or m.startswith('transitions.') or m == 'six'); "
    "print(','.join(bad))"
)

_LOADED_PACKAGE_MODULES_PROBE = (
    "import sys, specify_cli.mission_v1.events as e; print(','.join(sorted(m for m in sys.modules if m.startswith('specify_cli.mission_v1'))))"
)


def _hermetic_env() -> dict[str, str]:
    """Copy the environment but pin ``PYTHONPATH`` to this checkout's ``src``.

    ``pytest.ini``'s ``pythonpath = src`` does not propagate to subprocesses,
    and an inherited ``PYTHONPATH`` could point the child at a different
    checkout; setting it explicitly keeps the probe honest about *this* tree.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_SRC_DIR)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONSTARTUP", None)
    return env


def _probe(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env=_hermetic_env(),
        timeout=120,
    )
    return result.stdout.strip()


def test_events_import_does_not_load_transitions() -> None:
    """Importing ``mission_v1.events`` leaves ``transitions``/``six`` out of ``sys.modules``."""
    loaded = _probe(_FORBIDDEN_MODULES_PROBE)
    assert loaded == "", f"hot path loaded: {loaded}"


def test_events_import_loads_only_the_package_and_events() -> None:
    """The retired DSL modules are not pulled in by the package ``__init__``."""
    loaded = _probe(_LOADED_PACKAGE_MODULES_PROBE)
    assert loaded.split(",") == ["specify_cli.mission_v1", "specify_cli.mission_v1.events"], f"unexpected specify_cli.mission_v1 modules loaded: {loaded}"
