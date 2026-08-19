"""Authority adapters for the ``spec-kitty sync`` command surface (WP07).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``) extracts
the authority helpers off the single ``cli/commands/sync.py`` host into this
cohesive seam module. Authority here is **three distinct surfaces**, not two
(architect finding A-2), and the binding invariant (INV-2 / FR-004) is that they
stay **distinct ports/classes** — *not* that every call flow reads or writes only
one of them:

* **READ** — coord/daemon-owner coherence. :func:`_require_daemon_owner_coherence`
  **delegates** to :func:`specify_cli.sync.preflight.run_preflight` (FR-007).
* **WRITE** — share / unshare repository sharing. :func:`request_repository_share`
  and :func:`leave_repository_share` **delegate** to
  :mod:`specify_cli.sync.sharing_client`.
* **delivery-ADMISSION** — read-shaped but bound to the dispatch path.
  :func:`_assert_event_sync_runtime_authority` and
  :func:`_assert_delivery_target_matches_context` **delegate** the audience
  construction to :mod:`specify_cli.sync.target_authority`.

Every adapter is a **thin pass-through** to its named canonical surface — it does
not re-implement ``preflight`` / ``sharing_client`` / ``target_authority`` logic
(DIRECTIVE_044 / A-3: the package already carries ≥5 ``*Authority*`` surfaces; this
module forks none of them). The mixed-authority *flows* that legitimately read AND
write — ``_open_project_dispatch_runtime`` (in :mod:`sync_runtime`) and ``opt_out``
(on the host) — are **frozen verbatim (C-007)**: relocating the admission asserts
does not change how those flows call them; the flows keep reaching the asserts
late-bound through the ``sync`` host module object.

**Late-bound host access (INV-4 / WP03 convention).** The moved asserts are
re-established as ``sync.<name>`` host attributes by the host's husk re-export
block, so ``_open_project_dispatch_runtime`` in :mod:`sync_runtime` — which reaches
them by ``sync_module._assert_*`` attribute access — still resolves, and a
``monkeypatch.setattr("...cli.commands.sync._assert_event_sync_runtime_authority",
...)`` still intercepts. ``tests/architectural/test_sync_no_early_bind.py`` is the
AST guard against early-binding a seam name; ``tests/architectural/
test_sync_two_authority.py`` is the FR-004 guard that the three surfaces stay
distinct.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from specify_cli.cli.console import console


# ---------------------------------------------------------------------------
# READ authority — coord / daemon-owner coherence (delegates to preflight)
# ---------------------------------------------------------------------------
def _require_daemon_owner_coherence(command_name: str | None = None) -> None:
    """FR-007 precondition gate for sync mutating commands.

    Refuses to act when the foreground CLI's identity (package version,
    executable path, server URL, auth scope, queue DB path) does not match
    the registered daemon owner record on any D-3 field. The refusal
    message names the mismatched field(s) so the operator knows which fix
    is needed.

    WP03: thin wrapper over :func:`run_preflight`. ``require_auth`` is
    ``False`` because individual SaaS-producing call sites (``sync now``,
    ``setup-plan``) enforce auth-required explicitly; the generic gate
    only enforces the structural boundary (mismatches, orphans, legacy
    rows in scope).

    No-op when the boundary is coherent. Exits with code 2 otherwise.
    """
    from specify_cli.sync.preflight import run_preflight

    result = run_preflight(repo_root=Path.cwd(), require_auth=False)
    if result.ok:
        return
    label = f" `{command_name}`" if command_name else ""
    if label:
        console.print(f"[red]Refusing{label}.[/red]")
    result.render(console)
    raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# WRITE authority — repository sharing (delegates to sharing_client)
# ---------------------------------------------------------------------------
def request_repository_share(*, source_project_uuid: str, destination_team_slug: str) -> dict[str, Any]:
    """Share this repository into *destination_team_slug* — delegates to sharing_client.

    A thin pass-through to :func:`sharing_client.request_repository_share_sync`; the
    ``RepositorySharingClientError`` it may raise (carrying ``.status_code`` for the
    ``share`` 404-retry branch) propagates unchanged.
    """
    from specify_cli.sync.sharing_client import request_repository_share_sync

    response: dict[str, Any] = request_repository_share_sync(
        source_project_uuid=source_project_uuid,
        destination_team_slug=destination_team_slug,
    )
    return response


def leave_repository_share(*, source_project_uuid: str, destination_team_slug: str) -> dict[str, Any]:
    """Stop sharing this repository into *destination_team_slug* — delegates to sharing_client.

    A thin pass-through to :func:`sharing_client.leave_repository_share_sync`; the
    ``RepositorySharingClientError`` it may raise propagates unchanged.
    """
    from specify_cli.sync.sharing_client import leave_repository_share_sync

    response: dict[str, Any] = leave_repository_share_sync(
        source_project_uuid=source_project_uuid,
        destination_team_slug=destination_team_slug,
    )
    return response


# ---------------------------------------------------------------------------
# delivery-ADMISSION authority — dispatch-bound target/receiver admission
# (delegates the audience construction to target_authority)
# ---------------------------------------------------------------------------
def _assert_event_sync_runtime_authority(
    *,
    target: Any,
    delivery_target: Any,
    routing_project_uuid: str,
) -> None:
    """Fail closed when receiver/auth authority diverges from stored admission."""
    from specify_cli.auth import get_token_manager
    from specify_cli.auth.session import require_private_team_id
    from specify_cli.sync.target_authority import build_admission_audience

    audience = build_admission_audience(
        target,
        account_identity=str(delivery_target.account_identity),
        private_teamspace_id=str(delivery_target.private_teamspace_id),
        project_uuid=delivery_target.project_uuid,
        configuration_generation=int(delivery_target.configuration_generation),
    )
    if audience.normalized_server_origin != str(delivery_target.target_identity):
        raise RuntimeError("event-sync receiver URL does not match admitted delivery target")
    if routing_project_uuid != str(delivery_target.project_uuid.storage_token):
        raise RuntimeError("event-sync routing project does not match admitted delivery target")
    session = get_token_manager().get_current_session()
    if session is None:
        raise RuntimeError("event-sync admitted delivery target requires a local authenticated session")
    private_teamspace_id = require_private_team_id(session)
    account_candidates = {str(session.email), str(session.user_id)}
    if str(delivery_target.account_identity) not in account_candidates:
        raise RuntimeError("event-sync local authenticated account does not match admitted delivery target")
    if private_teamspace_id != str(delivery_target.private_teamspace_id):
        raise RuntimeError("event-sync local Private Teamspace does not match admitted delivery target")


def _assert_delivery_target_matches_context(
    *,
    delivery_target: Any,
    context: Any,
) -> None:
    """Bind the selected delivery target to the immutable context tuple."""
    target_audience = getattr(context, "target_audience", None)
    if target_audience is None:
        raise RuntimeError("event-sync selected context has no admitted target audience")
    checks = (
        str(delivery_target.target_identity) == str(target_audience.target_identity),
        str(delivery_target.account_identity) == str(target_audience.account_identity),
        str(delivery_target.private_teamspace_id) == str(target_audience.private_teamspace_id),
        str(delivery_target.project_uuid.storage_token) == str(target_audience.project_uuid.storage_token),
        int(delivery_target.configuration_generation) == int(target_audience.configuration_generation),
        str(delivery_target.admission_generation) == str(context.admission_generation),
        str(delivery_target.binding_audience) == str(context.binding_audience),
    )
    if not all(checks):
        raise RuntimeError("event-sync delivery target does not match immutable project context")
