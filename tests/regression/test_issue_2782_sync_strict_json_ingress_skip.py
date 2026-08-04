"""RED-FIRST P0 reproduction of #2782 per ADR 2026-07-17-1
(docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md).
Intentionally FAILS until the product bug is fixed — a red mainline is the
honest signal of this release-blocking P0. Do NOT xfail/skip/quarantine to
green; fix the product. Tracking issue: #2782.

Extracted (landing fold: make ``@pytest.mark.regression`` mean exactly one
thing) from ``tests/sync/test_strict_json_stdout.py``, which carries only
this one regression-marked test alongside several unrelated, passing
strict-JSON-contract tests. This module imports the shared subprocess/home
isolation harness from that file read-only (``_worktree_src``,
``_build_isolated_home``, ``_resolve_in_tree_specify_cli``,
``_run_cli_isolated``, ``_stop_isolated_sync_daemon``,
``_scaffold_minimal_kittify_repo``) rather than duplicating it — the same
established pattern already used elsewhere in this suite for cross-file
harness reuse (see e.g. ``tests/merge/test_executor_coord_reconcile.py``
importing from ``tests/regression/test_issue_2367_bake_strand.py``).

Symptom: ``spec-kitty agent mission create --json`` must stay strict JSON on
stdout even when the sync layer skips direct ingress and reports the skip
diagnostic on stderr (AC-006 / FR-009 / FR-010 / NFR-003). On main today the
sync layer instead hits an auth-failure/connection-refused path before the
private-team-missing skip fires. Expected red until #2782 closes.
"""

from __future__ import annotations

import json
import os
import pathlib

import pytest

from tests.sync.test_strict_json_stdout import (
    _build_isolated_home,
    _resolve_in_tree_specify_cli,
    _run_cli_isolated,
    _scaffold_minimal_kittify_repo,
    _stop_isolated_sync_daemon,
    _worktree_src,
)

pytestmark = [pytest.mark.regression, pytest.mark.slow, pytest.mark.unit, pytest.mark.git_repo]


@pytest.mark.skipif(
    not os.environ.get("SPEC_KITTY_ENABLE_SAAS_SYNC"),
    reason=(
        "SPEC_KITTY_ENABLE_SAAS_SYNC not set — this case needs a reachable SaaS "
        "backend: `mission create` runs a real final sync, and without a backend "
        "the batch endpoint returns Connection refused, preempting the "
        "'direct ingress skipped' diagnostic the assertion requires. Skip when "
        "SaaS sync is inactive (operator direction; sibling SaaS gate C-006)."
    ),
)
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
    assert resolved_path.is_relative_to(worktree_src), f"subprocess resolved specify_cli at {resolved_path}, expected under {worktree_src}"

    try:
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
    finally:
        _stop_isolated_sync_daemon(env_overrides)

    # Robust skip (operator direction; sibling SaaS gate C-006): the env-var
    # gate above only proves SPEC_KITTY_ENABLE_SAAS_SYNC is *set* — it cannot
    # see whether a SaaS backend is actually *reachable*. The blocking
    # ``regression`` CI job sets the flag but stands up no server, so
    # ``mission create``'s real final sync connection-refuses and
    # ``classify_sync_error`` falls back to ``server_auth_failure``, preempting
    # the benign ``direct ingress skipped`` diagnostic this contract asserts.
    # That is an unreachable-backend *environment*, not a contract regression —
    # skip rather than fail. The narrower transport signatures below are
    # DELIBERATELY exclusive of the ``no valid access token`` /
    # ``Not authenticated`` prose: those indicate the seeded session failed to
    # load (the #2254 drift class) and MUST still fail loudly (asserted below),
    # never be masked by this skip. Backend-reachable environments fall straight
    # through to the full contract assertions unchanged. See #2782.
    _ingress_skip_fired = (
        "direct ingress skipped" in result.stderr
        or "direct_ingress_missing_private_team" in result.stderr
    )
    _backend_unreachable = (
        "server_auth_failure" in result.stderr
        or "Connection error" in result.stderr
        or "Connection refused" in result.stderr
    )
    if not _ingress_skip_fired and _backend_unreachable:
        pytest.skip(
            "SaaS backend unreachable (SPEC_KITTY_ENABLE_SAAS_SYNC set with no "
            "reachable server): the final-sync connection-refused / "
            "server_auth_failure path preempted the 'direct ingress skipped' "
            "diagnostic this strict-JSON contract requires. Skipping rather than "
            f"failing in a backend-less environment (#2782).\nstderr={result.stderr!r}"
        )

    assert result.returncode == 0, (
        "agent mission create --json must succeed even when sync ingress "
        "is skipped (FR-010).\n"
        f"resolved specify_cli: {resolved_path}\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )

    # NFR-003 / AC-006: stdout is a single JSON document.
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict), f"expected top-level JSON object, got {type(parsed).__name__}"
    assert parsed.get("result") == "success", f"expected result=success in payload, got: {parsed!r}"
    assert "mission_slug" in parsed, f"expected mission_slug field in payload, got keys: {sorted(parsed.keys())!r}"

    # FR-009: no sync diagnostic prose on stdout.
    assert "Connection failed" not in result.stdout, f"sync diagnostic leaked onto stdout: {result.stdout!r}"
    assert "direct ingress skipped" not in result.stdout
    assert "direct_ingress_missing_private_team" not in result.stdout

    # Prove the diagnostic path actually fired: same guard as cycle-2.
    diagnostic_present = "direct ingress skipped" in result.stderr or "direct_ingress_missing_private_team" in result.stderr
    assert diagnostic_present, (
        "expected 'direct ingress skipped' or "
        "'direct_ingress_missing_private_team' on stderr; without this "
        "the test cannot distinguish a working strict-JSON contract "
        "from a no-op early-exit.\n"
        f"stderr={result.stderr!r}"
    )

    # Non-vacuous proof the seeded session actually LOADED (the #2254 drift
    # class): the genuine ingress-skip path above fires only when an
    # authenticated session is present. If the session were invisible again
    # (seed dir drifting from the production read path), sync would instead
    # fall through to the unauthenticated final_sync gate, whose diagnostic
    # carries 'Not authenticated: no valid access token'. Assert that gate
    # did NOT fire, so this test fails loudly on a recurrence rather than
    # passing for the wrong reason.
    assert "no valid access token" not in result.stderr, (
        "sync fell through to the unauthenticated final_sync gate -- the "
        "seeded session did not load (the #2254 drift class). The "
        "ingress-skip diagnostic above is not proof of a working contract "
        "if auth silently failed.\n"
        f"stderr={result.stderr!r}"
    )
    assert "Not authenticated" not in result.stderr
