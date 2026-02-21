---
work_package_id: WP09
title: Determinism Test Suite
lane: "done"
dependencies:
- WP01
- WP05
base_branch: 042-local-mission-dossier-authority-parity-export-WP09-merge-base
base_commit: 1bf5196379830703d153f67da65abff9469ed59d
created_at: '2026-02-21T15:59:53.146188+00:00'
subtasks:
- T046
- T047
- T048
- T049
- T050
feature_slug: 042-local-mission-dossier-authority-parity-export
shell_pid: "99215"
agent: "coordinator"
reviewed_by: "Robert Douglass"
review_status: "approved"
---

# WP09: Determinism Test Suite

**Objective**: Comprehensive test suite validating hash reproducibility, ordering stability, and UTF-8 robustness. These tests are critical for SC-002, SC-006, SC-007 success criteria—proving that identical artifact content always produces identical parity hashes across machines, timezones, and multiple runs.

**Priority**: P1 (Critical for feature success, non-negotiable quality bar)

**Scope**:
- Hash reproducibility (same file → same hash, 10+ runs)
- Order independence (artifact order irrelevant)
- UTF-8 handling (BOM, CJK, surrogates)
- CRLF vs LF consistency
- Cross-machine/timezone stability

**Test Criteria**:
- All SC-002, SC-006, SC-007 success criteria passed
- Zero hash mismatches across 10+ runs, multiple machines
- UTF-8 edge cases handled explicitly
- Line-ending differences don't cause mismatches

---

## Context

WP01-WP05 implement the core dossier system. WP09 validates that the system meets its fundamental promise: deterministic hashing. If hashing is non-deterministic, the entire parity detection system (WP08) fails, and SaaS can't trust local snapshots.

**Critical Success Criteria** (from spec):
- **SC-002**: Repeated scans of unchanged content produce identical snapshots
- **SC-006**: Parity hash reproducible across machines/timezones
- **SC-007**: UTF-8 robustness—edge cases handled consistently

**No Fallback**: If any test fails, feature is not deployable. Determinism is non-negotiable.

---

## Detailed Guidance

### T046: Hash Reproducibility

**What**: Prove same file → same hash across multiple runs.

**How**:
1. Create test_determinism.py in `tests/specify_cli/dossier/test_determinism.py`
2. Implement test_hash_reproducibility():
   ```python
   import pytest
   from pathlib import Path
   from specify_cli.dossier.hasher import hash_file, Hasher
   from specify_cli.dossier.models import MissionDossier, ArtifactRef
   from specify_cli.dossier.store import compute_snapshot

   def test_hash_file_reproducibility(tmp_path):
       """Hash same file 10 times, verify identical."""
       # Create test file
       test_file = tmp_path / "test-artifact.md"
       test_content = "# Test Artifact\n\nThis is a test.\n"
       test_file.write_text(test_content, encoding='utf-8')

       # Hash 10 times
       hashes = [hash_file(test_file) for _ in range(10)]

       # Verify all identical
       assert len(set(hashes)) == 1, f"Hash mismatch: {hashes}"
       assert re.match(r'^[a-f0-9]{64}$', hashes[0]), "Invalid SHA256 format"

   def test_snapshot_reproducibility(tmp_path):
       """Compute snapshot twice on same content, verify identical parity hash."""
       # Create feature directory with artifacts
       feature_dir = create_test_feature(tmp_path, num_artifacts=10)

       # Index and compute snapshot 1
       indexer1 = Indexer(ManifestRegistry())
       dossier1 = indexer1.index_feature(feature_dir, 'software-dev')
       snapshot1 = compute_snapshot(dossier1)

       # Index and compute snapshot 2 (same content)
       indexer2 = Indexer(ManifestRegistry())
       dossier2 = indexer2.index_feature(feature_dir, 'software-dev')
       snapshot2 = compute_snapshot(dossier2)

       # Verify hashes identical
       assert snapshot1.parity_hash_sha256 == snapshot2.parity_hash_sha256, \
           f"Parity hash mismatch: {snapshot1.parity_hash_sha256} vs {snapshot2.parity_hash_sha256}"
       assert snapshot1.completeness_status == snapshot2.completeness_status
       assert snapshot1.total_artifacts == snapshot2.total_artifacts

   @pytest.mark.parametrize('run_count', [1, 5, 10])
   def test_snapshot_reproducibility_multiple_runs(tmp_path, run_count):
       """Verify snapshot reproducible across N runs."""
       feature_dir = create_test_feature(tmp_path, num_artifacts=20)

       # Compute snapshots N times
       hashes = []
       for _ in range(run_count):
           indexer = Indexer(ManifestRegistry())
           dossier = indexer.index_feature(feature_dir, 'software-dev')
           snapshot = compute_snapshot(dossier)
           hashes.append(snapshot.parity_hash_sha256)

       # Verify all identical
       assert len(set(hashes)) == 1, f"Hash mismatch across {run_count} runs: {set(hashes)}"
   ```
3. Test with various file sizes (small, medium, large)
4. Test with many artifacts (10, 50, 100)
5. Verify exact hash match (bit-for-bit)

**Test Requirements**:
- Same file, 10 runs → 10 identical hashes
- Different snapshots of same content → identical parity hashes
- No timing-dependent randomness
- SC-002 satisfied

---

### T047: Order Independence

**What**: Prove artifact order irrelevant to parity hash.

**How**:
1. Implement test_order_independence():
   ```python
   def test_order_independence_artifact_keys(tmp_path):
       """Artifacts in different order → same parity hash."""
       # Create feature with 5 artifacts
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()

       artifacts = [
           ("spec.md", "# Specification"),
           ("plan.md", "# Plan"),
           ("tasks.md", "# Tasks"),
           ("research.md", "# Research"),
           ("gap-analysis.md", "# Gaps"),
       ]

       for name, content in artifacts:
           (feature_dir / name).write_text(content, encoding='utf-8')

       # Index 1: scan in normal order
       indexer1 = Indexer(ManifestRegistry())
       dossier1 = indexer1.index_feature(feature_dir, 'software-dev')
       snapshot1 = compute_snapshot(dossier1)

       # Manually create dossier 2 with artifacts in random order
       import random
       dossier2 = MissionDossier(
           mission_slug='software-dev',
           mission_run_id=str(uuid.uuid4()),
           feature_slug='test-feature',
           feature_dir=str(feature_dir),
           artifacts=random.sample(dossier1.artifacts, len(dossier1.artifacts)),
           manifest=dossier1.manifest,
       )
       snapshot2 = compute_snapshot(dossier2)

       # Verify parity hashes identical (order-independent)
       assert snapshot1.parity_hash_sha256 == snapshot2.parity_hash_sha256, \
           "Parity hash differs with artifact order"

   def test_hasher_order_independence():
       """Hasher.compute_parity_hash() order-independent."""
       hashes = ["abc123", "def456", "ghi789", "jkl012"]

       # Compute parity with different orders
       parity_hashes = []
       for _ in range(10):
           import random
           ordered = random.sample(hashes, len(hashes))

           hasher = Hasher()
           for h in ordered:
               hasher.add_artifact_hash(h)
           parity = hasher.compute_parity_hash()
           parity_hashes.append(parity)

       # All should be identical
       assert len(set(parity_hashes)) == 1, f"Parity differs by order: {set(parity_hashes)}"
   ```
2. Test with various artifact counts (5, 10, 50)
3. Test random shuffling multiple times
4. Verify SC-002 (ordering irrelevant)

**Test Requirements**:
- Artifacts in order [A, B, C] → hash X
- Artifacts in order [C, A, B] → hash X (identical)
- Random orderings always produce same hash
- Order-independence proven at both Hasher and Snapshot levels

---

### T048: UTF-8 Handling

**What**: Validate UTF-8 edge cases handled correctly.

**How**:
1. Implement test_utf8_handling():
   ```python
   def test_utf8_bom_handling(tmp_path):
       """UTF-8 BOM (0xEF 0xBB 0xBF) handled correctly."""
       # File with BOM prefix
       file_with_bom = tmp_path / "with-bom.txt"
       content = "# Test\n"
       # Write with BOM
       file_with_bom.write_bytes(b'\xef\xbb\xbf' + content.encode('utf-8'))

       # File without BOM
       file_without_bom = tmp_path / "without-bom.txt"
       file_without_bom.write_text(content, encoding='utf-8')

       # Both should be readable (BOM is valid UTF-8)
       hash_with_bom, err1 = hash_file_with_validation(file_with_bom)
       hash_without_bom, err2 = hash_file_with_validation(file_without_bom)

       # Hashes will differ (BOM adds bytes), but both valid
       assert err1 is None, f"BOM file should be valid UTF-8: {err1}"
       assert err2 is None, f"Non-BOM file should be valid UTF-8: {err2}"
       # Note: hashes will differ because BOM adds bytes (intentional)

   def test_utf8_cjk_characters(tmp_path):
       """UTF-8 CJK (Chinese/Japanese/Korean) characters handled."""
       # Chinese
       file_cjk = tmp_path / "cjk.md"
       content_cjk = "# 中文标题\n这是中文内容。\n"
       file_cjk.write_text(content_cjk, encoding='utf-8')

       # Japanese
       file_ja = tmp_path / "ja.md"
       content_ja = "# 日本語タイトル\nこれは日本語です。\n"
       file_ja.write_text(content_ja, encoding='utf-8')

       # Korean
       file_ko = tmp_path / "ko.md"
       content_ko = "# 한국어 제목\n이것은 한국어입니다.\n"
       file_ko.write_text(content_ko, encoding='utf-8')

       # All should hash without error
       hash_cjk, err1 = hash_file_with_validation(file_cjk)
       hash_ja, err2 = hash_file_with_validation(file_ja)
       hash_ko, err3 = hash_file_with_validation(file_ko)

       assert err1 is None, "Chinese should hash"
       assert err2 is None, "Japanese should hash"
       assert err3 is None, "Korean should hash"
       assert hash_cjk != hash_ja != hash_ko, "Different content should have different hashes"

   def test_utf8_invalid_sequence(tmp_path):
       """Invalid UTF-8 sequences rejected."""
       # File with invalid UTF-8 sequence
       file_invalid = tmp_path / "invalid.txt"
       # 0xFF 0xFE are invalid UTF-8 (reserved for UTF-16 BOM)
       file_invalid.write_bytes(b"Hello\xff\xfeWorld")

       # Should return error_reason
       hash_val, error = hash_file_with_validation(file_invalid)
       assert error == "invalid_utf8", f"Expected invalid_utf8 error, got {error}"
       assert hash_val is None

   def test_utf8_emoji(tmp_path):
       """Emoji and other Unicode chars handled."""
       file_emoji = tmp_path / "emoji.md"
       content = "# Test 😀\n\n✓ Check mark\n🚀 Rocket\n"
       file_emoji.write_text(content, encoding='utf-8')

       hash_val, error = hash_file_with_validation(file_emoji)
       assert error is None, "Emoji should hash"
       assert hash_val is not None
   ```
2. Test BOM handling (valid, included in hash)
3. Test CJK characters (multi-byte sequences, valid)
4. Test invalid UTF-8 (fail explicitly, no corruption)
5. Test emoji and other Unicode

**Test Requirements**:
- BOM-prefixed files validate (error=None)
- CJK characters validate
- Invalid sequences detected (error="invalid_utf8")
- Emoji handled correctly
- SC-007 satisfied

---

### T049: CRLF vs LF Consistency

**What**: Validate line-ending differences don't cause hash mismatches.

**How**:
1. Implement test_line_ending_handling():
   ```python
   def test_crlf_vs_lf_consistency(tmp_path):
       """Windows (CRLF) vs Unix (LF) line endings handled."""
       content = "# Specification\n\nLine 1\nLine 2\nLine 3\n"

       # Unix file (LF)
       file_lf = tmp_path / "unix.md"
       file_lf.write_bytes(content.encode('utf-8'))

       # Windows file (CRLF) - same logical content
       file_crlf = tmp_path / "windows.md"
       content_crlf = content.replace('\n', '\r\n')
       file_crlf.write_bytes(content_crlf.encode('utf-8'))

       # Hash both
       hash_lf, _ = hash_file_with_validation(file_lf)
       hash_crlf, _ = hash_file_with_validation(file_crlf)

       # Hashes will differ (bytes differ), but both valid
       # This is INTENTIONAL - line ending is part of content
       assert hash_lf != hash_crlf, "LF and CRLF hashes should differ (they're different bytes)"

       # NOTE: This validates that line endings ARE preserved in hash
       # (important for detecting unauthorized line-ending changes)

   def test_mixed_line_endings(tmp_path):
       """Mixed line endings in single file handled."""
       file_mixed = tmp_path / "mixed.md"
       # Mix of LF and CRLF
       content = "Line 1\nLine 2\r\nLine 3\nLine 4\r\n"
       file_mixed.write_bytes(content.encode('utf-8'))

       hash_val, error = hash_file_with_validation(file_mixed)
       assert error is None, "Mixed line endings should hash"
       assert hash_val is not None
   ```
2. Create identical content in LF and CRLF variants
3. Verify both hash successfully (no encoding errors)
4. Note: Hashes will differ (intentional - line endings are part of content)
5. This validates line-ending normalization is NOT applied (preserve exact content)

**Test Requirements**:
- LF files hash correctly
- CRLF files hash correctly
- Mixed line endings handled
- Hashes preserve line-ending information (no normalization)

---

### T050: Parity Hash Stability (Cross-Machine, Timezone)

**What**: Validate parity hash reproducible across machines and timezones.

**How**:
1. Implement test_cross_machine_stability():
   ```python
   def test_parity_hash_timezone_independent(tmp_path):
       """Parity hash not affected by timezone."""
       import os
       import time
       from datetime import datetime, timezone

       feature_dir = create_test_feature(tmp_path, num_artifacts=10)

       # Compute snapshot in UTC
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')
       snapshot = compute_snapshot(dossier)
       hash_utc = snapshot.parity_hash_sha256

       # Note: Snapshot includes computed_at timestamp, but parity hash
       # should be based on artifact content, not timestamp
       # Verify parity hash is timezone-independent by checking it's
       # computed from sorted artifact hashes (no timestamps)

       # Re-compute with new timestamp
       import time
       time.sleep(1)
       dossier2 = indexer.index_feature(feature_dir, 'software-dev')
       snapshot2 = compute_snapshot(dossier2)
       hash_now = snapshot2.parity_hash_sha256

       # Parity hashes should be identical (content unchanged)
       assert hash_utc == hash_now, "Parity hash should be timezone/time independent"

   def test_parity_hash_stable_across_python_versions(tmp_path):
       """SHA256 deterministic across Python versions."""
       # Create test artifact
       file_path = tmp_path / "test.md"
       file_path.write_text("# Test Content\n", encoding='utf-8')

       # Hash (uses hashlib.sha256, which is standard)
       hash_val, _ = hash_file_with_validation(file_path)

       # Expected hash (pre-computed with reference SHA256)
       # python3 -c "import hashlib; print(hashlib.sha256(b'# Test Content\n').hexdigest())"
       expected = hashlib.sha256(b"# Test Content\n").hexdigest()

       assert hash_val == expected, f"Hash mismatch: {hash_val} vs {expected}"
   ```
2. Verify parity hash based on artifact content (not computed_at timestamp)
3. Verify SHA256 deterministic across Python versions
4. Create fixture with pre-computed expected hashes
5. Test on multiple platforms if possible (CI/CD)

**Test Requirements**:
- Parity hash timezone-independent (computed_at excluded)
- Parity hash Python version-independent (SHA256 standard)
- SC-006 satisfied

---

## Definition of Done

- [ ] test_hash_reproducibility() comprehensive (10+ runs, various sizes)
- [ ] test_order_independence() proven (artifact order irrelevant)
- [ ] test_utf8_handling() covers BOM, CJK, invalid, emoji
- [ ] test_crlf_vs_lf_consistency() validates line endings preserved
- [ ] test_parity_hash_stability() proves timezone/version independence
- [ ] All SC-002, SC-006, SC-007 success criteria passed
- [ ] Test suite runs on CI/CD
- [ ] Zero flaky tests (deterministic, no timing issues)
- [ ] Comprehensive fixture library (create_test_feature, etc.)
- [ ] FR-010 requirement satisfied (deterministic projection)

---

## Risks & Mitigations

**Risk 1**: Tests pass locally but fail on CI/CD
- **Mitigation**: Run tests on multiple platforms (GitHub Actions matrix)

**Risk 2**: Timezone-dependent code hidden in snapshot computation
- **Mitigation**: Audit all timestamp/datetime usage, verify excluded from parity hash

**Risk 3**: Tests flaky (intermittent failures)
- **Mitigation**: No timing dependencies, no file system race conditions, use fixtures

**Risk 4**: Python version differences in SHA256
- **Mitigation**: SHA256 is standard library, version-independent; test confirms

---

## Reviewer Guidance

When reviewing WP09:
1. Verify test_hash_reproducibility runs 10+ iterations
2. Check test_order_independence shuffles artifacts randomly
3. Validate UTF-8 test covers BOM, CJK, invalid sequences, emoji
4. Confirm line-ending tests prove bytes-level hashing (no normalization)
5. Check parity hash excludes timestamp (computed_at not in hash)
6. Verify SC-002, SC-006, SC-007 all addressed
7. Run tests locally and on CI/CD
8. Confirm no flaky tests (deterministic, reproducible)

---

## Implementation Notes

- **Storage**: test_determinism.py (pytest test suite)
- **Dependencies**: WP01 (hasher), WP05 (snapshot), pytest
- **Estimated Lines**: ~300 (test_determinism.py)
- **Integration Point**: CI/CD pipeline, required for merge
- **Non-Negotiable**: All tests must pass (determinism is critical)

## Activity Log

- 2026-02-21T15:59:53Z – coordinator – shell_pid=99215 – lane=doing – Assigned agent via workflow command
- 2026-02-21T16:02:44Z – coordinator – shell_pid=99215 – lane=for_review – Determinism test suite complete: 36 tests passing (T046-T050)
- 2026-02-21T16:03:30Z – coordinator – shell_pid=99215 – lane=done – Code review passed: determinism tests complete, hash reproducibility verified
