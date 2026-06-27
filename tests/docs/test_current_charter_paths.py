"""Current docs must not publish legacy charter paths as active layout."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


CURRENT_DOC_PATHS = (
    Path("docs/3x"),
    Path("docs/how-to"),
    Path("docs/reference"),
    Path("spec-driven.md"),
)


def test_current_docs_do_not_publish_memory_charter_path() -> None:
    offenders: list[str] = []
    for root in CURRENT_DOC_PATHS:
        paths = [root] if root.is_file() else sorted(root.rglob("*.md"))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if ".kittify/memory/charter.md" in text or "memory/charter.md" in text:
                offenders.append(str(path))

    assert offenders == []
