"""Z6-C: canonical repository identity, against real git repositories.

Program-graph handle Z6-C ("Canonical repository identity in Spec Kitty"):
"Canonicalize repository identity across session-container directories;
ambiguous multi-checkout containers, symlinks, missing origin/quarantine
metadata, and conflicting roots fail rather than mint/guess identity."

Deliberately not mocked, mirroring zeitgeist's own
``tests/test_repo_identity.py``: the thing under test *is* the interaction
with git and the filesystem, so a mock would encode the very assumption
being verified. Several tests below assert a DIVERGENCE from that upstream
suite on purpose — see ``repo_identity.py``'s module docstring for why.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from specify_cli.zeitgeist_client import budget, repo_identity, transport

# Real `git init`/`clone`/`worktree` subprocesses throughout this file.
pytestmark = [pytest.mark.git_repo]


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture()
def origin(tmp_path: Path) -> Path:
    """A bare repo standing in for a hosted ``acme-widgets`` remote."""
    bare = tmp_path / "acme-widgets.git"
    bare.mkdir()
    _git("init", "--bare", "-q", cwd=bare)
    return bare


def _clone(origin: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _git("clone", "-q", str(origin), str(dest), cwd=dest.parent)
    _git("config", "user.email", "t@example.com", cwd=dest)
    _git("config", "user.name", "t", cwd=dest)
    (dest / "f.txt").write_text("x")
    _git("add", "f.txt", cwd=dest)
    _git("commit", "-qm", "init", cwd=dest)
    return dest


# --- repo_name(): origin is the only authority, same as upstream ----------


def test_renamed_clone_reports_repository_not_directory(tmp_path, origin):
    clone = _clone(origin, tmp_path / "work" / "some-other-dirname")
    assert repo_identity.repo_name(str(clone)) == "acme-widgets"


def test_worktree_reports_repository_not_worktree(tmp_path, origin):
    clone = _clone(origin, tmp_path / "work" / "acme-widgets")
    wt = tmp_path / "work" / "acme-widgets" / ".worktrees" / "lane-a"
    _git("worktree", "add", "-q", "-b", "lane", str(wt), cwd=clone)
    assert repo_identity.repo_name(str(wt)) == "acme-widgets"


def test_two_worktrees_of_one_clone_agree(tmp_path, origin):
    clone = _clone(origin, tmp_path / "work" / "acme-widgets")
    a = tmp_path / "work" / "acme-widgets" / ".worktrees" / "lane-a"
    b = tmp_path / "work" / "acme-widgets" / ".worktrees" / "lane-b"
    _git("worktree", "add", "-q", "-b", "la", str(a), cwd=clone)
    _git("worktree", "add", "-q", "-b", "lb", str(b), cwd=clone)
    assert repo_identity.repo_name(str(a)) == repo_identity.repo_name(str(b)) == "acme-widgets"


def test_origin_is_authoritative_even_for_a_fork(tmp_path):
    local = tmp_path / "x"
    local.mkdir()
    _git("init", "-q", cwd=local)
    _git("remote", "add", "origin", "git@github.com:me/my-fork.git", cwd=local)
    _git("remote", "add", "upstream", "git@github.com:org/canonical.git", cwd=local)
    assert repo_identity.repo_name(str(local)) == "my-fork"


# --- divergence from zeitgeist/integrations/repo_identity.py: fail closed --


def test_repo_without_origin_and_without_quarantine_raises_unverified(tmp_path):
    """Upstream's equivalent (``test_repo_without_remote_still_reports_something``)
    asserts ``repo_name(local) == "scratch"`` — the cwd basename. This module
    exists specifically to refuse that: a directory name is not provenance."""
    local = tmp_path / "scratch"
    local.mkdir()
    _git("init", "-q", cwd=local)
    with pytest.raises(repo_identity.UnverifiedRepositoryIdentity):
        repo_identity.repo_name(str(local))


def test_not_a_git_repo_raises_unverified(tmp_path):
    """Upstream falls back to the cwd basename here too
    (``test_not_a_git_repo_falls_back_to_basename``); this module has nothing
    to derive an identity from and must refuse rather than guess."""
    plain = tmp_path / "just-a-folder"
    plain.mkdir()
    with pytest.raises(repo_identity.UnverifiedRepositoryIdentity):
        repo_identity.repo_name(str(plain))


def test_repo_without_origin_but_with_quarantine_metadata_resolves(tmp_path):
    """``[kitty "quarantine"] origin = ...`` records a prior `origin` for a
    repo whose live remote was deliberately removed (this program's own
    HIC-BOOT-003 remote-quarantine contract is the motivating case) — a
    frozen fact a trusted process wrote, not a guess."""
    local = tmp_path / "scratch"
    local.mkdir()
    _git("init", "-q", cwd=local)
    config_path = local / ".git" / "config"
    with config_path.open("a") as f:
        f.write('\n[kitty "quarantine"]\n\torigin = https://example.invalid/org/acme-widgets.git\n')
    assert repo_identity.repo_name(str(local)) == "acme-widgets"


def test_live_origin_wins_over_stale_quarantine_metadata(tmp_path, origin):
    """A live `origin` remote is always authoritative over a quarantine
    record — quarantine metadata is a fallback for when `origin` is gone,
    never a stronger claim than the remote actually configured."""
    clone = _clone(origin, tmp_path / "work" / "clone")
    config_path = clone / ".git" / "config"
    with config_path.open("a") as f:
        f.write('\n[kitty "quarantine"]\n\torigin = https://example.invalid/org/stale-name.git\n')
    assert repo_identity.repo_name(str(clone)) == "acme-widgets"


# --- ambiguous multi-checkout containers -----------------------------------


def test_container_directory_with_two_child_checkouts_raises_ambiguous(tmp_path, origin):
    """A directory that is not itself a checkout but directly holds more than
    one ('session-container directories', Z6-C's own wording) — the caller's
    intended repository cannot be inferred, so this must refuse rather than
    pick one arbitrarily."""
    container = tmp_path / "sandboxes"
    container.mkdir()
    _clone(origin, container / "lane-a")
    _clone(origin, container / "lane-b")
    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(container))


def test_container_directory_with_one_child_checkout_is_unverified_not_ambiguous(tmp_path, origin):
    """A single child checkout is not an ambiguity — but querying the
    container itself (not the checkout) still has no `origin` of its own, so
    it fails as unverified rather than silently reaching into the child."""
    container = tmp_path / "sandboxes"
    container.mkdir()
    _clone(origin, container / "lane-a")
    with pytest.raises(repo_identity.UnverifiedRepositoryIdentity):
        repo_identity.repo_name(str(container))


# --- symlinks / conflicting roots ------------------------------------------


@pytest.mark.requires_symlinks
def test_symlink_into_a_different_checkout_raises_conflicting_roots(tmp_path, origin):
    repo_a = _clone(origin, tmp_path / "repo-a")

    other_origin = tmp_path / "other.git"
    other_origin.mkdir()
    _git("init", "--bare", "-q", cwd=other_origin)
    repo_b = _clone(other_origin, tmp_path / "repo-b")
    (repo_b / "sub").mkdir()

    link = repo_a / "link-into-b"
    link.symlink_to(repo_b / "sub")

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(link))


@pytest.mark.requires_symlinks
def test_symlink_within_the_same_checkout_does_not_raise(tmp_path, origin):
    clone = _clone(origin, tmp_path / "clone")
    real_dir = clone / "real"
    real_dir.mkdir()
    link = clone / "link"
    link.symlink_to(real_dir)
    assert repo_identity.repo_name(str(link)) == "acme-widgets"


# --- identity(): repo + branch + commit, one call --------------------------


def test_identity_returns_repo_branch_and_commit(tmp_path, origin):
    clone = _clone(origin, tmp_path / "clone")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=clone, check=True, capture_output=True, text=True
    ).stdout.strip()

    result = repo_identity.identity(str(clone))

    assert result.repo == "acme-widgets"
    assert result.branch  # non-empty — a real checked-out branch
    assert result.commit == head


def test_identity_propagates_ambiguous_repository_identity(tmp_path, origin):
    container = tmp_path / "sandboxes"
    container.mkdir()
    _clone(origin, container / "lane-a")
    _clone(origin, container / "lane-b")
    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.identity(str(container))


def test_identity_propagates_unverified_repository_identity(tmp_path):
    plain = tmp_path / "just-a-folder"
    plain.mkdir()
    with pytest.raises(repo_identity.UnverifiedRepositoryIdentity):
        repo_identity.identity(str(plain))


# --- NFR-001-style aggregate deadline, ported discipline -------------------


@pytest.fixture()
def wedged_clone(tmp_path, monkeypatch, origin):
    """A real clone, built with the real `git`, then `git` wedged on PATH.

    Mirrors zeitgeist's own `wedge_git` fixture: the repository must exist
    before PATH is replaced with a binary that never returns.
    """
    clone = _clone(origin, tmp_path / "work" / "clone")
    shim = tmp_path / "wedge-bin"
    shim.mkdir()
    fake = shim / "git"
    fake.write_text("#!/bin/sh\nexec /bin/sleep 600\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(shim))
    return clone


def test_filesystem_fallback_finds_origin_with_git_wedged(wedged_clone):
    assert repo_identity.repo_name(str(wedged_clone)) == "acme-widgets"


def test_aggregate_deadline_shared_across_repo_branch_and_commit(wedged_clone):
    """The one wedged live-git probe (`remote get-url origin`) spends the
    whole budget; branch/commit lookups must not each get a fresh one."""
    start = time.monotonic()
    result = repo_identity.identity(str(wedged_clone))
    elapsed = time.monotonic() - start

    assert elapsed < repo_identity.GIT_BUDGET_S + 1.0, (
        f"repo+branch+commit took {elapsed:.2f}s against a "
        f"{repo_identity.GIT_BUDGET_S}s aggregate budget"
    )
    assert elapsed >= repo_identity.GIT_BUDGET_S * 0.5, (
        f"only {elapsed:.2f}s elapsed — git was never actually invoked"
    )
    # Degraded (branch/commit empty — no budget left to ask), never wrong.
    assert result.repo == "acme-widgets"
    assert result.branch == ""
    assert result.commit == ""


@pytest.fixture()
def stalled_non_repo(tmp_path, monkeypatch):
    shim = tmp_path / "bin"
    shim.mkdir()
    fake = shim / "git"
    fake.write_text("#!/bin/sh\nexec /bin/sleep 600\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(shim))
    work = tmp_path / "work"
    work.mkdir()
    return str(work)


def test_not_a_git_repo_raises_even_with_git_wedged(stalled_non_repo):
    """Upstream's matching fixture asserts `repo_name(stalled_git) ==
    "work"` — exactly the spoofable directory-basename guess this module
    exists to refuse."""
    with pytest.raises(repo_identity.UnverifiedRepositoryIdentity):
        repo_identity.repo_name(stalled_non_repo)


def test_an_exhausted_deadline_skips_further_probes(tmp_path, monkeypatch):
    shim = tmp_path / "bin"
    shim.mkdir()
    fake = shim / "git"
    fake.write_text("#!/bin/sh\nexec /bin/sleep 600\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(shim))
    work = tmp_path / "work"
    work.mkdir()

    deadline = repo_identity.Deadline(0.4)
    start = time.monotonic()
    for _ in range(20):
        deadline.run(["rev-parse", "HEAD"], str(work))
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, (
        f"20 probes on a spent 0.4s budget took {elapsed:.2f}s — exhausted "
        f"probes are still spawning git"
    )
    assert deadline.expired()


def test_a_healthy_repo_is_not_slowed_by_the_deadline(tmp_path, origin):
    clone = _clone(origin, tmp_path / "clone")
    start = time.monotonic()
    repo_identity.identity(str(clone))
    elapsed = time.monotonic() - start
    assert elapsed < 1.0


# --- budget nesting: git identity + one offer fit inside one hook kill -----


def test_git_budget_nests_inside_the_hook_budget_with_the_offer_budget():
    assert (
        repo_identity.GIT_BUDGET_S + budget.OFFER_BUDGET_S < budget.HOOK_BUDGET_S
    ), "GIT_BUDGET_S + OFFER_BUDGET_S must still land inside HOOK_BUDGET_S with margin"


# --- ClientConfig.for_repository(): binding presence to canonical identity -


def test_for_repository_derives_repo_and_branch_from_git_truth_not_a_claim(tmp_path, origin):
    clone = _clone(origin, tmp_path / "work" / "renamed-checkout")
    _git("checkout", "-q", "-b", "feature/x", cwd=clone)

    config = transport.ClientConfig.for_repository(
        str(clone),
        relay_url="http://127.0.0.1:9",
        token="tok",
        harness="claude-code",
        session_id="sess-1",
    )

    assert config.repo == "acme-widgets"  # not "renamed-checkout" — no claim, no basename
    assert config.branch == "feature/x"
    assert config.relay_url == "http://127.0.0.1:9"
    assert config.token == "tok"
    assert config.harness == "claude-code"
    assert config.session_id == "sess-1"
    assert config.agent_id is None


def test_for_repository_raises_instead_of_constructing_an_unverified_client_config(tmp_path):
    plain = tmp_path / "just-a-folder"
    plain.mkdir()
    with pytest.raises(repo_identity.UnverifiedRepositoryIdentity):
        transport.ClientConfig.for_repository(
            str(plain),
            relay_url="http://127.0.0.1:9",
            token="tok",
            harness="claude-code",
            session_id="sess-1",
        )


def test_for_repository_raises_for_an_ambiguous_session_container(tmp_path, origin):
    container = tmp_path / "sandboxes"
    container.mkdir()
    _clone(origin, container / "lane-a")
    _clone(origin, container / "lane-b")
    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        transport.ClientConfig.for_repository(
            str(container),
            relay_url="http://127.0.0.1:9",
            token="tok",
            harness="claude-code",
            session_id="sess-1",
        )


def test_bare_client_config_construction_is_unaffected_a_free_form_claim(tmp_path):
    """Z1.md decision 7 ("caller fields are claims only") still governs the
    plain dataclass constructor — `for_repository` is an additive, stricter
    alternative, not a replacement."""
    config = transport.ClientConfig(
        relay_url="http://127.0.0.1:9",
        token="tok",
        harness="claude-code",
        session_id="sess-1",
        agent_id=None,
        repo="anything-i-claim",
        branch="anything",
    )
    assert config.repo == "anything-i-claim"
