"""CR-01 compat: ``governance.doctrine`` -> ``governance.charter`` cutover.

Mission ``charter-authority-flip-01M14RB3`` WP03 (T012). ``charter.yaml``'s
``governance:`` section used to nest its selection block under the retired
governing-term key ``doctrine:``. The canonical key is now ``charter:``
(``GovernanceConfig.charter``, ``src/charter/schemas.py``). An existing
project's ``charter.yaml`` may still carry the legacy key on disk, so
:func:`charter.sync.load_governance_config` maps it forward with a
deprecation warning (CR-01, ``kitty-specs/retire-doctrine-term-01M0JMK9/
inventory.md`` line 163) rather than failing closed.

The dict-level remap happens on the RAW ``governance_data`` mapping *before*
``GovernanceConfig.model_validate`` -- a pydantic ``Field(alias=...)`` would
remap silently, which defeats the warn-once contract (SC-002, research.md
Seam 2).
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from charter.sync import (
    LegacyGovernanceKeyWarning,
    _warn_legacy_governance_key_once,
    load_governance_config,
)

pytestmark = pytest.mark.fast


def _write_governance_section(root: Path, governance_body: str) -> None:
    """Write ``governance_body`` verbatim under charter.yaml's ``governance:`` key.

    Mirrors ``tests/charter/test_resolver.py``'s ``_write_charter_files``:
    writes at the CANONICAL root (``charter.resolution.
    resolve_canonical_repo_root``), which the ``tests/charter/conftest.py``
    autouse git-init fixture makes equal to ``root`` for a bare ``tmp_path``.
    """
    from charter.resolution import resolve_canonical_repo_root

    yaml = YAML()
    root.mkdir(parents=True, exist_ok=True)
    canonical_root = resolve_canonical_repo_root(root)
    charter_dir = canonical_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    document = {"governance": yaml.load(governance_body)}
    with (charter_dir / "charter.yaml").open("w", encoding="utf-8") as fh:
        yaml.dump(document, fh)


@pytest.fixture(autouse=True)
def _reset_warn_once_cache() -> None:
    """Reset the CR-01 warn-once gate so tests don't leak state (precedent:
    ``resolve_canonical_repo_root.cache_clear()`` in ``tests/charter/
    conftest.py``)."""
    _warn_legacy_governance_key_once.cache_clear()
    yield
    _warn_legacy_governance_key_once.cache_clear()


def test_governance_doctrine_key_warns_and_maps(tmp_path: Path) -> None:
    """The legacy ``doctrine:`` key is read, warned once, and mapped to ``charter``."""
    _write_governance_section(
        tmp_path,
        "doctrine:\n  selected_paradigms: []\n  selected_directives:\n    - DIRECTIVE_001\n  selected_tactics: []\n  template_set: software-dev-default\n",
    )

    with pytest.warns(LegacyGovernanceKeyWarning):
        governance = load_governance_config(tmp_path)

    # The legacy key's content is faithfully mapped onto the canonical field.
    assert governance.charter.selected_directives == ["DIRECTIVE_001"]
    assert governance.charter.template_set == "software-dev-default"

    # Warn-once: a second read within the same process does not warn again.
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        load_governance_config(tmp_path)
    legacy_warnings = [w for w in recorded if issubclass(w.category, LegacyGovernanceKeyWarning)]
    assert legacy_warnings == []


def test_governance_charter_key_canonical(tmp_path: Path) -> None:
    """The canonical ``charter:`` key reads with no deprecation warning."""
    _write_governance_section(
        tmp_path,
        "charter:\n  selected_paradigms: []\n  selected_directives:\n    - DIRECTIVE_001\n  selected_tactics: []\n  template_set: software-dev-default\n",
    )

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        governance = load_governance_config(tmp_path)

    legacy_warnings = [w for w in recorded if issubclass(w.category, LegacyGovernanceKeyWarning)]
    assert legacy_warnings == []
    assert governance.charter.selected_directives == ["DIRECTIVE_001"]
    assert governance.charter.template_set == "software-dev-default"


def test_governance_both_keys_present_prefers_canonical_silently(tmp_path: Path) -> None:
    """When both keys are present the canonical value wins with no warning
    (an operator who already migrated should not be nagged about stale
    legacy data they no longer read)."""
    _write_governance_section(
        tmp_path,
        "doctrine:\n  template_set: legacy-set\ncharter:\n  template_set: canonical-set\n",
    )

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        governance = load_governance_config(tmp_path)

    legacy_warnings = [w for w in recorded if issubclass(w.category, LegacyGovernanceKeyWarning)]
    assert legacy_warnings == []
    assert governance.charter.template_set == "canonical-set"
