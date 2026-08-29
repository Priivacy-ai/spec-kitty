"""FR-028 — ``sync import-history --apply`` is a sixth egress path, and it is ungated.

The 2026-07-27 incident delivered 1,322 events belonging to five never-opted-in
projects. The mission's fix pushed consent into *selection*
(``delivery/selection.select_consented``), which the journal dispatcher
consumes — and ``sync/history_import`` does not. A consent grep across
``src/specify_cli/sync/history_import/`` returned **zero** hits: the only gate on
this path is the ``GateKind`` set ``{SAAS_ENABLED, PRIVATE_TEAMSPACE, AUTH,
ENDPOINT_CONFIGURED}``, which this mission's own root-cause §1 states has no
consent field, plus a ``Mode.TEAMSPACE`` check.

What these tests assert is the **leak**, not a boolean: that no HTTP request is
made at all, and that the engagement name does not appear in the transmitted
bytes. In this product a mission slug is a client engagement name, so the
metadata *is* the confidential content — a test that only asserted
``report.rejected == 1`` would pass on an implementation that POSTed the whole
stream and then discarded the response.

There are **two** sinks on this path, not one. ``run_server_preflight``
(``upload.py``) POSTs the full envelope stream to ``/api/v1/events/preflight/``
before ``_deliver_chunks`` ever runs, so a gate placed at the delivery call would
still have leaked every envelope through the preflight. Both are covered here.

``test_import_history_transmits_for_a_consented_project`` is the **positive
control** and must pass on every tree, before and after the fix: without it, five
green refusals prove only that the harness never transmits anything.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from specify_cli.delivery.interfaces import DeliveryTarget, TargetIdentity
from specify_cli.delivery.receivers import TeamspaceReceiver
from specify_cli.delivery.targets import compute_target_id
from specify_cli.sync.consent import allocate_capture_sequence, record_project_opt_in
from specify_cli.sync.history_disclosure import (
    confirm_history_disclosure,
    preview_sealed_history,
)
from specify_cli.sync.history_import.upload import run_import_upload, upload_envelopes
from specify_cli.sync.project_context import AdmissionState
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

# A mission slug in this product IS a client engagement name (spec.md, FR-026).
# It is the string whose presence on the wire is the confidentiality breach.
_ENGAGEMENT = "acme-holdings-carve-out"
_PROJECT_SLUG = "acme-holdings"
_SERVER = "https://app.spec-kitty.ai"


# ── the recording ingress ─────────────────────────────────────────────────────


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.status_code = 200
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _RecordingIngress:
    """A poster that accepts everything and remembers every byte it was handed.

    Accepting (rather than refusing) is deliberate: a refusing fake would make a
    "nothing was delivered" assertion pass for the wrong reason. This one would
    happily ingest the leak, so the only thing that can keep it empty is a gate.
    """

    def __init__(self) -> None:
        self.requests: list[tuple[str, bytes]] = []

    def __call__(self, url: str, *, data: bytes, headers: dict[str, str], timeout: float) -> _Response:
        del timeout
        self.requests.append((url, data))
        raw = gzip.decompress(data) if headers.get("Content-Encoding") == "gzip" else data
        body = json.loads(raw.decode("utf-8"))
        return _Response(
            {
                "results": [{"event_id": env["event_id"], "status": "success"} for env in body["events"]],
            }
        )

    @property
    def transmitted(self) -> str:
        """Every byte that crossed the transport, decompressed, as one string."""
        return "".join((data.decode("utf-8") if url.endswith("/preflight/") else gzip.decompress(data).decode("utf-8")) for url, data in self.requests)


# ── fixtures: a real checkout, a real consent chain ───────────────────────────


def _write_checkout(repo_root: Path, project_uuid: str, *, sync_enabled: bool | None) -> None:
    """Write the ``.kittify/config.yaml`` a real checkout carries.

    ``sync_enabled=None`` writes **no** ``sync:`` section at all — the state of
    the five projects in the incident, which had never been opted in and so had
    no record at any level of the chain.
    """
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "project:",
        f"  uuid: {project_uuid}",
        f"  slug: {_PROJECT_SLUG}",
        "  node_id: node12345678",
        "  repo_slug: acme-holdings/engagement-assistant",
        "  build_id: 8a4a7da6-a97c-4bb4-893a-b31664abfee4",
    ]
    if sync_enabled is not None:
        lines += ["sync:", f"  enabled: {str(sync_enabled).lower()}"]
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, sync_enabled: bool | None) -> tuple[Path, str]:
    """A checkout under a fresh HOME with no machine-global consent record."""
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    home.mkdir()
    repo_root.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    project_uuid = str(uuid4())
    _write_checkout(repo_root, project_uuid, sync_enabled=sync_enabled)
    monkeypatch.chdir(repo_root)
    return repo_root, project_uuid


def _envelopes(project_uuid: str, count: int = 3) -> list[dict[str, Any]]:
    """The synthesized import stream, carrying the engagement name verbatim.

    Shaped like ``synthesize._envelope``'s output: a top-level ``project_uuid``
    (one of the three identity sites) plus the mission slug in the payload.
    """
    return [
        # canonical-event-exempt(exception-flow): mirrors synthesize._envelope's legacy import-stream shape; no Payload model exists
        {
            "event_id": f"01JQIMPORT{index:012d}",
            "event_type": "WPStatusChanged",
            "project_uuid": project_uuid,
            "project_slug": _PROJECT_SLUG,
            "mission_slug": _ENGAGEMENT,
            "payload": {"mission_slug": _ENGAGEMENT, "wp_id": f"WP{index:02d}", "to_lane": "done"},
        }
        for index in range(count)
    ]


def _receiver(ingress: _RecordingIngress) -> TeamspaceReceiver:
    return TeamspaceReceiver(resolved_server_url=_SERVER, auth_token="secret-token", poster=ingress)


def _history_authority(
    project_uuid: str,
    envelopes: list[dict[str, Any]],
) -> dict[str, object]:
    """Persist and explicitly confirm the positive-control cohort."""
    store = ProjectSyncStore(project_uuid)
    with store.unit_of_work() as unit:
        for envelope in envelopes:
            assignment = allocate_capture_sequence(unit)
            unit.execute(
                "INSERT INTO journal_entries (entry_id, project_uuid, epoch_id, capture_sequence, payload_json) VALUES (?, ?, ?, ?, ?)",
                (
                    envelope["event_id"],
                    project_uuid,
                    assignment.epoch_id,
                    assignment.capture_sequence,
                    json.dumps(envelope, sort_keys=True, separators=(",", ":")),
                ),
            )
    record_project_opt_in(project_uuid, actor="test:positive-control")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, ?, 'account-1', 'teamspace-1', 1, 'admitted', '1', "
            "'private-teamspace:teamspace-1')",
            (project_uuid, _SERVER),
        )
    context = store.create_context()
    capability = confirm_history_disclosure(
        store,
        preview_sealed_history(store),
        actor="test:positive-control",
        idempotency_key="consent-suite-positive",
        context=context,
    )
    audience = context.target_audience
    assert audience is not None
    identity = TargetIdentity(
        target_identity=audience.target_identity,
        account_identity=audience.account_identity,
        private_teamspace_id=audience.private_teamspace_id,
        project_uuid=audience.project_uuid,
        configuration_generation=audience.configuration_generation,
    )
    target = DeliveryTarget(
        target_id=compute_target_id(
            target_identity=identity.target_identity,
            account_identity=identity.account_identity,
            private_teamspace_id=identity.private_teamspace_id,
            project_uuid=identity.project_uuid,
            configuration_generation=identity.configuration_generation,
        ),
        identity=identity,
        admission_state=AdmissionState.ADMITTED,
        admission_generation=1,
        binding_audience="private-teamspace:teamspace-1",
        last_error_category=None,
    )
    return {
        "project_context": context,
        "target": target,
        "history_capability": capability,
    }


# ── the leak ──────────────────────────────────────────────────────────────────


def test_import_history_makes_no_request_for_a_project_with_no_consent_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A never-opted-in project's history must not reach the wire (FR-028, NFR-001).

    The incident's exact state: a checkout with a valid identity and **no**
    consent record at any level. Absence is not consent (FR-002).
    """
    repo_root, project_uuid = _checkout(tmp_path, monkeypatch, sync_enabled=None)
    ingress = _RecordingIngress()

    report = run_import_upload(
        _envelopes(project_uuid),
        receiver=_receiver(ingress),
        server_url=_SERVER,
        auth_token="secret-token",
        poster=ingress,
        checkout_root=repo_root,
    )

    assert ingress.requests == [], (
        f"import-history transmitted {len(ingress.requests)} request(s) for a project with no consent record; URLs: {[url for url, _ in ingress.requests]}"
    )
    assert _ENGAGEMENT not in ingress.transmitted, "the client engagement name reached the transport for a never-opted-in project"
    assert not report.ok, "a refused import must not report a clean run"
    assert any(_PROJECT_SLUG in sample or project_uuid in sample for sample in report.rejected_samples), (
        f"the refusal must name the project it refused; samples were {report.rejected_samples}"
    )


def test_import_history_makes_no_request_when_the_project_config_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A committed, reviewable ``sync.enabled: false`` must stop the import (FR-019)."""
    repo_root, project_uuid = _checkout(tmp_path, monkeypatch, sync_enabled=False)
    ingress = _RecordingIngress()

    run_import_upload(
        _envelopes(project_uuid),
        receiver=_receiver(ingress),
        server_url=_SERVER,
        auth_token="secret-token",
        poster=ingress,
        checkout_root=repo_root,
    )

    assert ingress.requests == [], "an explicit project-local refusal must stop the import"
    assert _ENGAGEMENT not in ingress.transmitted


def test_upload_envelopes_makes_no_request_for_a_project_with_no_consent_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The preflight-free entry point is gated too — both are public (``__init__``)."""
    repo_root, project_uuid = _checkout(tmp_path, monkeypatch, sync_enabled=None)
    ingress = _RecordingIngress()

    upload_envelopes(
        _envelopes(project_uuid),
        receiver=_receiver(ingress),
        checkout_root=repo_root,
    )

    assert ingress.requests == [], "upload_envelopes reached the wire without a consent answer"
    assert _ENGAGEMENT not in ingress.transmitted


def test_the_preflight_sink_is_gated_not_only_the_delivery_sink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``run_server_preflight`` POSTs the whole stream *before* ``_deliver_chunks``.

    Placing the gate at the ``receiver.deliver`` call alone would leave this
    sink open, and it carries the same envelopes. Pinned separately so a fix
    that only guards the delivery call cannot pass.
    """
    repo_root, project_uuid = _checkout(tmp_path, monkeypatch, sync_enabled=None)
    ingress = _RecordingIngress()

    run_import_upload(
        _envelopes(project_uuid),
        receiver=_receiver(ingress),
        server_url=_SERVER,
        auth_token="secret-token",
        poster=ingress,
        checkout_root=repo_root,
        chunk_size=1,
    )

    preflight_calls = [url for url, _ in ingress.requests if url.endswith("/preflight/")]
    assert preflight_calls == [], f"the preflight sink transmitted {len(preflight_calls)} request(s)"


# ── the positive control ──────────────────────────────────────────────────────


def test_import_history_transmits_for_a_consented_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """POSITIVE CONTROL: with consent recorded, the same harness *does* transmit.

    Without this, every refusal above would be satisfied by a harness that
    cannot reach the transport at all — five apparent successes proving nothing.
    This test must pass on the pre-fix tree and on the post-fix tree alike.
    """
    repo_root, project_uuid = _checkout(tmp_path, monkeypatch, sync_enabled=True)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    ingress = _RecordingIngress()
    envelopes = _envelopes(project_uuid)

    report = run_import_upload(
        envelopes,
        receiver=_receiver(ingress),
        server_url=_SERVER,
        auth_token="secret-token",
        poster=ingress,
        checkout_root=repo_root,
        **_history_authority(project_uuid, envelopes),
    )

    assert ingress.requests, f"the harness must be able to transmit, or the refusals prove nothing; report={report}"
    assert _ENGAGEMENT in ingress.transmitted, "the consented project's engagement name must reach the wire"
    assert report.ok, f"a consented import must run clean; samples: {report.rejected_samples}"
    assert report.success == 3
