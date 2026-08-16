---
work_package_id: WP01
title: Adopt canonical SPEC_KITTY_HOME owner in the drifting test
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
- C-004
- C-005
planning_base_branch: kitty/fix-home-pin-census-owner-adoption-3121
merge_target_branch: kitty/fix-home-pin-census-owner-adoption-3121
branch_strategy: Planning artifacts for this mission were generated on kitty/fix-home-pin-census-owner-adoption-3121. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/fix-home-pin-census-owner-adoption-3121 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-home-pin-census-owner-adoption-01M05C50
base_commit: 871db23cdf3839270a2c33fb16ff0e88bf268d69
created_at: '2026-08-16T13:37:30.096496+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Fix
history:
- timestamp: '2026-08-16T13:30:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- tests/cli/commands/test_sync_status_drain_blockers.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Adopt canonical `SPEC_KITTY_HOME` owner in the drifting test

## Objective

Green the `arch-adversarial (arch_shard_3)` census gate (#3121, C-011) by making the one
drifting test adopt the exempt canonical `SPEC_KITTY_HOME` owner instead of carrying its own
`setenv` pin — the design-sanctioned "green path" for a new home-pinning site. The census must
re-green with **zero edits to any frozen or forbidden artefact**, and the ratchet must still
bite.

## Background (why this is the correct fix)

The census is a monotone, shrink-only ratchet; "additions are not expressible." A legitimate
new pin landed in `tests/cli/commands/test_sync_status_drain_blockers.py:99` (#3497), making
`discover()` see a 41st member vs the frozen 40-member anchor. Re-freezing the anchor is inert
unless `members.json` (immutable third-party evidence) is edited — forbidden. The R1a mission's
own User Story 2 defines the sanctioned move: the new site adopts `canonical_home` and writes no
`setenv` of its own, so it leaves `discover()` and the equality re-greens.

`canonical_home` (`tests/conftest.py:372`) sets `SPEC_KITTY_HOME=<tmp_path>/home`, mkdirs it,
function-scoped — identical isolation to what the test needs (fresh per-test home ⇒ absent
layout record ⇒ LEGACY). It is the exempt owner (`E`), so it adds no census row.

## Subtasks

### T001 — Refactor the test to adopt the owner
File: `tests/cli/commands/test_sync_status_drain_blockers.py`, function
`test_queue_get_drain_blocked_counts_persists_through_drain_round_trip`.
- Change the signature to request the fixture: `def test_...(canonical_home: None) -> None:`
  (drop `tmp_path` and `monkeypatch` — they become unused).
- Delete the line `monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))`.
- Add as the first body line: `del canonical_home  # the ONE SPEC_KITTY_HOME owner (R1a #3121) pins the home`.
- Update the docstring: isolation is now provided by the canonical owner (keep the rationale
  about the whole-home-scoped layout record and the fresh LEGACY start).
- Do NOT change the test's assertions or its `begin_cutover`/`publish_project_only`/queue flow.

### T002 — Verify acceptance
- `PWHEADLESS=1 pytest tests/architectural/test_spec_kitty_home_pin_census.py -q` → 0 failures.
- `PWHEADLESS=1 pytest tests/cli/commands/test_sync_status_drain_blockers.py -q` → 0 failures.
- `ruff check tests/cli/commands/test_sync_status_drain_blockers.py` → clean.
- `mypy tests/cli/commands/test_sync_status_drain_blockers.py` → clean.
- `git status --porcelain` → only that one file; `git status --porcelain tests/architectural/`
  → empty (no census/anchor/baseline diff).

### T003 — Ratchet-bite proof (mandatory, NFR-001)
- Create a throwaway test with `monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))`.
- Run the census suite → it MUST go RED.
- Delete the throwaway test → the census suite returns GREEN.

## Guardrails (binding)

- **C-001**: never edit `members.json`, the anchor yaml, `_home_pin_exempt.py`, census
  `R1a.yaml`, or the baseline to green a test.
- **C-002**: do not weaken the census tests (t022–t026); equalities stay set-equalities.
- **C-003**: `E` stays `tuple[Exempt, Exempt]` (arity 2); `mypy --strict` clean.
- **C-004**: no scanner narrowing and no `resolve_value` evasion (do not hide the pin — remove it).
- **C-005**: no production/behaviour change (`sync/layout_generation.py` untouched).

## Definition of Done

- SC-001..SC-006 in `spec.md` all met.
- Diff confined to `tests/cli/commands/test_sync_status_drain_blockers.py`.
- `arch-adversarial (arch_shard_3)` green on CI for the PR.
