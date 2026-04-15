# Spec Kitty Documentation

Spec-kitty is a spec-driven development tool that coordinates AI agents through structured workflows. This documentation is organised using the [Divio documentation system](explanation/divio-documentation.md).

## Documentation Categories

| Category | Purpose | Start here |
|---|---|---|
| **Tutorials** | Step-by-step lessons to learn spec-kitty from scratch. | [Getting Started](tutorials/getting-started.md) |
| **How-To Guides** | Task-oriented recipes for solving specific problems. | [Install & Upgrade](how-to/install-spec-kitty.md) |
| **Reference** | Precise descriptions of CLI commands, configuration, and APIs. | [CLI Commands](reference/cli-commands.md) |
| **Explanation** | Background concepts, architecture, and design decisions. | [Spec-Driven Development](explanation/spec-driven-development.md) |

## Latest Release: 3.1.4

Spec Kitty 3.1.4 (released 2026-04-15) rounds out the `3.1.x` line with runtime, auth, charter, and command-surface cleanup. Key changes across `3.1.1` through `3.1.4`:

- **Runtime loop is now the primary mental model** — `spec-kitty next` remains the canonical driver, and query mode is safe and read-only
- **Hosted auth and SaaS sync are first-class** — browser-based `spec-kitty auth login`, explicit hosted rollout gating, and clearer tracker readiness checks
- **13 slash-command agents are supported** — including first-class Kiro support while retaining legacy `q` compatibility
- **Review and merge resilience improved again** — persisted review-cycle artifacts, focused fix prompts, sparse-checkout preflights, and `spec-kitty doctor sparse-checkout --fix`
- **Charter bundle is a validated contract** — `spec-kitty charter bundle validate` checks the canonical charter outputs and worktrees now resolve them from the main checkout
- **Generated command prompts were cleaned up in 3.1.3/3.1.4** — `charter`, `specify`, `plan`, `implement`, `review`, and `merge` now teach the actual mission/runtime flow instead of stale shim-era guidance

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
