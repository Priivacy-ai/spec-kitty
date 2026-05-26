"""Tasks-flow scaffolding helpers.

Public entry points consumed by ``spec-kitty agent mission finalize-tasks``
and related ``/spec-kitty.tasks`` surfaces.
"""

from specify_cli.tasks.issue_matrix import (
    IssueReference,
    detect_issue_references,
    scaffold_issue_matrix,
)

__all__ = [
    "IssueReference",
    "detect_issue_references",
    "scaffold_issue_matrix",
]
