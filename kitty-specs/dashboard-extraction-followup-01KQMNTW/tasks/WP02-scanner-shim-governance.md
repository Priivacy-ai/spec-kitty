---
work_package_id: WP02
title: DRIFT-1 — Scanner-Shim Governance Addendum
dependencies: []
requirement_refs:
- FR-004
- FR-005
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: architect-alphonso
authoritative_surface: kitty-specs/dashboard-service-extraction-01KQMCA6/
execution_mode: planning_artifact
owned_files:
- kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md
- architecture/2.x/05_ownership_map.md
- architecture/2.x/05_ownership_manifest.yaml
- architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md
role: architect
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load architect-alphonso
```

You are Architect Alphonso. Architectural documentation only — no source code in this WP.

## Objective

Retroactively document `src/specify_cli/scanner.py` (the 17-line re-export shim added during the parent extraction) so the parent mission's governance record is complete and a reviewer auditing DIRECTIVE_024 (Locality of Change) compliance can find the file from any of three independent entry points.

## Subtasks (already implemented at commit `dcbba9439`)

### T004 — Author the addendum

`kitty-specs/dashboard-service-extraction-01KQMCA6/scanner-shim-ownership-addendum.md` — captures: what the shim is, why it exists (FR-010 bridge), removal trigger (scanner extraction mission #613 completion), audit trail (3 entry points), scope guard (no expansion to unrelated symbols).

### T005 — Ownership map entry

`architecture/2.x/05_ownership_map.md` § Dashboard `shims:` adds:

```
- path: src/specify_cli/scanner.py
  canonical_import: specify_cli.dashboard.scanner (will move with scanner extraction mission #613)
  removal_release: scanner extraction mission completion (#613)
```

with a cross-link to the addendum.

### T006 — Manifest entry

`architecture/2.x/05_ownership_manifest.yaml` `dashboard.shims[1]` mirrors the map entry in machine-readable form. Schema-validated.

### T007 — ADR cross-link

`architecture/2.x/adr/2026-05-02-1-dashboard-service-extraction.md` Consequences section gains an "Auxiliary scanner shim" bullet that names the shim and links to the addendum.

## Definition of Done

- [ ] Addendum exists and is self-contained.
- [ ] Ownership map shim entry references the addendum.
- [ ] Manifest entry mirrors the map; schema test (`tests/architectural/test_ownership_manifest_schema.py`) passes.
- [ ] ADR Consequences names the shim and links to the addendum.

## Reviewer guidance

- Read the addendum cold (no other context) — does it answer "what is this shim, why does it exist, when does it retire, who owns it"?
- Cross-check map vs manifest text for drift.
- Confirm the ADR cross-link points at the right file.

## Risks

- Map / manifest text drift (caught by schema test for structural drift; manual review for text drift).

## Activity Log

- 2026-05-02T19:50:37Z – claude – Moved to claimed
- 2026-05-02T19:50:40Z – claude – Moved to in_progress
- 2026-05-02T19:52:32Z – claude – Moved to for_review
- 2026-05-02T19:52:36Z – claude – Moved to in_review
- 2026-05-02T19:52:39Z – claude – Moved to approved
- 2026-05-02T19:54:16Z – claude – Moved to done
