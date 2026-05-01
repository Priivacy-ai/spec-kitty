"""StateManager: lifecycle wrapper around :class:`PKCEState`.

This is the single surface WP04's flow orchestrator will call to obtain,
validate, and retire PKCE state for a login attempt. Keeping the pkce,
state, and validation logic behind one class lets the orchestrator stay
agnostic of the underlying primitives and makes future persistent state
(e.g. if we ever needed to survive a restart) a single-seam change.
"""

from __future__ import annotations

from ..errors import StateExpiredError
from .pkce import generate_pkce_pair
from .state import PKCEState


class StateManager:
    """Manages PKCE state lifecycle for in-flight Authorization Code flows."""

    def generate(self) -> PKCEState:
        """Generate a fresh :class:`PKCEState`.

        Returns:
            A new :class:`PKCEState` with a freshly-minted verifier, challenge,
            and CSRF nonce, expiring 5 minutes from now.
        """
        verifier, challenge = generate_pkce_pair()
        return PKCEState.create(verifier, challenge)

    def validate_not_expired(self, state: PKCEState) -> None:
        """Raise :class:`StateExpiredError` if ``state`` has expired.

        Args:
            state: The in-flight state to check.

        Raises:
            StateExpiredError: if ``state.is_expired()`` is True.
        """
        if state.is_expired():
            raise StateExpiredError(
                f"PKCEState expired (created {state.created_at.isoformat()}, expires {state.expires_at.isoformat()}). Run `spec-kitty auth login` again."
            )

    def cleanup(self, state: PKCEState) -> None:
        """No-op cleanup hook.

        Present so the orchestrator can call ``manager.cleanup(state)`` in a
        ``finally`` block; if/when state ever becomes persistent (e.g. stored
        on disk for cross-process resumption), cleanup logic lives here.
        """
        # Deliberate no-op: PKCEState is in-memory only today.
        del state
