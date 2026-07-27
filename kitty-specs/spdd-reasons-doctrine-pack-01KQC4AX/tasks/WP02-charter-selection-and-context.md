---
work_package_id: WP02
title: Charter Selection and Context Injection (SPDD/REASONS)
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-002
- C-001
- C-002
planning_base_branch: doctrine/spdd-reasons-pack
merge_target_branch: doctrine/spdd-reasons-pack
branch_strategy: Planning artifacts for this feature were generated on doctrine/spdd-reasons-pack. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/spdd-reasons-pack unless the human explicitly redirects the landing branch.
created_at: '2026-04-29T08:15:46Z'
subtasks:
- T008
- T009
- T010
- T011
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "35072"
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: python-pedro
authoritative_surface: src/doctrine/spdd_reasons/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- src/doctrine/spdd_reasons/__init__.py
- src/doctrine/spdd_reasons/activation.py
- src/doctrine/spdd_reasons/charter_context.py
- src/charter/context.py
- src/charter/bundle.py
- src/charter/synthesizer/targets.py
- tests/charter/test_charter_context_spdd_reasons.py
- tests/charter/__init__.py
- tests/charter/fixtures/spdd_inactive/.gitkeep
- tests/charter/fixtures/spdd_active/.gitkeep
role: implementer
tags:
- charter
- activation
---

## ⚡ Do This First: Load Agent Profile

- Run `/ad-hoc-profile-load` with profile `python-pedro` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/shipped/python-pedro.agent.yaml`.
- After load, restate identity, governance scope, and boundaries before continuing.

# WP02 — Charter Selection and Context Injection (SPDD/REASONS)

## Branch Strategy

- **Planning base branch**: `doctrine/spdd-reasons-pack`
- **Merge target**: `doctrine/spdd-reasons-pack`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP02 --agent claude --mission spdd-reasons-doctrine-pack-01KQC4AX`. Do not guess the worktree path.

## Objective

Wire the SPDD/REASONS pack into Spec Kitty's charter activation pipeline. This WP delivers two things:

1. The `is_spdd_reasons_active(repo_root)` helper — the single source of truth for "is the pack active for this project".
2. Charter-context injection that emits "SPDD/REASONS Guidance (action: `<action>`)" only when the pack is active. When inactive, charter context output is byte-identical to the pre-feature output.

Charter selection of the new paradigm/tactics/directive must flow through to `governance.yaml` (and friends) via existing synthesizer plumbing.

## Context

### Spec references
- FR-007, FR-008, FR-009, NFR-001, NFR-002, C-001, C-002.
- [contracts/activation.md](../contracts/activation.md) — `is_spdd_reasons_active()` contract.
- [contracts/charter-context.md](../contracts/charter-context.md) — charter-context injection contract.

### Code seams (verified)
- `src/charter/context.py:build_charter_context()` line 69 — public entry.
- `src/charter/context.py:_load_action_doctrine_bundle()` lines 213–249 — DRG resolution.
- `src/charter/context.py:_render_action_scoped()` lines 507–555 — composes "Action Doctrine" output.
- `src/charter/context.py:_append_action_doctrine_lines()` line 537 — directive/tactic line emission. Inject the SPDD/REASONS subsection right after this call.
- `src/charter/bundle.py` lines 33–42 — writes governance.yaml, directives.yaml, metadata.yaml, synthesis-manifest.yaml.
- `src/charter/synthesizer/targets.py` lines 1–80 — `SynthesisTarget` construction; kind ordering; artifact filename suffixes.
- `src/charter/synthesizer/write_pipeline.py` lines 1–28 — atomic write pipeline.

### Action scoping (from spec FR-009)
| Action | Canvas content surfaced in charter-context guidance |
|---|---|
| specify | Requirements, Entities |
| plan | Approach, Structure |
| tasks | Operations, WP boundaries |
| implement | Full WP-level canvas (R, E, A, S, O, N, S) |
| review | Comparison surface (R, O, N, S) |

## Subtasks

### T008 — Implement `is_spdd_reasons_active(repo_root)` helper

**New module**: `src/doctrine/spdd_reasons/__init__.py` and `src/doctrine/spdd_reasons/activation.py`.

Public surface:

```python
from pathlib import Path

def is_spdd_reasons_active(repo_root: Path) -> bool:
    """True iff the project's charter selection includes any one of:
       paradigm structured-prompt-driven-development, tactic reasons-canvas-fill,
       tactic reasons-canvas-review, or directive DIRECTIVE_038."""
```

Implementation rules (per `contracts/activation.md`):
- Read `.kittify/charter/governance.yaml` and/or `.kittify/charter/directives.yaml` via existing charter loaders. Look at how `src/charter/context.py` reads these files; reuse the same loader.
- Returns `False` if `.kittify/charter/` is absent (no error).
- Propagates loader exceptions on malformed YAML.
- May cache per-process for the lifetime of one CLI invocation. MUST NOT persist across invocations.

Write unit tests in `tests/charter/test_charter_context_spdd_reasons.py::TestActivation` covering all 7 cases in `contracts/activation.md`.

### T009 — Extend `build_charter_context()` to inject SPDD/REASONS guidance

**Edit**: `src/charter/context.py` (only at the seam — keep changes minimal).

Add:

```python
# top of file
from doctrine.spdd_reasons import is_spdd_reasons_active
from doctrine.spdd_reasons.charter_context import append_spdd_reasons_guidance
```

Then inside `_render_action_scoped()`, immediately after the existing `_append_action_doctrine_lines(...)` call (line 537 region), add a single conditional call:

```python
if is_spdd_reasons_active(self.repo_root):
    append_spdd_reasons_guidance(lines, mission, action)
```

Implementation lives in a new helper file (do not bloat `context.py`):

**New file**: `src/doctrine/spdd_reasons/charter_context.py`

```python
def append_spdd_reasons_guidance(lines: list[str], mission: str, action: str) -> None:
    """Append the SPDD/REASONS Guidance subsection for the given action.

    Idempotent and side-effect-free other than appending to `lines`. Action scoping
    follows FR-009 / contracts/charter-context.md.
    """
```

Subsection format (rendered):

```
SPDD/REASONS Guidance (action: <action>):
  - <bulleted action-scoped guidance — e.g., "Capture Requirements and Entities" for specify>
  - Reference: kitty-specs/<mission>/reasons-canvas.md (when present)
```

For each action emit 3–6 short bullets. Action-scoped content per the FR-009 table.

### T010 — Verify `bundle.py` / `targets.py` paradigm flow

**Goal**: When a project's charter selects `structured-prompt-driven-development` (paradigm), it must appear in `.kittify/charter/governance.yaml` (or wherever paradigms are recorded) so that `is_spdd_reasons_active()` can detect it.

Steps:
1. Read `src/charter/synthesizer/targets.py` lines 1–80. Identify the kind set it supports. If `paradigm` is already a first-class kind, no change is required.
2. If paradigm is missing, add minimal target plumbing — only enough to round-trip selection through synthesis. Do NOT change kind ordering for existing kinds. Do NOT introduce new schemas.
3. Read `src/charter/bundle.py` lines 33–42. Ensure paradigms are written to one of the four output files; if not, add to `governance.yaml` (most natural location).
4. If a charter test suite exists for synthesis (search `tests/charter/test_synthesizer*.py`), add a single round-trip test asserting paradigm selection survives.

Document any divergence from the plan in WP02 completion notes.

### T011 — Add `tests/charter/test_charter_context_spdd_reasons.py`

**Path**: `tests/charter/test_charter_context_spdd_reasons.py`

Test classes:

```python
class TestActivation:
    # 7 cases from contracts/activation.md
    def test_no_charter_returns_false(self, tmp_path): ...
    def test_unrelated_directives_returns_false(self, tmp_path): ...
    def test_paradigm_selected_returns_true(self, tmp_path): ...
    def test_only_tactic_fill_returns_true(self, tmp_path): ...
    def test_only_tactic_review_returns_true(self, tmp_path): ...
    def test_only_directive_038_returns_true(self, tmp_path): ...
    def test_malformed_governance_raises(self, tmp_path): ...

class TestCharterContextInactive:
    # NFR-001 enforcement: byte-identical baseline
    def test_inactive_specify_action_baseline_unchanged(self, tmp_path): ...
    def test_inactive_plan_action_baseline_unchanged(self, tmp_path): ...
    # ... and so on for tasks, implement, review

class TestCharterContextActive:
    # Active fixture: assert SPDD/REASONS Guidance subsection present
    def test_active_specify_contains_requirements_entities_guidance(self, tmp_path): ...
    def test_active_plan_contains_approach_structure_guidance(self, tmp_path): ...
    def test_active_implement_contains_full_canvas_reference(self, tmp_path): ...
    def test_active_review_contains_comparison_surface_reference(self, tmp_path): ...
    def test_active_tasks_contains_operations_wp_boundary_guidance(self, tmp_path): ...
    def test_performance_under_2s_active(self, tmp_path): ...  # NFR-002
```

Use small fixtures under `tests/charter/fixtures/spdd_inactive/` and `tests/charter/fixtures/spdd_active/`. Each fixture is a minimal `.kittify/charter/` directory.

For inactive baselines: capture the current output once, write it to a `*.expected.txt` file, and compare bytes (or normalized lines) on subsequent runs. Run the inactive test suite BEFORE making any context.py changes to lock the baseline; then add the changes.

## Definition of Done

- `is_spdd_reasons_active()` exists, is unit-tested for all seven cases, and is the only place that decides activation.
- `_render_action_scoped()` calls `append_spdd_reasons_guidance()` when active, never when inactive.
- Inactive `charter context --action <action> --json` output is byte-or-semantic identical to the captured baseline for all five actions.
- Active output contains the action-scoped REASONS subsection with the expected headlines.
- `bundle.py` / `targets.py` paradigm flow verified or minimally patched without schema change.
- `uv run pytest tests/charter -q` passes.
- `uv run pytest tests/doctrine -q` continues to pass.
- `uv run mypy --strict src/doctrine src/charter` clean.

## Reviewer guidance

- Confirm `is_spdd_reasons_active()` lives in `src/doctrine/spdd_reasons/activation.py` and has no other side effects.
- Confirm the only edits to `src/charter/context.py` are the import + single conditional call.
- Confirm inactive output is byte-identical to baseline. If a single newline differs, investigate.
- Confirm activation detection works for ANY of the four selectors (paradigm OR tactic OR tactic OR directive), per spec FR-009.

## Risks

- **Loader leakage**: If you import from `charter` into `doctrine.spdd_reasons.activation`, you can create an import cycle. Use the smallest necessary loader. If needed, copy a tiny YAML-loading helper rather than importing from `charter`.
- **Baseline capture**: If you capture the inactive baseline AFTER making changes, NFR-001 cannot be proven. Always capture first, then change.
- **Performance**: `is_spdd_reasons_active()` is called on every charter-context render. Cache per-invocation but never across invocations.

## Out of scope

- Prompt fragment rendering (WP04).
- Review-gate behavior (WP05).
- User-facing docs (WP06).

## Activity Log

- 2026-04-29T08:35:13Z – claude:opus:python-pedro:implementer – shell_pid=18693 – Started implementation via action command
- 2026-04-29T08:46:36Z – claude:opus:python-pedro:implementer – shell_pid=18693 – Ready for review: activation helper + charter-context injection + 3 test classes
- 2026-04-29T08:46:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=35072 – Started review via action command
- 2026-04-29T08:49:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=35072 – Review passed: activation helper covers all 4 selectors; charter-context inactive byte-clean; active emits action-scoped guidance; perf budget asserted; no schema/existing-artifact changes; all tests green.
