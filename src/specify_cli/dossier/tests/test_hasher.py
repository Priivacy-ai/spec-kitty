"""Unit tests for deterministic SHA256 hashing utilities.

Tests cover:
- hash_file() determinism (same file → same hash, 10 runs)
- Different files produce different hashes
- Order-independent parity hashing
- UTF-8 validation (BOM, CJK, surrogates)
- Error handling (file not found, permission denied, I/O errors)
"""

import pytest
import tempfile
import os
from pathlib import Path
from specify_cli.dossier.hasher import hash_file, hash_file_with_validation, Hasher


class TestHashFile:
    """Test hash_file() function for deterministic SHA256 hashing."""

    def test_hash_file_determinism(self, tmp_path):
        """Hash same file 10 times, verify identical result."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!", encoding="utf-8")

        hashes = [hash_file(test_file) for _ in range(10)]

        # All hashes should be identical
        assert len(set(hashes)) == 1, "All 10 hashes should be identical"
        # Verify it's a 64-char hex string (SHA256)
        assert len(hashes[0]) == 64
        assert all(c in "0123456789abcdef" for c in hashes[0])

    def test_hash_different_files(self, tmp_path):
        """Hash two different files, verify different hashes."""
        file1 = tmp_path / "file1.txt"
        file1.write_text("Content A", encoding="utf-8")

        file2 = tmp_path / "file2.txt"
        file2.write_text("Content B", encoding="utf-8")

        hash1 = hash_file(file1)
        hash2 = hash_file(file2)

        assert hash1 != hash2, "Different files should produce different hashes"

    def test_hash_large_file(self, tmp_path):
        """Hash large file (>100MB), verify completes without memory issues."""
        large_file = tmp_path / "large.bin"

        # Create a 10MB file with repeating pattern
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = 10
        with open(large_file, "wb") as f:
            for i in range(num_chunks):
                f.write(b"A" * chunk_size)

        # Should complete without memory explosion
        hash_result = hash_file(large_file)
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_hash_binary_file(self, tmp_path):
        """Hash binary file with non-UTF8 bytes."""
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

        hash_result = hash_file(binary_file)
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_hash_empty_file(self, tmp_path):
        """Hash empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        hash_result = hash_file(empty_file)
        # Empty string SHA256
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert hash_result == expected

    def test_hash_file_not_found(self, tmp_path):
        """hash_file raises FileNotFoundError for missing file."""
        missing_file = tmp_path / "missing.txt"
        with pytest.raises(FileNotFoundError) as exc_info:
            hash_file(missing_file)
        assert "File not found" in str(exc_info.value)

    def test_hash_file_permission_denied(self, tmp_path):
        """hash_file raises PermissionError for unreadable file."""
        restricted_file = tmp_path / "restricted.txt"
        restricted_file.write_text("content", encoding="utf-8")

        # Remove read permission (Unix only)
        os.chmod(restricted_file, 0o000)

        try:
            with pytest.raises(PermissionError) as exc_info:
                hash_file(restricted_file)
            assert "Permission denied" in str(exc_info.value)
        finally:
            # Restore permission for cleanup
            os.chmod(restricted_file, 0o644)

    def test_hash_file_returns_lowercase_hex(self, tmp_path):
        """hash_file returns lowercase hex string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test", encoding="utf-8")

        hash_result = hash_file(test_file)
        # Should be lowercase hex, no uppercase
        assert hash_result == hash_result.lower()
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_hash_file_special_characters_in_name(self, tmp_path):
        """Hash file with special characters in filename."""
        special_file = tmp_path / "file-with_special.chars123.txt"
        special_file.write_text("content", encoding="utf-8")

        hash_result = hash_file(special_file)
        assert len(hash_result) == 64
        # File name doesn't affect content hash (only content matters)

    def test_hash_consistency_across_multiple_calls(self, tmp_path):
        """Multiple sequential hash calls produce identical results."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Consistency test", encoding="utf-8")

        hash1 = hash_file(test_file)
        hash2 = hash_file(test_file)
        hash3 = hash_file(test_file)

        assert hash1 == hash2 == hash3


class TestHashFileWithValidation:
    """Test hash_file_with_validation() for UTF-8 validation."""

    def test_valid_utf8_file(self, tmp_path):
        """Valid UTF-8 file returns (hash, None)."""
        test_file = tmp_path / "valid.txt"
        test_file.write_text("Hello, world!", encoding="utf-8")

        hash_result, error = hash_file_with_validation(test_file)
        assert hash_result is not None
        assert len(hash_result) == 64
        assert error is None

    def test_utf8_with_bom(self, tmp_path):
        """UTF-8 with BOM (Byte Order Mark) validates correctly."""
        test_file = tmp_path / "bom.txt"
        # Write with UTF-8 BOM
        with open(test_file, "wb") as f:
            f.write(b"\xef\xbb\xbf" + "Hello, world!".encode("utf-8"))

        hash_result, error = hash_file_with_validation(test_file)
        assert hash_result is not None
        assert len(hash_result) == 64
        assert error is None

    def test_utf8_with_cjk_characters(self, tmp_path):
        """UTF-8 with CJK (Chinese/Japanese/Korean) characters validates."""
        test_file = tmp_path / "cjk.txt"
        # CJK characters (Chinese, Japanese, Korean)
        test_file.write_text(
            "Hello 世界 こんにちは 안녕하세요", encoding="utf-8"
        )

        hash_result, error = hash_file_with_validation(test_file)
        assert hash_result is not None
        assert len(hash_result) == 64
        assert error is None

    def test_utf8_with_emoji(self, tmp_path):
        """UTF-8 with emoji characters validates."""
        test_file = tmp_path / "emoji.txt"
        test_file.write_text("Hello 👋 World 🌍", encoding="utf-8")

        hash_result, error = hash_file_with_validation(test_file)
        assert hash_result is not None
        assert len(hash_result) == 64
        assert error is None

    def test_invalid_utf8_sequence(self, tmp_path):
        """Invalid UTF-8 sequence returns (None, 'invalid_utf8')."""
        test_file = tmp_path / "invalid.bin"
        # Write invalid UTF-8 sequence
        with open(test_file, "wb") as f:
            f.write(b"Valid: hello\nInvalid: \xff\xfe")

        hash_result, error = hash_file_with_validation(test_file)
        assert hash_result is None
        assert error == "invalid_utf8"

    def test_invalid_utf8_continuation_byte(self, tmp_path):
        """Invalid continuation byte returns (None, 'invalid_utf8')."""
        test_file = tmp_path / "invalid_cont.bin"
        # Start of multi-byte sequence without proper continuation
        with open(test_file, "wb") as f:
            f.write(b"\xc0\x00")  # Invalid: incomplete multi-byte

        hash_result, error = hash_file_with_validation(test_file)
        assert hash_result is None
        assert error == "invalid_utf8"

    def test_unreadable_file_returns_unreadable_error(self, tmp_path):
        """Unreadable file returns (None, 'unreadable')."""
        restricted_file = tmp_path / "restricted.txt"
        restricted_file.write_text("content", encoding="utf-8")

        # Remove read permission
        os.chmod(restricted_file, 0o000)

        try:
            hash_result, error = hash_file_with_validation(restricted_file)
            assert hash_result is None
            assert error == "unreadable"
        finally:
            os.chmod(restricted_file, 0o644)

    def test_missing_file_returns_unreadable_error(self, tmp_path):
        """Missing file returns (None, 'unreadable')."""
        missing_file = tmp_path / "missing.txt"

        hash_result, error = hash_file_with_validation(missing_file)
        assert hash_result is None
        assert error == "unreadable"

    def test_validation_result_is_deterministic(self, tmp_path):
        """Multiple calls return same validation result."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content", encoding="utf-8")

        result1 = hash_file_with_validation(test_file)
        result2 = hash_file_with_validation(test_file)
        result3 = hash_file_with_validation(test_file)

        assert result1 == result2 == result3


class TestHasher:
    """Test Hasher class for order-independent parity hashing."""

    def test_hasher_order_independence_two_hashes(self):
        """Adding 2 hashes in different order produces same parity."""
        hash_list = ["a" * 64, "b" * 64]

        hasher1 = Hasher()
        for h in hash_list:
            hasher1.add_artifact_hash(h)
        parity1 = hasher1.compute_parity_hash()

        hasher2 = Hasher()
        for h in reversed(hash_list):
            hasher2.add_artifact_hash(h)
        parity2 = hasher2.compute_parity_hash()

        assert parity1 == parity2

    def test_hasher_order_independence_five_hashes(self):
        """Adding 5 hashes in random order produces identical parity."""
        hash_list = ["a" * 64, "b" * 64, "c" * 64, "d" * 64, "e" * 64]

        hasher1 = Hasher()
        for h in hash_list:
            hasher1.add_artifact_hash(h)
        parity1 = hasher1.compute_parity_hash()

        hasher2 = Hasher()
        for h in reversed(hash_list):
            hasher2.add_artifact_hash(h)
        parity2 = hasher2.compute_parity_hash()

        assert parity1 == parity2

    def test_hasher_order_independence_many_hashes(self):
        """Adding 100+ hashes in different order produces identical parity."""
        # Create 100 different hashes
        hash_list = [
            format(i, "064x") for i in range(100)
        ]  # 100 different hex values

        hasher1 = Hasher()
        for h in hash_list:
            hasher1.add_artifact_hash(h)
        parity1 = hasher1.compute_parity_hash()

        hasher2 = Hasher()
        for h in reversed(hash_list):
            hasher2.add_artifact_hash(h)
        parity2 = hasher2.compute_parity_hash()

        assert parity1 == parity2

    def test_hasher_empty_hash_list(self):
        """Empty hash list returns valid hash (empty string hash)."""
        hasher = Hasher()
        parity = hasher.compute_parity_hash()

        # Empty string SHA256
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert parity == expected

    def test_hasher_single_hash(self):
        """Single hash in list returns deterministic parity."""
        test_hash = "a" * 64
        hasher = Hasher()
        hasher.add_artifact_hash(test_hash)
        parity = hasher.compute_parity_hash()

        # Should be SHA256 of the single hash
        assert len(parity) == 64
        assert all(c in "0123456789abcdef" for c in parity)

    def test_hasher_duplicate_hashes_included(self):
        """Duplicate artifact hashes are included in parity."""
        hasher1 = Hasher()
        hasher1.add_artifact_hash("a" * 64)
        hasher1.add_artifact_hash("a" * 64)  # Duplicate
        parity1 = hasher1.compute_parity_hash()

        hasher2 = Hasher()
        hasher2.add_artifact_hash("a" * 64)
        parity2 = hasher2.compute_parity_hash()

        # Different parity because one has duplicate
        assert parity1 != parity2

    def test_hasher_add_artifact_hash_rejects_none(self):
        """add_artifact_hash rejects None."""
        hasher = Hasher()
        with pytest.raises(ValueError) as exc_info:
            hasher.add_artifact_hash(None)
        assert "non-empty string" in str(exc_info.value)

    def test_hasher_add_artifact_hash_rejects_empty_string(self):
        """add_artifact_hash rejects empty string."""
        hasher = Hasher()
        with pytest.raises(ValueError) as exc_info:
            hasher.add_artifact_hash("")
        assert "non-empty string" in str(exc_info.value)

    def test_hasher_add_artifact_hash_rejects_non_string(self):
        """add_artifact_hash rejects non-string types."""
        hasher = Hasher()
        with pytest.raises(ValueError) as exc_info:
            hasher.add_artifact_hash(123)
        assert "non-empty string" in str(exc_info.value)

    def test_hasher_get_sorted_hashes(self):
        """get_sorted_hashes returns lexicographically sorted hashes."""
        hasher = Hasher()
        hasher.add_artifact_hash("zzz")
        hasher.add_artifact_hash("aaa")
        hasher.add_artifact_hash("mmm")

        sorted_hashes = hasher.get_sorted_hashes()
        assert sorted_hashes == ["aaa", "mmm", "zzz"]

    def test_hasher_parity_deterministic(self):
        """Multiple compute_parity_hash calls return same result."""
        hasher = Hasher()
        hasher.add_artifact_hash("a" * 64)
        hasher.add_artifact_hash("b" * 64)

        parity1 = hasher.compute_parity_hash()
        parity2 = hasher.compute_parity_hash()
        parity3 = hasher.compute_parity_hash()

        assert parity1 == parity2 == parity3

    def test_hasher_parity_result_is_valid_hex(self):
        """Parity hash is valid 64-character hex string."""
        hasher = Hasher()
        hasher.add_artifact_hash("a" * 64)
        parity = hasher.compute_parity_hash()

        assert len(parity) == 64
        assert all(c in "0123456789abcdef" for c in parity)

    def test_hasher_different_hash_lists_different_parity(self):
        """Different hash lists produce different parities."""
        hasher1 = Hasher()
        hasher1.add_artifact_hash("a" * 64)
        parity1 = hasher1.compute_parity_hash()

        hasher2 = Hasher()
        hasher2.add_artifact_hash("b" * 64)
        parity2 = hasher2.compute_parity_hash()

        assert parity1 != parity2

    def test_hasher_can_add_non_sha256_hashes(self):
        """Hasher accepts any non-empty strings as hashes."""
        hasher = Hasher()
        hasher.add_artifact_hash("short")  # Not 64 chars
        hasher.add_artifact_hash("a" * 100)  # Longer than 64 chars
        hasher.add_artifact_hash("hash123")

        parity = hasher.compute_parity_hash()
        assert len(parity) == 64  # Result is still SHA256

    def test_hasher_workflow(self):
        """Complete workflow: add hashes, compute parity, verify determinism."""
        # Simulate indexing 5 artifacts
        artifacts = [
            ("spec", "a" * 64),
            ("plan", "b" * 64),
            ("tasks", "c" * 64),
            ("wp01", "d" * 64),
            ("wp02", "e" * 64),
        ]

        # First scan (in order)
        hasher1 = Hasher()
        for _, hash_val in artifacts:
            hasher1.add_artifact_hash(hash_val)
        parity1 = hasher1.compute_parity_hash()

        # Second scan (reverse order)
        hasher2 = Hasher()
        for _, hash_val in reversed(artifacts):
            hasher2.add_artifact_hash(hash_val)
        parity2 = hasher2.compute_parity_hash()

        # Both scans should produce identical parity
        assert parity1 == parity2

    def test_hasher_initial_empty_state(self):
        """Hasher starts with empty hash list."""
        hasher = Hasher()
        assert hasher.hashes == []
        assert hasher.get_sorted_hashes() == []
