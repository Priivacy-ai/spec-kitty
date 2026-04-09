"""Tests for ``specify_cli.auth.secure_storage.file_fallback`` (feature 080, WP01 T006).

Critical coverage (per decision D-8 / constraint C-011):

- Scrypt KDF with random 16-byte salt stored at 0600.
- AES-256-GCM round-trip.
- v1 plaintext format is rejected with a clear error.
- Tampered ciphertext fails authentication → ``StorageDecryptionError``.
- Wrong salt → decryption fails (simulates a machine/UID mismatch).
- Concurrent writes coordinated by the FileLock (no corruption).
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import stat
from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest

from specify_cli.auth.errors import StorageDecryptionError
from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage
from specify_cli.auth.session import StoredSession, Team


def _now() -> datetime:
    return datetime.now(UTC)


def _make_session(access_token: str = "access") -> StoredSession:
    now = _now()
    return StoredSession(
        user_id="user-1",
        email="a@b.com",
        name="A B",
        teams=[Team(id="t1", name="T1", role="owner")],
        default_team_id="t1",
        access_token=access_token,
        refresh_token="refresh",
        session_id="sess",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=None,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


class FastFileFallback(FileFallbackStorage):
    """Subclass with a lower scrypt cost to keep test suite runtime reasonable."""

    _scrypt_n = 2**10
    _scrypt_r = 8
    _scrypt_p = 1


@pytest.fixture
def storage(tmp_path: Path) -> FastFileFallback:
    return FastFileFallback(base_dir=tmp_path)


def test_read_returns_none_when_no_file(storage: FastFileFallback):
    assert storage.read() is None


def test_roundtrip_write_read(storage: FastFileFallback):
    s = _make_session()
    storage.write(s)
    loaded = storage.read()
    assert loaded == s


def test_write_creates_salt_file_with_0600(storage: FastFileFallback, tmp_path: Path):
    storage.write(_make_session())
    salt_file = tmp_path / "credentials.salt"
    assert salt_file.exists()
    # Check permissions (POSIX only). Windows skips this.
    if hasattr(os, "getuid"):
        mode = stat.S_IMODE(salt_file.stat().st_mode)
        assert mode == 0o600
    assert len(salt_file.read_bytes()) == 16


def test_write_creates_credentials_file_with_0600(
    storage: FastFileFallback, tmp_path: Path
):
    storage.write(_make_session())
    cred_file = tmp_path / "credentials.json"
    assert cred_file.exists()
    if hasattr(os, "getuid"):
        mode = stat.S_IMODE(cred_file.stat().st_mode)
        assert mode == 0o600


def test_credentials_dir_created_with_0700(storage: FastFileFallback, tmp_path: Path):
    sub = tmp_path / "new-subdir"
    storage = FastFileFallback(base_dir=sub)
    storage.write(_make_session())
    assert sub.exists()
    if hasattr(os, "getuid"):
        mode = stat.S_IMODE(sub.stat().st_mode)
        assert mode == 0o700


def test_salt_is_random_across_instances(tmp_path: Path):
    # Two fresh storages in different dirs should produce different salts.
    s1 = FastFileFallback(base_dir=tmp_path / "a")
    s2 = FastFileFallback(base_dir=tmp_path / "b")
    s1.write(_make_session())
    s2.write(_make_session())
    salt1 = (tmp_path / "a" / "credentials.salt").read_bytes()
    salt2 = (tmp_path / "b" / "credentials.salt").read_bytes()
    assert salt1 != salt2


def test_encrypted_file_does_not_contain_plaintext(
    storage: FastFileFallback, tmp_path: Path
):
    s = _make_session(access_token="SUPER_SECRET_TOKEN_VALUE")
    storage.write(s)
    raw_bytes = (tmp_path / "credentials.json").read_bytes()
    # The access token must not appear in the on-disk bytes.
    assert b"SUPER_SECRET_TOKEN_VALUE" not in raw_bytes


def test_file_format_is_version_2(storage: FastFileFallback, tmp_path: Path):
    storage.write(_make_session())
    blob = json.loads((tmp_path / "credentials.json").read_text())
    assert blob["version"] == 2
    assert "nonce" in blob
    assert "ciphertext" in blob


def test_v1_plaintext_is_rejected(storage: FastFileFallback, tmp_path: Path):
    # Simulate a stale v1 file.
    (tmp_path).mkdir(parents=True, exist_ok=True)
    (tmp_path / "credentials.json").write_text(
        json.dumps({"version": 1, "user_id": "old"})
    )
    with pytest.raises(StorageDecryptionError) as excinfo:
        storage.read()
    assert "v1" in str(excinfo.value) or "version" in str(excinfo.value).lower()


def test_missing_salt_rejects_decryption(
    storage: FastFileFallback, tmp_path: Path
):
    storage.write(_make_session())
    (tmp_path / "credentials.salt").unlink()
    with pytest.raises(StorageDecryptionError):
        storage.read()


def test_tampered_ciphertext_fails_authentication(
    storage: FastFileFallback, tmp_path: Path
):
    storage.write(_make_session())
    cred_file = tmp_path / "credentials.json"
    blob = json.loads(cred_file.read_text())
    # Flip a byte of the ciphertext hex to break the AES-GCM tag.
    ct = bytearray(bytes.fromhex(blob["ciphertext"]))
    ct[0] ^= 0xFF
    blob["ciphertext"] = bytes(ct).hex()
    cred_file.write_text(json.dumps(blob))
    with pytest.raises(StorageDecryptionError):
        storage.read()


def test_wrong_salt_fails_decryption(
    storage: FastFileFallback, tmp_path: Path
):
    """Simulate the scenario where the salt file was replaced (e.g. user moved machine).

    The ciphertext was encrypted with the original salt-derived key; rotating
    the salt changes the derived key and AES-GCM authentication fails.
    """
    storage.write(_make_session())
    salt_file = tmp_path / "credentials.salt"
    # Replace with a brand-new random 16-byte salt.
    import secrets

    salt_file.write_bytes(secrets.token_bytes(16))
    with pytest.raises(StorageDecryptionError):
        storage.read()


def test_malformed_json_raises_decryption_error(
    storage: FastFileFallback, tmp_path: Path
):
    (tmp_path).mkdir(parents=True, exist_ok=True)
    (tmp_path / "credentials.json").write_text("{not-json")
    with pytest.raises(StorageDecryptionError):
        storage.read()


def test_delete_removes_cred_and_salt(
    storage: FastFileFallback, tmp_path: Path
):
    storage.write(_make_session())
    assert (tmp_path / "credentials.json").exists()
    assert (tmp_path / "credentials.salt").exists()
    storage.delete()
    assert not (tmp_path / "credentials.json").exists()
    assert not (tmp_path / "credentials.salt").exists()


def test_delete_is_idempotent(storage: FastFileFallback):
    storage.delete()
    storage.delete()


def test_concurrent_writes_do_not_corrupt(tmp_path: Path):
    """FileLock must serialize writes so the last one wins and the file stays valid."""
    storage = FastFileFallback(base_dir=tmp_path)
    # Pre-create so all workers reuse the same salt.
    storage.write(_make_session())

    def writer(i: int) -> None:
        worker = FastFileFallback(base_dir=tmp_path)
        worker.write(_make_session(access_token=f"token-{i}"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(writer, range(16)))

    loaded = storage.read()
    assert loaded is not None
    # The final access_token must match one of the worker tokens.
    assert loaded.access_token.startswith("token-")


def test_backend_name_is_file(storage: FastFileFallback):
    assert storage.backend_name == "file"


def test_rewrite_reuses_existing_salt(
    storage: FastFileFallback, tmp_path: Path
):
    storage.write(_make_session())
    salt_before = (tmp_path / "credentials.salt").read_bytes()
    storage.write(_make_session(access_token="different"))
    salt_after = (tmp_path / "credentials.salt").read_bytes()
    assert salt_before == salt_after
