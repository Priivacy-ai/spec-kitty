"""Architectural guard — selection-schema completeness.

Every artifact kind exposed by ``doctrine.service.DoctrineService`` MUST
be addressable via:

    * a charter ``selected_<kind>`` field on
      :class:`charter.schemas.DoctrineSelectionConfig` (global mode), AND
    * an org-charter ``required_<kind>`` field on
      :class:`specify_cli.doctrine.org_charter.OrgCharterPolicy`
      (org-pack distribution mode).

This is the parity rule that closes Case 1 / Case 2 step 3 from the
pre-flight: a user cannot declare a styleguide / toolguide / procedure
as charter-active today because the schema fields do not exist. Mission
B WP04 adds them; this test fails until they do, and FUTURE artifact
kinds added to ``DoctrineService`` must arrive with the matching
``selected_<kind>`` / ``required_<kind>`` fields or this test fails
again, preventing silent regression.

See ``docs/development/doctrine-artifact-selection-preflight.md`` →
"Accommodation options" item 1, and
``docs/development/mission-b-proposed-scope.md`` → WP04.

Expected status TODAY: FAIL (3 selection fields and 1 required field
exist; 8 artifact kinds are exposed).

Expected status AFTER Mission B WP04: PASS (8 selection fields, 8
required fields, all parity).
"""

from __future__ import annotations

import inspect

import pytest

from charter.schemas import DoctrineSelectionConfig
from doctrine.service import DoctrineService
from specify_cli.doctrine.org_charter import OrgCharterPolicy


pytestmark = [pytest.mark.architectural]


# ---------------------------------------------------------------------------
# Discovery helpers — keep them tiny + AST-light (introspection is enough)
# ---------------------------------------------------------------------------


# Artifact-kind names exposed as @property on DoctrineService. These are
# the canonical singular-form-with-trailing-s identifiers used as the
# ``selected_<kind>`` / ``required_<kind>`` suffix. Discovered via
# introspection so the test fails the moment a new kind lands without
# its matching selection fields.
def _doctrine_artifact_kinds() -> set[str]:
    kinds: set[str] = set()
    for name, value in inspect.getmembers(DoctrineService):
        if name.startswith("_"):
            continue
        if isinstance(value, property):
            kinds.add(name)
    return kinds


def _selected_fields(schema_cls: type) -> set[str]:
    """Field names on ``schema_cls`` matching the ``selected_*`` prefix."""
    return {name for name in schema_cls.model_fields if name.startswith("selected_")}


def _required_fields(schema_cls: type) -> set[str]:
    """Field names on ``schema_cls`` matching the ``required_*`` prefix."""
    return {name for name in schema_cls.model_fields if name.startswith("required_")}


# ---------------------------------------------------------------------------
# Parity tests
# ---------------------------------------------------------------------------


def test_every_doctrine_kind_has_a_charter_selected_field() -> None:
    """Each property on DoctrineService MUST have a matching
    ``selected_<kind>`` field on DoctrineSelectionConfig.

    Today's expected shortfall: ``selected_styleguides``,
    ``selected_toolguides``, ``selected_procedures``,
    ``selected_agent_profiles``, ``selected_mission_step_contracts``
    do not exist. Mission B WP04 adds all five.
    """
    kinds = _doctrine_artifact_kinds()
    selected = _selected_fields(DoctrineSelectionConfig)
    expected = {f"selected_{kind}" for kind in kinds}

    missing = sorted(expected - selected)
    extra = sorted(selected - expected)

    assert not missing, (
        "DoctrineSelectionConfig is missing the following `selected_<kind>` "
        "fields for artifact kinds exposed by DoctrineService:\n"
        + "\n".join(f"  - {name}" for name in missing)
        + "\n\n"
        "Each missing field blocks the charter from declaring its artifact "
        "as globally active. Mission B WP04 adds these fields to "
        "src/charter/schemas.py:DoctrineSelectionConfig.\n"
        f"\n  artifact kinds present on DoctrineService: {sorted(kinds)}\n"
        f"  selection fields present on DoctrineSelectionConfig: {sorted(selected)}\n"
    )
    assert not extra, (
        "DoctrineSelectionConfig declares `selected_<name>` fields that do "
        "NOT correspond to any DoctrineService kind:\n"
        + "\n".join(f"  - {name}" for name in extra)
        + "\n\n"
        "Either the kind was removed from DoctrineService (then drop the "
        "field) or the field name is wrong (then rename it to match the "
        "kind property)."
    )


def test_every_doctrine_kind_has_an_org_required_field() -> None:
    """Each property on DoctrineService MUST have a matching
    ``required_<kind>`` field on OrgCharterPolicy so org packs can
    distribute mandatory artifacts.

    Today's expected shortfall: ``required_styleguides``,
    ``required_toolguides``, ``required_procedures``,
    ``required_agent_profiles``, ``required_mission_step_contracts``,
    ``required_paradigms``, ``required_tactics`` do not exist (only
    ``required_directives``). Mission B WP04 adds the rest.
    """
    kinds = _doctrine_artifact_kinds()
    required = _required_fields(OrgCharterPolicy)
    expected = {f"required_{kind}" for kind in kinds}

    missing = sorted(expected - required)

    assert not missing, (
        "OrgCharterPolicy is missing the following `required_<kind>` fields "
        "for artifact kinds exposed by DoctrineService:\n"
        + "\n".join(f"  - {name}" for name in missing)
        + "\n\n"
        "Each missing field blocks an org pack from mandating that artifact. "
        "Mission B WP04 adds these fields to "
        "src/specify_cli/doctrine/org_charter.py:OrgCharterPolicy and "
        "extends `apply_org_charter_to_interview` to union them into the "
        "project's selection.\n"
        f"\n  artifact kinds present on DoctrineService: {sorted(kinds)}\n"
        f"  required fields present on OrgCharterPolicy: {sorted(required)}\n"
    )


def test_selection_and_required_field_names_are_consistent() -> None:
    """For every artifact kind ``K``, the project-level field is named
    ``selected_K`` and the org-level field is named ``required_K`` —
    same suffix, mirroring conventions.

    Pinning this prevents the schemas from drifting apart (e.g. a future
    PR introducing ``required_styleguide`` singular while
    ``selected_styleguides`` is plural). The mirror-rule is what makes
    ``apply_org_charter_to_interview`` mechanically simple.
    """
    selected = _selected_fields(DoctrineSelectionConfig)
    required = _required_fields(OrgCharterPolicy)

    selected_suffixes = {name.removeprefix("selected_") for name in selected}
    required_suffixes = {name.removeprefix("required_") for name in required}

    asymmetric_selected = sorted(selected_suffixes - required_suffixes)
    asymmetric_required = sorted(required_suffixes - selected_suffixes)

    assert not asymmetric_selected and not asymmetric_required, (
        "Selection / required field-name mirror is broken.\n"
        f"  selected_<X> on DoctrineSelectionConfig with NO matching "
        f"required_<X> on OrgCharterPolicy: {asymmetric_selected}\n"
        f"  required_<X> on OrgCharterPolicy with NO matching selected_<X> "
        f"on DoctrineSelectionConfig: {asymmetric_required}\n\n"
        "The naming convention is selected_<plural-kind> /"
        " required_<plural-kind> with identical suffix. Mission B WP04 must "
        "land both sides of each pair in lockstep."
    )
