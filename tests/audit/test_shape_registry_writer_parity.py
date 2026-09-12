"""Anti-drift guard for the ``meta.json`` audit shape registry (#2696, FR-011 / NFR-004).

The audit registry's ``meta.json`` known-key set MUST be derived from the
canonical mission-metadata writer schema (``MissionMetaRequired`` +
``MissionMetaOptional``) plus the coordination write-path keys — never a
hand-rolled second copy that can silently drift and start reporting canonical
keys as ``UNKNOWN_SHAPE`` false positives.

These tests fail loudly the moment the writer schema grows a field the audit
registry does not know about, so the two can never re-diverge (NFR-004).
"""

from __future__ import annotations

import pytest

from specify_cli.audit.shape_registry import (
    KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT,
    META_COORDINATION_KEYS,
)
from specify_cli.mission_metadata import MissionMetaOptional, MissionMetaRequired

pytestmark = [pytest.mark.unit]


def _writer_keys() -> frozenset[str]:
    return frozenset(MissionMetaRequired.__annotations__) | frozenset(
        MissionMetaOptional.__annotations__
    )


def test_every_writer_key_is_a_known_audit_key() -> None:
    """Writer keys ⊆ audit known keys — the anti-drift invariant (NFR-004)."""
    audit_keys = KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT["meta.json"]
    missing = _writer_keys() - audit_keys
    assert missing == set(), (
        "meta.json writer schema keys missing from the audit shape registry "
        f"(would be reported as UNKNOWN_SHAPE): {sorted(missing)}"
    )


def test_coordination_write_path_keys_are_known_audit_keys() -> None:
    """The four coordination write-path keys are part of the known set (FR-011)."""
    audit_keys = KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT["meta.json"]
    expected = frozenset({"coordination_branch", "topology", "flattened", "pr_bound"})
    assert expected == META_COORDINATION_KEYS
    assert audit_keys >= META_COORDINATION_KEYS


def test_identity_keys_remain_known_audit_keys() -> None:
    """mission_id / mission_number stay known (identity model 083+, not in the TypedDicts)."""
    audit_keys = KNOWN_TOP_LEVEL_KEYS_BY_ARTIFACT["meta.json"]
    assert {"mission_id", "mission_number"} <= audit_keys
