# Research: Live enforcement surface for the occurrence-map gate (resolves spec C-005)

**Question**: At the plan-completion / pre-implement boundary, which enforcement surface does the *live* runtime actually evaluate, so the gate reusing `ensure_occurrence_classification_ready` fires before `implement`?

Investigated read-only against the live checkout (branch `feat/bind-occurrence-map-guard-finalize`).

## Findings

### F1 — `mission.yaml` transition `conditions` are a DEAD surface (Option A rejected)
- `plan → implement` declares `conditions: ['artifact_exists("plan.md")', 'artifact_exists("tasks.md")']` — `src/doctrine/missions/software-dev/mission.yaml:42-46` (mirror `src/specify_cli/missions/software-dev/mission.yaml:45-46`).
- The only interpreter of those strings is `evaluate_guards()` — `src/runtime/next/decision.py:204-266` — documented dead: *"Legacy functions `derive_mission_state` and `evaluate_guards` ... are no longer called by `decide_next`"* (`decision.py:14-16`).
- Live `decide_next` (`decision.py:407-429`) → `runtime_bridge.decide_next_via_runtime` (`runtime_bridge.py:2514`), which enforces boundaries with hand-rolled per-step guards, not mission.yaml conditions.

### F2 — `mission_v1` guard machinery has no live consumer
- `compile_guards` / `GUARD_REGISTRY` (`src/specify_cli/mission_v1/guards.py:270-378`) consumed only inside `mission_v1/__init__.py:104`. Non-test imports of `mission_v1` in `src/` pull only `.events` and `.schema` — never `.guards` / `.runner`.
- The registered `occurrence_map_complete` guard (`guards.py:245-277`, wrapping `ensure_occurrence_classification_ready` at `:258-260`) is **registered-but-dead**. Confirms the post-spec adversarial finding.

### F3 — `finalize-tasks` is the correct command surface (Option B)
- `spec-kitty agent mission finalize-tasks` → `finalize_tasks()` at `src/specify_cli/cli/commands/agent/mission_finalize.py:1520+` (registered `mission.py:277,326`).
- Linear validation pipeline over `planning_dir` (SaaS preflight, requirement-mapping `:1621-1628`, dependency graph `:1617`, conflicts `:1630`, ownership `:1664`), each raising `typer.Exit(1)`. No occurrence-map gate today.
- Runs after `/spec-kitty.tasks`, before any `implement` — correct timing. `--validate-only` mode (`:1523-1525,1673`) is designed to surface finalization blockers; a call placed before the `if validate_only:` split fires in both modes.

### F4 — Existing live call sites of `ensure_occurrence_classification_ready` (backstop)
- Definition `src/specify_cli/bulk_edit/gate.py:49-96` → `GateResult(passed, change_mode, errors, warnings)`; internally `load_meta` → early-pass if not `bulk_edit` (`:54-60`) → presence (`:63-72`) → schema `validate_occurrence_map` (`:74-81`) → `check_admissibility` (`:83-90`). Renderer `render_gate_failure` (`:99-107`).
- Call sites (both fire later than finalize — the status quo this mission improves on): the **implement-time preflight** `implement.py:1239-1244` (inside `implement()`), and the **review-workflow gate** `agent/workflow.py:2365-2371` (inside `review()`, labelled FR-006 — fires at review, not implement). Each passes a single `feature_dir` and exits 1 via `render_gate_failure`. Both remain unchanged (FR-004 backstop).

### F5 — `change_mode` is read from `meta.json`
- `ensure_occurrence_classification_ready` calls `load_meta(feature_dir)` then `meta.get("change_mode")` (`gate.py:17,54-59`). Self-conditioning — caller only supplies the correct `feature_dir` (= `planning_dir` in finalize).

### F6 — Admissibility is a distinct rejection axis
- `check_admissibility` (`occurrence_map.py:377-399`) rejects placeholder terms and `< MIN_ADMISSIBLE_CATEGORIES = 3` (`occurrence_map.py:107`). "Valid" ⇒ schema-valid **and** admissible.

### F7 — The live `next`-loop bypasses the finalize command
- The `next`-loop's live pre-implement guards are `_check_composed_action_guard` (`action == "tasks"`, `runtime_bridge.py:1622-1637`) and `_check_cli_guards` (`runtime_bridge.py:1091-1108`). A `next`-driven mission that never invokes `finalize-tasks` would only hit the bad-map block at implement-time. → motivates IC-02 (non-vacuousness).

## Decision
Reuse `ensure_occurrence_classification_ready` at **both** live pre-implement surfaces: the `finalize-tasks` command (IC-01) and the `next`-loop tasks-finalize guard (IC-02, via one shared helper called from both enumerators). No new validation logic; no touching the dead `mission.yaml` / `mission_v1` surfaces. The existing implement-time and review-time gates remain as backstops (FR-004).

## Test seams
- Gate logic already covered: `tests/specify_cli/bulk_edit/test_gate.py` (missing / schema-invalid / `<3` categories / pass).
- New finalize integration: `tests/tasks/test_finalize_tasks_occurrence_gate.py` (bulk_edit × {missing, schema-invalid, inadmissible, valid} + non-bulk pass + `--validate-only` blocks).
- `next`-loop guard tests under `tests/next/`.
- Read-only invariant regression: `tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py` must still pass.
