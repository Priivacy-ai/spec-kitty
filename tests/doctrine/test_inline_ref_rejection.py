"""Negative-fixture suite asserting the per-kind validators reject any YAML
that still carries forbidden inline reference fields.

Covers the contract in
``kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/contracts/validator-rejection-error.schema.json``.

The migration hint emitted by :class:`InlineReferenceRejectedError` must
match the schema's regex pattern::

    ^Remove .+ from YAML; add edge \\{source: .+, target: .+, relation: requires\\}
     to src/doctrine/graph.yaml$

The hint uses the actual ``DRGEdge`` schema (``source``/``target``/``relation``)
and the ``requires`` relation -- the ``Relation`` enum does not contain
``uses``, so the earlier ``kind: uses`` text pointed operators at an
impossible edit.

Eight cases total: 7 per-kind top-level fixtures + 1 procedures step-level
fixture.
"""

from __future__ import annotations

import re
from pathlib import Path
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
    r"^Remove .+ from YAML; add edge "
    r"\{source: .+, target: .+, relation: requires\} "
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
    assert HINT_PATTERN.match(err.migration_hint), f"migration_hint {err.migration_hint!r} does not match schema regex"
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
    assert HINT_PATTERN.match(err.migration_hint), f"migration_hint {err.migration_hint!r} does not match schema regex"
    assert "procedure:my-procedure" in err.migration_hint


def test_procedure_step_level_paradigm_refs_rejected(tmp_path: Any) -> None:
    """Step-level ``paradigm_refs`` is also rejected with the structured error."""
    data: dict[str, Any] = {
        "id": "my-procedure",
        "steps": [{"title": "s0", "paradigm_refs": ["p1"]}],
    }
    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        reject_procedure_inline_refs(data, file_path=str(tmp_path / "p.procedure.yaml"))
    assert excinfo.value.forbidden_field == "paradigm_refs"


def test_clean_payload_passes_without_raising(tmp_path: Any) -> None:
    """A YAML without any forbidden inline fields does not raise."""
    data: dict[str, Any] = {"id": "clean-directive", "summary": "no inline refs"}
    reject_directive_inline_refs(data, file_path=str(tmp_path / "clean.directive.yaml"))


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


# ---------------------------------------------------------------------------
# Integration tests: the live repository ``_load`` paths must raise
# :class:`InlineReferenceRejectedError`, not silently warn with a generic
# Pydantic ``extra_forbidden``. Closes FR-008 Scenario 4 ("The loader does
# not silently ignore the field.").
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_directive_repository_rejects_project_inline_refs(tmp_path: Path) -> None:
    """Loading a project directive that carries ``applies_to:`` must raise
    :class:`InlineReferenceRejectedError` at _load time, not warn.
    """
    from doctrine.directives.repository import DirectiveRepository

    project_dir = tmp_path / "directives"
    _write_yaml(
        project_dir / "my-directive.directive.yaml",
        "id: MY-DIRECTIVE\ntitle: demo\nintent: demo intent\napplies_to: [software-dev]\n",
    )

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        DirectiveRepository(
            shipped_dir=tmp_path / "nonexistent_shipped",
            project_dir=project_dir,
        )
    err = excinfo.value
    assert err.artifact_kind == "directive"
    assert err.forbidden_field == "applies_to"
    assert HINT_PATTERN.match(err.migration_hint)


def test_tactic_repository_rejects_shipped_inline_refs(tmp_path: Path) -> None:
    """Shipped tactics with forbidden inline refs must raise at load time."""
    from doctrine.tactics.repository import TacticRepository

    shipped_dir = tmp_path / "tactics_shipped"
    _write_yaml(
        shipped_dir / "bad.tactic.yaml",
        "id: bad-tactic\nname: bad\npurpose: test\nparadigm_refs: [p1]\n",
    )

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        TacticRepository(shipped_dir=shipped_dir, project_dir=None)
    assert excinfo.value.artifact_kind == "tactic"
    assert excinfo.value.forbidden_field == "paradigm_refs"


def test_paradigm_repository_rejects_inline_refs(tmp_path: Path) -> None:
    from doctrine.paradigms.repository import ParadigmRepository

    shipped_dir = tmp_path / "paradigms_shipped"
    _write_yaml(
        shipped_dir / "bad.paradigm.yaml",
        "id: bad-paradigm\nname: bad\nsummary: test\ntactic_refs: [t1]\n",
    )

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        ParadigmRepository(shipped_dir=shipped_dir, project_dir=None)
    assert excinfo.value.artifact_kind == "paradigm"
    assert excinfo.value.forbidden_field == "tactic_refs"


def test_styleguide_repository_rejects_inline_refs(tmp_path: Path) -> None:
    from doctrine.styleguides.repository import StyleguideRepository

    shipped_dir = tmp_path / "styleguides_shipped"
    _write_yaml(
        shipped_dir / "bad.styleguide.yaml",
        "id: bad-style\ntitle: bad\nprinciples: [x]\napplies_to: [y]\n",
    )

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        StyleguideRepository(shipped_dir=shipped_dir, project_dir=None)
    assert excinfo.value.artifact_kind == "styleguide"
    assert excinfo.value.forbidden_field == "applies_to"


def test_toolguide_repository_rejects_inline_refs(tmp_path: Path) -> None:
    from doctrine.toolguides.repository import ToolguideRepository

    shipped_dir = tmp_path / "toolguides_shipped"
    _write_yaml(
        shipped_dir / "bad.toolguide.yaml",
        "id: bad-tool\ntitle: bad\nsummary: x\ntactic_refs: [t1]\n",
    )

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        ToolguideRepository(shipped_dir=shipped_dir, project_dir=None)
    assert excinfo.value.artifact_kind == "toolguide"
    assert excinfo.value.forbidden_field == "tactic_refs"


def test_procedure_repository_rejects_top_level_inline_refs(tmp_path: Path) -> None:
    from doctrine.procedures.repository import ProcedureRepository

    shipped_dir = tmp_path / "procedures_shipped"
    _write_yaml(
        shipped_dir / "bad.procedure.yaml",
        "id: bad-proc\nname: bad\npurpose: x\nsteps: []\napplies_to: [y]\n",
    )

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        ProcedureRepository(shipped_dir=shipped_dir, project_dir=None)
    assert excinfo.value.artifact_kind == "procedure"
    assert excinfo.value.forbidden_field == "applies_to"


def test_procedure_repository_rejects_step_level_inline_refs(tmp_path: Path) -> None:
    """FR-008 step-level scan: ``steps[*].tactic_refs`` rejected with the
    structured :class:`InlineReferenceRejectedError`, not Pydantic's generic
    ``extra_forbidden`` warning.
    """
    from doctrine.procedures.repository import ProcedureRepository

    shipped_dir = tmp_path / "procedures_shipped"
    _write_yaml(
        shipped_dir / "bad-step.procedure.yaml",
        "id: bad-step-proc\nname: bad-step\npurpose: x\nsteps:\n  - title: step-0\n    body: ok\n  - title: step-1\n    tactic_refs: [t1]\n",
    )

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        ProcedureRepository(shipped_dir=shipped_dir, project_dir=None)
    err = excinfo.value
    assert err.artifact_kind == "procedure"
    assert err.forbidden_field == "tactic_refs"
    assert HINT_PATTERN.match(err.migration_hint)


def test_agent_profile_repository_rejects_inline_refs(tmp_path: Path) -> None:
    from doctrine.agent_profiles.repository import AgentProfileRepository

    shipped_dir = tmp_path / "agent_profiles_shipped"
    # agent profile YAMLs use kebab-case keys; the rejection scan is for
    # extra top-level fields, so ``applies_to`` is unambiguous.
    _write_yaml(
        shipped_dir / "bad.agent.yaml",
        "profile-id: bad-profile\nrole: implementer\napplies_to: [software-dev]\n",
    )

    with pytest.raises(InlineReferenceRejectedError) as excinfo:
        AgentProfileRepository(shipped_dir=shipped_dir, project_dir=None)
    assert excinfo.value.artifact_kind == "agent_profile"
    assert excinfo.value.forbidden_field == "applies_to"
