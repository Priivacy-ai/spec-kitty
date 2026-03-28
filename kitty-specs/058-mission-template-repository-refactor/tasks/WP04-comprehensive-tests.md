---
work_package_id: WP04
title: Comprehensive Tests
lane: "for_review"
dependencies: [WP01, WP02, WP03, WP11]
requirement_refs:
- NFR-002
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
base_branch: 058-mission-template-repository-refactor-WP04-merge-base
base_commit: 1ce5ab94fbe5db8b797c70f95d05abf8983af3fc
created_at: '2026-03-28T08:46:00.882991+00:00'
subtasks:
- T017
- T018
phase: Phase 1 - New API Foundation
assignee: ''
agent: opencode
shell_pid: '26986'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-27T04:37:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer
---

# Work Package Prompt: WP04 – Comprehensive Tests

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

1. Existing `test_mission_repository.py` passes (verifying backward compatibility via alias)
2. New `test_mission_template_repository.py` covers all public API methods
3. 90%+ line coverage for new code in `repository.py` (constitution requirement)
4. Tests cover: value objects, doctrine reads, None returns, enumeration, YAML parsing, alias, resolver integration, edge cases

**Success gate**: `pytest tests/doctrine/ -v` passes with all tests green.

## Context & Constraints

- **Contract**: `kitty-specs/058-mission-template-repository-refactor/contracts/mission-template-repository.md` (Testing Contract section)
- **Prerequisite**: WP01-WP03 must be complete (full API surface exists)
- **Existing tests**: `tests/doctrine/missions/test_mission_repository.py` -- must still pass
- **Test conventions**: Use real doctrine assets where possible. Use `tmp_path` for edge cases. Use `MissionTemplateRepository.default()` for doctrine-level tests.
- **Note**: Tests should NOT use hardcoded paths like `Path("src/doctrine/missions/...")`. Use the repository API or `importlib.resources.files()`.

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP04 --base WP03`

## Subtasks & Detailed Guidance

### Subtask T017 – Verify existing test_mission_repository.py passes via alias

- **Purpose**: Confirm backward compatibility. The old test file imports `MissionRepository` which is now an alias for `MissionTemplateRepository`.
- **Steps**:
  1. Run: `pytest tests/doctrine/missions/test_mission_repository.py -v`
  2. If tests fail because they call old method names (e.g., `get_command_template()` which now returns `TemplateResult` instead of `Path`), note the failures but do NOT modify the old test file heavily. Instead:
     - If the test imports `MissionRepository`, that should still work (alias)
     - If the test calls `repo.get_command_template(...)` and expects `Path`, it needs to be updated to either:
       a. Use the new private name `repo._command_template_path(...)` for `Path` returns, OR
       b. Use the new public API and assert `TemplateResult` instead
     - Prefer option (b) for tests that verify content, option (a) only for tests specifically testing path resolution
  3. Read the existing test file, understand what it tests, and make minimal changes
  4. Re-run after changes: `pytest tests/doctrine/missions/test_mission_repository.py -v`
- **Files**: `tests/doctrine/missions/test_mission_repository.py`
- **Parallel?**: No, must verify before writing new tests

### Subtask T018 – Create comprehensive test module

- **Purpose**: Full test coverage for the new `MissionTemplateRepository` API.
- **Steps**:
  1. Create `tests/doctrine/test_mission_template_repository.py` (note: at `tests/doctrine/` level, not `tests/doctrine/missions/`)
  2. Structure tests by category:

  **Category 1: Value Object Tests**
  ```python
  class TestTemplateResult:
      def test_properties(self):
          result = TemplateResult(content="hello", origin="doctrine/test/a.md")
          assert result.content == "hello"
          assert result.origin == "doctrine/test/a.md"
          assert result.tier is None

      def test_with_tier(self):
          result = TemplateResult(content="hello", origin="test", tier="some_tier")
          assert result.tier == "some_tier"

      def test_repr(self):
          result = TemplateResult(content="x", origin="o")
          assert "TemplateResult" in repr(result)
          assert "o" in repr(result)

  class TestConfigResult:
      def test_properties(self):
          result = ConfigResult(content="key: val", origin="test.yaml", parsed={"key": "val"})
          assert result.content == "key: val"
          assert result.origin == "test.yaml"
          assert result.parsed == {"key": "val"}

      def test_repr(self):
          result = ConfigResult(content="x", origin="o", parsed={})
          assert "ConfigResult" in repr(result)
  ```

  **Category 2: Doctrine-Level Read Tests**
  ```python
  class TestDoctrineReads:
      """Tests against real doctrine bundled assets."""

      @pytest.fixture
      def repo(self):
          return MissionTemplateRepository.default()

      def test_get_command_template_exists(self, repo):
          result = repo.get_command_template("software-dev", "implement")
          assert result is not None
          assert isinstance(result, TemplateResult)
          assert len(result.content) > 0
          assert "doctrine/software-dev/command-templates/implement.md" == result.origin
          assert result.tier is None

      def test_get_content_template_exists(self, repo):
          result = repo.get_content_template("software-dev", "spec-template.md")
          assert result is not None
          assert len(result.content) > 0

      def test_get_action_index(self, repo):
          result = repo.get_action_index("software-dev", "implement")
          # This may be None if no action index exists -- check doctrine assets first
          if result is not None:
              assert isinstance(result, ConfigResult)
              assert isinstance(result.parsed, dict)

      def test_get_action_guidelines(self, repo):
          result = repo.get_action_guidelines("software-dev", "implement")
          if result is not None:
              assert isinstance(result, TemplateResult)
              assert len(result.content) > 0

      def test_get_mission_config(self, repo):
          result = repo.get_mission_config("software-dev")
          assert result is not None
          assert isinstance(result.parsed, dict)
          assert "mission.yaml" in result.origin

      def test_get_expected_artifacts(self, repo):
          result = repo.get_expected_artifacts("software-dev")
          # May or may not exist -- check doctrine assets
          if result is not None:
              assert isinstance(result.parsed, (dict, list))
  ```

  **Category 3: None Returns**
  ```python
  class TestNoneReturns:
      @pytest.fixture
      def repo(self):
          return MissionTemplateRepository.default()

      def test_nonexistent_mission_command_template(self, repo):
          assert repo.get_command_template("nonexistent", "implement") is None

      def test_nonexistent_template_name(self, repo):
          assert repo.get_command_template("software-dev", "nonexistent") is None

      def test_nonexistent_content_template(self, repo):
          assert repo.get_content_template("software-dev", "nonexistent.md") is None

      def test_nonexistent_action_index(self, repo):
          assert repo.get_action_index("software-dev", "nonexistent") is None

      def test_nonexistent_mission_config(self, repo):
          assert repo.get_mission_config("nonexistent") is None
  ```

  **Category 4: Enumeration Tests**
  ```python
  class TestEnumeration:
      @pytest.fixture
      def repo(self):
          return MissionTemplateRepository.default()

      def test_list_missions(self, repo):
          missions = repo.list_missions()
          assert isinstance(missions, list)
          assert "software-dev" in missions
          assert missions == sorted(missions)

      def test_list_command_templates(self, repo):
          names = repo.list_command_templates("software-dev")
          assert isinstance(names, list)
          assert "implement" in names
          assert names == sorted(names)
          # Verify no .md extension in names
          assert all(not n.endswith(".md") for n in names)

      def test_list_content_templates(self, repo):
          names = repo.list_content_templates("software-dev")
          assert isinstance(names, list)
          assert "spec-template.md" in names
          assert names == sorted(names)

      def test_list_command_templates_nonexistent(self, repo):
          assert repo.list_command_templates("nonexistent") == []

      def test_list_content_templates_nonexistent(self, repo):
          assert repo.list_content_templates("nonexistent") == []
  ```

  **Category 5: Backward Compatibility**
  ```python
  class TestBackwardCompat:
      def test_alias_import(self):
          from doctrine.missions import MissionRepository, MissionTemplateRepository
          assert MissionRepository is MissionTemplateRepository

      def test_isinstance(self):
          from doctrine.missions import MissionRepository
          repo = MissionTemplateRepository.default()
          assert isinstance(repo, MissionRepository)

      def test_default_missions_root(self):
          # Classmethod still works on alias
          from doctrine.missions import MissionRepository
          root = MissionRepository.default_missions_root()
          assert root.is_dir()
  ```

  **Category 6: Edge Cases**
  ```python
  class TestEdgeCases:
      def test_empty_missions_root(self, tmp_path):
          repo = MissionTemplateRepository(tmp_path)
          assert repo.list_missions() == []
          assert repo.get_command_template("anything", "anything") is None

      def test_nonexistent_missions_root(self, tmp_path):
          repo = MissionTemplateRepository(tmp_path / "nonexistent")
          assert repo.list_missions() == []

      def test_default_classmethod(self):
          repo = MissionTemplateRepository.default()
          assert isinstance(repo, MissionTemplateRepository)
          assert repo._missions_root.is_dir()
  ```

  **Category 7: Resolver Integration** (if possible without mock project)
  ```python
  class TestResolverIntegration:
      def test_resolve_command_template_package_default(self):
          repo = MissionTemplateRepository.default()
          result = repo.resolve_command_template("software-dev", "implement")
          assert isinstance(result, TemplateResult)
          assert len(result.content) > 0
          assert result.tier is not None
          # Without project_dir, should fall back to package default

      def test_resolve_command_template_not_found(self):
          repo = MissionTemplateRepository.default()
          with pytest.raises(FileNotFoundError):
              repo.resolve_command_template("software-dev", "nonexistent-template-xyz")
  ```

  3. Import the classes at the top of the test file:
     ```python
     import pytest
     from doctrine.missions import MissionTemplateRepository, TemplateResult, ConfigResult
     ```

- **Files**: `tests/doctrine/test_mission_template_repository.py` (NEW)
- **Parallel?**: No, sequential -- T017 first, then T018

## Test Strategy

Run the full doctrine test suite after completion:
```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/doctrine/ -v
```

Check coverage:
```bash
source .venv/bin/activate && .venv/bin/python -m pytest tests/doctrine/test_mission_template_repository.py -v --cov=doctrine.missions.repository --cov-report=term-missing
```

Target: 90%+ line coverage on `repository.py`.

## Risks & Mitigations

1. **Doctrine assets may change**: Test for presence/type rather than exact content. Use `assert len(result.content) > 0` not `assert result.content == "specific text"`.
2. **Resolver integration test may fail without global runtime**: The `resolve_command_template` without `project_dir` should still work by falling back to package default. If the resolver requires `~/.kittify/` to exist, the test may need a conditional skip or mock.
3. **Existing test file may need significant changes**: If `test_mission_repository.py` calls methods that no longer exist (renamed to private), update minimally. Prefer keeping old test file as a backward-compat smoke test.

## Review Guidance

- Verify test categories match the contract's "Required Test Categories"
- Verify tests use `MissionTemplateRepository.default()` for doctrine-level tests, not hardcoded paths
- Verify edge case tests use `tmp_path` fixture
- Verify `from doctrine.missions import MissionRepository` alias test exists
- Verify coverage meets 90%+ threshold
- Run `pytest tests/doctrine/ -v` and confirm all pass

## Activity Log

- 2026-03-27T04:37:32Z – system – lane=planned – Prompt created.
- 2026-03-28T08:46:06Z – opencode – shell_pid=26986 – lane=doing – Assigned agent via workflow command
- 2026-03-28T08:51:21Z – opencode – shell_pid=26986 – lane=for_review – 78 new tests covering all public API methods, value objects, enumeration, backward compat, and edge cases. 94% line coverage on repository.py (target 90%+). Full doctrine suite: 948 passed, 3 pre-existing failures (agent profile tests unrelated to WP04).
