---
work_package_id: WP05
title: Verification and Closeout
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- C-001
- C-002
- C-004
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: feat/retire-doctrine-term
merge_target_branch: feat/retire-doctrine-term
branch_strategy: Planning artifacts for this mission were generated on feat/retire-doctrine-term. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/retire-doctrine-term unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 5 - Verification Gate
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/verification-report.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/verification-report.md
role: reviewer
tags: []
task_type: review
tracker_refs: []
---

# Work Package Prompt: WP05 – Verification and Closeout

## Start and boundary

Load `reviewer-renata`; read all mission artifacts/contracts and quickstart. Verify only; write
`verification-report.md`; route substantive failures to WP01–WP04. Every check records command/procedure,
hash/base, timestamp, evidence excerpt/answers, and pass/fail. Missing evidence fails.

## T016 — Baseline, scope, ADR

- Verify frozen target→implementation→HEAD ancestry and committed+working-tree planning-only diff.
- Verify ADR registration freshness and independent eight-question self-sufficiency review.
- Confirm explicit operator override, no-data-loss boundary, M1/I1 effectiveness, the exact per-artifact
  Charter owner/no-op/deletion map, full-current-tree scope outside `kitty-specs/`, the two fixed
  exclusions (Git object history; immutable `kitty-specs/` archive — `DM-01M0NMS9WPH33EPFCJQRTQVNSA`), and
  exact M6 audits.
- Confirm activation fields are written only by activation engine/pack manager commands and answers use
  the sanctioned lossless migration until round-trip-safe interview serialization lands.
- Confirm WP04 consumed canonical `issue-matrix.json` #2727 and M1 atomically joins docs context,
  `.kittify/glossaries/spec_kitty_core.yaml`, built-in glossary pack, and active-referrer parity.
- Fail any user-visible/supported-only, X1/X2/X3, immutable-current-tree-outside-`kitty-specs/`,
  additional-exclusion, internal-source refuge, or runtime managed-path ledger statement.

## T017 — Inventory reproduction

Run the exact frozen no-pipeline subprocess wrappers for forced-text `git grep -a` (fixed
`:(exclude)kitty-specs/`) and NUL-safe `git ls-tree -z` (`kitty-specs/` dropped after rc check). Prove grep
rc 1/empty is the sole content-zero result, grep rc >1 fails, any ls-tree nonzero rc fails, and the named
failing-git mutation cannot produce zero evidence. Regenerate the untracked `inventory-hits.tsv` from the
frozen base and match the SHA-256, row count, and per-kind/S/OC counts recorded in `inventory.md`
byte-for-byte (`DM-01M0NMSD60JYG7K7V5MJCKJ3P8`). Verify TSV set equality, deterministic rows/hashes,
repeated-match ordinals, pathname byte safety, OC/S1–S10 on every row, excluded-root orientation counts,
and zero X/exempt/ignored/unclassified/duplicate/omitted rows. Confirm internal code/tests/build,
metadata/generated, Charter, history/ADR/docs/archive/evidence, fixtures/controls and filenames outside
`kitty-specs/` are present and nothing under `kitty-specs/` is a row.
Run `test_inventory_match_sha256_byte_identical_reproduction` and independently recompute both row kinds
from the exact domain tag, LP framing, big-endian integers, tree OID, and raw path/match bytes.

## T018 — Methodology and invariants

Verify I1–I6 exactly:

- M1 all Charter/glossary owner sources/outputs + override + guard;
- M2 exhaustive private/public topology and pre-edit collision closure, with no old live executable/code
  hit outside registered CR;
- M3/M4 backup/verified canonical preservation, divergent hard fail, no old path on completed migration,
  and no runtime-ledger overdesign;
- M5 every remaining current-tree prose/history file/path/referrer outside `kitty-specs/`; archive
  byte-identical; archive referrers recited by `mission_id`/mid8 or token-free path;
- M6 every alias/key/path/control/fixture/baseline removed, numeric-byte negative tests, exact content/path
  zero over `HEAD` with the single fixed `kitty-specs/` exclusion, bound to one final commit/tree and rerun
  by CI/release through the mandatory entrypoint and `terminology-zero-current-tree` marker on the result
  tree; external evidence does not mutate it.

Check one named verifier per S1–S10 and failure/rollback mutations.

## T019 — Stack arithmetic and dry runs

Prove OC member union equals manifest; M1–M6 owner sets pairwise disjoint/complete; no current-repo
deferral. Verify frozen-base CR source disjointness/introduction=OC owner and distinct later-created
product/control coordinates assigned to M6 removal. Dry-run
M1 with zero questions and every Charter input/output. Dry-run M2's sole topology-map gate and prove every
collision/consumer fixed before edits. Confirm exact dependencies, outputs, merge gates, and rollback.

## T020 — Static/workflow and final verdict

Run `git diff --check`, workflow validation WP01–WP05, contract-reference sweep, and stale-conflict search
for X/internal/history exemptions beyond the fixed `kitty-specs/` root, any wording that edits or renames
under that root, managed-ledger/runtime-state architecture, old-path-survives-completion, or otherwise
narrowed zero wording. Record SC-001..SC-004 verdicts.

## Rejection conditions

Reject on any ownerless hit, X/exemption class, missing pathname/content audit, Charter omission, unresolved
M2 topology collision, completed M3/M4 old path, any M5 history carve-out other than the required fixed
`kitty-specs/` archive root (or any plan that edits/renames under it), a terminal audit that omits that
root or adds any other, retained M6 control/baseline, literal-bearing post-M6 negative fixture, or
nonzero/otherwise-narrowed terminal audit.

## Done

`verification-report.md` contains reproducible PASS evidence for every requirement or explicit routed
failure. Reviewer does not self-repair deliverables.

## Activity Log

Runtime-owned. Do not edit this prompt to record activity; use Spec Kitty task status/events.
