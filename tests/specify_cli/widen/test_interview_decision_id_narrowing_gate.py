"""Mypy gate: shared narrow-once decision_id seam (#2675 / WP07 T060-T061).

Before WP07, ``specify_interview.py`` and ``plan_interview.py`` each carried
a byte-identical block: an intermediate ``_already_widened`` bool computed
from ``current_decision_id is not None``, followed by re-passing the still
``str | None``-typed ``current_decision_id`` into
``render_already_widened_prompt(decision_id: str)``. mypy cannot carry a
narrowing through a stored bool, so both call sites raised a
``str | None -> str`` ``arg-type`` error.

T061 replaced both local blocks with a single call into
``specify_cli.widen.interview_helpers.resolve_already_widened_prompt``,
which narrows ``decision_id`` once and gates the
``render_already_widened_prompt`` call directly on the narrowed parameter
(no intermediate stored bool). This test pins that fix at the mypy level so
a regression to the old per-file pattern (or a new per-file duplicate patch
that narrows twice instead of consolidating) is caught immediately.

Environment requirement: this test invokes mypy via ``sys.executable -m
mypy``, which requires the ``lint`` extra to be installed in the test env
(e.g. ``uv run --extra test --extra lint python -m pytest ...``).

Note: ``widen/interview_helpers.py`` MUST be included in the mypy
invocation alongside the two interview files. The project's blanket
``[[tool.mypy.overrides]] module = ["specify_cli.*"] follow_imports =
"skip"`` treats a ``specify_cli.*`` module's exported symbols as ``Any``
when that module is only *imported* (not itself passed on the command
line) — which silently hides the ``decision_id`` arg-type error. Omitting
``interview_helpers.py`` from the invocation would make this gate pass
vacuously even with the bug present.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [pytest.mark.integration]

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGETS = [
    "src/specify_cli/missions/plan/specify_interview.py",
    "src/specify_cli/missions/plan/plan_interview.py",
    "src/specify_cli/widen/interview_helpers.py",
]


@pytest.mark.slow  # mypy invocation is comparatively expensive
def test_interview_decision_id_narrowing_is_mypy_clean() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", *TARGETS],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "mypy failed on the decision_id narrow-once seam (specify_interview.py / "
        "plan_interview.py / widen/interview_helpers.py). Expected the shared "
        "resolve_already_widened_prompt() helper to narrow decision_id once and "
        "leave both interview files mypy-clean.\n"
        "stdout:\n" + result.stdout + "\nstderr:\n" + result.stderr
    )
    assert "decision_id" not in result.stdout, (
        "A decision_id-related mypy error resurfaced — has the narrow-once seam "
        "regressed to a per-file duplicate fix?\n" + result.stdout
    )
