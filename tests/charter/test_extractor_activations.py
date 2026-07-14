"""Unit tests for the WP02 activation-registry extractor extensions.

Covers :meth:`charter.extractor.Extractor._apply_activations_block` and
:meth:`Extractor._collect_activations_from_section`: reading a top-level
``activations:`` list from any fenced YAML block inside ``charter.md``
and surfacing the validated rows on
:attr:`charter.schemas.GovernanceConfig.activations` (mission
``charter-mediated-doctrine-selection-01KRTZCA``, WP02 T007 + T009).

Tests assert four contracts from
``contracts/activation-registry.md`` and the WP02 task spec:

  1. A well-formed ``activations:`` block lands as a list of
     :class:`charter.activations.ActivationEntry` rows on the governance
     config.
  2. Round-trip through :func:`charter.schemas.emit_yaml` preserves the
     block byte-for-content (per NFR-005).
  3. Invalid entries (vocabulary violations) raise ``ValueError``
     during extraction (T009 validation hook).
  4. An empty charter (no ``activations:`` block) keeps the field empty
     AND keeps the key out of emitted YAML (NFR-005 byte stability).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.activations import ActivationEntry
from charter.extractor import Extractor
from charter.schemas import GovernanceConfig, emit_yaml


pytestmark = [pytest.mark.unit]


_CHARTER_WITH_ONE_ACTIVATION = """\
# Test Charter

## Doctrine Selection

```yaml
template_set: software-dev-default

activations:
  - activation_context:
      mission_type: software-dev
      action: implement
    doctrine_pack_id: very-serious-developers
    artifact_id: caveman-comments
    artifact_kind: styleguides
```
"""


_CHARTER_WITH_WILDCARD_ACTIVATION = """\
# Test Charter

## Doctrine Selection

```yaml
activations:
  - activation_context: {}
    doctrine_pack_id: project
    artifact_id: caveman-comments
```
"""


_CHARTER_WITH_INVALID_MISSION_TYPE = """\
# Test Charter

## Doctrine Selection

```yaml
activations:
  - activation_context:
      mission_type: dev
      action: implement
    doctrine_pack_id: project
    artifact_id: caveman-comments
```
"""


_CHARTER_WITH_INVALID_ACTION = """\
# Test Charter

## Doctrine Selection

```yaml
activations:
  - activation_context:
      action: bogus-action
    doctrine_pack_id: project
    artifact_id: caveman-comments
```
"""


_CHARTER_WITH_INVALID_KIND = """\
# Test Charter

## Doctrine Selection

```yaml
activations:
  - activation_context: {}
    doctrine_pack_id: project
    artifact_id: caveman-comments
    artifact_kind: bogus-kind
```
"""


_CHARTER_WITHOUT_ACTIVATIONS = """\
# Test Charter

## Purpose

A charter with no activations registry at all.
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_extractor_reads_one_activation_entry() -> None:
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_ONE_ACTIVATION)
    assert len(result.governance.activations) == 1
    entry = result.governance.activations[0]
    assert isinstance(entry, ActivationEntry)
    assert entry.activation_context == {
        "mission_type": "software-dev",
        "action": "implement",
    }
    assert entry.doctrine_pack_id == "very-serious-developers"
    assert entry.artifact_id == "caveman-comments"
    assert entry.artifact_kind == "styleguides"


def test_extractor_accepts_empty_activation_context_as_wildcard() -> None:
    """``activation_context: {}`` is the terse wildcard form (both slots
    default to "match every value"). The extractor must accept it.
    """
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_WILDCARD_ACTIVATION)
    assert len(result.governance.activations) == 1
    entry = result.governance.activations[0]
    assert entry.activation_context == {}
    assert entry.doctrine_pack_id == "project"
    assert entry.artifact_id == "caveman-comments"
    assert entry.artifact_kind is None


def test_extractor_skips_non_dict_activation_items() -> None:
    """Non-dict list items (e.g. a bare string) must be skipped silently —
    they don't represent a meaningful entry.
    """
    charter = """\
# Test Charter

## Doctrine Selection

```yaml
activations:
  - "not a dict"
  - activation_context: {}
    doctrine_pack_id: project
    artifact_id: caveman-comments
```
"""
    extractor = Extractor()
    result = extractor.extract(charter)
    assert len(result.governance.activations) == 1
    assert result.governance.activations[0].doctrine_pack_id == "project"


# ---------------------------------------------------------------------------
# Round-trip via emit_yaml
# ---------------------------------------------------------------------------


def test_activations_block_round_trips_through_emit_yaml(tmp_path: Path) -> None:
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_ONE_ACTIVATION)
    out = tmp_path / "governance.yaml"
    emit_yaml(result.governance, out)
    reloaded_raw = YAML().load(out)
    assert reloaded_raw["activations"] == [
        {
            "activation_context": {
                "mission_type": "software-dev",
                "action": "implement",
            },
            "doctrine_pack_id": "very-serious-developers",
            "artifact_id": "caveman-comments",
            "artifact_kind": "styleguides",
        }
    ]


def test_activations_round_trips_through_governance_config_model_validate(
    tmp_path: Path,
) -> None:
    """End-to-end: extract → emit_yaml → YAML.load →
    GovernanceConfig.model_validate must produce a list of
    ActivationEntry instances with the original field values intact.
    """
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_ONE_ACTIVATION)
    out = tmp_path / "governance.yaml"
    emit_yaml(result.governance, out)
    reloaded_raw = YAML().load(out)
    reloaded = GovernanceConfig.model_validate(reloaded_raw)
    assert {a.artifact_id for a in reloaded.activations} == {"caveman-comments"}
    entry = reloaded.activations[0]
    assert isinstance(entry, ActivationEntry)
    assert entry.activation_context == {
        "mission_type": "software-dev",
        "action": "implement",
    }
    assert entry.doctrine_pack_id == "very-serious-developers"
    assert entry.artifact_id == "caveman-comments"
    assert entry.artifact_kind == "styleguides"


def test_empty_activations_omitted_from_emitted_yaml(tmp_path: Path) -> None:
    """NFR-005 byte-stability regression: an empty activations list MUST
    NOT serialize to ``activations: []`` in the emitted file.
    """
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITHOUT_ACTIVATIONS)
    out = tmp_path / "governance.yaml"
    emit_yaml(result.governance, out)
    text = out.read_text(encoding="utf-8")
    assert "activations" not in text, (
        "NFR-005 violation: empty activations list leaked into emitted "
        f"governance.yaml. Raw:\n{text}"
    )


# ---------------------------------------------------------------------------
# Validation (T009)
# ---------------------------------------------------------------------------


def test_extractor_rejects_invalid_mission_type() -> None:
    """A charter declaring ``mission_type: dev`` (not in
    ``ALLOWED_MISSION_TYPES``) must raise ``ValueError`` during extraction
    so the operator typo is loud rather than silently dropped.
    """
    extractor = Extractor()
    with pytest.raises(ValueError, match=r"charter activations: invalid entry"):
        extractor.extract(_CHARTER_WITH_INVALID_MISSION_TYPE)


def test_extractor_rejects_invalid_action() -> None:
    extractor = Extractor()
    with pytest.raises(ValueError, match=r"charter activations: invalid entry"):
        extractor.extract(_CHARTER_WITH_INVALID_ACTION)


def test_extractor_rejects_invalid_artifact_kind() -> None:
    extractor = Extractor()
    with pytest.raises(ValueError, match=r"charter activations: invalid entry"):
        extractor.extract(_CHARTER_WITH_INVALID_KIND)


def test_extractor_error_message_surfaces_offending_entry() -> None:
    """The ``ValueError`` raised on validation failure must name the
    offending entry so an operator can locate the bad row in charter.md.
    """
    extractor = Extractor()
    with pytest.raises(ValueError) as excinfo:
        extractor.extract(_CHARTER_WITH_INVALID_MISSION_TYPE)
    msg = str(excinfo.value)
    assert "dev" in msg, (
        f"Validation error must surface the offending mission_type value. "
        f"Got: {msg!r}"
    )
