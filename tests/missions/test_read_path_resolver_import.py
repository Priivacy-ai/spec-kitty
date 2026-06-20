"""Import-time guardrails for mission directory resolver fast paths."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_read_path_resolver_import_does_not_load_charter_or_doctrine() -> None:
    """Keep ``spec-kitty next`` query startup from loading doctrine primitives."""
    code = textwrap.dedent(
        """
        import sys

        before = set(sys.modules)
        import specify_cli.missions._read_path_resolver  # noqa: F401
        after = set(sys.modules)

        loaded = sorted(
            module
            for module in after - before
            if module == "charter"
            or module.startswith("charter.")
            or module == "doctrine"
            or module.startswith("doctrine.")
        )
        assert not loaded, loaded
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
