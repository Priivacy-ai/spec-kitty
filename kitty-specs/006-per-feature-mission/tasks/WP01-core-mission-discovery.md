---
work_package_id: WP01
title: Core Mission Discovery
lane: done
history:
- timestamp: '2025-12-15T11:55:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: ''
phase: Phase 1 - Foundation
review_status: ''
reviewed_by: ''
shell_pid: '41190'
subtasks:
- T001
- T002
- T003
- T004
- T005
---

# Work Package Prompt: WP01 – Core Mission Discovery

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Add `get_mission_for_feature()` function to resolve mission from a feature's `meta.json`
- Add `discover_missions()` function returning all missions with source indicators
- Maintain backward compatibility: missing `mission` field defaults to "software-dev"
- Unit tests pass for all new functions

**Success Metrics**:
- `get_mission_for_feature(feature_dir)` returns correct Mission object
- Features without `mission` field return software-dev Mission
- `discover_missions()` returns dict with "project" and "built-in" sources

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/006-per-feature-mission/spec.md` (FR-001, FR-004)
- Plan: `kitty-specs/006-per-feature-mission/plan.md` (Phase 1)
- Data Model: `kitty-specs/006-per-feature-mission/data-model.md` (Function Signatures)

**Existing Code**:
- `src/specify_cli/mission.py` contains `Mission` class, `MissionConfig` Pydantic model
- `get_active_mission()` at line ~378 reads from `.kittify/active-mission` (to be deprecated later)
- `get_mission_by_name()` at line ~464 loads mission by key

**Constraints**:
- Do NOT modify `get_active_mission()` yet (other code depends on it)
- New functions should follow existing patterns in mission.py

## Subtasks & Detailed Guidance

### Subtask T001 – Add `get_mission_for_feature()` function

- **Purpose**: Enable per-feature mission resolution from `meta.json`
- **Files**: `src/specify_cli/mission.py`
- **Steps**:
  1. Add function signature matching data-model.md:
     ```python
     def get_mission_for_feature(feature_dir: Path, project_root: Optional[Path] = None) -> Mission:
     ```
  2. Load `meta.json` from `feature_dir`:
     ```python
     meta_file = feature_dir / "meta.json"
     if not meta_file.exists():
         raise MissionNotFoundError(f"Feature meta.json not found: {meta_file}")
     with open(meta_file, 'r') as f:
         meta = json.load(f)
     ```
  3. Extract mission field with default:
     ```python
     mission_key = meta.get("mission", "software-dev")
     ```
  4. Find project root if not provided (look for `.kittify`)
  5. Call `get_mission_by_name(mission_key, kittify_dir)` to load mission
  6. If mission not found, warn and return software-dev:
     ```python
     except MissionNotFoundError:
         warnings.warn(f"Mission '{mission_key}' not found, using software-dev")
         return get_mission_by_name("software-dev", kittify_dir)
     ```
- **Parallel?**: No (foundational)

### Subtask T002 – Add `discover_missions()` function

- **Purpose**: List all available missions with source indicators for UI/prompts
- **Files**: `src/specify_cli/mission.py`
- **Steps**:
  1. Add function signature:
     ```python
     def discover_missions(project_root: Optional[Path] = None) -> Dict[str, Tuple[Mission, str]]:
     ```
  2. Find project root / `.kittify` directory
  3. Scan `.kittify/missions/` for valid mission directories:
     ```python
     missions = {}
     missions_dir = kittify_dir / "missions"
     for mission_dir in missions_dir.iterdir():
         if mission_dir.is_dir() and (mission_dir / "mission.yaml").exists():
             try:
                 mission = Mission(mission_dir)
                 # For now, all missions are "project" source
                 # (built-in and project share same location)
                 missions[mission_dir.name] = (mission, "project")
             except MissionError as e:
                 warnings.warn(f"Skipping invalid mission {mission_dir.name}: {e}")
     ```
  4. Return the dict
- **Parallel?**: No (foundational)

### Subtask T003 – Add helper to read mission field from meta.json

- **Purpose**: Reusable helper for extracting mission from feature metadata
- **Files**: `src/specify_cli/mission.py`
- **Steps**:
  1. Add helper function:
     ```python
     def get_feature_mission_key(feature_dir: Path) -> str:
         """Extract mission key from feature's meta.json, defaulting to software-dev."""
         meta_file = feature_dir / "meta.json"
         if not meta_file.exists():
             return "software-dev"
         try:
             with open(meta_file, 'r') as f:
                 meta = json.load(f)
             return meta.get("mission", "software-dev")
         except (json.JSONDecodeError, OSError):
             return "software-dev"
     ```
  2. Import `json` at top of file if not already imported
- **Parallel?**: No (used by T001)

### Subtask T004 – Unit tests for `get_mission_for_feature()`

- **Purpose**: Verify per-feature mission resolution works correctly
- **Files**: `tests/unit/test_mission.py`
- **Steps**:
  1. Add test fixture creating temp feature directory with meta.json:
     ```python
     @pytest.fixture
     def feature_with_mission(tmp_path, sample_kittify_dir):
         feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
         feature_dir.mkdir(parents=True)
         meta = {
             "feature_number": "001",
             "slug": "001-test-feature",
             "mission": "software-dev"
         }
         (feature_dir / "meta.json").write_text(json.dumps(meta))
         return feature_dir
     ```
  2. Add test for valid mission:
     ```python
     def test_get_mission_for_feature_valid(feature_with_mission, sample_kittify_dir):
         mission = get_mission_for_feature(feature_with_mission, sample_kittify_dir.parent)
         assert mission.name == "Software Dev Kitty"
     ```
  3. Add test for research mission
  4. Add test for invalid mission (should warn and return software-dev)
- **Parallel?**: Yes (once T001-T003 done)

### Subtask T005 – Unit tests for backward compatibility

- **Purpose**: Verify features without mission field default to software-dev
- **Files**: `tests/unit/test_mission.py`
- **Steps**:
  1. Add fixture for feature WITHOUT mission field:
     ```python
     @pytest.fixture
     def legacy_feature(tmp_path, sample_kittify_dir):
         feature_dir = tmp_path / "kitty-specs" / "000-legacy"
         feature_dir.mkdir(parents=True)
         meta = {
             "feature_number": "000",
             "slug": "000-legacy"
             # NO mission field
         }
         (feature_dir / "meta.json").write_text(json.dumps(meta))
         return feature_dir
     ```
  2. Add test:
     ```python
     def test_get_mission_for_feature_legacy_defaults_to_software_dev(legacy_feature, sample_kittify_dir):
         mission = get_mission_for_feature(legacy_feature, sample_kittify_dir.parent)
         assert mission.domain == "software"
         assert "software" in mission.name.lower()
     ```
  3. Add test for missing meta.json (should raise or return default based on design)
- **Parallel?**: Yes (once T001-T003 done)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing `get_active_mission()` callers | Keep function unchanged; add new functions alongside |
| JSON parsing errors in meta.json | Handle gracefully with try/except, default to software-dev |
| Mission directory structure varies | Validate mission.yaml exists before loading |

## Definition of Done Checklist

- [ ] `get_mission_for_feature()` function implemented and returns correct Mission
- [ ] `discover_missions()` function returns all missions with source indicators
- [ ] `get_feature_mission_key()` helper extracts mission from meta.json
- [ ] Unit tests pass for all new functions
- [ ] Backward compatibility verified (missing mission field → software-dev)
- [ ] No changes to existing `get_active_mission()` function

## Review Guidance

- Verify function signatures match `data-model.md` contract
- Check error handling is consistent with existing mission.py patterns
- Ensure tests cover edge cases: missing file, invalid JSON, unknown mission key
- Confirm no breaking changes to existing code paths

## Activity Log

- 2025-12-15T11:55:00Z – system – lane=planned – Prompt created.
- 2025-12-15T11:00:52Z – claude – shell_pid=40801 – lane=doing – Started implementation
- 2025-12-15T11:03:25Z – claude – shell_pid=41190 – lane=for_review – Ready for review - all tests pass
