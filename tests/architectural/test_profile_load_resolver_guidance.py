"""Keep shipped profile-loading guidance resolver-first."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHIPPED_ROOTS = (_REPO_ROOT / "src" / "charter" / "offering", _REPO_ROOT / "packs" / "built-in")
_TEXT_SUFFIXES = frozenset({".md", ".yaml", ".yml"})
_GUIDANCE_MARKERS = ("profile load", "profile-loaded", "agent profile show", ".agent.yaml")
_RAW_READ = re.compile(
    r"\b(?:read|open|load|inspect|search|browse|look\s+for)\b"
    r"(?:(?!\n\s*\n).){0,240}(?:\.agent\.yaml|agent_profiles/)",
    re.IGNORECASE | re.DOTALL,
)
_FALLBACK_TERMS = ("read-only", "cannot invoke the cli", "diverge", "overlays", "lineage", "overrides")


def _guidance_and_offenders(roots: tuple[Path, ...]) -> tuple[list[Path], list[Path]]:
    guidance: list[Path] = []
    offenders: list[Path] = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8")
            if any(marker in text.lower() for marker in _GUIDANCE_MARKERS):
                guidance.append(path)
            for paragraph in re.split(r"\n\s*\n", text):
                if not _RAW_READ.search(paragraph):
                    continue
                lowered = paragraph.lower()
                if not all(term in lowered for term in _FALLBACK_TERMS):
                    offenders.append(path)
                    break
    return guidance, offenders


def test_profile_guidance_is_resolver_first_with_one_bounded_fallback(
    tmp_path: Path,
) -> None:
    live_guidance, live_offenders = _guidance_and_offenders(_SHIPPED_ROOTS)
    assert live_guidance
    assert live_offenders == []

    root = tmp_path / "doctrine"
    poison = root / "poison.md"
    fallback = root / "fallback.md"
    root.mkdir()
    poison.write_text(
        "First read `packs/built-in/agent_profiles/reviewer.agent.yaml`.\n",
        encoding="utf-8",
    )
    fallback.write_text(
        "Only a read-only harness that cannot invoke the CLI may inspect "
        "`packs/built-in/agent_profiles/reviewer.agent.yaml`. This can diverge because "
        "overlays, lineage, and overrides are not applied.\n",
        encoding="utf-8",
    )

    planted_guidance, planted_offenders = _guidance_and_offenders((root,))
    assert planted_guidance == [fallback, poison]
    assert planted_offenders == [poison]
