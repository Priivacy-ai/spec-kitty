r"""WP02 — fenced-YAML resolver-input block extraction.

These tests pin the FR-007 / FR-008 contract: ``charter sync`` reads
fenced YAML blocks (the ```yaml ...``` shape) anywhere in the charter
body and lifts the top-level keys ``template_set``, ``available_tools``,
and ``authority_paths`` into ``DoctrineSelectionConfig``. The contract
is designed so a charter without any of these declarations syncs
byte-identically to today (NFR-005).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.extractor import Extractor
from charter.sync import sync

pytestmark = pytest.mark.fast


def _load_governance(path: Path) -> dict[str, object]:
    yaml = YAML()
    data = yaml.load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


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


def test_fenced_yaml_authority_paths_extracted(tmp_path: Path) -> None:
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(_CHARTER_WITH_FULL_BLOCK, encoding="utf-8")

    result = sync(charter_file, tmp_path)
    assert result.synced is True

    data = _load_governance(tmp_path / "governance.yaml")
    doctrine = data["doctrine"]
    assert isinstance(doctrine, dict)
    assert doctrine.get("authority_paths") == [
        "docs/context/",
        "docs/adr/3.x/",
    ]
    assert doctrine.get("governance_references") == ["spec/constitution.md"]


def test_fenced_yaml_required_reading_alias_extracted(tmp_path: Path) -> None:
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
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(charter, encoding="utf-8")

    result = sync(charter_file, tmp_path)
    assert result.synced is True

    data = _load_governance(tmp_path / "governance.yaml")
    doctrine = data["doctrine"]
    assert isinstance(doctrine, dict)
    assert doctrine.get("governance_references") == [
        "spec/constitution.md",
        "docs/security-policy.md",
    ]


def test_fenced_yaml_template_set_extracted(tmp_path: Path) -> None:
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(_CHARTER_WITH_FULL_BLOCK, encoding="utf-8")

    sync(charter_file, tmp_path)
    data = _load_governance(tmp_path / "governance.yaml")
    assert data["doctrine"]["template_set"] == "software-dev-default"  # type: ignore[index]


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


def test_charter_without_yaml_block_unchanged(tmp_path: Path) -> None:
    """NFR-005: a charter without any of the new declarations syncs and
    produces output without the new optional fields, so existing files
    stay byte-identical.
    """
    charter = """\
# Charter

## Testing

Minimum 80% coverage; pytest.
"""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(charter, encoding="utf-8")

    result = sync(charter_file, tmp_path)
    assert result.synced is True
    assert result.error is None

    governance_yaml = tmp_path / "governance.yaml"
    body = governance_yaml.read_text(encoding="utf-8")
    # NFR-005: the new authority_paths key MUST NOT be emitted when empty.
    assert "authority_paths" not in body
    assert "governance_references" not in body

    directives_body = (tmp_path / "directives.yaml").read_text(encoding="utf-8")
    # NFR-005: references MUST NOT be emitted when empty (per contract §2).
    assert "references" not in directives_body


def test_references_field_omitted_when_no_citations(tmp_path: Path) -> None:
    charter = """\
# Charter

## Project Directives

1. Plain rule with no DIRECTIVE_NNN citation whatsoever.
2. Another plain rule.
"""
    charter_file = tmp_path / "charter.md"
    charter_file.write_text(charter, encoding="utf-8")

    sync(charter_file, tmp_path)
    body = (tmp_path / "directives.yaml").read_text(encoding="utf-8")
    assert "DIR-001" in body  # directives were emitted
    assert "references" not in body  # but no references key when empty


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
