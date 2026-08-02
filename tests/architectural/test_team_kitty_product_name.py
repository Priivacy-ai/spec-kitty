"""Keep active product language canonical while compatibility symbols migrate."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
SCANNED = (
    ROOT / "src",
    ROOT / "docs",
    ROOT / "README.md",
    ROOT / "MANUAL_TEST_PLAN.md",
    ROOT / "AGENTS.md",
)
REJECTED_PRODUCT_LANGUAGE = re.compile(
    r"\b(?:Team" + "Space|Team" + "space|Kitty" + "Space|Spec Kitty " + r"SaaS)\b"
)


def _active_files() -> list[Path]:
    files: list[Path] = []
    for root in SCANNED:
        if root.is_file():
            files.append(root)
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.suffix in {".py", ".md", ".json", ".yaml", ".yml", ".html"}
            and "archive" not in path.parts
        )
    return files


def test_active_product_language_names_team_kitty() -> None:
    violations: list[str] = []

    for path in _active_files():
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            if REJECTED_PRODUCT_LANGUAGE.search(line):
                violations.append(
                    f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}"
                )

    assert not violations, "Retired product name found:\n" + "\n".join(violations)
