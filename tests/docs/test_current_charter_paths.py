"""Current docs must not publish legacy charter paths as active layout."""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).resolve().parents[2]

CURRENT_DOC_PATHS = (
    Path("docs/context"),
    Path("docs/guides"),
    Path("docs/api"),
    # spec-driven.md was rehomed from the repository root into docs/context/
    # (mission common-docs-convergence WP11, T031).
    Path("docs/context/spec-driven.md"),
)

# Charter files whose ``charter.offering.authority_paths`` block declares the
# directories the runtime treats as canonical authority surfaces.
_AUTHORITY_PATH_SOURCES = (
    Path(".kittify/charter/charter.yaml"),
    Path(".kittify/charter/governance.yaml"),
)


def test_current_docs_do_not_publish_memory_charter_path() -> None:
    offenders: list[str] = []
    for root in CURRENT_DOC_PATHS:
        abs_root = REPO_ROOT / root
        paths = [abs_root] if abs_root.is_file() else sorted(abs_root.rglob("*.md"))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if ".kittify/memory/charter.md" in text or "memory/charter.md" in text:
                offenders.append(str(path))

    assert offenders == []


def _authority_paths(charter_file: Path) -> list[str]:
    """Extract ``charter.offering.authority_paths`` from a charter/governance YAML file."""
    data = YAML(typ="safe").load(charter_file.read_text(encoding="utf-8"))
    # charter.yaml nests under ``governance``; governance.yaml is flat.
    doctrine = data.get("governance", data).get("doctrine", {})
    return list(charter.offering.get("authority_paths", []))


def test_declared_charter_authority_paths_resolve() -> None:
    """Every declared authority path must resolve to an existing dir/file (FR-019).

    Guards against the dead ``glossary/contexts/``, ``architecture/3.x/adr/`` and
    ``architecture/adrs/`` authority paths regressing back into the charter.
    """
    unresolved: list[str] = []
    for charter_file in _AUTHORITY_PATH_SOURCES:
        abs_charter = REPO_ROOT / charter_file
        if not abs_charter.exists():
            continue
        for declared in _authority_paths(abs_charter):
            if not (REPO_ROOT / declared).exists():
                unresolved.append(f"{charter_file}: {declared}")

    assert unresolved == [], (
        "Charter authority_paths must resolve on disk; unresolved: " f"{unresolved}"
    )
