"""Per-run pytest temp root (#63) — keep every pytest run out of the shared
``pytest-of-<user>`` numbered-dir tree.

**The failure this closes.** Every ``make test-full`` run of main crashed before
a pytest summary with ``OSError: could not create numbered dir with prefix
test_* in <temproot>/pytest-of-exedev/pytest-0/popen-gw<N> after 10 tries``, on a
different set of xdist workers each run (#63). pytest's default temp layout puts
ALL runs — concurrent or sequential, healthy or killed — inside one shared
``pytest-of-<user>`` tree, where :func:`_pytest.pathlib.make_numbered_dir` and
its cleanup wrapper scan sibling dirs, take symlink locks with a 3-day timeout,
and prune old roots while other processes may still be creating numbered dirs in
the same parents. Ten blind ``mkdir`` retries against that shared state fail
whenever another run's prune/lock/delete races the retry loop (or the tree has
accumulated stale locks from a SIGKILL'd run), and the OSError escapes fixture
setup as a pre-summary crash: zero pass/fail data from the whole run.

**The fix.** Give each pytest invocation its own private, uniquely-named
basetemp under ``<temproot>/spec-kitty-pytest-tmp/run-<pid>``:

* **Private per run** — nothing else ever creates, scans, locks, or prunes
  siblings inside that tree, so the numbered-dir retry loop races nobody.
* **Wiped per run** — an explicit ``--basetemp`` is removed and recreated by
  pytest itself at first use (``TempPathFactory.getbasetemp``), so no state ever
  crosses runs even when a PID is recycled.
* **Reaped per run** — the controller registers an ``atexit`` handler removing
  the run's dir, so a healthy run leaves nothing behind.
* **Swept for crash leftovers** — dirs older than :data:`STALE_RUN_MAX_AGE_S`
  (only a SIGKILL'd run can leave one; no live suite runs that long) are removed
  at controller startup, so hard-killed runs do not accumulate.

xdist needs no separate handling: the controller's factory resolves this
basetemp during worker setup and hands each worker ``<basetemp>/popen-gwN``
(``xdist.workermanage``), so workers nest exactly as they would under a CLI
``--basetemp``. An explicit ``--basetemp`` on the command line still wins
untouched — whoever passes one owns its lifecycle, including its persistence
(default retention does not apply to explicit basetemps).

The trade-off is deliberate: because the reaper removes the run dir at exit, a
run's ``tmp_path`` contents are NOT retained for post-mortem inspection the way
pytest's default 3-session retention retains them. Pass an explicit
``--basetemp`` to opt out of both the private root and the reap.
"""

from __future__ import annotations

import atexit
import contextlib
import os
import shutil
import tempfile
from collections.abc import Iterable
from functools import partial
from pathlib import Path

import pytest

#: Sibling of WP04's ``spec-kitty-test-homes`` under the resolved temproot —
#: a namespace this repo owns entirely, never shared with pytest's default
#: ``pytest-of-<user>`` tree or any other tool.
RUN_TMP_ROOT_NAME = "spec-kitty-pytest-tmp"

#: A run dir older than this is a crash leftover: no live suite runs this long
#: (CI's whole four-pass target is bounded well under an hour), so sweeping it
#: cannot race a concurrent healthy run.
STALE_RUN_MAX_AGE_S = 24 * 60 * 60


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
    remove_run_dirs(stale_run_dirs(root, now=now))

    basetemp = run_basetemp_dir()
    config.option.basetemp = str(basetemp)
    # Reap after the session regardless of outcome. Registered during configure
    # — i.e. BEFORE the sessionstart handlers and any service shutdown callbacks
    # registered later — so LIFO ordering runs it last, after everything that
    # might still hold a file open under tmp_path.
    atexit.register(partial(shutil.rmtree, basetemp, ignore_errors=True))
