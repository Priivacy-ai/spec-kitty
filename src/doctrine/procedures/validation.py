"""YAML schema validation utilities for procedures.

Introduced in WP03 of the
``excise-doctrine-curation-and-inline-references-01KP54J6`` mission. Unlike
the other per-kind validators, procedures require BOTH a top-level scan AND
a step-level scan for forbidden inline-reference fields (FR-008). Without
the step-level scan, step-level ``tactic_refs`` would fall through to
Pydantic's generic ``extra_forbidden`` error after WP02 removed
``ProcedureStep.tactic_refs`` -- a valid rejection, but without the
structured migration hint the spec requires.
"""

from __future__ import annotations

from typing import Any

from doctrine.shared.errors import (
    reject_inline_refs,
    reject_inline_refs_in_procedure_steps,
)


def reject_procedure_inline_refs(data: dict[str, Any], *, file_path: str) -> None:
    """Raise :class:`~doctrine.shared.exceptions.InlineReferenceRejectedError`
    if the procedure YAML carries forbidden inline references at either the
    top level or within any ``steps[i]`` entry.
    """
    reject_inline_refs(data, file_path=file_path, artifact_kind="procedure")
    reject_inline_refs_in_procedure_steps(data, file_path=file_path)
