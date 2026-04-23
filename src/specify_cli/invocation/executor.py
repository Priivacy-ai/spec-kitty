"""ProfileInvocationExecutor: single execution primitive for profile-governed invocations.

IMPORTANT: mark_loaded=False is always passed to build_charter_context().
Failing to pass this flag would corrupt context-state.json and break the
specify/plan first-load detection — these commands use first_load as a
sentinel to decide whether to show the full charter vs a compact summary.
The invocation executor must NEVER claim a first-load token.
"""

from __future__ import annotations

import datetime
import hashlib
import json as _json_mod
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from specify_cli.glossary.chokepoint import GlossaryChokepoint

import ulid as _ulid_mod  # matches codebase pattern: status/emit.py, core/mission_creation.py

from charter.context import build_charter_context
from specify_cli.invocation.errors import InvalidModeForEvidenceError, InvocationError
from specify_cli.invocation.modes import ModeOfWork
from specify_cli.invocation.propagator import InvocationSaaSPropagator
from specify_cli.invocation.record import InvocationRecord, promote_to_evidence
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.router import ActionRouter, RouterDecision  # WP02: router implemented
from specify_cli.invocation.writer import InvocationWriter, normalise_ref


def _new_ulid() -> str:
    """Generate a new ULID string using the codebase's existing ulid library.

    Matches the pattern in src/specify_cli/status/emit.py lines 80-84.
    Handles both python-ulid API variants gracefully.
    """
    try:
        # python-ulid >= 1.0 API: _ulid_mod.new().str
        new_fn = getattr(_ulid_mod, "new", None)
        if new_fn is not None:
            return str(new_fn().str)
    except Exception:  # noqa: BLE001
        pass
    # Fallback: construct ULID directly
    return str(_ulid_mod.ULID())


class ActionRouterPlugin(Protocol):
    """No-op protocol stub — reserved for future hybrid routing extension (WP02)."""

    # No methods in v1. Fill in WP02's ActionRouterPlugin slot here.


class InvocationPayload:
    """Ephemeral response returned to CLI callers."""

    __slots__ = (
        "invocation_id",
        "profile_id",
        "profile_friendly_name",
        "action",
        "governance_context_text",
        "governance_context_hash",
        "governance_context_available",
        "router_confidence",
        "glossary_observations",
    )

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {}
        for s in self.__slots__:
            # Use getattr default so callers that omit glossary_observations
            # (e.g. tests constructing InvocationPayload directly) get None
            # instead of AttributeError. C-005 backward-compat fix.
            val = getattr(self, s, None)
            # Only serialise glossary_observations via its to_dict() — explicit,
            # not duck-typed, to avoid accidentally serialising future slots
            # that happen to carry objects with a to_dict() method. RISK-3 fix.
            if s == "glossary_observations" and val is not None:
                result[s] = val.to_dict()
            else:
                result[s] = val
        return result


class ProfileInvocationExecutor:
    """Single execution primitive for all profile-governed invocations.

    Does NOT spawn any LLM call. Returns synchronously.
    mark_loaded=False ensures first-load state for specify/plan/implement/review
    is NOT poisoned by invocation calls.
    """

    def __init__(
        self,
        repo_root: Path,
        router: ActionRouter | None = None,
        propagator: InvocationSaaSPropagator | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._registry = ProfileRegistry(repo_root)
        self._writer = InvocationWriter(repo_root)
        self._router = router
        self._propagator = propagator
        self._chokepoint: GlossaryChokepoint | None = None  # lazy-loaded on first invoke

    def invoke(
        self,
        request_text: str,
        profile_hint: str | None = None,
        actor: str = "unknown",
        mode_of_work: ModeOfWork | None = None,
    ) -> InvocationPayload:
        """Route the request, load governance context, write started record, return payload.

        IMPORTANT: Does NOT spawn any LLM call. Returns synchronously.
        mark_loaded=False ensures first-load state for specify/plan/implement/review
        is NOT poisoned by invocation calls.
        """
        invocation_id = _new_ulid()  # uses codebase-standard ulid library

        # 1. Resolve (profile_id, action)
        router_confidence: str | None = None
        if profile_hint is not None:
            profile = self._registry.resolve(profile_hint)  # raises ProfileNotFoundError
            action = self._derive_action_from_request(request_text, profile.role)
            router_confidence = None  # caller supplied explicit hint
        elif self._router is not None:
            # route() returns RouterDecision or raises RouterAmbiguityError (never returns error)
            result: RouterDecision = self._router.route(request_text)
            profile = self._registry.resolve(result.profile_id)
            action = result.action
            router_confidence = result.confidence
        else:
            raise RuntimeError(
                "No profile_hint and no router configured. "
                "Use 'spec-kitty ask <profile>' or supply a router."
            )

        # 2. Assemble governance context (mark_loaded=False — critical)
        # NEVER pass mark_loaded=True here — would corrupt context-state.json
        # and break the specify/plan first-load detection.
        ctx_result = build_charter_context(
            self._repo_root,
            profile=profile.profile_id,
            action=action,
            mark_loaded=False,
        )
        ctx_hash = hashlib.sha256(ctx_result.text.encode()).hexdigest()[:16]
        ctx_available = ctx_result.mode != "missing"

        # 2a. Run glossary chokepoint scan (T016/T017)
        # Severity routing: bundle.high_severity = HIGH only; bundle.all_conflicts = all severities.
        # This routing is performed inside GlossaryChokepoint._run_inner() (WP02 code).
        # Exception guard: any failure returns an error-bundle; the invocation always continues.
        from specify_cli.glossary.chokepoint import GlossaryChokepoint, GlossaryObservationBundle
        try:
            if self._chokepoint is None:
                self._chokepoint = GlossaryChokepoint(self._repo_root)
            bundle = self._chokepoint.run(
                request_text,
                invocation_id=invocation_id,
                actor_id=actor,
            )
        except Exception as _exc:  # noqa: BLE001
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "glossary chokepoint outer exception (invocation_id=%r): %r", invocation_id, _exc)
            bundle = GlossaryObservationBundle(
                matched_urns=(), high_severity=(), all_conflicts=(),
                tokens_checked=0, duration_ms=0.0, error_msg=repr(_exc))

        # 3. Write started record (raises InvocationWriteError on fs failure)
        started_at = datetime.datetime.now(datetime.UTC).isoformat()
        record = InvocationRecord(
            event="started",
            invocation_id=invocation_id,
            profile_id=profile.profile_id,
            action=action,
            request_text=request_text,
            governance_context_hash=ctx_hash,
            governance_context_available=ctx_available,
            actor=actor,
            router_confidence=router_confidence,
            started_at=started_at,
            mode_of_work=mode_of_work.value if mode_of_work else None,
        )
        self._writer.write_started(record)  # raises InvocationWriteError → non-zero exit

        # Step 5: Write glossary observation to trail (best-effort)
        try:  # noqa: SIM105
            self._writer.write_glossary_observation(invocation_id, bundle)
        except Exception:  # noqa: BLE001
            pass

        # Propagate started event (non-blocking, best-effort)
        if self._propagator is not None:
            self._propagator.submit(record)

        return InvocationPayload(
            invocation_id=invocation_id,
            profile_id=profile.profile_id,
            profile_friendly_name=profile.name,  # AgentProfile.name (not friendly_name — that field does not exist)
            action=action,
            governance_context_text=ctx_result.text,
            governance_context_hash=ctx_hash,
            governance_context_available=ctx_available,
            router_confidence=router_confidence,
            glossary_observations=bundle,
        )

    def complete_invocation(
        self,
        invocation_id: str,
        outcome: str | None = None,
        evidence_ref: str | None = None,
        artifact_refs: list[str] | None = None,
        commit_sha: str | None = None,
    ) -> InvocationRecord:
        """Close an open invocation record and propagate the completed event.

        Wraps ``InvocationWriter.write_completed`` so that the completed record
        is also submitted to the SaaS propagator (non-blocking, best-effort).

        Raises ``AlreadyClosedError`` if already closed (idempotent guard).
        Raises ``InvocationError`` if invocation_id is not found.
        Raises ``InvocationWriteError`` on filesystem failure.
        Raises ``InvalidModeForEvidenceError`` if evidence_ref is supplied on an
            advisory or query invocation (FR-009). This is a pre-write check —
            no JSONL lines are written if this error is raised.
        """
        # Step 1: Read started event for mode enforcement (FR-009).
        started_mode = self._read_started_mode(invocation_id)

        # Step 2: Enforce mode gate on evidence promotion BEFORE any write.
        if evidence_ref is not None and started_mode in {ModeOfWork.ADVISORY, ModeOfWork.QUERY}:
            raise InvalidModeForEvidenceError(invocation_id, started_mode)

        # Step 3: Append completed event (existing behaviour).
        completed = self._writer.write_completed(
            invocation_id,
            self._repo_root,
            outcome=outcome,
            evidence_ref=evidence_ref,
        )

        # Step 4: Promote to Tier 2 evidence artifact if --evidence was supplied (existing behaviour).
        self._promote_evidence_if_requested(completed, evidence_ref)

        # Step 5 (NEW): Append artifact_link events (FR-007).
        self._append_artifact_links(invocation_id, artifact_refs)

        # Step 6 (NEW): Append commit_link event (FR-007).
        self._append_commit_link(invocation_id, commit_sha)

        # Step 7: Propagate completed event (non-blocking, best-effort; existing behaviour).
        # Correlation events (artifact_link, commit_link) are locally written by
        # append_correlation_link() above but are NOT submitted to the propagator in
        # this release. The policy gate in projection_policy.py is implemented (and
        # POLICY_TABLE assigns project=True for task_execution/mission_step correlation
        # events), but the dict-record submission path in _propagate_one is not yet
        # wired. SaaS projection of correlation events is deferred consistent with the
        # ADR-004 local-only stance for Tier 2 content in the 3.2.x line. See
        # propagator.py NOTE and docs/trail-model.md "Correlation Links" section.
        if self._propagator is not None:
            self._propagator.submit(completed)

        return completed

    def _promote_evidence_if_requested(
        self,
        completed: InvocationRecord,
        evidence_ref: str | None,
    ) -> None:
        if evidence_ref is None:
            return
        content = self._resolve_evidence_content(evidence_ref)
        evidence_base_dir = self._repo_root / ".kittify" / "evidence"
        promote_to_evidence(completed, evidence_base_dir, content)

    def _resolve_evidence_content(self, evidence_ref: str) -> str:
        candidate_path = self._resolve_evidence_path(evidence_ref)
        try:
            return (
                candidate_path.read_text(encoding="utf-8")
                if candidate_path is not None
                else evidence_ref
            )
        except OSError:
            return evidence_ref

    def _resolve_evidence_path(self, evidence_ref: str) -> Path | None:
        evidence_path = Path(evidence_ref)
        if evidence_path.is_absolute():
            return evidence_path

        repo_root = self._repo_root.resolve()
        resolved_relative_path = (repo_root / evidence_path).resolve()
        if resolved_relative_path.is_relative_to(repo_root):
            return resolved_relative_path
        return None

    def _append_artifact_links(
        self,
        invocation_id: str,
        artifact_refs: list[str] | None,
    ) -> None:
        for raw_ref in artifact_refs or []:
            normalised = normalise_ref(raw_ref, self._repo_root)
            self._writer.append_correlation_link(
                invocation_id,
                kind="artifact",
                ref=normalised,
            )

    def _append_commit_link(self, invocation_id: str, commit_sha: str | None) -> None:
        if commit_sha is None:
            return
        self._writer.append_correlation_link(invocation_id, sha=commit_sha)

    def _read_started_mode(self, invocation_id: str) -> ModeOfWork | None:
        """Read mode_of_work from the started event. Returns None for pre-mission records
        or when the stored value is not a recognised ModeOfWork (malformed trail)."""
        path = self._writer.invocation_path(invocation_id)
        if not path.exists():
            raise InvocationError(f"Invocation record not found: {invocation_id}")
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        first = _json_mod.loads(first_line)
        raw = first.get("mode_of_work")
        if not raw:
            return None
        try:
            return ModeOfWork(raw)
        except ValueError:
            return None  # unknown/invalid mode_of_work → treat as legacy, skip enforcement

    def _derive_action_from_request(self, request_text: str, role: object) -> str:  # noqa: ARG002
        """Derive canonical action token from role when profile_hint is explicit."""
        from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES
        from doctrine.agent_profiles.profile import Role

        caps = DEFAULT_ROLE_CAPABILITIES.get(role) if isinstance(role, Role) else None
        if caps and caps.canonical_verbs:
            return caps.canonical_verbs[0]
        return "advise"  # default fallback
