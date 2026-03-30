---
work_package_id: WP02
title: WP Frontmatter Structured Agent
lane: "done"
dependencies: [WP01]
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 2 - Identity Integration
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: ''
review_status: "approved"
reviewed_by: "Stijn Dejongh"
review_feedback: ''
history:
- timestamp: '2026-03-08T10:13:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-004
- NFR-004
- C-002
---

# Work Package Prompt: WP02 – WP Frontmatter Structured Agent

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

- Update frontmatter read path to parse structured agent YAML mappings into `ActorIdentity`
- Update frontmatter write path to always emit structured YAML mapping for `ActorIdentity` values
- Update `WorkPackage.agent` property to return `ActorIdentity | None`
- Maintain backwards compatibility with scalar `agent: "claude"` format (C-002)

**Success metrics**:
- Read `agent: "claude"` → `ActorIdentity(tool="claude", model="unknown", ...)`
- Read `agent:\n  tool: claude\n  model: opus\n  profile: impl\n  role: impl` → `ActorIdentity(tool="claude", model="opus", profile="impl", role="impl")`
- Write `ActorIdentity` → always emits structured YAML mapping
- Unknown tool names preserved through read→write round-trip

## Context & Constraints

- **Spec**: FR-004 (Structured Frontmatter Agent), C-002 (No Frontmatter Migration)
- **Data model**: `data-model.md` — StatusEvent (modified) section shows serialisation format
- **Research**: `research.md` — R1 (serialisation strategy)
- **Dependency**: WP01 must be complete (provides `ActorIdentity` dataclass)
- **Key file**: `src/specify_cli/frontmatter.py` — current `extract_scalar()` uses regex, only handles string values
- **Key file**: `src/specify_cli/tasks_support.py` — `WorkPackage.agent` property returns `str | None`

## Subtasks & Detailed Guidance

### Subtask T006 – Update Frontmatter Read Path

**Purpose**: When reading a WP file's frontmatter, parse the `agent:` field into an `ActorIdentity` regardless of whether it's a scalar string or a YAML mapping.

**Steps**:
1. In `src/specify_cli/frontmatter.py`, examine how `extract_scalar()` works (lines ~145-154):
   - It uses regex `rf"^{key}:\s*(.+)$"` to extract values
   - This only captures single-line scalar values, not multi-line YAML mappings
2. Create a new function `extract_agent_identity()` (or modify extraction logic):
   ```python
   def extract_agent_identity(frontmatter: str) -> ActorIdentity | None:
       """Extract agent field from frontmatter, handling both scalar and mapping formats."""
       # Try YAML parsing first for structured format
       import ruamel.yaml
       yaml = ruamel.yaml.YAML(typ='safe')
       try:
           data = yaml.load(frontmatter)
           if not isinstance(data, dict):
               return None
           agent_val = data.get("agent")
           if agent_val is None or agent_val == "":
               return None
           if isinstance(agent_val, dict):
               return ActorIdentity.from_dict(agent_val)
           if isinstance(agent_val, str):
               return ActorIdentity.from_legacy(agent_val)
       except Exception:
           pass
       # Fallback to extract_scalar for simple strings
       scalar = extract_scalar(frontmatter, "agent")
       if scalar:
           return ActorIdentity.from_legacy(scalar)
       return None
   ```
3. Add import: `from specify_cli.identity import ActorIdentity`

**Files**: `src/specify_cli/frontmatter.py`
**Parallel?**: No — T007 and T008 depend on this

### Subtask T007 – Update Frontmatter Write Path

**Purpose**: When writing agent identity to frontmatter, always use the structured YAML mapping format.

**Steps**:
1. Locate the frontmatter write/update functions in `src/specify_cli/frontmatter.py`
2. When the value to write for `agent:` is an `ActorIdentity`:
   - Emit a YAML mapping:
     ```yaml
     agent:
       tool: claude
       model: opus-4
       profile: implementer
       role: implementer
     ```
3. Use `ruamel.yaml` to properly format the mapping within the frontmatter block
4. Ensure existing non-agent fields in frontmatter are not affected

**Files**: `src/specify_cli/frontmatter.py`
**Parallel?**: No — sequential with T006

**Edge cases**:
- If `ActorIdentity` has all `"unknown"` except tool, still write the full mapping (no shortcutting to scalar)
- Preserve frontmatter field ordering (ruamel.yaml preserves order by default)

### Subtask T008 – Update WorkPackage.agent Property

**Purpose**: Change the return type of `WorkPackage.agent` from `str | None` to `ActorIdentity | None` so all consumers get structured identity.

**Steps**:
1. In `src/specify_cli/tasks_support.py`, update the property (~lines 278-279):
   ```python
   # Before:
   @property
   def agent(self) -> str | None:
       return extract_scalar(self.frontmatter, "agent")
   
   # After:
   @property
   def agent(self) -> ActorIdentity | None:
       from specify_cli.frontmatter import extract_agent_identity
       return extract_agent_identity(self.frontmatter)
   ```
2. Add import at top of file or use lazy import as shown
3. Search for callers of `WorkPackage.agent` and verify they handle the new type:
   - Use `rg "\.agent" src/specify_cli/tasks_support.py src/specify_cli/cli/ --type py` to find usages
   - Update any code that treats the return value as a plain string

**Files**: `src/specify_cli/tasks_support.py`
**Parallel?**: No — depends on T006

### Subtask T009 – Handle Unknown Tool Names in Round-Trip

**Purpose**: Ensure that WP frontmatter containing agent identities with unknown/custom tool names (not in the known agent list) can be stored and read back faithfully without data loss.

**Steps**:
1. Write a test case: create frontmatter with `agent:\n  tool: my-custom-agent\n  model: v1\n  ...`
2. Read it back and verify `ActorIdentity(tool="my-custom-agent", model="v1", ...)`
3. Write it back and verify the YAML mapping is preserved identically
4. Ensure no validation rejects unknown tool names — `ActorIdentity` only validates non-empty strings

**Files**: `tests/specify_cli/test_frontmatter_agent.py` (or add to existing test file)
**Parallel?**: Yes — can proceed alongside T006-T008

## Test Strategy

- Unit tests for `extract_agent_identity()`: scalar input, mapping input, empty, None
- Round-trip test: write structured → read → compare
- Legacy compat test: read `agent: "claude"` → verify ActorIdentity
- Unknown tool test: read/write custom tool name → verify preservation
- Regression: `pytest tests/specify_cli/ -k frontmatter -v` should pass

## Risks & Mitigations

- **Frontmatter regex parsing vs YAML parsing**: Current regex approach may conflict with ruamel.yaml parsing → use YAML parsing as primary path, regex as fallback
- **Performance**: YAML parsing is slower than regex → acceptable for CLI tool (< 2s budget)
- **Existing callers of `WorkPackage.agent`**: May expect `str` → search and update all callers

## Review Guidance

- Verify both scalar and mapping formats parse correctly
- Verify write always produces mapping format
- Verify round-trip preserves all fields
- Check that `WorkPackage.agent` callers handle `ActorIdentity | None`
- Run `pytest tests/specify_cli/ -v -k "frontmatter or tasks_support"` — 0 failures

## Activity Log

- 2026-03-08T10:13:04Z – system – lane=planned – Prompt created.
- 2026-03-09T04:29:01Z – claude-sonnet-4-6 – lane=done – Implementation complete and merged | Done override: History was rebased; branch ancestry tracking not applicable
