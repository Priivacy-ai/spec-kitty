"""Bridge between CLI ``decide_next()`` and the CLI-internal ``_internal_runtime`` engine.

The runtime is now internalized as part of mission
``shared-package-boundary-cutover-01KQ22DS``; production code no longer imports
the standalone ``spec-kitty-runtime`` PyPI package.

Maps the CLI's Decision dataclass to the runtime's NextDecision by:

1. Starting or loading a mission run (persisted under .kittify/runtime/)
2. Delegating step planning to the runtime DAG planner
3. Handling WP-level iteration within "implement" and "review" steps
4. Enforcing CLI-level guards (artifact checks, WP status)
5. Preserving the existing JSON output contract

Run state is stored locally under ``.kittify/runtime/runs/<run_id>/``.
A tracked-mission-to-run compatibility index currently lives at
``.kittify/runtime/feature-runs.json``.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from charter.invocation_context import OperationalContext as OperationalContextT

import yaml
from runtime.next._internal_runtime import (
    DiscoveryContext,
    MissionPolicySnapshot,
    MissionRunRef,
    NextDecision,
    NullEmitter,
    next_step as runtime_next_step,
    provide_decision_answer as runtime_provide_decision_answer,
    start_mission_run,
)
from runtime.next._internal_runtime.schema import ActorIdentity, MissionRuntimeError, load_mission_template_file

from specify_cli.core.atomic import atomic_write
from specify_cli.core.constants import MISSION_TYPE_SOFTWARE_DEV
from specify_cli.mission import get_mission_type
from specify_cli.mission_metadata import load_meta, load_meta_or_empty
from specify_cli.status import CanonicalStatusNotFoundError
from specify_cli.status import Lane
from specify_cli.status import wp_state_for
from runtime.next.decision import (
    Decision,
    DecisionKind,
    InvalidStepDecision,
    _build_prompt_or_error,
    _build_prompt_safe,
    _compute_wp_progress,
    _find_first_wp_by_lane,
    _state_to_action,
)
from specify_cli.sync.runtime_event_emitter import SyncRuntimeEventEmitter
from mission_runtime import routes_through_coordination

logger = logging.getLogger(__name__)

KITTIFY_DIR = ".kittify"
MISSION_RUNTIME_YAML = "mission-runtime.yaml"
MISSION_YAML = "mission.yaml"

class DecisionGitLogUnavailable(RuntimeError):
    """Decision audit logging cannot be made durable for a modern mission."""


def _primary_runtime_feature_dir(repo_root: Path, mission_slug: str) -> Path:
    """Return the PRIMARY-checkout mission feature dir for identity/meta reads.

    Mission identity (``mission_id``, ``coordination_branch``, stored topology)
    is persisted ONLY on the primary checkout's ``meta.json``. Under coordination
    topology the topology-aware resolver (``candidate_feature_dir_for_mission``)
    returns the coordination worktree once it is materialized — whose mission dir
    has NO ``meta.json`` — so reading identity there found nothing and fell back
    to the bare slug, yielding an empty ``mid8`` and a malformed
    ``kitty/mission-<slug>-`` coord branch (#2091). Anchor on the topology-BLIND
    :func:`primary_feature_dir_for_mission`, mirroring
    :func:`_mission_routes_through_coordination` above and the canonical
    precedent in ``core/paths.py`` (the same bug-class fixed for the merge
    target): the coord-aware resolver fail-closes for a materialized-but-empty
    coord worktree, so it must not gate primary-anchored identity reads.
    """
    from specify_cli.missions._read_path_resolver import (
        _canonicalize_primary_read_handle,
        primary_feature_dir_for_mission,
    )

    # WP05/FR-005: route through _canonicalize_primary_read_handle.
    return primary_feature_dir_for_mission(
        repo_root,
        _canonicalize_primary_read_handle(repo_root, mission_slug),
    )


def _resolve_coordination_branch(mission_slug: str, repo_root: Path) -> str:
    """Return the coordination branch for a mission from meta.json.

    When meta.json declares ``coordination_branch`` explicitly, that value is
    authoritative. Otherwise the branch is composed via the fail-closed WP01
    seam (:func:`coord_branch_name`/:func:`mission_branch_name_required`) using
    the declared ``mission_id``, instead of a bare ``kitty/mission-<slug>``
    f-string that drops the ``-<mid8>`` disambiguator (#1978). When the mission
    is legacy/unresolvable the seam still composes the legacy branch; a modern
    slug with no recoverable identity raises :class:`BranchIdentityUnresolved`,
    surfacing the lost identity rather than silently mis-composing.
    """
    # load_meta_or_empty (post-#2091 silent contract) absorbs a missing or
    # malformed meta.json to {}, matching the prior try/except-{} absorption.
    meta: dict[str, Any] = load_meta_or_empty(
        _primary_runtime_feature_dir(repo_root, mission_slug)
    )
    branch = meta.get("coordination_branch")
    if isinstance(branch, str) and branch.strip():
        return branch.strip()

    from specify_cli.lanes.branch_naming import mission_branch_name_required

    mission_id = meta.get("mission_id")
    resolved_id = mission_id.strip() if isinstance(mission_id, str) and mission_id.strip() else None
    return mission_branch_name_required(mission_slug, resolved_id)


def _resolve_mission_ulid(mission_slug: str, repo_root: Path) -> str | None:
    """Read the canonical ULID mission_id from meta.json via the identity SSOT.

    WP04/FR-004: Routes through ``mission_metadata.resolve_mission_identity``
    (the single source of truth) instead of hand-rolling a json.loads read.
    Returns the ULID string when present, or ``None`` when absent — fail-closed:
    callers must NOT substitute the slug for the absent ULID.
    """
    from specify_cli.mission_metadata import resolve_mission_identity  # noqa: PLC0415

    feature_dir = _primary_runtime_feature_dir(repo_root, mission_slug)
    return resolve_mission_identity(feature_dir).mission_id


def _mission_routes_through_coordination(mission_slug: str, repo_root: Path) -> bool:
    """Return True when the mission's STORED topology routes through coordination.

    Reads the WP02 stored :class:`MissionTopology` (FR-004) from ``meta.json`` via
    the **pure** :func:`read_topology` reader and disposes the coord-vs-flattened
    SHAPE from it — replacing the retired ``meta.coordination_branch is not None``
    derivation (the second #2069 inference, which keyed the decision on a value
    presence rather than the stored shape, SC-001). The read is PURE: an
    un-backfilled mission is classified once and NOT persisted, so this read path
    never writes ``meta.json`` (the read-only contract, #1814). The coord-routing
    membership is disposed by the ONE canonical predicate
    (:func:`routes_through_coordination`) over the ONE canonical set — no second
    ``{COORD, LANES_WITH_COORD}`` set is restated here (FR-005). A coord-routing
    topology (``COORD`` / ``LANES_WITH_COORD``) returns ``True``; the coord-less
    cells return ``False``. Missing/malformed meta degrades to non-coord (matching
    the historical "no declared coord topology" arm).
    """
    from specify_cli.migration.backfill_topology import read_topology
    from specify_cli.missions._read_path_resolver import (
        _canonicalize_primary_read_handle,
        primary_feature_dir_for_mission,
    )

    # Anchor the stored-topology read on the topology-BLIND primary dir (where
    # meta.json lives), mirroring ``resolution._resolve_coordination_branch`` — the
    # coord-aware resolver fail-closes for a materialized-but-empty coord worktree,
    # so it must not gate this read.
    # WP05/FR-005: route through _canonicalize_primary_read_handle.
    feature_dir = primary_feature_dir_for_mission(
        repo_root,
        _canonicalize_primary_read_handle(repo_root, mission_slug),
    )
    try:
        topology = read_topology(feature_dir)
    except (FileNotFoundError, ValueError, OSError):
        return False
    return routes_through_coordination(topology)


def _wrap_with_decision_git_log(
    emitter: SyncRuntimeEventEmitter,
    mission_slug: str,
    repo_root: Path,
) -> Any:
    """Wrap ``emitter`` with DecisionGitLog for durable decision recording.

    Returns the wrapped emitter.  If construction fails (e.g. import error),
    the original emitter is returned unchanged so mission execution is not
    blocked.
    """
    coord_routing_topology = _mission_routes_through_coordination(
        mission_slug, repo_root,
    )
    try:
        from mission_runtime import CommitTarget
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.events.decision_log import DecisionGitLog

        coordination_branch = _resolve_coordination_branch(mission_slug, repo_root)
        mission_id = _resolve_mission_ulid(mission_slug, repo_root)  # str | None

        # Resolve coord worktree path (pure static method, no side effects).
        # Derive the mid8 authoritatively from the declared mission_id via the
        # WP01 seam (FR-004): the heuristic mid8_from_slug trusts a coincidental
        # 8-char tail with no identity to confirm against, so it must not sit on
        # this correctness path (#1918). resolve_mid8 returns mission_id[:8] when
        # a ULID is declared, and declines (``""``) on a bare slug or None.
        # WP04: slug-as-sentinel removed — mission_id is now str | None from SSOT.
        from specify_cli.lanes.branch_naming import resolve_mid8 as _resolve_mid8
        _mid8 = _resolve_mid8(mission_slug, mission_id=mission_id)

        # Fail loud, never compose a malformed ``kitty/mission-<slug>-`` branch
        # (#2091): an empty mid8 on a coord-routing mission means identity was
        # unresolvable, so refuse here with a clear message rather than letting
        # ``git worktree add`` fail with an opaque exit-128 on a non-existent
        # branch. With the primary-anchored identity read above this is
        # belt-and-suspenders, but it closes the dormant mask if any future read
        # path loses the ULID again.
        if coord_routing_topology and not _mid8:
            raise DecisionGitLogUnavailable(
                f"Cannot resolve mid8 for coordination-topology mission "
                f"{mission_slug!r} (mission_id unresolvable); refusing to compose "
                "a malformed coordination branch without durable decision evidence."
            )

        # The decision-target topology SHAPE is READ from the WP02 stored topology
        # (FR-004 / SC-001) — never from ``_coord_path.exists()`` (the retired
        # disk-``stat`` ladder, C-004). The on-disk worktree-materialization check
        # (``_coord_path.exists()``) survives ONLY to choose the worktree_root for a
        # coord-routing mission (C-006 transient discrimination: materialized →
        # use it; not-yet-materialized → compose via ``CoordinationWorkspace.resolve``)
        # — it is NOT the topology classifier.
        if coord_routing_topology:
            _coord_path = CoordinationWorkspace.worktree_path(
                repo_root, mission_slug, _mid8
            )
            # C-011 risk site: the worktree_root selection is preserved EXACTLY —
            # keyed off the stored-topology coord-routing decision and the C-006
            # transient on-disk materialization check, never ``.kind``.
            worktree_root = (
                _coord_path
                if _coord_path.exists()
                else CoordinationWorkspace.resolve(repo_root, mission_slug, _mid8)
            )
            # The vestigial topology ``.kind`` carrier is dropped (WP04 drain):
            # DecisionGitLog → safe_commit reads only ``target.ref``. The VO field
            # defaults transitionally until WP16 removes it.
            decision_target = CommitTarget(ref=coordination_branch)
        else:
            # Coord-less topology: decisions land on the primary checkout's
            # current branch (a lane/mission branch); landing == coordination ==
            # target. worktree_root is the repo_root (preserved exactly).
            worktree_root = repo_root
            decision_target = CommitTarget(ref=coordination_branch)

        return DecisionGitLog(
            repo_root=repo_root,
            worktree_root=worktree_root,
            destination_ref=coordination_branch,
            mission_slug=mission_slug,
            inner=emitter,
            mission_id=mission_id,
            target=decision_target,
        )
    except Exception as exc:
        if coord_routing_topology:
            raise DecisionGitLogUnavailable(
                "DecisionGitLog construction failed for declared coordination "
                f"topology mission {mission_slug!r}; refusing to continue "
                "without durable decision evidence."
            ) from exc
        logger.warning(
            "DecisionGitLog construction failed for mission %s; "
            "falling back to plain emitter.",
            mission_slug,
            exc_info=True,
        )
        return emitter


# FR-001 / C-IC02: the typed read-path codes whose fidelity MUST be preserved
# across the next-family catch-sites. These are *read-path topology* failures
# (the mission exists but its status read surface is broken / ambiguous), as
# opposed to a genuinely-missing mission (``FEATURE_CONTEXT_UNRESOLVED`` and the
# like), which legitimately stays ``MISSION_NOT_FOUND``. Collapsing a code in
# this set into ``MISSION_NOT_FOUND`` mis-routes the operator (the disease #15).
_READ_PATH_ERROR_CODES: frozenset[str] = frozenset(
    {
        "STATUS_READ_PATH_NOT_FOUND",
        "COORDINATION_BRANCH_DELETED",
        "MISSION_AMBIGUOUS_SELECTOR",
    }
)


def _is_read_path_error(exc: object) -> bool:
    """Return True when *exc* carries a typed read-path topology code (C-IC02)."""
    return getattr(exc, "code", None) in _READ_PATH_ERROR_CODES


class QueryModeValidationError(ValueError):
    """Raised when query mode cannot produce a truthful read-only preview."""


class MissionNotFoundError(Exception):
    """Raised when a mission handle cannot be resolved to an existing mission.

    Carries the attempted handle so callers can include it in structured
    error output (FR-004 / WP03 — fail-closed next query mode), plus an
    actionable ``next_step`` remediation so operators are told concretely how
    to recover (list available missions / verify the handle). The ``next_step``
    affordance restores the operator guidance the superseded
    ``QueryModeValidationError`` used to carry (#1911).
    """

    error_code: str = "MISSION_NOT_FOUND"

    def __init__(self, handle: str, next_step: str | None = None) -> None:
        self.handle = handle
        self.next_step = next_step or (
            "Run 'spec-kitty mission list' to see available missions, then "
            f"re-run with a valid handle (attempted: '{handle}')."
        )
        super().__init__(f"Mission not found: '{handle}'")


# ---------------------------------------------------------------------------
# Feature → Run index
# ---------------------------------------------------------------------------

_FEATURE_RUNS_FILE = "feature-runs.json"
TASKS_GLOB = "WP*.md"
_REQUIREMENT_REF_PATTERN = re.compile(r"\b(?:FR|NFR|C)-\d+\b", re.IGNORECASE)


def _extract_wp_heading(line: str) -> tuple[str, int] | None:
    """Return ``(wp_id, matched_prefix_len)`` for a tasks.md WP heading line."""
    heading_level = 0
    while heading_level < len(line) and line[heading_level] == "#":
        heading_level += 1
    if heading_level < 2 or heading_level > 4:
        return None
    if heading_level >= len(line) or not line[heading_level].isspace():
        return None

    cursor = heading_level
    while cursor < len(line) and line[cursor].isspace():
        cursor += 1

    work_package_prefix = "Work Package"
    if line.startswith(work_package_prefix, cursor):
        prefix_end = cursor + len(work_package_prefix)
        if prefix_end >= len(line) or not line[prefix_end].isspace():
            return None
        cursor = prefix_end
        while cursor < len(line) and line[cursor].isspace():
            cursor += 1

    if not line.startswith("WP", cursor):
        return None
    digit_start = cursor + 2
    digit_end = digit_start + 2
    if digit_end > len(line) or not line[digit_start:digit_end].isdigit():
        return None

    wp_id = line[cursor:digit_end]
    if digit_end == len(line):
        return wp_id, digit_end

    trailing = line[digit_end]
    if trailing == ":" or not (trailing.isalnum() or trailing == "_"):
        return wp_id, digit_end
    return None


def _parse_wp_sections_from_tasks_md(tasks_content: str) -> dict[str, str]:
    """Extract WP sections from tasks.md keyed by WP ID."""
    sections: dict[str, str] = {}
    matches: list[tuple[str, int, int]] = []
    content_len = len(tasks_content)
    search_at = 0

    while True:
        wp_pos = tasks_content.find("WP", search_at)
        if wp_pos == -1:
            break

        line_start = tasks_content.rfind("\n", 0, wp_pos) + 1
        newline = tasks_content.find("\n", wp_pos)
        line_end = content_len if newline == -1 else newline + 1
        search_at = line_end

        if not tasks_content.startswith("##", line_start):
            continue

        line = tasks_content[line_start:line_end]
        heading = _extract_wp_heading(line)
        if heading is not None:
            wp_id, matched_prefix_len = heading
            matches.append((wp_id, line_start + matched_prefix_len, line_start))

    for idx, (wp_id, start, _line_start) in enumerate(matches):
        end = matches[idx + 1][2] if idx + 1 < len(matches) else len(tasks_content)
        sections[wp_id] = tasks_content[start:end]

    return sections


def _parse_requirement_refs_from_tasks_md(tasks_content: str) -> dict[str, list[str]]:
    """Parse requirement references per WP from tasks.md content."""
    return {
        wp_id: _collect_requirement_refs_for_section(section_content)
        for wp_id, section_content in _parse_wp_sections_from_tasks_md(tasks_content).items()
    }


def _collect_requirement_refs_for_section(section_content: str) -> list[str]:
    """Collect deduplicated requirement refs from one WP section."""
    refs: list[str] = []
    in_requirement_ref_list = False
    for line in section_content.splitlines():
        stripped_line = line.strip()
        if in_requirement_ref_list:
            if not stripped_line:
                continue
            if stripped_line.startswith(("-", "*")):
                refs.extend(_iter_requirement_refs(stripped_line))
                continue
            in_requirement_ref_list = False

        suffix = _requirement_inline_refs_suffix(line)
        if suffix is not None:
            refs.extend(_iter_requirement_refs(suffix))
            continue
        if _is_requirement_heading(stripped_line):
            in_requirement_ref_list = True
    return list(dict.fromkeys(refs))


def _iter_requirement_refs(text: str) -> list[str]:
    """Return normalized requirement refs found in ``text``."""
    return [ref_id.upper() for ref_id in _REQUIREMENT_REF_PATTERN.findall(text)]


def _requirement_inline_refs_suffix(line: str) -> str | None:
    """Return inline requirement-ref suffix when ``line`` is a label/value row."""
    lower_line = line.lower()
    if "requirement" not in lower_line:
        return None
    prefix, separator, suffix = line.partition(":")
    if separator and "requirement" in prefix.lower():
        return suffix
    return None


def _is_requirement_heading(stripped_line: str) -> bool:
    """Return whether a markdown heading denotes a requirement refs section."""
    if not stripped_line.startswith("#"):
        return False

    body = stripped_line.lstrip("#").strip()
    if not body:
        return False

    normalized_body = body.replace("*", "").strip().lower()
    return normalized_body in {"requirement", "requirements", "requirement refs", "requirements refs"}


class _BufferingRuntimeEmitter:
    """Records runtime emit calls in order and replays them on flush.

    Used on the legacy DAG dispatch path when the retrospective gate is
    opted in: the engine's ``next_step()`` synchronously calls the
    emitter's ``emit_mission_run_completed`` (and its sync side-effects:
    remote dispatch, queueing, etc.) the moment a terminal advance lands.
    A naive rollback that only restores local files would leave those
    sync events fired and unretractable.

    The buffer captures every emit call in order. After the engine
    returns, the bridge either flushes the buffer to the real emitter
    (gate allowed) or drops it (gate blocked). The ``flush`` is a single
    one-shot replay; subsequent calls flush nothing.

    Implements the ``RuntimeEventEmitter`` Protocol structurally — every
    emit method records ``(method_name, payload)`` and returns ``None``.
    """

    def __init__(self) -> None:
        self._calls: list[tuple[str, Any]] = []
        self._flushed = False

    def _record(self, method_name: str, payload: Any) -> None:
        self._calls.append((method_name, payload))

    def emit_mission_run_started(self, payload: Any) -> None:
        self._record("emit_mission_run_started", payload)

    def emit_next_step_issued(self, payload: Any) -> None:
        self._record("emit_next_step_issued", payload)

    def emit_next_step_auto_completed(self, payload: Any) -> None:
        self._record("emit_next_step_auto_completed", payload)

    def emit_decision_input_requested(self, payload: Any) -> None:
        self._record("emit_decision_input_requested", payload)

    def emit_decision_input_answered(self, payload: Any) -> None:
        self._record("emit_decision_input_answered", payload)

    def emit_mission_run_completed(self, payload: Any) -> None:
        self._record("emit_mission_run_completed", payload)

    def emit_significance_evaluated(self, payload: Any) -> None:
        self._record("emit_significance_evaluated", payload)

    def emit_decision_timeout_expired(self, payload: Any) -> None:
        self._record("emit_decision_timeout_expired", payload)

    def seed_from_snapshot(self, snapshot: Any) -> None:
        # Pass-through for SyncRuntimeEventEmitter compatibility; not
        # buffered because seed is idempotent and side-effect-free.
        del snapshot

    def call_count(self) -> int:
        return len(self._calls)

    def discard(self) -> None:
        """Drop all buffered calls without replaying them."""
        self._calls.clear()
        self._flushed = True

    def flush(self, target: Any) -> None:
        """Replay all buffered calls into ``target`` and mark as flushed.

        Re-flushing is a no-op so the same buffer can safely be passed
        through multiple paths without double-emitting.
        """
        if self._flushed:
            return
        for method_name, payload in self._calls:
            method = getattr(target, method_name, None)
            if method is None:
                continue
            method(payload)
        # Also seed phase state on the target from any buffered events that
        # imply phase transitions, since the buffered emitter did not run
        # the SyncRuntimeEventEmitter's _enter_phase logic.
        self._calls.clear()
        self._flushed = True


def _rich_hic_prompt() -> tuple[bool, str | None]:
    """Operator-facing Rich prompt for the HiC retrospective lifecycle.

    Lives in the bridge layer so the ``_internal_runtime/`` package keeps a
    rich/typer-free import surface (test_internal_runtime_parity).
    """
    from rich.prompt import Confirm, Prompt

    run_now: bool = Confirm.ask("Run retrospective now?", default=True)
    if run_now:
        return True, None

    skip_reason: str = ""
    while not skip_reason.strip():
        skip_reason = Prompt.ask("Skip reason (required, must be non-empty)")
    return False, skip_reason.strip()


def _resolve_mission_id_for_terminus(feature_dir: Path) -> str:
    """Read the canonical ULID mission_id from ``meta.json`` next to the feature.

    Used by the retrospective terminus wiring to identify the mission for
    event emission and gate consultation. Falls back to the feature_dir name
    when meta.json is missing or malformed (older missions predating the
    ULID identity rollout); the gate handles missing identities defensively.
    """
    # load_meta_or_empty (post-#2091 silent contract) absorbs a missing or
    # malformed meta.json to {}, matching the prior try/except-fallback.
    meta = load_meta_or_empty(feature_dir)
    mission_id = meta.get("mission_id") if isinstance(meta, dict) else None
    if isinstance(mission_id, str) and mission_id.strip():
        return mission_id
    return feature_dir.name


_RESOLUTION_ERROR = "<resolution_error>"


def _build_retrospective_facilitator_callback(
    mission_slug: str,
    repo_root: Path,
    provenance_kind: str = "runtime_post_completion",
) -> Any:
    """Build the facilitator callback that wires WP01/02/03 surfaces into the terminus.

    Returns a callable suitable for ``facilitator_callback=`` in ``run_terminus()``.
    When invoked by the terminus, it:

    1. Resolves policy via WP01 ``resolve_policy()``.
    2. Dispatches to the generator via WP02 ``generate_retrospective()``.
    3. Writes the record via WP03 ``write_gen_record(mode="error")``.
    4. Emits a ``RetrospectiveCaptured`` lifecycle event (WP03 ``emit_captured()``).

    The callback returns a ``RetrospectiveRecord`` (the old pydantic-based schema type)
    to satisfy the terminus contract.  Generator failures are classified and logged;
    the caller (terminus) decides whether to block or continue based on the exception
    propagating upward.

    WP04 — T018/T019/T020/T021
    """
    del repo_root
    # Late imports to keep the module-level import graph clean and to allow
    # the terminus to remain the single import point for heavy optional deps.
    from specify_cli.retrospective.policy import (
        PolicyResolutionError,
        resolve_policy,
    )
    from specify_cli.retrospective.generator import generate_retrospective
    from specify_cli.retrospective.writer import RecordExistsError, write_gen_record
    from specify_cli.retrospective.lifecycle_events import (
        Actor as RetroActor,
        emit_captured,
        emit_capture_failed,
    )

    _prov: str = provenance_kind  # captured in closure

    def _facilitator(
        *,
        mission_id: str,
        feature_dir: Path,  # noqa: ARG001
        repo_root: Path,
        **_kwargs: Any,
    ) -> Any:
        """WP04 facilitator: policy-resolve → generate → write → emit."""
        # Step 1: Resolve policy.
        try:
            policy, source_map = resolve_policy(repo_root)
        except PolicyResolutionError as exc:
            source_map = _resolution_error_source_map()
            _classify_and_emit_failure(
                mission_id=mission_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                exc=exc,
                source_map=source_map,
                provenance_kind=_prov,
                emit_capture_failed=emit_capture_failed,
            )
            raise

        # Short-circuit if policy disabled.
        if not policy.enabled:
            return None  # terminus interprets None as no-op for disabled paths

        # Step 2: Generate.
        try:
            record = generate_retrospective(
                mission_slug,
                policy,
                repo_root,
                provenance_kind=_prov,  # type: ignore[arg-type]
                policy_source=source_map,
            )
        except FileNotFoundError as exc:
            _classify_and_emit_failure(
                mission_id=mission_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                exc=exc,
                source_map=source_map,
                provenance_kind=_prov,
                emit_capture_failed=emit_capture_failed,
            )
            raise

        except Exception as exc:  # noqa: BLE001
            _classify_and_emit_failure(
                mission_id=mission_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                exc=exc,
                source_map=source_map,
                provenance_kind=_prov,
                emit_capture_failed=emit_capture_failed,
            )
            raise

        # Step 3: Write record.
        try:
            write_gen_record(record, repo_root=repo_root, mode="error")
        except RecordExistsError:
            # Record already written (e.g. backfill ran first).  Treat as
            # non-fatal: emit Captured with existing record path and continue.
            logger.debug(
                "Retrospective record already exists for mission %s — skipping write.",
                mission_slug,
            )
        except Exception as exc:  # noqa: BLE001
            _classify_and_emit_failure(
                mission_id=mission_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                exc=exc,
                source_map=source_map,
                provenance_kind=_prov,
                emit_capture_failed=emit_capture_failed,
            )
            raise

        # Step 4: Emit RetrospectiveCaptured lifecycle event.
        # Guard against emit failure after a successful record write — without
        # this guard, an emit-side failure (event log corruption, disk full
        # during JSONL append, etc.) leaves an orphan retrospective.yaml on
        # disk with no corresponding RetrospectiveCaptured event in the log.
        # That breaks the summary classifier (read on disk + absence of
        # Captured/Failed event → state misreported as "missing" or "failed").
        # Mission review (TOCTOU finding) caught this; we now downgrade to a
        # Failed event so the on-disk record AND the event log agree.
        runtime_actor = RetroActor(kind="runtime", id="spec-kitty-generator")
        try:
            emit_captured(
                record,
                repo_root,
                provenance_kind=_prov,  # type: ignore[arg-type]
                actor=runtime_actor,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Retrospective record written but RetrospectiveCaptured emit "
                "failed for mission %s; emitting RetrospectiveCaptureFailed.",
                mission_slug,
                exc_info=exc,
            )
            _classify_and_emit_failure(
                mission_id=mission_id,
                mission_slug=mission_slug,
                repo_root=repo_root,
                exc=exc,
                source_map=source_map,
                provenance_kind=_prov,
                emit_capture_failed=emit_capture_failed,
            )
            # Do NOT re-raise — the record is on disk; mission completion
            # should proceed under default-warn policy. Strict-block policy
            # would have already raised before reaching this step.

        # Return a minimal stub satisfying the terminus protocol.
        # The terminus uses this as a truthy "record was produced" sentinel.
        return record

    return _facilitator


def _resolution_error_source_map() -> dict[str, str]:
    """Return a minimal policy source map for malformed policy failures."""
    return {
        "enabled": _RESOLUTION_ERROR,
        "timing": _RESOLUTION_ERROR,
        "failure_policy": _RESOLUTION_ERROR,
    }


def _resolve_retrospective_policy_for_runtime(
    repo_root: Path,
) -> tuple[Any, dict[str, str], Exception | None]:
    """Resolve retrospective policy for runtime dispatch without raising."""
    from specify_cli.retrospective.policy import default_policy, resolve_policy

    try:
        policy, source_map = resolve_policy(repo_root)
    except Exception as exc:  # noqa: BLE001
        return default_policy(), _resolution_error_source_map(), exc
    return policy, source_map, None


def _retrospective_blocks_completion(policy: Any) -> bool:
    """Return True for the explicit strict pre-completion gate policy."""
    return (
        bool(getattr(policy, "enabled", False))
        and getattr(policy, "timing", None) == "before_completion"
        and getattr(policy, "failure_policy", None) == "block"
    )


def _run_retrospective_learning_capture(
    *,
    mission_id: str,
    mission_slug: str,
    feature_dir: Path,
    repo_root: Path,
    block_on_failure: bool,
) -> None:
    """Run the policy-driven retrospective capture path.

    The default product path is best-effort post-completion learning: write the
    record and emit canonical RetrospectiveCaptured/CaptureFailed events, but do
    not hold mission completion hostage. Strict projects opt into blocking by
    policy via timing=before_completion + failure_policy=block.
    """
    callback = _build_retrospective_facilitator_callback(
        mission_slug=mission_slug,
        repo_root=repo_root,
        provenance_kind="runtime_strict_gate" if block_on_failure else "runtime_post_completion",
    )
    try:
        callback(mission_id=mission_id, feature_dir=feature_dir, repo_root=repo_root)
    except Exception:
        logger.exception(
            "retrospective capture failed for mission %s (block_on_failure=%s)",
            mission_slug,
            block_on_failure,
        )
        if block_on_failure:
            raise


def _classify_exc(exc: Exception) -> str:
    """Map an exception to a failure_category string per T019 classify() table."""
    from specify_cli.retrospective.writer import RecordExistsError  # noqa: PLC0415

    if isinstance(exc, RecordExistsError):
        return "other"
    if isinstance(exc, (FileNotFoundError, IsADirectoryError)):
        return "missing_artifacts"
    # Default: generator_exception
    return "generator_exception"


def _remediation_hint(exc: Exception, source_map: dict[str, str]) -> str | None:
    """Return a remediation hint appropriate for the given exception."""
    from specify_cli.retrospective.writer import RecordExistsError  # noqa: PLC0415

    if isinstance(exc, RecordExistsError):
        return "Re-run with --overwrite to replace the existing record."
    if isinstance(exc, (FileNotFoundError, IsADirectoryError)):
        return "Run `spec-kitty migrate normalize-lifecycle` to repair missing artifacts."
    # PolicyResolutionError: surface the source
    sources = ", ".join(sorted(set(source_map.values()))) if source_map else "unknown"
    return f"Check policy configuration at: {sources}"


def _classify_and_emit_failure(
    *,
    mission_id: str,
    mission_slug: str,
    repo_root: Path,
    exc: Exception,
    source_map: dict[str, str],
    provenance_kind: str,
    emit_capture_failed: Any,
) -> None:
    """Classify ``exc`` and emit a ``RetrospectiveCaptureFailed`` event."""
    from specify_cli.retrospective.lifecycle_events import Actor as RetroActor  # noqa: PLC0415

    failure_category = _classify_exc(exc)
    hint = _remediation_hint(exc, source_map)
    runtime_actor = RetroActor(kind="runtime", id="spec-kitty-generator")

    # Trim message — no stack traces in events (T019).
    message = str(exc)[:400] if exc else "Unknown error"

    missing: list[str] | None = None
    if isinstance(exc, FileNotFoundError):
        missing = [str(exc.filename)] if getattr(exc, "filename", None) else None

    try:
        emit_capture_failed(
            mission_id=mission_id,
            mission_slug=mission_slug,
            repo_root=repo_root,
            failure_category=failure_category,  # type: ignore[arg-type]
            failure_message=message,
            remediation_hint=hint,
            policy_source=source_map,
            attempted_provenance_kind=provenance_kind,  # type: ignore[arg-type]
            missing_artifacts=missing,
            actor=runtime_actor,
        )
    except Exception:  # noqa: BLE001
        # If emission itself fails, log but don't mask the original exception.
        logger.warning("Failed to emit RetrospectureCaptureFailed event", exc_info=True)


def _feature_runs_path(repo_root: Path) -> Path:
    return repo_root / KITTIFY_DIR / "runtime" / _FEATURE_RUNS_FILE


def _load_feature_runs(repo_root: Path) -> dict[str, dict[str, str]]:
    path = _feature_runs_path(repo_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_feature_runs(repo_root: Path, index: dict[str, dict[str, str]]) -> None:
    path = _feature_runs_path(repo_root)
    content = json.dumps(index, indent=2, sort_keys=True)
    atomic_write(path, content, mkdir=True)


def _mission_key_for_run_ref(run_ref: MissionRunRef, default: str) -> str:
    """Read the mission key from either runtime field name."""
    mission_key = getattr(run_ref, "mission_key", None)
    if isinstance(mission_key, str) and mission_key.strip():
        return mission_key
    mission_type = getattr(run_ref, "mission_type", None)
    if isinstance(mission_type, str) and mission_type.strip():
        return mission_type
    return default


def _build_run_ref(*, run_id: str, run_dir: str, mission_type: str) -> MissionRunRef:
    """Construct MissionRunRef across runtime versions."""
    try:
        return MissionRunRef(
            run_id=run_id,
            run_dir=run_dir,
            mission_key=mission_type,
        )
    except TypeError:
        return MissionRunRef(
            run_id=run_id,
            run_dir=run_dir,
            mission_type=mission_type,
        )


# ---------------------------------------------------------------------------
# WP iteration helpers
# ---------------------------------------------------------------------------

_WP_ITERATION_STEPS = frozenset({"implement", "review"})


def _is_wp_iteration_step(step_id: str) -> bool:
    """Check if a step is a WP-iteration step (implement, review)."""
    return step_id in _WP_ITERATION_STEPS


def _finalized_task_board_override_step(
    feature_dir: Path,
    progress: dict[str, int | float] | None,
    *,
    status_dir: Path | None = None,
) -> str | None:
    """Return the next step implied by finalized WP state, if available.

    This is intentionally narrow: it only overrides stale early runtime phases
    after a mission already has tasks.md, finalized WP files, and canonical WP
    lane state. It does not reorder non-finalized mission DAG execution.
    """
    if progress is None:
        return None
    total = int(progress.get("total_wps", 0) or 0)
    if total <= 0:
        return None
    if not (feature_dir / "tasks.md").is_file() or not (feature_dir / "tasks").is_dir():
        return None

    if _find_first_wp_by_lane(feature_dir, "planned", status_dir=status_dir) is not None:
        return "implement"
    if _find_first_wp_by_lane(feature_dir, "claimed", status_dir=status_dir) is not None:
        return "implement"
    if _find_first_wp_by_lane(feature_dir, "in_progress", status_dir=status_dir) is not None:
        return "implement"
    if _find_first_wp_by_lane(feature_dir, "for_review", status_dir=status_dir) is not None:
        return "review"
    if _find_first_wp_by_lane(feature_dir, "in_review", status_dir=status_dir) is not None:
        return "blocked:review_in_progress"

    done = int(progress.get("done_wps", 0) or 0)
    approved = int(progress.get("approved_wps", 0) or 0)
    if done == total:
        return "done"
    if approved + done == total:
        return "accept"
    return "blocked:no_actionable_wp"


def _should_advance_wp_step(step_id: str, feature_dir: Path) -> bool:
    """Check if all WPs are done for this phase, meaning we should advance.

    For implement: all WPs must be handed off or complete
    (for_review, approved, or done).
    For review: all WPs must be approved or done.
    """
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return True  # no WPs to iterate over

    wp_files = sorted(tasks_dir.glob(TASKS_GLOB))
    if not wp_files:
        return True

    # Get canonical lane state from event log (hard-fail if absent)
    import re as _re
    from specify_cli.status import get_wp_lane

    for wp_file in wp_files:
        wp_match = _re.match(r"(WP\d+)", wp_file.stem)
        wp_id = wp_match.group(1) if wp_match else wp_file.stem
        raw_lane = get_wp_lane(feature_dir, wp_id)
        try:
            state = wp_state_for(raw_lane)
        except ValueError:
            # Unknown lane (e.g. "uninitialized" before status bootstrap) — treat as
            # not-yet-handed-off, so this WP blocks advancement.
            return False
        if _wp_blocks_step(step_id, state):
            return False

    return True


def _wp_blocks_step(step_id: str, state: Any) -> bool:
    """Return whether a WP state blocks advancement for ``step_id``."""
    lane = state.lane
    if step_id == "implement":
        # Advance past implement only when the WP has been handed off
        # (for_review or approved) or completed (done/canceled).
        # is_run_affecting is True for all active lanes; we further restrict
        # to only allow advancement for the "handed off" active lanes.
        return (
            state.is_blocked
            or (state.is_run_affecting and lane not in (Lane.FOR_REVIEW, Lane.APPROVED))
        )
    if step_id == "review":
        return lane not in (Lane.DONE, Lane.APPROVED)
    return False


# ---------------------------------------------------------------------------
# Guard evaluation (CLI-level, not runtime-level)
# ---------------------------------------------------------------------------


SPEC_ARTIFACT = "spec.md"
PLAN_ARTIFACT = "plan.md"
TASKS_ARTIFACT = "tasks.md"
STATE_FILE = "state.json"
MISSING_ARTIFACT_MESSAGE = "Required artifact missing: {name}"
MISSING_TASK_FILES_MESSAGE = f"Required: at least one tasks/{TASKS_GLOB} file"


def _check_cli_guards(step_id: str, feature_dir: Path) -> list[str]:  # noqa: C901
    """Check CLI-level guard conditions before completing a step.

    Returns list of failure descriptions. Empty list means all guards pass.
    """
    failures: list[str] = []

    if step_id == "specify":
        if not (feature_dir / SPEC_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=SPEC_ARTIFACT))

    elif step_id == "plan":
        if not (feature_dir / PLAN_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=PLAN_ARTIFACT))

    elif step_id == "tasks_outline":
        if not (feature_dir / TASKS_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=TASKS_ARTIFACT))

    elif step_id == "tasks_packages":
        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.is_dir() or not list(tasks_dir.glob(TASKS_GLOB)):
            failures.append(MISSING_TASK_FILES_MESSAGE)
        else:
            failures.extend(_check_requirement_mapping_ready(feature_dir))

    elif step_id == "tasks_finalize":
        tasks_dir = feature_dir / "tasks"
        if not tasks_dir.is_dir():
            failures.append("Required: tasks/ directory with finalized WP files")
        else:
            wp_files = sorted(tasks_dir.glob(TASKS_GLOB))
            if not wp_files:
                failures.append(MISSING_TASK_FILES_MESSAGE)
            else:
                for wp_file in wp_files:
                    if not _has_raw_dependencies_field(wp_file):
                        failures.append(f"WP {wp_file.stem} missing 'dependencies' in frontmatter (run 'spec-kitty agent mission finalize-tasks')")
                        break  # One failure message is enough
        failures.extend(_occurrence_gate_failures(feature_dir))

    elif step_id == "implement":
        if not _should_advance_wp_step("implement", feature_dir):
            failures.append("Not all work packages have required status (for_review, approved, or done)")

    elif step_id == "review" and not _should_advance_wp_step("review", feature_dir):
        failures.append("Not all work packages are approved or done")

    return failures


def _occurrence_gate_failures(feature_dir: Path) -> list[str]:
    """Bulk-edit occurrence-map gate errors (empty when not bulk_edit or map is valid).

    Reuses the existing ``ensure_occurrence_classification_ready`` enforcement
    (C-001: no new validation logic). Self-conditions on stored ``change_mode``
    (C-003), so it is safe to call unconditionally at the tasks_finalize
    boundary — non-bulk-edit missions and valid-admissible bulk-edit missions
    both return an empty list.
    """
    from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready

    return list(ensure_occurrence_classification_ready(feature_dir).errors)


def _check_requirement_mapping_ready(feature_dir: Path) -> list[str]:
    """Validate requirement coverage before issuing the finalize-tasks prompt.

    This intentionally mirrors ``agent mission finalize-tasks`` requirement
    source precedence: WP frontmatter is primary, and ``tasks.md`` is only a
    legacy fallback when no ``wps.yaml`` manifest is present.
    """
    spec_md = feature_dir / SPEC_ARTIFACT
    if not spec_md.exists():
        return []

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return []

    try:
        from specify_cli.core.wps_manifest import load_wps_manifest
        from specify_cli.requirement_mapping import (
            parse_requirement_ids_from_spec_md,
            read_all_wp_requirement_refs,
        )

        spec_ids = parse_requirement_ids_from_spec_md(spec_md.read_text(encoding="utf-8"))
        all_spec_requirement_ids = set(spec_ids["all"])
        functional_requirement_ids = set(spec_ids["functional"])

        wps_manifest = load_wps_manifest(feature_dir)
        wp_requirement_refs = read_all_wp_requirement_refs(tasks_dir)

        if wps_manifest is None:
            tasks_md = feature_dir / TASKS_ARTIFACT
            if tasks_md.exists():
                tasks_md_refs = _parse_requirement_refs_from_tasks_md(tasks_md.read_text(encoding="utf-8"))
                for wp_id, refs in tasks_md_refs.items():
                    if refs and not wp_requirement_refs.get(wp_id):
                        wp_requirement_refs[wp_id] = refs
    except Exception as exc:
        return [f"Requirement mapping preflight failed: {exc}"]

    wp_ids = sorted(wp_file.stem.split("-", 1)[0] for wp_file in tasks_dir.glob(TASKS_GLOB))
    missing_requirement_refs_wps: list[str] = []
    unknown_requirement_refs: dict[str, list[str]] = {}
    mapped_requirement_ids: set[str] = set()

    for wp_id in wp_ids:
        refs = wp_requirement_refs.get(wp_id, [])
        if not refs:
            missing_requirement_refs_wps.append(wp_id)
            continue

        unknown_refs = sorted(ref for ref in refs if ref not in all_spec_requirement_ids)
        if unknown_refs:
            unknown_requirement_refs[wp_id] = unknown_refs
        else:
            mapped_requirement_ids.update(refs)

    unmapped_functional_requirements = sorted(functional_requirement_ids - mapped_requirement_ids)
    if not (missing_requirement_refs_wps or unknown_requirement_refs or unmapped_functional_requirements):
        return []

    details: list[str] = []
    if missing_requirement_refs_wps:
        details.append(f"missing refs for WPs: {', '.join(missing_requirement_refs_wps)}")
    if unknown_requirement_refs:
        unknown_parts = [
            f"{wp_id}: {', '.join(refs)}"
            for wp_id, refs in sorted(unknown_requirement_refs.items())
        ]
        details.append(f"unknown refs: {'; '.join(unknown_parts)}")
    if unmapped_functional_requirements:
        details.append(f"unmapped FRs: {', '.join(unmapped_functional_requirements)}")

    return [
        "Requirement mapping incomplete before finalize-tasks: "
        + "; ".join(details)
        + ". Run `spec-kitty agent tasks map-requirements --batch ... --mission "
        + f"{feature_dir.name} --json` or update WP requirement_refs before finalizing."
    ]


def _has_raw_dependencies_field(wp_file: Path) -> bool:
    """Check if WP file has an explicit 'dependencies' field in raw frontmatter.

    Reads raw text to avoid auto-injection by read_frontmatter().
    """
    try:
        text = wp_file.read_text(encoding="utf-8")
    except OSError:
        return False
    if not text.startswith("---"):
        return False
    end = text.find("---", 3)
    if end == -1:
        return False
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies:"):
            return True
    return False


# ---------------------------------------------------------------------------
# Composition dispatch (WP02 / mission software-dev-composition-rewrite-01KQ26CY)
# ---------------------------------------------------------------------------
#
# These helpers route the live runtime path for the built-in ``software-dev``
# mission's five public actions (``specify``, ``plan``, ``tasks``,
# ``implement``, ``review``) through ``StepContractExecutor.execute`` instead
# of the legacy mission-runtime.yaml DAG step handlers. All other missions and
# step IDs continue to fall through to the runtime planner path unchanged
# (constraint C-008).
#
# Constraints active here:
#   - C-001: the composition path MUST go through ``StepContractExecutor``;
#     never call ``ProfileInvocationExecutor`` directly.
#   - C-002: composition produces invocation payloads; this bridge does NOT
#     generate text or call models.
#   - C-003 / FR-007: any lane-state writes inside composed steps go through
#     ``emit_status_transition`` -- this bridge writes no raw lane strings.
#   - C-008: dispatch is hard-guarded on ``mission == "software-dev"``.

# Legacy run snapshots and project-local templates may still contain the old
# tasks substep IDs. Normalize them into the single public ``tasks`` action so
# existing in-flight missions can advance through the composition path.
_LEGACY_TASKS_STEP_IDS: frozenset[str] = frozenset(
    {"tasks_outline", "tasks_packages", "tasks_finalize"}
)


def _normalize_action_for_composition(step_id: str) -> str:
    """Map a legacy DAG step ID to its composed action ID.

    The legacy ``mission-runtime.yaml`` splits ``tasks`` into three steps;
    the composition layer exposes a single ``tasks`` action whose contract
    holds the substructure internally. All other step IDs pass through
    unchanged.
    """
    if step_id in _LEGACY_TASKS_STEP_IDS:
        return "tasks"
    return step_id


def _should_dispatch_via_composition(
    mission: str,
    step_id: str,
    *,
    run_dir: Path | None = None,
    repo_root: Path | None = None,
) -> bool:
    """Return True iff ``(mission, step_id)`` routes through composition.

    Order is critical and load-bearing:

    1. **Live charter lookup** (FR-007 / FR-008): calls
       ``charter.resolve_action_sequence(mission, repo_root)`` to obtain the
       action sequence from the resolved mission-type profile.  When
       ``repo_root`` is ``None`` (e.g., the very first ``decide_next`` call
       before a run is started), fall through directly to the custom widening
       path below without a charter lookup.
    2. **Custom mission widening** (Phase 6 / R-005): consulted only when
       ``run_dir`` is provided AND the charter lookup did not already return
       ``True``. The active step's explicit binding is read from the frozen
       template; a non-empty ``agent_profile`` OR ``contract_ref`` triggers
       composition. Empty / missing bindings fall through to the legacy DAG
       handler unchanged.
    """
    # Live charter lookup path (FR-007 / FR-008).  ``repo_root`` is required;
    # without it skip directly to the custom widening path.
    if repo_root is not None:
        try:
            from charter.mission_type_profiles import (  # noqa: PLC0415
                resolve_action_sequence as _charter_resolve_action_sequence,
            )

            action_sequence = _charter_resolve_action_sequence(mission, repo_root)
            if _normalize_action_for_composition(step_id) in action_sequence:
                return True
        except Exception:
            # Degrade gracefully: if charter is unavailable or the mission type
            # is unknown, fall through to the custom widening path below so
            # in-flight missions are not broken.
            pass

    # Custom mission widening (R-005). ``run_dir`` is required to read the
    # frozen template; without it (e.g., on the very first decide_next call
    # before the run is started), fall through to the legacy DAG handler.
    if run_dir is None:
        return False
    profile, contract_ref = _resolve_step_binding(run_dir, step_id)
    return bool(profile or contract_ref)  # treat empty strings as falsy


def _resolve_step_binding(run_dir: Path, step_id: str) -> tuple[str | None, str | None]:
    """Return ``(agent_profile, contract_ref)`` for ``step_id`` in the frozen template.

    Missing templates, missing steps, and empty strings all resolve to
    ``None`` values so callers fail closed through the legacy path or the
    executor's structured error surface.
    """
    try:
        from runtime.next._internal_runtime.engine import _load_frozen_template

        template = _load_frozen_template(run_dir)
    except Exception:
        return None, None

    normalized = _normalize_action_for_composition(step_id)
    for step in template.steps:
        if step.id == step_id or step.id == normalized:
            profile = step.agent_profile.strip() if step.agent_profile else None
            contract_ref = step.contract_ref.strip() if step.contract_ref else None
            return profile or None, contract_ref or None
    return None, None


def _resolve_step_agent_profile(run_dir: Path, step_id: str) -> str | None:
    """Return the ``agent_profile`` set on ``step_id`` in the frozen template.

    Returns ``None`` when:

    - ``run_dir`` lacks a frozen template (e.g., the run has not been started
      yet, or template load otherwise raises).
    - The step is not present in the template.
    - The step's ``agent_profile`` is ``None`` or an empty string (treated as
      falsy so the gate widens only for explicit author opt-in).

    The lookup tolerates legacy ``tasks_outline`` / ``tasks_packages`` /
    ``tasks_finalize`` substep IDs by normalizing through
    ``_normalize_action_for_composition``.
    """
    profile, _contract_ref = _resolve_step_binding(run_dir, step_id)
    return profile


def _resolve_runtime_contract_for_step(
    *,
    repo_root: Path,
    run_dir: Path,
    mission: str,
    step_id: str,
) -> Any | None:
    """Resolve a custom step contract from durable frozen-template state.

    ``mission run`` and ``next`` normally execute in separate CLI processes,
    so the process-local registry populated by ``mission run`` cannot be the
    only handoff for synthesized contracts.
    """
    try:
        from doctrine.missions.step_contracts import (
            MissionStepContractRepository,
        )
        from specify_cli.mission_loader.contract_synthesis import synthesize_contracts
        from specify_cli.mission_loader.registry import lookup_contract
        from runtime.next._internal_runtime.engine import _load_frozen_template

        template = _load_frozen_template(run_dir)
    except Exception:
        return None

    normalized = _normalize_action_for_composition(step_id)
    for step in template.steps:
        if step.id != step_id and step.id != normalized:
            continue
        contract_ref = step.contract_ref.strip() if step.contract_ref else None
        if contract_ref:
            repository = MissionStepContractRepository(
                project_dir=repo_root
                / KITTIFY_DIR
                / "doctrine"
                / "mission_step_contracts"
            )
            return lookup_contract(contract_ref, repository)
        profile = step.agent_profile.strip() if step.agent_profile else None
        if profile:
            contract_id = f"custom:{mission}:{normalized}"
            for contract in synthesize_contracts(template):
                if contract.id == contract_id:
                    return contract
        return None
    return None


def _composition_dispatch_inputs(
    *,
    repo_root: Path,
    run_dir: Path,
    mission: str,
    step_id: str,
    action: str,
) -> tuple[str | None, Any | None]:
    """Return ``(profile_hint, contract)`` for a composition dispatch."""
    try:
        from charter.mission_type_profiles import (  # noqa: PLC0415
            resolve_action_sequence as _charter_resolve_action_sequence,
        )

        action_sequence = _charter_resolve_action_sequence(mission, repo_root)
        if action in action_sequence:
            return None, None
    except Exception:
        pass
    return (
        _resolve_step_agent_profile(run_dir, step_id),
        _resolve_runtime_contract_for_step(
            repo_root=repo_root,
            run_dir=run_dir,
            mission=mission,
            step_id=step_id,
        ),
    )


def _count_source_documented_events(feature_dir: Path) -> int:
    """Return the number of ``source_documented`` events in the mission event log.

    Mirrors the v1 ``event_count`` guard primitive (see
    ``src/specify_cli/mission_v1/guards.py``): reads
    ``feature_dir / "mission-events.jsonl"``, treats each line as a JSON
    record, and counts those whose ``type`` equals ``"source_documented"``.

    Missing or unreadable logs return ``0`` so the guard fails closed at the
    research ``gathering`` branch.
    """
    log_path = feature_dir / "mission-events.jsonl"
    if not log_path.is_file():
        return 0
    count = 0
    try:
        for raw_line in log_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict) and entry.get("type") == "source_documented":
                count += 1
    except OSError:
        return 0
    return count


def _publication_approved(feature_dir: Path) -> bool:
    """Return True iff the mission event log carries a ``publication_approved`` gate event.

    Mirrors the v1 ``gate_passed`` guard primitive: a gate event is recorded
    as ``{"type": "gate_passed", "name": "<gate_name>"}`` in
    ``feature_dir / "mission-events.jsonl"``. Missing or unreadable logs
    return ``False`` so the research ``output`` guard fails closed.

    This signal was chosen because the research mission's existing v1
    ``mission.yaml`` declares the same surface
    (``gate_passed("publication_approved")``) for both the source-side gate
    check and the publication-approval gate. Keeping the runtime bridge's
    guard reading from the same JSONL the v1 guard primitives consume
    avoids forking the gate-event surface during the v2 composition
    rewrite.
    """
    log_path = feature_dir / "mission-events.jsonl"
    if not log_path.is_file():
        return False
    try:
        for raw_line in log_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(entry, dict)
                and entry.get("type") == "gate_passed"
                and entry.get("name") == "publication_approved"
            ):
                return True
    except OSError:
        return False
    return False


def _has_generated_docs(feature_dir: Path) -> bool:
    """Return True iff at least one *.md file exists under feature_dir / 'docs'.

    Used by the documentation `generate` guard branch (D6 of plan.md).
    """
    docs_root = feature_dir / "docs"
    if not docs_root.is_dir():
        return False
    return next(docs_root.rglob("*.md"), None) is not None


def _check_composed_action_guard(  # noqa: C901
    action: str,
    feature_dir: Path,
    *,
    mission: str = "software-dev",
    legacy_step_id: str | None = None,
) -> list[str]:
    """CLI-level guards that fire AFTER a composed action completes.

    Mirrors ``_check_cli_guards`` semantics for the composed actions.

    The ``mission`` keyword-only parameter selects the guard branch family:

    * ``mission="software-dev"`` (default) routes through the original
      software-dev guard chain (``specify`` / ``plan`` / ``tasks`` /
      ``implement`` / ``review``).
    * ``mission="research"`` routes through the research guard chain
      (``scoping`` / ``methodology`` / ``gathering`` / ``synthesis`` /
      ``output``) plus a **fail-closed default** for any unknown research
      action — closing the v1 P1 silent-pass finding where unknown actions
      fell through with empty failures.

    For ``tasks``, the assertion shape depends on which surface invoked us:

    * **Legacy DAG path** (``legacy_step_id`` is ``"tasks_outline"`` /
      ``"tasks_packages"`` / ``"tasks_finalize"``): the runtime engine fires
      the bridge **once per substep**, so the guard must reflect the artifact
      state the user is **expected** to have produced **at that substep**, not
      the terminal post-finalize state. Demanding the terminal state on
      ``tasks_outline`` blocks the user with "Required: at least one
      tasks/WP*.md file" while the surfaced retry action is still
      ``tasks-outline`` — an unsatisfiable loop. (Mission-review follow-up to
      the original WP02 collapsed guard, which conflated dispatch
      normalization with guard semantics.)

    * **Composition-only path** (``legacy_step_id`` is ``None``): a direct
      ``action="tasks"`` invocation represents the terminal state of the
      whole composed action; the guard demands the **union** of all three
      legacy substep checks (no weakening).

    Returns a list of failure descriptions; an empty list means all guards
    pass.
    """
    failures: list[str] = []

    if mission == "research":
        # Research composition guard chain (D3) + fail-closed default for
        # unknown research actions (T022 — closes the v1 P1 silent-pass
        # finding). Every (mission="research", action=<unknown>) tuple
        # produces a non-empty failures list, which the dispatch surface
        # propagates as a structured error with no run-state advancement.
        if action == "scoping":
            if not (feature_dir / SPEC_ARTIFACT).is_file():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=SPEC_ARTIFACT))
        elif action == "methodology":
            if not (feature_dir / PLAN_ARTIFACT).is_file():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=PLAN_ARTIFACT))
        elif action == "gathering":
            if not (feature_dir / "source-register.csv").is_file():
                failures.append("Required artifact missing: source-register.csv")
            if _count_source_documented_events(feature_dir) < 3:
                failures.append("Insufficient sources documented (need >=3)")
        elif action == "synthesis":
            if not (feature_dir / "findings.md").is_file():
                failures.append("Required artifact missing: findings.md")
        elif action == "output":
            if not (feature_dir / "report.md").is_file():
                failures.append("Required artifact missing: report.md")
            if not _publication_approved(feature_dir):
                failures.append("Publication approval gate not passed")
        else:
            failures.append(
                f"No guard registered for research action: {action}"
            )
        return failures

    if mission == "documentation":
        if action == "discover":
            if not (feature_dir / SPEC_ARTIFACT).is_file():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=SPEC_ARTIFACT))
        elif action == "audit":
            if not (feature_dir / "gap-analysis.md").is_file():
                failures.append("Required artifact missing: gap-analysis.md")
        elif action == "design":
            if not (feature_dir / PLAN_ARTIFACT).is_file():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=PLAN_ARTIFACT))
        elif action == "generate":
            if not _has_generated_docs(feature_dir):
                failures.append(
                    "Required artifact missing: docs/**/*.md "
                    "(no Markdown files found under docs/)"
                )
        elif action == "validate":
            if not (feature_dir / "audit-report.md").is_file():
                failures.append("Required artifact missing: audit-report.md")
        elif action == "publish":
            if not (feature_dir / "release.md").is_file():
                failures.append("Required artifact missing: release.md")
        elif action == "accept":
            pass  # terminal status commit step; publish gate is sufficient
        else:
            failures.append(
                f"No guard registered for documentation action: {action}"
            )
        return failures

    if action == "specify":
        if not (feature_dir / SPEC_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=SPEC_ARTIFACT))

    elif action == "plan":
        if not (feature_dir / PLAN_ARTIFACT).exists():
            failures.append(MISSING_ARTIFACT_MESSAGE.format(name=PLAN_ARTIFACT))

    elif action == "tasks":
        if legacy_step_id == "tasks_outline":
            # After tasks_outline the user is expected to have produced
            # tasks.md. WP files and dependencies come in later substeps.
            if not (feature_dir / TASKS_ARTIFACT).exists():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=TASKS_ARTIFACT))
        elif legacy_step_id == "tasks_packages":
            # After tasks_packages: tasks.md AND >=1 WP file. Dependencies
            # are not yet expected — finalize-tasks adds them in the next
            # substep. Requirement mapping must already be complete so the
            # next surfaced prompt does not blindly run finalize-tasks.
            if not (feature_dir / TASKS_ARTIFACT).exists():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=TASKS_ARTIFACT))
            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.is_dir() or not list(tasks_dir.glob("WP*.md")):
                failures.append("Required: at least one tasks/WP*.md file")
            else:
                failures.extend(_check_requirement_mapping_ready(feature_dir))
        else:
            # legacy_step_id == "tasks_finalize" OR composition-only
            # (legacy_step_id is None): demand the full terminal state.
            # Union of legacy tasks_outline + tasks_packages + tasks_finalize
            # checks; no weakening of assertions.
            if not (feature_dir / TASKS_ARTIFACT).exists():
                failures.append(MISSING_ARTIFACT_MESSAGE.format(name=TASKS_ARTIFACT))
            tasks_dir = feature_dir / "tasks"
            if not tasks_dir.is_dir() or not list(tasks_dir.glob("WP*.md")):
                failures.append("Required: at least one tasks/WP*.md file")
            else:
                failures.extend(_check_requirement_mapping_ready(feature_dir))
                for wp_file in sorted(tasks_dir.glob("WP*.md")):
                    if not _has_raw_dependencies_field(wp_file):
                        failures.append(
                            f"WP {wp_file.stem} missing 'dependencies' in frontmatter "
                            "(run 'spec-kitty agent mission finalize-tasks')"
                        )
                        break  # One failure message is enough
            failures.extend(_occurrence_gate_failures(feature_dir))

    elif action == "implement":
        if not _should_advance_wp_step("implement", feature_dir):
            failures.append(
                "Not all work packages have required status (for_review, approved, or done)"
            )

    elif action == "review" and not _should_advance_wp_step("review", feature_dir):
        failures.append("Not all work packages are approved or done")

    return failures


def _dispatch_via_composition(
    *,
    repo_root: Path,
    mission: str,
    action: str,
    actor: str,
    profile_hint: str | None,
    request_text: str | None,
    mode_of_work: Any | None,
    feature_dir: Path,
    legacy_step_id: str | None = None,
    contract: Any | None = None,
) -> list[str] | None:
    """Run a composed action via ``StepContractExecutor``; then guard.

    Returns:
      - ``None`` on success (composition succeeded AND post-action guard
        passed). On the live ``decide_next_via_runtime`` path the caller then
        invokes :func:`_advance_run_state_after_composition` to progress run
        state without entering the legacy DAG dispatch handler
        (single-dispatch, FR-001/FR-002).
      - A non-empty list of failure descriptions if the executor raised
        ``StepContractExecutionError`` (FR-009: structured CLI surface, not a
        Python traceback) or the post-action guard failed. The caller turns
        this into a ``Decision`` with ``guard_failures`` populated.

    Constraint C-001 is preserved: this function only ever invokes
    ``StepContractExecutor.execute``; it never touches
    ``ProfileInvocationExecutor`` directly.

    The follow-up advancement is performed by
    :func:`_advance_run_state_after_composition`, which reuses the same
    primitives ``runtime_next_step(...)`` uses internally for state, lane,
    and prompt progression. The legacy ``runtime_next_step`` is **not**
    called for composition-backed actions (FR-001).
    """
    # Local import keeps module load lean and avoids circular import risk.
    from specify_cli.mission_step_contracts.executor import (
        StepContractExecutionContext,
        StepContractExecutionError,
        StepContractExecutor,
    )

    context = StepContractExecutionContext(
        repo_root=repo_root,
        mission=mission,
        action=action,
        actor=actor or "unknown",
        profile_hint=profile_hint,
        request_text=request_text,
        mode_of_work=mode_of_work,
    )
    # For custom missions, prefer the durable contract resolved from the
    # frozen template during ``next``. Fall back to the process-local registry
    # for in-process tests and callers, and then to the executor's repository
    # lookup for built-in software-dev dispatch.
    from specify_cli.mission_loader.registry import get_runtime_contract_registry

    selected_contract = contract or get_runtime_contract_registry().lookup(
        f"custom:{mission}:{action}"
    )
    try:
        result = StepContractExecutor(repo_root=repo_root).execute(
            context, contract=selected_contract
        )
    except StepContractExecutionError as exc:
        # Structured CLI failure surface (FR-009) — caller turns this into a
        # Decision; no Python traceback escapes.
        return [f"composition failed for {mission}/{action}: {exc}"]
    except Exception as exc:  # noqa: BLE001 — FR-009 contract: any executor
        # exception class must surface as a structured CLI failure rather than
        # a Python traceback. The narrow ``StepContractExecutionError`` catch
        # above handles the documented executor failure mode; this widened
        # catch defends against contract drift (e.g., a future executor change
        # that raises ``ValueError`` from a malformed YAML, or a transient
        # ``OSError`` reading a contract file). The exception detail is logged
        # for operator triage; the structured surface preserves the FR-009 UX.
        logger.exception(
            "unexpected exception in composition for %s/%s", mission, action
        )
        return [
            f"composition crashed for {mission}/{action}: "
            f"{type(exc).__name__}: {exc}"
        ]

    # FR-008: forward the invocation_id chain produced by the executor to the
    # bridge log so downstream event/trail writers and operators can correlate
    # the composed action with its underlying ProfileInvocationExecutor calls.
    # Defensive ``getattr`` + duck-typed length so test mocks (MagicMock) and
    # real ``StepContractExecutionResult`` instances both flow through cleanly.
    invocation_ids = getattr(result, "invocation_ids", ()) or ()
    try:
        invocation_count = len(invocation_ids)
    except TypeError:
        invocation_count = 0
    logger.info(
        "composed %s/%s emitted %d invocation(s): %s",
        mission,
        action,
        invocation_count,
        invocation_ids,
    )

    failures = _check_composed_action_guard(
        action, feature_dir, mission=mission, legacy_step_id=legacy_step_id
    )
    if failures:
        return failures
    return None


# Single-dispatch invariant (FR-001 / phase6-composition-stabilization-01KQ2JAS):
# After a composition-backed software-dev action succeeds, run state must still
# advance through the next public step — but the legacy ``runtime_next_step``
# DAG dispatch handler MUST NOT be invoked for the same action attempt. The
# helper below performs the equivalent run-state, event, and prompt
# progression by reusing the same engine primitives ``runtime_next_step`` uses
# internally (``_read_snapshot``, ``_append_event``, ``_load_frozen_template``,
# ``plan_next``, ``_write_snapshot``) plus the same ``SyncRuntimeEventEmitter``
# the legacy path uses, without re-entering the legacy DAG dispatch.
def _advance_run_state_after_composition(
    *,
    run_ref: MissionRunRef,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    feature_dir: Path,
    timestamp: str,
    progress: dict[str, int | float] | None,
    origin: dict[str, Any],
    sync_emitter: SyncRuntimeEventEmitter,
) -> Decision:
    """Advance run state after a successful composed action and return a Decision.

    Reuses the same engine primitives as ``runtime_next_step(...)`` for state,
    lane-event, and prompt progression — but does NOT invoke
    ``runtime_next_step``. This is the single-dispatch enforcement point for
    composition-backed software-dev actions (FR-001, FR-002).

    Behavior mirrors the success branch of
    ``spec_kitty_runtime.engine.next_step``:

    1. Read the current snapshot.
    2. Mark the issued step as completed; emit ``NextStepAutoCompleted``.
    3. Plan the next decision via ``plan_next`` against the frozen template.
    4. On a ``step`` decision, emit ``NextStepIssued`` and stamp
       ``issued_step_id`` so the next bridge call sees fresh state.
    5. On a ``terminal`` decision (a step actually completed), emit
       ``MissionRunCompleted``.
    6. Persist the snapshot.
    7. Return the mapped ``Decision`` via :func:`_map_runtime_decision`.

    Returns the same ``Decision`` shape ``runtime_next_step(...)`` would have
    produced for the same advance (FR-005); only the dispatch path differs.
    """
    # Local imports keep the legacy import block at the top of the module
    # focused and mirror the pattern used by ``_dispatch_via_composition``.
    from datetime import UTC, datetime

    from runtime.next._internal_runtime.engine import (
        _append_event,
        _load_frozen_template,
        _read_snapshot,
        _write_snapshot,
    )
    from runtime.next._internal_runtime.events import (
        DECISION_INPUT_REQUESTED,
        MISSION_RUN_COMPLETED,
        NEXT_STEP_AUTO_COMPLETED,
        NEXT_STEP_ISSUED,
    )
    from spec_kitty_events.mission_next import (
        DecisionInputRequestedPayload,
        MissionRunCompletedPayload,
        NextStepAutoCompletedPayload,
        NextStepIssuedPayload,
        RuntimeActorIdentity,
    )
    from runtime.next._internal_runtime.planner import plan_next
    from runtime.next._internal_runtime.schema import DecisionRequest, MissionRunSnapshot

    run_dir = Path(run_ref.run_dir)
    snapshot = _read_snapshot(run_dir)
    sync_emitter.seed_from_snapshot(snapshot)

    did_complete_step = snapshot.issued_step_id is not None

    # Step 1 — mark current step completed (success path only; composition
    # surfaces failures via ``_dispatch_via_composition``'s failure list).
    if snapshot.issued_step_id is not None:
        completed_steps = list(snapshot.completed_steps)
        completed_step_id = snapshot.issued_step_id
        if completed_step_id not in completed_steps:
            completed_steps.append(completed_step_id)

        snapshot = MissionRunSnapshot(
            run_id=snapshot.run_id,
            mission_key=snapshot.mission_key,
            template_path=snapshot.template_path,
            template_hash=snapshot.template_hash,
            policy_snapshot=snapshot.policy_snapshot,
            issued_step_id=None,
            completed_steps=completed_steps,
            inputs=snapshot.inputs,
            decisions=snapshot.decisions,
            pending_decisions=snapshot.pending_decisions,
            blocked_reason=snapshot.blocked_reason,
            mission_id=snapshot.mission_id,
            mission_slug=snapshot.mission_slug,
        )
        ac_actor = RuntimeActorIdentity(actor_id=agent, actor_type="llm")
        ac_payload = NextStepAutoCompletedPayload(
            run_id=snapshot.run_id,
            step_id=completed_step_id,
            agent_id=agent,
            result="success",
            actor=ac_actor,
        )
        _append_event(
            run_dir, NEXT_STEP_AUTO_COMPLETED, ac_payload.model_dump(mode="json")
        )
        sync_emitter.emit_next_step_auto_completed(ac_payload)

    # Step 2 — plan the next decision against the frozen template, mirroring
    # ``runtime_next_step``'s drift-detection plumbing.
    template = _load_frozen_template(run_dir)
    live_template_path: Path | None = None
    if snapshot.template_path:
        candidate = Path(snapshot.template_path)
        if candidate.exists():
            live_template_path = candidate

    decision = plan_next(
        snapshot,
        template,
        snapshot.policy_snapshot,
        actor_context={"agent_id": agent},
        live_template_path=live_template_path,
    )

    # Step 3 — record issued step / completion-of-mission / decision-required
    # events as the engine does, so downstream consumers of the run event log
    # see equivalent state. The three branches mirror
    # ``spec_kitty_runtime.engine.next_step``:
    #   - ``step``           → emit ``NextStepIssued``, stamp issued_step_id.
    #   - ``decision_required`` → persist ``pending_decisions[decision_id]``
    #     and emit ``DecisionInputRequested`` so a downstream caller can answer
    #     it. Required for project/runtime overrides and custom missions that
    #     introduce input/audit gates after a composed step (mission-review.md
    #     RISK-2 fix).
    #   - ``terminal``       → emit ``MissionRunCompleted`` if a step actually
    #     just completed (avoid duplicate emit on re-poll).
    issued_step_id = snapshot.issued_step_id
    pending_decisions = dict(snapshot.pending_decisions)
    if decision.kind == DecisionKind.step and decision.step_id:
        issued_step_id = decision.step_id
        si_actor = RuntimeActorIdentity(actor_id=agent, actor_type="llm")
        si_payload = NextStepIssuedPayload(
            run_id=snapshot.run_id,
            step_id=decision.step_id,
            agent_id=agent,
            actor=si_actor,
        )
        _append_event(run_dir, NEXT_STEP_ISSUED, si_payload.model_dump(mode="json"))
        sync_emitter.emit_next_step_issued(si_payload)
    elif decision.kind == DecisionKind.decision_required and decision.decision_id:
        # Persist input-keyed decisions in pending_decisions so they're
        # answerable; only emit + persist on first occurrence to avoid
        # duplicates on re-poll. Mirrors engine.next_step's branch verbatim
        # (modulo the runtime emitter passed in, which is the same instance).
        if decision.decision_id not in pending_decisions:
            dr_actor = RuntimeActorIdentity(actor_id=agent, actor_type="llm")
            req = DecisionRequest(
                decision_id=decision.decision_id,
                step_id=decision.step_id or "",
                question=decision.question or "",
                options=decision.options or [],
                requested_by=dr_actor,
                requested_at=datetime.now(UTC),
            )
            pending_decisions[decision.decision_id] = req.model_dump(mode="json")

            dr_payload = DecisionInputRequestedPayload(
                run_id=snapshot.run_id,
                decision_id=decision.decision_id,
                step_id=decision.step_id or "",
                question=decision.question or "",
                options=tuple(decision.options or []),
                input_key=decision.input_key,
                actor=dr_actor,
            )
            _append_event(
                run_dir, DECISION_INPUT_REQUESTED, dr_payload.model_dump(mode="json")
            )
            sync_emitter.emit_decision_input_requested(dr_payload)
    elif decision.kind == DecisionKind.terminal and did_complete_step:
        policy, _source_map, policy_error = _resolve_retrospective_policy_for_runtime(repo_root)
        retrospective_enabled = bool(getattr(policy, "enabled", False))
        block_on_retrospective = _retrospective_blocks_completion(policy)
        mission_id = _resolve_mission_id_for_terminus(feature_dir)

        if retrospective_enabled and block_on_retrospective:
            if policy_error is not None:
                raise policy_error
            _run_retrospective_learning_capture(
                mission_id=mission_id,
                mission_slug=mission_slug,
                feature_dir=feature_dir,
                repo_root=repo_root,
                block_on_failure=True,
            )

        mc_actor = RuntimeActorIdentity(actor_id=agent, actor_type="llm")
        mc_payload = MissionRunCompletedPayload(
            run_id=snapshot.run_id,
            mission_type=snapshot.mission_key,
            actor=mc_actor,
        )
        _append_event(
            run_dir, MISSION_RUN_COMPLETED, mc_payload.model_dump(mode="json")
        )
        sync_emitter.emit_mission_run_completed(mc_payload)

        if retrospective_enabled and not block_on_retrospective:
            _run_retrospective_learning_capture(
                mission_id=mission_id,
                mission_slug=mission_slug,
                feature_dir=feature_dir,
                repo_root=repo_root,
                block_on_failure=False,
            )

    # Step 4 — persist the new snapshot so the next ``decide_next_via_runtime``
    # call observes the fresh issued_step_id and any new pending_decisions.
    snapshot = MissionRunSnapshot(
        run_id=snapshot.run_id,
        mission_key=snapshot.mission_key,
        template_path=snapshot.template_path,
        template_hash=snapshot.template_hash,
        policy_snapshot=snapshot.policy_snapshot,
        issued_step_id=issued_step_id,
        completed_steps=snapshot.completed_steps,
        inputs=snapshot.inputs,
        decisions=snapshot.decisions,
        pending_decisions=pending_decisions,
        blocked_reason=snapshot.blocked_reason,
        mission_id=snapshot.mission_id,
        mission_slug=snapshot.mission_slug,
    )
    _write_snapshot(run_dir, snapshot)

    # Step 5 — map the runtime decision to the public ``Decision`` shape using
    # the same mapper the legacy path uses, preserving FR-005.
    return _map_runtime_decision(
        decision,
        agent,
        mission_slug,
        mission_type,
        repo_root,
        feature_dir,
        timestamp,
        progress,
        origin,
    )


# ---------------------------------------------------------------------------
# Run management
# ---------------------------------------------------------------------------


def _build_discovery_context(repo_root: Path) -> DiscoveryContext:
    """Build a DiscoveryContext that finds the runtime mission template."""
    import specify_cli  # noqa: PLC0415

    # Runtime bridge uses the legacy runtime templates under specify_cli/missions.
    # The doctrine mission catalog is not behaviorally equivalent yet.
    package_root = Path(specify_cli.__file__).resolve().parent / "missions"
    return DiscoveryContext(
        project_dir=repo_root,
        builtin_roots=[package_root],
    )


def _split_env_paths(value: str) -> list[Path]:
    if not value.strip():
        return []
    return [Path(chunk) for chunk in value.split(os.pathsep) if chunk.strip()]


def _project_config_pack_paths(repo_root: Path) -> list[Path]:
    config_file = repo_root / KITTIFY_DIR / "config.yaml"
    if not config_file.exists():
        return []
    try:
        raw = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    mission_packs = raw.get("mission_packs", [])
    if not isinstance(mission_packs, list):
        return []
    return [repo_root / pack for pack in mission_packs if isinstance(pack, str)]


def _candidate_templates_for_root(root: Path, mission_type: str) -> list[Path]:
    candidates: list[Path] = []

    if root.is_file():
        if root.name in {MISSION_RUNTIME_YAML, MISSION_YAML}:
            candidates.append(root)
    elif root.exists() and root.is_dir():
        candidates.extend(
            [
                root / mission_type / MISSION_RUNTIME_YAML,
                root / mission_type / MISSION_YAML,
                root / "missions" / mission_type / MISSION_RUNTIME_YAML,
                root / "missions" / mission_type / MISSION_YAML,
                root / MISSION_RUNTIME_YAML,
                root / MISSION_YAML,
            ]
        )

    # De-duplicate while preserving order.
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _template_key_for_file(path: Path) -> str | None:
    try:
        template = load_mission_template_file(path)
        return template.mission.key
    except Exception:
        return None


def _resolve_runtime_template_in_root(root: Path, mission_type: str) -> Path | None:
    for candidate in _candidate_templates_for_root(root, mission_type):
        if not candidate.exists() or not candidate.is_file():
            continue

        paths_to_try = [candidate]
        # Prefer mission-runtime.yaml sidecar when candidate is mission.yaml.
        if candidate.name == MISSION_YAML:
            runtime_sidecar = candidate.with_name(MISSION_RUNTIME_YAML)
            if runtime_sidecar.exists() and runtime_sidecar.is_file():
                paths_to_try = [runtime_sidecar, candidate]

        for path in paths_to_try:
            template_key = _template_key_for_file(path)
            if template_key == mission_type:
                return path.resolve()

    return None


def _runtime_template_key(mission_type: str, repo_root: Path) -> str:
    """Resolve the runtime template path for a mission key.

    Uses deterministic runtime discovery precedence for mission-runtime YAML:
    explicit -> env -> project override -> project legacy -> project config
    -> user global -> built-in.

    For the built-in ``software-dev`` mission, the packaged runtime template is
    canonical after this composition rewrite. Stale user-global mission packs
    from earlier installs must not reintroduce the legacy tasks_* DAG, while
    explicit, env, and project-scoped overrides remain honored.
    """
    context = _build_discovery_context(repo_root)
    env_value = os.environ.get(context.env_var_name, "")
    project_tiers: list[list[Path]] = [
        list(context.explicit_paths),
        _split_env_paths(env_value),
        [repo_root / KITTIFY_DIR / "overrides" / "missions"],
        [repo_root / KITTIFY_DIR / "missions"],
        _project_config_pack_paths(repo_root),
    ]
    global_tier = [context.user_home / KITTIFY_DIR / "missions"]
    builtin_tier = list(context.builtin_roots)
    tiers = (
        project_tiers + [builtin_tier, global_tier]
        if mission_type == MISSION_TYPE_SOFTWARE_DEV
        else project_tiers + [global_tier, builtin_tier]
    )

    for roots in tiers:
        for root in roots:
            resolved = _resolve_runtime_template_in_root(root, mission_type)
            if resolved is not None:
                return str(resolved)

    # Fallback: let runtime resolve mission key via mission.yaml discovery.
    return mission_type


def _workflow_runtime_template(
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    template_key: str,
):
    """Compose a runtime template when mission meta selects a workflow."""
    del mission_type
    mission_dir = _resolve_runtime_feature_dir(repo_root, mission_slug)
    # load_meta (post-#2091 canonical contract): allow_missing=True absorbs a
    # missing meta.json to None; malformed content still raises (on_malformed
    # defaults to "raise"), matching the prior unguarded json.loads.
    meta = load_meta(mission_dir)
    if meta is None:
        return None, None

    workflow_id = meta.get("workflow_id")
    if workflow_id is None:
        return None, None

    from runtime.next._internal_runtime.discovery import load_mission_template
    from runtime.next._internal_runtime.planner import compose_template_with_workflow
    from runtime.next._internal_runtime.workflow_registry import get_workflow

    context = _build_discovery_context(repo_root)
    base_template = load_mission_template(template_key, context=context)
    workflow = get_workflow(str(workflow_id), project_root=repo_root)
    template = compose_template_with_workflow(base_template, workflow)
    template_path = f"{template_key}#workflow:{workflow.workflow_id}"
    return template, template_path


def _existing_run_ref(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
) -> MissionRunRef | None:
    """Return an existing run without creating a new one."""
    index = _load_feature_runs(repo_root)

    if mission_slug not in index:
        return None

    entry = index[mission_slug]
    run_dir = Path(entry["run_dir"])
    if not (run_dir / STATE_FILE).exists():
        return None

    stored_mission_type = entry.get("mission_type") or entry.get("mission_key") or mission_type
    return _build_run_ref(
        run_id=entry["run_id"],
        run_dir=entry["run_dir"],
        mission_type=stored_mission_type,
    )


def _start_ephemeral_query_run(
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
) -> tuple[MissionRunRef, Path]:
    """Start a fresh query-only run outside the repository.

    This keeps fresh query mode non-mutating for the project working tree and
    `.kittify/runtime/feature-runs.json` while still using the runtime's own
    snapshot/bootstrap behavior. The temp run store is cleaned up if any
    bootstrap step raises so we never leak directories on failure paths.
    """
    run_store = Path(tempfile.mkdtemp(prefix="spec-kitty-query-run-"))
    try:
        template_key = _runtime_template_key(mission_type, repo_root)
        template_override, template_path_override = _workflow_runtime_template(
            mission_slug, mission_type, repo_root, template_key
        )
        context = _build_discovery_context(repo_root)

        run_ref = start_mission_run(
            template_key=template_key,
            inputs={"mission_slug": mission_slug},
            policy_snapshot=MissionPolicySnapshot(),
            context=context,
            run_store=run_store,
            emitter=NullEmitter(),
            template_override=template_override,
            template_path_override=template_path_override,
        )
    except Exception:
        shutil.rmtree(run_store, ignore_errors=True)
        raise
    return run_ref, run_store


def get_or_start_run(
    mission_slug: str,
    repo_root: Path,
    mission_type: str,
    *,
    emitter: Any | None = None,
) -> MissionRunRef:
    """Load existing run or start a new one.

    Run mapping stored in .kittify/runtime/feature-runs.json:
    { "042-test-feature": { "run_id": "abc", "run_dir": "..." } }
    """
    index = _load_feature_runs(repo_root)

    if mission_slug in index:
        entry = index[mission_slug]
        run_dir = Path(entry["run_dir"])
        if (run_dir / STATE_FILE).exists():
            stored_mission_type = entry.get("mission_type") or entry.get("mission_key") or mission_type
            return _build_run_ref(
                run_id=entry["run_id"],
                run_dir=entry["run_dir"],
                mission_type=stored_mission_type,
            )

    # Start a new run
    run_store = repo_root / KITTIFY_DIR / "runtime" / "runs"
    template_key = _runtime_template_key(mission_type, repo_root)
    template_override, template_path_override = _workflow_runtime_template(
        mission_slug, mission_type, repo_root, template_key
    )
    context = _build_discovery_context(repo_root)

    run_ref = start_mission_run(
        template_key=template_key,
        inputs={"mission_slug": mission_slug},
        policy_snapshot=MissionPolicySnapshot(),
        context=context,
        run_store=run_store,
        emitter=emitter or NullEmitter(),
        template_override=template_override,
        template_path_override=template_path_override,
    )

    # Persist to index
    resolved_mission_type = _mission_key_for_run_ref(run_ref, mission_type)
    resolved_mission_id = _resolve_mission_ulid(mission_slug, repo_root)
    index[mission_slug] = {
        "run_id": run_ref.run_id,
        "run_dir": run_ref.run_dir,
        "mission_type": resolved_mission_type,
        "mission_key": resolved_mission_type,
        "mission_id": resolved_mission_id,
        "mission_slug": mission_slug,
    }
    _save_feature_runs(repo_root, index)

    return run_ref


# ---------------------------------------------------------------------------
# OperationalContext wiring (FR-017, NFR-004)
# ---------------------------------------------------------------------------


def _resolve_run_dir_for_mission(
    repo_root: Path, mission_slug: str
) -> Path | None:
    """Return the persisted run directory for ``mission_slug``, read-only.

    Looks the run up in the durable ``feature-runs.json`` index without
    starting a new run (unlike :func:`get_or_start_run`). Returns ``None`` when
    no run has been recorded yet. This keeps OC construction at the claim sites
    free of any run-start side effect (NFR-004).
    """
    index = _load_feature_runs(repo_root)
    entry = index.get(mission_slug)
    if not entry:
        return None
    run_dir_raw = entry.get("run_dir")
    if not run_dir_raw:
        return None
    return Path(run_dir_raw)


def _resolve_tech_stack_for_profile(
    repo_root: Path, profile_id: str | None
) -> frozenset[str]:
    """Best-effort resolution of the in-scope tech stack for ``profile_id``.

    The tech stack is sourced from the resolved agent profile's
    ``applies_to_languages`` / specialization-context languages (charter/meta
    per data-model §7). This is best-effort: any resolution failure yields an
    empty frozenset rather than raising, so populating an
    :class:`~charter.invocation_context.OperationalContext` never blocks a
    claim or decision. The lookup is read-only and creates no worktree or
    status side effects (NFR-004).
    """
    if not profile_id:
        return frozenset()
    try:
        from doctrine.agent_profiles import AgentProfileRepository  # noqa: PLC0415

        repo = AgentProfileRepository(project_dir=repo_root / KITTIFY_DIR / "doctrine")
        profile = repo.resolve_profile(profile_id)
    except Exception:
        return frozenset()
    if profile is None:
        return frozenset()
    languages: list[str] = list(getattr(profile, "applies_to_languages", []) or [])
    spec_ctx = getattr(profile, "specialization_context", None)
    if spec_ctx is not None:
        languages.extend(getattr(spec_ctx, "languages", []) or [])
    return frozenset(lang for lang in languages if lang)


def build_operational_context_for_claim(
    *,
    repo_root: Path,
    feature_dir: Path,  # noqa: ARG001 — accepted for call-site symmetry; OC fields derive from run state/profile
    mission_slug: str,
    wp_id: str,
    actor: str | None,
    active_model: str | None,
    active_role: str | None,
    current_activity: str = "implement",
    active_profile: str | None = None,
) -> OperationalContextT:
    """Build a populated ``OperationalContext`` for a WP-claim call site.

    Shared by the two claim entry points (``implement.py`` and
    ``agent/workflow.py``) so OC-construction logic is not forked between them
    (T062/T063). Resolves the active profile from the frozen mission template
    step (via :func:`_resolve_step_agent_profile`) when the caller does not
    supply one explicitly, and derives ``tech_stack`` from that profile.

    This builder is read-only: it consults durable run state and profile
    definitions but performs no worktree allocation and emits no status event,
    so callers may invoke it before or after their own precondition checks
    without violating NFR-004.

    Args:
        repo_root: Repository root.
        feature_dir: Feature directory for the mission.
        mission_slug: Mission slug (used to locate the run directory).
        wp_id: Work package being claimed (current activity scope).
        actor: Claim actor — becomes ``active_role`` when ``active_role`` is
            not supplied.
        active_model: The ``--agent`` value for the claim.
        active_role: Explicit active role; falls back to ``actor``.
        current_activity: Activity label (defaults to ``"implement"``).
        active_profile: Explicit profile id; resolved from the template step
            when ``None``.

    Returns:
        A populated :class:`~charter.invocation_context.OperationalContext`.
    """
    from charter.invocation_context import build_operational_context  # noqa: PLC0415

    resolved_profile = active_profile
    if resolved_profile is None:
        try:
            run_dir = _resolve_run_dir_for_mission(repo_root, mission_slug)
            if run_dir is not None:
                resolved_profile = _resolve_step_agent_profile(
                    run_dir, current_activity
                )
        except Exception:
            resolved_profile = None

    return build_operational_context(
        active_model=active_model,
        active_profile=resolved_profile,
        active_role=active_role or actor,
        current_activity=current_activity or wp_id,
        tech_stack=_resolve_tech_stack_for_profile(repo_root, resolved_profile),
    )


def _build_operational_context_for_decision(
    *,
    agent: str,
    run_ref: MissionRunRef,
    feature_dir: Path,  # noqa: ARG001 — part of the R-011-E helper contract; OC fields derive from run_ref/step_id
    repo_root: Path,
    step_id: str | None,
    mission_state: str | None = None,
) -> OperationalContextT:
    """Build a populated ``OperationalContext`` for the ``next`` decision boundary.

    Extracted helper (T064) so ``decide_next_via_runtime`` — already flagged
    ``# noqa: C901`` — does not grow in complexity. Resolves the active profile
    from the issued step via :func:`_resolve_step_agent_profile`, uses
    ``step_id`` / ``mission_state`` as the current activity, and derives the
    tech stack from the resolved profile. Read-only; no side effects (NFR-004).
    """
    from charter.invocation_context import build_operational_context  # noqa: PLC0415

    activity = step_id or mission_state
    resolved_profile: str | None = None
    if step_id is not None:
        try:
            resolved_profile = _resolve_step_agent_profile(
                Path(run_ref.run_dir), step_id
            )
        except Exception:
            resolved_profile = None

    return build_operational_context(
        active_model=agent,
        active_profile=resolved_profile,
        active_role=agent,
        current_activity=activity,
        tech_stack=_resolve_tech_stack_for_profile(repo_root, resolved_profile),
    )


# ---------------------------------------------------------------------------
# Main bridge functions
# ---------------------------------------------------------------------------


def _resolve_runtime_feature_dir(repo_root: Path, mission_slug: str) -> Path:
    """Resolve a mission dir for runtime reads without importing CLI context.

    Routes through the single guarded read-side seam
    (:func:`resolve_handle_to_read_path`, WP01/IC-01): it reads the PRIMARY
    ``meta.json``, runs the ONE sanctioned mid8 cascade (``resolve_declared_mid8``)
    and returns the existence-gated topology-aware dir — folding away the bespoke
    ``_resolve_mission_ulid`` → ``resolve_mid8`` cascade here (FR-002, C-007).

    Boundary-safe fold-in (C-007): ``runtime_bridge`` already imports
    ``specify_cli.missions._read_path_resolver`` (see ``_primary_runtime_feature_dir``
    at module top), so consuming ``resolve_handle_to_read_path`` from the same
    module adds NO new package-boundary edge.

    Subsumption note (T013): the retired body derived ``mid8`` as
    ``resolve_mid8(slug, mission_id=<declared ULID or None>)`` — exactly tier 2 of
    the seam's ``resolve_declared_mid8``. The seam additionally honours an explicit
    declared ``meta.mid8`` (tier 1) before that and the ``mid8_from_slug`` heuristic
    (tier 3) after, so it resolves the SAME dir for any meta the old body handled
    while also covering the explicit-mid8 case the old body silently skipped.
    """
    from specify_cli.missions._read_path_resolver import (
        resolve_handle_to_read_path as _resolve_handle,
    )

    return _resolve_handle(repo_root, mission_slug)


def decide_next_via_runtime(  # noqa: C901
    agent: str,
    mission_slug: str,
    result: str,
    repo_root: Path,
) -> Decision:
    """Main entry point replacing old decide_next().

    Flow:
    1. Resolve mission_type from meta.json
    2. get_or_start_run() to obtain MissionRunRef
    3. Check if current step is a WP-iteration step
       a. If yes and WPs remain: skip runtime advance, build WP prompt, return step
       b. If yes and all WPs done: call next_step(result="success") to advance
    4. For non-WP steps: call next_step(run_ref, agent, result) directly
    5. Map NextDecision -> Decision (preserving JSON contract)
    """
    feature_dir = _resolve_runtime_feature_dir(repo_root, mission_slug)
    now = datetime.now(UTC).isoformat()

    if not feature_dir.is_dir():
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission="unknown",
            mission_state="unknown",
            timestamp=now,
            reason=f"Feature directory not found: {feature_dir}",
        )

    mission_type = get_mission_type(feature_dir)
    sync_emitter = SyncRuntimeEventEmitter.for_feature(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        mission_type=mission_type,
    )
    # Wrap with DecisionGitLog so decision events are durably committed to
    # the coordination branch (spec-kitty #1546, FR-001–FR-005).
    emitter_for_engine: Any = _wrap_with_decision_git_log(
        sync_emitter, mission_slug, repo_root
    )

    # Resolve origin info
    origin: dict[str, Any] = {}
    try:
        from specify_cli.runtime.resolver import resolve_mission as resolve_mission_path

        mission_result = resolve_mission_path(mission_type, repo_root)
        origin = {
            "mission_tier": getattr(mission_result.tier, "value", str(mission_result.tier)),
            "mission_path": str(mission_result.path.parent),
        }
    except FileNotFoundError:
        origin = {"mission_tier": "unknown", "mission_path": "unknown"}

    progress = _compute_wp_progress(feature_dir)

    # Get or start runtime run (before result handling so failed/blocked
    # decisions include canonical run_id, step_id, and mission_state)
    try:
        run_ref = get_or_start_run(
            mission_slug,
            repo_root,
            mission_type,
            emitter=emitter_for_engine,
        )
    except Exception as exc:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state="unknown",
            timestamp=now,
            reason=f"Failed to start/load runtime run: {exc}",
            progress=progress,
            origin=origin,
        )

    # Read current run state
    try:
        from runtime.next._internal_runtime.engine import _read_snapshot

        snapshot = _read_snapshot(Path(run_ref.run_dir))
        current_step_id = snapshot.issued_step_id
        sync_emitter.seed_from_snapshot(snapshot)
    except Exception:
        current_step_id = None

    # FR-017: populate the runtime OperationalContext at the `next` decision
    # boundary via the extracted helper (keeps this C901 function flat). The
    # builder is read-only — it never allocates a worktree or emits a status
    # event (NFR-004).
    operational_context = _build_operational_context_for_decision(
        agent=agent,
        run_ref=run_ref,
        feature_dir=feature_dir,
        repo_root=repo_root,
        step_id=current_step_id,
        mission_state=current_step_id,
    )
    logger.debug(
        "decide_next operational context: model=%s profile=%s role=%s activity=%s",
        operational_context.active_model,
        operational_context.active_profile,
        operational_context.active_role,
        operational_context.current_activity,
    )

    # WP iteration check: if we're on a WP step and WPs remain, don't advance runtime
    if result == "success" and current_step_id and _is_wp_iteration_step(current_step_id):
        try:
            should_advance = _should_advance_wp_step(current_step_id, feature_dir)
        except CanonicalStatusNotFoundError as exc:
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id,
                timestamp=now,
                reason=str(exc),
                guard_failures=[str(exc)],
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=current_step_id,
            )
        if not should_advance:
            # Stay in current step, return WP-level action
            return _build_wp_iteration_decision(
                current_step_id,
                agent,
                mission_slug,
                mission_type,
                feature_dir,
                repo_root,
                now,
                progress,
                origin,
                run_ref,
            )
        # All WPs done for this step — check guards before advancing
        guard_failures = _check_cli_guards(current_step_id, feature_dir)
        if guard_failures:
            return _build_wp_iteration_decision(
                current_step_id,
                agent,
                mission_slug,
                mission_type,
                feature_dir,
                repo_root,
                now,
                progress,
                origin,
                run_ref,
                guard_failures=guard_failures,
            )

    # Check guards for non-WP steps before advancing
    if result == "success" and current_step_id and not _is_wp_iteration_step(current_step_id):
        guard_failures = _check_cli_guards(current_step_id, feature_dir)
        if guard_failures:
            action, wp_id, workspace_path = _state_to_action(
                current_step_id,
                mission_slug,
                feature_dir,
                repo_root,
                mission_type,
            )
            prompt_file: str | None = None
            prompt_error: str | None = None
            if action:
                prompt_file, prompt_error = _build_prompt_or_error(
                    action,
                    feature_dir,
                    mission_slug,
                    wp_id,
                    agent,
                    repo_root,
                    mission_type,
                )
            else:
                prompt_error = (
                    f"no action mapped for step '{current_step_id}'; cannot resolve prompt"
                )
            if prompt_file is None:
                # WP06 (FR-006/FR-013): never issue kind=step with prompt_file=None.
                # When a prompt cannot be resolved, surface a structured blocked
                # decision so callers can stop, not partial-execute.
                return Decision(
                    kind=DecisionKind.blocked,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission=mission_type,
                    mission_state=current_step_id,
                    timestamp=now,
                    reason=prompt_error or "prompt_file_not_resolvable",
                    action=action,
                    wp_id=wp_id,
                    workspace_path=workspace_path,
                    guard_failures=guard_failures,
                    progress=progress,
                    origin=origin,
                    run_id=run_ref.run_id,
                    step_id=current_step_id,
                )
            try:
                return Decision(
                    kind=DecisionKind.step,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission=mission_type,
                    mission_state=current_step_id,
                    timestamp=now,
                    action=action,
                    wp_id=wp_id,
                    workspace_path=workspace_path,
                    prompt_file=prompt_file,
                    guard_failures=guard_failures,
                    progress=progress,
                    origin=origin,
                    run_id=run_ref.run_id,
                    step_id=current_step_id,
                )
            except InvalidStepDecision:
                # C-005: keep the kind=step prompt contract as a hard
                # constructor invariant. If the file disappears between
                # resolution and construction, surface a structured blocker.
                return Decision(
                    kind=DecisionKind.blocked,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission=mission_type,
                    mission_state=current_step_id,
                    timestamp=now,
                    reason=prompt_error or "prompt_file_not_resolvable",
                    action=action,
                    wp_id=wp_id,
                    workspace_path=workspace_path,
                    guard_failures=guard_failures,
                    progress=progress,
                    origin=origin,
                    run_id=run_ref.run_id,
                    step_id=current_step_id,
                )

    # Composition dispatch (mission `software-dev-composition-rewrite-01KQ26CY`).
    #
    # For the built-in `software-dev` mission's five public actions, route the
    # just-completed step through `StepContractExecutor.execute` BEFORE we let
    # the runtime planner advance run state. The composition produces the
    # invocation_id chain (host harness interprets it); a structured guard
    # failure surface (Decision.kind=blocked, guard_failures populated) is
    # used in lieu of a Python traceback when the executor raises
    # `StepContractExecutionError`. C-008 hard-guards this on
    # `mission == "software-dev"`; every other mission falls through to the
    # runtime planner unchanged.
    if (
        result == "success"
        and current_step_id
        and _should_dispatch_via_composition(
            mission_type,
            current_step_id,
            run_dir=Path(run_ref.run_dir),
            repo_root=repo_root,
        )
    ):
        run_dir = Path(run_ref.run_dir)
        composed_action = _normalize_action_for_composition(current_step_id)
        # R-005: for custom missions, the active step's ``agent_profile`` is
        # the source of truth for ``profile_hint``. For built-in missions
        # (e.g., ``software-dev``), built-in templates do NOT set
        # ``agent_profile``, so this resolves to ``None`` and the executor's
        # ``_resolve_profile_hint`` falls back to ``_ACTION_PROFILE_DEFAULTS``
        # — preserving byte-identical built-in dispatch behavior (FR-010).
        resolved_profile, runtime_contract = _composition_dispatch_inputs(
            repo_root=repo_root,
            run_dir=run_dir,
            mission=mission_type,
            step_id=current_step_id,
            action=composed_action,
        )
        composition_failures = _dispatch_via_composition(
            repo_root=repo_root,
            mission=mission_type,
            action=composed_action,
            actor=agent,
            profile_hint=resolved_profile,
            request_text=None,
            mode_of_work=None,
            feature_dir=feature_dir,
            # Thread the original step_id so the post-action guard can branch
            # on substep semantics for legacy tasks_outline/tasks_packages/
            # tasks_finalize. Without this, the collapsed guard demands the
            # terminal post-finalize state on every substep and blocks the
            # live tasks_outline → tasks_packages → tasks_finalize flow.
            legacy_step_id=current_step_id,
            contract=runtime_contract,
        )
        if composition_failures:
            action, wp_id, workspace_path = _state_to_action(
                current_step_id,
                mission_slug,
                feature_dir,
                repo_root,
                mission_type,
            )
            prompt_file = (
                _build_prompt_safe(
                    action or current_step_id,
                    feature_dir,
                    mission_slug,
                    wp_id,
                    agent,
                    repo_root,
                    mission_type,
                )
                if action
                else None
            )
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id,
                timestamp=now,
                reason=composition_failures[0],
                action=action,
                wp_id=wp_id,
                workspace_path=workspace_path,
                prompt_file=prompt_file,
                guard_failures=composition_failures,
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=current_step_id,
            )
        # Composition succeeded; advance run state via the
        # composition-specific advancement helper and short-circuit the
        # legacy ``runtime_next_step`` fall-through (FR-001/FR-002). The
        # helper emits the same lane / state events the legacy path emits;
        # any error from it surfaces through the existing ``Decision``
        # ``blocked`` shape (EDGE-003) — the legacy DAG dispatch handler is
        # **not** entered as a fallback.
        try:
            return _advance_run_state_after_composition(
                run_ref=run_ref,
                agent=agent,
                mission_slug=mission_slug,
                mission_type=mission_type,
                repo_root=repo_root,
                feature_dir=feature_dir,
                timestamp=now,
                progress=progress,
                origin=origin,
                sync_emitter=sync_emitter,
            )
        except Exception as exc:  # noqa: BLE001 — EDGE-003 contract: any
            # advancement-helper failure must surface as a structured
            # Decision, not as a Python traceback, and MUST NOT silently
            # fall through to the legacy DAG dispatch handler.
            logger.exception(
                "advancement helper failed after composition for %s/%s",
                mission_type,
                composed_action,
            )
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id,
                timestamp=now,
                reason=(
                    f"Run-state advancement after composition failed for "
                    f"{mission_type}/{composed_action}: "
                    f"{type(exc).__name__}: {exc}"
                ),
                progress=progress,
                origin=origin,
                run_id=run_ref.run_id,
                step_id=current_step_id,
            )

    # Strict retrospective policy remains a pre-completion gate. The default
    # post-completion policy is best-effort and must not buffer or roll back
    # MissionRunCompleted; it runs after terminal events have flushed.
    policy, _source_map, policy_error = _resolve_retrospective_policy_for_runtime(repo_root)
    retrospective_enabled = bool(getattr(policy, "enabled", False))
    block_on_retrospective = _retrospective_blocks_completion(policy)

    pre_state_bytes: bytes | None = None
    pre_events_size: int | None = None
    # Use the DecisionGitLog-wrapped emitter as the engine's emitter so that
    # decision events are durably committed to the coordination branch.
    engine_emitter: Any = emitter_for_engine
    buffer: _BufferingRuntimeEmitter | None = None

    if block_on_retrospective:
        run_dir = Path(run_ref.run_dir)
        state_path = run_dir / STATE_FILE
        events_path = run_dir / "run.events.jsonl"
        try:
            pre_state_bytes = state_path.read_bytes() if state_path.exists() else None
            pre_events_size = events_path.stat().st_size if events_path.exists() else 0
        except OSError:
            # If we cannot capture pre-state we cannot guarantee a clean
            # rollback. Surface this as a blocked Decision rather than
            # advancing into a state we cannot retract.
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id or "unknown",
                timestamp=now,
                reason=(
                    "Cannot read run state.json / run.events.jsonl before "
                    "speculative engine advance; refusing to advance"
                ),
                progress=progress,
                origin=origin,
            )
        buffer = _BufferingRuntimeEmitter()
        engine_emitter = buffer

    # Advance via runtime
    try:
        runtime_decision = runtime_next_step(
            run_ref,
            agent_id=agent,
            result=result,
            emitter=engine_emitter,
        )
    except Exception as exc:
        # Engine raised: discard any buffered events; nothing left to flush.
        if buffer is not None:
            buffer.discard()
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=current_step_id or "unknown",
            timestamp=now,
            reason=f"Runtime engine error: {exc}",
            progress=progress,
            origin=origin,
        )

    if block_on_retrospective and runtime_decision.kind == DecisionKind.terminal:
        mission_id = _resolve_mission_id_for_terminus(feature_dir)
        try:
            if policy_error is not None:
                raise policy_error
            _run_retrospective_learning_capture(
                mission_id=mission_id,
                mission_slug=mission_slug,
                feature_dir=feature_dir,
                repo_root=repo_root,
                block_on_failure=True,
            )
        except Exception as exc:
            # Gate refused. Drop the buffered emit calls (so no
            # MissionRunCompleted ever reaches the real emitter) and
            # restore state.json + truncate run.events.jsonl to pre-call.
            if buffer is not None:
                buffer.discard()
            run_dir = Path(run_ref.run_dir)
            if pre_state_bytes is not None:
                try:
                    (run_dir / STATE_FILE).write_bytes(pre_state_bytes)
                except OSError as restore_exc:
                    logger.error(
                        "rollback of state.json failed after gate block: %s",
                        restore_exc,
                    )
            if pre_events_size is not None:
                events_path = run_dir / "run.events.jsonl"
                try:
                    if events_path.exists():
                        with open(events_path, "r+b") as handle:
                            handle.truncate(pre_events_size)
                except OSError as restore_exc:
                    logger.error(
                        "rollback of run.events.jsonl failed after gate block: %s",
                        restore_exc,
                    )
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=current_step_id or "unknown",
                timestamp=now,
                reason=f"Retrospective gate refused completion: {exc}",
                progress=progress,
                origin=origin,
            )

    # Gate either passed (terminal allow) or never ran (non-terminal /
    # not opted in): flush any buffered emit calls into the real sync
    # emitter so observers receive them in original order.
    if buffer is not None:
        buffer.flush(sync_emitter)

    if (
        retrospective_enabled
        and not block_on_retrospective
        and runtime_decision.kind == DecisionKind.terminal
    ):
        mission_id = _resolve_mission_id_for_terminus(feature_dir)
        _run_retrospective_learning_capture(
            mission_id=mission_id,
            mission_slug=mission_slug,
            feature_dir=feature_dir,
            repo_root=repo_root,
            block_on_failure=False,
        )

    return _map_runtime_decision(
        runtime_decision,
        agent,
        mission_slug,
        mission_type,
        repo_root,
        feature_dir,
        now,
        progress,
        origin,
    )

def _build_finalized_override_query_decision(
    *,
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    now: str,
    progress: dict | None,
    emitted_run_id: str | None,
    repo_root: Path,
    finalized_override: str,
) -> Decision:
    override_wp_id: str | None = None
    if finalized_override == "done":
        mission_state = "done"
        preview_step = None
        reason = "All work packages are done"
    elif finalized_override.startswith("blocked:"):
        mission_state = "blocked"
        preview_step = None
        reason = finalized_override.split(":", 1)[1].replace("_", " ")
    else:
        mission_state = finalized_override
        preview_step = finalized_override
        reason = None
        if finalized_override == "implement":
            from mission_runtime import MissionArtifactKind, mission_context_for
            from runtime.next.discovery import preview_claimable_wp

            mission_context = mission_context_for(repo_root, mission_slug)
            preview = preview_claimable_wp(
                mission_context.artifact(MissionArtifactKind.WORK_PACKAGE_TASK).read_dir,
                status_dir=mission_context.artifact(MissionArtifactKind.STATUS_STATE).read_dir,
            )
            override_wp_id = preview.wp_id
            if preview.wp_id is None and preview.selection_reason is not None:
                reason = preview.selection_reason
    return Decision(
        kind=DecisionKind.query,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=mission_state,
        timestamp=now,
        is_query=True,
        reason=reason,
        progress=progress,
        run_id=emitted_run_id,
        preview_step=preview_step,
        wp_id=override_wp_id,
    )


def _build_initial_query_decision(
    *,
    runtime_decision: Any,
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    now: str,
    progress: dict | None,
    emitted_run_id: str | None,
) -> Decision:
    return Decision(
        kind=DecisionKind.query,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state="not_started",
        timestamp=now,
        is_query=True,
        reason=None,
        progress=progress,
        run_id=emitted_run_id,
        preview_step=runtime_decision.step_id,
    )


def _build_decision_required_query(
    *,
    runtime_decision: Any,
    snapshot: Any,
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    now: str,
    progress: dict | None,
    emitted_run_id: str | None,
) -> Decision:
    return Decision(
        kind=DecisionKind.query,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=snapshot.issued_step_id or runtime_decision.step_id or "unknown",
        timestamp=now,
        is_query=True,
        reason=None,
        progress=progress,
        run_id=emitted_run_id,
        step_id=snapshot.issued_step_id or runtime_decision.step_id,
        decision_id=runtime_decision.decision_id,
        input_key=runtime_decision.input_key,
        question=runtime_decision.question,
        options=runtime_decision.options,
    )


def _build_runtime_query_decision(
    *,
    runtime_decision: Any,
    snapshot: Any,
    agent: str | None,
    mission_slug: str,
    mission_type: str,
    now: str,
    progress: dict | None,
    emitted_run_id: str | None,
) -> Decision:
    mission_state = runtime_decision.step_id or "unknown"
    blocked_reason: str | None = None
    if runtime_decision.kind == DecisionKind.terminal:
        mission_state = "done"
    elif runtime_decision.kind == DecisionKind.blocked:
        mission_state = snapshot.issued_step_id or runtime_decision.step_id or "blocked"
        blocked_reason = snapshot.blocked_reason or getattr(runtime_decision, "reason", None)
    return Decision(
        kind=DecisionKind.query,
        agent=agent,
        mission_slug=mission_slug,
        mission=mission_type,
        mission_state=mission_state,
        timestamp=now,
        is_query=True,
        reason=blocked_reason,
        progress=progress,
        run_id=emitted_run_id,
        step_id=snapshot.issued_step_id or runtime_decision.step_id,
    )


def query_current_state(
    agent: str | None,
    mission_slug: str,
    repo_root: Path,
) -> Decision:
    """Return current mission state without advancing the DAG.

    Reads the run snapshot idempotently. Does NOT call next_step().
    Returns a Decision with kind=DecisionKind.query and is_query=True.

    Args:
        agent: Agent name (for Decision construction only).
        mission_slug: Mission slug (e.g. '069-planning-pipeline-integrity').
        repo_root: Repository root path.
    """
    from mission_runtime import ActionContextError, MissionArtifactKind, mission_context_for

    now = datetime.now(UTC).isoformat()
    try:
        mission_context = mission_context_for(repo_root, mission_slug)
        mission_slug = mission_context.mission_slug
    except ActionContextError as exc:
        # FR-001 / C-IC02: pass a typed *read-path* error through VERBATIM. The
        # resolver already produced the precise code (e.g.
        # COORDINATION_BRANCH_DELETED / STATUS_READ_PATH_NOT_FOUND) plus the real
        # read-path remediation; collapsing it into a generic MISSION_NOT_FOUND
        # ("run mission list") points the operator the wrong way (the mission is
        # not missing — its read path is broken; the disease #15). The command
        # layer surfaces ``exc.code`` + checked paths from the typed error.
        # (Earlier this raised ``MissionNotFoundError`` for ALL ActionContextError
        # and mis-attributed the collapse to FR-004 / WP03; that attribution was
        # stale — the next-family collapse is owned by THIS WP.)
        if _is_read_path_error(exc):
            raise
        # A genuinely-missing mission (e.g. FEATURE_CONTEXT_UNRESOLVED — no mission
        # directory at all) is legitimately MISSION_NOT_FOUND (FR-004 / WP03).
        raise MissionNotFoundError(mission_slug) from exc

    task_board = mission_context.artifact(MissionArtifactKind.WORK_PACKAGE_TASK)
    status_state = mission_context.artifact(MissionArtifactKind.STATUS_STATE)

    if not task_board.read_dir.is_dir():
        # Conscious decision (C-IC02): reaching here means the resolver RESOLVED
        # a directory and verified it ``exists()`` (see resolution.py), yet it is
        # not a directory on disk — i.e. the canonical mission dir name resolved
        # to a regular file. That is a genuinely malformed / missing mission, not
        # a read-path topology miss, so ``MISSION_NOT_FOUND`` is the correct,
        # deliberately-kept classification here (NOT a read-path collapse).
        raise MissionNotFoundError(mission_slug)

    mission_type = mission_context.mission_type
    progress = _compute_wp_progress(task_board.read_dir, status_dir=status_state.read_dir)

    run_ref = _existing_run_ref(mission_slug, repo_root, mission_type)
    ephemeral_run_store: Path | None = None

    # Read current step WITHOUT calling next_step(). When no step has been
    # issued yet, use the planner read-only to compute a truthful preview.
    # The try/finally below guarantees the ephemeral run store is cleaned up
    # on every return path (success, raise, or early exit).
    try:
        try:
            from runtime.next._internal_runtime import engine
            from runtime.next._internal_runtime.planner import plan_next

            if run_ref is None:
                run_ref, ephemeral_run_store = _start_ephemeral_query_run(
                    mission_slug,
                    mission_type,
                    repo_root,
                )
                snapshot = engine._read_snapshot(Path(run_ref.run_dir))
                template_path = Path(run_ref.run_dir) / "mission_template_frozen.yaml"
                template = load_mission_template_file(template_path)
            else:
                snapshot = engine._read_snapshot(Path(run_ref.run_dir))
                template_path = Path(snapshot.template_path)
                template = load_mission_template_file(template_path)
            runtime_decision = plan_next(
                snapshot,
                template,
                snapshot.policy_snapshot,
                live_template_path=template_path,
            )
        except QueryModeValidationError:
            raise
        except Exception as exc:
            raise QueryModeValidationError(f"Could not read query state for mission '{mission_slug}': {exc}") from exc

        # Query mode never persists the ephemeral run it bootstraps for a
        # not-yet-started mission. Returning that run's id in the JSON would
        # mislead callers into thinking they can issue ``spec-kitty next
        # --mission <slug> --result …`` against it; in reality the run state
        # is wiped in the finally block before the function returns. Only
        # emit ``run_id`` when the run is a real, persisted one.
        emitted_run_id: str | None = None
        if ephemeral_run_store is None:
            emitted_run_id = getattr(run_ref, "run_id", None)

        finalized_override = _finalized_task_board_override_step(
            task_board.read_dir,
            progress,
            status_dir=status_state.read_dir,
        )
        if finalized_override is not None:
            return _build_finalized_override_query_decision(
                agent=agent,
                mission_slug=mission_slug,
                mission_type=mission_type,
                now=now,
                progress=progress,
                emitted_run_id=emitted_run_id,
                repo_root=repo_root,
                finalized_override=finalized_override,
            )

        if not snapshot.completed_steps and not snapshot.pending_decisions and not snapshot.decisions:
            if runtime_decision.kind in {DecisionKind.step, DecisionKind.decision_required} and runtime_decision.step_id:
                return _build_initial_query_decision(
                    runtime_decision=runtime_decision,
                    agent=agent,
                    mission_slug=mission_slug,
                    mission_type=mission_type,
                    now=now,
                    progress=progress,
                    emitted_run_id=emitted_run_id,
                )
            raise QueryModeValidationError(f"Mission '{mission_type}' has no issuable first step for run '{mission_slug}'")

        if runtime_decision.kind == DecisionKind.decision_required:
            return _build_decision_required_query(
                runtime_decision=runtime_decision,
                snapshot=snapshot,
                agent=agent,
                mission_slug=mission_slug,
                mission_type=mission_type,
                now=now,
                progress=progress,
                emitted_run_id=emitted_run_id,
            )

        return _build_runtime_query_decision(
            runtime_decision=runtime_decision,
            snapshot=snapshot,
            agent=agent,
            mission_slug=mission_slug,
            mission_type=mission_type,
            now=now,
            progress=progress,
            emitted_run_id=emitted_run_id,
        )
    finally:
        if ephemeral_run_store is not None:
            shutil.rmtree(ephemeral_run_store, ignore_errors=True)


def answer_decision_via_runtime(
    mission_slug: str,
    decision_id: str,
    answer: str,
    agent: str,
    repo_root: Path,
    *,
    actor_type: str = "human",
) -> None:
    """Answer a pending decision.

    CLI answers are human-authored by default even though the command still
    carries an ``--agent`` identity for the surrounding mission loop.
    """
    import logging

    logger = logging.getLogger(__name__)

    from mission_runtime import ActionContextError, resolve_action_context

    try:
        _ctx = resolve_action_context(
            repo_root,
            action="tasks",
            feature=mission_slug,
        )
        feature_dir = Path(_ctx.feature_dir)
    except ActionContextError as exc:
        # FR-001 / C-IC02: preserve the typed read-path error IDENTICALLY on the
        # decision-answer path (the same fidelity obligation as the query path).
        # Collapsing it into a generic "not found" MissionRuntimeError would drop
        # ``exc.code`` (e.g. COORDINATION_BRANCH_DELETED) and the read-path
        # remediation, mis-routing the operator. Log the context, then re-raise
        # the typed ActionContextError so the command layer surfaces its code.
        logger.warning(
            "answer_decision_via_runtime: read-path error (%s) for mission %r in "
            "repo %s — cannot answer decision %r",
            exc.code,
            mission_slug,
            repo_root,
            decision_id,
        )
        raise
    if not feature_dir.is_dir():
        logger.warning(
            "answer_decision_via_runtime: mission %r resolved to missing dir %s — cannot answer decision %r",
            mission_slug,
            feature_dir,
            decision_id,
        )
        raise MissionRuntimeError(
            f"Mission {mission_slug!r} not found; cannot answer decision {decision_id!r}"
        )
    mission_type = get_mission_type(feature_dir)
    run_ref = get_or_start_run(mission_slug, repo_root, mission_type)
    sync_emitter = SyncRuntimeEventEmitter.for_feature(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        mission_type=mission_type,
    )
    try:
        from runtime.next._internal_runtime.engine import _read_snapshot

        sync_emitter.seed_from_snapshot(_read_snapshot(Path(run_ref.run_dir)))
    except Exception as exc:
        logger.warning(
            "answer_decision_via_runtime: failed to seed emitter from snapshot for run %r: %s",
            run_ref.run_dir,
            exc,
        )
    # Wrap with DecisionGitLog so the answered decision is committed to the
    # coordination branch (spec-kitty #1546, FR-001–FR-005).
    answer_emitter: Any = _wrap_with_decision_git_log(
        sync_emitter, mission_slug, repo_root
    )
    actor = ActorIdentity(actor_id=agent, actor_type=actor_type)
    runtime_provide_decision_answer(
        run_ref,
        decision_id,
        answer,
        actor,
        emitter=answer_emitter,
    )


# ---------------------------------------------------------------------------
# Internal mapping helpers
# ---------------------------------------------------------------------------


def _build_wp_iteration_decision(
    step_id: str,
    agent: str,
    mission_slug: str,
    mission_type: str,
    feature_dir: Path,
    repo_root: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
    run_ref: MissionRunRef,
    guard_failures: list[str] | None = None,
) -> Decision:
    """Build a Decision for WP iteration within a step."""
    action, wp_id, workspace_path = _state_to_action(
        step_id,
        mission_slug,
        feature_dir,
        repo_root,
        mission_type,
    )

    if action is None:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=f"No action mapped for step '{step_id}'",
            guard_failures=guard_failures or [],
            progress=progress,
            origin=origin,
            run_id=run_ref.run_id,
            step_id=step_id,
        )

    prompt_file, prompt_error = _build_prompt_or_error(
        action,
        feature_dir,
        mission_slug,
        wp_id,
        agent,
        repo_root,
        mission_type,
    )
    if prompt_file is None:
        # WP06 (FR-006/FR-013): kind=step decisions must always carry a
        # non-empty resolvable prompt_file. When prompt resolution fails,
        # surface a structured blocked decision instead of a partial step.
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=prompt_error or "no_prompt_template",
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
            guard_failures=guard_failures or [],
            progress=progress,
            origin=origin,
            run_id=run_ref.run_id,
            step_id=step_id,
        )

    try:
        return Decision(
            kind=DecisionKind.step,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
            prompt_file=prompt_file,
            guard_failures=guard_failures or [],
            progress=progress,
            origin=origin,
            run_id=run_ref.run_id,
            step_id=step_id,
        )
    except InvalidStepDecision:
        # C-005: prompt_builder failed to produce a usable prompt for this
        # WP iteration. Route to kind=blocked rather than emitting a
        # kind=step with a null/unresolvable prompt_file.
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id,
            timestamp=timestamp,
            reason=prompt_error or "prompt_file_not_resolvable",
            action=action,
            wp_id=wp_id,
            workspace_path=workspace_path,
            guard_failures=guard_failures or [],
            progress=progress,
            origin=origin,
            run_id=run_ref.run_id,
            step_id=step_id,
        )


def _map_runtime_decision(
    decision: NextDecision,
    agent: str,
    mission_slug: str,
    mission_type: str,
    repo_root: Path,
    feature_dir: Path,
    timestamp: str,
    progress: dict | None,
    origin: dict,
) -> Decision:
    """Convert runtime NextDecision to CLI Decision dataclass.

    Exit-code contract (FR-008):
    - ``kind="terminal"`` → ``DecisionKind.terminal`` → ``next_cmd`` exits 0
    - ``kind="blocked"``  → ``DecisionKind.blocked``  → ``next_cmd`` exits 1
    - ``kind="step"``     → ``DecisionKind.step``     → ``next_cmd`` exits 0

    ``next_cmd.py`` maps the kind to exit code; this function must not change
    the kind semantics. Verified by:
    - ``tests/next/test_next_command_integration.py::TestNextCommandCLI::test_terminal_state_exit_code_zero``
    - ``tests/next/test_next_command_integration.py::TestNextCommandCLI::test_blocked_result_exit_code``
    """
    step_id = decision.step_id
    run_id = decision.run_id

    if decision.kind == DecisionKind.terminal:
        return Decision(
            kind=DecisionKind.terminal,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state="done",
            timestamp=timestamp,
            reason=decision.reason or "Mission complete",
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )

    if decision.kind == DecisionKind.blocked:
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=decision.reason,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )

    if decision.kind == DecisionKind.decision_required:
        prompt_file = None
        if decision.question:
            from runtime.next.prompt_builder import build_decision_prompt

            try:
                _, prompt_path = build_decision_prompt(
                    question=decision.question,
                    options=decision.options,
                    decision_id=decision.decision_id or "unknown",
                    mission_slug=mission_slug,
                    repo_root=repo_root,
                    agent=agent,
                )
                prompt_file = str(prompt_path)
            except Exception:
                pass

        return Decision(
            kind=DecisionKind.decision_required,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=decision.reason or "Decision required",
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
            decision_id=decision.decision_id,
            input_key=decision.input_key,
            question=decision.question,
            options=decision.options,
            prompt_file=prompt_file,
        )

    # kind == "step"
    if step_id and _is_wp_iteration_step(step_id):
        # WP step: map to implement/review action with WP selection
        action, wp_id, workspace_path = _state_to_action(
            step_id,
            mission_slug,
            feature_dir,
            repo_root,
            mission_type,
        )
        if action is None:
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=timestamp,
                reason=f"No action mapped for WP step '{step_id}'",
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
            )
        prompt_file, prompt_error = _build_prompt_or_error(
            action,
            feature_dir,
            mission_slug,
            wp_id,
            agent,
            repo_root,
            mission_type,
        )
        if prompt_file is None:
            # WP06 (FR-006/FR-013): kind=step requires a resolvable prompt;
            # fall through to blocked when one cannot be built.
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=timestamp,
                reason=prompt_error or "prompt_file_not_resolvable",
                action=action,
                wp_id=wp_id,
                workspace_path=workspace_path,
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
            )
        try:
            return Decision(
                kind=DecisionKind.step,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=timestamp,
                action=action,
                wp_id=wp_id,
                workspace_path=workspace_path,
                prompt_file=prompt_file,
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
            )
        except InvalidStepDecision:
            return Decision(
                kind=DecisionKind.blocked,
                agent=agent,
                mission_slug=mission_slug,
                mission=mission_type,
                mission_state=step_id,
                timestamp=timestamp,
                reason=prompt_error or "prompt_file_not_resolvable",
                action=action,
                wp_id=wp_id,
                workspace_path=workspace_path,
                progress=progress,
                origin=origin,
                run_id=run_id,
                step_id=step_id,
            )

    # Non-WP step: map step_id to action via template resolution
    action, wp_id, workspace_path = _state_to_action(
        step_id or "unknown",
        mission_slug,
        feature_dir,
        repo_root,
        mission_type,
    )
    prompt_file: str | None = None
    prompt_error: str | None = None
    if action or step_id:
        prompt_file, prompt_error = _build_prompt_or_error(
            action or step_id or "unknown",
            feature_dir,
            mission_slug,
            wp_id,
            agent,
            repo_root,
            mission_type,
        )
    else:
        prompt_error = "no action and no step_id; cannot resolve prompt"
    if prompt_file is None:
        # WP06 (FR-006/FR-013): emit a structured blocked decision rather than
        # an issued step that has no resolvable prompt.
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=prompt_error or "no_prompt_template",
            action=action or step_id,
            wp_id=wp_id,
            workspace_path=workspace_path,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )

    try:
        return Decision(
            kind=DecisionKind.step,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            action=action or step_id,
            wp_id=wp_id,
            workspace_path=workspace_path,
            prompt_file=prompt_file,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )
    except InvalidStepDecision:
        # C-005: non-WP step path — prompt resolution failed (no template,
        # build error, or null step_id with no action). Surface as blocked
        # rather than emit kind=step with a null/unresolvable prompt.
        return Decision(
            kind=DecisionKind.blocked,
            agent=agent,
            mission_slug=mission_slug,
            mission=mission_type,
            mission_state=step_id or "unknown",
            timestamp=timestamp,
            reason=prompt_error or "prompt_file_not_resolvable",
            action=action or step_id,
            wp_id=wp_id,
            workspace_path=workspace_path,
            progress=progress,
            origin=origin,
            run_id=run_id,
            step_id=step_id,
        )
