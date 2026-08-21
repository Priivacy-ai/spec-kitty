---
work_package_id: WP03
title: '#3488 — verify-and-close delivery residual + FR-008 anti-divergence bind'
dependencies:
- WP02
requirement_refs:
- FR-007
- FR-008
- C-004
planning_base_branch: rc3-drg-projection-completeness-01M0GGS7
merge_target_branch: rc3-drg-projection-completeness-01M0GGS7
branch_strategy: Planning artifacts for this mission were generated on rc3-drg-projection-completeness-01M0GGS7. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-drg-projection-completeness-01M0GGS7 unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
history: []
agent_profile: implementer-ivan
authoritative_surface: tests/charter/
create_intent:
- docs/architecture/doctrine-projection-and-delivery.md
- tests/charter/test_emit_delivery_bind.py
execution_mode: code_change
owned_files:
- docs/architecture/doctrine-projection-and-delivery.md
- tests/charter/test_emit_delivery_bind.py
tags: []
tracker_refs: []
---

# WP03 — #3488: verify-and-close delivery residual + FR-008 bind

**C-004 — verify before touching.** The rc1 #3488 delivery gaps are **already fixed
and correct on current main** (confirmed in research.md): operating-procedures is
data-driven (`_emit_operating_procedure_edges:646`, fail-loud) with a fail-closed
doctor check (`_doctrine_collect.py:_run_operating_procedures_check`); step
`description` renders (`profile_sections.py:142–177`); styleguide/toolguide
pointer-only is a documented deliberate choice (`_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON`,
`:98`). **Do NOT re-fix or revert working delivery code.** The residual is
discoverability + a structural bind.

### Subtask T009 — surface the two contracts (docs)
- **Files:** `docs/architecture/doctrine-projection-and-delivery.md` (new or extend
  an existing doctrine doc — reconcile-don't-duplicate: check for an existing home
  first).
- Document, for pack authors: (a) the styleguide/toolguide **pointer-only** delivery
  contract and why (NFR-001 token budget); (b) the `operating_procedures_unresolved`
  fail-closed diagnostic surfaced by `doctor doctrine`. (FR-007/AC-006)
- Run the terminology guard + docs-freshness after prose edits.

### Subtask T010 — `[red]` FR-008 emit↔delivery anti-divergence test
- **Files:** `tests/charter/test_emit_delivery_bind.py` (new; declare a `pytestmark`).
- Enumerate the profile selector channels. Assert every channel **projected into the
  DRG** is either body-delivering **or** carries an attested pointer-only contract —
  a channel added to one seam but not the other **fails**. This is the durable
  deliverable that stops the two seams silently re-diverging. (FR-008/AC-007)

### Subtask T011 — attest the pointer-only reason
- **Files:** `tests/charter/test_emit_delivery_bind.py` (or sibling).
- Add an assertion pinning `_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON` so the
  deliberate choice is test-attested, not merely a docstring (AC-006).

## Definition of Done
- [ ] Pointer-only + unresolved-diagnostic contracts documented for pack authors.
- [ ] FR-008 structural test passes and fails on an injected one-seam-only channel.
- [ ] Pointer-only reason attested by a test.
- [ ] **No change to shipped delivery code** (`profile_sections.py` logic) unless a
      real gap is found — if one is, STOP and report (it would contradict the C-004
      grounding).
- [ ] New test file carries a `pytestmark`; terminology + docs-freshness green.

Implement: `spec-kitty agent action implement WP03 --agent claude`
