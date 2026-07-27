---
work_package_id: WP16
title: Non-vacuous inline meta-read ratchet (new gate)
dependencies:
- WP05
- WP06
- WP07
- WP12
- WP13
- WP14
- WP15
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T045
- T046
- T047
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3480311"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_inline_meta_read_gate.py
- tests/architectural/inline_meta_read_allowlist.yaml
execution_mode: code_change
owned_files:
- tests/architectural/test_inline_meta_read_gate.py
- tests/architectural/inline_meta_read_allowlist.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-006, NFR-002, SC-002), `plan.md`
(IC-06), and `contracts/meta-read-ratchet.md`. **Append to `traces/*.md`.**

## Objective

Stand up the first architectural gate for inline `json.loads(<meta>)` reads so the drained class
(WP05/06/07 + WP12–15) cannot regrow. **Non-vacuous** — all four mechanics from the contract are
required. Model on `test_resolution_authority_gates.py`; do NOT invent a weaker shape.

## Context

- **Depends on ALL Thread-B routing** (collision B-edits WP05/06/07 + B-only WP12–15) — the floor is
  pinned at the post-drain count.
- Contract: `contracts/meta-read-ratchet.md` (scanner scope, 4 mechanics, invariants, 3 self-tests).
- Scanner excludes `mission_metadata.py` internals + the `task_utils` adapter.
- Deferred `m_0_13_*` entries (from WP15) are allow-list `{key, rationale, issue}` entries.

## Subtasks

### T045 — Scanner
AST/heuristic scanner over `src/` flagging an inline meta read (`json.loads`/`json.load(open())` whose
arg derives from a `meta.json` path — var names `meta_path|meta_file|meta_json|target_meta_path` or a
`<dir> / "meta.json"` join), excluding `mission_metadata.py` + `task_utils`.

### T046 — Gate (4 mechanics)
`INLINE_META_READ_FLOOR` (integer floor) + `FLOOR_MARGIN` (live−margin ≤ floor < live) +
**routed-count floor** (mirrors `ROUTED_CANONICALIZER_FLOOR` — routed `load_meta*` count can only
rise; blocks mass-allow-listing) + composite-key allow-list with **stale-entry detection**
(`allowlist_keys − live_keys` non-empty ⇒ FAIL). Each deferred entry `{key, rationale, issue}`.

### T047 — 3 self-tests
`test_new_inline_meta_read_is_flagged` (plant → RED), `test_allowlist_entries_are_still_live`
(stale-entry twin-guard), `test_routed_count_floor_blocks_mass_allowlist` (mass-allow-list → RED).

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP16 --agent <name>`.

## Definition of Done
- [ ] All 4 gate mechanics present (floor + margin + routed-count floor + stale-entry detection).
- [ ] 3 self-tests green; a planted raw read goes RED; mass-allow-list attempt goes RED.
- [ ] m_0_13_* deferrals carry rationale + issue; ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Confirm the gate is NON-VACUOUS (all 4 mechanics; the allow-list cannot swallow the census). Verify the
routed-count floor genuinely blocks a mass-allow-list drain. Confirm the 3 self-tests bite.

## Activity Log

- 2026-07-08T09:09:30Z – claude:sonnet:python-pedro:implementer – shell_pid=3265814 – Assigned agent via action command
- 2026-07-08T09:30:44Z – claude:sonnet:python-pedro:implementer – shell_pid=3265814 – Ready: floor=7 (the deferred m_0_13_* + 2 charter-layer sites), 4 mechanics (floor+margin+routed-count-floor+stale-entry), 3 self-tests green
- 2026-07-08T10:11:48Z – user – shell_pid=3265814 – Ready: non-vacuous meta-read ratchet, floor=7 (deferred m_0_13_* + 2 charter-layer sites), 4 mechanics + 3 self-tests
- 2026-07-08T10:13:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=3480311 – Started review via action command
- 2026-07-08T10:18:51Z – user – shell_pid=3480311 – Review passed: non-vacuous meta-read ratchet — 4 mechanics (floor 7 + margin 2 + routed-floor 113/live-117 + composite-key stale-entry twin-guard), scanner exact-7 = deferred sites 1:1 with allow-list (m_0_13_0:56,113 #2477 / m_0_13_5:73 #2478 / m_0_13_8:48,86 #2479 / charter _io.py:380 + mission_type_profiles.py:372 #2480, all OPEN), 3 self-tests bite, 28 green, ruff/mypy clean
