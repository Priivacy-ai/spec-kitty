"""LintEngine: orchestrates all charter-lint checkers into a single DecayReport.

Usage::

    from pathlib import Path
    from specify_cli.charter_lint import LintEngine

    report = LintEngine(Path(".")).run()
    print(report.to_json())

Zero LLM calls.  All checks are pure graph traversal.
"""

from __future__ import annotations

import datetime
import logging
import time
from pathlib import Path

from .findings import DecayReport, LintFinding
from .checks.orphan import OrphanChecker
from .checks.contradiction import ContradictionChecker
from .checks.staleness import StalenessChecker
from .checks.reference_integrity import ReferenceIntegrityChecker
from ._drg import load_merged_drg

logger = logging.getLogger(__name__)

_ALL_CHECKS: frozenset[str] = frozenset({"orphans", "contradictions", "staleness", "reference_integrity"})

_CHECK_MAP: dict[str, type] = {
    "orphans": OrphanChecker,
    "contradictions": ContradictionChecker,
    "staleness": StalenessChecker,
    "reference_integrity": ReferenceIntegrityChecker,
}


class LintEngine:
    """Orchestrate the four charter-lint checkers and produce a :class:`DecayReport`.

    Parameters
    ----------
    repo_root:
        Path to the repository root (containing ``.kittify/``).
    staleness_threshold_days:
        Number of days before a synthesized artifact is considered stale.
        Forwarded to :class:`StalenessChecker`.
    """

    def __init__(self, repo_root: Path, staleness_threshold_days: int = 90) -> None:
        self._repo_root = repo_root
        self._staleness_days = staleness_threshold_days

    def run(
        self,
        feature_scope: str | None = None,
        checks: set[str] | None = None,
        min_severity: str = "low",
    ) -> DecayReport:
        """Run requested checkers, time the run, write lint-report.json, return DecayReport.

        Parameters
        ----------
        feature_scope:
            Optional feature slug to scope findings (propagated to each checker).
        checks:
            Set of check names to run.  ``None`` means all four checks.
            Valid values: ``"orphans"``, ``"contradictions"``, ``"staleness"``,
            ``"reference_integrity"``.
        min_severity:
            Filter out findings below this severity level before returning.
            One of ``"low"`` (default, keeps everything), ``"medium"``,
            ``"high"``, ``"critical"``.

        Returns
        -------
        DecayReport
            Aggregated findings, always returned (never raises).
        """
        active_checks: set[str] = set(checks) if checks is not None else set(_ALL_CHECKS)
        unknown = active_checks - set(_ALL_CHECKS)
        if unknown:
            raise ValueError(f"Unknown check categories: {sorted(unknown)}")

        drg = load_merged_drg(self._repo_root)
        if drg is None:
            logger.warning("LintEngine: merged DRG not found — returning empty report")
            empty = DecayReport(
                findings=[],
                scanned_at=datetime.datetime.now(datetime.UTC).isoformat(),
                feature_scope=feature_scope,
                duration_seconds=0.0,
                drg_node_count=0,
                drg_edge_count=0,
            )
            self._persist(empty)
            return empty

        t0 = time.monotonic()
        all_findings: list[LintFinding] = []

        for check_name in sorted(active_checks):
            checker_cls = _CHECK_MAP[check_name]
            kwargs: dict = {}
            if check_name == "staleness":
                kwargs["staleness_threshold_days"] = self._staleness_days
            checker = checker_cls(**kwargs)
            try:
                findings = checker.run(drg, feature_scope=feature_scope)
                all_findings.extend(findings)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Checker %s failed: %s", check_name, exc)

        duration = time.monotonic() - t0

        report = DecayReport(
            findings=all_findings,
            scanned_at=datetime.datetime.now(datetime.UTC).isoformat(),
            feature_scope=feature_scope,
            duration_seconds=round(duration, 3),
            drg_node_count=len(list(getattr(drg, "nodes", []))),
            drg_edge_count=len(list(getattr(drg, "edges", []))),
        )

        if min_severity != "low":
            report = report.filter_by_severity(min_severity)

        self._persist(report)
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _persist(self, report: DecayReport) -> None:
        """Write *report* to ``.kittify/lint-report.json`` (silent on OSError)."""
        try:
            report_path = self._repo_root / ".kittify" / "lint-report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report.to_json(), encoding="utf-8")
        except OSError as exc:
            logger.warning("LintEngine: could not write lint-report.json: %s", exc)
