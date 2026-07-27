# Contract: Codex Plugin Manifest

**Mission**: agent-profile-projection-plugin-production-01KV3NGS
**Contract ID**: plugin-manifest-codex-01
**Status**: Proposed

---

## Output Path

`dist/spec-kitty-plugins/codex/.codex-plugin/plugin.json`

## Required Fields

| Field | Value | Source |
|---|---|---|
| `name` | `"spec-kitty"` | Constant |
| `version` | Current spec-kitty-cli release (strict semver) | `importlib.metadata.version("spec-kitty-cli")` |
| `description` | Human-facing description | Constant string |
| `author.name` | `"Priivacy AI"` | Constant |
| `interface.displayName` | `"Spec Kitty"` | Constant |
| `interface.shortDescription` | ≤120 chars | Constant string |

## Component Pointers (only when companion files exist)

| Field | Path | Condition |
|---|---|---|
| `skills` | `"./skills/"` | Always — canonical skills always present |
| `mcpServers` | `"./.mcp.json"` | Only if `.mcp.json` exists in bundle |
| `apps` | `"./.app.json"` | Only if `.app.json` exists in bundle |

## Explicitly Forbidden

- `"hooks"` as a top-level key in `plugin.json` — Codex rejects this field; hooks are discovered by filesystem presence of the `hooks/` directory
- `"agents"` as a top-level key — Codex plugin-level agent packaging is NOT confirmed as supported; omit entirely

## Bundle Directory Layout

```
dist/spec-kitty-plugins/codex/
├── .codex-plugin/
│   └── plugin.json         ← this contract
├── skills/
│   └── spec-kitty.<cmd>/   ← one per canonical command
│       └── SKILL.md
├── hooks/                  ← discovered by presence, NOT referenced in plugin.json
│   └── (hook scripts if any)
└── marketplace.json        ← repo-local marketplace catalog
```

## `marketplace.json` Format

```json
{
  "name": "spec-kitty-plugins",
  "interface": { "displayName": "Spec Kitty Plugins" },
  "plugins": [{
    "name": "spec-kitty",
    "source": { "source": "local", "path": "." },
    "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
    "category": "Productivity"
  }]
}
```

## Install Command (documented in README)

```bash
codex plugin marketplace add <path-to-dist/spec-kitty-plugins/codex>
codex plugin add spec-kitty@spec-kitty-plugins
```

## Version Invariant

`plugin.json:version` MUST equal `importlib.metadata.version("spec-kitty-cli")` and be valid semver.
A mismatch or non-semver value is a build error.
