---
work_package_id: WP09
title: Document machine-global env vars
dependencies: []
requirement_refs:
- FR-018
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:54:48.701834+00:00'
subtasks:
- T023
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: docs/guides/
owned_files:
- docs/guides/sync-workspaces.md
---

# WP09 — Documentation

`SPEC_KITTY_ENABLE_SAAS_SYNC` and `SPEC_KITTY_SAAS_URL` are process/shell-global with no
project-scoped form, so a single `export` arms every project that shell subsequently touches. In the
incident the operator armed the shell **on our own advice**, and nothing warned them.

## Definition of done

- The env-var reference states the machine-global scope explicitly, alongside the per-project consent
  model that now governs delivery.
- A **CI-checkable anchor test** fails if the section is removed — otherwise this silently rots.
