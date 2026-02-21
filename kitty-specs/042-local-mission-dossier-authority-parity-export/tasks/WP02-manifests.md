---
work_package_id: "WP02"
title: "Expected Artifact Manifests"
feature_slug: 042-local-mission-dossier-authority-parity-export
lane: planned
dependencies: []
subtasks:
  - T006
  - T007
  - T008
  - T009
  - T010
  - T011
---

# WP02: Expected Artifact Manifests

**Objective**: Design manifest schema (YAML-based) and create v1 manifests for software-dev, research, and documentation missions. Manifests define which artifacts are required/optional at each mission step, enabling completeness checking and missing-artifact detection.

**Priority**: P1 (Foundation for completeness checking)

**Scope**:
- Manifest schema design (required_always, required_by_step, optional_always)
- ManifestRegistry loader (reads mission.yaml states)
- 3 mission-specific expected-artifacts.yaml files
- Manifest validation (step existence, path pattern validation)
- Integration with mission.yaml state machine

**Test Criteria**:
- Manifest loads from YAML without errors
- Registry correctly maps step names to artifact lists
- Unknown missions handled gracefully (return None)
- Step-aware completeness checking works
- All manifest paths exist in respective missions

---

## Context

Feature 042's dossier system needs to know which artifacts are required at any given point in a mission workflow. Unlike hardcoded phases, manifests are mission-aware: they read from mission.yaml state machine and define requirements per step (e.g., "specify" → requires spec.md, "planning" → requires plan.md, "implementation" → requires code changes).

**Key Requirements**:
- **FR-003**: System MUST define expected-artifact manifests per mission type, step-aware
- **FR-004**: System MUST detect missing required artifacts and emit MissionDossierArtifactMissing events
- **Assumption 1**: Expected artifact manifests are defined in mission templates (not hard-coded)

**Mission Context**:
- software-dev: States include "discover", "specify", "plan", "implement", "review", "done"
- research: States include "scoping", "methodology", "gathering", "synthesis", "output", "done"
- documentation: Mission-specific states

---

## Detailed Guidance

### T006: Design Manifest Schema

**What**: Define YAML schema for expected artifact manifests.

**How**:
1. Create schema structure with 3 top-level sections:
   ```yaml
   schema_version: "1.0"
   mission_type: "software-dev"  # or "research", "documentation"
   manifest_version: "1"

   required_always:
     - artifact_key: "..."
       artifact_class: "..."
       path_pattern: "..."
       blocking: true/false

   required_by_step:
     discover:
       - artifact_key: "..."
         artifact_class: "..."
         path_pattern: "..."
         blocking: true/false
     specify:
       - ...
     # More steps as mission defines

   optional_always:
     - artifact_key: "..."
       artifact_class: "..."
       path_pattern: "..."
   ```
2. Define validation rules:
   - artifact_key: Stable, unique, format "class.category.qualifier" (e.g., "input.spec.main")
   - artifact_class: One of {input, workflow, output, evidence, policy, runtime}
   - path_pattern: Glob pattern relative to feature dir (e.g., "spec.md", "tasks/*.md")
   - blocking: If true, missing artifact blocks completeness; if false, non-blocking
   - Step names: MUST match mission.yaml state IDs (validated in T011)

3. Document design decisions:
   - **Step-aware over phase-locked**: Uses mission.yaml state machine, not hardcoded phases
   - **Order-independent**: Artifacts can be indexed in any order; manifest defines requirements
   - **Blocking semantics**: Some artifacts (spec.md) block completeness; others (research.md) don't
   - **Extensibility**: Path patterns support wildcards; easy to add new steps

4. Add comprehensive docstring and examples in schema

**Schema Example**:
```yaml
# software-dev expected-artifacts.yaml
schema_version: "1.0"
mission_type: "software-dev"
manifest_version: "1"

required_always:
  - artifact_key: "meta.feature.definition"
    artifact_class: "workflow"
    path_pattern: "spec.md"
    blocking: true

required_by_step:
  specify:
    - artifact_key: "input.spec.main"
      artifact_class: "input"
      path_pattern: "spec.md"
      blocking: true

  plan:
    - artifact_key: "output.plan.main"
      artifact_class: "output"
      path_pattern: "plan.md"
      blocking: true
    - artifact_key: "output.tasks.list"
      artifact_class: "output"
      path_pattern: "tasks.md"
      blocking: true

optional_always:
  - artifact_key: "evidence.research"
    artifact_class: "evidence"
    path_pattern: "research.md"
  - artifact_key: "evidence.gap-analysis"
    artifact_class: "evidence"
    path_pattern: "gap-analysis.md"
```

**Test Requirements**:
- Valid manifest YAML parses without errors
- Invalid artifact_class rejected
- Missing required steps allowed (optional)
- Path patterns with wildcards accepted
- Schema fields documented

---

### T007: Implement ManifestRegistry Loader

**What**: Create ManifestRegistry class to load and query manifests.

**How**:
1. Create manifest.py in `src/specify_cli/dossier/manifest.py`
2. Define ExpectedArtifactSpec and ExpectedArtifactManifest pydantic models (from data-model.md):
   ```python
   class ArtifactClassEnum(str, Enum):
       INPUT = "input"
       WORKFLOW = "workflow"
       OUTPUT = "output"
       EVIDENCE = "evidence"
       POLICY = "policy"
       RUNTIME = "runtime"

   class ExpectedArtifactSpec(BaseModel):
       artifact_key: str
       artifact_class: ArtifactClassEnum
       path_pattern: str
       blocking: bool = False

   class ExpectedArtifactManifest(BaseModel):
       schema_version: str = "1.0"
       mission_type: str
       manifest_version: str = "1"
       required_always: List[ExpectedArtifactSpec] = Field(default_factory=list)
       required_by_step: Dict[str, List[ExpectedArtifactSpec]] = Field(default_factory=dict)
       optional_always: List[ExpectedArtifactSpec] = Field(default_factory=list)

       @classmethod
       def from_yaml_file(cls, path: Path) -> "ExpectedArtifactManifest":
           """Load manifest from YAML file."""
           import ruamel.yaml
           yaml = ruamel.yaml.YAML()
           with open(path) as f:
               data = yaml.load(f)
           return cls(**data)
   ```
3. Create ManifestRegistry class:
   ```python
   class ManifestRegistry:
       _cache: Dict[str, Optional[ExpectedArtifactManifest]] = {}

       @staticmethod
       def load_manifest(mission_type: str) -> Optional[ExpectedArtifactManifest]:
           """Load manifest for mission type. Return None if not found."""
           if mission_type in ManifestRegistry._cache:
               return ManifestRegistry._cache[mission_type]

           manifest_path = Path(__file__).parent.parent / "missions" / mission_type / "expected-artifacts.yaml"
           if not manifest_path.exists():
               ManifestRegistry._cache[mission_type] = None
               return None

           manifest = ExpectedArtifactManifest.from_yaml_file(manifest_path)
           ManifestRegistry._cache[mission_type] = manifest
           return manifest

       @staticmethod
       def get_required_artifacts(manifest: ExpectedArtifactManifest, step_id: str) -> List[ExpectedArtifactSpec]:
           """Get required specs for mission step."""
           base = manifest.required_always
           step_specific = manifest.required_by_step.get(step_id, [])
           return base + step_specific

       @staticmethod
       def clear_cache():
           """Clear manifest cache (for testing)."""
           ManifestRegistry._cache.clear()
   ```
4. Add methods to get artifacts by class, filter by blocking, etc.

**Test Requirements**:
- load_manifest("software-dev") returns valid manifest
- load_manifest("unknown") returns None
- get_required_artifacts(manifest, "specify") returns correct list
- Cache works (second call doesn't reload file)
- Unknown step returns empty list (graceful)

---

### T008: Create software-dev expected-artifacts.yaml

**What**: Create expected-artifacts.yaml for software-dev mission.

**How**:
1. Analyze existing software-dev mission template in `src/specify_cli/missions/software-dev/`
2. Review mission.yaml to identify state machine (states: discover, specify, plan, implement, review, done)
3. Identify all artifacts expected at each state:
   - **discover** (none expected)
   - **specify**: spec.md (required, input)
   - **plan**: plan.md, tasks.md (required, output)
   - **implement**: code changes (tracked via git, not filesystem artifacts)
   - **review**: review summary (optional, evidence)
4. Create expected-artifacts.yaml with:
   - required_always:[] (no artifacts required regardless of state)
   - required_by_step: See above
   - optional_always: research.md, gap-analysis.md, quickstart.md
5. Reference data-model.md for field definitions
6. Validate against actual mission template structure

**File Location**: `src/specify_cli/missions/software-dev/expected-artifacts.yaml`

**Example Content**:
```yaml
schema_version: "1.0"
mission_type: "software-dev"
manifest_version: "1"

required_always: []

required_by_step:
  specify:
    - artifact_key: "input.spec.main"
      artifact_class: "input"
      path_pattern: "spec.md"
      blocking: true

  plan:
    - artifact_key: "output.plan.main"
      artifact_class: "output"
      path_pattern: "plan.md"
      blocking: true
    - artifact_key: "output.tasks.list"
      artifact_class: "output"
      path_pattern: "tasks.md"
      blocking: true

optional_always:
  - artifact_key: "evidence.research"
    artifact_class: "evidence"
    path_pattern: "research.md"
  - artifact_key: "evidence.gap-analysis"
    artifact_class: "evidence"
    path_pattern: "gap-analysis.md"
```

**Test Requirements**:
- Manifest loads without errors
- All referenced states exist in mission.yaml
- Path patterns match existing artifacts in mission template
- Blocking field correctly marks blocking artifacts

---

### T009: Create research expected-artifacts.yaml

**What**: Create expected-artifacts.yaml for research mission.

**How**:
1. Analyze research mission template in `src/specify_cli/missions/research/`
2. Review mission.yaml states (scoping, methodology, gathering, synthesis, output, done)
3. Identify artifacts per state:
   - **scoping**: research-plan.md (required)
   - **methodology**: methodology.md (required)
   - **gathering**: findings-log.md (optional)
   - **synthesis**: findings.md, analysis.md (required)
   - **output**: report.md (required)
4. Create expected-artifacts.yaml following same structure as T008
5. Validate path patterns match actual research mission structure

**File Location**: `src/specify_cli/missions/research/expected-artifacts.yaml`

**Test Requirements**:
- Manifest loads without errors
- States align with actual mission.yaml
- Blocking semantics correct (findings.md blocks completeness at synthesis state)

---

### T010: Create documentation expected-artifacts.yaml

**What**: Create expected-artifacts.yaml for documentation mission.

**How**:
1. Analyze documentation mission template in `src/specify_cli/missions/documentation/`
2. Review mission.yaml states and identify documentation artifacts
3. Determine which artifacts are required per Divio 4-type system (tutorial, how-to, reference, explanation)
4. Create manifest with step-aware requirements
5. Validate path patterns

**File Location**: `src/specify_cli/missions/documentation/expected-artifacts.yaml`

**Test Requirements**:
- Manifest loads without errors
- Divio types (tutorial, how-to, reference, explanation) properly mapped
- Path patterns valid

---

### T011: Manifest Validation

**What**: Implement validation that manifests are correct (steps exist, paths valid).

**How**:
1. Add validation methods to ManifestRegistry:
   ```python
   @staticmethod
   def validate_manifest(manifest: ExpectedArtifactManifest, mission_dir: Path) -> Tuple[bool, List[str]]:
       """Validate manifest against mission structure.

       Returns: (is_valid, error_messages)
       """
       errors = []

       # Check all steps exist in mission.yaml
       mission_yaml_path = mission_dir / "mission.yaml"
       if mission_yaml_path.exists():
           mission_yaml = load_mission_yaml(mission_yaml_path)
           states = extract_states_from_mission_yaml(mission_yaml)
           for step_id in manifest.required_by_step.keys():
               if step_id not in states:
                   errors.append(f"Step '{step_id}' not found in mission.yaml states")

       # Check path patterns are reasonable (not absolute, not parent refs)
       for specs in manifest.required_always + sum(manifest.required_by_step.values(), []) + manifest.optional_always:
           if specs.path_pattern.startswith('/'):
               errors.append(f"Path pattern must be relative: {specs.path_pattern}")
           if '..' in specs.path_pattern:
               errors.append(f"Path pattern cannot reference parent: {specs.path_pattern}")

       return len(errors) == 0, errors
   ```
2. Call validation during manifest loading (warn if validation fails, but don't block)
3. Add validation tests

**Test Requirements**:
- Valid manifest passes validation
- Invalid step name detected
- Absolute paths rejected
- Parent references (..) rejected
- Validation results logged

---

## Definition of Done

- [ ] Manifest schema documented (YAML structure, field definitions)
- [ ] ManifestRegistry class created, loads/caches manifests
- [ ] ExpectedArtifactSpec and ExpectedArtifactManifest pydantic models created
- [ ] software-dev expected-artifacts.yaml created and validated
- [ ] research expected-artifacts.yaml created and validated
- [ ] documentation expected-artifacts.yaml created and validated
- [ ] Manifest validation implemented (steps exist, paths valid)
- [ ] All manifests load without errors
- [ ] Unknown missions handled gracefully (return None)
- [ ] Comprehensive tests for loading, querying, validation
- [ ] FR-003 requirement satisfied

---

## Risks & Mitigations

**Risk 1**: Manifest steps don't match mission.yaml
- **Mitigation**: Validation (T011) checks step existence; validation failures logged

**Risk 2**: Path patterns don't match actual files
- **Mitigation**: Manual review of mission templates during implementation; tests verify paths

**Risk 3**: Manifest versions diverge across missions
- **Mitigation**: Single manifest_version field per mission; versioning strategy deferred post-042

**Risk 4**: Custom/unknown missions not supported
- **Mitigation**: Graceful degradation: unknown missions return None, no missing detection

---

## Reviewer Guidance

When reviewing WP02:
1. Verify manifest schema matches data-model.md (schema_version, mission_type, manifest_version, required_always, required_by_step, optional_always)
2. Check all 3 manifests (software-dev, research, documentation) created in mission directories
3. Confirm step names match mission.yaml state IDs (from each mission template)
4. Verify path patterns are relative, use wildcards correctly
5. Ensure blocking field semantics correct (spec.md blocks, research.md doesn't)
6. Validate ManifestRegistry handles unknown missions (returns None, no exception)
7. Check validation detects invalid steps, absolute paths, parent references
8. Confirm FR-003 requirement satisfied (step-aware, manifest-based)

---

## Implementation Notes

- **Storage**: manifest.py (registry, models), missions/*/expected-artifacts.yaml (data)
- **Dependencies**: pydantic, ruamel.yaml (both existing)
- **Estimated Lines**: ~400 (manifest.py ~150, 3 YAML files ~250)
- **Integration Point**: WP03 (indexing) will use ManifestRegistry
- **Deferred**: Manifest versioning strategy, custom mission support (post-042)
