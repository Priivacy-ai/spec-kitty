"""Architecture docs consistency checks.

Verifies structural integrity of the architecture corpus:
- Required directories and files are present.
- ADR files follow the naming convention.
- ADR files contain required sections.
- Local links within architecture markdown files resolve.
- User-journey actor-table persona links point to existing audience files.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCH_DIR = REPO_ROOT / "architecture"

ADR_TRACKS = {
    "1.x": ARCH_DIR / "1.x" / "adr",
    "2.x": ARCH_DIR / "2.x" / "adr",
}

ADR_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d+-.+\.md$")

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

REQUIRED_ARCH_PATHS: list[Path] = [
    ARCH_DIR / "README.md",
    ARCH_DIR / "adr-template.md",
    ARCH_DIR / "ARCHITECTURE_DOCS_GUIDE.md",
    ARCH_DIR / "NAVIGATION_GUIDE.md",
    ARCH_DIR / "adrs",
    ARCH_DIR / "audience" / "README.md",
    ARCH_DIR / "audience" / "internal",
    ARCH_DIR / "audience" / "external",
    ARCH_DIR / "1.x" / "adr",
    ARCH_DIR / "2.x" / "adr",
    ARCH_DIR / "2.x" / "user_journey",
]

# Each entry is a tuple of acceptable alternatives for a required section.
# An ADR satisfies the requirement when ANY alternative is present.
# Alternatives are treated as substrings searched via re.search with MULTILINE.
_CONTEXT_SECTION_RE = re.compile(r"^##\s+Context(\s+and\s+Problem\s+Statement)?\s*$", re.MULTILINE)
_DECISION_SECTION_RE = re.compile(r"^##\s+Decision(\s+Outcome)?\s*$", re.MULTILINE)

REQUIRED_ADR_SECTION_CHECKS: tuple[tuple[str, re.Pattern[str] | None], ...] = (
    ("Status", None),
    ("Context / Context and Problem Statement", _CONTEXT_SECTION_RE),
    ("Decision / Decision Outcome", _DECISION_SECTION_RE),
)


def _collect_arch_md_files() -> list[Path]:
    """Return all markdown files under architecture/, resolving symlinks."""
    return sorted(ARCH_DIR.rglob("*.md"))


def _collect_adr_files() -> list[tuple[str, Path]]:
    """Return (track_label, path) for every ADR file in both tracks.

    README.md index files are excluded because they are not ADRs.
    """
    result: list[tuple[str, Path]] = []
    for track, adr_dir in ADR_TRACKS.items():
        if adr_dir.is_dir():
            for path in sorted(adr_dir.glob("*.md")):
                if path.name.lower() == "readme.md":
                    continue
                result.append((track, path))
    return result


ARCH_MD_FILES = _collect_arch_md_files()
ARCH_MD_IDS = [str(path.relative_to(REPO_ROOT)) for path in ARCH_MD_FILES]

ADR_FILES = _collect_adr_files()
ADR_IDS = [f"{track}::{path.name}" for track, path in ADR_FILES]


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
        # Skip absolute filesystem paths (e.g. /Users/... references to local machine
        # files found in some notes/drafts).  All paths of this kind found in the
        # architecture corpus point to off-repo locations and cannot be validated here.
        # Repo-root-relative links do not appear in these files.
        if target.startswith("/"):
            continue
        line_number = text.count("\n", 0, match.start()) + 1
        links.append((target, line_number))
    return links


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


def test_architecture_required_paths_exist() -> None:
    missing = [str(p.relative_to(REPO_ROOT)) for p in REQUIRED_ARCH_PATHS if not p.exists()]
    assert not missing, f"Missing required architecture paths: {missing}"


def test_architecture_adr_directories_are_not_empty() -> None:
    empty = [
        str(adr_dir.relative_to(REPO_ROOT))
        for adr_dir in ADR_TRACKS.values()
        if adr_dir.is_dir() and not list(adr_dir.glob("*.md"))
    ]
    assert not empty, f"ADR directories are empty (expected at least one .md file): {empty}"


# ---------------------------------------------------------------------------
# ADR naming convention
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("track,adr_path", ADR_FILES, ids=ADR_IDS)
def test_adr_filename_follows_naming_convention(track: str, adr_path: Path) -> None:
    assert ADR_FILENAME_RE.match(adr_path.name), (
        f"ADR in track '{track}' does not follow naming convention "
        f"'YYYY-MM-DD-N-descriptive-title.md': {adr_path.name}"
    )


# ---------------------------------------------------------------------------
# ADR required sections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("track,adr_path", ADR_FILES, ids=ADR_IDS)
def test_adr_contains_required_sections(track: str, adr_path: Path) -> None:
    text = adr_path.read_text(encoding="utf-8")
    missing_sections: list[str] = []
    for label, pattern in REQUIRED_ADR_SECTION_CHECKS:
        if pattern is None:
            # Simple substring check (e.g. "Status" field in bold or table form).
            if label not in text:
                missing_sections.append(label)
        else:
            if not pattern.search(text):
                missing_sections.append(label)
    assert not missing_sections, (
        f"ADR '{adr_path.relative_to(REPO_ROOT)}' (track '{track}') is missing "
        f"required sections: {missing_sections}"
    )


# ---------------------------------------------------------------------------
# Link resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source_path", ARCH_MD_FILES, ids=ARCH_MD_IDS)
def test_architecture_relative_links_resolve(source_path: Path) -> None:
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


# ---------------------------------------------------------------------------
# User-journey actor persona links
# ---------------------------------------------------------------------------

ACTOR_LINK_RE = re.compile(r"\[([^\]]+)\]\((\.\.\/\.\.\/audience[^)]+)\)")


def _collect_user_journey_files() -> list[Path]:
    user_journey_dir = ARCH_DIR / "2.x" / "user_journey"
    if not user_journey_dir.is_dir():
        return []
    return sorted(user_journey_dir.glob("*.md"))


USER_JOURNEY_FILES = _collect_user_journey_files()
USER_JOURNEY_IDS = [str(p.relative_to(REPO_ROOT)) for p in USER_JOURNEY_FILES]


@pytest.mark.parametrize("source_path", USER_JOURNEY_FILES, ids=USER_JOURNEY_IDS)
def test_user_journey_persona_links_resolve(source_path: Path) -> None:
    text = source_path.read_text(encoding="utf-8")
    failures: list[str] = []
    for match in ACTOR_LINK_RE.finditer(text):
        raw_target = match.group(2).strip()
        parsed = urlparse(unquote(raw_target))
        link_path = parsed.path
        destination = (source_path.parent / link_path).resolve()
        try:
            destination.relative_to(REPO_ROOT.resolve())
        except ValueError:
            line_number = text.count("\n", 0, match.start()) + 1
            failures.append(
                f"{source_path.relative_to(REPO_ROOT)}:{line_number} persona link escapes repo: {raw_target}"
            )
            continue
        if not destination.exists():
            line_number = text.count("\n", 0, match.start()) + 1
            failures.append(
                f"{source_path.relative_to(REPO_ROOT)}:{line_number} missing persona file: {raw_target}"
            )

    assert not failures, "\n".join(failures)
