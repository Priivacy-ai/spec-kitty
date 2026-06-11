"""Pure-Python retrospective generator for Spec Kitty missions.

Reads mission artifacts from disk and produces a schema-valid GenRetrospectiveRecord.
The output is byte-deterministic given the same (mission_handle, policy, repo_root) inputs.

Source-of-truth spec: kitty-specs/retrospective-default-policy-01KS049J/spec.md
Data model:           kitty-specs/retrospective-default-policy-01KS049J/data-model.md
FR refs: FR-006, FR-007, FR-010

Design decision:
- Pure-Python; no subprocess calls.
- Missing optional artifacts are recorded as gaps entries, NOT exceptions.
- Generation MUST NOT mutate doctrine / DRG / glossary. Proposals are data only.
- findings_status values in persisted records: ONLY "has_findings" or "ran_no_findings".
  "missing" and "failed" are event-payload-only states per data-model invariants.
"""

from __future__ import annotations

from specify_cli.core.constants import KITTY_SPECS_DIR
import contextlib
import datetime
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.retrospective.schema import (
    FindingsStatus,
    GenActor,
    GenEvidenceRef,
    GenFinding,
    GenProposal,
    GenProvenance,
    GenRetrospectiveRecord,
    ProvenanceKind,
    validate_record,
)
# NOTE: ``REVIEWER_SELF_APPROVAL`` is imported lazily inside the consuming
# function (see below) rather than at module scope. This module is reached
# during ``status`` package initialization (status.models →
# retrospective.schema → retrospective.__init__ → generator), so a module-level
# ``from specify_cli.status import ...`` would form an import cycle against the
# partially-initialized facade. The lazy import keeps the consumer on the public
# facade without re-introducing a deep ``status.*`` submodule import.

if TYPE_CHECKING:
    from specify_cli.retrospective.policy import RetrospectivePolicy

# Public constant: version this generator so future tooling can reason about
# field-by-field freshness.
GENERATOR_VERSION = "1.0"

# Only "flag_not_helpful" proposals are low-risk.  Everything else is structural.
# Proposal.suggested_action must start with one of these values (e.g.
# "flag_not_helpful: <term>") for risk_class to be "low".
LOW_RISK_PROPOSAL_KINDS: frozenset[str] = frozenset({"flag_not_helpful"})

# Regex to detect open clarification markers in spec.md
_NEEDS_CLARIFICATION_RE = re.compile(r"\[NEEDS CLARIFICATION:", re.IGNORECASE)

# Regex to detect FR references in WP task files
_FR_REF_RE = re.compile(r"\b(FR-\d{3,})\b")

_WP_ID_RE = re.compile(r"^\w{2,5}\d{2,3}$")


# ---------------------------------------------------------------------------
# Mission resolution helpers
# ---------------------------------------------------------------------------


def _resolve_mission_dir(mission_handle: str, repo_root: Path) -> Path | None:
    """Resolve a mission handle to its kitty-specs directory.

    Resolution order:
    1. Exact match of handle to directory name under kitty-specs/.
    2. Partial match: handle is a prefix (e.g. slug without mission_number prefix).
    3. Match against mission_id / mid8 in meta.json.

    Returns the feature_dir Path on success, or None if not found.
    """
    specs_root = repo_root / KITTY_SPECS_DIR
    if not specs_root.exists():
        return None

    # Direct match
    candidate: Path = specs_root / mission_handle
    if candidate.exists() and candidate.is_dir():
        return candidate

    # Partial match: scan all dirs, match by slug or mission_id
    for child in sorted(specs_root.iterdir(), key=lambda p: p.name):
        child_path = Path(child)
        if not child_path.is_dir():
            continue
        # Match directory name prefix
        if child_path.name == mission_handle or child_path.name.endswith(f"-{mission_handle}"):
            return child_path
        # Match via meta.json mission_id or mission_slug
        meta_path = child_path / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                mid = str(meta.get("mission_id", ""))
                slug = str(meta.get("mission_slug", ""))
                if mid == mission_handle or mid[:8] == mission_handle or slug == mission_handle:
                    return child_path
            except (json.JSONDecodeError, OSError):
                continue

    return None


def _load_meta(feature_dir: Path) -> dict[str, Any]:
    """Load meta.json; return empty dict if missing or malformed."""
    meta_path = feature_dir / "meta.json"
    if not meta_path.exists():
        return {}
    try:
        result: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
        return result
    except (json.JSONDecodeError, OSError):
        return {}


def _read_optional_text(path: Path) -> str | None:
    """Read a text file; return None if it does not exist."""
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None
    return None


def _load_events(feature_dir: Path) -> list[dict[str, Any]]:
    """Load all status events from status.events.jsonl.

    Returns a list of event dicts sorted by natural file order (append order).
    """
    events_path = feature_dir / "status.events.jsonl"
    if not events_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _load_wp_files(feature_dir: Path) -> list[tuple[str, str]]:
    """Load tasks/WP*.md files; return sorted (filename, content) pairs."""
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return []
    wp_files = sorted(tasks_dir.glob("WP*.md"), key=lambda p: p.name)
    result = []
    for wp_path in wp_files:
        with contextlib.suppress(OSError):
            result.append((wp_path.name, wp_path.read_text(encoding="utf-8")))
    return result


# ---------------------------------------------------------------------------
# Evidence reference helpers
# ---------------------------------------------------------------------------


def _make_evidence_counter() -> list[int]:
    return [0]


def _next_evidence_id(counter: list[int]) -> str:
    counter[0] += 1
    return f"e-{counter[0]:03d}"


def _next_finding_id(prefix: str, counter: dict[str, list[int]]) -> str:
    """Generate stable finding ids like h-001, g-001, n-001."""
    if prefix not in counter:
        counter[prefix] = [0]
    counter[prefix][0] += 1
    return f"{prefix}-{counter[prefix][0]:03d}"


def _next_proposal_id(counter: list[int]) -> str:
    counter[0] += 1
    return f"p-{counter[0]:03d}"


# ---------------------------------------------------------------------------
# Findings classification helpers (T009)
# ---------------------------------------------------------------------------


def _has_review_feedback(event: dict[str, Any]) -> bool:
    """Return True when a lane event carries documented review feedback."""
    if event.get("review_ref"):
        return True
    evidence = event.get("evidence")
    if isinstance(evidence, dict):
        review = evidence.get("review")
        if isinstance(review, dict):
            return bool(review.get("reference")) and review.get("verdict") == "changes_requested"
    return isinstance(evidence, str) and bool(evidence.strip())


_BACKWARD_LANE_MOVES: frozenset[tuple[str, str]] = frozenset({
    ("for_review", "planned"),
    ("for_review", "in_progress"),
    ("for_review", "claimed"),
    ("in_review", "planned"),
    ("in_review", "in_progress"),
    ("in_review", "claimed"),
    ("in_progress", "planned"),
    ("in_progress", "claimed"),
})


def _is_backward_lane_event(event: dict[str, Any]) -> bool:
    return (event.get("from_lane", ""), event.get("to_lane", "")) in _BACKWARD_LANE_MOVES


def _is_review_rejection_event(event: dict[str, Any]) -> bool:
    return (
        event.get("from_lane", "") == "in_review"
        and event.get("to_lane", "") in ("planned", "in_progress", "claimed")
        and _has_review_feedback(event)
    )


def _is_lane_friction_event(event: dict[str, Any]) -> bool:
    return _is_backward_lane_event(event) and not _is_review_rejection_event(event)


def _detect_rejection_cycles(events: list[dict[str, Any]]) -> dict[str, int]:
    """Return a mapping of wp_id -> rejection_cycle_count.

    A rejection cycle is a documented reviewer-feedback transition out of
    in_review. Earlier for_review rewinds and force moves are lane friction, not
    review rejections.
    """
    rejection_counts: dict[str, int] = {}
    for event in events:
        wp_id = event.get("wp_id", "")
        if not wp_id:
            continue
        if _is_review_rejection_event(event):
            rejection_counts[wp_id] = rejection_counts.get(wp_id, 0) + 1
    return rejection_counts


def _detect_lane_friction(events: list[dict[str, Any]]) -> dict[str, int]:
    """Return backward lane moves that are not documented reviewer rejections."""
    friction_counts: dict[str, int] = {}
    for event in events:
        wp_id = event.get("wp_id", "")
        if not wp_id:
            continue
        if _is_lane_friction_event(event):
            friction_counts[wp_id] = friction_counts.get(wp_id, 0) + 1
    return friction_counts


def _detect_done_wps(events: list[dict[str, Any]]) -> set[str]:
    """Return wp_ids that reached 'done' or 'approved' state."""
    done_wps: set[str] = set()
    for event in events:
        to_lane = event.get("to_lane", "")
        wp_id = event.get("wp_id", "")
        if wp_id and to_lane in ("done", "approved"):
            done_wps.add(wp_id)
    return done_wps


# ---------------------------------------------------------------------------
# T039 / FR-010 (F-04): --force transitions, arbiter overrides, implementation cycles
# ---------------------------------------------------------------------------

# Bootstrap actors emit force=True legitimately (e.g., finalize-tasks creating
# the initial planned→planned synthetic event).  They are not "force overrides"
# in the retrospective sense and must be excluded.
_BOOTSTRAP_ACTORS: frozenset[str] = frozenset({
    "finalize-tasks",
    "bootstrap",
    "migrate",
})

# Arbiter override markers in the `note` / `reason` fields.  Case-insensitive
# substring match keeps the heuristic simple while staying generous toward
# operator phrasing.
_ARBITER_MARKERS: tuple[str, ...] = (
    "arbiter",
    "arbiter-override",
    "arbiter override",
    "override arbiter",
)


def _is_force_override_event(event: dict[str, Any]) -> bool:
    """Return True if this event is a meaningful operator-driven --force override.

    Excludes finalize-tasks / bootstrap synthetic events whose force=True is a
    structural artifact, not an override.  Also excludes no-op transitions
    (from_lane == to_lane) which carry no signal.
    """
    if not event.get("force"):
        return False
    actor = str(event.get("actor", "")).lower()
    if actor in _BOOTSTRAP_ACTORS:
        return False
    return event.get("from_lane") != event.get("to_lane")


def _detect_force_overrides(events: list[dict[str, Any]]) -> dict[str, int]:
    """Count operator-driven --force transitions per WP."""
    counts: dict[str, int] = {}
    for event in events:
        wp_id = event.get("wp_id", "")
        if not wp_id:
            continue
        if _is_force_override_event(event):
            counts[wp_id] = counts.get(wp_id, 0) + 1
    return counts


def _event_wp_id(event: dict[str, Any]) -> str:
    """Return WP id from status event top-level fields or lifecycle payload."""
    wp_id = event.get("wp_id")
    if isinstance(wp_id, str) and wp_id:
        return wp_id
    payload = event.get("payload")
    if isinstance(payload, dict):
        payload_wp_id = payload.get("wp_id")
        if isinstance(payload_wp_id, str):
            return payload_wp_id
    return ""


def _is_reviewer_self_approval_event(event: dict[str, Any]) -> bool:
    from specify_cli.status import REVIEWER_SELF_APPROVAL

    return bool(event.get("event_type") == REVIEWER_SELF_APPROVAL)


def _detect_reviewer_self_approvals(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        if not _is_reviewer_self_approval_event(event):
            continue
        wp_id = _event_wp_id(event)
        if wp_id:
            counts[wp_id] = counts.get(wp_id, 0) + 1
    return counts


def _event_note(event: dict[str, Any]) -> str:
    """Return the human-readable note/reason text from an event, lower-cased."""
    parts: list[str] = []
    reason = event.get("reason")
    if isinstance(reason, str) and reason.strip():
        parts.append(reason)
    evidence = event.get("evidence")
    if isinstance(evidence, dict):
        for key in ("note", "reason"):
            value = evidence.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value)
    return " ".join(parts).lower()


def _is_arbiter_event(event: dict[str, Any]) -> bool:
    """Return True if event note/reason contains an arbiter override marker."""
    note = _event_note(event)
    if not note:
        return False
    return any(marker in note for marker in _ARBITER_MARKERS)


def _detect_arbiter_overrides(events: list[dict[str, Any]]) -> dict[str, int]:
    """Count arbiter-override events per WP."""
    counts: dict[str, int] = {}
    for event in events:
        wp_id = event.get("wp_id", "")
        if not wp_id:
            continue
        if _is_arbiter_event(event):
            counts[wp_id] = counts.get(wp_id, 0) + 1
    return counts


def _detect_implementation_cycles(events: list[dict[str, Any]]) -> dict[str, int]:
    """Count distinct planned→in_progress (or claimed→in_progress) cycles per WP.

    A WP that needs >1 implementation cycle indicates rework that didn't
    surface as a documented review rejection.  Bootstrap and synthetic
    transitions are excluded.
    """
    counts: dict[str, int] = {}
    for event in events:
        wp_id = event.get("wp_id", "")
        if not wp_id:
            continue
        actor = str(event.get("actor", "")).lower()
        if actor in _BOOTSTRAP_ACTORS:
            continue
        from_lane = event.get("from_lane", "")
        to_lane = event.get("to_lane", "")
        if from_lane in ("planned", "claimed") and to_lane == "in_progress":
            counts[wp_id] = counts.get(wp_id, 0) + 1
    # Only WPs with MORE THAN ONE cycle are interesting (the first cycle is normal).
    return {wp: n for wp, n in counts.items() if n > 1}


def _collect_fr_references(wp_files: list[tuple[str, str]]) -> dict[str, set[str]]:
    """Return mapping of FR-id -> set of WP filenames that reference it."""
    fr_to_wps: dict[str, set[str]] = {}
    for filename, content in wp_files:
        for fr_id in _FR_REF_RE.findall(content):
            if fr_id not in fr_to_wps:
                fr_to_wps[fr_id] = set()
            fr_to_wps[fr_id].add(filename)
    return fr_to_wps


def _find_unmapped_frs(spec_text: str, fr_to_wps: dict[str, set[str]]) -> list[str]:
    """Find FR ids mentioned in spec.md but not referenced in any WP task file."""
    spec_frs = set(_FR_REF_RE.findall(spec_text))
    return sorted(fr for fr in spec_frs if fr not in fr_to_wps)


def _classify_risk(suggested_action: str) -> tuple[str, bool]:
    """Return (risk_class, auto_applicable) for a proposal suggested_action.

    risk_class is "low" if the suggested_action starts with a LOW_RISK_PROPOSAL_KINDS
    marker (e.g. "flag_not_helpful: <term>"); otherwise "structural".
    auto_applicable is always False at generation time — the runtime/CLI sets it
    based on policy.permissions.apply_low_risk_changes at apply time.
    """
    action_prefix = suggested_action.split(":")[0].strip().lower()
    if action_prefix in LOW_RISK_PROPOSAL_KINDS:
        return "low", False
    return "structural", False


def _event_id_range_for(
    events: list[dict[str, Any]],
    wp_id: str,
    predicate: Any,
) -> str:
    """Return ``first..last`` (or single id) for events matching ``predicate`` on a WP."""
    ids = [
        str(ev.get("event_id", ""))
        for ev in events
        if _event_wp_id(ev) == wp_id and predicate(ev)
    ]
    if len(ids) > 1:
        return f"{ids[0]}..{ids[-1]}"
    return ids[0] if ids else ""


def _build_event_mining_findings(
    *,
    events: list[dict[str, Any]],
    events_rel: str,
    finding_id_counters: dict[str, list[int]],
    ev_reg: _EvidenceRegistry,
) -> tuple[list[GenFinding], list[GenFinding]]:
    """Build T039 / FR-010 (F-04) findings — force, arbiter, implementation cycles.

    Returns ``(not_helpful_additions, gaps_additions)``.
    """
    not_helpful: list[GenFinding] = []
    gaps: list[GenFinding] = []

    # Force overrides → not_helpful
    for wp_id, count in sorted(_detect_force_overrides(events).items()):
        range_str = _event_id_range_for(events, wp_id, _is_force_override_event)
        ev_id = ev_reg.add_event_range(events_rel, range_str or "force_override", f"force_override_{wp_id}")
        not_helpful.append(
            GenFinding(
                id=_next_finding_id("n", finding_id_counters),
                category="process",
                summary=f"{wp_id} required {count} --force override(s) during workflow",
                details=(
                    f"WP {wp_id} required {count} operator-driven --force lane transition(s). "
                    "Force overrides typically indicate the runtime guard failed or "
                    "the operator routed around it; investigate the underlying cause."
                ),
                evidence_refs=[ev_id],
            )
        )

    # Self-review fallback → not_helpful
    for wp_id, count in sorted(_detect_reviewer_self_approvals(events).items()):
        range_str = _event_id_range_for(events, wp_id, _is_reviewer_self_approval_event)
        ev_id = ev_reg.add_event_range(events_rel, range_str or "reviewer_self_approval", f"reviewer_self_approval_{wp_id}")
        matching_payloads = [
            ev.get("payload", {})
            for ev in events
            if _event_wp_id(ev) == wp_id and _is_reviewer_self_approval_event(ev)
        ]
        first_payload = matching_payloads[0] if matching_payloads and isinstance(matching_payloads[0], dict) else {}
        intended = str(first_payload.get("intended_reviewer") or "unknown")
        actor = str(first_payload.get("implementing_actor") or "unknown")
        reason = str(first_payload.get("failure_reason") or "reviewer_failed")
        not_helpful.append(
            GenFinding(
                id=_next_finding_id("n", finding_id_counters),
                category="process",
                summary=f"{wp_id} used self-review fallback instead of independent review",
                details=(
                    f"WP {wp_id} recorded {count} ReviewerSelfApproval event(s): "
                    f"{actor} self-reviewed after intended reviewer {intended} failed "
                    f"({reason}). Treat this as a review-independence gap."
                ),
                evidence_refs=[ev_id],
            )
        )

    # Arbiter overrides → gaps
    for wp_id, count in sorted(_detect_arbiter_overrides(events).items()):
        range_str = _event_id_range_for(events, wp_id, _is_arbiter_event)
        ev_id = ev_reg.add_event_range(events_rel, range_str or "arbiter", f"arbiter_{wp_id}")
        gaps.append(
            GenFinding(
                id=_next_finding_id("g", finding_id_counters),
                category="process",
                summary=f"Arbiter override needed for {wp_id} ({count}x)",
                details=(
                    f"WP {wp_id} required {count} arbiter override(s). Arbiter overrides "
                    "are an escape hatch; recurring use suggests the normal review path is "
                    "blocked and the underlying policy/guard may need adjustment."
                ),
                evidence_refs=[ev_id],
            )
        )

    # Multi-cycle implementations → not_helpful
    for wp_id, count in sorted(_detect_implementation_cycles(events).items()):
        ev_id = ev_reg.add_event_range(events_rel, "implementation_cycles", f"impl_cycles_{wp_id}")
        not_helpful.append(
            GenFinding(
                id=_next_finding_id("n", finding_id_counters),
                category="implementation",
                summary=f"{wp_id} needed {count} implementation cycles",
                details=(
                    f"WP {wp_id} entered in_progress {count} times. Multiple implementation "
                    "cycles suggest rework not captured as a documented review rejection; "
                    "the WP scope or contract may need refinement."
                ),
                evidence_refs=[ev_id],
            )
        )

    return not_helpful, gaps


def _build_lane_friction_findings(
    *,
    events: list[dict[str, Any]],
    lane_friction_counts: dict[str, int],
    events_rel: str,
    finding_id_counters: dict[str, list[int]],
    ev_reg: _EvidenceRegistry,
) -> list[GenFinding]:
    findings: list[GenFinding] = []
    for wp_id in sorted(lane_friction_counts):
        count = lane_friction_counts[wp_id]
        friction_event_ids = [
            str(ev.get("event_id", ""))
            for ev in events
            if ev.get("wp_id") == wp_id
            and _is_lane_friction_event(ev)
        ]
        if len(friction_event_ids) > 1:
            range_str = f"{friction_event_ids[0]}..{friction_event_ids[-1]}"
        elif friction_event_ids:
            range_str = friction_event_ids[0]
        else:
            range_str = ""
        ev_id = ev_reg.add_event_range(events_rel, range_str or "lane_friction", f"lane_friction_{wp_id}")
        findings.append(
            GenFinding(
                id=_next_finding_id("n", finding_id_counters),
                category="process",
                summary=f"{wp_id} had {count} lane bounce(s) before approval",
                details=(
                    f"WP {wp_id} moved backward across workflow lanes {count} time(s) "
                    "outside the documented reviewer-feedback flow."
                ),
                evidence_refs=[ev_id],
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Evidence registry — mutable accumulator passed through generation pipeline
# ---------------------------------------------------------------------------


class _EvidenceRegistry:
    """Mutable accumulator for evidence_refs.  Keeps generate_retrospective complexity low."""

    def __init__(self) -> None:
        self._counter: list[int] = [0]
        self._map: dict[str, str] = {}
        self.refs: list[GenEvidenceRef] = []

    def add_file(self, rel_path: str) -> str:
        """Register a file as an evidence_ref; return its id (idempotent)."""
        if rel_path not in self._map:
            eid = _next_evidence_id(self._counter)
            self._map[rel_path] = eid
            self.refs.append(GenEvidenceRef(id=eid, kind="file", path=rel_path))
        return self._map[rel_path]

    def add_event_range(self, rel_path: str, range_str: str, range_key: str) -> str:
        """Register an event range as an evidence_ref; return its id (idempotent)."""
        key = f"{rel_path}:{range_key}"
        if key not in self._map:
            eid = _next_evidence_id(self._counter)
            self._map[key] = eid
            self.refs.append(GenEvidenceRef(id=eid, kind="event_range", path=rel_path, range=range_str))
        return self._map[key]


def _resolve_mission_number(raw: object) -> int | None:
    """Coerce raw meta.json mission_number to int or None."""
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return None


# ---------------------------------------------------------------------------
# Findings classification (T009) — extracted to keep generate_retrospective simple
# ---------------------------------------------------------------------------


def _build_findings(
    *,
    events: list[dict[str, Any]],
    spec_text: str,
    plan_text: str,
    research_text: str | None,
    data_model_text: str | None,
    wp_files: list[tuple[str, str]],
    wp_evidence_ids: dict[str, str],
    events_rel: str,
    spec_rel: str,
    generate_proposals: bool,
    ev_reg: _EvidenceRegistry,
) -> tuple[list[GenFinding], list[GenFinding], list[GenFinding], list[GenProposal]]:
    """Classify events and artifacts into (helped, not_helpful, gaps, proposals).

    Extracted from generate_retrospective to keep its cyclomatic complexity within limits.
    Evidence-ref registration is done via the ev_reg accumulator.
    """
    finding_id_counters: dict[str, list[int]] = {}
    helped: list[GenFinding] = []
    not_helpful: list[GenFinding] = []
    gaps: list[GenFinding] = []
    proposals: list[GenProposal] = []

    rejection_counts = _detect_rejection_cycles(events)
    lane_friction_counts = _detect_lane_friction(events)
    done_wps = _detect_done_wps(events)

    # --- Helped: WPs completed without rejection cycles (only notable by contrast)
    clean_wps = [
        wp
        for wp in sorted(done_wps)
        if rejection_counts.get(wp, 0) == 0 and lane_friction_counts.get(wp, 0) == 0
    ]
    if rejection_counts or lane_friction_counts:
        for wp_id in clean_wps:
            wp_file_name = f"{wp_id}.md"
            if wp_file_name in wp_evidence_ids:
                ev_refs = [wp_evidence_ids[wp_file_name]]
            elif events:
                ev_refs = [ev_reg.add_file(events_rel)]
            else:
                ev_refs = []

            if ev_refs:
                helped.append(
                    GenFinding(
                        id=_next_finding_id("h", finding_id_counters),
                        category="implementation",
                        summary=f"{wp_id} completed without rejection cycles",
                        details=None,
                        evidence_refs=ev_refs,
                    )
                )

    # --- Not-helpful: WPs with ≥1 rejection cycle
    for wp_id in sorted(rejection_counts.keys()):
        count = rejection_counts[wp_id]
        rejection_event_ids = [
            str(ev.get("event_id", ""))
            for ev in events
            if ev.get("wp_id") == wp_id
            and ev.get("from_lane") in ("for_review", "in_review")
            and ev.get("to_lane") in ("planned", "in_progress", "claimed")
        ]
        range_str = (
            f"{rejection_event_ids[0]}..{rejection_event_ids[-1]}"
            if len(rejection_event_ids) > 1
            else (rejection_event_ids[0] if rejection_event_ids else "")
        )
        ev_id = ev_reg.add_event_range(events_rel, range_str or "rejection", f"rejection_{wp_id}")
        not_helpful.append(
            GenFinding(
                id=_next_finding_id("n", finding_id_counters),
                category="review_loop",
                summary=f"{wp_id} required {count} rejection cycle(s) before approval",
                details=f"WP {wp_id} was sent back from review to planning {count} time(s).",
                evidence_refs=[ev_id],
            )
        )

    not_helpful.extend(
        _build_lane_friction_findings(
            events=events,
            lane_friction_counts=lane_friction_counts,
            events_rel=events_rel,
            finding_id_counters=finding_id_counters,
            ev_reg=ev_reg,
        )
    )

    # --- T039 / FR-010 (F-04): force-override, arbiter, and impl-cycle findings
    _new_not_helpful, _new_gaps = _build_event_mining_findings(
        events=events,
        events_rel=events_rel,
        finding_id_counters=finding_id_counters,
        ev_reg=ev_reg,
    )
    not_helpful.extend(_new_not_helpful)
    gaps.extend(_new_gaps)

    # --- Gaps: open [NEEDS CLARIFICATION:] markers in spec.md
    if spec_text:
        for match in _NEEDS_CLARIFICATION_RE.finditer(spec_text):
            line_num = spec_text[: match.start()].count("\n") + 1
            spec_ev_id = ev_reg.add_file(spec_rel)
            gaps.append(
                GenFinding(
                    id=_next_finding_id("g", finding_id_counters),
                    category="spec_quality",
                    summary=f"Unresolved clarification marker in spec.md (line {line_num})",
                    details=(
                        f"Found '[NEEDS CLARIFICATION:' marker at line {line_num} of spec.md. "
                        "This indicates a specification gap that was not resolved before implementation."
                    ),
                    evidence_refs=[spec_ev_id],
                )
            )

    # --- Gaps: FRs in spec.md with no WP coverage
    if spec_text and wp_files:
        fr_to_wps_map = _collect_fr_references(wp_files)
        for fr_id in _find_unmapped_frs(spec_text, fr_to_wps_map):
            spec_ev_id = ev_reg.add_file(spec_rel)
            gaps.append(
                GenFinding(
                    id=_next_finding_id("g", finding_id_counters),
                    category="spec_quality",
                    summary=f"{fr_id} defined in spec.md has no WP coverage",
                    details=(
                        f"Requirement {fr_id} appears in spec.md but is not referenced by "
                        "any work package task file. It may be unimplemented."
                    ),
                    evidence_refs=[ev_reg.add_file(spec_rel)],
                )
            )

    # --- Gaps: missing optional documentation artifacts (only when spec.md is present)
    if spec_text:
        if research_text is None:
            gaps.append(
                GenFinding(
                    id=_next_finding_id("g", finding_id_counters),
                    category="doc",
                    summary="research.md absent",
                    details=(
                        "spec.md is present but research.md is missing. "
                        "Research artifacts help future maintainers understand design decisions."
                    ),
                    evidence_refs=[ev_reg.add_file(spec_rel)],
                )
            )
        if data_model_text is None and (spec_text or plan_text):
            gaps.append(
                GenFinding(
                    id=_next_finding_id("g", finding_id_counters),
                    category="doc",
                    summary="data-model.md absent",
                    details=(
                        "spec.md is present but data-model.md is missing. "
                        "A data model document clarifies domain entity relationships."
                    ),
                    evidence_refs=[ev_reg.add_file(spec_rel)],
                )
            )

    # Stable sort: byte-deterministic output
    helped.sort(key=lambda f: (f.category, f.summary))
    not_helpful.sort(key=lambda f: (f.category, f.summary))
    gaps.sort(key=lambda f: (f.category, f.summary))
    if generate_proposals:
        proposals.sort(key=lambda p: (p.category, p.summary))

    return helped, not_helpful, gaps, proposals


# ---------------------------------------------------------------------------
# Main generator function (T008)
# ---------------------------------------------------------------------------


def generate_retrospective(
    mission_handle: str,
    policy: RetrospectivePolicy,
    repo_root: Path,
    *,
    provenance_kind: ProvenanceKind = "runtime_post_completion",
    invoked_at: str | None = None,
    actor: GenActor | None = None,
    policy_source: dict[str, str] | None = None,
) -> GenRetrospectiveRecord:
    """Generate a deterministic retrospective record for the given mission.

    Reads mission artifacts in the order specified by the WP02 prompt:
    meta.json → spec.md → plan.md → research.md → data-model.md → contracts/
    → quickstart.md → tasks.md → tasks/WP*.md → status.events.jsonl
    → mission-review-report.md → charter context.

    Missing optional artifacts become 'gaps' entries, NOT exceptions.

    Args:
        mission_handle: The mission slug, mission_id, or directory name under kitty-specs/.
        policy:         Resolved RetrospectivePolicy (caller already resolved it).
        repo_root:      Absolute path to the project root.
        provenance_kind: Kind of provenance to record (default: runtime_post_completion).
        invoked_at:     RFC 3339 timestamp; defaults to utcnow.
        actor:          Who invoked the generator; defaults to a runtime actor.
        policy_source:  source_map from resolve_policy(); if None, uses empty dict.

    Returns:
        A validated GenRetrospectiveRecord. validate_record() is called before return.

    Raises:
        FileNotFoundError: If the mission directory cannot be resolved.
        RecordValidationError: If the generator produces an invalid record (indicates a bug).
    """
    if invoked_at is None:
        invoked_at = datetime.datetime.now(datetime.UTC).isoformat()

    if actor is None:
        actor = GenActor(kind="runtime", id="spec-kitty-generator", display="Spec Kitty Generator")

    if policy_source is None:
        policy_source = {}

    # ------------------------------------------------------------------
    # Step 1: Resolve mission directory
    # ------------------------------------------------------------------
    feature_dir = _resolve_mission_dir(mission_handle, repo_root)
    if feature_dir is None:
        raise FileNotFoundError(
            f"Mission {mission_handle!r} not found under {repo_root / KITTY_SPECS_DIR}. "
            "Check the mission handle (slug, mission_id, or directory name)."
        )

    # ------------------------------------------------------------------
    # Step 2: Read artifacts in canonical order
    # ------------------------------------------------------------------
    meta = _load_meta(feature_dir)

    spec_text = _read_optional_text(feature_dir / "spec.md") or ""
    plan_text = _read_optional_text(feature_dir / "plan.md") or ""
    tasks_text = _read_optional_text(feature_dir / "tasks.md") or ""

    # Optional artifacts
    research_text = _read_optional_text(feature_dir / "research.md")
    data_model_text = _read_optional_text(feature_dir / "data-model.md")

    wp_files = _load_wp_files(feature_dir)
    events = _load_events(feature_dir)

    # ------------------------------------------------------------------
    # Step 3: Build evidence_refs via registry (stable, sorted order)
    # ------------------------------------------------------------------
    ev_reg = _EvidenceRegistry()
    spec_rel = f"kitty-specs/{feature_dir.name}/spec.md"
    plan_rel = f"kitty-specs/{feature_dir.name}/plan.md"
    tasks_rel = f"kitty-specs/{feature_dir.name}/tasks.md"
    events_rel = f"kitty-specs/{feature_dir.name}/status.events.jsonl"
    meta_rel = f"kitty-specs/{feature_dir.name}/meta.json"

    if meta:
        ev_reg.add_file(meta_rel)
    if spec_text:
        ev_reg.add_file(spec_rel)
    if plan_text:
        ev_reg.add_file(plan_rel)
    if tasks_text:
        ev_reg.add_file(tasks_rel)

    wp_evidence_ids: dict[str, str] = {}
    for wp_name, _ in wp_files:
        wp_rel = f"kitty-specs/{feature_dir.name}/tasks/{wp_name}"
        wp_evidence_ids[wp_name] = ev_reg.add_file(wp_rel)

    if events:
        ev_reg.add_file(events_rel)

    # ------------------------------------------------------------------
    # Step 4: Classify findings (T009)
    # generate_proposals from policy gates whether proposals are populated.
    # ------------------------------------------------------------------
    helped, not_helpful, gaps, proposals = _build_findings(
        events=events,
        spec_text=spec_text,
        plan_text=plan_text,
        research_text=research_text,
        data_model_text=data_model_text,
        wp_files=wp_files,
        wp_evidence_ids=wp_evidence_ids,
        events_rel=events_rel,
        spec_rel=spec_rel,
        generate_proposals=policy.generate_proposals,
        ev_reg=ev_reg,
    )

    # ------------------------------------------------------------------
    # Step 5: findings_status resolution (T010)
    # NOTE: "missing" and "failed" are event-payload-only states and
    # MUST NOT appear in a persisted RetrospectiveRecord.
    # ------------------------------------------------------------------
    findings_status: FindingsStatus = "has_findings" if any([helped, not_helpful, gaps, proposals]) else "ran_no_findings"

    # ------------------------------------------------------------------
    # Step 6: Resolve mission identity from meta.json
    # ------------------------------------------------------------------
    mission_id = str(meta.get("mission_id") or "")
    mission_slug = str(meta.get("mission_slug") or meta.get("slug") or feature_dir.name)
    friendly_name = str(meta.get("friendly_name") or meta.get("name") or mission_slug)
    mission_type = str(meta.get("mission_type") or "software-dev")
    target_branch = str(meta.get("target_branch") or "main")
    mission_number = _resolve_mission_number(meta.get("mission_number"))

    # ------------------------------------------------------------------
    # Step 7: Assemble the record
    # ------------------------------------------------------------------
    provenance = GenProvenance(
        kind=provenance_kind,
        command=None,
        invoked_at=invoked_at,
        policy_resolved_from=dict(policy_source),
    )

    record = GenRetrospectiveRecord(
        schema_version=1,
        mission_id=mission_id,
        mission_slug=mission_slug,
        mission_number=mission_number,
        friendly_name=friendly_name,
        mission_type=mission_type,
        target_branch=target_branch,
        created_at=invoked_at,
        created_by=actor,
        provenance=provenance,
        policy_source=dict(policy_source),
        findings_status=findings_status,
        helped=helped,
        not_helpful=not_helpful,
        gaps=gaps,
        proposals=proposals,
        evidence_refs=ev_reg.refs,
        generator_version=GENERATOR_VERSION,
        provenance_history=[],
    )

    # ------------------------------------------------------------------
    # Step 8: Validate before returning.
    # Validation failure is a generator bug — raise immediately.
    # ------------------------------------------------------------------
    validate_record(record)

    return record
