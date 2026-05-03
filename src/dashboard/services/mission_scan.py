"""Mission scanning and kanban assembly service.

Per ``DIRECTIVE_API_DEPENDENCY_DIRECTION`` (mission
``mission-registry-and-api-boundary-doctrine-01KQPDBB``), this service is the
boundary between the FastAPI transport (routers in ``src/dashboard/api/routers/``)
and the canonical mission/WP read path (the ``MissionRegistry`` in
``src/dashboard/services/registry.py``).

Routers MUST NOT import the scanner modules directly. They consume mission
data through ``MissionScanService``, which in turn drives mission iteration
through the registry. The dashboard-specific per-feature wire-shape fields
(artifacts / workflow / worktree status) still flow through the existing
scanner helpers — that is allowed inside the service layer because the
service layer is below the architectural transport boundary that WP05
will enforce.

The wire shape returned by ``get_features_list()`` and ``get_kanban()`` is
byte-identical to the legacy stack (see ``tests/test_dashboard/test_seams.py``
and the OpenAPI snapshot test) — this service preserves parity by reusing
the same wire-shape building blocks, while delegating the *iteration source*
to the registry.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from dashboard.api_types import FeaturesListResponse, KanbanResponse, MissionContext

if TYPE_CHECKING:  # pragma: no cover - type-only import
    from dashboard.services.registry import MissionRecord, MissionRegistry


def parse_kanban_path(path: str) -> str | None:
    """Extract the feature_id segment from a `/api/kanban/<id>` request path.

    Returns None when the path is too short to contain a feature segment.
    Module-level (not a staticmethod) so seam tests that patch
    ``MissionScanService`` do not also intercept this pure function.
    """
    parts = path.split("/")
    if len(parts) < 4:
        return None
    return parts[3]


class MissionScanService:
    """Scans all missions, resolves active mission, assembles kanban state.

    All callable dependencies accept overrides (``_scan_all``, ``_resolve_active``,
    etc.) so the handler can pass its own module-level names — which tests may
    mock via ``patch.object(features_module, "scan_all_features", ...)``.
    Production callers pass nothing and the service imports from its own defaults.

    The optional ``registry`` parameter (added by mission
    ``mission-registry-and-api-boundary-doctrine-01KQPDBB``) is the mission
    iteration source; when omitted the service constructs a short-lived
    registry scoped to ``project_dir``.
    """

    def __init__(
        self,
        project_dir: Path,
        *,
        registry: "MissionRegistry | None" = None,
        _scan_all: Callable[..., Any] | None = None,
        _resolve_active: Callable[..., Any] | None = None,
        _is_legacy: Callable[..., Any] | None = None,
        _get_mission: Callable[..., Any] | None = None,
        _format_path: Callable[..., Any] | None = None,
        _resolve_feature: Callable[..., Any] | None = None,
        _scan_kanban: Callable[..., Any] | None = None,
    ) -> None:
        from specify_cli.legacy_detector import is_legacy_format
        from specify_cli.mission import get_mission_by_name
        from specify_cli.scanner import (
            format_path_for_display,
            resolve_active_feature,
            resolve_feature_dir,
            scan_all_features,
            scan_feature_kanban,
        )

        # Lazy import keeps the registry construction scoped to first use; the
        # FastAPI app injects a long-lived registry via app.state, so production
        # paths typically do not hit this default branch.
        from dashboard.services.registry import MissionRegistry

        self._project_dir = project_dir.resolve()
        self._registry = registry if registry is not None else MissionRegistry(self._project_dir)
        self._scan_all = _scan_all if _scan_all is not None else scan_all_features
        self._resolve_active = _resolve_active if _resolve_active is not None else resolve_active_feature
        self._is_legacy = _is_legacy if _is_legacy is not None else is_legacy_format
        self._get_mission = _get_mission if _get_mission is not None else get_mission_by_name
        self._format_path = _format_path if _format_path is not None else format_path_for_display
        self._resolve_feature = _resolve_feature if _resolve_feature is not None else resolve_feature_dir
        self._scan_kanban = _scan_kanban if _scan_kanban is not None else scan_feature_kanban

    @property
    def registry(self) -> "MissionRegistry":
        """Expose the underlying registry for handler-side ambiguity resolution."""
        return self._registry

    def get_features_list(self) -> FeaturesListResponse:
        """Scan all missions and return the full features-list payload.

        Mission iteration is driven by ``MissionRegistry.list_missions()`` —
        the canonical sanctioned reader of ``kitty-specs/``. Per-feature
        wire-shape enrichment (artifacts, workflow, kanban_stats, worktree)
        still flows through the existing scanner helpers via ``self._scan_all``;
        we filter the helper's output down to the registry's mission set so
        the registry is authoritative for which missions surface, while the
        wire shape remains byte-identical for missions both layers see.

        The fallback when the helper returns nothing for a registry mission
        (e.g., if a mission was just created and the helper's caches lag)
        is to surface the mission with a minimal wire shape rather than
        drop it — this keeps the registry's view authoritative.
        """
        from specify_cli.mission import MissionError

        # Drive iteration via the registry. Each MissionRecord identifies a
        # mission by slug + identity; we then use the existing scanner helper
        # to build the dashboard-shaped wire payload per feature.
        mission_records = self._registry.list_missions()
        wire_features = self._scan_all(self._project_dir)

        features = self._merge_registry_with_wire_features(mission_records, wire_features)

        for feature in features:
            feature_dir = self._project_dir / feature["path"]
            feature["is_legacy"] = self._is_legacy(feature_dir)

        mission_context: MissionContext = {
            "name": "No active feature",
            "domain": "unknown",
            "version": "",
            "slug": "",
            "description": "",
            "path": "",
        }

        active_feature = self._resolve_active(self._project_dir)

        if active_feature:
            feature_mission_type = active_feature.get("meta", {}).get("mission", "software-dev")
            try:
                kittify_dir = self._project_dir / ".kittify"
                mission = self._get_mission(feature_mission_type, kittify_dir)
                mission_context = {
                    "name": mission.name,
                    "domain": mission.config.domain,
                    "version": mission.config.version,
                    "slug": mission.path.name,
                    "description": mission.config.description or "",
                    "path": self._format_path(str(mission.path)),
                    "feature": active_feature.get("name", ""),
                }
            except MissionError:
                mission_context = {
                    "name": f"Unknown ({feature_mission_type})",
                    "domain": "unknown",
                    "version": "",
                    "slug": feature_mission_type,
                    "description": "",
                    "path": "",
                    "feature": active_feature.get("name", ""),
                }

        worktrees_root_path = self._project_dir / ".worktrees"
        try:
            worktrees_root_resolved = worktrees_root_path.resolve()
        except Exception:
            worktrees_root_resolved = worktrees_root_path

        try:
            current_path = Path.cwd().resolve()
        except Exception:
            current_path = Path.cwd()

        worktrees_root_exists = worktrees_root_path.exists()
        worktrees_root_display = (
            self._format_path(str(worktrees_root_resolved)) if worktrees_root_exists else None
        )

        active_worktree_display: str | None = None
        if worktrees_root_exists:
            try:
                current_path.relative_to(worktrees_root_resolved)
                active_worktree_display = self._format_path(str(current_path))
            except ValueError:
                active_worktree_display = None

        if not active_worktree_display and current_path != self._project_dir:
            active_worktree_display = self._format_path(str(current_path))

        return {
            "features": features,
            "active_feature_id": active_feature.get("id") if active_feature else None,
            "project_path": self._format_path(str(self._project_dir)),
            "worktrees_root": worktrees_root_display,
            "active_worktree": active_worktree_display,
            "active_mission": mission_context,
        }

    def get_kanban(self, feature_id: str) -> KanbanResponse:
        """Return kanban lanes and weighted progress for a specific feature.

        The mission is pre-resolved through the registry so unknown handles
        return an empty kanban with ``is_legacy=False`` (matches legacy
        behavior on miss). Once the mission is known, the per-feature
        kanban-board wire shape is still built via ``self._scan_kanban``
        (which carries fields like ``prompt_markdown`` that the registry's
        ``WorkPackageRecord`` does not surface).
        """
        from specify_cli.status.progress import compute_weighted_progress
        from specify_cli.status.reducer import materialize

        # Pre-resolve through the registry. On miss, return an empty response
        # — the legacy handler returns the same shape with empty lanes and
        # is_legacy=False. Routers that want a 404 instead can call
        # registry.get_mission() themselves before reaching this method.
        mission_record = self._registry.get_mission(feature_id)

        kanban_data = self._scan_kanban(self._project_dir, feature_id)

        if mission_record is not None:
            feature_dir: Path | None = mission_record.feature_dir
            is_legacy = mission_record.is_legacy
        else:
            feature_dir = self._resolve_feature(self._project_dir, feature_id)
            is_legacy = self._is_legacy(feature_dir) if feature_dir else False

        weighted_pct = None
        if feature_dir and not is_legacy:
            try:
                snap = materialize(feature_dir)
                progress = compute_weighted_progress(snap)
                weighted_pct = round(progress.percentage, 1)
            except Exception:
                pass

        return {
            "lanes": kanban_data,
            "is_legacy": is_legacy,
            "upgrade_needed": is_legacy,
            "weighted_percentage": weighted_pct,
        }

    # ── Private helpers ───────────────────────────────────────────────────

    def _merge_registry_with_wire_features(
        self,
        mission_records: "list[MissionRecord]",
        wire_features: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Pair MissionRecord iteration with per-feature wire-shape dicts.

        The registry is authoritative for which missions to surface (and in
        what display order). The scanner helper produces the byte-identical
        wire-shape dict per feature. We index the helper's output by the
        feature ``id`` (slug) and look up each registry mission in turn.

        For missions the helper did not produce (rare — e.g., a mission
        directory without ``tasks/`` and without a numeric prefix), we
        synthesise a minimal wire-shape entry so the registry's view stays
        authoritative; ``scan_all_features`` already filters those, so the
        scanner-driven path retains compatibility.

        Wire-shape parity invariant: when the helper has produced a feature
        for a mission, this function returns *that exact dict* — no field
        additions, no reformatting. Wire shape is preserved byte-identically.
        """
        wire_by_id: dict[str, dict[str, Any]] = {}
        for feat in wire_features:
            fid = feat.get("id")
            if isinstance(fid, str):
                wire_by_id[fid] = feat

        merged: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for record in mission_records:
            wire = wire_by_id.get(record.mission_slug)
            if wire is not None:
                merged.append(wire)
                seen_ids.add(record.mission_slug)
                continue
            # Fallback: registry knows about this mission but the helper did
            # not surface it. Emit a minimal wire shape; per the WP04
            # contract, the helper's output is the canonical wire shape, so
            # this branch only triggers for filesystem races.
            merged.append(self._minimal_feature_item_from_record(record))
            seen_ids.add(record.mission_slug)

        # Preserve scanner ordering: registry's display order is sorted by
        # display_number then slug; the legacy wire ordering is by recency.
        # To keep the wire shape and ordering byte-identical, we yield the
        # scanner's order for features it knows, and append registry-only
        # entries (the rare fallback case) at the tail.
        ordered_known = [feat for feat in wire_features if feat.get("id") in seen_ids]
        registry_only = [feat for feat in merged if feat.get("id") not in {f.get("id") for f in ordered_known}]
        return ordered_known + registry_only

    def _minimal_feature_item_from_record(self, record: "MissionRecord") -> dict[str, Any]:
        """Build a minimal wire-shape FeatureItem dict for a registry-only mission.

        Only used in the rare race where the registry sees a mission but the
        scanner helper has not yet picked it up. Fields default to the
        legacy "empty" shape so the wire response remains a valid
        FeaturesListResponse.
        """
        from specify_cli.scanner import format_path_for_display

        try:
            relative_path = str(record.feature_dir.relative_to(self._project_dir))
        except ValueError:
            relative_path = str(record.feature_dir)

        worktree_path = self._project_dir / ".worktrees" / record.mission_slug
        return {
            "id": record.mission_slug,
            "name": record.friendly_name,
            "display_name": record.friendly_name,
            "path": relative_path,
            "artifacts": {},
            "workflow": {
                "specify": "pending",
                "plan": "pending",
                "tasks": "pending",
                "implement": "pending",
            },
            "kanban_stats": {
                "total": record.lane_counts.total,
                "planned": record.lane_counts.planned,
                "doing": record.lane_counts.in_progress,
                "for_review": record.lane_counts.for_review,
                "approved": record.lane_counts.approved,
                "done": record.lane_counts.done,
            },
            "meta": {},
            "worktree": {
                "path": format_path_for_display(str(worktree_path)),
                "exists": worktree_path.exists(),
            },
        }
