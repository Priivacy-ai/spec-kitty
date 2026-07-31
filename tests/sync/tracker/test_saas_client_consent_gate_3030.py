"""FR-029: the tracker SaaS transport must not ship a non-consenting project (#3030).

The 2026-07-27 incident delivered 1,322 events belonging to five never-opted-in
projects. In this product a ``mission_slug`` **is a client engagement name**, so
shipping one is itself the confidentiality breach rather than incidental
metadata.

``tracker/saas_client.py`` was gated on authentication and ``X-Team-Slug`` only;
``project_uuid`` appeared nowhere in the module. Ten endpoints, three of them
POSTs carrying ``mission_slug`` / ``project_slug`` / ``mission_id`` / the external
issue ``title``.

**Everything here asserts at the transport.** The recorded requests are searched
for the engagement name — in the body *and* in the URL — rather than checking
that some boolean flipped. A gate that returns the right verdict while the bytes
still leave the machine is not a fix, and this mission has already found a pin
that passed with the invariant stripped entirely.

Two properties every refusal test relies on and one of them states outright:

* **Auth is satisfied throughout.** The token and team-slug bridges are stubbed
  to succeed, so a refusal can only come from the consent gate. The incident was
  carried by a correctly authenticated client with a correct team header.
* **A positive control transmits.** Without one, "no requests recorded" is
  equally consistent with a harness that never wired the transport at all.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from specify_cli.tracker.saas_client import SaaSTrackerClient, SaaSTrackerClientError

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# The disclosing values. Realistic, and legible in a diff: a reader must be able
# to see at a glance that these are a client's name, not test noise.
# ---------------------------------------------------------------------------

ENGAGEMENT = "acme-holdings-carve-out"
MISSION_SLUG = f"{ENGAGEMENT}-01KZTESTULID0001"
PROJECT_SLUG = "acme-holdings"
MISSION_ID = "01KZTESTULID000000000001"
ISSUE_TITLE = "ACME Holdings carve-out: draft the disclosure schedule"


# ---------------------------------------------------------------------------
# Recording transport
# ---------------------------------------------------------------------------


class RecordingResponse:
    """Minimal ``httpx.Response`` stand-in — 200 with an empty JSON object."""

    status_code = 200

    def json(self) -> dict[str, Any]:
        return {}


class RecordingClient:
    """Captures every request instead of sending it.

    Records the *whole* request — method, URL, JSON body, query params and
    headers — because E3's sibling defect proved a gate can be body-shaped and
    still leak through the URL. :func:`transmitted_text` flattens all of it so a
    test can assert on the bytes rather than on a field it remembered to check.
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
        self._sink.append(
            {
                "method": method,
                "url": url,
                "json": json,
                "headers": dict(headers or {}),
                "params": dict(params or {}),
            }
        )
        return RecordingResponse()


def transmitted_text(sink: list[dict[str, Any]]) -> str:
    """Every byte the transport was asked to send, as one searchable string."""
    return json.dumps(sink, default=str, sort_keys=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def write_project_config(
    repo_root: Path,
    *,
    sync_enabled: bool | None = None,
    with_tracker: bool = True,
) -> None:
    """Write a ``.kittify/config.yaml`` with a complete project identity.

    ``sync_enabled=None`` is the state of every project on a machine where nobody
    ever ran ``sync opt-in`` for it — the overwhelmingly common case, and the one
    the incident turned on.
    """
    config_dir = repo_root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "project:",
        f"  uuid: {uuid4()}",
        f"  slug: {PROJECT_SLUG}",
        "  node_id: node12345678",
        f"  repo_slug: acme-holdings/{PROJECT_SLUG}",
        "  build_id: 8a4a7da6-a97c-4bb4-893a-b31664abfee4",
    ]
    if with_tracker:
        lines += [
            "tracker:",
            "  provider: linear",
            f"  project_slug: {PROJECT_SLUG}",
        ]
    if sync_enabled is not None:
        lines += ["sync:", f"  enabled: {str(sync_enabled).lower()}"]
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def sink(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Install the recording transport and satisfy auth.

    Auth is stubbed to *succeed* on purpose: it makes every refusal below
    attributable to consent alone, and it reproduces the incident's actual
    conditions (a valid token and a valid team).
    """
    recorded: list[dict[str, Any]] = []

    monkeypatch.setattr(
        "specify_cli.tracker.saas_client.httpx.Client",
        lambda **kwargs: RecordingClient(recorded, **kwargs),
    )
    monkeypatch.setattr(
        "specify_cli.tracker.saas_client._fetch_access_token_sync",
        lambda: "valid-token",
    )
    monkeypatch.setattr(
        "specify_cli.tracker.saas_client._current_team_slug_sync",
        lambda: "acme-team",
    )
    return recorded


@pytest.fixture
def isolated_machine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A checkout under a fresh HOME with no machine-global sync config at all."""
    home = tmp_path / "home"
    repo_root = tmp_path / "acme-holdings"
    home.mkdir()
    repo_root.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.chdir(repo_root)
    return repo_root


def refusal_of(call: Any, client: SaaSTrackerClient) -> SaaSTrackerClientError | None:
    """Run *call*, returning its refusal instead of raising.

    Exists so every leak test can assert **on the transmitted bytes first** and
    on the exception second. Ordering matters more than it looks: with
    ``pytest.raises`` wrapping the call, stripping the gate reds with "DID NOT
    RAISE" — the absence of an exception, which is a fact about control flow and
    not about confidentiality. The failure a reader must see is the engagement
    name sitting in a recorded request.
    """
    try:
        call(client)
    except SaaSTrackerClientError as exc:
        return exc
    return None


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


# ---------------------------------------------------------------------------
# The positive control — without it, every red below is unfalsifiable
# ---------------------------------------------------------------------------


def test_consenting_project_still_transmits_the_engagement_name(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """POSITIVE CONTROL: a project that opted in ships, and the harness sees it.

    This test must pass both before and after the fix. It proves the recording
    transport is really wired in and really captures the disclosing value, so a
    later "engagement name absent from the transmitted bytes" assertion is
    evidence of a gate rather than evidence of a broken fixture.
    """
    write_project_config(isolated_machine, sync_enabled=True)

    bind_call(SaaSTrackerClient(project_root=isolated_machine))

    # Which request, not how many. ``bind_mission_origin`` is the authoritative
    # POST; a build in which it degenerates to a lookup and never writes still
    # records exactly one request, and ``transmitted_text`` still finds the
    # engagement name — in the lookup's URL. The count cannot tell those apart,
    # so the control would go on certifying a transport that binds nothing.
    assert [record["method"] for record in sink] == ["POST"], (
        f"consenting project must transmit the authoritative bind POST; recorded {sink!r}"
    )
    assert MISSION_SLUG in transmitted_text(sink), (
        "the control must actually carry the engagement name, or the absence "
        "assertions in this file prove nothing"
    )


# ---------------------------------------------------------------------------
# The leak
# ---------------------------------------------------------------------------


def test_unconsented_project_transmits_no_engagement_name(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """THE LEAK: a project with no consent record must ship nothing.

    Identical to the control except that no consent was ever recorded — the
    state of the five projects in the incident. Asserted on the transmitted
    bytes, not on a verdict.
    """
    write_project_config(isolated_machine, sync_enabled=None)

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=isolated_machine))

    body = transmitted_text(sink)
    assert ENGAGEMENT not in body, (
        f"the client engagement name reached the transport: {sink!r}"
    )
    assert MISSION_SLUG not in body, (
        f"the mission slug — an engagement name — reached the transport: {sink!r}"
    )
    assert ISSUE_TITLE not in body, f"the issue title reached the transport: {sink!r}"
    assert sink == [], (
        "a project that never opted in must not reach the transport at all; "
        f"recorded {sink!r}"
    )
    assert refusal is not None, "the call must refuse, not silently no-op"
    assert refusal.error_code == "project_consent_denied", (
        "a refusal must be distinguishable from an auth or transport failure, or "
        "the operator will go and check their token"
    )


def test_machine_global_arming_is_not_a_grant(
    isolated_machine: Path, sink: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The incident's own mechanism must not authorize a send.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is machine-global *arming*. One exported
    shell variable carried five never-opted-in projects along with the intended
    one; the spec states it is never a grant.
    """
    write_project_config(isolated_machine, sync_enabled=None)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=isolated_machine))

    assert ENGAGEMENT not in transmitted_text(sink), (
        f"machine-global arming carried the engagement name off the machine: {sink!r}"
    )
    assert sink == [], "machine-global arming must never stand in for project consent"
    assert refusal is not None


def test_project_local_refusal_is_honoured(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """A committed, reviewable ``sync.enabled: false`` denies."""
    write_project_config(isolated_machine, sync_enabled=False)

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=isolated_machine))

    assert ENGAGEMENT not in transmitted_text(sink), (
        f"a committed refusal was overridden and the engagement name shipped: {sink!r}"
    )
    assert sink == []
    assert refusal is not None


def test_undetermined_project_denies(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """An unresolvable project is a refusal, not a proceed (FR-003 / NFR-001).

    A client constructed without being told whose data it carries cannot resolve
    consent. This mission has found the opposite reading — undetermined treated
    as permission — independently in four places.
    """
    write_project_config(isolated_machine, sync_enabled=True)

    # ``project_root=None`` is passed *explicitly*. The autouse shim in this
    # directory's conftest injects a consenting project only when the kwarg is
    # omitted entirely — so omitting it here would quietly get that default and
    # this test would prove nothing.
    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=None))

    assert ENGAGEMENT not in transmitted_text(sink), (
        "an unattributed transport shipped the engagement name under a nearby "
        f"project's consent: {sink!r}"
    )
    assert sink == [], (
        "a transport with no project attribution must refuse even when a "
        "consenting project happens to exist nearby"
    )
    assert refusal is not None
    assert "could not be determined" in str(refusal)


def test_every_production_construction_site_attributes_its_project() -> None:
    """The attribution precondition, made executable.

    The gate resolves consent from the checkout root it is handed, so it is only
    sound while **every** construction site passes the root of the project that
    owns the record the request will carry. That condition is stated in
    ``tracker/egress_consent.py``; a prose statement alone is how this class
    regenerates, because it reads as obviously fine until someone adds the caller
    that breaks it and nothing tells them they broke it.

    This scans ``src/`` and fails on a ``SaaSTrackerClient(...)`` built without an
    explicit ``project_root``. It cannot prove the root passed is the *right* one
    — that is the reviewable part, enumerated per site in the module docstring —
    but it does make the omission a red build rather than a silent refusing
    client, and it forces a new caller to think about whose data it is sending.
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
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name != "SaaSTrackerClient":
                continue
            scanned += 1
            if not any(kw.arg == "project_root" for kw in node.keywords):
                unattributed.append(f"{path.relative_to(src.parent.parent)}:{node.lineno}")

    assert scanned, (
        "no SaaSTrackerClient construction found in src/ — the scan is vacuous, "
        "which would make this guard decoration"
    )
    assert not unattributed, (
        "SaaSTrackerClient constructed without project_root at:\n  "
        + "\n  ".join(unattributed)
        + "\n\nEvery construction site must pass the root of the project that OWNS "
        "the data the request carries (#3030 FR-029) — never the process cwd, and "
        "never another project's root. Without it the client refuses every request; "
        "with the wrong one it asks the wrong project. See "
        "tracker/egress_consent.py for the precondition and what falsifies it."
    )


def test_no_attribution_is_a_refusal_at_the_gate_itself() -> None:
    """The invariant, asserted below the transport and below every fixture.

    The transport tests above run under this directory's autouse shim, which can
    inject a project. This one calls the gate function directly, so "no project
    attribution refuses" is pinned by something no fixture can arrange.
    """
    from specify_cli.tracker.egress_consent import project_egress_refusal

    refusal = project_egress_refusal(None)

    assert refusal is not None, "an unattributed send must never be permitted"
    assert "could not be determined" in refusal


def test_a_directory_that_is_not_a_project_denies(
    tmp_path: Path, sink: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A path with no project identity is unidentifiable, so never consentable."""
    home = tmp_path / "home"
    stray = tmp_path / "not-a-spec-kitty-project"
    home.mkdir()
    stray.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=stray))

    assert ENGAGEMENT not in transmitted_text(sink), (
        f"an unidentifiable checkout shipped the engagement name: {sink!r}"
    )
    assert sink == []
    assert refusal is not None


# ---------------------------------------------------------------------------
# Every endpoint, not just the three that were reported
# ---------------------------------------------------------------------------

_IDENTITY_PAYLOAD: dict[str, Any] = {
    "uuid": "8a4a7da6-a97c-4bb4-893a-b31664abfee4",
    "slug": PROJECT_SLUG,
    "node_id": "node12345678",
    "repo_slug": f"acme-holdings/{PROJECT_SLUG}",
    "build_id": "8a4a7da6-a97c-4bb4-893a-b31664abfee4",
}

#: One invocation per public endpoint on ``SaaSTrackerClient``. Kept complete by
#: :func:`test_endpoint_coverage_is_exhaustive` below, so a future endpoint
#: cannot be added without either being gated or reddening the suite.
ENDPOINT_CALLS: dict[str, Any] = {
    "pull": lambda c: c.pull("linear", PROJECT_SLUG),
    "status": lambda c: c.status("linear", PROJECT_SLUG),
    "mappings": lambda c: c.mappings("linear", PROJECT_SLUG),
    "search_issues": lambda c: c.search_issues("linear", PROJECT_SLUG, query_text=ENGAGEMENT),
    "list_tickets": lambda c: c.list_tickets("linear", PROJECT_SLUG),
    "bind_mission_origin": bind_call,
    "resources": lambda c: c.resources("linear"),
    "bind_resolve": lambda c: c.bind_resolve("linear", dict(_IDENTITY_PAYLOAD)),
    "bind_confirm": lambda c: c.bind_confirm("linear", "tok", dict(_IDENTITY_PAYLOAD)),
    "bind_validate": lambda c: c.bind_validate("linear", "ref", dict(_IDENTITY_PAYLOAD)),
    "push": lambda c: c.push("linear", PROJECT_SLUG, [{"title": ISSUE_TITLE}]),
    "run": lambda c: c.run("linear", PROJECT_SLUG),
}


@pytest.mark.parametrize("endpoint", sorted(ENDPOINT_CALLS))
def test_every_endpoint_refuses_without_consent(
    endpoint: str, isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """No endpoint may transmit for a project that has not consented.

    The reported instance named three POSTs. Consent is a property of the
    transport, not of the three methods someone happened to look at, so every
    endpoint is exercised — including the GETs, whose query strings carry
    ``project_slug``.
    """
    write_project_config(isolated_machine, sync_enabled=None)
    client = SaaSTrackerClient(project_root=isolated_machine)

    refusal = refusal_of(ENDPOINT_CALLS[endpoint], client)

    assert ENGAGEMENT not in transmitted_text(sink), (
        f"{endpoint} put the engagement name on the wire without consent: {sink!r}"
    )
    assert sink == [], f"{endpoint} transmitted without consent: {sink!r}"
    assert refusal is not None, f"{endpoint} did not refuse"


def test_endpoint_coverage_is_exhaustive() -> None:
    """The parametrization above must name every public endpoint on the client.

    A meta-test, because the audit is the point: an endpoint added later and not
    listed here would otherwise be silently unproven. Copied in spirit from
    ``test_auth_transport_singleton``'s no-stale-entries check, which exists for
    the same reason.
    """
    public = {
        name
        for name in vars(SaaSTrackerClient)
        if not name.startswith("_") and callable(vars(SaaSTrackerClient)[name])
    }
    missing = public - set(ENDPOINT_CALLS)
    stale = set(ENDPOINT_CALLS) - public
    assert not missing, (
        f"public SaaSTrackerClient endpoints with no consent-gate test: {sorted(missing)}. "
        "Add them to ENDPOINT_CALLS — every sender must be proven gated."
    )
    assert not stale, (
        f"ENDPOINT_CALLS names methods that no longer exist: {sorted(stale)}. "
        "A stale entry makes the coverage assertion above pass vacuously."
    )


# ---------------------------------------------------------------------------
# The non-interactive reach — the one that matters most
# ---------------------------------------------------------------------------


def write_pending_origin(repo_root: Path) -> None:
    (repo_root / ".kittify" / "pending-origin.yaml").write_text(
        "\n".join(
            [
                "provider: linear",
                "issue_key: ENG-99",
                "issue_id: issue-456",
                # Quoted: the title carries a ``: `` and an unquoted scalar would
                # make ``read_pending_origin`` swallow the file and report "no
                # pending origin", which would make both tests below pass for
                # entirely the wrong reason.
                f'title: "{ISSUE_TITLE}"',
                "url: https://linear.app/acme/ENG-99",
                "status: In Progress",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_feature_dir(repo_root: Path) -> Path:
    feature_dir = repo_root / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)
    # A *complete* meta.json: ``set_origin_ticket`` validates it after the SaaS
    # call, so a minimal one would make the positive control fail on the local
    # write and stop proving that the send happened.
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": MISSION_ID,
                "mission_slug": MISSION_SLUG,
                "slug": MISSION_SLUG,
                "friendly_name": "ACME Holdings carve-out",
                "mission_type": "feature",
                "target_branch": "main",
                "created_at": "2026-07-30T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    return feature_dir


def test_mission_creation_bind_transmits_for_a_consenting_project(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """POSITIVE CONTROL for the non-interactive path.

    Drives the real chain — ``consume_pending_origin_impl`` →
    ``tracker/origin.bind_mission_origin`` → the transport — with no client
    injected, so the production construction site is the one under test.
    """
    from specify_cli.tracker.origin_consumer import consume_pending_origin_impl

    write_project_config(isolated_machine, sync_enabled=True)
    write_pending_origin(isolated_machine)
    feature_dir = write_feature_dir(isolated_machine)

    attempted, succeeded, error_msg, _meta = consume_pending_origin_impl(
        isolated_machine, feature_dir, {"mission_id": MISSION_ID, "mission_slug": MISSION_SLUG}
    )

    assert (attempted, succeeded, error_msg) == (True, True, None)
    # Same reason as the control above, and it bites harder here: this path reports
    # its own success through ``succeeded``, so a chain that resolves a lookup and
    # never reaches the bind POST reports ``True`` with one request recorded and the
    # slug in that request's URL. Naming the method is what separates "the bind
    # happened" from "something happened".
    assert [record["method"] for record in sink] == ["POST"], (
        f"the non-interactive path must reach the bind POST; recorded {sink!r}"
    )
    assert MISSION_SLUG in transmitted_text(sink), (
        "the control must carry the engagement name for the refusal test below "
        "to mean anything"
    )


def test_mission_creation_bind_leaks_nothing_without_consent(
    isolated_machine: Path, sink: list[dict[str, Any]]
) -> None:
    """THE ONE THAT MATTERS: no operator action is required to reach this send.

    ``core/mission_creation.py`` → ``core.adapters.consume_pending_origin`` →
    ``tracker/origin_consumer.py`` → ``bind_mission_origin``. A test that only
    exercised ``sync push`` would miss it entirely, and this is the reachability
    with no human in the loop to notice.

    Mission creation itself must still succeed locally — the refusal is reported
    through the existing ``origin_binding_error`` channel that
    ``mission_create.py`` already surfaces, not by aborting the mission.
    """
    from specify_cli.tracker.origin_consumer import consume_pending_origin_impl

    write_project_config(isolated_machine, sync_enabled=None)
    write_pending_origin(isolated_machine)
    feature_dir = write_feature_dir(isolated_machine)

    attempted, succeeded, error_msg, _meta = consume_pending_origin_impl(
        isolated_machine, feature_dir, {"mission_id": MISSION_ID, "mission_slug": MISSION_SLUG}
    )

    assert sink == [], (
        "mission creation must not transmit an engagement name for a project "
        f"that never opted in; recorded {sink!r}"
    )
    assert ENGAGEMENT not in transmitted_text(sink)
    assert ISSUE_TITLE not in transmitted_text(sink)

    assert attempted is True
    assert succeeded is False
    assert error_msg is not None and "consent" in error_msg.lower(), (
        "the refusal must reach the operator through origin_binding_error rather "
        f"than failing silently; got {error_msg!r}"
    )
