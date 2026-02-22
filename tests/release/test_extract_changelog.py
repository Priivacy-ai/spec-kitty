from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR = REPO_ROOT / "scripts" / "release" / "extract_changelog.py"


def run_extract(tmp_path: Path, version: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXTRACTOR), version],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_extracts_rc_section(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        dedent(
            """
            # Changelog

            ## [1.0.0rc1] - 2026-02-22

            - RC notes

            ## [0.16.2] - 2026-02-21

            - Stable notes
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_extract(tmp_path, "1.0.0rc1")

    assert result.returncode == 0
    assert "RC notes" in result.stdout
    assert "Stable notes" not in result.stdout


def test_returns_fallback_when_missing(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

    result = run_extract(tmp_path, "9.9.9rc9")

    assert result.returncode == 0
    assert "No changelog entry found" in result.stdout
