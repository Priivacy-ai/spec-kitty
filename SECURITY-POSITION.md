# Security Position: Spec Kitty

**Last updated**: 2026-02-18

## Executive Summary

Spec Kitty core is a deterministic workflow CLI. It does not force external AI tools into unrestricted execution modes.

As of 2026-02-18, autonomous orchestration is externalized behind a host CLI contract and is optional.

## What Spec Kitty Core Does

1. Manages repository-native workflow artifacts and status transitions.
2. Creates and coordinates isolated worktree-based implementation flow.
3. Provides deterministic CLI command surfaces for plan/task/accept/merge operations.

## Security and Policy Boundaries

1. **No forced YOLO mode in core**: core does not set external AI CLI approval/sandbox/network flags.
2. **State authority in host CLI**: workflow mutations must go through host commands.
3. **Orchestrator is optional**: autonomous runtime is external (`spec-kitty-orchestrator`) and can be disallowed by policy.
4. **Policy metadata required for run-affecting orchestration calls**: host validates and records policy metadata.
5. **No direct provider to SaaS write path**: observability is host-event driven.

## Enterprise Deployment Guidance

1. Run AI CLIs under organization-approved controls (approval mode, sandbox profile, network egress, credential scoping).
2. Treat any autonomous provider as a separately governed component.
3. Use repository/workstation controls appropriate for your environment (least privilege, isolated credentials, endpoint controls).

## Clarification

Historic concerns about bundled autonomous paths in earlier implementations are addressed by current separation:
core host workflow in `spec-kitty`, optional external provider in `spec-kitty-orchestrator`.
