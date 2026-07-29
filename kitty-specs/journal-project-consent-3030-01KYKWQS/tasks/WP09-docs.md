---
work_package_id: WP09
title: Document machine-global env vars
dependencies: []
requirement_refs:
- FR-018
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-journal-project-consent-3030-01KYKWQS
base_commit: b09ac6680ad89efcdaf0fbf029895cea7ca3394b
created_at: '2026-07-29T11:05:47.586998+00:00'
subtasks:
- T023
history: []
authoritative_surface: docs/guides/
execution_mode: code_change
owned_files:
- docs/guides/sync-workspaces.md
tags: []
tracker_refs: []
---

# WP09 — Documentation

**Corrected target.** The original `owned_files` named `docs/guides/sync-workspaces.md`, which is
about **git workspace** sync, not SaaS sync. Both variables are actually documented in
`docs/api/environment-variables.md` (§ Hosted Auth and Sync) — that is the page an operator reads
before exporting, so that is where the warning belongs.

`SPEC_KITTY_ENABLE_SAAS_SYNC` and `SPEC_KITTY_SAAS_URL` are process/shell-global with no
project-scoped form, so a single `export` arms every project that shell subsequently touches. In the
incident the operator armed the shell **on our own advice**, and nothing warned them.

## Definition of done

- The env-var reference states the machine-global scope explicitly, alongside the per-project consent
  model that now governs delivery.
- A **CI-checkable anchor test** fails if the section is removed — otherwise this silently rots.
