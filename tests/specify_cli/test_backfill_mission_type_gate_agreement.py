"""Gate regression + cross-authority agreement for the mission_type backfill (rc3 M0 WP03).

Covers T007/T008/T009 (FR-009; spec.md AC-5, AC-6 gate side, AC-11; R-3).

Two gate roles exist over the same six-state audit
(``specify_cli.cli.commands._mission_type_audit``), and this module is the
canonical place documenting both — co-located with the tests that prove them
(T009; the operator-facing changelog entry is closeout-owned):

* **Completeness gate** — ``doctor mission-type --fail-on legacy-key-only``.
  Reds while ANY mission still carries only the retired ``mission`` key (no
  ``mission_type`` at all) — i.e. while the backfill has not yet visited every
  eligible legacy mission in the tree. Drives ``test_completeness_gate_red_
  then_green`` (AC-11): red on an un-migrated repo, green immediately after
  :func:`~specify_cli.migration.backfill_mission_type.backfill_mission_type_repo`
  runs once.

* **Release-safety gate** — ``doctor mission-type --fail-on
  legacy-key-only,typeless,error`` (the corrected three-state predicate,
  operator decision "B" — NOT the single-state completeness gate). This is
  the gate a release pipeline should run: it reds on anything the M3/M5
  program gate (module docstring of ``backfill_mission_type``) would break on
  upgrade — an un-migrated legacy mission (``legacy-key-only``), a mission
  with no resolvable type at all (``typeless``), or an unreadable
  ``meta.json`` (``error``). Critically, it does NOT require every
  ``mission_type`` to be *activated* — an unactivated-but-profile-resolving
  built-in type (e.g. ``research`` on a bare, unprovisioned repo) still
  greens this gate (``test_unactivated_builtin_written_and_release_gate_
  greens``, AC-5), because the backfill's own write predicate is
  profile-resolution, not charter activation (see
  ``backfill_mission_type.py``'s module docstring, "Predicate =
  profile-resolution, NOT charter activation"). Conversely, the gate still
  reds while a ``typeless`` or a non-resolving (``needs_manual_resolution``,
  still ``legacy-key-only`` per the audit) mission remains
  (``test_release_gate_reds_on_typeless_and_needs_manual``, AC-6 gate side).

**Residual gap (M3 coordination, out of scope here):** neither gate covers
the ``unknown`` state (a present, non-blank ``mission_type`` that is a typo
or otherwise unregistered/unresolvable anywhere). A mission whose
``mission_type`` was hand-typed with a typo — as opposed to left on the
legacy ``mission`` key — will NOT be caught by
``--fail-on legacy-key-only,typeless,error``; it classifies as ``unknown``
and is silently accepted by both gates as defined today. Closing that gap is
explicitly deferred to mission M3's per-type hard-fail work (see
``backfill_mission_type.py``'s module docstring) and is not a WP03 defect.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands._mission_type_audit import (
    audit_mission_types,
    run_mission_type_audit,
)
from specify_cli.migration.backfill_mission_type import (
    backfill_mission_type_repo,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_meta(repo_root: Path, slug: str, meta: dict[str, object]) -> Path:
    """Write ``meta`` under ``kitty-specs/<slug>/meta.json``."""
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return feature_dir


def _read_meta(feature_dir: Path) -> dict[str, object]:
    result: dict[str, object] = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    return result


def _run_gate(repo_root: Path, fail_on: str) -> int:
    """Invoke ``run_mission_type_audit`` and return the raised exit code."""
    with pytest.raises(typer.Exit) as exc:
        run_mission_type_audit(repo_root, False, None, fail_on)
    return exc.value.exit_code


# ---------------------------------------------------------------------------
# T007 — cross-authority agreement + completeness gate
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_writer_candidates_equal_audit_legacy_key_only(tmp_path: Path) -> None:
    """The writer's candidate set (write OR needs_manual) equals the audit's
    ``legacy-key-only`` set, non-vacuously (R-3).

    Corpus (five missions, five distinct outcomes):

    - ``001-resolving``: a real legacy value that resolves a governance
      profile — writer WRITES it; audit classifies ``legacy-key-only``.
    - ``002-typo``: a legacy value that resolves no profile at any layer —
      writer flags ``needs_manual_resolution`` (never written); audit STILL
      classifies this ``legacy-key-only`` (the audit only asks "is there a
      ``mission_type`` key", not "does the legacy value resolve").
    - ``003-blank-typeless``: a present-but-blank ``mission_type`` alongside a
      resolving legacy value — writer SKIPS it (key already present); audit
      classifies ``typeless`` (blank wins over the legacy key, per FR-008).
    - ``004-nonstring-typeless``: a non-string legacy value — writer SKIPS it
      (``no legacy mission value``); audit classifies ``typeless`` (the
      legacy value never canonicalizes to a string key).
    - ``005-already-typed``: a real ``mission_type`` key already present —
      writer SKIPS it (``mission_type already present``); audit does NOT
      classify this ``legacy-key-only`` (a ``mission_type`` key is present).

    The writer-candidate set and the audit's ``legacy-key-only`` set must be
    IDENTICAL: ``{001-resolving, 002-typo}`` — a non-vacuous two-member
    agreement, with the other three missions proving the disagreement cases
    (typeless, typeless, already-typed) are correctly excluded from both
    sides for the SAME reason (no bare ``mission`` key with no
    ``mission_type`` key).
    """
    _write_meta(tmp_path, "001-resolving", {"mission": "software-dev"})
    _write_meta(tmp_path, "002-typo", {"mission": "sofware-dev"})
    _write_meta(tmp_path, "003-blank-typeless", {"mission_type": "", "mission": "software-dev"})
    _write_meta(tmp_path, "004-nonstring-typeless", {"mission": 123})
    _write_meta(
        tmp_path,
        "005-already-typed",
        {"mission_type": "software-dev", "mission": "software-dev"},
    )

    writer_results = backfill_mission_type_repo(tmp_path, dry_run=True)
    writer_candidates = {
        r.slug for r in writer_results if r.action in ("wrote", "needs_manual_resolution")
    }

    audit_states = audit_mission_types(tmp_path)
    audit_legacy_key_only = {s.slug for s in audit_states if s.state == "legacy-key-only"}

    assert writer_candidates == {"001-resolving", "002-typo"}, writer_candidates
    assert audit_legacy_key_only == {"001-resolving", "002-typo"}, audit_legacy_key_only
    assert writer_candidates == audit_legacy_key_only

    # Non-vacuous: the blank-type and non-string missions are genuinely
    # skipped by the writer (never candidates) AND excluded from the audit's
    # legacy-key-only set (classified typeless instead) — for the same
    # underlying reason (no bare legacy-only value).
    by_slug = {r.slug: r for r in writer_results}
    assert by_slug["003-blank-typeless"].action == "skip"
    assert by_slug["003-blank-typeless"].reason == "mission_type already present"
    assert by_slug["004-nonstring-typeless"].action == "skip"
    assert by_slug["004-nonstring-typeless"].reason == "no legacy mission value"
    assert by_slug["005-already-typed"].action == "skip"

    audit_by_slug = {s.slug: s for s in audit_states}
    assert audit_by_slug["003-blank-typeless"].state == "typeless"
    assert audit_by_slug["004-nonstring-typeless"].state == "typeless"
    assert audit_by_slug["005-already-typed"].state != "legacy-key-only"


@pytest.mark.integration
def test_completeness_gate_red_then_green(tmp_path: Path) -> None:
    """AC-11: ``--fail-on legacy-key-only`` reds before the backfill runs (a
    resolving legacy-key-only mission is present) and greens immediately
    after :func:`backfill_mission_type_repo` runs once.
    """
    _write_meta(tmp_path, "001-resolving", {"mission": "software-dev"})

    before = _run_gate(tmp_path, "legacy-key-only")
    assert before != 0, "completeness gate must red while a legacy-key-only mission remains"

    results = backfill_mission_type_repo(tmp_path)
    assert results[0].action == "wrote"

    after = _run_gate(tmp_path, "legacy-key-only")
    assert after == 0, "completeness gate must green once the backfill has visited the mission"


# ---------------------------------------------------------------------------
# T008 — predicate-correctness regression (release-safety gate)
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_unactivated_builtin_written_and_release_gate_greens(tmp_path: Path) -> None:
    """AC-5: a SINGLE ``{"mission": "research"}`` mission on a bare temp repo
    (``research`` is NOT in any ``mission_type_activations`` — there is no
    ``.kittify/`` at all) is WRITTEN by the backfill, and the release-safety
    gate (``legacy-key-only,typeless,error``) greens.

    This is the predicate-correctness regression: it would RED against the
    rejected ``registered ∧ roster`` predicate, because an unactivated
    built-in type would never satisfy ``registered`` on a bare repo with no
    charter activation at all — the writer would (wrongly) leave ``research``
    on the legacy ``mission`` key forever, and the release-safety gate would
    (correctly, but for the wrong underlying reason) stay red on
    ``legacy-key-only``. Proving the gate greens here proves the writer used
    the profile-resolution predicate (``MissionTypeProfileRepository.get``),
    not activation.
    """
    feature_dir = _write_meta(tmp_path, "001-research", {"mission": "research"})
    assert not (tmp_path / ".kittify").exists(), "must be a bare, unprovisioned repo"

    results = backfill_mission_type_repo(tmp_path)

    assert len(results) == 1
    assert results[0].action == "wrote", "research must be WRITTEN despite being unactivated"
    assert results[0].mission_type == "research"

    meta = _read_meta(feature_dir)
    assert meta["mission_type"] == "research"

    gate_exit = _run_gate(tmp_path, "legacy-key-only,typeless,error")
    assert gate_exit == 0, "release-safety gate must green once research is written"


@pytest.mark.regression
def test_release_gate_reds_on_typeless_and_needs_manual(tmp_path: Path) -> None:
    """AC-6 (gate side): the release-safety gate
    (``legacy-key-only,typeless,error``) exits non-zero while EITHER a
    ``typeless`` mission or a non-resolving ``needs_manual_resolution``
    mission (still ``legacy-key-only`` per the audit) remains — proving the
    gate is not vacuously green just because nothing is un-migrated.
    """
    _write_meta(tmp_path, "001-typeless", {"mission_type": ""})

    typeless_only_exit = _run_gate(tmp_path, "legacy-key-only,typeless,error")
    assert typeless_only_exit != 0, "gate must red on a typeless-only repo"

    other_root = tmp_path / "needs-manual-repo"
    _write_meta(other_root, "002-typo", {"mission": "sofware-dev"})

    # The typo mission is left on the legacy key forever (never written) —
    # confirm the writer's own disposition before checking the gate.
    writer_results = backfill_mission_type_repo(other_root, dry_run=True)
    assert writer_results[0].action == "needs_manual_resolution"

    needs_manual_exit = _run_gate(other_root, "legacy-key-only,typeless,error")
    assert needs_manual_exit != 0, "gate must red while a non-resolving legacy mission remains"
