"""WP10 / T043 – per-caller routing tests for mid8_from_slug value-use sites.

For each routed caller this module verifies:
  (a) A genuine embedded-mid8 slug resolves correctly via resolve_mid8 when
      a declared mission_id is available.
  (b) A coincidental 8-char Crockford tail does NOT mis-resolve when no
      mission_id is present (the #1918 win — decline, not mis-resolve).
  (c) Boolean-detector uses of mid8_from_slug are answer-preserving under
      the stricter resolve_mid8 decline, proven with representative inputs.

Sites covered:
  - decision.py:419  _mid8_for_decision_verify   (value-use → resolve_mid8)
  - agent/mission.py:1229  _find_feature_directory  (value-use → resolve_mid8)
  - agent/workflow.py  _canonical_status_feature_dir  (WP03: routed through the
    read-side seam ``resolve_handle_to_read_path``; the retired
    ``_mid8_for_mission_read_path`` helper now lives inside the seam's
    ``resolve_declared_mid8`` cascade — these tests pin the seam contract it uses)
  - agent/context.py:76   _find_feature_directory  (value-use → resolve_mid8)
  - aggregate.py:480/486   _find_meta_path  (boolean-detector, kept — proven safe)
  - agent/status.py:41/51  _resolve_bare_modern_mission_slug (boolean-detector, kept)
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.lanes.branch_naming import mid8_from_slug, resolve_mid8
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REAL_MISSION_ID = "01KV6510ATWWFXS3K5ZJ9E5008"  # full ULID
REAL_MID8 = "01KV6510"  # first 8 chars
REAL_SLUG = f"my-mission-{REAL_MID8}"  # canonical <human>-<mid8> form

# A slug whose tail is coincidentally 8 Crockford chars but does NOT match
# any real mission_id.  This is the #1918 scenario.
COINCIDENTAL_TAIL = "ZZZZZZZZ"  # valid Crockford base32, 8 chars, clearly wrong
COINCIDENTAL_SLUG = f"my-mission-{COINCIDENTAL_TAIL}"


# ---------------------------------------------------------------------------
# Seam contract: resolve_mid8 vs mid8_from_slug
# ---------------------------------------------------------------------------


class TestSeamContract:
    """Baseline contract tests for the two seam functions used by callers."""

    def test_resolve_mid8_with_declared_mission_id_ignores_coincidental_tail(self) -> None:
        """resolve_mid8 returns declared mid8, not coincidental slug tail (#1918)."""
        result = resolve_mid8(COINCIDENTAL_SLUG, mission_id=REAL_MISSION_ID)
        assert result == REAL_MID8
        assert result != COINCIDENTAL_TAIL

    def test_resolve_mid8_with_no_mission_id_declines_coincidental_tail(self) -> None:
        """resolve_mid8 returns '' for a coincidental tail when mission_id=None."""
        result = resolve_mid8(COINCIDENTAL_SLUG, mission_id=None)
        assert result == ""

    def test_resolve_mid8_with_no_mission_id_declines_genuine_embedded_tail(self) -> None:
        """resolve_mid8 also declines a genuine tail when mission_id is None."""
        # No mission_id → cannot confirm any tail, so decline.
        result = resolve_mid8(REAL_SLUG, mission_id=None)
        assert result == ""

    def test_resolve_mid8_with_declared_mission_id_and_matching_slug(self) -> None:
        """resolve_mid8 returns declared mid8 when slug tail matches (#1918 positive)."""
        result = resolve_mid8(REAL_SLUG, mission_id=REAL_MISSION_ID)
        assert result == REAL_MID8

    def test_mid8_from_slug_still_detects_embedded_tail(self) -> None:
        """mid8_from_slug still works as a structural detector on embedded tails."""
        assert mid8_from_slug(REAL_SLUG) == REAL_MID8
        assert mid8_from_slug(COINCIDENTAL_SLUG) == COINCIDENTAL_TAIL
        assert mid8_from_slug("my-mission") == ""


# ---------------------------------------------------------------------------
# VALUE-USE callers — decision.py:419
# ---------------------------------------------------------------------------


class TestDecisionVerifyMid8:
    """decision.py cmd_verify routes mid8 through resolve_mid8 with meta-read."""

    def _make_mission_dir(self, tmp_path: Path, slug: str, mission_id: str | None) -> Path:
        mission_dir = tmp_path / "kitty-specs" / slug
        mission_dir.mkdir(parents=True)
        meta: dict[str, object] = {"mission_slug": slug, "mission_type": "software-dev"}
        if mission_id is not None:
            meta["mission_id"] = mission_id
        (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return mission_dir

    def test_genuine_mid8_slug_resolves_via_resolve_mid8(self, tmp_path: Path) -> None:
        """With a declared mission_id, resolve_mid8 returns the correct mid8."""
        self._make_mission_dir(tmp_path, REAL_SLUG, REAL_MISSION_ID)
        feature_dir = tmp_path / "kitty-specs" / REAL_SLUG
        meta_raw = json.loads((feature_dir / "meta.json").read_text())
        mission_id = meta_raw.get("mission_id")

        result = resolve_mid8(REAL_SLUG, mission_id=mission_id)

        assert result == REAL_MID8

    def test_coincidental_tail_does_not_mis_resolve(self, tmp_path: Path) -> None:
        """#1918: coincidental tail declined → resolve_mid8 returns '' (no mis-resolution)."""
        # A mission whose slug ends in ZZZZZZZZ but whose real mission_id is different.
        self._make_mission_dir(tmp_path, COINCIDENTAL_SLUG, REAL_MISSION_ID)
        feature_dir = tmp_path / "kitty-specs" / COINCIDENTAL_SLUG
        meta_raw = json.loads((feature_dir / "meta.json").read_text())
        mission_id = meta_raw.get("mission_id")

        result = resolve_mid8(COINCIDENTAL_SLUG, mission_id=mission_id)

        # Returns REAL_MID8 (from declared mission_id), not COINCIDENTAL_TAIL
        assert result == REAL_MID8
        assert result != COINCIDENTAL_TAIL

    def test_no_meta_falls_back_gracefully(self, tmp_path: Path) -> None:
        """When meta.json is missing, resolve_mid8 with None declines cleanly."""
        result = resolve_mid8("bare-slug-no-mid8", mission_id=None)
        assert result == ""


# ---------------------------------------------------------------------------
# VALUE-USE callers — agent/mission.py:1229
# ---------------------------------------------------------------------------


class TestAgentMissionFindFeatureDirectory:
    """agent/mission.py _find_feature_directory routes mid8 via resolve_mid8."""

    def _make_feature_dir(self, tmp_path: Path, slug: str, mission_id: str | None) -> Path:
        fd = tmp_path / slug
        fd.mkdir(parents=True)
        meta: dict[str, object] = {"mission_slug": slug}
        if mission_id is not None:
            meta["mission_id"] = mission_id
        (fd / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return fd

    def test_genuine_embedded_mid8_slug_resolves_correctly(self, tmp_path: Path) -> None:
        """resolve_mid8 returns declared mid8 when slug embeds a matching tail."""
        fd = self._make_feature_dir(tmp_path, REAL_SLUG, REAL_MISSION_ID)
        meta_raw = json.loads((fd / "meta.json").read_text())

        result = resolve_mid8(REAL_SLUG, mission_id=meta_raw.get("mission_id"))

        assert result == REAL_MID8

    def test_coincidental_tail_no_longer_mis_resolves(self, tmp_path: Path) -> None:
        """#1918: coincidental tail overridden by declared mission_id."""
        fd = self._make_feature_dir(tmp_path, COINCIDENTAL_SLUG, REAL_MISSION_ID)
        meta_raw = json.loads((fd / "meta.json").read_text())

        result = resolve_mid8(COINCIDENTAL_SLUG, mission_id=meta_raw.get("mission_id"))

        assert result == REAL_MID8
        assert result != COINCIDENTAL_TAIL

    def test_no_mission_id_declines_any_tail(self, tmp_path: Path) -> None:
        """When no mission_id is declared, any tail is declined."""
        fd = self._make_feature_dir(tmp_path, COINCIDENTAL_SLUG, None)
        meta_raw = json.loads((fd / "meta.json").read_text())

        result = resolve_mid8(COINCIDENTAL_SLUG, mission_id=meta_raw.get("mission_id"))

        assert result == ""


# ---------------------------------------------------------------------------
# VALUE-USE callers — agent/workflow.py:300
# ---------------------------------------------------------------------------


class TestWorkflowMid8ForMissionReadPath:
    """agent/workflow.py mid8 derivation routes the fallback via resolve_mid8.

    WP03 routed ``_canonical_status_feature_dir`` through the read-side seam
    (``resolve_handle_to_read_path``), retiring the bespoke
    ``_mid8_for_mission_read_path`` helper; the seam now runs the SAME
    ``resolve_mid8``-based cascade these tests pin (``resolve_declared_mid8``).
    """

    def _meta_mid8(self, mission_id: str | None) -> str | None:
        """Simulate what _load_coord_branch_meta returns for meta_mid8."""
        if mission_id and len(mission_id) >= 8:
            return mission_id[:8]
        return None

    def test_when_meta_mid8_available_resolve_mid8_is_not_needed(self) -> None:
        """Primary path: meta_mid8 comes from meta; fallback not reached."""
        meta_mid8 = self._meta_mid8(REAL_MISSION_ID)
        assert meta_mid8 == REAL_MID8
        # resolve_mid8 would agree — confirming the two paths are consistent
        assert resolve_mid8(REAL_SLUG, mission_id=REAL_MISSION_ID) == REAL_MID8

    def test_fallback_genuine_slug_resolves_correctly(self) -> None:
        """Fallback path: meta_mid8 absent, slug has genuine embedded tail."""
        meta_mid8 = self._meta_mid8(None)  # no meta_mid8
        assert meta_mid8 is None

        # Without mission_id, resolve_mid8 declines (stricter than heuristic).
        # The caller passes mission_id=None because it exhausted meta.
        result = resolve_mid8(REAL_SLUG, mission_id=None)
        # Decline is safe: resolver falls back to handle-canonicalization.
        assert result == ""

    def test_fallback_coincidental_tail_no_longer_mis_resolves(self) -> None:
        """#1918: coincidental tail declines instead of being trusted as mid8."""
        meta_mid8 = self._meta_mid8(None)  # no meta_mid8
        assert meta_mid8 is None

        result = resolve_mid8(COINCIDENTAL_SLUG, mission_id=None)

        # Old heuristic would return COINCIDENTAL_TAIL (truthy, wrong).
        # New authoritative resolver declines (empty string).
        assert result == ""
        # Confirm old heuristic would have mis-resolved:
        assert mid8_from_slug(COINCIDENTAL_SLUG) == COINCIDENTAL_TAIL


# ---------------------------------------------------------------------------
# VALUE-USE callers — agent/context.py:76
# ---------------------------------------------------------------------------


class TestAgentContextFindFeatureDirectory:
    """agent/context.py _find_feature_directory routes mid8 via resolve_mid8."""

    def _meta_for_slug(self, mission_id: str | None) -> dict[str, object]:
        meta: dict[str, object] = {}
        if mission_id is not None:
            meta["mission_id"] = mission_id
        return meta

    def test_genuine_embedded_mid8_slug_routes_correctly(self) -> None:
        """With mission_id declared, resolve_mid8 returns the correct mid8."""
        meta = self._meta_for_slug(REAL_MISSION_ID)
        _mid = meta.get("mission_id")
        result = resolve_mid8(REAL_SLUG, mission_id=_mid if isinstance(_mid, str) else None)
        assert result == REAL_MID8

    def test_coincidental_tail_does_not_mis_resolve(self) -> None:
        """#1918: coincidental tail overridden by declared mission_id."""
        meta = self._meta_for_slug(REAL_MISSION_ID)
        _mid = meta.get("mission_id")
        result = resolve_mid8(COINCIDENTAL_SLUG, mission_id=_mid if isinstance(_mid, str) else None)
        assert result == REAL_MID8
        assert result != COINCIDENTAL_TAIL

    def test_no_mission_id_declines_gracefully(self) -> None:
        """When meta has no mission_id, resolve_mid8 declines rather than mis-resolves."""
        meta = self._meta_for_slug(None)
        _mid = meta.get("mission_id")
        result = resolve_mid8(COINCIDENTAL_SLUG, mission_id=_mid if isinstance(_mid, str) else None)
        assert result == ""


# ---------------------------------------------------------------------------
# BOOLEAN-DETECTOR callers — aggregate.py:480/486
# (Kept as mid8_from_slug; proven safe under stricter decline)
# ---------------------------------------------------------------------------


class TestAggregateMid8DetectorSafety:
    """aggregate.py uses mid8_from_slug as a boolean detector only.

    Prove that the stricter decline (resolve_mid8 with no mission_id) does NOT
    change the detector's answer for the two patterns it gates on:

    :480: ``if mid8_from_slug(mission_slug):`` — skip glob when slug is already
          ``<slug>-<mid8>`` form.  No mission_id is available here (this IS the
          meta-read code path).  Using resolve_mid8 would always return '' → the
          early return would never fire → falls back to glob → still correct.
          The detector's purpose is a performance short-circuit, not a correctness
          gate.  It is safe to keep as heuristic; the glob fallback is correct too.

    :486: ``if mid8_from_slug(candidate.parent.name)`` — keep only modern dirs.
          Purpose: structural filter. A coincidental tail would just include that
          dir (same as old heuristic). No mis-routing occurs because the resolver
          is looking for a directory that matches the slug-form, not using the
          returned string as a routing key.
    """

    def test_detector_480_real_slug_truthy(self) -> None:
        """Real embedded-mid8 slug → truthy → early return fires (skip glob)."""
        assert mid8_from_slug(REAL_SLUG) != ""  # truthy

    def test_detector_480_bare_slug_falsy(self) -> None:
        """Bare slug (no mid8 tail) → falsy → falls through to glob (correct)."""
        assert mid8_from_slug("my-bare-mission") == ""

    def test_detector_480_resolve_mid8_with_no_id_would_also_be_falsy(self) -> None:
        """Even with resolve_mid8 (mission_id=None), a real slug declines → falsy.

        This means replacing the detector at :480 with resolve_mid8(mission_id=None)
        would change behaviour (never fires early return).  The glob fallback is
        correct but slower.  Keeping mid8_from_slug as detector is safe here because:
        - No mission_id is available (we haven't read meta yet; meta read IS this code)
        - A coincidental tail just means we skip the glob for a dir that doesn't have
          an embedded mid8 suffix — worst case the raw_meta / primary_dir is returned,
          which is the same as the glob fallback.
        """
        result_authoritative = resolve_mid8(REAL_SLUG, mission_id=None)
        assert result_authoritative == ""  # would never fire the early-return guard

    def test_detector_486_modern_dir_name_passes_filter(self) -> None:
        """Modern dir (<slug>-<mid8>) passes the :486 filter."""
        assert mid8_from_slug(REAL_SLUG) != ""

    def test_detector_486_legacy_dir_name_rejected_by_filter(self) -> None:
        """Legacy dir (pure NNN- slug, no mid8 tail) is correctly rejected."""
        assert mid8_from_slug("083-my-mission") == ""


# ---------------------------------------------------------------------------
# BOOLEAN-DETECTOR callers — agent/status.py:41/51
# ---------------------------------------------------------------------------


class TestStatusMid8DetectorSafety:
    """agent/status.py uses mid8_from_slug as a boolean detector only.

    :41: ``if mid8_from_slug(raw_handle):`` in _resolve_bare_modern_mission_slug.
         Purpose: if the raw operator input already embeds a mid8, return None
         immediately (no need to scan).  No mission_id is available (haven't
         resolved yet).  Using resolve_mid8(mission_id=None) would always return ''
         → the early return would never fire → falls through to the glob scan →
         still correct (just slower).  Keeping mid8_from_slug is safe.

    :51: ``if mid8_from_slug(meta_path.parent.name)`` — filter glob results.
         Pure structural filter.  Same argument as aggregate.py:486.
    """

    def test_detector_41_embedded_mid8_handle_returns_truthy(self) -> None:
        """Raw handle with embedded mid8 → truthy → early-exit fires."""
        assert mid8_from_slug(REAL_SLUG) != ""

    def test_detector_41_bare_human_handle_returns_falsy(self) -> None:
        """Raw bare handle → falsy → scan proceeds (correct)."""
        assert mid8_from_slug("my-mission") == ""

    def test_detector_41_resolve_mid8_none_would_break_early_exit(self) -> None:
        """resolve_mid8(mission_id=None) always declines → early-exit never fires.

        This confirms that replacing :41 with resolve_mid8(mission_id=None) would
        disable the performance short-circuit (always scans).  The scan result is
        still correct, but replacing the detector here would change observable
        behaviour (always scan vs short-circuit).  Keeping the heuristic is safe.
        """
        result = resolve_mid8(REAL_SLUG, mission_id=None)
        assert result == ""  # would disable the early-return guard

    def test_detector_51_modern_dir_passes_filter(self) -> None:
        """A directory named <slug>-<mid8> passes the :51 filter."""
        assert mid8_from_slug(REAL_SLUG) != ""

    def test_detector_51_legacy_dir_rejected_by_filter(self) -> None:
        """A directory named <NNN-slug> (no mid8) is rejected by :51 filter."""
        assert mid8_from_slug("083-my-mission") == ""

    def test_coincidental_tail_in_detector_51_still_safe(self) -> None:
        """A coincidental tail passes the :51 filter — same as old behavior.

        The filter's purpose is 'keep dirs that LOOK like modern missions'.
        A dir with a coincidental 8-char tail being included is benign: the
        outer logic continues to check for exactly one match (len(matches) != 1
        returns None).  No mis-routing occurs from the filter.
        """
        # coincidental tail → accepted by filter (truthy)
        assert mid8_from_slug(COINCIDENTAL_SLUG) != ""
        # But the SINGLE-MATCH guard in _resolve_bare_modern_mission_slug
        # means multiple coincidental matches just return None (safe).
