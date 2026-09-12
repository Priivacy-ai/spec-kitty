"""ATDD: pending-batch-a fail-closed routing for meta.json corruption (FR-007 / #3162).

Runtime/next half of the ``pending-batch-a`` ATDD set, split out of
``tests/specify_cli/test_meta_fail_closed_pending_batch_a.py`` (PR #4008 fix
round): CI module shards select tests by DIRECTORY (the registry's
``test_dirs``), and top-level ``tests/specify_cli/`` is in no module's
``test_dirs`` — so tests living there never execute in CI and their coverage
of the changed critical-path lines (``src/runtime/next/**`` is a diff-cover
CRITICAL_PATHS root) was invisible to the ci-aggregate PR gate. This file
lives in ``tests/runtime/``, which the ``execution_context`` module runs with
``runtime.next`` in its ``cov_targets``.

Exercises the REAL entry points of the two ``runtime/next`` sites the
``pending-batch-a`` bucket named — not ``load_meta``/``load_meta_fail_closed``
directly — so this test is genuinely red if a routed call site regresses back
to the unwrapped ``mission_metadata.load_meta`` call. Typed-raise sites: a
corrupt or non-object ``meta.json`` surfaces the typed
:class:`MissionMetaReadError`, never a raw ``ValueError``.

Both corrupt-meta and non-dict-meta cases are driven — the two shapes
``mission_metadata._parse_meta_text`` treats as "malformed" (json.JSONDecodeError
and non-object top level).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.paths import MissionMetaReadError

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
# runtime/next — route-unwrapped sites now surface the typed error.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_planner_resolve_workflow_raises_typed(tmp_path: Path, meta_text: str) -> None:
    """``planner._resolve_workflow_for_mission`` raises MissionMetaReadError.

    A raw ``ValueError`` would also satisfy ``pytest.raises(Exception)``;
    ``MissionMetaReadError`` is a ``RuntimeError`` subclass, NOT a
    ``ValueError``, so this genuinely fails on a regression to the unwrapped
    ``load_meta(...)`` call.
    """
    from runtime.next._internal_runtime.planner import _resolve_workflow_for_mission

    mission_dir = _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        _resolve_workflow_for_mission(mission_dir)


@pytest.mark.parametrize("meta_text", _CASES, ids=_CASE_IDS)
def test_runtime_bridge_workflow_template_raises_typed(tmp_path: Path, meta_text: str) -> None:
    """``runtime_bridge_io._workflow_runtime_template`` raises MissionMetaReadError.

    The corrupt meta is hit either at this module's own routed read or at the
    read-side seam it resolves through (``read_primary_meta``, routed in the
    same pass) — both raise the same typed error, never a raw ``ValueError``.
    """
    from runtime.next.runtime_bridge_io import _workflow_runtime_template

    _seed(tmp_path, meta_text)
    with pytest.raises(MissionMetaReadError, match="fail-closed"):
        _workflow_runtime_template(_SLUG, "software-dev", tmp_path, "software-dev")
