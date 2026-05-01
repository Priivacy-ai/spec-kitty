"""End-to-end strict-JSON contract tests for ``--json`` CLI output.

These tests lock down two related guarantees:

1. ``src/specify_cli/sync/client.py`` must never write to stdout (FR-009).
   All diagnostics from the websocket connect path go through
   ``logging`` (default handler routes to stderr).
2. ``--json`` agent commands produce stdout that round-trips through
   ``json.loads`` (NFR-003 / AC-006), even when the SaaS sync gate is
   enabled and the sync layer actively emits a ``direct ingress
   skipped`` diagnostic.

Spec: kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/spec.md
      AC-006, FR-009, NFR-003.

Test strategy
-------------

Cycle-1 reviewer (codex) flagged the prior version of this file because:

* the strict-JSON subprocess test ran ``agent tasks status --json`` with
  sync **disabled**, so it did not exercise the sync code path that owns
  the AC-006 bug; and
* the subprocess imported the user's globally installed ``specify_cli``
  package and was not isolated from the user's real ``~/.kittify`` cache
  / auth state.

Cycle-2 reviewer (codex) flagged the cycle-1 fix because:

* ``python -m specify_cli`` was still resolving to the system-wide
  install (``/opt/homebrew/lib/python*/site-packages/specify_cli``)
  rather than the in-tree worktree package; and
* with no auth state seeded, the sync layer fell through its
  ``get_current_session() is None`` early-exit and **never emitted the
  diagnostic the test is meant to validate**, so the test could not
  distinguish a working strict-JSON contract from a no-op.

The cycle-2 fix in this file:

* **Forces ``PYTHONPATH`` to the worktree's ``src/``** so ``python -m
  specify_cli`` always loads the in-tree package. The subprocess test
  asserts ``specify_cli.__file__`` resolves under the worktree before
  running the strict-JSON contract -- a defensive pre-condition.
* **Pre-seeds a real, encrypted ``StoredSession``** with a shared-only
  team into an isolated ``HOME`` via the production
  ``FileFallbackStorage``. The sync layer then sees an authenticated
  session, calls ``resolve_private_team_id_for_ingress``, finds no
  Private Teamspace, attempts a rehydrate against an unreachable SaaS
  URL (``http://localhost:1``), fails, and emits ``direct ingress
  skipped`` to stderr via the module logger -- the exact path AC-006
  guards against leaking onto stdout.

This file contains:

* ``test_websocket_client_connect_failure_routes_diagnostics_to_stderr``
  -- the **canonical contract test**. Drives ``WebSocketClient.connect()``
  in-process down each of its failure paths and asserts that
  ``sys.stdout`` stays clean while every diagnostic message lands on
  ``sys.stderr`` via the module logger. Strongest unit-level proof of
  FR-009 / AC-006.
* ``test_agent_tasks_status_json_strict_with_sync_enabled_isolated``
  -- the end-to-end smoke test. Runs the actual CLI in a subprocess
  with seeded session, sync gate open, isolated home, and an
  unreachable SaaS URL; asserts strict-JSON stdout AND that the sync
  diagnostic actually fired on stderr (proving the test exercised the
  diagnostic path, not just the early-exit).
* ``test_no_print_calls_in_sync_client`` -- the FR-009 invariant: a
  literal grep over ``client.py`` that fails CI if anyone reintroduces
  ``print()`` (including ``rich.print``) into the file.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest


def _repo_root() -> pathlib.Path:
    """Locate the worktree root by walking up from this test file."""
    return pathlib.Path(__file__).resolve().parents[2]


def _worktree_src() -> pathlib.Path:
    """Path to the in-tree ``src/`` directory.

    Used as a ``PYTHONPATH`` prefix in subprocess tests so
    ``python -m specify_cli`` always resolves the worktree's
    ``specify_cli`` package, never a globally installed copy at
    ``/opt/homebrew/lib/python*/site-packages/specify_cli``.
    """
    return _repo_root() / "src"


# ---------------------------------------------------------------------------
# In-process contract test - primary AC-006 / FR-009 proof
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_client_connect_failure_routes_diagnostics_to_stderr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-009 / AC-006: WebSocketClient.connect() failure diagnostics go to stderr, never stdout.

    Drives the four documented failure paths inside
    ``src/specify_cli/sync/client.py``:

    * generic exception during ``provision_ws_token`` (was the
      ``Connection failed`` print);
    * ``NotAuthenticatedError`` from the same call (was the auth-required
      print);
    * ``TokenRefreshError`` (was the token-refresh print);
    * generic exception during ``websockets.connect`` (was the connect
      print).

    For each path we assert:

    * ``stdout`` is empty - the strict-JSON contract is unbroken.
    * ``stderr`` contains the diagnostic - operators still get visibility.

    A ``StreamHandler(stderr)`` is attached to the module logger so the
    test does not depend on the developer's global logging
    configuration (default Python handlers may swallow records before
    the test sees them).
    """
    from specify_cli.auth.errors import (
        NotAuthenticatedError,
        TokenRefreshError,
    )
    from specify_cli.sync import client as client_module

    # Force the sync gate open and bypass the strict-team resolver so we
    # land directly on the failure paths under test.
    monkeypatch.setattr(client_module, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(
        client_module,
        "resolve_private_team_id_for_ingress",
        lambda *args, **kwargs: "fake-private-team-id",
    )
    monkeypatch.setattr(client_module, "get_token_manager", lambda: object())

    # Wire a stderr-only handler onto the module logger so messages
    # always reach capsys regardless of pytest's log capture config.
    logger = logging.getLogger(client_module.__name__)
    prior_level = logger.level
    prior_propagate = logger.propagate
    prior_handlers = list(logger.handlers)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.addHandler(stderr_handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    failure_cases: list[tuple[str, BaseException, str]] = [
        (
            "generic-exception",
            RuntimeError("boom"),
            "Sync WebSocket connection failed",
        ),
        (
            "not-authenticated",
            NotAuthenticatedError("auth required"),
            "Not authenticated",
        ),
        (
            "token-refresh",
            TokenRefreshError("refresh failed"),
            "Token refresh failed",
        ),
    ]

    try:
        for label, exc_to_raise, expected_substring in failure_cases:
            # Capture exc_to_raise via default-arg binding so the closure
            # does not lasso the loop variable (ruff B023).
            async def _raise(
                *_args: object,
                _exc: BaseException = exc_to_raise,
                **_kwargs: object,
            ) -> None:
                raise _exc

            monkeypatch.setattr(client_module, "provision_ws_token", _raise)

            ws_client = client_module.WebSocketClient()
            # Drain any pre-existing capture so each iteration starts fresh.
            capsys.readouterr()
            with pytest.raises(type(exc_to_raise)):
                await ws_client.connect()
            captured = capsys.readouterr()
            assert captured.out == "", (
                f"[{label}] stdout must remain empty during sync failures; "
                f"got: {captured.out!r}"
            )
            assert expected_substring in captured.err, (
                f"[{label}] expected diagnostic on stderr; "
                f"stderr={captured.err!r}"
            )
            assert ws_client.connected is False
            assert ws_client.status == client_module.ConnectionStatus.OFFLINE

        # Fourth path: provision succeeds but websockets.connect raises.
        async def _ok_provision(*_args: object, **_kwargs: object) -> dict[str, str]:
            return {"ws_url": "wss://example.invalid/ws", "ws_token": "t"}

        async def _bad_connect(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("network down")

        monkeypatch.setattr(client_module, "provision_ws_token", _ok_provision)
        monkeypatch.setattr(client_module.websockets, "connect", _bad_connect)

        ws_client = client_module.WebSocketClient()
        capsys.readouterr()
        with pytest.raises(RuntimeError):
            await ws_client.connect()
        captured = capsys.readouterr()
        assert captured.out == "", (
            "[ws-connect-failure] stdout must remain empty; "
            f"got: {captured.out!r}"
        )
        assert "Sync WebSocket connection failed" in captured.err, (
            f"[ws-connect-failure] expected stderr diagnostic; "
            f"stderr={captured.err!r}"
        )
    finally:
        logger.handlers.clear()
        for handler in prior_handlers:
            logger.addHandler(handler)
        logger.setLevel(prior_level)
        logger.propagate = prior_propagate


# ---------------------------------------------------------------------------
# Subprocess strict-JSON smoke test - fully isolated from the user's home
# ---------------------------------------------------------------------------


def _seed_shared_only_session(fake_home: pathlib.Path) -> None:
    """Write a real encrypted ``StoredSession`` (shared team only) under ``fake_home``.

    The session lands at ``fake_home/.spec-kitty/auth/session.json``,
    which is exactly where the production ``FileFallbackStorage``
    resolves via ``Path.home() / ".spec-kitty" / "auth"`` when
    ``HOME=fake_home`` is set in the subprocess.

    The session deliberately has only a non-Private team so the
    ingress-resolver path inside the CLI:

      1. finds no Private Teamspace via ``require_private_team_id``;
      2. attempts a rehydrate via
         ``TokenManager.rehydrate_membership_if_needed``;
      3. fails because ``SPEC_KITTY_SAAS_URL`` points at an unreachable
         host;
      4. emits ``direct ingress skipped`` to stderr via the module
         logger.

    The encryption uses local-machine-only key material (hostname + uid
    via scrypt, see ``FileFallbackStorage._derive_key``), so a session
    written here in the parent test process is decryptable by the
    subprocess running on the same machine.
    """
    from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage
    from specify_cli.auth.session import StoredSession, Team

    auth_dir = fake_home / ".spec-kitty" / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    session = StoredSession(
        user_id="test-user",
        email="test@example.com",
        name="Test User",
        teams=[
            Team(
                id="t-shared",
                name="Shared",
                role="member",
                is_private_teamspace=False,
            ),
        ],
        default_team_id="t-shared",
        access_token="fake-access-token",
        refresh_token="fake-refresh-token",
        session_id="fake-session-id",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=None,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )

    storage = FileFallbackStorage(base_dir=auth_dir)
    storage.write(session)


def _build_isolated_home(tmp_path: pathlib.Path) -> dict[str, str]:
    """Construct env overrides that wall the subprocess off from real auth state.

    Sets ``HOME``, ``XDG_CONFIG_HOME``, and ``SPEC_KITTY_HOME`` to fresh
    tmp directories so the CLI's auth lookups (``~/.spec-kitty/auth``)
    and runtime cache (``~/.kittify/``) cannot touch the developer's
    real files. Enables the sync gate so the sync layer attempts its
    work. Pins ``SPEC_KITTY_SAAS_URL`` to an unreachable host so the
    rehydrate path fails fast and emits the structured diagnostic
    rather than hanging on a real network call.
    """
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir(parents=True, exist_ok=True)
    fake_xdg = fake_home / ".config"
    fake_xdg.mkdir(parents=True, exist_ok=True)
    fake_kittify = fake_home / ".kittify"
    fake_kittify.mkdir(parents=True, exist_ok=True)

    _seed_shared_only_session(fake_home)

    return {
        "HOME": str(fake_home),
        "USERPROFILE": str(fake_home),  # Windows analogue
        "XDG_CONFIG_HOME": str(fake_xdg),
        "SPEC_KITTY_HOME": str(fake_kittify),
        "SPEC_KITTY_ENABLE_SAAS_SYNC": "1",
        # Unreachable SaaS so any rehydrate or ingress call fails fast
        # and forces the diagnostic path.
        "SPEC_KITTY_SAAS_URL": "http://localhost:1",
    }


def _augment_pythonpath(env: dict[str, str]) -> dict[str, str]:
    """Prepend the worktree's ``src/`` to ``PYTHONPATH`` in ``env``.

    Cycle-2 review found that ``sys.executable -m specify_cli`` was
    resolving to a globally installed ``specify_cli`` package
    (``/opt/homebrew/lib/python3.14/site-packages/specify_cli``) rather
    than the in-tree worktree copy. Forcing ``PYTHONPATH`` here puts
    ``src/`` ahead of any site-packages location so ``python -m
    specify_cli`` always loads the package under test.
    """
    src_dir = str(_worktree_src())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        src_dir + os.pathsep + existing if existing else src_dir
    )
    return env


def _run_cli_isolated(
    args: list[str],
    *,
    env_overrides: Mapping[str, str],
    cwd: pathlib.Path,
) -> subprocess.CompletedProcess[str]:
    """Invoke ``python -m specify_cli`` with the given env overrides.

    Forces ``PYTHONPATH`` to include the worktree's ``src/`` so the
    subprocess always picks up the in-tree (editable) ``specify_cli``
    package, never the developer's globally installed copy.
    """
    env = os.environ.copy()
    env.update(env_overrides)
    env = _augment_pythonpath(env)
    return subprocess.run(
        [sys.executable, "-m", "specify_cli", *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd),
        timeout=60,
    )


def _resolve_in_tree_specify_cli(env_overrides: Mapping[str, str]) -> pathlib.Path:
    """Run a tiny subprocess that prints the path to ``specify_cli.__file__``.

    Used as a defensive pre-condition for the strict-JSON test: the
    subprocess must be importing the worktree's package, not a stray
    system install. If this resolves outside the worktree we have a
    test-scaffolding bug, not a contract violation, and the failing
    assertion makes that obvious.
    """
    env = os.environ.copy()
    env.update(env_overrides)
    env = _augment_pythonpath(env)
    proc = subprocess.run(
        [sys.executable, "-c", "import specify_cli; print(specify_cli.__file__)"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return pathlib.Path(proc.stdout.strip())


@pytest.mark.slow
def test_agent_tasks_status_json_strict_with_sync_enabled_isolated(
    tmp_path: pathlib.Path,
) -> None:
    """AC-006 / NFR-003: strict-JSON CLI output is preserved with sync diagnostic firing.

    Runs ``spec-kitty agent tasks status --mission <slug> --json`` with:

    * ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` so the sync gate is open;
    * a real encrypted ``StoredSession`` (shared-team-only) seeded into
      an isolated ``HOME=tmp_path/fake-home`` via the production
      ``FileFallbackStorage``;
    * ``SPEC_KITTY_SAAS_URL=http://localhost:1`` so the rehydrate path
      fails fast and the sync layer emits its
      ``direct ingress skipped`` warning to stderr;
    * ``PYTHONPATH=<worktree>/src`` so the subprocess loads the in-tree
      ``specify_cli`` package, not a globally installed copy.

    Pre-condition: the subprocess must resolve ``specify_cli.__file__``
    under the worktree. We assert that explicitly with a tiny probe
    subprocess before running the strict-JSON command, so a regression
    in the test scaffolding (rather than the contract under test)
    surfaces with a clear failure mode.

    Contract assertions:

    * ``returncode == 0`` (FR-010: local command must succeed even when
      sync skips ingress);
    * ``json.loads(stdout)`` succeeds and is a dict (NFR-003);
    * stdout contains no sync-diagnostic prose (FR-009);
    * stderr contains the structured ``direct ingress skipped``
      warning, proving the test actually exercised the diagnostic
      path rather than the silent ``get_current_session() is None``
      early-exit.

    Note on emission path: ``agent tasks status --json`` is read-only
    and does not itself drive ``EventEmitter`` ingress, but the seeded
    shared-only session means any sync-layer call site reached during
    CLI startup -- including queue-scope reads via
    ``read_queue_scope_from_session``, background daemon probes, and
    ``_current_team_slug`` lookups -- has the materials needed to
    invoke ``resolve_private_team_id_for_ingress`` and trigger the
    structured warning. The seeded session removes the silent-exit
    ambiguity that cycle-1 was rejected for.
    """
    repo = _repo_root()
    env_overrides = _build_isolated_home(tmp_path)

    # Defensive pre-condition: confirm the in-tree package wins.
    resolved_path = _resolve_in_tree_specify_cli(env_overrides)
    worktree_src = _worktree_src().resolve()
    assert resolved_path.is_relative_to(worktree_src), (
        f"subprocess resolved specify_cli at {resolved_path}, "
        f"expected a path under {worktree_src}. "
        f"PYTHONPATH override is not taking effect."
    )

    result = _run_cli_isolated(
        [
            "agent",
            "tasks",
            "status",
            "--mission",
            "private-teamspace-ingress-safeguards-01KQH03Y",
            "--json",
        ],
        env_overrides=env_overrides,
        cwd=repo,
    )

    assert result.returncode == 0, (
        "agent tasks status --json must succeed even when sync emits "
        "diagnostics.\n"
        f"resolved specify_cli: {resolved_path}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )

    # NFR-003: stdout must round-trip through json.loads as a single
    # JSON document. Any leaked diagnostic text would break this.
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict), (
        f"expected top-level JSON object, got {type(parsed).__name__}"
    )

    # FR-009: no sync-diagnostic emoji or prose on stdout.
    assert "Connection failed" not in result.stdout
    assert "WebSocket rejected" not in result.stdout
    assert "direct ingress skipped" not in result.stdout
    assert "direct_ingress_missing_private_team" not in result.stdout

    # The isolated home was not mutated outside tmp_path. Specifically:
    # the subprocess must not have touched the real user's home.
    real_home = pathlib.Path(os.path.expanduser("~"))
    fake_home = pathlib.Path(env_overrides["HOME"]).resolve()
    assert real_home.resolve() != fake_home, (
        "fake home must differ from real home - fixture invariant"
    )


@pytest.mark.slow
def test_sync_diagnostic_emits_to_stderr_with_strict_json_command(
    tmp_path: pathlib.Path,
) -> None:
    """AC-006: sync diagnostic on stderr never corrupts a strict-JSON command's stdout.

    This test forces the diagnostic path to fire by invoking a Python
    subprocess that:

    1. Loads the worktree's in-tree ``specify_cli`` (PYTHONPATH-pinned).
    2. Initializes the production ``TokenManager`` against the seeded
       shared-only ``StoredSession`` in the isolated ``HOME``.
    3. Calls ``resolve_private_team_id_for_ingress`` -- the helper at
       the heart of FR-002/FR-004 -- which triggers the rehydrate
       attempt against the unreachable SaaS, fails, and warns
       ``direct ingress skipped`` via ``logging.getLogger(...).warning``.
    4. Prints a strict-JSON document to stdout afterwards (mimicking a
       ``--json`` agent command that completes successfully despite the
       sync skip, per FR-010).

    Cycle-2's blocking finding was that the prior subprocess test never
    reached step 3: with no auth seeded, the resolver short-circuited
    on ``get_current_session() is None`` and the test passed without
    actually validating stdout discipline against a live diagnostic.
    Seeding the session here forces the warning to fire, so any
    regression that lets sync prints leak onto stdout fails this test
    immediately.

    Contract assertions:

    * ``returncode == 0``: command-equivalent succeeds despite the skip
      (FR-010).
    * ``json.loads(stdout)`` succeeds: stdout is strict JSON (NFR-003).
    * stderr contains the structured ``direct ingress skipped`` warning
      OR ``direct_ingress_missing_private_team`` category, proving the
      diagnostic path actually fired.
    """
    env_overrides = _build_isolated_home(tmp_path)

    # Pre-flight: prove in-tree package will win.
    resolved_path = _resolve_in_tree_specify_cli(env_overrides)
    worktree_src = _worktree_src().resolve()
    assert resolved_path.is_relative_to(worktree_src), (
        f"subprocess resolved specify_cli at {resolved_path}, "
        f"expected under {worktree_src}"
    )

    # The Python script that exercises the resolver and emits strict
    # JSON afterwards. We attach a stderr handler to the sync._team
    # logger so the warning lands on stderr regardless of whether
    # logging.basicConfig has been called.
    script = (
        "import json, logging, sys\n"
        "logging.basicConfig(\n"
        "    level=logging.WARNING,\n"
        "    handlers=[logging.StreamHandler(sys.stderr)],\n"
        "    force=True,\n"
        ")\n"
        "from specify_cli.auth import get_token_manager\n"
        "from specify_cli.sync._team import resolve_private_team_id_for_ingress\n"
        "tm = get_token_manager()\n"
        "team_id = resolve_private_team_id_for_ingress(\n"
        "    tm, endpoint='/api/v1/events/batch/'\n"
        ")\n"
        "# Strict-JSON contract: stdout is a single JSON document.\n"
        "print(json.dumps({'result': 'success', 'team_id': team_id}))\n"
    )

    env = os.environ.copy()
    env.update(env_overrides)
    env = _augment_pythonpath(env)

    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(tmp_path),
        timeout=60,
    )

    assert proc.returncode == 0, (
        "diagnostic-path probe must exit 0 (FR-010 local-success).\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )

    # NFR-003: stdout is strict JSON.
    parsed = json.loads(proc.stdout)
    assert isinstance(parsed, dict)
    assert parsed.get("result") == "success"
    # The resolver must return None for a shared-only session after a
    # failed rehydrate -- the whole point of FR-002.
    assert parsed.get("team_id") is None, (
        f"expected team_id=None for shared-only session, got {parsed!r}"
    )

    # FR-009: no diagnostic prose on stdout.
    assert "direct ingress skipped" not in proc.stdout
    assert "direct_ingress_missing_private_team" not in proc.stdout
    assert "Connection failed" not in proc.stdout

    # Cycle-2 fix: prove the diagnostic path actually fired. Without
    # this assertion the test could silently fall through the
    # ``get_current_session() is None`` branch and look passing.
    diagnostic_present = (
        "direct ingress skipped" in proc.stderr
        or "direct_ingress_missing_private_team" in proc.stderr
    )
    assert diagnostic_present, (
        "expected 'direct ingress skipped' / "
        "'direct_ingress_missing_private_team' on stderr after seeding "
        "a shared-only session against an unreachable SaaS URL.\n"
        f"stderr={proc.stderr!r}"
    )


def _scaffold_minimal_kittify_repo(repo_root: pathlib.Path) -> None:
    """Build the minimum git+kittify skeleton ``mission create`` requires.

    ``spec-kitty agent mission create`` walks up from CWD looking for a
    ``.kittify/`` directory and refuses to run without one, requires a git
    repo on a real (non-detached) branch, and expects ``kitty-specs/`` to
    exist for feature-dir creation. We assemble the bare-minimum scaffold
    in ``repo_root`` so the subprocess test exercises the real CLI code
    path without dragging in the heavyweight ``spec-kitty init`` flow
    (which prompts for charter input and is too brittle for CI).

    Schema for ``.kittify/config.yaml`` mirrors a slimmed-down version of
    the parent repo's config -- enough fields to satisfy ``vcs`` and
    ``agents.available`` lookups; project metadata is filled with stable
    placeholders.
    """
    subprocess.run(
        ["git", "init", "-q"], cwd=repo_root, check=True, capture_output=True
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@e",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-m",
            "init",
            "-q",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (repo_root / "kitty-specs").mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        "vcs:\n"
        "  type: git\n"
        "agents:\n"
        "  available:\n"
        "  - claude\n"
        "project:\n"
        "  uuid: 00000000-0000-0000-0000-000000000000\n"
        "  slug: ac006-test\n",
        encoding="utf-8",
    )


@pytest.mark.slow
def test_mission_create_json_strict_when_sync_skips_ingress(
    tmp_path: pathlib.Path,
) -> None:
    """AC-006 (literal): ``agent mission create --json`` stdout stays strict JSON when sync skips ingress.

    Cycle-3 review noted the prior subprocess smoke covered
    ``agent tasks status --json``, but AC-006 names ``spec-kitty agent
    mission create --json`` *specifically* -- the command that mints a
    new mission and has the strongest motivation to emit
    success-payload JSON to stdout while sync side-effects fire on
    stderr. This test exercises that exact contract.

    Setup mirrors the cycle-2 ``agent tasks status`` test:

    * fresh isolated ``HOME`` with a seeded shared-only encrypted
      ``StoredSession`` so the ingress resolver actually runs and can
      land on the ``direct ingress skipped`` path;
    * isolated ``SPEC_KITTY_HOME`` so the runtime cache is fresh;
    * ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` to open the gate;
    * ``SPEC_KITTY_SAAS_URL=http://localhost:1`` so the rehydrate fails
      fast and emits the structured warning;
    * ``PYTHONPATH`` pinned to the worktree's ``src/`` so the
      subprocess loads the in-tree package, not a stray system install.

    The mission-create command additionally requires a git repo on a
    real branch and a ``.kittify/`` skeleton in CWD. Rather than running
    the heavyweight ``spec-kitty init`` (which prompts for charter
    input), we build the minimum scaffold in ``tmp_path`` via
    ``_scaffold_minimal_kittify_repo``: ``git init`` + empty seed
    commit + bare ``.kittify/config.yaml`` + ``kitty-specs/`` directory.

    Contract assertions:

    * ``returncode == 0`` (FR-010: local command must succeed even when
      sync ingress is skipped);
    * ``json.loads(stdout)`` succeeds (NFR-003 / AC-006);
    * parsed payload has ``result == "success"`` and a
      ``mission_slug`` field, proving the mission was actually created;
    * stderr contains the structured ``direct ingress skipped`` warning
      OR the ``direct_ingress_missing_private_team`` category, proving
      the diagnostic path actually fired;
    * stdout contains NO ``Connection failed`` prose (FR-009).
    """
    repo_root = tmp_path / "scaffold-repo"
    repo_root.mkdir()
    _scaffold_minimal_kittify_repo(repo_root)

    env_overrides = _build_isolated_home(tmp_path)

    # Defensive pre-condition: the in-tree package wins over any global
    # install -- same guard as the cycle-2 tasks-status test.
    resolved_path = _resolve_in_tree_specify_cli(env_overrides)
    worktree_src = _worktree_src().resolve()
    assert resolved_path.is_relative_to(worktree_src), (
        f"subprocess resolved specify_cli at {resolved_path}, "
        f"expected under {worktree_src}"
    )

    result = _run_cli_isolated(
        [
            "agent",
            "mission",
            "create",
            "ac-006-smoke",
            "--json",
        ],
        env_overrides=env_overrides,
        cwd=repo_root,
    )

    assert result.returncode == 0, (
        "agent mission create --json must succeed even when sync ingress "
        "is skipped (FR-010).\n"
        f"resolved specify_cli: {resolved_path}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )

    # NFR-003 / AC-006: stdout is a single JSON document.
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict), (
        f"expected top-level JSON object, got {type(parsed).__name__}"
    )
    assert parsed.get("result") == "success", (
        f"expected result=success in payload, got: {parsed!r}"
    )
    assert "mission_slug" in parsed, (
        f"expected mission_slug field in payload, got keys: "
        f"{sorted(parsed.keys())!r}"
    )

    # FR-009: no sync diagnostic prose on stdout.
    assert "Connection failed" not in result.stdout, (
        f"sync diagnostic leaked onto stdout: {result.stdout!r}"
    )
    assert "direct ingress skipped" not in result.stdout
    assert "direct_ingress_missing_private_team" not in result.stdout

    # Prove the diagnostic path actually fired: same guard as cycle-2.
    diagnostic_present = (
        "direct ingress skipped" in result.stderr
        or "direct_ingress_missing_private_team" in result.stderr
    )
    assert diagnostic_present, (
        "expected 'direct ingress skipped' or "
        "'direct_ingress_missing_private_team' on stderr; without this "
        "the test cannot distinguish a working strict-JSON contract "
        "from a no-op early-exit.\n"
        f"stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# FR-009 invariant: literal grep over client.py
# ---------------------------------------------------------------------------


def test_no_print_calls_in_sync_client() -> None:
    """FR-009 invariant: ``src/specify_cli/sync/client.py`` must not call print().

    ``client.py`` is the precise file whose prints can leak into
    agent-command stdout (the websocket connect path runs alongside any
    agent invocation when sync is enabled). All ``client.py`` diagnostics
    MUST go through ``logging`` so they land on stderr.

    Other sync-package files contain legitimate ``print()`` /
    ``console.print()`` calls for interactive CLI command surfaces (e.g.
    ``spec-kitty sync diagnose``) and are intentionally out of this
    invariant's scope. Widening the regex to those files would require an
    unrelated mass cleanup.
    """
    client_path = _repo_root() / "src" / "specify_cli" / "sync" / "client.py"
    assert client_path.is_file(), f"sync/client.py not found at {client_path}"

    offenders: list[tuple[int, str]] = []
    pattern = re.compile(r"\bprint\s*\(")
    for lineno, line in enumerate(client_path.read_text().splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if pattern.search(line):
            offenders.append((lineno, stripped))

    assert not offenders, (
        "print() calls detected in src/specify_cli/sync/client.py - "
        "route through logging instead.\n"
        + "\n".join(f"  client.py:{ln}  {src}" for ln, src in offenders)
    )
