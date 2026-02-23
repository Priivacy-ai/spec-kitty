"""Glossary markdown link integrity checks."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GLOSSARY_CONTEXTS_DIR = REPO_ROOT / "glossary" / "contexts"

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _slugify_heading(text: str) -> str:
    heading = re.sub(r"\s+#+\s*$", "", text.strip())
    heading = heading.replace("`", "").lower()
    heading = re.sub(r"[^a-z0-9 _-]", "", heading)
    heading = heading.replace(" ", "-")
    heading = re.sub(r"-{2,}", "-", heading).strip("-")
    return heading


@lru_cache(maxsize=None)
def _anchors_for(path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        slug = _slugify_heading(match.group(1))
        if slug:
            anchors.add(slug)
    return anchors


def _iter_local_links(path: Path) -> list[tuple[str, int]]:
    text = path.read_text(encoding="utf-8")
    links: list[tuple[str, int]] = []
    for match in LINK_RE.finditer(text):
        raw_target = match.group(1).strip()
        if not raw_target:
            continue
        target = raw_target.split()[0].strip("<>")
        if not target:
            continue
        if target.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        if "://" in target:
            continue
        line_number = text.count("\n", 0, match.start()) + 1
        links.append((target, line_number))
    return links


_CONTEXT_FILES = sorted(GLOSSARY_CONTEXTS_DIR.glob("*.md"))
_CONTEXT_IDS = [str(path.relative_to(REPO_ROOT)) for path in _CONTEXT_FILES]


@pytest.mark.parametrize("source_path", _CONTEXT_FILES, ids=_CONTEXT_IDS)
def test_glossary_relative_links_resolve(source_path: Path) -> None:
    failures: list[str] = []
    for target, line_number in _iter_local_links(source_path):
        parsed = urlparse(unquote(target))
        link_path = parsed.path
        fragment = parsed.fragment

        if link_path:
            destination = (source_path.parent / link_path).resolve()
        else:
            destination = source_path.resolve()

        try:
            destination.relative_to(REPO_ROOT.resolve())
        except ValueError:
            failures.append(
                f"{source_path.relative_to(REPO_ROOT)}:{line_number} "
                f"link escapes repository: {target}"
            )
            continue

        if link_path and not destination.exists():
            failures.append(
                f"{source_path.relative_to(REPO_ROOT)}:{line_number} "
                f"missing file target: {target}"
            )
            continue

        if fragment and destination.suffix.lower() == ".md":
            if fragment not in _anchors_for(destination):
                failures.append(
                    f"{source_path.relative_to(REPO_ROOT)}:{line_number} "
                    f"missing anchor '{fragment}' in {destination.relative_to(REPO_ROOT)}"
                )

    assert not failures, "\n".join(failures)
