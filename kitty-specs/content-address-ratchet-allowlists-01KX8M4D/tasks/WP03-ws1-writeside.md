---
work_package_id: WP03
title: IC-WS1-WRITESIDE — write-side + wp05 migration
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-006
- FR-013
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1580485"
history:
- created at planning (tasks) — WS1 write-side + wp05
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/test_no_write_side_rederivation.py
- tests/architectural/test_wp05_write_target_drain.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read the plan's
**descriptor feasibility table** ([plan.md](../plan.md) Post-Plan Squad Hardening)
— it gives you the EXACT `(qualname, token_substring)` for every seed you migrate
(WS#1–3, CG#1–4, WP05). Consume the WP02 resolver; do not reinvent it.

## Objective
Migrate the write-side re-derivation seeds and the wp05 anchor from line-number
seeds to content descriptors (WP02 resolver), convert the line-number twin-guards
to descriptor-still-live, and delete the re-anchor changelog fossils.

## Subtasks

### T010 — Migrate `_ALLOW_LIST_SEED` (WS#1/2/3)
Replace the `(rel_path, line)` tuples with content descriptors, per the table:
- WS#1: `_resolve_write_target` / `coord_branch or _current_branch`
- WS#2: `_review_feedback_root` / `return feature_dir . parent . parent`
- WS#3: `_status_commit_destination_branch` / `get_current_branch ( repo_root ) or fallback_branch`
Author each `token_substring` from the finding's **own** normalized token line
(GAP-1). Keep the rationale strings.

### T011 — Migrate `_CHECKOUT_GRAMMAR_ALLOW_LIST_SEED` (CG#1-4)
Per the table: CG#1 `BookkeepingTransaction.commit` / `CommitTarget ( ref = self . destination_ref )`;
CG#2 `_mr_resolve_context` / `CommitTarget ( ref = st . target_branch )`;
CG#3 `_commit_via_legacy_safe_commit` / `CommitTarget ( ref = target_branch )`;
CG#4 `_mt_commit_lane_deliverables` / `CommitTarget ( ref = workspace . branch_name )`.

### T012 — Convert the three line-number twin-guards
`test_checkout_head_selector_entry_is_still_a_live_finding`,
`test_checkout_grammar_allow_list_entries_are_still_live`, and
`test_allow_listed_line_is_the_deferred_head_selector` currently assert `seed_line
∈ {live linenos}` / read the seed line. Convert each to
`descriptor_still_live(...)` — exactly-one, key-equal. NO line-number set membership.

### T013 — Migrate `test_wp05_write_target_drain.py`
Two positional anchors: the `_ALLOW_LISTED_LINE = 347` scalar constant (`:53` —
claim-verified name) AND the `composite_key(source, _ALLOW_LISTED_LINE)` call-arg
(`:170`) — both point at `_resolve_write_target` / `coord_branch or _current_branch`.
Replace with a content descriptor + the WP02 resolver. **Preserve the two
behavioural reachability probes** (`test_negative_probe_reaches_336_fallback...`,
`test_336_short_circuits_to_coord_branch...`) unchanged.

### T014 — Delete the re-anchor changelog fossils
Remove the stale `343→347` note in wp05 and the `_CHECKOUT_GRAMMAR` bump notes in
`test_no_write_side_rederivation.py` — they document the tax now removed.

### T015 — Plant-and-catch + motion battery (FR-013, NFR-001/002)
- Motion battery: insert blank/comment/multi-line above a migrated site → gate green.
- Bite: plant a new un-allowlisted re-derivation → red.
- **Same-qualname sibling** (the D-1 case): in a function holding a sanctioned
  allow-listed site, plant a *second* un-sanctioned offender with the same token
  line → the gate reds (proves exactly-one + key-equal staleness didn't absorb it).

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json`
via `spec-kitty agent action implement WP03 --agent <you>` (branches from WP02's approved base).

## Definition of Done
- All 3 `_ALLOW_LIST_SEED` + 4 `_CHECKOUT_GRAMMAR` + wp05 anchors are content
  descriptors; 3 twin-guards use `descriptor_still_live`; fossils deleted; wp05
  probes intact.
- Motion battery 0 false-reds; bite + same-qualname-sibling reds; full
  `tests/architectural/` 869/0; no line number in any authoritative comparand of
  these two files.

## Reviewer guidance
Cross-check each migrated descriptor against the plan's table. Verify the twin-guards
are exactly-one/key-equal (not "≥1"). Run the motion battery and confirm 0 false-reds,
and the same-qualname-sibling bite test actually reds.

## Activity Log

- 2026-07-11T15:51:30Z – claude:sonnet:python-pedro:implementer – shell_pid=1494601 – Started implementation via action command
- 2026-07-11T16:16:59Z – claude:sonnet:python-pedro:implementer – shell_pid=1494601 – Ready: WS#1-3 + CG#1-4 + wp05 anchor migrated to content descriptors (WP02 resolve_descriptor/descriptor_still_live); 3 twin-guards converted to descriptor_still_live (exactly-one, key-equal); re-anchor changelog fossils deleted; T015 plant-and-catch added (motion battery green, bite red, D-1 same-qualname-sibling red). ruff check exit 0. Full tests/architectural/ = 850 passed, 4 skipped, 0 failed. Note: cherry-picked WP02's resolver commit (945fae896) onto this lane in a separate commit first -- the coordination branch this lane was created from predates WP02's approval merge, so tests/architectural/_ratchet_keys.py's resolver additions were absent; pulled forward verbatim rather than reinventing.
- 2026-07-11T16:17:52Z – claude:opus:reviewer-renata:reviewer – shell_pid=1580485 – Started review via action command
- 2026-07-11T16:31:17Z – user – shell_pid=1580485 – Review passed: WS#1-3 + CG#1-4 + wp05 anchor migrated to ContentDescriptors (token_substrings match plan table, each from finding's own normalized token line, verified by import-time resolve_descriptor). 3 twin-guards use descriptor_still_live (exactly-one, key-equal). wp05 scalar+call-arg replaced by descriptor; 2 reachability probes untouched. Fossils deleted; no line-number in any comparand. T015: motion battery green, bite reds, same-qualname-sibling reds (D-1 exactly-one proof). WP02 resolver cherry-pick verbatim. Owned tests 25/25; full tests/architectural 850/0; ruff clean.
