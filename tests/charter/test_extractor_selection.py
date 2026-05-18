"""Unit tests for the WP02 selection-row extractor extensions.

Covers :meth:`charter.extractor.Extractor._apply_selection_row` reading the
five additive ``selected_<kind>`` fields from a fenced YAML block inside
``charter.md`` and round-tripping them through
:func:`charter.schemas.emit_yaml` / ``YAML().load(...)`` (mission
``charter-mediated-doctrine-selection-01KRTZCA``, WP02 T006).

Each test follows the same shape used elsewhere in ``tests/charter/``:

  1. Build a minimal charter string carrying the relevant fenced YAML block.
  2. Run :meth:`Extractor.extract` on it.
  3. Inspect ``result.governance.doctrine`` for the parsed value.
  4. Where round-trip is being asserted, also write the governance config
     out via :func:`emit_yaml` and reload it to confirm the value survives.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.extractor import Extractor
from charter.schemas import GovernanceConfig, emit_yaml


pytestmark = [pytest.mark.unit]


_CHARTER_WITH_ALL_NEW_SELECTIONS = """\
# Test Charter

## Doctrine Selection

```yaml
template_set: software-dev-default
available_tools: [git, pytest]
selected_styleguides:
  - caveman-comments
selected_toolguides:
  - pytest-flow
selected_procedures:
  - daily-standup
selected_agent_profiles:
  - python-pedro
selected_mission_step_contracts:
  - implement-step
```
"""


_CHARTER_WITH_ONLY_STYLEGUIDE = """\
# Test Charter

## Doctrine Selection

```yaml
selected_styleguides:
  - caveman-comments
```
"""


_CHARTER_WITH_CANONICAL_AND_ALIAS_PRECEDENCE = """\
# Test Charter

## Doctrine Selection

```yaml
selected_styleguides:
  - prefixed-wins
styleguides:
  - alias-loses
```
"""


_CHARTER_EMPTY_DOCTRINE = """\
# Test Charter

## Purpose

A charter with no doctrine selection block at all.
"""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def test_extractor_reads_selected_styleguides() -> None:
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_ONLY_STYLEGUIDE)
    assert result.governance.doctrine.selected_styleguides == ["caveman-comments"]


def test_extractor_reads_all_five_new_selection_fields() -> None:
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_ALL_NEW_SELECTIONS)
    doctrine = result.governance.doctrine
    assert doctrine.selected_styleguides == ["caveman-comments"]
    assert doctrine.selected_toolguides == ["pytest-flow"]
    assert doctrine.selected_procedures == ["daily-standup"]
    assert doctrine.selected_agent_profiles == ["python-pedro"]
    assert doctrine.selected_mission_step_contracts == ["implement-step"]


def test_canonical_prefixed_key_wins_over_bare_alias() -> None:
    """Per WP02 reviewer guidance: ``selected_<kind>`` MUST be the canonical
    first entry in the candidate-key tuple, so a charter declaring BOTH the
    canonical and the alias key falls back to the canonical value.
    """
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_CANONICAL_AND_ALIAS_PRECEDENCE)
    assert result.governance.doctrine.selected_styleguides == ["prefixed-wins"]


def test_empty_charter_yields_empty_selection_fields() -> None:
    extractor = Extractor()
    result = extractor.extract(_CHARTER_EMPTY_DOCTRINE)
    doctrine = result.governance.doctrine
    assert doctrine.selected_styleguides == []
    assert doctrine.selected_toolguides == []
    assert doctrine.selected_procedures == []
    assert doctrine.selected_agent_profiles == []
    assert doctrine.selected_mission_step_contracts == []


# ---------------------------------------------------------------------------
# Round-trip via emit_yaml / YAML().load
# ---------------------------------------------------------------------------


def test_selected_styleguides_round_trips_through_emit_yaml(tmp_path: Path) -> None:
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_ONLY_STYLEGUIDE)
    out = tmp_path / "governance.yaml"
    emit_yaml(result.governance, out)
    reloaded = YAML().load(out)
    assert (
        reloaded["doctrine"]["selected_styleguides"] == ["caveman-comments"]
    ), f"emitted governance.yaml dropped the field. Raw:\n{out.read_text()}"


def test_all_five_new_selection_fields_round_trip_through_emit_yaml(
    tmp_path: Path,
) -> None:
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_ALL_NEW_SELECTIONS)
    out = tmp_path / "governance.yaml"
    emit_yaml(result.governance, out)
    reloaded = YAML().load(out)
    doctrine = reloaded["doctrine"]
    assert doctrine["selected_styleguides"] == ["caveman-comments"]
    assert doctrine["selected_toolguides"] == ["pytest-flow"]
    assert doctrine["selected_procedures"] == ["daily-standup"]
    assert doctrine["selected_agent_profiles"] == ["python-pedro"]
    assert doctrine["selected_mission_step_contracts"] == ["implement-step"]


def test_empty_selection_fields_omitted_from_emitted_yaml(tmp_path: Path) -> None:
    """NFR-005 byte-stability regression: empty additive fields stay out of
    the emitted YAML so existing charters keep their on-disk bytes stable.
    """
    extractor = Extractor()
    result = extractor.extract(_CHARTER_EMPTY_DOCTRINE)
    out = tmp_path / "governance.yaml"
    emit_yaml(result.governance, out)
    text = out.read_text(encoding="utf-8")
    for key in (
        "selected_styleguides",
        "selected_toolguides",
        "selected_procedures",
        "selected_agent_profiles",
        "selected_mission_step_contracts",
    ):
        assert key not in text, (
            f"NFR-005 violation: empty additive field {key!r} leaked into "
            f"emitted governance.yaml. Raw:\n{text}"
        )


def test_round_trip_via_governance_config_model_validate(tmp_path: Path) -> None:
    """A round-trip through the full Pydantic surface (extract → emit_yaml
    → YAML.load → GovernanceConfig.model_validate) preserves all five
    additive fields. This is the surface the runtime consumers (sync
    loader, charter context builder) actually use.
    """
    extractor = Extractor()
    result = extractor.extract(_CHARTER_WITH_ALL_NEW_SELECTIONS)
    out = tmp_path / "governance.yaml"
    emit_yaml(result.governance, out)
    reloaded_raw = YAML().load(out)
    reloaded = GovernanceConfig.model_validate(reloaded_raw)
    assert reloaded.doctrine.selected_styleguides == ["caveman-comments"]
    assert reloaded.doctrine.selected_toolguides == ["pytest-flow"]
    assert reloaded.doctrine.selected_procedures == ["daily-standup"]
    assert reloaded.doctrine.selected_agent_profiles == ["python-pedro"]
    assert reloaded.doctrine.selected_mission_step_contracts == ["implement-step"]
