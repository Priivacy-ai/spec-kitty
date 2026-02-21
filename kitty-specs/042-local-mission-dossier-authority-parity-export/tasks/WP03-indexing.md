---
work_package_id: WP03
title: Indexing & Missing Detection
lane: planned
dependencies: []
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
feature_slug: 042-local-mission-dossier-authority-parity-export
---

# WP03: Indexing & Missing Detection

**Objective**: Implement artifact scanner that recursively indexes feature directory, classifies artifacts using manifest definitions, detects missing required artifacts, and builds complete MissionDossier inventory. This WP converts filesystem into structured artifact catalog.

**Priority**: P1 (Core dossier functionality)

**Scope**:
- Artifact indexing (recursive directory scan)
- Artifact classification (deterministic, 6 classes)
- Missing artifact detection (required vs optional per manifest)
- Unreadable artifact handling (permission, encoding errors, deleted files)
- MissionDossier builder (aggregate indexed artifacts)
- Step-aware completeness checking

**Test Criteria**:
- Scans 30+ artifacts without errors
- Correctly identifies required vs optional
- Missing required artifacts flagged with reason codes
- Optional artifacts ignored if absent (no missing events)
- Unreadable artifacts recorded (not skipped silently)

---

## Context

After WP01 defines the ArtifactRef model and WP02 defines manifests, WP03 brings them together: scan feature directory, create ArtifactRef for each file found, compare against manifest requirements, and identify gaps. The indexer is the bridge between filesystem and dossier system.

**Key Requirements**:
- **FR-001**: System MUST index all artifact files and compute deterministic content_hash_sha256
- **FR-002**: System MUST support 6 artifact classes
- **FR-004**: System MUST detect missing required artifacts and emit events
- **FR-009**: System MUST never silently omit artifacts

**Mission Context**:
- Feature directory structure: spec.md, plan.md, tasks.md, tasks/*.md, etc.
- Hidden files/directories: ignore .git, .kittify, etc.
- Symlinks: handle gracefully (optional: follow or skip)

---

## Detailed Guidance

### T012: Implement Indexer.index_feature() Scanning Logic

**What**: Create Indexer class with index_feature() method for recursive directory scan.

**How**:
1. Create indexer.py in `src/specify_cli/dossier/indexer.py`
2. Define Indexer class:
   ```python
   class Indexer:
       def __init__(self, manifest_registry: ManifestRegistry):
           self.manifest_registry = manifest_registry
           self.artifacts: List[ArtifactRef] = []
           self.errors: List[dict] = []

       def index_feature(self, feature_dir: Path, mission_type: str, step_id: Optional[str] = None) -> MissionDossier:
           """Scan feature directory and build MissionDossier.

           Args:
               feature_dir: Path to feature directory
               mission_type: e.g., 'software-dev'
               step_id: Current mission step (e.g., 'plan'), for completeness check

           Returns:
               MissionDossier with all indexed artifacts
           """
           self.artifacts = []
           self.errors = []

           # Recursively scan feature directory
           for file_path in self._scan_directory(feature_dir):
               artifact = self._index_file(file_path, feature_dir, mission_type)
               if artifact:
                   self.artifacts.append(artifact)

           # Load manifest
           manifest = self.manifest_registry.load_manifest(mission_type)

           # Build MissionDossier
           dossier = MissionDossier(
               mission_slug=mission_type,
               mission_run_id=str(uuid.uuid4()),
               feature_slug=extract_feature_slug(feature_dir),
               feature_dir=str(feature_dir),
               artifacts=self.artifacts,
               manifest=manifest,
           )

           return dossier

       def _scan_directory(self, directory: Path) -> Iterator[Path]:
           """Recursively yield all files in directory (skip hidden/git)."""
           for item in directory.rglob("*"):
               # Skip hidden files/directories
               if any(part.startswith('.') for part in item.relative_to(directory).parts):
                   continue
               if item.is_file():
                   yield item

       def _index_file(self, file_path: Path, feature_dir: Path, mission_type: str) -> Optional[ArtifactRef]:
           """Index single file, return ArtifactRef or None if unindexable."""
           # Implemented in T013-T015
   ```
3. Handle errors gracefully (log, continue scan)
4. Return iterator (don't load all files in memory at once)

**Implementation Details**:
- Use `pathlib.Path.rglob()` for recursive scan
- Skip hidden files/dirs (names starting with .)
- Skip .git, .kittify directories explicitly
- Don't follow symlinks (optional enhancement post-042)
- Return Path objects (relative_to feature_dir in ArtifactRef)

**Test Requirements**:
- Scan feature directory with 30+ files, no errors
- Skip .git, .kittify directories
- Yield all non-hidden files
- Recursively traverse subdirectories

---

### T013: Artifact Classification

**What**: Implement deterministic artifact classification (6 classes).

**How**:
1. Add classification logic to Indexer._index_file():
   ```python
   def _classify_artifact(self, file_path: Path, manifest: Optional[ExpectedArtifactManifest]) -> str:
       """Deterministically classify artifact into one of 6 classes.

       Classes: input, workflow, output, evidence, policy, runtime

       Returns:
           One of the 6 classes (never "other" or unknown)
       """
       # Strategy 1: Check manifest definitions (if manifest exists)
       if manifest:
           for specs in (manifest.required_always + sum(manifest.required_by_step.values(), []) + manifest.optional_always):
               if self._matches_pattern(file_path, specs.path_pattern):
                   return specs.artifact_class

       # Strategy 2: Filename-based patterns (fallback)
       name = file_path.name.lower()
       if name in ['spec.md', 'specification.md']:
           return 'input'
       if name in ['plan.md']:
           return 'output'
       if name in ['tasks.md'] or name.startswith('wp') and name.endswith('.md'):
           return 'workflow'
       if 'test' in name or 'test_' in name:
           return 'evidence'
       if 'research' in name or 'gap-analysis' in name:
           return 'evidence'
       if 'requirements' in name or 'constraints' in name:
           return 'policy'

       # Strategy 3: Fail explicitly if can't classify (no "other" fallback)
       raise ValueError(f"Cannot classify artifact: {file_path} (not in manifest, no pattern match)")

   def _matches_pattern(self, file_path: Path, pattern: str) -> bool:
       """Check if file_path matches glob pattern."""
       import fnmatch
       relative = file_path.name  # Simple match on filename
       return fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(str(file_path), pattern)
   ```
2. Ensure classification is deterministic (same file, always same class)
3. Never return "other" or unknown class (fail explicitly if can't classify)
4. Log classification reasoning

**Classification Rules**:
- **input**: spec.md, requirements.md, research.md
- **workflow**: plan.md, tasks.md, tasks/*.md, mission artifacts
- **output**: implementation artifacts, reports, findings.md
- **evidence**: test files, research logs, gap-analysis.md
- **policy**: constraints.md, requirements-nonfunctional.md
- **runtime**: generated files, logs, runtime state

**Test Requirements**:
- Classify spec.md → input
- Classify plan.md → output
- Classify tasks.md → workflow
- Classify research.md → evidence
- Fail explicitly if artifact doesn't match any pattern
- Deterministic (same file, always same class)

---

### T014: Missing Artifact Detection

**What**: Compare indexed artifacts against manifest requirements, identify gaps.

**How**:
1. Add method to Indexer:
   ```python
   def _detect_missing_artifacts(self, dossier: MissionDossier, step_id: Optional[str] = None) -> List[ArtifactRef]:
       """Detect required artifacts that are not present.

       Returns:
           List of "ghost" ArtifactRef objects (is_present=False) for each missing artifact
       """
       if not dossier.manifest:
           return []  # No manifest, can't detect missing

       # Get required artifacts for current step
       required_specs = dossier.manifest.required_always
       if step_id:
           required_specs += dossier.manifest.required_by_step.get(step_id, [])

       # Check each required spec
       missing = []
       for spec in required_specs:
           # Check if any indexed artifact matches this spec
           matched = False
           for artifact in dossier.artifacts:
               if artifact.artifact_key == spec.artifact_key:
                   matched = True
                   break

           if not matched:
               # Create "ghost" artifact ref (missing)
               ghost = ArtifactRef(
                   artifact_key=spec.artifact_key,
                   artifact_class=spec.artifact_class,
                   relative_path=spec.path_pattern,
                   content_hash_sha256=None,
                   size_bytes=0,
                   required_status='required',
                   is_present=False,
                   error_reason='not_found',
                   indexed_at=datetime.utcnow(),
               )
               missing.append(ghost)

       return missing
   ```
2. Link detected missing artifacts to dossier for event emission (handled in WP04)
3. Distinguish between required and optional (blocking vs non-blocking)

**Missing Reason Codes**:
- "not_found": Required artifact expected but filesystem scan found no match
- "unreadable": Found but couldn't read (permission, I/O error)
- "invalid_format": Found but failed validation (encoding error, malformed)
- "deleted_after_scan": Found during scan but deleted before hashing

**Test Requirements**:
- Missing required artifact detected (reason="not_found")
- Missing optional artifact not flagged
- Multiple missing artifacts detected
- Blocking field correctly set

---

### T015: Unreadable Artifact Handling

**What**: Gracefully handle artifacts that can't be read.

**How**:
1. Wrap file operations in try-catch:
   ```python
   def _index_file(self, file_path: Path, feature_dir: Path, mission_type: str) -> Optional[ArtifactRef]:
       """Index single file, handle read errors gracefully."""
       relative_path = str(file_path.relative_to(feature_dir))
       artifact_key = self._derive_artifact_key(file_path, mission_type)

       try:
           # Try to read and hash
           file_hash, error_reason = hash_file_with_validation(file_path)
           if error_reason:
               # UTF-8 validation failed
               return ArtifactRef(
                   artifact_key=artifact_key,
                   artifact_class=self._classify_artifact(file_path),
                   relative_path=relative_path,
                   content_hash_sha256=None,
                   size_bytes=file_path.stat().st_size,
                   required_status='optional',
                   is_present=False,
                   error_reason=error_reason,
               )

           # Successfully hashed
           return ArtifactRef(
               artifact_key=artifact_key,
               artifact_class=self._classify_artifact(file_path),
               relative_path=relative_path,
               content_hash_sha256=file_hash,
               size_bytes=file_path.stat().st_size,
               required_status=self._get_required_status(artifact_key),
               is_present=True,
               error_reason=None,
           )

       except PermissionError:
           return ArtifactRef(..., is_present=False, error_reason='unreadable')
       except IOError:
           return ArtifactRef(..., is_present=False, error_reason='unreadable')
       except OSError:
           return ArtifactRef(..., is_present=False, error_reason='unreadable')
   ```
2. Record error_reason on ArtifactRef
3. Continue scan (no silent failures)
4. Log all errors

**Error Scenarios**:
- Permission denied: error_reason="unreadable"
- File deleted after iteration start: error_reason="unreadable"
- I/O error (disk issues): error_reason="unreadable"
- Invalid UTF-8: error_reason="invalid_utf8"
- File size too large (optional limit): error_reason="size_limit"

**Test Requirements**:
- Unreadable artifact (no read permission) recorded with error_reason="unreadable"
- Invalid UTF-8 file recorded with error_reason="invalid_utf8"
- Scan continues after errors (no exception thrown)
- All errors logged

---

### T016: MissionDossier Builder

**What**: Aggregate indexed artifacts and missing artifacts into complete MissionDossier.

**How**:
1. In Indexer.index_feature(), build MissionDossier:
   ```python
   def index_feature(self, feature_dir: Path, mission_type: str, step_id: Optional[str] = None) -> MissionDossier:
       """Build complete MissionDossier from indexed artifacts."""
       # Scan and index
       self.artifacts = []
       for file_path in self._scan_directory(feature_dir):
           artifact = self._index_file(file_path, feature_dir, mission_type)
           if artifact:
               self.artifacts.append(artifact)

       # Load manifest
       manifest = self.manifest_registry.load_manifest(mission_type)

       # Detect missing artifacts
       dossier = MissionDossier(
           mission_slug=mission_type,
           mission_run_id=str(uuid.uuid4()),
           feature_slug=extract_feature_slug(feature_dir),
           feature_dir=str(feature_dir),
           artifacts=self.artifacts,
           manifest=manifest,
       )

       # Add missing artifacts
       missing = self._detect_missing_artifacts(dossier, step_id)
       dossier.artifacts.extend(missing)

       # Update timestamp
       dossier.dossier_updated_at = datetime.utcnow()

       return dossier
   ```
2. MissionDossier should include all artifacts (present + missing + unreadable)
3. Completeness status automatically computed by MissionDossier.completeness_status

**Test Requirements**:
- Dossier includes all indexed artifacts
- Dossier includes missing artifacts (is_present=False)
- Completeness status correctly computed
- Timestamps accurate

---

### T017: Step-Aware Completeness Checking

**What**: Implement logic to check completeness for specific mission step.

**How**:
1. Add method to MissionDossier (from data-model.md):
   ```python
   def get_required_artifacts(self, step_id: Optional[str] = None) -> List[ArtifactRef]:
       """Return required artifacts for step (or all required if step_id=None)."""
       if not self.manifest:
           return []

       required_specs = self.manifest.required_always
       if step_id:
           required_specs += self.manifest.required_by_step.get(step_id, [])

       # Match specs against indexed artifacts
       required_artifacts = []
       for spec in required_specs:
           for artifact in self.artifacts:
               if artifact.artifact_key == spec.artifact_key:
                   required_artifacts.append(artifact)
                   break

       return required_artifacts

   def get_missing_required_artifacts(self, step_id: Optional[str] = None) -> List[ArtifactRef]:
       """Return required artifacts that are not present."""
       required = self.get_required_artifacts(step_id)
       return [a for a in required if not a.is_present]

   @property
   def completeness_status(self) -> str:
       """Return 'complete', 'incomplete', or 'unknown'."""
       if not self.manifest:
           return 'unknown'
       missing = self.get_missing_required_artifacts()
       return 'complete' if not missing else 'incomplete'
   ```
2. Completeness is step-aware (depends on step_id passed)
3. Optional artifacts never affect completeness

**Test Requirements**:
- completeness_status='complete' when all required present
- completeness_status='incomplete' when any required missing
- completeness_status='unknown' when no manifest
- Optional artifacts don't affect status
- Step-specific checks work correctly

---

## Definition of Done

- [ ] Indexer class created, index_feature() scans recursively
- [ ] Artifact classification implemented, deterministic, never returns "other"
- [ ] Missing artifact detection identifies gaps vs manifest
- [ ] Unreadable artifacts handled gracefully (error_reason recorded)
- [ ] MissionDossier builder aggregates all artifacts (present + missing)
- [ ] Step-aware completeness checking implemented
- [ ] All hidden files/directories skipped (.git, .kittify, etc.)
- [ ] 30+ artifact test suite passing
- [ ] Zero silent failures (all errors explicit)
- [ ] FR-001, FR-002, FR-004, FR-009 requirements satisfied

---

## Risks & Mitigations

**Risk 1**: Hidden files indexed when they shouldn't be
- **Mitigation**: Explicit skip of hidden dirs (names starting with .)

**Risk 2**: Symlinks cause issues (loops, permission errors)
- **Mitigation**: Don't follow symlinks (deferred post-042 enhancement)

**Risk 3**: Classification fails for unknown artifacts
- **Mitigation**: Fail explicitly (raise exception), don't return "other"

**Risk 4**: Concurrent file deletion during scan
- **Mitigation**: Catch FileNotFoundError, mark as unreadable

**Risk 5**: Large feature directories (1000s of files) slow indexing
- **Mitigation**: Use iterator (don't load all in memory); SC-005 validates performance

---

## Reviewer Guidance

When reviewing WP03:
1. Verify Indexer recursively scans feature directory (Path.rglob)
2. Check artifact classification deterministic (same file, always same class)
3. Confirm classification never returns "other" (fail explicitly)
4. Verify missing artifact detection compares against manifest requirements
5. Check unreadable artifacts recorded with error_reason (not skipped)
6. Confirm MissionDossier includes all artifacts (present + missing + unreadable)
7. Validate step-aware completeness (optional artifacts don't affect status)
8. Test with 30+ artifacts, verify no errors
9. Confirm FR-001, FR-004 requirements satisfied

---

## Implementation Notes

- **Storage**: indexer.py (Indexer class)
- **Dependencies**: WP01 (ArtifactRef, hash_file), WP02 (ManifestRegistry)
- **Estimated Lines**: ~400 (indexer.py + tests)
- **Integration Point**: WP04 will use MissionDossier for event emission
- **Performance**: <1s for 30 artifacts (SC-001)
