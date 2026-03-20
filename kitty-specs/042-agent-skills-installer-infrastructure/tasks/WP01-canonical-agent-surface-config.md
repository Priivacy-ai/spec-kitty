---
work_package_id: WP01
title: Canonical Agent Surface Config
lane: "doing"
dependencies: []
base_branch: main
base_commit: 4054a2d1253a294814072ecba33a429142fc41ee
created_at: '2026-03-20T16:38:56.718624+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Foundation
assignee: ''
agent: "coordinator"
shell_pid: "58802"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
review_feedback: "feedback://042-agent-skills-installer-infrastructure/WP01/20260320T164958Z-9a4c3c54.md"
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-018
- NFR-001
- NFR-004
- NFR-005
- C-006
---

# Work Package Prompt: WP01 – Canonical Agent Surface Config

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies — this WP branches from main.

---

## Objectives & Success Criteria

1. Create `AGENT_SURFACE_CONFIG` as the single canonical agent registry with all 12 agents.
2. Each agent entry includes distribution class, skill roots, wrapper config, and compatibility notes per PRD section 8.1.
3. Derived compatibility views produce **byte-exact** equivalents of the old `AGENT_COMMAND_CONFIG`, `AGENT_DIRS`, and `AGENT_DIR_TO_KEY`.
4. All existing import paths continue to work — zero call-site changes for consumers.
5. New code passes `mypy --strict` and `ruff check`.

## Context & Constraints

- **Spec**: `kitty-specs/042-agent-skills-installer-infrastructure/spec.md` (FR-001, FR-002, FR-003, FR-018, NFR-001, C-006)
- **Plan**: `kitty-specs/042-agent-skills-installer-infrastructure/plan.md` (Sections 1–2, Call-Site Impact Analysis)
- **Data model**: `kitty-specs/042-agent-skills-installer-infrastructure/data-model.md` (AgentSurface, WrapperConfig, DistributionClass)
- **Current AGENT_COMMAND_CONFIG**: `src/specify_cli/core/config.py` lines 44–57
- **Current AGENT_DIRS**: `src/specify_cli/agent_utils/directories.py` lines 16–29
- **Current AGENT_DIR_TO_KEY**: `src/specify_cli/agent_utils/directories.py` lines 33–46
- **Critical constraint**: `agent_surface.py` must be **self-contained** — it must NOT import from `config.py` or `directories.py` to avoid circular imports. The flow is one-directional: `agent_surface.py` defines → `config.py`/`directories.py` derive.

## Subtasks & Detailed Guidance

### Subtask T001 – Create agent_surface.py with dataclasses

**Purpose**: Define the DistributionClass enum, WrapperConfig value object, and AgentSurface entity as typed, frozen dataclasses.

**Steps**:
1. Create `src/specify_cli/core/agent_surface.py`
2. Add `from __future__ import annotations`
3. Define `DistributionClass(Enum)` with three values:
   - `SHARED_ROOT_CAPABLE = "shared-root-capable"`
   - `NATIVE_ROOT_REQUIRED = "native-root-required"`
   - `WRAPPER_ONLY = "wrapper-only"`
4. Define `WrapperConfig` as `@dataclass(frozen=True)` with fields `dir: str`, `ext: str`, `arg_format: str`
5. Define `AgentSurface` as `@dataclass(frozen=True)` with fields:
   - `key: str`
   - `display_name: str`
   - `distribution_class: DistributionClass`
   - `agent_root: str`
   - `wrapper: WrapperConfig`
   - `wrapper_subdir: str`
   - `skill_roots: tuple[str, ...]`
   - `compat_notes: str = ""`

**Files**: `src/specify_cli/core/agent_surface.py` (new, ~200 lines)

### Subtask T002 – Populate AGENT_SURFACE_CONFIG with all 12 agents

**Purpose**: Hand-maintain the canonical registry with accurate data per PRD section 8.1.

**Steps**:
1. In `agent_surface.py`, define `AGENT_SURFACE_CONFIG: dict[str, AgentSurface]` as a module-level dict
2. Add all 12 entries. The wrapper config values MUST match the current `AGENT_COMMAND_CONFIG` exactly:

```python
AGENT_SURFACE_CONFIG: dict[str, AgentSurface] = {
    "claude": AgentSurface(
        key="claude",
        display_name="Claude Code",
        distribution_class=DistributionClass.NATIVE_ROOT_REQUIRED,
        agent_root=".claude",
        wrapper=WrapperConfig(dir=".claude/commands", ext="md", arg_format="$ARGUMENTS"),
        wrapper_subdir="commands",
        skill_roots=(".claude/skills/",),
        compat_notes="Commands merged into skills; also supports personal, plugin, enterprise, nested project skills",
    ),
    "copilot": AgentSurface(
        key="copilot",
        display_name="GitHub Copilot",
        distribution_class=DistributionClass.SHARED_ROOT_CAPABLE,
        agent_root=".github",
        wrapper=WrapperConfig(dir=".github/prompts", ext="prompt.md", arg_format="$ARGUMENTS"),
        wrapper_subdir="prompts",
        skill_roots=(".agents/skills/", ".github/skills/"),
        compat_notes="Also scans .claude/skills/; user roots, plugin dirs, COPILOT_SKILLS_DIRS",
    ),
    # ... continue for all 12 agents
}
```

3. Verify each entry matches the capability matrix in the plan:

| Key | Distribution Class | Skill Roots | wrapper.dir | wrapper.ext | wrapper.arg_format |
|-----|-------------------|-------------|-------------|-------------|-------------------|
| `claude` | NATIVE_ROOT_REQUIRED | `(".claude/skills/",)` | `.claude/commands` | `md` | `$ARGUMENTS` |
| `copilot` | SHARED_ROOT_CAPABLE | `(".agents/skills/", ".github/skills/")` | `.github/prompts` | `prompt.md` | `$ARGUMENTS` |
| `gemini` | SHARED_ROOT_CAPABLE | `(".agents/skills/", ".gemini/skills/")` | `.gemini/commands` | `toml` | `{{args}}` |
| `cursor` | SHARED_ROOT_CAPABLE | `(".agents/skills/", ".cursor/skills/")` | `.cursor/commands` | `md` | `$ARGUMENTS` |
| `qwen` | NATIVE_ROOT_REQUIRED | `(".qwen/skills/",)` | `.qwen/commands` | `toml` | `{{args}}` |
| `opencode` | SHARED_ROOT_CAPABLE | `(".agents/skills/", ".opencode/skills/")` | `.opencode/command` | `md` | `$ARGUMENTS` |
| `windsurf` | SHARED_ROOT_CAPABLE | `(".agents/skills/", ".windsurf/skills/")` | `.windsurf/workflows` | `md` | `$ARGUMENTS` |
| `codex` | SHARED_ROOT_CAPABLE | `(".agents/skills/",)` | `.codex/prompts` | `md` | `$ARGUMENTS` |
| `kilocode` | NATIVE_ROOT_REQUIRED | `(".kilocode/skills/",)` | `.kilocode/workflows` | `md` | `$ARGUMENTS` |
| `auggie` | SHARED_ROOT_CAPABLE | `(".agents/skills/", ".augment/skills/")` | `.augment/commands` | `md` | `$ARGUMENTS` |
| `roo` | SHARED_ROOT_CAPABLE | `(".agents/skills/", ".roo/skills/")` | `.roo/commands` | `md` | `$ARGUMENTS` |
| `q` | WRAPPER_ONLY | `()` | `.amazonq/prompts` | `md` | `$ARGUMENTS` |

**Critical**: The `codex` wrapper ext is `md`, NOT `prompt.md`. Check the current `AGENT_COMMAND_CONFIG` carefully — `codex` uses `"ext": "md"` while `copilot` uses `"ext": "prompt.md"`. This distinction must be preserved exactly.

**Files**: `src/specify_cli/core/agent_surface.py`

### Subtask T003 – Implement derived view functions

**Purpose**: Create functions that compute the old data shapes from the canonical source.

**Steps**:
1. Add to `agent_surface.py`:

```python
def get_agent_command_config() -> dict[str, dict[str, str]]:
    """Derive AGENT_COMMAND_CONFIG-compatible dict from canonical config."""
    return {
        key: {"dir": s.wrapper.dir, "ext": s.wrapper.ext, "arg_format": s.wrapper.arg_format}
        for key, s in AGENT_SURFACE_CONFIG.items()
    }

def get_agent_dirs() -> list[tuple[str, str]]:
    """Derive AGENT_DIRS-compatible list from canonical config."""
    return [(s.agent_root, s.wrapper_subdir) for s in AGENT_SURFACE_CONFIG.values()]

def get_agent_dir_to_key() -> dict[str, str]:
    """Derive AGENT_DIR_TO_KEY-compatible dict from canonical config."""
    return {s.agent_root: s.key for s in AGENT_SURFACE_CONFIG.values()}

def get_agent_surface(agent_key: str) -> AgentSurface:
    """Return full capability profile for one agent. Raises KeyError if not found."""
    return AGENT_SURFACE_CONFIG[agent_key]
```

2. Add `__all__` list exporting all public names.

**Files**: `src/specify_cli/core/agent_surface.py`

### Subtask T004 – Wire derived AGENT_COMMAND_CONFIG into config.py

**Purpose**: Replace the hardcoded dict in `config.py` with a derived view from the canonical source.

**Steps**:
1. In `src/specify_cli/core/config.py`, replace lines 44–57 (the hardcoded `AGENT_COMMAND_CONFIG` dict) with:

```python
from specify_cli.core.agent_surface import get_agent_command_config

AGENT_COMMAND_CONFIG: dict[str, dict[str, str]] = get_agent_command_config()
```

2. Keep the type annotation so existing consumers see the same type.
3. **DO NOT** change `AI_CHOICES` or any other constant in this file.
4. **DO NOT** remove `AGENT_COMMAND_CONFIG` from the `__all__` list.

**Files**: `src/specify_cli/core/config.py`

**Validation**: After this change, `AGENT_COMMAND_CONFIG["claude"]` must return `{"dir": ".claude/commands", "ext": "md", "arg_format": "$ARGUMENTS"}` — identical to the old hardcoded value.

### Subtask T005 – Wire derived AGENT_DIRS and AGENT_DIR_TO_KEY into directories.py

**Purpose**: Replace the hardcoded lists in `directories.py` with derived views.

**Steps**:
1. In `src/specify_cli/agent_utils/directories.py`, replace lines 16–46 (the hardcoded `AGENT_DIRS` list and `AGENT_DIR_TO_KEY` dict) with:

```python
from specify_cli.core.agent_surface import get_agent_dirs, get_agent_dir_to_key

# Canonical list derived from AGENT_SURFACE_CONFIG
AGENT_DIRS: list[tuple[str, str]] = get_agent_dirs()

# Mapping derived from AGENT_SURFACE_CONFIG
AGENT_DIR_TO_KEY: dict[str, str] = get_agent_dir_to_key()
```

2. Keep the existing type annotations.
3. **DO NOT** change the `get_agent_dirs_for_project()` function — it reads from `AGENT_DIRS` which is now derived but has the same value.

**Files**: `src/specify_cli/agent_utils/directories.py`

**Validation**: `AGENT_DIRS[0]` must still be `(".claude", "commands")`. `AGENT_DIR_TO_KEY[".github"]` must still be `"copilot"`.

### Subtask T006 – Update __init__.py re-exports

**Purpose**: Make new public API available through expected import paths.

**Steps**:
1. In `src/specify_cli/core/__init__.py`, add imports and re-exports for:
   - `AGENT_SURFACE_CONFIG`
   - `AgentSurface`
   - `DistributionClass`
   - `WrapperConfig`
   - `get_agent_surface`
2. In `src/specify_cli/agent_utils/__init__.py`, verify `AGENT_DIRS`, `AGENT_DIR_TO_KEY`, `get_agent_dirs_for_project` are still re-exported (they should be — no changes needed if they already are).

**Files**: `src/specify_cli/core/__init__.py`, `src/specify_cli/agent_utils/__init__.py`

### Subtask T007 – Unit tests

**Purpose**: Verify correctness, backward compatibility, and PRD matrix compliance.

**Steps**:
1. Create `tests/specify_cli/test_core/test_agent_surface.py`
2. Write tests:

```python
# Test all 12 agents present
def test_all_agents_present():
    assert len(AGENT_SURFACE_CONFIG) == 12
    assert set(AGENT_SURFACE_CONFIG.keys()) == {"claude", "copilot", "gemini", "cursor", "qwen", "opencode", "windsurf", "codex", "kilocode", "auggie", "roo", "q"}

# Test distribution class assignments match PRD
@pytest.mark.parametrize("agent_key,expected_class", [
    ("claude", DistributionClass.NATIVE_ROOT_REQUIRED),
    ("copilot", DistributionClass.SHARED_ROOT_CAPABLE),
    # ... all 12
    ("q", DistributionClass.WRAPPER_ONLY),
])
def test_distribution_classes(agent_key, expected_class):
    assert AGENT_SURFACE_CONFIG[agent_key].distribution_class == expected_class

# Test derived AGENT_COMMAND_CONFIG matches old hardcoded values
def test_derived_agent_command_config_matches_legacy():
    derived = get_agent_command_config()
    # Compare against known-good values from the old hardcoded dict
    assert derived["claude"] == {"dir": ".claude/commands", "ext": "md", "arg_format": "$ARGUMENTS"}
    assert derived["gemini"] == {"dir": ".gemini/commands", "ext": "toml", "arg_format": "{{args}}"}
    assert derived["copilot"] == {"dir": ".github/prompts", "ext": "prompt.md", "arg_format": "$ARGUMENTS"}
    # ... all 12

# Test derived AGENT_DIRS matches old hardcoded values
def test_derived_agent_dirs_matches_legacy():
    dirs = get_agent_dirs()
    assert dirs[0] == (".claude", "commands")
    assert (".github", "prompts") in dirs
    assert len(dirs) == 12

# Test derived AGENT_DIR_TO_KEY matches old hardcoded values
def test_derived_agent_dir_to_key_matches_legacy():
    mapping = get_agent_dir_to_key()
    assert mapping[".github"] == "copilot"
    assert mapping[".augment"] == "auggie"
    assert mapping[".amazonq"] == "q"

# Test wrapper-only agents have no skill roots
def test_wrapper_only_no_skill_roots():
    assert AGENT_SURFACE_CONFIG["q"].skill_roots == ()

# Test native-root-required agents don't list .agents/skills/
def test_native_agents_no_shared_root():
    for key in ("claude", "qwen", "kilocode"):
        surface = AGENT_SURFACE_CONFIG[key]
        assert ".agents/skills/" not in surface.skill_roots

# Test get_agent_surface function
def test_get_agent_surface():
    surface = get_agent_surface("claude")
    assert surface.key == "claude"
    assert surface.distribution_class == DistributionClass.NATIVE_ROOT_REQUIRED

def test_get_agent_surface_invalid_key():
    with pytest.raises(KeyError):
        get_agent_surface("nonexistent")

# Test structural consistency: wrapper.dir == agent_root/wrapper_subdir
@pytest.mark.parametrize("agent_key", list(AGENT_SURFACE_CONFIG.keys()))
def test_wrapper_dir_consistency(agent_key):
    s = AGENT_SURFACE_CONFIG[agent_key]
    assert s.wrapper.dir == f"{s.agent_root}/{s.wrapper_subdir}"
```

**Files**: `tests/specify_cli/test_core/test_agent_surface.py` (new, ~120 lines)

## Test Strategy

- All tests are unit tests — no I/O, no filesystem, no subprocess
- Parametrized across all 12 agents where applicable
- Derived view tests compare against known-good values from the old hardcoded dicts
- Run: `pytest tests/specify_cli/test_core/test_agent_surface.py -v`

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular import between agent_surface.py and config.py | Import error at startup | agent_surface.py must not import from config.py. Flow is one-directional. |
| Derived AGENT_DIRS order changes | Migrations may process agents in different order | Verify order in tests; order comes from dict insertion order in AGENT_SURFACE_CONFIG |
| Typo in wrapper config values | Wrappers generated to wrong paths | Byte-exact comparison tests in WP08 catch this |

## Review Guidance

1. **Verify each of the 12 entries** against the table in T002. Any mismatch in wrapper dir/ext/arg_format is a regression.
2. Verify `agent_surface.py` has **zero imports** from `config.py` or `directories.py`.
3. Verify derived views match old values by running the unit tests.
4. Check `__all__` lists are updated.

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
- 2026-03-20T16:38:57Z – coordinator – shell_pid=29009 – lane=doing – Assigned agent via workflow command
- 2026-03-20T16:45:04Z – coordinator – shell_pid=29009 – lane=for_review – Ready for review: canonical agent surface config with 12 agents, derived views, and 51 unit tests
- 2026-03-20T16:45:38Z – codex – shell_pid=52348 – lane=doing – Started review via workflow command
- 2026-03-20T16:49:58Z – codex – shell_pid=52348 – lane=planned – Moved to planned
- 2026-03-20T16:50:44Z – coordinator – shell_pid=58802 – lane=doing – Started implementation via workflow command
