"""Acceptance harness for tracker egress refusal (Mission `tracker-egress-refusal-3108-01KYWF1R`).

Stage 1 of the Mission (`plan.md`): this file is the whole deliverable of WP01, and it is
committed **before** any product code lands (WP03/WP04/WP05). Per the charter's ATDD rule, the
refusing pins in this file are RED on purpose, on the un-gated tree, until those later work
packages land the Channel-2 (`tracker.egress`) gate. Only the positive/consenting controls and the
harness's own non-vacuity checks are required to pass at this stage. See ``## Definition of Done``
in ``WP01-acceptance-harness.md`` for the exact exit criterion; a reviewer applying a blanket
"the suite must be green" rule to this file is applying the wrong rule to this WP.

Four independent mechanisms have been measured to produce a green refusal test with **no gate
built at all** (FR-018). Every fixture in this file defeats all four simultaneously:

* **H1 -- ownership mode.** Every fixture pins ``doctrine: {mode: spec_kitty_authoritative}``.
  Under the default ``external_authoritative``, a *consenting* push captures only
  ``['<cmd>', '--json', 'list']`` -- the sentinel never reaches ``create``.
* **H2 -- injection point.** The recorder *is* a real ``#!``-script on disk, named through the
  machine-global tracker credential file (the same path ``factory.py``'s ``build_connector``
  reads). ``SubprocessCommandRunner`` is not exported from ``spec_kitty_tracker.__all__`` and
  ``build_connector`` passes no runner, so there is no injection seam to patch, and none of
  ``_build_engine`` / ``build_connector`` / ``SyncEngine`` / ``LocalTrackerService`` /
  ``TrackerService`` are patched anywhere in this file (SC-020 pin below).
* **H3 -- arming.** Every fixture sets ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` explicitly (never
  inherited) and every refusal assertion checks refusal **text**, never a bare exit code, plus a
  negative pin (US1 sc3) proving the un-armed abort message is not what matched.
* **H8 -- the store is seeded.** Every push/run fixture seeds the tracker store with the sentinel
  issue via ``asyncio.run(store.upsert_issue(...))`` *before* the command runs -- an empty store
  never reaches ``create_issue`` (``SyncEngine.push`` iterates ``store.list_issues`` first).

Hazard 7 (this directory's own autouse fixture) -- read before touching the US5 (hosted) tests
------------------------------------------------------------------------------------------------
``tests/sync/tracker/conftest.py`` defines an ``autouse=True`` fixture that patches
``saas_client._fetch_access_token_sync`` to whatever ``mock_credential_store`` fixture the test
file defines, falling back to a ``MagicMock`` returning ``"test-access-token"`` when no such
fixture exists. Left unneutralised, every hosted control in this file would sail past the token
check into a real ``httpx`` call and trip the HTTP trip-wire -- which would misread as a gate. This
file defines its own ``mock_credential_store`` fixture below, whose ``get_access_token()`` returns
``None``, restoring the real ``No valid access token`` base behaviour the US5 controls are written
against (re-derived and quoted from inside this directory, per T007's validation clause).

Why the hosted (US5) cells construct ``TrackerService`` / ``SaaSTrackerService`` directly instead
of going through ``typer.testing.CliRunner`` -- a recorded DEPARTURE, not a resolution
---------------------------------------------------------------------------------------------
``plan.md`` Stage 5 instructs that SC-005 and SC-005a's hosted-destination cells "run end to end
through the CLI." This file's US5 cells do **not** do that, and this is recorded here as an
enlarged residual against that clause (see also ``research.md`` / plan.md §7.3's open items),
not as something this WP resolved.

Measured: ``spec_kitty tracker sync push`` / ``list-tickets --provider jira`` on a SaaS-backed
binding calls ``_check_sync_readiness`` / ``_check_readiness``, whose auth probe
(``saas.readiness._probe_auth``) asks ``get_token_manager().is_authenticated`` -- a *different*,
process-wide authentication signal, wholly orthogonal to the tracker-egress consent gate this
Mission is about. In an isolated ``HOME`` that probe is always ``False``, so a literal CLI
invocation is rejected at ``MISSING_AUTH`` (``"No SaaS authentication token is present."``) before
ever reaching ``TrackerService``, ``SaaSTrackerService`` or ``SaaSTrackerClient._request`` --
the exact code this Mission's gate lives in and around. Faking that unrelated auth signal (e.g.
patching ``get_token_manager``) to force a CLI run through is a bigger and less honest patch than
simply constructing the real, un-mocked ``TrackerService`` / ``SaaSTrackerService`` the CLI command
itself would have constructed, and calling its real method. Neither class is in the H2 patch-site
prohibition list (that list is about not *stubbing out* ``_build_engine`` /
``SyncEngine`` / etc. -- it says nothing against constructing the real classes directly). Every
hosted assertion in this file therefore exercises real, unpatched ``TrackerService`` /
``SaaSTrackerService`` / ``SaaSTrackerClient`` code, from the same entry point the CLI command
would have reached it from, one layer below the CLI's own readiness pre-flight -- sound as far as
it goes, but it is **not** "end to end through the CLI" and must not be described as satisfying
that clause. A follow-up issue is tracked for ``saas.readiness._probe_auth`` blocking hosted
tracker CLI acceptance coverage; this file's US5 coverage is honestly **resolved-negative** on
the CLI-literal reading of Stage 5, and **resolved-positive** only one layer below it. The
*local* (US1-4) cells carry no such gap -- ``_check_sync_readiness`` short-circuits entirely for
a local binding via ``_is_local_binding()`` -- and are run through the real CLI via ``CliRunner``,
so Stage 5's "through the CLI" clause is fully satisfied there.

Scope decision recorded for T006 step 2 (the bind counters)
-------------------------------------------------------------
Both bind-counter patch targets (``specify_cli.tracker.local_service.tracker_egress_verdict`` and
``specify_cli.tracker.saas_client.tracker_egress_verdict``) do not exist on the un-gated base --
WP04/WP05 land the names. Installing a delegating wrapper against a name that does not exist
raises ``AttributeError`` at *install* time, which **is** the committed red T006 describes:
*"Until WP04 and WP05 land there is no name to wrap at either target ... let those assertions be
part of the committed red."* This file wires each counter once, against a representative refusing
cell per destination (``test_local_bind_counter_wired_against_named_target`` /
``test_hosted_bind_counter_wired_against_named_target``), rather than duplicating the wrapper
install in all thirteen refusing cells -- duplicating an assertion that fails identically (and for
the identical reason -- the target does not exist) thirteen times adds no additional evidence and
makes the primary leak-focused assertions in each cell harder to read. Once WP04/WP05 land, extend
those two representative tests' cell coverage per T006's own table; do not delete them.

US1 sc4's exemption (T006/T007): **no bind counter is asserted** in the hosted-sync queue-drain
cell (``test_us1_sc4_hosted_drain_unaffected_by_tracker_key`` below). Neither the local nor the
hosted ``tracker_egress_verdict`` name is ever called on that path -- it is the hosted body/event
drain (``BackgroundSyncService.drain_body_uploads_only``), a different transport with its own,
unrelated consent chain, and this Mission changes nothing about it.

POSIX scope (Hazard 6)
-----------------------
The recorder is a ``#!``-script made executable via ``chmod``, and ``subprocess.run`` is invoked
with no shell. Windows would need a ``.cmd``/``.bat`` sibling this Mission has no runner to prove,
so the whole module is skipped on ``nt`` rather than silently claiming cross-platform coverage it
has not earned.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import importlib
import json
import os
import stat
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import httpx
import pytest
import typer
from typer.testing import CliRunner

from spec_kitty_tracker import (
    CanonicalIssue,
    CanonicalIssueType,
    CanonicalStatus,
    ExternalRef,
)

from specify_cli.tracker.config import load_tracker_config
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.tracker.credentials import TrackerCredentialStore
from specify_cli.tracker.local_service import LocalTrackerService
from specify_cli.tracker.saas_client import SaaSTrackerClientError, TrackerEgressRefusedError
from specify_cli.tracker.saas_service import SaaSTrackerService
from specify_cli.tracker.service import TrackerService
from specify_cli.tracker.store import TrackerSqliteStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    # Selection marker, added after WP07 measured that this file carried only a `skipif` and was
    # therefore **orphaned -- selected by zero CI gates**. This is the mission's acceptance
    # harness: the suite that proves the leak is closed. A harness CI never runs cannot turn the
    # branch red, which is the same class of false green the whole mission exists to eliminate,
    # aimed at itself. `integration` rather than `unit` because these cells spawn a real
    # subprocess recorder and open a real sqlite store, which `unit` explicitly excludes.
    pytest.mark.integration,
    pytest.mark.skipif(
        os.name == "nt",
        reason=(
            "Hazard 6: the recorder is a #!-script made executable via chmod and invoked by "
            "subprocess.run with no shell. Windows needs a .cmd/.bat sibling this Mission has "
            "no runner to prove; the skip is recorded here rather than silently claiming "
            "cross-platform coverage that was never measured."
        ),
    ),
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

# ---------------------------------------------------------------------------
# Sentinel fixtures data -- distinctive so a leak is legible in a diff.
# ---------------------------------------------------------------------------

SENTINEL_TITLE = "ACME Holdings carve-out"
CONFIDENTIAL_BODY = "confidential body"
SENTINEL_ASSIGNEE = "alice@acme.example"
SENTINEL_LABEL = "secret-label"

#: A well-formed UUID; identity must RESOLVE (Hazard 8). Any well-formed value works -- the
#: consent chain only requires it to parse, not to belong to a real registered project.
CONSENTING_PROJECT_UUID = "6f1c2f2e-59a1-4a1f-9a2e-0f1c2f2e59a1"

#: The base's own arming-disabled message (core/saas_sync_config.py) -- the negative pin (US1 sc3)
#: asserts a refusal's text is never confusable with this one.
_ARMING_DISABLED_FRAGMENT = "Hosted SaaS sync is not enabled on this machine. Set"

RUNNER = CliRunner()


# ---------------------------------------------------------------------------
# T002 -- isolation, arming, trip-wires
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_home_and_arming(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated HOME/SPEC_KITTY_HOME and explicit arming, per test, never inherited.

    Both the machine-global consent index and the machine-global tracker credential file live
    under SPEC_KITTY_HOME (``get_runtime_root()``); an isolated HOME keeps every other
    home-relative read (auth, git config) from leaking between tests too.
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    return home


@pytest.fixture
def mock_credential_store() -> MagicMock:
    """Neutralise the directory's autouse token-bridge fixture (Hazard 7).

    ``get_access_token`` returns ``None`` so ``saas_client._fetch_access_token_sync`` returns
    ``None`` too, restoring the real ``No valid access token`` base behaviour the US5 controls in
    this file are written against, instead of the legacy suites' ``"test-access-token"`` default.
    """
    store = MagicMock(name="mock_credential_store")
    store.get_access_token.return_value = None
    store.get_team_slug.return_value = "team-acme"
    store.get_refresh_token.return_value = None
    return store


@dataclass
class _HttpTripwire:
    """Counts, and refuses to perform, every ``httpx.Client.request`` attempt."""

    attempts: int = 0


@pytest.fixture
def http_tripwire(monkeypatch: pytest.MonkeyPatch) -> _HttpTripwire:
    wire = _HttpTripwire()

    def _tripped(self: httpx.Client, method: str, url: str, *args: Any, **kwargs: Any) -> Any:
        wire.attempts += 1
        raise AssertionError(f"HTTP trip-wire fired: {method} {url} attempted to reach the network. A refused command must perform zero HTTP attempts (NFR-002).")

    monkeypatch.setattr(httpx.Client, "request", _tripped)
    return wire


@dataclass
class _SubprocessCounter:
    """Counts ``subprocess.run`` invocations without changing behaviour (counting only)."""

    count: int = 0


@pytest.fixture
def subprocess_counter(monkeypatch: pytest.MonkeyPatch) -> _SubprocessCounter:
    counter = _SubprocessCounter()
    real_run = subprocess.run

    def _counted(*args: Any, **kwargs: Any) -> Any:
        counter.count += 1
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _counted)
    return counter


def test_smoke_arming_is_explicit_and_tripwire_fires_when_tripped(
    http_tripwire: _HttpTripwire,
) -> None:
    """T002 validation: control the diagnostic before trusting it elsewhere in this file."""
    assert os.environ["SPEC_KITTY_ENABLE_SAAS_SYNC"] == "1"
    with httpx.Client() as client, pytest.raises(AssertionError, match="HTTP trip-wire fired"):
        client.request("GET", "https://example.invalid/probe")
    assert http_tripwire.attempts == 1


# ---------------------------------------------------------------------------
# Fixture-writer helper (T002): the sync:, tracker: and doctrine: blocks as
# explicit, independently-omittable arguments, so two fixtures rendered by
# this helper differing in exactly one argument differ by exactly one line.
# ---------------------------------------------------------------------------


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        # Only a real YAML boolean records a decision (Hazard 8) -- never a quoted string.
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


def _write_project_config(
    root: Path,
    *,
    project_uuid: str | None = None,
    project_slug: str = "acme-holdings-carve-out",
    sync_block: dict[str, Any] | None = None,
    tracker_block: dict[str, Any] | None = None,
    doctrine_block: dict[str, Any] | None = None,
) -> Path:
    """Render this project's committed ``.kittify/config.yaml``.

    Each of ``sync_block`` / ``tracker_block`` / ``doctrine_block`` is an explicit, independently
    omittable argument (``None`` means the block/key is absent, not present-with-a-null-value) so
    that two calls differing in exactly one keyword argument render files differing by exactly one
    committed line -- checkable by diffing the two rendered files.
    """
    lines: list[str] = []
    if project_uuid is not None:
        lines += ["project:", f"  uuid: {project_uuid}", f"  slug: {project_slug}"]
    if sync_block is not None:
        lines.append("sync:")
        for key, value in sync_block.items():
            lines.append(f"  {key}: {_yaml_scalar(value)}")
    if tracker_block is not None or doctrine_block is not None:
        lines.append("tracker:")
        for key, value in (tracker_block or {}).items():
            lines.append(f"  {key}: {_yaml_scalar(value)}")
        if doctrine_block is not None:
            lines.append("  doctrine:")
            for key, value in doctrine_block.items():
                lines.append(f"    {key}: {_yaml_scalar(value)}")

    config_path = root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    enabled = (sync_block or {}).get("enabled")
    if project_uuid is not None and isinstance(enabled, bool):
        if enabled:
            record_project_opt_in(project_uuid, actor="tracker-egress-refusal-test")
        else:
            record_project_opt_out(project_uuid, actor="tracker-egress-refusal-test")
    return config_path


def _project(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    return root


_DOCTRINE_SPEC_KITTY_AUTHORITATIVE = {"mode": "spec_kitty_authoritative"}


# ---------------------------------------------------------------------------
# T003 -- the recorder: a real fake executable on disk, nothing patched
# ---------------------------------------------------------------------------

_RECORDER_ISSUE_ID = "recorder-issue-1"


def _recorder_script_body(capture_path: Path) -> str:
    """A ``#!``-script that appends every argv it receives (one JSON line) and answers
    ``list``/``create``/``show``/``update`` well enough for BeadsConnector to parse.

    ``list`` must answer an empty array -- SyncEngine.push calls
    connector.list_issues before store.list_issues, and a non-empty list would divert the seeded
    issue down the update branch, voiding the whole 3-argv pair (T003 step 3).
    """
    return f"""#!{sys.executable}
import json, sys

CAPTURE = {str(capture_path)!r}
argv = sys.argv
with open(CAPTURE, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(argv) + chr(10))


def _issue():
    return {{
        "id": {_RECORDER_ISSUE_ID!r},
        "title": "recorder-issue",
        "status": "open",
        "issue_type": "task",
        "priority": 2,
        "assignee": {SENTINEL_ASSIGNEE!r},
        "labels": [{SENTINEL_LABEL!r}],
        "description": "recorder body",
    }}


if "list" in argv:
    print(json.dumps([]))
elif "create" in argv:
    print(json.dumps(_issue()))
elif "show" in argv:
    print(json.dumps(_issue()))
elif "update" in argv:
    print(json.dumps(_issue()))
else:
    print(json.dumps([]))
"""


def _make_recorder(tmp_path: Path, capture_path: Path, name: str = "fake-bd") -> Path:
    script = tmp_path / name
    script.write_text(_recorder_script_body(capture_path), encoding="utf-8")
    mode = script.stat().st_mode
    script.chmod(mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


def _read_captured(capture_path: Path) -> list[list[str]]:
    if not capture_path.exists():
        return []
    lines = capture_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _bind_recorder_credentials(command_path: Path, *, provider: str = "beads") -> None:
    """Name the recorder through the machine-global tracker credential file.

    Uses the public writer ``TrackerCredentialStore.set_provider`` (the same file
    ``factory.py``'s ``build_connector`` reads at ``command=credentials.get("command")``), not a
    hand-authored TOML file.
    """
    TrackerCredentialStore().set_provider(provider, {"command": str(command_path)})


def test_recorder_script_hand_validation_for_each_subcommand(tmp_path: Path) -> None:
    """T003 step 3 validation: run the recorder by hand for list/create/show before trusting it.

    Control the diagnostic -- if this fails, every push/pull/run acceptance cell below is
    void, and it is much easier to find out here than by misreading a 1-argv "gate".
    """
    capture = tmp_path / "capture.jsonl"
    script = _make_recorder(tmp_path, capture)

    for args, expect_id in (
        (["--json", "list"], None),
        (["--json", "create", SENTINEL_TITLE, "--type", "task"], _RECORDER_ISSUE_ID),
        (["--json", "show", _RECORDER_ISSUE_ID], _RECORDER_ISSUE_ID),
    ):
        result = subprocess.run([str(script), *args], capture_output=True, text=True, timeout=10, check=True)
        payload = json.loads(result.stdout)
        if expect_id is None:
            assert payload == []
        else:
            assert payload["id"] == expect_id

    captured = _read_captured(capture)
    assert len(captured) == 3  # golden-count: cardinality-is-contract


_FORBIDDEN_PATCH_TARGETS = (
    "_build_engine",
    "build_connector",
    "SyncEngine",
    "LocalTrackerService",
    "TrackerService",
)


def _iter_patch_call_sites(text: str, filename: str) -> list[tuple[int, str]]:
    """Parse *text* with ``ast`` and return ``(lineno, unparsed_call)`` for every
    ``<anything>.setattr(...)`` / ``patch.object(...)`` / ``patch(...)`` call expression.

    A line-based regex was measured (by review) to miss two real cases: a call whose target
    argument sits on a continuation line (``[^\\n]*`` stops at the first newline), and an
    aliased monkeypatch fixture (``mp.setattr(...)`` -- this file's own idiom in several
    tests -- never matches a pattern that requires the literal substring ``monkeypatch.``).
    Parsing the AST and inspecting ``Call`` nodes structurally is immune to both: it does not
    care about line breaks, and it matches ``.setattr(...)`` on any attribute-access base
    (``monkeypatch``, ``mp``, or any future alias) rather than a specific spelled-out name.
    """
    try:
        tree = ast.parse(text, filename=filename)
    except SyntaxError:
        return []

    sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_dot_setattr = isinstance(func, ast.Attribute) and func.attr == "setattr"
        is_patch_object = isinstance(func, ast.Attribute) and func.attr == "object" and isinstance(func.value, ast.Name) and func.value.id == "patch"
        is_bare_patch = isinstance(func, ast.Name) and func.id == "patch"
        if not (is_dot_setattr or is_patch_object or is_bare_patch):
            continue
        try:
            call_src = ast.unparse(node)
        except Exception:  # pragma: no cover - defensive, ast.unparse is stdlib and stable
            call_src = ast.dump(node)
        sites.append((node.lineno, call_src))
    return sites


def test_sc020_build_engine_never_patched_across_mission_test_files() -> None:
    """SC-020, as literally specified (T003 step 4): grep this Mission's *own* test files
    (Mission-wide, by the ``*_3108*.py`` naming convention) for a patch on ``_build_engine``
    specifically -- the single escape hatch Hazard 1 documents (``test_local_service.py``'s own
    docstring: *"We mock `_build_engine` to avoid needing the spec_kitty_tracker package"*).

    Printed input count so a scan of zero files cannot pass vacuously. This check is
    Mission-wide on purpose (SC-020 names only ``_build_engine``); the broader five-name
    prohibition below is narrower in scope -- see
    ``test_forbidden_seams_never_patched_in_this_acceptance_suite``. Parses each file with
    ``ast`` (see ``_iter_patch_call_sites``) rather than a line-scoped regex, so a
    reformatted, multi-line call site or an aliased ``mp.setattr(...)`` cannot hide a violation.
    """
    repo_root = Path(__file__).resolve().parents[3]
    mission_test_files = sorted((repo_root / "tests").rglob("*_3108*.py"))
    print(f"SC-020 INPUT COUNT: {len(mission_test_files)} Mission test file(s) scanned")
    assert mission_test_files, "SC-020 grep pin scanned zero files -- vacuous"

    violations: list[str] = []
    for test_file in mission_test_files:
        text = test_file.read_text(encoding="utf-8")
        for lineno, call_src in _iter_patch_call_sites(text, str(test_file)):
            if "_build_engine" in call_src:
                violations.append(f"{test_file}:{lineno}: {call_src}")
    assert not violations, "_build_engine patched somewhere in the Mission:\n" + "\n".join(violations)


def test_forbidden_seams_never_patched_in_this_acceptance_suite() -> None:
    """The broader five-name prohibition (``_build_engine``, ``build_connector``, ``SyncEngine``,
    ``LocalTrackerService``, ``TrackerService``) is scoped to *this acceptance suite and those
    named seams* (T003's own edge case) -- explicitly **not** a blanket Mission-wide ban (``plan.md``
    Open Items 8). A sibling work package's own test file (e.g. WP02's config-lifecycle tests)
    legitimately patches ``LocalTrackerService.__init__`` / ``SaaSTrackerService.__init__`` for
    unrelated capturing purposes; that is out of this pin's scope by design. Scanned file count
    printed so scanning zero files (a rename of this file) cannot pass vacuously. Same AST-based
    detection as the SC-020 pin above -- see ``_iter_patch_call_sites``.
    """
    this_file = Path(__file__).resolve()
    print(f"forbidden-seam scope INPUT COUNT: 1 file scanned ({this_file.name})")
    text = this_file.read_text(encoding="utf-8")
    violations: list[str] = []
    for lineno, call_src in _iter_patch_call_sites(text, str(this_file)):
        for target in _FORBIDDEN_PATCH_TARGETS:
            if target in call_src:
                violations.append(f":{lineno}: {call_src}")
    assert not violations, "forbidden seam patched in this acceptance suite:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# Seeding + db-path resolution helpers (T004)
# ---------------------------------------------------------------------------


def _resolve_db_path(repo_root: Path, workspace: str, *, provider: str = "beads") -> Path:
    """Resolve the db path the *same way production does* -- via the real, un-patched
    ``LocalTrackerService._resolve_db_path``, never a re-implementation of the hash.
    """
    config = load_tracker_config(repo_root)
    svc = LocalTrackerService(repo_root, config)
    credentials = svc.credential_store.get_provider(provider)
    return cast("Path", svc._resolve_db_path(config, credentials))


def _seed_store(db_path: Path, *, workspace: str, provider: str = "beads") -> int:
    """Seed the tracker store with the sentinel issue; return the post-seed store size.

    ``TrackerSqliteStore.upsert_issue`` is ``async def`` -- called synchronously it would return
    an unawaited coroutine, never touch the database, and leave the store empty (H8's exact
    failure mode). Always run through ``asyncio.run`` and assert the store is non-empty after.
    """
    store = TrackerSqliteStore(db_path)
    issue = CanonicalIssue(
        ref=ExternalRef(system=provider, workspace=workspace, id="local-seed-1"),
        title=SENTINEL_TITLE,
        body=CONFIDENTIAL_BODY,
        status=CanonicalStatus.TODO,
        issue_type=CanonicalIssueType.TASK,
        assignees=[SENTINEL_ASSIGNEE],
        labels=[SENTINEL_LABEL],
    )
    asyncio.run(store.upsert_issue(issue))
    issues = asyncio.run(store.list_issues(system=provider))
    return len(issues)


def _sentinel_in_argvs(argvs: list[list[str]]) -> bool:
    return any(SENTINEL_TITLE in element for argv in argvs for element in argv)


def _digest(path: Path) -> bytes | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).digest()  # noqa: TID251 - test-only content-identity check


# ---------------------------------------------------------------------------
# CLI invocation helper (local, US1-US4): the real typer app, registered fresh
# per invocation so ``is_saas_sync_enabled()`` (read at registration time) sees
# the arming this test just set.
# ---------------------------------------------------------------------------


def _build_app() -> typer.Typer:
    from specify_cli.cli.commands import register_commands

    app = typer.Typer()
    register_commands(app)
    return app


def _invoke(monkeypatch: pytest.MonkeyPatch, repo_root: Path, args: list[str]) -> Any:
    monkeypatch.chdir(repo_root)
    app = _build_app()
    return RUNNER.invoke(app, args)


# ---------------------------------------------------------------------------
# A fully-wired local (``beads``) fixture builder, used by every US1-US4 cell.
# ---------------------------------------------------------------------------


@dataclass
class _LocalFixture:
    repo_root: Path
    capture_path: Path
    db_path: Path
    workspace: str = "acme-ws"

    def captured(self) -> list[list[str]]:
        return _read_captured(self.capture_path)


def _build_local_fixture(
    tmp_path: Path,
    *,
    name: str,
    project_uuid: str | None,
    sync_block: dict[str, Any] | None,
    tracker_egress: str | None,
    seed: bool = True,
    workspace: str = "acme-ws",
) -> _LocalFixture:
    """Build one ``beads``-bound project: config, recorder, credentials, and (optionally) a
    seeded store -- everything T004/T005/T006 need for one push/pull/run cell.
    """
    root = _project(tmp_path, name)
    tracker_block: dict[str, Any] = {"provider": "beads", "workspace": workspace}
    if tracker_egress is not None:
        tracker_block["egress"] = tracker_egress
    _write_project_config(
        root,
        project_uuid=project_uuid,
        sync_block=sync_block,
        tracker_block=tracker_block,
        doctrine_block=_DOCTRINE_SPEC_KITTY_AUTHORITATIVE,
    )
    capture_path = tmp_path / f"{name}-capture.jsonl"
    recorder = _make_recorder(tmp_path, capture_path, name=f"{name}-fake-bd")
    _bind_recorder_credentials(recorder, provider="beads")

    db_path = _resolve_db_path(root, workspace)
    if seed:
        seeded_count = _seed_store(db_path, workspace=workspace)
        assert seeded_count == 1, "seeding did not land -- H8's exact false-green precondition"

    return _LocalFixture(repo_root=root, capture_path=capture_path, db_path=db_path, workspace=workspace)


# ---------------------------------------------------------------------------
# T004 -- positive controls, on the un-gated base. MUST PASS.
# ---------------------------------------------------------------------------


class TestT004PositiveControls:
    """The two false-greens (H1 ownership mode, H8 empty store) that survive H2 and H3.

    This class is Stage 1's exit criterion: both controls below must pass, quoted, on the
    un-gated base, before any refusing pin in this file means anything.
    """

    def test_seeded_push_control_captures_exactly_3_argv_with_sentinel(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="t004-seeded",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=True,
        )
        digest_before = _digest(fx.db_path)
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        digest_after = _digest(fx.db_path)
        print(f"### SEEDED STORE ### push exit={result.exit_code} CAPTURED {len(argvs)} argv")
        assert result.exit_code == 0, result.output
        assert len(argvs) == 3, argvs  # golden-count: cardinality-is-contract
        assert argvs[0][1:] == ["--json", "list"]
        assert argvs[1][1] == "--json" and argvs[1][2] == "create"
        assert argvs[2][1:3] == ["--json", "show"]
        assert _sentinel_in_argvs(argvs), "sentinel title must appear verbatim in the create argv"
        assert SENTINEL_TITLE in argvs[1]
        # NFR-002(a)'s paired non-vacuity control: the refusing members (US1 sc1, US3 sc1, ...)
        # assert the db file is byte-identical across a refused push; that assertion means
        # nothing unless a *consenting* push is shown to actually change the bytes -- otherwise
        # "unchanged" would be true of a push that never touched the file at all.
        assert digest_before != digest_after, (
            "the consenting control must actually change the tracker db's bytes, or the refusing members' byte-identity assertion is vacuous (NFR-002a)"
        )

    def test_unseeded_push_control_captures_exactly_1_argv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="t004-unseeded",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=False,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        print(f"### EMPTY STORE ### push exit={result.exit_code} CAPTURED {len(argvs)} argv")
        assert result.exit_code == 0, result.output
        assert len(argvs) == 1, argvs  # golden-count: cardinality-is-contract
        assert argvs[0][1:] == ["--json", "list"]
        assert not _sentinel_in_argvs(argvs)

    def test_pull_control_argv_shape(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="t004-pull",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "pull"])
        argvs = fx.captured()
        assert result.exit_code == 0, result.output
        assert len(argvs) == 1  # golden-count: cardinality-is-contract
        assert argvs[0][1:] == ["--json", "list"]


# ---------------------------------------------------------------------------
# T005 -- US1, US2, US3: the refusing pins. COMMITTED RED on the un-gated base.
# ---------------------------------------------------------------------------


class TestUS1TrackerRefusesWithoutRefusingHostedSync:
    """US1: Channel 1 (hosted-sync consent) granted throughout; Channel 2 (tracker key) varies."""

    def test_sc1_channel2_refused_leaks_on_base_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Red on the base: the recorder captures 3 argv with the confidential title inside the
        ``create`` -- the leak itself, not a return code standing in for one. Flips green at WP04.
        """
        fx = _build_local_fixture(
            tmp_path,
            name="us1-sc1",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress="refused",
            seed=True,
        )
        digest_before = _digest(fx.db_path)
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        digest_after = _digest(fx.db_path)

        print(f"US1 sc1 (committed red until WP04): exit={result.exit_code} CAPTURED {len(argvs)} argv; sentinel_present={_sentinel_in_argvs(argvs)}")
        if _sentinel_in_argvs(argvs):
            leaking = next(a for a in argvs if any(SENTINEL_TITLE in e for e in a))
            print(f"  LEAK: sentinel '{SENTINEL_TITLE}' captured in argv: {leaking}")

        assert len(argvs) == 0, f"expected zero argv, captured {len(argvs)}: {argvs}"  # golden-count: cardinality-is-contract
        assert not _sentinel_in_argvs(argvs)
        assert digest_before == digest_after, "tracker SQLite file must be byte-identical (NFR-002a)"
        assert result.exit_code != 0
        assert "Channel 2" in result.output or "tracker.egress" in result.output

    def test_sc2_channel2_absent_is_the_positive_control(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Must pass: this is what makes sc1's absence assertion mean anything."""
        fx = _build_local_fixture(
            tmp_path,
            name="us1-sc2",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        assert result.exit_code == 0, result.output
        assert len(argvs) == 3, argvs  # golden-count: cardinality-is-contract
        assert _sentinel_in_argvs(argvs)

    def test_sc3_negative_pin_refusal_is_not_the_arming_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Negative pin: without it, the un-armed abort would satisfy sc1 with nothing built.

        Committed red on the base via the exit-code assertion (today's push succeeds, exit 0).
        """
        fx = _build_local_fixture(
            tmp_path,
            name="us1-sc3",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress="refused",
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert result.exit_code != 0, "committed red until WP04 lands the Channel-2 gate"
        assert _ARMING_DISABLED_FRAGMENT not in result.output


class TestUS2LocalTrackerWithoutHostedConsent:
    """US2: no hosted-sync consent record at any level; Channel 2 (tracker key) varies."""

    def test_sc1_channel2_permits_independent_of_channel1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Green on the base (nothing gates the local path today) and green after (Channel 2
        grants independently of Channel 1)."""
        fx = _build_local_fixture(
            tmp_path,
            name="us2-sc1",
            project_uuid=None,
            sync_block=None,
            tracker_egress="permitted",
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        assert result.exit_code == 0, result.output
        assert len(argvs) == 3, argvs  # golden-count: cardinality-is-contract
        assert _sentinel_in_argvs(argvs)

    def test_sc2_channel2_absent_refuses_naming_channel1_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The paired negative -- differs from sc1 by removing the tracker key. Red until WP04."""
        fx = _build_local_fixture(
            tmp_path,
            name="us2-sc2",
            project_uuid=None,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        assert len(argvs) == 0, argvs  # golden-count: cardinality-is-contract
        assert result.exit_code != 0
        assert "Channel 1" in result.output

    def test_sc3_recorded_hosted_refusal_does_not_veto_explicit_tracker_grant(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Green on the base (nothing gates the local path today) and green after (Channel 2's
        grant is independent of a recorded hosted-sync refusal)."""
        fx = _build_local_fixture(
            tmp_path,
            name="us2-sc3",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": False},
            tracker_egress="permitted",
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        assert result.exit_code == 0, result.output
        assert len(argvs) == 3, argvs  # golden-count: cardinality-is-contract
        # The count's companion (WP07 review, LOW-5). Its three sibling permitting cells all
        # follow the count with this line; this one did not, so it was the only `== 3` where the
        # cardinality was the *sole* argv assertion -- three calls of any shape would satisfy it,
        # including three that never carried the title. The point of a permitting cell is that
        # the payload *does* reach the recorder.
        assert _sentinel_in_argvs(argvs), argvs


class TestUS3UngatedLocalPathRefusesWhenNeitherChannelPermits:
    def test_sc1_no_record_no_tracker_key_refuses_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The 'no record' Channel-1 state per Hazard 8's own recipe: `project.uuid` **present**,
        no `sync:` block and no `sync.enabled` key -- distinct from 'not consentable', which omits
        `project.uuid` entirely. The spec's own wording for this scenario names the state
        explicitly ("the printed refusal carries the Channel-1 remedies for the 'no record'
        state"), so the fixture must resolve to that state, not a different one that also happens
        to refuse."""
        fx = _build_local_fixture(
            tmp_path,
            name="us3-sc1",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        digest_before = _digest(fx.db_path)
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        digest_after = _digest(fx.db_path)

        assert len(argvs) == 0, argvs  # golden-count: cardinality-is-contract
        assert digest_before == digest_after
        assert result.exit_code != 0
        # No "or Channel 1" escape: a WP04 implementation emitting one undifferentiated
        # "Channel 1 denies" message for all three Channel-1 states would satisfy that weaker
        # disjunct without actually distinguishing "no record" (T006 step 3's own requirement).
        assert "no record" in result.output.lower()
        assert "tracker.egress" in result.output or "Channel 2" in result.output

    def test_sc2_recorded_hosted_refusal_distinct_wording_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us3-sc2",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": False},
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        assert len(argvs) == 0, argvs  # golden-count: cardinality-is-contract
        assert result.exit_code != 0
        assert "refus" in result.output.lower()
        # Distinct from sc1's "no record" wording -- both refuse, but for a different reason.
        assert "no record" not in result.output.lower()

    def test_sc3_positive_control_three_argv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us3-sc3",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        assert result.exit_code == 0, result.output
        assert len(argvs) == 3, argvs  # golden-count: cardinality-is-contract
        assert _sentinel_in_argvs(argvs)

    def test_sc4_unseeded_pair_refusing_creates_no_file_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """NFR-002 clause (b), the file-existence clause. No sentinel assertion is made here --
        an unseeded store never reaches ``create_issue``, so no title crosses in either member;
        asserting its absence would establish nothing (only the seeded pair's digest clause (a)
        carries the sentinel argument). Per spec: "identical to scenarios 1 and 3 except ...
        unseeded" -- so this refusing member reuses sc1's 'no record' fixture shape
        (`project.uuid` present, no `sync:` block), not the 'not consentable' shape."""
        fx = _build_local_fixture(
            tmp_path,
            name="us3-sc4-refusing",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block=None,
            tracker_egress=None,
            seed=False,
        )
        assert not fx.db_path.exists(), "precondition: no file at the resolved db path yet"
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        assert not fx.db_path.exists(), "a refused command must create no file at the db path"
        assert len(argvs) == 0, argvs  # golden-count: cardinality-is-contract
        assert result.exit_code != 0
        assert "no record" in result.output.lower()
        assert "tracker.egress" in result.output or "Channel 2" in result.output

    def test_sc4_unseeded_pair_consenting_creates_file_and_one_argv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us3-sc4-consenting",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=False,
        )
        assert not fx.db_path.exists()
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        assert result.exit_code == 0, result.output
        assert fx.db_path.exists(), "consenting member must create the db file at that exact path"
        assert len(argvs) == 1, argvs  # golden-count: cardinality-is-contract
        assert argvs[0][1:] == ["--json", "list"]


# ---------------------------------------------------------------------------
# T006 -- US4 totality, bind counters, US6 executed remedies
# ---------------------------------------------------------------------------


class TestUS4TotalityAcrossThreeEntryPoints:
    """``sync_pull``, ``sync_push`` and ``sync_run`` each get their own refusing case and their
    own consenting control -- a parametrised pair run once and asserted three times would not
    satisfy NFR-004."""

    def test_pull_refusing_zero_argv_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Mirrors US3 sc1's 'no record' fixture shape (`project.uuid` present, no `sync:`
        block) rather than 'not consentable' -- same mislabelling class already corrected
        elsewhere in this file, fixed here for consistency."""
        fx = _build_local_fixture(
            tmp_path,
            name="us4-pull-refusing",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "pull"])
        argvs = fx.captured()
        assert len(argvs) == 0, argvs  # golden-count: cardinality-is-contract
        assert result.exit_code != 0
        assert "no record" in result.output.lower()
        assert "tracker.egress" in result.output or "Channel 2" in result.output

    def test_pull_consenting_control(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us4-pull-consenting",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "pull"])
        argvs = fx.captured()
        assert result.exit_code == 0, result.output
        assert len(argvs) == 1  # golden-count: cardinality-is-contract
        assert argvs[0][1:] == ["--json", "list"]

    def test_run_refusing_zero_argv_neither_half_reaches_runner_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Same 'no record' fixture shape as the pull-refusing cell above, for consistency."""
        fx = _build_local_fixture(
            tmp_path,
            name="us4-run-refusing",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "run"])
        argvs = fx.captured()
        assert len(argvs) == 0, argvs  # golden-count: cardinality-is-contract
        assert result.exit_code != 0
        assert "no record" in result.output.lower()
        assert "tracker.egress" in result.output or "Channel 2" in result.output

    def test_run_consenting_both_halves_carry_sentinel(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us4-run-consenting",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "run"])
        argvs = fx.captured()
        assert result.exit_code == 0, result.output
        assert len(argvs) >= 1
        assert _sentinel_in_argvs(argvs), "the push half of `sync run` must carry the sentinel"


# ---------------------------------------------------------------------------
# T006 step 2 -- the bind counters (H4). Delegating wrappers, never stubs.
# ---------------------------------------------------------------------------


def _install_delegating_counter(monkeypatch: pytest.MonkeyPatch, target: str) -> list[int]:
    """Install a delegating (never a stub) call counter at *target* (a dotted path).

    On the un-gated base neither ``specify_cli.tracker.local_service.tracker_egress_verdict`` nor
    ``specify_cli.tracker.saas_client.tracker_egress_verdict`` exists yet -- WP04/WP05 bind the
    names. ``getattr`` raises ``AttributeError`` here, and that raise **is** T006 step 2's
    committed red: "until WP04 and WP05 land there is no name to wrap at either target."
    """
    module_path, _, attr = target.rpartition(".")
    module = importlib.import_module(module_path)
    real = getattr(module, attr)  # AttributeError here IS the committed red (T006 step 2).
    count = [0]

    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        count[0] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(module, attr, _wrapper)
    return count


LOCAL_BIND_COUNTER_TARGET = "specify_cli.tracker.local_service.tracker_egress_verdict"
HOSTED_BIND_COUNTER_TARGET = "specify_cli.tracker.saas_client.tracker_egress_verdict"


def test_local_bind_counter_wired_against_named_target_committed_red(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H4: a representative refusing local cell (US3 sc1) must enter the gate before refusing.

    Committed red until WP04 lands ``tracker_egress_verdict`` and binds it under this exact name
    in ``local_service.py`` -- see the module docstring's "Scope decision" note for why this is
    one representative cell rather than a duplicate wrapper in every US1-US4 refusing test.
    """
    counter = _install_delegating_counter(monkeypatch, LOCAL_BIND_COUNTER_TARGET)
    fx = _build_local_fixture(
        tmp_path,
        name="bind-counter-local",
        project_uuid=None,
        sync_block=None,
        tracker_egress=None,
        seed=True,
    )
    _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
    print(f"local bind count (python {sys.version_info[:2]}): {counter[0]}")
    assert counter[0] > 0, "a gate never entered is not a gate"


def test_hosted_bind_counter_wired_against_named_target_committed_red(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_credential_store: MagicMock) -> None:
    """H4, hosted destination: US5 sc1 must enter the gate before refusing. Committed red until
    WP05 lands ``tracker_egress_verdict`` and swaps ``saas_client.py`` onto it."""
    counter = _install_delegating_counter(monkeypatch, HOSTED_BIND_COUNTER_TARGET)
    root = _project(tmp_path, "bind-counter-hosted")
    _write_project_config(
        root,
        project_uuid=CONSENTING_PROJECT_UUID,
        sync_block={"enabled": True},
        tracker_block={"provider": "jira", "project_slug": "acme-jira", "egress": "refused"},
    )
    config = load_tracker_config(root)
    svc = SaaSTrackerService(root, config)
    with contextlib.suppress(Exception):
        svc.sync_push(items=[])
    print(f"hosted bind count (python {sys.version_info[:2]}): {counter[0]}")
    assert counter[0] > 0, "a gate never entered is not a gate"


def _argv_without_recorder_path(argvs: list[list[str]]) -> list[list[str]]:
    """Strip ``argv[0]`` (the recorder's own absolute path) from each captured line.

    The recorder path is deliberately made to differ between the two ``_run_once`` arms below
    (each fixture is named ``wrapper-{refusing,consenting}-{install_counter}`` so the two arms'
    capture files never collide) -- but that name is not part of the *observable outcome* a
    counting wrapper must leave unchanged. Comparing full argv here would make the assertion
    fail for a reason that has nothing to do with the wrapper, for every run, forever -- exactly
    the false-red review finding this helper exists to close.
    """
    return [argv[1:] for argv in argvs]


def test_bind_counter_wrapper_changes_no_outcome_committed_red(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A counting wrapper that changed an outcome would be a stub, not a counter. Compares one
    refusing cell and one consenting cell, with and without the wrapper installed, asserting
    identical captured argv (excluding the recorder's own path -- see
    ``_argv_without_recorder_path``) and exit status. Committed red today via the same
    ``AttributeError`` T006 step 2 describes."""

    def _run_once(install_counter: bool) -> tuple[int, list[list[str]], int, list[list[str]]]:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
            mp.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
            if install_counter:
                _install_delegating_counter(mp, LOCAL_BIND_COUNTER_TARGET)
            # Distinct workspaces: the resolved db path is a hash of
            # (provider, workspace, server_url, username, team_slug) only -- it does NOT depend
            # on repo_root -- so two fixtures sharing a workspace under the same SPEC_KITTY_HOME
            # would collide on one sqlite file and double-seed it.
            refusing = _build_local_fixture(
                tmp_path,
                name=f"wrapper-refusing-{install_counter}",
                project_uuid=None,
                sync_block=None,
                tracker_egress=None,
                seed=True,
                workspace=f"acme-ws-refusing-{install_counter}",
            )
            r1 = _invoke(mp, refusing.repo_root, ["tracker", "sync", "push"])
            consenting = _build_local_fixture(
                tmp_path,
                name=f"wrapper-consenting-{install_counter}",
                project_uuid=CONSENTING_PROJECT_UUID,
                sync_block={"enabled": True},
                tracker_egress=None,
                seed=True,
                workspace=f"acme-ws-consenting-{install_counter}",
            )
            r2 = _invoke(mp, consenting.repo_root, ["tracker", "sync", "push"])
            return (
                r1.exit_code,
                _argv_without_recorder_path(refusing.captured()),
                r2.exit_code,
                _argv_without_recorder_path(consenting.captured()),
            )

    without = _run_once(False)
    with_counter = _run_once(True)
    assert without == with_counter, "the delegating wrapper must not change any observable outcome"


# ---------------------------------------------------------------------------
# T006 step 3 -- US6: executed remedies (H5). Never a substring-only check.
# ---------------------------------------------------------------------------


class TestUS6ExecutedRemedies:
    """For each of the three Channel-1 states, assert the pre-remedy refusal, apply the remedy,
    re-run, and assert the sentinel now reaches the recorder. All committed red on the base: the
    pre-remedy refusal assertion itself is what is red today (nothing gates the local path yet)."""

    def test_no_record_remedy_sync_enabled_true_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us6-no-record-a",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        pre = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        pre_argvs = fx.captured()
        assert len(pre_argvs) == 0, pre_argvs  # golden-count: cardinality-is-contract
        assert pre.exit_code != 0, "pre-remedy state must actually be refusing"
        # T006 step 3: assert the printed *no record* state wording before applying the remedy --
        # distinguishing the three Channel-1 states is the entire point of these three cells.
        # No "or Channel 1" escape: an undifferentiated "Channel 1 denies" message for every
        # state would satisfy that weaker disjunct without distinguishing anything.
        assert "no record" in pre.output.lower()

        # Remedy 1: sync.enabled: true in the project's own config.
        _write_project_config(
            fx.repo_root,
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_block={"provider": "beads", "workspace": fx.workspace},
            doctrine_block=_DOCTRINE_SPEC_KITTY_AUTHORITATIVE,
        )
        post = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert post.exit_code == 0, post.output
        assert _sentinel_in_argvs(fx.captured())

    def test_no_record_remedy_spec_kitty_sync_opt_in_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from specify_cli.sync.routing import enable_checkout_sync

        fx = _build_local_fixture(
            tmp_path,
            name="us6-no-record-b",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        pre = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        pre_argvs = fx.captured()
        assert len(pre_argvs) == 0, pre_argvs  # golden-count: cardinality-is-contract
        assert pre.exit_code != 0
        assert "no record" in pre.output.lower()

        # Remedy 2: `spec-kitty sync opt-in` -- its underlying function, applied to this fixture.
        monkeypatch.chdir(fx.repo_root)
        enable_checkout_sync(fx.repo_root)

        post = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert post.exit_code == 0, post.output
        assert _sentinel_in_argvs(fx.captured())

    def test_no_record_remedy_tracker_egress_permitted_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us6-no-record-c",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        pre = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        pre_argvs = fx.captured()
        assert len(pre_argvs) == 0, pre_argvs  # golden-count: cardinality-is-contract
        assert pre.exit_code != 0
        assert "no record" in pre.output.lower()

        # Remedy 3: tracker.egress: permitted (the Channel-2 grant). Keeps `project_uuid` as the
        # pre-state had it -- changing it here too would additionally flip the Channel-1 state
        # from "no record" to "not consentable", making this a two-line remedy rather than one
        # (the "grant needs no identity at all" case is demonstrated separately, in
        # ``test_not_consentable_remedy_channel2_grant_committed_red``, where the pre-state
        # already has no identity to begin with).
        _write_project_config(
            fx.repo_root,
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block=None,
            tracker_block={"provider": "beads", "workspace": fx.workspace, "egress": "permitted"},
            doctrine_block=_DOCTRINE_SPEC_KITTY_AUTHORITATIVE,
        )
        post = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert post.exit_code == 0, post.output
        assert _sentinel_in_argvs(fx.captured())

    def test_recorded_refusal_remedy_change_decision_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us6-refusal-a",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": False},
            tracker_egress=None,
            seed=True,
        )
        pre = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        pre_argvs = fx.captured()
        assert len(pre_argvs) == 0, pre_argvs  # golden-count: cardinality-is-contract
        assert pre.exit_code != 0
        # Distinct from the "no record" wording above -- a recorded refusal is a different
        # Channel-1 state (T006 step 3) and must not be reported identically to "no record".
        assert "refus" in pre.output.lower()
        assert "no record" not in pre.output.lower()

        _write_project_config(
            fx.repo_root,
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_block={"provider": "beads", "workspace": fx.workspace},
            doctrine_block=_DOCTRINE_SPEC_KITTY_AUTHORITATIVE,
        )
        post = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert post.exit_code == 0, post.output
        assert _sentinel_in_argvs(fx.captured())

    def test_recorded_refusal_remedy_channel2_grant_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fx = _build_local_fixture(
            tmp_path,
            name="us6-refusal-b",
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": False},
            tracker_egress=None,
            seed=True,
        )
        pre = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        pre_argvs = fx.captured()
        assert len(pre_argvs) == 0, pre_argvs  # golden-count: cardinality-is-contract
        assert pre.exit_code != 0
        assert "refus" in pre.output.lower()
        assert "no record" not in pre.output.lower()

        _write_project_config(
            fx.repo_root,
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": False},
            tracker_block={"provider": "beads", "workspace": fx.workspace, "egress": "permitted"},
            doctrine_block=_DOCTRINE_SPEC_KITTY_AUTHORITATIVE,
        )
        post = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert post.exit_code == 0, post.output
        assert _sentinel_in_argvs(fx.captured())

    def test_not_consentable_remedy_channel2_grant_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Not-consentable: no project.uuid at all, so `enable_checkout_sync` would raise
        `ConsentIdentityUnresolvedError` and hand-authoring `sync.enabled: true` still denies
        (Hazard 8's fourth variant). The Channel-2 grant needs no identity at all."""
        fx = _build_local_fixture(
            tmp_path,
            name="us6-not-consentable-a",
            project_uuid=None,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        pre = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        pre_argvs = fx.captured()
        assert len(pre_argvs) == 0, pre_argvs  # golden-count: cardinality-is-contract
        assert pre.exit_code != 0
        # Distinct from both "no record" and "recorded refusal" -- identity never resolved at
        # all, so the state (and its remedies) differ from either.
        assert "not consentable" in pre.output.lower() or "identity" in pre.output.lower()

        _write_project_config(
            fx.repo_root,
            project_uuid=None,
            sync_block=None,
            tracker_block={"provider": "beads", "workspace": fx.workspace, "egress": "permitted"},
            doctrine_block=_DOCTRINE_SPEC_KITTY_AUTHORITATIVE,
        )
        post = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert post.exit_code == 0, post.output
        assert _sentinel_in_argvs(fx.captured())

    def test_not_consentable_remedy_mint_identity_then_channel1_committed_red(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """SC-007's **first** not-consentable remedy: mint an identity, *then* record Channel 1.

        Added by the mission owner after WP08 found the gap. SC-007 specifies two remedies for
        this state and this file only executed the second (the Channel-2 grant, above). The
        upgrade note documents both, and WP08's rule is that a documented remedy must have an
        executed-remedy test behind it -- so WP08 proved this one with a scratch probe rather
        than document an unverified claim, and reported it instead of editing this approved
        file. This is that proof, committed.

        It matters more than a coverage tick. The shipped hosted refusal text points an
        identity-less operator at ``spec-kitty sync opt-in``, which **cannot work** without a
        project identity -- ``enable_checkout_sync`` raises ``ConsentIdentityUnresolvedError``.
        The order here (identity first, then consent) is the only Channel-1 route out of this
        state, and it is what the note tells operators to do.

        ``ensure_identity`` is the call ``spec-kitty init`` makes; driving it directly keeps the
        cell about the remedy rather than about ``init``'s unrelated scaffolding.
        """
        from specify_cli.identity.project import ensure_identity  # noqa: PLC0415
        from specify_cli.sync.routing import enable_checkout_sync  # noqa: PLC0415

        fx = _build_local_fixture(
            tmp_path,
            name="us6-not-consentable-init",
            project_uuid=None,
            sync_block=None,
            tracker_egress=None,
            seed=True,
        )
        pre = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert len(fx.captured()) == 0, fx.captured()  # golden-count: cardinality-is-contract
        assert pre.exit_code != 0
        assert "not consentable" in pre.output.lower() or "identity" in pre.output.lower()
        # Negative half, matching this class's own idiom (review LOW-8): without it the `mid`
        # assertion below would silently stop proving a state *transition* if the
        # not-consentable wording were ever reworded to contain the token.
        assert "no record" not in pre.output.lower()

        # Remedy step 1: mint the identity. On its own this must NOT open the gate -- Channel 1
        # still has no recorded decision, and absence denies. Asserting the intermediate state
        # is what makes this a two-step remedy rather than two things happening at once.
        ensure_identity(fx.repo_root)
        mid = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert mid.exit_code != 0, mid.output
        assert len(fx.captured()) == 0, "minting an identity must not by itself grant egress"  # golden-count: cardinality-is-contract
        assert "no record" in mid.output.lower(), "after minting, the state must move from not-consentable to no-record"

        # Remedy step 2: now Channel 1 can actually be recorded, which the pre-state refused.
        enable_checkout_sync(fx.repo_root)
        post = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        assert post.exit_code == 0, post.output
        assert _sentinel_in_argvs(fx.captured())

    def test_not_consentable_hand_authoring_sync_enabled_still_denies(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without this state the binding is permanently dead with actively wrong advice: hand-
        authoring `sync.enabled: true` with no `project.uuid` still denies at Channel 1, because
        identity never resolved. Documents the failure mode `enable_checkout_sync` guards against
        -- does not call it, since a missing uuid makes it raise `ConsentIdentityUnresolvedError`."""
        fx = _build_local_fixture(
            tmp_path,
            name="us6-not-consentable-b",
            project_uuid=None,
            sync_block={"enabled": True},
            tracker_egress=None,
            seed=True,
        )
        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "push"])
        argvs = fx.captured()
        # Committed red: nothing gates the local path yet, so this "still denies" documentation
        # cell currently succeeds instead -- and the assertion below prints the leaked sentinel
        # inside the captured argv, not a bare boolean. Flips once WP04 lands the Channel-2-aware
        # gate that also consults the (still-denying) Channel-1 state correctly.
        assert not _sentinel_in_argvs(argvs), (
            f"hand-authoring sync.enabled: true with no project.uuid must still deny (identity never resolved) -- committed red until WP04; captured argv: {argvs}"
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# T007 -- US5 (hosted destination) and US1 sc4 (hosted-sync drain, unaffected)
# ---------------------------------------------------------------------------


def _write_jira_config(
    root: Path,
    *,
    project_uuid: str | None,
    sync_block: dict[str, Any] | None,
    tracker_egress: str | None,
    provider: str = "jira",
    project_slug: str = "acme-jira",
) -> None:
    tracker_block: dict[str, Any] = {"provider": provider, "project_slug": project_slug}
    if tracker_egress is not None:
        tracker_block["egress"] = tracker_egress
    _write_project_config(root, project_uuid=project_uuid, sync_block=sync_block, tracker_block=tracker_block)
    if project_uuid is not None and (sync_block or {}).get("enabled") is True:
        with ProjectSyncStore(project_uuid).unit_of_work() as unit:
            unit.execute(
                "INSERT INTO project_target_admissions "
                "(project_uuid, target_identity, account_identity, private_teamspace_id, "
                "configuration_generation, admission_state, admission_generation, binding_audience) "
                "VALUES (?, 'https://app.spec-kitty.ai', 'legacy-account', "
                "'legacy-private-teamspace', 1, 'admitted', 'legacy-admission', 'legacy-binding') "
                "ON CONFLICT(project_uuid) DO UPDATE SET target_identity = excluded.target_identity, "
                "account_identity = excluded.account_identity, private_teamspace_id = excluded.private_teamspace_id, "
                "configuration_generation = excluded.configuration_generation, "
                "admission_state = excluded.admission_state, admission_generation = excluded.admission_generation, "
                "binding_audience = excluded.binding_audience",
                (project_uuid,),
            )


class TestUS5TrackerKeyNarrowsHostedDestinationNeverGrantsIt:
    """One project bound to ``jira``. Real, un-patched ``TrackerService`` / ``SaaSTrackerService``
    / ``SaaSTrackerClient`` -- see the module docstring for why the CLI's own readiness layer is
    bypassed for the hosted cells specifically (an unrelated auth precondition, not this Mission's
    gate)."""

    def test_sc1_hosted_refuses_channel2_committed_red(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_credential_store: MagicMock,
        http_tripwire: _HttpTripwire,
    ) -> None:
        """Committed red: the base has no Channel-2 gate on the hosted path either, so this
        currently fails at `No valid access token` (0 HTTP still) rather than the required
        `TrackerEgressRefusedError` naming Channel 2. The red must pin exception type + message,
        never the HTTP count (T007's own warning: 0 HTTP is already true on the base)."""
        root = _project(tmp_path, "us5-sc1")
        _write_jira_config(root, project_uuid=CONSENTING_PROJECT_UUID, sync_block={"enabled": True}, tracker_egress="refused")
        config = load_tracker_config(root)
        svc = SaaSTrackerService(root, config)
        with pytest.raises(TrackerEgressRefusedError) as excinfo:
            svc.sync_push(items=[])
        assert "Channel 2" in str(excinfo.value) or "tracker.egress" in str(excinfo.value)
        assert http_tripwire.attempts == 0

    def test_sc2_hosted_refuses_channel1_notes_tracker_grant_noop_committed_red(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_credential_store: MagicMock,
        http_tripwire: _HttpTripwire,
    ) -> None:
        root = _project(tmp_path, "us5-sc2")
        _write_jira_config(root, project_uuid=None, sync_block=None, tracker_egress="permitted")
        config = load_tracker_config(root)
        svc = SaaSTrackerService(root, config)
        with pytest.raises(TrackerEgressRefusedError) as excinfo:
            svc.sync_push(items=[])
        message = str(excinfo.value)
        assert "Channel 1" in message or "has not consented to hosted sync" in message
        assert http_tripwire.attempts == 0
        # Committed red: the base's project_egress_refusal message says nothing about a
        # recorded-but-inapplicable tracker grant -- that additional clause is WP03's.
        assert "no-op" in message.lower() or "does not apply" in message.lower(), (
            "committed red until WP03 adds the tracker-grant-is-a-no-op-at-HOSTED_SERVICE clause"
        )

    def test_sc3_positive_control_reaches_no_valid_access_token(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_credential_store: MagicMock,
        http_tripwire: _HttpTripwire,
    ) -> None:
        """The shipped #3030 behaviour, unchanged. Must pass."""
        root = _project(tmp_path, "us5-sc3")
        _write_jira_config(root, project_uuid=CONSENTING_PROJECT_UUID, sync_block={"enabled": True}, tracker_egress=None)
        config = load_tracker_config(root)
        svc = SaaSTrackerService(root, config)
        with pytest.raises(SaaSTrackerClientError) as excinfo:
            svc.sync_push(items=[])
        assert "No valid access token" in str(excinfo.value)
        assert http_tripwire.attempts == 0

    def test_sc4_sc005a_subject_refuses_naming_channel1_green_before_and_after(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_credential_store: MagicMock,
        http_tripwire: _HttpTripwire,
    ) -> None:
        """SC-005a. GREEN BEFORE AND AFTER -- not a red-then-green pin (T007 step 4's own
        warning). On-disk provider is `beads`; `--provider jira` overrides it in memory via
        `TrackerService._resolve_saas_backend_for_provider`, which routes to
        `SaaSTrackerClient._request` regardless. Discriminates a destination-as-parameter
        implementation from a destination-as-derivation one (which would read `beads` off disk,
        apply the local half, and grant -- reopening #3030's P0 boundary)."""
        root = _project(tmp_path, "us5-sc4-subject")
        _write_project_config(
            root,
            project_uuid=None,
            sync_block=None,
            tracker_block={"provider": "beads", "workspace": "acme-ws", "egress": "permitted"},
        )
        svc = TrackerService(root)
        with pytest.raises(TrackerEgressRefusedError) as excinfo:
            svc.list_tickets(provider="jira", limit=20)
        assert "Channel 1" in str(excinfo.value) or "has not consented to hosted sync" in str(excinfo.value)
        assert http_tripwire.attempts == 0

    def test_sc4_sc005a_positive_control_reaches_no_valid_access_token(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_credential_store: MagicMock,
        http_tripwire: _HttpTripwire,
    ) -> None:
        """The paired positive control: on-disk `provider: jira`, Channel 1 granted, no tracker
        key -- reaches `No valid access token`, so the zero-HTTP count in the subject is not
        vacuous."""
        root = _project(tmp_path, "us5-sc4-control")
        _write_jira_config(root, project_uuid=CONSENTING_PROJECT_UUID, sync_block={"enabled": True}, tracker_egress=None)
        svc = TrackerService(root)
        with pytest.raises(SaaSTrackerClientError) as excinfo:
            svc.list_tickets(provider="jira", limit=20)
        assert "No valid access token" in str(excinfo.value)
        assert http_tripwire.attempts == 0

    def test_sc4_sc005a_negative_control_beads_disk_raises_discriminator(self, tmp_path: Path) -> None:
        """The probe discriminates: asking for the on-disk local provider as a hosted read must
        raise `TrackerServiceError`, proving the override path is genuinely provider-specific."""
        from specify_cli.tracker.service import TrackerServiceError

        root = _project(tmp_path, "us5-sc4-negative")
        _write_project_config(
            root,
            project_uuid=None,
            sync_block=None,
            tracker_block={"provider": "beads", "workspace": "acme-ws"},
        )
        svc = TrackerService(root)
        with pytest.raises(TrackerServiceError):
            svc.list_tickets(provider="beads", limit=20)

    def test_sc5_hosted_near_miss_singular_refuse_committed_red(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_credential_store: MagicMock,
        http_tripwire: _HttpTripwire,
    ) -> None:
        """The hosted near-miss end to end (C-020): `egress: refuse` (singular) is neither legal
        value. Must refuse with 0 HTTP, raising nothing but `TrackerEgressRefusedError`, naming
        the key, quoting `refuse` verbatim, and naming both legal values. One representative
        near-miss; the full 15-value probed set is WP03's unit-level pins."""
        root = _project(tmp_path, "us5-sc5")
        _write_jira_config(root, project_uuid=CONSENTING_PROJECT_UUID, sync_block={"enabled": True}, tracker_egress="refuse")
        config = load_tracker_config(root)
        svc = SaaSTrackerService(root, config)
        with pytest.raises(TrackerEgressRefusedError) as excinfo:
            svc.sync_push(items=[])
        message = str(excinfo.value)
        assert "refuse" in message
        assert "refused" in message and "permitted" in message
        assert http_tripwire.attempts == 0


# ---------------------------------------------------------------------------
# US1 sc4 -- hosted sync (the queue drain) is unaffected by the tracker key.
# Ported seam from tests/sync/test_body_drain_consent_3030.py (its own precedent).
# ---------------------------------------------------------------------------


@dataclass
class _DrainEgress:
    """Records every outbound HTTP attempt the body-upload drain makes (a *different* transport
    -- ``requests``, not ``httpx`` -- so this coexists with, and is independent of, the
    ``http_tripwire`` fixture used everywhere else in this file)."""

    status: int = 201
    posts: list[dict[str, Any]] = field(default_factory=list)
    store: ProjectSyncStore | None = None

    def _record(self, url: str, payload: object) -> Any:
        if self.store is not None:
            # Transport must run outside every project transaction.  A fresh
            # immediate UoW here is the behavioural proof: the former fixture
            # held one across the callback and this exact probe locked.
            with self.store.unit_of_work(lock_timeout_seconds=0):
                pass
        decoded = json.loads(payload) if isinstance(payload, bytes) else payload
        assert isinstance(decoded, dict)
        self.posts.append({"url": url, "json": decoded})
        return SimpleNamespace(
            status_code=self.status,
            json=lambda: {
                "artifact_path": decoded["artifact_path"],
                "content_hash": decoded["content_hash"],
                "status": "stored",
            },
        )

    def post(
        self,
        url: str,
        *,
        data: bytes,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        del headers, timeout
        return self._record(url, data)

    def fallback(self, method: str, url: str, **kwargs: Any) -> Any:
        assert method == "POST"
        return self._record(url, kwargs.get("content"))

    @property
    def bodies(self) -> list[str]:
        return [str(p["json"].get("content_body", "")) for p in self.posts]

    @property
    def project_uuids(self) -> list[str]:
        return [str(p["json"].get("project_uuid", "")) for p in self.posts]


@dataclass(frozen=True)
class _BodyQueueFacade:
    """Connection-free test handle over the canonical project-owned queue."""

    store: ProjectSyncStore

    def enqueue(self, **kwargs: Any) -> Any:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        with self.store.unit_of_work() as unit:
            return OfflineBodyUploadQueue(unit, self.store.layout_generation()).enqueue(**kwargs)

    def size(self) -> int:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        with self.store.unit_of_work() as unit:
            return OfflineBodyUploadQueue(unit, self.store.layout_generation()).size()

    def remove_project_tasks(self, project_uuid: str) -> int:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        with self.store.unit_of_work() as unit:
            return OfflineBodyUploadQueue(unit, self.store.layout_generation()).remove_project_tasks(project_uuid)


@contextlib.contextmanager
def _drain_service(
    monkeypatch: pytest.MonkeyPatch,
    project_uuid: str,
) -> Iterator[tuple[Any, _BodyQueueFacade]]:
    from specify_cli.sync.background import BackgroundSyncService
    from specify_cli.sync.consent import record_project_opt_in
    from specify_cli.sync.layout_generation import LayoutMode
    from unittest.mock import MagicMock as _MM

    monkeypatch.setattr("specify_cli.sync.background._fetch_access_token_sync", lambda: "test-token")
    monkeypatch.setattr("specify_cli.sync.background.is_saas_sync_enabled", lambda: True)
    manager = _MM()
    manager.get_current_session.return_value = SimpleNamespace(
        email="account-1",
        teams=[SimpleNamespace(id="teamspace-1", is_private_teamspace=True)],
    )
    monkeypatch.setattr("specify_cli.sync.background.get_token_manager", lambda: manager)

    config = _MM()
    config.resolve_runtime_target.return_value = SimpleNamespace(resolved_server_url="https://saas.example.test")
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("tracker-egress-hosted-drain-fixture")
        authority.publish_project_only(
            "tracker-egress-hosted-drain-fixture",
            verify_exact=lambda: True,
        )
    record_project_opt_in(project_uuid, actor="tracker-egress-hosted-drain-fixture")
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://saas.example.test', 'account-1', 'teamspace-1', 1, "
            "'admitted', '1', 'private-teamspace:teamspace-1') "
            "ON CONFLICT(project_uuid) DO UPDATE SET "
            "target_identity = excluded.target_identity, "
            "account_identity = excluded.account_identity, "
            "private_teamspace_id = excluded.private_teamspace_id, "
            "configuration_generation = excluded.configuration_generation, "
            "admission_state = excluded.admission_state, "
            "admission_generation = excluded.admission_generation, "
            "binding_audience = excluded.binding_audience",
            (project_uuid,),
        )
    monkeypatch.setattr(
        "specify_cli.sync.background._enumerate_project_store_candidates",
        lambda: (store.project_uuid,),
    )
    service = BackgroundSyncService(queue=_MM(), config=config)
    assert service._body_queue is None
    from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
    from specify_cli.sync.project_context import AdmissionState, ConsentState

    context = store.create_context()
    assert context.consent_state is ConsentState.GRANTED
    assert context.admission_state is AdmissionState.ADMITTED
    authenticated = service._authenticated_runtime_target()
    assert authenticated is not None
    resolved, account_identity, private_teamspace_id = authenticated
    with store.unit_of_work() as unit:
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None
    assert service._target_matches_current_auth(
        target,
        resolved,
        account_identity,
        private_teamspace_id,
        store.project_uuid,
    )
    yield service, _BodyQueueFacade(store)


def _enqueue_two_bodies(
    queue: Any,
    project_uuid: str,
    *,
    identity_namespace: str,
) -> None:
    from specify_cli.sync.namespace import NamespaceRef

    for i in range(2):
        content = f"# Spec\n\nACME Holdings engagement note {i}.\n"
        digest = hashlib.sha256(content.encode()).hexdigest()  # noqa: TID251 - body-integrity checksum
        queue.enqueue(
            namespace=NamespaceRef(
                project_uuid=project_uuid,
                mission_slug="3108-carve-out",
                target_branch="main",
                mission_type="software-dev",
                manifest_version="1",
            ),
            artifact_path=f"{identity_namespace}/spec-{i}.md",
            content_hash=digest,
            content_body=content,
            size_bytes=len(content.encode()),
        )


def test_us1_sc4_hosted_drain_unaffected_by_tracker_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    http_tripwire: _HttpTripwire,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """US1 sc4: hosted sync (the queue drain) is unaffected by the tracker key. This is a
    *different* transport (the body/event drain) with its own, unrelated consent chain; this
    Mission changes nothing about it, so it is a positive control -- green on the base and after.
    No bind counter is asserted here (T006/T007's stated exemption): neither the local nor the
    hosted `tracker_egress_verdict` name is ever called on this path.

    Each arm gets its **own real project root** -- one committing `tracker: {egress: refused}`,
    one with no tracker key at all -- and the test ``chdir``s into it for the enqueue+drain, so
    the fixture actually names the thing the cell's docstring claims to compare, not a clone of
    itself with only the sqlite filename differing. Measured (and confirmed by review): today
    ``BackgroundSyncService.drain_body_uploads_only`` (``sync/background.py:490-512``) consults
    only ``is_saas_sync_enabled()`` and the uuid-keyed consent index -- it never reads a repo
    root at all -- so this is a **forward-looking guard**, not a live discriminator: it reds the
    day the tracker key reaches this transport, which is precisely the regression US1 sc4 exists
    to catch, even though nothing in this Mission wires that path today. The honest limit of that
    guard: it covers only a **cwd-shaped** regression (a future reader of ``Path.cwd()``, which is
    what ``chdir`` into each arm's root would catch); ``background.py:284-286`` records that a
    cwd-derived consent answer *is* the defect this Mission's siblings have already found, so a
    tracker-key regression on this transport would more plausibly key on
    ``_drain_checkout_roots()`` than on cwd -- a shape this cell does not simulate and would not
    catch.
    """
    root_with_key = _project(tmp_path, "us1-sc4-with-key")
    _write_project_config(
        root_with_key,
        project_uuid=CONSENTING_PROJECT_UUID,
        sync_block={"enabled": True},
        tracker_block={"provider": "beads", "workspace": "acme-ws", "egress": "refused"},
    )
    root_no_key = _project(tmp_path, "us1-sc4-no-key")
    _write_project_config(
        root_no_key,
        project_uuid=CONSENTING_PROJECT_UUID,
        sync_block={"enabled": True},
        tracker_block={"provider": "beads", "workspace": "acme-ws"},
    )

    store = ProjectSyncStore(CONSENTING_PROJECT_UUID)
    egress_with_key = _DrainEgress(store=store)
    monkeypatch.setattr(
        "specify_cli.sync.body_transport.requests",
        __import__("types").SimpleNamespace(post=egress_with_key.post, ConnectionError=ConnectionError, Timeout=TimeoutError),
    )
    monkeypatch.setattr("specify_cli.sync.body_transport.request_with_stdlib_fallback_sync", egress_with_key.fallback)
    monkeypatch.chdir(root_with_key)
    with _drain_service(monkeypatch, CONSENTING_PROJECT_UUID) as (svc_with_key, queue_with_key):
        _enqueue_two_bodies(
            queue_with_key,
            CONSENTING_PROJECT_UUID,
            identity_namespace="with-key",
        )
        assert queue_with_key.size() == 2, "non-vacuity: queue must be non-empty before drain"
        with store.unit_of_work(lock_timeout_seconds=0):
            pass
        svc_with_key.drain_body_uploads_only()
        assert queue_with_key.size() == 0, "non-vacuity: queue must be empty after drain"
        # The two historical arms used separate legacy sqlite files. The
        # canonical project store is UUID-scoped, so remove completed fixture
        # rows before enqueueing the second arm's distinct transport identities.
        queue_with_key.remove_project_tasks(CONSENTING_PROJECT_UUID)

    egress_no_key = _DrainEgress(store=store)
    monkeypatch.setattr(
        "specify_cli.sync.body_transport.requests",
        __import__("types").SimpleNamespace(post=egress_no_key.post, ConnectionError=ConnectionError, Timeout=TimeoutError),
    )
    monkeypatch.setattr("specify_cli.sync.body_transport.request_with_stdlib_fallback_sync", egress_no_key.fallback)
    monkeypatch.chdir(root_no_key)
    with _drain_service(monkeypatch, CONSENTING_PROJECT_UUID) as (svc_no_key, queue_no_key):
        _enqueue_two_bodies(
            queue_no_key,
            CONSENTING_PROJECT_UUID,
            identity_namespace="no-key",
        )
        assert queue_no_key.size() == 2
        with store.unit_of_work(lock_timeout_seconds=0):
            pass
        svc_no_key.drain_body_uploads_only()
        assert queue_no_key.size() == 0

    assert egress_with_key.project_uuids == egress_no_key.project_uuids
    assert egress_with_key.bodies == egress_no_key.bodies
    assert len(egress_with_key.posts) == len(egress_no_key.posts) == 2
    assert [post["url"] for post in egress_with_key.posts] == [post["url"] for post in egress_no_key.posts]
    assert all(str(post["url"]).endswith("/api/dossier/push-content/") for post in (*egress_with_key.posts, *egress_no_key.posts))
    assert "project sync store is locked" not in caplog.text
    # This file's own httpx trip-wire stays armed throughout and must still record 0 -- the
    # drain path is instrumented above it (a `requests`-based transport), which is precisely why
    # the two coexist.
    assert http_tripwire.attempts == 0


# ---------------------------------------------------------------------------
# #3174 -- NO OVER-GATING. The converse of US4's totality assertions.
# ---------------------------------------------------------------------------
#
# US4 above pins that the three GATED entry points (`sync pull` / `sync push` / `sync run`)
# refuse. That property is satisfied by a gate that refuses *unconditionally* -- so is every
# other refusal assertion in this file. What none of them pin is the other half of the
# specification: `docs/migrations/tracker-egress-refusal.md` promises operators that `status`,
# `bind`, `unbind`, `map add` and `map list` keep working on a project that records
# `tracker: {egress: refused}`. Until this section landed, nothing executed that promise --
# it was asserted only structurally (a call-site census showing 6 `tracker_egress_verdict`
# call expressions across 5 enclosing functions, none of them an ungated command). A census is
# re-derived by hand and goes stale; these cells run the commands.
#
# Every cell here carries an **in-cell discriminator** (`_assert_gate_is_live`): the same
# repo root that serves the ungated command must first refuse `tracker sync pull`, naming
# Channel 2. Without it a cell would stay green on a fixture that was never refusing at all --
# "the ungated commands work on a project with no gate" is not the claim.
#
# Each cell asserts the command **succeeded and returned its expected local-only payload**,
# never merely "did not print the refusal". A command that exits 1 for an unrelated reason
# (missing binary, missing auth, absent config) must not be able to satisfy these.


#: The exact Channel-2 refusal `_refused_message` composes at ``LOCAL_SUBPROCESS`` for a
#: committed ``tracker: {egress: refused}``. Quoted, not paraphrased: a cell that asserted
#: only ``exit_code != 0`` would be satisfied by the un-armed abort (US1 sc3's negative pin).
_CHANNEL2_REFUSAL_FRAGMENT = (
    "Channel 2 refused: tracker.egress is recorded as 'refused' in this project's own .kittify/config.yaml; refusing tracker egress to local_subprocess"
)

#: Every module-level binding of ``tracker_egress_verdict`` that exists in the product today.
#: Re-derived by AST over ``src/`` rather than copied from the mission documents -- see
#: ``tests/architectural/test_tracker_egress_guards_3108.py``'s G4 census, the authoritative full
#: count across ``src/``: (as of the 2026-08-10 landing pass, PR #3135, HIGH-1 / #3108 follow-up)
#: 7 call expressions across 6 enclosing functions (``sync._render_tracker_egress`` x2,
#: ``LocalTrackerService.sync_pull``/``sync_push``/``sync_run``, ``SaaSTrackerClient._request``,
#: ``cli.commands.tracker._check_sync_readiness``), bound in exactly these four modules. The
#: fourth (``cli.commands.tracker``) is never reached by any cell in this class -- every fixture
#: here binds a LOCAL provider, and ``_check_sync_readiness``'s own verdict call sits on the
#: HOSTED_SERVICE branch, past the ``_is_local_binding()`` early return -- so it is watched here
#: purely for completeness (it is asserted at 0 in both cells below, the same way
#: ``saas_client``'s HOSTED-only binding already was before this addition). Each caller does
#: ``from ... import tracker_egress_verdict`` at import time, so the *caller's* module attribute
#: is the only observable seam -- patching the definition module would count nothing.
_VERDICT_BINDING_TARGETS = (
    "specify_cli.tracker.local_service.tracker_egress_verdict",
    "specify_cli.tracker.saas_client.tracker_egress_verdict",
    "specify_cli.cli.commands.sync.tracker_egress_verdict",
    "specify_cli.cli.commands.tracker.tracker_egress_verdict",
)


def _refusing_project(tmp_path: Path, name: str) -> _LocalFixture:
    """One ``beads``-bound project that records ``tracker: {egress: refused}``.

    Channel 1 is deliberately left *permitting* (``sync: {enabled: True}`` against a resolvable
    ``project.uuid``) so the only thing refusing is the project's own tracker key. A fixture
    that refused on both channels would leave a passing cell ambiguous about which half the
    ungated commands were surviving.
    """
    return _build_local_fixture(
        tmp_path,
        name=name,
        project_uuid=CONSENTING_PROJECT_UUID,
        sync_block={"enabled": True},
        tracker_egress="refused",
        seed=True,
    )


def _assert_gate_is_live(monkeypatch: pytest.MonkeyPatch, fx: _LocalFixture) -> None:
    """Discriminator: this exact repo root refuses a GATED command, on Channel 2, by name.

    Run first in every cell below. `sync pull` on a refusing fixture mutates nothing (it is
    refused before `_load_runtime`), so it is safe to run ahead of the ungated command under
    test and leaves the store and the config untouched -- asserted here via the recorder's
    zero-argv count.
    """
    refused = _invoke(monkeypatch, fx.repo_root, ["tracker", "sync", "pull"])
    assert refused.exit_code != 0, refused.output
    assert _CHANNEL2_REFUSAL_FRAGMENT in refused.output, refused.output
    assert len(fx.captured()) == 0, fx.captured()  # golden-count: cardinality-is-contract


def _json_payload(output: str) -> Any:
    """Parse the JSON object ``_print_json`` echoed, tolerating any preamble the CLI printed.

    ``tracker.py``'s ``_print_json`` is a bare ``typer.echo(json.dumps(...))``, but a future
    banner or deprecation line ahead of it must not turn a real payload assertion into a
    ``JSONDecodeError`` that reads as a gate. The brace search is anchored, and the parse
    failing is itself a legible failure.
    """
    start = output.index("{")
    return json.loads(output[start:])


class TestUS7NoOverGatingUngatedCommandsSurviveRefusal:
    """`#3174`: a project that refuses tracker egress keeps its local-only commands working.

    ``bind`` is **not** covered here, and that is a measured exclusion rather than an omission.
    ``tracker bind`` calls ``_check_readiness(require_mission_binding=False, ...)`` directly --
    it has no ``_is_local_binding()`` short-circuit, unlike ``_check_binding_readiness`` which
    serves ``status``/``map``/``unbind``. Measured under this file's isolated ``HOME``:

        tracker bind --provider beads --workspace acme-ws --credential command=... -> exit 1
        spec-kitty tracker: readiness=missing_auth next=spec-kitty-auth-login

    That is `#3172`'s class exactly -- a hosted auth pre-flight aborting a *local* invocation
    before mission code is reached -- and `#3172` is out of scope for this mission. Asserting
    ``exit_code == 0`` for ``bind`` is unreachable without faking an auth signal orthogonal to
    the egress gate, and asserting ``exit_code != 0`` would be a false green pointing the wrong
    way. Recorded as a residual instead. Note the gate is genuinely absent from ``bind`` either
    way: the binding-counter cell below proves zero verdict calls, and ``LocalTrackerService.bind``
    carries no verdict call in the census.
    """

    def test_status_succeeds_and_returns_the_local_payload_under_refusal(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The cell `#3174` names first: `status` on a refusing project reports the real local
        store, not a refusal and not an empty stub."""
        fx = _refusing_project(tmp_path, "no-over-gating-status")
        _assert_gate_is_live(monkeypatch, fx)

        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "status", "--json"])

        assert result.exit_code == 0, result.output
        payload = _json_payload(result.output)
        # Payload identity, not merely "it did not refuse": these fields can only come from
        # this fixture's own committed config and its own seeded sqlite store.
        assert payload["configured"] is True, payload
        assert payload["provider"] == "beads", payload
        assert payload["workspace"] == fx.workspace, payload
        assert payload["doctrine_mode"] == "spec_kitty_authoritative", payload
        assert payload["db_path"] == str(fx.db_path), payload
        assert payload["issue_count"] == 1, payload  # the seeded sentinel, read back through status
        assert payload["mapping_count"] == 0, payload
        assert payload["credentials_present"] is True, payload
        assert _CHANNEL2_REFUSAL_FRAGMENT not in result.output, result.output
        # `status` constructs no connector and runs no subprocess -- the recorder stays at zero
        # across the whole cell, refused command included.
        assert len(fx.captured()) == 0, fx.captured()  # golden-count: cardinality-is-contract

    def test_map_list_succeeds_and_returns_the_local_mapping_set_under_refusal(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`map list` without ``--provider`` -- the ungated spelling. The ``--provider`` spelling
        takes the hosted branch (``_check_readiness``) and is a different command shape."""
        fx = _refusing_project(tmp_path, "no-over-gating-map-list")
        _assert_gate_is_live(monkeypatch, fx)

        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "map", "list", "--json"])

        assert result.exit_code == 0, result.output
        payload = _json_payload(result.output)
        # An empty list is the *correct* answer for a fixture seeded with issues but no
        # mappings, and it is only meaningful because the roundtrip cell below shows the same
        # command returning a populated list on the same code path.
        assert payload == {"mappings": [], "pending_binding_upgrade": None}, payload
        assert _CHANNEL2_REFUSAL_FRAGMENT not in result.output, result.output
        assert len(fx.captured()) == 0, fx.captured()  # golden-count: cardinality-is-contract

    def test_map_add_then_map_list_roundtrip_under_refusal(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`map add` is a *write*, and the write must actually land: read it back through the
        separate ``map list`` command rather than trusting ``map add``'s own echo."""
        fx = _refusing_project(tmp_path, "no-over-gating-map-add")
        _assert_gate_is_live(monkeypatch, fx)

        added = _invoke(
            monkeypatch,
            fx.repo_root,
            ["tracker", "map", "add", "--wp-id", "WP01", "--external-id", "ext-3174"],
        )
        assert added.exit_code == 0, added.output
        assert "Mapping saved: WP01 -> ext-3174" in added.output, added.output

        listed = _invoke(monkeypatch, fx.repo_root, ["tracker", "map", "list", "--json"])
        assert listed.exit_code == 0, listed.output
        mappings = _json_payload(listed.output)["mappings"]
        assert len(mappings) == 1, mappings  # golden-count: cardinality-is-contract
        assert mappings[0]["wp_id"] == "WP01", mappings
        assert mappings[0]["external_id"] == "ext-3174", mappings
        assert mappings[0]["system"] == "beads", mappings
        assert mappings[0]["workspace"] == fx.workspace, mappings
        assert _CHANNEL2_REFUSAL_FRAGMENT not in added.output + listed.output
        assert len(fx.captured()) == 0, fx.captured()  # golden-count: cardinality-is-contract

    def test_unbind_succeeds_and_clears_the_binding_under_refusal(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`unbind` is destructive, so it runs last within its own cell and its effect is read
        back from the committed config rather than from ``status``.

        Measured: ``tracker status`` *after* an unbind exits 1 with
        ``readiness=missing_auth`` -- with no local binding left, ``_is_local_binding()`` is
        False and ``_check_binding_readiness`` falls through to the full hosted readiness
        chain. That is correct behaviour for an unbound checkout and is `#3172`'s pre-flight
        again, not the egress gate; asserting through it would couple this cell to an unrelated
        signal. ``load_tracker_config`` is the direct, uncoupled observation.
        """
        fx = _refusing_project(tmp_path, "no-over-gating-unbind")
        _assert_gate_is_live(monkeypatch, fx)
        assert load_tracker_config(fx.repo_root).provider == "beads"  # non-vacuity: bound before

        result = _invoke(monkeypatch, fx.repo_root, ["tracker", "unbind"])

        assert result.exit_code == 0, result.output
        assert "Tracker binding removed" in result.output, result.output
        assert _CHANNEL2_REFUSAL_FRAGMENT not in result.output, result.output
        assert load_tracker_config(fx.repo_root).provider is None
        assert len(fx.captured()) == 0, fx.captured()  # golden-count: cardinality-is-contract

    def test_ungated_commands_consult_no_verdict_binding_while_sync_pull_consults_one(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The census, executed. Delegating counters (never stubs) on all three module bindings
        of ``tracker_egress_verdict``; the ungated commands must leave every counter at zero,
        and the gated one on the same root must move exactly one of them.

        This is the cell that reds on an over-gating regression introduced at *any* existing
        binding, including one whose refusal a future command swallowed into an exit-0 path --
        a shape the exit-code cells above would miss.
        """
        counters = {target: _install_delegating_counter(monkeypatch, target) for target in _VERDICT_BINDING_TARGETS}
        fx = _refusing_project(tmp_path, "no-over-gating-counters")

        for args in (
            ["tracker", "status", "--json"],
            ["tracker", "map", "list", "--json"],
            ["tracker", "map", "add", "--wp-id", "WP01", "--external-id", "ext-3174"],
            ["tracker", "unbind"],
        ):
            result = _invoke(monkeypatch, fx.repo_root, args)
            assert result.exit_code == 0, f"{' '.join(args)}: {result.output}"
        assert {t: c[0] for t, c in counters.items()} == dict.fromkeys(_VERDICT_BINDING_TARGETS, 0)

        # Non-vacuity for the counters themselves: the same wrappers, the same process, a
        # command that *is* gated. Re-bind first -- the unbind above cleared the binding.
        rebound = _refusing_project(tmp_path, "no-over-gating-counters-gated")
        refused = _invoke(monkeypatch, rebound.repo_root, ["tracker", "sync", "pull"])
        assert refused.exit_code != 0, refused.output
        assert _CHANNEL2_REFUSAL_FRAGMENT in refused.output, refused.output
        assert {t: c[0] for t, c in counters.items()} == {
            "specify_cli.tracker.local_service.tracker_egress_verdict": 1,
            "specify_cli.tracker.saas_client.tracker_egress_verdict": 0,
            "specify_cli.cli.commands.sync.tracker_egress_verdict": 0,
            "specify_cli.cli.commands.tracker.tracker_egress_verdict": 0,
        }  # golden-count: cardinality-is-contract


# ===========================================================================
# Landing pass (PR #3135, 2026-08-10) -- HIGH-1: refusal precedes the
# readiness network probe on the hosted sync path (#3108 follow-up).
# ===========================================================================


class TestHigh1RefusalPrecedesReadinessNetworkProbe:
    """HIGH-1 (#3108 follow-up): ``_check_sync_readiness``'s hosted (SaaS-backed) branch called
    ``_check_readiness(..., probe_reachability=True)`` as its very first act. Once auth and
    host-config both resolve, that call issues a real ``urllib.request.urlopen`` HEAD probe
    (``saas/readiness.py:_probe_reachability``) to the configured SaaS host -- *before*
    ``SaaSTrackerClient._request``'s own Channel-1/Channel-2 ``tracker_egress_verdict`` gate
    (the one this Mission's WP04/WP05 landed) ever ran. A project whose hosted-sync consent is
    absent or refused therefore still emitted one HTTP HEAD to the tracker host ahead of the
    eventual refusal -- "refusal precedes any HTTP attempt" was violated on the CLI's own
    pre-flight, one layer above every gate this Mission's own harness (above) exercises.

    Fixed by consulting ``tracker_egress_verdict`` inside ``_check_sync_readiness`` itself,
    before ``_check_readiness`` is called at all, reusing the exact
    ``TrackerEgressRefusedError`` / ``TRACKER_EGRESS_IDENTIFIER_KINDS`` pairing
    ``SaaSTrackerClient._request`` already uses so the refusal text stays byte-identical.

    Auth and host-config are monkeypatched to *pass* here -- not because the fix depends on it,
    but because the pre-fix bug is only reachable once both already resolve (an isolated,
    unauthenticated ``HOME`` hits ``MISSING_AUTH`` before reachability regardless, which would
    make the reachability probe unreachable for an unrelated reason on both the red and the
    green run, proving nothing about this specific ordering defect).
    """

    def test_sync_pull_refuses_before_any_reachability_probe(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Red on the pre-fix ``_check_sync_readiness`` (the reachability probe fires before
        refusal); green after (refusal fires first, the probe is never reached)."""
        root = _project(tmp_path, "high1-sync-pull")
        # Channel 1 refuses: no `project.uuid`, so the project's identity never resolves --
        # `_classify_channel1`'s `CHANNEL1_NOT_CONSENTABLE` state. Channel 2 is absent (no
        # `tracker.egress` key), so the verdict is Channel-1-decided either way.
        _write_jira_config(root, project_uuid=None, sync_block=None, tracker_egress=None)

        monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: True)
        monkeypatch.setattr("specify_cli.saas.readiness._probe_host_config", lambda: "https://saas.example.test")

        reachability_calls: list[str] = []

        def _counting_probe_reachability(server_url: str, timeout_s: float = 2.0) -> bool:
            reachability_calls.append(server_url)
            return False

        monkeypatch.setattr("specify_cli.saas.readiness._probe_reachability", _counting_probe_reachability)

        result = _invoke(monkeypatch, root, ["tracker", "sync", "pull"])

        # The HIGH-1 pin: on the pre-fix tree this list is non-empty (the probe fired ahead of
        # refusal); the fix must leave it empty.
        assert reachability_calls == [], (
            f"HIGH-1: the reachability probe fired {len(reachability_calls)} time(s) ({reachability_calls}) before the hosted-egress refusal was ever consulted."
        )
        assert result.exit_code != 0, result.output
        assert "Refusing to send tracker data to Spec Kitty SaaS" in result.output, result.output

    def test_sync_pull_permitting_verdict_still_reaches_the_reachability_probe(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Companion positive control: a PERMITTED verdict must change nothing -- execution still
        falls through to ``_check_readiness`` and its reachability probe exactly as before. Proves
        the fix narrows (refuse-first) rather than removes (skip-always) the existing readiness
        chain."""
        root = _project(tmp_path, "high1-sync-pull-permitted")
        _write_jira_config(
            root,
            project_uuid=CONSENTING_PROJECT_UUID,
            sync_block={"enabled": True},
            tracker_egress=None,
        )

        monkeypatch.setattr("specify_cli.saas.readiness._probe_auth", lambda *_: True)
        monkeypatch.setattr("specify_cli.saas.readiness._probe_host_config", lambda: "https://saas.example.test")

        reachability_calls: list[str] = []

        def _counting_probe_reachability(server_url: str, timeout_s: float = 2.0) -> bool:
            reachability_calls.append(server_url)
            return False

        monkeypatch.setattr("specify_cli.saas.readiness._probe_reachability", _counting_probe_reachability)

        result = _invoke(monkeypatch, root, ["tracker", "sync", "pull"])

        assert reachability_calls == ["https://saas.example.test"], reachability_calls
        # Reachability fails (mocked False) -> HOST_UNREACHABLE -> non-zero exit. The point of
        # this control is that the probe *ran*, not that the overall command succeeded. Rendered
        # under this harness's non-interactive OutputPolicy as the stable
        # ``readiness=host_unreachable`` token (see ``_render_readiness_failure``), not the
        # 2-line interactive message.
        assert result.exit_code != 0, result.output
        assert "readiness=host_unreachable" in result.output, result.output


# ===========================================================================
# Landing pass (PR #3135, 2026-08-10) -- HIGH-3: local `tracker bind` was
# over-gated against the documented promise (#3174).
# ===========================================================================


class TestHigh3LocalBindSkipsHostedReadiness:
    """HIGH-3 (#3174): ``docs/migrations/tracker-egress-refusal.md``'s "Which Commands Are
    Gated" table promises ``tracker bind`` keeps a refusing/local project working. Before this
    fix, ``bind_command`` called ``_check_readiness(require_mission_binding=False,
    probe_reachability=False)`` *unconditionally*, ahead of the local-provider branch -- so an
    unauthenticated project's ``tracker bind --provider beads ...`` failed at ``missing_auth``
    before ever reaching the local-bind code path, contradicting the documented promise. `#3172`'s
    own class of defect (a hosted auth pre-flight aborting a *local* invocation), applied here to
    `bind` specifically. This Mission's own harness (``TestUS7NoOverGatingUngatedCommandsSurviveRefusal``
    above) explicitly recorded `bind` as **excluded** from its over-gating coverage for exactly
    this measured reason -- this class is the fix for that recorded exclusion, not a duplicate of
    it.

    Fixed by gating the readiness call on ``normalize_provider(provider) in LOCAL_PROVIDERS``
    (``bind`` creates the binding, so there is no existing config for ``_is_local_binding()`` to
    read). SaaS providers keep the existing readiness check unchanged.
    """

    def test_local_bind_succeeds_without_hosted_auth(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Red on the pre-fix ``bind_command`` (exits 1, ``readiness=missing_auth``); green
        after (the binding is created, exit 0)."""
        root = _project(tmp_path, "high3-local-bind")

        result = _invoke(
            monkeypatch,
            root,
            [
                "tracker",
                "bind",
                "--provider",
                "beads",
                "--workspace",
                "acme-ws",
                "--credential",
                "command=/bin/true",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "missing_auth" not in result.output, result.output
        assert "Tracker binding saved" in result.output, result.output

        config = load_tracker_config(root)
        assert config.provider == "beads", config
        assert config.workspace == "acme-ws", config

    def test_hosted_bind_still_requires_hosted_readiness(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Companion positive control: a SaaS-provider ``bind`` must still hit the hosted
        readiness pre-flight (unauthenticated -> ``missing_auth``), unchanged by this fix."""
        root = _project(tmp_path, "high3-hosted-bind")

        result = _invoke(
            monkeypatch,
            root,
            ["tracker", "bind", "--provider", "jira"],
        )

        assert result.exit_code != 0, result.output
        assert "missing_auth" in result.output or "No SaaS authentication token" in result.output, result.output
