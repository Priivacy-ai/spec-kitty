---
work_package_id: WP05
title: Packager publish-flow documentation + changelog
dependencies:
- WP02
- WP04
requirement_refs:
- FR-008
- FR-018
- FR-019
- FR-020
tracker_refs: []
planning_base_branch: feat/oss-fork-packaging-hooks
merge_target_branch: feat/oss-fork-packaging-hooks
branch_strategy: Planning artifacts for this mission were generated on feat/oss-fork-packaging-hooks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/oss-fork-packaging-hooks unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T022
- T023
- T024
- T025
agent: "cursor"
shell_pid: "8275"
history:
- at: '2026-07-21T15:03:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: scribe-sally
authoritative_surface: docs/guides/
create_intent:
- docs/guides/fork-packaging-hooks.md
execution_mode: code_change
owned_files:
- docs/guides/fork-packaging-hooks.md
- docs/guides/upgrade-cli.md
- docs/guides/install-and-upgrade.md
- docs/changelog/CHANGELOG.md
role: implementer
tags: []
---

# Work Package Prompt: WP05 – Packager Documentation

## ⚡ Do This First: Load Agent Profile

Load `scribe-sally` (or `python-pedro` if scribe unavailable) via `/ad-hoc-profile-load` before continuing.

## Objectives & Success Criteria

1. Complete `docs/guides/fork-packaging-hooks.md` covering Phases 1–3 end-state publish flow (thin module + entry points; no `src/specify_cli/**` overlays).
2. Explicit packager-owned vs upstream-owned concerns (FR-020).
3. Link from `docs/guides/upgrade-cli.md` and/or `install-and-upgrade.md` (NFR-005).
4. CHANGELOG entry: additive hooks; stock behaviour unchanged.
5. Terminology guard / docs lint for owned paths.

## Context

Read FR-018–020, IC-05, quickstart. Expand the WP02 stub; do not invent fork hostnames as recommended defaults — use `example.invalid` in samples.

## Branch Strategy

Depends on WP02 + WP04. `spec-kitty agent action implement WP05 --agent <name>`.

## Subtasks

- **T011**: Author Phase 1 registration examples in the guide.
- **T022**: Complete guide end-state (Phases 1–3).
- **T023**: Add discoverability links.
- **T024**: CHANGELOG note.
- **T025**: Quality/terminology sweep on owned docs.

## Definition of Done

FR-018–020 + NFR-005 satisfied; guide usable by a packager who has never patched Spec Kitty core.

## Reviewer Guidance

Ensure out-of-scope list matches spec; no real private registry URLs as upstream defaults.

## Activity Log

- 2026-07-21T16:27:00Z – cursor – shell_pid=5539 – Assigned agent via action command
- 2026-07-21T16:29:30Z – cursor – shell_pid=5539 – Ready for review: fork-packaging guide + links + CHANGELOG.
- 2026-07-21T16:30:22Z – cursor – shell_pid=8275 – Started review via action command
