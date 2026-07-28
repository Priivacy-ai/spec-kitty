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

**Acceptance criterion owned: SC-008.** The frontmatter `requirement_refs` are numeric-FR-shaped, so
SC-008 is carried here and in the DoD below — it is the criterion this WP exists to discharge and it
must not be traceable only through prose.

Owns SC-008, the criterion no other work package claimed. Unowned by a WP means never executed, which
is how a fake-green ships.

## Why a fake is not sufficient here

This program has already been burned by offline HTTP-fake witnesses passing while the real provider
behaved differently. WP06's recording ingress (NFR-007) proves the selection logic; only a real drain
proves the wire contract.

## Definition of done

- **SC-008**: a live drain against **`spec-kitty-dev`** at the incident's shape — **≥6 projects**: 1
  consented, ≥3 with no consent record, ≥1 explicit opt-out, ≥1 identity-less. Two projects cannot
  distinguish "delivers only the consented project" from "delivers the only identity-resolved project".
- Verified **server-side** by grouping delivered events by `project_slug` — the same query that exposed
  the incident. If `saas#585` FR-011's report command has shipped, use it; otherwise a read-only
  Django-shell aggregation is the sanctioned fallback.
- The artefact carries its own falsifier: **before/after counts per `project_slug`**, the drain's own
  reported delivered count (so a drain that delivered nothing cannot pass), and the **CLI commit SHA**
  so the evidence ties to the code it attests.
- **Never production.** `docs/production-safety-guardrails.md` is the controlling runbook.
