"""Regression: ``migrate backfill-topology --mission X`` blast-radius scope (WP06 / #2219).

#2219 — the repo-global backfill churn (the ~203-file blast radius) — was ALREADY FIXED
upstream (#2070 added the ``--mission <slug>`` scope to ``backfill_topology_repo`` and
the ``migrate backfill-topology`` command; #1814 made ``read_topology`` a pure,
non-persisting reader). This module is the DURABLE GUARD: it drives the real
``migrate backfill-topology --mission X`` CLI surface in a multi-mission repo and proves
ONLY the target ``meta.json`` is mutated while every sibling stays BYTE-IDENTICAL.

Non-vacuousness (C-006 reasoned-RED). The fixture seeds BOTH the target AND ≥ 1 sibling
mission that LACK the ``topology`` field, so the sibling is a genuine backfill candidate
that ONLY the ``--mission`` scoping — not the idempotent-skip
(:func:`backfill_mission_topology` ``action="skip"`` when ``topology`` is already
present) — can keep untouched. :func:`test_unscoped_repo_global_walk_dirties_sibling`
exercises the SAME fixture through the UNSCOPED repo walk (behaviourally the pre-#2070
repo-global path) and asserts it DOES dirty the topology-lacking sibling — proving the
scope guard is load-bearing rather than a tautology. A sibling that already carried
``topology`` would be left alone by the idempotent-skip regardless of scoping, so the
byte-identical assertion would prove nothing.

Verified-already-fixed pin (#2219): ``0e270b10a`` / ``5b8e317aa`` (#2070 / #1814).
No production change — this WP is verify-and-guard only (NFR-002).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrate_app
from specify_cli.migration.backfill_topology import backfill_topology_repo

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_LOCATE_ROOT = "specify_cli.cli.commands.migrate_cmd.locate_project_root"

# Production-shaped, real-format mission identities (ULID mission_id + ``<slug>-<mid8>``
# directory names), so the fixture exercises the same meta.json shape a live repo carries.
_TARGET_SLUG = "backfill-scope-regression-01KW4V6C"
_TARGET_MISSION_ID = "01KW4V6CQ43CMRKN7C1E6GQGXB"
_SIBLING_SLUG = "surface-resolver-coherence-01KVTVZS"
_SIBLING_MISSION_ID = "01KVTVZS8E2N7P4QH0CMR3WD9A"


def _seed_mission(
    specs_dir: Path,
    slug: str,
    mission_id: str,
    *,
    coordination_branch: str | None,
    with_topology: bool,
) -> Path:
    """Write a production-shaped ``kitty-specs/<slug>/meta.json`` and return its path.

    When ``with_topology`` is ``False`` the ``topology`` key is OMITTED entirely — the
    un-backfilled legacy shape that makes the mission a genuine backfill candidate.
    """
    feature_dir = specs_dir / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "created_at": "2026-06-27T15:29:26.757176+00:00",
        "flattened": False,
        "friendly_name": slug.replace("-", " "),
        "mission_id": mission_id,
        "mission_number": None,
        "mission_slug": slug,
        "mission_type": "software-dev",
        "slug": slug,
        "target_branch": f"mission/{slug}",
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    if with_topology:
        meta["topology"] = "lanes"
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta_path


def _seed_multi_mission_repo(repo_root: Path) -> tuple[Path, Path]:
    """Seed a two-mission repo where BOTH missions LACK ``topology``.

    Returns ``(target_meta_path, sibling_meta_path)``. Both missions are backfill
    candidates — what keeps the sibling untouched under ``--mission`` is the scope,
    not the idempotent-skip (the non-vacuousness precondition).
    """
    specs_dir = repo_root / "kitty-specs"
    target_meta = _seed_mission(
        specs_dir,
        _TARGET_SLUG,
        _TARGET_MISSION_ID,
        coordination_branch="kitty/mission-backfill-scope-regression-01KW4V6C",
        with_topology=False,
    )
    sibling_meta = _seed_mission(
        specs_dir,
        _SIBLING_SLUG,
        _SIBLING_MISSION_ID,
        coordination_branch=None,
        with_topology=False,
    )
    return target_meta, sibling_meta


def _topology_of(meta_path: Path) -> object | None:
    meta: dict[str, object] = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta.get("topology")


# ---------------------------------------------------------------------------
# T015 — the blast-radius guard: scoped CLI run touches ONLY the target.
# ---------------------------------------------------------------------------


def test_cli_mission_scope_touches_only_target_siblings_byte_identical(tmp_path: Path) -> None:
    """``backfill-topology --mission X`` backfills X only; topology-lacking siblings unchanged.

    The 203-file blast-radius guard (#2219): in a multi-mission repo where the target
    AND a sibling both lack ``topology``, scoping to ``--mission X`` must leave the
    sibling BYTE-IDENTICAL — the durable regression that pins #2070's scoping.
    """
    target_meta, sibling_meta = _seed_multi_mission_repo(tmp_path)
    sibling_before = sibling_meta.read_bytes()
    assert _topology_of(target_meta) is None, "precondition: target lacks topology"
    assert _topology_of(sibling_meta) is None, "precondition: sibling lacks topology (non-vacuous)"

    with patch(_LOCATE_ROOT, return_value=tmp_path):
        result = CliRunner().invoke(migrate_app, ["backfill-topology", "--mission", _TARGET_SLUG])

    assert result.exit_code == 0, result.output
    # Target was backfilled to a concrete topology...
    assert _topology_of(target_meta) == "coord"
    # ...and the sibling is BYTE-IDENTICAL — only the target's meta.json moved.
    assert sibling_meta.read_bytes() == sibling_before, (
        "scoped --mission run must not mutate sibling missions (the #2219 blast-radius guard)"
    )


def test_cli_mission_scope_json_reports_single_result(tmp_path: Path) -> None:
    """The scoped CLI run reports exactly ONE mission in its JSON summary (no fan-out)."""
    _seed_multi_mission_repo(tmp_path)

    with patch(_LOCATE_ROOT, return_value=tmp_path):
        result = CliRunner().invoke(
            migrate_app, ["backfill-topology", "--mission", _TARGET_SLUG, "--json"]
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.find("{") :])
    assert payload["summary"]["total"] == 1, "scope must visit exactly the named mission"
    assert payload["summary"]["wrote"] == 1
    assert payload["results"][0]["slug"] == _TARGET_SLUG


def test_cli_mission_scope_idempotent_rerun_is_noop(tmp_path: Path) -> None:
    """A second scoped run on an already-backfilled mission is a byte-identical no-op."""
    target_meta, _sibling_meta = _seed_multi_mission_repo(tmp_path)

    with patch(_LOCATE_ROOT, return_value=tmp_path):
        first = CliRunner().invoke(migrate_app, ["backfill-topology", "--mission", _TARGET_SLUG])
    assert first.exit_code == 0, first.output
    after_first = target_meta.read_bytes()

    with patch(_LOCATE_ROOT, return_value=tmp_path):
        second = CliRunner().invoke(migrate_app, ["backfill-topology", "--mission", _TARGET_SLUG])
    assert second.exit_code == 0, second.output
    assert target_meta.read_bytes() == after_first, "idempotent re-run must not rewrite meta.json"


def test_unscoped_repo_global_walk_dirties_sibling(tmp_path: Path) -> None:
    """Reasoned-RED cross-check: the UNSCOPED walk DOES dirty the topology-lacking sibling.

    Behaviourally the pre-#2070 repo-global path (no ``mission_slug``). Driving the same
    fixture through it backfills EVERY topology-lacking mission — including the sibling —
    proving the sibling is a real backfill candidate that only the ``--mission`` scoping
    (not the idempotent-skip) protects. Were the scoped run to fan out the same way, the
    scope guard above would go RED; that is exactly the regression #2070 closed.
    """
    target_meta, sibling_meta = _seed_multi_mission_repo(tmp_path)
    sibling_before = sibling_meta.read_bytes()

    results = backfill_topology_repo(tmp_path)  # no mission_slug → repo-global walk

    wrote_slugs = {r.slug for r in results if r.action == "wrote"}
    assert _SIBLING_SLUG in wrote_slugs and _TARGET_SLUG in wrote_slugs, (
        "unscoped walk must process BOTH missions"
    )
    assert sibling_meta.read_bytes() != sibling_before, (
        "the topology-lacking sibling IS a backfill candidate — only --mission scoping "
        "spares it, so the scope guard is non-vacuous"
    )
    assert _topology_of(target_meta) == "coord"
    assert _topology_of(sibling_meta) == "single_branch"
