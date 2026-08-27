"""Per-run pytest temp root — retire the shared ``pytest-of-<user>`` numbered-dir
tree's unbounded growth and stale-lock debt.

**What this is NOT: a fix for #63's crash mechanism.** An earlier version of
this module claimed the ``OSError: could not create numbered dir with prefix
test_* ... after 10 tries`` crash in #63 (a different xdist worker each run) was
cross-run contention in :func:`_pytest.pathlib.make_numbered_dir` and its
cleanup wrapper (sibling scans, symlink locks, old-root pruning). A
controller-qa audit on this fix falsified that: every #63 crash names a
*worker* basetemp (``pytest-0/popen-gw<N>``) — an already-resolved
``_given_basetemp`` — and ``TempPathFactory.getbasetemp`` takes the
given-basetemp branch there (plain ``rm_rf`` + ``mkdir``), never the
numbered-dir path with its locks and pruning. Exactly one process ever writes
that directory, so there is no sibling to race. ``_pytest/pathlib.py``'s
numbered-dir ``mkdir`` also swallows *any* ``Exception``, so the "after 10
tries" message fires identically for ENOSPC / EDQUOT / inode exhaustion as it
would for a real collision — the message names no cause. CI reproduced the
crash on a head that already carried this fix, confirming it does not touch
the real driver: ``pytest.ini`` set no ``tmp_path_retention_policy``, so
pytest's ``all`` default keeps *every* test's ``tmp_path`` — pass or fail —
alive for the whole session, and across the ~40k tests of ``make test-full``
that is enough to exhaust the runner's temp filesystem. The fix for that is
``tmp_path_retention_policy = failed`` in ``pytest.ini``, not this module.

**What this is.** A genuinely private, self-reaping basetemp per invocation,
worth keeping on its own terms regardless of #63: pytest's default puts every
run — concurrent, sequential, or SIGKILL'd — into one shared
``pytest-of-<user>`` tree that only ever shrinks through its own locked,
timeout-gated pruning; on a long-lived box that accumulates stale
``pytest-<N>`` roots, some with live ``.lock`` files, that nobody notices until
someone clears them by hand. Giving each invocation its own
``<temproot>/spec-kitty-pytest-tmp/run-<pid>`` instead:

* **Private per run** — nothing else ever creates, scans, locks, or prunes
  siblings inside that tree.
* **Wiped per run** — an explicit ``--basetemp`` is removed and recreated by
  pytest itself at first use (``TempPathFactory.getbasetemp``), so no state ever
  crosses runs even when a PID is recycled.
* **Reaped on success, retained on failure** — the controller registers an
  ``atexit`` handler that removes the run's dir only when the session finished
  with ``ExitCode.OK``; a session with failures, errors, or an interruption
  keeps its ``tmp_path`` tree for post-mortem inspection (#76 — retention is
  gated on outcome, not dropped outright: a bare reap-everything policy would
  lose exactly the forensics a failed run needs, and the private-per-run tree
  is what fixed #63, not the reap).
* **Swept for crash leftovers** — dirs older than :data:`STALE_RUN_MAX_AGE_S`
  (a SIGKILL'd run leaves one with no ``pytest_sessionfinish`` ever firing, so
  the atexit gate above never ran for it; no live suite runs this long) are
  removed at controller startup, so hard-killed runs — and retained
  failure-run trees past their forensic window — do not accumulate forever.

xdist needs no separate handling: the controller's factory resolves this
basetemp during worker setup and hands each worker ``<basetemp>/popen-gwN``
(``xdist.workermanage``), so workers nest exactly as they would under a CLI
``--basetemp``. An explicit ``--basetemp`` on the command line still wins
untouched — whoever passes one owns its lifecycle, including its persistence
(default retention does not apply to explicit basetemps).

Pass an explicit ``--basetemp`` to opt out of both the private root and the
outcome-gated reap.
"""

from __future__ import annotations

import atexit
import contextlib
import os
import shutil
import stat
import tempfile
from collections.abc import Iterable
from functools import partial
from pathlib import Path

import pytest
from _pytest.compat import get_user_id

#: Sibling of WP04's ``spec-kitty-test-homes`` under the resolved temproot —
#: a namespace this repo owns entirely, never shared with pytest's default
#: ``pytest-of-<user>`` tree or any other tool.
RUN_TMP_ROOT_NAME = "spec-kitty-pytest-tmp"

#: A run dir older than this is a crash leftover: no live suite runs this long
#: (CI's whole four-pass target is bounded well under an hour), so sweeping it
#: cannot race a concurrent healthy run.
STALE_RUN_MAX_AGE_S = 24 * 60 * 60

#: ``config`` attribute holding this run's :class:`_SessionOutcome`. Set only
#: on the controller config that :func:`install_run_basetemp` actually
#: installed a private basetemp against — absent for xdist workers and for an
#: explicit ``--basetemp`` (whoever passes one owns its own lifecycle), so
#: :func:`mark_session_outcome` is a safe no-op in both cases.
_OUTCOME_CONFIG_ATTR = "_spec_kitty_run_basetemp_outcome"


class _SessionOutcome:
    """Mutable box the atexit reaper reads at exit and ``pytest_sessionfinish``
    writes: sessionfinish always runs before atexit callbacks, so by the time
    the reaper fires this already holds the final verdict."""

    def __init__(self) -> None:
        self.succeeded = False


def mark_session_outcome(config: pytest.Config, *, succeeded: bool) -> None:
    """Tell this run's atexit reaper whether to keep or remove its tmp tree.

    Call from ``pytest_sessionfinish`` with ``succeeded=exitstatus ==
    pytest.ExitCode.OK``. A no-op if :func:`install_run_basetemp` never
    installed a reaper against *config* (xdist worker, or an explicit
    ``--basetemp``) — there is nothing to tell.
    """
    outcome = getattr(config, _OUTCOME_CONFIG_ATTR, None)
    if outcome is not None:
        outcome.succeeded = succeeded


def temproot() -> Path:
    """The temp root this scheme lives under, honoring pytest's own override.

    Same resolution order as the default branch of
    ``TempPathFactory.getbasetemp``: ``PYTEST_DEBUG_TEMPROOT`` wins, then the
    platform temp dir (which itself honors ``TMPDIR``).
    """
    return Path(os.environ.get("PYTEST_DEBUG_TEMPROOT") or tempfile.gettempdir())


def run_tmp_root() -> Path:
    """The directory holding every run's private basetemp."""
    return temproot() / RUN_TMP_ROOT_NAME


def run_basetemp_dir(pid: int | None = None) -> Path:
    """This invocation's basetemp: unique per controller process.

    The controller process IS the run (serial master or xdist controller); two
    live runs therefore never share a name. A recycled PID collides only with a
    dead run's leftover, which pytest wipes before recreating the dir anyway.
    """
    return run_tmp_root() / f"run-{pid if pid is not None else os.getpid()}"


def stale_run_dirs(
    root: Path,
    *,
    now: float,
    max_age_s: float = STALE_RUN_MAX_AGE_S,
) -> list[Path]:
    """Entries of *root* untouched for longer than *max_age_s*.

    Caller supplies the clock (``kernel.clock.now_epoch`` at the conftest call
    site) so neither this module nor its tests read wall clock directly.
    """
    cutoff = now - max_age_s
    stale: list[Path] = []
    try:
        entries = list(root.iterdir())
    except OSError:
        return stale
    for entry in entries:
        try:
            mtime = entry.stat().st_mtime
        except OSError:
            continue  # vanished between iterdir and stat — not ours to judge
        if mtime < cutoff:
            stale.append(entry)
    return stale


def remove_run_dirs(dirs: Iterable[Path]) -> list[Path]:
    """Best-effort removal of *dirs*; returns the ones THIS call removed.

    ``ignore_errors`` throughout: cleanup must never be the thing that turns a
    green run red. Inputs that are already absent are skipped — they were not
    removed by this call and are not reported.
    """
    removed: list[Path] = []
    for path in dirs:
        try:
            if not (path.exists() or path.is_symlink()):
                continue
        except OSError:
            continue  # unstattable — vanished mid-iteration, not ours to judge
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
        else:
            with contextlib.suppress(OSError):
                path.unlink()
        if not path.exists():
            removed.append(path)
    return removed


def _validate_existing_root(root: Path) -> None:
    """Apply the same owner/mode/symlink hardening pytest's own
    ``TempPathFactory.getbasetemp`` applies to its ``pytest-of-<user>``
    rootdir (:mod:`_pytest.tmpdir`) — ``root.mkdir(..., exist_ok=True)``
    accepts a pre-existing directory unchanged, so a predictable, shared
    temproot means whatever is already there (wrong owner, world-writable,
    or a symlink) would otherwise be trusted as-is (#77).

    Raises :class:`OSError` on a symlinked or wrong-owner root, matching
    pytest's fail-closed behavior. A world/group-readable root is repaired
    in place (chmod), matching pytest's own historical-permissiveness
    fixup rather than rejecting it outright.
    """
    uid = get_user_id()
    if uid is None:
        return  # platform can't tell us an owner (Windows) — nothing to check
    stat_follow_symlinks = os.stat not in os.supports_follow_symlinks
    root_stat = root.stat(follow_symlinks=stat_follow_symlinks)
    if stat.S_ISLNK(root_stat.st_mode):
        raise OSError(f"The temporary directory {root} is a symbolic link. Fix this and try again.")
    if root_stat.st_uid != uid:
        raise OSError(f"The temporary directory {root} is not owned by the current user. Fix this and try again.")
    if (root_stat.st_mode & 0o077) != 0:
        chmod_follow_symlinks = os.chmod not in os.supports_follow_symlinks
        root.chmod(root_stat.st_mode & ~0o077, follow_symlinks=chmod_follow_symlinks)


def install_run_basetemp(config: pytest.Config, now: float) -> None:
    """Point *config* at this run's private basetemp unless the user already did.

    Must run from ``pytest_configure``: the builtin tmpdir plugin snapshots
    ``config.option.basetemp`` into its ``TempPathFactory`` there, and xdist
    derives every worker's ``popen-gwN`` from the controller's factory value at
    worker setup. Controller-gated (``workerinput is None``) like the session
    reaper — an xdist worker receives its own nested basetemp over the wire and
    must not second-guess it.
    """
    if getattr(config, "workerinput", None) is not None:
        return
    if config.option.basetemp:
        return

    root = run_tmp_root()
    # pytest creates the given basetemp with a bare mkdir (no parents), so the
    # intermediate root must exist before the factory first resolves it.
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _validate_existing_root(root)
    remove_run_dirs(stale_run_dirs(root, now=now))

    basetemp = run_basetemp_dir()
    config.option.basetemp = str(basetemp)

    outcome = _SessionOutcome()
    setattr(config, _OUTCOME_CONFIG_ATTR, outcome)
    # Reap only if pytest_sessionfinish later marks the session as succeeded
    # (mark_session_outcome) — a failed/errored/interrupted session, or one
    # that crashes before sessionfinish ever runs, leaves `outcome.succeeded`
    # at its False default and keeps its tmp tree for post-mortem inspection.
    # Registered during configure — i.e. BEFORE the sessionstart handlers and
    # any service shutdown callbacks registered later — so LIFO ordering runs
    # it last, after everything that might still hold a file open under
    # tmp_path.
    atexit.register(partial(_reap_if_succeeded, basetemp, outcome))


def _reap_if_succeeded(basetemp: Path, outcome: _SessionOutcome) -> None:
    """The atexit callback :func:`install_run_basetemp` registers.

    Removes *basetemp* only when *outcome* was marked succeeded; otherwise
    leaves it for the forensic window bounded by :data:`STALE_RUN_MAX_AGE_S`.
    """
    if outcome.succeeded:
        shutil.rmtree(basetemp, ignore_errors=True)
