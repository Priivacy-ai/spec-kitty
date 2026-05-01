"""Validate OAuth callback parameters against the expected state (CSRF).

Separated from :mod:`callback_server` so the validation logic is
independently testable without starting a real HTTP server.

Three distinct failure modes are signalled with different exceptions:

- :class:`CallbackError` – the SaaS reported an OAuth-level error
  (``error`` query parameter present) such as ``access_denied``.
- :class:`CallbackValidationError` – the callback is structurally
  invalid from the CLI's point of view: missing ``code``, missing
  ``state``, or ``state`` does not match the expected nonce.

Callers should treat :class:`CallbackValidationError` as a hard stop
(it likely indicates tampering or a stale tab) and :class:`CallbackError`
as something to surface to the user verbatim.
"""

from __future__ import annotations


from ..errors import CallbackError, CallbackValidationError


class CallbackHandler:
    """Validates the OAuth callback parameters against the expected state."""

    def __init__(self, expected_state: str) -> None:
        """Store the CSRF nonce the caller expects to see echoed back.

        Args:
            expected_state: The ``state`` value the CLI sent in the
                authorization request; the SaaS must return the same
                value in the callback URL.
        """
        self._expected_state = expected_state

    def validate(self, params: dict[str, str]) -> tuple[str, str]:
        """Validate ``params`` and return ``(code, state)`` on success.

        Args:
            params: The callback query parameters (already flattened to
                a simple ``dict[str, str]``).

        Returns:
            A tuple of ``(authorization_code, state)``.

        Raises:
            CallbackError: If the SaaS returned an OAuth-level ``error``.
            CallbackValidationError: If ``code`` or ``state`` is missing,
                or if ``state`` does not match the expected CSRF nonce.
        """
        # SaaS-reported OAuth error takes precedence: even if code/state
        # are absent, the user wants to see the real error message.
        if "error" in params:
            error = params["error"]
            desc = params.get("error_description", "")
            if desc:
                raise CallbackError(
                    f"OAuth provider returned error: {error} ({desc})"
                )
            raise CallbackError(f"OAuth provider returned error: {error}")

        if "code" not in params:
            raise CallbackValidationError(
                "Missing 'code' in callback parameters"
            )
        if "state" not in params:
            raise CallbackValidationError(
                "Missing 'state' in callback parameters"
            )

        if params["state"] != self._expected_state:
            # Show only the first 8 chars of each state value in the
            # message so we don't leak the full CSRF nonce to logs.
            raise CallbackValidationError(
                "State mismatch (possible CSRF attack): expected "
                f"{self._expected_state[:8]}..., got {params['state'][:8]}..."
            )

        return params["code"], params["state"]


def validate_callback_params(
    params: dict[str, str], expected_state: str
) -> tuple[str, str]:
    """Functional wrapper around :meth:`CallbackHandler.validate`.

    Convenience for call sites that don't need to keep a handler around;
    identical semantics to constructing a :class:`CallbackHandler` and
    calling ``.validate(params)``.
    """
    return CallbackHandler(expected_state).validate(params)
