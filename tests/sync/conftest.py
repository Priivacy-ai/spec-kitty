"""Shared fixtures for sync module tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from specify_cli.core.env import SYNC_DISABLE_ENV_VARS
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.clock import LamportClock
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.git_metadata import GitMetadata, GitMetadataResolver
from specify_cli.sync.project_identity import ProjectIdentity

# FR-007 leak-guard detection layer (#3115) -- moved to its own module
# (landing-fold cohesion refactor, PR #3144) because it is pure and
# hook-independent; the pytest HOOKS below stay here (pytest only
# discovers hook implementations in a conftest.py) and consume this
# import for everything they need. ``_content_fingerprint`` is re-exported
# under ``as`` (its own name) because
# ``tests/sync/test_leak_guard_fingerprint_3115.py`` imports it directly
# via ``from tests.sync.conftest import _content_fingerprint`` -- the
# explicit "as same-name" form marks the re-export as intentional so ruff's
# F401 does not flag it as unused.
from tests.sync._leak_guard import (
    _ACCEPTED_PINNED_LEAKS,
    _LEAK_GUARD_BEFORE,
    _LEAK_GUARD_INSPECTED_NODE_IDS,
    _MARKER_LEVEL_UNOBSERVED,
    _PINNED_LEAKS,
    _PINNED_LEAKS_BY_NODE_ID,
    _SUPPRESSED_INHERITED_DIRTY,
    _UNEVALUATABLE_WATCHED_ENTRIES,
    _UNWATCHED_ENTRIES,
    _WATCHED_ENV_KEYS,
    _WATCHED_GLOBALS,
    _compute_dirty_lines,
    _evaluate_pin,
    _leak_guard_snapshot,
)
from tests.sync._leak_guard import _content_fingerprint as _content_fingerprint


@pytest.fixture
def temp_queue(tmp_path: Path) -> OfflineQueue:
    """Temporary SQLite queue for testing."""
    db_path = tmp_path / "test_queue.db"
    return OfflineQueue(db_path=db_path)


@pytest.fixture
def mock_auth(monkeypatch) -> MagicMock:
    """Patched TokenManager accessor used by the sync layer.

    Post-WP08 the sync layer reaches for ``specify_cli.auth.get_token_manager``
    instead of the legacy ``AuthClient``. This fixture installs a MagicMock
    so tests that previously depended on ``is_authenticated`` / team slug
    lookups continue to see an authenticated state without needing a real
    ``StoredSession`` on disk.
    """
    # Build a session-like mock with a single default team.
    team = MagicMock()
    team.id = "test-team"
    team.slug = "test-team"

    session = MagicMock()
    session.default_team_id = "test-team"
    session.teams = [team]
    session.email = "tester@example.com"
    session.name = "Test User"

    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = session

    def _get_tm():
        return tm

    # Patch the process-wide factory at its canonical location. This covers
    # every call site because all sync-layer modules call it via
    # ``from specify_cli.auth import get_token_manager`` rebinding each time.
    monkeypatch.setattr("specify_cli.auth.get_token_manager", _get_tm)
    return tm


@pytest.fixture
def temp_clock(tmp_path: Path) -> LamportClock:
    """LamportClock persisted to tmp_path (avoids touching ~/.spec-kitty/)."""
    clock_path = tmp_path / "clock.json"
    return LamportClock(value=0, node_id="test-node-id", _storage_path=clock_path)


@pytest.fixture
def mock_config() -> MagicMock:
    """Mock SyncConfig that returns a local server URL."""
    config = MagicMock(spec=SyncConfig)
    config.get_server_url.return_value = "https://test.spec-kitty.dev"
    return config


@pytest.fixture
def mock_identity() -> ProjectIdentity:
    """Mock project identity with all fields populated."""
    return ProjectIdentity(
        project_uuid=uuid4(),
        project_slug="test-project",
        node_id="test-node-123",
        build_id="test-build-id-0000-0000-000000000001",
    )


@pytest.fixture
def empty_identity() -> ProjectIdentity:
    """Empty project identity (no fields populated)."""
    return ProjectIdentity()


@pytest.fixture
def mock_git_metadata() -> GitMetadata:
    """Mock git metadata for testing."""
    return GitMetadata(
        git_branch="test-branch",
        head_commit_sha="a" * 40,
        repo_slug="test-org/test-repo",
    )


@pytest.fixture
def mock_git_resolver(mock_git_metadata: GitMetadata) -> MagicMock:
    """Mock GitMetadataResolver that returns fixed metadata."""
    resolver = MagicMock(spec=GitMetadataResolver)
    resolver.resolve.return_value = mock_git_metadata
    resolver.repo_root = Path("/nonexistent/test-repo")
    return resolver


@pytest.fixture
def emitter(
    temp_queue: OfflineQueue,
    mock_auth: MagicMock,
    temp_clock: LamportClock,
    mock_config: MagicMock,
    mock_identity: ProjectIdentity,
    mock_git_resolver: MagicMock,
) -> EventEmitter:
    """EventEmitter wired to temp queue, isolated clock, mock identity, and mock git resolver.

    ``mock_auth`` is included for its monkeypatch side-effect (installs a
    fake ``get_token_manager``); the emitter itself reaches for that
    accessor internally so no ``auth`` kwarg is needed post-WP08.
    """
    del mock_auth  # side-effect-only dependency
    em = EventEmitter(
        clock=temp_clock,
        config=mock_config,
        queue=temp_queue,
        ws_client=None,
        _identity=mock_identity,  # Pre-populate with mock identity
        _git_resolver=mock_git_resolver,  # Pre-populate with mock git resolver
    )
    return em


@pytest.fixture(autouse=True)
def _isolate_pre_review_gate_sync_toggles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset the sync-disable toggles the pre-review gate reuses, per test (#2794/#2809).

    Mirrors the fixture at
    ``tests/specify_cli/cli/commands/agent/conftest.py`` (added under #2794).
    The pre-review regression gate reuses the sync layer's process-wide
    opt-outs ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` / ``SPEC_KITTY_SYNC_DISABLE``
    (the canonical ``core.env.SYNC_DISABLE_ENV_VARS``). In the
    whole-tree parallel run (``-n auto --dist loadfile``) one of those vars
    can be present in the xdist worker -- leaked mid-run from a sibling test
    or daemon path -- which silently *skips* sync-dependent assertions in
    ``tests/sync/`` and reds tests that assert a live sync diagnostic fired
    (issue #2809). Unsetting both toggles before every test in this package
    makes those tests worker- and order-independent, and neutralises the
    ``monkeypatch.setenv`` "restore-to-a-leaked-value" perpetuation.

    Tests that need a toggle set set it themselves inside the test body
    (after this fixture runs), so they are unaffected. No production
    behaviour changes -- this only isolates the test env.

    Note: this fixture only guards against a *leaked toggle* silently
    disabling sync. It does not -- and cannot -- paper over a genuine
    live-connection failure in the sync layer (e.g. a real ``Connection
    refused`` from the ``final_sync`` phase), which is orthogonal to what
    this fixture isolates. (This scope note originally cross-referenced the
    then-open #2782 P0; #2782 has since been resolved as a corrected test
    contract and its reproduction retired.)
    """
    for _name in SYNC_DISABLE_ENV_VARS:
        monkeypatch.delenv(_name, raising=False)


@pytest.fixture
def emitter_without_identity(
    temp_queue: OfflineQueue,
    mock_auth: MagicMock,
    temp_clock: LamportClock,
    mock_config: MagicMock,
    empty_identity: ProjectIdentity,
    mock_git_resolver: MagicMock,
) -> EventEmitter:
    """EventEmitter with empty identity (simulates non-project context)."""
    del mock_auth  # side-effect-only dependency
    em = EventEmitter(
        clock=temp_clock,
        config=mock_config,
        queue=temp_queue,
        ws_client=None,
        _identity=empty_identity,  # Pre-populate with empty identity
        _git_resolver=mock_git_resolver,  # Pre-populate with mock git resolver
    )
    return em


@pytest.fixture(autouse=True)
def _consented_checkout_by_default(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Treat the checkout under test as consented, unless the test says otherwise.

    Consent became **opt-in** in spec-kitty#3030 (absorbing #3031): an
    unconfigured checkout now resolves ``effective_sync_enabled = False``, which
    is the fix for the 2026-07-27 breach where five never-opted-in projects were
    delivered to a hosted instance.

    Almost every test in this package exercises *transport* behaviour — batching,
    retry hygiene, error surfacing, offline replay — in a throwaway tmp repo that
    has no consent record and never had one. Under opt-in consent those tests
    short-circuit with ``sync_disabled`` before reaching the behaviour they
    assert, which is a fixture artefact, not a finding.

    This fixture restores their premise explicitly rather than weakening the
    production default. It patches only the routing/emit consent read, so:

    * consent itself is still covered, by suites that assert on the real
      resolver — ``tests/sync/test_routing.py`` and the upstream pins in
      ``tests/sync/test_sync_consent_default_deny.py``, neither of which calls
      the patched seam; and
    * a test that *wants* the denial can still opt out with
      ``monkeypatch.setattr(..., lambda *a, **k: False)``.

    Named rather than implicit so a future reader can tell that these suites
    assume consent, instead of inferring it from a green run.

    **Extended for #3030 M1/M1-1.** The emitter no longer reads
    ``is_sync_enabled_for_checkout`` at all: the capture gate, the drain-blocked
    classification and the WebSocket publish decision all resolve consent per project
    through ``EventEmitter._project_consents_to_capture``. Patching only the old seam
    would leave this fixture patching a name production never consults — green for the
    wrong reason — so the per-project predicate is patched too.

    **Narrowed for #3167.** Of the two old seams only ``sync/runtime.py``'s survives:
    it binds the routing predicate at module import and reads it in
    ``_auto_start_enabled``, so the patch
    still lands on a name production consults. ``sync/batch.py``'s was removed —
    see the comment on the ``setattr`` call below for why, and why ``raising=False``
    went with it.

    Most emitters in this package are built with no ``_identity``, so they resolve the
    *ambient* repo's uuid, for which a throwaway home has no record. That is what
    makes the premise a fixture concern rather than a per-test one.
    """
    # Never touch the suites that assert on the real predicate. Without this guard the
    # fixture would mask the very pins it must not weaken the moment they go green —
    # and a blanket grant is exactly the mutant those pins exist to catch.
    #
    # ``capture_gate`` is listed alongside ``consent`` because
    # ``test_capture_gate_project_identity_3030.py`` pins the per-project capture gate
    # bidirectionally without the word "consent" in its filename.
    protected = ("consent", "capture_gate")
    name = Path(str(request.node.fspath)).name
    if any(token in name for token in protected):
        return

    # ``sync/emitter.py`` is deliberately absent here: #3030 M1-1 removed the import,
    # so patching the name there would only *create* an attribute nothing reads and
    # imply the emitter still consults cwd.
    #
    # ``specify_cli.sync.batch.is_sync_enabled_for_checkout`` used to be patched
    # alongside this one, in a two-element loop. #3167 retired the queue-backed drain,
    # and with it ``_is_checkout_sync_enabled_for_batch`` and the ``from .routing
    # import is_sync_enabled_for_checkout`` that bound the name in ``sync/batch.py``.
    # That seam therefore named an attribute that no longer exists — and because of
    # ``raising=False`` it did not error: ``monkeypatch.setattr`` **created** the
    # attribute instead, on a module where nothing reads it. Not a patch that fails,
    # a patch that succeeds at nothing — precisely the "green for the wrong reason"
    # this fixture's own docstring warns about two paragraphs up. It is removed rather
    # than kept resolvable, because a resolvable name is not a consulted one.
    #
    # ``raising=False`` is gone with it, deliberately. The surviving target is bound at
    # ``sync/runtime.py`` at import and read inside ``_auto_start_enabled``, so the default
    # ``raising=True`` **resolves** rather than errors — while a future rename or typo
    # here now fails loudly at setup instead of quietly granting consent to nothing.
    # That matters because nothing else covers this line:
    # ``scripts/check_patch_targets.py`` resolves ``patch("...")`` target strings in CI
    # but its regex never matches ``monkeypatch.setattr("...")``, so ``raising=True``
    # is the whole guard. Demonstrated by mutation rather than assumed (#3167 T013):
    # pointing this string at the deleted ``sync.batch`` name errors this package's
    # every unprotected test in SETUP with ``AttributeError: 'module' object at
    # specify_cli.sync.batch has no attribute 'is_sync_enabled_for_checkout'``.
    monkeypatch.setattr("specify_cli.sync.runtime.is_sync_enabled_for_checkout", lambda *args, **kwargs: True)

    monkeypatch.setattr(
        "specify_cli.sync.emitter.EventEmitter._project_consents_to_capture",
        lambda *args, **kwargs: True,
    )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item: pytest.Item):
    """FR-007: snapshot watched state before this test's own setup runs."""
    _LEAK_GUARD_BEFORE[item.nodeid] = _leak_guard_snapshot()
    _LEAK_GUARD_INSPECTED_NODE_IDS.append(item.nodeid)
    return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None):
    """FR-007: fail the polluter, not the victim.

    Paired with ``pytest_runtest_setup`` above: compares the state
    ``_leak_guard_snapshot()`` sees before this test's setup against the
    state it sees after this test's own teardown, across every symbol in
    ``_WATCHED_GLOBALS``, the ``_WATCHED_ENV_KEYS`` env vars, the CWD, and
    the live-thread set. Fails the test -- naming the symbol (or the
    thread's ``name`` and ``target``) and this test's own ``nodeid`` -- if
    anything watched differs.

    **Why a hook, not an autouse fixture.** The first implementation used a
    plain ``@pytest.fixture(autouse=True)`` with a ``yield``. Measured
    against a real test (not assumed): ``tests/sync/conftest.py`` already
    has two other autouse fixtures that request ``monkeypatch``
    (``_isolate_pre_review_gate_sync_toggles``,
    ``_consented_checkout_by_default``). Once ``monkeypatch`` is a
    dependency of *any* fixture in the closure, pytest's fixture-ordering
    placed a plain no-dependency autouse fixture's teardown BEFORE
    ``monkeypatch``'s own restore -- reproduced with a minimal 3-fixture
    ``--setup-show`` trace, and unchanged even after making the guard
    fixture explicitly depend on ``monkeypatch`` too (still torn down
    first: SETUP order was ``monkeypatch`` -> the-other-autouse-fixture ->
    mine; TEARDOWN was the exact reverse). Concretely, a fixture-based
    guard read ``tests/sync/test_consent_field_fault_3030.py``'s
    ``monkeypatch.chdir(root)`` (a correctly-self-restoring, non-leaking
    pattern) as a live CWD leak on 145 of 2122 tests in the
    ``fast-tests-sync`` selection -- a false-positive storm, not a real
    finding (WP04's own inventory found exactly one ``os.chdir`` leak
    candidate, already reset-seamed). A ``pytest_runtest_teardown``
    *hookwrapper* sidesteps the whole fixture-ordering question: yielding
    inside it waits for every non-wrapper implementation of the hook --
    including the builtin runner's, which is what actually calls
    ``item.teardown()`` and tears down every real fixture, ``monkeypatch``
    included -- so the code after ``yield`` here is guaranteed to run after
    ALL of this test's own fixture teardown has completed, not merely
    after whichever fixtures happened to land in a favourable position in
    the closure order. Verified with the same minimal reproduction: a
    ``monkeypatch.chdir``-based test is correctly left clean, and a raw
    ``os.chdir`` with no restore is correctly flagged.

    **Detects and fails; does not repair.** Two reasons, both load-bearing:

    1. Restoring here would silence the very pins this guard exists to
       protect -- the ``tests/sync/conftest.py:242-259`` filename-token-guard
       precedent (WP05's explicit prohibition) is a shared fixture whose
       "helpful" behaviour quietly hid the thing it was supposed to police.
    2. Because nothing is restored, a dirty value left by test N becomes
       test N+1's own *baseline* -- so if N+1 does not change it further,
       N+1's before/after snapshots match and N+1 is NOT flagged. Only the
       test whose run actually introduced the change is flagged. That is
       what makes this "fail the polluter, not the victim" rather than
       "fail whichever test happens to run next."

    **Named blind spot: a polluter that restores to the same WRONG value it
    found is invisible to a per-test before/after diff.** This is the exact
    shape the mission's own control case can take: if a test's setup and
    teardown are each individually self-consistent (its own "before" always
    equals its own "after") but that shared value is itself incorrect
    process-wide -- e.g. every test in a file runs with a watched slot
    already cleared from a PRIOR, unrelated failure, and each test's own
    teardown puts it back to that same cleared state -- no single test's
    diff ever shows a change, so nothing is ever flagged, even though the
    slot is wrong for the whole session. Demonstrated externally (reviewer
    finding, WP05 review round 1): with the control case's own restore
    mechanism suppressed at every call site across its file, a per-test
    census of the same shape as this one reported zero flagged nodes, while
    a downstream test reded on its own domain assertion instead -- the
    leak was real, but it surfaced as a victim's failure, not a polluter's,
    because the "before" this guard would have captured was already dirty
    for every test in that run. Within FR-007's own design (a per-test
    diff can only ever see a *transition*, not an absolute correctness
    check against a known-good value), so this is not a defect to fix
    here -- it is a reach limit, named beside the other unwatched entries
    (``_UNWATCHED_ENTRIES``) so a reader of a clean run does not mistake
    "nothing flagged" for "nothing wrong that this shape of guard could
    ever see."

    C-002 ("fixtures restore, they do not clear") governs fixtures that
    *own* process-global state -- e.g. ``_consented_checkout_by_default``
    above, or a fixture that sets an env var it must put back. It does not
    apply here: this hook owns no state, it only observes.

    Scoped to WP04's inventory (FR-006), not to WP06's attribution -- ships
    whether or not the sync-half attribution ever converges (H4). Scoped to
    ``tests/sync/`` structurally, too: pytest only calls a conftest.py's
    hook implementations for items collected under that conftest's own
    subtree (verified with a two-directory reproduction), so this guard
    cannot fire for, and cannot protect, anything outside ``tests/sync/`` --
    including the mission's designated control case,
    ``tests/specify_cli/invocation/test_propagator_consent_gate_3030.py``,
    which lives elsewhere.

    **Teardown safety, added this revision (reviewer MEDIUM).** The first
    version had a bare ``result = yield`` -- if any real fixture's own
    teardown raised, that exception surfaced AT the ``yield`` and propagated
    immediately: the snapshot/compare below never ran (a pinned node's
    strict check silently lapsed for that run) and
    ``_LEAK_GUARD_BEFORE[nodeid]`` was never popped (this guard leaking its
    own snapshot dict, one entry per failing-teardown test, for the rest of
    the session). Fixed by catching the exception from ``yield`` instead of
    letting it propagate past this hook, running the SAME check regardless,
    and only then re-raising -- chained (``raise ... from``) if this guard
    ALSO wants to fail, so both the original teardown failure and any leak
    this guard found are visible, not one silently replacing the other.
    Built and proved against a synthetic fixture whose teardown raises (a
    real one could not be constructed without editing an owned-elsewhere
    test file) -- see the WP05 transition note.
    """
    teardown_exc: BaseException | None = None
    result: object = None
    try:
        result = yield  # let ALL real fixture teardown -- including monkeypatch's -- run first, but don't let its exception skip the check below
    except BaseException as exc:  # noqa: BLE001 - must observe every teardown outcome, not just the clean ones, then re-raise (see below)
        teardown_exc = exc

    before = _LEAK_GUARD_BEFORE.pop(item.nodeid, None)
    if before is None:  # pragma: no cover - defensive; setup always runs first
        if teardown_exc is not None:
            raise teardown_exc
        return result

    after = _leak_guard_snapshot()
    dirty = _compute_dirty_lines(before, after)

    pin = _PINNED_LEAKS_BY_NODE_ID.get(item.nodeid)
    if pin is not None:
        failure_lines = _evaluate_pin(pin, dirty, before, item.nodeid)
    elif dirty:
        failure_lines = [
            f"[FR-007 leak guard] {item.nodeid} left inventoried "
            "process-global state dirty "
            "(docs/development/process-global-inventory-3115.md):",
            *dirty,
        ]
    else:
        failure_lines = None

    if failure_lines is not None:
        message = "\n".join(failure_lines)
        if teardown_exc is not None:
            message += (
                f"\n\n[FR-007 leak guard] this test's own teardown ALSO raised "
                f"{teardown_exc!r} -- see the chained exception for its traceback."
            )
        try:
            pytest.fail(message, pytrace=False)
        except BaseException as leak_exc:  # noqa: BLE001 - re-raised immediately, chained onto the teardown exception if there was one
            if teardown_exc is not None:
                raise leak_exc from teardown_exc
            raise

    if teardown_exc is not None:
        raise teardown_exc
    return result


def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:  # noqa: ARG001
    """FR-007 positive control (H8 / NFR-008): report reach, not just verdicts.

    A guard that only ever prints on failure cannot be told apart from a
    guard that never ran. Every session under ``tests/sync/`` prints how many
    tests it inspected and which WP04 inventory entries it did not watch,
    with the reason -- so "clean" and "never armed" are never confused.

    **Known undercount under xdist, stated in the printed line itself, not
    only here** (reviewer MEDIUM: the artefact must carry the caveat, not
    just the WP report -- CI logs are read without the report). Measured
    directly: a real ``-n 4 --dist loadfile`` run that inspected 2122 tests
    printed ``inspected 0 test(s)``, because each xdist worker is a
    separate process holding its own ``_LEAK_GUARD_INSPECTED_NODE_IDS``,
    and only the controller process -- which never runs a test itself --
    calls this hook. Full cross-worker aggregation (``workerinput`` /
    ``pytest_report_to_serializable``) was judged out of proportion for a
    reporting-only gap; the cheap fix is the caveat below, printed whenever
    xdist is active so it survives to CI logs even when nobody reads this
    docstring.
    """
    inspected = len(_LEAK_GUARD_INSPECTED_NODE_IDS)
    watched_count = len(_WATCHED_GLOBALS) + len(_WATCHED_ENV_KEYS) + 1  # +1: CWD (E53)
    terminalreporter.write_sep("-", "FR-007 leak guard coverage")

    numprocesses = getattr(config.option, "numprocesses", None)
    running_under_xdist_controller = bool(numprocesses) and not hasattr(config, "workerinput")
    if running_under_xdist_controller:
        terminalreporter.write_line(
            f"[FR-007 leak guard] inspected {inspected} test(s) IN THIS PROCESS under "
            f"tests/sync/ -- xdist is active (-n {numprocesses}). Every test actually ran "
            "in a separate worker process, each with its OWN counter; this controller "
            "process never runs a test itself, so this number is NOT the session total. "
            "'inspected 0' here does NOT mean the guard never armed -- it means xdist is "
            "on. For an accurate total, re-run with '-n0' / '-p no:xdist', or read a "
            "worker's own captured output."
        )
    else:
        terminalreporter.write_line(f"[FR-007 leak guard] inspected {inspected} test(s) under tests/sync/.")
    terminalreporter.write_line(
        f"[FR-007 leak guard] watched {watched_count} process-global symbol(s) "
        f"({len(_WATCHED_GLOBALS)} module attributes + {len(_WATCHED_ENV_KEYS)} "
        "os.environ key(s) + CWD), plus the live-thread set."
    )
    terminalreporter.write_line(
        f"[FR-007 leak guard] {len(_UNWATCHED_ENTRIES)} inventory row-group(s) "
        "were NOT watched:"
    )
    for entry_ids, reason in _UNWATCHED_ENTRIES:
        terminalreporter.write_line(f"  - {entry_ids}: {reason}")

    if _UNEVALUATABLE_WATCHED_ENTRIES:
        # Platform-import failures (rot control fix, CI finding): the entry's
        # FILE exists but cannot be imported here -- not staleness, printed
        # separately so "the registry is stale" and "this platform can't
        # evaluate it" are never confused. See _resolve_watched_global's
        # docstring.
        terminalreporter.write_line(
            f"[FR-007 leak guard] {len(_UNEVALUATABLE_WATCHED_ENTRIES)} watched "
            "entry(ies) could not be evaluated on this platform (NOT a stale "
            "registry -- their module files exist and import fine elsewhere):"
        )
        for entry_id, reason in _UNEVALUATABLE_WATCHED_ENTRIES.items():
            terminalreporter.write_line(f"  - {entry_id}: {reason}")

    # Pinned-leak visibility (#3130) -- "un-forgettable", per the operator's
    # own framing: printed every session a pinned node actually ran, not
    # only when something goes wrong. Subject to the same per-process xdist
    # undercount as "inspected" above (each worker holds its own
    # _ACCEPTED_PINNED_LEAKS); the caveat is repeated rather than assumed
    # read once.
    #
    # **Locator corrected, round-3 review**: the first version of this
    # caveat claimed a worker's own acceptances "are in its own captured
    # output" -- false, measured: pytest_terminal_summary is a controller-
    # only hook under xdist and is never invoked in a worker process at
    # all, so `grep -c "ACCEPTED (#3130)"` across a worker's output returns
    # 0, always. The load-bearing summary line above DOES print correctly
    # under -n 8 and -n 4 (the operator's "un-forgettable" requirement is
    # met by that line); only the "where else to look" pointer was wrong.
    # Corrected to match the sibling "inspected" caveat's actual, truthful
    # remedy.
    terminalreporter.write_line(
        f"[FR-007 leak guard] {len(_PINNED_LEAKS)} node(s) are pinned to a known, filed leak "
        "(#3130) -- a TEMPORARY pin on a verified defect, not a permanent exemption; removing "
        "an entry in tests/sync/conftest.py is how a fix gets proven:"
    )
    if running_under_xdist_controller:
        terminalreporter.write_line(
            "  (this controller process ran no tests itself, and pytest_terminal_summary is "
            "never invoked in an xdist worker either -- per-node ACCEPTED lines are not "
            "printed anywhere in this mode. For an accurate per-node accounting, re-run with "
            "'-n0' / '-p no:xdist' -- same remedy as 'inspected' above)"
        )
    marker_level_unobserved_by_node: dict[str, list[str]] = {}
    for node_id, marker in _MARKER_LEVEL_UNOBSERVED:
        marker_level_unobserved_by_node.setdefault(node_id, []).append(marker)
    if _ACCEPTED_PINNED_LEAKS:
        for node_id, accounted_lines in _ACCEPTED_PINNED_LEAKS:
            pin = _PINNED_LEAKS_BY_NODE_ID[node_id]
            terminalreporter.write_line(f"  - ACCEPTED ({pin.issue}): {node_id} -- {pin.note}")
            excused = marker_level_unobserved_by_node.get(node_id)
            if excused:
                terminalreporter.write_line(
                    f"    (markers excused as unobservable this run, per-marker baseline "
                    f"state: {excused!r})"
                )
            for line in accounted_lines:
                terminalreporter.write_line(f"    {line.strip()}")
    if _SUPPRESSED_INHERITED_DIRTY:
        # requires_clean_baseline pins whose own watched entry was already
        # dirty coming in -- unobserved this run, not accepted-as-leaking
        # and not fixed either. A third, distinct outcome from the two
        # above; kept out of _ACCEPTED_PINNED_LEAKS on purpose.
        for node_id in _SUPPRESSED_INHERITED_DIRTY:
            pin = _PINNED_LEAKS_BY_NODE_ID[node_id]
            terminalreporter.write_line(
                f"  - UNOBSERVABLE this run ({pin.issue}, requires_clean_baseline): {node_id} -- "
                f"its own before-snapshot for {pin.baseline_watch!r} was already dirty, so an empty "
                "diff here is not evidence of a fix"
            )
    if (
        not _ACCEPTED_PINNED_LEAKS
        and not _SUPPRESSED_INHERITED_DIRTY
        and not _MARKER_LEVEL_UNOBSERVED
        and not running_under_xdist_controller
    ):
        terminalreporter.write_line(
            f"  (none of the {len(_PINNED_LEAKS)} pinned node-ids ran in this process this session)"
        )
