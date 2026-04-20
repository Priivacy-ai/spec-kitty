# Spec Kitty Documentation

Spec-kitty is a spec-driven development tool that coordinates AI agents through structured workflows. This documentation is organised using the [Divio documentation system](explanation/divio-documentation.md).

## Documentation Categories

| Category | Purpose | Start here |
|---|---|---|
| **Tutorials** | Step-by-step lessons to learn spec-kitty from scratch. | [Getting Started](tutorials/getting-started.md) |
| **How-To Guides** | Task-oriented recipes for solving specific problems. | [Install & Upgrade](how-to/install-spec-kitty.md) |
| **Reference** | Precise descriptions of CLI commands, configuration, and APIs. | [CLI Commands](reference/cli-commands.md) |
| **Explanation** | Background concepts, architecture, and design decisions. | [Spec-Driven Development](explanation/spec-driven-development.md) |

## Latest Release: 3.1.6

Spec Kitty 3.1.6 (released 2026-04-20) is a focused `3.1.x` hotfix:

- **`agent action implement` now exposes `--acknowledge-not-bulk-edit`** — the wrapper forwards the override to the underlying workspace-allocation command, so non-bulk-edit missions can proceed past false-positive bulk-edit inference warnings.
- **The internal maintainer charter now codifies the user-customization ownership boundary** — package-owned mutation flows must preserve user-authored custom commands, custom skills, and project overrides unless ownership is proven by a managed-path or manifest contract.

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
