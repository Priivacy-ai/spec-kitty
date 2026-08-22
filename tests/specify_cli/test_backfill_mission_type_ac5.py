"""rc3 M5 WP05 / AC-5: the M0 backfill is the safety net for the legacy retirement.

Verify-first: M0 (#3614) already shipped ``spec-kitty migrate
backfill-mission-type``. M5 does NOT rebuild it — these pins confirm the
sequencing contract that makes the deliberate legacy-``mission`` retirement
non-breaking:

  * a legacy ``{"mission": "research"}``-only mission gains ``mission_type:
    research`` and resolves via the shared ``read_mission_type`` seam afterward
    (AC-5);
  * a legacy value that resolves no governance profile is reported
    ``needs_manual_resolution`` and NEVER written — the backfill never
    manufactures an M3-breaker.

``migrate backfill-identity`` mints ``mission_id`` only — it does NOT backfill
``mission_type`` (documented coverage gap; ``backfill-mission-type`` is the
command that does).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from charter.mission_type_key import read_mission_type
from specify_cli.migration.backfill_mission_type import backfill_mission_type_repo

pytestmark = [pytest.mark.integration]


def _mission(repo_root: Path, slug: str, meta: dict[str, object]) -> Path:
    d = repo_root / "kitty-specs" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return d


def test_legacy_only_mission_is_backfilled_and_then_resolves(tmp_path: Path) -> None:
    feature_dir = _mission(tmp_path, "legacy-research", {"mission": "research", "mission_slug": "legacy-research"})

    results = backfill_mission_type_repo(tmp_path)

    wrote = [r for r in results if r.slug == "legacy-research"]
    assert wrote and wrote[0].action == "wrote"
    assert wrote[0].mission_type == "research"

    # After backfill the mission resolves via the shared M5 seam (post-retirement).
    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["mission_type"] == "research"
    assert read_mission_type(meta) == "research"


def test_unresolvable_legacy_value_is_never_written(tmp_path: Path) -> None:
    feature_dir = _mission(
        tmp_path,
        "bogus",
        {"mission": "totally-not-a-real-type", "mission_slug": "bogus"},
    )

    results = backfill_mission_type_repo(tmp_path)

    row = next(r for r in results if r.slug == "bogus")
    assert row.action == "needs_manual_resolution"
    # meta.json must be untouched — no fabricated mission_type (no M3-breaker).
    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert "mission_type" not in meta


def test_existing_mission_type_is_left_alone(tmp_path: Path) -> None:
    _mission(tmp_path, "typed", {"mission_type": "software-dev", "mission": "research"})

    results = backfill_mission_type_repo(tmp_path)

    row = next(r for r in results if r.slug == "typed")
    assert row.action == "skip"
