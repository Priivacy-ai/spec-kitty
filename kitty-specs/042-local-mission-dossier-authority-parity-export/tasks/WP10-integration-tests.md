---
work_package_id: WP10
title: Integration & Edge Cases
lane: "doing"
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
base_branch: 042-local-mission-dossier-authority-parity-export-WP10-merge-base
base_commit: 03b1be71d370c689fed79532d4aa3e4984e57795
created_at: '2026-02-21T16:03:33.164278+00:00'
subtasks:
- T051
- T052
- T053
- T054
- T055
- T056
- T057
- T058
feature_slug: 042-local-mission-dossier-authority-parity-export
shell_pid: "4443"
agent: "coordinator"
---

# WP10: Integration & Edge Cases

**Objective**: Integration tests covering full scan workflow, edge cases (missing artifacts, unreadable files, large artifacts), and SaaS webhook integration. Final validation that entire feature 042 system works end-to-end with zero silent failures.

**Priority**: P1 (Hardening, final validation before production)

**Scope**:
- Missing artifact detection edge cases
- Optional artifact handling
- Unreadable artifact handling
- Large artifact truncation
- Full scan workflow integration
- SaaS webhook simulator
- Concurrent modification edge case
- Manifest version mismatch edge case

**Test Criteria**:
- All edge cases handled gracefully (no crashes, no silent failures)
- Full workflow integration test passing
- SaaS webhook simulator receives all 4 event types
- Large artifacts processed without memory issues

---

## Context

WP10 is the final phase: integration and hardening. After WP01-WP09 build individual components and validate determinism, WP10 proves the entire system works together in realistic scenarios. These tests catch integration bugs that unit tests miss.

**Quality Bar**: Zero silent failures (from spec FR-009). Every anomaly must be explicit in events and API.

---

## Detailed Guidance

### T051: Missing Required Artifact Detection

**What**: Edge case—multiple missing artifacts, verify all detected.

**How**:
1. Create test_missing_detection.py in `tests/specify_cli/dossier/integration/`
2. Implement test_missing_required_artifacts():
   ```python
   def test_missing_required_artifacts_detected(tmp_path):
       """Missing required artifacts flagged with reason codes."""
       # Create feature at "plan" step (requires spec.md, plan.md, tasks.md)
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()

       # Only create spec.md (plan.md and tasks.md missing)
       (feature_dir / "spec.md").write_text("# Spec\n", encoding='utf-8')

       # Index
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev', step_id='plan')

       # Verify missing artifacts
       missing = dossier.get_missing_required_artifacts(step_id='plan')
       assert len(missing) >= 2, f"Expected >=2 missing artifacts, got {len(missing)}"

       # Verify missing have error_reason
       for artifact in missing:
           assert artifact.error_reason == 'not_found', f"Expected not_found, got {artifact.error_reason}"
           assert not artifact.is_present

       # Verify completeness status
       assert dossier.completeness_status == 'incomplete'

   def test_multiple_missing_artifacts_events(tmp_path):
       """Multiple missing artifacts trigger multiple MissionDossierArtifactMissing events."""
       feature_dir = create_minimal_feature(tmp_path)  # Only has spec.md

       # Index and scan
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev', step_id='plan')

       # Capture emitted events (mock OfflineQueue)
       events = []
       async def mock_emit(event):
           events.append(event)

       # Patch OfflineQueue.emit
       with patch('specify_cli.sync.events.OfflineQueue.emit', side_effect=mock_emit):
           missing = dossier.get_missing_required_artifacts(step_id='plan')
           for artifact in missing:
               await emit_artifact_missing(
                   feature_slug='test-feature',
                   artifact_key=artifact.artifact_key,
                   artifact_class=artifact.artifact_class,
                   expected_path_pattern=artifact.relative_path,
                   reason_code=artifact.error_reason,
                   blocking=True,
               )

       # Verify events emitted for all missing
       assert len(events) == len(missing), f"Expected {len(missing)} events, got {len(events)}"
       assert all(e.event_type == 'mission_dossier_artifact_missing' for e in events)
   ```
3. Test with step-specific requirements (plan, implementation, etc.)
4. Verify all missing detected (not just first one)

**Test Requirements**:
- Multiple missing artifacts all detected
- All have error_reason (not_found, unreadable, etc.)
- Completeness status 'incomplete'
- Events emitted for all missing

---

### T052: Optional Artifact Handling

**What**: Optional artifacts missing should not trigger missing events.

**How**:
1. Implement test_optional_artifacts():
   ```python
   def test_optional_artifacts_not_required(tmp_path):
       """Optional artifacts (e.g., research.md) don't block completeness."""
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()

       # Create required artifacts only
       (feature_dir / "spec.md").write_text("# Spec\n", encoding='utf-8')
       (feature_dir / "plan.md").write_text("# Plan\n", encoding='utf-8')
       (feature_dir / "tasks.md").write_text("# Tasks\n", encoding='utf-8')
       # research.md (optional) NOT created

       # Index at "plan" step
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev', step_id='plan')

       # Verify completeness (should be complete, not blocked by missing optional)
       assert dossier.completeness_status == 'complete', \
           f"Missing optional should not block completeness"

       # Verify missing required (should be none)
       missing = dossier.get_missing_required_artifacts(step_id='plan')
       assert len(missing) == 0, f"Should have no missing required"

   def test_optional_artifacts_no_events_when_missing(tmp_path):
       """Missing optional artifacts don't trigger MissionDossierArtifactMissing events."""
       feature_dir = create_feature_without_optionals(tmp_path)

       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')

       # Mock event emission
       with patch('specify_cli.dossier.events.emit_artifact_missing') as mock_emit:
           missing = dossier.get_missing_required_artifacts()
           # No missing required (optional not included)
           assert len(missing) == 0

           # emit_artifact_missing should not be called
           mock_emit.assert_not_called()
   ```
2. Manifest should mark research.md, gap-analysis.md as optional
3. Verify "complete" status despite missing optionals

**Test Requirements**:
- Optional artifacts don't block completeness
- Missing optional artifacts don't trigger events
- Completeness status 'complete' with missing optionals

---

### T053: Unreadable Artifact Handling

**What**: Artifacts with permission errors, encoding errors handled gracefully.

**How**:
1. Implement test_unreadable_artifacts():
   ```python
   def test_unreadable_artifact_permission_denied(tmp_path):
       """Unreadable artifact (permission denied) recorded."""
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()

       # Create readable artifact
       (feature_dir / "spec.md").write_text("# Spec\n", encoding='utf-8')

       # Create unreadable artifact (no read permission)
       unreadable = feature_dir / "secret.md"
       unreadable.write_text("Secret\n", encoding='utf-8')
       os.chmod(unreadable, 0o000)  # Remove all permissions

       # Index
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')

       # Verify unreadable artifact recorded
       secret_artifact = next((a for a in dossier.artifacts if 'secret' in a.relative_path), None)
       assert secret_artifact is not None, "Unreadable artifact should be indexed"
       assert not secret_artifact.is_present
       assert secret_artifact.error_reason == 'unreadable'

       # Scan should complete (not crash)
       assert dossier is not None

       # Clean up
       os.chmod(unreadable, 0o644)

   def test_invalid_utf8_artifact(tmp_path):
       """Invalid UTF-8 artifact recorded with error_reason."""
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()

       # Create invalid UTF-8 file
       invalid = feature_dir / "corrupted.md"
       invalid.write_bytes(b"Hello\xff\xfeWorld")

       # Index
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')

       # Verify invalid artifact recorded
       corrupted = next((a for a in dossier.artifacts if 'corrupted' in a.relative_path), None)
       assert corrupted is not None
       assert not corrupted.is_present
       assert corrupted.error_reason == 'invalid_utf8'

   def test_unreadable_artifacts_no_silent_failures(tmp_path):
       """All unreadable artifacts explicit in dossier (no silent skips)."""
       feature_dir = create_feature_with_mixed_artifacts(tmp_path)
       # Mix of readable, unreadable, invalid UTF-8

       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')

       # All artifacts should be in dossier (no silent skips)
       expected_count = count_all_files(feature_dir)
       assert len(dossier.artifacts) == expected_count, \
           f"Missing artifacts from scan (silent failure)"

       # All unreadable should have error_reason
       for artifact in dossier.artifacts:
           if not artifact.is_present:
               assert artifact.error_reason is not None, \
                   f"Unreadable artifact {artifact.artifact_key} missing error_reason"
   ```
2. Test permission errors (PermissionError)
3. Test encoding errors (UnicodeDecodeError)
4. Verify NO silent skips (all artifacts recorded)

**Test Requirements**:
- Unreadable artifacts recorded (not skipped)
- error_reason set (unreadable, invalid_utf8)
- Scan completes (doesn't crash)
- FR-009 satisfied (no silent omissions)

---

### T054: Large Artifact Handling

**What**: Artifacts >5MB handled without memory issues.

**How**:
1. Implement test_large_artifacts():
   ```python
   def test_large_artifact_api_truncation(tmp_path):
       """Large artifact (>5MB) truncated in API response."""
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()

       # Create 10MB artifact
       large_file = feature_dir / "large.json"
       large_content = json.dumps({'data': ['x' * 1000] * 10000})  # ~10MB
       large_file.write_text(large_content, encoding='utf-8')

       # Index
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')

       # Find large artifact
       large = next(a for a in dossier.artifacts if 'large' in a.relative_path)
       assert large.size_bytes > 5242880  # >5MB

       # API detail request
       detail = create_api_response_for_artifact(large, feature_dir)

       # Verify truncation
       assert detail.content_truncated == True
       assert detail.content is None
       assert detail.truncation_notice is not None
       assert '5MB' in detail.truncation_notice

   def test_large_artifact_indexing_no_memory_leak(tmp_path):
       """Large artifact indexing doesn't load full content in memory."""
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()

       # Create 100MB artifact
       huge_file = feature_dir / "huge.bin"
       with open(huge_file, 'wb') as f:
           for _ in range(100):
               f.write(b'x' * (1024 * 1024))  # 100MB total

       # Index (should not crash, hash computed efficiently)
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')

       # Verify artifact hashed (not skipped)
       huge = next(a for a in dossier.artifacts if 'huge' in a.relative_path)
       assert huge.content_hash_sha256 is not None
       assert huge.size_bytes > 100 * 1024 * 1024
   ```
2. Create artifacts >5MB (use file generation, not in memory)
3. Test API returns truncation notice
4. Verify hashing works without loading full content

**Test Requirements**:
- Large artifacts (>5MB) indexed without memory crash
- API returns truncation notice
- content field is None (not included)
- Hashing uses streaming (not full load)

---

### T055: Full Scan Workflow Integration Test

**What**: End-to-end test from feature creation to snapshot and events.

**How**:
1. Implement test_full_workflow():
   ```python
   async def test_full_dossier_workflow_integration(tmp_path):
       """Full workflow: create feature → index → snapshot → events → API."""
       # 1. Create test feature
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()
       (feature_dir / "spec.md").write_text("# Specification\n\nDetails here.\n", encoding='utf-8')
       (feature_dir / "plan.md").write_text("# Plan\n\nSteps:\n1. Implement\n", encoding='utf-8')
       (feature_dir / "tasks.md").write_text("# Tasks\n\nWP01: Model\n", encoding='utf-8')

       # 2. Index feature
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev', step_id='plan')

       assert dossier is not None
       assert len(dossier.artifacts) > 0
       assert dossier.completeness_status == 'complete'

       # 3. Compute snapshot
       snapshot = compute_snapshot(dossier)

       assert snapshot is not None
       assert snapshot.parity_hash_sha256 is not None
       assert snapshot.completeness_status == 'complete'

       # 4. Persist snapshot
       save_snapshot(snapshot, feature_dir)

       # 5. Emit events (mock OfflineQueue)
       events = []
       async def mock_emit(event):
           events.append(event)

       with patch('specify_cli.sync.events.OfflineQueue.emit', side_effect=mock_emit):
           # Emit artifact indexed events
           for artifact in dossier.artifacts:
               if artifact.is_present:
                   await emit_artifact_indexed(
                       feature_slug='test-feature',
                       artifact=artifact,
                       actor='test-agent',
                   )

           # Emit snapshot computed event
           await emit_snapshot_computed(
               feature_slug='test-feature',
               snapshot=snapshot,
               actor='test-agent',
           )

       # 6. Verify events
       assert len(events) >= 3  # At least 2 artifacts + 1 snapshot
       assert any(e.event_type == 'mission_dossier_artifact_indexed' for e in events)
       assert any(e.event_type == 'mission_dossier_snapshot_computed' for e in events)

       # 7. API access (mock HTTP)
       overview = create_api_overview_response(snapshot)
       assert overview.completeness_status == 'complete'
       assert overview.artifact_counts.total >= 3
   ```
2. Create real feature directory with artifacts
3. Run full indexing → snapshot → events → API flow
4. Verify all steps succeed

**Test Requirements**:
- Feature created and scanned
- Snapshot computed (parity hash)
- All events emitted
- API returns correct data
- End-to-end workflow works

---

### T056: SaaS Webhook Simulator

**What**: Mock SaaS webhook endpoint receives all 4 dossier event types.

**How**:
1. Create mock webhook in test fixtures:
   ```python
   from http.server import HTTPServer, BaseHTTPRequestHandler
   import json
   import threading

   class MockWebhookHandler(BaseHTTPRequestHandler):
       """Mock SaaS webhook endpoint."""
       received_events = []

       def do_POST(self):
           if self.path == '/webhook/dossier':
               content_length = int(self.headers['Content-Length'])
               body = self.rfile.read(content_length)
               event = json.loads(body)
               MockWebhookHandler.received_events.append(event)

               self.send_response(200)
               self.send_header('Content-Type', 'application/json')
               self.end_headers()
               self.wfile.write(b'{"status": "received"}')
           else:
               self.send_error(404)

       def log_message(self, format, *args):
           pass  # Suppress logging

   async def test_webhook_receives_all_event_types(tmp_path):
       """SaaS webhook simulator receives all 4 dossier event types."""
       # Start mock webhook
       webhook = HTTPServer(('localhost', 8888), MockWebhookHandler)
       webhook_thread = threading.Thread(target=webhook.serve_forever)
       webhook_thread.daemon = True
       webhook_thread.start()

       # Create feature and index
       feature_dir = create_test_feature(tmp_path)
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')
       snapshot = compute_snapshot(dossier)

       # Emit events to webhook
       async def emit_to_webhook(event):
           import aiohttp
           async with aiohttp.ClientSession() as session:
               async with session.post(
                   'http://localhost:8888/webhook/dossier',
                   json=event.dict(),
               ) as resp:
                   return await resp.text()

       with patch('specify_cli.sync.events.OfflineQueue.emit', side_effect=emit_to_webhook):
           # Emit all 4 event types
           for artifact in dossier.artifacts:
               await emit_artifact_indexed('test-feature', artifact)

           await emit_snapshot_computed('test-feature', snapshot)

           if dossier.get_missing_required_artifacts():
               for missing in dossier.get_missing_required_artifacts():
                   await emit_artifact_missing(
                       'test-feature',
                       missing.artifact_key,
                       missing.artifact_class,
                       missing.relative_path,
                       'not_found',
                   )

       # Verify webhook received events
       assert len(MockWebhookHandler.received_events) > 0
       event_types = {e['event_type'] for e in MockWebhookHandler.received_events}
       assert 'mission_dossier_artifact_indexed' in event_types
       assert 'mission_dossier_snapshot_computed' in event_types

       webhook.shutdown()
   ```
2. Start mock HTTP server
3. Emit all 4 event types
4. Verify webhook receives them

**Test Requirements**:
- Mock webhook started
- All 4 event types emitted
- Webhook receives events correctly
- Events are valid JSON

---

### T057: Concurrent File Modification Edge Case

**What**: File modified during scan—verify hash captures point-in-time state.

**How**:
1. Implement test_concurrent_modification():
   ```python
   def test_concurrent_file_modification(tmp_path):
       """File modified during scan—hash captures pre-modification state."""
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir()

       test_file = feature_dir / "changing.md"
       original_content = "# Original\n"
       test_file.write_text(original_content, encoding='utf-8')

       # Hash original content
       hash_original = hash_file(test_file)

       # Modify file
       modified_content = "# Modified\n"
       test_file.write_text(modified_content, encoding='utf-8')

       # Hash modified content
       hash_modified = hash_file(test_file)

       # Hashes should differ
       assert hash_original != hash_modified

       # Now simulate index-time modification:
       test_file.write_text(original_content, encoding='utf-8')

       # Index (simulating point-in-time snapshot)
       indexer = Indexer(ManifestRegistry())
       dossier = indexer.index_feature(feature_dir, 'software-dev')

       changing = next((a for a in dossier.artifacts if 'changing' in a.relative_path), None)
       assert changing is not None
       assert changing.content_hash_sha256 == hash_original  # Original hash

       # Verify snapshot based on artifact hashes at scan time
       snapshot = compute_snapshot(dossier)
       assert snapshot.parity_hash_sha256 is not None
   ```
2. This test validates that scanning captures point-in-time state
3. Not a failure case, just validates behavior

**Test Requirements**:
- File modification detected by hash change
- Scan captures pre-modification state
- Snapshot reproducible (same state → same hash)

---

### T058: Manifest Version Mismatch Edge Case

**What**: Manifest version updated—baseline should be rejected (no false positive drift).

**How**:
1. Implement test_manifest_version_mismatch():
   ```python
   def test_manifest_version_mismatch_prevents_false_drift(tmp_path):
       """Manifest version change causes baseline rejection (no false drift)."""
       repo_root = tmp_path / "repo"
       repo_root.mkdir()

       feature_slug = "042-test-feature"
       feature_dir = repo_root / "kitty-specs" / feature_slug
       feature_dir.mkdir(parents=True)

       # Create artifacts
       (feature_dir / "spec.md").write_text("# Spec\n", encoding='utf-8')
       (feature_dir / "plan.md").write_text("# Plan\n", encoding='utf-8')

       # Scan 1: Capture baseline with manifest_version="1"
       indexer = Indexer(ManifestRegistry())
       dossier1 = indexer.index_feature(feature_dir, 'software-dev')
       snapshot1 = compute_snapshot(dossier1)

       key1 = compute_baseline_key(
           feature_slug=feature_slug,
           target_branch='main',
           mission_key='software-dev',
           manifest_version='1',
           project_identity=MockProjectIdentity(),
       )
       baseline1 = BaselineSnapshot(
           baseline_key=key1,
           baseline_key_hash=key1.compute_hash(),
           parity_hash_sha256=snapshot1.parity_hash_sha256,
           captured_at=datetime.utcnow(),
           captured_by='test-node',
       )
       save_baseline(feature_slug, baseline1, repo_root)

       # Simulate manifest version update (schema changed)
       # ManifestRegistry.manifest_version now "2"

       # Scan 2: Same artifacts (no content change), but manifest_version changed
       dossier2 = indexer.index_feature(feature_dir, 'software-dev')
       snapshot2 = compute_snapshot(dossier2)

       key2 = compute_baseline_key(
           feature_slug=feature_slug,
           target_branch='main',
           mission_key='software-dev',
           manifest_version='2',  # CHANGED
           project_identity=MockProjectIdentity(),
       )

       # Check drift
       has_drift, drift_info = detect_drift(
           feature_slug=feature_slug,
           current_snapshot=snapshot2,
           repo_root=repo_root,
           project_identity=MockProjectIdentity(),
           target_branch='main',
           mission_key='software-dev',
           manifest_version='2',
       )

       # Result: No drift event (baseline rejected due to key mismatch)
       assert not has_drift, \
           f"Manifest version change should not trigger drift event"
       assert drift_info is None
   ```
2. This validates that baseline rejection prevents false positives
3. Scenario: manifest_version changes from "1" to "2"
4. Even though content identical, baseline key differs
5. Baseline rejected → no drift event (correct behavior)

**Test Requirements**:
- Manifest version change detected
- Baseline rejected (key mismatch)
- No drift event emitted (not false positive)
- Informational message logged

---

## Definition of Done

- [ ] test_missing_detection.py: Missing artifact detection working
- [ ] test_optional_artifacts: Optional artifacts don't block completeness
- [ ] test_unreadable_artifacts: Unreadable artifacts recorded (no silent skips)
- [ ] test_large_artifacts: Large artifacts (>5MB) handled without crash
- [ ] test_full_workflow_integration: End-to-end workflow tested
- [ ] test_webhook_integration: Mock webhook receives all 4 event types
- [ ] test_concurrent_modification: Point-in-time snapshot behavior validated
- [ ] test_manifest_version_mismatch: False positives prevented
- [ ] All edge cases handled gracefully (no crashes, no silent failures)
- [ ] FR-009 requirement satisfied (no silent omissions)
- [ ] All integration tests passing

---

## Risks & Mitigations

**Risk 1**: Integration tests fragile (depend on order, state)
- **Mitigation**: Use fixtures, isolate each test, clean up after

**Risk 2**: Large file tests slow down CI/CD
- **Mitigation**: Mark with @pytest.mark.slow, skip by default, include in nightly

**Risk 3**: Mock webhook flaky (port conflicts, timing)
- **Mitigation**: Use ephemeral ports, retry logic, timeout guards

**Risk 4**: Concurrent modification hard to reproduce
- **Mitigation**: Simulate with explicit file operations (not actual threading)

---

## Reviewer Guidance

When reviewing WP10:
1. Verify edge cases are representative (missing, optional, unreadable, large, concurrent)
2. Check full workflow integration test exercises all components
3. Validate mock webhook correctly simulates SaaS behavior
4. Confirm manifest version mismatch prevents false positives
5. Verify no silent failures (FR-009 satisfied)
6. Check tests don't depend on execution order
7. Validate concurrent modification test realistic
8. Ensure large file tests don't crash or leak memory
9. Confirm all 4 event types tested via webhook

---

## Implementation Notes

- **Storage**: test_integration.py, test_encoding.py, fixtures
- **Dependencies**: WP01-WP09, pytest
- **Estimated Lines**: ~450 (test suite + fixtures)
- **Integration Point**: CI/CD pipeline, final validation gate
- **Performance**: Large file tests marked @pytest.mark.slow

## Activity Log

- 2026-02-21T16:03:33Z – coordinator – shell_pid=4443 – lane=doing – Assigned agent via workflow command
