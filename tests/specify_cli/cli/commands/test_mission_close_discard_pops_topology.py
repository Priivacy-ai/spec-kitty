"""Permanent guard: ``mission close --discard`` must pop ``topology``, not
just ``coordination_branch`` (#3219 / FR-015 / SC-009) -- the discard-pops-
topology bug is fixed.

Formerly a red-first ``@pytest.mark.regression`` reproduction under
``tests/regression/``; relocated here (next to
``test_mission_type_force_delete_branch.py``, its functional home -- both
are direct, no-git unit tests of ``specify_cli.cli.commands.mission_type``
helpers) and un-marked (2026-08 landing fold: make
``@pytest.mark.regression`` mean exactly one thing) once
``_flatten_discarded_mission`` converged onto the canonical
``flatten_coordination_metadata`` primitive and this suite went stably
green. Note: #3219 itself remained OPEN at relocation time for the broader
primitive-extraction refactor it also tracks -- only this specific
discard-pops-topology defect is confirmed fixed here.

Before verdict-seam-write-unification-01KZ9Q35 WP10, ``_flatten_discarded_mission``
called only ``clear_coordination_metadata`` -- ONE of the canonical THREE
coordination-flatten mutations. It cleared ``coordination_branch`` but never
popped the stored ``topology`` and never recorded ``flattened=True``. A discarded
coordination mission therefore kept a stale ``topology: "coord"`` value in
``meta.json``, so a later command could still resolve it as a coordination
Mission and hit ``CoordinationBranchDeleted`` (the #1848 data-loss hard-fail) --
on a mission the operator had already discarded.

``_flatten_discarded_mission`` now converges onto the canonical
``flatten_coordination_metadata`` primitive (T051), which performs all three
mutations (clear ``coordination_branch``, pop ``topology``, record
``flattened=True``) atomically.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.mission_type import _flatten_discarded_mission

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Production-shaped identity (26-char ULID / mid8 convention), matching the
# real mission-identity model rather than a placeholder short string.
_MISSION_ID = "01JQANARZDISCPOPTOPOLOGY12"[:26]
_MID8 = _MISSION_ID[:8].lower()
_SLUG = f"discard-pops-topology-{_MID8}"


def _write_meta(feature_dir: Path, fields: dict[str, object]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(fields, indent=2) + "\n", encoding="utf-8"
    )


def test_discard_flatten_pops_topology_not_just_coordination_branch(
    tmp_path: Path,
) -> None:
    """Permanent guard for #3219: a discarded coord mission must have BOTH
    ``coordination_branch`` cleared AND ``topology`` popped, plus
    ``flattened=True`` recorded -- not just the former.
    """
    feature_dir = tmp_path / "kitty-specs" / _SLUG
    _write_meta(
        feature_dir,
        {
            "mission_id": _MISSION_ID,
            "mid8": _MID8,
            "mission_slug": _SLUG,
            "coordination_branch": f"kitty/mission-{_SLUG}",
            "topology": "coord",
        },
    )

    _flatten_discarded_mission(feature_dir)

    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert "coordination_branch" not in meta, (
        "coordination_branch must be cleared by the discard flatten"
    )
    assert "topology" not in meta, (
        "#3219 latent bug: a discarded coord mission still carried a stored "
        "'topology' value, so it could route back through coordination and "
        "hit CoordinationBranchDeleted -- the discard flatten must pop "
        "'topology' too, not just 'coordination_branch'"
    )
    assert meta.get("flattened") is True, (
        "a discarded coord mission must record flattened=True (parity with "
        "merge's #3086 flatten and `doctor coordination --fix`)"
    )


def test_discard_flatten_is_tolerant_of_missing_meta_json(tmp_path: Path) -> None:
    """Best-effort cleanup: a missing meta.json (legacy mission) must not raise."""
    feature_dir = tmp_path / "kitty-specs" / "no-meta-mission"
    feature_dir.mkdir(parents=True)

    _flatten_discarded_mission(feature_dir)  # must not raise


def test_discard_flatten_is_noop_for_non_coord_mission(tmp_path: Path) -> None:
    """A non-coord mission (no ``coordination_branch``) is left untouched --
    the discard flatten must not spuriously stamp ``flattened=True`` or pop an
    unrelated mission's ``topology`` on every discard.
    """
    feature_dir = tmp_path / "kitty-specs" / "non-coord-discard-mission"
    _write_meta(
        feature_dir,
        {
            "mission_id": _MISSION_ID,
            "mission_slug": "non-coord-discard-mission",
            "topology": "single_branch",
        },
    )

    _flatten_discarded_mission(feature_dir)

    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("topology") == "single_branch", (
        "a non-coord mission's topology must not be popped by the discard flatten"
    )
    assert "flattened" not in meta, (
        "a non-coord mission must not be marked flattened by the discard flatten"
    )
