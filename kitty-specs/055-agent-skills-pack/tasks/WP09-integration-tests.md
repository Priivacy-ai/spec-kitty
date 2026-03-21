---
work_package_id: WP09
title: End-to-End Integration Tests
lane: planned
dependencies:
- WP05
subtasks:
- T036
- T037
- T038
- T039
- T040
phase: Phase 2 - Integration
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-21T07:39:56Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- NFR-003
- NFR-005
---

# Work Package Prompt: WP09 – End-to-End Integration Tests

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Comprehensive integration tests covering the full skill lifecycle
- Test init → verify → repair cycle end-to-end
- Test all three installation classes
- Test manifest persistence and drift detection
- All tests pass with pytest

**Success**: `pytest tests/specify_cli/skills/test_e2e.py` passes with all test cases green.

## Context & Constraints

- **NFR-003**: 90%+ test coverage for new code
- **NFR-005**: All operations work fully offline
- **Dependencies**: WP05 (init integration), WP07 (verify integration), WP08 (skill content)

**Implementation command**: `spec-kitty implement WP09 --base WP05`

## Subtasks & Detailed Guidance

### Subtask T036 – Test full init → verify → repair cycle

- **Purpose**: Verify the complete lifecycle works end-to-end.
- **Steps**:
  1. Create `tests/specify_cli/skills/test_e2e.py`
  2. Test `test_full_lifecycle`:
     ```python
     def test_full_lifecycle(tmp_path):
         """Install skills, verify ok, corrupt one, verify detects, repair, verify ok again."""
         # Setup: create skill fixture, registry
         skill_dir = tmp_path / "skills" / "spec-kitty-setup-doctor"
         skill_dir.mkdir(parents=True)
         (skill_dir / "SKILL.md").write_text("---\nname: spec-kitty-setup-doctor\n---\nContent")

         registry = SkillRegistry(tmp_path / "skills")
         project = tmp_path / "project"
         project.mkdir()
         (project / ".kittify").mkdir()

         # Step 1: Install for claude (native-root)
         skills = registry.discover_skills()
         entries = install_skills_for_agent(project, "claude", skills)
         manifest = ManagedSkillManifest(entries=entries, ...)
         save_manifest(manifest, project)

         # Step 2: Verify → should be ok
         result = verify_installed_skills(project)
         assert result.ok

         # Step 3: Delete the skill file
         skill_file = project / ".claude" / "skills" / "spec-kitty-setup-doctor" / "SKILL.md"
         skill_file.unlink()

         # Step 4: Verify → should detect missing
         result = verify_installed_skills(project)
         assert not result.ok
         assert len(result.missing) == 1

         # Step 5: Repair
         repaired, failed = repair_skills(project, result, registry)
         assert repaired == 1
         assert failed == 0

         # Step 6: Verify again → should be ok
         result = verify_installed_skills(project)
         assert result.ok
     ```
- **Files**: `tests/specify_cli/skills/test_e2e.py` (new)

### Subtask T037 – Test per-installation-class distribution

- **Purpose**: Verify each installation class receives skills in the correct root.
- **Steps**:
  1. Add test `test_per_class_distribution`:
     - Install for claude (native) → verify `.claude/skills/`
     - Install for codex (shared) → verify `.agents/skills/`
     - Install for q (wrapper-only) → verify no skill root, empty entries
  2. Verify file paths match expected roots from `AGENT_SKILL_CONFIG`
- **Files**: `tests/specify_cli/skills/test_e2e.py` (add test)
- **Parallel?**: Yes

### Subtask T038 – Test manifest persistence across sessions

- **Purpose**: Verify manifest survives save/load cycle with correct data.
- **Steps**:
  1. Add test `test_manifest_persistence`:
     - Install skills, save manifest
     - Create new manifest instance from `load_manifest()`
     - Verify all entries, hashes, and metadata match
  2. Verify JSON file is valid and human-readable
- **Files**: `tests/specify_cli/skills/test_e2e.py` (add test)
- **Parallel?**: Yes

### Subtask T039 – Test drift detection and repair

- **Purpose**: Verify modify-then-verify-then-repair cycle.
- **Steps**:
  1. Add test `test_drift_detection_and_repair`:
     - Install skill, save manifest
     - Modify installed SKILL.md (change content)
     - Verify → should detect drift with correct actual hash
     - Repair → should restore original content
     - Verify → should be ok
  2. Verify manifest hash is updated after repair
- **Files**: `tests/specify_cli/skills/test_e2e.py` (add test)
- **Parallel?**: Yes

### Subtask T040 – Test multiple agents simultaneously

- **Purpose**: Verify correct behavior with mixed installation classes in one init.
- **Steps**:
  1. Add test `test_multiple_agents_mixed_classes`:
     - Install skills for: claude (native), copilot (shared), codex (shared), q (wrapper-only)
     - Verify:
       - `.claude/skills/` has skill files (native root)
       - `.agents/skills/` has skill files (shared root — one copy)
       - No `.amazonq/skills/` (wrapper-only)
       - Manifest has entries for claude, copilot, codex (not q)
       - copilot and codex manifest entries point to same `.agents/skills/` path
  2. Verify shared-root deduplication: only one file copy exists
- **Files**: `tests/specify_cli/skills/test_e2e.py` (add test)
- **Parallel?**: Yes

## Test Strategy

- Use `tmp_path` pytest fixture for all filesystem operations
- Create minimal skill fixtures (just SKILL.md with frontmatter)
- No mocking of `SkillRegistry` — use real registry with test directories
- Mock `get_local_repo_root()` and `get_package_asset_root()` to use fixture paths
- All tests must be deterministic (no random, no time-dependent assertions)

## Risks & Mitigations

- **Slow tests**: Full lifecycle tests may be slow → keep fixtures minimal, avoid full init
- **Flaky tests**: Filesystem timing issues → use synchronous operations, no polling
- **Missing fixtures**: Tests depend on WP08 skill content → use minimal stub content for tests

## Review Guidance

- Verify all three installation classes are tested
- Verify drift detection tests both missing AND modified cases
- Verify deduplication is tested (two shared-root agents, one file copy)
- Verify all tests are deterministic
- Run full test suite: `pytest tests/specify_cli/skills/ -v`

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.
