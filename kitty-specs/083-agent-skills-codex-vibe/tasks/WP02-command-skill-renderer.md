---
work_package_id: WP02
title: Command-Skill Renderer
dependencies: []
base_branch: main
base_commit: 05e6c3ed6d49dda2dc83fa525d8958632daa2c09
created_at: '2026-04-14T09:48:57.342632+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
lane: "doing"
shell_pid: "3994"
history:
- at: '2026-04-14T00:00:00+00:00'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/skills/command_renderer.py
branch_strategy: lane-worktree
execution_mode: code_change
merge_target_branch: main
owned_files:
- src/specify_cli/skills/command_renderer.py
- src/specify_cli/skills/_user_input_block.py
- tests/specify_cli/skills/test_command_renderer.py
- tests/specify_cli/skills/__snapshots__/**
planning_base_branch: main
requirement_refs:
- FR-004
- FR-005
- NFR-004
---

# WP02 — Command-Skill Renderer

## Objective

Deliver the pure renderer that turns a `command-templates/<command>.md` source file into a `RenderedSkill` (frontmatter + body) for Codex and Vibe. The renderer must (a) rewrite the `## User Input` block so the skill body no longer depends on literal `$ARGUMENTS` pre-substitution, (b) guard against stray `$ARGUMENTS` tokens elsewhere, and (c) be deterministic to the byte so snapshot tests are trustworthy.

This WP stands alone — no dependency on WP01 (manifest) or WP03 (installer). It can start in parallel with WP01.

## Context

`kitty-specs/083-agent-skills-codex-vibe/research.md` establishes that Codex's Agent Skills do not perform `$ARGUMENTS` substitution and Vibe's substitution semantics are undocumented by Mistral. The renderer's job is to make the skill body work correctly **without** relying on literal substitution, while preserving the full workflow logic for every canonical command.

The contract for this module is frozen at `kitty-specs/083-agent-skills-codex-vibe/contracts/skill-renderer.contract.md`. Read it before starting.

Canonical commands (16 total, in `src/specify_cli/missions/software-dev/command-templates/` and equivalents under other mission directories):
`specify`, `plan`, `tasks`, `tasks-outline`, `tasks-packages`, `tasks-finalize`, `implement`, `review`, `accept`, `merge`, `analyze`, `research`, `checklist`, `status`, `dashboard`, `charter`.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per lane from `lanes.json` after `finalize-tasks`. Likely lane B given this parallels WP01.

## Implementation

### Subtask T006 — Create `command_renderer.py` with `RenderedSkill` and `SkillRenderError`

Create `src/specify_cli/skills/command_renderer.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Any

SUPPORTED_AGENTS = ("codex", "vibe")

@dataclass(frozen=True)
class RenderedSkill:
    name: str                          # "spec-kitty.<command>"
    frontmatter: dict[str, Any]        # sorted keys
    body: str                          # markdown body; no $ARGUMENTS
    source_template: Path              # absolute path to the source
    source_hash: str                   # SHA-256 of source bytes at render time
    agent_key: Literal["codex", "vibe"]
    spec_kitty_version: str

    def to_skill_md(self) -> str:
        """Serialize to the on-disk SKILL.md bytes (frontmatter + body)."""

class SkillRenderError(Exception):
    def __init__(self, code: str, **context):
        self.code = code
        self.context = context
        super().__init__(f"{code}: {context}")
```

Error codes to support: `template_not_found`, `user_input_block_missing`, `stray_arguments_token`, `unsupported_agent`.

`to_skill_md()` must emit frontmatter in a stable order: `name`, `description`, `user-invocable`. Use a tiny hand-rolled YAML emitter or a deterministic subset of `ruamel.yaml` (confirm no incidental quoting differences between runs). Validate with a snapshot test.

### Subtask T007 — Implement `## User Input` block identifier

Keep this in a sibling module `src/specify_cli/skills/_user_input_block.py` so the core renderer stays narrow.

`identify(body: str) -> tuple[int, int] | None` returns the `(start_byte, end_byte)` span of the User-Input block, or `None` if absent.

A "block" starts at a line matching the regex `^##\s+User Input\s*$` and continues through (exclusive) the next heading at the same or shallower level (`^#{1,2}\s`). The newline before the next heading is included in the span so the replacement leaves tidy spacing.

Regex to match the start heading: `re.compile(r"^## +User Input\s*$", re.MULTILINE)`.
Regex to match the terminating heading: `re.compile(r"^#{1,2} +\S", re.MULTILINE)`.

Tests (belong in T011 but write them alongside the function):
- A template with one User-Input block returns a correct span.
- A template with no User-Input block returns `None`.
- A template that uses `## User Input` inside a code fence is correctly ignored (add defensive handling: strip fenced blocks before scanning, OR use a stricter regex that checks column position). Decide based on whether any canonical template has that edge case today (`grep -n '^## User Input' src/specify_cli/missions/*/command-templates/*.md` — if all hits are real headings, simpler regex suffices).

### Subtask T008 — Implement User-Input block rewrite

Create a constant in `_user_input_block.py`:

```python
REPLACEMENT_BLOCK = (
    "## User Input\n\n"
    "The content of the user's message that invoked this skill "
    "(everything after the skill invocation token, e.g. after "
    "`/spec-kitty.<command>` or `$spec-kitty.<command>`) is the User Input "
    "referenced elsewhere in these instructions.\n\n"
    "You **MUST** consider this user input before proceeding (if not empty).\n"
)
```

The exact string is load-bearing — it is the semantic bridge between the command surface and the skill runtime. Lock it with a snapshot test (T011). If it must change, that is a deliberate version bump, not a drift.

`rewrite(body: str) -> str` identifies the block span and replaces it with `REPLACEMENT_BLOCK`. If no block is found, raise `SkillRenderError("user_input_block_missing")`.

### Subtask T009 — Implement `$ARGUMENTS` stray-token guard

After the rewrite, scan the body for the literal substring `$ARGUMENTS`. Any occurrence raises `SkillRenderError("stray_arguments_token", path=<template_path>, line=<1-indexed>, excerpt=<full line>)`.

Current templates have `$ARGUMENTS` references *outside* the User-Input block in some commands (e.g. `specify.md:268`, `checklist.md:42,71`, `analyze.md:184`, `tasks.md:245`, `tasks-outline.md:206`, `tasks-packages.md:191`). These are incompatible with skills-layer rendering. Two options:

- **Option A (recommended)**: open each offending template and rewrite those references to describe behavior in words (e.g., replace `"do not rely on raw $ARGUMENTS"` with `"do not rely on the raw invocation text"`). This is an additive edit that also helps the command-file pipeline (the wording is clearer for all agents). If taken, note that these template edits are shared with the non-migrated agents' pipeline — because they do not remove the User-Input substitution, the command-file output for the twelve non-migrated agents may change. Coordinate with WP07's baseline snapshot: **capture the WP07 baseline AFTER these edits land**, not before.
- **Option B**: emit only the subset of commands that pass the guard; skip the rest with a warning. Not recommended — it ships partial Vibe/Codex support.

Prefer Option A. Document the rewrites in the WP02 PR description so reviewers can see the before/after.

### Subtask T010 — Implement frontmatter builder [P]

`_build_frontmatter(template_body: str, name: str, agent_key: str) -> dict`:

- `name`: `"spec-kitty.<command>"` (derived from the template filename, dropped extension).
- `description`: first sentence of the `## Purpose` section (if present) or the first non-heading paragraph of the template, trimmed to ≤140 characters. If neither is present, fallback to `f"Spec Kitty {command} workflow"`.
- `user-invocable`: `True` for both Codex and Vibe.
- `allowed-tools` and `license` and `compatibility` are intentionally omitted (not emitted at all when null).

Return a plain `dict` with keys in insertion order: `name`, `description`, `user-invocable`.

### Subtask T011 — Snapshot tests

Create `tests/specify_cli/skills/test_command_renderer.py` and a sibling `__snapshots__/` directory.

Tests:

- **All 16 × 2 render determinism**: for every canonical command template and for `agent_key in ("codex", "vibe")`, render twice and assert byte-identical `RenderedSkill.to_skill_md()` output. Persist the expected output once per (command, agent) combination as a snapshot file `__snapshots__/<agent>/<command>.SKILL.md`; assert the render matches the snapshot.
- **User-Input block absent**: craft a minimal template with no `## User Input` heading, assert `SkillRenderError("user_input_block_missing")`.
- **Stray `$ARGUMENTS`**: craft a template with `$ARGUMENTS` in a section other than User Input, assert `SkillRenderError("stray_arguments_token", line=...)`.
- **Unsupported agent**: call with `agent_key="claude"`, assert `SkillRenderError("unsupported_agent")`.
- **Frontmatter stability**: assert the serialized frontmatter emits keys in the expected order (`name`, `description`, `user-invocable`) across Python versions.
- **Description fallback**: craft a template without `## Purpose`, assert the description falls back to the first paragraph or the canonical fallback string.

Snapshot update workflow: document in the test file's module docstring how to regenerate snapshots (e.g., `PYTEST_UPDATE_SNAPSHOTS=1 pytest ...`). Implement the update logic with a simple env-var check.

## Definition of Done

- [ ] `src/specify_cli/skills/command_renderer.py` and `src/specify_cli/skills/_user_input_block.py` exist.
- [ ] `pytest tests/specify_cli/skills/test_command_renderer.py` passes.
- [ ] Snapshot files for all 16 × 2 combinations are committed under `tests/specify_cli/skills/__snapshots__/`.
- [ ] `ruff check src/specify_cli/skills/` passes.
- [ ] Stray `$ARGUMENTS` tokens in the 16 canonical templates have been removed (Option A) or an explicit decision to use Option B is captured in the PR description.
- [ ] Module docstring in `command_renderer.py` lists the three invariants (deterministic, no-stray-`$ARGUMENTS`, single-body-for-both-agents).
- [ ] No changes to files outside `owned_files`.

## Risks

- **Template rewrites affect the non-migrated agent snapshot (WP07).** If Option A is taken, coordinate so WP07 captures its baseline after these edits. Otherwise WP07 will produce a non-zero diff and block the release.
- **Description heuristics.** The `## Purpose` section does not exist in every template. The fallback logic must be unambiguous and deterministic — no randomness, no dependence on file modification time.
- **YAML emission.** Hand-rolled YAML is fine for this narrow schema but must not double-quote strings with colons or hashes. Add a test that uses a description containing a colon and asserts round-trip.

## Reviewer Guidance

- Re-read the `REPLACEMENT_BLOCK` string out loud and confirm it unambiguously tells the model what to do. This string is the semantic bridge; a weak wording here becomes a subtle regression.
- Check `_build_frontmatter` does not leak user-facing test-only fields. Production frontmatter is exactly `name`, `description`, `user-invocable` — nothing more.
- Confirm the stray-`$ARGUMENTS` guard uses a substring check, not a whole-word regex, so variants like `$ARGUMENTS.strip()` are also caught.

## Command to run implementation

```bash
spec-kitty agent action implement WP02 --agent <name>
```
