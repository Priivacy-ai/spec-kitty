# Configuration Reference

This document describes all configuration files used by Spec Kitty.

---

## meta.json (Feature Metadata)

Each feature has a `meta.json` file in its directory that stores metadata about the feature.

**Location**: `kitty-specs/<feature-slug>/meta.json`

**Fields**:

```json
{
  "feature_number": "014",
  "slug": "014-comprehensive-end-user-documentation",
  "friendly_name": "Comprehensive End-User Documentation",
  "mission": "documentation",
  "vcs": "git",
  "source_description": "Original feature description provided during /spec-kitty.specify",
  "created_at": "2026-01-16T12:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `feature_number` | string | Three-digit feature number (e.g., "014") |
| `slug` | string | Full feature slug including number |
| `friendly_name` | string | Human-readable feature name |
| `mission` | string | Mission type: `software-dev`, `research`, or `documentation` |
| `vcs` | string | VCS backend: `git` (auto-detected if not specified) |
| `source_description` | string | Original description from `/spec-kitty.specify` |
| `created_at` | string | ISO 8601 timestamp of creation |

> **VCS Lock**: Once a feature is created, its VCS is locked in `meta.json`. All workspaces for that feature use the same VCS backend. This ensures consistency across work packages.

---

## Work Package Frontmatter

Each work package file (`tasks/WP##-*.md`) contains YAML frontmatter that tracks its status.

**Location**: `kitty-specs/<feature-slug>/tasks/WP##-*.md`

**Fields**:

```yaml
---
work_package_id: "WP01"
title: "Setup and Configuration"
lane: "planned"
dependencies: ["WP00"]
subtasks:
  - "T001"
  - "T002"
  - "T003"
phase: "Phase 1 - Foundation"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-16T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---
```

| Field | Type | Description |
|-------|------|-------------|
| `work_package_id` | string | WP identifier (e.g., "WP01") |
| `title` | string | Work package title |
| `lane` | string | Current lane: `planned`, `doing`, `for_review`, `done` |
| `dependencies` | list | WP IDs this WP depends on |
| `subtasks` | list | Task IDs belonging to this WP |
| `phase` | string | Development phase |
| `assignee` | string | Human assignee name |
| `agent` | string | AI agent type (e.g., "claude") |
| `shell_pid` | string | Process ID of implementing agent |
| `review_status` | string | Empty, `has_feedback`, or `approved` |
| `reviewed_by` | string | Reviewer name |
| `history` | list | Activity log entries |

---

## docfx.json (Documentation Build)

DocFX configuration for building the documentation site.

**Location**: `docs/docfx.json`

**Key sections**:

```json
{
  "build": {
    "content": [
      {
        "files": [
          "*.md",
          "tutorials/*.md",
          "how-to/*.md",
          "reference/*.md",
          "explanation/*.md",
          "toc.yml"
        ]
      }
    ],
    "resource": [
      {
        "files": ["assets/**"]
      }
    ],
    "dest": "_site",
    "template": ["default", "modern"],
    "globalMetadata": {
      "_appTitle": "Spec Kitty Documentation",
      "_enableSearch": true
    }
  }
}
```

| Section | Description |
|---------|-------------|
| `content.files` | Markdown files to include |
| `resource.files` | Static assets (images, CSS) |
| `dest` | Output directory (don't commit this) |
| `template` | DocFX templates to use |
| `globalMetadata` | Site-wide settings |

---

## toc.yml (Table of Contents)

Defines the documentation navigation structure.

**Location**: `docs/toc.yml`

**Format**:

```yaml
- name: Home
  href: index.md

- name: Tutorials
  items:
    - name: Getting Started
      href: tutorials/getting-started.md
    - name: Your First Feature
      href: tutorials/your-first-feature.md

- name: How-To Guides
  items:
    - name: Install & Upgrade
      href: how-to/install-spec-kitty.md
```

Each entry has:
- `name`: Display text in navigation
- `href`: Path to markdown file
- `items`: Nested navigation items (optional)

---

## constitution.md (Project Principles)

Optional file defining project-wide coding principles and standards.

**Location**: `.kittify/memory/constitution.md`

**Purpose**: When present, all slash commands reference these principles. Claude and other agents will follow these guidelines during implementation.

**Example**:

```markdown
# Project Constitution

## Code Quality Principles

1. All APIs must have rate limiting
2. All database queries must use parameterized statements
3. All user input must be validated
4. Test coverage must be at least 80%

## Architecture Principles

1. Use dependency injection for testability
2. Separate business logic from infrastructure
3. Document all public APIs
```

**Creating**: Use `/spec-kitty.constitution` to interactively create this file.

---

## Mission Configuration (Advanced)

Mission-specific templates and configuration.

**Location**: `.kittify/missions/<mission-key>/`

**Structure**:

```
.kittify/missions/
├── software-dev/
│   └── mission.yaml
├── research/
│   └── mission.yaml
└── documentation/
    └── mission.yaml
```

**mission.yaml fields**:

```yaml
key: software-dev
name: Software Development
domain: Building software features
phases:
  - research
  - design
  - implement
  - test
  - review
artifacts:
  - spec.md
  - plan.md
  - tasks.md
  - data-model.md
```

---

## VCS Configuration (0.12.0+)

Spec Kitty uses Git as the version control backend. Configuration options control VCS detection and behavior.

### Project-Level VCS Settings

Spec Kitty uses git for version control. Once a feature is created, its VCS is locked in `meta.json`:

```json
{
  "slug": "016-documentation",
  "vcs": "git"
}
```

All work packages for that feature use the same VCS backend, ensuring consistency.

### Checking Current VCS

Use `spec-kitty verify-setup --diagnostics` to see which VCS is active:

```bash
$ spec-kitty verify-setup --diagnostics
VCS Backend: git
```

---

## Server Configuration (2.x)

Configuration for connecting to a spec-kitty server for real-time sync.

**Location**: `~/.spec-kitty/config.toml` (user home directory)

**Fields**:

```toml
[server]
url = "https://your-server.example.com"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `server.url` | string | (none) | Base URL of the spec-kitty server |

> **Note**: This file is created manually or by `spec-kitty auth login` if it doesn't exist.

---

## Credential Storage (2.x)

Stores JWT authentication credentials for server communication.

**Location**: `~/.spec-kitty/credentials.json`

**File permissions**: `600` (owner read/write only)

**Fields**:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "access_expires_at": "2026-02-05T16:00:00Z",
  "refresh_expires_at": "2026-02-12T15:00:00Z",
  "username": "user@example.com",
  "server_url": "https://your-server.example.com"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT access token (short-lived, ~1 hour) |
| `refresh_token` | string | JWT refresh token (longer-lived, ~7 days) |
| `access_expires_at` | ISO 8601 | Expiry timestamp of access token |
| `refresh_expires_at` | ISO 8601 | Expiry timestamp of refresh token |
| `username` | string | Authenticated user's email |
| `server_url` | string | Server this credential is for |

> **Note**: This file is managed by `spec-kitty auth login` and `spec-kitty auth logout`. Do not edit manually.

### WebSocket Authentication (2.x)

During sync, JWT tokens are exchanged for short-lived WebSocket tokens via `POST /api/v1/ws-token/`. The flow is:

1. JWT access token is sent to the server
2. Server returns a short-lived WebSocket token
3. CLI uses the WebSocket token for the sync handshake

This is handled automatically by the CLI — users do not need to manage WebSocket tokens.

See [Sync Architecture](../explanation/sync-architecture.md) for details on the full sync flow.

---

## Agent Configuration

Spec Kitty supports 12 AI agents across different platforms. Agent configuration is stored in `.kittify/config.yaml` and can be managed via CLI commands.

### Supported Agents

| Agent Key | Directory | Platform |
|-----------|-----------|----------|
| `claude` | `.claude/commands/` | Claude (Anthropic) |
| `copilot` | `.github/prompts/` | GitHub Copilot |
| `gemini` | `.gemini/commands/` | Google Gemini |
| `cursor` | `.cursor/commands/` | Cursor AI |
| `qwen` | `.qwen/commands/` | Qwen Code |
| `opencode` | `.opencode/command/` | OpenCode |
| `windsurf` | `.windsurf/workflows/` | Windsurf |
| `codex` | `.codex/prompts/` | GitHub Codex |
| `kilocode` | `.kilocode/workflows/` | Kilocode |
| `auggie` | `.augment/commands/` | Augment Code |
| `roo` | `.roo/commands/` | Roo Cline |
| `q` | `.amazonq/prompts/` | Amazon Q |

### Configuration File

Agent configuration is stored in `.kittify/config.yaml`:

```yaml
agents:
  available:
    - opencode
    - claude
  selection:
    strategy: preferred
    preferred_implementer: opencode
    preferred_reviewer: claude
```

| Field | Type | Description |
|-------|------|-------------|
| `agents.available` | list | Agents enabled for this project |
| `selection.strategy` | string | `"preferred"` or `"random"` |
| `selection.preferred_implementer` | string | Agent for implementation tasks |
| `selection.preferred_reviewer` | string | Agent for review tasks |

### Config-Driven Agent Management

Starting in spec-kitty 0.12.0, agent configuration follows a config-driven model where `.kittify/config.yaml` is the single source of truth for which agents are active in your project.

**Key principles**:
- Agent directories on filesystem (e.g., `.claude/commands/`) are derived from `config.yaml`
- Migrations respect `config.yaml` - only process configured agents
- Use `spec-kitty agent config` commands to manage agents (not manual editing)

**Schema**:
```yaml
agents:
  available:
    - claude
    - codex
    - opencode
  selection:
    strategy: preferred  # or "random"
    preferred_implementer: claude
    preferred_reviewer: codex
```

**Fields**:
- `available` (list): Agent keys currently active in project
- `selection.strategy` (string): Agent selection strategy (`preferred` or `random`)
- `selection.preferred_implementer` (string): Preferred agent for implementation tasks
- `selection.preferred_reviewer` (string): Preferred agent for review tasks

**See**:
- [Managing AI Agents](../how-to/manage-agents.md) - Complete guide to agent management commands
- [CLI Reference: spec-kitty agent config](cli-commands.md#spec-kitty-agent-config) - Command syntax and options
- [ADR #6: Config-Driven Agent Management](../../architecture/adrs/2026-01-23-6-config-driven-agent-management.md) - Architectural decision rationale

> **Legacy behavior**: Projects without `agents.available` field default to all 12 agents for backward compatibility. To adopt config-driven model, use `spec-kitty agent config remove` to remove unwanted agents.

### Managing Agents

#### List Configured Agents

```bash
spec-kitty agent config list
```

Output:
```
Configured agents:
  ✓ opencode (.opencode/command/)
  ✓ claude (.claude/commands/)

Available but not configured:
  - codex, copilot, gemini, ...
```

#### Add Agents

```bash
spec-kitty agent config add claude codex
```

This command:
1. Creates agent directories (`.claude/commands/`, `.codex/prompts/`)
2. Copies slash command templates from mission templates
3. Updates `config.yaml` to include new agents

#### Remove Agents

```bash
spec-kitty agent config remove codex gemini
```

This command:
1. Deletes agent directories
2. Updates `config.yaml` to remove agents

**Options:**
- `--keep-config`: Delete directory but keep in config (useful for temporary removal)

#### Check Agent Status

```bash
spec-kitty agent config status
```

Shows a table of all agents with their status:
- **OK**: Configured and directory exists
- **Missing**: Configured but directory doesn't exist
- **Orphaned**: Directory exists but not configured
- **Not used**: Neither configured nor present

Example output:
```
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Agent Key ┃ Directory           ┃ Configured ┃ Exists ┃ Status   ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ opencode  │ .opencode/command   │     ✓      │   ✓    │ OK       │
│ claude    │ .claude/commands    │     ✓      │   ✓    │ OK       │
│ codex     │ .codex/prompts      │     ✗      │   ✓    │ Orphaned │
└───────────┴─────────────────────┴────────────┴────────┴──────────┘

⚠ 1 orphaned directory found (present but not configured)
```

#### Sync Filesystem with Config

```bash
spec-kitty agent config sync
```

Synchronizes filesystem with `config.yaml`:
- By default, removes orphaned directories (present but not configured)
- Use `--create-missing` to create directories for configured agents
- Use `--keep-orphaned` to keep orphaned directories

**Examples:**

```bash
# Remove orphaned agents (default)
spec-kitty agent config sync

# Create missing directories for configured agents
spec-kitty agent config sync --create-missing

# Keep orphaned directories
spec-kitty agent config sync --keep-orphaned
```

### Agent Selection During Init

When creating a new project, select agents interactively or via CLI:

```bash
# Interactive selection
spec-kitty init myproject

# CLI selection
spec-kitty init myproject --ai opencode,claude

# Single agent
spec-kitty init myproject --ai opencode
```

Selected agents are stored in `config.yaml` and their directories are created automatically.

### Migration Behavior

**Important:** Migrations respect `config.yaml` as the single source of truth.

- **Upgrades only process configured agents** - If you remove an agent, upgrades won't recreate it
- **Deleted agents stay deleted** - Manual deletions are respected
- **Legacy projects fallback gracefully** - Projects without `config.yaml` process all 12 agents

This ensures your agent preferences are preserved across upgrades.

### Troubleshooting

**Q: Why did upgrade recreate agents I deleted?**

This was a bug in versions prior to 0.12.0. Upgrade to the latest version and use `spec-kitty agent config remove` instead of manual deletion.

**Q: How do I add an agent I initially skipped?**

```bash
spec-kitty agent config add <agent-key>
```

**Q: Can I use multiple agents in one project?**

Yes! Configure multiple agents in `config.yaml` and they'll be used according to your selection strategy (`preferred` or `random`).

**Q: What if I manually deleted agent directories?**

Use `spec-kitty agent config sync` to clean up the config or `--create-missing` to recreate them.

---

## Legacy Configuration

### .kittify/active-mission (Deprecated)

**Status**: Deprecated in v0.8.0+

Previously stored the project-wide active mission. Now missions are per-feature and stored in `meta.json`.

If you see this file in older projects, it will be ignored. The mission in each feature's `meta.json` takes precedence.

---

## See Also

- [File Structure](file-structure.md) — Directory layout reference
- [Environment Variables](environment-variables.md) — Runtime configuration
- [Missions](missions.md) — Mission types and their artifacts
- [CLI Commands](cli-commands.md) — Command reference including `--vcs` flag
- [Authentication How-To](../how-to/authenticate.md) — Login, status, logout
- [Server Sync How-To](../how-to/sync-to-server.md) — Pushing/pulling events
- [Sync Architecture](../explanation/sync-architecture.md) — How sync works

## Getting Started
- [Claude Code Integration](../tutorials/claude-code-integration.md)

## Practical Usage
- [Non-Interactive Init](../how-to/non-interactive-init.md)
- [Upgrade to 0.11.0](../how-to/upgrade-to-0-11-0.md)
