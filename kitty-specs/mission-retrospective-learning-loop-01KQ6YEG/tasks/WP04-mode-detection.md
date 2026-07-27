---
work_package_id: WP04
title: Mode Detection
dependencies:
- WP02
requirement_refs:
- C-013
- FR-016
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
agent: "claude:opus:reviewer:reviewer"
shell_pid: "98894"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/retrospective/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/specify_cli/retrospective/mode.py
- tests/retrospective/test_mode_detection.py
priority: P1
status: planned
tags: []
---

# WP04 — Mode Detection

## Objective

Implement `mode.detect()` that resolves the active mission mode (`autonomous` | `human_in_command`) through the strict precedence: **charter override > explicit flag > environment > parent process**. The selected mode and its source signal must both be returned.

## Spec coverage

- **FR-016** mode detection precedence; selected mode and source signal recorded.
- **C-013** charter override is sovereign in any conflict.
- Supporting work for **FR-011..FR-015** (gate consumes `Mode`).

## Context

Source-of-truth shapes are in [`../data-model.md`](../data-model.md) (`Mode`, `ModeSourceSignal`) and [`../research.md`](../research.md) R-001 (precedence rationale + parent-process heuristic).

The charter loader already exists in the codebase (look for `spec_kitty charter context` flow). This WP must integrate with it, not reimplement charter parsing.

## Subtasks

### T015 [P] — `Mode` + `ModeSourceSignal` Pydantic models

The `Mode` and `ModeSourceSignal` types are referenced from WP02's `RetrospectiveRecord` and from WP03's event payloads. Coordinate with WP02 to keep the canonical home in `specify_cli/retrospective/schema.py` if WP02 already placed them there; otherwise place them in `mode.py` and have WP02 import. **Default**: place in `schema.py` (WP02), have `mode.py` import.

If models already in WP02: this subtask is just import wiring; spend the bulk of effort on T016–T019.

### T016 — `mode.detect()` precedence implementation

```python
def detect(
    *,
    repo_root: Path,
    explicit_flag: Literal["autonomous", "human_in_command"] | None = None,
    env: Mapping[str, str] | None = None,
    parent_process_name: str | None = None,
) -> Mode:
    """Resolve mode with precedence: charter > flag > env > parent."""
```

Implementation:

1. **Charter override**: load charter via the existing charter context API. If the charter declares a mode policy that produces a definite value, return it with `source_signal.kind="charter_override"` and `evidence` set to the charter clause id.
2. **Explicit flag**: if `explicit_flag` is non-None, return that value with `source_signal.kind="explicit_flag"` and `evidence=str(explicit_flag)`.
3. **Environment**: read `SPEC_KITTY_MODE` from `env` (or `os.environ` if `env is None`). Allowed values: `autonomous`, `human_in_command`. Anything else: skip to next layer.
4. **Parent process**: inspect via `psutil.Process(os.getppid()).name()` (with a fallback when psutil is unavailable). If the name is in the conservative non-interactive list, return `autonomous`. Else default to `human_in_command`.

The function MUST NOT raise on missing charter — that's just "no signal here, fall through."

### T017 — Charter-override loader integration

Wire to the existing charter context loader. Required behavior:

- Charter exists and has no mode declaration → no signal; fall through.
- Charter exists and declares `mode: autonomous` (with optional clauses) → return autonomous.
- Charter exists and declares `mode: human_in_command` → return HiC.
- Charter exists but is malformed → raise `ModeResolutionError` (structured error, not silent fall-through).

The charter clause ids are recorded in `Mode.source_signal.evidence` so the gate (WP05) can later check whether a clause permits operator-skip.

### T018 — Parent-process heuristic with conservative non-interactive list

Maintain a small constant list of recognized non-interactive parent names (CI runners, agent harnesses, cron). Conservative: when in doubt → HiC. Examples (verify against actual process names on macOS/Linux):

```python
NON_INTERACTIVE_PARENTS: frozenset[str] = frozenset({
    "github-actions",
    "gitlab-runner",
    "cron",
    "launchd",
    "systemd",
    # add CI/agent harnesses as discovered
})
```

If `psutil` is not importable in the runtime environment, treat parent-process layer as "no signal" rather than crashing.

### T019 — Tests: each precedence layer + ambiguous resolution + audit recording

In `tests/retrospective/test_mode_detection.py`:

- Charter declares autonomous, flag says HiC → result is autonomous, source is `charter_override`.
- Charter is silent, flag is autonomous → result is autonomous, source is `explicit_flag`.
- Charter is silent, no flag, env is `human_in_command` → result is HiC, source is `environment`.
- Charter silent, no flag, no env, parent process is `cron` → result is autonomous, source is `parent_process`.
- All signals absent → result is HiC (conservative default), source is `parent_process` with evidence "default-no-signal" (or similar; document the chosen evidence string).
- Charter malformed → raises `ModeResolutionError`.

Test the audit-recording aspect: every detected `Mode` carries a non-None `source_signal` with non-empty `evidence`.

## Definition of Done

- [ ] `mode.detect()` honors precedence in all paths.
- [ ] Charter integration uses the existing loader (no duplicate parser).
- [ ] Parent-process layer survives missing psutil gracefully.
- [ ] Tests cover all precedence rows.
- [ ] `mypy --strict` passes.
- [ ] Coverage ≥ 90%.
- [ ] No changes outside `owned_files`.

## Risks

- **Charter loader API drift**: read the existing charter context flow before implementing; do not assume API shape.
- **psutil cross-platform**: parent-process names differ between macOS and Linux. Document the heuristic's behavior on both.

## Reviewer guidance

- Confirm the precedence order is `charter > flag > env > parent` in code (read the function top-down).
- Confirm test for "all signals absent" produces a deterministic default (HiC) — not an error.
- Confirm `ModeResolutionError` is a typed exception (not a generic `Exception`).

## Implementation command

```bash
spec-kitty agent action implement WP04 --agent <name>
```

## Activity Log

- 2026-04-27T09:21:42Z – claude:sonnet:implementer:implementer – shell_pid=93389 – Started implementation via action command
- 2026-04-27T09:31:04Z – claude:sonnet:implementer:implementer – shell_pid=93389 – Ready for review: mode.detect() with charter > flag > env > parent precedence
- 2026-04-27T09:31:31Z – claude:opus:reviewer:reviewer – shell_pid=98894 – Started review via action command
- 2026-04-27T09:33:22Z – claude:opus:reviewer:reviewer – shell_pid=98894 – Review passed: 4-layer precedence correct (charter>flag>env>parent), charter override sovereign over conflicting flag (C-013), malformed charter raises typed ModeResolutionError, conservative HiC default with default-no-signal evidence, 42 tests pass, mypy --strict clean
