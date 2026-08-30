"""Architectural guard — ``ruff format --check .`` is enforced, not advisory.

Issue #473's acceptance criterion is "``ruff format --check .`` exits 0 on
``main``, **and stays that way**". Filed against PR #531 (which turned the
whole-repo check green): nothing automated ever invoked that command --

* ``Makefile`` had a ``lint`` target (``ruff check src/``) but no
  ``format-check`` target, and ``src/`` is narrower than the repo anyway;
* ``make test-full`` (the CI agent's target) was pytest only; and
* the planning repo's CI lint step ran ``ruff check`` but never
  ``ruff format``.

So the only thing holding the gate green was manual charter compliance
(``agents/implementer.md``, "the WHOLE repo, not just your files"). The first
unformatted file an implementer adds puts the gate back where #425/#473
found it, with no red signal anywhere (#558).

This guard shells out to the repo's real, pinned ``ruff`` (the same shape
``tests/architectural/test_tid251_enforcement.py`` uses to make TID251
enforced rather than advisory) and asserts ``ruff format --check .`` exits 0.
That puts the gate inside ``make test-full``, so the CI agent's existing
green/red verdict covers it with no change needed to the planning repo's
``bin/ci-run.sh``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ruff_format_check_is_clean_on_whole_repo() -> None:
    """``ruff format --check .`` must exit 0 -- issue #473's acceptance gate."""
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        "`ruff format --check .` is red on the whole repo -- issue #473's "
        "acceptance gate has regressed. Run `ruff format .` to fix the "
        "offending file(s), or, if the file predates the formatter baseline, "
        "add it to [tool.ruff.format].exclude in pyproject.toml with a "
        "comment explaining why (the formatter-debt ratchet).\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
