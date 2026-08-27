"""FR-029 (#3030) at the transport, re-homed for the single-channel gate (#5, #121).

``tests/sync/tracker/test_saas_client_consent_gate_3030.py`` (903 lines, deleted whole with
``tests/sync/tracker/`` in issue #5/#114) asserted — at the transport, on the recorded bytes,
never on a verdict alone — that a non-consenting project's ``mission_slug`` (a client
engagement name in this product) never reaches ``SaaSTrackerClient``'s wire. That assertion
style is what this file re-homes.

Almost none of the *scenarios* survive verbatim: that file's model was "hosted egress needs a
per-project opt-in, and absence/undetermined/machine-global-arming all refuse". Issue #5
retired Channel 1 (hosted-sync consent) along with the sync transport it lived in, and
``tracker/egress_verdict.py`` now makes ``HOSTED_SERVICE`` **narrowing-only**: absence,
"undetermined", and any machine-global toggle all fall through to *permit* — the request rides
the operator's authenticated SaaS session, and team-side admission is decided server-side, not
here. Only a committed ``tracker.egress: refused`` (or an illegal/unreadable value) still
refuses. That polarity table is pinned at the verdict-function level in
``tests/tracker/test_egress_verdict.py`` and, exhaustively, by the architectural G7 guard in
``tests/architectural/test_tracker_egress_guards_3108.py``.

What neither of those pins does — and what is re-homed here — is prove it **at the transport**:
that ``SaaSTrackerClient._request``'s consent check actually runs before ``httpx.Client`` is
ever constructed, so a refused project's engagement name never touches the wire. A verdict
object being ``refused=True`` is not the same fact as zero bytes leaving the machine; the
deleted file's own docstring made exactly this point, and it is why this file keeps the
recording-transport technique rather than asserting on ``verdict.refused`` a second time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.tracker.config import TrackerProjectConfig, save_tracker_config
from specify_cli.tracker.saas_client import (
    SaaSTrackerClient,
    SaaSTrackerClientError,
    TrackerEgressRefusedError,
)

pytestmark = pytest.mark.fast

ENGAGEMENT = "acme-holdings-carve-out"
MISSION_SLUG = f"{ENGAGEMENT}-01KZTESTULID0001"
PROJECT_SLUG = "acme-holdings"
MISSION_ID = "01KZTESTULID000000000001"
ISSUE_TITLE = "ACME Holdings carve-out: draft the disclosure schedule"


class RecordingResponse:
    """Minimal ``httpx.Response`` stand-in -- 200 with an empty JSON object."""

    status_code = 200

    def json(self) -> dict[str, Any]:
        return {}


class RecordingClient:
    """Captures every request instead of sending it.

    Records the whole request -- method, URL, JSON body, and query params -- because the
    original incident this guards proved a leak can hide in the URL of a GET just as easily
    as in a POST body.
    """

    def __init__(self, sink: list[dict[str, Any]], **_kwargs: Any) -> None:
        self._sink = sink

    def __enter__(self) -> RecordingClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        headers: Any = None,
        params: Any = None,
    ) -> RecordingResponse:
        self._sink.append({"method": method, "url": url, "json": json, "params": dict(params or {})})
        return RecordingResponse()


def transmitted_text(sink: list[dict[str, Any]]) -> str:
    """Every byte the transport was asked to send, as one searchable string."""
    return json.dumps(sink, default=str, sort_keys=True)


@pytest.fixture
def sink(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Install the recording transport in place of ``httpx.Client``."""
    recorded: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "specify_cli.tracker.saas_client.httpx.Client",
        lambda **kwargs: RecordingClient(recorded, **kwargs),
    )
    return recorded


def bind_call(client: SaaSTrackerClient) -> dict[str, Any]:
    """The POST that fires non-interactively during mission creation."""
    return client.bind_mission_origin(
        "linear",
        PROJECT_SLUG,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        external_issue_id="issue-456",
        external_issue_key="ENG-99",
        external_issue_url="https://linear.app/acme/ENG-99",
        title=ISSUE_TITLE,
    )


def pull_call(client: SaaSTrackerClient) -> dict[str, Any]:
    """A read endpoint, to prove the gate is transport-wide, not one write path."""
    return client.pull("linear", PROJECT_SLUG)


def refusal_of(call: Any, client: SaaSTrackerClient) -> SaaSTrackerClientError | None:
    """Run *call*, returning its refusal instead of raising."""
    try:
        call(client)
    except SaaSTrackerClientError as exc:
        return exc
    return None


def test_permitted_project_transmits_the_engagement_name(tmp_path: Path, sink: list[dict[str, Any]]) -> None:
    """POSITIVE CONTROL: a project with ``tracker.egress: permitted`` ships, and the harness
    sees it. Proves the recording transport is wired in and really captures the disclosing
    value, so the refusal test below is evidence of a gate rather than of a broken fixture.
    """
    save_tracker_config(tmp_path, TrackerProjectConfig(provider="linear", egress="permitted"))

    bind_call(SaaSTrackerClient(project_root=tmp_path))

    assert [record["method"] for record in sink] == ["POST"]
    assert MISSION_SLUG in transmitted_text(sink), "the control must carry the engagement name, or the absence assertion below proves nothing"


def test_absent_egress_key_also_transmits(tmp_path: Path, sink: list[dict[str, Any]]) -> None:
    """Narrowing-only, the other half: no committed key at all still ships (#5's design --
    absence falls through to the authenticated-session default, it does not refuse).
    """
    bind_call(SaaSTrackerClient(project_root=tmp_path))

    assert MISSION_SLUG in transmitted_text(sink)


def test_refused_project_transmits_no_engagement_name(tmp_path: Path, sink: list[dict[str, Any]]) -> None:
    """THE GATE: a committed ``tracker.egress: refused`` must ship nothing.

    Asserted on the transmitted bytes, not on the verdict object -- a gate that computes the
    right verdict while ``httpx.Client`` still fires is not a fix.
    """
    save_tracker_config(tmp_path, TrackerProjectConfig(provider="linear", egress="refused"))

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=tmp_path))

    body = transmitted_text(sink)
    assert ENGAGEMENT not in body, f"the client engagement name reached the transport: {sink!r}"
    assert MISSION_SLUG not in body, f"the mission slug reached the transport: {sink!r}"
    assert sink == [], f"a refused project must never reach the transport at all; recorded {sink!r}"
    assert isinstance(refusal, TrackerEgressRefusedError)
    assert refusal.error_code == "project_consent_denied"


def test_refused_project_refuses_every_endpoint_kind(tmp_path: Path, sink: list[dict[str, Any]]) -> None:
    """The gate lives at the one ``_request``/``_request_with_retry`` chokepoint, so it must
    hold for a GET-shaped read (``pull``) exactly as it does for the authoritative bind POST --
    not just the endpoint the original incident happened to name.
    """
    save_tracker_config(tmp_path, TrackerProjectConfig(provider="linear", egress="refused"))

    refusal = refusal_of(pull_call, SaaSTrackerClient(project_root=tmp_path))

    assert sink == [], f"pull() must refuse before any request is issued; recorded {sink!r}"
    assert isinstance(refusal, TrackerEgressRefusedError)


def test_illegal_egress_value_fails_closed_at_the_transport(tmp_path: Path, sink: list[dict[str, Any]]) -> None:
    """An illegal/unreadable ``tracker.egress`` value is a fault, and a fault still refuses
    (NFR-001: inability to determine consent is never consent) -- pinned here at the transport,
    not only as a ``verdict.refused`` boolean.
    """
    save_tracker_config(tmp_path, TrackerProjectConfig(provider="linear", egress="sometimes"))

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=tmp_path))

    assert sink == [], f"a fault verdict must never reach the transport; recorded {sink!r}"
    assert isinstance(refusal, TrackerEgressRefusedError)
