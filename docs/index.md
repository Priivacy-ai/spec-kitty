---
title: "Spec Kitty 3.2 Documentation"
description: "Current Spec Kitty 3.2 documentation for new adopters, upgrade operators, harness users, and CLI integrators."
---

<section class="sk-docs-hero" aria-labelledby="sk-docs-title">
  <p class="sk-eyebrow">Spec Kitty 3.2</p>
  <h1 id="sk-docs-title">Spec Kitty 3.2 documentation</h1>
  <p class="sk-docs-lead">Install the CLI, run missions through your AI harness, and keep specs, plans, work packages, and review evidence aligned.</p>
  <nav class="sk-docs-actions" aria-label="Primary documentation paths">
    <a class="sk-btn sk-btn-primary" href="tutorials/getting-started.md">Start from zero</a>
    <a class="sk-btn" href="how-to/upgrade-project.md">Upgrade a project</a>
    <a class="sk-btn" href="reference/cli-commands.md">Open CLI reference</a>
  </nav>
</section>

Spec Kitty 3.2 is the current documentation set. Use it when you are installing Spec Kitty for the first time, upgrading an existing project, running missions through an AI harness, or checking exact CLI behavior.

## Answer summary

- Current target version: Spec Kitty 3.2.
- Current runtime model: Charter-era missions with governed context injection.
- Current governance source: `.kittify/charter/charter.md`.
- Current mission loop: `spec-kitty next --agent <name> --mission <slug>`.
- Upgrade path: start at [Migration to Spec Kitty 3.2](migration/index.md), then follow the current install and project upgrade guides.

## Choose your path

<div class="sk-card-grid">
  <a class="sk-doc-card" href="tutorials/getting-started.md">
    <span class="sk-card-kicker">Tutorial</span>
    <strong>New to Spec Kitty</strong>
    <span>Install the CLI, initialize a project, and run your first mission with a guided outcome.</span>
  </a>
  <a class="sk-doc-card" href="how-to/upgrade-cli.md">
    <span class="sk-card-kicker">How-to</span>
    <strong>Upgrading to 3.2</strong>
    <span>Upgrade the CLI, refresh project files, and use migration notes only when older behavior matters.</span>
  </a>
  <a class="sk-doc-card" href="reference/supported-harnesses.md">
    <span class="sk-card-kicker">How-to</span>
    <strong>Run in your harness</strong>
    <span>Use Claude Code, Codex, OpenCode, Cursor, Gemini, Pi TUI, and other supported hosts.</span>
  </a>
  <a class="sk-doc-card" href="reference/cli-commands.md">
    <span class="sk-card-kicker">Reference</span>
    <strong>Look up commands</strong>
    <span>Find CLI commands, generated files, configuration, environment variables, and supported harnesses.</span>
  </a>
</div>

## Divio documentation types

The current docs keep the four Divio types separate so you can choose by intent:

| Need | Use | Good first page |
|---|---|---|
| Learn by completing a guided flow | [Tutorials](tutorials/getting-started.md) | [Getting Started](tutorials/getting-started.md) |
| Complete a specific task | [How-To Guides](how-to/install-macos.md) | [Install on macOS](how-to/install-macos.md) |
| Look up exact behavior | [Reference](reference/README.md) | [CLI Commands](reference/cli-commands.md) |
| Understand why the system works this way | [Explanation](explanation/spec-driven-development.md) | [Mission System](explanation/mission-system.md) |

## Current 3.2 surface

- [3.2 current overview](3x/index.md) explains the current Charter-era model.
- [Install and upgrade guides](how-to/upgrade-project.md) are the source of truth for current project files.
- [Supported harnesses](reference/supported-harnesses.md) shows the host support matrix.
- [Slash commands](reference/slash-commands.md) maps host command files to Spec Kitty actions.
- [Environment variables](reference/environment-variables.md) covers CI, sync, and local runtime switches.

## Migration and archive

Use migration pages when moving an existing project into 3.2. They are not the current learning path.

- [Migrating from 2.x / early 3.x](migration/from-charter-2x.md)
- [Historical upgrade to 0.12.0](migration/upgrade-to-0-12-0.md)
- [Archive: 2.x docs](archive/2x/index.md)
- [Archive: 1.x docs](archive/1x/index.md)

1.x and 2.x docs are preserved as historical archive. They should not be used to start a new 3.2 project.
