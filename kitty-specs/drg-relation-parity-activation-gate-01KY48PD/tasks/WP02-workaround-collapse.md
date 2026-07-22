---
work_package_id: WP02
title: Workaround collapse (tension-scan + parity gate)
dependencies:
- WP01
requirement_refs:
- C-001
- FR-003
- NFR-002
planning_base_branch: doctrine/drg-completeness-2843
merge_target_branch: doctrine/drg-completeness-2843
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-completeness-2843. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-completeness-2843 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
history:
- timestamp: '2026-07-22T08:11:16Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/consistency_check.py
create_intent:
- tests/charter/test_check_graph_kind_parity.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/consistency_check.py
- tests/charter/test_check_graph_kind_parity.py
- tests/architectural/_baselines.yaml
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/test_no_dead_modules.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `python-pedro` implementer profile via the
`/ad-hoc-profile-load` skill. Adopt its identity, boundaries, and init declaration. TDD-first,
type-safe Python 3.11+, complexity ≤15, zero suppressions.

## Objective

Now that WP01 made the gate correct, remove the two genuine workarounds so stem→canonical resolution
lives in exactly ONE place (SC-003). Delete the tension-scan reimplementation (it becomes a plain
consumer of the gate) and re-point `_check_graph_kind_parity` from KIND-granular to per-ID (an
intended **behavior upgrade**, owned with tests). Delete the constant orphaned by both.

Read: `research.md` (D2), `plan.md` IC-02. **Do NOT touch** `charter/compiler.py`'s `references.yaml`
projection (C-001 — it is independent-correct, a catalog projection not a graph filter).

## Subtasks

### T006 — Delete the tension-scan trio (WP02)

**Steps**: delete `_node_is_tension_scan_active` / `_build_tension_active_urns` /
`_resolve_activated_urns_for_kind` (`consistency_check.py:874-956`) and re-point the tension
consistency check to consume `filter_graph_by_activation` (as `_check_drg_cross_kind_refs` already
does at `:424`). Remove now-dead imports.
**Validation**: tension-consistency verdicts are **unchanged** vs merge-base. Do NOT prove this with a
self-fulfilling snapshot of the new run — either (a) commit a golden captured on the **merge-base** with
the merge-base sha + a recorded regeneration command in the fixture header, or (b) assert a
**discriminating property** derived independently (a specific tension edge/verdict the real corpus
produces), not `assert new_run == <hand-typed literal>`.

### T007 — Re-point `_check_graph_kind_parity` KIND→per-ID (WP02)

**Steps**: `_check_graph_kind_parity` (`:776`) is intentionally KIND-granular today (docstring
`:785-803`, which explicitly states it "deliberately does NOT use `filter_graph_by_activation` … that
helper's per-ID gate is unsuitable" — now false). Re-point it to per-ID by consuming the corrected
gate, and **rewrite that docstring** (`:783-812`) to the new per-ID behavior. This is a **behavior
upgrade** — own it with tests in `tests/charter/test_check_graph_kind_parity.py` asserting the new
per-ID verdicts. Preserve its fail-closed-**report** contract (`:811-812`), but tighten the tests so
"never crashes" cannot be faked with a broad `except`:
- Resolution errors are caught **narrowly** (`except UnknownArtifactIdError`), NOT `except Exception`.
- A test asserts an **unknown stem** yields a **specific** `verification_errors` entry that **names the
  unresolvable id** (not merely "an entry was appended" / "no exception raised").
- A guard test asserts a genuine non-drift error (e.g. a programming bug) is **NOT** silently converted
  into a drift `verification_errors` entry.
**Validation**: new per-ID tests green; unknown-stem names the id; non-drift errors are not swallowed.

### T008 — Delete the orphaned constant + fix baselines (WP02)

**Steps**: after T006/T007, `_DRG_SINGULAR_TO_ACTIVATED_KINDS_MEMBER` (`consistency_check.py:124`) has
no remaining uses (its only uses were `:835` in the re-pointed parity check and `:920` in the deleted
trio) → delete it. Confirm no other orphan (neighbors `_DRG_SINGULAR_TO_CLI_KIND` `:457/:466`,
`_CLI_KIND_TO_DRG_SINGULAR` `:126`, `resolve_doctrine_root` import `:683` survive). Re-run the
dead-symbol / dead-module gates and update `_baselines.yaml` counts + `test_no_dead_symbols.py` /
`test_no_dead_modules.py` entries for any symbol/module the deletions retire (follow the campsite
pattern: the gate tells you the exact new count; add a `# justification:` line).
**Validation**: `uv run pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_dead_modules.py tests/architectural/test_ratchet_baselines.py -q` green; then the WP gates:
`uv run ruff check src/charter/consistency_check.py tests/charter/test_check_graph_kind_parity.py` and
`uv run python -m mypy --strict src/charter` clean (complexity ≤15).

## Branch Strategy

Generated on **`doctrine/drg-completeness-2843`**; merges back into it. Worktrees per lane from
`lanes.json`. Depends on WP01 (implement after it lands).

## Definition of Done

- [ ] Tension-scan trio deleted; tension consistency consumes the one gate; verdicts unchanged.
- [ ] `_check_graph_kind_parity` per-ID with own tests; still fail-closed-report (no raise).
- [ ] Orphaned constant deleted; dead-symbol/module + ratchet baselines green.
- [ ] `references.yaml` projection untouched (C-001); ruff + mypy --strict clean; complexity ≤15.

## Risks

- The parity re-point is the one place "collapse" becomes new behavior — it must be test-owned and
  stay non-crashing. Deleting the trio without re-pointing the tension consumer leaves a dangling call.

## Reviewer Guidance (reviewer-renata / opus)

Confirm one stem→canonical seam remains (grep `resolve_artifact_urn`); the tension-verdict test is a
merge-base golden or a discriminating property (NOT a snapshot of the new run); `_check_graph_kind_parity`
catches **narrowly** (`except UnknownArtifactIdError`, never broad `except Exception`) and its
unknown-stem test **names the unresolvable id**; the stale docstring is rewritten; the compiler
projection is untouched; baseline bumps carry justifications.
