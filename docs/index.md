# Spec Kitty Documentation

Spec-kitty is a spec-driven development tool that coordinates AI agents through structured workflows. This documentation is organised using the [Divio documentation system](explanation/divio-documentation.md).

## Documentation Categories

| Category | Purpose | Start here |
|---|---|---|
| **Tutorials** | Step-by-step lessons to learn spec-kitty from scratch. | [Getting Started](tutorials/getting-started.md) |
| **How-To Guides** | Task-oriented recipes for solving specific problems. | [Install & Upgrade](how-to/install-spec-kitty.md) |
| **Reference** | Precise descriptions of CLI commands, configuration, and APIs. | [CLI Commands](reference/cli-commands.md) |
| **Explanation** | Background concepts, architecture, and design decisions. | [Spec-Driven Development](explanation/spec-driven-development.md) |

## Version Tracks

Spec-kitty ships two major version lines. Choose the track that matches the version you have installed.

| Track | Use when | Entry point |
|---|---|---|
| `1.x` | You are maintaining a deprecated legacy workflow that is now maintenance-only. | [Open 1.x docs](1x/index.md) |
| `2.x` | You are building on the current stable line published from `main` and PyPI. | [Open 2.x docs](2x/index.md) |

## Verification Notes

Versioned docs are tested for:

1. Relative-link integrity.
2. Required version-track pages.
3. Exclusion of out-of-scope hosted-platform terminology in `docs/1x/` and `docs/2x/`.
