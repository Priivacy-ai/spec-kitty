---
work_package_id: WP02
title: Gemini/Qwen Shim Generation Fix
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-stabilization-release-core-bug-fixes-01KPQJAN
base_commit: aa295eb7d50473be016f6cbddca2976f68ca93b8
created_at: '2026-04-21T09:24:54.622952+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
shell_pid: "70133"
agent: "claude:sonnet:reviewer:reviewer"
history:
- 2026-04-21T08:41:50Z – planned – stabilization WP02
authoritative_surface: src/specify_cli/shims/
execution_mode: code_change
mission_id: 01KPQJAN4P2V4MTHRFGS7VW17M
mission_slug: stabilization-release-core-bug-fixes-01KPQJAN
owned_files:
- src/specify_cli/shims/generator.py
- src/specify_cli/runtime/agent_commands.py
- tests/specify_cli/shims/
- tests/specify_cli/regression/_twelve_agent_baseline/
tags: []
---

# WP02 — Gemini/Qwen Shim Generation Fix

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Dependency**: WP01 must be approved before this WP is claimed.
- **Workspace**: Enter with `spec-kitty agent action implement WP02 --agent <name>`.

## Objective

Fix the shim generation path so Gemini and Qwen produce valid TOML files (`.toml` extension, `description`/`prompt` flat schema) with `{{args}}` as the argument placeholder. There are **two generation paths** that both need fixing: `src/specify_cli/shims/generator.py` (used by project-local `generate_all_shims()`) and `src/specify_cli/runtime/agent_commands.py` (used by global agent command installation). All other agent formats must remain byte-for-byte identical.

**Fixes**: Issue #673  
**Requirements**: FR-005, FR-006, FR-007, FR-008, NFR-001–004

## Context

**What config.py already knows**: `AGENT_COMMAND_CONFIG` in `src/specify_cli/core/config.py` is the authoritative format registry:
```python
"gemini": {"dir": ".gemini/commands", "ext": "toml", "arg_format": "{{args}}"},
"qwen":   {"dir": ".qwen/commands",   "ext": "toml", "arg_format": "{{args}}"},
```
Both Gemini and Qwen use `.toml` extension and `{{args}}`. The generator is not reading this config — it always produces Markdown.

**TOML schema (from regression baselines)**: The actual Gemini/Qwen format is a flat TOML file:
```toml
description = "Create a mission specification"

prompt = """
<!-- spec-kitty-command-version: X.Y.Z -->
...command body...
"""
```
Not `[[commands]]` array-of-tables. The baselines at `tests/specify_cli/regression/_twelve_agent_baseline/gemini/specify.toml` and `qwen/specify.toml` are the source of truth for the expected schema.

**Two generation paths**:
1. `generator.py` → `generate_all_shims()` — project-local, used by `spec-kitty upgrade`
2. `agent_commands.py` → `_sync_agent_commands()` at line 173 — global install, used by `spec-kitty agent config add`

Both paths call `generate_shim_content()` which always returns Markdown. Both must be fixed. The cleanest approach: add `generate_shim_content_for_agent()` in `generator.py` that reads `AGENT_COMMAND_CONFIG` to dispatch, then update both callers.

---

## Subtask T006 — Add `generate_shim_content_toml()` with correct flat schema

**File**: `src/specify_cli/shims/generator.py`

The TOML schema matches the regression baselines: flat `description` key + `prompt` multiline string.

Add immediately after `generate_shim_content()`:

```python
def generate_shim_content_toml(
    command: str, agent_name: str, arg_placeholder: str
) -> str:
    """Return a TOML shim for agents that require TOML format (Gemini, Qwen).

    Uses the flat ``description``/``prompt`` schema that matches the
    regression baselines in ``tests/specify_cli/regression/_twelve_agent_baseline/``.

    Args:
        command:         Skill verb, e.g. ``"implement"``.
        agent_name:      Agent key, e.g. ``"gemini"``.
        arg_placeholder: Runtime placeholder, e.g. ``"{{args}}"``.
    """
    version = _get_cli_version()
    cli_call = _canonical_command(command, agent_name, arg_placeholder)
    description = SHIM_DESCRIPTIONS.get(command, f"spec-kitty {command}")
    body = (
        f"<!-- spec-kitty-command-version: {version} -->\n"
        "Run this exact command and treat its output as authoritative.\n"
        "Do not rediscover context from branches, files, prompt contents, or separate charter loads.\n"
        "When mission selection is required, pass --mission <handle> (mission_id, mid8, or mission_slug).\n"
        "\n"
        f"`{cli_call}`\n"
    )
    # TOML multiline strings use triple-quote; escape any triple-quote in body (unlikely but safe)
    body_escaped = body.replace('"""', '""\\"')
    return (
        f'description = "{description}"\n'
        "\n"
        f'prompt = """\n{body_escaped}"""\n'
    )
```

**Validation**:
- [ ] `generate_shim_content_toml("specify", "gemini", "{{args}}")` output matches the structure of `tests/specify_cli/regression/_twelve_agent_baseline/gemini/specify.toml`
- [ ] `tomllib.loads(output)` parses without error
- [ ] Output does not contain `---` (no YAML frontmatter)
- [ ] Output contains `{{args}}` in the prompt body

---

## Subtask T007 — Add `generate_shim_content_for_agent()` routing function

**File**: `src/specify_cli/shims/generator.py`

This routing function reads `AGENT_COMMAND_CONFIG` to decide format and placeholder, replacing the duplicate logic in both callers.

```python
def generate_shim_content_for_agent(command: str, agent_key: str) -> str:
    """Return shim content for *command* targeting *agent_key*, using the format
    and argument placeholder defined in ``AGENT_COMMAND_CONFIG``.

    Dispatches to :func:`generate_shim_content` (Markdown) or
    :func:`generate_shim_content_toml` (TOML) based on the configured extension.
    Falls back to Markdown / ``$ARGUMENTS`` for unknown agents.

    Args:
        command:   Skill verb, e.g. ``"implement"``.
        agent_key: Agent key, e.g. ``"gemini"``.
    """
    from specify_cli.core.config import AGENT_COMMAND_CONFIG

    config = AGENT_COMMAND_CONFIG.get(agent_key, {})
    arg_placeholder: str = config.get("arg_format", _DEFAULT_ARG_PLACEHOLDER)
    ext: str = config.get("ext", "md")

    if ext == "toml":
        return generate_shim_content_toml(command, agent_key, arg_placeholder)
    return generate_shim_content(command, agent_key, arg_placeholder)
```

**Validation**:
- [ ] `generate_shim_content_for_agent("specify", "gemini")` returns TOML content
- [ ] `generate_shim_content_for_agent("specify", "qwen")` returns TOML content
- [ ] `generate_shim_content_for_agent("specify", "claude")` returns Markdown with `$ARGUMENTS`
- [ ] `generate_shim_content_for_agent("specify", "unknown_agent")` returns Markdown with `$ARGUMENTS`

---

## Subtask T008 — Update `generate_all_shims()` to use the routing function

**File**: `src/specify_cli/shims/generator.py`

1. Inside `generate_all_shims()`, replace the content generation and filename logic:
   ```python
   # Old:
   filename = f"spec-kitty.{skill}.md"
   content = generate_shim_content(skill, agent_key, arg_placeholder)
   ```
   With:
   ```python
   from specify_cli.core.config import AGENT_COMMAND_CONFIG as _ACC
   _ext = _ACC.get(agent_key, {}).get("ext", "md")
   filename = f"spec-kitty.{skill}.{_ext}" if _ext else f"spec-kitty.{skill}"
   content = generate_shim_content_for_agent(skill, agent_key)
   ```
   (The `arg_placeholder` variable computed earlier in the loop is superseded by `generate_shim_content_for_agent` which reads it from config internally. Remove the now-unused `arg_placeholder` lookup if it is only used by the old content call.)

2. Do not change any other part of `generate_all_shims()`.

**Validation**:
- [ ] Gemini agent produces `.toml` files under `.gemini/commands/`
- [ ] Qwen agent produces `.toml` files under `.qwen/commands/`
- [ ] Claude agent produces `.md` files under `.claude/commands/` (unchanged)

---

## Subtask T009 — Update `_sync_agent_commands()` in `agent_commands.py`

**File**: `src/specify_cli/runtime/agent_commands.py`

At line 173, replace:
```python
content = generate_shim_content(command, agent_key, arg_placeholder)
```
With:
```python
content = generate_shim_content_for_agent(command, agent_key)
```

Also update the import at line 120–124 to include `generate_shim_content_for_agent`:
```python
from specify_cli.shims.generator import (
    AGENT_ARG_PLACEHOLDERS,
    _DEFAULT_ARG_PLACEHOLDER,
    generate_shim_content,          # keep for any other callers in this file
    generate_shim_content_for_agent, # new routing function
)
```

`_compute_output_filename()` already reads from `AGENT_COMMAND_CONFIG` to produce the correct extension — no change needed there.

**Validation**:
- [ ] After the change, `_sync_agent_commands("gemini", ...)` writes `.toml` files with the flat `description`/`prompt` schema
- [ ] `_sync_agent_commands("claude", ...)` still writes `.md` files (no regression)

---

## Subtask T010 — Regression tests: Gemini output matches baselines

**File**: `tests/specify_cli/shims/test_generator.py` (create if absent)

```python
import tomllib

def test_gemini_shim_content_is_valid_toml():
    """generate_shim_content_for_agent produces parseable TOML for gemini."""
    content = generate_shim_content_for_agent("specify", "gemini")
    parsed = tomllib.loads(content)
    assert "description" in parsed
    assert "prompt" in parsed
    assert "{{args}}" in parsed["prompt"]
    assert "$ARGUMENTS" not in parsed["prompt"]

def test_gemini_shim_matches_baseline_schema():
    """Gemini shim uses flat description/prompt schema, not [[commands]]."""
    content = generate_shim_content_for_agent("specify", "gemini")
    assert "description = " in content
    assert 'prompt = """' in content
    assert "[[commands]]" not in content

def test_generate_all_shims_gemini_writes_toml(tmp_path, monkeypatch):
    """generate_all_shims writes .toml for gemini, no .md."""
    # configure project with gemini
    # run generate_all_shims
    gemini_dir = tmp_path / ".gemini" / "commands"
    assert list(gemini_dir.glob("spec-kitty.*.toml")), "expected .toml files"
    assert not list(gemini_dir.glob("spec-kitty.*.md")), "unexpected .md files"

def test_gemini_uses_mustache_placeholder():
    content = generate_shim_content_for_agent("implement", "gemini")
    assert "{{args}}" in content
    assert "$ARGUMENTS" not in content
```

**Validation**:
- [ ] All four tests pass
- [ ] `tomllib.loads()` asserts valid TOML

---

## Subtask T011 — Regression tests: Qwen output

```python
def test_qwen_shim_content_is_valid_toml():
    content = generate_shim_content_for_agent("specify", "qwen")
    parsed = tomllib.loads(content)
    assert "description" in parsed
    assert "{{args}}" in parsed["prompt"]

def test_qwen_shim_uses_toml_extension_in_generate_all_shims(tmp_path):
    """generate_all_shims writes .toml for qwen."""
    # configure project with qwen, run generate_all_shims
    qwen_dir = tmp_path / ".qwen" / "commands"
    assert list(qwen_dir.glob("spec-kitty.*.toml"))
    assert not list(qwen_dir.glob("spec-kitty.*.md"))
```

---

## Subtask T012 — Regression tests: Claude/Codex unchanged

```python
def test_claude_shim_unchanged():
    """Claude still gets Markdown with $ARGUMENTS."""
    content = generate_shim_content_for_agent("implement", "claude")
    assert content.startswith("---\n")   # YAML frontmatter
    assert "$ARGUMENTS" in content
    assert "{{args}}" not in content

def test_codex_shim_unchanged():
    content = generate_shim_content_for_agent("implement", "codex")
    assert "$PROMPT" in content

def test_regression_baselines_match_generated_output():
    """Generated output for gemini/specify matches the checked-in baseline."""
    import pathlib
    baseline_path = (
        pathlib.Path(__file__).parents[2]
        / "regression/_twelve_agent_baseline/gemini/specify.toml"
    )
    if not baseline_path.exists():
        pytest.skip("baseline file not present")
    generated = generate_shim_content_for_agent("specify", "gemini")
    # Allow version string to differ; compare structure
    baseline = tomllib.loads(baseline_path.read_text())
    parsed = tomllib.loads(generated)
    assert set(parsed.keys()) == set(baseline.keys()), "TOML key set mismatch"
```

---

## Definition of Done

- [ ] `generate_shim_content_toml()` produces flat `description`/`prompt` TOML matching the regression baselines
- [ ] `generate_shim_content_for_agent()` routing function dispatches correctly for all agents
- [ ] `generate_all_shims()` updated to use routing function and correct extension from `AGENT_COMMAND_CONFIG`
- [ ] `agent_commands.py` updated to call `generate_shim_content_for_agent()` instead of `generate_shim_content()` directly
- [ ] `tests/specify_cli/shims/test_generator.py` exists with ≥10 tests
- [ ] `tomllib.loads()` asserts on all generated Gemini/Qwen TOML content
- [ ] Baseline comparison test passes (or skips gracefully if baseline absent)
- [ ] `mypy --strict src/specify_cli/shims/generator.py src/specify_cli/runtime/agent_commands.py` exits 0
- [ ] FR-005, FR-006, FR-007, FR-008 satisfied (verify spec scenarios S-03, S-04)

## Risks

- **Schema drift**: The `description`/`prompt` schema is inferred from the regression baselines. If the baselines are stale, update them alongside the generator. The baseline-comparison test will catch schema mismatches.
- **`generate_shim_content` callers outside this WP**: Search the codebase for other calls to `generate_shim_content()` before closing this WP. Any caller not updated to `generate_shim_content_for_agent()` will still produce Markdown for TOML agents.
- **Existing .md files in .gemini/commands/**: Old files from before this fix are not automatically cleaned up. Operators must manually delete stale `.md` shims or run `spec-kitty upgrade` which will overwrite via migrations.

## Reviewer Guidance

1. Confirm both generation paths (`generate_all_shims()` and `_sync_agent_commands()`) now produce `.toml` for Gemini and Qwen.
2. Verify `tomllib.loads()` succeeds on every generated Gemini/Qwen shim.
3. Confirm the TOML schema matches `tests/specify_cli/regression/_twelve_agent_baseline/gemini/specify.toml` structure.
4. Confirm Claude/Codex outputs are byte-for-byte identical to pre-fix output.

## Activity Log

- 2026-04-21T09:24:56Z – claude:sonnet:implementer:implementer – shell_pid=64353 – Assigned agent via action command
- 2026-04-21T09:29:32Z – claude:sonnet:implementer:implementer – shell_pid=64353 – Ready for review: TOML shim generation for Gemini/Qwen, routing function, both generation paths fixed, 32 new tests + 66 total passing, 185 regression tests passing
- 2026-04-21T09:29:58Z – claude:sonnet:reviewer:reviewer – shell_pid=70133 – Started review via action command
