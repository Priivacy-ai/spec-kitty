"""Negative-fixture suite asserting the per-kind validators reject any YAML
that still carries forbidden inline reference fields.

Covers the contract in
``kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/contracts/validator-rejection-error.schema.json``.

The migration hint emitted by :class:`InlineReferenceRejectedError` must
match the schema's regex pattern::

    ^Remove .+ from YAML; add edge \\{from: .+, to: .+, kind: uses\\}
     to src/doctrine/graph.yaml$

Eight cases total: 7 per-kind top-level fixtures + 1 procedures step-level
fixture.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from doctrine.agent_profiles.validation import reject_agent_profile_inline_refs
from doctrine.directives.validation import reject_directive_inline_refs
from doctrine.paradigms.validation import reject_paradigm_inline_refs
from doctrine.procedures.validation import reject_procedure_inline_refs
from doctrine.shared.exceptions import InlineReferenceRejectedError
from doctrine.styleguides.validation import reject_styleguide_inline_refs
from doctrine.tactics.validation import reject_tactic_inline_refs
from doctrine.toolguides.validation import reject_toolguide_inline_refs

#: Matches ``migration_hint`` per the JSON schema.
HINT_PATTERN = re.compile(
    r"^Remove .+ from YAML; add edge \{from: .+, to: .+, kind: uses\} "
    r"to src/doctrine/graph\.yaml$"
)

#: Registry of (reject_fn, artifact_kind, sample_data_factory) entries for each
#: per-kind validator plus the procedures step-level case.


def _make_data_with_field(artifact_id: str, forbidden_field: str) -> dict[str, Any]:
    return {"id": artifact_id, forbidden_field: ["target-1", "target-2"]}


@pytest.mark.parametrize(
    "reject_fn, artifact_kind, forbidden_field",
    [
        (reject_directive_inline_refs, "directive", "tactic_refs"),
        (reject_tactic_inline_refs, "tactic", "paradigm_refs"),
        (reject_procedure_inline_refs, "procedure", "applies_to"),
        (reject_paradigm_inline_refs, "paradigm", "tactic_refs"),
        (reject_styleguide_inline_refs, "styleguide", "applies_to"),
        (reject_toolguide_inline_refs, "toolguide", "tactic_refs"),
        (reject_agent_profile_inline_refs, "agent_profile", "applies_to"),
    ],
)
def test_top_level_inline_ref_is_rejected(
    reject_fn: Any,
    artifact_kind: str,
    forbidden_field: str,
    tmp_path: Any,
) -> None:
    """Every per-kind validator rejects top-level inline reference fields
    with a structured :class:`InlineReferenceRejectedError`."""
    artifact_id = f"sample-{artifact_kind}"
    data = _make_data_with_field(artifact_id, forbidden_field)
    file_path = str(tmp_path / f"{artifact_id}.{artifact_kind}.yaml")

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        reject_fn(data, file_path=file_path)

    err = excinfo.value
    assert err.file_path == file_path
    assert err.forbidden_field == forbidden_field
    assert err.artifact_kind == artifact_kind
    assert HINT_PATTERN.match(err.migration_hint), (
        f"migration_hint {err.migration_hint!r} does not match schema regex"
    )
    # The hint embeds the artifact id so operators can locate the source quickly.
    assert f"{artifact_kind}:{artifact_id}" in err.migration_hint


def test_procedure_step_level_tactic_refs_rejected(tmp_path: Any) -> None:
    """A procedure YAML with ``steps[i].tactic_refs`` must be rejected with a
    structured error (FR-008 step-level scan requirement).

    Without this scan, step-level ``tactic_refs`` would fall through to
    Pydantic's generic ``extra_forbidden`` error -- valid rejection but
    missing the migration hint the spec requires.
    """
    data: dict[str, Any] = {
        "id": "my-procedure",
        "steps": [
            {"title": "step-0", "body": "..."},
            {"title": "step-1", "tactic_refs": ["tactic-a"]},
        ],
    }
    file_path = str(tmp_path / "my-procedure.procedure.yaml")

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        reject_procedure_inline_refs(data, file_path=file_path)

    err = excinfo.value
    assert err.artifact_kind == "procedure"
    assert err.forbidden_field == "tactic_refs"
    assert err.file_path == file_path
    assert HINT_PATTERN.match(err.migration_hint), (
        f"migration_hint {err.migration_hint!r} does not match schema regex"
    )
    assert "procedure:my-procedure" in err.migration_hint


def test_procedure_step_level_paradigm_refs_rejected(tmp_path: Any) -> None:
    """Step-level ``paradigm_refs`` is also rejected with the structured error."""
    data: dict[str, Any] = {
        "id": "my-procedure",
        "steps": [{"title": "s0", "paradigm_refs": ["p1"]}],
    }
    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        reject_procedure_inline_refs(
            data, file_path=str(tmp_path / "p.procedure.yaml")
        )
    assert excinfo.value.forbidden_field == "paradigm_refs"


def test_clean_payload_passes_without_raising(tmp_path: Any) -> None:
    """A YAML without any forbidden inline fields does not raise."""
    data: dict[str, Any] = {"id": "clean-directive", "summary": "no inline refs"}
    reject_directive_inline_refs(
        data, file_path=str(tmp_path / "clean.directive.yaml")
    )


def test_all_three_forbidden_fields_are_flagged() -> None:
    """Verify each of the three forbidden field names is rejected on at
    least one per-kind validator, satisfying the schema enum coverage."""
    flagged: set[str] = set()
    for data, reject_fn in [
        ({"id": "a", "tactic_refs": ["x"]}, reject_directive_inline_refs),
        ({"id": "b", "paradigm_refs": ["y"]}, reject_tactic_inline_refs),
        ({"id": "c", "applies_to": ["z"]}, reject_styleguide_inline_refs),
    ]:
        try:
            reject_fn(data, file_path="/tmp/fake.yaml")
        except InlineReferenceRejectedError as err:
            flagged.add(err.forbidden_field)
    assert flagged == {"tactic_refs", "paradigm_refs", "applies_to"}
