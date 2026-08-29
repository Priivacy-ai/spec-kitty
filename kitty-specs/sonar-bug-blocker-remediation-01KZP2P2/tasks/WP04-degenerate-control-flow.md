---
work_package_id: WP04
title: Degenerate control flow (S3516 x4, S2583 x2)
dependencies: []
requirement_refs:
- C-002
- FR-002
- FR-003
- NFR-001
- NFR-002
planning_base_branch: fix/sonar-bug-blocker-remediation
merge_target_branch: fix/sonar-bug-blocker-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/sonar-bug-blocker-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sonar-bug-blocker-remediation unless the human explicitly redirects the landing branch.
created_at: '2026-08-10T15:05:00+00:00'
subtasks:
- T009
- T010
phase: Investigate stream - control flow
history:
- at: '2026-08-10T15:05:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/activation/pack_manager.py
- src/specify_cli/cli/commands/_command_surface_doctor.py
- src/specify_cli/core/file_lock.py
- src/specify_cli/status/reducer.py
- src/runtime/next/runtime_bridge.py
- src/specify_cli/compat/remediation.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Resolve 4 **S3516** BLOCKER issues ("Refactor this method to not always return the same value") and
2 **S2583** BUG issues ("Fix this condition that always evaluates to true"). Both are degenerate
control flow: a method whose every path returns the same value, and a condition that can never be
false. Each is either a **real bug** (a branch that should vary but cannot) or an **intentional
constant / defensive guard** that reads as a smell.

This is an **investigate** WP — classify each site, then apply the matching remedy. Never suppress.

## Per-site method

1. **Read the function/branch and its callers.** Decide:
   - **Real bug**: the return/condition was supposed to depend on state but a logic error makes it
     constant (e.g. a variable shadowed, a wrong operator, an early `return` swallowing a branch) →
     **fix the logic** so it varies as intended; add a behavioral test covering both outcomes.
   - **Intentional constant**: the method conforms to a protocol/interface and legitimately always
     returns the same value, or the condition is a deliberate always-on guard → **remove the smell**
     without changing behavior: drop the vacuous `return`, narrow the return type / signature, hoist a
     constant, or restructure so the intent is explicit. Add a test pinning the (now-explicit) behavior.
2. **Every new branch/helper gets a test** (C-002). A behavioral test — not just "it imports".
3. **No suppression** (NFR-001).

## Subtasks

### T009 — S3516 always-same-return (4 sites)

- `src/charter/activation/pack_manager.py:559`
- `src/specify_cli/cli/commands/_command_surface_doctor.py:164`
- `src/specify_cli/core/file_lock.py:271`
- `src/specify_cli/status/reducer.py:751`

Classify each. Likely mix: `_command_surface_doctor` and `file_lock` may have a method that returns a
constant status (intentional → make explicit); `status/reducer.py:751` in the reducer is
higher-suspicion for a real bug (a reduce branch that should differ) — trace carefully, because the
reducer is the status source of truth. `pack_manager.py:559` — check whether a computed value is being
discarded. For each real-bug fix, add a test asserting the differing outcomes; for each intentional
one, restructure to remove the vacuous return and pin behavior.

### T010 — S2583 always-true conditions (2 sites)

- `src/runtime/next/runtime_bridge.py:1497`
- `src/specify_cli/compat/remediation.py:445`

For each: determine whether the condition should be able to be false (real bug — fix the predicate) or
is a dead/redundant guard (remove it, keeping the reachable branch). Add a test that exercises the
corrected predicate / the retained path. Be careful in `runtime_bridge` (runtime loop) — a wrong
"simplification" could change loop/termination behavior.

## Squad findings (AUTHORITATIVE — a pre-implementation debugger squad classified every site; implement exactly this)

Apply the per-site remedy below. 5 sites are INTENTIONAL smells (behavior-preserving removal + a test
pinning current behavior). 1 site is a REAL BUG with an operator-chosen fix. Do not deviate without
re-reading the surrounding code and flagging it.

1. **`pack_manager.py:559` `deactivate` — INTENTIONAL.** `result` is built once before the branch; the
   `if not plan.deactivated` guard only gates the `commit_plan` side effect. Fix: guard only the side
   effect, single trailing `return result`:
   ```python
   if plan.deactivated:
       commit_plan(target_path, data, plan, save=save)
   return result
   ```
   Test: no-op deactivate (ID absent) → `deactivated == []` AND activation source bytes untouched
   (assert `commit_plan` not called / file unchanged); real deactivate → removed ID returned + written.

2. **`_command_surface_doctor.py:164` `_print_slash_command_report` — INTENTIONAL.** Three returns all
   `return slash_healthy` (computed once as `not slash_gaps`). **KEEP the `-> bool` signature** —
   `tests/specify_cli/cli/commands/test_command_surface_doctor.py:165-170` asserts True/True/False.
   Fix: collapse to a single trailing `return slash_healthy`; convert the early returns into
   fall-through guards around the `console.print` blocks. Existing test pins behavior.

3. **`file_lock.py:271` `force_release` — REAL BUG (operator decision: RAISE on genuine errors).** The
   `_os_lock` handler has two identical `return False` arms and discards `_is_contention_error(exc)`,
   swallowing genuine FS errors (`EIO`/`ENOSPC`) — contradicting the module contract (`:119`, `:135`)
   and its honored twin `__aenter__` (`:377`). Fix:
   ```python
   except OSError as exc:
       if not _is_contention_error(exc):
           raise           # genuine FS error propagates, per module contract + __aenter__
       return False        # true contention -> lock held, cannot force-release
   ```
   **Red-first test to ADD**: monkeypatch `_os_lock` to raise `OSError(EIO)` on a stale lock; assert
   `force_release` RAISES (currently returns False → RED), then passes after the fix. Keep
   `test_force_release_clear_failure` (`:319`) green — it targets the DIFFERENT clear-step `except`
   (`:302`), a deliberate best-effort swallow that must be preserved. Preserve all other outcomes:
   contention→False, missing→False, fresh→False, stale→True.

4. **`reducer.py:751` `materialize` — INTENTIONAL (HIGH CARE — status source of truth).** Both returns
   are `return snapshot` (computed once); the guard gates only the write side effect (FR-001/NFR-001
   byte-identical skip-write). Fix: single trailing `return snapshot`, PRESERVING (a) skip write when
   byte-identical, (b) atomic tmp-write + `os.replace`, (c) always return the freshly-computed snapshot.
   Do NOT alter `materialize_snapshot`/`materialize_to_json`. Re-run `tests/status/test_reducer.py`
   (byte-identical :425/:465, creates :491, atomic :520, overwrites :554).

5. **`runtime_bridge.py:1497` — INTENTIONAL (HIGH CARE — runtime loop).** The `_build_prompt_safe(...)`
   call runs only under `if action` (`:1505`), so `action or current_step_id` always yields `action`;
   the `or current_step_id` fallback is dead. Fix: pass bare `action` (matches the sibling at
   `:1431`). Change NOTHING else in the loop/termination logic. Run
   `tests/runtime/test_bridge_decide_next.py` + `test_bridge_compat_surface.py`.

6. **`remediation.py:445` — INTENTIONAL.** `_uv_injected_dep_source` is total (always returns a
   non-empty `str` via the `f"{req.name}{req.specifier or ''}"` fallback), so `if source is not None`
   is always true and the trailing `return None` is dead. Fix: drop the vacuous guard
   (`source = _uv_injected_dep_source(req); return ["--with", source]`) OR narrow the helper's return
   annotation to `-> str`. The real refusal path stays the `is_supported` gate (`:440`). Test: unsupported
   req → `None` (via `:440`); bare-name req → `["--with", "<name><specifier>"]`.

Every fix carries a behavioral test (C-002). Sites 3, 4, 5 are highest-risk — verify against their
existing suites. No suppression.

## Branch Strategy

Planning base and final merge target are both `fix/sonar-bug-blocker-remediation`. Consume the
workspace `spec-kitty implement` resolves from `lanes.json`.

## Definition of Done

- All 4 S3516 + 2 S2583 sites resolved with a documented classification (real-bug vs intentional) and,
  for each, a behavioral test.
- `status/reducer.py` and `runtime_bridge.py` changes verified against their existing suites (reducer
  determinism; runtime loop behavior) — no behavior regression.
- `ruff`/`mypy` clean on changed src; scoped tests green; zero suppressions.
- The PR body records the per-site classification.
- `move-task --to for_review` pre-review gate passes.

## Risks / reviewer guidance

- **Highest-risk files**: `status/reducer.py` (status SoT — a wrong "fix" corrupts snapshots) and
  `runtime_bridge.py` (runtime loop). The reviewer must confirm behavior is preserved for intentional
  cases and genuinely corrected for real bugs, backed by the new tests.
- Do not "add a branch" just to satisfy Sonar — an invented branch with no real caller is worse than
  the smell. When intentional, make the invariant explicit instead.
