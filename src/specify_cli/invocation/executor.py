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
from pathlib import Path
from typing import Protocol

import ulid as _ulid_mod  # matches codebase pattern: status/emit.py, core/mission_creation.py

from charter.context import build_charter_context
from specify_cli.invocation.errors import InvocationWriteError, ProfileNotFoundError
from specify_cli.invocation.propagator import InvocationSaaSPropagator
from specify_cli.invocation.record import InvocationRecord, promote_to_evidence
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.router import ActionRouter, RouterDecision  # WP02: router implemented
from specify_cli.invocation.writer import InvocationWriter


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
    )

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> dict[str, object]:
        return {s: getattr(self, s) for s in self.__slots__}


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

    def invoke(
        self,
        request_text: str,
        profile_hint: str | None = None,
        actor: str = "unknown",
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

        # 3. Write started record (raises InvocationWriteError on fs failure)
        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
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
        )
        self._writer.write_started(record)  # raises InvocationWriteError → non-zero exit

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
        )

    def complete_invocation(
        self,
        invocation_id: str,
        outcome: str | None = None,
        evidence_ref: str | None = None,
    ) -> InvocationRecord:
        """Close an open invocation record and propagate the completed event.

        Wraps ``InvocationWriter.write_completed`` so that the completed record
        is also submitted to the SaaS propagator (non-blocking, best-effort).

        Raises ``AlreadyClosedError`` if already closed (idempotent guard).
        Raises ``InvocationError`` if invocation_id is not found.
        Raises ``InvocationWriteError`` on filesystem failure.
        """
        completed = self._writer.write_completed(
            invocation_id,
            self._repo_root,
            outcome=outcome,
            evidence_ref=evidence_ref,
        )
        # Promote to Tier 2 evidence artifact if --evidence was supplied
        if evidence_ref is not None:
            evidence_path = Path(evidence_ref)
            candidate_path: Path | None = None
            if not evidence_path.is_absolute():
                repo_root = self._repo_root.resolve()
                resolved_relative_path = (repo_root / evidence_path).resolve()
                if resolved_relative_path.is_relative_to(repo_root):
                    candidate_path = resolved_relative_path
            else:
                # Absolute paths are the operator's explicit choice.
                candidate_path = evidence_path
            try:
                content = (
                    candidate_path.read_text(encoding="utf-8")
                    if candidate_path is not None
                    else evidence_ref
                )
            except OSError:
                content = evidence_ref  # fallback: treat the value as inline content
            evidence_base_dir = self._repo_root / ".kittify" / "evidence"
            promote_to_evidence(completed, evidence_base_dir, content)
        # Propagate completed event (non-blocking, best-effort)
        if self._propagator is not None:
            self._propagator.submit(completed)
        return completed

    def _derive_action_from_request(self, request_text: str, role: object) -> str:  # noqa: ARG002
        """Derive canonical action token from role when profile_hint is explicit."""
        from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES
        from doctrine.agent_profiles.profile import Role

        caps = DEFAULT_ROLE_CAPABILITIES.get(role) if isinstance(role, Role) else None
        if caps and caps.canonical_verbs:
            return caps.canonical_verbs[0]
        return "advise"  # default fallback
