"""Workflow registry (FR-012, FR-015).

Loads ``.workflow.yaml`` files from ``src/doctrine/workflows/`` and returns
validated ``WorkflowSequence`` instances.

Search precedence
-----------------
1. ``src/doctrine/workflows/<workflow_id>.workflow.yaml`` (shipped defaults)
2. ``src/doctrine/workflows/_fixtures/<workflow_id>.workflow.yaml`` (test fixtures)

Operator override at ``.kittify/workflows/<workflow_id>.workflow.yaml`` is
reserved for a future extension (not load-bearing this mission).

Layer rule (C-001 / NFR-003)
-----------------------------
This module lives inside the runtime package
(``specify_cli.next._internal_runtime``).  It MUST NOT import from ``charter``,
``doctrine`` (Python modules), or ``kernel``.  Doctrine YAML files are loaded
as raw data from disk; they are not imported as Python modules.

FR-015 — no silent fallback
----------------------------
If *workflow_id* does not match any file in the search roots,
``UnknownWorkflowError`` is raised with a message that names the unknown id
AND lists all currently available workflows.  Callers MUST NOT silently
fall back to ``software-dev-default``; fall-back logic belongs in the
caller (currently WP11's ``planner.plan_next``).
"""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

from .workflow_schema import WorkflowSequence

__all__ = ["get_workflow", "list_available_workflows", "UnknownWorkflowError"]


class UnknownWorkflowError(Exception):
    """Raised when *workflow_id* cannot be resolved to a workflow YAML file.

    FR-015 binding: this exception MUST name the unknown id AND list the
    currently available workflow ids.  The caller MUST NOT silently fall back
    to ``software-dev-default``.
    """


# ---------------------------------------------------------------------------
# Search roots — resolved relative to this file so the registry works both
# in a source-checkout and after installation via pip / uv.
#
# Path(__file__).resolve() is e.g.:
#   <repo>/src/specify_cli/next/_internal_runtime/workflow_registry.py
# parents[4] is <repo>/  (src/ is parents[0], specify_cli is parents[1],
#   next is parents[2], _internal_runtime is parents[3] — wait, let's count:
#   0: _internal_runtime/
#   1: next/
#   2: specify_cli/
#   3: src/
#   4: <repo root>
# So parents[3] / "src" / "doctrine" / "workflows" is the canonical root.
# ---------------------------------------------------------------------------
_RUNTIME_FILE = Path(__file__).resolve()
_SRC_ROOT = _RUNTIME_FILE.parents[3]  # …/src/
_WORKFLOWS_ROOT = _SRC_ROOT / "doctrine" / "workflows"

_SEARCH_ROOTS: tuple[Path, ...] = (
    _WORKFLOWS_ROOT,
    _WORKFLOWS_ROOT / "_fixtures",
)


@functools.cache
def get_workflow(workflow_id: str) -> WorkflowSequence:
    """Return the validated ``WorkflowSequence`` for *workflow_id*.

    Search order: shipped defaults first, then test fixtures (see module
    docstring for the full precedence list).

    Raises
    ------
    UnknownWorkflowError
        If *workflow_id* cannot be resolved to any file in the search roots.
        The exception message names the unknown id and lists available ids
        (FR-015 binding).
    pydantic.ValidationError
        If the resolved YAML file fails ``WorkflowSequence`` validation.
    """
    for root in _SEARCH_ROOTS:
        candidate = root / f"{workflow_id}.workflow.yaml"
        if candidate.exists():
            raw = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            return WorkflowSequence.model_validate(raw)

    available = list_available_workflows()
    raise UnknownWorkflowError(
        f"Unknown workflow_id={workflow_id!r}. "
        f"Available: {available}. "
        f"Searched: {[str(r) for r in _SEARCH_ROOTS]}."
    )


def list_available_workflows() -> list[str]:
    """Return a sorted list of workflow ids resolvable from the search roots."""
    available: list[str] = []
    for root in _SEARCH_ROOTS:
        if root.exists():
            for p in sorted(root.glob("*.workflow.yaml")):
                # p.stem is e.g. "software-dev-default.workflow"
                workflow_id = p.stem.replace(".workflow", "")
                available.append(workflow_id)
    return sorted(set(available))
