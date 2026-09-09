"""ATDD: pending-batch-a fail-closed routing for meta.json corruption (FR-007 / #3162).

Mission-runtime half of the ``pending-batch-a`` ATDD set, split out of
``tests/specify_cli/test_meta_fail_closed_pending_batch_a.py`` (PR #4008 fix
round): CI module shards select tests by DIRECTORY (the registry's
``test_dirs``), and top-level ``tests/specify_cli/`` is in no module's
``test_dirs`` — so tests living there never execute in CI and their coverage
of the changed critical-path lines (``src/mission_runtime/**`` is a
diff-cover CRITICAL_PATHS root) was invisible to the ci-aggregate PR gate.
This file lives in ``tests/mission_runtime/``, which the ``execution_context``
module runs with ``mission_runtime`` in its ``cov_targets``.

Exercises the REAL entry points of the three divergent-wrapper probes in
``mission_runtime/resolution.py`` named by the ``pending-batch-a`` bucket —
not ``load_meta``/``load_meta_fail_closed`` directly — so this test is
genuinely red if a routed call site regresses back to the unwrapped
``mission_metadata.load_meta`` call (a raw ``ValueError`` escaping to the
caller). Degrade sites: the typed :class:`MissionMetaReadError` is absorbed
into each probe's historical sentinel answer, mirroring the
``lifecycle_phase._read_baseline_merge_commit`` carve-out.

Both corrupt-meta and non-dict-meta cases are driven — the two shapes
``mission_metadata._parse_meta_text`` treats as "malformed" (json.JSONDecodeError
and non-object top level).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

#: Corrupt: truncated, syntactically invalid JSON — genuinely unparseable.
_CORRUPT_META = '{"mission_id": "01JABCDEFGHJKMNPQRSTVWXYZ", '
#: Non-dict: parses cleanly but the top level is a list, not an object.
_NON_DICT_META = "[1, 2, 3]"

_SLUG = "probe-mission"

_CASES = [_CORRUPT_META, _NON_DICT_META]
_CASE_IDS = ["corrupt-json", "non-dict-json"]


def _seed(root: Path, meta_text: str) -> Path:
    """Create a minimal mission directory with a raw ``meta.json`` body."""
    mission_dir = root / "kitty-specs" / _SLUG
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "meta.json").write_text(meta_text, encoding="utf-8")
    return mission_dir


# ---------------------------------------------------------------------------
# mission_runtime/resolution.py — the three divergent-wrapper probes degrade
# to their historical sentinels via the typed error (never a raw ValueError).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_mid8_from_primary_meta_degrades_to_empty(tmp_path: Path, meta_text: str) -> None:
    """Corrupt primary meta → ``""`` (the historical malformed→empty degrade)."""
    from mission_runtime.resolution import _mid8_from_primary_meta

    _seed(tmp_path, meta_text)
    assert _mid8_from_primary_meta(tmp_path, _SLUG) == ""


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_resolve_coordination_branch_degrades_to_none(tmp_path: Path, meta_text: str) -> None:
    """Corrupt primary meta → ``None`` (coordination topology undeclared)."""
    from mission_runtime.resolution import _resolve_coordination_branch

    _seed(tmp_path, meta_text)
    assert _resolve_coordination_branch(tmp_path, _SLUG) is None


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_resolve_mission_id_degrades_to_legacy_sentinel(tmp_path: Path, meta_text: str) -> None:
    """Corrupt primary meta → the ``legacy-<slug>`` bootstrap sentinel."""
    from mission_runtime.resolution import _resolve_mission_id

    _seed(tmp_path, meta_text)
    assert _resolve_mission_id(tmp_path, _SLUG) == f"legacy-{_SLUG}"
