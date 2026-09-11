"""Regression for #4125: the background version-cache refresh is launched as
a real module (``python -m specify_cli.session_presence.upgrade_check``),
never ``python -c "<codegen>"``.

A ``-c`` child has no ``__main__.__file__``; a transitive import that reads
it during interpreter bootstrap crashed with ``AttributeError`` on Windows.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.integration]


def test_module_entry_point_runs_and_never_raises(tmp_path):
    """`python -m ...upgrade_check` must run to completion without a traceback.

    Points the cache at a tmp_path via SPEC_KITTY_HOME so it never touches a
    real ~/.kittify, and opts out of network access via
    SPEC_KITTY_NO_UPGRADE_CHECK so this stays a fast, offline regression
    check on the entry point's wiring, not the network refresh itself.
    """
    env = dict(os.environ)
    env["SPEC_KITTY_NO_UPGRADE_CHECK"] = "1"
    env["SPEC_KITTY_HOME"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "specify_cli.session_presence.upgrade_check"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "Traceback" not in result.stderr
    assert "__main__' has no attribute '__file__'" not in result.stderr
