---
work_package_id: WP01
title: Policy-reversal ADR + design-decision resolution (foundation)
dependencies: []
requirement_refs:
- FR-016
- C-002
planning_base_branch: pr/rc3-charter-gate-predicate-inversion
merge_target_branch: pr/rc3-charter-gate-predicate-inversion
branch_strategy: Planning artifacts for this mission were generated on pr/rc3-charter-gate-predicate-inversion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/rc3-charter-gate-predicate-inversion unless the human explicitly redirects the landing branch.
subtasks: []
history: []
agent_profile: planner-priti
authoritative_surface: docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md
create_intent: []
execution_mode: planning_artifact
owned_files:
- docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md
role: implementer
tags:
- adr
- governance
tracker_refs: []
---

# WP01 — Policy-reversal ADR (foundation)

## Context
The single policy-reversal ADR (`docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md`, authored at plan) is the governance sign-off (C-002) for the two deliberate behaviour reversals and the third (bugfix) change, and the canonical record of the resolved design decisions. Every code WP references it in its red-by-design reversal.

## Definition of done (verification — no ATDD test; doc deliverable)
1. The ADR **names all four** red-by-design tests (FR-016): `test_every_load_delivery.py:197`, `test_context_schema_version_ledger.py:104`, `test_mission_type_profiles.py:260`, `test_worktree.py:263`.
2. The ADR resolves: filename authority = `expected-artifacts.yaml` `path_pattern`; FR-001 predicate = node-URN membership (with `None` guard); custom-family gate = data-driven presence + retained strict-raise; no `load_validated_graph` memoization; pin-and-defer third kind; stray-`spec.md` labelled a bugfix distinct from the two policy reversals.
3. Registered in the page inventory + era README (`freshen_adr_inventory.py`) and `check_docs_freshness.py --ci` is clean.
4. **Owns no tracker issue** — the issue-matrix must not create a row for WP01 (issue-verdict would otherwise flag an orphan WP).

## Validation surface
`scripts/docs/check_docs_freshness.py --ci` (errors=0); `pytest tests/architectural/test_no_legacy_terminology.py`.
