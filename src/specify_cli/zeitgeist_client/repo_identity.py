"""Canonical repository identity (Z6-C, program-graph handle Z6-C):
"Canonicalize repository identity across session-container directories;
ambiguous multi-checkout containers, symlinks, missing origin/quarantine
metadata, and conflicting roots fail rather than mint/guess identity."

``credentials.py``'s own module docstring anticipated this: "Keyed by
canonical repo (from ``repo_identity.identity()`` — not yet ported in this
pass)." This is that module. It is NOT a literal parity port the way
``grammar.py`` is a byte-for-byte transcription of
``zeitgeist/editor.py:146-192`` — that file's grammar is already correct for
Z1's purpose. ``zeitgeist/integrations/repo_identity.py`` is not, for THIS
purpose: its own ``repo_name()`` falls back, when no ``origin`` remote is
configured, to the basename of ``--git-common-dir``'s parent and finally to
the basename of ``cwd`` itself — i.e. a DIRECTORY NAME. A directory name is
exactly what an ordinary ``mv``, or a hostile checkout, controls. Z1's own
``transport.ClientConfig.repo`` is an explicit caller-supplied CLAIM (Z1.md
decision 7, "caller fields are claims only") — this module exists to give a
canonical-identity-aware caller (the not-yet-built CLI adapter; see
``docs/plans/zeitgeist-client-wp01-remaining.md`` item 5) something stronger
than a claim to bind presence to, so a checkout renamed or relocated to
impersonate a different project cannot mint that project's identity.
Directory-basename fallbacks would defeat exactly that, so this module never
uses one: ``repo_name()`` derives ONLY from ``origin`` (live, or a
``.git/config``-only read when git is slow/unavailable) or from committed
"quarantine metadata" (see ``_QUARANTINE_SECTION`` below — a frozen record of
a prior ``origin`` for a repository whose live remote was deliberately
removed, e.g. this program's own HIC-BOOT-003 remote-quarantine contract).
Everything else — no origin and no quarantine record, an ambiguous
"session-container" directory holding more than one checkout, or a symlink
that makes the syntactic path and the resolved path disagree about which
checkout is meant — raises rather than guesses.

``Deadline``, the ``origin``/``.git``-directory filesystem readers, and the
aggregate-git-budget discipline (NFR-001 in zeitgeist's own WP01) ARE ported
unchanged from ``zeitgeist/integrations/repo_identity.py`` — that machinery's
correctness does not depend on the guess-vs-fail question above, and
``GIT_BUDGET_S`` keeps upstream's own 2.0s value: nested inside
``budget.HOOK_BUDGET_S`` (4.0s) alongside ``budget.OFFER_BUDGET_S`` (0.75s)
with margin to spare, the same nesting discipline ``budget.py`` documents for
its own constant.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass

# Repo derivation, branch lookup, and commit lookup share this — one wall-clock
# budget for ALL Git work in one identity() call, not a per-subprocess value.
# Ported from zeitgeist/integrations/repo_identity.py (NFR-001).
GIT_BUDGET_S = 2.0

# Below this there is no point starting another subprocess: fork+exec of git
# costs more than the remaining budget, and a probe launched with ~0s left can
# only be killed. Give up and take the next fallback instead.
_MIN_PROBE_S = 0.05

# Section a trusted quarantine process writes into `.git/config`, recording
# the `origin` a checkout had before its live remote was removed. Same INI
# shape as `[remote "origin"]`, so it is read by the identical minimal walk.
_QUARANTINE_SECTION = 'kitty "quarantine"'

# `git`'s own repository-discovery env overrides. Left ambient, any one of
# these can make `git` resolve to (and therefore report the `origin` of) a
# DIFFERENT repository than the one at `cwd` — e.g. an ambient `GIT_DIR`
# pointing at another checkout entirely. `Deadline.run` strips all of them
# before every probe so discovery is forced to start from `cwd`, the same
# starting point the filesystem-based canonical resolution above it already
# used — the live-git probe must corroborate that resolution, not be
# spoofable into contradicting it.
_GIT_DISCOVERY_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_CEILING_DIRECTORIES",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
)


class RepoIdentityError(Exception):
    """Base for every way `identity()`/`repo_name()` refuse to mint an
    identity rather than guess one. Callers that only care "did this fail"
    can catch this; callers that want to distinguish why catch the specific
    subclasses below."""


class AmbiguousRepositoryIdentity(RepoIdentityError):
    """More than one checkout could be "the" repository: a session-container
    directory holding several independent checkouts, or a symlink whose
    syntactic path and resolved path disagree about which checkout is
    meant."""


class UnverifiedRepositoryIdentity(RepoIdentityError):
    """A single checkout was found, but it carries no non-spoofable
    provenance: no `origin` remote (live or in `.git/config`) and no
    `[kitty "quarantine"]` record of a prior one."""


@dataclass(frozen=True)
class RepoIdentity:
    """`(repo, branch, commit)` for one checkout, under ONE aggregate Git
    deadline — "the exact repo/commit truth" `identity()` returns."""

    repo: str
    branch: str
    commit: str


class Deadline:
    """A shrinking wall-clock budget shared across several Git probes.

    ``run()`` passes what is LEFT to ``subprocess.run(timeout=...)``, so N
    probes under one Deadline finish in the budget, not N times the budget.
    Exhausted probes return ``""`` — identical to a failed probe, so every
    caller's existing fallback chain already handles them and no call site
    needs a timeout branch. Ported unchanged from
    ``zeitgeist/integrations/repo_identity.py``.
    """

    def __init__(self, budget: float = GIT_BUDGET_S):
        self.expires_at = time.monotonic() + budget

    def remaining(self) -> float:
        return self.expires_at - time.monotonic()

    def expired(self) -> bool:
        return self.remaining() < _MIN_PROBE_S

    def run(self, args: list[str], cwd: str) -> str:
        """One ``git`` probe against the remaining budget. ``""`` on any
        failure, including a spent budget.

        Runs with ``git``'s own repository-discovery env overrides
        (``_GIT_DISCOVERY_ENV_VARS``) stripped from the inherited
        environment, so an ambient ``GIT_DIR``/``GIT_WORK_TREE``/etc.
        pointing at a different repository cannot make this probe report
        that repository's identity instead of ``cwd``'s."""
        left = self.remaining()
        if left < _MIN_PROBE_S:
            return ""
        env = {k: v for k, v in os.environ.items() if k not in _GIT_DISCOVERY_ENV_VARS}
        try:
            out = subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=left,
                env=env,
            )
            return out.stdout.strip() if out.returncode == 0 else ""
        except Exception:
            return ""


def _name_from_url(url: str) -> str:
    name = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name


def _reject_symlinked_git_entry(candidate: str) -> None:
    """Raise ``AmbiguousRepositoryIdentity`` if the ``.git`` entry at
    ``candidate`` is itself a symlink (to a directory OR to a file).

    Git never legitimately produces a symlinked ``.git`` entry: a worktree
    or submodule always uses a plain FILE containing a ``gitdir:`` line, not
    a symlink to a directory (or to another file). A directory whose ONLY
    ``.git`` entry is a symlink pointing at a different checkout's real
    ``.git`` — no sibling ambiguity, no env var, no clone needed — would
    otherwise have that foreign checkout's ``origin``/branch/commit read
    straight through the symlink by ``isdir``/``isfile``/``exists``, all of
    which follow symlinks by default. That is exactly the "symlink that
    makes the syntactic path and the resolved path disagree about which
    checkout is meant" the module docstring already commits to rejecting —
    checked here at ``.git``-entry granularity, at every level a discovery
    walk considers (``cwd`` itself or any ancestor), not only when the
    disagreement shows up in an outer path component."""
    if os.path.islink(candidate):
        raise AmbiguousRepositoryIdentity(
            f"{candidate!r} is a symlink — git never legitimately produces a "
            "symlinked `.git` entry (a worktree/submodule `.git` is always a "
            "plain file with a `gitdir:` line, never a symlink); refusing to "
            "trust it as provenance for a checkout identity"
        )


_WORKTREE_MARKER = os.sep + "worktrees" + os.sep


def _worktree_backref_target(mainrepo_git_dir: str, name: str) -> str:
    """Read ``<mainrepo_git_dir>/worktrees/<name>/gitdir`` — a real
    ``git worktree add`` writes this file itself, containing the absolute
    path of the worktree checkout's OWN ``.git`` file (the back-reference a
    legitimate worktree registration always carries). ``""`` if the
    registration does not exist — exactly the case for a fabricated
    ``gitdir:`` pointer using a synthetic/unregistered worktree name."""
    backref = os.path.join(mainrepo_git_dir, "worktrees", name, "gitdir")
    try:
        with open(backref) as f:
            return f.read().strip()
    except OSError:
        return ""


def _submodule_backref_target(gitdir: str) -> str:
    """Read ``core.worktree`` out of ``<gitdir>/config`` — a real
    ``git submodule add`` writes this into the submodule's admin directory,
    recording the working-tree path whose ``.git`` file points back at it.
    ``""`` if absent, which is exactly the case for a hand-crafted
    ``gitdir:`` pointer at an arbitrary foreign ``.git`` directory that
    carries no such record."""
    worktree = _read_ini_value(gitdir, "[core]", "worktree")
    if not worktree:
        return ""
    if not os.path.isabs(worktree):
        worktree = os.path.normpath(os.path.join(gitdir, worktree))
    return worktree


def _verify_gitdir_provenance(candidate: str, path: str, gitdir: str) -> str:
    """A ``.git`` FILE's ``gitdir:`` pointer is trusted ONLY when the target
    is a VERIFIABLY registered worktree or submodule of that repository — a
    matching back-reference the real ``git worktree add``/``git submodule
    add`` machinery itself wrote, not merely a path that happens to exist.

    Without this, a hand-crafted ``.git`` FILE containing
    ``gitdir: <foreign>/.git`` (no symlink, no env var, no sibling
    ambiguity — just a fabricated pointer) would mint the foreign repo's
    identity: real ``git`` itself also follows such a pointer, so the
    live-git probe would corroborate the spoof rather than catch it. This
    check is what stands between "a `.git` file points somewhere" and "that
    pointer is legitimate provenance."

    Raises ``AmbiguousRepositoryIdentity`` for any pointer that cannot be
    corroborated this way — covering a bare (non-worktree) pointer at an
    unregistered foreign ``.git`` directory, and a pointer forged with a
    synthetic/unregistered ``/worktrees/<name>`` segment."""
    if _WORKTREE_MARKER in gitdir:
        mainrepo_git_dir, _, rest = gitdir.partition(_WORKTREE_MARKER)
        name = rest.split(os.sep, 1)[0]
        backref = _worktree_backref_target(mainrepo_git_dir, name)
        if backref and os.path.realpath(backref) == os.path.realpath(candidate):
            return mainrepo_git_dir
        raise AmbiguousRepositoryIdentity(
            f"{candidate!r} points to {gitdir!r}, claiming to be a worktree "
            f"of {mainrepo_git_dir!r} — but no matching back-reference "
            f"({mainrepo_git_dir!r}/worktrees/{name!r}/gitdir) registers it "
            "as one; refusing to trust unregistered `gitdir:` provenance"
        )

    backref = _submodule_backref_target(gitdir)
    if backref and os.path.realpath(backref) == os.path.realpath(path):
        return gitdir
    raise AmbiguousRepositoryIdentity(
        f"{candidate!r} points to {gitdir!r} with no `/worktrees/` marker "
        "and no matching submodule back-reference (`core.worktree`) — "
        "refusing to trust unregistered `gitdir:` provenance"
    )


def _git_dir_from_filesystem(cwd: str) -> str:
    """Locate the common ``.git`` directory by reading files, never running
    git. Ported unchanged from ``zeitgeist/integrations/repo_identity.py``: a
    worktree's ``.git`` is a plain text file containing
    ``gitdir: /path/to/main/.git/worktrees/<name>``, so the whole layout is
    readable without a subprocess.

    Raises ``AmbiguousRepositoryIdentity`` — rather than resolving through it
    — the moment any ``.git`` entry considered along the upward walk (at
    ``cwd`` or any ancestor) is itself a symlink; see
    ``_reject_symlinked_git_entry``. Also raises it when a ``.git`` FILE's
    ``gitdir:`` pointer cannot be corroborated as a registered
    worktree/submodule of the target repository; see
    ``_verify_gitdir_provenance``."""
    path = os.path.abspath(cwd)
    while True:
        candidate = os.path.join(path, ".git")
        _reject_symlinked_git_entry(candidate)
        if os.path.isdir(candidate):
            return candidate
        if os.path.isfile(candidate):
            try:
                with open(candidate) as f:
                    for line in f:
                        if line.startswith("gitdir:"):
                            gitdir = line.split(":", 1)[1].strip()
                            if not os.path.isabs(gitdir):
                                gitdir = os.path.join(path, gitdir)
                            gitdir = os.path.normpath(gitdir)
                            return _verify_gitdir_provenance(candidate, path, gitdir)
            except OSError:
                return ""
        parent = os.path.dirname(path)
        if parent == path:
            return ""
        path = parent


def _read_ini_value(git_dir: str, section_marker: str, key: str) -> str:
    """Read ``key`` out of the first matching ``[section]`` block of
    ``<git_dir>/config``, with no subprocess. Shared minimal-INI walk behind
    both ``_origin_from_filesystem`` and the quarantine-metadata reader —
    ``configparser`` rejects real-world ``.git/config`` files, so both use
    the same small walk upstream chose for the origin case."""
    try:
        with open(os.path.join(git_dir, "config")) as f:
            in_section = False
            for raw_line in f:
                line = raw_line.strip()
                if line.startswith("["):
                    in_section = line.replace(" ", "").lower() == section_marker
                elif in_section and line.lower().startswith(key):
                    _, _, value = line.partition("=")
                    return value.strip()
    except OSError:
        return ""
    return ""


def _origin_from_filesystem(cwd: str) -> str:
    """Read ``[remote "origin"] url`` out of ``.git/config`` with no
    subprocess. Ported unchanged from
    ``zeitgeist/integrations/repo_identity.py``."""
    git_dir = _git_dir_from_filesystem(cwd)
    if not git_dir:
        return ""
    return _read_ini_value(git_dir, '[remote"origin"]', "url")


def _quarantine_origin_from_filesystem(cwd: str) -> str:
    """Read the frozen ``origin`` a quarantine process recorded before
    removing the live remote — see the module docstring and
    ``_QUARANTINE_SECTION``."""
    git_dir = _git_dir_from_filesystem(cwd)
    if not git_dir:
        return ""
    marker = "[" + _QUARANTINE_SECTION.replace(" ", "").lower() + "]"
    return _read_ini_value(git_dir, marker, "origin")


def _sibling_checkouts(path: str) -> list[str]:
    """Immediate child directories of ``path`` that are themselves git
    checkouts (contain their own ``.git``). Two or more make ``path`` an
    ambiguous "session-container directory" — Z6-C's own term for e.g. this
    program's ``.sandboxes/`` — when queried directly rather than from
    inside one specific checkout.

    ``entry.is_dir()`` is resolved WITH symlinks followed
    (``follow_symlinks=True``, the default): a symlinked child checkout is
    exactly as real a checkout as a plain-directory one for ambiguity
    purposes, and gating on ``follow_symlinks=False`` (which reports a
    symlink as "not a directory" even when it resolves to one) previously
    let a symlinked sibling go uncounted — a container with one real
    checkout and one symlinked checkout would then mint an ancestor
    directory's identity instead of raising."""
    try:
        entries = list(os.scandir(path))
    except OSError:
        return []
    found = []
    for entry in entries:
        try:
            is_dir = entry.is_dir()
        except OSError:
            continue
        if is_dir and os.path.exists(os.path.join(entry.path, ".git")):
            found.append(entry.name)
    return found


def _canonical_git_dir(cwd: str) -> str:
    """The one checkout ``cwd`` unambiguously belongs to, or ``""`` if it is
    not inside any checkout at all. Raises ``AmbiguousRepositoryIdentity``
    rather than picking one when that cannot be determined — see the module
    docstring.

    The sibling-checkout ("session-container") check below must run
    whenever ``cwd`` is not itself directly a checkout root/worktree (no
    ``.git`` sitting AT ``cwd``), regardless of whether the upward walk from
    ``cwd`` finds an ANCESTOR directory's ``.git``. A session-container that
    holds several independent checkouts can itself sit inside another git
    repository — exactly this program's own ``.sandboxes/``, nested inside
    the root control-plane repo — and trusting the ancestor's ``.git`` first
    would silently mint that unrelated ancestor's identity instead of
    refusing to guess (the whole point of this module)."""
    raw_abspath = os.path.abspath(cwd)
    real_abspath = os.path.realpath(cwd)

    raw = _git_dir_from_filesystem(raw_abspath)
    real = _git_dir_from_filesystem(real_abspath)
    if raw and real and os.path.realpath(raw) != os.path.realpath(real):
        raise AmbiguousRepositoryIdentity(
            f"{cwd!r} resolves to two different repository roots depending on "
            f"whether a symlink in its path is followed ({raw!r} via the "
            f"literal path vs {real!r} via the resolved path) — refusing to "
            "guess which is canonical"
        )

    # Exotic follow-up (Z6-M2-01, deferred by HIC-M1-Z6C-GOODENOUGH): the
    # check above only fires when BOTH `raw` and `real` independently find a
    # (different) checkout. It says nothing when one side finds NOTHING —
    # which is not proof of agreement. Concretely: `cwd` = a symlink sitting
    # in a directory with no git identity of its own (e.g. an isolated
    # sandbox dir), pointing into a SUBDIRECTORY of a real, unrelated
    # checkout (a subdirectory, so it carries no `.git` of its own — only
    # its ancestor does). `raw`'s walk-up is a STRING (`os.path.dirname`)
    # walk from `raw_abspath`; the OS transparently resolves the symlink for
    # the FIRST candidate check (`raw_abspath/.git`), but every subsequent
    # step walks up the SYNTACTIC ancestor chain, which never reaches the
    # foreign checkout's `.git` — so `raw` comes back empty, not merely
    # "different". `real`, walking up from the fully-resolved location,
    # correctly reaches the foreign checkout and comes back non-empty. That
    # asymmetry (real mints an identity that raw never independently
    # corroborated) is exactly the "syntactic path and resolved path
    # disagree about which checkout is meant" case this module already
    # commits to rejecting for the "different checkout" shape — "no
    # checkout at all" is just as much a disagreement as "a different one".
    #
    # The REVERSE asymmetry (raw finds a checkout, real finds nothing — a
    # symlink INSIDE a real checkout pointing OUTSIDE any repo) is
    # deliberately NOT raised here: `real` is what an actual `git`
    # subprocess run at `cwd` would observe (the OS's own `chdir` follows
    # symlinks the same way `os.path.realpath` does), so an empty `real`
    # there means the live probe fails closed on its own and every fallback
    # re-derives `raw`'s single candidate — repo_a's own identity for a path
    # that is genuinely part of repo_a — with no competing identity to
    # disagree with. See
    # test_symlink_into_a_subdirectory_of_a_different_checkout_raises_ambiguous
    # and test_symlink_inside_a_checkout_to_a_non_repo_location_does_not_raise.
    if raw_abspath != real_abspath and not raw and real:
        raise AmbiguousRepositoryIdentity(
            f"{cwd!r} only resolves to a repository root ({real!r}) when a "
            "symlink in its path is followed — the literal path never "
            "independently reaches that checkout (or any other); refusing "
            "to mint an identity the syntactic path does not corroborate"
        )

    # Belt-and-suspenders alongside the walk-level check inside
    # `_git_dir_from_filesystem` above (which already raises before this
    # line is reached whenever `real_abspath/.git` is a symlink): this
    # `.git`-entry existence check is exactly the kind `os.path.islink` must
    # gate before `os.path.exists` (which follows symlinks) is trusted, so
    # it is asserted explicitly here too rather than relying only on the
    # call above never being reordered or bypassed.
    real_git_entry = os.path.join(real_abspath, ".git")
    _reject_symlinked_git_entry(real_git_entry)
    cwd_is_own_checkout = os.path.exists(real_git_entry)
    if not cwd_is_own_checkout:
        siblings = _sibling_checkouts(real_abspath)
        if len(siblings) >= 2:
            raise AmbiguousRepositoryIdentity(
                f"{cwd!r} is not itself a checkout but directly contains "
                f"{len(siblings)} independent ones ({sorted(siblings)!r}) — "
                "refusing to guess which is canonical; call identity() from "
                "inside the intended checkout instead"
            )

    return real or raw


def _origin_candidates(cwd: str, deadline: Deadline) -> Iterator[str]:
    """The four origin-URL sources ``repo_name``/``origin_url`` consult, in
    order: the checkout's own configured ``remote.origin.url``, the
    transport view of that same remote, ``.git/config``, and the frozen
    quarantine record. Shared so both callers can never drift apart about
    which sources exist or in what order they are tried.

    The configured URL is read through ``git config --get`` rather than
    ``git remote get-url`` on purpose: the latter reports where a fetch
    would actually go, which is not where the checkout says it came from
    once a global ``url.<base>.insteadOf`` rewrite stands in between (a
    corporate mirror, an integration proxy). Team Kitty admits presence by
    the forge host the checkout itself names — a machine-local transport
    rewrite must never re-home that identity to a forge it has never heard
    of. The transport view stays second as a fallback for remotes whose URL
    only resolves at transport time."""
    yield deadline.run(["config", "--get", "remote.origin.url"], cwd)
    yield deadline.run(["remote", "get-url", "origin"], cwd)
    yield _origin_from_filesystem(cwd)
    yield _quarantine_origin_from_filesystem(cwd)


def repo_name(cwd: str, deadline: Deadline | None = None) -> str:
    """Canonical repo name, from ``origin`` or quarantine metadata ONLY —
    never a directory name. See the module docstring for the full rationale
    and the divergence from ``zeitgeist/integrations/repo_identity.py``.

    Raises ``AmbiguousRepositoryIdentity`` for a session-container directory
    or a symlink-caused root conflict, and ``UnverifiedRepositoryIdentity``
    when a single checkout is found but has no `origin` (live or on disk)
    and no quarantine record.

    Pass a ``deadline`` to share one budget with the caller's other probes
    (branch/commit lookups); called without one it allocates its own, which
    is correct only when this is the single Git consumer in the process —
    ``identity()`` is what callers binding presence want.
    """
    deadline = deadline or Deadline()
    _canonical_git_dir(cwd)  # may raise AmbiguousRepositoryIdentity

    for url in _origin_candidates(cwd, deadline):
        if url:
            name = _name_from_url(url)
            if name:
                return name

    raise UnverifiedRepositoryIdentity(
        f"{cwd!r} has no `origin` remote (live or in `.git/config`) and no "
        f"[{_QUARANTINE_SECTION}] quarantine record — refusing to mint an "
        "identity from a directory name"
    )


def origin_url(cwd: str, deadline: Deadline | None = None) -> str:
    """The checkout's ``origin`` URL, verbatim, from the same sources and in
    the same order :func:`repo_name` mints the canonical name from — see
    :func:`_origin_candidates` for the full four-source chain. ``""`` when
    none of them has one.

    Callers that need more than the bare name — E3 credential resolution
    derives the ``owner/repo`` slug and remote host Team Kitty admits by —
    read the URL here rather than re-shelling out to git themselves, so the
    symlink/ambiguity hardening above applies to their input too. Raises
    ``AmbiguousRepositoryIdentity`` under exactly the conditions
    :func:`repo_name` does.
    """
    _canonical_git_dir(cwd)  # may raise AmbiguousRepositoryIdentity
    for url in _origin_candidates(cwd, deadline or Deadline()):
        if url:
            return url
    return ""


def branch_name(cwd: str, deadline: Deadline | None = None) -> str:
    """Current branch, or ``""`` when Git is unavailable, detached, or out of
    budget — never identity-critical (unlike ``repo_name``, a wrong branch
    guess cannot make presence appear as a different repository), so this
    degrades quietly rather than raising."""
    _canonical_git_dir(cwd)  # may raise AmbiguousRepositoryIdentity
    return (deadline or Deadline()).run(["rev-parse", "--abbrev-ref", "HEAD"], cwd)


def commit_oid(cwd: str, deadline: Deadline | None = None) -> str:
    """Current commit OID, or ``""`` when Git is unavailable or out of
    budget. Same non-fatal degradation as ``branch_name``."""
    _canonical_git_dir(cwd)  # may raise AmbiguousRepositoryIdentity
    return (deadline or Deadline()).run(["rev-parse", "HEAD"], cwd)


def identity(cwd: str, budget: float = GIT_BUDGET_S, *, deadline: Deadline | None = None) -> RepoIdentity:
    """``RepoIdentity(repo, branch, commit)`` for ``cwd``, under ONE
    aggregate Git deadline — the sanctioned entry point for a caller binding
    client presence to canonical identity (Z6-C). Deriving the three
    separately would let independent timeouts stack past a hook's harness
    bound, exactly the bug zeitgeist's own WP01 fixed for repo+branch.

    Pass ``deadline`` to fold this call into a *caller's* broader Git
    budget — e.g. one status transition resolving credentials, presence
    identity, and a focus capability in the same handler invocation — so the
    three don't each stack their own ``budget`` on top of the others past a
    fan-out's own bound (EXPERIMENTAL-spec-kitty#203). Omit it to allocate a
    fresh ``Deadline(budget)``, correct when this is the call's only Git
    consumer.

    Raises ``AmbiguousRepositoryIdentity``/``UnverifiedRepositoryIdentity``
    (both ``RepoIdentityError``) instead of returning a guessed ``repo``.
    """
    deadline = deadline or Deadline(budget)
    repo = repo_name(cwd, deadline)
    branch = branch_name(cwd, deadline)
    commit = commit_oid(cwd, deadline)
    return RepoIdentity(repo=repo, branch=branch, commit=commit)
