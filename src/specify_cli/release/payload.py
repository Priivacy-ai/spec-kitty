"""Release-prep payload assembler for spec-kitty.

Reads pyproject.toml (current version), git tags (previous tag), and
kitty-specs/ artifacts (missions included in this release window).
Zero network calls (FR-014, C-002).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .changelog import build_changelog_block
from .version import ReleaseChannel, propose_version

# Kept as Literal for JSON serialization compatibility
_ChannelLiteral = Literal["alpha", "beta", "stable"]


@dataclass(frozen=True)
class ReleasePrepPayload:
    """Full release-prep payload produced by ``build_release_prep_payload``.

    Fields:
        channel: The release channel used to compute the version bump.
        current_version: Version string from ``pyproject.toml``.
        proposed_version: Next version string computed from channel rules.
        changelog_block: Multi-line markdown ready to paste into CHANGELOG.md.
        mission_slug_list: Slugs of missions included in this release window.
        target_branch: Branch being released into (always ``"main"`` for
            spec-kitty core).
        structured_inputs: Name->value pairs for the release tag/PR workflow.
            Keys: version, tag_name, release_title, release_notes_body,
            mission_slug_list (comma-separated).

    Automated by ``spec-kitty agent release prep``:
        - Changelog draft (via ``build_changelog_block``)
        - Version bump proposal (via ``propose_version``)
        - Structured release-prep payload (``structured_inputs``)
        - JSON output mode for downstream automation

    Still manual (FR-023 scope cut):
        - PR creation: ``gh pr create --title "..." --body "<changelog_block>"``
        - Tag push: ``git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z``
        - Release workflow monitoring: ``gh run watch``
    """

    channel: _ChannelLiteral
    current_version: str
    proposed_version: str
    changelog_block: str
    mission_slug_list: list[str]
    target_branch: str
    structured_inputs: dict[str, str]


def _read_current_version(repo_root: Path) -> str:
    """Read ``version`` from ``pyproject.toml`` using stdlib ``tomllib``.

    Raises:
        FileNotFoundError: if ``pyproject.toml`` does not exist.
        KeyError: if the ``[project]`` table or ``version`` key is absent.
    """
    pyproject_path = repo_root / "pyproject.toml"
    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise TypeError(f"Expected version to be a string, got {type(version)!r}")
    return version


def build_release_prep_payload(
    channel: ReleaseChannel,
    repo_root: Path,
) -> ReleasePrepPayload:
    """Assemble the full release-prep payload from local artifacts.

    Reads:
      - ``pyproject.toml`` for the current version string.
      - ``kitty-specs/`` for missions accepted since the previous git tag.
      - Local git for the previous ``v*`` tag (no network access).

    Returns:
        A fully-populated :class:`ReleasePrepPayload` ready to render or
        serialize.

    Performance:
        <= 5 seconds wall-clock on a mission with up to 16 WPs (NFR-004).
        The implementation makes at most one ``git`` subprocess call for tag
        resolution, then reads filesystem only.

    No network calls are made (FR-014, C-002). Raises :class:`ValueError` if
    the current version cannot be parsed for the requested channel.
    """
    current_version = _read_current_version(repo_root)
    proposed_version = propose_version(current_version, channel)

    changelog_block, mission_slug_list = build_changelog_block(repo_root)

    release_title = f"Release v{proposed_version}"
    tag_name = f"v{proposed_version}"
    mission_slug_csv = ", ".join(mission_slug_list)

    structured_inputs: dict[str, str] = {
        "version": proposed_version,
        "tag_name": tag_name,
        "release_title": release_title,
        "release_notes_body": changelog_block,
        "mission_slug_list": mission_slug_csv,
    }

    return ReleasePrepPayload(
        channel=channel,
        current_version=current_version,
        proposed_version=proposed_version,
        changelog_block=changelog_block,
        mission_slug_list=mission_slug_list,
        target_branch="main",
        structured_inputs=structured_inputs,
    )
