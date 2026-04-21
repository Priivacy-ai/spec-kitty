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
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
history:
- 2026-04-21T08:41:50Z – planned – stabilization WP02
authoritative_surface: src/specify_cli/shims/
execution_mode: code_change
mission_id: 01KPQJAN4P2V4MTHRFGS7VW17M
mission_slug: stabilization-release-core-bug-fixes-01KPQJAN
owned_files:
- src/specify_cli/shims/generator.py
- tests/specify_cli/shims/
tags: []
---

# WP02 — Gemini/Qwen Shim Generation Fix

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Dependency**: WP01 must be approved before this WP is claimed.
- **Workspace**: Enter with `spec-kitty agent action implement WP02 --agent <name>`.

## Objective

Fix `src/specify_cli/shims/generator.py` so that Gemini-targeted shim files are written as valid TOML (`.toml` extension, `[[commands]]` schema) and both Gemini and Qwen use `{{args}}` as the argument placeholder instead of `$ARGUMENTS`. All other agent formats must remain byte-for-byte identical to pre-fix output.

**Fixes**: Issue #673  
**Requirements**: FR-005, FR-006, FR-007, FR-008, NFR-001–004

## Context

The shim generator currently has:
- `AGENT_ARG_PLACEHOLDERS` maps only `claude → $ARGUMENTS` and `codex → $PROMPT`; all others fall through to `_DEFAULT_ARG_PLACEHOLDER = "$ARGUMENTS"`
- `generate_shim_content()` always returns Markdown with YAML frontmatter — there is no per-agent format dispatch
- `generate_all_shims()` always writes `spec-kitty.{skill}.md` with hardcoded `.md` extension

Gemini CLI reads commands from `.gemini/commands/*.toml` files using a `[[commands]]` TOML array-of-tables structure with a `{{args}}` placeholder. Qwen Code reads `.qwen/commands/*.md` with `{{args}}` (same Markdown format as Claude, different placeholder).

The fix adds per-agent format dispatch without disturbing the existing Markdown path used by Claude, Codex, GitHub Copilot, and all other agents.

---

## Subtask T006 — Add Gemini + Qwen to `AGENT_ARG_PLACEHOLDERS`

**File**: `src/specify_cli/shims/generator.py`

**Steps**:

1. Locate `AGENT_ARG_PLACEHOLDERS` (around line 54):
   ```python
   AGENT_ARG_PLACEHOLDERS: dict[str, str] = {
       "claude": "$ARGUMENTS",
       "codex": "$PROMPT",
   }
   ```

2. Add the two new entries:
   ```python
   AGENT_ARG_PLACEHOLDERS: dict[str, str] = {
       "claude": "$ARGUMENTS",
       "codex": "$PROMPT",
       "gemini": "{{args}}",
       "qwen": "{{args}}",
   }
   ```

3. The `_DEFAULT_ARG_PLACEHOLDER` fallback stays as `"$ARGUMENTS"` — agents not in the dict continue to use it.

**Validation**:
- [ ] `_get_arg_placeholder("gemini")` returns `"{{args}}"`
- [ ] `_get_arg_placeholder("qwen")` returns `"{{args}}"`
- [ ] `_get_arg_placeholder("claude")` still returns `"$ARGUMENTS"`
- [ ] `_get_arg_placeholder("copilot")` still returns `"$ARGUMENTS"` (falls through to default)

---

## Subtask T007 — Add `AGENT_SHIM_FORMATS` dispatch dict

**File**: `src/specify_cli/shims/generator.py`

**Steps**:

1. Add a new module-level constant after `AGENT_ARG_PLACEHOLDERS`:
   ```python
   # Agents that require a non-Markdown shim format.
   # Key: agent key (matches AGENT_DIR_TO_KEY values)
   # Value: format identifier ("toml" | "md")
   # Agents not listed default to "md".
   AGENT_SHIM_FORMATS: dict[str, str] = {
       "gemini": "toml",
   }
   ```

2. Add a helper to retrieve the format for an agent key:
   ```python
   def _get_shim_format(agent_key: str) -> str:
       """Return the shim format for *agent_key* ('md' or 'toml')."""
       return AGENT_SHIM_FORMATS.get(agent_key, "md")
   ```

**Validation**:
- [ ] `_get_shim_format("gemini")` returns `"toml"`
- [ ] `_get_shim_format("claude")` returns `"md"`
- [ ] `_get_shim_format("qwen")` returns `"md"` (Qwen uses Markdown, only placeholder differs)

---

## Subtask T008 — Implement `generate_shim_content_toml()`

**File**: `src/specify_cli/shims/generator.py`

**Steps**:

Add the following function immediately after `generate_shim_content()`:

```python
def generate_shim_content_toml(
    command: str, agent_name: str, arg_placeholder: str
) -> str:
    """Return a TOML command file for agents that require TOML format (e.g. Gemini).

    Gemini CLI reads ``.gemini/commands/*.toml`` files. The schema is a
    ``[[commands]]`` array of tables with ``name``, ``description``, and
    ``command`` keys.  The ``command`` value calls the canonical spec-kitty CLI
    directly, using *arg_placeholder* for the user-provided argument string.

    Args:
        command:         Skill verb, e.g. ``"implement"``.
        agent_name:      Agent key, e.g. ``"gemini"``.
        arg_placeholder: Runtime variable name, e.g. ``"{{args}}"``.

    Returns:
        A multi-line TOML string ready to write as a ``.toml`` file.
    """
    cli_call = _canonical_command(command, agent_name, arg_placeholder)
    description = SHIM_DESCRIPTIONS.get(command, f"spec-kitty {command}")
    return (
        "[[commands]]\n"
        f'name = "spec-kitty.{command}"\n'
        f'description = "{description}"\n'
        f'command = "{cli_call}"\n'
    )
```

**Validation**:
- [ ] `generate_shim_content_toml("implement", "gemini", "{{args}}")` starts with `[[commands]]`
- [ ] Output contains `command = "spec-kitty agent action implement {{args}} --agent gemini"`
- [ ] Output does not contain `---` (no YAML frontmatter)
- [ ] `tomllib.loads(output)` (Python 3.11+ stdlib) parses without error — add this assertion to tests

---

## Subtask T009 — Update `generate_all_shims()` for per-agent dispatch

**File**: `src/specify_cli/shims/generator.py`

**Steps**:

1. Inside the `for agent_root, command_subdir in agent_dirs:` loop, after resolving `arg_placeholder`, add format detection:
   ```python
   shim_format = _get_shim_format(agent_key)
   ```

2. Inside the `for skill in cli_skills:` loop, replace the current fixed-path write block:
   ```python
   # Old (fixed .md always):
   filename = f"spec-kitty.{skill}.md"
   content = generate_shim_content(skill, agent_key, arg_placeholder)
   out_path = target_dir / filename
   out_path.write_text(content, encoding="utf-8")
   written.append(out_path)
   ```
   With format-dispatching logic:
   ```python
   if shim_format == "toml":
       filename = f"spec-kitty.{skill}.toml"
       content = generate_shim_content_toml(skill, agent_key, arg_placeholder)
   else:
       filename = f"spec-kitty.{skill}.md"
       content = generate_shim_content(skill, agent_key, arg_placeholder)
   out_path = target_dir / filename
   out_path.write_text(content, encoding="utf-8")
   written.append(out_path)
   ```

3. Do not change any other part of `generate_all_shims()`.

**Validation**:
- [ ] Running `generate_all_shims(repo_root)` for a project with Gemini configured produces `.toml` files under `.gemini/commands/`
- [ ] No `.md` files are produced under `.gemini/commands/`
- [ ] Running the same for a project with Claude configured produces `.md` files under `.claude/commands/` (unchanged)

---

## Subtask T010 — Regression tests: Gemini output

**File**: `tests/specify_cli/shims/test_generator.py` (create directory and file if absent)

**Tests to write**:

```python
import tomllib  # Python 3.11+ stdlib

def test_gemini_shim_uses_toml_extension(tmp_path):
    """generate_all_shims writes .toml files for gemini agent."""
    # Setup: project with gemini configured
    # Run: generate_all_shims(tmp_path)
    gemini_dir = tmp_path / ".gemini" / "commands"
    shim_files = list(gemini_dir.glob("spec-kitty.*.toml"))
    assert len(shim_files) > 0, "No .toml files written for gemini"
    # No .md files should exist for gemini
    md_files = list(gemini_dir.glob("spec-kitty.*.md"))
    assert len(md_files) == 0, f"Unexpected .md files for gemini: {md_files}"

def test_gemini_shim_content_is_valid_toml(tmp_path):
    """Gemini shim content parses as valid TOML."""
    content = generate_shim_content_toml("implement", "gemini", "{{args}}")
    parsed = tomllib.loads(content)
    assert "commands" in parsed
    cmd = parsed["commands"][0]
    assert cmd["name"] == "spec-kitty.implement"
    assert "{{args}}" in cmd["command"]
    assert "--agent gemini" in cmd["command"]

def test_gemini_shim_uses_mustache_placeholder(tmp_path):
    """Gemini shim uses {{args}}, not $ARGUMENTS."""
    content = generate_shim_content_toml("implement", "gemini", "{{args}}")
    assert "{{args}}" in content
    assert "$ARGUMENTS" not in content

def test_gemini_shim_has_correct_structure():
    """Gemini shim starts with [[commands]] array-of-tables."""
    content = generate_shim_content_toml("status", "gemini", "{{args}}")
    assert content.startswith("[[commands]]")
    assert "---" not in content  # no YAML frontmatter
```

**Validation**:
- [ ] All four tests pass
- [ ] `tomllib.loads()` assertion ensures the TOML is actually parseable

---

## Subtask T011 — Regression tests: Qwen output

**File**: `tests/specify_cli/shims/test_generator.py`

**Tests to write**:

```python
def test_qwen_shim_uses_md_extension(tmp_path):
    """generate_all_shims writes .md files for qwen (Markdown format)."""
    # Setup project with qwen configured
    qwen_dir = tmp_path / ".qwen" / "commands"
    shim_files = list(qwen_dir.glob("spec-kitty.*.md"))
    assert len(shim_files) > 0

def test_qwen_shim_uses_mustache_placeholder(tmp_path):
    """Qwen shim uses {{args}}, not $ARGUMENTS."""
    content = generate_shim_content("implement", "qwen", "{{args}}")
    assert "{{args}}" in content
    assert "$ARGUMENTS" not in content

def test_qwen_placeholder_lookup():
    """_get_arg_placeholder returns {{args}} for qwen."""
    assert _get_arg_placeholder("qwen") == "{{args}}"
```

**Validation**:
- [ ] Tests pass
- [ ] `_get_arg_placeholder` is importable from `specify_cli.shims.generator`

---

## Subtask T012 — Regression tests: Claude/Codex unchanged

**File**: `tests/specify_cli/shims/test_generator.py`

**Tests to write**:

```python
def test_claude_shim_unchanged_format(tmp_path):
    """Claude shim uses .md extension and $ARGUMENTS placeholder."""
    content = generate_shim_content("implement", "claude", "$ARGUMENTS")
    assert content.startswith("---\n")  # YAML frontmatter
    assert "$ARGUMENTS" in content
    assert "{{args}}" not in content

def test_codex_shim_unchanged_format(tmp_path):
    """Codex shim uses .md extension and $PROMPT placeholder."""
    content = generate_shim_content("implement", "codex", "$PROMPT")
    assert "$PROMPT" in content

def test_non_gemini_agents_get_md_extension(tmp_path):
    """All non-Gemini agents write .md files."""
    for agent_key in ("claude", "copilot", "qwen", "opencode", "cursor"):
        assert _get_shim_format(agent_key) == "md", (
            f"Expected 'md' format for {agent_key}, got {_get_shim_format(agent_key)}"
        )
```

**Validation**:
- [ ] Tests pass confirming no regression in other agent output
- [ ] Run full suite: `pytest -q tests/specify_cli/shims/`

---

## Definition of Done

- [ ] `AGENT_ARG_PLACEHOLDERS` has `gemini` and `qwen` entries with `{{args}}`
- [ ] `AGENT_SHIM_FORMATS` dict exists with `gemini → toml`
- [ ] `generate_shim_content_toml()` produces valid, parseable TOML
- [ ] `generate_all_shims()` dispatches on format and uses `.toml` extension for Gemini
- [ ] `tests/specify_cli/shims/test_generator.py` exists with ≥10 tests covering all three scenarios
- [ ] All new tests pass
- [ ] `mypy --strict src/specify_cli/shims/generator.py` exits 0
- [ ] FR-005, FR-006, FR-007, FR-008 satisfied (verify spec scenarios S-03, S-04)

## Risks

- **Qwen format assumption**: research.md documents Qwen as Markdown + `{{args}}`. If Qwen uses a different format, update `AGENT_SHIM_FORMATS` and add a `generate_shim_content_qwen()` if needed. Update the research note.
- **TOML TOML schema drift**: The Gemini `[[commands]]` schema may evolve. The current implementation targets the schema documented in research.md. If the schema differs, update `generate_shim_content_toml()` and the test assertions together.
- **Existing .md files in .gemini/commands/**: Old files from before this fix are not automatically cleaned up. Operators must manually delete `.md` shims in `.gemini/commands/` after upgrading. Do not add auto-cleanup in this WP — that is out of scope.

## Reviewer Guidance

1. Confirm `generate_all_shims()` for a Gemini-configured project writes only `.toml`, not `.md`.
2. Confirm `tomllib.loads()` succeeds on every Gemini shim produced by the new generator.
3. Confirm Claude and Codex shim outputs are identical to pre-WP02 output (diff against a snapshot if one is available in the test suite).
4. Check that `_get_shim_format` and `_get_arg_placeholder` are unit-tested independently.
