"""Cross-platform process liveness — the single canonical is-alive check (C-002).

Promoted from ``sync/daemon._is_process_alive`` so ``core`` and ``lanes`` can consult
process liveness without depending on the daemon's socket/HTTPServer machinery
(layering — do not import this from ``sync``). Never raises: NFR-004 requires a
conservative "not provably alive" (False) or "cannot prove dead" (True, AccessDenied)
result for every input, including absent, unparseable, dead, or recycled PIDs.
"""

from __future__ import annotations

import psutil


def is_process_alive(pid: int) -> bool:
    """Return whether ``pid`` is a currently-running process.

    Conservative and NFR-004-safe: never raises.

    - ``psutil.NoSuchProcess`` (the PID does not exist / has exited) -> ``False``.
    - ``psutil.AccessDenied`` (the PID exists but permissions block inspection) ->
      ``True`` — we cannot prove the process is dead, so we conservatively treat it
      as alive.
    - Any other unexpected exception -> ``False``.
    """
    try:
        proc = psutil.Process(pid)
        return bool(proc.is_running())
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        return True
    except Exception:
        return False
