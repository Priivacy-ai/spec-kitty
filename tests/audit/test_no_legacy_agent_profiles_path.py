"""Regression guards for the removed legacy doctrine profile path."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DIRNAME = "agent" + "-" + "profiles"
LEGACY_PATH = REPO_ROOT / "src" / "doctrine" / LEGACY_DIRNAME
ACTIVE_CODEBASE_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "src",
    REPO_ROOT / "tests",
    REPO_ROOT / "docs",
    REPO_ROOT / "architecture",
    REPO_ROOT / "research",
    REPO_ROOT / "README.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "pyproject.toml",
)


def _active_codebase_files() -> list[Path]:
    files: list[Path] = []
    for path in ACTIVE_CODEBASE_PATHS:
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        files.extend(
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file() and "__pycache__" not in candidate.parts and candidate.suffix != ".pyc"
        )
    return sorted(files)


def test_legacy_agent_profiles_directory_removed() -> None:
    """The old hyphenated doctrine directory must stay deleted."""
    assert not LEGACY_PATH.exists(), (
        "Legacy doctrine path reintroduced: "
        f"{LEGACY_PATH.relative_to(REPO_ROOT)}"
    )


def test_no_legacy_agent_profiles_path_literals_in_active_codebase() -> None:
    """The active codebase must not mention the removed hyphenated path."""
    violations = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in _active_codebase_files()
        if LEGACY_DIRNAME in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert violations == [], (
        f"Found legacy {LEGACY_DIRNAME!r} path references in active codebase files: "
        + ", ".join(violations)
    )
