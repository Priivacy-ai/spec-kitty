---
work_package_id: WP02
title: Codex Native Profile Renderer
dependencies:
- WP01
requirement_refs:
- FR-011
- FR-016
tracker_refs: []
planning_base_branch: feat/agent-profile-projection-plugin-production
merge_target_branch: feat/agent-profile-projection-plugin-production
branch_strategy: Planning artifacts for this mission were generated on feat/agent-profile-projection-plugin-production. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-profile-projection-plugin-production unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: claude
history:
- at: '2026-06-14T00:00:00Z'
  event: created
  actor: claude
agent_profile: engineer
authoritative_surface: src/specify_cli/tool_surface/profiles/
create_intent:
- src/specify_cli/tool_surface/profiles/codex_renderer.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/profiles/codex_renderer.py
- src/specify_cli/tool_surface/profiles/renderers.py
- pyproject.toml
role: Senior Python Engineer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading any other section of this prompt, load your agent profile:

```
/ad-hoc-profile-load engineer
```

---

## Objective

Implement `CodexProfileRenderer` that projects Spec Kitty agent profiles to `.codex/agents/<profile_id>.toml` files in valid TOML format. Register it alongside `ClaudeCodeProfileRenderer` and `CopilotProfileRenderer`. After this WP, `doctor tool-surfaces --kind agent_profile` must no longer report Codex as `research_gap`.

---

## Context

`src/specify_cli/tool_surface/profiles/renderers.py` currently contains:
- `ClaudeCodeProfileRenderer` (format_key: `"claude-agent"`, output: `.claude/agents/<id>.md`)
- `CopilotProfileRenderer` (format_key: `"copilot-agent"`, output: `.github/agents/<id>.agent.md`)

The Codex custom agent format (confirmed in research.md R-03) uses TOML files at `.codex/agents/<id>.toml` with three required fields:
- `name` (string)
- `description` (string)
- `developer_instructions` (string — the system prompt body)

Optional fields: `model`, `model_reasoning_effort`, `sandbox_mode`.

`tomli-w` is the appropriate write-only TOML library (Python 3.11 stdlib only has `tomllib` for reading). Add it to `pyproject.toml` dependencies.

Do not confuse Codex config.toml agent defaults (user-global) with per-project `.codex/agents/` files. The renderer targets the per-project path only.

---

## Subtask Guidance

### T006 — Add `tomli-w` to dependencies; implement `CodexProfileRenderer.render()`

Add to `pyproject.toml`:
```toml
[project]
dependencies = [
  ...
  "tomli-w>=1.0.0",
]
```

Create `src/specify_cli/tool_surface/profiles/codex_renderer.py`:

```python
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
import tomli_w

if TYPE_CHECKING:
    from specify_cli.tool_surface.profiles.models import AgentProfile

FORMAT_CODEX_AGENT = "codex-agent"

class CodexProfileRenderer:
    format_key: str = FORMAT_CODEX_AGENT

    def can_render(self, tool_key: str) -> bool:
        return tool_key in {"codex", "codex-cli", FORMAT_CODEX_AGENT}

    def output_path(self, project_root: Path, profile: AgentProfile) -> Path:
        return project_root / ".codex" / "agents" / f"{profile.profile_id}.toml"

    def render(self, profile: AgentProfile) -> bytes:
        doc: dict[str, object] = {
            "name": profile.friendly_name or profile.profile_id,
            "description": profile.description or "",
            "developer_instructions": profile.system_prompt or "",
        }
        if getattr(profile, "model", None):
            doc["model"] = profile.model
        if getattr(profile, "model_reasoning_effort", None):
            doc["model_reasoning_effort"] = profile.model_reasoning_effort
        if getattr(profile, "sandbox_mode", None) is not None:
            doc["sandbox_mode"] = profile.sandbox_mode
        return tomli_w.dumps(doc).encode("utf-8")
```

Note: `render()` returns bytes. If the existing `ProfileRenderer` Protocol defines it as `str`, adjust to match — but prefer bytes for TOML output since TOML is UTF-8 by spec.

### T007 — Implement `can_render()`, `output_path()`, `format_key`; optional-field passthrough

Verify that `CodexProfileRenderer` satisfies the `ProfileRenderer` protocol defined in `renderers.py`. Check the Protocol definition for:
- Return type of `render()` (bytes or str)
- Whether `output_path()` takes `(project_root, profile)` or just `(profile)`
- Whether `format_key` is a class attribute or instance attribute

Adjust `CodexProfileRenderer` to exactly match the Protocol. Do not change the Protocol itself unless all existing renderers already satisfy the new signature.

Also implement optional-field passthrough: if `AgentProfile` carries fields not in the required three, silently skip them rather than raising. Use `getattr(profile, field, None)` pattern.

### T008 — Register renderer and `FORMAT_CODEX_AGENT` constant

In `src/specify_cli/tool_surface/profiles/renderers.py`, import and register `CodexProfileRenderer`:

```python
from specify_cli.tool_surface.profiles.codex_renderer import (
    FORMAT_CODEX_AGENT,
    CodexProfileRenderer,
)

PROFILE_RENDERERS: list[ProfileRenderer] = [
    ClaudeCodeProfileRenderer(),
    CopilotProfileRenderer(),
    CodexProfileRenderer(),  # add here
]
```

Export `FORMAT_CODEX_AGENT` from `renderers.py` alongside `FORMAT_CLAUDE_AGENT` and `FORMAT_COPILOT_AGENT` so callers have a single import point.

### T009 — Verify `doctor tool-surfaces --kind agent_profile` no longer reports `research_gap` for Codex

After implementing the renderer, run:
```bash
spec-kitty doctor tool-surfaces --kind agent_profile --json
```

The JSON findings for `codex` harness must now report `missing` (if `.codex/agents/` doesn't exist yet) or `present` (if it does) — NOT `research_gap`. `research_gap` should only appear for harnesses with genuinely unconfirmed native agent primitive support.

If the doctor still shows `research_gap` for Codex, trace the capability matrix lookup in `AgentProfilesProvider` and confirm the renderer is registered before the doctor runs.

---

## Branch Strategy

- **Planning base branch**: `feat/agent-profile-projection-plugin-production`
- **Final merge target**: `main` (local only)
- **Depends on**: WP01 must be merged first

To start work: `spec-kitty agent action implement WP02 --agent claude`

---

## Definition of Done

- [ ] `tomli-w` added to `pyproject.toml` dependencies
- [ ] `CodexProfileRenderer` in `src/specify_cli/tool_surface/profiles/codex_renderer.py`
- [ ] `can_render()` returns True for `"codex"`, `"codex-cli"`, `"codex-agent"`
- [ ] `output_path()` returns `<project_root>/.codex/agents/<profile_id>.toml`
- [ ] `render()` produces valid TOML with at least `name`, `description`, `developer_instructions`
- [ ] `FORMAT_CODEX_AGENT` exported from `renderers.py`
- [ ] `doctor tool-surfaces --kind agent_profile --json` shows Codex as `missing` (not `research_gap`)
- [ ] `ruff check` and `mypy --strict` pass on changed modules

---

## Risks

- `tomli-w` version may conflict with existing dependencies — check `uv lock` after adding
- `AgentProfile` model may not have all optional fields (`model`, `sandbox_mode`) — use `getattr` with defaults
- `ProfileRenderer` Protocol may require `render()` to return `str`, not `bytes` — check before implementing
