---
work_package_id: WP05
title: accept --json surfaces the SC-008 stranded-verdict advisory
dependencies: []
requirement_refs:
- FR-011
planning_base_branch: hardening/verdict-seam-facade-followup
merge_target_branch: hardening/verdict-seam-facade-followup
branch_strategy: Planning artifacts for this mission were generated on hardening/verdict-seam-facade-followup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into hardening/verdict-seam-facade-followup unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verdict-seam-boundary-hardening-01KZG179
base_commit: 56a9abd9a337e2a09716927be1ba27112fe36d5a
created_at: '2026-08-08T11:23:29.329505+00:00'
subtasks:
- T020
- T021
- T022
phase: Phase 2 - Parallel hardening
history:
- at: '2026-08-08T09:55:00Z'
  actor: system
  action: Prompt generated from plan.md IC-04
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/accept.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/accept.py
- tests/specify_cli/cli/commands/test_accept_stranded_verdict_note.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3255'
---

# Work Package Prompt: WP05 – accept --json advisories

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` and behave per its guidance before parsing the rest of this prompt.

## Goal

`spec-kitty accept --json` drops the SC-008 stranded-verdict backfill advisory because it is gated behind `if not json_output:`. Surface it in the JSON payload as a uniform top-level `advisories` array so automation sees the "run `spec-kitty upgrade`" hint. **Advisory-only; independent parallel lane.**

## Subtasks

### T020 — Lift the advisory out of the gate; inject `advisories[]` at the emit layer
In `cli/commands/accept.py`:
- Compute `provenance_note = _stranded_verdict_provenance_note(resolved.feature_dir)` **unconditionally** (lift it out of the `if not json_output:` block ~L673-677; keep the human-facing `console.print` inside the non-JSON branch).
- Add a small CLI-layer helper, e.g. `_with_advisories(payload: dict, notes: list[str]) -> dict`, and wrap each `json.dumps(...)` at the **four non-error** emit sites (~L751 diagnose, L763 checklist, L773 not-ok, L879 success) so every emitted payload carries a top-level `"advisories": [...]` (empty list in the converged/steady state).
- **Do NOT touch the ~8 ERROR `json.dumps` sites** (`accept.py` ~L644, 663, 712, 721, 738, 824, 861, 868) — a skim for `json.dumps` hits ~12 sites; only the four non-error result payloads carry `advisories[]`. Error payloads stay as-is.
- **C-005:** keep this entirely in the CLI layer — do **not** thread the advisory into `AcceptanceSummary`/`AcceptanceResult` (the acceptance domain model).

### T021 — Campsite: fix the effect-free except (S110)
`_safe_emit_error_logged` (~L44-51) has `except Exception:` / `pass` (confirmed S110). While here, bring it in line with the sibling handler (~L72): `logger.debug(...)` + a `# noqa: BLE001` with a one-line rationale, instead of a bare `pass`.

### T022 — Tests
In `tests/specify_cli/cli/commands/test_accept_stranded_verdict_note.py` (reuse the existing `_write_stranded_mission` fixture):
- stranded mission → `accept(..., json_output=True)` payload contains the SC-008 advisory string in the top-level `advisories` array.
- converged mission → `advisories` present and empty (`[]`).

## Branch Strategy
Independent parallel lane off `hardening/verdict-seam-facade-followup`; merges back to same.

## Definition of Done
- `advisories: list[str]` present on all four non-error `accept --json` payloads; carries the SC-008 advisory when stranded, empty when converged.
- No coupling into the acceptance domain model (C-005).
- S110 campsite fixed. `ruff`/`mypy` clean, zero new suppressions.
- New tests green; existing `test_accept_stranded_verdict_note.py` green.

## Reviewer Guidance
Confirm the advisory is injected uniformly at all four emit sites (not just one), that the domain model is untouched, and that the converged case yields `[]` (present, not absent). Confirm the S110 fix logs at debug with a rationale.

## Risks
- Missing one of the four emit sites → inconsistent JSON surface; enumerate them explicitly.
- Accidentally threading the note into `AcceptanceSummary.warnings` (drags scope + couples a migration concern into the domain model) — keep it CLI-layer.
