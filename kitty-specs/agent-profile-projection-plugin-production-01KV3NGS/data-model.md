# Data Model: Agent Profile Projection and Plugin Production Pipeline

**Mission**: agent-profile-projection-plugin-production-01KV3NGS
**Date**: 2026-06-14

---

## Existing Entities (unchanged)

### `ProfileRenderer` Protocol (`profiles/renderers.py`)

```python
@runtime_checkable
class ProfileRenderer(Protocol):
    format_key: str
    def can_render(self, tool_key: str) -> bool: ...
    def output_path(self, tool_key: str, profile: AgentProfile, project_root: Path) -> Path: ...
    def render(self, profile: AgentProfile) -> str: ...
```

**Invariants:**
- `output_path()` must return a path within `project_root` OR be flagged as user-global (Amazon Q)
- `render()` must produce content that round-trips through the target harness's parser without error

### `NativeAgentProfile` (`model.py`)

Fields: `tool_key`, `profile_id`, `output_path`, `status` (`present`/`missing`/`drifted`/`not_applicable`/`research_gap`)

---

## New Entities

### `CodexAgentProfile`

Not a new Python class — it is the TOML file written to disk. The data contract:

| TOML Key | Source Field | Required | Notes |
|---|---|---|---|
| `name` | `AgentProfile.profile_id` | Yes | Codex uses this as the agent identifier |
| `description` | `AgentProfile.description` or `friendly_name` | Yes | Human-readable guidance for when to use this agent |
| `developer_instructions` | Rendered from profile body (delegations + instructions) | Yes | Multiline TOML string; the agent's system prompt |
| `model` | `AgentProfile.model_hint` (if present) | No | Omit if not set in profile |
| `model_reasoning_effort` | `AgentProfile.reasoning_effort` (if present) | No | `"low"` / `"medium"` / `"high"` |
| `sandbox_mode` | `AgentProfile.sandbox_mode` (if present) | No | `"read-only"` or absent |

**State transitions:** `research_gap` → `missing` (once `CodexProfileRenderer` is registered) → `present` (after first upgrade runs the renderer)

### `AmazonQAgentConfig`

The JSON file written to `~/.aws/amazonq/cli-agents/<profile_id>.json`. This is a suggestion-only output (not manifest-tracked):

```json
{
  "name": "<profile_id>",
  "description": "<profile description>",
  "tools": ["*"],
  "resources": []
}
```

**Note**: Amazon Q CLI agent JSON is user-global; it lives outside the project root. This renderer generates the file but does not add it to the project manifest — no drift/repair loop. `doctor tool-surfaces` reports its status by inspecting `~/.aws/amazonq/cli-agents/` directly.

### `AugmentAgentProfile`

The Markdown file written to `.augment/agents/<profile_id>.md`:

```markdown
---
name: <profile_friendly_name>
description: <profile description>
model: <model_hint if present>
tools: ["*"]
---

<profile body — delegations, instructions, avoidance_boundary>

<!-- spec-kitty managed: do not edit by hand -->
```

Manifest-tracked under `.kittify/` with content hash for drift detection.

### `ClaudePluginManifest`

Written to `dist/spec-kitty-plugins/claude-code/.claude-plugin/plugin.json`:

```json
{
  "name": "spec-kitty",
  "displayName": "Spec Kitty",
  "version": "<current spec-kitty-cli version>",
  "description": "Spec-Driven Development toolkit — agent profiles, skills, and governance for AI-assisted software development",
  "author": {
    "name": "Priivacy AI",
    "url": "https://github.com/Priivacy-ai/spec-kitty"
  },
  "keywords": ["spec-driven", "sdd", "agents", "governance"],
  "license": "MIT",
  "skills": "./skills/",
  "agents": "./agents/",
  "hooks": "./hooks/hooks.json"
}
```

**Invariants:**
- `version` must equal `importlib.metadata.version("spec-kitty-cli")` at build time
- `skills`, `agents`, `hooks` paths must point to directories/files that actually exist in the bundle

### `CodexPluginManifest`

Written to `dist/spec-kitty-plugins/codex/.codex-plugin/plugin.json`:

```json
{
  "name": "spec-kitty",
  "version": "<current spec-kitty-cli version>",
  "description": "Spec-Driven Development toolkit for Codex",
  "author": { "name": "Priivacy AI", "email": "..." },
  "skills": "./skills/",
  "mcpServers": "./.mcp.json",
  "interface": {
    "displayName": "Spec Kitty",
    "shortDescription": "Spec-Driven Development — skills and governance",
    "longDescription": "Provides the full Spec Kitty command-skill set for Codex: specify, plan, tasks, implement, review, accept, merge, and more.",
    "category": "Productivity",
    "capabilities": ["Interactive", "Write"]
  }
}
```

**Invariants:**
- `hooks` key must NOT appear in `plugin.json` (rejected by Codex validator)
- `apps` and `mcpServers` keys must be absent if `.app.json` / `.mcp.json` do not exist in the bundle
- `interface.displayName` and `interface.shortDescription` are required non-empty strings

### `DriftPolicySummary`

Emitted by `SurfaceRepairService.repair()` after a repair run:

```python
@dataclass(frozen=True)
class DriftPolicySummary:
    created: list[Path]       # surfaces auto-created (were missing)
    repaired: list[Path]      # surfaces auto-repaired (were stale)
    drifted: list[Path]       # surfaces reported-only (were drifted, not overwritten)
    overwritten: list[Path]   # surfaces force-overwritten (--repair-drift=overwrite)
    skipped: list[Path]       # surfaces skipped (not_applicable)
```

This replaces the existing `RepairResult` for the init/upgrade context (or extends it with the `drifted` and `overwritten` fields).

### `HarnessCapabilityRecord`

Represents the capability ruling for a harness with respect to native agent profiles. Used internally by `AgentProfilesProvider`:

```python
@dataclass(frozen=True)
class HarnessCapabilityRecord:
    tool_key: str
    agent_profile_status: Literal["supported", "not_applicable", "research_gap"]
    reason: str          # human-readable explanation
    renderer_key: str | None   # format_key of the registered renderer, or None
```

---

## State Transitions

### Agent Profile Surface Status (per harness)

```
research_gap  →  (renderer implemented)  →  missing
missing       →  (init/upgrade runs)      →  present
present       →  (user edits file)        →  drifted
drifted       →  (--repair-drift=overwrite OR interactive confirm)  →  present
drifted       →  (user restores original) →  present
present       →  (profile removed)        →  missing
```

### Command-Skill Surface Status

Same as above, with one additional transition:
```
symlink_artifact  →  (upgrade detects + removes)  →  missing  →  (repair creates)  →  present
```

---

## Invariants

1. A `research_gap` entry must never be written to the project manifest; it is computed at runtime from the registry.
2. `not_applicable` entries are never auto-created or auto-repaired — they are skipped silently and included in the summary count only.
3. User-global paths (Amazon Q CLI `~/.aws/amazonq/cli-agents/`) are never added to the project manifest; they are always reported by direct filesystem inspection.
4. Plugin bundle output directories (`dist/spec-kitty-plugins/`) are never tracked in the project manifest — they are ephemeral build outputs.
5. Drift detection requires a content hash stored at last-repair time; manifests without a hash treat the surface as `missing` (not `drifted`).
