"""Versioned docs integrity checks for 1.x and 2.x tracks."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
TRACKS = ("1x", "2x")

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

FORBIDDEN_TERMS = (
    "saas",
    "auth0",
    "nango",
    "authentication",
    "login",
    "dashboard",
    "websocket",
)


def _collect_track_docs() -> list[Path]:
    files: list[Path] = [DOCS_DIR / "index.md"]
    for track in TRACKS:
        files.extend(sorted((DOCS_DIR / track).glob("*.md")))
    return files


DOC_FILES = _collect_track_docs()
DOC_IDS = [str(path.relative_to(REPO_ROOT)) for path in DOC_FILES]


def _iter_local_links(path: Path) -> list[tuple[str, int]]:
    text = path.read_text(encoding="utf-8")
    links: list[tuple[str, int]] = []
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip().strip("<>")
        if not target:
            continue
        if target.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        if "://" in target:
            continue
        line_number = text.count("\n", 0, match.start()) + 1
        links.append((target, line_number))
    return links


def test_versioned_docs_required_files_exist() -> None:
    expected = [
        DOCS_DIR / "index.md",
        DOCS_DIR / "toc.yml",
        DOCS_DIR / "1x" / "index.md",
        DOCS_DIR / "1x" / "toc.yml",
        DOCS_DIR / "2x" / "index.md",
        DOCS_DIR / "2x" / "toc.yml",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in expected if not path.is_file()]
    assert not missing, f"Missing required versioned docs files: {missing}"


@pytest.mark.parametrize("source_path", DOC_FILES, ids=DOC_IDS)
def test_versioned_docs_relative_links_resolve(source_path: Path) -> None:
    failures: list[str] = []
    for target, line_number in _iter_local_links(source_path):
        parsed = urlparse(unquote(target))
        link_path = parsed.path

        if not link_path:
            continue

        destination = (source_path.parent / link_path).resolve()
        try:
            destination.relative_to(REPO_ROOT.resolve())
        except ValueError:
            failures.append(
                f"{source_path.relative_to(REPO_ROOT)}:{line_number} link escapes repo: {target}"
            )
            continue

        if not destination.exists():
            failures.append(
                f"{source_path.relative_to(REPO_ROOT)}:{line_number} missing file target: {target}"
            )

    assert not failures, "\n".join(failures)


def test_versioned_docs_exclude_out_of_scope_terms() -> None:
    failures: list[str] = []
    for track in TRACKS:
        for doc_path in sorted((DOCS_DIR / track).glob("*.md")):
            text = doc_path.read_text(encoding="utf-8").lower()
            for term in FORBIDDEN_TERMS:
                if term in text:
                    failures.append(f"{doc_path.relative_to(REPO_ROOT)} contains forbidden term: '{term}'")
    assert not failures, "\n".join(failures)
