r"""WP02 — fenced-YAML resolver-input block extraction.

These tests pin the FR-007 / FR-008 contract: the (still-live)
doctrine-selection extraction reads fenced YAML blocks (the
```yaml ...``` shape) anywhere in the charter body and lifts the
top-level keys ``template_set``, ``available_tools``, and
``authority_paths`` into ``DoctrineSelectionConfig``. The contract is
designed so a charter without any of these declarations extracts
byte-identically to today (NFR-005).

consolidate-charter-bundle (IC-04 / WP04, T028c): the tests below were
originally written against ``charter.sync.sync()``, reading its emitted
``governance.yaml``/``directives.yaml`` back off disk. ``sync()``'s
prose->triad WRITE is now retired (governance/directives are hand-authored
sections inside ``charter.yaml``); the extraction ITSELF
(``charter.extractor.Extractor``) is still live, so these tests now call
it directly rather than round-tripping through the retired file writer.
"""

from __future__ import annotations

import pytest

from charter.extractor import Extractor

pytestmark = pytest.mark.fast


_CHARTER_WITH_FULL_BLOCK = """\
# Charter

## Charter Resolution Hints

```yaml
template_set: software-dev-default
available_tools:
  - git
  - spec-kitty
  - pytest
authority_paths:
  - docs/context/
  - docs/adr/3.x/
governance_references:
  - spec/constitution.md
```
"""


def test_fenced_yaml_authority_paths_extracted() -> None:
    extraction = Extractor().extract(_CHARTER_WITH_FULL_BLOCK)
    doctrine = extraction.governance.doctrine
    assert doctrine.authority_paths == [
        "docs/context/",
        "docs/adr/3.x/",
    ]
    assert doctrine.governance_references == ["spec/constitution.md"]


def test_fenced_yaml_required_reading_alias_extracted() -> None:
    charter = """\
# Charter

## Supporting Governance

```yaml
required_reading:
  - spec/constitution.md
reading_list:
  - docs/security-policy.md
```
"""
    extraction = Extractor().extract(charter)
    doctrine = extraction.governance.doctrine
    assert doctrine.governance_references == [
        "spec/constitution.md",
        "docs/security-policy.md",
    ]


def test_fenced_yaml_template_set_extracted() -> None:
    extraction = Extractor().extract(_CHARTER_WITH_FULL_BLOCK)
    assert extraction.governance.doctrine.template_set == "software-dev-default"


def test_fenced_yaml_available_tools_merges_with_existing() -> None:
    """When a selection table sets [git] and a fenced YAML block adds
    [pytest, mypy], the resulting list is a dedup-preserving merge.
    """
    charter = """\
# Charter

## Doctrine Tools

| available_tools |
| --- |
| git |

## Resolution

```yaml
available_tools:
  - pytest
  - mypy
  - git
```
"""
    extractor = Extractor()
    result = extractor.extract(charter)
    tools = result.governance.doctrine.available_tools
    # Order is "selection-table first, fenced YAML appended"; duplicates
    # are squashed (git only listed once).
    assert tools == ["git", "pytest", "mypy"]


def test_charter_without_yaml_block_unchanged() -> None:
    """NFR-005: a charter without any of the new declarations extracts
    without the new optional fields populated, so existing emitted YAML
    (via ``charter.schemas.emit_yaml``) stays byte-identical.
    """
    charter = """\
# Charter

## Testing

Minimum 80% coverage; pytest.
"""
    extraction = Extractor().extract(charter)
    assert extraction.warnings == [] or all(
        "authority_paths" not in w and "governance_references" not in w
        for w in extraction.warnings
    )
    doctrine = extraction.governance.doctrine
    # NFR-005: the new optional fields stay empty (emit_yaml's
    # _OPTIONAL_EMPTY_OMIT_KEYS then omits them from the on-disk bytes).
    assert doctrine.authority_paths == []
    assert doctrine.governance_references == []
    # Directive-body extraction is retired (module docstring): always empty.
    assert extraction.directives.directives == []


def test_references_field_omitted_when_no_citations() -> None:
    """Directive-body extraction is retired: no citations, no directives, ever."""
    charter = """\
# Charter

## Project Directives

1. Plain rule with no DIRECTIVE_NNN citation whatsoever.
2. Another plain rule.
"""
    extraction = Extractor().extract(charter)
    assert extraction.directives.directives == []


def test_non_string_authority_path_rejected() -> None:
    """T008 conformance: non-string authority_paths entries fail loudly."""
    charter = """\
# Charter

## Resolution

```yaml
authority_paths:
  - docs/context/
  - 12345
```
"""
    extractor = Extractor()
    with pytest.raises(ValueError, match="authority_paths"):
        extractor.extract(charter)


def test_non_string_governance_reference_rejected() -> None:
    charter = """\
# Charter

## Resolution

```yaml
governance_references:
  - spec/constitution.md
  - 12345
```
"""
    extractor = Extractor()
    with pytest.raises(ValueError, match="governance_references"):
        extractor.extract(charter)


def test_fenced_yaml_block_template_set_overrides_table_with_info_log(caplog: pytest.LogCaptureFixture) -> None:
    """T007: fenced YAML block wins on conflict with a selection-table row."""
    charter = """\
# Charter

## Doctrine Tools

| template_set |
| --- |
| legacy-set |

## Resolution

```yaml
template_set: software-dev-default
```
"""
    extractor = Extractor()
    with caplog.at_level("INFO"):
        result = extractor.extract(charter)
    assert result.governance.doctrine.template_set == "software-dev-default"
    # Diagnostic surfaces so an operator can see the override happened.
    assert any("overrides selection-table template_set" in r.message for r in caplog.records)
