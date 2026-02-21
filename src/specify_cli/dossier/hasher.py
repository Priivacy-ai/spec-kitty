"""Deterministic SHA256 hashing utilities for mission artifacts.

This module provides functions and classes for computing deterministic
content hashes and order-independent parity hashes, critical for
reproducible artifact indexing and drift detection.

See: kitty-specs/042-local-mission-dossier-authority-parity-export/data-model.md
"""

import hashlib
from pathlib import Path
from typing import List, Optional, Tuple


def hash_file(file_path: Path) -> str:
    """Compute SHA256 hash of file content (bytes).

    Reads file in binary mode and computes deterministic SHA256 hash,
    immune to encoding assumptions and timezone differences.

    Args:
        file_path: Path to file to hash

    Returns:
        64-character lowercase hex string (SHA256)

    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be read (permission denied)
        IOError: If other I/O errors occur during reading

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        ...     f.write('Hello, world!')
        ...     path = Path(f.name)
        >>> hash1 = hash_file(path)
        >>> hash2 = hash_file(path)
        >>> hash1 == hash2
        True
        >>> len(hash1)
        64
    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read in 8KB chunks to avoid memory issues with large files
            while chunk := f.read(8192):
                hasher.update(chunk)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {file_path}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied reading file: {file_path}") from e
    except IOError as e:
        raise IOError(f"I/O error reading file: {file_path}") from e

    return hasher.hexdigest()


def hash_file_with_validation(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Hash file with UTF-8 validation, return (hash_or_none, error_reason).

    Attempts to read file as UTF-8 text (validates encoding), then hashes
    the bytes. If UTF-8 validation fails, captures error reason without
    silent corruption.

    UTF-8 validation is explicit: BOM (Byte Order Mark), CJK characters,
    and multi-byte sequences are handled correctly. Invalid UTF-8 sequences
    cause explicit error_reason return, never silent fallback.

    Args:
        file_path: Path to file to hash and validate

    Returns:
        Tuple of (hash_or_none, error_reason):
        - On success: (64-char hex string, None)
        - On UTF-8 error: (None, "invalid_utf8")
        - On file access error: (None, "unreadable")

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> # Valid UTF-8 file
        >>> with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
        ...     f.write('Hello, 世界!')  # Chinese characters
        ...     path = Path(f.name)
        >>> hash_val, error = hash_file_with_validation(path)
        >>> error is None
        True
        >>> len(hash_val) == 64
        True
        >>> # Invalid UTF-8 file
        >>> import os
        >>> with tempfile.NamedTemporaryFile(delete=False) as f:
        ...     f.write(b'\xff\xfe')  # Invalid UTF-8 sequence
        ...     path = Path(f.name)
        >>> hash_val, error = hash_file_with_validation(path)
        >>> error
        'invalid_utf8'
        >>> hash_val is None
        True
    """
    try:
        # Read entire file as bytes
        with open(file_path, "rb") as f:
            content_bytes = f.read()

        # Validate UTF-8 encoding by attempting decode
        try:
            content_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            return None, "invalid_utf8"

        # Hash the bytes directly
        hasher = hashlib.sha256()
        hasher.update(content_bytes)
        return hasher.hexdigest(), None

    except FileNotFoundError:
        return None, "unreadable"
    except PermissionError:
        return None, "unreadable"
    except IOError:
        return None, "unreadable"


class Hasher:
    """Compute order-independent parity hash from artifact hashes.

    Maintains a pool of artifact hashes and computes deterministic parity hash
    by lexicographically sorting hashes before concatenation. This ensures
    that artifacts indexed in any order produce identical parity hash,
    critical for reproducible dossier snapshots.

    Attributes:
        hashes: List of artifact content hashes (hex strings)

    Examples:
        >>> hasher = Hasher()
        >>> hasher.add_artifact_hash("abc123def456")
        >>> hasher.add_artifact_hash("xyz789")
        >>> parity = hasher.compute_parity_hash()
        >>> len(parity)
        64
        >>> # Order independence: same hashes, different order
        >>> hasher2 = Hasher()
        >>> hasher2.add_artifact_hash("xyz789")
        >>> hasher2.add_artifact_hash("abc123def456")
        >>> hasher2.compute_parity_hash() == parity
        True
    """

    def __init__(self):
        """Initialize empty hash pool."""
        self.hashes: List[str] = []

    def add_artifact_hash(self, artifact_hash: str) -> None:
        """Add artifact hash to pool.

        Args:
            artifact_hash: 64-character SHA256 hex string (or other hash)

        Raises:
            ValueError: If artifact_hash is not a non-empty string
        """
        if not artifact_hash or not isinstance(artifact_hash, str):
            raise ValueError(
                f"artifact_hash must be non-empty string; got {repr(artifact_hash)}"
            )
        self.hashes.append(artifact_hash)

    def compute_parity_hash(self) -> str:
        """Compute order-independent parity hash from pooled hashes.

        Algorithm:
        1. Sort artifact hashes lexicographically
        2. Concatenate sorted hashes into single string
        3. Compute SHA256 of concatenated string
        4. Return 64-character hex string

        Order-independent: artifacts can be scanned in any order,
        parity hash will be identical.

        Returns:
            64-character lowercase hex string (SHA256 of concatenated sorted hashes)

        Examples:
            >>> hasher = Hasher()
            >>> hasher.add_artifact_hash("zzz")
            >>> hasher.add_artifact_hash("aaa")
            >>> hasher.add_artifact_hash("mmm")
            >>> parity1 = hasher.compute_parity_hash()
            >>> hasher2 = Hasher()
            >>> hasher2.add_artifact_hash("aaa")
            >>> hasher2.add_artifact_hash("zzz")
            >>> hasher2.add_artifact_hash("mmm")
            >>> parity2 = hasher2.compute_parity_hash()
            >>> parity1 == parity2
            True
        """
        # Sort hashes lexicographically
        sorted_hashes = sorted(self.hashes)

        # Concatenate into single string
        combined = "".join(sorted_hashes)

        # Compute SHA256 of concatenated string
        parity_hasher = hashlib.sha256()
        parity_hasher.update(combined.encode("utf-8"))

        return parity_hasher.hexdigest()

    def get_sorted_hashes(self) -> List[str]:
        """Get sorted artifact hashes (for audit/debugging).

        Returns:
            Lexicographically sorted list of artifact hashes
        """
        return sorted(self.hashes)
