# Spec Kitty Documentation

Spec-kitty is a spec-driven development tool that coordinates AI agents through structured workflows. This documentation is organised using the [Divio documentation system](explanation/divio-documentation.md).

## Documentation Categories

| Category | Purpose | Start here |
|---|---|---|
| **Tutorials** | Step-by-step lessons to learn spec-kitty from scratch. | [Getting Started](tutorials/getting-started.md) |
| **How-To Guides** | Task-oriented recipes for solving specific problems. | [Install & Upgrade](how-to/install-spec-kitty.md) |
| **Reference** | Precise descriptions of CLI commands, configuration, and APIs. | [CLI Commands](reference/cli-commands.md) |
| **Explanation** | Background concepts, architecture, and design decisions. | [Spec-Driven Development](explanation/spec-driven-development.md) |

## Latest Release: 3.1.0

Spec Kitty 3.1.0 (released 2026-04-07) stabilises planning and execution reliability and adds recovery workflows. Key changes:

- **Read-only commands no longer dirty the git tree** — `status`, `next` (query mode), and `dashboard` leave `git status --porcelain` clean
- **`wps.yaml` manifest** — structured dependency source eliminates prose-parser lane corruption; `finalize-tasks` derives deps from YAML, `tasks.md` becomes a generated artifact
- **`spec-kitty next` query mode** — bare call returns current step with `[QUERY]` label; does not advance the state machine
- **Execution resilience** — `merge --resume`, `implement --recover`, `doctor` for stale-claim diagnostics
- **Review resilience** — versioned review-cycle artifacts, focused fix prompts, dirty-state classification
- **Charter** — `spec-kitty charter` replaces `spec-kitty constitution`; auto-migrated by `spec-kitty upgrade`
- **`--mission`** — canonical flag everywhere; `--feature` retained only as a hidden deprecated alias during migration

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
