"""Static wiring assertion: ``sonar.projectVersion`` is derived, not hardcoded.

WP01 / SC-001a. The ``sonarcloud`` job in ``.github/workflows/ci-quality.yml``
is gated to ``schedule`` / ``workflow_dispatch`` only — it runs on NEITHER
``pull_request`` NOR ``push`` — so the wiring cannot be observed in a PR or on
merge. It is verified here by a genuine static YAML parse (no network, no live
analysis), red-first against the current unwired tree.

The assertions tie the wiring to the extraction module end to end:

1. exactly one step in the ``sonarcloud`` job invokes
   ``scripts/ci/sonar_project_version.py`` and exports its stdout to
   ``$GITHUB_OUTPUT`` under some output name;
2. ``sonar.projectVersion`` is consumed (in the materialize step's ``run`` or
   the scanner-action ``args``) as a ``${{ steps.<id>.outputs.<name> }}``
   expression whose ``<id>`` is that extraction step and whose ``<name>`` is the
   output it exports;
3. ``sonar.projectVersion`` is never assigned a hardcoded literal version.

A behaviour-preserving YAML reorder / step rename never reds this (it resolves
the extraction step by the script it runs, not by a fixed id).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-quality.yml"
_SCRIPT_REL = "scripts/ci/sonar_project_version.py"

_PROJECT_VERSION_EXPR = re.compile(
    r"sonar\.projectVersion=\$\{\{\s*steps\.([\w-]+)\.outputs\.([\w-]+)\s*\}\}"
)
# A hardcoded literal: ``sonar.projectVersion=`` immediately followed by a digit
# (e.g. ``sonar.projectVersion=3.2.5``) — the anti-pattern FR-002 forbids.
_PROJECT_VERSION_LITERAL = re.compile(r"sonar\.projectVersion=\d")


def _sonarcloud_steps() -> list[dict[str, Any]]:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    assert "sonarcloud" in jobs, "ci-quality.yml has no 'sonarcloud' job"
    steps = jobs["sonarcloud"]["steps"]
    assert isinstance(steps, list) and steps
    return steps


def _step_run(step: dict[str, Any]) -> str:
    run = step.get("run", "")
    return run if isinstance(run, str) else ""


def _step_args(step: dict[str, Any]) -> str:
    with_block = step.get("with")
    if not isinstance(with_block, dict):
        return ""
    args = with_block.get("args", "")
    return args if isinstance(args, str) else ""


def _consuming_text(steps: list[dict[str, Any]]) -> str:
    """All places projectVersion could be wired: every ``run`` + every ``args``."""
    return "\n".join(_step_run(s) + "\n" + _step_args(s) for s in steps)


def _extraction_step(steps: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [s for s in steps if _SCRIPT_REL in _step_run(s)]
    assert len(matches) == 1, (
        f"expected exactly one sonarcloud step to invoke {_SCRIPT_REL}, found {len(matches)}"
    )
    return matches[0]


def test_extraction_script_is_invoked_and_exported() -> None:
    steps = _sonarcloud_steps()
    step = _extraction_step(steps)
    assert step.get("id"), "the extraction step must have an 'id' so its output is referenceable"
    assert "GITHUB_OUTPUT" in _step_run(step), (
        "the extraction step must export the derived version to $GITHUB_OUTPUT"
    )


def test_projectversion_wired_via_extraction_step_output() -> None:
    steps = _sonarcloud_steps()
    extraction = _extraction_step(steps)
    match = _PROJECT_VERSION_EXPR.search(_consuming_text(steps))
    assert match is not None, (
        "sonar.projectVersion must be wired as ${{ steps.<id>.outputs.<name> }}"
    )
    referenced_step_id, referenced_output = match.group(1), match.group(2)
    assert referenced_step_id == extraction["id"], (
        "sonar.projectVersion must reference the extraction step's output, "
        f"got steps.{referenced_step_id} but the script runs in steps.{extraction['id']}"
    )
    assert f"{referenced_output}=" in _step_run(extraction), (
        f"the extraction step must export the '{referenced_output}' output "
        "that sonar.projectVersion consumes"
    )


def test_projectversion_is_not_hardcoded() -> None:
    steps = _sonarcloud_steps()
    literal = _PROJECT_VERSION_LITERAL.search(_consuming_text(steps))
    assert literal is None, (
        "sonar.projectVersion must be single-sourced from pyproject.toml via the "
        f"extraction script, not a hardcoded literal ({literal.group(0) if literal else ''})"
    )
