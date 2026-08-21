"""Negotiated client-side admission for ``spec-kitty sync now`` (#3620, WP1).

Commit cd3d6a91d2 (#3293) shipped a hard, unconditional client admission gate:
``sync now`` refuses to deliver unless a project carries an ADMITTED delivery
target, and the only writer of that state
(:meth:`specify_cli.sync.admission_operations.AdmissionOperationService.perform`)
has no production caller — its server endpoint (``PUT
/api/v1/sync/projects/{uuid}/sync-admission/``) is not deployed. The deployed
SaaS batch-ingest endpoint requires no admission at all, so every consented
project's delivery is gated shut for a capability the server never asked for.

**Keep-gate-but-negotiate.** This module keeps the ADMITTED invariant honest
(:mod:`specify_cli.delivery.dispatcher` still refuses a non-admitted context)
but conditions *how a project becomes admitted* on what the server has
actually advertised:

* :func:`server_requires_strict_admission` resolves whether the server has
  advertised strict admission. Default ``False`` — the deployed SaaS needs no
  admission today (D-009: strict activates only after the server advertises
  it, not before). ``True`` only on an explicit signal: a future handshake key
  (dormant until SaaS #795 ships) or an explicit local override.
* :func:`maybe_admit_locally` mints a **labeled** local self-admission row —
  ``binding_audience`` prefixed ``"local-nonstrict:"`` (see
  :data:`specify_cli.delivery.targets.LOCAL_NONSTRICT_AUDIENCE_PREFIX`) — for a
  consented, authenticated project against a non-strict server, so the
  existing (still locally-consent-gated) delivery path can proceed without a
  live call to the undeployed admission endpoint. This is **not** egress
  relaxation: no new transmit primitive is added, and the label makes the
  self-admission auditable and distinct from a real server-acknowledged one.
  When SaaS #795 ships and a server starts advertising strict admission, this
  becomes a permanent no-op for that origin, and
  ``AdmissionOperationService.perform`` becomes the sole writer again.

Non-goals (N1 in the mission spec): no live call to the admission endpoint is
wired here — it stays dormant.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.sync.project_store import ProjectSyncStore
    from specify_cli.sync.target_authority import ResolvedSyncTarget

#: Explicit local override: force the strict-admission path even against a
#: server that has not advertised it (operator/test escape hatch).
STRICT_ADMISSION_ENV_VAR = "SPEC_KITTY_SYNC_STRICT_ADMISSION"

#: Persisted equivalent, read from the same ``[event_sync]`` config table
#: ``sync_runtime.py`` already owns (``_read_event_sync_table``).
_EVENT_SYNC_STRICT_ADMISSION_KEY = "strict_admission"

#: Dormant handshake shape SaaS #795 will advertise: ``{"admission": {"required": true}}``.
_HANDSHAKE_ADMISSION_KEY = "admission"
_HANDSHAKE_REQUIRED_KEY = "required"

_TRUTHY_ENV_TOKENS = frozenset({"1", "true", "yes", "on"})

#: Per-normalized-origin memoization (module-level; contract: resolved once
#: per process, not once per dispatch batch). :func:`reset_strict_admission_cache`
#: is the test-only escape hatch.
_strict_admission_cache: dict[str, bool] = {}


def reset_strict_admission_cache() -> None:
    """Clear the per-origin memoization (test-only; production never needs this)."""
    _strict_admission_cache.clear()


def _handshake_requires_strict(handshake: Mapping[str, object] | None) -> bool:
    if not handshake:
        return False
    admission = handshake.get(_HANDSHAKE_ADMISSION_KEY)
    if not isinstance(admission, Mapping):
        return False
    return admission.get(_HANDSHAKE_REQUIRED_KEY) is True


def _env_requires_strict() -> bool:
    raw = os.environ.get(STRICT_ADMISSION_ENV_VAR)
    return raw is not None and raw.strip().lower() in _TRUTHY_ENV_TOKENS


def _config_requires_strict() -> bool:
    from specify_cli.sync.sync_runtime import _read_event_sync_table

    table = _read_event_sync_table()
    return table.get(_EVENT_SYNC_STRICT_ADMISSION_KEY) is True


def _normalize_origin(server_origin: str) -> str:
    # Sibling private helper: matches the sync package's established
    # cross-module reuse of underscore helpers (e.g. sync_store_report_core
    # importing straight from sync_runtime).
    from specify_cli.sync.target_authority import _normalize_server_origin

    try:
        normalized: str = _normalize_server_origin(server_origin)
        return normalized
    except ValueError:
        # An unparsable origin still needs a stable cache key; fail toward the
        # safer (strict-capable) shape rather than raising out of a resolver.
        return server_origin.strip()


def server_requires_strict_admission(
    server_origin: str,
    *,
    handshake: Mapping[str, object] | None = None,
) -> bool:
    """Whether *server_origin* has advertised strict client admission (D-009, #795).

    Default ``False`` — the deployed SaaS requires no admission today. Returns
    ``True`` only on an explicit strict signal:

    1. ``handshake["admission"]["required"] is True`` — a future/dormant key,
       safe to omit (``handshake=None`` today, always).
    2. ``SPEC_KITTY_SYNC_STRICT_ADMISSION`` truthy in the environment.
    3. ``[event_sync] strict_admission = true`` in the persisted config table.

    Memoized per normalized *server_origin* in a module-level dict, so the
    capability is resolved once per process rather than once per dispatch
    batch. :func:`reset_strict_admission_cache` clears it (tests only).
    """
    normalized = _normalize_origin(server_origin)
    if normalized in _strict_admission_cache:
        return _strict_admission_cache[normalized]
    strict = _handshake_requires_strict(handshake) or _env_requires_strict() or _config_requires_strict()
    _strict_admission_cache[normalized] = strict
    return strict


def maybe_admit_locally(
    store: ProjectSyncStore,
    *,
    target: ResolvedSyncTarget,
    routing_project_uuid: str,
) -> None:
    """Mint a LOCAL self-admission row for a consented, non-strict-server project.

    A no-op unless **every** guard holds:

    * local consent is GRANTED for this project (``record_project_opt_in``
      already wrote it; this never re-asks or overrides consent — G1/N1);
    * a local authenticated session with a resolvable Private Teamspace exists
      (the audience local self-admission would bind to);
    * the resolved server has not advertised strict admission
      (:func:`server_requires_strict_admission`); and
    * the project is not already admitted (idempotent — AC-3: a second
      ``sync now`` does not re-mint or touch an existing admitted row,
      local or real).

    All four guards and the write happen inside one project unit of work, so
    the check-then-write is atomic against a concurrent admission.
    """
    if server_requires_strict_admission(target.resolved_server_url):
        return
    from specify_cli.auth import get_token_manager
    from specify_cli.auth.session import require_private_team_id

    session = get_token_manager().get_current_session()
    if session is None:
        return
    private_teamspace_id = require_private_team_id(session)
    if private_teamspace_id is None:
        return

    from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
    from specify_cli.sync.project_context import AdmissionState, ConsentState
    from specify_cli.sync.target_authority import build_admission_audience

    registry = ProjectDeliveryTargetRegistry(store)
    with store.unit_of_work() as unit:
        context = store.create_context_from_unit(unit)
        if context.consent_state is not ConsentState.GRANTED:
            return
        current = registry.get_current(unit)
        if current is not None and current.admission_state is AdmissionState.ADMITTED:
            return
        audience = build_admission_audience(
            target,
            account_identity=str(session.email),
            private_teamspace_id=private_teamspace_id,
            project_uuid=routing_project_uuid,
            configuration_generation=1,
        )
        registry.admit_locally(unit, audience)


__all__ = [
    "maybe_admit_locally",
]
