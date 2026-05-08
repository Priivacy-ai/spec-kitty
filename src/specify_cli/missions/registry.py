"""Mission and work-package registries — single sanctioned reader for ``kitty-specs/``.

Canonical home: ``specify_cli.missions.registry``.
The dashboard path ``dashboard.services.registry`` is now a compatibility shim
that re-exports all public symbols from this module. Do not add business logic there.

This module is the **service layer** for mission/WP data. Per
``DIRECTIVE_API_DEPENDENCY_DIRECTION`` (introduced by mission
``mission-registry-and-api-boundary-doctrine-01KQPDBB``; see
``architecture/2.x/initiatives/2026-05-stable-application-api-surface/README.md``),
every transport-side consumer (FastAPI router, CLI command body, MCP tool,
future SDK) MUST consume mission/WP data exclusively through these registries.
The architectural test ``tests/architectural/test_transport_does_not_import_scanner.py``
(authored in WP05) enforces this at import time.

Records returned by the registry are **frozen ``dataclass`` types** — Pydantic-free
so CLI / MCP / SDK consumers can depend on them without pulling Pydantic. The
FastAPI Pydantic transport models in ``src/dashboard/api/models.py`` are mapped
*from* these records by the routers; the records themselves are a stable internal
Python contract.

The registry wraps the legacy scanner (``specify_cli.dashboard.scanner``); it does
NOT reimplement the directory walk. ``MissionRegistry.list_missions()`` calls
``scan_all_features`` once, transforms the result into ``MissionRecord`` instances,
caches the result, and serves subsequent calls from the cache until the
underlying ``kitty-specs/`` directory mtime / size / dirent set changes.

Cache key triple (per FR-002, NFR-002, NFR-003):

    (mtime_ns, total_size_or_count, sorted_dirent_names_hash)

The dirent-name hash protects against rename-without-mtime-change scenarios where
``mtime_ns`` and ``size`` happen to collide (R-1 in research.md).

Two-level cache (P1 fix, FR-002):
    Level 1 — structural key: (mtime_ns, dirent_count, dirent_hash) of kitty-specs/.
    Level 2 — per-mission key: derived from meta.json + status.events.jsonl + tasks/.
    A structural hit still checks per-mission keys; only missions whose per-mission key
    changed are re-scanned. This makes list_missions() detect status.events.jsonl
    appends without requiring a kitty-specs/ directory mutation.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ─────────────────────────────────────────────────────────────────────────────
# Records (frozen dataclasses) — public service-layer return types.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LaneCounts:
    """Aggregate lane counts across a mission's WPs.

    Frozen value object. Total equals the sum of the nine lane counters; the
    registry guarantees this invariant for every record it produces.
    """
    total: int
    planned: int
    claimed: int
    in_progress: int
    for_review: int
    in_review: int
    approved: int
    done: int
    blocked: int
    canceled: int


@dataclass(frozen=True)
class MissionRecord:
    """One mission's identity + summary state. Immutable cache snapshot.

    A consumer holding a record after the cache invalidates still sees the
    snapshot from the cache time (TOCTOU safety per data-model.md).
    """
    mission_id: str               # ULID, canonical identity (or pseudo-key for legacy)
    mission_slug: str             # human-readable directory name
    display_number: int | None    # numeric prefix for display sort; None pre-merge
    mid8: str                     # first 8 chars of mission_id (empty for pseudo-keys)
    feature_dir: Path             # absolute path to kitty-specs/<slug>/
    friendly_name: str            # title from meta.json
    mission_type: str             # software-dev, research, etc.
    target_branch: str            # branch the mission lands on
    created_at: datetime | None   # from meta.json; None if unparseable
    lane_counts: LaneCounts
    weighted_percentage: float | None  # None for legacy missions w/ no event log
    is_legacy: bool               # mission directory without meta.json or status.events.jsonl
    purpose_tldr: str | None = None   # one-line summary from meta.json
    purpose_context: str | None = None  # extended context from meta.json


@dataclass(frozen=True)
class WorkPackageRecord:
    """One WP's identity + assignment + lane state. Immutable cache snapshot."""
    wp_id: str
    title: str
    lane: str                     # planned | claimed | in_progress | for_review | in_review | approved | done | blocked | canceled
    subtasks_done: int
    subtasks_total: int
    agent: str | None
    agent_profile: str | None
    role: str | None
    assignee: str | None
    phase: str | None
    prompt_path: Path
    dependencies: tuple[str, ...]
    requirement_refs: tuple[str, ...]
    last_event_id: str | None
    last_event_at: datetime | None
    claimed_at: datetime | None = None    # timestamp of most recent →claimed event
    blocked_reason: str | None = None     # reason from most recent →blocked event


@dataclass(frozen=True)
class CacheEntry(Generic[T]):
    """Internal cache primitive.

    The cache key is the (mtime_ns, size_or_count, sorted_dirent_names_hash)
    triple from the watched filesystem location. Two entries with different
    keys MUST be treated as different snapshots; a hit means all three
    components matched.
    """
    value: T
    cache_key: tuple[int, int, str]
    cached_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _parse_iso_datetime(raw: Any) -> datetime | None:
    """Best-effort ISO-8601 parse. Returns None on any failure (records never raise)."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        # datetime.fromisoformat handles RFC3339-ish strings on Python 3.11+
        # including the trailing 'Z' (Python 3.11 needs replace; 3.11+ tolerates).
        normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        return datetime.fromisoformat(normalized)
    except (ValueError, TypeError):
        return None


def _dirent_hash(dirents: list[str]) -> str:
    """Stable 16-char hex digest of a sorted dirent name list."""
    payload = b"\n".join(name.encode("utf-8") for name in sorted(dirents))
    return hashlib.sha256(payload).hexdigest()[:16]


def _kitty_specs_cache_key(project_dir: Path) -> tuple[int, int, str]:
    """Compute the (mtime_ns, dirent_count, sorted-dirent-names-hash) cache key for kitty-specs/.

    Returns (0, 0, "") when the directory does not exist (treated as empty).
    """
    kitty_specs = project_dir / "kitty-specs"
    if not kitty_specs.exists():
        return (0, 0, "")
    try:
        st = kitty_specs.stat()
    except OSError:
        return (0, 0, "")
    try:
        dirents = [entry.name for entry in kitty_specs.iterdir()]
    except OSError:
        dirents = []
    return (st.st_mtime_ns, len(dirents), _dirent_hash(dirents))


def _mission_dir_cache_key(feature_dir: Path) -> tuple[int, int, str]:
    """Compute the cache key for a single mission directory.

    Triple: (max(mtime_ns of meta.json + status.events.jsonl + tasks/ if present),
             total_byte_size of those same files,
             dirent hash of tasks/ if present else "").

    Designed so that *content-length-changes-with-same-mtime* and *file-additions
    in tasks/* both invalidate the cache deterministically. Missing files
    contribute (0, 0) — the absence itself is part of the fingerprint.
    """
    components_mtime = 0
    components_size = 0
    tasks_dirent_hash = ""

    meta = feature_dir / "meta.json"
    if meta.exists():
        try:
            st = meta.stat()
            components_mtime = max(components_mtime, st.st_mtime_ns)
            components_size += st.st_size
        except OSError:
            pass

    events = feature_dir / "status.events.jsonl"
    if events.exists():
        try:
            st = events.stat()
            components_mtime = max(components_mtime, st.st_mtime_ns)
            components_size += st.st_size
        except OSError:
            pass

    tasks = feature_dir / "tasks"
    if tasks.exists():
        try:
            st = tasks.stat()
            components_mtime = max(components_mtime, st.st_mtime_ns)
            # tasks/ size component: count files (a "size" surrogate); also hash dirent
            dirents: list[str] = []
            for entry in tasks.iterdir():
                dirents.append(entry.name)
                try:
                    components_size += entry.stat().st_size
                except OSError:
                    continue
            tasks_dirent_hash = _dirent_hash(dirents)
        except OSError:
            pass

    return (components_mtime, components_size, tasks_dirent_hash)


def _read_meta_json(feature_dir: Path) -> dict[str, Any] | None:
    """Parse meta.json. Returns None on any IO/JSON error (registry never raises)."""
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def _coerce_display_number(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Lane / progress derivation (consumes existing canonical APIs).
# ─────────────────────────────────────────────────────────────────────────────


def _derive_lane_counts_and_progress(
    feature_dir: Path,
) -> tuple[LaneCounts, float | None, bool]:
    """Materialize lane counts + weighted_percentage + degraded flag.

    Strategy:
      1. If status.events.jsonl is missing → treat as legacy; counts come from
         a tasks/-directory file count, weighted_percentage is None.
      2. Otherwise call the canonical reducer (``materialize``) and
         ``compute_weighted_progress``. The 9-lane counters are materialised
         from snapshot.summary; missing keys default to 0. Total is the sum.
      3. Any exception (corrupted event log, unreadable WP frontmatter, etc.)
         is logged and falls back to all-zero counts with weighted_percentage
         None. The caller keeps the mission visible with a degraded view rather
         than raising.

    Returns ``(lane_counts, weighted_percentage, is_legacy)`` where ``is_legacy``
    is True when the event log file is absent.
    """
    events_path = feature_dir / "status.events.jsonl"
    if not events_path.exists():
        # Legacy / un-finalised: count WP files in tasks/.
        wp_total = 0
        tasks_dir = feature_dir / "tasks"
        if tasks_dir.exists():
            try:
                wp_total = sum(1 for p in tasks_dir.glob("WP*.md") if p.is_file())
            except OSError:
                wp_total = 0
        return (
            LaneCounts(
                total=wp_total,
                planned=wp_total,
                claimed=0,
                in_progress=0,
                for_review=0,
                in_review=0,
                approved=0,
                done=0,
                blocked=0,
                canceled=0,
            ),
            None,
            True,
        )

    try:
        from specify_cli.status.progress import compute_weighted_progress
        from specify_cli.status.reducer import materialize

        snapshot = materialize(feature_dir)
        progress = compute_weighted_progress(snapshot)
        summary = snapshot.summary or {}
        counts = LaneCounts(
            total=sum(summary.values()),
            planned=int(summary.get("planned", 0)),
            claimed=int(summary.get("claimed", 0)),
            in_progress=int(summary.get("in_progress", 0)),
            for_review=int(summary.get("for_review", 0)),
            in_review=int(summary.get("in_review", 0)),
            approved=int(summary.get("approved", 0)),
            done=int(summary.get("done", 0)),
            blocked=int(summary.get("blocked", 0)),
            canceled=int(summary.get("canceled", 0)),
        )
        return counts, round(progress.percentage, 4), False
    except Exception as exc:
        logger.debug(
            "registry: degraded lane counts for %s (%s)",
            feature_dir.name,
            exc,
        )
        # Degraded: corrupted event log etc. Mission still visible.
        return (
            LaneCounts(
                total=0,
                planned=0,
                claimed=0,
                in_progress=0,
                for_review=0,
                in_review=0,
                approved=0,
                done=0,
                blocked=0,
                canceled=0,
            ),
            None,
            False,
        )


def _load_mission_record(feature_dir: Path) -> MissionRecord:
    """Build a MissionRecord from on-disk artifacts. Never raises."""
    meta = _read_meta_json(feature_dir) or {}

    mission_id_raw = meta.get("mission_id")
    mission_id: str = mission_id_raw if isinstance(mission_id_raw, str) and mission_id_raw else ""
    _slug_raw = meta.get("mission_slug")
    mission_slug: str = _slug_raw if isinstance(_slug_raw, str) and _slug_raw else feature_dir.name
    display_number = _coerce_display_number(meta.get("mission_number"))
    mid8 = mission_id[:8] if mission_id else ""
    _name_raw = meta.get("friendly_name")
    friendly_name: str = _name_raw if isinstance(_name_raw, str) and _name_raw else feature_dir.name
    _type_raw = meta.get("mission_type")
    _type_fallback = meta.get("mission")
    mission_type: str = (
        _type_raw if isinstance(_type_raw, str) and _type_raw
        else (_type_fallback if isinstance(_type_fallback, str) and _type_fallback else "software-dev")
    )
    _branch_raw = meta.get("target_branch")
    target_branch: str = _branch_raw if isinstance(_branch_raw, str) and _branch_raw else "main"
    created_at = _parse_iso_datetime(meta.get("created_at"))

    lane_counts, weighted_percentage, events_missing_flag = _derive_lane_counts_and_progress(feature_dir)

    # is_legacy: mission lacks both meta.json identity AND a finalised event log.
    is_legacy = (not mission_id) and events_missing_flag

    # Use slug as a synthetic id for legacy missions so list_missions still surfaces them.
    if not mission_id:
        mission_id = f"legacy:{feature_dir.name}"

    def _str_or_none(key: str) -> str | None:
        v = meta.get(key)
        return " ".join(v.split()) if isinstance(v, str) and v.strip() else None

    return MissionRecord(
        mission_id=mission_id,
        mission_slug=mission_slug,
        display_number=display_number,
        mid8=mid8,
        feature_dir=feature_dir.resolve(),
        friendly_name=friendly_name,
        mission_type=mission_type,
        target_branch=target_branch,
        created_at=created_at,
        lane_counts=lane_counts,
        weighted_percentage=weighted_percentage,
        is_legacy=is_legacy,
        purpose_tldr=_str_or_none("purpose_tldr"),
        purpose_context=_str_or_none("purpose_context"),
    )


def _missions_display_order(records: list[MissionRecord]) -> list[MissionRecord]:
    """Sort records into display order per registry-interface.md.

    1. Missions with a numeric ``display_number`` come first, ascending.
    2. Then missions without a number, sorted by ``created_at`` descending.
    3. Then legacy missions (no meta.json), sorted by directory name.
    """
    def sort_key(record: MissionRecord) -> tuple[int, int, float, str]:
        if record.is_legacy:
            return (2, 0, 0.0, record.mission_slug)
        if record.display_number is not None:
            return (0, record.display_number, 0.0, record.mission_slug)
        # No display number; sort by created_at descending. Use negative ts.
        ts = -record.created_at.timestamp() if record.created_at else 0.0
        return (1, 0, ts, record.mission_slug)

    return sorted(records, key=sort_key)


# ─────────────────────────────────────────────────────────────────────────────
# WorkPackageRegistry
# ─────────────────────────────────────────────────────────────────────────────


class WorkPackageRegistry:
    """Per-mission work-package reader. Construct via ``MissionRegistry.workpackages_for(...)``.

    Cache key is derived from the (mtime, size, dirent-hash) triple of the
    watched mission directory (meta.json + status.events.jsonl + tasks/).
    Mission-level changes that don't touch tasks/ or the event log don't
    invalidate this cache; e.g. editing spec.md keeps the WP cache warm.

    All methods are safe for concurrent use; mutations serialize on a
    per-instance ``threading.Lock``.
    """

    def __init__(self, feature_dir: Path) -> None:
        self._feature_dir = feature_dir.resolve()
        self._cache: CacheEntry[list[WorkPackageRecord]] | None = None
        self._lock = threading.Lock()

    @property
    def feature_dir(self) -> Path:
        return self._feature_dir

    def list_work_packages(self) -> list[WorkPackageRecord]:
        """Return every WP for the scoped mission, ordered by ``wp_id`` ascending.

        Never raises. Malformed WP frontmatter produces a record with best-effort
        fields.
        """
        cache_key = _mission_dir_cache_key(self._feature_dir)
        cache = self._cache
        if cache is not None and cache.cache_key == cache_key:
            return cache.value

        with self._lock:
            # Double-check after acquiring the lock.
            cache = self._cache
            if cache is not None and cache.cache_key == cache_key:
                return cache.value
            wps = self._scan()
            self._cache = CacheEntry(
                value=wps,
                cache_key=cache_key,
                cached_at=datetime.now(UTC),
            )
            return wps

    def get_work_package(self, wp_id: str) -> WorkPackageRecord | None:
        """Resolve one WP by ID. Returns ``None`` on miss; never raises."""
        if not wp_id:
            return None
        for wp in self.list_work_packages():
            if wp.wp_id == wp_id:
                return wp
        return None

    def lane_counts(self) -> LaneCounts:
        """Aggregate lane counts derived from this mission's WPs.

        Same data as ``MissionRecord.lane_counts`` but accessed via the WP-scoped
        cache. Falls back to the canonical reducer for parity with
        ``MissionRegistry``.
        """
        # Prefer the canonical reducer to stay in lockstep with MissionRecord.
        counts, _pct, _legacy = _derive_lane_counts_and_progress(self._feature_dir)
        return counts

    def invalidate(self) -> None:
        """Test-only: drop the cached snapshot."""
        with self._lock:
            self._cache = None

    # ── Private ────────────────────────────────────────────────────────────

    def _scan(self) -> list[WorkPackageRecord]:
        tasks_dir = self._feature_dir / "tasks"
        if not tasks_dir.exists():
            return []

        # Build a one-shot snapshot of WP lanes from the canonical event log,
        # if it exists. We bypass scanner internals here — the registry is the
        # canonical reader and consumes the canonical reducer directly.
        from specify_cli.status.lane_reader import has_event_log
        from specify_cli.status.wp_metadata import read_wp_frontmatter

        wp_lanes: dict[str, str] = {}
        last_event_by_wp: dict[str, tuple[str, datetime | None]] = {}
        claimed_at_by_wp: dict[str, datetime | None] = {}
        blocked_reason_by_wp: dict[str, str | None] = {}
        if has_event_log(self._feature_dir):
            try:
                from specify_cli.status.reducer import materialize

                snapshot = materialize(self._feature_dir)
                for wp_id, state in (snapshot.work_packages or {}).items():
                    wp_lanes[wp_id] = str(state.get("lane", "planned"))
            except Exception as exc:
                logger.debug(
                    "registry: cannot materialise event log for %s (%s)",
                    self._feature_dir.name,
                    exc,
                )

            # Last-event metadata per WP from raw events; also capture claimed_at
            # and blocked_reason by scanning events in chronological order.
            try:
                from specify_cli.status.store import read_events_raw

                for ev in read_events_raw(self._feature_dir):
                    wp_id = ev.get("wp_id")
                    if not isinstance(wp_id, str):
                        continue
                    event_id = ev.get("event_id")
                    at = _parse_iso_datetime(ev.get("at"))
                    if isinstance(event_id, str):
                        last_event_by_wp[wp_id] = (event_id, at)
                    to_lane = ev.get("to_lane")
                    if to_lane == "claimed":
                        claimed_at_by_wp[wp_id] = _parse_iso_datetime(ev.get("at"))
                    elif to_lane == "blocked":
                        reason = ev.get("reason")
                        blocked_reason_by_wp[wp_id] = reason if isinstance(reason, str) else None
            except Exception as exc:
                logger.debug(
                    "registry: cannot read raw events for %s (%s)",
                    self._feature_dir.name,
                    exc,
                )

        records: list[WorkPackageRecord] = []
        for prompt_file in sorted(tasks_dir.glob("WP*.md")):
            try:
                meta, _body = read_wp_frontmatter(prompt_file)
            except Exception as exc:
                logger.debug(
                    "registry: WP frontmatter unreadable %s (%s)",
                    prompt_file.name,
                    exc,
                )
                continue

            wp_id = meta.work_package_id or prompt_file.stem
            lane = wp_lanes.get(wp_id, "planned")

            # Subtask totals
            subtasks = list(meta.subtasks or [])
            subtasks_total = len(subtasks)
            subtasks_done = sum(
                1
                for s in subtasks
                if isinstance(s, dict)
                and (
                    s.get("status") == "done"
                    or s.get("done") is True
                )
            )

            agent_raw = meta.agent
            if isinstance(agent_raw, dict):
                agent_str: str | None = agent_raw.get("tool")
            elif isinstance(agent_raw, str) and agent_raw:
                agent_str = agent_raw
            else:
                agent_str = None

            last_event_id, last_event_at = last_event_by_wp.get(wp_id, (None, None))

            records.append(
                WorkPackageRecord(
                    wp_id=wp_id,
                    title=meta.title or prompt_file.stem,
                    lane=lane,
                    subtasks_done=subtasks_done,
                    subtasks_total=subtasks_total,
                    agent=agent_str,
                    agent_profile=meta.agent_profile,
                    role=meta.role,
                    assignee=meta.assignee,
                    phase=meta.phase,
                    prompt_path=prompt_file.resolve(),
                    dependencies=tuple(meta.dependencies or ()),
                    requirement_refs=tuple(meta.requirement_refs or ()),
                    last_event_id=last_event_id,
                    last_event_at=last_event_at,
                    claimed_at=claimed_at_by_wp.get(wp_id),
                    blocked_reason=blocked_reason_by_wp.get(wp_id),
                )
            )

        records.sort(key=lambda r: r.wp_id)
        return records


# ─────────────────────────────────────────────────────────────────────────────
# MissionRegistry
# ─────────────────────────────────────────────────────────────────────────────


class MissionRegistry:
    """Single sanctioned reader for mission-level data.

    Per ``DIRECTIVE_API_DEPENDENCY_DIRECTION`` (introduced by mission
    ``mission-registry-and-api-boundary-doctrine-01KQPDBB``), no transport-side
    module (FastAPI router, CLI command body, MCP tool) may import directly from
    ``specify_cli.dashboard.scanner``. They go through this class instead.

    Cache key is the (mtime_ns, dirent_count, sorted_dirent_names_hash) triple
    of ``<project_dir>/kitty-specs/``. Cache hits skip the directory walk
    entirely; cache misses trigger a full re-scan via the canonical scanner.

    Two-level cache (P1 fix, FR-002):
      Level 1 — structural key of kitty-specs/ directory.
      Level 2 — per-mission key for each individual mission directory.
      A structural hit still checks each mission's per-mission key; only stale
      missions are re-loaded. This ensures list_missions() detects
      status.events.jsonl appends without a kitty-specs/ directory mutation.

    All methods are safe for concurrent use; cache mutations serialize on a
    ``threading.Lock``. Concurrent reads share the cache.

    ``_wp_registries`` uses a strong-reference dict (P2 fix, FR-003). Entries
    are evicted only when the enclosing ``MissionRegistry`` instance is
    garbage-collected.
    """

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir.resolve()
        self._list_cache: CacheEntry[list[MissionRecord]] | None = None
        # Per-mission cache: keyed by feature_dir Path, holds individual CacheEntry[MissionRecord].
        self._per_mission_cache: dict[Path, CacheEntry[MissionRecord]] = {}
        # Strong-reference store for WP registries (P2 fix: was WeakValueDictionary).
        # Entries are evicted only when this MissionRegistry is garbage-collected.
        self._wp_registries: dict[str, WorkPackageRegistry] = {}
        self._lock = threading.Lock()

    @property
    def project_dir(self) -> Path:
        return self._project_dir

    def list_missions(self) -> list[MissionRecord]:
        """Return every mission under ``kitty-specs/`` in display order.

        Two-level cache behaviour (P1 fix, FR-002):
          - Structural miss: full rescan of kitty-specs/; per-mission cache rebuilt.
          - Structural hit + all missions fresh: fast path (no lock, no IO).
          - Structural hit + some missions stale: under lock, reload only stale missions.

        Never raises. Malformed meta.json produces a record with ``is_legacy=True``
        and best-effort field values.
        """
        structural_key = _kitty_specs_cache_key(self._project_dir)
        cache = self._list_cache

        if cache is not None and cache.cache_key == structural_key:
            # Structure unchanged — check per-mission freshness outside lock (fast path)
            any_stale = False
            for record in cache.value:
                mission_key = _mission_dir_cache_key(record.feature_dir)
                cached_mission = self._per_mission_cache.get(record.feature_dir)
                if cached_mission is None or cached_mission.cache_key != mission_key:
                    any_stale = True
                    break
            if not any_stale:
                # Return the exact same list object so identity checks pass (same as original).
                return cache.value

        with self._lock:
            # Double-check after acquiring the lock
            cache = self._list_cache
            if cache is None or cache.cache_key != structural_key:
                records = self._scan()
                now = datetime.now(UTC)
                self._per_mission_cache = {
                    r.feature_dir: CacheEntry(r, _mission_dir_cache_key(r.feature_dir), now)
                    for r in records
                }
                self._list_cache = CacheEntry(records, structural_key, now)
                return records

            # Structure unchanged — rebuild only stale missions
            now = datetime.now(UTC)
            result: list[MissionRecord] = []
            for record in cache.value:
                mission_key = _mission_dir_cache_key(record.feature_dir)
                cached_mission = self._per_mission_cache.get(record.feature_dir)
                if cached_mission is None or cached_mission.cache_key != mission_key:
                    record = _load_mission_record(record.feature_dir)
                    self._per_mission_cache[record.feature_dir] = CacheEntry(
                        record, mission_key, now
                    )
                else:
                    record = cached_mission.value
                result.append(record)
            self._list_cache = CacheEntry(result, structural_key, now)
            return result

    def get_mission(self, mission_id_or_slug: str) -> MissionRecord | None:
        """Resolve a mission by ``mission_id`` (ULID), ``mid8`` (8-char prefix), or ``mission_slug``.

        Resolution precedence: ``mission_id`` > ``mid8`` > ``mission_slug``.

        Returns ``None`` on miss. Never raises. An ambiguous ``mid8`` (matching
        more than one mission) returns ``None``; callers needing strict
        disambiguation should call ``list_missions()`` and filter.
        """
        if not mission_id_or_slug:
            return None
        missions = self.list_missions()

        # 1) mission_id full match
        for m in missions:
            if m.mission_id == mission_id_or_slug:
                return m

        # 2) mid8 prefix match (only if handle is exactly 8 chars and at least
        #    one mission has a mid8). Ambiguity returns None per contract.
        if len(mission_id_or_slug) == 8:
            mid8_matches = [m for m in missions if m.mid8 and m.mid8 == mission_id_or_slug]
            if len(mid8_matches) == 1:
                return mid8_matches[0]
            if len(mid8_matches) > 1:
                # Ambiguous — caller must list+filter.
                return None

        # 3) slug match
        for m in missions:
            if m.mission_slug == mission_id_or_slug:
                return m

        return None

    def workpackages_for(self, mission_id_or_slug: str) -> WorkPackageRegistry:
        """Return a WP registry scoped to one mission.

        Raises ``ValueError`` if the mission does not exist (use
        :meth:`get_mission` first to handle the missing case gracefully).

        The same ``WorkPackageRegistry`` instance is returned across calls for
        the same mission (strong-reference dict keyed by ``mission_id``). Entries
        are evicted only when this ``MissionRegistry`` instance is
        garbage-collected.
        """
        mission = self.get_mission(mission_id_or_slug)
        if mission is None:
            raise ValueError(
                f"Mission not found: {mission_id_or_slug!r}. "
                "Call get_mission() first if you need to handle the miss case."
            )

        if mission.mission_id not in self._wp_registries:
            with self._lock:
                if mission.mission_id not in self._wp_registries:
                    self._wp_registries[mission.mission_id] = WorkPackageRegistry(mission.feature_dir)
        return self._wp_registries[mission.mission_id]

    def invalidate_all(self) -> None:
        """Force a full cache flush across mission-level AND all WP-level caches.

        For test use ONLY. Production consumers MUST rely on mtime-based
        invalidation.
        """
        with self._lock:
            self._list_cache = None
            self._per_mission_cache = {}
            for wp_reg in list(self._wp_registries.values()):
                wp_reg.invalidate()

    # ── Private ────────────────────────────────────────────────────────────

    def _scan(self) -> list[MissionRecord]:
        kitty_specs = self._project_dir / "kitty-specs"
        if not kitty_specs.exists():
            return []

        records: list[MissionRecord] = []
        try:
            entries = list(kitty_specs.iterdir())
        except OSError:
            return []
        for entry in entries:
            if not entry.is_dir():
                continue
            try:
                records.append(_load_mission_record(entry))
            except Exception as exc:
                # Defence in depth: _load_mission_record already swallows; any
                # unexpected raise here is logged and skipped.
                logger.warning(
                    "registry: skipping mission directory %s due to unexpected error: %s",
                    entry.name,
                    exc,
                )
                continue

        return _missions_display_order(records)
