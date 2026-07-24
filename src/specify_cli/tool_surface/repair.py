"""Repair service for the tool surface contract bounded context.

:class:`SurfaceRepairService` accepts provider-owned :class:`SurfaceStatus`
objects (never reconstructs :class:`SurfaceInstance` from a finding) and
delegates the actual mutation to the provider that owns each surface kind. This
preserves the manifest/source/hash/refcount context the providers carry.

:func:`run_surface_repair` is the single entry point for ``init`` and
``upgrade``. It applies the 6-rule drift policy (contract: drift-policy-01)
and returns a structured :class:`DriftPolicySummary`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .enums import ActivationMode, RequiredPolicy, ToolSurfaceKind
from .findings import SurfaceFinding
from .providers.protocol import ReportingSurfaceProvider
from .status import (
    STATE_DRIFTED,
    STATE_MISSING,
    STATE_NOT_APPLICABLE,
    STATE_STALE,
    SurfaceStatus,
    _surface_id,
)


@dataclass(frozen=True)
class RepairResult:
    """Outcome of :meth:`SurfaceRepairService.repair`."""

    repaired: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()
    dry_run: bool = False
    findings_after: tuple[SurfaceFinding, ...] = ()

    def to_json(self) -> dict[str, object]:
        """Serialize to a JSON-friendly mapping."""
        return {
            "repaired": list(self.repaired),
            "skipped": list(self.skipped),
            "failed": list(self.failed),
            "dry_run": self.dry_run,
            "findings_after": [f.to_json() for f in self.findings_after],
        }


@dataclass
class _RepairTally:
    """Mutable accumulator while folding per-status repair outcomes."""

    repaired: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


class SurfaceRepairService:
    """Execute repair for a sequence of provider-owned statuses."""

    def __init__(self, providers: Sequence[ReportingSurfaceProvider]) -> None:
        self._providers = list(providers)

    def _provider_for(
        self, status: SurfaceStatus
    ) -> ReportingSurfaceProvider | None:
        for provider in self._providers:
            if provider.can_handle(status.instance.definition):
                return provider
        return None

    def repair(
        self,
        project_root: Path,
        statuses: Sequence[SurfaceStatus],
        *,
        kinds: set[ToolSurfaceKind] | None = None,
        dry_run: bool = False,
    ) -> RepairResult:
        """Repair the supplied statuses, grouped by owning provider."""
        selected = self._select(statuses, kinds)
        tally = _RepairTally()
        grouped = self._group_by_provider(selected, tally)
        for provider, provider_statuses in grouped:
            self._apply(provider, project_root, provider_statuses, dry_run, tally)
        return RepairResult(
            repaired=tuple(tally.repaired),
            skipped=tuple(tally.skipped),
            failed=tuple(tally.failed),
            dry_run=dry_run,
        )

    @staticmethod
    def _select(
        statuses: Sequence[SurfaceStatus],
        kinds: set[ToolSurfaceKind] | None,
    ) -> list[SurfaceStatus]:
        if kinds is None:
            return list(statuses)
        return [s for s in statuses if s.instance.definition.kind in kinds]

    def _group_by_provider(
        self,
        statuses: Sequence[SurfaceStatus],
        tally: _RepairTally,
    ) -> list[tuple[ReportingSurfaceProvider, list[SurfaceStatus]]]:
        """Bucket statuses by provider; record orphans as failures."""
        buckets: list[tuple[ReportingSurfaceProvider, list[SurfaceStatus]]] = []
        index: dict[int, list[SurfaceStatus]] = {}
        for status in statuses:
            provider = self._provider_for(status)
            if provider is None:
                tally.failed.append(_surface_id(status.instance))
                continue
            key = id(provider)
            if key not in index:
                index[key] = []
                buckets.append((provider, index[key]))
            index[key].append(status)
        return buckets

    @staticmethod
    def _apply(
        provider: ReportingSurfaceProvider,
        project_root: Path,
        statuses: list[SurfaceStatus],
        dry_run: bool,
        tally: _RepairTally,
    ) -> None:
        result = provider.repair(project_root, statuses, dry_run=dry_run)
        tally.repaired.extend(result.repaired)
        tally.skipped.extend(result.skipped)
        tally.failed.extend(result.failed)


# ---------------------------------------------------------------------------
# Drift-policy public interface (contract drift-policy-01)
# ---------------------------------------------------------------------------

_DRIFT_PROMPT = "Drifted: {path}. Overwrite? [y/N] "
_AMAZON_Q_TOOL_KEYS = frozenset({"q", "amazon-q", "amazon-q-agent"})


@dataclass
class DriftPolicySummary:
    """Structured outcome of the 6-rule drift policy applied by :func:`run_surface_repair`.

    Rules (contract drift-policy-01):
      1. Missing  → auto-created (``created``).
      2. Stale    → auto-repaired (``repaired``).
      3. Drifted + interactive, no --repair-drift → prompt; overwrite on ``y``.
      4. Drifted + non-interactive, no --repair-drift → report-only.
      5. --repair-drift=overwrite → overwrite unconditionally (``drifted_overwritten``).
      6. not_applicable → skip silently (``skipped``).
    """

    created: list[Path] = field(default_factory=list)
    repaired: list[Path] = field(default_factory=list)
    drifted_overwritten: list[Path] = field(default_factory=list)
    drifted_reported: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


def render_surface_summary_lines(summary: DriftPolicySummary) -> list[str]:
    """Render the human-facing tool-surface summary as ``rich``-markup lines.

    Shared by ``init`` and ``upgrade`` so both report identical, count-based
    text (FR-007). Each bucket is reported as a *count*, never the raw list of
    :class:`~pathlib.Path` objects. Returns one line per non-empty bucket, in a
    stable order; the caller is responsible for the drift-exit control flow.
    """
    lines: list[str] = []
    if summary.created:
        lines.append(f"[dim]Created {len(summary.created)} tool surface(s)[/dim]")
    if summary.repaired:
        lines.append(
            f"[dim]Repaired {len(summary.repaired)} stale tool surface(s)[/dim]"
        )
    if summary.drifted_overwritten:
        lines.append(
            f"[dim]Overwrote {len(summary.drifted_overwritten)} drifted tool surface(s)[/dim]"
        )
    if summary.drifted_reported:
        lines.append(
            f"[dim]Note: {len(summary.drifted_reported)} tool surface(s) have local edits "
            f"— run 'spec-kitty doctor tool-surfaces' to review[/dim]"
        )
    if summary.skipped:
        lines.append(
            f"  {len(summary.skipped)} surface(s) not applicable, skipped."
        )
    return lines


def _prompt_overwrite(path: Path) -> bool:
    """Prompt the user whether to overwrite a drifted file.  Returns True on ``y``."""
    try:
        answer = input(_DRIFT_PROMPT.format(path=path))
    except EOFError:
        return False
    return answer.strip().lower() == "y"


def _classify_drifted(
    status: SurfaceStatus,
    *,
    interactive: bool,
    repair_drift: bool,
    summary: DriftPolicySummary,
    overwrite_statuses: list[SurfaceStatus],
) -> None:
    """Apply drift-policy Rules 3, 4, and 5 for a single drifted surface."""
    path = status.instance.path
    if repair_drift:
        # Rule 5: overwrite unconditionally.
        overwrite_statuses.append(status)
    elif interactive and _prompt_overwrite(path):
        # Rule 3: user answered y.
        overwrite_statuses.append(status)
    else:
        # Rule 3 (user answered N) or Rule 4 (non-interactive): report only.
        summary.drifted_reported.append(path)


def _apply_auto_repairs(
    project_root: Path,
    providers: list[ReportingSurfaceProvider],
    missing_statuses: list[SurfaceStatus],
    stale_statuses: list[SurfaceStatus],
    summary: DriftPolicySummary,
) -> None:
    """Apply Rules 1 and 2 (auto-create missing, auto-repair stale)."""
    auto_repair_statuses = [
        status
        for status in (*missing_statuses, *stale_statuses)
        if _is_init_upgrade_auto_repairable(status)
    ]
    if not auto_repair_statuses:
        return
    service = SurfaceRepairService(providers)
    result = service.repair(project_root, auto_repair_statuses)
    for sid in result.repaired:
        parent = next(
            (s for s in auto_repair_statuses if _surface_id(s.instance) == sid),
            None,
        )
        if parent is None:
            continue
        if parent.state == STATE_MISSING:
            summary.created.append(parent.instance.path)
        else:
            summary.repaired.append(parent.instance.path)


def _is_init_upgrade_auto_repairable(status: SurfaceStatus) -> bool:
    """Return whether init/upgrade may repair this status without more user intent."""
    definition = status.instance.definition
    if definition.required_policy != RequiredPolicy.REPAIRABLE_REQUIRED:
        return False
    if definition.activation_mode == ActivationMode.DISABLED:
        return False
    return not (
        definition.kind == ToolSurfaceKind.AGENT_PROFILE
        and status.instance.owner in _AMAZON_Q_TOOL_KEYS
    )


def run_surface_repair(
    project_root: Path,
    *,
    interactive: bool,
    repair_drift: bool = False,
) -> DriftPolicySummary:
    """Apply the 6-rule drift policy and return a structured summary.

    This is the sole entry point for ``spec-kitty init`` and
    ``spec-kitty upgrade``.  It MUST NOT mutate :class:`SurfaceRepairService`
    or any existing caller.

    Critical guard (NFR-007 / FR-003):
      ``interactive=True`` does NOT imply ``repair_drift=True``.
      Passing ``--yes`` to ``init``/``upgrade`` sets ``interactive=False``,
      which triggers Rule 4 (report-only), NOT Rule 5 (overwrite).

    Args:
        project_root: Root of the project being repaired.
        interactive: Whether the session is interactive (a TTY).  When
            ``False``, drifted files are reported but never overwritten
            unless ``repair_drift`` is also ``True``.
        repair_drift: When ``True``, apply Rule 5: overwrite drifted files
            unconditionally.  Requires explicit ``--repair-drift=overwrite``
            flag from the caller; never implied by ``--yes``.
    """
    # Import here (lazy) to avoid circular import at module load time;
    # service.py already imports from repair.py.
    from .service import build_providers, build_registry
    from .plan import SurfacePlanBuilder
    from .status import SurfaceStatusService

    from specify_cli.agent_utils.directories import AGENT_DIR_TO_KEY
    from specify_cli.core.agent_config import get_configured_agents

    # Resolve configured tools — must run AFTER config is flushed to disk.
    try:
        configured_tools = list(get_configured_agents(project_root))
    except Exception:  # noqa: BLE001 — fallback to all known agents on config error
        configured_tools = list(AGENT_DIR_TO_KEY.values())

    if not configured_tools:
        return DriftPolicySummary()

    providers = build_providers()
    registry = build_registry(configured_tools)
    builder = SurfacePlanBuilder(registry, providers)
    plans = builder.build(configured_tools, project_root)
    report = SurfaceStatusService(providers).collect(
        project_root, plans, configured_tools=configured_tools
    )

    summary = DriftPolicySummary()
    missing_statuses: list[SurfaceStatus] = []
    stale_statuses: list[SurfaceStatus] = []
    overwrite_statuses: list[SurfaceStatus] = []

    for status in report.surfaces:
        state = status.state
        if state == STATE_NOT_APPLICABLE:
            summary.skipped.append(status.instance.path)  # Rule 6
        elif state == STATE_MISSING:
            missing_statuses.append(status)  # Rule 1 (batched below)
        elif state == STATE_STALE:
            stale_statuses.append(status)  # Rule 2 (batched below)
        elif state == STATE_DRIFTED:
            _classify_drifted(
                status,
                interactive=interactive,
                repair_drift=repair_drift,
                summary=summary,
                overwrite_statuses=overwrite_statuses,
            )
        # Other states (present, orphaned, unsafe, unsupported) are not acted on.

    # Rules 1 & 2: auto-create missing, auto-repair stale.
    _apply_auto_repairs(project_root, providers, missing_statuses, stale_statuses, summary)

    # Rules 3/5: apply drift overwrites.
    if overwrite_statuses:
        SurfaceRepairService(providers).repair(project_root, overwrite_statuses)
        for status in overwrite_statuses:
            summary.drifted_overwritten.append(status.instance.path)

    return summary
