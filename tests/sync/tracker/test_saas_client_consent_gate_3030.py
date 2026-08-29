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

import ast
import json
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest

from specify_cli.tracker.saas_client import (
    SaaSTrackerClient,
    SaaSTrackerClientError,
    _HostedTrackerAuthority,
)
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

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
    project_uuid = str(uuid4())
    lines = [
        "project:",
        f"  uuid: {project_uuid}",
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
    if sync_enabled is True:
        record_project_opt_in(project_uuid, actor="tracker-consent-positive")
        with ProjectSyncStore(project_uuid).unit_of_work() as unit:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://app.spec-kitty.ai', 'account-test', 'private-test', 1, "
                "'admitted', 'admission-test', 'binding-test')",
                (project_uuid,),
            )


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
        "specify_cli.tracker.saas_client._hosted_authority_for_token",
        lambda _token: _HostedTrackerAuthority(
            account_identity="account-test",
            private_teamspace_id="private-test",
            collaborative_team_slug="acme-team",
        ),
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
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home / ".spec-kitty"))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    # Pin the resolved hosted target to the admitted target row these tests
    # write. Without this the resolved URL is whatever the developer's shell
    # (or DEFAULT_SERVER_URL) says, and the WP05 target-authority check
    # refuses with target_authority_mismatch on machines/CI where they differ.
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://app.spec-kitty.ai")
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
    return cast(
        dict[str, Any],
        client.bind_mission_origin(
            "linear",
            PROJECT_SLUG,
            mission_id=MISSION_ID,
            mission_slug=MISSION_SLUG,
            external_issue_id="issue-456",
            external_issue_key="ENG-99",
            external_issue_url="https://linear.app/acme/ENG-99",
            title=ISSUE_TITLE,
        ),
    )


# ---------------------------------------------------------------------------
# The positive control — without it, every red below is unfalsifiable
# ---------------------------------------------------------------------------


def test_consenting_project_still_transmits_the_engagement_name(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
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
    assert [record["method"] for record in sink] == ["POST"], f"consenting project must transmit the authoritative bind POST; recorded {sink!r}"
    assert MISSION_SLUG in transmitted_text(sink), "the control must actually carry the engagement name, or the absence assertions in this file prove nothing"


# ---------------------------------------------------------------------------
# The leak
# ---------------------------------------------------------------------------


def test_unconsented_project_transmits_no_engagement_name(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
    """THE LEAK: a project with no consent record must ship nothing.

    Identical to the control except that no consent was ever recorded — the
    state of the five projects in the incident. Asserted on the transmitted
    bytes, not on a verdict.
    """
    write_project_config(isolated_machine, sync_enabled=None)

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=isolated_machine))

    body = transmitted_text(sink)
    assert ENGAGEMENT not in body, f"the client engagement name reached the transport: {sink!r}"
    assert MISSION_SLUG not in body, f"the mission slug — an engagement name — reached the transport: {sink!r}"
    assert ISSUE_TITLE not in body, f"the issue title reached the transport: {sink!r}"
    assert sink == [], f"a project that never opted in must not reach the transport at all; recorded {sink!r}"
    assert refusal is not None, "the call must refuse, not silently no-op"
    assert refusal.error_code == "project_consent_denied", (
        "a refusal must be distinguishable from an auth or transport failure, or the operator will go and check their token"
    )


def test_machine_global_arming_is_not_a_grant(isolated_machine: Path, sink: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch) -> None:
    """The incident's own mechanism must not authorize a send.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is machine-global *arming*. One exported
    shell variable carried five never-opted-in projects along with the intended
    one; the spec states it is never a grant.
    """
    write_project_config(isolated_machine, sync_enabled=None)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=isolated_machine))

    assert ENGAGEMENT not in transmitted_text(sink), f"machine-global arming carried the engagement name off the machine: {sink!r}"
    assert sink == [], "machine-global arming must never stand in for project consent"
    assert refusal is not None


def test_project_local_refusal_is_honoured(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
    """A committed, reviewable ``sync.enabled: false`` denies."""
    write_project_config(isolated_machine, sync_enabled=False)

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=isolated_machine))

    assert ENGAGEMENT not in transmitted_text(sink), f"a committed refusal was overridden and the engagement name shipped: {sink!r}"
    assert sink == []
    assert refusal is not None


def test_undetermined_project_denies(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
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

    assert ENGAGEMENT not in transmitted_text(sink), f"an unattributed transport shipped the engagement name under a nearby project's consent: {sink!r}"
    assert sink == [], "a transport with no project attribution must refuse even when a consenting project happens to exist nearby"
    assert refusal is not None
    assert "could not be determined" in str(refusal)


#: Non-vacuity floor for the tracker attribution scan, as a **named integer**
#: (SC-005 ``[standing]``). Re-measured over **1197** files under ``src/``
#: — and identical under the old ``src/specify_cli`` root (936 files), which
#: is why widening the scan moved no count.
#:
#: The bare ``assert scanned`` this replaces reds only when *every* site of the
#: class disappears. The named integer is what makes losing **one** site red.
TRACKER_CONSTRUCTION_SITE_FLOOR = 3

#: What this guard does **not** see (R5 — the floor is not coverage). The bound
#: is the **literal class-name match** on ``SaaSTrackerClient`` below: an aliased
#: import, a factory, or an injected transport is invisible to it.
#:
#: It is **not** ``#3113``, which is a property of ``_transmits_a_body`` in the
#: *boundary* guard. This predicate counts every match regardless of call form —
#: it accepts an attribute receiver as well as a bare name — and so has no
#: positional blind spot.
TRACKER_PREDICATE_BOUND = "literal class-name match on `SaaSTrackerClient`; aliases, factories and injected transports are out of scope"


def _tracker_site_attribution(node: ast.Call) -> tuple[bool, bool]:
    """Classify one call node as ``(matched, attributed)`` for the tracker client.

    **One object, two callers** — the live corpus scan below and the synthetic
    witness assertions both call *this* function, for the reason spelled out in
    the SaaS guard's counterpart.

    Strictness is preserved exactly as it was inline, and it is deliberately
    **looser on the receiver** than the SaaS predicate:

    * ``matched`` — ``func.id`` for a bare ``ast.Name``, else ``func.attr``, so
      an **attribute-receiver** call (``mod.SaaSTrackerClient(...)``) still
      matches. All three live sites are bare names, so nothing in the corpus
      exercises that branch — which is exactly why SC-013 asserts it.
    * ``attributed`` — ``project_root=`` **only**. Not ``repo_root=``.
    """
    func = node.func
    name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
    if name != "SaaSTrackerClient":
        return False, False
    return True, any(kw.arg == "project_root" for kw in node.keywords)


def test_every_production_construction_site_attributes_its_project() -> None:
    """The attribution precondition, made executable.

    The gate resolves consent from the checkout root it is handed, so it is only
    sound while **every** construction site passes the root of the project that
    owns the record the request will carry. That condition is stated in
    ``specify_cli/egress.py``; a prose statement alone is how this class
    regenerates, because it reads as obviously fine until someone adds the caller
    that breaks it and nothing tells them they broke it.

    This scans ``src/`` and fails on a ``SaaSTrackerClient(...)`` built without an
    explicit ``project_root``. It cannot prove the root passed is the *right* one
    — that is the reviewable part, enumerated per site in the module docstring —
    but it does make the omission a red build rather than a silent refusing
    client, and it forces a new caller to think about whose data it is sending.
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
            matched, attributed = _tracker_site_attribution(node)
            if not matched:
                continue
            scanned += 1
            if not attributed:
                unattributed.append(f"{_repo_relative(path)}:{node.lineno}")

    assert scanned >= TRACKER_CONSTRUCTION_SITE_FLOOR, (
        f"expected at least {TRACKER_CONSTRUCTION_SITE_FLOOR} SaaSTrackerClient "
        f"construction sites in src/, found {scanned}. A bare `assert scanned` reds "
        "only when every site of the class disappears; this named floor is what "
        "makes losing ONE site red. If a site was deliberately removed, lower the "
        "floor in the same commit and say why — do not delete the assertion.\n\n"
        f"What this floor does NOT prove: {TRACKER_PREDICATE_BOUND}."
    )
    assert not unattributed, (
        "SaaSTrackerClient constructed without project_root at:\n  "
        + "\n  ".join(unattributed)
        + "\n\nEvery construction site must pass the root of the project that OWNS "
        "the data the request carries (#3030 FR-029) — never the process cwd, and "
        "never another project's root. Without it the client refuses every request; "
        "with the wrong one it asks the wrong project. See "
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


def test_tracker_predicate_flags_a_form_it_matches_but_does_not_accept() -> None:
    """SC-012 — asserted on a synthetic sample, through the extracted predicate.

    ``SaaSTrackerClient(repo_root=…)`` is **matched and flagged unattributed**:
    this guard accepts ``project_root=`` and nothing else. ``repo_root=`` is the
    SaaS client's ``from_env`` spelling, and admitting it here is exactly the
    vocabulary widening MUT-4 performs — a widening **no count can see**, because
    ``scanned`` increments before the attribution test.
    """
    matched, attributed = _tracker_site_attribution(_call("SaaSTrackerClient(repo_root=r)"))

    assert matched, "SaaSTrackerClient(...) must be matched regardless of its kwargs"
    assert not attributed, (
        "SaaSTrackerClient(repo_root=r) must be flagged unattributed: this guard "
        "accepts project_root= only. If this now reads as attributed, the tracker "
        "vocabulary was widened to admit the SaaS client's spelling — which leaves "
        "both scanned counts exactly unchanged, so no count would catch it."
    )


def test_tracker_predicate_matches_a_shape_no_src_site_uses() -> None:
    """SC-013 — a **match** on a shape the live corpus never exercises.

    All three live tracker sites are bare ``ast.Name`` callees, so nothing in the
    corpus exercises the attribute-receiver branch. Narrowing this predicate to a
    literal ``Name`` receiver — MUT-5 — would blind the guard to
    ``mod.SaaSTrackerClient(...)`` **while leaving ``scanned`` at exactly its
    floor of 3**, which is why the floor alone cannot detect it.

    No non-match is asserted here; see the SaaS counterpart for why.
    """
    matched, attributed = _tracker_site_attribution(_call("mod.SaaSTrackerClient(project_root=r)"))

    assert matched, (
        "mod.SaaSTrackerClient(project_root=...) must be matched — the predicate "
        "reads func.attr for an attribute receiver. If this stops matching, the "
        "predicate was narrowed to a literal Name receiver and scanned stays at "
        "exactly 3, so the floor would not catch it."
    )
    assert attributed, "project_root= is the attributed spelling for this class"


def test_tracker_predicate_rejects_a_bare_positional_root() -> None:
    """WP01 F2 — the widening shape that the two witnesses above cannot see.

    ``SaaSTrackerClient(r)`` is **matched and flagged unattributed**. The tracker
    constructor is ``(sync_config=None, *, project_root=None, timeout=30.0)`` —
    ``project_root`` is **keyword-only**, and the sole positional slot is
    ``sync_config``. A bare positional therefore does not merely spell the root
    differently: it binds a *different parameter* and leaves ``_project_root``
    ``None``, producing a client that refuses every request. Reading it as
    attributed would bless a call the class cannot honour.

    **Why it needs its own witness.** All three live sites pass
    ``project_root=``, so nothing in the corpus is a bare positional, and neither
    witness above reds if ``bool(node.args)`` is added to the attribution test:

    * SC-012 pins ``SaaSTrackerClient(repo_root=r)`` — no positional args, so it
      stays unattributed and stays green.
    * SC-013 pins ``mod.SaaSTrackerClient(project_root=r)`` — already attributed.
    * The corpus scan cannot move: ``scanned`` stays at 3 and ``unattributed``
      stays empty, because no live site is positional.

    ``bool(node.args)`` is not a hypothetical edit: it is *correct* in the SaaS
    predicate, where ``from_env`` really does thread the root positionally. Copying
    that clause across while "harmonising" the two predicates is the selective
    widening this pins — the naive unification is already caught by SC-012.

    **No non-match is asserted here**, for the reason given in the SaaS
    counterpart (T006): a must-not-match pin would red on a coverage improvement.
    """
    matched, attributed = _tracker_site_attribution(_call("SaaSTrackerClient(r)"))

    assert matched, (
        "SaaSTrackerClient(...) must be matched regardless of its call form — a "
        "construction the predicate stops seeing is one it cannot hold to the "
        "attribution precondition at all"
    )
    assert not attributed, (
        "SaaSTrackerClient(r) must be flagged unattributed: project_root is "
        "keyword-only on this constructor and the positional slot is sync_config, "
        "so a bare positional binds a different parameter and leaves the client "
        "with no project. If this now reads as attributed, a `bool(node.args)` clause "
        "was carried over from the SaaS predicate — where it is correct, because "
        "from_env does thread the root positionally. That widening leaves scanned "
        "at exactly 3 and reds neither SC-012 nor SC-013 above."
    )


def test_no_attribution_is_a_refusal_at_the_gate_itself() -> None:
    """The invariant, asserted below the transport and below every fixture.

    The transport tests above run under this directory's autouse shim, which can
    inject a project. This one calls the gate function directly, so "no project
    attribution refuses" is pinned by something no fixture can arrange.
    """
    from specify_cli.egress import project_egress_refusal
    from specify_cli.tracker.saas_client import TRACKER_EGRESS_IDENTIFIER_KINDS

    refusal = project_egress_refusal(None, TRACKER_EGRESS_IDENTIFIER_KINDS)

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
    ``sync.enabled: false`` under this checkout, through the call at
    ``tracker/saas_client.py::_request``, to the operator-visible string.
    """
    from specify_cli.egress import _DENIED_TEMPLATE
    from specify_cli.tracker.saas_client import TRACKER_EGRESS_IDENTIFIER_KINDS

    write_project_config(isolated_machine, sync_enabled=False)

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=isolated_machine))

    assert sink == [], f"a refused project reached the transport: {sink!r}"
    assert refusal is not None, "the DENIED path did not refuse"
    text = str(refusal)

    # SC-016 — the merged wording itself. Hard-coded on purpose: under the
    # operator's Q2 decision this text is FIXED by the spec, not chosen by the
    # implementer.
    assert "has not consented to hosted sync" in text, text
    assert "must not be transmitted" in text, text

    # NFR-004 — the branch is operator-actionable.
    assert "sync opt-in" in text, f"the DENIED branch names no next action: {text!r}"
    assert ".kittify/config.yaml" in text, text

    # SC-004 clause 2 — this transport's OWN identifier set, and no foreign kind.
    assert TRACKER_EGRESS_IDENTIFIER_KINDS in text, text
    assert TRACKER_EGRESS_IDENTIFIER_KINDS == "mission and engagement identifiers", "the tracker fragment changed; both DENIED strings survive Q2 verbatim"
    assert "decision identifiers" not in text, f"this transport carries no decision_id, so naming one overstates the exposure to an operator (US2-AS2): {text!r}"

    # SC-004 clause 1 — the non-fragment portion came from the ONE shared
    # template.
    # ``endswith`` rather than ``==`` so a transport that prefixes its own
    # context onto the refusal (as the SaaS client's error type does) still
    # pins the whole rendered string.
    rendered = _DENIED_TEMPLATE.format(project_root=isolated_machine, identifiers=TRACKER_EGRESS_IDENTIFIER_KINDS)
    assert text.endswith(rendered), (
        "the rendered refusal is not this transport's fragment in the shared "
        f"template — a second presentation of the policy exists:\n"
        f"  observed: {text!r}\n  expected tail: {rendered!r}"
    )


def test_a_directory_that_is_not_a_project_denies(tmp_path: Path, sink: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch) -> None:
    """A path with no project identity is unidentifiable, so never consentable."""
    home = tmp_path / "home"
    stray = tmp_path / "not-a-spec-kitty-project"
    home.mkdir()
    stray.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)

    refusal = refusal_of(bind_call, SaaSTrackerClient(project_root=stray))

    assert ENGAGEMENT not in transmitted_text(sink), f"an unidentifiable checkout shipped the engagement name: {sink!r}"
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
def test_every_endpoint_refuses_without_consent(endpoint: str, isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
    """No endpoint may transmit for a project that has not consented.

    The reported instance named three POSTs. Consent is a property of the
    transport, not of the three methods someone happened to look at, so every
    endpoint is exercised — including the GETs, whose query strings carry
    ``project_slug``.
    """
    write_project_config(isolated_machine, sync_enabled=None)
    client = SaaSTrackerClient(project_root=isolated_machine)

    refusal = refusal_of(ENDPOINT_CALLS[endpoint], client)

    assert ENGAGEMENT not in transmitted_text(sink), f"{endpoint} put the engagement name on the wire without consent: {sink!r}"
    assert sink == [], f"{endpoint} transmitted without consent: {sink!r}"
    assert refusal is not None, f"{endpoint} did not refuse"


def test_endpoint_coverage_is_exhaustive() -> None:
    """The parametrization above must name every public endpoint on the client.

    A meta-test, because the audit is the point: an endpoint added later and not
    listed here would otherwise be silently unproven. Copied in spirit from
    ``test_auth_transport_singleton``'s no-stale-entries check, which exists for
    the same reason.
    """
    public = {name for name in vars(SaaSTrackerClient) if not name.startswith("_") and callable(vars(SaaSTrackerClient)[name])}
    missing = public - set(ENDPOINT_CALLS)
    stale = set(ENDPOINT_CALLS) - public
    assert not missing, (
        f"public SaaSTrackerClient endpoints with no consent-gate test: {sorted(missing)}. Add them to ENDPOINT_CALLS — every sender must be proven gated."
    )
    assert not stale, f"ENDPOINT_CALLS names methods that no longer exist: {sorted(stale)}. A stale entry makes the coverage assertion above pass vacuously."


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


def test_mission_creation_bind_transmits_for_a_consenting_project(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
    """POSITIVE CONTROL for the non-interactive path.

    Drives the real chain — ``consume_pending_origin_impl`` →
    ``tracker/origin.bind_mission_origin`` → the transport — with no client
    injected, so the production construction site is the one under test.
    """
    import specify_cli.sync.runtime as runtime_mod
    from specify_cli.tracker.origin_consumer import consume_pending_origin_impl

    runtime_before = runtime_mod._runtime
    write_project_config(isolated_machine, sync_enabled=True)
    write_pending_origin(isolated_machine)
    feature_dir = write_feature_dir(isolated_machine)

    try:
        attempted, succeeded, error_msg, _meta = consume_pending_origin_impl(
            isolated_machine, feature_dir, {"mission_id": MISSION_ID, "mission_slug": MISSION_SLUG}
        )

        assert (attempted, succeeded, error_msg) == (True, True, None)
        # Same reason as the control above, and it bites harder here: this path reports
        # its own success through ``succeeded``, so a chain that resolves a lookup and
        # never reaches the bind POST reports ``True`` with one request recorded and the
        # slug in that request's URL. Naming the method is what separates "the bind
        # happened" from "something happened".
        assert [record["method"] for record in sink] == ["POST"], f"the non-interactive path must reach the bind POST; recorded {sink!r}"
        assert MISSION_SLUG in transmitted_text(sink), "the control must carry the engagement name for the refusal test below to mean anything"
    finally:
        # Preserve the incoming process-global state.  Unconditionally resetting
        # here made this test order-dependent: when an earlier test had already
        # created the runtime, teardown changed that live singleton to ``None``.
        if runtime_before is None:
            runtime_mod.reset_runtime()
        else:
            assert runtime_mod._runtime is runtime_before


def test_mission_creation_bind_leaks_nothing_without_consent(isolated_machine: Path, sink: list[dict[str, Any]]) -> None:
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

    attempted, succeeded, error_msg, _meta = consume_pending_origin_impl(isolated_machine, feature_dir, {"mission_id": MISSION_ID, "mission_slug": MISSION_SLUG})

    assert sink == [], f"mission creation must not transmit an engagement name for a project that never opted in; recorded {sink!r}"
    assert ENGAGEMENT not in transmitted_text(sink)
    assert ISSUE_TITLE not in transmitted_text(sink)

    assert attempted is True
    assert succeeded is False
    assert error_msg is not None and "consent" in error_msg.lower(), (
        f"the refusal must reach the operator through origin_binding_error rather than failing silently; got {error_msg!r}"
    )
