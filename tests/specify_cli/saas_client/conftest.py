"""Shared fixtures for ``tests/specify_cli/saas_client/``.

#3030 FR-030 gave :class:`~specify_cli.saas_client.client.SaasClient` a consent
gate: every request is refused unless the client was told which project owns the
data *and* that project has consented to hosted sync. The refusing default is
deliberate — a transport with no project attribution cannot resolve consent, and
inability to determine consent is never consent.

``test_client.py`` predates that and constructs clients inline in ten places to
test URL construction, error mapping and timeouts. Rather than thread a project
through every one of those call sites, this autouse fixture injects a checkout
that has genuinely opted in, so the **real** consent chain runs on every legacy
call and grants.

Deliberately not done by stubbing ``project_egress_refusal`` to a no-op. A gate
switched off across a whole file is indistinguishable from a gate that does not
work, and #3030 has already found a pin that passed with its invariant stripped
entirely. Here the chain executes for real; only the answer is arranged.

``test_client_consent_gate_3030.py`` passes ``project_root`` explicitly on every
construction, so the injection below never fires for it — including the cases
that pass ``None`` on purpose to prove an unattributed client refuses.

Mirrors the same idiom in ``tests/sync/tracker/conftest.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.saas_client import client as _client_mod
from specify_cli.sync.consent import record_project_opt_in

#: Matches the shape ``identity/project.py`` mints, so the consent resolver's
#: level-1 read finds a complete, understandable record rather than a fault.
_CONSENTING_CONFIG = (
    "\n".join(
        [
            "project:",
            "  uuid: 2b7f6a10-3c4d-4e5f-8a9b-2b7f6a103c4d",
            "  slug: legacy-saas-client-suite",
            "  node_id: node00000002",
            "  repo_slug: spec-kitty-tests/legacy-saas-client-suite",
            "  build_id: 2b7f6a10-3c4d-4e5f-8a9b-2b7f6a103c4d",
            "sync:",
            "  enabled: true",
        ]
    )
    + "\n"
)


@pytest.fixture(autouse=True)
def _default_saas_client_project(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Give inline-constructed ``SaasClient``s a consenting project by default."""
    consenting: dict[str, Any] = {}
    tmp_path = request.getfixturevalue("tmp_path")
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    def _consenting_project_root():
        if "path" not in consenting:
            root = tmp_path / "legacy-saas-client-checkout"
            (root / ".kittify").mkdir(parents=True, exist_ok=True)
            (root / ".kittify" / "config.yaml").write_text(_CONSENTING_CONFIG, encoding="utf-8")
            consenting["path"] = root
        return consenting["path"]

    real_init = _client_mod.SaasClient.__init__

    def _seed_authority(base_url: str) -> None:
        # Issue #3 removed the hosted transport's project→host admission
        # binding, so only the consent decision is seeded here; no client in
        # this package reads ``project_target_admissions`` any more.
        del base_url
        project_uuid = "2b7f6a10-3c4d-4e5f-8a9b-2b7f6a103c4d"
        record_project_opt_in(project_uuid, actor="legacy-saas-client-fixture")

    def _init_with_default_project(self, *args: Any, **kwargs: Any) -> None:
        # Injected only when the caller omitted the kwarg entirely, so a test
        # that passes ``project_root=None`` on purpose still gets an
        # unattributed — and therefore refusing — client.
        if "project_root" not in kwargs:
            kwargs["project_root"] = _consenting_project_root()
            base_url = str(args[0] if args else kwargs["base_url"])
            _seed_authority(base_url)
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(_client_mod.SaasClient, "__init__", _init_with_default_project)
    monkeypatch.setattr(
        _client_mod,
        "_authenticated_authority_for_token",
        lambda token: (
            (
                "account-test",
                "private-test",
                "acme-team" if token == "valid-token" else "acme-team-a",
            )
            if token in {"valid-token", "token-belonging-to-A"}
            else ("legacy-account", "legacy-private-teamspace", "my-team")
        ),
    )
    yield
