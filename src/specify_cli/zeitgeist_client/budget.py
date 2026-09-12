"""Wall-clock budgets: a ported process-wide hook bound, plus a new,
tighter, TOTAL per-offer bound nested inside it.

``HOOK_BUDGET_S``/``arm``/``disarm``/``NoRedirects``/``open_bounded`` are a
port of zeitgeist's ``integrations/client_budget.py`` (unchanged constant and
behaviour) — see that module's own docstring for why a per-socket-operation
timeout does not compose into a total bound, and why the fix has to live at
the process/call layer instead. Z1's hook entry points (``presence-hook``,
etc.) arm this exactly as zeitgeist's own hooks do.

``OFFER_BUDGET_S`` is new: the 750ms hard, single-offer, drop-no-retry bound
Z1-T1's criterion names, deliberately *nested inside* (not competing with)
``HOOK_BUDGET_S`` (Z1.md §3.2 item 5, decision 5) — one offer's 750ms always
finishes comfortably inside the 4s hook kill with margin for git/spool work.

``run_with_deadline`` is Z1's own primitive for enforcing that bound as a
TOTAL wall-clock deadline on one callable (typically one HTTP POST), not a
per-socket-operation timeout: it runs the callable in a daemon worker thread
and returns as soon as the deadline elapses, whichever happens first,
regardless of whether the callable is blocked on `connect`, a slow drip of
response bytes, or DNS resolution. The worker thread is intentionally
abandoned (never joined past the deadline) — daemon threads do not block
process exit, and the offer contract is "returns at 750ms", not "guarantees
the underlying socket is closed by then".
"""

from __future__ import annotations

import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from collections.abc import Callable

# The harness kills a hook at 5s (zeitgeist/integrations/client_budget.py).
# Land clearly inside it: the margin absorbs interpreter startup, import
# time, and per-call overshoot.
HOOK_BUDGET_S = 4.0

# The hard, single-offer, drop-no-retry bound (Z1-T1's own criterion word).
# Comfortably nested inside HOOK_BUDGET_S with >=1s margin for the git/spool
# work a hook does around the offer step.
OFFER_BUDGET_S = 0.75

_timer: threading.Timer | None = None


def arm(seconds: float = HOOK_BUDGET_S, stream: Any = None) -> None:
    """Guarantee this process exits 0 within ``seconds``, whatever it is
    doing. Ported unchanged from zeitgeist/integrations/client_budget.py."""

    def _expire(*_args: object) -> None:
        try:
            if stream is not None:
                stream.flush()
        except Exception:
            pass
        os._exit(0)

    global _timer
    _timer = threading.Timer(seconds, _expire)
    _timer.daemon = True
    _timer.start()

    try:
        import signal

        signal.signal(signal.SIGALRM, lambda *_a: _expire())
        signal.setitimer(signal.ITIMER_REAL, seconds + 0.25)
    except (ImportError, AttributeError, ValueError):
        pass


def disarm() -> None:
    """Cancel the bound. Ported unchanged from zeitgeist's client_budget.py."""
    global _timer
    if _timer is not None:
        _timer.cancel()
        _timer = None
    try:
        import signal

        signal.setitimer(signal.ITIMER_REAL, 0)
    except (ImportError, AttributeError, ValueError):
        pass


class NoRedirects:
    """An opener that refuses redirects. Ported unchanged from zeitgeist's
    client_budget.py: nothing Z1 talks to legitimately redirects."""

    @staticmethod
    def build() -> Any:
        import urllib.request

        class _Blocked(urllib.request.HTTPRedirectHandler):
            # Overrides HTTPRedirectHandler.redirect_request, which urllib
            # calls positionally — the leading underscores are the ARG002
            # convention for "part of a required base-class signature, never
            # read", not a rename hazard.
            def redirect_request(
                self,
                _req: Any,
                _fp: Any,
                _code: Any,
                _msg: Any,
                _headers: Any,
                _newurl: Any,
            ) -> None:
                return None

        return urllib.request.build_opener(_Blocked)


def open_bounded(req: Any, timeout: float) -> Any:
    """``urlopen`` with redirects refused. NOT a total bound by itself — see
    module docstring; the total bound is ``run_with_deadline``."""
    return NoRedirects.build().open(req, timeout=timeout)


def bound_stdout(seconds: float = HOOK_BUDGET_S) -> None:
    """``arm()`` for a hook whose output goes to stdout."""
    arm(seconds, stream=sys.stdout)


T = TypeVar("T")


@dataclass(frozen=True)
class DeadlineOutcome(Generic[T]):
    completed: bool
    result: T | None
    error: BaseException | None
    elapsed_s: float


def run_with_deadline(fn: Callable[[], T], *, deadline_s: float) -> DeadlineOutcome[T]:
    """Run ``fn()`` in a daemon worker thread; return within ``deadline_s``
    wall-clock TOTAL, regardless of what ``fn`` is internally blocked on.

    If the worker has not finished by the deadline, returns immediately with
    ``completed=False`` and abandons the worker (daemon thread — it will not
    block process exit, and any eventual result it produces is discarded).
    """
    box: list[tuple[str, Any]] = []

    def _run() -> None:
        try:
            box.append(("ok", fn()))
        except BaseException as exc:  # noqa: BLE001 - propagated to the caller, not swallowed
            box.append(("error", exc))

    worker = threading.Thread(target=_run, daemon=True)
    start = time.monotonic()
    worker.start()
    worker.join(deadline_s)
    elapsed = time.monotonic() - start

    if worker.is_alive() or not box:
        return DeadlineOutcome(completed=False, result=None, error=None, elapsed_s=elapsed)

    kind, payload = box[0]
    if kind == "error":
        return DeadlineOutcome(completed=True, result=None, error=payload, elapsed_s=elapsed)
    return DeadlineOutcome(completed=True, result=payload, error=None, elapsed_s=elapsed)
