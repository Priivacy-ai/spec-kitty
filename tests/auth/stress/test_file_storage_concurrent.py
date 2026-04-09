"""Stress test for :class:`FileFallbackStorage` atomicity (WP11 T062).

Concurrently issues many writes and reads against the encrypted file
fallback backend and asserts that:

1. No write produces a corrupted file (every subsequent ``read()``
   returns a valid :class:`StoredSession`, not ``None`` due to a
   half-written JSON blob).
2. The final state is a well-formed session from one of the writers
   (last-writer-wins semantics — not a blended/torn record).
3. No :class:`Exception` escapes from the concurrent workers.

Implementation notes:

- Uses a tmp_path-scoped ``FileFallbackStorage`` so no production
  ``~/.config/spec-kitty`` directory is touched.
- Subclasses the production storage to drop the scrypt cost parameters
  to the floor (``N=2**10``) so 20+ encrypt operations complete in
  under a second. This is ONLY a test-speed hack — the file format,
  locking, and atomic-rename semantics are identical to production.
- Uses ``ThreadPoolExecutor`` rather than asyncio because the real
  atomic-write contract is defended by :class:`filelock.FileLock`
  (a thread-level lock), and that is exactly what we want to stress.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, UTC
from pathlib import Path

from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage
from specify_cli.auth.session import StoredSession, Team


class _FastFileFallbackStorage(FileFallbackStorage):
    """Production backend with reduced scrypt cost for fast stress tests.

    Keeps the same file format, locking semantics, and atomic-rename path.
    Only the KDF cost parameters change, so a regression that breaks the
    atomic-write contract will still surface here.
    """

    _scrypt_n = 2**10  # 1024 — test only; production is 2**14
    _scrypt_r = 8
    _scrypt_p = 1


def _make_session(i: int) -> StoredSession:
    """Return a distinct StoredSession tagged with the writer index ``i``."""
    now = datetime.now(UTC)
    return StoredSession(
        user_id=f"u_writer_{i}",
        email=f"writer{i}@example.com",
        name=f"Writer {i}",
        teams=[Team(id="tm_stress", name="Stress Team", role="admin")],
        default_team_id="tm_stress",
        access_token=f"at_writer_{i}",
        refresh_token=f"rt_writer_{i}",
        session_id=f"sess_writer_{i}",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=now + timedelta(days=89),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def test_concurrent_writes_never_corrupt_file(tmp_path: Path) -> None:
    """20 threads concurrently writing → final file is a valid session.

    The central invariant is that :class:`filelock.FileLock` serializes
    every write, and each write is committed via ``tmp.replace(final)``.
    Therefore, no matter how the interleaving plays out, a subsequent
    ``read()`` must always return a well-formed StoredSession (one of
    the 20 writers won).

    NOTE: We seed the salt file via an initial serial write before
    firing the concurrent writers. This mirrors the real CLI flow
    where the first ``auth login`` is always serial and creates the
    salt; subsequent refreshes/writes then race safely against the
    FileLock-protected write path.
    """
    storage = _FastFileFallbackStorage(base_dir=tmp_path)
    # Seed the salt/credentials file with a serial write so concurrent
    # writers share a stable salt.
    storage.write(_make_session(-1))

    errors: list[Exception] = []
    errors_lock = threading.Lock()

    def _writer(i: int) -> None:
        try:
            storage.write(_make_session(i))
        except Exception as exc:  # pragma: no cover - captured below
            with errors_lock:
                errors.append(exc)

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(_writer, i) for i in range(20)]
        for future in as_completed(futures):
            future.result()

    # No exceptions escaped from the writers.
    assert not errors, f"writers raised {len(errors)} exception(s): {errors[:3]}"

    # Final file is a valid, decryptable session from ONE of the writers.
    final = storage.read()
    assert final is not None, "read() returned None after concurrent writes"
    assert final.email.startswith("writer")
    assert final.email.endswith("@example.com")
    winner_idx = int(final.email.removeprefix("writer").removesuffix("@example.com"))
    assert 0 <= winner_idx < 20

    # Session fields are consistent (no blending / torn record).
    assert final.user_id == f"u_writer_{winner_idx}"
    assert final.access_token == f"at_writer_{winner_idx}"
    assert final.refresh_token == f"rt_writer_{winner_idx}"
    assert final.session_id == f"sess_writer_{winner_idx}"


def test_interleaved_reads_and_writes_never_see_corruption(tmp_path: Path) -> None:
    """Interleave 10 writers with 10 readers; no reader must ever see corruption.

    The reader may legitimately see ``None`` (before the first write lands)
    or any valid session from one of the writers, but it must NEVER:

    - raise a decryption / JSON-decode error,
    - return a session with inconsistent fields.
    """
    storage = _FastFileFallbackStorage(base_dir=tmp_path)

    # Prime the file so readers never see ``None`` legitimately. This
    # also seeds the salt, so the concurrent writers below all share
    # one stable KDF salt (matches the real CLI lifecycle).
    storage.write(_make_session(0))

    errors: list[Exception] = []
    errors_lock = threading.Lock()
    read_results: list[StoredSession] = []
    reads_lock = threading.Lock()

    def _writer(i: int) -> None:
        try:
            storage.write(_make_session(i))
        except Exception as exc:
            with errors_lock:
                errors.append(exc)

    def _reader() -> None:
        try:
            for _ in range(5):
                session = storage.read()
                if session is not None:
                    with reads_lock:
                        read_results.append(session)
        except Exception as exc:
            with errors_lock:
                errors.append(exc)

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = []
        for i in range(10):
            futures.append(pool.submit(_writer, i))
            futures.append(pool.submit(_reader))
        for future in as_completed(futures):
            future.result()

    assert not errors, (
        f"concurrent reads/writes produced {len(errors)} exceptions: {errors[:3]}"
    )
    # Every observed read is a well-formed session from one of the writers.
    for session in read_results:
        assert session.email.startswith("writer")
        winner = int(
            session.email.removeprefix("writer").removesuffix("@example.com")
        )
        assert 0 <= winner < 10
        # Fields are consistent — no torn records.
        assert session.user_id == f"u_writer_{winner}"
        assert session.access_token == f"at_writer_{winner}"
        assert session.refresh_token == f"rt_writer_{winner}"


def test_file_permissions_are_0600_after_concurrent_writes(tmp_path: Path) -> None:
    """After any write, the credentials file must have mode 0600.

    Covers FR-006 / constraint C-011: file fallback must never be
    world-readable. This is the last-ditch defense against a hostile
    local user reading tokens off disk.
    """
    storage = _FastFileFallbackStorage(base_dir=tmp_path)
    # Seed salt via a serial write (matches the real CLI login lifecycle).
    storage.write(_make_session(-1))

    with ThreadPoolExecutor(max_workers=10) as pool:
        list(
            as_completed(
                [pool.submit(storage.write, _make_session(i)) for i in range(10)]
            )
        )

    cred_file = tmp_path / "credentials.json"
    assert cred_file.exists()
    # POSIX permission check. On Windows os.getuid() is absent but
    # the test suite only runs on POSIX CI so this is safe.
    mode = cred_file.stat().st_mode & 0o777
    assert mode == 0o600, f"credentials.json has mode {oct(mode)}, expected 0o600"

    # Salt file is also locked down.
    salt_file = tmp_path / "credentials.salt"
    salt_mode = salt_file.stat().st_mode & 0o777
    assert salt_mode == 0o600, (
        f"credentials.salt has mode {oct(salt_mode)}, expected 0o600"
    )


def test_sequential_login_logout_login_cycle_under_concurrent_writes(
    tmp_path: Path,
) -> None:
    """Mirrors a realistic login → logout → login cycle under write load.

    Production serializes logout (delete) against writes at the CLI level:
    one process owns the terminal and runs the flow to completion. This
    test therefore runs the logout phase between two waves of concurrent
    writes, matching how the CLI actually behaves.

    The contract under test is that each cycle leaves the file in a
    consistent state — either a well-formed session or cleanly deleted.
    """
    storage = _FastFileFallbackStorage(base_dir=tmp_path)
    # Seed salt via serial write.
    storage.write(_make_session(-1))

    errors: list[Exception] = []
    errors_lock = threading.Lock()

    def _writer(i: int) -> None:
        try:
            storage.write(_make_session(i))
        except Exception as exc:
            with errors_lock:
                errors.append(exc)

    # Phase 1: 10 concurrent writers → exactly one wins.
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_writer, i) for i in range(10)]
        for future in as_completed(futures):
            future.result()
    assert not errors, f"phase 1 writers raised: {errors[:3]}"
    assert storage.read() is not None

    # Phase 2: logout (delete). Must leave the file absent.
    storage.delete()
    assert storage.read() is None

    # Phase 3: concurrent re-login writers, starting from a clean slate.
    # Re-seed the salt with a serial write, mirroring how the real CLI
    # re-runs ``spec-kitty auth login`` after a logout.
    storage.write(_make_session(99))
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_writer, i + 100) for i in range(10)]
        for future in as_completed(futures):
            future.result()
    assert not errors, f"phase 3 writers raised: {errors[:3]}"

    # Final read returns a valid session from the second wave.
    final = storage.read()
    assert final is not None
    assert final.email.startswith("writer")
    winner = int(final.email.removeprefix("writer").removesuffix("@example.com"))
    assert 100 <= winner < 110, f"unexpected winner index {winner}"
    assert final.user_id == f"u_writer_{winner}"
