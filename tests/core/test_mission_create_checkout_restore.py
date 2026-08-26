"""FR-011 (#3339): a failed mission-create must be atomic for git side-effects.

WP12 — mission-create checkout restore. A ``create_mission_core`` that fails
*after* minting the coordination branch must:

  (a) leave the operator on their ORIGINAL branch/checkout, and
  (b) delete the orphan coordination branch it minted.

These tests drive a real git repository (``git init`` + subprocess), so they
carry the ``git_repo`` marker.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.core.git_ops import get_current_branch
from specify_cli.core.mission_creation import (
    _restore_git_state_after_failed_create,
    create_mission_core,
)

from tests._factories import provision_test_charter

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_ORIGINAL_BRANCH = "operator-work"
_COORDINATION_GLOB = "kitty/mission-*"


def _init_git_repo(repo: Path) -> None:
    (repo / ".kittify").mkdir(exist_ok=True)
    # WP04 fail-closed: create_mission_core requires a provisioned charter.
    provision_test_charter(repo)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty"], cwd=repo, capture_output=True, check=True
    )
    # Deterministic, operator-named branch so the assertion is decoupled from
    # the ambient git ``init.defaultBranch`` (master vs main).
    subprocess.run(
        ["git", "branch", "-M", _ORIGINAL_BRANCH], cwd=repo, capture_output=True, check=True
    )


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").strip() or "test mission"
    return {
        "friendly_name": title.title(),
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (
            f"This mission delivers {title} so product and engineering can move "
            "forward with a clear outcome and shared understanding."
        ),
    }


def _coordination_branches(repo: Path) -> list[str]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "branch",
            "--list",
            _COORDINATION_GLOB,
            "--format=%(refname:short)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_failed_create_restores_branch_and_leaves_no_orphan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2 / FR-011: a create that fails AFTER the coordination branch is minted
    restores the operator's original branch and leaves no orphan branch."""
    _init_git_repo(tmp_path)
    assert get_current_branch(tmp_path) == _ORIGINAL_BRANCH
    assert _coordination_branches(tmp_path) == []

    # Inject a failure that fires AFTER the coordination branch is minted:
    # ``write_meta`` runs immediately after the mint + topology corroboration.
    boom = RuntimeError("injected failure after branch mint")

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise boom

    monkeypatch.setattr("specify_cli.mission_metadata.write_meta", _explode)

    with pytest.raises(RuntimeError, match="injected failure after branch mint"):
        create_mission_core(
            tmp_path,
            "atomicity-check",
            allow_worktree_context=True,
            **_mission_summary("atomicity-check"),
        )

    # (a) operator is back on their original branch.
    assert get_current_branch(tmp_path) == _ORIGINAL_BRANCH
    # (b) no orphan coordination branch remains.
    assert _coordination_branches(tmp_path) == []


def test_restore_helper_switches_back_and_deletes_new_branches(tmp_path: Path) -> None:
    """Focused coverage: the rollback helper restores the checkout and deletes
    the coordination branch that appeared during the aborted create."""
    _init_git_repo(tmp_path)
    pre = frozenset(_coordination_branches(tmp_path))  # empty
    orphan = "kitty/mission-simulated-abcd1234"
    subprocess.run(
        ["git", "-C", str(tmp_path), "branch", orphan], capture_output=True, text=True, check=True
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "checkout", orphan], capture_output=True, text=True, check=True
    )
    assert get_current_branch(tmp_path) == orphan

    _restore_git_state_after_failed_create(
        tmp_path,
        original_branch=_ORIGINAL_BRANCH,
        pre_existing_coordination_branches=pre,
    )

    assert get_current_branch(tmp_path) == _ORIGINAL_BRANCH
    assert _coordination_branches(tmp_path) == []


def test_meta_json_commit_hard_failure_raises_and_restores_git_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-001 / NFR-003 (primary mission-type call site, mission_creation.py:767).

    A hard git failure while committing ``meta.json`` must propagate out of
    ``create_mission_core`` (not be swallowed by the ``contextlib.suppress
    (Exception)`` that previously wrapped the ``_commit_feature_file`` call),
    surfacing the underlying git error text (Acceptance Scenario 1/2) --  and
    the existing rollback (``_restore_git_state_after_failed_create``) must
    leave the checkout's branch, HEAD commit, and index tree indistinguishable
    from before ``create_mission_core`` was invoked (NFR-003).

    The mock raises the RAW underlying error exactly as production's
    ``safe_commit`` would (no "meta.json commit failed" prefix baked in --
    that prefix is production's own contribution via the ``try/except``
    wrapper around each ``_commit_feature_file`` call site). This proves the
    step-naming context comes from production code, not from the mock.

    Revert sensitivity: reverting the fix (re-wrapping the
    ``_commit_feature_file`` call in ``contextlib.suppress(Exception)``)
    swallows ``boom`` silently, ``create_mission_core`` returns normally, and
    ``pytest.raises`` below fails with "DID NOT RAISE".
    """
    _init_git_repo(tmp_path)
    assert get_current_branch(tmp_path) == _ORIGINAL_BRANCH

    original_tip = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    original_index_tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Simulates a hard git failure (e.g. a pre-commit hook that always
    # rejects) surfacing from inside the meta.json commit call -- the RAW
    # ``safe_commit``-shaped error, with no step-name prefix (production adds
    # that itself; see the docstring above).
    boom = RuntimeError(
        f"safe_commit: git commit failed in {tmp_path} for destination_ref='main': pre-commit hook rejected (exit 1)"
    )

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise boom

    monkeypatch.setattr("specify_cli.core.mission_creation._commit_feature_file", _explode)

    with pytest.raises(RuntimeError, match="pre-commit hook rejected") as exc_info:
        create_mission_core(
            tmp_path,
            "meta-commit-hard-failure",
            allow_worktree_context=True,
            **_mission_summary("meta-commit-hard-failure"),
        )

    # NFR-001: the step name is added by production's try/except wrapper
    # around the ``_commit_feature_file`` call -- not present in the mock's
    # raw raise -- so this proves production, not the mock, names the step.
    assert "meta.json commit failed" in str(exc_info.value)

    # NFR-003: branch, HEAD commit, and index tree are unchanged -- no
    # partial mutation survives the raise.
    assert get_current_branch(tmp_path) == _ORIGINAL_BRANCH
    restored_tip = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    restored_index_tree = subprocess.run(
        ["git", "-C", str(tmp_path), "write-tree"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert restored_tip == original_tip
    assert restored_index_tree == original_index_tree
    assert _coordination_branches(tmp_path) == []


def test_restore_helper_preserves_pre_existing_coordination_branches(tmp_path: Path) -> None:
    """The rollback deletes only NEW coordination branches, never one that was
    already present before the aborted create (no collateral deletion)."""
    _init_git_repo(tmp_path)
    keep = "kitty/mission-keep-me-00000000"
    subprocess.run(
        ["git", "-C", str(tmp_path), "branch", keep], capture_output=True, text=True, check=True
    )
    pre = frozenset(_coordination_branches(tmp_path))  # {keep}
    new = "kitty/mission-new-11111111"
    subprocess.run(
        ["git", "-C", str(tmp_path), "branch", new], capture_output=True, text=True, check=True
    )

    _restore_git_state_after_failed_create(
        tmp_path,
        original_branch=_ORIGINAL_BRANCH,  # already on it
        pre_existing_coordination_branches=pre,
    )

    remaining = _coordination_branches(tmp_path)
    assert keep in remaining
    assert new not in remaining


def test_meta_json_commit_hard_failure_message_names_step_and_git_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-001 / Acceptance Scenario 2: the raised exception's message names
    the failing step ("meta.json commit") AND surfaces the underlying git
    error text, so a calling agent can distinguish this failure from any
    other ``specify`` failure without parsing prose -- in both the
    human-readable exit path (asserted here) and the ``--json`` path.

    The mock raises the RAW underlying error exactly as production's
    ``safe_commit`` would (no "meta.json commit failed" prefix baked in).
    The step-name prefix asserted below must therefore come from
    production's own ``try/except`` wrapper around the
    ``_commit_feature_file`` call, not from the mock -- proving NFR-001 is
    met in production, not just in the test double.

    WP01 owns only ``mission_creation.py`` and this test file -- the
    ``--json`` envelope itself is assembled by ``_run_create_core_phase``'s
    existing generic ``except Exception as e: _emit_json({"error": str(e)})``
    funnel in ``cli/commands/agent/mission_create.py`` (verified by direct
    read, 2026-08-23; that file is NOT in WP01's owned-files list, is
    unmodified by this WP, and already forwards ``str(exc)`` verbatim into
    the JSON ``error`` field -- see also
    ``tests/specify_cli/cli/commands/agent/test_mission_create_json_remediation.py``,
    which pins that same funnel for a different exception type). Asserting
    the message content at the ``create_mission_core`` raise boundary is
    therefore equivalent, for this WP's scope, to asserting the ``--json``
    payload shape: the identical string reaches both output modes through
    that unmodified, already-existing funnel.

    Revert sensitivity: reverting the fix suppresses the raise entirely (see
    the sibling hard-failure test above), so this exception -- and its
    message -- never surfaces at all; ``pytest.raises`` below fails with
    "DID NOT RAISE".
    """
    _init_git_repo(tmp_path)
    # RAW underlying error, shaped exactly like ``safe_commit``'s own
    # RuntimeError -- no "meta.json commit failed" prefix baked in here.
    boom = RuntimeError(
        f"safe_commit: git commit failed in {tmp_path} for destination_ref='main': "
        "fatal: unable to write new index file (disk full)"
    )

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise boom

    monkeypatch.setattr("specify_cli.core.mission_creation._commit_feature_file", _explode)

    with pytest.raises(RuntimeError) as exc_info:
        create_mission_core(
            tmp_path,
            "meta-commit-json-payload",
            allow_worktree_context=True,
            **_mission_summary("meta-commit-json-payload"),
        )

    message = str(exc_info.value)
    # Names the failing step -- added by production's try/except wrapper
    # around the ``_commit_feature_file`` call, not by the mock.
    assert "meta.json commit failed" in message
    # ... and surfaces the underlying git error text, not a generic message.
    assert "unable to write new index file" in message
    # The exception chain preserves the original error for debuggability.
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert "unable to write new index file" in str(exc_info.value.__cause__)
