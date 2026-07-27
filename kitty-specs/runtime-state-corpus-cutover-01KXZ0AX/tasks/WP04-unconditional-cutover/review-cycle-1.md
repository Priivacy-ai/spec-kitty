---
affected_files: []
cycle_number: 1
mission_slug: runtime-state-corpus-cutover-01KXZ0AX
reproduction_command: null
reviewed_at: '2026-07-20T13:59:29Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP04
---

# WP04 Review — Cycle 1: APPROVED (unconditional reader/writer cutover — headline US2)

Full adversarial review (opus). All rubric checks pass; zero snapshot-behaviour regressions.

- **Byte-stability (SC-004/NFR-003) NON-VACUOUS:** real `read_bytes()` before/after on real `emit_status_transition`/`emit_inner_state_changed` + the reworked `implement()` end-to-end test (whose pre-cutover version asserted the OPPOSITE → would fail if the dual-write block remained). Fixture has NO `lane:` field → kept lane mirror is a genuine no-op. 13 + 18 pass.
- **Red classification HONEST — no regression:** ran the flagged behavioral files; every snapshot-authoritative/flag-ON assertion PASSES, including the C-001 symmetric-window fallback (`test_wp_never_touched_by_log_falls_back_to_legacy_markdown`) — the legitimate `tasks_shared` silent-slot fallback was NOT over-deleted. All 4 reds are `..._flag_off` tests in unowned files = WP06/IC-05 split-suite reconciliation.
- **Predicate deleted (SC-002/C-002), not defaulted:** `_phase1_snapshot_authority_active` + facade alias + `__all__` gone from all src except WP05's deferred `tasks_move_task.py`. C-004 twins (`_legacy_lane_mirror_enabled`/`_read_status_phase`) verbatim.
- **`write_shell_pid_claim` fully retired** (def + `__all__` + docstring; zero src call sites; `test_no_dead_symbols` green — only pre-existing SYNC_DISABLE_ENV_VARS reds); 4 test callers reconciled.
- **11 sites collapsed correctly** (snapshot branch kept, legacy dropped, orphan imports/wrappers removed); lane-mirror regression non-vacuous (0 vs 1, identical resolved lane, activation proven real). Writer sweep complete.
- ruff clean (14 files); mypy 1 pre-existing (`emit.py:457`, byte-identical on base). Deviation (kept CLI `shell_pid` param — cascades to user-facing `--shell-pid`, out of scope) acceptable; no `shell_pid:` field emitted.

**⚠️ MERGE-UNIT (concretely proven):** WP04's tip reds `test_persist_wp_file_shell_pid_routes_through_canonical_writer` via `tasks_move_task.py:1958` (WP05's deferred facade import) — WP04 must NOT merge alone; land WP04+WP05(+WP06) as one unit.

**Verdict: APPROVED.**
