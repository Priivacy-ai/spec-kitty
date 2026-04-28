# Spec Kitty Documentation

Spec-kitty is a spec-driven development tool that coordinates AI agents through structured workflows. This documentation is organised using the [Divio documentation system](explanation/divio-documentation.md).

## Documentation Categories

| Category | Purpose | Start here |
|---|---|---|
| **Tutorials** | Step-by-step lessons to learn spec-kitty from scratch. | [Getting Started](tutorials/getting-started.md) |
| **How-To Guides** | Task-oriented recipes for solving specific problems. | [Install & Upgrade](how-to/install-spec-kitty.md) |
| **Reference** | Precise descriptions of CLI commands, configuration, and APIs. | [CLI Commands](reference/cli-commands.md) |
| **Explanation** | Background concepts, architecture, and design decisions. | [Spec-Driven Development](explanation/spec-driven-development.md) |

## Latest Release: 3.1.7

Spec Kitty 3.1.7 (released 2026-04-28) is a focused `3.1.x` stability hotfix:

- **Compact charter context now keeps charter anchors in LLM context** — follow-on agent prompts retain charter section anchors plus directive and tactic IDs after bootstrap.
- **Review, intake, auth, tracker, dashboard, and sync stability fixes** — 3.1.7 backports targeted quality fixes from HEAD without taking the larger 3.2 feature tranche.

**Upgrading from 3.0.x?** Run `spec-kitty upgrade` — all renames happen automatically.

See the full [CHANGELOG](../CHANGELOG.md) for complete release notes.

## Version Tracks

| Track | Use when | Entry point |
|---|---|---|
| `3.x` (current) | New projects and all projects on `main` or PyPI. | This documentation |
| `1.x` | Maintaining a deprecated legacy workflow (maintenance-only). | [Open 1.x docs](1x/index.md) |

## Verification Notes

Versioned docs are tested for:

1. Relative-link integrity.
2. Required version-track pages.
3. Exclusion of out-of-scope hosted-platform terminology in `docs/1x/` and `docs/2x/`.
