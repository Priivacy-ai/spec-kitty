---
work_package_id: WP05
title: Post-Save Hook and Integration
lane: "done"
dependencies: [WP03]
base_branch: develop
base_commit: 32230f09a89c8c51c5b76535e10b05110e90f3c2
created_at: '2026-02-16T05:49:58.437693+00:00'
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
phase: Phase 3 - Migration and Integration
assignee: ''
agent: "claude"
shell_pid: '639215'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-15T22:11:29Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Post-Save Hook and Integration

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Implement post-save hook that auto-triggers sync after CLI constitution writes
- Wire hook into constitution command template write path
- Implement convenience loader functions for Feature 044/046 consumers
- Finalize `constitution/__init__.py` public API exports
- **All tests pass**, **mypy --strict clean**, **ruff clean**

**Success metrics**:

- After `/spec-kitty.constitution` completes, YAML files are auto-generated
- `load_governance_config(repo_root)` returns a validated `GovernanceConfig` instance
- `load_agents_config(repo_root)` returns a validated `AgentsConfig` instance
- Post-save hook failure doesn't crash the CLI (warning only)

## Context & Constraints

- **Spec**: `kitty-specs/045-constitution-doctrine-config-sync/spec.md` — FR-2.1 through FR-2.5, FR-4.1–4.5
- **Plan**: `kitty-specs/045-constitution-doctrine-config-sync/plan.md` — AD-4 (synchronous hook)
- **Quickstart**: `kitty-specs/045-constitution-doctrine-config-sync/quickstart.md` — API usage examples
- **Depends on WP03**: `sync()` function, `SyncResult`
- **Consumers**: Feature 044 (governance hooks), Feature 046 (routing provider)

**Implementation command**: `spec-kitty implement WP05 --base WP03`

## Subtasks & Detailed Guidance

### Subtask T033 – Implement Post-Save Hook Function

**Purpose**: Create a hook function that triggers sync() after CLI writes to constitution.md (FR-2.1).

**Steps**:

1. Add to `src/specify_cli/constitution/sync.py` (or a new `hooks.py`):

   ```python
   import logging

   logger = logging.getLogger(__name__)

   def post_save_hook(constitution_path: Path) -> None:
       """Auto-trigger sync after constitution write.

       Called synchronously after CLI writes to constitution.md.
       Failures are logged but don't propagate (FR-2.3).
       """
       try:
           result = sync(constitution_path, force=True)
           if result.synced:
               logger.info(
                   "Constitution synced: %d YAML files updated",
                   len(result.files_written),
               )
           elif result.error:
               logger.warning("Constitution sync warning: %s", result.error)
       except Exception:
           logger.warning(
               "Constitution auto-sync failed. Run 'spec-kitty constitution sync' manually.",
               exc_info=True,
           )
   ```

2. Key requirements:
   - Synchronous — called inline after write (AD-4)
   - Never raises — catches all exceptions, logs warning (FR-2.3)
   - Force=True — always extract after a write (new content)

**Files**:

- `src/specify_cli/constitution/sync.py` (or `hooks.py`)

### Subtask T034 – Wire Hook into Constitution Write Path

**Purpose**: Call the post-save hook after CLI commands that write constitution.md (FR-2.1, FR-2.5).

**Steps**:

1. Identify the code path where `/spec-kitty.constitution` writes the constitution file:
   - Check `src/specify_cli/missions/software-dev/command-templates/constitution.md` — this is the template that agents use
   - The actual write happens via the agent's file write (not Python code)
   - **IMPORTANT**: The post-save hook must be triggered from the CLI command that orchestrates the constitution flow

2. Find the CLI command or orchestrator that handles constitution writes:

   ```bash
   grep -r "constitution" src/specify_cli/cli/ --include="*.py" -l
   grep -r "constitution" src/specify_cli/orchestrator/ --include="*.py" -l
   ```

3. Add hook call after the write:

   ```python
   from specify_cli.constitution.sync import post_save_hook

   # After constitution.md is written:
   constitution_path = repo_root / ".kittify" / "constitution" / "constitution.md"
   if constitution_path.exists():
       post_save_hook(constitution_path)
   ```

4. If the write happens via agent command template (not Python code):
   - Add the hook to the `init` command's constitution phase (if it exists)
   - Document that manual edits require `spec-kitty constitution sync`

**Files**:

- Varies — depends on where the constitution write path is in the codebase
- Likely: `src/specify_cli/cli/commands/init.py` or related orchestration code

**Notes**:

- The hook location depends on the codebase's write path for constitution
- If writes happen via agent templates (outside Python), document that auto-sync only fires for CLI writes
- Manual edits → user runs `spec-kitty constitution sync` (documented in quickstart.md)

### Subtask T035 – Implement `load_governance_config()` Convenience Function

**Purpose**: Provide a simple API for Feature 044's governance hooks to load structured config (FR-4.1).

**Steps**:

1. Add to `src/specify_cli/constitution/sync.py` or a new `loaders.py`:

   ```python
   def load_governance_config(repo_root: Path) -> GovernanceConfig:
       """Load governance config from .kittify/constitution/governance.yaml.

       Falls back to empty GovernanceConfig if file missing (FR-4.4).
       Checks staleness and logs warning if stale (FR-4.2).

       Performance: YAML loading only, no AI invocation (FR-4.5).
       """
       constitution_dir = repo_root / ".kittify" / "constitution"
       governance_path = constitution_dir / "governance.yaml"

       if not governance_path.exists():
           logger.warning(
               "governance.yaml not found. Run 'spec-kitty constitution sync'."
           )
           return GovernanceConfig()

       # Check staleness
       constitution_path = constitution_dir / "constitution.md"
       metadata_path = constitution_dir / "metadata.yaml"
       if constitution_path.exists() and metadata_path.exists():
           stale, _, _ = is_stale(constitution_path, metadata_path)
           if stale:
               logger.warning(
                   "Constitution changed since last sync. "
                   "Run 'spec-kitty constitution sync' to update."
               )

       # Load and validate
       yaml = YAML()
       data = yaml.load(governance_path)
       return GovernanceConfig.model_validate(data)
   ```

**Files**:

- `src/specify_cli/constitution/sync.py` or `loaders.py`

**Parallel?**: Yes — independent of T033-T034.

**Performance**: Must complete in <100ms (FR-4.5) — YAML loading only, no AI.

### Subtask T036 – Implement `load_agents_config()` Convenience Function

**Purpose**: Provide API for Feature 046's routing provider to load agent profiles (FR-4.3).

**Steps**:

1. Similar to T035 but for agents.yaml:

   ```python
   def load_agents_config(repo_root: Path) -> AgentsConfig:
       """Load agents config from .kittify/constitution/agents.yaml."""
       constitution_dir = repo_root / ".kittify" / "constitution"
       agents_path = constitution_dir / "agents.yaml"

       if not agents_path.exists():
           logger.warning("agents.yaml not found.")
           return AgentsConfig()

       yaml = YAML()
       data = yaml.load(agents_path)
       return AgentsConfig.model_validate(data)
   ```

**Files**:

- `src/specify_cli/constitution/sync.py` or `loaders.py`

**Parallel?**: Yes — independent of T035.

### Subtask T037 – Finalize `constitution/__init__.py` Public API Exports

**Purpose**: Define the clean public API for the constitution subpackage.

**Steps**:

1. Update `src/specify_cli/constitution/__init__.py`:

   ```python
   """Constitution parser and structured config extraction.

   Provides:
   - sync(): Parse constitution.md → structured YAML files
   - load_governance_config(): Load governance rules for hook evaluation
   - load_agents_config(): Load agent profiles for routing
   - post_save_hook(): Auto-trigger sync after CLI writes
   """

   from specify_cli.constitution.schemas import (
       AgentProfile,
       AgentsConfig,
       Directive,
       DirectivesConfig,
       ExtractionMetadata,
       GovernanceConfig,
   )
   from specify_cli.constitution.sync import (
       SyncResult,
       load_agents_config,
       load_governance_config,
       post_save_hook,
       sync,
   )

   __all__ = [
       "AgentProfile",
       "AgentsConfig",
       "Directive",
       "DirectivesConfig",
       "ExtractionMetadata",
       "GovernanceConfig",
       "SyncResult",
       "load_agents_config",
       "load_governance_config",
       "post_save_hook",
       "sync",
   ]
   ```

**Files**:

- `src/specify_cli/constitution/__init__.py`

**Parallel?**: Yes — can proceed once all modules exist.

### Subtask T038 – Write Integration Tests

**Purpose**: End-to-end tests validating the full constitution workflow.

**Steps**:

1. Create `tests/specify_cli/constitution/test_integration.py`:

2. **End-to-end tests**:
   - Write constitution.md → post_save_hook() → verify YAML files exist
   - Write constitution.md → sync() → load_governance_config() → verify values
   - Modify constitution.md → is_stale() → sync() → verify updated values
   - load_governance_config() with missing YAML → verify fallback defaults
   - load_agents_config() with empty profiles → verify empty list

3. **Post-save hook tests**:
   - Hook succeeds → verify YAML files created
   - Hook fails (mock extraction error) → verify no crash, warning logged
   - Hook with missing constitution → verify graceful handling

4. **Performance test** (informational):

   ```python
   def test_governance_loading_performance(tmp_path):
       """load_governance_config should complete in <100ms (FR-4.5)."""
       # Setup: write governance.yaml
       # Time the load
       import time
       start = time.monotonic()
       config = load_governance_config(tmp_path)
       elapsed = time.monotonic() - start
       assert elapsed < 0.1, f"Loading took {elapsed:.3f}s (>100ms)"
   ```

**Files**:

- `tests/specify_cli/constitution/test_integration.py`

**Target**: 10-12 tests covering the full workflow and edge cases.

## Test Strategy

- **Integration tests**: Full workflow from write → sync → load
- **Hook tests**: Success + failure scenarios
- **Performance test**: YAML loading < 100ms
- **Run**: `pytest tests/specify_cli/constitution/ -v`
- **Type check**: `mypy --strict src/specify_cli/constitution/`

## Risks & Mitigations

- **Risk**: Post-save hook adds latency → Deterministic extraction <500ms (acceptable per AD-4)
- **Risk**: Circular imports → Use lazy imports between modules if needed
- **Risk**: Hook fires when constitution doesn't exist yet → Check path exists before calling
- **Risk**: Feature 044/046 not ready → Convenience loaders are standalone, no dependency on 044/046

## Review Guidance

- Verify post-save hook never raises (catches all exceptions)
- Check load functions have staleness warning (FR-4.2, FR-5.2)
- Ensure **init**.py exports match quickstart.md API examples
- Test load_governance_config performance (<100ms)
- Verify the hook is wired into the correct CLI write path

## Activity Log

- 2026-02-15T22:11:29Z – system – lane=planned – Prompt created.
- 2026-02-16T05:56:56Z – claude – shell_pid=639215 – lane=for_review – Moved to for_review
- 2026-02-16T06:01:31Z – claude – shell_pid=639215 – lane=done – Self-review: All 6 subtasks complete, 13 integration tests passing, no critical issues.
