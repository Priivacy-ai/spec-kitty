# Spec Kitty Documentation

Spec-kitty is a spec-driven development tool that coordinates AI agents through structured workflows. This documentation is organised using the [Divio documentation system](explanation/divio-documentation.md).

## Documentation Categories

| Category | Purpose | Start here |
|---|---|---|
| **Tutorials** | Step-by-step lessons to learn spec-kitty from scratch. | [Getting Started](tutorials/getting-started.md) |
| **How-To Guides** | Task-oriented recipes for solving specific problems. | [Install & Upgrade](how-to/install-spec-kitty.md) |
| **Reference** | Precise descriptions of CLI commands, configuration, and APIs. | [CLI Commands](reference/cli-commands.md) |
| **Explanation** | Background concepts, architecture, and design decisions. | [Spec-Driven Development](explanation/spec-driven-development.md) |

## Latest Release: 3.1.5

Spec Kitty 3.1.5 (released 2026-04-16) continues the `3.1.x` stable line with upgrade hardening, neutral charter defaults, and release-surface cleanup:

- **Runtime loop is now the primary mental model** — `spec-kitty next` remains the canonical driver, and query mode is safe and read-only
- **Hosted auth and SaaS sync are first-class** — browser-based `spec-kitty auth login`, explicit hosted rollout gating, and clearer tracker readiness checks
- **13 slash-command agents are supported** — including first-class Kiro support while retaining legacy `q` compatibility
- **Review and merge resilience improved again** — persisted review-cycle artifacts, focused fix prompts, sparse-checkout preflights, and `spec-kitty doctor sparse-checkout --fix`
- **Charter bundle is a validated contract** — `spec-kitty charter bundle validate` checks the canonical charter outputs and worktrees now resolve them from the main checkout
- **Upgrade auto-commit no longer trips on rename-heavy migrations** — `safe_commit` keeps a one-path-per-line probe and upgrade staging expands changed directories before validation
- **Charter defaults are language-neutral by design** — no pytest/junit bias in packaged defaults or plan templates, and scoped doctrine assets still load when the repo has not declared an active language set yet

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
