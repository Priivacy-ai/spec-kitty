"""Workflow sequence schema (FR-012).

Pydantic v2 models for the workflow YAML artifact.  Every ``.workflow.yaml``
file under ``src/doctrine/workflows/`` MUST validate against ``WorkflowSequence``.

Layer rule (C-001 / NFR-003): this module lives inside the runtime package
(``specify_cli.next._internal_runtime``).  It MUST NOT import from ``charter``,
``doctrine`` (Python modules), or ``kernel``.  Doctrine YAML files are loaded
as data by ``workflow_registry``; they are not imported as Python modules.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["WorkflowSequence", "ActionStep"]


class ActionStep(BaseModel):
    """A single step in a workflow sequence (FR-012, data-model §6)."""

    model_config = ConfigDict(extra="forbid")

    action_name: str
    next: list[str] = Field(default_factory=list)
    description: str
    terminal: bool = False

    @model_validator(mode="after")
    def _validate_terminal_has_no_next(self) -> ActionStep:
        if self.terminal and self.next:
            raise ValueError(
                f"action {self.action_name!r}: terminal=True forbids non-empty `next`"
            )
        return self


class WorkflowSequence(BaseModel):
    """A composable mission workflow (FR-012, data-model §5).

    Invariants enforced at validation time:
    * ``action_name`` values are unique within the workflow.
    * ``initial`` names an action that exists in ``actions``.
    * Every ``next`` reference names an action that exists in ``actions``.
    * The action graph is acyclic (DAG check from ``initial``).
    """

    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    description: str
    actions: list[ActionStep]
    initial: str
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_invariants(self) -> WorkflowSequence:
        names = [a.action_name for a in self.actions]
        if len(names) != len(set(names)):
            raise ValueError("action_name values must be unique within a workflow")
        if self.initial not in names:
            raise ValueError(f"initial={self.initial!r} not in actions")
        # All `next` references must resolve.
        names_set = set(names)
        for a in self.actions:
            for n in a.next:
                if n not in names_set:
                    raise ValueError(
                        f"action {a.action_name!r} references unknown next: {n!r}"
                    )
        # DAG check: BFS/DFS from initial; ensure no cycle.
        _check_acyclic(self.actions, self.initial)
        return self


def _check_acyclic(actions: list[ActionStep], start: str) -> None:
    """Raise ``ValueError`` if the action graph contains a cycle.

    Uses an iterative DFS with a ``visiting`` (grey) set and a ``visited``
    (black) set so it works on workflows with unreachable nodes too.
    """
    by_name = {a.action_name: a for a in actions}
    visiting: set[str] = set()
    visited: set[str] = set()

    def _dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise ValueError(f"cycle detected at action {node!r}")
        visiting.add(node)
        for n in by_name[node].next:
            _dfs(n)
        visiting.discard(node)
        visited.add(node)

    _dfs(start)
