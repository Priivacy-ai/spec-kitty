---
work_package_id: WP09
title: Integration Tests and Final Validation
lane: planned
dependencies: [WP05, WP06, WP07, WP08]
subtasks:
- T040
- T041
- T042
- T043
- T044
phase: Phase 4 - Validation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- NFR-003
- NFR-004
- NFR-005
---

# Work Package Prompt: WP09 – Integration Tests and Final Validation

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP09 --base WP08
```

Depends on all prior WPs. This is the final validation gate.

---

## Objectives & Success Criteria

1. End-to-end init test across multiple agent combinations and `--skills` modes.
2. Golden-file backward compatibility test for wrapper generation across all 12 agents.
3. `mypy --strict` passes on all new modules.
4. `ruff check` passes on all new modules.
5. 90%+ test coverage for new code.
6. All success criteria from spec are verified.

## Context & Constraints

- **Spec**: SC-001 through SC-007, NFR-003, NFR-004, NFR-005
- **Plan**: Testing Strategy section
- **All new modules**: `src/specify_cli/core/agent_surface.py`, `src/specify_cli/skills/*.py`, migration file
- **Constitution**: pytest 90%+, mypy --strict, ruff check

## Subtasks & Detailed Guidance

### Subtask T040 – End-to-end init integration tests

**Purpose**: Verify the full init → skill roots → manifest → verification pipeline works.

**Steps**:
1. Create or extend `tests/specify_cli/test_cli/test_init_skills.py`
2. Integration tests that exercise the real init flow:

```python
# Test: init with all 12 agents in auto mode
def test_init_all_agents_auto(tmp_path):
    # Run init with all 12 agents
    # Verify: .agents/skills/ created (shared root)
    # Verify: .claude/skills/, .qwen/skills/, .kilocode/skills/ created (native roots)
    # Verify: manifest has all expected roots
    # Verify: manifest has wrapper files for all 12 agents
    # Verify: all wrapper directories exist

# Test: init with only wrapper-only agent
def test_init_wrapper_only_agent(tmp_path):
    # Run init with --ai q --skills auto
    # Verify: no skill root directories created
    # Verify: .amazonq/prompts/ has wrappers
    # Verify: manifest has empty installed_skill_roots

# Test: init with --skills native
def test_init_native_mode_all(tmp_path):
    # Run init with copilot + claude in native mode
    # Verify: .github/skills/ created (copilot native)
    # Verify: .claude/skills/ created (claude native)
    # Verify: .agents/skills/ NOT created (native mode avoids shared)

# Test: wrappers-only preserves pre-Phase-0 behavior
def test_init_wrappers_only_no_skill_roots(tmp_path):
    # Run init with --skills wrappers-only
    # Verify: ZERO skill root directories
    # Verify: all wrapper files present
    # Verify: manifest exists but installed_skill_roots is empty

# Test: manifest content matches filesystem
def test_manifest_reflects_reality(tmp_path):
    # Run init
    # Load manifest
    # For each managed_file entry, verify file exists and hash matches
    # For each installed_skill_root, verify directory exists
```

**Files**: `tests/specify_cli/test_cli/test_init_skills.py` (~150 lines)

**Note**: Use `--non-interactive`, `--ai`, `--no-git`, and `--template-root` (pointing to local source) flags to make init testable without interaction. Study existing init tests for patterns.

### Subtask T041 – Golden-file backward compat test

**Purpose**: SC-002 — prove wrapper output is byte-exact identical.

**Steps**:
1. Create `tests/specify_cli/test_template/test_wrapper_backward_compat.py`
2. The test should:
   a. Store reference wrapper content as test fixtures (golden files)
   b. Generate wrappers using the new code path
   c. Compare byte-by-byte

```python
# Generate golden files (run once before refactor, store as fixtures)
# Then compare after refactor:

@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_backward_compat(agent_key, tmp_path):
    """Verify new code produces identical wrappers to pre-refactor code."""
    # Generate wrappers
    generate_agent_assets(templates_dir, tmp_path, agent_key, "sh")

    surface = AGENT_SURFACE_CONFIG[agent_key]
    output_dir = tmp_path / surface.wrapper.dir

    # Verify all files match expected content
    for wrapper_file in sorted(output_dir.iterdir()):
        if not wrapper_file.name.startswith("spec-kitty."):
            continue
        content = wrapper_file.read_text(encoding="utf-8")
        # Verify non-empty
        assert len(content) > 0, f"Empty wrapper: {wrapper_file.name} for {agent_key}"
        # Verify correct extension
        assert wrapper_file.name.endswith(f".{surface.wrapper.ext}")
```

3. **Alternative approach**: If golden files are impractical, generate wrappers using the old import path (via derived view) and new import path (via `get_agent_surface`) and diff them:
   ```python
   # Both paths produce the same result because the derived view IS the canonical source
   # But this test proves it explicitly
   ```

**Files**: `tests/specify_cli/test_template/test_wrapper_backward_compat.py` (~60 lines)

### Subtask T042 – mypy --strict validation

**Purpose**: NFR-004 — type safety.

**Steps**:
1. Run `mypy --strict` on all new modules:
   ```bash
   mypy --strict src/specify_cli/core/agent_surface.py \
                 src/specify_cli/skills/ \
                 src/specify_cli/upgrade/migrations/m_2_1_0_agent_surface_manifest.py
   ```
2. Fix any type errors found.
3. Common issues to watch for:
   - Missing return type annotations
   - `dict[str, Any]` where more specific types are possible
   - Optional fields without explicit `None` handling

**Files**: All new modules

### Subtask T043 – ruff check validation

**Purpose**: NFR-005 — lint compliance.

**Steps**:
1. Run `ruff check` on all new modules:
   ```bash
   ruff check src/specify_cli/core/agent_surface.py \
              src/specify_cli/skills/ \
              src/specify_cli/upgrade/migrations/m_2_1_0_agent_surface_manifest.py
   ```
2. Fix any lint issues found.

**Files**: All new modules

### Subtask T044 – Coverage report

**Purpose**: NFR-003 — 90%+ coverage for new code.

**Steps**:
1. Run pytest with coverage:
   ```bash
   pytest tests/specify_cli/test_core/test_agent_surface.py \
          tests/specify_cli/test_skills/ \
          tests/specify_cli/test_template/test_asset_generator_compat.py \
          tests/specify_cli/test_template/test_wrapper_backward_compat.py \
          tests/specify_cli/test_migrations/test_agent_surface_migration.py \
          tests/specify_cli/test_cli/test_init_skills.py \
          tests/specify_cli/test_cli/test_sync_skills.py \
          --cov=specify_cli.core.agent_surface \
          --cov=specify_cli.skills \
          --cov-report=term-missing
   ```
2. Verify 90%+ coverage for each new module.
3. Add any missing test cases to bring coverage above threshold.

**Files**: Test files across all WPs

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Init integration tests are slow (filesystem + subprocess) | Use `--no-git` and local templates to minimize I/O |
| Golden file tests are fragile if templates change | Generate golden files from the same template set used in tests |
| Coverage calculation includes untestable branches | Mark `# pragma: no cover` for lines that cannot be reached in tests (e.g., error recovery) |

## Review Guidance

1. Verify integration tests cover ALL four `--skills` modes.
2. Verify backward compat test runs for ALL 12 agents.
3. Verify mypy and ruff output is clean (zero errors).
4. Verify coverage is 90%+ for each new module.
5. This is the final gate — approval means the feature is ready.

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
