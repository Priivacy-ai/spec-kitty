"""Live-wiring integration test for mission-type governance profiles.

This is the FR-011 / journey-4 contract gate for WP08 cycle 2.  The cycle-1
ATDD spec at ``tests/missions/test_mission_type_profile_resolution.py``
exercised ``charter.mission_type_profiles.resolve_mission_type_governance``
in isolation, which proved the loader/resolver was *correct in a sandbox*
but did NOT prove a real documentation mission flowing through the
implement-prompt pipeline avoids the ``software-dev-default`` leak.

That gap is what this test closes.  It stages a fixture mission whose
``meta.json`` declares ``mission_type: documentation`` (no
project-level ``selected_*`` overrides) and invokes the production
prompt-build entry point — :func:`specify_cli.next.prompt_builder._build_wp_prompt` —
with ``action="implement"``.  The resulting prompt text MUST NOT contain
``software-dev-default``, proving the mission-type resolver fires inline
during prompt assembly rather than the implementer-agent silently
inheriting software-dev governance.

If a future refactor strips the
``resolve_mission_type_governance(repo_root, feature_dir)`` call from
``_build_wp_prompt``, this test goes red and pins the regression
immediately.

See:
* ``kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/tasks/WP08-mission-type-profiles.md``
  → T046 ("Wire resolve_governance into the mission-context pipeline").
* ``kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/tasks/WP08-mission-type-profiles/review-cycle-1.md``
  for the rejection rationale that prompted this test.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.next.prompt_builder import _build_wp_prompt
from tests.lane_test_utils import write_single_lane_manifest


pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


_MINIMAL_DOC_CHARTER_MD = """\
# Test Documentation Project Charter

> Version: 1.0.0

## Purpose

A minimal charter used by the WP08 mission-type-profile live-wiring
integration test.  The charter deliberately declares NO
``template_set`` so the resolver MUST source its mission-type defaults
from the documentation governance profile rather than silently falling
back to ``software-dev-default``.

## Technical Standards

Markdown, Sphinx, MkDocs.
"""


_WP_FOR_DOCUMENTATION_MISSION = """\
---
work_package_id: WP01
title: Author tutorial scaffolding
dependencies: []
requirement_refs: [FR-001]
subtasks: [T001]
agent: claude
agent_profile: documentation-dora
role: implementer
authoritative_surface: docs/
owned_files: [docs/index.md]
execution_mode: code_change
history: []
---
# WP01 — Author tutorial scaffolding

Create the initial Divio tutorial scaffolding under ``docs/guides/``.
"""


def _git_init_minimal(repo_root: Path) -> None:
    """Initialise a git repo so charter resolution accepts the project root."""
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "atdd@example.com"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ATDD"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo_root, check=True, capture_output=True)


def _write_minimal_doc_charter(repo_root: Path) -> None:
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text(_MINIMAL_DOC_CHARTER_MD, encoding="utf-8")


@pytest.fixture
def documentation_mission(tmp_path: Path) -> tuple[Path, Path, str]:
    """Stage a documentation mission with meta.json: mission_type=documentation.

    Returns ``(repo_root, feature_dir, mission_slug)``.  The fixture
    intentionally omits any project-level ``selected_*`` overrides so the
    mission-type resolver is the sole authority for documentation
    defaults.
    """
    repo_root = tmp_path
    _git_init_minimal(repo_root)
    mission_slug = "999-documentation-live-wiring"
    feature_dir = repo_root / "kitty-specs" / mission_slug
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "tasks" / "WP01.md").write_text(_WP_FOR_DOCUMENTATION_MISSION, encoding="utf-8")
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))
    _write_minimal_doc_charter(repo_root)

    # The keystone for live wiring: a meta.json with mission_type=documentation.
    # If the prompt builder reads this and routes through the documentation
    # governance profile, no `software-dev-default` content leaks downstream.
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_type": "documentation",
                "mission_slug": mission_slug,
            }
        ),
        encoding="utf-8",
    )

    return repo_root, feature_dir, mission_slug


def test_documentation_mission_wp_prompt_does_not_leak_software_dev_default(
    documentation_mission: tuple[Path, Path, str],
) -> None:
    """The live entry point MUST route a documentation mission through the
    documentation governance profile, not ``software-dev-default``.

    This is the FR-011 / journey-4 contract: if this test fails, the
    implementer-agent for a documentation mission is being given the
    software-dev governance payload (template_set, selected directives,
    selected tactics, etc.), which is the precise drift WP08 was
    chartered to eliminate.  Rejecting cycle-1 of WP08 was about
    closing exactly this gap.
    """
    repo_root, feature_dir, mission_slug = documentation_mission

    prompt = _build_wp_prompt(
        action="implement",
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id="WP01",
        agent="claude",
        repo_root=repo_root,
        mission_type="documentation",
    )

    assert "software-dev-default" not in prompt.lower(), (
        "WP08 FR-011 regression: the implement prompt for a documentation mission "
        "contains `software-dev-default`. The mission-type resolver is either not "
        "wired into prompt_builder._build_wp_prompt or is being overridden by a "
        "downstream fallback. See "
        "kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/tasks/"
        "WP08-mission-type-profiles/review-cycle-1.md for the live-wiring "
        "contract.\n\n"
        "Prompt excerpt (first 800 chars):\n"
        f"{prompt[:800]}"
    )


def test_documentation_mission_wp_prompt_declares_mission_type_profile_header(
    documentation_mission: tuple[Path, Path, str],
) -> None:
    """The mission-type profile MUST be visibly rendered in the prompt.

    Beyond proving the negative (no software-dev leak), we also pin the
    positive contract: the rendered ``Mission-Type Governance Profile:
    documentation`` header MUST appear in the prompt text.  Without
    this, a future refactor could silently drop the call but pass the
    negative assertion by coincidence (e.g. the project charter happens
    to declare a different template_set).
    """
    repo_root, feature_dir, mission_slug = documentation_mission

    prompt = _build_wp_prompt(
        action="implement",
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id="WP01",
        agent="claude",
        repo_root=repo_root,
        mission_type="documentation",
    )

    assert "Mission-Type Governance Profile: documentation" in prompt, (
        "WP08 wiring regression: the mission-type resolver's rendered payload "
        "(``Mission-Type Governance Profile: documentation``) is NOT present "
        "in the implement WP prompt. The call to "
        "``resolve_mission_type_governance(repo_root, feature_dir)`` in "
        "``_build_wp_prompt`` has been removed or short-circuited. "
        "See WP08 review-cycle-1.md.\n\n"
        "Prompt excerpt (first 800 chars):\n"
        f"{prompt[:800]}"
    )
