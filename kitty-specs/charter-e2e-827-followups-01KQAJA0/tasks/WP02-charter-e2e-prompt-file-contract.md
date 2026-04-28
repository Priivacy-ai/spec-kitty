---
work_package_id: WP02
title: '#844 — charter E2E mandates a real prompt_file for kind=step'
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
agent: claude
history:
- at: '2026-04-28T19:59:16Z'
  actor: planner
  note: Initial work package created from /spec-kitty.tasks.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
mission_id: 01KQAJA02YZ2Q7SH5WND713HKA
mission_slug: charter-e2e-827-followups-01KQAJA0
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/next/decision.py
- src/specify_cli/next/runtime_bridge.py
- src/doctrine/skills/spec-kitty-runtime-next/SKILL.md
- tests/e2e/test_charter_epic_golden_path.py
- tests/specify_cli/next/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the assigned profile so your behavior matches what this work package expects:

```
/ad-hoc-profile-load python-pedro
```

This sets `role=implementer`, scopes your editing surface to the `owned_files` declared above, and applies Python-specialist standards.

## Objective

Tighten the `RuntimeDecision` envelope contract so a `kind=step` decision MUST carry a non-null, on-disk-resolvable `prompt_file` (or its alias `prompt_path`). Update the charter golden-path E2E to enforce that contract. Scrub host-facing doctrine that legitimizes null prompts. Add focused unit tests for the construction-time validator.

## Context

- The `RuntimeDecision` dataclass at `src/specify_cli/next/decision.py:61` currently declares `prompt_file: str | None = None`. The wire format admits `null` for `kind=step`.
- The inline comment at `src/specify_cli/next/decision.py:79` reads `# "prompt_file": <path> | null  (advance mode populates this)` — this is the legitimizing text per FR-008.
- The current E2E test at `tests/e2e/test_charter_epic_golden_path.py:570` only checks "a prompt key exists in the payload":
  ```python
  if "prompt_file" not in payload and "prompt_path" not in payload:
      raise ...
  ```
  It does NOT assert non-null, non-empty, or `Path.is_file()`.
- `runtime_bridge.py` constructs decision envelopes at multiple sites — grep findings include lines around 1571, 1594, 1662, 1686, 2118, 2138, 2193, 2225, 2252, 2271, 2286, 2310. Some sites set `prompt_file = None` directly (line 2193).
- The contract this WP enforces is documented in [`contracts/next-prompt-file-contract.md`](../contracts/next-prompt-file-contract.md) (C1, C2, C3) and [`data-model.md`](../data-model.md) (INV-844-1, INV-844-2, INV-844-3).

## Detailed guidance per subtask

### Subtask T005 — Tighten `RuntimeDecision` validation

**Purpose**: Make a `kind=step` envelope with a null/empty/non-existent `prompt_file` impossible to construct without conscious intent.

**Steps**:

1. Open `src/specify_cli/next/decision.py`.
2. Add a `__post_init__` (or peer construction-time validator) on the `RuntimeDecision` dataclass:
   ```python
   def __post_init__(self) -> None:
       if self.kind == "step":
           prompt = self.prompt_file or self.prompt_path  # whichever attribute exists
           if not prompt:
               raise InvalidStepDecision(
                   "kind='step' requires a non-empty prompt_file; got None/empty"
               )
           if not Path(prompt).is_file():
               raise InvalidStepDecision(
                   f"kind='step' prompt_file must resolve on disk: {prompt!r} does not"
               )
   ```
3. Define `InvalidStepDecision` as a dedicated exception in the same module (subclass of `ValueError`) so call sites can `try/except` it cleanly.
4. Replace the legitimizing inline comment at line 79:
   - Old: `# "prompt_file": <path> | null  (advance mode populates this)`
   - New: a comment that says: "kind='step' MUST carry a non-null prompt_file that resolves on disk (see C1/C2 in kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/next-prompt-file-contract.md). null is legal only for non-step kinds."
5. Verify `mypy --strict` is clean on the change.

**Files**: `src/specify_cli/next/decision.py` (modified, ~10–25 lines added).

**Validation**:
- [ ] Constructing `RuntimeDecision(kind="step", prompt_file=None)` raises `InvalidStepDecision`.
- [ ] Constructing `RuntimeDecision(kind="step", prompt_file="/tmp/does-not-exist")` raises `InvalidStepDecision`.
- [ ] Constructing `RuntimeDecision(kind="step", prompt_file=<path-to-real-file>)` succeeds.
- [ ] Constructing `RuntimeDecision(kind="blocked", prompt_file=None)` succeeds.
- [ ] Inline comment legitimizing null is removed.

### Subtask T006 — Audit `runtime_bridge.py` step-construction sites

**Purpose**: Wherever the runtime currently emits `kind=step` with a null prompt, route to `kind=blocked` with a reason instead. Per Constraint C-005 in the spec, the `kind=step` contract must NOT be weakened.

**Steps**:

1. Open `src/specify_cli/next/runtime_bridge.py`.
2. Locate every site that constructs a `RuntimeDecision` (search for `RuntimeDecision(` and surrounding factory calls). Focus on the lines around 1571, 1594, 1662, 1686, 2118, 2138, 2193, 2225, 2252, 2271, 2286, 2310 — but do not assume those line numbers; locate them by content.
3. At each site that may produce `kind=step` with a possibly-null prompt:
   - Wrap construction in `try / except InvalidStepDecision` (the new exception from T005).
   - On exception, emit a `kind=blocked` envelope with `reason="prompt_file_not_resolvable"` (or a more specific reason if the call site has more context).
4. At sites that explicitly set `prompt_file = None` (e.g. line ~2193) and then emit `kind=step`: change the kind to `blocked` directly, with a reason captured from local context. Do NOT silently drop the call.
5. If a site genuinely produces a non-step kind already (e.g. `kind=blocked`, `kind=complete`), no change is needed.
6. Run `uv run pytest tests/next -q` and `uv run pytest tests/contract/test_next_no_implicit_success.py tests/contract/test_next_no_unknown_state.py -q` to surface any caller that depended on the old null-prompt-step shape. Adjust call sites accordingly.

**Files**: `src/specify_cli/next/runtime_bridge.py` (modified, scope depends on audit; estimated 30–80 changed/added lines).

**Validation**:
- [ ] `grep -n "kind=\"step\"" src/specify_cli/next/runtime_bridge.py` produces no site that can emit a step with null prompt.
- [ ] All sites either pass a real `prompt_file` or fall back to `kind=blocked` with a reason.
- [ ] `uv run pytest tests/next -q` passes.
- [ ] `uv run pytest tests/contract/test_next_no_implicit_success.py tests/contract/test_next_no_unknown_state.py -q` passes.

### Subtask T007 [P] — Tighten the E2E assertion

**Purpose**: The golden-path E2E enforces the C1/C2 contract.

**Steps**:

1. Open `tests/e2e/test_charter_epic_golden_path.py`.
2. Locate the existing prompt-key check (around line 570 in the current code).
3. Replace it with the strict contract check for every issued decision where `kind == "step"`:
   ```python
   if payload.get("kind") == "step":
       prompt = payload.get("prompt_file") or payload.get("prompt_path")
       assert prompt is not None and prompt != "", (
           "kind='step' must carry a non-empty prompt_file (C1). "
           f"Live envelope keys: {sorted(payload.keys())}"
       )
       assert Path(prompt).is_file(), (
           f"kind='step' prompt_file must resolve on disk (C2): {prompt!r}"
       )
   ```
4. Do NOT assert anything about prompt fields for non-step kinds (`blocked`, `complete`, etc.) — leave those untouched.
5. Run `PWHEADLESS=1 uv run pytest tests/e2e/test_charter_epic_golden_path.py -q` and verify it passes against the changes from T005 and T006.

**Files**: `tests/e2e/test_charter_epic_golden_path.py` (modified, ~10–20 lines changed).

**Validation**:
- [ ] E2E passes against the post-T005/T006 codebase.
- [ ] If you temporarily monkey-patch the runtime to emit a `kind=step` envelope with `prompt_file=None`, the E2E fails with a message that names the violated contract.

### Subtask T008 [P] — Scrub doctrine

**Purpose**: Remove host-facing text that legitimizes null prompts for `kind=step`, per FR-008.

**Steps**:

1. Open `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`.
2. Search for any phrasing along the lines of:
   - "advance mode populates this"
   - "prompt may be null"
   - "kind=step with no prompt"
   - "blocked or step without prompt"
3. Replace with explicit contract language:
   - "A `kind=step` envelope MUST carry a `prompt_file` (or `prompt_path` alias) that is non-null, non-empty, and resolves on disk. A `kind=step` with a missing or non-resolvable prompt is a runtime invariant violation, not a substitute for `kind=blocked`."
   - "When the runtime cannot produce an actionable step (no composed action, blocked dependency, etc.), it returns `kind=blocked` with a `reason` field. Do not treat a `kind=step` with a null prompt as 'safe to ignore'."
4. If other doctrine surfaces in `src/doctrine/skills/` reference the same legitimizing wording, update them too. Do NOT touch unrelated doctrine content.

**Files**: `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` (modified). Possibly other files under `src/doctrine/skills/` if the same wording appears there (audit-only).

**Validation**:
- [ ] No remaining text in `src/doctrine/` legitimizes null prompts for `kind=step`.
- [ ] Replacement text accurately reflects the C1/C2/C3 contract.

### Subtask T009 [P] — Unit tests for the validator

**Purpose**: Lock in the construction-time validator with focused tests.

**Steps**:

1. Locate or create the appropriate test module: `tests/specify_cli/next/test_decision_validation.py` (or similar name aligned with project conventions).
2. Tests to add:
   - `test_step_with_real_prompt_file_succeeds`: write a temp file, construct `RuntimeDecision(kind="step", prompt_file=str(tmp))`, assert no exception.
   - `test_step_with_null_prompt_raises`: construct `RuntimeDecision(kind="step", prompt_file=None)`, assert `InvalidStepDecision` raised.
   - `test_step_with_empty_prompt_raises`: same with `prompt_file=""`.
   - `test_step_with_nonexistent_prompt_raises`: same with `prompt_file="/tmp/definitely-does-not-exist-<random>"`.
   - `test_blocked_with_null_prompt_succeeds`: construct `RuntimeDecision(kind="blocked", prompt_file=None, reason="...")`, assert no exception.
   - `test_complete_with_null_prompt_succeeds` (if `kind=complete` is legal in the codebase): same shape, no exception.
3. Use `tmp_path` (pytest fixture) for the real-file case.
4. Run `uv run pytest tests/specify_cli/next/test_decision_validation.py -q`. Expect all PASS.

**Files**: `tests/specify_cli/next/test_decision_validation.py` (new, ~80–120 lines).

**Validation**:
- [ ] All 5–6 unit tests pass.
- [ ] `mypy --strict` clean.

## Branch strategy

- **Planning/base branch**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: assigned per lane by `finalize-tasks` (lane B per the tasks.md plan).

## Definition of Done

- [ ] `RuntimeDecision` raises `InvalidStepDecision` for `kind=step` with null/empty/non-resolvable prompt; non-step kinds remain permissive.
- [ ] No site in `src/specify_cli/next/runtime_bridge.py` emits `kind=step` with a null prompt.
- [ ] E2E test asserts the C1/C2 contract for every `kind=step` envelope.
- [ ] Doctrine SKILL.md contains no text legitimizing null prompts for `kind=step`.
- [ ] New unit tests under `tests/specify_cli/next/` cover the positive and negative cases.
- [ ] `PWHEADLESS=1 uv run pytest tests/e2e/test_charter_epic_golden_path.py -q` passes.
- [ ] `uv run pytest tests/next -q` passes.
- [ ] `uv run pytest tests/contract/test_next_no_implicit_success.py tests/contract/test_next_no_unknown_state.py -q` passes.
- [ ] `uv run pytest tests/specify_cli/next -q` passes.
- [ ] `mypy --strict` clean.
- [ ] Only files in this WP's `owned_files` list were modified.

## Implementation command

This WP has no upstream dependencies. Issue with:

```bash
spec-kitty agent action implement WP02 --agent claude --mission charter-e2e-827-followups-01KQAJA0
```

## Reviewer guidance

- The validator MUST be at construction time, not at serialization time, so the wire format is self-consistent by definition.
- A `runtime_bridge.py` site that catches `InvalidStepDecision` and silently retries with a different prompt is a code smell — the right behavior is `kind=blocked` with a reason.
- The E2E test must not assert on prompt fields for non-step kinds — over-asserting would be a regression of its own.
- Doctrine scrub is content-only; do not restructure unrelated doctrine sections.

## Requirement references

- **FR-004** (`prompt_file` exposed as stable public field).
- **FR-005** (non-null, non-empty, resolves on disk).
- **FR-006** (non-actionable state uses non-step kind).
- **FR-007** (E2E enforces all of the above).
- **FR-008** (doctrine no longer legitimizes null).
- **C-005** (kind=step contract not weakened).
- Contributes to **NFR-003** (verification matrix).
