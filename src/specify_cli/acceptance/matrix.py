"""Acceptance matrix — derived evidence view for feature acceptance.

The acceptance matrix is NOT an authoritative state source. The canonical
state authority remains status.events.jsonl + meta.json. This module
provides a structured evidence artifact that the acceptance gate reads
to validate evidence completeness before emitting transitions through
the existing event pipeline.

Persisted at kitty-specs/{mission_slug}/acceptance-matrix.json.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.configured_command import ConfiguredCommandUnsupported, run_configured_command
from specify_cli.mission_metadata import mission_identity_fields, resolve_mission_identity

if TYPE_CHECKING:
    from specify_cli.acceptance.execution_context import GateExecutionContext

CRITERION_VERDICTS = frozenset({"pass", "fail", "pending"})

# The negative-invariant results that represent an *actual, established
# judgement* (data-model.md Result state machine). Membership in this set is the
# NI-2 preservation guard: a terminal result is never re-judged or overwritten
# (C3). ``deferred_to_consolidation`` is deliberately EXCLUDED — it is a
# scheduled-not-yet-judged state (NI-4), so freezing it here would make its
# post-consolidation verification (C6) impossible.
TERMINAL_INVARIANT_RESULTS = frozenset({"confirmed_absent", "still_present", "verification_error"})

# The fourth Result value (NI / data-model.md): a ``pending`` invariant whose
# subject cannot exist on the current surface defers here rather than reporting a
# false ``still_present`` (FR-003 / C4).
DEFERRED_TO_CONSOLIDATION = "deferred_to_consolidation"

NEGATIVE_INVARIANT_RESULTS = TERMINAL_INVARIANT_RESULTS | {"pending", DEFERRED_TO_CONSOLIDATION}

# Provenance origin vocabulary (data-model.md NI-1). ``recorded`` requires full
# provenance; ``legacy_unrecorded`` is the FR-014 sentinel for results captured
# before provenance existed and permits null provenance for THAT origin only.
# ``legacy_unrecorded`` is a ``provenance_origin`` value, NEVER a
# ``TopologySurface`` member (the surface enum's anti-phantom rule).
PROVENANCE_RECORDED = "recorded"
PROVENANCE_LEGACY_UNRECORDED = "legacy_unrecorded"
PROVENANCE_ORIGINS = frozenset({PROVENANCE_RECORDED, PROVENANCE_LEGACY_UNRECORDED})

# The fourth ``overall_verdict`` value (NI-5): deferral contributes neither a
# ``fail`` nor a silent ``pass`` — acceptance is not blocked, but the mission
# cannot reach ``done`` while any invariant is still deferred.
VERDICT_PASS_PENDING_CONSOLIDATION = "pass_pending_consolidation"  # noqa: S105  # verdict name, not a secret

# The phase name a deferred invariant is scheduled to be judged at (NI-4 / C4).
# Stored as the ``LifecyclePhase.POST_CONSOLIDATION`` member NAME (a plain string)
# so the matrix serialises without importing the phase enum into its storage.
POST_CONSOLIDATION_PHASE_NAME = "POST_CONSOLIDATION"


def _is_allowed_value(value: Any, allowed: frozenset[str]) -> bool:
    return isinstance(value, str) and value in allowed


def _split_known_fields(
    cls: type[Any],
    data: dict[str, Any],
    *,
    exclude: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    excluded = exclude or set()
    known = {f.name for f in fields(cls)} - {"extras"} - excluded
    kwargs = {key: value for key, value in data.items() if key in known}
    extras = {key: value for key, value in data.items() if key not in known and key not in excluded}
    return kwargs, extras


@dataclass
class AcceptanceCriterion:
    """A single acceptance criterion with evidence."""

    criterion_id: str
    description: str
    proof_type: str  # "automated_test" | "manual_qa" | "code_review" | "negative_invariant"
    evidence: str | None = None
    pass_fail: str = "pending"  # noqa: S105  # "pass" | "fail" | "pending"
    verified_by: str | None = None
    verified_at: str | None = None
    notes: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcceptanceCriterion:
        kwargs, extras = _split_known_fields(cls, data)
        return cls(**kwargs, extras=extras)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extras = data.pop("extras", {}) or {}
        data.update(extras)
        return data


@dataclass
class NegativeInvariant:
    """A negative invariant — something that must NOT exist."""

    invariant_id: str
    description: str
    verification_method: str  # "grep_absence" | "route_check" | "custom_command"
    verification_command: str | None = None
    result: str = "pending"  # see NEGATIVE_INVARIANT_RESULTS (incl. deferred_to_consolidation)
    evidence: str | None = None
    # Optional path-scope for ``grep_absence``: whitespace-separated repo-relative
    # search root(s). When set, the grep runs only under these paths instead of
    # the whole repo, so a pattern that a mission's OWN spec/plan/WP prose
    # mentions does not false-positive as "still_present" (#1834). Default
    # (``None``) preserves the whole-repo search (unchanged behaviour).
    scope: str | None = None
    # --- Provenance (data-model.md NI-1 / contract C1-C2). A judgement states
    # the surface and ref it was established against so it is attributable and
    # never silently re-judged from a surface that cannot hold it. ---
    # The git ref the outcome was established against (null until judged).
    verified_ref: str | None = None
    # The ``TopologySurface`` value (e.g. ``"primary"`` / ``"coord"`` /
    # ``"consolidated"``) that established the outcome. Stored as the plain enum
    # VALUE, never the sentinel ``legacy_unrecorded`` (which is a
    # ``provenance_origin``, not a surface — the anti-phantom rule).
    verified_surface_kind: str | None = None
    # Why judgement was postponed, when ``result == deferred_to_consolidation``.
    deferred_reason: str | None = None
    # The ``LifecyclePhase`` NAME the deferral will be judged at (NI-4).
    deferred_to_phase: str | None = None
    # ``recorded`` requires full provenance; ``legacy_unrecorded`` (the FR-014
    # sentinel) permits null provenance for pre-schema results. The default is
    # ``legacy_unrecorded`` so an existing on-disk matrix — which predates these
    # fields — round-trips through ``validate_matrix_evidence`` unchanged (its
    # terminal results carry no provenance yet, and the FR-014 backfill has not
    # run). The gate stamps ``recorded`` explicitly when it judges an invariant.
    provenance_origin: str = PROVENANCE_LEGACY_UNRECORDED
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NegativeInvariant:
        kwargs, extras = _split_known_fields(cls, data)
        return cls(**kwargs, extras=extras)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extras = data.pop("extras", {}) or {}
        # Omit unset optional keys so existing matrices are not rewritten with a
        # ``null`` key on their next serialization (byte-stability across the
        # ~160 tracked matrices). C2 round-trip is preserved: an omitted key
        # restores to its ``None`` default via ``from_dict``.
        for key in (
            "scope",
            "verified_ref",
            "verified_surface_kind",
            "deferred_reason",
            "deferred_to_phase",
        ):
            if data.get(key) is None:
                data.pop(key, None)
        # ``legacy_unrecorded`` is the default; omit it so pre-schema matrices
        # stay byte-stable. A ``recorded`` origin is always emitted.
        if data.get("provenance_origin") == PROVENANCE_LEGACY_UNRECORDED:
            data.pop("provenance_origin", None)
        data.update(extras)
        return data


@dataclass
class AcceptanceMatrix:
    """Complete acceptance matrix for a feature.

    This is a derived evidence view. It does NOT participate in state
    transitions. The acceptance gate reads it to validate evidence
    completeness, then emits transitions through the event pipeline.
    """

    mission_slug: str
    criteria: list[AcceptanceCriterion] = field(default_factory=list)
    negative_invariants: list[NegativeInvariant] = field(default_factory=list)
    mission_number: str | None = None
    mission_type: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_verdict(self) -> str:
        """Compute verdict from individual results."""
        criterion_results = [c.pass_fail for c in self.criteria]
        invariant_results = [ni.result for ni in self.negative_invariants]
        if not criterion_results and not invariant_results:
            return "pending"
        if any(not _is_allowed_value(v, CRITERION_VERDICTS) for v in criterion_results):
            return "fail"
        if any(not _is_allowed_value(v, NEGATIVE_INVARIANT_RESULTS) for v in invariant_results):
            return "fail"
        if any(v == "fail" for v in criterion_results):
            return "fail"
        if any(v in {"still_present", "verification_error"} for v in invariant_results):
            return "fail"
        if any(v == "pending" for v in criterion_results + invariant_results):
            return "pending"
        # NI-5: a deferred invariant is neither a failure nor a silent pass. It
        # yields the fourth verdict — acceptance is NOT blocked (C5), but the
        # verdict is distinguishable from a clean ``pass`` so the mission cannot
        # reach ``done`` while a deferral is outstanding. Checked AFTER ``pending``
        # so an unverified criterion still dominates.
        if any(v == DEFERRED_TO_CONSOLIDATION for v in invariant_results):
            return VERDICT_PASS_PENDING_CONSOLIDATION
        return "pass"

    def to_dict(self) -> dict[str, Any]:
        data = {
            **mission_identity_fields(
                self.mission_slug,
                self.mission_number,
                self.mission_type,
            ),
            "overall_verdict": self.overall_verdict,
            "criteria": [c.to_dict() for c in self.criteria],
            "negative_invariants": [ni.to_dict() for ni in self.negative_invariants],
        }
        data.update(self.extras)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcceptanceMatrix:
        kwargs, extras = _split_known_fields(cls, data, exclude={"overall_verdict"})
        identity = mission_identity_fields(
            data["mission_slug"],
            data.get("mission_number"),
            data.get("mission_type"),
        )
        return cls(
            mission_slug=identity["mission_slug"],
            criteria=[
                AcceptanceCriterion.from_dict(c) for c in data.get("criteria", [])
            ],
            negative_invariants=[
                NegativeInvariant.from_dict(ni) for ni in data.get("negative_invariants", [])
            ],
            mission_number=kwargs.get("mission_number", identity["mission_number"]),
            mission_type=kwargs.get("mission_type", identity["mission_type"]),
            extras=extras,
        )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

MATRIX_FILENAME = "acceptance-matrix.json"


def write_acceptance_matrix(feature_dir: Path, matrix: AcceptanceMatrix) -> Path:
    """Write acceptance-matrix.json to the feature directory."""
    if (feature_dir / "meta.json").exists():
        identity = resolve_mission_identity(feature_dir)
        matrix.mission_slug = identity.mission_slug
        matrix.mission_number = (
            str(identity.mission_number)
            if identity.mission_number is not None
            else None
        )
        matrix.mission_type = identity.mission_type
    path = feature_dir / MATRIX_FILENAME
    path.write_text(
        json.dumps(matrix.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def read_acceptance_matrix(feature_dir: Path) -> AcceptanceMatrix | None:
    """Read acceptance-matrix.json. Returns None if absent."""
    path = feature_dir / MATRIX_FILENAME
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return AcceptanceMatrix.from_dict(data)


# Marker dropped into scaffolded criteria so operators (and reviewers) can
# tell a placeholder row apart from a real, authored acceptance criterion.
SCAFFOLD_TODO_MARKER = "TODO: replace with a real acceptance criterion"


def scaffold_acceptance_matrix(
    feature_dir: Path,
    mission_slug: str,
    requirement_ids: list[str] | None = None,
    *,
    home_dir: Path | None = None,
) -> Path | None:
    """Author a minimal, schema-valid ``acceptance-matrix.json`` for a feature.

    Lane-based features require ``acceptance-matrix.json`` to exist before the
    acceptance gate will run (see ``specify_cli.acceptance``). This helper
    scaffolds a minimal but schema-valid matrix at task-finalization time so the
    artifact is never silently missing.

    The scaffold is **idempotent**: an existing ``acceptance-matrix.json`` is
    never overwritten, so operator-curated criteria survive re-runs.

    **FR-010 / C8 / AH-3 — single authoritative home.** The idempotency check
    consults the matrix's DECLARED HOME (``home_dir``, when supplied by the
    caller from the same surface resolver the gate reads through), not merely the
    ``feature_dir`` staging location. Under coordination topology the authoritative
    matrix lives on the coord surface; without this check a re-finalize would find
    no matrix at the primary ``feature_dir`` and scaffold a *second*, divergent
    primary copy alongside the real coord one (#2882). Consulting the declared home
    means exactly one copy is ever authored, so the provenance fields cannot
    diverge across copies. When ``home_dir`` is omitted the check falls back to
    ``feature_dir`` (the flat/create-window case, where primary IS the home).

    When ``requirement_ids`` are supplied (e.g. functional requirement ids from
    ``spec.md``), one ``pending`` criterion is derived per requirement. When no
    requirement ids are available, a single placeholder criterion carrying
    :data:`SCAFFOLD_TODO_MARKER` is written so the file is valid yet obviously
    awaiting real content.

    Args:
        feature_dir: The ``kitty-specs/<slug>/`` directory for the mission (the
            staging location the finalize flow collects and routes from).
        mission_slug: Feature slug (e.g. ``010-lane-only-runtime``).
        requirement_ids: Optional functional requirement ids to seed criteria.
        home_dir: The matrix's declared home directory, when the caller has
            resolved it. Used for the single-home idempotency check.

    Returns:
        Path to the scaffolded (or pre-existing) ``acceptance-matrix.json``.
    """
    home = home_dir if home_dir is not None else feature_dir
    home_path = home / MATRIX_FILENAME
    if home_path.exists():
        # C8 / AH-3: the single declared home already holds the matrix — never
        # author a second (primary-scaffold) copy that could diverge on the new
        # provenance fields.
        return home_path
    path = feature_dir / MATRIX_FILENAME
    if path.exists():
        # Respect operator-curated content; idempotent re-runs must not clobber.
        return path

    criteria: list[AcceptanceCriterion] = []
    for req_id in requirement_ids or []:
        criteria.append(
            AcceptanceCriterion(
                criterion_id=req_id,
                description=f"Verify {req_id} is satisfied",
                proof_type="automated_test",
                pass_fail="pending",  # noqa: S106
                notes=SCAFFOLD_TODO_MARKER,
            )
        )

    if not criteria:
        # Empty-but-valid scaffold with an explicit TODO marker. A single
        # placeholder keeps the JSON schema-valid while signalling clearly that
        # no real criteria have been authored yet.
        criteria.append(
            AcceptanceCriterion(
                criterion_id="AC-001",
                description=SCAFFOLD_TODO_MARKER,
                proof_type="automated_test",
                pass_fail="pending",  # noqa: S106
                notes=SCAFFOLD_TODO_MARKER,
            )
        )

    matrix = AcceptanceMatrix(mission_slug=mission_slug, criteria=criteria)
    return write_acceptance_matrix(feature_dir, matrix)


# ---------------------------------------------------------------------------
# Evidence validation
# ---------------------------------------------------------------------------


def validate_manual_evidence(criterion: AcceptanceCriterion) -> list[str]:
    """Validate that manual QA criteria have required evidence fields.

    Returns list of error messages. Empty means valid.
    """
    errors: list[str] = []
    if criterion.proof_type != "manual_qa":
        return errors
    if not criterion.evidence:
        errors.append(
            f"{criterion.criterion_id}: manual QA requires evidence (URL/screenshot)"
        )
    if not criterion.verified_at:
        errors.append(
            f"{criterion.criterion_id}: manual QA requires verified_at timestamp"
        )
    if not criterion.verified_by:
        errors.append(
            f"{criterion.criterion_id}: manual QA requires verified_by identity"
        )
    return errors


def validate_matrix_evidence(matrix: AcceptanceMatrix) -> list[str]:
    """Validate all evidence in the matrix. Returns list of errors."""
    errors: list[str] = []
    for criterion in matrix.criteria:
        if not _is_allowed_value(criterion.pass_fail, CRITERION_VERDICTS):
            allowed = ", ".join(sorted(CRITERION_VERDICTS))
            errors.append(f"{criterion.criterion_id}: pass_fail must be one of {allowed}; got {criterion.pass_fail!r}")
        errors.extend(validate_manual_evidence(criterion))
    for invariant in matrix.negative_invariants:
        errors.extend(_validate_invariant_provenance(invariant))
    return errors


def _validate_invariant_provenance(invariant: NegativeInvariant) -> list[str]:
    """NI-1: enforce provenance on a recorded judgement, with the legacy escape.

    A ``recorded`` TERMINAL result must carry both ``verified_ref`` and
    ``verified_surface_kind``; a provenance-less ``recorded`` terminal result is a
    validation error (C1). A ``legacy_unrecorded`` result may carry null
    provenance — that origin, and only that origin, permits the absence (the
    FR-014 sentinel for pre-schema results). ``pending`` and
    ``deferred_to_consolidation`` are scheduled-not-yet-judged states and are
    exempt: they have no surface to attribute a judgement to.
    """
    errors: list[str] = []
    result = invariant.result
    if not _is_allowed_value(result, NEGATIVE_INVARIANT_RESULTS):
        allowed = ", ".join(sorted(NEGATIVE_INVARIANT_RESULTS))
        errors.append(f"{invariant.invariant_id}: result must be one of {allowed}; got {result!r}")
        return errors
    if not _is_allowed_value(invariant.provenance_origin, PROVENANCE_ORIGINS):
        allowed = ", ".join(sorted(PROVENANCE_ORIGINS))
        errors.append(
            f"{invariant.invariant_id}: provenance_origin must be one of {allowed}; "
            f"got {invariant.provenance_origin!r}"
        )
        return errors
    if (
        result in TERMINAL_INVARIANT_RESULTS
        and invariant.provenance_origin == PROVENANCE_RECORDED
        and (invariant.verified_ref is None or invariant.verified_surface_kind is None)
    ):
        errors.append(
            f"{invariant.invariant_id}: a recorded {result!r} result requires both "
            "verified_ref and verified_surface_kind (NI-1)"
        )
    return errors


# ---------------------------------------------------------------------------
# Negative invariant enforcement
# ---------------------------------------------------------------------------


def enforce_negative_invariants(
    repo_root: Path,
    invariants: list[NegativeInvariant],
    *,
    context: GateExecutionContext | None = None,
) -> list[NegativeInvariant]:
    """Run all negative invariant checks. Returns updated invariants.

    Verification methods:
    - grep_absence: Run grep for pattern in repo; exit code 1 means absent.
    - custom_command: Run a command, check exit code (0 = absent/pass).

    **NI-2 / C3 (preservation).** A negative invariant that already carries a
    TERMINAL ``result`` (``confirmed_absent`` / ``still_present`` /
    ``verification_error``) is NOT re-verified: it is preserved verbatim, provenance
    included. The guard keys on TERMINAL-SET MEMBERSHIP, not ``result != "pending"``
    — so the fourth value ``deferred_to_consolidation`` is *not* frozen (it must
    remain re-judgeable at ``POST_CONSOLIDATION`` per NI-4), while a recorded
    judgement stays immutable. This matters because the gate runs both during per-WP
    review (from the integrated lane worktree, where mission-added files exist) and
    again at ``accept`` (from the pre-merge primary root, where they do not — they
    land only via ``spec-kitty merge``); re-running a recorded invariant against the
    pre-merge tree would clobber an honest ``confirmed_absent`` with a false
    ``still_present`` (#1834).

    **NI-3 / C4 / C9 (deferral).** When a ``context`` is supplied and a ``pending``
    invariant's subject cannot exist on the current surface (a ``grep_absence``
    scoped to a source dir that is absent pre-consolidation), it transitions to
    ``deferred_to_consolidation`` with a ``deferred_reason`` and
    ``deferred_to_phase = POST_CONSOLIDATION`` — never to a false ``still_present``.
    An unscoped grep, or a scoped grep whose dir already exists (C9), is judged
    normally. A freshly judged terminal result is stamped ``recorded`` with the
    context's surface + ref (NI-1 provenance). Without a ``context`` the legacy
    behaviour is preserved (judge ``pending``, no provenance stamp, no deferral).
    """
    results: list[NegativeInvariant] = []
    for ni in invariants:
        if ni.result in TERMINAL_INVARIANT_RESULTS:
            results.append(ni)  # NI-2 / C3: a recorded judgement is never overwritten.
            continue
        if ni.result == DEFERRED_TO_CONSOLIDATION:
            # NI-4: not terminal, but judged by the post-consolidation op (C6),
            # not re-judged here pre-consolidation. Left intact.
            results.append(ni)
            continue
        # ``pending`` — the scaffolded default, so this is the common path.
        if context is not None and _should_defer(repo_root, ni, context):
            results.append(_defer_invariant(ni, context))
            continue
        updated = _check_invariant(repo_root, ni)
        results.append(_stamp_provenance(updated, context))
    return results


def _should_defer(
    repo_root: Path, ni: NegativeInvariant, context: GateExecutionContext
) -> bool:
    """NI-3 / C9: does this ``pending`` invariant's subject exist on the surface?

    Only a ``grep_absence`` SCOPED to a source directory can defer: if any of its
    scoped roots is absent under ``repo_root`` (the tree the grep runs against),
    the subject cannot yet exist, so the invariant defers rather than reporting a
    false ``still_present`` (FR-003). A scoped root that already exists (C9) or an
    unscoped whole-repo grep is judgeable now. Deferral only applies before
    ``POST_CONSOLIDATION`` — at/after that phase the consolidated tree holds the
    subject and it is judged (C6).
    """
    if context.phase.name == POST_CONSOLIDATION_PHASE_NAME:
        return False
    if ni.verification_method != "grep_absence" or not ni.scope:
        return False
    return any(not (repo_root / root).exists() for root in ni.scope.split())


def _defer_invariant(
    ni: NegativeInvariant, context: GateExecutionContext
) -> NegativeInvariant:
    """Transition a ``pending`` invariant to ``deferred_to_consolidation`` (C4)."""
    surface = context.surface_kind.value
    return replace(
        ni,
        result=DEFERRED_TO_CONSOLIDATION,
        evidence=(
            f"Scoped subject {ni.scope!r} is absent on the {surface} surface "
            f"pre-consolidation; deferred to post-consolidation verification."
        ),
        deferred_reason=(
            f"Scoped path(s) {ni.scope!r} do not exist on the {surface} surface at "
            f"ref {context.ref!r}; judging here would report a false still_present "
            "(FR-003). Deferred to the post-consolidation verification op."
        ),
        deferred_to_phase=POST_CONSOLIDATION_PHASE_NAME,
    )


def _stamp_provenance(
    ni: NegativeInvariant, context: GateExecutionContext | None
) -> NegativeInvariant:
    """NI-1: stamp a freshly judged result with the surface + ref it was established against.

    A terminal result gets ``provenance_origin = recorded`` plus the context's
    surface and ref, so it satisfies NI-1 and is attributable. A result that stays
    ``pending`` (unknown method / missing command) is left unstamped — provenance
    attaches to judgements, not to unjudged rows. Without a ``context`` (legacy
    callers) nothing is stamped.
    """
    if context is None or ni.result not in TERMINAL_INVARIANT_RESULTS:
        return ni
    return replace(
        ni,
        provenance_origin=PROVENANCE_RECORDED,
        verified_ref=context.ref,
        verified_surface_kind=context.surface_kind.value,
    )


def _check_invariant(repo_root: Path, ni: NegativeInvariant) -> NegativeInvariant:
    """Run a single negative invariant check."""
    if ni.verification_method == "grep_absence":
        return _check_grep_absence(repo_root, ni)
    elif ni.verification_method == "custom_command":
        return _check_custom_command(repo_root, ni)
    else:
        # Unknown method — leave as pending
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="pending",
            evidence=f"Unknown verification method: {ni.verification_method}",
            extras=ni.extras,
        )


def _check_grep_absence(repo_root: Path, ni: NegativeInvariant) -> NegativeInvariant:
    """Grep for pattern; exit code 1 means confirmed absent."""
    if not ni.verification_command:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="pending",
            evidence="No grep pattern specified in verification_command",
            scope=ni.scope,
            extras=ni.extras,
        )

    # A scoped invariant restricts the grep to its declared repo-relative
    # search root(s); an unscoped one searches the whole repo (``.``), as before.
    search_roots = ni.scope.split() if ni.scope else ["."]

    try:
        result = subprocess.run(
            [
                "grep",
                "-r",
                "--exclude=acceptance-matrix.json",
                "--exclude-dir=.git",
                "--",
                ni.verification_command,
                *search_roots,
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="verification_error",
            evidence=f"grep failed to start: {exc}",
            scope=ni.scope,
            extras=ni.extras,
        )
    if result.returncode == 1:
        # No matches — pattern is absent
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="confirmed_absent",
            evidence="grep found zero matches",
            scope=ni.scope,
            extras=ni.extras,
        )
    if result.returncode == 0:
        matches = result.stdout.strip().splitlines()[:5]
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="still_present",
            evidence=f"grep found matches: {'; '.join(matches)}",
            scope=ni.scope,
            extras=ni.extras,
        )
    details = (result.stderr or result.stdout).strip()[:500]
    return NegativeInvariant(
        invariant_id=ni.invariant_id,
        description=ni.description,
        verification_method=ni.verification_method,
        verification_command=ni.verification_command,
        result="verification_error",
        evidence=f"grep verification failed (exit {result.returncode}): {details}",
        scope=ni.scope,
        extras=ni.extras,
    )


def _check_custom_command(repo_root: Path, ni: NegativeInvariant) -> NegativeInvariant:
    """Run custom command — exit code 0 means confirmed absent."""
    if not ni.verification_command:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="pending",
            evidence="No command specified in verification_command",
            extras=ni.extras,
        )

    try:
        result = run_configured_command(
            ni.verification_command,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
    except ConfiguredCommandUnsupported as exc:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="pending",
            evidence=str(exc),
            extras=ni.extras,
        )
    except OSError as exc:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="still_present",
            evidence=f"Command failed to start: {exc}",
            extras=ni.extras,
        )
    if result.returncode == 0:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="confirmed_absent",
            evidence=f"Command exited 0: {result.stdout.strip()[:200]}",
            extras=ni.extras,
        )
    else:
        return NegativeInvariant(
            invariant_id=ni.invariant_id,
            description=ni.description,
            verification_method=ni.verification_method,
            verification_command=ni.verification_command,
            result="still_present",
            evidence=f"Command exited {result.returncode}: {result.stderr.strip()[:200]}",
            extras=ni.extras,
        )
