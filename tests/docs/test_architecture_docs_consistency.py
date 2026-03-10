"""Architecture documentation consistency checks."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE_DIR = REPO_ROOT / "architecture"
DOCS_DIR = REPO_ROOT / "docs"
AUDIENCE_DIR = ARCHITECTURE_DIR / "audience"
USER_JOURNEY_DIR = ARCHITECTURE_DIR / "2.x" / "user_journey"

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_architecture_required_directories_exist() -> None:
    required_dirs = [
        ARCHITECTURE_DIR / "1.x",
        ARCHITECTURE_DIR / "1.x" / "adr",
        ARCHITECTURE_DIR / "1.x" / "notes",
        ARCHITECTURE_DIR / "2.x",
        ARCHITECTURE_DIR / "2.x" / "adr",
        ARCHITECTURE_DIR / "2.x" / "user_journey",
        ARCHITECTURE_DIR / "2.x" / "initiatives",
        ARCHITECTURE_DIR / "2.x" / "initiatives" / "2026-02-architecture-discovery-and-restructure",
        ARCHITECTURE_DIR / "2.x" / "initiatives" / "next-mission-mappings",
        ARCHITECTURE_DIR / "2.x" / "01_context",
        ARCHITECTURE_DIR / "2.x" / "02_containers",
        ARCHITECTURE_DIR / "2.x" / "03_components",
        ARCHITECTURE_DIR / "audience",
        ARCHITECTURE_DIR / "audience" / "internal",
        ARCHITECTURE_DIR / "audience" / "external",
        ARCHITECTURE_DIR / "glossary",
        ARCHITECTURE_DIR / "adrs",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in required_dirs if not path.is_dir()]
    assert not missing, f"Missing required architecture directories: {missing}"


def test_legacy_adr_aliases_cover_canonical_adr_files() -> None:
    canonical = {}
    for track in ("1.x", "2.x"):
        for adr in sorted((ARCHITECTURE_DIR / track / "adr").glob("*.md")):
            if adr.name == "README.md":
                continue
            canonical[adr.name] = adr.resolve()

    assert canonical, "No canonical ADR files found under architecture/1.x/adr or architecture/2.x/adr"

    legacy_dir = ARCHITECTURE_DIR / "adrs"
    for filename, canonical_target in canonical.items():
        legacy = legacy_dir / filename
        assert legacy.exists(), f"Missing legacy ADR alias: {legacy.relative_to(REPO_ROOT)}"
        assert legacy.is_symlink(), f"Legacy ADR alias must be a symlink: {legacy.relative_to(REPO_ROOT)}"
        assert legacy.resolve() == canonical_target, (
            f"Legacy ADR alias points to wrong target: {legacy.relative_to(REPO_ROOT)}"
        )


def test_key_docs_use_versioned_adr_paths() -> None:
    key_docs = [
        DOCS_DIR / "2x" / "runtime-and-missions.md",
        DOCS_DIR / "2x" / "adr-coverage.md",
        DOCS_DIR / "how-to" / "manage-agents.md",
        DOCS_DIR / "how-to" / "upgrade-to-0-12-0.md",
        DOCS_DIR / "reference" / "configuration.md",
        ARCHITECTURE_DIR / "README.md",
        ARCHITECTURE_DIR / "ARCHITECTURE_DOCS_GUIDE.md",
        ARCHITECTURE_DIR / "NAVIGATION_GUIDE.md",
    ]

    stale_references: list[str] = []
    for doc in key_docs:
        text = doc.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if "architecture/adrs/" in line and "compatibility" not in line.lower():
                stale_references.append(f"{doc.relative_to(REPO_ROOT)}:{line_no}: {line.strip()}")

    assert not stale_references, "Found stale direct architecture/adrs references in key docs:\n" + "\n".join(
        stale_references
    )


def test_deprecated_docs_architecture_locations_removed() -> None:
    deprecated_dirs = [
        REPO_ROOT / "docs" / "architecture",
        REPO_ROOT / "docs" / "development" / "tracking",
    ]
    still_present = [str(path.relative_to(REPO_ROOT)) for path in deprecated_dirs if path.exists()]
    assert not still_present, "Deprecated documentation directories should be removed after migration: " + ", ".join(
        still_present
    )


def _iter_actor_persona_cells(path: Path) -> list[tuple[str, int]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    actor_rows: list[tuple[str, int]] = []
    in_actor_table = False

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("|"):
            header_cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if (
                len(header_cells) >= 5
                and header_cells[0] == "#"
                and header_cells[1].lower().startswith("actor")
                and header_cells[2].lower().startswith("type")
                and header_cells[3].lower().startswith("persona")
            ):
                in_actor_table = True
                continue

        if in_actor_table:
            if not stripped.startswith("|"):
                in_actor_table = False
                continue

            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) < 5:
                continue

            if set(cells[0]) <= {"-"}:
                continue

            if not cells[0].isdigit():
                continue

            actor_rows.append((cells[3], line_no))

    return actor_rows


def test_user_journey_actor_personas_link_to_audience_docs() -> None:
    journey_files = [
        path for path in sorted(USER_JOURNEY_DIR.glob("*.md")) if path.name not in {"README.md", "evaluation.md"}
    ]

    assert journey_files, "No canonical user journey files found for persona-link validation"

    failures: list[str] = []
    for journey in journey_files:
        actor_personas = _iter_actor_persona_cells(journey)
        if not actor_personas:
            failures.append(f"{journey.relative_to(REPO_ROOT)} has no actor persona rows in the expected actor table")
            continue

        for persona_cell, line_no in actor_personas:
            match = MARKDOWN_LINK_RE.fullmatch(persona_cell)
            if not match:
                failures.append(
                    f"{journey.relative_to(REPO_ROOT)}:{line_no} persona cell must be a markdown link to audience doc: {persona_cell}"  # noqa: E501
                )
                continue

            target = match.group(1).strip().strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "tel:")):
                failures.append(f"{journey.relative_to(REPO_ROOT)}:{line_no} persona link must be local: {target}")
                continue

            parsed = urlparse(unquote(target))
            link_path = parsed.path
            if not link_path:
                failures.append(f"{journey.relative_to(REPO_ROOT)}:{line_no} persona link missing path: {target}")
                continue

            destination = (journey.parent / link_path).resolve()
            if not destination.exists() or not destination.is_file():
                failures.append(f"{journey.relative_to(REPO_ROOT)}:{line_no} persona target missing: {target}")
                continue

            try:
                destination.relative_to(AUDIENCE_DIR.resolve())
            except ValueError:
                failures.append(
                    f"{journey.relative_to(REPO_ROOT)}:{line_no} persona link must target architecture/audience/: {target}"  # noqa: E501
                )

    assert not failures, "\n".join(failures)
