"""Permanent guard: mission create commits meta.json after origin-binding on
the pending-origin (ticket-first) flow (squad follow-on to #2693/#2739).

DEFECT (fixed)
--------------
``_consume_pending_origin_if_present`` (step 9 of ``create_mission_core``) runs
AFTER the step-8.5 transactional scaffold commit (#2693) already landed
``meta.json``. On the ticket-first flow, a successful origin bind
(``bind_mission_origin`` -> ``set_origin_ticket`` -> ``write_meta``) then
writes the ``origin_ticket`` subtree straight to ``meta.json`` on disk — a
plain file write, not a commit. The mission-creation entry point still
reports success (``origin_binding_succeeded: True``, ``--json`` claims the
mission was created cleanly) while ``meta.json`` sits modified-uncommitted in
the working tree (``git status --porcelain`` shows ``M meta.json``).

FIX
---
After step 9, when ``origin_binding_succeeded`` is ``True``, ``meta.json`` is
re-committed through the SAME sanctioned commit surface used at step 8.5
(``_commit_feature_file``, targeting the create-time placement seam), so the
tree is clean the moment origin binding succeeds.

INVARIANT
---------
After ``create_mission_core`` returns with ``origin_binding_succeeded is
True``, ``meta.json`` carries NO uncommitted change (staged, unstaged, or
untracked) — the ticket-first flow's origin-bound metadata write is exactly
as transactionally complete as the ticket-less flow's scaffold commit.
(``spec.md`` remains intentionally uncommitted per #846 and is out of scope
for this guard.)

Drives the real production entry point ``create_mission_core`` over a real git
repository with the real ``consume_pending_origin_impl`` consumer registered;
only the outer SaaS call inside ``bind_mission_origin`` is replaced (no
network / consent-gate dependency) with a fake that performs the SAME local
write (``set_origin_ticket``) the real implementation performs after its SaaS
call succeeds — so the reproduced symptom is the real symptom, not a stand-in.

NOTE: mission-create trips the "inside a worktree" guard when the test
process itself runs from a git worktree checkout (the CI lane checks the
suite out into a per-SHA ``git worktree add --detach`` tree). Both calls
below therefore pass ``allow_worktree_context=True`` — the bypass reserved
for programmatic test callers (``tests/_factories`` defaults it on for the
same reason; ``tests/architectural/test_no_production_worktree_guard_bypass.py``
keeps it out of ``src/``). The guard under test here is the step-9.5
post-bind meta.json commit, not the step-2 process-cwd worktree guard.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from mission_runtime import MissionTopology
from specify_cli.core.adapters import (
    register_pending_origin_consumer,
    reset_origin_consumer,
)
from specify_cli.core.mission_creation import create_mission_core
from specify_cli.tracker.origin_consumer import consume_pending_origin_impl

from tests._factories import provision_test_charter

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# A non-protected feature branch — ``safe_commit`` refuses to write to a
# protected branch (``main``); mirrors the sibling #2693 guard.
_FEATURE_BRANCH = "feat/pending-origin-guard"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _init_git_repo(repo: Path) -> None:
    """A clean checkout with a provisioned charter, on a feature branch, with
    the baseline committed — mirrors ``test_issue_2693``'s harness."""
    (repo / ".kittify").mkdir(exist_ok=True)
    provision_test_charter(repo)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    (repo / "kitty-specs" / ".gitkeep").touch()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "baseline")
    _git(repo, "branch", "-M", "main")
    _git(repo, "checkout", "-b", _FEATURE_BRANCH)


def _mission_summary(slug: str) -> dict[str, str]:
    title = slug.replace("-", " ").strip() or "test mission"
    return {
        "friendly_name": title.title(),
        "purpose_tldr": f"Deliver {title} cleanly for the team.",
        "purpose_context": (f"This mission delivers {title} so product and engineering can move forward with a clear outcome and shared understanding."),
    }


def _write_pending_origin(repo_root: Path) -> Path:
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    pending = kittify / "pending-origin.yaml"
    pending.write_text(
        "\n".join(
            [
                "provider: linear",
                "issue_key: ENG-77",
                "issue_id: issue-987",
                "title: Land the pending-origin commit guard",
                "url: https://linear.app/acme/ENG-77",
                "status: In Progress",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return pending


def _fake_bind_mission_origin(
    *,
    feature_dir: Path,
    candidate: Any,
    provider: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    client: Any = None,
) -> tuple[dict[str, Any], bool]:
    """Stand-in for ``tracker.origin.bind_mission_origin`` that skips the SaaS
    call (steps 1-3 of the real function) but performs the SAME local write
    (step 5, ``set_origin_ticket``) the real implementation performs after its
    SaaS call succeeds. This reproduces the real symptom under test — a
    disk-only meta.json write with no accompanying commit — without a network
    dependency.
    """
    from specify_cli.mission_metadata import set_origin_ticket

    origin_ticket = {
        "provider": provider,
        "resource_type": resource_type or "linear_team",
        "resource_id": resource_id or "team-pending-origin-guard",
        "external_issue_id": candidate.external_issue_id,
        "external_issue_key": candidate.external_issue_key,
        "external_issue_url": candidate.url,
        "title": candidate.title,
    }
    updated_meta = set_origin_ticket(feature_dir, origin_ticket)
    return updated_meta, False


def test_pending_origin_bind_leaves_clean_tree_after_create(tmp_path: Path) -> None:
    """(squad) mission create's ticket-first flow leaves NO uncommitted changes
    once origin binding succeeds — meta.json's post-bind write is committed,
    not just landed on disk.
    """
    _init_git_repo(tmp_path)
    _write_pending_origin(tmp_path)

    register_pending_origin_consumer(consume_pending_origin_impl)
    try:
        with patch(
            "specify_cli.tracker.origin.bind_mission_origin",
            side_effect=_fake_bind_mission_origin,
        ):
            result = create_mission_core(
                tmp_path,
                "pending-origin-guard",
                topology=MissionTopology.SINGLE_BRANCH,
                allow_worktree_context=True,
                **_mission_summary("pending-origin-guard"),
            )
    finally:
        reset_origin_consumer()

    # Precondition: the bug can only manifest if binding actually ran and
    # actually wrote the origin ticket into meta.json.
    assert result.origin_binding_attempted is True
    assert result.origin_binding_succeeded is True
    assert result.origin_binding_error is None
    meta_file = result.feature_dir / "meta.json"
    assert meta_file.exists()
    assert "origin_ticket" in meta_file.read_text(encoding="utf-8")

    # The core assertion: meta.json itself carries NO uncommitted change —
    # neither staged-modified nor unstaged-modified nor untracked. ``spec.md``
    # is intentionally left uncommitted (#846, disclosed in ``created_files``)
    # and other ambient untracked files (e.g. ``.kittify/sync-state.json``)
    # are unrelated to this guard, so the assertion targets meta.json's own
    # status line specifically rather than requiring a fully empty tree.
    status_lines = _git(tmp_path, "status", "--porcelain").stdout.splitlines()
    meta_rel = str(meta_file.relative_to(tmp_path))
    meta_status_lines = [line for line in status_lines if line[3:].strip() == meta_rel]
    assert not meta_status_lines, (
        "mission create reported a successful origin bind but left meta.json "
        f"uncommitted (squad #2739 follow-on): {meta_status_lines!r}. Full "
        f"git status --porcelain:\n{status_lines!r}"
    )

    # The committed meta.json on HEAD (not just the working copy) carries the
    # origin ticket — proving the SECOND commit actually landed the bind, not
    # merely that nothing changed after step 8.5.
    committed_meta = _git(tmp_path, "show", f"HEAD:{meta_file.relative_to(tmp_path)}").stdout
    assert "origin_ticket" in committed_meta, (
        "HEAD's committed meta.json does not carry the origin_ticket subtree — the post-bind commit did not land the write it was meant to capture."
    )


def test_pending_origin_bind_failure_does_not_trigger_extra_commit(
    tmp_path: Path,
) -> None:
    """(squad) when origin binding FAILS, no extra commit is attempted — the
    step-8.5 scaffold commit's tree stays exactly as it landed (sibling
    guard to the success-path test above; proves the fix is gated on
    ``origin_binding_succeeded``, not unconditional).
    """
    _init_git_repo(tmp_path)
    _write_pending_origin(tmp_path)

    register_pending_origin_consumer(consume_pending_origin_impl)
    try:
        with patch(
            "specify_cli.tracker.origin.bind_mission_origin",
            side_effect=RuntimeError("saas bind rejected"),
        ):
            result = create_mission_core(
                tmp_path,
                "pending-origin-guard-fail",
                topology=MissionTopology.SINGLE_BRANCH,
                allow_worktree_context=True,
                **_mission_summary("pending-origin-guard-fail"),
            )
    finally:
        reset_origin_consumer()

    assert result.origin_binding_attempted is True
    assert result.origin_binding_succeeded is False
    assert result.origin_binding_error is not None

    # The step-8.5 scaffold commit still landed cleanly; a failed bind must
    # not leave meta.json dirty either (it was never rewritten on disk since
    # the fake bind raised before any write) — the extra commit must not even
    # be attempted (it is gated on ``origin_binding_succeeded``). The staged
    # ``pending-origin.yaml`` is intentionally RETAINED on a failed bind (so
    # the operator can retry) and stays untracked — that is expected, not the
    # defect this guard targets.
    meta_file = result.feature_dir / "meta.json"
    status_lines = _git(tmp_path, "status", "--porcelain").stdout.splitlines()
    meta_rel = str(meta_file.relative_to(tmp_path))
    meta_status_lines = [line for line in status_lines if line[3:].strip() == meta_rel]
    assert not meta_status_lines, f"a failed origin bind left meta.json uncommitted: {meta_status_lines!r}. Full git status --porcelain:\n{status_lines!r}"
