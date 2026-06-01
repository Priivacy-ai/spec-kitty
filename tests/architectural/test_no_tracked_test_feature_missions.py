"""Guard against accidentally committing generated test mission fixtures."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_tracked_test_feature_missions() -> None:
    result = subprocess.run(
        ["git", "ls-files", "kitty-specs/test-feature-*"],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    tracked = [line for line in result.stdout.splitlines() if line.strip()]
    assert tracked == [], (
        "Generated test missions must not be tracked under kitty-specs/: "
        f"{tracked}. Remove them with `git rm -r kitty-specs/test-feature-*`."
    )
