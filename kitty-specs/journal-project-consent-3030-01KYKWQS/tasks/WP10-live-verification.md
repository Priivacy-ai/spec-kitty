---
work_package_id: WP10
title: Live two-project drain against spec-kitty-dev
dependencies:
- WP06
requirement_refs:
- NFR-001
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 1dc38ea23ee04dbcabd5a56bb19e141163bbb497
created_at: '2026-07-28T13:54:48.701834+00:00'
subtasks:
- T024
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: docs/verification/
create_intent:
- docs/verification/journal-project-consent-live-drain.md
owned_files:
- docs/verification/journal-project-consent-live-drain.md
---

# WP10 — Live verification

Owns SC-008, the criterion no other work package claimed. Unowned by a WP means never executed, which
is how a fake-green ships.

## Why a fake is not sufficient here

This program has already been burned by offline HTTP-fake witnesses passing while the real provider
behaved differently. WP06's recording ingress (NFR-007) proves the selection logic; only a real drain
proves the wire contract.

## Definition of done

- A live two-project drain against **`spec-kitty-dev`** delivers only the consented project.
- Verified **server-side** by grouping delivered events by `project_slug` — the same query that exposed
  the incident. If `saas#585` FR-011's report command has shipped, use it; otherwise a read-only
  Django-shell aggregation is the sanctioned fallback.
- The deliverable is the **captured query output**, committed as the evidence artefact — not a green test.
- **Never production.** `docs/production-safety-guardrails.md` is the controlling runbook.
