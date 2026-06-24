---
work_package_id: WP04
title: _identity_audit extraction + identity CC19 decompose
dependencies:
- WP03
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: prog/2059-doctor
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T010
- T011
- T012
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3166836"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_identity_audit.py
create_intent:
- src/specify_cli/cli/commands/_identity_audit.py
- tests/specify_cli/cli/commands/test_identity_audit.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_identity_audit.py
- tests/specify_cli/cli/commands/test_identity_audit.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Extract the identity + topology cluster (D) into `_identity_audit.py` and **decompose the `identity` command (CC19)** into ≤15-CC tested helpers as part of the move — not relocated oversized.

## Context

- Cluster D (research §2): `_scope_to_mission` (1068), `_scope_prefixes` (1085), `_print_dup_and_ambig` (1099), `_print_identity_human` (1125), `identity` cmd (1172, CC19), `_read_stored_topology` (1276), `_collect_topology_rows` (1300), `_print_topology_human` (1315), `topology` cmd (1330).
- The `identity` command's branchiness (CC19) comes from `--mission` scoping, `--fail-on` gating, dup/ambig rendering, and `--json` vs human output. Extract render/scope/gate sub-helpers (each ≤15 CC) and test them directly (Sonar new-code-coverage).

## Subtasks

### T010 — Create `_identity_audit.py` + decompose `identity`
- Move Cluster D helpers + bodies into `_identity_audit.py`, importing shared infra from `_doctor_shared`. Split `identity` into ≤15-CC helpers (e.g. `_resolve_identity_scope`, `_emit_identity_json`, `_emit_identity_human`, `_apply_fail_on_gate`).
- `ruff check --select C901` on `_identity_audit.py` → zero findings.

### T011 — Delegate + re-export
- `identity` and `topology` command bodies in `doctor.py` become thin shells delegating to `_identity_audit` entrypoints, preserving every `raise typer.Exit(code)` and the `--fail-on` semantics.
- Re-export any identity/topology private symbols the doctor test files import (grep to confirm).

### T012 — Focused tests
- `test_identity_audit.py`: per-helper tests for scope resolution, dup/ambig rendering, `--fail-on` gating, topology row collection. ≥90% coverage; cover each decomposed branch.
- WP01 golden green.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED per-helper tests (especially the decomposed `identity` branches) before extraction; GREEN after. Golden stays green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — delegate `identity`/`topology` bodies + re-export. Owned by WP11; sequential chain → no concurrent writer.

## Definition of Done

- Cluster D in `_identity_audit.py`; `identity` decomposed to ≤15-CC helpers (C901 clean).
- `identity`/`topology` exit + `--fail-on` semantics byte-preserved (golden green).
- `_identity_audit` ≥90% covered; ruff + mypy --strict clean, zero new suppressions.

## Risks

- Decomposition must preserve the `--fail-on`-triggered exit-1 vs not-found exit-1 distinction.
- Relocating `identity` at CC19 (without decomposition) fails the complexity gate.

## Reviewer Guidance

Recommended reviewer: standard. Verify `identity` is decomposed (C901 clean), exit/`--fail-on` semantics unchanged, ≥90% per-helper coverage, golden green.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP03; decompose identity CC19).
- 2026-06-24T20:56:40Z – claude:opus:randy-reducer:implementer – shell_pid=3109154 – Assigned agent via action command
- 2026-06-24T21:10:55Z – claude:opus:randy-reducer:implementer – shell_pid=3109154 – identity decomposed to <=15CC; _identity_audit 99% cov; golden+existing tests green; ruff/mypy clean
- 2026-06-24T21:10:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=3166836 – Started review via action command
- 2026-06-24T21:11:11Z – user – shell_pid=3166836 – Cluster D in _identity_audit; identity decomposed to <=15CC helpers (C901 clean); exit/--fail-on semantics byte-preserved (golden + existing test_doctor_topology/test_identity_audit green); repo_root injected from doctor shell preserves monkeypatch seam; one-way imports (AST-verified); 99% coverage; mypy --strict clean
