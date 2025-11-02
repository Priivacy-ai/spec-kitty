#!/usr/bin/env python3
"""Extract changelog section for a specific version.

Used by the GitHub Actions release workflow to populate the release notes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


CHANGELOG_HEADING_RE = re.compile(
    r"^##\s*(?:\[\s*)?(?P<version>\d+\.\d+\.\d+)(?:\s*\]|)(?:\s*-.*)?$"
)


def extract_changelog_section(changelog_text: str, version: str) -> str:
    """Extract the changelog section for the given version.

    Args:
        changelog_text: Full changelog content
        version: Version to extract (e.g., "0.2.3")

    Returns:
        The changelog section for the version, or a default message if not found.
    """
    lines = changelog_text.splitlines()
    capture = False
    content: list[str] = []

    for line in lines:
        heading = CHANGELOG_HEADING_RE.match(line)
        if heading:
            if capture:
                # We've hit the next version heading, stop capturing
                break
            # Check if this is the version we're looking for
            capture = heading.group("version") == version
            continue

        if capture:
            content.append(line)

    if not content:
        return f"Release {version}\n\nNo changelog entry found for this version."

    # Remove leading and trailing empty lines
    while content and not content[0].strip():
        content.pop(0)
    while content and not content[-1].strip():
        content.pop()

    return "\n".join(content)


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} VERSION", file=sys.stderr)
        print("Example: extract_changelog.py 0.2.3", file=sys.stderr)
        return 1

    version = sys.argv[1]
    changelog_path = Path("CHANGELOG.md")

    if not changelog_path.exists():
        print(f"Error: CHANGELOG.md not found at {changelog_path}", file=sys.stderr)
        return 1

    changelog_text = changelog_path.read_text(encoding="utf-8")
    section = extract_changelog_section(changelog_text, version)
    print(section)

    return 0


if __name__ == "__main__":
    sys.exit(main())
