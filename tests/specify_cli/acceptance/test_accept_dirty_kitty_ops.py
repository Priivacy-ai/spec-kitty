"""T001 / T003 / T004 — dirty-tree gate convergence for kitty-ops orphans (FR-001 / #2251).

A stray ``kitty-ops/<ULID>.jsonl`` Op-record orphan must NOT block any of the
four dirty-tree gates.  This module proves:

1. **RED evidence** (T001): the tests were failing on pre-fix code (see commit
   message for the captured output — the assertions below drove the fix).
2. **GREEN (post-fix)**: after T002–T004 all assertions pass.
3. **Counter-contracts**: genuine mission dirt STILL blocks all gates (NFR-003 /
   G-5 invariant).
4. **Tightness**: ``kitty-ops/notes.txt`` (non-ULID basename) is NOT excluded.

Gates covered here:
  - Accept gate:  ``acceptance._accept_dirty_gate`` (T003)
  - Merge gate:   ``merge.git_probes._classify_porcelain_lines`` (T004 arm 1)
  - Review gate:  ``review.dirty_classifier._is_benign`` / ``classify_dirty_paths``
                  (T004 arm 2)

The record-analysis gate (``mission._enforce_analysis_report_write_preflight``)
is covered by ``tests/mission_runtime/test_self_bookkeeping_allowlist.py``
(T005 / original FR-003 suite).

Contract G-5 (data-model.md): the self-bookkeeping allowlist is DISJOINT from
planning artifacts.  A stale ``spec.md`` is planning dirt and MUST still block.

See also: #2102 (original allowlist), #1914 (no-op-stable gates umbrella).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.acceptance import _accept_dirty_gate
from specify_cli.merge.git_probes import _classify_porcelain_lines
from specify_cli.review.dirty_classifier import _is_benign, classify_dirty_paths

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Production-shaped 26-char Crockford base32 ULID — valid against the
# invocation-record ULID regex ``[0-9A-HJKMNP-TV-Z]{26}`` (no I, L, O, U).
_OP_ULID = "01KWD0V5ABCDEFGHJKMNPQRSTV"
_OP_JSONL = f"kitty-ops/{_OP_ULID}.jsonl"

# A real mission-relevant dirty path — must block at ALL gates (G-5 / NFR-003).
_REAL_DIRT = "src/specify_cli/acceptance/__init__.py"

# Mission slug used when calling the accept gate (minimal fixture — no dir needed).
_FEATURE = "reliability-papercut-sweep-01KWD0V5"


# ---------------------------------------------------------------------------
# Accept gate  (acceptance.__init__._accept_dirty_gate)
# ---------------------------------------------------------------------------


class TestAcceptGateKittyOps:
    """_accept_dirty_gate must exclude kitty-ops orphans, not real dirt.

    Red-first evidence: before T003 fix, ``_call_accept_gate([_OP_JSONL])``
    returned ``[' M kitty-ops/...jsonl']`` (non-empty → gate blocked).
    """

    def _call_accept_gate(
        self, tmp_path: Path, dirty_paths: list[str]
    ) -> list[str]:
        """Drive _accept_dirty_gate with fabricated porcelain lines.

        tmp_path serves as repo_root.  The mission has no meta.json, so
        topology degrades to SINGLE_BRANCH (non-coordination) — the
        coordination-residue filter is a no-op and only the shared
        is_self_bookkeeping_path arm filters the kitty-ops line.
        """
        # Porcelain v1 format: two status chars + space + path
        raw_lines = [f" M {p}" for p in dirty_paths]
        feature_dir = tmp_path / "kitty-specs" / _FEATURE
        return _accept_dirty_gate(
            raw_lines,
            repo_root=tmp_path,
            feature=_FEATURE,
            feature_dir=feature_dir,
            read_feature_dir=feature_dir,
            status_feature_dir=feature_dir,
        )

    def test_kitty_ops_orphan_does_not_block_accept_gate(
        self, tmp_path: Path
    ) -> None:
        """Accept gate must NOT block on a kitty-ops Op-record orphan (#2251)."""
        result = self._call_accept_gate(tmp_path, [_OP_JSONL])
        assert result == [], (
            f"Accept gate must not block on kitty-ops orphan; got {result!r}"
        )

    def test_real_dirt_still_blocks_accept_gate(self, tmp_path: Path) -> None:
        """Counter-contract (G-5): genuine source dirt MUST still block."""
        result = self._call_accept_gate(tmp_path, [_REAL_DIRT])
        assert len(result) == 1, (
            f"Accept gate must still block on real dirt; result was {result!r}"
        )

    def test_non_ulid_kitty_ops_does_not_bypass_accept_gate(
        self, tmp_path: Path
    ) -> None:
        """Tightness: ``kitty-ops/notes.txt`` (non-ULID) must still block."""
        non_ulid = "kitty-ops/notes.txt"
        result = self._call_accept_gate(tmp_path, [non_ulid])
        assert len(result) == 1, (
            f"Accept gate must block on non-ULID kitty-ops path; got {result!r}"
        )


# ---------------------------------------------------------------------------
# Merge gate  (merge.git_probes._classify_porcelain_lines)
# ---------------------------------------------------------------------------


class TestMergeGateKittyOps:
    """_classify_porcelain_lines must exclude kitty-ops orphans, not real dirt.

    Red-first evidence: before T004 fix, ``_call_merge_gate([_OP_JSONL])``
    returned offending ``[' M kitty-ops/...jsonl']`` (non-empty → gate blocked).
    """

    def _call_merge_gate(self, dirty_paths: list[str]) -> tuple[list[str], int]:
        """Drive _classify_porcelain_lines with fabricated porcelain lines."""
        lines = [f" M {p}" for p in dirty_paths]
        return _classify_porcelain_lines(lines, expected_paths=set())

    def test_kitty_ops_orphan_does_not_block_merge_gate(self) -> None:
        """Merge gate must NOT block on a kitty-ops Op-record orphan (#2251)."""
        offending, _skipped = self._call_merge_gate([_OP_JSONL])
        assert offending == [], (
            f"Merge gate must not block on kitty-ops orphan; offending={offending!r}"
        )

    def test_real_dirt_still_blocks_merge_gate(self) -> None:
        """Counter-contract (G-5): genuine source dirt MUST still block."""
        offending, _skipped = self._call_merge_gate([_REAL_DIRT])
        assert len(offending) == 1, (
            f"Merge gate must still block on real dirt; offending={offending!r}"
        )

    def test_non_ulid_kitty_ops_does_not_bypass_merge_gate(self) -> None:
        """Tightness: ``kitty-ops/notes.txt`` (non-ULID) must still block."""
        non_ulid = "kitty-ops/notes.txt"
        offending, _skipped = self._call_merge_gate([non_ulid])
        assert len(offending) == 1, (
            f"Merge gate must block on non-ULID kitty-ops path; got {offending!r}"
        )


# ---------------------------------------------------------------------------
# Review / implement-handoff gate  (review.dirty_classifier)
# ---------------------------------------------------------------------------


class TestReviewGateKittyOps:
    """_is_benign / classify_dirty_paths must treat kitty-ops orphans as benign.

    Red-first evidence: before T004 fix, ``_is_benign(_OP_JSONL, 'WP01')``
    returned False (blocking), and classify_dirty_paths put the orphan in
    ``blocking`` not ``benign``.
    """

    _WP_ID = "WP01"

    def test_kitty_ops_orphan_is_benign(self) -> None:
        """Review gate must treat a kitty-ops Op-record orphan as benign (#2251)."""
        assert _is_benign(_OP_JSONL, self._WP_ID), (
            f"_is_benign must return True for kitty-ops orphan; path={_OP_JSONL!r}"
        )

    def test_real_dirt_is_not_benign(self) -> None:
        """Counter-contract (G-5): real source dirt is NOT benign."""
        assert not _is_benign(_REAL_DIRT, self._WP_ID), (
            f"Real dirt must not be benign; path={_REAL_DIRT!r}"
        )

    def test_classify_dirty_paths_kitty_ops_orphan_in_benign(self) -> None:
        """classify_dirty_paths must route kitty-ops orphan to benign bucket."""
        blocking, benign = classify_dirty_paths(
            [_OP_JSONL], wp_id=self._WP_ID, mission_slug=_FEATURE
        )
        assert _OP_JSONL in benign, (
            f"Kitty-ops orphan must be benign; blocking={blocking!r}, benign={benign!r}"
        )
        assert _OP_JSONL not in blocking

    def test_classify_dirty_paths_real_dirt_in_blocking(self) -> None:
        """Counter-contract: classify_dirty_paths puts real dirt in blocking."""
        blocking, benign = classify_dirty_paths(
            [_REAL_DIRT], wp_id=self._WP_ID, mission_slug=_FEATURE
        )
        assert _REAL_DIRT in blocking, (
            f"Real dirt must be blocking; blocking={blocking!r}, benign={benign!r}"
        )

    def test_non_ulid_kitty_ops_path_is_not_benign(self) -> None:
        """Tightness: kitty-ops/notes.txt (non-ULID basename) is NOT benign."""
        non_ulid = "kitty-ops/notes.txt"
        assert not _is_benign(non_ulid, self._WP_ID), (
            f"Non-ULID kitty-ops path must NOT be benign; path={non_ulid!r}"
        )
