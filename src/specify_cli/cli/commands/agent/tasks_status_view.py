"""Pure status-aggregation core for ``agent tasks status`` (WP05).

This module lifts ``status``' **compute/aggregation** — the kanban lane rollup,
the progress percentages, the stale count, and the per-WP dependency readiness —
out of the interleaved command body into ONE pure function,
:func:`build_status_view`, plus the pure stale-detection fallback builder
:func:`build_stale_fallback_results`. It is a behaviour-preserving (pure-parity)
extraction (FR-006 / FR-002 / NFR-002): it reproduces the live command's exact
current aggregation — byte-for-byte — with no unification and no "improvement".

Design (functional core / imperative shell):

* The orchestrator (``status``) performs all filesystem / git / clock reads
  (repo/mission resolution, WP-frontmatter parse, event-log reduce, per-WP
  workspace resolution, review-artifact + git-commit staleness detection) and
  freezes the resulting facts in a :class:`StatusRequest`.
* :func:`build_status_view` is **PURE** (INV-4) — no filesystem, git,
  status-emission, rendering, or clock access — and returns a :class:`StatusView`:

  - ``lanes`` — the kanban rollup: every non-``GENESIS`` :class:`Lane` mapped to
    the ordered WP rows it holds (rows that fall outside the board land in an
    ``"other"`` bucket, exactly as the live grouping did). Holds the **same** row
    objects the shell passed in, so the shell's downstream rendering mutations
    (display markers, applied stale fields) still propagate.
  - ``lane_counts`` — ``Counter``-equivalent of the per-lane populations, the
    first-seen-ordered mapping the ``--json`` ``by_lane`` key serialises.
  - ``total_wps`` / ``done_count`` / ``in_progress_count`` / ``planned_count`` /
    ``stale_count`` — the population aggregates both output legs report.
  - ``done_percentage`` / ``progress_percentage`` — the rounded done-share and the
    lane-weighted readiness (``0`` — an ``int``, matching the live ``else 0`` arm —
    when there is no reduced snapshot).
  - ``dependency_readiness`` — per-WP :class:`DependencyReadiness` over the
    declared dependencies and the current lane map (via the canonical
    :func:`dependency_readiness_for_wp`; ``approved``/``done`` satisfy the gate).

**Rendering stays in the shell.** The Render port migration (WP07/WP09) draws the
rich tables/panels and assembles the ``--json`` envelope; this core returns only
the aggregated DATA, never draws.

**Stale-timing note (parity-critical, FR-002 / NFR-002).** ``stale_count`` is the
count of rows the shell has flagged ``is_stale`` (from the injected git-staleness
results, or from :func:`build_stale_fallback_results` when detection cannot run).
The core reads the already-applied flag rather than re-running detection, keeping
the git/clock I/O — and its exact original sequence — inside the shell.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from specify_cli.core.stale_detection import StaleCheckResult

from specify_cli.core.dependency_graph import (
    DependencyReadiness,
    dependency_readiness_for_wp,
)
from specify_cli.status import (
    Lane,
    StatusSnapshot,
    compute_done_percentage,
    compute_weighted_progress,
)

# The overflow bucket key for rows whose lane is not a display lane (parity with
# the live ``by_lane.setdefault("other", ...)`` fall-through).
OTHER_LANE_BUCKET = "other"

# Row = one status WP entry (heterogeneous frontmatter/derived fields). The core
# reads only ``id`` / ``lane`` / ``is_stale``; the shell owns the rest and mutates
# these same objects afterwards (display markers, applied stale fields), so the
# row type stays a mutable ``dict`` rather than a read-only ``Mapping``.
StatusRow = dict[str, object]


@dataclass(frozen=True)
class StatusRequest:
    """Every fact :func:`build_status_view` needs — all resolved by the shell.

    The shell (``status``) performs the I/O (WP-frontmatter parse, event-log
    reduce, workspace resolution, and — for the JSON leg — the git-staleness
    application) and freezes the results here so the decision is pure.
    """

    # Ordered WP rows (sorted-glob order), each carrying at least ``id`` and
    # ``lane``; for the JSON leg the shell has additionally applied ``is_stale``.
    work_packages: Sequence[StatusRow]
    # Reduced status snapshot for lane-weighted progress (``None`` → ``0``).
    snapshot: StatusSnapshot | None
    # Declared dependencies per WP id (from frontmatter) — drives readiness.
    wp_dependencies: Mapping[str, Sequence[str]]


@dataclass(frozen=True)
class StatusView:
    """The pure status aggregation the shell renders (human table + JSON)."""

    lanes: dict[Lane | str, list[StatusRow]]
    lane_counts: dict[Lane, int]
    total_wps: int
    done_count: int
    in_progress_count: int
    planned_count: int
    stale_count: int
    done_percentage: float
    progress_percentage: float
    dependency_readiness: dict[str, DependencyReadiness]


def build_stale_fallback_results(
    doing_wps: Sequence[StatusRow], error: Exception
) -> dict[str, StaleCheckResult]:
    """Return per-WP stale fallbacks when git-staleness detection cannot run.

    PURE (INV-4): reproduces the live ``_build_stale_fallback_results`` verbatim.
    Invoked from the shell's ``except`` arm when :func:`check_doing_wps_for_staleness`
    raises (e.g. ``MissingLanesError``); it manufactures a ``not_applicable``
    :class:`StaleCheckResult` per in-progress WP so the aggregation and rendering
    proceed with a defined (non-stale) verdict instead of crashing.
    """
    from specify_cli.core.stale_detection import (
        PLANNING_ARTIFACT_REPO_ROOT_REASON,
        StaleCheckResult,
        StaleState,
    )

    results: dict[str, StaleCheckResult] = {}
    for wp in doing_wps:
        wp_id = wp.get("id") or wp.get("work_package_id")
        if not wp_id:
            continue
        workspace_kind = str(wp.get("workspace_kind", "unknown"))
        execution_mode = str(wp.get("execution_mode", ""))
        fallback_reason = (
            PLANNING_ARTIFACT_REPO_ROOT_REASON
            if workspace_kind == "repo_root" and execution_mode == "planning_artifact"
            else "stale_detection_unavailable"
        )
        results[str(wp_id)] = StaleCheckResult(
            wp_id=str(wp_id),
            stale=StaleState(status="not_applicable", reason=fallback_reason),
            workspace_exists=False,
            workspace_kind=workspace_kind,
            error=str(error),
        )
    return results


def _kanban_rollup(
    work_packages: Sequence[StatusRow],
) -> dict[Lane | str, list[StatusRow]]:
    """Group rows into the display board (verbatim parity with the live loop).

    Seeds every non-``GENESIS`` :class:`Lane` with an empty bucket, appends each
    row to its lane bucket, and routes any row whose lane is off the board to the
    ``"other"`` overflow bucket — preserving the same key set, insertion order,
    and row-object identity the inline ``by_lane`` grouping produced.
    """
    lanes: dict[Lane | str, list[StatusRow]] = {
        lane: [] for lane in Lane if lane is not Lane.GENESIS
    }
    for row in work_packages:
        lane = row["lane"]
        if lane in lanes:
            lanes[cast("Lane | str", lane)].append(row)
        else:
            lanes.setdefault(OTHER_LANE_BUCKET, []).append(row)
    return lanes


def _weighted_progress_percentage(snapshot: StatusSnapshot | None) -> float:
    """Rounded lane-weighted readiness, or the live ``else 0`` (int) fall-through.

    Reproduces ``round(compute_weighted_progress(snapshot).percentage, 1) if
    snapshot else 0`` exactly — including the bare ``int`` ``0`` the no-snapshot
    arm returns, so the ``--json`` value serialises as ``0`` (not ``0.0``).
    """
    if snapshot:
        return round(float(compute_weighted_progress(snapshot).percentage), 1)
    return cast(float, 0)


def build_status_view(req: StatusRequest) -> StatusView:
    """Aggregate the status board purely (FR-006 / FR-002 / NFR-002).

    Computes the kanban rollup, the population counts, the done/weighted
    percentages, the stale count, and the per-WP dependency readiness with NO
    side effects (INV-4). The shell applies the git/clock staleness I/O first and
    renders the returned view.
    """
    lanes = _kanban_rollup(req.work_packages)

    lane_counts: Counter[Lane] = Counter()
    for row in req.work_packages:
        lane_counts[cast(Lane, row["lane"])] += 1

    total_wps = len(req.work_packages)
    done_count = len(lanes[Lane.DONE])
    in_progress_count = (
        len(lanes[Lane.CLAIMED])
        + len(lanes[Lane.IN_PROGRESS])
        + len(lanes[Lane.IN_REVIEW])
        + len(lanes[Lane.FOR_REVIEW])
    )
    planned_count = len(lanes[Lane.PLANNED])
    stale_count = sum(1 for row in req.work_packages if row.get("is_stale"))

    done_percentage = round(compute_done_percentage(done_count, total_wps), 1)
    progress_percentage = _weighted_progress_percentage(req.snapshot)

    lane_by_wp: dict[str, Lane] = {}
    for row in req.work_packages:
        wp_id = row.get("id")
        if isinstance(wp_id, str) and wp_id:
            lane_by_wp[wp_id] = cast(Lane, row["lane"])

    dependency_readiness = {
        wp_id: dependency_readiness_for_wp(wp_id, deps, lane_by_wp)
        for wp_id, deps in req.wp_dependencies.items()
    }

    return StatusView(
        lanes=lanes,
        lane_counts=dict(lane_counts),
        total_wps=total_wps,
        done_count=done_count,
        in_progress_count=in_progress_count,
        planned_count=planned_count,
        stale_count=stale_count,
        done_percentage=done_percentage,
        progress_percentage=progress_percentage,
        dependency_readiness=dependency_readiness,
    )
