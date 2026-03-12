from __future__ import annotations

import subprocess
from pathlib import Path


def test_feature_creation_requires_main_branch(test_project: Path, run_cli) -> None:
    """Create-feature should fail when not on main branch."""
    subprocess.run(
        ["git", "checkout", "-b", "not-main"],
        cwd=test_project,
        check=True,
        capture_output=True,
    )

    result = run_cli(
        test_project,
        "agent",
        "feature",
        "create-feature",
        "should-fail",
        "--json",
    )

    assert result.returncode != 0, "create-feature should fail when not on main branch"
    assert "main" in result.stdout.lower() or "main" in result.stderr.lower(), (
        "Error message should mention main branch requirement"
    )
