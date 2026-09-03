"""Any-edge cold-import boundary: status orchestration must stay out of hot paths.

Regression guard for #1461, generalized after the #3843 owned-checkout stack silently
reconnected the status orchestration package into the ``specify_cli.task_utils`` leaf —
which 37 CLI command modules cold-import — through ``core.owned_mission``'s module-level
``context.mission_resolver`` / ``checkout_ownership`` imports.

The pre-existing enforcement (``tests/cli/commands/test_charter_package_exports.py``)
watched only the ``charter`` command package and enumerated four exact modules, so a new
edge into a *shared leaf below* charter slid straight through the hole. This gate is the
durable form: it protects every cold-import-sensitive root and forbids the whole status
orchestration / workspace subtree (an *any-edge* check), not four named modules.

The invariant lives in prose today at ``task_utils/support.py`` ("avoid pulling in the
full status orchestration package during cold command imports"); this promotes it to an
enforced, edge-general architectural gate.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

# Cold-import roots that must never drag status orchestration in at import time.
# task_utils.support is the shared leaf (37 CLI commands cold-import it); charter is the
# command package that historically carried the only #1461 assertion; owned_mission is
# the core preflight module whose module-level imports reconnected the chain in #3843.
_PROTECTED_ROOTS = (
    "specify_cli.cli.commands.charter",
    "specify_cli.task_utils.support",
    "specify_cli.core.owned_mission",
)

# The status orchestration + workspace subtree, plus the agent-utils status surface.
# Matched exactly or by dotted-prefix, so the lightweight sibling ``specify_cli.status_lanes``
# (a lanes-constant module, not the orchestration package) is deliberately NOT forbidden.
_FORBIDDEN_ROOTS = (
    "specify_cli.status",
    "specify_cli.workspace",
    "specify_cli.agent_utils.status",
)


def _forbidden_modules_loaded_by(module: str) -> list[str]:
    """Cold-import ``module`` in a fresh interpreter, return any forbidden modules loaded."""
    forbidden_literal = repr(_FORBIDDEN_ROOTS)
    script = (
        "import sys\n"
        f"import {module}\n"
        f"forbidden = {forbidden_literal}\n"
        "hit = sorted(\n"
        "    m for m in sys.modules\n"
        "    if any(m == f or m.startswith(f + '.') for f in forbidden)\n"
        ")\n"
        "print('\\n'.join(hit))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT,
        env={"PYTHONPATH": str(_SRC), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


@pytest.mark.parametrize("root", _PROTECTED_ROOTS)
def test_cold_import_keeps_status_orchestration_out(root: str) -> None:
    """A protected cold-import root must not transitively load status/workspace."""
    leaked = _forbidden_modules_loaded_by(root)
    assert not leaked, (
        f"Cold-importing {root!r} loaded {len(leaked)} forbidden status/workspace "
        f"module(s): {leaked[:10]}. Keep status orchestration behind a function-local "
        f"import on the hot path (see #1461 / owned_mission)."
    )
