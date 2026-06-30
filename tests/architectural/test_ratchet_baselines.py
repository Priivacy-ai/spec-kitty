"""Meta-test for architectural ratchet baselines (Slice F WP01, FR-110/FR-111).

This test is the canonical executable contract for the burn-down policy
pinned by C-004 / C-006 of the Slice F charter pack. It loads
``tests/architectural/_baselines.yaml`` and compares the recorded
per-test, per-category allowlist size against the live size of each
gated test module's allowlist symbol.

Failure semantics
-----------------
* **Growth above baseline** -> ``pytest.fail`` with a remediation hint
  (either remove the new allowlist entry or edit ``_baselines.yaml`` in
  the same PR with a justification comment).
* **Shrinkage below baseline** -> ``warnings.warn`` (informational; the
  ratchet does not fail on shrinkage so legitimate cleanup is not
  blocked, but it nudges the PR author to lock in the new lower bound).

The full schema and per-test invariants live in
``kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/contracts/
ratchet-baseline-format.md``.

ATDD anchors (per ``atdd-coverage.md``):

* Scenario 6: ``test_growing_an_allowlist_above_baseline_fails``
* AC-6:       ``test_baseline_file_exists_with_required_keys``
              AND ``test_growth_fails_shrinkage_warns``
* AC-7:       ``test_no_dead_modules.test_category_7_grandfathered_at_most_seven_entries``
              (lives in the gated test module itself; see T007)

This file is committed RED in the WP01 T001 commit and turns GREEN as
T002-T007 land the baseline file, the per-category refactor, the three
Cat-7 deletions, and the Cat-7 baseline at 7.
"""

from __future__ import annotations

import importlib
import warnings
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from pydantic import BaseModel

pytestmark = [pytest.mark.architectural]


# ---------------------------------------------------------------------------
# BaselinesFile Pydantic model (FR-141 / ratchet-baseline-format.md)
# ---------------------------------------------------------------------------
# This model is referenced by the FR-140 round-trip gate in
# ``tests/contract/test_example_round_trip.py`` via:
#   pydantic_model: tests.architectural.test_ratchet_baselines.BaselinesFile
#
# The schema is intentionally permissive at the top level (dict[str, Any])
# so it tolerates new per-test entries without requiring changes here.
# The individual values MUST be non-negative integers or mappings of them.
# ---------------------------------------------------------------------------

class _PerCategorySection(BaseModel):
    """A section with per-category integer baselines."""

    model_config = {"extra": "allow"}

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> _PerCategorySection:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if not isinstance(v, int) or v < 0:
                    raise ValueError(
                        f"Per-category baseline {k!r} must be a non-negative integer; got {v!r}"
                    )
        return super().model_validate(obj, **kwargs)


class BaselinesFile(BaseModel):
    """Pydantic model for ``tests/architectural/_baselines.yaml``.

    Each top-level key names a gated test module.  Values are either a
    single integer (for tests with one allowlist) or a mapping of
    per-category integer baselines (for tests with categorised allowlists).

    The schema is permissive (``extra="allow"``) to tolerate future gated
    test additions without requiring changes here.

    Slice F FR-141 / ratchet-baseline-format.md.
    """

    model_config = {"extra": "allow"}

    test_no_dead_modules: dict[str, int]
    test_migration_chain_integrity: dict[str, int]
    test_runtime_charter_doctrine_boundary: dict[str, int]
    test_auth_transport_singleton: dict[str, int]
    test_compat_shims: dict[str, int]
    test_example_round_trip: dict[str, int]
    test_all_declarations_required: dict[str, int]


_BASELINES_PATH = Path(__file__).parent / "_baselines.yaml"

# Required top-level keys. Each names a test module whose ratchet is
# tracked. Sub-keys (per-category integers OR a single integer) are
# defined by the contract.
_REQUIRED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "test_no_dead_modules",
        "test_migration_chain_integrity",
        "test_runtime_charter_doctrine_boundary",
        "test_auth_transport_singleton",
        "test_compat_shims",
        "test_example_round_trip",
        "test_all_declarations_required",
    }
)

# Per-category sub-keys for test_no_dead_modules (FR-112 refactor).
_REQUIRED_NO_DEAD_MODULES_CATEGORIES: frozenset[str] = frozenset(
    {
        "category_1_auto_discovered_migrations",
        "category_2_build_schema_generators",
        "category_3_external_cli_entrypoints",
        "category_4_backcompat_shims",
        "category_5_wp_in_flight_adapters",
        "category_6_frozen_runtime_reexports",
        "category_7_grandfathered_orphans",
    }
)


def _load_baselines() -> dict[str, Any]:
    """Load and parse the baselines YAML. Raise FileNotFoundError if missing."""
    if not _BASELINES_PATH.exists():
        raise FileNotFoundError(
            f"`tests/architectural/_baselines.yaml` is missing. This file is a "
            f"binding ratchet artefact per C-004 (Slice F charter pack). Restore "
            f"it from the previous commit OR run the WP01 bootstrap. Expected at: "
            f"{_BASELINES_PATH}"
        )
    text = _BASELINES_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(
            f"`tests/architectural/_baselines.yaml` is malformed: top level must "
            f"be a mapping, got {type(data).__name__}."
        )
    return data


def _import_module_attr(module_dotted: str, attr_name: str) -> frozenset[Any]:
    """Import *module_dotted* and return its *attr_name* attribute.

    Used to look up gated test modules' allowlist symbols by name.
    """
    module = importlib.import_module(module_dotted)
    if not hasattr(module, attr_name):
        raise AttributeError(
            f"Module `{module_dotted}` does not export `{attr_name}`. The "
            f"FR-112 per-category refactor must publish this attribute at "
            f"module scope so the ratchet baseline meta-test can introspect "
            f"its size."
        )
    return cast("frozenset[Any]", getattr(module, attr_name))


def test_baseline_file_exists_with_required_keys() -> None:
    """AC-6: `_baselines.yaml` must exist with one section per gated test.

    The schema is defined in
    ``kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/contracts/
    ratchet-baseline-format.md`` and pinned by C-004.
    """
    data = _load_baselines()

    missing = _REQUIRED_TOP_LEVEL_KEYS - set(data.keys())
    assert not missing, (
        f"`_baselines.yaml` is missing required top-level key(s): "
        f"{sorted(missing)}. Each gated test module's ratchet must be "
        f"recorded so the meta-test can compare current size against the "
        f"baseline."
    )

    # test_no_dead_modules must carry per-category sub-keys (FR-112).
    nd_section = data["test_no_dead_modules"]
    assert isinstance(nd_section, dict), (
        "`_baselines.yaml::test_no_dead_modules` must be a mapping of "
        "per-category integers (FR-112 refactor)."
    )
    missing_cats = _REQUIRED_NO_DEAD_MODULES_CATEGORIES - set(nd_section.keys())
    assert not missing_cats, (
        f"`_baselines.yaml::test_no_dead_modules` is missing per-category "
        f"key(s): {sorted(missing_cats)}. The FR-112 refactor splits the "
        f"single `_ALLOWLIST` into per-category frozensets so growth in "
        f"Cat-1 (auto-discovered migrations) cannot disguise Cat-7 "
        f"grandfathered-orphan regression."
    )


def test_growing_an_allowlist_above_baseline_fails() -> None:
    """Scenario 6 / AC-6: any ratchet growing above its baseline fails this test.

    The test imports each gated module dynamically, reads the live
    allowlist size, and compares it against the baseline integer in
    ``_baselines.yaml``. ``current > baseline`` => ``pytest.fail``.
    Shrinkage (``current < baseline``) is handled by the
    ``test_growth_fails_shrinkage_warns`` test below.
    """
    data = _load_baselines()
    growth_failures: list[str] = []

    # test_no_dead_modules: per-category comparison.
    nd_cats = data["test_no_dead_modules"]
    nd_module = "tests.architectural.test_no_dead_modules"
    per_category_attrs = {
        "category_1_auto_discovered_migrations": "_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS",
        "category_2_build_schema_generators": "_CATEGORY_2_BUILD_SCHEMA_GENERATORS",
        "category_3_external_cli_entrypoints": "_CATEGORY_3_EXTERNAL_CLI_ENTRYPOINTS",
        "category_4_backcompat_shims": "_CATEGORY_4_BACKCOMPAT_SHIMS",
        "category_5_wp_in_flight_adapters": "_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS",
        "category_6_frozen_runtime_reexports": "_CATEGORY_6_FROZEN_RUNTIME_REEXPORTS",
        "category_7_grandfathered_orphans": "_CATEGORY_7_GRANDFATHERED_ORPHANS",
    }
    for cat_key, attr_name in per_category_attrs.items():
        baseline = nd_cats[cat_key]
        current = len(_import_module_attr(nd_module, attr_name))
        if current > baseline:
            growth_failures.append(
                f"  - test_no_dead_modules.{cat_key}: baseline={baseline} "
                f"current={current}. Remove the new entry OR edit "
                f"_baselines.yaml from {baseline} to {current} with a "
                f"justification comment in the PR."
            )

    # Single-integer ratchets.
    single_baselines: list[tuple[str, str, str, int]] = [
        (
            "test_migration_chain_integrity",
            "tests.architectural.test_migration_chain_integrity",
            "_KNOWN_LINE_JUMPS",
            data["test_migration_chain_integrity"]["known_line_jumps"],
        ),
        (
            "test_runtime_charter_doctrine_boundary",
            "tests.architectural.test_runtime_charter_doctrine_boundary",
            "_BASELINE_ALLOWLIST",
            data["test_runtime_charter_doctrine_boundary"]["baseline_allowlist"],
        ),
        (
            "test_auth_transport_singleton",
            "tests.architectural.test_auth_transport_singleton",
            "_TRANSPORT_ALLOWLIST",
            data["test_auth_transport_singleton"]["allowed_direct_httpx_files"],
        ),
        (
            "test_compat_shims",
            "tests.architectural.test_compat_shims",
            "_ADAPTER_FILES",
            data["test_compat_shims"]["pure_shim_files"],
        ),
        # FR-141: legacy contract allowlist for the round-trip gate.
        (
            "test_example_round_trip",
            "tests.contract.test_example_round_trip",
            "_LEGACY_CONTRACT_ALLOWLIST",
            data["test_example_round_trip"]["legacy_contract_allowlist"],
        ),
        # #2255: permanently-non-executable ``# round-trip: skip:`` blocks. Growth
        # is visible (a new skip fails the ratchet until the baseline is bumped);
        # unlike the legacy allowlist these are permanent (no shrink mandate).
        (
            "test_example_round_trip",
            "tests.contract.test_example_round_trip",
            "_SKIP_MARKED_BLOCKS",
            data["test_example_round_trip"]["skip_marker_blocks"],
        ),
    ]
    for label, module_dotted, attr_name, baseline in single_baselines:
        current = len(_import_module_attr(module_dotted, attr_name))
        if current > baseline:
            growth_failures.append(
                f"  - {label}.{attr_name}: baseline={baseline} current={current}. "
                f"Remove the new entry OR edit _baselines.yaml from {baseline} "
                f"to {current} with a justification comment in the PR."
            )

    assert not growth_failures, (
        "Ratchet baseline GROWTH detected (FR-111 violation). The following "
        "allowlists exceeded their pinned baselines:\n"
        + "\n".join(growth_failures)
        + "\n\nPer the burn-down policy (Slice F C-004), each growth requires "
        "a one-line YAML diff to _baselines.yaml in the same PR plus a "
        "`# justification:` comment naming why the growth is acceptable."
    )


def test_growth_fails_shrinkage_warns() -> None:
    """AC-6: shrinkage below baseline emits a pytest warning, never fails.

    The warning nudges the PR author to lock in the new lower bound by
    editing ``_baselines.yaml`` in the same PR. Shrinkage is good news
    (a previously-grandfathered orphan got wired or deleted) so it must
    not block CI.
    """
    data = _load_baselines()
    shrinkage_messages: list[str] = []

    # Per-category for test_no_dead_modules.
    nd_cats = data["test_no_dead_modules"]
    nd_module = "tests.architectural.test_no_dead_modules"
    per_category_attrs = {
        "category_1_auto_discovered_migrations": "_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS",
        "category_2_build_schema_generators": "_CATEGORY_2_BUILD_SCHEMA_GENERATORS",
        "category_3_external_cli_entrypoints": "_CATEGORY_3_EXTERNAL_CLI_ENTRYPOINTS",
        "category_4_backcompat_shims": "_CATEGORY_4_BACKCOMPAT_SHIMS",
        "category_5_wp_in_flight_adapters": "_CATEGORY_5_WP_IN_FLIGHT_ADAPTERS",
        "category_6_frozen_runtime_reexports": "_CATEGORY_6_FROZEN_RUNTIME_REEXPORTS",
        "category_7_grandfathered_orphans": "_CATEGORY_7_GRANDFATHERED_ORPHANS",
    }
    for cat_key, attr_name in per_category_attrs.items():
        baseline = nd_cats[cat_key]
        current = len(_import_module_attr(nd_module, attr_name))
        if current < baseline:
            shrinkage_messages.append(
                f"test_no_dead_modules.{cat_key}: baseline={baseline} "
                f"current={current}. Edit _baselines.yaml to lock in the "
                f"shrinkage."
            )

    # Single-integer ratchets.
    single_baselines: list[tuple[str, str, str, int]] = [
        (
            "test_migration_chain_integrity",
            "tests.architectural.test_migration_chain_integrity",
            "_KNOWN_LINE_JUMPS",
            data["test_migration_chain_integrity"]["known_line_jumps"],
        ),
        (
            "test_runtime_charter_doctrine_boundary",
            "tests.architectural.test_runtime_charter_doctrine_boundary",
            "_BASELINE_ALLOWLIST",
            data["test_runtime_charter_doctrine_boundary"]["baseline_allowlist"],
        ),
        (
            "test_auth_transport_singleton",
            "tests.architectural.test_auth_transport_singleton",
            "_TRANSPORT_ALLOWLIST",
            data["test_auth_transport_singleton"]["allowed_direct_httpx_files"],
        ),
        (
            "test_compat_shims",
            "tests.architectural.test_compat_shims",
            "_ADAPTER_FILES",
            data["test_compat_shims"]["pure_shim_files"],
        ),
        # FR-141: legacy contract allowlist for the round-trip gate.
        (
            "test_example_round_trip",
            "tests.contract.test_example_round_trip",
            "_LEGACY_CONTRACT_ALLOWLIST",
            data["test_example_round_trip"]["legacy_contract_allowlist"],
        ),
        # #2255: permanently-non-executable ``# round-trip: skip:`` blocks. Growth
        # is visible (a new skip fails the ratchet until the baseline is bumped);
        # unlike the legacy allowlist these are permanent (no shrink mandate).
        (
            "test_example_round_trip",
            "tests.contract.test_example_round_trip",
            "_SKIP_MARKED_BLOCKS",
            data["test_example_round_trip"]["skip_marker_blocks"],
        ),
    ]
    for label, module_dotted, attr_name, baseline in single_baselines:
        current = len(_import_module_attr(module_dotted, attr_name))
        if current < baseline:
            shrinkage_messages.append(
                f"{label}.{attr_name}: baseline={baseline} current={current}. "
                f"Edit _baselines.yaml to lock in the shrinkage."
            )

    # Emit warnings (one per shrinkage) so pytest surfaces them.
    for msg in shrinkage_messages:
        warnings.warn(
            f"Ratchet baseline SHRINKAGE (informational, not failing): {msg}",
            UserWarning,
            stacklevel=2,
        )

    # This test never fails on shrinkage. It exists to (a) emit the
    # warning surface, and (b) assert that the contract API holds (i.e.
    # the baselines load and the ratchets are introspectable).
    assert isinstance(data, dict)
