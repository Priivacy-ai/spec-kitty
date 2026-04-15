"""Regression guard against language-specific tool bias in generic shipped artifacts."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]


REPO_ROOT = Path(__file__).resolve().parents[2]
DENYLIST = (
    r"\bpytest\b",
    r"\bjunit\b",
    r"\bjest\b",
    r"\bcargo\s+test\b",
    r"\bxctest\b",
    r"\bmypy\b",
    r"\bruff\b",
    r"\bgradle\b",
    r"\bmaven\b",
    r"\bphpunit\b",
    r"\brspec\b",
)
GENERIC_SURFACES = (
    Path("src/doctrine/agent_profiles/shipped"),
    Path("src/doctrine/skills"),
    Path("src/doctrine/tactics/shipped"),
    Path("src/doctrine/templates"),
    Path("src/doctrine/missions/software-dev/templates"),
    Path("src/specify_cli/missions/software-dev/templates"),
    Path("src/specify_cli/templates"),
    Path("src/charter/defaults.yaml"),
)
ALLOWED_PATH_SNIPPETS = (
    "python-",
    "PYTHON_",
    "claudeignore-template",
)


def _iter_generic_artifacts() -> list[Path]:
    paths: list[Path] = []
    for surface in GENERIC_SURFACES:
        absolute = REPO_ROOT / surface
        if absolute.is_file():
            paths.append(absolute)
            continue
        if not absolute.is_dir():
            continue
        paths.extend(path for path in absolute.rglob("*") if path.is_file())
    return sorted(paths)


def _is_allowlisted(path: Path, content: str) -> bool:
    as_posix = path.as_posix()
    if any(snippet in as_posix for snippet in ALLOWED_PATH_SNIPPETS):
        return True
    return "applies_to_languages:" in content


def test_generic_shipped_artifacts_do_not_embed_language_specific_tool_bias() -> None:
    violations: list[str] = []

    for path in _iter_generic_artifacts():
        content = path.read_text(encoding="utf-8")
        if _is_allowlisted(path, content):
            continue

        for pattern in DENYLIST:
            if re.search(pattern, content, flags=re.IGNORECASE):
                violations.append(f"{path.relative_to(REPO_ROOT)} matches {pattern}")

    assert violations == []
