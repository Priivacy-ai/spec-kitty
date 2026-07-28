---
work_package_id: WP03
title: 'Terminal reject classification (folds #3005)'
dependencies: []
requirement_refs:
- FR-014
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:53:39.091131+00:00'
subtasks:
- T009
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: src/specify_cli/delivery/
owned_files:
- src/specify_cli/delivery/ledger.py
- src/specify_cli/delivery/interfaces.py
---

# WP03 — Terminal reject classification

Unblocks `saas#585` FR-004 and folds #3005.

## Problem

`failed_permanent` is produced at **exactly one site** in the CLI: `sync/batch.py:414-418`, the local
oversized-single-event path. Every server-originated rejection becomes `status="rejected"` →
`process_batch_results` bumps `retry_count` and never deletes (`sync/queue.py:1780-1805`).
`error_category` is not consulted. There is no retry ceiling on the drain path.

## Consequence if unfixed

A server that refuses a project makes the client re-POST the same FIFO window forever, and the
consented project behind it never delivers. That is why `saas#585` FR-004 is capability-gated.

## Definition of done

- A stable refusal reason maps to `failed_permanent` and is counted in terminal-failure totals.
- SC-009: the drain makes **forward progress** past a refused project.
