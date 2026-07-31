"""FR-030: the widen-mode SaaS client must not ship a non-consenting project (#3030).

``saas_client/client.py`` had no consent consumer anywhere in the package — a
grep for the consent chain returned zero hits, exactly as it did for
``tracker/``. Both packages touch no spec-kitty store at all, which is why a
dossier whose unit of reasoning was *the store* could not see either of them.

**Where the leak lives is the point.** One POST carries only ``invited_user_ids``.
The other four calls are GETs that put ``mission_id`` — documented "ULID **or
slug**" — in the **URL path**, and in this product a mission slug is a client
engagement name. A gate written against request bodies would pass every test and
close nothing, so every assertion here searches the recorded *URLs* as well as
the bodies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from specify_cli.saas_client import SaasClient, SaasClientError
from specify_cli.saas_client.errors import SaasConsentError

pytestmark = [pytest.mark.fast, pytest.mark.regression]


ENGAGEMENT = "acme-holdings-carve-out"
MISSION_SLUG = f"{ENGAGEMENT}-01KZTESTULID0001"
DECISION_ID = "01KZDECISIONULID00000001"
TEAM_SLUG = "acme-team"


# ---------------------------------------------------------------------------
# Recording transport
# ---------------------------------------------------------------------------


class RecordingResponse:
    status_code = 200
    is_success = True
    text = "{}"

    def json(self) -> dict[str, Any]:
        return {}


class RecordingHttp:
    """An ``httpx.Client`` stand-in that records instead of sending.

    Injected through ``SaasClient(_http=...)``, i.e. exactly the seam the
    package documents for tests, so the gate is proven at the real transport
    boundary rather than at a wrapper invented for the test.
    """

    def __init__(self, sink: list[dict[str, Any]]) -> None:
        self._sink = sink

    def get(self, url: str, *, timeout: float | None = None) -> RecordingResponse:
        self._sink.append({"method": "GET", "url": url, "json": None})
        return RecordingResponse()

    def post(
        self, url: str, *, json: Any = None, timeout: float | None = None
    ) -> RecordingResponse:
        self._sink.append({"method": "POST", "url": url, "json": json})
        return RecordingResponse()


def transmitted_text(sink: list[dict[str, Any]]) -> str:
    """Every byte the transport was asked to send — URLs included."""
    return json.dumps(sink, default=str, sort_keys=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def write_project_config(repo_root: Path, *, sync_enabled: bool | None = None) -> None:
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "project:",
        f"  uuid: {uuid4()}",
        "  slug: acme-holdings",
        "  node_id: node12345678",
        "  repo_slug: acme-holdings/acme-holdings",
        "  build_id: 8a4a7da6-a97c-4bb4-893a-b31664abfee4",
    ]
    if sync_enabled is not None:
        lines += ["sync:", f"  enabled: {str(sync_enabled).lower()}"]
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def sink() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def isolated_machine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    repo_root = tmp_path / "acme-holdings"
    home.mkdir()
    repo_root.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.chdir(repo_root)
    return repo_root


def make_client(
    sink: list[dict[str, Any]], project_root: Path | None
) -> SaasClient:
    """A fully authenticated client — so a refusal is attributable to consent."""
    return SaasClient(
        base_url="https://saas.example.invalid",
        token="valid-token",
        team_slug=TEAM_SLUG,
        _http=RecordingHttp(sink),
        project_root=project_root,
    )


def refusal_of(call: Any, client: SaasClient) -> SaasClientError | None:
    """Run *call*, returning its refusal instead of raising.

    Lets every leak test assert **on the transmitted bytes first**. With
    ``pytest.raises`` wrapping the call, stripping the gate reds with "DID NOT
    RAISE" — a fact about control flow rather than about confidentiality. The
    failure a reader must see is the engagement name sitting in a recorded URL.
    """
    try:
        call(client)
    except SaasClientError as exc:
        return exc
    return None


#: One invocation per public endpoint. Held complete by
#: :func:`test_endpoint_coverage_is_exhaustive`.
ENDPOINT_CALLS: dict[str, Any] = {
    "get_audience_default": lambda c: c.get_audience_default(MISSION_SLUG),
    "post_widen": lambda c: c.post_widen(DECISION_ID, [1, 2]),
    "get_team_integrations": lambda c: c.get_team_integrations(TEAM_SLUG),
    "fetch_discussion": lambda c: c.fetch_discussion(DECISION_ID),
    # ``health_probe`` swallows SaasClientError by contract and returns a bool,
    # so it is exercised separately in ``test_health_probe_refuses_quietly``.
    "health_probe": lambda c: c.health_probe(),
}


# ---------------------------------------------------------------------------
# Positive control
# ---------------------------------------------------------------------------


def test_consenting_project_transmits_the_engagement_name_in_the_url(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """POSITIVE CONTROL, and it also *demonstrates* the leak's shape.

    Must pass before and after the fix. It proves the recording transport is
    wired in, and it shows the engagement name sitting in the request path —
    which is why the refusal assertions below search URLs and not just bodies.
    """
    write_project_config(isolated_machine, sync_enabled=True)

    make_client(sink, isolated_machine).get_audience_default(MISSION_SLUG)

    # Method and body together, not a count: the leak's shape is "the engagement
    # name rides in the URL of a GET", and a single request is consistent with the
    # opposite shape too. One POST carrying the slug in a JSON body is the same
    # count, and it would make the URL-searching refusal assertions below blind to
    # the very egress they are supposed to catch.
    assert [(r["method"], r["json"]) for r in sink] == [("GET", None)], (
        f"a consenting project must transmit exactly one GET with no body; recorded {sink!r}"
    )
    assert MISSION_SLUG in sink[0]["url"], (
        "the control must carry the engagement name in the URL path, or the "
        "absence assertions in this file prove nothing"
    )


# ---------------------------------------------------------------------------
# The leak
# ---------------------------------------------------------------------------


def test_unconsented_project_puts_no_engagement_name_on_the_wire(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """THE LEAK: a project with no consent record must ship nothing."""
    write_project_config(isolated_machine, sync_enabled=None)

    refusal = refusal_of(
        ENDPOINT_CALLS["get_audience_default"], make_client(sink, isolated_machine)
    )

    assert MISSION_SLUG not in transmitted_text(sink), (
        "the engagement name reached the transport, in the URL path: "
        f"{[r['url'] for r in sink]!r}"
    )
    assert ENGAGEMENT not in transmitted_text(sink)
    assert sink == [], f"nothing may reach the transport; recorded {sink!r}"
    assert isinstance(refusal, SaasConsentError), (
        f"the call must refuse with a consent error; got {refusal!r}"
    )


def test_machine_global_arming_is_not_a_grant(
    isolated_machine: Path, sink: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """``SPEC_KITTY_ENABLE_SAAS_SYNC`` is the incident's own mechanism, not consent."""
    write_project_config(isolated_machine, sync_enabled=None)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    refusal = refusal_of(
        ENDPOINT_CALLS["get_audience_default"], make_client(sink, isolated_machine)
    )

    assert MISSION_SLUG not in transmitted_text(sink), (
        f"machine-global arming carried the engagement name off the machine: {sink!r}"
    )
    assert sink == []
    assert isinstance(refusal, SaasConsentError)


def test_project_local_refusal_is_honoured(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    write_project_config(isolated_machine, sync_enabled=False)

    refusal = refusal_of(
        ENDPOINT_CALLS["get_audience_default"], make_client(sink, isolated_machine)
    )

    assert MISSION_SLUG not in transmitted_text(sink), (
        f"a committed refusal was overridden and the engagement name shipped: {sink!r}"
    )
    assert sink == []
    assert isinstance(refusal, SaasConsentError)


def test_undetermined_project_denies(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """A client with no project attribution refuses (FR-003 / NFR-001)."""
    write_project_config(isolated_machine, sync_enabled=True)

    refusal = refusal_of(ENDPOINT_CALLS["get_audience_default"], make_client(sink, None))

    assert MISSION_SLUG not in transmitted_text(sink), (
        "an unattributed transport shipped the engagement name under a nearby "
        f"project's consent: {sink!r}"
    )
    assert sink == [], (
        "a transport with no project attribution must refuse even when a "
        "consenting project happens to exist nearby"
    )
    assert refusal is not None
    assert "could not be determined" in str(refusal)


@pytest.mark.parametrize("endpoint", sorted(ENDPOINT_CALLS))
def test_every_endpoint_refuses_without_consent(
    endpoint: str, isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """No endpoint may transmit for a project that has not consented.

    Including ``health_probe``: it is gated at the shared ``_get`` chokepoint
    with no carve-out. An exemption parameter on a chokepoint is a bypass switch
    that the next endpoint author will find, and refusing the probe has the right
    downstream effect — the widen prereq check reports the feature unavailable,
    so a non-consenting project is never offered a flow that would then send its
    mission identifiers.
    """
    write_project_config(isolated_machine, sync_enabled=None)
    client = make_client(sink, isolated_machine)

    # ``health_probe`` answers with a bool by contract; every other endpoint
    # refuses by raising. Both are captured without asserting, so the byte-level
    # assertions below are what red when the gate is stripped.
    is_probe = endpoint == "health_probe"
    probe_result = ENDPOINT_CALLS[endpoint](client) if is_probe else None
    refusal = None if is_probe else refusal_of(ENDPOINT_CALLS[endpoint], client)

    assert ENGAGEMENT not in transmitted_text(sink), (
        f"{endpoint} put the engagement name on the wire without consent: {sink!r}"
    )
    assert sink == [], f"{endpoint} transmitted without consent: {sink!r}"
    if is_probe:
        assert probe_result is False, "health_probe must refuse by returning False"
    else:
        assert refusal is not None, f"{endpoint} did not refuse"


def test_every_production_construction_site_attributes_its_project() -> None:
    """The attribution precondition, made executable.

    Every production site reaches the client through ``from_env``, which threads
    its ``repo_root`` onto the client as the project whose consent gates the send.
    A ``from_env()`` with no root produces a client that refuses everything, so
    the failure mode is loud rather than leaky — but it is still a broken caller,
    and a direct ``SaasClient(...)`` without ``project_root`` is the same.

    Scans ``src/`` for both shapes. It cannot prove the root is the *right* one;
    that is enumerated per site in ``saas_client/egress_consent.py``, including
    the one site (``decision widen``) where root and subject can legitimately
    diverge and why that is bounded today.
    """
    import ast

    src = Path(__file__).resolve().parents[3] / "src" / "specify_cli"
    assert src.is_dir(), f"source tree not found at {src} — path regression?"

    unattributed: list[str] = []
    scanned = 0
    for path in sorted(src.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # ``SaasClient(...)`` or ``SaasClient.from_env(...)``
            is_direct = isinstance(func, ast.Name) and func.id == "SaasClient"
            is_from_env = (
                isinstance(func, ast.Attribute)
                and func.attr == "from_env"
                and isinstance(func.value, ast.Name)
                and func.value.id == "SaasClient"
            )
            if not (is_direct or is_from_env):
                continue
            scanned += 1
            if is_from_env:
                attributed = bool(node.args) or any(
                    kw.arg == "repo_root" for kw in node.keywords
                )
            else:
                attributed = any(kw.arg == "project_root" for kw in node.keywords)
            if not attributed:
                unattributed.append(f"{path.relative_to(src.parent.parent)}:{node.lineno}")

    assert scanned, (
        "no SaasClient construction found in src/ — the scan is vacuous, which "
        "would make this guard decoration"
    )
    assert not unattributed, (
        "SaasClient built without a project attribution at:\n  "
        + "\n  ".join(unattributed)
        + "\n\nPass the root of the project that OWNS the mission or decision "
        "record the request carries (#3030 FR-030) — `from_env(repo_root=...)`, or "
        "`project_root=` on a direct construction. See "
        "saas_client/egress_consent.py for the precondition and what falsifies it."
    )


def test_no_attribution_is_a_refusal_at_the_gate_itself() -> None:
    """The invariant, asserted below the transport and below every fixture.

    This directory's autouse conftest can inject a consenting project into a
    client built without one; calling the gate directly pins "no attribution
    refuses" where no fixture can arrange the answer.
    """
    from specify_cli.saas_client.egress_consent import project_egress_refusal

    refusal = project_egress_refusal(None)

    assert refusal is not None, "an unattributed send must never be permitted"
    assert "could not be determined" in refusal


def test_endpoint_coverage_is_exhaustive() -> None:
    """The parametrization must name every public endpoint on the client.

    ``has_token`` and ``from_env`` are excluded by name: the first is a property
    over local state and the second is a constructor. Everything else on the
    public surface is a sender and must be proven gated.
    """
    not_a_sender = {"has_token", "from_env"}
    public = {
        name
        for name, obj in vars(SaasClient).items()
        if not name.startswith("_") and (callable(obj) or isinstance(obj, property))
    } - not_a_sender
    missing = public - set(ENDPOINT_CALLS)
    stale = set(ENDPOINT_CALLS) - public
    assert not missing, (
        f"public SaasClient endpoints with no consent-gate test: {sorted(missing)}"
    )
    assert not stale, (
        f"ENDPOINT_CALLS names methods that no longer exist: {sorted(stale)}"
    )


def test_health_probe_refuses_quietly_and_sends_nothing(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """``health_probe`` keeps its never-raises contract, and still sends nothing.

    Its documented contract is "returns ``False`` on any error — this method
    never raises", and the widen prereq path depends on that. The refusal must
    therefore arrive as ``False``, not as an exception that would escape
    ``_check_health``.
    """
    write_project_config(isolated_machine, sync_enabled=None)

    probe_result = make_client(sink, isolated_machine).health_probe()

    assert sink == [], f"health_probe reached the transport without consent: {sink!r}"
    assert probe_result is False


# ---------------------------------------------------------------------------
# The construction site — a gate nobody wires up is not a gate
# ---------------------------------------------------------------------------


def test_from_env_carries_the_project_it_was_given(
    isolated_machine: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``from_env(repo_root)`` must thread that root onto the client.

    Every production construction site goes through ``from_env``. If the root
    stopped being carried, every one of them would silently fall back to the
    refusing default and the feature would break loudly — but if it were carried
    from somewhere *other* than the caller's repo_root, the gate would answer for
    the wrong project and fail silently. This pins the direction that fails
    silently.
    """
    write_project_config(isolated_machine, sync_enabled=True)
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.example.invalid")
    monkeypatch.setenv("SPEC_KITTY_SAAS_TOKEN", "valid-token")

    client = SaasClient.from_env(repo_root=isolated_machine)

    assert client._project_root == isolated_machine


def test_from_env_without_a_repo_root_produces_a_refusing_client(
    isolated_machine: Path, sink: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """No repo_root means no project whose consent could be resolved — so deny."""
    write_project_config(isolated_machine, sync_enabled=True)
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.example.invalid")
    monkeypatch.setenv("SPEC_KITTY_SAAS_TOKEN", "valid-token")
    # Supplied so the call reaches the consent gate rather than being turned back
    # earlier by ``_resolve_team_slug`` — the refusal under test must be the
    # consent one, not a missing-team one that would mask it.
    monkeypatch.setenv("SPEC_KITTY_TEAM_SLUG", TEAM_SLUG)

    client = SaasClient.from_env()
    client._http = RecordingHttp(sink)  # type: ignore[assignment]

    refusal = refusal_of(ENDPOINT_CALLS["get_audience_default"], client)

    assert MISSION_SLUG not in transmitted_text(sink), (
        f"a client built without a repo_root shipped the engagement name: {sink!r}"
    )
    assert sink == []
    assert isinstance(refusal, SaasConsentError)


def test_consent_refusal_is_suppressible_like_any_saas_failure(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """``SaasConsentError`` must remain a ``SaasClientError``.

    The widen prereq probe, the interview helpers and the audience resolver all
    catch ``SaasClientError`` to degrade locally (C-007). A refusal that escaped
    those handlers would turn a confidentiality control into a crash in the
    middle of an interview — the fix would be worse than the defect for anyone
    who had simply not opted in.
    """
    write_project_config(isolated_machine, sync_enabled=None)
    client = make_client(sink, isolated_machine)

    assert issubclass(SaasConsentError, SaasClientError)

    refusal = refusal_of(ENDPOINT_CALLS["fetch_discussion"], client)

    assert sink == [], f"fetch_discussion transmitted without consent: {sink!r}"
    assert isinstance(refusal, SaasConsentError), (
        "the refusal must be catchable as SaasClientError by the existing "
        f"local-first handlers; got {refusal!r}"
    )
