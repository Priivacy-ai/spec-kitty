---
work_package_id: WP05
title: IC-METAGUARD — standing positional-anchor ban
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
- FR-014
- FR-015
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1712622"
history:
- created at planning (tasks) — standing meta-guard
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_ratchet_positional_anchor_ban.py
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/test_ratchet_positional_anchor_ban.py
- tests/_arch_shard_map.py
- src/specify_cli/contracts/anchoring.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Read
[contracts/positional-anchor-ban.md](../contracts/positional-anchor-ban.md) and
the plan's meta-guard predicate ruling. **CRITICAL SEQUENCING**: this WP depends on
WP03 + WP04 — it can only go GREEN once no un-migrated line seed remains. Write it
**red-first**; do not merge it before the WS1 migrations.

## Objective
Create the standing all-suite meta-guard that bans an integer reaching a
line-locator sink in an authoritative comparand — the DIR-041 generalization and
#2077's recurrence guard. Enroll it in the CI shard map in this same WP.

## Design (authoritative — do not deviate)
The ban is **int-to-line-sink**, NOT "positional anchor" and NOT `module::Name`
(that would be circular with WS2 and unsatisfiable vs FR-014):
- **Python**: an AST detector flagging an int literal that reaches a line sink —
  the 2nd positional arg of `composite_key(source, N)` / `composite_key_from_file(path, N)`,
  or a subscript/`.get()` into `code_tokens_by_line(...)`. Post-WS1, no such sink
  remains → green; a reintroduced `(rel, N)` line seed lights it up.
- **YAML**: a field-name rule — ints permitted ONLY in `line` (documented
  non-authoritative locator), `count`, and `*_baseline`; comparand keys
  (`token`/`qualname`/`file`) are non-int by construction.
- `occurrence` ordinals and `module::Name`/`path::qualname` keys are structurally
  never caught.

## Subtasks

### T020 — `test_ratchet_positional_anchor_ban.py` (NEW)
Implement the Python AST int-to-line-sink detector + the YAML field-name rule over
ALL of `tests/architectural/` (Python seeds + `resolution_gate_allowlist.yaml` +
`inline_meta_read_allowlist.yaml`). Reuse `anchoring.is_file_line_anchor` where it
already fires (string `path:NNN` shape); add the AST detector for the call-arg sink.
**S3776 pre-extraction (squad — keep ≤15):** one predicate per sink shape
(`_is_composite_key_line_arg`, `_is_tokens_by_line_index`), a separate
`_yaml_int_field_violations(doc)`, and a thin file-walker — do NOT nest all shape
checks in one `visit_Call`. Give each predicate its own direct unit test.

### T021 — FR-014 census enumeration
The guard's report MUST enumerate the two **deferred** `path::qualname` census
allow-lists (`test_org_activation_seam._BUILTIN_ONLY_ALLOWLIST`,
`test_coord_read_residuals_closeout._IDENTITY_CALLSHAPE_KNOWN_RESIDUALS`) as
known-relocation-anchored-but-out-of-scope, with the follow-up reference.

### T022 — CI shard-map enrollment (SAME WP — landmine)
Add `test_ratchet_positional_anchor_ban.py` to one of the three shard `*_FILES`
tuples in `tests/_arch_shard_map.py` IN THIS WP, or `test_arch_shard_marker_completeness`
reds (unmarked pole-root test → total-partition violation). Post-rebase onto #2545,
add `test_trio_seam_only.py`'s shard entry in the same fold. **Do NOT bump any
`_baselines.yaml total_tests`** — squad-verified that key does not exist
(`total_tests` lives, unenforced, in `_gate_coverage_baseline.json`; `_baselines.yaml`
ratchets allow-list *sizes*, none of which this WP changes). Set
`pytestmark = [pytest.mark.architectural]` on the new test (marker-convention gate).

### T023 — Anchoring helper + escape hatch
Add any needed helper to `anchoring.py` (sole owner) for the detector; keep the
contract's explicit-marker escape hatch for a genuinely new diagnostic int a
future author introduces.

### T024 — Non-vacuity (FR-013)
Plant an int reaching a line sink in a scratch authoritative seed → guard reds.
Confirm the two compliant YAMLs' non-authoritative `line:` fields and the
count-floor baselines stay GREEN (authoritative-vs-diagnostic).

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json`
via `spec-kitty agent action implement WP05 --agent <you>` (branches from the
approved WP03+WP04 base — the meta-guard needs their migrations landed to green).

## Definition of Done
- The guard bans int-to-line-sink in authoritative comparands across all
  `tests/architectural/`; `module::Name`/`path::qualname`/`occurrence`/count-floors
  NOT flagged; the 2 compliant YAMLs green.
- New test enrolled in `tests/_arch_shard_map.py`;
  `test_arch_shard_marker_completeness` green; baselines bumped.
- Non-vacuity reds on a planted sink; full `tests/architectural/` 869/0 (+ the new test).

## Reviewer guidance
The make-or-break: confirm the predicate is int-to-line-sink, NOT `module::Name` (a
`::Name` ban would be circular with WS2 + unsatisfiable vs FR-014). Confirm the
shard-map entry exists (else CI reds post-merge). Confirm the compliant YAMLs stay green.

## Activity Log

- 2026-07-11T16:36:01Z – claude:sonnet:python-pedro:implementer – shell_pid=1619730 – Assigned agent via action command
- 2026-07-11T16:57:30Z – claude:sonnet:python-pedro:implementer – shell_pid=1619730 – Ready: standing int-to-line-sink meta-guard (composite_key 2nd-arg + code_tokens_by_line index + module-level path:NNN seed-string arms; YAML field-name rule permitting int only in line/count/*_baseline). Escape-hatch helper in anchoring.py (sole owner, C-006). FR-014 census enumerated. Shard-map enrolled in _ARCH_SHARD_2_FILES. ruff exit 0; targeted 37 passed; full tests/architectural/ 887 passed/4 skipped/0 failed. Guard is GREEN on live tree (all WS1 line seeds migrated by WP03+WP04).
- 2026-07-11T17:02:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=1712622 – Started review via action command
