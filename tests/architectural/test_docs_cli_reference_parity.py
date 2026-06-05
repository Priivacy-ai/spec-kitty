"""Architectural parity test: live Typer surface vs CLI reference docs.

Asserts the set of non-hidden command paths discovered by the
``scripts.docs._typer_walker`` matches exactly the set named in
``docs/reference/cli-commands.md`` and ``docs/reference/agent-subcommands.md``.

If the reference files are not yet present (e.g., a branch where WP07
hasn't run), the test :func:`pytest.skip` s with an explicit reason so
the architectural gate stays green during the documentation refresh.

Mirrors the discovery pattern in
``tests/architectural/test_safety_registry_completeness.py``.

The :func:`test_skill_docs_profile_subcommands_are_registered` guard (FR-018)
additionally scans shipped skill docs for ``spec-kitty agent profile <sub>``
tokens and asserts every ``<sub>`` is a registered command on the ``profile``
Typer app. This locks the ``ad-hoc-profile-load`` skill against re-introducing
references to non-existent profile subcommands (FR-017).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

# CRITICAL: env flags MUST be set before importing specify_cli so that
# the tracker / issue-search subtree is registered.
os.environ.setdefault("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
os.environ.setdefault("SPEC_KITTY_NO_UPGRADE_CHECK", "1")

# Ensure scripts/docs is importable (matches tests/docs/conftest.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs._typer_walker import walk  # noqa: E402
from scripts.docs.check_cli_reference_freshness import (  # noqa: E402
    extract_referenced_paths,
)

pytestmark = [pytest.mark.architectural]


REFERENCE_PATH = _REPO_ROOT / "docs" / "reference" / "cli-commands.md"
AGENT_REFERENCE_PATH = _REPO_ROOT / "docs" / "reference" / "agent-subcommands.md"


def _build_live_app() -> object:
    """Mirror the discovery pattern used by ``test_safety_registry_completeness``."""
    from specify_cli import app
    from specify_cli.cli.commands import register_commands

    saved = sys.argv[:]
    sys.argv = ["spec-kitty", "--help"]
    try:
        register_commands(app)
    finally:
        sys.argv = saved
    return app


# Sentinel marker emitted by ``scripts/docs/build_cli_reference.py``.
# A reference file that does not carry this marker has not yet been
# rebuilt by WP07's generator pass; the parity assertion is meaningless
# in that case, so we skip with an explicit reason.
_WP07_GENERATOR_MARKER = "<!-- BEGIN GENERATED -->"


def _read_or_skip(path: Path, *, wp_label: str) -> str:
    if not path.exists():
        pytest.skip(
            f"{wp_label} not yet run: {path} is missing. "
            "Re-run after the rebuilt CLI reference lands."
        )
    text = path.read_text(encoding="utf-8")
    if _WP07_GENERATOR_MARKER not in text:
        pytest.skip(
            f"{wp_label} not yet run: {path} does not carry the generator "
            "marker. Re-run after the rebuilt CLI reference lands."
        )
    return text


@pytest.fixture(scope="module")
def reference_text() -> str:
    return _read_or_skip(REFERENCE_PATH, wp_label="WP07")


@pytest.fixture(scope="module")
def agent_reference_text() -> str:
    return _read_or_skip(AGENT_REFERENCE_PATH, wp_label="WP07")


def test_visible_paths_match_reference(
    reference_text: str, agent_reference_text: str
) -> None:
    """Every visible (non-hidden) command path must appear in one of the references."""
    app = _build_live_app()
    entries = walk(app)
    live_visible = {e.path for e in entries if not e.hidden}

    main_paths = set(extract_referenced_paths(reference_text).keys())
    agent_paths = set(extract_referenced_paths(agent_reference_text).keys())
    referenced = main_paths | agent_paths

    missing = live_visible - referenced
    extra = referenced - {e.path for e in entries}

    assert not missing, (
        "Visible command paths missing from the reference docs:\n"
        + "\n".join(f"  - spec-kitty {' '.join(p)}" for p in sorted(missing))
    )
    assert not extra, (
        "Reference docs name command paths that are not in the live tree:\n"
        + "\n".join(f"  - spec-kitty {' '.join(p)}" for p in sorted(extra))
    )


def test_deprecated_paths_classified(reference_text: str, agent_reference_text: str) -> None:
    """Deprecated visible commands must carry a Deprecated banner in the reference."""
    app = _build_live_app()
    entries = walk(app)
    deprecated = [e for e in entries if e.deprecated and not e.hidden]
    if not deprecated:
        pytest.skip("No deprecated visible commands found in the live tree.")

    main_paths = extract_referenced_paths(reference_text)
    agent_paths = extract_referenced_paths(agent_reference_text)
    combined = {**main_paths, **agent_paths}

    unclassified = [
        e.path
        for e in deprecated
        if combined.get(e.path)
        and not combined[e.path].get("classified_deprecated")
    ]
    assert not unclassified, (
        "Deprecated paths missing Deprecated banner in the reference:\n"
        + "\n".join(f"  - spec-kitty {' '.join(p)}" for p in sorted(unclassified))
    )


# ---------------------------------------------------------------------------
# FR-018: skill-doc / CLI parity guard for ``agent profile`` subcommands.
# ---------------------------------------------------------------------------

#: Shipped skill docs that name ``spec-kitty agent profile <sub>`` commands.
#: At minimum the ad-hoc-profile-load SKILL.md (the source template — generated
#: agent copies under ``.claude/`` etc. propagate from it on upgrade, so they
#: are intentionally out of scope here per C-006).
_SKILL_DOCS = (
    _REPO_ROOT / "src" / "doctrine" / "skills" / "ad-hoc-profile-load" / "SKILL.md",
)

#: Match ``spec-kitty agent profile <sub>`` where ``<sub>`` is a command token
#: (lower-case word, optionally hyphenated). The ``spec-kitty`` prefix anchors
#: the match to genuine command invocations, so prose like "load an agent
#: profile on demand" (which lacks the prefix) is never captured.
_PROFILE_CMD_RE = re.compile(
    r"spec-kitty\s+agent\s+profile\s+([a-z][a-z-]*)(?=\s|$|`)"
)


def _registered_profile_commands() -> set[str]:
    """Return the set of command names registered on the ``profile`` Typer app."""
    from specify_cli.cli.commands import profiles_cmd

    return {
        cmd.name
        for cmd in profiles_cmd.app.registered_commands
        if cmd.name is not None
    }


def test_skill_docs_profile_subcommands_are_registered() -> None:
    """Every ``agent profile <sub>`` named in skill docs must be a real command.

    FR-018: fail on any orphan reference to a profile subcommand that is not
    registered on the ``profile`` Typer app. This is the regression lock for
    the FR-017 SKILL.md reconciliation.
    """
    registered = _registered_profile_commands()
    assert registered, "Expected at least one registered profile command."

    orphans: list[tuple[str, str]] = []
    scanned_any = False
    for doc in _SKILL_DOCS:
        if not doc.exists():
            continue
        scanned_any = True
        text = doc.read_text(encoding="utf-8")
        for match in _PROFILE_CMD_RE.finditer(text):
            sub = match.group(1)
            if sub not in registered:
                rel = doc.relative_to(_REPO_ROOT)
                orphans.append((str(rel), sub))

    assert scanned_any, (
        "No skill docs were scanned — expected at least "
        f"{_SKILL_DOCS[0].relative_to(_REPO_ROOT)} to exist."
    )
    assert not orphans, (
        "Skill docs reference 'spec-kitty agent profile <sub>' commands that "
        "are not registered on the profile Typer app "
        f"(registered: {sorted(registered)}):\n"
        + "\n".join(f"  - {doc}: 'agent profile {sub}'" for doc, sub in sorted(orphans))
    )
