"""Canonical ``uv run`` pytest-invocation resolver (SSOT D3, #2570.3).

``pytest`` is a test-only optional-dependency extra (see the project's
``pyproject.toml``), so the ambient CLI interpreter (``sys.executable``)
legitimately may not have it installed. The pre-review gate previously
hardcoded ``sys.executable -m pytest`` at its one call site
(``review.pre_review_gate.run_scoped_tests_at_head``); under an interpreter
that lacks the ``test`` extra this fails with ``No module named pytest`` and
the gate silently degrades to a false ``GateOutcome.NO_COVERAGE`` warn — the
exact failure #2570.3 removes.

``uv run --project <repo_root> ...`` re-resolves the project's own
``uv``-managed environment (which DOES carry the test extras), so it is
preferred whenever both ``uv`` is on ``PATH`` and the target looks like a
``uv``-managed project (a ``pyproject.toml`` at its root). There is no other
shared ``uv run`` executor in ``src/`` today — ``compat/`` only carries
``uv tool install`` provenance, a distinct concern (installing spec-kitty
itself via uv, not invoking pytest) — so this module is the single new
canonical seam a later consumer should import rather than re-deriving.

**Consumer relocation (mission ``doctrine-controlled-transition-gates-01KY51Z7``
WP02, T007).** The sole production consumer is now
``specify_cli.review.scope_source.GateCoverageScopeSource.test_command()``,
which injects ``--junitxml``/``-q`` and calls this resolver instead of the
old direct call from ``review.pre_review_gate.run_scoped_tests_at_head``
(``pre_review_gate.py`` itself is untouched here — WP03 repoints its call
site). This resolver's own behaviour is unchanged; only its consumer moved.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

__all__ = ["resolve_pytest_command"]


def resolve_pytest_command(pytest_args: Sequence[str], *, repo_root: Path) -> list[str]:
    """Build the ``python -m pytest`` invocation for an interpreter that has pytest.

    Resolution order:

    1. ``uv`` is on ``PATH`` **and** ``<repo_root>/pyproject.toml`` exists ->
       ``["uv", "run", "--project", str(repo_root), "python", "-m", "pytest", *pytest_args]``.
       ``uv run`` resolves the project's own managed virtualenv, which is
       where the ``test`` extra (and therefore ``pytest`` itself) actually
       lives.
    2. Otherwise -> ``[sys.executable, "-m", "pytest", *pytest_args]``, the
       universal fallback used when ``uv`` is unavailable, or when
       ``repo_root`` is not a ``uv``-managed project (no ``pyproject.toml``
       at its root — a named edge case: the AND's second leg).
    """
    if shutil.which("uv") is not None and (repo_root / "pyproject.toml").is_file():
        return ["uv", "run", "--project", str(repo_root), "python", "-m", "pytest", *pytest_args]
    return [sys.executable, "-m", "pytest", *pytest_args]
