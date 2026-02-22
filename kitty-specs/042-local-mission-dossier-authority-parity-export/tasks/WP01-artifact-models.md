---
work_package_id: WP01
title: ArtifactRef Model & Deterministic Hashing
lane: "done"
dependencies: []
base_branch: 2.x
base_commit: a61abc8adeb69a5452dda768efcc262bcdf7d5b3
created_at: '2026-02-21T15:32:13.451041+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
feature_slug: 042-local-mission-dossier-authority-parity-export
shell_pid: "83296"
agent: "codex"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# WP01: ArtifactRef Model & Deterministic Hashing

**Objective**: Define immutable ArtifactRef pydantic model and implement deterministic SHA256 hashing utilities for artifact content. This WP establishes the foundation for all downstream artifact indexing, classification, and parity computation.

**Priority**: P1 (Foundation for all other WPs)

**Scope**:

- ArtifactRef model (~25 fields)
- Hasher utility class
- Deterministic SHA256 hashing
- Order-independent parity hash computation
- UTF-8 validation and error handling
- Unit tests for reproducibility

**Test Criteria**:

- ArtifactRef validates all required fields, rejects malformed inputs
- Same file hashed 10x produces identical SHA256
- Different files produce different hashes
- Parity hash unchanged by artifact order
- UTF-8 encoding errors explicit (no corruption)

---

## Context

Feature 042 requires a mission artifact dossier system. The dossier stores immutable references to indexed artifacts, each with deterministic content hash (SHA256) and metadata. The ArtifactRef model is the core data structure; the Hasher utility ensures deterministic hashing across machines/timezones/runs.

**Key Requirements**:

- **FR-001**: System MUST index all artifact files and compute deterministic content_hash_sha256
- **FR-005**: System MUST compute deterministic parity_hash_sha256 from artifact hashes
- **SC-002**: Snapshots are deterministic—repeated scans produce identical hashes
- **SC-007**: UTF-8 robustness—edge cases handled consistently, not corruption sources

---

## Detailed Guidance

### T001: ArtifactRef Pydantic Model

**What**: Create comprehensive pydantic BaseModel for ArtifactRef.

**How**:

1. Define ArtifactRef class in `src/specify_cli/dossier/models.py`
2. Include 25 fields across 6 categories:
   - **Identity**: artifact_key (unique per dossier), artifact_class (6-type enum)
   - **Location & Content**: relative_path (from feature dir), content_hash_sha256, size_bytes
   - **Metadata**: wp_id (optional), step_id (optional), required_status (required|optional)
   - **Provenance**: provenance dict (source_kind, actor_id, captured_at)
   - **State**: is_present (bool), error_reason (not_found|unreadable|invalid_format|deleted_after_scan)
   - **Timestamps**: indexed_at (UTC datetime)
3. Add Field() descriptors with detailed descriptions for documentation
4. Include Config class with json_encoders for datetime serialization
5. Add docstring referencing data-model.md

**Example Signature**:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ArtifactRef(BaseModel):
    # Identity
    artifact_key: str = Field(..., description="...")
    artifact_class: str = Field(..., description="...")
    # ... more fields
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
```

**Validation**:

- artifact_key must be non-empty, alphanumeric + dots/underscores
- artifact_class must be in {input, workflow, output, evidence, policy, runtime}
- required_status must be in {required, optional}
- size_bytes must be >= 0
- content_hash_sha256 must be 64 hex chars (SHA256) or None (if error_reason set)

**Test Requirements**:

- Create valid ArtifactRef, verify all fields present
- Reject artifact_key=None, verify error
- Reject artifact_class="unknown", verify error
- Serialize to JSON, deserialize back, verify identity

---

### T002: SHA256 Deterministic Hashing Utility

**What**: Create standalone hash_file() function for deterministic content hashing.

**How**:

1. Create hasher.py module in `src/specify_cli/dossier/hasher.py`
2. Implement `hash_file(file_path: Path) -> str` function:
   - Read file as bytes (binary mode, no text encoding assumptions)
   - Compute SHA256 hash of bytes directly
   - Return 64-char hex string (lowercase)
3. Handle errors:
   - FileNotFoundError → raise with context
   - PermissionError → raise with context
   - IOError → raise with context
4. Add docstring with examples

**Implementation Sketch**:

```python
import hashlib
from pathlib import Path

def hash_file(file_path: Path) -> str:
    """Compute SHA256 hash of file content (bytes).

    Args:
        file_path: Path to file to hash

    Returns:
        64-char hex string (SHA256)

    Raises:
        FileNotFoundError, PermissionError, IOError on file access errors
    """
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()
```

**Test Requirements**:

- Hash same file 10 times, verify identical result
- Hash two different files, verify different hashes
- Hash large file (>100MB), verify completes without memory issues
- Hash file with special characters in name, verify works
- FileNotFoundError raises on missing file
- PermissionError raises on unreadable file (if testable)

**Notes**:

- Use binary mode (rb) to avoid encoding assumptions
- Chunk read size: 8192 bytes (standard buffer size)
- No encoding/decoding steps (handled in WP04 UTF-8 validation)

---

### T003: Hasher Class with Order-Independent Parity

**What**: Create Hasher class that computes order-independent parity hash from artifact hashes.

**How**:

1. Create Hasher class in hasher.py:

   ```python
   class Hasher:
       def __init__(self):
           self.hashes: List[str] = []

       def add_artifact_hash(self, artifact_hash: str) -> None:
           """Add artifact hash to pool."""

       def compute_parity_hash(self) -> str:
           """Compute order-independent parity hash."""
   ```

2. Implement `compute_parity_hash()`:
   - Sort artifact hashes lexicographically
   - Concatenate sorted hashes into single string
   - Compute SHA256 of concatenated string
   - Return 64-char hex string
3. Add method to get sorted hashes (for audit/debugging)
4. Add docstring explaining order-independence

**Algorithm**:

```python
def compute_parity_hash(self) -> str:
    """Compute SHA256 of sorted artifact hashes.

    Order-independent: artifacts can be scanned in any order,
    parity hash will be identical.
    """
    sorted_hashes = sorted(self.hashes)
    combined = "".join(sorted_hashes)
    parity = hashlib.sha256(combined.encode()).hexdigest()
    return parity
```

**Test Requirements**:

- Add 5 artifact hashes in order [A, B, C, D, E], compute parity → X
- Add same 5 hashes in random order [C, A, E, B, D], compute parity → X (identical)
- Add hashes with 100+ artifacts, verify deterministic
- Empty hash list returns valid hash (empty string hash)
- Duplicate artifact hashes included in parity (intentional)

**Notes**:

- UTF-8 encode concatenated string before hashing (hashes are hex strings)
- Duplicates allowed and included in parity (features may have duplicate artifacts)

---

### T004: UTF-8 Validation & Error Handling

**What**: Add UTF-8 validation to hashing pipeline, ensure no silent corruption.

**How**:

1. Create `hash_file_with_validation(file_path: Path) -> Tuple[str, Optional[str]]` function:
   - Attempt to read file as UTF-8 text (validate encoding)
   - If valid UTF-8, hash bytes normally
   - If invalid UTF-8, capture error_reason (e.g., "invalid_utf8")
   - Return (hash_or_none, error_reason)
2. Add error_reason enum with codes:
   - "valid" (no error)
   - "unreadable" (permission, I/O error)
   - "invalid_utf8" (bytes not valid UTF-8)
   - "size_limit" (file too large, optional)
3. Update ArtifactRef.error_reason field to capture these codes
4. Add docstring with examples

**Implementation Sketch**:

```python
def hash_file_with_validation(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Hash file, validate UTF-8 encoding, return (hash, error_reason)."""
    try:
        # Validate UTF-8 by attempting text decode
        with open(file_path, 'rb') as f:
            content_bytes = f.read()
        content_bytes.decode('utf-8')  # Validate
        # Hash the bytes
        hasher = hashlib.sha256()
        hasher.update(content_bytes)
        return hasher.hexdigest(), None
    except UnicodeDecodeError as e:
        return None, "invalid_utf8"
    except (FileNotFoundError, PermissionError) as e:
        return None, "unreadable"
    except IOError as e:
        return None, "unreadable"
```

**Test Requirements**:

- Valid UTF-8 file: returns (hash, None)
- File with BOM (UTF-8 BOM prefix): validates, hashes correctly
- File with CJK characters (Chinese/Japanese): validates, hashes correctly
- File with UTF-8 surrogates (invalid sequence): returns (None, "invalid_utf8")
- File with mixed encodings: returns (None, "invalid_utf8")
- Unreadable file (permission): returns (None, "unreadable")

**Notes**:

- No fallback encoding (e.g., latin-1). Invalid UTF-8 is error, not silent corruption.
- BOM handling: UTF-8 BOM is valid (bytes 0xEF, 0xBB, 0xBF); Python's decode('utf-8') handles it.
- CJK: Valid UTF-8 multibyte sequences should validate cleanly.

---

### T005: Unit Tests for Hashing Determinism

**What**: Comprehensive unit tests for deterministic hashing.

**How**:

1. Create `tests/specify_cli/dossier/test_hasher.py`
2. Add test cases:
   - **test_hash_file_determinism**: Hash same file 10 times, verify identical
   - **test_hash_file_different_files**: Hash 2 different files, verify different
   - **test_hash_file_large_file**: Hash 100MB file, verify no memory explosion
   - **test_hasher_order_independence**: Add hashes in random order, verify parity identical
   - **test_hasher_empty_list**: Empty hash list, verify returns valid hash
   - **test_hash_file_with_validation_valid_utf8**: Valid UTF-8 file, verify (hash, None)
   - **test_hash_file_with_validation_invalid_utf8**: Invalid sequence, verify (None, "invalid_utf8")
   - **test_artifact_ref_serialization**: Create ArtifactRef, JSON serialize/deserialize, verify identity
   - **test_artifact_ref_validation_bad_class**: Try artifact_class="invalid", verify validation error
   - **test_artifact_ref_validation_bad_hash**: Try content_hash_sha256="short", verify validation error
3. Use pytest fixtures for test files (create temp files in /tmp)
4. Add parametrized tests for multiple scenarios

**Test Structure**:

```python
import pytest
from pathlib import Path
from specify_cli.dossier.hasher import hash_file, Hasher
from specify_cli.dossier.models import ArtifactRef

def test_hash_file_determinism(tmp_path):
    """Hash same file 10 times, verify identical."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, world!", encoding="utf-8")

    hashes = [hash_file(test_file) for _ in range(10)]
    assert len(set(hashes)) == 1, "All hashes should be identical"

def test_hasher_order_independence():
    """Adding hashes in different order produces same parity."""
    hash_list = ["abc123", "def456", "ghi789"]

    hasher1 = Hasher()
    for h in hash_list:
        hasher1.add_artifact_hash(h)
    parity1 = hasher1.compute_parity_hash()

    hasher2 = Hasher()
    for h in reversed(hash_list):
        hasher2.add_artifact_hash(h)
    parity2 = hasher2.compute_parity_hash()

    assert parity1 == parity2, "Parity should be order-independent"
```

---

## Definition of Done

- [ ] ArtifactRef model created, all fields present, validation working
- [ ] hash_file() function implemented, tested on various file sizes
- [ ] hash_file_with_validation() returns (hash, error_reason) correctly
- [ ] Hasher class implemented, parity computation order-independent
- [ ] UTF-8 validation explicit (BOM, CJK, surrogates handled)
- [ ] All 10+ unit tests passing
- [ ] Code follows spec-kitty style conventions
- [ ] Docstrings complete, examples provided
- [ ] No silent failures, all errors explicit
- [ ] SC-002, SC-007 requirements validated

---

## Risks & Mitigations

**Risk 1**: Encoding assumptions (e.g., assuming UTF-8)

- **Mitigation**: Hash bytes directly, validate UTF-8 separately, no fallback encoding

**Risk 2**: Memory issues on large files

- **Mitigation**: Chunk read size (8192 bytes), test with 100MB+ files

**Risk 3**: Hash collision false positives

- **Mitigation**: SHA256 is standard, tested across Python versions; collision probability negligible

**Risk 4**: Timezone/platform differences in hash

- **Mitigation**: Hash is deterministic (bytes-based), timezone-independent; SC-006 validates

---

## Reviewer Guidance

When reviewing WP01:

1. Verify ArtifactRef model matches data-model.md exactly (all 25 fields)
2. Confirm hash_file() uses binary mode (no encoding assumptions)
3. Check UTF-8 validation handles BOM, CJK, surrogates explicitly
4. Verify Hasher.compute_parity_hash() is order-independent (sort before concatenate)
5. Ensure all error paths explicit (no silent corruption)
6. Confirm unit tests cover at least 10+ scenarios (determinism, order-independence, encoding)
7. Validate SC-002, SC-006, SC-007 requirements addressed

---

## Implementation Notes

- **Storage**: models.py (ArtifactRef), hasher.py (Hasher, hash_file)
- **Dependencies**: hashlib (stdlib), pydantic (existing)
- **Estimated Lines**: ~300 (models ~100, hasher ~120, tests ~80)
- **Testing**: Parametrized tests, fixtures for temp files
- **Integration Point**: WP03 (indexing) will use these models/functions

## Activity Log

- 2026-02-21T15:32:13Z – coordinator – shell_pid=72113 – lane=doing – Assigned agent via workflow command
- 2026-02-21T15:44:37Z – coordinator – shell_pid=72113 – lane=for_review – Ready for code review: All 66 tests passing
- 2026-02-21T15:45:10Z – codex – shell_pid=83296 – lane=doing – Started review via workflow command
- 2026-02-21T15:45:26Z – codex – shell_pid=83296 – lane=done – Code review passed: 66 tests, all AC met, foundation ready for downstream WPs
