---
work_package_id: WP04
title: 'Single golden re-ledger (terminal; gated on M3 #3617)'
dependencies:
- WP03
requirement_refs:
- FR-009
- NFR-001
- C-001
- C-002
planning_base_branch: rc3-drg-projection-completeness-01M0GGS7
merge_target_branch: rc3-drg-projection-completeness-01M0GGS7
branch_strategy: Planning artifacts for this mission were generated on rc3-drg-projection-completeness-01M0GGS7. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-drg-projection-completeness-01M0GGS7 unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
history: []
agent_profile: implementer-ivan
authoritative_surface: packs/built-in/
create_intent: []
execution_mode: code_change
owned_files:
- packs/built-in/directive.graph.yaml
- packs/built-in/tactic.graph.yaml
- packs/built-in/paradigm.graph.yaml
- packs/built-in/procedure.graph.yaml
- packs/built-in/mission_type.graph.yaml
tags: []
tracker_refs: []
---

# WP04 — single golden re-ledger

**The graph moves exactly once (C-002).** Both extractor edits (WP01 #3605, WP02
#3604) change what `regenerate-graph` emits; this WP is the one golden-moving commit.
Never hand-edit goldens (C-001).

**External gate (landing sequence):** run this **only after M3 (`#3617`) is merged**.
M3 reads `bundle.merged` but does not regenerate goldens; M2 owns the golden move.
Rebasing onto landed M3 first guarantees M3's cascade tests are validated against
M2's re-ledgered goldens.

### Subtask T012 — regenerate once
- **Preconditions:** WP01 + WP02 landed on this branch; **M3 merged**; this branch
  rebased onto landed `upstream/main` (with M3).
- **Files:** `packs/built-in/*.graph.yaml`.
- Run `spec-kitty doctrine regenerate-graph` **once**; commit the updated fragments
  in a single commit. (FR-009, C-001, C-002 / AC-008)

### Subtask T013 — prove determinism + M3 coexistence
- Run `spec-kitty doctrine regenerate-graph --check` → must be clean (byte-
  deterministic, NFR-001).
- Run M3's cascade tests (`tests/charter/test_cascade.py`) → green against the
  re-ledgered goldens.
- Run this mission's WP01/WP02 tests → green against committed goldens.

## Definition of Done
- [ ] Exactly one commit moves `packs/built-in/*.graph.yaml`.
- [ ] `regenerate-graph --check` clean.
- [ ] M3 cascade tests + M2 tests green against the re-ledgered goldens.
- [ ] Sequenced after M3 merge; branch rebased onto landed M3 first.

Implement: `spec-kitty agent action implement WP04 --agent claude`
