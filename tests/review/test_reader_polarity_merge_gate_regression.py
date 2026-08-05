"""WP14 (FR-012/SC-012, T065/T066) -- declared reader polarity regressions.

Two regressions live in this file, both about a reader's behaviour on a
DAMAGED verdict record (non-UTF-8 content, or a malformed event-sourced
slot), and both about pinning an ALREADY-correct behaviour rather than
introducing a new one:

* T066 -- the merge gate (``post_merge/review_artifact_consistency.py::
  find_rejected_review_artifact_conflicts``) is already fail-closed on a
  non-UTF-8 verdict record, but only BECAUSE ``UnicodeDecodeError`` happens
  to subclass ``ValueError`` and the gate's own bare ``except ValueError``
  catches it. That is an ACCIDENT of Python's exception hierarchy, not a
  designed guarantee -- a future reader-side exception outside that
  hierarchy (e.g. a raw ``OSError`` that stops being wrapped into
  ``ValueError``) would silently re-open the gate to fail-open behaviour
  with no edit to the gate itself. This WP does not own
  ``post_merge/review_artifact_consistency.py`` or its existing test file
  (``tests/post_merge/test_review_artifact_consistency.py`` -- both belong
  to WP07/WP13) and makes no edit to either; this file is the pinning
  regression T066 requires instead, calling the gate's public entry point
  as a black box. The rationale comment WP13 could add at the gate's
  exception-handling site recording this incidental-inheritance fact is
  filed as a cross-WP finding in this WP's Activity Log, not authored here.

* T065 -- ``review/arbiter.py::get_arbiter_overrides_for_wp`` was, before
  WP12 (T051-T053), an uncaught-crash site: a manual YAML/JSON parse of two
  non-durable override representations (frontmatter block + JSON sidecar)
  with no exception handling at all. WP12 retired BOTH representations
  outright (not narrowed in place) into the event-sourced ``ReviewOverride``
  read via ``wp_snapshot_state`` -- the surviving reader already wraps
  ``ReviewOverride.from_dict`` in a narrow
  ``except (KeyError, TypeError, ValueError)``. Verified directly against
  ``review/arbiter.py`` at this WP's base commit (WP14's Activity Log): the
  manual parse this defect lived in no longer exists in the file at all, so
  there is nothing left for T065 to fix in code. The two tests below pin
  that already-correct behaviour, and prove the narrow catch has not
  widened into a blanket ``except Exception`` that would also swallow a
  genuine programming error.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.post_merge.review_artifact_consistency import (
    ReviewArtifactSchemaFinding,
    find_rejected_review_artifact_conflicts,
)
from specify_cli.review.arbiter import get_arbiter_overrides_for_wp
from specify_cli.status import ReviewOverride
from specify_cli.status.models import Lane
from tests.reliability.fixtures import (
    WorkPackageSpec,
    append_status_event,
    create_mission_fixture,
    write_work_package,
)

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# T066 -- merge gate: non-UTF-8 verdict record pins the incidental
# ValueError/UnicodeDecodeError inheritance that keeps the gate fail-closed.
# ---------------------------------------------------------------------------


def test_merge_gate_returns_structured_finding_for_non_utf8_verdict_record(
    tmp_path: Path,
) -> None:
    """A non-UTF-8 ``review-cycle-1.md`` must surface as a structured
    :class:`ReviewArtifactSchemaFinding`, never propagate an exception out of
    :func:`find_rejected_review_artifact_conflicts` (the merge gate's public
    entry point, called here as a black box -- no reimplementation of its
    internals).

    Why this passes today (recorded per T066, not fixed here): the gate's
    read path (``review/artifacts.py::ReviewCycleArtifact.from_file`` via
    ``latest_review_artifact_verdict``) calls ``path.read_text(encoding=
    "utf-8")`` directly -- NOT inside its own ``except OSError`` guard (that
    guard only wraps the read call itself and re-raises as ``ValueError``,
    but ``UnicodeDecodeError`` is not an ``OSError``, so it is never caught
    there). ``UnicodeDecodeError`` IS a ``ValueError`` subclass, though, so it
    propagates uncaught out of ``from_file``/``latest_review_artifact_verdict``
    as a ``ValueError`` and lands in
    ``find_rejected_review_artifact_conflicts``'s own ``except ValueError``
    (``post_merge/review_artifact_consistency.py:415``). That is an accident
    of Python's exception hierarchy, not a designed guarantee -- a future
    reader-side exception type outside it (e.g. a raw, unwrapped ``OSError``)
    would silently re-open the gate to fail-open behaviour with NO code
    change to the gate itself. This test is what converts the accident into a
    guarded invariant: a future refactor that narrows the gate's catch clause
    (e.g. to ``except FileNotFoundError`` only) reds this test immediately.
    """
    mission = create_mission_fixture(tmp_path)
    write_work_package(mission, WorkPackageSpec(lane="approved"))
    append_status_event(
        mission,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        event_id="01KZ1CGFWP14MERGEGATE00001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    # 0xFF is never a valid UTF-8 lead byte -- guaranteed UnicodeDecodeError
    # on ``.read_text(encoding="utf-8")``, not merely malformed YAML content.
    (artifact_dir / "review-cycle-1.md").write_bytes(
        b"---\n\xffverdict: approved\n---\n# Review\n"
    )

    findings = find_rejected_review_artifact_conflicts(
        mission.mission_dir,
        wp_ids=["WP01"],
    )

    assert len(findings) == 1
    finding = findings[0]
    assert isinstance(finding, ReviewArtifactSchemaFinding)
    assert finding.wp_id == "WP01"
    assert finding.artifact_path == artifact_dir / "review-cycle-1.md"


# ---------------------------------------------------------------------------
# T065 -- arbiter override reader: already-correct post-WP12 behaviour.
# ---------------------------------------------------------------------------


def test_arbiter_override_reader_refuses_a_malformed_event_sourced_slot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A ``review`` snapshot slot present but missing a required
    ``ReviewOverride`` field (the event-sourced successor to the retired
    frontmatter/JSON representations) is silently skipped -- never an
    uncaught crash -- by the narrow
    ``except (KeyError, TypeError, ValueError)`` already in
    ``get_arbiter_overrides_for_wp``. Monkeypatches ``wp_snapshot_state`` at
    its ``specify_cli.status`` source (the same module ``arbiter.py``
    resolves it from via its own function-local import) rather than mutating
    a tracked event-log fixture, per this WP's no-mutation rule.
    """
    import specify_cli.status as status_pkg

    def _fake_wp_snapshot_state(feature_dir: Path, wp_id: str) -> dict[str, object]:
        # Missing "wp_id" and "reason" -- ReviewOverride.from_dict raises
        # KeyError on the first missing key it looks up.
        return {"review": {"at": "2026-01-01T00:00:00+00:00", "actor": "operator"}}

    monkeypatch.setattr(status_pkg, "wp_snapshot_state", _fake_wp_snapshot_state)

    result = get_arbiter_overrides_for_wp(tmp_path, "WP01")

    assert result == []


def test_arbiter_override_reader_does_not_swallow_an_unrelated_bug(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The narrow catch must stay narrow: an exception type OUTSIDE
    ``(KeyError, TypeError, ValueError)`` -- standing in for a genuine
    programming error, not a parse failure -- must propagate uncaught, not
    be silently absorbed. Guards against a future "helpful" widening to a
    blanket ``except Exception`` (this WP's own Risks section)."""
    import specify_cli.status as status_pkg

    def _fake_wp_snapshot_state(feature_dir: Path, wp_id: str) -> dict[str, object]:
        return {
            "review": {
                "at": "2026-01-01T00:00:00+00:00",
                "actor": "operator",
                "wp_id": "WP01",
                "reason": "[custom] looks complete",
            }
        }

    monkeypatch.setattr(status_pkg, "wp_snapshot_state", _fake_wp_snapshot_state)

    def _boom(cls: type[ReviewOverride], data: object) -> ReviewOverride:
        raise RuntimeError("simulated unrelated bug — must not be swallowed")

    monkeypatch.setattr(ReviewOverride, "from_dict", classmethod(_boom))

    with pytest.raises(RuntimeError, match="simulated unrelated bug"):
        get_arbiter_overrides_for_wp(tmp_path, "WP01")
