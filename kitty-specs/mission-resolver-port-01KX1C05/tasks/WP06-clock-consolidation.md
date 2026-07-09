---
work_package_id: WP06
title: Clock consolidation (+ Sonar stamp campsite)
dependencies:
- WP01
requirement_refs:
- FR-009
- NFR-004
tracker_refs: []
planning_base_branch: feat/mission-resolver-port-2173
merge_target_branch: feat/mission-resolver-port-2173
branch_strategy: Planning artifacts for this mission were generated on feat/mission-resolver-port-2173. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-resolver-port-2173 unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "206504"
history:
- at: '2026-07-08T18:06:06+00:00'
  actor: planner
  action: created
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/
create_intent:
- src/specify_cli/core/time_utils.py
- tests/specify_cli/test_clock_consolidation.py
execution_mode: code_change
owned_files:
- src/specify_cli/core/time_utils.py
- src/specify_cli/event_journal/journal.py
- src/specify_cli/event_journal/coalesce.py
- src/specify_cli/sync/migrate_journal.py
- src/specify_cli/status/reducer.py
- src/specify_cli/status/emit.py
- src/specify_cli/status/lifecycle_events.py
- src/specify_cli/retrospective/lifecycle_events.py
- src/specify_cli/retrospective/events.py
- src/specify_cli/delivery/ledger.py
- src/specify_cli/delivery/targets.py
- src/specify_cli/delivery/retention.py
- src/specify_cli/dossier/events.py
- src/specify_cli/cli/commands/agent/mission_parsing.py
- tests/specify_cli/test_clock_consolidation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load your agent profile via `/ad-hoc-profile-load` for `randy-reducer` (implementer — behavior-preserving
reduction). Then read `kitty-specs/mission-resolver-port-01KX1C05/spec.md` (FR-009, NFR-004), `plan.md`
(IC-06), and `research.md` (D-04 + census).

## Objective

Collapse the **12 byte-identical** isoformat `_now_utc` copies into **one** canonical helper, while
**preserving** the two distinct-contract helper families (2 `%Y-%m-%dT%H:%M:%SZ` stamp callers, 2
`-> datetime` callers) so on-disk timestamps do not change (NFR-004). Fold one SAFE Sonar campsite item.

## The three families (do NOT merge across them)
- **Isoformat string (12 copies → one)**: `return datetime.now(UTC).isoformat()`.
- **Stamp string (preserve, 2)**: `task_utils/support.py:101`, `cli/commands/agent/mission_parsing.py:257`
  → `%Y-%m-%dT%H:%M:%SZ` (second precision, `Z` suffix). Different serialized output — MUST NOT fold into
  the isoformat helper.
- **`datetime` (preserve, 2)**: `decisions/emit.py:64`, `decisions/service.py:86` return a `datetime`, not
  a string. Out of this WP's owned files — leave them; only note them.

## Subtasks

### T024 — One canonical isoformat helper + migrate the 12 copies
- Add `now_utc_iso() -> str` to a shared home. **Naming caution (squad):** `task_utils/support.py:101`
  already defines a `now_utc()` returning a **stamp** string (via `TIMESTAMP_FORMAT`) — do NOT create a
  confusingly-named sibling. Host `now_utc_iso()` in `task_utils/support.py` (already a time-helper home)
  with a clear distinct name, or a new `src/specify_cli/core/time_utils.py` (confirmed not to exist yet).
  Body: `datetime.now(UTC).isoformat()`.
- Replace the 12 byte-identical copies (owned files) with imports of the one helper. Delete the local
  `_now_utc`/`_utc_now_iso`/`_now_iso`/`_iso_utc_now` defs.
- **Completeness follow-up (squad — whack-a-field guard):** ~18 more byte-identical isoformat copies live in
  **NON-owned** files (`sync/*`, `review/*`, `skills/command_installer.py:363`, `merge/state.py`,
  `analysis_report.py`, …). This WP routes only the owned copies — so "one canonical helper" is only
  half-delivered. **File a Priti follow-up** to route the rest and say so in the review; do NOT claim full
  consolidation.

### T025 — Triage the cross-package copies
- Byte-identical isoformat copies exist **across package boundaries**: `src/glossary/events.py:217`,
  `src/runtime/next/_internal_runtime/retrospective_terminus.py:65`, and
  **`src/charter/evidence/code_reader.py:108`** (squad-found; was missing from the plan). Do NOT silently
  stop at 12: for each, either point it at the shared helper (if import direction allows) or record it
  **OUT with a one-line rationale** (import-direction). Not in this WP's owned files — document the decision
  in the review; do not reach out to edit them here.

### T026 — SAFE Sonar campsite + NFR-004 test
- **SAFE fold**: `cli/commands/agent/mission_parsing.py:259` hard-codes `"%Y-%m-%dT%H:%M:%SZ"` — replace
  with the shared stamp constant (`UTC_SECOND_TIMESTAMP_FORMAT`/`TIMESTAMP_FORMAT`). Do NOT change the
  serialized output.
- **ADJACENT (note, don't fold)**: the literal recurs 18× with 4 redundant constant defs
  (`review/cycle.py:23`, `cli/commands/agent/tasks.py:355`, `tasks_materialization.py:43`,
  `task_utils/support.py:22`) — a separate stamp-consolidation cleanup; record it, don't do it here.
- **NFR-004 test**: new `tests/specify_cli/test_clock_consolidation.py` — assert the stamp callers produce
  byte-identical output vs a frozen expected string, and that the one canonical isoformat helper is the
  single definition (grep-style or import assertion).

## Branch Strategy
Planning branch and merge target: `feat/mission-resolver-port-2173`. Lane worktree per `lanes.json`.

## Definition of Done
- One canonical `now_utc_iso()`; the 12 owned copies import it; local dup defs deleted.
- Stamp + datetime families untouched in behavior; NFR-004 byte-identical test green.
- Cross-package copies triaged (routed or OUT-with-rationale, documented).
- `ruff`/`mypy` clean.

## Risks / reviewer guidance
- **NFR-004**: reviewer confirms no serialized timestamp format changed (diff the test's expected strings).
- Confirm the monkeypatch-based determinism tests that patched a folded `_now_utc` still control time
  (update them to patch the canonical helper).

## Activity Log

- 2026-07-08T19:10:22Z – claude:sonnet:randy-reducer:implementer – shell_pid=4187596 – Assigned agent via action command
- 2026-07-08T19:45:43Z – claude:sonnet:randy-reducer:implementer – shell_pid=4187596 – 12 owned isoformat copies -> one canonical now_utc_iso() in src/specify_cli/core/time_utils.py (new). status/reducer.py copy was dead code (no callers), deleted outright rather than replaced. Stamp family (2 callers, %Y-%m-%dT%H:%M:%SZ) and datetime-returning family (2 callers, decisions/*, not owned) preserved untouched -- NFR-004 byte-identical. T026 SAFE fold: mission_parsing.py routes its stamp literal through task_utils.support.TIMESTAMP_FORMAT. Updated test_parity.py/test_reducer.py monkeypatches from the deleted reducer._now_utc to core.time_utils.now_utc_iso. New tests/specify_cli/test_clock_consolidation.py (9 tests, pytest.mark.fast) pins single-definition + byte-identical stamp output. FOLLOW-UP NEEDED (not done here, out of owned_files): ~18 more isoformat copies in non-owned files (sync/*, review/*, skills/command_installer.py, merge/state.py, analysis_report.py...) still need routing -- do not claim full consolidation without a tracker follow-up. T025 cross-package triage (read-only, no edits): retrospective_terminus.py is import-direction-SAFE for a future WP; glossary/events.py and charter/evidence/code_reader.py are OUT (would be new reverse package edges). ruff clean, mypy clean on all touched files (10 pre-existing no-any-return findings confirmed via git blame as predating this WP, untouched by this diff). tests/status, tests/event_journal, tests/sync/test_migrate_journal.py, tests/retrospective, tests/delivery, tests/dossier, tests/specify_cli/cli/commands/agent/test_mission_parsing.py, tests/architectural all green (827 passed/4 skipped in architectural suite).
- 2026-07-08T19:48:50Z – claude:opus:reviewer-renata:reviewer – shell_pid=206504 – Started review via action command
- 2026-07-08T19:55:16Z – user – shell_pid=206504 – Review passed. NFR-004 byte-identical VERIFIED: both stamp callers (task_utils/support.now_utc untouched; mission_parsing._utc_now_iso now routes hardcoded literal through TIMESTAMP_FORMAT='%Y-%m-%dT%H:%M:%SZ' constant, byte-identical) proved by characterization tests asserting frozen '2026-07-08T12:34:56Z'; decisions/* datetime family untouched. reducer._now_utc DELETION VERIFIED zero-caller: base-tree reducer.py defined _now_utc but never called it (materialized_at derives from sorted_events[-1].at); no cross-module import of reducer._now_utc in production. One canonical core/time_utils.now_utc_iso(); 11 owned copies import it + reducer dead-copy deleted = 12. Monkeypatches in test_parity/test_reducer retargeted to core.time_utils.now_utc_iso; 727 passed. Diff-scoped ruff exit 0; mypy 10 no-any-return all PRE-EXISTING (confirmed identical on base tree, line-shifted by the deleted def). No over-reach into ~18 non-owned copies (follow-up flagged). No --feature regression.
