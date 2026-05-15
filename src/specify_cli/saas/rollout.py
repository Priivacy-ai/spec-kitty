"""Compatibility surface for hosted SaaS sync rollout.

Stability contract: ``contracts/saas_rollout.md``.

Hosted SaaS sync is release-ready and no longer hidden behind
``SPEC_KITTY_ENABLE_SAAS_SYNC``.  The symbols in this module remain for
backwards-compatible imports from tracker/sync code and older tests, but the
environment variable is intentionally ignored.
"""

from __future__ import annotations

SAAS_SYNC_ENV_VAR = "SPEC_KITTY_ENABLE_SAAS_SYNC"

_DISABLED_MESSAGE = (
    "Hosted SaaS sync is enabled by default. "
    "Use `spec-kitty sync opt-out` to disable uploads for this checkout."
)


def is_saas_sync_enabled() -> bool:
    """Return whether hosted SaaS sync is available in this release channel.

    The answer is always ``True``.  Per-checkout and per-repository opt-out
    still lives in ``specify_cli.sync.routing`` / ``SyncConfig`` and is the
    supported way to stop uploads.
    """
    return True


def saas_sync_disabled_message() -> str:
    """Return the compatibility message for stale disabled-gate callers.

    New code should not branch on this message; SaaS sync is no longer
    feature-flagged off by environment.
    """
    return _DISABLED_MESSAGE
