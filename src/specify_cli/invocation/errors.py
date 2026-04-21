"""Structured error types for the invocation package."""

from __future__ import annotations


class InvocationError(Exception):
    """Base for all invocation errors."""


class ProfileNotFoundError(InvocationError):
    def __init__(self, profile_id: str, available: list[str]) -> None:
        self.profile_id = profile_id
        self.available = available
        super().__init__(f"Profile '{profile_id}' not found. Available: {available}")


class ContextUnavailableError(InvocationError):
    """Governance context could not be assembled (charter not synthesized)."""


class InvocationWriteError(InvocationError):
    """JSONL write failed. Invocation not started."""


class RouterAmbiguityError(InvocationError):
    def __init__(
        self,
        request_text: str,
        error_code: str,  # ROUTER_AMBIGUOUS | ROUTER_NO_MATCH | PROFILE_NOT_FOUND
        candidates: list[dict[str, str]],
        suggestion: str,
    ) -> None:
        self.request_text = request_text
        self.error_code = error_code
        self.candidates = candidates
        self.suggestion = suggestion
        super().__init__(f"{error_code}: {suggestion}")


class AlreadyClosedError(InvocationError):
    def __init__(self, invocation_id: str) -> None:
        super().__init__(f"Invocation {invocation_id} is already closed.")
