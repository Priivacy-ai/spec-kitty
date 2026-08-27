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

import os
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


def test_container_nested_inside_a_parent_repo_with_origin_still_raises_ambiguous(
    tmp_path, origin
):
    """Reproduces the real motivating topology named in this module's own
    docstring: a session-container (this program's own `.sandboxes/`) that
    holds multiple independent checkouts, itself sitting inside ANOTHER git
    repository that has a live `origin` (this program's own root
    control-plane repo). The upward `.git` filesystem walk from the
    container finds the PARENT repo's `.git` first — that must never let
    the parent's identity be minted in place of refusing the real
    sibling-checkout ambiguity; the isolated-tmp_path variant of this test
    above (parent outside any repo) cannot exercise this because there is no
    ancestor `.git` for the walk to find."""
    parent = tmp_path / "root-control-plane"
    parent.mkdir()
    _git("init", "-q", cwd=parent)
    _git("remote", "add", "origin", "git@github.com:me/root-repo.git", cwd=parent)

    container = parent / "sandboxes"
    container.mkdir()
    _clone(origin, container / "lane-a")
    _clone(origin, container / "lane-b")

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(container))


def test_container_nested_inside_a_parent_repo_without_origin_raises_ambiguous_not_unverified(
    tmp_path, origin
):
    """Same nested-container topology as above, but the parent repo has no
    `origin` (this exact repository's actual topology). Before the fix this
    accidentally failed closed too — but via the WRONG error
    (`UnverifiedRepositoryIdentity`, with a misleading message claiming the
    container itself has no origin) rather than the correct
    `AmbiguousRepositoryIdentity` for a real sibling-checkout conflict. The
    accidental pass must not be topology-dependent."""
    parent = tmp_path / "root-control-plane"
    parent.mkdir()
    _git("init", "-q", cwd=parent)

    container = parent / "sandboxes"
    container.mkdir()
    _clone(origin, container / "lane-a")
    _clone(origin, container / "lane-b")

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
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


@pytest.mark.requires_symlinks
def test_symlinked_git_entry_at_cwd_raises_ambiguous_not_foreign_identity(tmp_path, origin):
    """A PLAIN, non-symlinked directory whose ONLY ``.git`` entry is itself a
    SYMLINK pointing at a different repo's real ``.git`` directory must not
    mint that foreign repo's identity — no sibling ambiguity, no env var, no
    clone involved, just a symlinked ``.git`` entry at ``cwd`` itself. Git
    never legitimately produces a directory-symlink ``.git`` entry —
    worktrees and submodules always use a plain FILE containing a
    ``gitdir:`` line, never a symlink to a directory — so a symlinked
    ``.git`` is illegitimate provenance and must fail closed rather than be
    trusted the way a real ``.git`` dir or worktree file would be."""
    victim = _clone(origin, tmp_path / "victim")
    evil = tmp_path / "evil"
    evil.mkdir()
    (evil / ".git").symlink_to(victim / ".git")

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(evil))


@pytest.mark.requires_symlinks
def test_symlinked_git_entry_at_an_ancestor_level_raises_ambiguous(tmp_path, origin):
    """Same illegitimate provenance as above, one (or more) levels up the
    upward filesystem walk: ``cwd`` itself has no ``.git`` at all, but an
    ANCESTOR directory the walk reaches does — and that ancestor's ``.git``
    is itself a symlink into a foreign checkout. The whole discovery path,
    not just the cwd level, must fail closed on a symlinked ``.git`` entry."""
    victim = _clone(origin, tmp_path / "victim")
    evil_parent = tmp_path / "evil-parent"
    evil_parent.mkdir()
    (evil_parent / ".git").symlink_to(victim / ".git")
    nested = evil_parent / "nested" / "deeper"
    nested.mkdir(parents=True)

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(nested))


@pytest.mark.requires_symlinks
def test_container_with_real_and_symlinked_checkout_raises_ambiguous_not_ancestor(
    tmp_path, origin
):
    """Reproduces the symlinked-sibling undercount: `_sibling_checkouts`
    gated on `entry.is_dir(follow_symlinks=False)`, so a SYMLINKED child
    checkout was never counted as a sibling. A session-container holding one
    real checkout and one symlinked checkout (pointing at a wholly different
    real repo elsewhere) is exactly as ambiguous as two real-directory
    checkouts — nested inside an ancestor repo with its own `origin`, the
    undercount let the container's identity resolution fall through and mint
    the ANCESTOR's identity instead of raising. A symlinked checkout must
    count toward the ambiguity just like a real one."""
    parent = tmp_path / "root-control-plane"
    parent.mkdir()
    _git("init", "-q", cwd=parent)
    _git("remote", "add", "origin", "git@github.com:me/root-repo.git", cwd=parent)

    container = parent / "sandboxes"
    container.mkdir()
    _clone(origin, container / "lane-a")

    elsewhere_origin = tmp_path / "elsewhere.git"
    elsewhere_origin.mkdir()
    _git("init", "--bare", "-q", cwd=elsewhere_origin)
    elsewhere = _clone(elsewhere_origin, tmp_path / "elsewhere-checkout")

    (container / "lane-b-symlink").symlink_to(elsewhere)

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(container))


@pytest.mark.requires_symlinks
def test_symlink_into_a_subdirectory_of_a_different_checkout_raises_ambiguous(tmp_path, origin):
    """Exotic follow-up (Z6-M2-01, deferred by HIC-M1-Z6C-GOODENOUGH beyond
    the five M1-closed classes): ``test_symlink_into_a_different_checkout_
    raises_conflicting_roots`` above only covers a symlink living INSIDE
    another real checkout (``repo_a``) — there, both the syntactic and the
    resolved walk-up independently find a ``.git`` (``repo_a``'s and
    ``repo_b``'s), so they can be compared and found to disagree. This test
    is the same identity-theft shape with the symlink's OWN container
    carrying no git identity at all: an isolated, non-checkout directory
    holds nothing but a symlink into a SUBDIRECTORY (not the root — a
    subdirectory carries no ``.git`` of its own, only its ancestor does) of
    an unrelated victim checkout. The syntactic walk-up from the isolated
    container never independently reaches the victim's ``.git`` (it only
    gets there via the OS's transparent, one-hop symlink resolution on the
    FIRST candidate check; every subsequent step walks the isolated
    container's OWN — checkout-free — ancestor chain), so it comes back
    empty rather than "a different, non-empty match". Before this fix, an
    empty `raw` short-circuited the raw/real comparison entirely
    (`if raw and real and ...`), so the resolved side's foreign identity
    went completely unchallenged — `repo_name()` minted `victim-widgets` for
    a directory with no more relationship to that project than "one of its
    subdirectories happens to be readable by symlink"."""
    victim = _clone(origin, tmp_path / "victim")
    (victim / "subdir").mkdir()

    evil = tmp_path / "isolated-evil"
    evil.mkdir()
    link = evil / "link"
    link.symlink_to(victim / "subdir")

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(link))


@pytest.mark.requires_symlinks
def test_symlink_into_a_subdirectory_of_a_different_checkout_raises_even_nested(
    tmp_path, origin
):
    """Same theft, with `cwd` several directory levels below the symlink
    jump itself — the syntactic-vs-resolved divergence must be caught
    regardless of how deep under the jump `cwd` sits, not only when `cwd`
    IS the symlink."""
    victim = _clone(origin, tmp_path / "victim")
    (victim / "subdir" / "deeper" / "still").mkdir(parents=True)

    evil = tmp_path / "isolated-evil"
    evil.mkdir()
    link = evil / "link"
    link.symlink_to(victim / "subdir")
    nested_cwd = link / "deeper" / "still"

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(nested_cwd))


@pytest.mark.requires_symlinks
def test_symlink_inside_a_checkout_to_a_non_repo_location_does_not_raise(
    tmp_path, origin, monkeypatch
):
    """Regression guard pinning the deliberate asymmetry in the fix above:
    a symlink living INSIDE a real checkout that happens to point OUTSIDE
    any git repository must NOT raise. `real` (the resolved side) governs
    what an actual `git` subprocess run at `cwd` would observe — the OS's
    own `chdir` follows symlinks exactly like `os.path.realpath` does — so
    an empty `real` here means the live probe already fails closed on its
    own, and every fallback re-derives the checkout's OWN identity (there is
    only ONE candidate: the checkout the symlink object itself lives in, not
    a foreign one) with nothing to disagree with. Raising here would be
    over-rejection of an ordinary, harmless symlink that a real checkout is
    free to contain.

    `isolated_no_git` claiming "no git identity of its own" is about ITS OWN
    ancestry, not `tmp_path`'s — some sandboxes mount `/tmp` (or an ancestor
    of it) inside a git checkout of their own (planning#158), which would
    make the real, unresolved walk-up from `isolated_no_git` find that
    unrelated ancestor's `.git` and turn this into a DIFFERENT regression
    this test does not cover. So the one filesystem lookup that must see "no
    repository here" for `isolated_no_git` itself is pinned directly,
    leaving every other lookup (in particular the syntactic walk-up from
    `link` that must still independently find `repo_a`) running the real,
    unmocked git-discovery code."""
    repo_a = _clone(origin, tmp_path / "repo-a")
    isolated_no_git = tmp_path / "isolated-no-git"
    isolated_no_git.mkdir()
    link = repo_a / "link-out"
    link.symlink_to(isolated_no_git)

    isolated_real = os.path.realpath(str(isolated_no_git))
    original_lookup = repo_identity._git_dir_from_filesystem

    def _lookup_with_isolated_boundary(cwd: str) -> str:
        if os.path.abspath(cwd) == isolated_real:
            return ""
        return original_lookup(cwd)

    monkeypatch.setattr(repo_identity, "_git_dir_from_filesystem", _lookup_with_isolated_boundary)

    assert repo_identity.repo_name(str(link)) == "acme-widgets"


# --- fabricated `gitdir:` FILE provenance (no symlink involved) ------------


def test_fabricated_gitdir_file_at_cwd_raises_ambiguous_not_foreign_identity(tmp_path, origin):
    """A PLAIN (non-symlink) ``.git`` FILE at ``cwd`` containing a
    hand-crafted ``gitdir: <foreign>/.git`` line must not mint the foreign
    repo's identity. No symlink, no env var, no sibling ambiguity — just a
    fabricated pointer with no back-reference registering it as a real
    worktree/submodule of that foreign repo. Real ``git`` itself would also
    follow this pointer and report the foreign origin, so the live-git probe
    corroborates rather than catches the spoof — the filesystem-level check
    must refuse before a probe is ever run."""
    victim = _clone(origin, tmp_path / "victim")
    evil = tmp_path / "evil"
    evil.mkdir()
    (evil / ".git").write_text(f"gitdir: {victim / '.git'}\n")

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(evil))


def test_fabricated_gitdir_file_at_an_ancestor_level_raises_ambiguous(tmp_path, origin):
    """Same fabricated pointer, discovered one or more levels up the upward
    walk rather than at ``cwd`` itself."""
    victim = _clone(origin, tmp_path / "victim")
    evil_parent = tmp_path / "evil-parent"
    evil_parent.mkdir()
    (evil_parent / ".git").write_text(f"gitdir: {victim / '.git'}\n")
    nested = evil_parent / "nested" / "deeper"
    nested.mkdir(parents=True)

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(nested))


def test_fabricated_gitdir_file_with_synthetic_worktrees_segment_raises_ambiguous(
    tmp_path, origin
):
    """A fabricated ``gitdir:`` pointer can also masquerade as a legitimate
    worktree by including a synthetic ``/worktrees/<name>`` path segment,
    hoping the marker-based fast path is trusted without checking for the
    real worktree admin directory's back-reference. ``<name>`` here does not
    correspond to any worktree the victim repo actually registered, so the
    back-reference (``<victim>/.git/worktrees/<name>/gitdir``) does not
    exist and this must still fail closed."""
    victim = _clone(origin, tmp_path / "victim")
    evil = tmp_path / "evil"
    evil.mkdir()
    fake_worktree_path = victim / ".git" / "worktrees" / "not-a-real-worktree"
    (evil / ".git").write_text(f"gitdir: {fake_worktree_path}\n")

    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.repo_name(str(evil))


def test_real_worktree_add_still_resolves_correctly(tmp_path, origin):
    """Regression guard against over-rejection: a REAL ``git worktree add``
    checkout's genuine ``gitdir:`` file — with a matching back-reference at
    ``<main>/.git/worktrees/<name>/gitdir`` — must keep resolving to the main
    repo's identity, exactly as before this fix."""
    clone = _clone(origin, tmp_path / "work" / "acme-widgets")
    wt = tmp_path / "elsewhere" / "a-worktree-checkout"
    _git("worktree", "add", "-q", "-b", "lane-real", str(wt), cwd=clone)
    assert repo_identity.repo_name(str(wt)) == "acme-widgets"


def test_real_submodule_still_resolves_to_its_own_origin(tmp_path, origin):
    """Regression guard: a REAL ``git submodule add`` checkout's genuine
    ``gitdir:`` file (a bare pointer with no ``/worktrees/`` marker) — with a
    matching ``core.worktree`` back-reference in the submodule's admin
    ``config`` — must keep resolving to the submodule's OWN origin, not
    raise."""
    sub_origin = tmp_path / "sub-widget.git"
    sub_origin.mkdir()
    _git("init", "--bare", "-q", cwd=sub_origin)
    sub_seed = _clone(sub_origin, tmp_path / "sub-seed")
    default_ref = subprocess.run(
        ["git", "symbolic-ref", "HEAD"],
        cwd=sub_origin,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git("push", "-q", "origin", f"HEAD:{default_ref}", cwd=sub_seed)

    parent = tmp_path / "parent"
    parent.mkdir()
    _git("init", "-q", cwd=parent)
    _git(
        "-c", "protocol.file.allow=always", "submodule", "-q", "add", str(sub_origin), "sub",
        cwd=parent,
    )

    assert repo_identity.repo_name(str(parent / "sub")) == "sub-widget"


# --- GIT_DIR / GIT_WORK_TREE env bypass -------------------------------------


def test_git_dir_env_does_not_spoof_identity_for_an_unambiguous_checkout(
    tmp_path, origin, monkeypatch
):
    """`Deadline.run` shells out to `git ...` with `cwd=<checkout>`, but
    (pre-fix) inherited the ambient environment wholesale. An ambient
    `GIT_DIR` pointing at a different, unrelated repo makes git obey the env
    override and report THAT repo's `origin` regardless of `cwd` — spoofing
    identity even for a single, otherwise-unambiguous checkout. The probe
    must be forced to discover from `cwd`, corroborating the
    filesystem-based canonical resolution above it, never trusting an
    ambient env spoof."""
    victim = _clone(origin, tmp_path / "victim")

    spoof_origin = tmp_path / "spoof.git"
    spoof_origin.mkdir()
    _git("init", "--bare", "-q", cwd=spoof_origin)
    spoof = _clone(spoof_origin, tmp_path / "spoof-checkout")

    monkeypatch.setenv("GIT_DIR", str(spoof / ".git"))

    assert repo_identity.repo_name(str(victim)) == "acme-widgets"


def test_git_work_tree_env_does_not_spoof_identity_for_an_unambiguous_checkout(
    tmp_path, origin, monkeypatch
):
    """Same spoof as above, via `GIT_WORK_TREE` instead of `GIT_DIR` —
    either identity-discovery override must be stripped from the probe's
    environment, not just one of them."""
    victim = _clone(origin, tmp_path / "victim")

    spoof_origin = tmp_path / "spoof.git"
    spoof_origin.mkdir()
    _git("init", "--bare", "-q", cwd=spoof_origin)
    spoof = _clone(spoof_origin, tmp_path / "spoof-checkout")

    monkeypatch.setenv("GIT_DIR", str(spoof / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(spoof))

    assert repo_identity.repo_name(str(victim)) == "acme-widgets"


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


def test_identity_honors_a_caller_supplied_deadline_instead_of_minting_its_own(tmp_path, origin, monkeypatch):
    """A caller folding this call into its OWN broader Git budget (e.g. one
    status-transition broadcast resolving credentials, presence identity,
    and a focus capability) must have that ONE deadline threaded to every
    probe — not have identity() silently mint a fresh GIT_BUDGET_S on top
    of it (EXPERIMENTAL-spec-kitty#203)."""
    clone = _clone(origin, tmp_path / "clone")
    shared = repo_identity.Deadline(60.0)
    seen: list[object] = []

    real_repo_name = repo_identity.repo_name
    real_branch_name = repo_identity.branch_name
    real_commit_oid = repo_identity.commit_oid
    monkeypatch.setattr(repo_identity, "repo_name", lambda cwd, deadline=None: (seen.append(deadline), real_repo_name(cwd, deadline))[1])
    monkeypatch.setattr(repo_identity, "branch_name", lambda cwd, deadline=None: (seen.append(deadline), real_branch_name(cwd, deadline))[1])
    monkeypatch.setattr(repo_identity, "commit_oid", lambda cwd, deadline=None: (seen.append(deadline), real_commit_oid(cwd, deadline))[1])

    repo_identity.identity(str(clone), deadline=shared)

    assert seen == [shared, shared, shared], (
        "identity() must thread the SAME caller-supplied Deadline into repo_name/branch_name/commit_oid, not mint a fresh one per probe or per call"
    )


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
    """The one wedged live-git probe (`config --get remote.origin.url`, the
    first origin candidate) spends the whole budget; branch/commit lookups
    must not each get a fresh one."""
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


def test_for_repository_passes_the_given_deadline_to_identity(tmp_path, origin, monkeypatch):
    """The transport-config half of #203: ``for_repository`` must forward a
    caller's shared Deadline into ``repo_identity.identity`` rather than
    letting it default to a fresh ``GIT_BUDGET_S`` budget of its own."""
    clone = _clone(origin, tmp_path / "work" / "clone")
    shared = repo_identity.Deadline(60.0)
    seen: list[object] = []
    real_identity = repo_identity.identity
    monkeypatch.setattr(
        repo_identity,
        "identity",
        lambda cwd, budget=repo_identity.GIT_BUDGET_S, *, deadline=None: (
            seen.append(deadline),
            real_identity(cwd, budget, deadline=deadline),
        )[1],
    )

    transport.ClientConfig.for_repository(
        str(clone),
        relay_url="http://127.0.0.1:9",
        token="tok",
        harness="claude-code",
        session_id="sess-1",
        deadline=shared,
    )

    assert seen == [shared], "for_repository must forward the caller's Deadline, not mint its own"


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


# --- origin_url(): the verbatim URL behind the canonical name ---------------


def test_origin_url_returns_the_live_remote_verbatim(tmp_path, origin):
    """E3 credential resolution derives Team Kitty's ``owner/repo`` slug and
    host from this URL -- it must be the remote itself, never a name minted
    from it."""
    clone = _clone(origin, tmp_path / "work" / "some-other-dirname")
    url = repo_identity.origin_url(str(clone))
    assert url.endswith("acme-widgets.git")
    assert "work" not in url  # the checkout path leaks nothing into it


def test_origin_url_ignores_a_global_insteadof_transport_rewrite(tmp_path, origin, instead_of_rewrite):
    """``git remote get-url`` reports where a fetch would go — through any
    global ``url.<base>.insteadOf`` rewrite — not where the checkout says it
    came from. The identity must report the latter: on a proxy-rewriting
    machine the rewritten host leaking into ``origin_url`` had Team Kitty
    being asked to admit a forge it has never heard of (#81)."""
    clone = _clone(origin, tmp_path / "work" / "some-other-dirname")
    _git("remote", "set-url", "origin", "https://github.com/acme/acme-widgets.git", cwd=clone)
    assert repo_identity.origin_url(str(clone)) == "https://github.com/acme/acme-widgets.git"


def test_repo_name_is_unchanged_by_a_global_insteadof_transport_rewrite(tmp_path, origin, instead_of_rewrite):
    """Name and URL share one candidate chain on purpose (repo_name and
    origin_url must never drift): under the same rewrite both still agree
    about which repository this is."""
    clone = _clone(origin, tmp_path / "work" / "some-other-dirname")
    _git("remote", "set-url", "origin", "https://github.com/acme/acme-widgets.git", cwd=clone)
    assert repo_identity.repo_name(str(clone)) == "acme-widgets"


def test_origin_url_uses_the_quarantine_record_when_the_remote_is_gone(tmp_path):
    """Same sources, same order as repo_name: the frozen quarantine record
    is the fallback once the live remote was deliberately removed."""
    local = tmp_path / "scratch"
    local.mkdir()
    _git("init", "-q", cwd=local)
    config_path = local / ".git" / "config"
    with config_path.open("a") as f:
        f.write('\n[kitty "quarantine"]\n\torigin = https://example.invalid/org/acme-widgets.git\n')
    assert (
        repo_identity.origin_url(str(local)) == "https://example.invalid/org/acme-widgets.git"
    )


def test_origin_url_is_empty_when_no_source_has_one(tmp_path):
    local = tmp_path / "scratch"
    local.mkdir()
    _git("init", "-q", cwd=local)
    assert repo_identity.origin_url(str(local)) == ""


def test_origin_url_refuses_an_ambiguous_container_like_repo_name(tmp_path, origin):
    """The hardening around identity applies to the URL too: a
    session-container directory must raise, not hand back whichever
    ancestor's remote happens to be reachable."""
    _clone(origin, tmp_path / "container" / "one")
    _clone(origin, tmp_path / "container" / "two")
    with pytest.raises(repo_identity.AmbiguousRepositoryIdentity):
        repo_identity.origin_url(str(tmp_path / "container"))
