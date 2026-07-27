---
work_package_id: WP08
title: End-to-End Integration Tests
lane: "done"
dependencies: [WP01, WP02, WP03, WP06, WP07]
subtasks:
- T033
- T034
- T035
- T036
- T037
phase: Phase 4 - Convergence
assignee: Codex
agent: "codex:gpt-5:reviewer:reviewer"
shell_pid: ''
review_status: "approved"
reviewed_by: "Codex"
review_feedback: ''
history:
- timestamp: '2026-03-08T10:13:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-010
- NFR-001
- NFR-004
---

# Work Package Prompt: WP08 – End-to-End Integration Tests

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Implementation Command

```bash
spec-kitty implement WP08 --base WP07
```

---

## Objectives & Success Criteria

- Validate both tracks work together end-to-end
- Track A: structured identity flows CLI → frontmatter → event log → read back with all 4 fields intact
- Track B: profile-aware compilation resolves directives → tactics → guides transitively
- Regression: all existing test suites pass without modification

**Success metrics**:
- SC-001: 100% of new events carry structured actor; 100% of legacy events read without errors
- SC-002: All existing test suites pass (0 modifications needed)
- SC-004: CLI flags correctly populate event log in 100% of test scenarios
- SC-005: Compilation without DoctrineService emits exactly one diagnostic warning

## Context & Constraints

- **Spec**: FR-010 (End-to-End Pipeline), all success criteria
- **All prior WPs**: WP01–WP07 must be complete
- **Test locations**: `tests/integration/` for new integration tests
- **Existing tests**: `tests/specify_cli/status/`, `tests/specify_cli/constitution/` for regression
- **Tools**: Use `rg` (ripgrep) for all code searches — do NOT use `grep`. Example: `rg "ActorIdentity" tests/`

## Subtasks & Detailed Guidance

### Subtask T033 – Integration Test: Structured Identity Pipeline

**Purpose**: Verify that a structured identity written to WP frontmatter flows through the full pipeline to the event log and back.

**Steps**:
1. Create `tests/integration/test_structured_identity_e2e.py`
2. Test scenario:
   ```python
   def test_structured_identity_full_pipeline(tmp_path):
       """Structured identity flows: frontmatter → status event → JSONL → read back."""
       # 1. Write a WP file with structured agent frontmatter
       wp_content = textwrap.dedent("""\
           ---
           work_package_id: "WP01"
           title: "Test WP"
           lane: "planned"
           agent:
             tool: claude
             model: opus-4
             profile: implementer
             role: implementer
           ---
           # Test WP
       """)
       wp_file = tmp_path / "WP01-test.md"
       wp_file.write_text(wp_content)
       
       # 2. Read frontmatter and extract agent identity
       from specify_cli.frontmatter import extract_agent_identity
       identity = extract_agent_identity(wp_content.split("---")[1])
       assert identity is not None
       assert identity.tool == "claude"
       assert identity.model == "opus-4"
       
       # 3. Emit a status event with this identity
       # ... set up feature dir, emit transition ...
       
       # 4. Read back from JSONL
       from specify_cli.status.store import read_events
       events = read_events(feature_dir)
       assert events[-1].actor.tool == "claude"
       assert events[-1].actor.model == "opus-4"
       assert events[-1].actor.profile == "implementer"
       assert events[-1].actor.role == "implementer"
   ```
3. Include setup for feature directory, meta.json, and event log file

**Files**: `tests/integration/test_structured_identity_e2e.py` (NEW)
**Parallel?**: Yes — independent test file

### Subtask T034 – Integration Test: Profile-Aware Constitution Compilation

**Purpose**: Verify profile-aware compilation produces the correct transitive closure of governance artifacts.

**Steps**:
1. Create `tests/integration/test_profile_constitution_e2e.py`
2. Test scenario:
   ```python
   def test_profile_aware_compilation(tmp_path):
       """Profile compilation resolves directives → tactics → guides transitively."""
       # 1. Set up doctrine directory with:
       #    - directive D1 with tactic_refs: [T1]
       #    - tactic T1 with references: [{type: styleguide, id: S1}]
       #    - styleguide S1
       #    - agent profile "reviewer" with directive_references: [{code: D1}]
       
       # 2. Initialize DoctrineService
       service = DoctrineService(shipped_root=tmp_path / "doctrine")
       
       # 3. Create interview with agent_profile="reviewer"
       interview = ConstitutionInterview(
           mission="software-dev",
           profile="minimal",
           answers={},
           selected_paradigms=[],
           selected_directives=[],
           available_tools=[],
           agent_profile="reviewer",
       )
       
       # 4. Compile constitution
       result = compile_constitution(
           mission="software-dev",
           interview=interview,
           doctrine_service=service,
       )
       
       # 5. Verify output includes D1, T1, S1
       assert "D1" in str(result.markdown) or "D1" in str(result.references)
       # Verify transitive resolution
   ```
3. Set up fixture YAML files for directives, tactics, styleguides, and agent profiles

**Files**: `tests/integration/test_profile_constitution_e2e.py` (NEW)
**Parallel?**: Yes — independent test file

### Subtask T035 – Integration Test: CLI Compound Flag → Event Log

**Purpose**: Verify CLI `--agent` compound flag produces a structured event log entry.

**Steps**:
1. Add to `tests/integration/test_structured_identity_e2e.py`:
   ```python
   def test_cli_compound_agent_flag(tmp_path):
       """CLI --agent flag produces structured actor in JSONL."""
       # 1. Set up a project with a WP in planned state
       # 2. Call move-task programmatically:
       from typer.testing import CliRunner
       runner = CliRunner()
       result = runner.invoke(app, [
           "agent", "tasks", "move-task", "WP01",
           "--to", "doing",
           "--agent", "claude:opus-4:implementer:implementer",
           "--feature", feature_slug,
       ])
       assert result.exit_code == 0
       
       # 3. Read JSONL event
       events = read_events(feature_dir)
       last = events[-1]
       assert isinstance(last.actor, ActorIdentity)
       assert last.actor.tool == "claude"
       assert last.actor.model == "opus-4"
   ```

**Files**: `tests/integration/test_structured_identity_e2e.py`
**Parallel?**: Yes — same file but independent test

### Subtask T036 – Regression Validation

**Purpose**: Ensure all existing test suites pass without modification.

**Steps**:
1. Run full existing test suites:
   ```bash
   pytest tests/specify_cli/status/ -v
   pytest tests/specify_cli/constitution/ -v
   ```
2. Both must produce 0 failures, 0 errors
3. If any test fails, investigate whether it's a real regression or a test that needs updating
4. Document any test modifications needed (should be 0 per NFR-004)

**Files**: No new files — run existing tests
**Parallel?**: No — validation step, run after all changes

### Subtask T037 – Integration Test: Mixed Event Log Reduces Correctly

**Purpose**: Verify that a JSONL event log containing both legacy bare-string actors and new structured actors reduces to a valid snapshot.

**Steps**:
1. Add to `tests/integration/test_structured_identity_e2e.py`:
   ```python
   def test_mixed_event_log_reduces(tmp_path):
       """Mixed event log (legacy + structured) produces valid snapshot."""
       # 1. Create JSONL with mixed actor formats
       events_jsonl = [
           # Legacy event (bare string actor)
           '{"event_id":"01","feature_slug":"test","wp_id":"WP01",'
           '"from_lane":"planned","to_lane":"claimed","at":"2026-01-01T00:00:00Z",'
           '"actor":"claude","force":false,"execution_mode":"direct_repo"}',
           # Structured event (dict actor)
           '{"event_id":"02","feature_slug":"test","wp_id":"WP01",'
           '"from_lane":"claimed","to_lane":"in_progress","at":"2026-01-01T01:00:00Z",'
           '"actor":{"tool":"claude","model":"opus-4","profile":"impl","role":"impl"},'
           '"force":false,"execution_mode":"worktree"}',
       ]
       
       # 2. Write to event log file
       event_file = tmp_path / "status.events.jsonl"
       event_file.write_text("\n".join(events_jsonl) + "\n")
       
       # 3. Read and reduce
       from specify_cli.status.store import read_events
       from specify_cli.status.reducer import reduce
       events = read_events(tmp_path)
       snapshot = reduce(events)
       
       # 4. Assert valid snapshot
       assert len(events) == 2
       assert events[0].actor.tool == "claude"
       assert events[0].actor.model == "unknown"  # legacy
       assert events[1].actor.tool == "claude"
       assert events[1].actor.model == "opus-4"   # structured
       assert snapshot is not None  # Valid reduction
   ```

**Files**: `tests/integration/test_structured_identity_e2e.py`
**Parallel?**: Yes — independent test function

## Test Strategy

- Run all integration tests: `pytest tests/integration/ -v -k "structured_identity or profile_constitution"`
- Run all regression tests: `pytest tests/specify_cli/status/ tests/specify_cli/constitution/ -v`
- Combined: `pytest tests/ -v --tb=short` for full suite
- Type check: `mypy src/specify_cli/identity.py src/specify_cli/status/ src/specify_cli/constitution/`

## Risks & Mitigations

- **Test fixture complexity**: Integration tests need full project setup → use `tmp_path` fixtures and minimal file structures
- **Import paths**: Integration tests may have different import context → ensure `src/` is on PYTHONPATH
- **Flaky timestamps**: Use deterministic timestamps in test JSONL data

## Review Guidance

- Verify each integration test exercises the full pipeline (not just individual components)
- Verify regression tests produce 0 failures
- Verify mixed event log test covers the backwards compatibility contract
- Verify test fixtures are minimal and self-contained
- Run `pytest tests/ -v --tb=short` — 0 failures

## Activity Log

- 2026-03-08T10:13:04Z – system – lane=planned – Prompt created.
- 2026-03-09T06:13:18Z – codex:gpt-5:implementer:implementer – lane=in_progress – Starting FEAT-48 end-to-end convergence tests.
- 2026-03-09T06:14:02Z – codex:gpt-5:implementer:implementer – lane=for_review – Integration coverage complete for structured identity and profile-aware constitution flows.
- 2026-03-09T06:19:38Z – codex:gpt-5:reviewer:reviewer – lane=done – Reviewed: focused FEAT-48 integration coverage and regressions passed without blocking findings. | Done override: Approved on feature branch prior to feature merge.
