# Contract: Claude Code Plugin Manifest

**Mission**: agent-profile-projection-plugin-production-01KV3NGS
**Contract ID**: plugin-manifest-claude-01
**Status**: Proposed

---

## Output Path

`dist/spec-kitty-plugins/claude-code/.claude-plugin/plugin.json`

## Required Fields

| Field | Value | Source |
|---|---|---|
| `name` | `"spec-kitty"` | Constant |
| `displayName` | `"Spec Kitty"` | Constant |
| `version` | Current spec-kitty-cli release | `importlib.metadata.version("spec-kitty-cli")` |
| `description` | Human-facing description | Constant string |
| `author.name` | `"Priivacy AI"` | Constant |

## Component Pointers (present only when component exists in bundle)

| Field | Path | Condition |
|---|---|---|
| `skills` | `"./skills/"` | Always — canonical skills always present |
| `agents` | `"./agents/"` | Always — built-in profiles always present |
| `hooks` | `"./hooks/hooks.json"` | Only if hooks.json is non-empty |

## Bundle Directory Layout

```
dist/spec-kitty-plugins/claude-code/
├── .claude-plugin/
│   └── plugin.json         ← this contract
├── skills/
│   └── spec-kitty.<cmd>/   ← one per canonical command (≥15)
│       └── SKILL.md
├── agents/
│   └── <profile_id>.md     ← one per built-in profile
├── bin/
│   └── spec-kitty-wrapper  ← CLI check + uvx fallback script
│       └── spec-kitty-wrapper.cmd  ← Windows equivalent
└── marketplace.json        ← git-based distribution catalog
```

## Validation Gate

`claude plugin validate --strict dist/spec-kitty-plugins/claude-code/` must exit 0.
Runs in CI in the `plugin-validate` job before release.

## Version Invariant

`plugin.json:version` MUST equal `importlib.metadata.version("spec-kitty-cli")` at build time.
A mismatch is a build error, not a warning.
