"""Guard resolver-first profile-loading guidance under canonical doctrine."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCTRINE_ROOT = _REPO_ROOT / "src" / "doctrine"
# Built-in doctrine pack content (agent profiles, styleguides, procedures, ...)
# relocated out of ``src/doctrine`` into the flattened ``packs/built-in`` pack
# root (relocate-builtin-doctrine-packs). Profile-load guidance now lives across
# both trees, so the real-tree scans below cover the pair to keep the denominator
# whole rather than lowering the floor.
_PACKS_BUILT_IN_ROOT = _REPO_ROOT / "packs" / "built-in"
_SHIPPED_DOCTRINE_ROOTS = (_DOCTRINE_ROOT, _PACKS_BUILT_IN_ROOT)
# Frozen at the live denominator (shrink-only ratchet, charter standing order 5).
# A floor materially below the live count lets the scanned surface silently
# shrink while the guard still reports green. Raise this in lockstep when new
# profile-load guidance lands; lower it ONLY alongside a deliberate, reviewed
# doctrine relocation that explains where the guidance went.
_GUIDANCE_FILE_FLOOR = 18
_TEXT_SUFFIXES = frozenset({".md", ".yaml", ".yml"})
_GUIDANCE_MARKERS = (
    "profile-loaded",
    "profile load",
    "load agent profile",
    "load the agent profile",
    "agent profile show",
    "agent_profiles/built-in/",
    ".agent.yaml",
)
_RAW_PROFILE_PATH = re.compile(
    r"(?:src/doctrine/)?agent_profiles/[^\s`\"']+\.agent\.yaml",
    re.IGNORECASE,
)
_RAW_PROFILE_DIRECTORY = re.compile(
    r"(?:src/doctrine/)?agent_profiles/(?:built-in/)?",
    re.IGNORECASE,
)
_RAW_READ_INSTRUCTION = re.compile(
    r"\b(?:first\s+)?(?:read|reads|open|opens|load|loads|inspect|inspects)\b"
    r"(?:(?!\n\s*\n).){0,240}"
    r"(?:agent_profiles/[^\s`\"']+\.agent\.yaml|\.agent\.yaml)",
    re.IGNORECASE | re.DOTALL,
)
_RAW_DIRECTORY_LOOKUP = re.compile(
    r"\b(?:look\s+for|search|searches|browse|browses|inspect|inspects)\b"
    r"(?:(?!\n\s*\n).){0,240}"
    r"(?:src/doctrine/)?agent_profiles/(?:built-in/)?",
    re.IGNORECASE | re.DOTALL,
)
_FALLBACK_SCOPE_MARKERS = ("read-only", "cannot invoke the cli")
_DIVERGENCE_MARKERS = ("diverge", "overlays", "lineage", "overrides")


def _doctrine_text_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES
    )


def _profile_guidance_files(root: Path) -> list[Path]:
    matches: list[Path] = []
    for path in _doctrine_text_files(root):
        text = path.read_text(encoding="utf-8").lower()
        if any(marker in text for marker in _GUIDANCE_MARKERS):
            matches.append(path)
    return matches


def _is_bounded_read_only_fallback(paragraph: str) -> bool:
    lowered = paragraph.lower()
    return all(marker in lowered for marker in _FALLBACK_SCOPE_MARKERS) and all(
        marker in lowered for marker in _DIVERGENCE_MARKERS
    )


def _raw_profile_instruction_offenders(root: Path) -> list[Path]:
    offenders: list[Path] = []
    for path in _doctrine_text_files(root):
        text = path.read_text(encoding="utf-8")
        for paragraph in re.split(r"\n\s*\n", text):
            file_lookup = bool(
                _RAW_PROFILE_PATH.search(paragraph)
                and _RAW_READ_INSTRUCTION.search(paragraph)
            )
            directory_lookup = bool(
                _RAW_PROFILE_DIRECTORY.search(paragraph)
                and _RAW_DIRECTORY_LOOKUP.search(paragraph)
            )
            if not file_lookup and not directory_lookup:
                continue
            if not _is_bounded_read_only_fallback(paragraph):
                offenders.append(path)
                break
    return offenders


def test_profile_guidance_scan_has_concrete_denominator() -> None:
    guidance_files = [
        path for root in _SHIPPED_DOCTRINE_ROOTS for path in _profile_guidance_files(root)
    ]

    assert len(guidance_files) >= _GUIDANCE_FILE_FLOOR, (
        "Profile-load guidance scan fell below its concrete file floor; "
        "review the markers or doctrine relocation before weakening the guard. "
        f"Found {len(guidance_files)} file(s):\n"
        + "\n".join(str(path.relative_to(_REPO_ROOT)) for path in guidance_files)
    )


def test_raw_profile_reads_are_not_primary_guidance() -> None:
    offenders = [
        path
        for root in _SHIPPED_DOCTRINE_ROOTS
        for path in _raw_profile_instruction_offenders(root)
    ]

    assert not offenders, (
        "Raw .agent.yaml profile reads must not be primary guidance. Use "
        "`spec-kitty agent profile show <profile-id>`; retain a raw read only "
        "for a CLI-less read-only harness with the resolution-divergence caveat:\n"
        + "\n".join(str(path.relative_to(_REPO_ROOT)) for path in offenders)
    )


def test_guard_rejects_a_planted_primary_raw_read_and_names_its_path(
    tmp_path: Path,
) -> None:
    doctrine_root = tmp_path / "src" / "doctrine"
    poison = doctrine_root / "skills" / "poison" / "SKILL.md"
    poison.parent.mkdir(parents=True)
    poison.write_text(
        "FIRST read "
        "`src/doctrine/agent_profiles/built-in/reviewer.agent.yaml` "
        "and adopt its directives.\n",
        encoding="utf-8",
    )

    assert _raw_profile_instruction_offenders(doctrine_root) == [poison]


def test_guard_rejects_exact_raw_directory_lookup_wording(tmp_path: Path) -> None:
    doctrine_root = tmp_path / "src" / "doctrine"
    poison = doctrine_root / "missions" / "tasks" / "prompt.md"
    poison.parent.mkdir(parents=True)
    poison.write_text(
        "If this command is unavailable, look for profiles under "
        "`src/doctrine/agent_profiles/built-in/`.\n",
        encoding="utf-8",
    )

    assert _raw_profile_instruction_offenders(doctrine_root) == [poison]


def test_guard_allows_only_the_caveated_read_only_fallback(tmp_path: Path) -> None:
    doctrine_root = tmp_path / "src" / "doctrine"
    fallback = doctrine_root / "skills" / "fallback" / "SKILL.md"
    fallback.parent.mkdir(parents=True)
    fallback.write_text(
        "Only a read-only harness that cannot invoke the CLI may read "
        "`src/doctrine/agent_profiles/built-in/reviewer.agent.yaml`. "
        "This can diverge because overlays, lineage, and overrides are not applied.\n",
        encoding="utf-8",
    )

    assert _raw_profile_instruction_offenders(doctrine_root) == []


def test_guard_allows_caveated_read_only_directory_fallback(tmp_path: Path) -> None:
    doctrine_root = tmp_path / "src" / "doctrine"
    fallback = doctrine_root / "missions" / "tasks" / "prompt.md"
    fallback.parent.mkdir(parents=True)
    fallback.write_text(
        "Only a read-only harness that cannot invoke the CLI may inspect profiles under "
        "`src/doctrine/agent_profiles/built-in/`. This can diverge because overlays, "
        "lineage, and overrides are not applied.\n",
        encoding="utf-8",
    )

    assert _raw_profile_instruction_offenders(doctrine_root) == []
