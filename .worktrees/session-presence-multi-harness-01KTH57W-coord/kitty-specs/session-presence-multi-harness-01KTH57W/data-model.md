# Data Model: Session Presence Multi-Harness Orientation

This mission has no persistent data entities (no database, no new structured storage beyond the file formats documented in `contracts/`). The relevant value objects and enumerations are described below.

## Value Objects

### `SessionPresenceContent`

Immutable value object that carries all fields needed to render the orientation block.

| Field | Type | Description |
|---|---|---|
| `version` | `str` | Installed `spec-kitty` version (from `importlib.metadata`) |
| `project_slug` | `str` | Human-readable project identifier (from `AgentConfig`) |
| `health` | `Literal["healthy", "upgrade-available", "migration-required"]` | Project health state |
| `available_version` | `str \| None` | Latest PyPI version if cached; `None` on first run |

**Invariants**:
- `available_version` is `None` only when no version cache exists yet; never `""`.
- When `health == "upgrade-available"`, `available_version` is not `None` and differs from `version`.
- When `health == "migration-required"`, `available_version` may or may not be `None`.

**`render()` output contract**: See `contracts/claude-md-section.md` for the exact text structure.

---

### Health State Determination

Health is derived at `_build_content()` time by evaluating two independent checks in priority order:

```
1. project_needs_migration(project_root)  →  "migration-required"
2. available_version and available_version != version  →  "upgrade-available"
3. otherwise  →  "healthy"
```

`"migration-required"` takes priority over `"upgrade-available"` — a project that needs migration may also be on an old version, but the migration warning is more actionable.

---

## File-Based State

### Version Cache (`~/.kittify/last-cli-check.json`)

See `contracts/version-cache.md`.

### Orientation Block (in harness config files)

The block is bounded by `<!-- spec-kitty:orientation -->` and `<!-- /spec-kitty:orientation -->` markers in all Markdown-based harness targets. The presence of `SECTION_OPEN` in the file is the sole signal used by `has_presence()`. See `contracts/claude-md-section.md`.

### SessionStart Hook (`.claude/settings.json`)

A single JSON object entry in the `hooks.SessionStart` list. See `contracts/settings-json-hook.md`.

---

## Writer Registry Shape

The `WRITER_REGISTRY` is a `dict[str, Writer]` keyed by agent key string (same keys used in `.kittify/config.yaml`). All 19 harness keys must have an entry — no silent gaps.

| Pattern | Writer class | Harness keys |
|---|---|---|
| A (Claude Code) | `ClaudeCodeWriter` | `claude` |
| B (Markdown rules) | `MarkdownRulesWriter` | `cursor`, `windsurf`, `copilot`, `roo`, `kiro`, `gemini` |
| C (AGENTS.md) | `AgentsMdWriter` | `codex`, `opencode`, `antigravity` |
| D (Skills preamble) | `SkillsPreambleWriter` | `pi`, `vibe`, `letta` |
| E (stub) | `NullWriter` | `qwen`, `kilocode`, `auggie`, `q` |
