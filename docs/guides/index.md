---
title: Guides
description: 'End-user how-to guides for Spec Kitty: installing, running missions, orchestration, dashboards, and troubleshooting your own project.'
doc_status: active
updated: '2026-07-21'
related:
- docs/configuration/index.md
- docs/core-concepts/index.md
- docs/development/index.md
- docs/index.md
- docs/operations/index.md
- docs/plans/index.md
- docs/reference/index.md
---
# Guides

## Start here

- [Tutorials](tutorials-index.md) — learning-oriented walkthroughs, in order:
  getting started, your first mission, the governed charter workflow, and
  multi-agent/harness integration.
- [How-to guides](how-to-index.md) — install, run a mission end to end, manage
  agents and the glossary, and recover from common problems.

## Install and set up

- [Install Spec Kitty](install-spec-kitty.md) — platform guides for
  [Linux](install-linux.md), [macOS](install-macos.md),
  [Windows](install-windows.md).
- [Install and upgrade](install-and-upgrade.md), [upgrade the CLI](upgrade-cli.md),
  [upgrade an existing project](upgrade-project.md).
- [Install the Claude Code plugin](install-claude-code-plugin.md), [set up
  Codex](setup-codex-spec-kitty-launcher.md).
- [Non-interactive init](non-interactive-init.md), [uninstall](uninstall.md).
- [Diagnose installation problems](diagnose-installation.md).

## Governance and doctrine

- [Set up project governance](setup-governance.md) — the charter interview,
  generate, and sync.
- [Synthesize and maintain doctrine](synthesize-doctrine.md).
- [Create an org doctrine pack](create-an-org-doctrine-pack.md) — package your
  organization's doctrine for reuse across projects.
- [Manage the glossary](manage-glossary.md).
- [Troubleshoot charter failures](troubleshoot-charter.md).

## Orchestration and multi-agent work

- [Manage AI agents](manage-agents.md), [switch missions](switch-missions.md),
  [sync workspaces](sync-workspaces.md).
- [Start an ad-hoc specialist session](adhoc-specialist-session.md).
- [Build a custom orchestrator](build-custom-orchestrator.md), [run the
  external orchestrator](run-external-orchestrator.md).
- [Keep MCP agents in the worktree](worktrees-with-mcp-agents.md).
- [Use the `wps.yaml` manifest](use-wps-yaml-manifest.md).

## Operate and observe

- [Use the Spec Kitty dashboard](use-dashboard.md), [use operation
  history](use-operation-history.md).
- [Use retrospective learning](use-retrospective-learning.md).
- [Keep main clean](keep-main-clean.md), [parallel development](parallel-development.md).
- [Review Spec Kitty artifacts with PlanBridge](review-artifacts-with-planbridge.md).
- [Render glossary observations from InvocationPayload](gstack-glossary-observations.md).

## Recover from problems

- [Recover from an implementation crash](recover-from-implementation-crash.md).
- [Recover from an interrupted merge](recover-from-interrupted-merge.md),
  [troubleshoot merge issues](troubleshoot-merge.md).
- [Repair tool surfaces after an upgrade](tool-surface-upgrade-and-repair.md).

## AI harness setup

Per-harness setup and lint-hook notes live under
[`harnesses/`](harnesses/amazon-q.md): Claude Code, Codex, Cursor, Gemini,
Copilot, Windsurf, and others.

## See also

- [Core Concepts](../core-concepts/index.md) — background on missions,
  doctrine, and governance.
- [Development (contributor/maintainer zone)](../development/index.md) —
  landing PRs, the test suite, release process, and CI internals. This
  content lives outside the Guides zone so end-user navigation never
  surfaces contributor-only pages.
- [Reference](../reference/index.md) — exact CLI, configuration, and API
  behavior.
