"""Forbidden-key sets and the client-side "forbidden-field zero-attempt" gate.

``FORBIDDEN_CONTROL_KEYS`` mirrors F3's ``FORBIDDEN_KEYS_V1``
(m1-contract-drafts/F3.md §3.1 item 2, closed, versioned, direction-agnostic,
recursive key-only walk). ``FORBIDDEN_OBSERVATION_KEYS`` mirrors F1's set
(m1-contract-drafts/F1.md §3.3). Both are bundled here as literal frozensets
— Z1 cannot import either upstream package (Z1.md §2.5, §3.2 item 3) — with a
committed version constant each, so a future drift is a deliberate,
versioned, re-pinned act rather than silent bit-rot (Z1.md §4 row N20).

``assert_clean`` is called synchronously *before* any network attempt
(Z1.md §3.2 item 8 step 2): "forbidden-field zero-attempt" means the relay's
request log stays empty when it fires, not merely that the request later
fails.

The key match is case-sensitive exact-match by design, parity-anchored to
F3's own case-sensitive forbidden-key check (F3.md §3.1 item 2) — this is a
deliberate parity choice, not an oversight, so ``{"Token": "x"}`` is not
rejected by ``FORBIDDEN_CONTROL_KEYS``/``FORBIDDEN_OBSERVATION_KEYS`` unless
the exact-cased key is present.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# m1-contract-drafts/F3.md:103
FORBIDDEN_CONTROL_KEYS: frozenset[str] = frozenset(
    {
        "token",
        "authorization",
        "bearer",
        "password",
        "detail",
        "team",
        "team_id",
        "deployment",
        "deployment_id",
        "membership",
        "role",
        "user_id",
        "url",
        "runtime_url",
    }
)
FORBIDDEN_CONTROL_KEYS_VERSION: int = 1

# m1-contract-drafts/F1.md:162-166
FORBIDDEN_OBSERVATION_KEYS: frozenset[str] = frozenset(
    {
        "detail",
        "message",
        "text",
        "prose",
        "body",
        "command_text",
        "stdout",
        "stderr",
        "user",
        "user_id",
        "email",
        "actor",
        "team",
        "team_id",
        "team_slug",
        "deployment",
        "deployment_id",
        "token",
        "authorization",
        "bearer",
        "password",
        "secret",
        "url",
        "runtime_url",
        "branch",
    }
)
FORBIDDEN_OBSERVATION_KEYS_VERSION: str = "v1"


class ForbiddenFieldError(ValueError):
    """A document carried a forbidden key. Never repaired — the caller must
    not send this document at all."""

    def __init__(self, key: str, path: tuple[str | int, ...]):
        self.key = key
        self.path = path
        super().__init__(
            f"forbidden key {key!r} at path {'.'.join(str(p) for p in path) or '<root>'}"
        )


def _walk(node: Any, forbidden: frozenset[str], path: tuple[str | int, ...]) -> None:
    if isinstance(node, Mapping):
        # Depth-first, first hit in document order — matches F3.md's own
        # precedence rule for the forbidden-key check (§3.1 item 3).
        for key, value in node.items():
            if key in forbidden:
                raise ForbiddenFieldError(key, path + (key,))
            _walk(value, forbidden, path + (key,))
    elif isinstance(node, (list, tuple)):
        for index, item in enumerate(node):
            _walk(item, forbidden, path + (index,))


def assert_clean(
    document: Mapping[str, Any], *, forbidden: frozenset[str] = FORBIDDEN_CONTROL_KEYS
) -> None:
    """Recursive key-only walk. Raises :class:`ForbiddenFieldError` on the
    first hit; never repairs, never returns a cleaned copy.

    A string *value* equal to a forbidden key name is accepted — this is a
    key-only walk, matching F3.md:153's own precedent (mirrors
    ``spec_kitty_events.forbidden_keys``).
    """
    _walk(document, forbidden, ())
