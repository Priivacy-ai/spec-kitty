---
work_package_id: WP04
title: DRG regeneration, pinned-gate refresh & validation sweep
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-003
- FR-004
- NFR-001
- NFR-003
planning_base_branch: feat/rehome-writing-comms-doctrine
merge_target_branch: feat/rehome-writing-comms-doctrine
branch_strategy: Planning artifacts for this mission were generated on feat/rehome-writing-comms-doctrine. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/rehome-writing-comms-doctrine unless the human explicitly redirects the landing branch.
created_at: '2026-08-05T21:14:46Z'
subtasks:
- T020
- T021
- T022
- T023
- T024
history:
- at: '2026-08-05T21:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/doctrine/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- packs/built-in/agent_profile.graph.yaml
- packs/built-in/directive.graph.yaml
- packs/built-in/styleguide.graph.yaml
- packs/built-in/procedure.graph.yaml
- packs/built-in/tactic.graph.yaml
- packs/built-in/asset.graph.yaml
- tests/doctrine/test_pack_relocation_doctor_gate.py
- tests/doctrine/test_shipped_profiles.py
- tests/doctrine/drg/test_reachability.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

The landing gate. With WP01-WP03's frontmatter final, regenerate the DRG fragments from that
frontmatter, refresh the pinned doctrine-integrity counts to the enlarged set, and prove the
whole set validates clean with no orphans (research D-05). Do NOT hand-edit graph fragments — the
built-in layer is generated (`generated_by: drg-migration-v1`).

## Context & Constraints

- **Depends on WP01-WP03** — only run after all artifact frontmatter is final (edge minting reads
  frontmatter). Branch from the integrated base.
- **Regenerate, don't hand-author (C-002):** `spec-kitty doctrine regenerate-graph` mints the
  nodes/edges; `regenerate-graph --check` gates freshness.
- **Measure, don't guess (D-05):** recompute the node/edge cardinality and the reachability
  frozensets empirically; do not speculatively edit reachability literals.
- **Reachability likely unchanged:** the pins are `_activated() − reachable` over the repo's
  explicit `.kittify/charter/charter.yaml` `activated_*` lists; `agent_profile`/`asset` are not
  activation kinds. Unless this mission *activates* the new directives/procedures/styleguides/
  tactic in that charter (it does not, by default), the reachability literals stay put — but
  verify by running the module's traversal calls and diffing.

## Subtask T020 — Regenerate the DRG fragments

- Run `spec-kitty doctrine regenerate-graph`; commit the regenerated per-kind fragments
  (`packs/built-in/*.graph.yaml`).
- Run `spec-kitty doctrine regenerate-graph --check` → must exit 0 (no staleness).
- **Validation:** every new artifact appears as a node with ≥1 inbound reachability edge
  (`requires`/`suggests`); no new orphan.

## Subtask T021 — test_pack_relocation_doctor_gate.py

- `EXPECTED_PROFILE_COUNT` 18 → 25.
- Recompute the `(node_count, edge_count)` tuple (was `(324, 892)`) from the regenerated
  fragments. **Anti-green-wash (renata-H2):** the expected node delta is **exactly +21** (7
  profiles + 4 directives + 2 styleguides + 2 procedures + 1 tactic + 5 assets), i.e.
  `node_count == 345`; assert `edge_count >= 892 + 21` (each new node needs ≥1 inbound edge). If
  the measured node count is **not 345**, an artifact did NOT scan (e.g. a mis-nested asset — see
  WP03) — STOP and fix the scan; do NOT paste the observed number to make the gate green (a blind
  paste of 340 would hide 5 dropped asset nodes and green-wash SC-001/SC-003). Update the docstring
  mentions to the recomputed values only after the 345 invariant holds.
- Leave `EXPECTED_GLOSSARY_TERM_COUNT = 108` unchanged.
- **Validation:** `pytest tests/doctrine/test_pack_relocation_doctor_gate.py -q` → green.

## Subtask T022 — test_shipped_profiles.py

- Add the 7 new ids to `EXPECTED_PROFILE_IDS` (25 total). (The per-profile contract fields were
  authored in WP01; this WP only registers the ids.)
- **Validation:** `pytest tests/doctrine/test_shipped_profiles.py -q` → green (all 7 satisfy the
  6-field contract; both READMEs match).

## Subtask T023 — drg/test_reachability.py (empirical)

- Run the module's traversal calls (see its docstring) and diff the measured sets against the
  pinned frozensets. Expected: **unchanged** (the new artifacts aren't charter-activated).
  **Anti-skip (renata-L1):** capture the five traversal-call outputs into the T024 evidence
  bundle so "measured, unchanged" is provable — doing nothing must not be indistinguishable from
  measuring.
- If (and only if) a pin genuinely moves, update it AND add the matching ledger row in
  `docs/plans/doctrine/delivery-reachability-wiring-table.md` (else
  `TestProfileRescuesHaveLedgerCoverage` fails). If nothing moves, leave the file untouched.
- **Validation:** `pytest tests/doctrine/drg/test_reachability.py -q` → green.

## Subtask T024 — Validation sweep + evidence

- `spec-kitty doctrine pack validate packs/built-in` → OK, including the `type: asset` tactic
  reference now that the assets exist (confirms research D-02 end-to-end).
- `spec-kitty doctor doctrine --json` → `profile_health.healthy == true`, builtin
  discovered==valid==25, `invalid_profiles == []`, none of the 7 in `skipped_profiles`,
  `org_drg.errors == []`, exit 0.
- `pytest tests/architectural/test_no_legacy_terminology.py -q` → green (Terminology Canon).
- Capture the command outputs as landing evidence (contracts/doctrine-integrity-gates.md G-1…G-7).
- **Validation:** all commands pass; evidence recorded.

## Branch Strategy

Planning base and mission merge target are both `feat/rehome-writing-comms-doctrine`. This WP
depends on WP01-WP03 and its worktree is allocated per computed lane from `lanes.json` off the
integrated base. Completed work merges back into `feat/rehome-writing-comms-doctrine`; the
operator merges the eventual PR to `origin/main`. The **full** `tests/` suite is the CI release
authority (not run in-session).

## Definition of Done

- [ ] `regenerate-graph` run; fragments committed; `--check` exits 0; no new orphan (T020).
- [ ] `EXPECTED_PROFILE_COUNT == 25`; `(node,edge)` tuple recomputed from live fragments; glossary 108 (T021).
- [ ] `EXPECTED_PROFILE_IDS` has the 7 new ids; shipped-profiles gate green (T022).
- [ ] reachability recomputed empirically; unchanged, or moved-with-ledger-row (T023).
- [ ] `doctrine pack validate` OK (incl. type:asset); `doctor doctrine` healthy 25/25, 0 skipped, 0 DRG errors; terminology guard green; evidence captured (T024).

## Risks & Mitigations

- **Stale fragments:** always finish with `regenerate-graph --check`; a stale commit fails CI.
- **Guessed counts:** compute `(node,edge)` from the regenerated files, never estimate.
- **Speculative reachability edits:** measure first; touch a pin only with a ledger row.
- **type:asset resolution failure:** if it fails, the asset path/id (WP03/T018) is wrong — fix
  there, don't relabel the reference.

## Reviewer Guidance

- Demand the `regenerate-graph --check` exit-0 evidence and the recomputed `(node,edge)` values.
- Confirm no graph fragment was hand-edited (diff should be regenerator output only).
- Confirm `doctor doctrine` shows 25/25 and zero skipped/orphan.
- Confirm reachability changes (if any) carry a ledger row.

## Activity Log

- 2026-08-05T21:14:46Z — system — Prompt generated via /spec-kitty.tasks
