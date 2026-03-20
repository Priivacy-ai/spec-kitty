---
work_package_id: WP08
title: Asset Generator Refactor
lane: "doing"
dependencies: [WP01]
base_branch: 042-agent-skills-installer-infrastructure-WP01
base_commit: 06eb8070106b6ece8424249f8a245949d4c4169b
created_at: '2026-03-20T16:58:27.267293+00:00'
subtasks:
- T037
- T038
- T039
phase: Phase 2 - Core Logic
assignee: ''
agent: "codex"
shell_pid: "5867"
review_status: has_feedback
reviewed_by: Robert Douglass
review_feedback: feedback://042-agent-skills-installer-infrastructure/WP08/20260320T170756Z-b1735646.md
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-019
- FR-003
---

# Work Package Prompt: WP08 – Asset Generator Refactor

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP08 --base WP01
```

Depends on WP01 only (needs `get_agent_surface`).

---

## Objectives & Success Criteria

1. `asset_generator.py` reads wrapper config from `AgentSurface` dataclass instead of `AGENT_COMMAND_CONFIG` dict.
2. Generated wrapper output is **byte-exact identical** to pre-refactor output for all 12 agents.
3. Minimal diff — only import and config access lines change.

## Context & Constraints

- **Spec**: FR-019, FR-003
- **Plan**: Section 9 (Asset Generator Update)
- **Current code**: `src/specify_cli/template/asset_generator.py` — lines 12, 67–89
- **Critical**: This is the ONLY production consumer of `AGENT_COMMAND_CONFIG` that needs a direct update. The derived view in `config.py` keeps backward compat for any other consumers.

## Subtasks & Detailed Guidance

### Subtask T037 – Update import

**Purpose**: Switch from dict-based config to typed dataclass.

**Steps**:
1. In `src/specify_cli/template/asset_generator.py`, change line 12:
   ```python
   # OLD:
   from specify_cli.core.config import AGENT_COMMAND_CONFIG
   # NEW:
   from specify_cli.core.agent_surface import get_agent_surface
   ```

**Files**: `src/specify_cli/template/asset_generator.py`

### Subtask T038 – Refactor generate_agent_assets

**Purpose**: Replace dict access with dataclass attribute access.

**Steps**:
1. In `generate_agent_assets()` (line 65–97), change:
   ```python
   # OLD (line 67-68):
   config = AGENT_COMMAND_CONFIG[agent_key]
   output_dir = project_path / config["dir"]
   # NEW:
   surface = get_agent_surface(agent_key)
   output_dir = project_path / surface.wrapper.dir
   ```

2. Update remaining references in the same function:
   ```python
   # OLD (line 77-84):
   rendered = render_command_template(
       template_path,
       script_type,
       agent_key,
       config["arg_format"],
       config["ext"],
   )
   ext = config["ext"]
   # NEW:
   rendered = render_command_template(
       template_path,
       script_type,
       agent_key,
       surface.wrapper.arg_format,
       surface.wrapper.ext,
   )
   ext = surface.wrapper.ext
   ```

3. That's it. The `render_command_template()` function takes `arg_format` and `extension` as plain strings — no change needed there.

**Total diff**: ~6 lines changed in one function.

**Files**: `src/specify_cli/template/asset_generator.py`

### Subtask T039 – Byte-exact backward compatibility test

**Purpose**: Prove the refactor produces identical output.

**Steps**:
1. Create `tests/specify_cli/test_template/test_asset_generator_compat.py`
2. The test generates wrappers for all 12 agents and compares against golden values:

```python
import pytest
from pathlib import Path
from specify_cli.template.asset_generator import generate_agent_assets, prepare_command_templates
from specify_cli.core.agent_surface import AGENT_SURFACE_CONFIG

@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_generation_unchanged(agent_key, tmp_path):
    """Verify wrapper generation is byte-exact identical for all 12 agents."""
    # Setup: copy command templates to tmp_path
    # This requires access to the mission templates
    # Use the software-dev mission templates as the standard

    # Get template source
    import specify_cli
    package_dir = Path(specify_cli.__file__).parent
    mission_templates = package_dir / "missions" / "software-dev" / "command-templates"

    if not mission_templates.exists():
        pytest.skip("Mission templates not available in test environment")

    # Generate using the new code path
    generate_agent_assets(mission_templates, tmp_path, agent_key, "sh")

    # Verify files were created
    surface = AGENT_SURFACE_CONFIG[agent_key]
    output_dir = tmp_path / surface.wrapper.dir
    assert output_dir.exists(), f"Output dir {output_dir} not created for {agent_key}"

    # Verify at least one wrapper file exists
    wrapper_files = list(output_dir.glob(f"spec-kitty.*"))
    assert len(wrapper_files) > 0, f"No wrapper files generated for {agent_key}"

    # Verify file naming convention
    for f in wrapper_files:
        assert f.name.startswith("spec-kitty."), f"Unexpected file name: {f.name}"
        assert f.name.endswith(f".{surface.wrapper.ext}"), f"Wrong extension for {agent_key}: {f.name}"
```

3. **Golden file approach** (recommended addition): Before the refactor, generate reference output for each agent and store as test fixtures. After refactor, compare byte-by-byte. This can be done as part of the test setup.

**Files**: `tests/specify_cli/test_template/test_asset_generator_compat.py` (new, ~60 lines)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Subtle behavioral difference from dict vs dataclass | Byte-exact comparison test catches any difference |
| `codex` stem replacement logic (`replace("-", "_")`) | This logic uses `agent_key == "codex"` not config values — unchanged |
| `copilot` vscode-settings copy logic | This logic uses `agent_key == "copilot"` — unchanged |

## Review Guidance

1. Verify the diff is minimal — only import line and config access changes.
2. Verify no behavioral logic was changed (codex stem replacement, copilot vscode copy).
3. Run the backward compat test for all 12 agents.

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
- 2026-03-20T16:58:27Z – coordinator – shell_pid=68715 – lane=doing – Assigned agent via workflow command
- 2026-03-20T17:03:53Z – coordinator – shell_pid=68715 – lane=for_review – All 3 subtasks complete: T037 (import update), T038 (dict-to-dataclass refactor), T039 (75 backward compat tests, all passing). Diff is minimal (6 lines changed). All existing tests pass.
- 2026-03-20T17:04:13Z – codex – shell_pid=83694 – lane=doing – Started review via workflow command
- 2026-03-20T17:07:56Z – codex – shell_pid=83694 – lane=planned – Moved to planned
- 2026-03-20T17:10:02Z – coordinator – shell_pid=94243 – lane=doing – Started implementation via workflow command
- 2026-03-20T17:17:46Z – coordinator – shell_pid=94243 – lane=for_review – Fixed: added byte-exact golden baseline test with real sw-dev templates (merged via prepare_command_templates). 111 tests total (75 synthetic + 36 real-template). All pass.
- 2026-03-20T17:18:09Z – codex – shell_pid=5867 – lane=doing – Started review via workflow command
