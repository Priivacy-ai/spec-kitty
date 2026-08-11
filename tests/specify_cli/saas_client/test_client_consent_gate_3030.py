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

import ast
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from specify_cli.saas_client import SaasClient, SaasClientError
from specify_cli.saas_client.errors import SaasConsentError
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_store import ProjectSyncStore

pytestmark = pytest.mark.fast

#: The `src/` tree, as a LITERAL. The corpus-scan constant inside the guard is
#: editable and is what a re-narrowing touches; this is not, which is what makes
#: the reach assertion able to fail. Do not fold the two together.
_SRC_TREE = Path(__file__).resolve().parents[3] / "src"


def _repo_relative(path: Path) -> str:
    """The ONE place the failure message's repo-relative path is computed.

    F1b was graded a blocker because the previous pin recomputed ``src.parent``
    inside the assertion, so it pinned a *copy* of the arithmetic and reverting the
    reporting line left it green — two objects with the same source text, which
    this module's own predicate docstring names as the state that goes green while
    the guard goes blind.

    A stronger assertion is not the answer: **no runtime assertion can observe
    which expression another line uses.** So the arithmetic now exists exactly
    once, which makes divergence unrepresentable rather than merely detected.

    Anchored on ``_SRC_TREE``, not on the guard's editable scan constant, so
    narrowing the scan root cannot silently change the reported prefix.

    Residual limit, stated rather than implied: a future edit that *bypasses* this
    helper and inlines its own arithmetic is a different failure, and nothing here
    catches it. That is the same "one object, two callers" bound the predicates
    carry.
    """
    return path.relative_to(_SRC_TREE.parent).as_posix()


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

    def post(self, url: str, *, json: Any = None, headers: dict[str, str] | None = None, timeout: float | None = None) -> RecordingResponse:
        del headers
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
    project_uuid = str(uuid4())
    lines = [
        "project:",
        f"  uuid: {project_uuid}",
        "  slug: acme-holdings",
        "  node_id: node12345678",
        "  repo_slug: acme-holdings/acme-holdings",
        "  build_id: 8a4a7da6-a97c-4bb4-893a-b31664abfee4",
    ]
    if sync_enabled is not None:
        lines += ["sync:", f"  enabled: {str(sync_enabled).lower()}"]
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if sync_enabled is True:
        record_project_opt_in(project_uuid, actor="generic-consent-positive")
        with ProjectSyncStore(project_uuid).unit_of_work() as unit:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://saas.example.invalid', 'account-test', 'private-test', 1, "
                "'admitted', 'admission-test', 'binding-test')",
                (project_uuid,),
            )


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
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.chdir(repo_root)
    return repo_root


def make_client(sink: list[dict[str, Any]], project_root: Path | None) -> SaasClient:
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


def test_consenting_project_transmits_the_engagement_name_in_the_url(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
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
    assert [(r["method"], r["json"]) for r in sink] == [("GET", None)], f"a consenting project must transmit exactly one GET with no body; recorded {sink!r}"
    assert MISSION_SLUG in sink[0]["url"], "the control must carry the engagement name in the URL path, or the absence assertions in this file prove nothing"


# ---------------------------------------------------------------------------
# The leak
# ---------------------------------------------------------------------------


def test_unconsented_project_puts_no_engagement_name_on_the_wire(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
    """THE LEAK: a project with no consent record must ship nothing."""
    write_project_config(isolated_machine, sync_enabled=None)

    refusal = refusal_of(ENDPOINT_CALLS["get_audience_default"], make_client(sink, isolated_machine))

    assert MISSION_SLUG not in transmitted_text(sink), f"the engagement name reached the transport, in the URL path: {[r['url'] for r in sink]!r}"
    assert ENGAGEMENT not in transmitted_text(sink)
    assert sink == [], f"nothing may reach the transport; recorded {sink!r}"
    assert isinstance(refusal, SaasConsentError), f"the call must refuse with a consent error; got {refusal!r}"


def test_machine_global_arming_is_not_a_grant(isolated_machine: Path, sink: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch) -> None:
    """``SPEC_KITTY_ENABLE_SAAS_SYNC`` is the incident's own mechanism, not consent."""
    write_project_config(isolated_machine, sync_enabled=None)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    refusal = refusal_of(ENDPOINT_CALLS["get_audience_default"], make_client(sink, isolated_machine))

    assert MISSION_SLUG not in transmitted_text(sink), f"machine-global arming carried the engagement name off the machine: {sink!r}"
    assert sink == []
    assert isinstance(refusal, SaasConsentError)


def test_project_local_refusal_is_honoured(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
    write_project_config(isolated_machine, sync_enabled=False)

    refusal = refusal_of(ENDPOINT_CALLS["get_audience_default"], make_client(sink, isolated_machine))

    assert MISSION_SLUG not in transmitted_text(sink), f"a committed refusal was overridden and the engagement name shipped: {sink!r}"
    assert sink == []
    assert isinstance(refusal, SaasConsentError)


def test_undetermined_project_denies(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
    """A client with no project attribution refuses (FR-003 / NFR-001)."""
    write_project_config(isolated_machine, sync_enabled=True)

    refusal = refusal_of(ENDPOINT_CALLS["get_audience_default"], make_client(sink, None))

    assert MISSION_SLUG not in transmitted_text(sink), f"an unattributed transport shipped the engagement name under a nearby project's consent: {sink!r}"
    assert sink == [], "a transport with no project attribution must refuse even when a consenting project happens to exist nearby"
    assert refusal is not None
    assert "could not be determined" in str(refusal)


@pytest.mark.parametrize("endpoint", sorted(ENDPOINT_CALLS))
def test_every_endpoint_refuses_without_consent(endpoint: str, isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
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

    assert ENGAGEMENT not in transmitted_text(sink), f"{endpoint} put the engagement name on the wire without consent: {sink!r}"
    assert sink == [], f"{endpoint} transmitted without consent: {sink!r}"
    if is_probe:
        assert probe_result is False, "health_probe must refuse by returning False"
    else:
        assert refusal is not None, f"{endpoint} did not refuse"


#: Non-vacuity floor for the SaaS attribution scan, as a **named integer**
#: (SC-005 ``[standing]``). Re-measured over **1197** files under ``src/``
#: — and identical under the old ``src/specify_cli`` root (936 files), which
#: is why widening the scan moved no count: ``direct=0, from_env=4``.
#:
#: The bare ``assert scanned`` this replaces reds only when *every* site of the
#: class disappears. The named integer is what makes losing **one** site red.
SAAS_CONSTRUCTION_SITE_FLOOR = 4

#: What this guard does **not** see, stated here because it is easy to mistake
#: the floor above for coverage (R5). The bound is the **literal class-name
#: match** below — an aliased import, a factory, or a transport injected as a
#: parameter is invisible to it. That is a property of *this* predicate.
#:
#: It is **not** ``#3113``. That issue is a property of ``_transmits_a_body`` in
#: ``tests/architectural/test_egress_consent_boundary.py``, which derives its
#: kwargs from ``node.keywords`` only and so misses all-positional calls. This
#: predicate counts every match regardless of call form and has no positional
#: blind spot. Do not credit any coverage claim here to ``#3113``.
SAAS_PREDICATE_BOUND = "literal class-name match on `SaasClient`; aliases, factories and injected transports are out of scope"


def _saas_site_attribution(node: ast.Call) -> tuple[bool, bool]:
    """Classify one call node as ``(matched, attributed)`` for the SaaS client.

    **One object, two callers** — the live corpus scan in
    ``test_every_production_construction_site_attributes_its_project`` and the
    synthetic witness assertions both call *this* function. A synthetic
    assertion that re-implements this logic instead of calling it does not
    satisfy SC-012/SC-013: two objects with the same source text is the state
    that goes green while the guard goes blind.

    Strictness is preserved exactly as it was inline (FR-016 is about keeping
    this, not improving it):

    * ``matched`` — a **literal** ``ast.Name`` receiver named ``SaasClient``,
      either constructed directly or via a ``SaasClient.from_env`` attribute.
    * ``attributed`` — for ``from_env``, a bare positional **or** ``repo_root=``;
      for direct construction, ``project_root=``.
    """
    func = node.func
    # ``SaasClient(...)`` or ``SaasClient.from_env(...)``
    is_direct = isinstance(func, ast.Name) and func.id == "SaasClient"
    is_from_env = isinstance(func, ast.Attribute) and func.attr == "from_env" and isinstance(func.value, ast.Name) and func.value.id == "SaasClient"
    if not (is_direct or is_from_env):
        return False, False
    if is_from_env:
        # ``from_env`` threads the root as a bare positional or as ``repo_root=``.
        return True, bool(node.args) or any(kw.arg == "repo_root" for kw in node.keywords)
    # Direct construction threads it as ``project_root=``.
    return True, any(kw.arg == "project_root" for kw in node.keywords)


def test_every_production_construction_site_attributes_its_project() -> None:
    """The attribution precondition, made executable.

    Every production site reaches the client through ``from_env``, which threads
    its ``repo_root`` onto the client as the project whose consent gates the send.
    A ``from_env()`` with no root produces a client that refuses everything, so
    the failure mode is loud rather than leaky — but it is still a broken caller,
    and a direct ``SaasClient(...)`` without ``project_root`` is the same.

    Scans ``src/`` for both shapes. It cannot prove the root is the *right* one;
    that is enumerated per site in ``specify_cli/egress.py``, including the one
    site (``decision widen``) where root and subject can legitimately diverge and
    what actually bounds it.
    """
    # **US3 (``../../kitty-specs/…/spec.md:213-217``)** is the source of the scope,
    # quoted: *"Each package carries its own AST guard that scans ``src/``, reds,
    # and names the file and line. That protection must survive this mission at
    # full strength for both packages."*
    #
    # An earlier version of this comment cited SC-007/FR-014 as saying it. NEITHER
    # DOES — SC-007 is a per-class *count* criterion ("counts are at least the
    # bb2020fea baseline") and FR-014 is "per-class non-vacuity floor". Presenting
    # them as the source was a claim nobody had followed back to its text, which is
    # this mission's own recurring failure. SC-007/FR-014 belong where they are
    # cited below: as the reason the FLOORS are named per-class integers.
    #
    # This scanned ``src/specify_cli`` while its docstring and failure message said
    # ``src/`` — the divergence recorded as WP03 R-1, one module over.
    #
    # Widening is free HERE and that was measured, not assumed: both class
    # counts are identical under either root (SaasClient 4, SaaSTrackerClient
    # 3), so **neither floor moves**. What it buys is reach — a construction
    # site landing in a sibling package under ``src/`` was previously invisible
    # to a guard whose message claimed to cover it.
    src = Path(__file__).resolve().parents[3] / "src"
    assert src.is_dir(), f"source tree not found at {src} — path regression?"

    unattributed: list[str] = []
    scanned = 0
    files = sorted(src.rglob("*.py"))

    # EXECUTABLE PIN FOR THE SCOPE ABOVE — F1.
    #
    # Without this, reverting the widening is SILENTLY GREEN: the reviewer built
    # that counterfactual and both guards still reported their exact HEAD tallies.
    # Nothing observed the scope, which made the "fix" strictly weaker than the
    # pre-fix SC-015 state — that at least had a file-count floor. A scope claim
    # with no assertion behind it is the shape this whole mission keeps finding.
    #
    # Anchored on `_SRC_TREE`, a module-level literal that a narrowing of the scan
    # constant CANNOT move. The previous form derived `src_packages` from `src`
    # itself — the scan constant — so both sides moved together and the pin was
    # vacuous against the exact edit it was added to catch. Measured: under a
    # narrowed `src/specify_cli`, `src.iterdir()` enumerates that package's **67**
    # subpackages, `rglob` reaches all of them, `unreached` is `[]` by
    # construction, and `len(...) > 1` passes at 67 — two nested controls both
    # green under the regression.
    src_packages = [d for d in sorted(_SRC_TREE.iterdir()) if (d / "__init__.py").is_file()]
    assert len(src_packages) > 1, (
        f"anti-vacuity: {_SRC_TREE} holds {len(src_packages)} package(s). This "
        "control exists so 'the scan spans every package' cannot be satisfied by a "
        "tree with one package in it."
    )
    unreached = [d.name for d in src_packages if not any(f.is_relative_to(d) for f in files)]
    assert not unreached, (
        f"the scan reached {len(files)} files but none in {unreached} — package(s) "
        f"that exist under {_SRC_TREE}. US3 mandates a guard that scans `src/`, the "
        "whole tree; narrowing the scan root is what reds this."
    )
    # The report path's arithmetic lives in `_repo_relative` and nowhere else, so
    # this exercises the SAME code the failure message uses rather than a copy of
    # it. A wrong base otherwise manifests only INSIDE a red, where no green can
    # catch it.
    assert _repo_relative(_SRC_TREE / "specify_cli" / "egress.py") == ("src/specify_cli/egress.py"), (
        "_repo_relative no longer yields repo-relative paths, so every path this guard names in a failure would be wrong — and only on a red."
    )

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            matched, attributed = _saas_site_attribution(node)
            if not matched:
                continue
            scanned += 1
            if not attributed:
                unattributed.append(f"{_repo_relative(path)}:{node.lineno}")

    assert scanned >= SAAS_CONSTRUCTION_SITE_FLOOR, (
        f"expected at least {SAAS_CONSTRUCTION_SITE_FLOOR} SaasClient construction "
        f"sites in src/, found {scanned}. A bare `assert scanned` reds only when "
        "every site of the class disappears; this named floor is what makes losing "
        "ONE site red. If a site was deliberately removed, lower the floor in the "
        "same commit and say why — do not delete the assertion.\n\n"
        f"What this floor does NOT prove: {SAAS_PREDICATE_BOUND}."
    )
    assert not unattributed, (
        "SaasClient built without a project attribution at:\n  " + "\n  ".join(unattributed) + "\n\nPass the root of the project that OWNS the mission or decision "
        "record the request carries (#3030 FR-030) — `from_env(repo_root=...)`, or "
        "`project_root=` on a direct construction. See "
        "specify_cli/egress.py for the precondition and what falsifies it."
    )


def _call(expr: str) -> ast.Call:
    """Parse a single call expression into the node the predicate consumes."""
    # `body[0]` is typed `ast.stmt`, which has no `.value`; it is an `ast.Expr`
    # here because every caller passes a bare expression. The isinstance check
    # below is what actually enforces that, so the narrowing is verified rather
    # than assumed.
    node = ast.parse(expr).body[0].value  # type: ignore[attr-defined]
    assert isinstance(node, ast.Call), f"{expr!r} is not a call expression"
    return node


def test_saas_predicate_flags_a_form_it_matches_but_does_not_accept() -> None:
    """SC-012 — asserted on a synthetic sample, through the extracted predicate.

    ``SaasClient.from_env(project_root=r)`` is **matched and flagged
    unattributed**: ``from_env`` threads its root as a bare positional or as
    ``repo_root=``, so ``project_root=`` is the wrong keyword for that form.

    **The obvious witness would have been vacuous** (DB-4). "The SaaS guard is
    not widened to admit tracker-only spellings" is vacuously true — the tracker
    accepts exactly ``{project_root=}``, which this guard *already* accepts for
    direct construction, so that phrasing bites nothing. The ``from_env`` form is
    the one that flips the moment the SaaS vocabulary is widened.
    """
    matched, attributed = _saas_site_attribution(_call("SaasClient.from_env(project_root=r)"))

    assert matched, "SaasClient.from_env(...) must be matched — if it is not, the guard has stopped seeing the form every production site actually uses"
    assert not attributed, (
        "SaasClient.from_env(project_root=r) must be flagged unattributed: "
        "from_env accepts a bare positional or repo_root=, not project_root=. "
        "If this now reads as attributed, the SaaS vocabulary was widened and "
        "the guard accepts a spelling that does not thread the root."
    )


def test_saas_predicate_matches_a_shape_no_src_site_uses() -> None:
    """SC-013 — a **match** on a shape the live corpus never exercises.

    Measured corpus: ``direct=0, from_env=4``. Bare ``SaasClient(project_root=…)``
    is therefore *matched but unused*, so a unification that collapsed the
    predicate onto the ``from_env`` form would drop it **silently, with no count
    moving** — ``scanned`` would stay at exactly 4.

    **No non-match is asserted here, deliberately.** Pinning
    ``mod.SaasClient(...)`` as must-not-match was proposed and withdrawn on
    measurement: this predicate is already the stricter of the two, so
    unification can only *loosen* it — the guard would see more constructions, a
    coverage gain. Such a pin would red on an improvement and collide with FU-8,
    which exists precisely because ``mod.SaasClient.from_env(x)`` is unguarded on
    both guards and closing it means **widening** a predicate.
    """
    matched, attributed = _saas_site_attribution(_call("SaasClient(project_root=r)"))

    assert matched, (
        "bare SaasClient(project_root=...) must still be matched. The live corpus "
        "is direct=0, so this shape is matched-but-unused: dropping it moves no "
        "count and the floor stays at exactly 4 — which is why it is asserted here "
        "rather than left to the corpus scan."
    )
    assert attributed, "SaasClient(project_root=...) is the attributed spelling for direct construction; if this reads unattributed the predicate was narrowed"


def test_saas_predicate_rejects_the_from_env_root_spelling_on_a_direct_construction() -> None:
    """WP01 F2 — the widening shape that the two witnesses above cannot see.

    ``SaasClient(repo_root=r)`` is **matched and flagged unattributed**:
    ``repo_root=`` is ``from_env``'s spelling of the root, and ``__init__`` has no
    such parameter at all — its signature is ``(base_url, token, team_slug=None,
    timeout=…, _http=None, project_root=None)``. The call does not merely fail to
    attribute a project; it does not construct. Reading it as attributed would
    bless a call that cannot exist.

    **Why it needs its own witness.** The live corpus is ``direct=0,
    from_env=4``, so no production site exercises this shape; and neither witness
    above reds if the *direct* branch alone starts accepting ``repo_root=``:

    * SC-012 pins ``from_env(project_root=r)`` — a **from_env** node, untouched.
    * SC-013 pins ``SaasClient(project_root=r)`` — still attributed either way.
    * The corpus scan cannot move: ``scanned`` stays at 4 and ``unattributed``
      stays empty, because there is no direct site to reclassify.

    The *naive* unification — one accepted-kwarg set for both branches — is
    caught, by SC-012. Only a **selective** widening of the direct branch slips
    through, and that is precisely the edit someone makes while "harmonising" the
    two predicates' vocabularies.

    **No non-match is asserted here** (T006): this predicate is already the
    stricter of the two, so unification can only loosen it, and a must-not-match
    pin would red on that improvement and collide with FU-8.
    """
    matched, attributed = _saas_site_attribution(_call("SaasClient(repo_root=r)"))

    assert matched, (
        "SaasClient(...) must be matched regardless of its kwargs — a direct "
        "construction that the guard stops seeing is a construction it cannot "
        "hold to the attribution precondition at all"
    )
    assert not attributed, (
        "SaasClient(repo_root=r) must be flagged unattributed: repo_root= is "
        "from_env's spelling and __init__ has no such parameter, so this call "
        "does not construct at all — let alone attribute a project. "
        "If this now reads as attributed, the direct branch was "
        "widened to admit from_env's vocabulary — a change no count can see "
        "(direct=0 in the live corpus, so scanned stays at exactly 4) and one "
        "that neither SC-012 nor SC-013 above reds on."
    )


def test_no_attribution_is_a_refusal_at_the_gate_itself() -> None:
    """The invariant, asserted below the transport and below every fixture.

    This directory's autouse conftest can inject a consenting project into a
    client built without one; calling the gate directly pins "no attribution
    refuses" where no fixture can arrange the answer.
    """
    from specify_cli.egress import project_egress_refusal
    from specify_cli.saas_client.client import SAAS_EGRESS_IDENTIFIER_KINDS

    refusal = project_egress_refusal(None, SAAS_EGRESS_IDENTIFIER_KINDS)

    assert refusal is not None, "an unattributed send must never be permitted"
    assert "could not be determined" in refusal


def test_sc016_denied_wording_is_pinned_for_this_transport(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
    """SC-016 / FR-024: the ``DENIED`` branch's merged wording, pinned here.

    **Added alongside the four pre-existing ``could not be determined``
    assertions, never replacing them.** Those target ``UNDETERMINED`` — a
    *different* branch — and would stay green if the ``DENIED`` branch were
    deleted outright, which is precisely the state this test exists to red on
    (demonstrated by MUT-1 in the mission evidence).

    Driven end-to-end through the real refusal path: a committed
    ``sync.enabled: false`` under this checkout, through
    ``client.py::_refuse_unless_project_consents``, to the operator-visible
    string. Nothing here reads the wrapper directly.
    """
    from specify_cli.egress import _DENIED_TEMPLATE
    from specify_cli.saas_client.client import SAAS_EGRESS_IDENTIFIER_KINDS

    write_project_config(isolated_machine, sync_enabled=False)

    refusal = refusal_of(ENDPOINT_CALLS["get_audience_default"], make_client(sink, isolated_machine))

    assert sink == [], f"a refused project reached the transport: {sink!r}"
    assert isinstance(refusal, SaasConsentError), f"the DENIED path did not produce a consent refusal: {refusal!r}"
    text = str(refusal)

    # SC-016 — the merged wording itself. Hard-coded on purpose: under the
    # operator's Q2 decision this text is FIXED by the spec, not chosen by the
    # implementer, so an implementer cannot both pick the wording and write the
    # assertion that blesses it.
    assert "has not consented to hosted sync" in text, text
    assert "must not be transmitted" in text, text

    # NFR-004 — the branch is operator-actionable. "Non-empty and
    # distinguishable" is explicitly not the bar.
    assert "sync opt-in" in text, f"the DENIED branch names no next action: {text!r}"
    assert ".kittify/config.yaml" in text, text

    # SC-004 clause 2 — this transport's OWN identifier set, and no foreign kind.
    assert SAAS_EGRESS_IDENTIFIER_KINDS in text, text
    assert SAAS_EGRESS_IDENTIFIER_KINDS == "mission and decision identifiers", "the SaaS fragment changed; both DENIED strings survive Q2 verbatim"
    assert "engagement identifiers" not in text, (
        f"this transport carries no engagement names, so naming them overstates the exposure to an operator (US2-AS2): {text!r}"
    )

    # SC-004 clause 1 — the non-fragment portion came from the ONE shared
    # template. Two templates that happened to agree today would fail here as
    # soon as one of them was edited.
    # ``endswith`` rather than ``==`` because ``SaasConsentError`` prefixes the
    # wrapper's string with its own "Refusing to call Spec Kitty SaaS: " context.
    # The whole rendered refusal is still pinned — only the exception's prefix is
    # allowed in front of it.
    rendered = _DENIED_TEMPLATE.format(project_root=isolated_machine, identifiers=SAAS_EGRESS_IDENTIFIER_KINDS)
    assert text.endswith(rendered), (
        "the rendered refusal is not this transport's fragment in the shared "
        f"template — a second presentation of the policy exists:\n"
        f"  observed: {text!r}\n  expected tail: {rendered!r}"
    )


def test_endpoint_coverage_is_exhaustive() -> None:
    """The parametrization must name every public endpoint on the client.

    ``has_token`` and ``from_env`` are excluded by name: the first is a property
    over local state and the second is a constructor. Everything else on the
    public surface is a sender and must be proven gated.
    """
    not_a_sender = {"has_token", "from_env"}
    public = {name for name, obj in vars(SaasClient).items() if not name.startswith("_") and (callable(obj) or isinstance(obj, property))} - not_a_sender
    missing = public - set(ENDPOINT_CALLS)
    stale = set(ENDPOINT_CALLS) - public
    assert not missing, f"public SaasClient endpoints with no consent-gate test: {sorted(missing)}"
    assert not stale, f"ENDPOINT_CALLS names methods that no longer exist: {sorted(stale)}"


def test_health_probe_refuses_quietly_and_sends_nothing(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
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


def test_from_env_carries_the_project_it_was_given(isolated_machine: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_from_env_without_a_repo_root_produces_a_refusing_client(isolated_machine: Path, sink: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch) -> None:
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

    assert MISSION_SLUG not in transmitted_text(sink), f"a client built without a repo_root shipped the engagement name: {sink!r}"
    assert sink == []
    assert isinstance(refusal, SaasConsentError)


def test_consent_refusal_is_suppressible_like_any_saas_failure(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
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
    assert isinstance(refusal, SaasConsentError), f"the refusal must be catchable as SaasClientError by the existing local-first handlers; got {refusal!r}"
