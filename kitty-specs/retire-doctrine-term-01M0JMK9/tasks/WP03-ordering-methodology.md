---
work_package_id: WP03
title: Ordering and Methodology Analysis
dependencies:
- WP02
requirement_refs:
- C-004
- FR-008
planning_base_branch: feat/retire-doctrine-term
merge_target_branch: feat/retire-doctrine-term
branch_strategy: Planning artifacts for this mission were generated on feat/retire-doctrine-term. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-doctrine-term unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 3 - Methodology
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: planner-priti
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Ordering and Methodology

## Start

Load `planner-priti`; read ADR, inventory/manifest, `research.md`, `data-model.md`, both map/stack
contracts, and quickstart §§5–7. Check review feedback.

## Goal

Create `methodology.md` with strict M1→M6 order, I0→I6, per-surface verification, transition-guard/CR
lifecycle, bounded data-safe migrations, and rollback. I6 means exact content/path counts zero over `HEAD`
with the single fixed `kitty-specs/` exclusion (`DM-01M0NMS9WPH33EPFCJQRTQVNSA`).

## T009 — Sequence and invariants

For each transition cite exact OC/hits and risk:

1. M1 makes ADR override effective and executes the ADR contract's exact Charter owner/no-op/obsolete-
   graph-deletion map plus all glossary owners before guard.
2. M2 freezes every internal+public topology row/collision, then merges old source tree into
   `src/charter/` and updates symbols/imports/tests/build/CLI/API/config/workflow/metadata.
3. M3 backs up and verifies project data at `.kittify/charter-packs/`, removing old root only after proof;
   divergence blocks completion.
4. M4 does the same for every source/generated/installed/shared agent artifact/ID/path.
5. M5 rewrites/renames all remaining current-tree prose/history/ADR/docs/archive/evidence/referrers
   outside `kitty-specs/`; the archive is byte-identical; archive referrers are recited by
   `mission_id`/mid8 or token-free path.
6. M6 deletes all compatibility/control/fixture/baseline machinery and passes exact zero audits with the
   fixed exclusion only.

State I1–I6 exactly as `data-model.md`; no internal/history/X terminal state beyond the fixed archive root.

## T010 — Guard and compatibility lifecycle

Define exact shrink-only fingerprints and CR reservations for M1–M5: disjoint frozen-base source hits
retain the introduction-wave OC owner; bounded product/control coordinates created later are distinct
M6-removal work, not duplicate source ownership; exact controls/tests. M6 removes product/control/tombstone plus baseline/
allowlist machinery. Negative tests encode numeric bytes. Mutations must catch new/equal-count/moved hits,
wrong-wave aliases, budget/overlap/control errors, and a surviving detector literal.

## T011 — Verification matrix

Assign one named verifier to S1–S10. Mandatory cases:

- every tracked Charter artifact plus present runtime cache, each exact owner/source input, verified
  no-ops, and repeated zero-consumer proof before obsolete `graph.yml` deletion;
- M2 map set equality, private/public topology, collision freeze, import/build/test closure;
- M3/M4 absent destination, identical destination, divergence, interruption, backup rollback, completed
  old-path absence;
- M5 current-tree ADR/docs/archive filename/referrer closure outside `kitty-specs/`, plus archive
  byte-identity;
- M6 all compatibility categories removed, no exception machinery, forced-text/NUL-safe zero gate, and
  numeric-byte negative test.

## T012 — Evidence and rollback

Each wave freezes a fresh base and occurrence map; records exact inputs/outputs/tests/gate. Before
dependents, revert one wave; afterward reverse suffix/forward-fix. M3/M4 restore verified backup on failure;
post-4.0 is release rollback. Explicitly reject runtime managed-path ledger/state architecture: the plan
needs bounded migration preflight/evidence, not product architecture.

## Done

Every inventory class has a sequenced risk/verifier/rollback path; no policy question or terminal escape
remains.

## Activity Log

Runtime-owned. Do not edit this prompt to record activity; use Spec Kitty task status/events.
