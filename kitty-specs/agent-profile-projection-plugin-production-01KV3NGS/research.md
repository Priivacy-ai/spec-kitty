# Research: Agent Profile Projection and Plugin Production Pipeline

**Mission**: agent-profile-projection-plugin-production-01KV3NGS
**Phase**: 0 — Pre-design research
**Date**: 2026-06-14

---

## 1. TOML Serialization for Codex Agent Profiles

**Decision**: Use Python 3.11 `tomllib` (stdlib, read-only) for parsing and `tomli-w` for writing.

**Rationale**: `tomllib` was added to the stdlib in Python 3.11 (read-only). For writing, `tomli-w` is the canonical lightweight write-only companion (≈200 lines, no dependencies, used by popular projects). Alternative: pure string formatting — rejected because hand-rolled TOML serialization is brittle for multiline strings (`developer_instructions` will commonly contain newlines requiring triple-quoted TOML syntax).

**Codex TOML schema (confirmed from `developers.openai.com/codex/subagents`):**
```toml
name = "profile_id"
description = "Human-facing guidance for when Codex should use this agent."
developer_instructions = """
Core instructions that define the agent's behavior.
Multiple lines are common here.
"""
# Optional fields accepted by Codex:
model = "gpt-5.3-codex-spark"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
```

**Mapping from Spec Kitty profile schema to Codex TOML fields:**
- `profile_id` → `name`
- `friendly_name` or `description` → `description` (human-facing)
- Body (delegations + avoidance_boundary + instructions) → `developer_instructions` (multiline string)
- `model` hint (if present in profile) → `model` (optional)

**Alternatives considered**: `tomlkit` (full round-trip, heavier), `pytoml` (unmaintained). `tomli-w` is the minimum viable option and is already used in the Python ecosystem for exactly this case.

---

## 2. Wiring Repair Service into Init/Upgrade

**Decision**: Extract a dedicated `run_surface_repair()` entry point in `src/specify_cli/tool_surface/service.py` that accepts `project_root`, `is_interactive`, and `configured_tools` — call this from init and upgrade rather than calling `run_tool_surfaces()` (which includes the full doctor probe path and is designed for `doctor` output, not init/upgrade summary output).

**Rationale**: `run_tool_surfaces()` returns a `SurfaceReport` + `RepairResult` structured for JSON doctor output. Init/upgrade need a different UX: a rich summary panel, not JSON. Extracting `run_surface_repair()` keeps the concerns separated and avoids coupling the upgrade summary format to the doctor JSON schema.

**Threading `is_interactive`**: The typer context provides `ctx.obj.is_interactive` (or equivalent). The repair entry point accepts this as a parameter. The `SurfaceRepairService.repair()` method already accepts `dry_run`; a new `interactive` parameter controls whether to prompt or report-only on drift. The prompt uses rich `Confirm.ask()`.

**`--repair-drift=overwrite` flag design**: Both `init` and `upgrade` commands gain a `--repair-drift` option (typer `Option`) accepting `"overwrite"` as the only valid value currently. `--yes` is explicitly documented to NOT imply `--repair-drift=overwrite`. The non-interactive path checks `is_interactive=False AND repair_drift != "overwrite"` → report-only for drifted surfaces.

**Idempotency guarantee**: After a successful repair run, the repair service writes a content hash for each generated file to the manifest. On the second run, the hash comparison detects no drift and no staleness → zero changes reported. This is the existing `ManagedFileEntry` pattern in `manifest.py`.

---

## 3. Harness Capability Matrix — Research Findings

**Confirmed native agent profile primitives (as of 2026-06-14):**

| Harness | Format | Location | Status |
|---|---|---|---|
| Claude Code | Markdown + YAML frontmatter | `.claude/agents/<id>.md` | GA (v2.0.12+) |
| Codex CLI | TOML | `.codex/agents/<id>.toml` | Confirmed in official docs |
| Copilot / VS Code | Markdown + YAML frontmatter | `.github/agents/<id>.agent.md` | GA in VS Code |
| Amazon Q CLI | JSON | `~/.aws/amazonq/cli-agents/<id>.json` | GA (AWS What's New, July 2025) |
| Augment Code | Markdown + YAML frontmatter | `.augment/agents/<id>.md` | CLI-GA; IDE-beta |

**Confirmed no native agent profile primitive:**

| Harness | Reason | Ruling |
|---|---|---|
| Cursor | Rules only (`.cursorrules`, `.cursor/rules/*.mdc`); no switchable persona primitive | `not_applicable` |
| Windsurf / Devin Desktop | Rules/memories (`.devin/rules/`, `.windsurfrules`); no persona picker | `not_applicable` |
| Kiro | Steering files (`.kiro/steering/`); context injection only, not persona switching | `not_applicable` |
| Amazon Q (IDE/web) | No file-based agent primitive for IDE/chat surfaces | `not_applicable` |
| Roo Code | Product shut down 2026-05-15; `.roo/` no longer maintained | deprecated/removed |
| Cline (Roo fork) | Custom instructions only; no named persona file format | `not_applicable` |
| GitHub Copilot CLI (`gh copilot`) | Separate from VS Code custom agents; no file-based persona format | `not_applicable` |
| OpenCode | Command-based only; no agent profile primitive | `not_applicable` |
| Qwen Code | Command-based only; no confirmed agent primitive | `not_applicable` |
| Google Gemini CLI | No confirmed native agent primitive | `not_applicable` (pending docs) |
| Pi / Letta / Vibe | Skill-based agents only | `not_applicable` |
| Kilocode / Windsurf Workflows | Workflow-based only | `not_applicable` |

**Amazon Q CLI path note**: `~/.aws/amazonq/cli-agents/` is user-global only. No project-level path (`<repo>/.amazonq/cli-agents/`) is documented. Renderer must write to the user home path. The repair service's project-root staging guard must be relaxed only for Amazon Q JSON output (user-global paths are intentional, not out-of-tree violations). Alternatively, the Amazon Q renderer can be classified as "user-managed" (not tracked by project manifest), which means `init`/`upgrade` suggest the path but do not track/repair it. **Recommendation**: Implement `AmazonQProfileRenderer` as a suggestion-only renderer — generate the JSON, suggest the install path, but do not add it to the project manifest (no drift/repair loop for user-global paths).

**Augment Code**: CLI-GA as of official docs; `.augment/agents/` is workspace-scope (equivalent to `.github/agents/` for Copilot). Implement `AugmentProfileRenderer` with full manifest tracking.

---

## 4. Claude Code Plugin Build — CI Availability of `claude` CLI

**Problem**: `claude plugin validate --strict` requires the Claude CLI to be installed. CI environments may not have it.

**Decision**: Add a CI step that installs Claude CLI via npm before running validate. The Claude CLI is distributed as an npm package (`@anthropic-ai/claude-code`).

```yaml
# .github/workflows steps
- name: Install Claude CLI
  run: npm install -g @anthropic-ai/claude-code
- name: Validate plugin bundle
  run: claude plugin validate --strict dist/spec-kitty-plugins/claude-code/
```

**Alternative**: Mock/skip the validate step in unit tests; run only in a dedicated integration CI job. This is the fallback if the npm install is too slow (≈60s) for fast-test jobs. Use a `@pytest.mark.integration` marker and skip in fast-test suites.

**Plugin version injection**: `version` in `.claude-plugin/plugin.json` must match the release version. Read from `importlib.metadata.version("spec-kitty-cli")` at build time, or parse `pyproject.toml` with `tomllib`. `importlib.metadata` is preferred (no file I/O, works after install).

**`bin/` wrapper script design** (shell-portable):
```bash
#!/usr/bin/env sh
# Spec Kitty CLI wrapper — checks for installed CLI, falls back to uvx
PINNED_VERSION="__VERSION__"  # replaced at build time

if command -v spec-kitty >/dev/null 2>&1; then
    exec spec-kitty "$@"
else
    exec uvx "spec-kitty-cli==${PINNED_VERSION}" "$@"
fi
```
The build step substitutes `__VERSION__` with the current release version. A `.cmd` equivalent is needed for Windows.

**`marketplace.json` format** (Claude Code git-based marketplace):
```json
{
  "name": "spec-kitty-plugins",
  "interface": { "displayName": "Spec Kitty Plugins" },
  "plugins": [{
    "name": "spec-kitty",
    "source": {
      "source": "git-subdir",
      "url": "https://github.com/Priivacy-ai/spec-kitty.git",
      "path": "dist/spec-kitty-plugins/claude-code"
    },
    "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
    "category": "Developer Tools"
  }]
}
```

---

## 5. Codex Plugin Bundle — Schema Constraints

**Confirmed from `developers.openai.com/codex/plugins/build`:**

- Required manifest fields: `name`, `version`, `description`, `author.name`, `interface.displayName`, `interface.shortDescription`
- `hooks` is NOT a valid top-level key in `plugin.json` — hooks are auto-discovered by filesystem presence of `hooks/` directory
- `apps` and `mcpServers` keys must be absent unless the companion files (`.app.json`, `.mcp.json`) actually exist
- Plugins CAN package custom agents via `skills/<name>/agents/openai.yaml` — but Spec Kitty's agent profiles use the direct `.codex/agents/*.toml` mechanism, which is more appropriate for named personas. The plugin bundles skills only.

**`codex plugin marketplace add`** registers a non-default marketplace. The personal marketplace at `~/.agents/plugins/marketplace.json` is auto-discovered.

**Marketplace format** for Codex:
```json
{
  "name": "spec-kitty-plugins",
  "interface": { "displayName": "Spec Kitty Plugins" },
  "plugins": [{
    "name": "spec-kitty",
    "source": { "source": "local", "path": "./dist/spec-kitty-plugins/codex" },
    "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
    "category": "Productivity"
  }]
}
```

---

## 6. Command-Skill Manifest Self-Heal

**Stale detection mechanism**: `manifest_store.py` stores each installed skill's `content_hash` (SHA-256 of the rendered SKILL.md content) alongside `installed_at`. On upgrade, the repair service re-renders the canonical SKILL.md and compares hashes:
- Hash matches disk content → present (no action)
- Hash doesn't match disk content and disk file matches `installed_at` hash → stale (auto-repair)
- Hash doesn't match disk content and disk file does NOT match `installed_at` hash → drifted (prompt/report)
- File absent → missing (auto-create)

**Symlink detection**: `os.path.islink(path)` + path matches a canonical skill root → flag as unsafe symlink artifact. Remove only if the symlink target does NOT point to a user-owned location outside spec-kitty's managed roots.

---

## 7. Roo Code Removal — Scope

**Affected files (grep confirmed)**:
- `src/specify_cli/__init__.py`: `AI_CHOICES` includes `"roo"`, `agent_folder_map` maps `"roo"` to `.roo/`
- `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`: `AGENT_DIRS` includes `(".roo", "commands")`
- `src/specify_cli/agent_utils/directories.py`: `AGENT_DIR_TO_KEY` maps `.roo` → `roo`
- `src/specify_cli/cli/commands/init.py`: help text mentions Roo Code
- `README.md`: Roo Code in Supported AI Agents table
- Test files referencing `roo` or `.roo/` (to be identified during implementation)

**Migration approach**: New migration `m_0_XX_roo_deprecation.py` that:
1. Checks for `.roo/` directory existence — if present, emits deprecation notice
2. Reads `config.yaml` — if `roo` in agent list, removes it and saves
3. Does NOT delete `.roo/` contents

**Version bump**: This removal is a breaking change for `roo` users — requires minor version bump and `CHANGELOG.md` entry.
