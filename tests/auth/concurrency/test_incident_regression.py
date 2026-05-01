"""Multiprocess regression test for the rotate-then-stale-grant incident.

This is the verification spine of mission
``cli-session-survival-daemon-singleton-01KQ9M3M``: two real Python
subprocesses (each acting as an independent CLI invocation in a temp
checkout) drive the rotate-then-stale-grant ordering against a fake
refresh server bound to ``127.0.0.1``. The bug was that worker B would
silently delete the freshly persisted session on receiving
``invalid_grant`` for its stale-in-memory refresh token; the fix is in
WP02's :func:`run_refresh_transaction`. This test asserts the deployment
shape is correct end-to-end.

NFR-005 ceiling: the entire test must finish in under 30 s. We enforce
that with a hard ``wait_for(timeout=30.0)`` per worker join.

Skipped on Windows: subprocess + file-barrier ordering is portable in
principle, but :class:`MachineFileLock`'s POSIX path uses ``fcntl.flock``;
the Windows code path is covered by the WP01 platform test.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import threading
import time
from datetime import datetime, timedelta, UTC
from http.server import HTTPServer
from pathlib import Path

import pytest

from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage
from specify_cli.auth.session import StoredSession, Team

from .conftest import _build_handler_class


pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason=("Subprocess + file-barrier ordering is exercised on POSIX; Windows lock semantics are covered by the WP01 platform test."),
)


# ---------------------------------------------------------------------------
# Worker scripts (executed via ``python -c``)
# ---------------------------------------------------------------------------

# Worker A: waits for B to be loaded, then refreshes (rotates v1 -> v2),
# then signals "rotated", then exits.
_WORKER_A_SCRIPT = textwrap.dedent(
    """
    from __future__ import annotations
    import asyncio
    import os
    import sys
    import time
    from pathlib import Path

    BARRIER_DIR = Path(os.environ["BARRIER_DIR"])
    B_LOADED = BARRIER_DIR / "b_loaded.flag"
    ROTATED = BARRIER_DIR / "rotated.flag"

    # Wait until B has loaded its TokenManager (and therefore captured the
    # pre-rotation refresh token in memory). Bounded poll — the orchestrator
    # enforces an outer 30 s ceiling.
    deadline = time.monotonic() + 25.0
    while not B_LOADED.exists():
        if time.monotonic() > deadline:
            print("worker-a: timed out waiting for b_loaded.flag", file=sys.stderr)
            sys.exit(2)
        time.sleep(0.05)

    from specify_cli.auth import get_token_manager, reset_token_manager
    reset_token_manager()
    tm = get_token_manager()
    sess = tm.get_current_session()
    if sess is None:
        print("worker-a: no session loaded", file=sys.stderr)
        sys.exit(3)

    async def _go() -> None:
        await tm.refresh_if_needed()

    asyncio.run(_go())

    after = tm.get_current_session()
    if after is None or after.refresh_token != "rt_rotated_v2":
        print(
            f"worker-a: expected rotated rt_rotated_v2, got {after}",
            file=sys.stderr,
        )
        sys.exit(4)

    ROTATED.touch()
    sys.exit(0)
    """
).strip()


# Worker B: loads its TokenManager (capturing the pre-rotation refresh
# token in memory), signals b_loaded, waits for rotated, then attempts a
# refresh. The stale token will be rejected by the fake server; the WP02
# reconciler must preserve the on-disk rotated session and adopt it as
# the new in-memory state. Exit 0 if the in-memory session and the
# on-disk session both reflect the rotated material; exit 1 otherwise.
_WORKER_B_SCRIPT = textwrap.dedent(
    """
    from __future__ import annotations
    import asyncio
    import os
    import sys
    import time
    from pathlib import Path

    BARRIER_DIR = Path(os.environ["BARRIER_DIR"])
    B_LOADED = BARRIER_DIR / "b_loaded.flag"
    ROTATED = BARRIER_DIR / "rotated.flag"

    from specify_cli.auth import get_token_manager, reset_token_manager
    reset_token_manager()
    tm = get_token_manager()
    sess = tm.get_current_session()
    if sess is None:
        print("worker-b: no session loaded", file=sys.stderr)
        sys.exit(3)
    if sess.refresh_token != "rt_seed_v1":
        print(
            f"worker-b: expected pre-rotation rt_seed_v1, got {sess.refresh_token}",
            file=sys.stderr,
        )
        sys.exit(4)

    # Signal that B has captured the pre-rotation token in memory.
    B_LOADED.touch()

    # Wait for A to complete its rotation.
    deadline = time.monotonic() + 25.0
    while not ROTATED.exists():
        if time.monotonic() > deadline:
            print("worker-b: timed out waiting for rotated.flag", file=sys.stderr)
            sys.exit(2)
        time.sleep(0.05)

    async def _go() -> None:
        await tm.refresh_if_needed()

    asyncio.run(_go())

    after = tm.get_current_session()
    if after is None:
        print(
            "worker-b: session was cleared on stale-grant rejection (FR-006 regression)",
            file=sys.stderr,
        )
        sys.exit(1)
    if after.refresh_token != "rt_rotated_v2":
        print(
            f"worker-b: expected rt_rotated_v2 after stale-grant reconcile, got {after.refresh_token}",
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(0)
    """
).strip()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed_disk_session(home_dir: Path) -> StoredSession:
    """Persist an expired starter session under ``home_dir/.spec-kitty/auth``."""
    auth_dir = home_dir / ".spec-kitty" / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    session = StoredSession(
        user_id="user_seed",
        email="seed@example.com",
        name="Seed User",
        teams=[Team(id="t-seed", name="T", role="owner")],
        default_team_id="t-seed",
        access_token="at_seed_v1",
        refresh_token="rt_seed_v1",
        session_id="sess_seed",
        issued_at=now - timedelta(seconds=900),
        # Already expired so refresh_if_needed will fire in both workers.
        access_token_expires_at=now - timedelta(seconds=1),
        refresh_token_expires_at=now + timedelta(days=30),
        scope="openid offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )
    storage = FileFallbackStorage(base_dir=auth_dir)
    storage.write(session)
    return session


# ---------------------------------------------------------------------------
# The headline test
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_incident_regression_two_subprocess_workers(
    tmp_path: Path,
) -> None:
    """SC-002: rotate-then-stale-grant survives across two CLI processes.

    Orchestration:

    1. Build an HTTP fake-refresh server on ``127.0.0.1:0``.
    2. Seed an expired session under ``tmp_path/.spec-kitty/auth``.
    3. Spawn worker A and worker B with ``HOME=tmp_path`` and
       ``SPEC_KITTY_SAAS_URL`` pointing at the fake server.
    4. Worker B captures the pre-rotation token and signals ``b_loaded``.
    5. Worker A refreshes (rotation, server hit #1), signals ``rotated``,
       exits 0.
    6. Worker B enters ``run_refresh_transaction`` holding the stale
       in-memory token. Inside the machine-wide lock the transaction
       reloads the persisted material (now rotated by A), takes the
       :attr:`RefreshOutcome.ADOPTED_NEWER` fast path (FR-004), adopts
       A's rotated session WITHOUT a network call, and exits 0.
    7. The orchestrator asserts both exits are 0, the on-disk session
       still exists and reflects the rotated material, and the server
       saw exactly one request (A's rotation).

    The original pre-WP02 incident was that worker B, on receiving
    ``invalid_grant`` for its stale in-memory token, would clear the
    freshly persisted session. WP02's read-decide-refresh-reconcile
    sequence eliminates the unsafe path on two fronts: the fast-path
    adoption (FR-004) skips the network call entirely when persisted
    material is newer-and-valid, and the post-rejection reconciler
    (FR-006) preserves the persisted session whenever a rejection
    arrives against material that has since been rotated by another
    process. This test pins the FR-004 fast path; the FR-006 reconciler
    branch is verified deterministically by
    :mod:`tests.auth.concurrency.test_stale_grant_preservation`.

    NFR-005: the whole sequence must complete within 30 s.
    """
    # --- Fake refresh server ------------------------------------------------
    counter_path = tmp_path / "refresh_counter.bin"
    counter_path.write_bytes(b"")
    handler_cls = _build_handler_class(
        counter_path=counter_path,
        seed_refresh_token="rt_seed_v1",
        rotated_refresh_token="rt_rotated_v2",
        rotated_session_id="sess_seed",
    )
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _host_raw, _port = server.server_address[0], server.server_address[1]
    _host = _host_raw.decode() if isinstance(_host_raw, bytes) else _host_raw
    server_url = f"http://{_host}:{_port}"

    try:
        # --- Seed the on-disk session --------------------------------------
        _seed_disk_session(tmp_path)
        barrier_dir = tmp_path / "barriers"
        barrier_dir.mkdir(parents=True, exist_ok=True)

        # --- Build the subprocess environment ------------------------------
        # Bringing in the parent's PYTHONPATH ensures the workers can
        # import ``specify_cli`` even when this test runs from a checkout
        # without an editable install on ``sys.path``.
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        env["SPEC_KITTY_SAAS_URL"] = server_url
        env["BARRIER_DIR"] = str(barrier_dir)
        # Suppress accidental SaaS sync; tests must not touch real SaaS.
        env.pop("SPEC_KITTY_ENABLE_SAAS_SYNC", None)
        # Make sure subprocesses can find ``specify_cli`` even when this
        # test runs from a non-editable checkout. Inheriting sys.path
        # via PYTHONPATH is the standard contract.
        env["PYTHONPATH"] = os.pathsep.join([p for p in sys.path if p])

        # --- Spawn both workers --------------------------------------------
        proc_a = subprocess.Popen(
            [sys.executable, "-c", _WORKER_A_SCRIPT],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc_b = subprocess.Popen(
            [sys.executable, "-c", _WORKER_B_SCRIPT],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # --- Bounded join (NFR-005) ----------------------------------------
        deadline = time.monotonic() + 30.0
        for proc in (proc_a, proc_b):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                proc.kill()
                proc.wait(timeout=2.0)
                pytest.fail("NFR-005: subprocess regression exceeded the 30 s ceiling")
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
                pytest.fail("NFR-005: subprocess regression exceeded the 30 s ceiling")

        # --- Assertions ----------------------------------------------------
        out_a, err_a = proc_a.communicate(timeout=5.0)
        out_b, err_b = proc_b.communicate(timeout=5.0)
        assert proc_a.returncode == 0, f"worker-a exit={proc_a.returncode}\nstdout={out_a!r}\nstderr={err_a!r}"
        assert proc_b.returncode == 0, f"worker-b exit={proc_b.returncode} (non-zero indicates FR-006 regression)\nstdout={out_b!r}\nstderr={err_b!r}"

        # WP02's FR-004 fast path adopts the rotated material without a
        # second network call; the fake server therefore sees exactly
        # one POST /oauth/token (worker A's rotation). A regression that
        # bypassed the lock or skipped the read-decide step would surface
        # here as a count of 2 (worker B unnecessarily contacting the
        # server with the persisted token).
        request_count = counter_path.stat().st_size
        assert request_count == 1, f"Expected exactly 1 fake-refresh request (worker A's rotation; worker B should adopt via FR-004), saw {request_count}"

        # The on-disk session must still exist and contain the rotated
        # material — this is the FR-006 invariant the bug violated.
        on_disk = FileFallbackStorage(base_dir=tmp_path / ".spec-kitty" / "auth").read()
        assert on_disk is not None, "FR-006 regression: on-disk session was deleted by worker-b"
        assert on_disk.refresh_token == "rt_rotated_v2"
        assert on_disk.session_id == "sess_seed"
        # Sanity: the persisted access token reflects the rotation, not
        # the seed — proves the storage write happened in worker-a.
        assert on_disk.access_token.startswith("at_rotated_")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
