---
work_package_id: WP05
title: Display prose-consumer re-point
dependencies:
- WP04
requirement_refs:
- FR-008
tracker_refs:
- '#2773'
planning_base_branch: feat/consolidate-charter-bundle
merge_target_branch: feat/consolidate-charter-bundle
branch_strategy: Planning artifacts for this mission were generated on feat/consolidate-charter-bundle. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/consolidate-charter-bundle unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_context_display_charter_md.py
execution_mode: code_change
owned_files:
- src/charter/context.py
- src/charter/compact.py
- src/charter/context_renderers/section_bodies.py
- tests/charter/test_context_display_charter_md.py
role: implementer
tags: []
shell_pid: "679243"
shell_pid_created_at: "1784390707.16"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer). Load the YAML.

## Objective
Re-point the **display-only** `charter.md`-prose consumers so `charter.md` stays a display/companion surface and NO governance DECISION reads prose. The DECISION loader-calls in `context.py` auto-follow WP04's signature-stable loaders — touch only the **prose call-sites** here (keeps ownership disjoint from WP04).

**Authoritative**: [`plan.md`](../plan.md) IC-05; empirical trace in [`research/charter-authority-inversion-assessment.md`](../research/charter-authority-inversion-assessment.md) (§prose is display-only).

## Context / grounding
- `context.py:274 _extract_policy_summary`, `:1023/2754/2784 render_critical_section_bodies`, `:341 render_critical_section_include`.
- `compact.py:59 extract_section_anchors`, `:131-138 render_compact_view`.
- `context_renderers/section_bodies.py:184/231/282`.

## Subtasks
### T021 — context.py display call-sites
- The policy-summary + critical-section-body renders continue to read `charter.md` (it still exists as the companion). Confirm/adjust so they read the companion prose and feed DISPLAY strings only — no branch/decision consumes them.
### T022 — compact.py + section_bodies.py
- Section anchors + critical-section bodies render from the companion `charter.md`. Ensure `compact.py` is included (FR-008 named context.py; compact.py is a real consumer).
### T023 — Tests
- `tests/charter/test_context_display_charter_md.py`: bootstrap/context render still includes the policy summary + critical sections; a grep-style assertion that no governance DECISION path reads charter.md content (INV-3).

## ⚠ Campsite (carla)
`context.py:971 _render_bootstrap_text` is at complexity **15** (ceiling) and sits on the edit region (`_extract_policy_summary:274`, `render_critical_section_bodies:1023`). If you add any prose-source branch here, extract a helper to stay ≤15 (C901/S3776). Consume WP01's shared `CHARTER_YAML`/`CHARTER_FILENAME` constant — do not re-scatter (context.py:76 has a dup).

## ATDD (red-first)
Red-first: assert the bootstrap text still renders the policy summary from the companion `charter.md` and that governance resolution does NOT depend on it.

## Branch Strategy
Base `feat/consolidate-charter-bundle` per `lanes.json` (dep WP04); merges back to `feat/consolidate-charter-bundle`.

## Definition of Done
- Display prose consumers render from the companion; no decision reads charter.md; ruff + mypy --strict clean; complexity ≤15; owned tests green.

## Reviewer guidance
- Verify only DISPLAY call-sites were touched (decision loader-calls untouched, auto-following WP04).
- Verify INV-3 (no governance decision reads charter.md prose).

## Activity Log

- 2026-07-18T15:41:00Z – claude:sonnet:python-pedro:implementer – shell_pid=609724 – Assigned agent via action command
- 2026-07-18T16:04:56Z – claude:sonnet:python-pedro:implementer – shell_pid=609724 – display prose consumers (context.py/compact.py) read charter.md companion + handle absence; no governance decision reads prose (INV-3). Gates foreground (orchestrator-run): ruff/mypy/C901 clean, 16 owned tests passed. test_context.py::TestBuildContextV2 fallout is WP07's. (Implementer backgrounded full sweep + stalled; finished by orchestrator.)
- 2026-07-18T16:05:10Z – claude:opus:reviewer-renata:reviewer – shell_pid=679243 – Started review via action command
- 2026-07-18T16:08:03Z – user – shell_pid=679243 – INV-3 holds: decision path (resolver.resolve_project_governance, _load_action_doctrine_bundle et al) reads no charter.md prose; new AST test pins it. Graceful absence: _compact_section_block + render_compact_view degrade to empty on missing/unreadable charter.md (NFR-005), tests cover absent/None/OSError. Only DISPLAY call-sites re-pointed to shared charter.bundle.CHARTER_MD; CHARTER_FILENAME dup retired (S1192). Gates green: ruff+C901 clean, mypy --strict clean, 16 owned tests pass. Scope: only context.py/compact.py/test file authored by WP05.
