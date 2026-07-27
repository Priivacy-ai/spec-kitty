---
work_package_id: WP01
title: Single context factory + freeze + build-invariant + write-projection boundary
dependencies: []
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T037
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2420540"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/
create_intent:
- tests/mission_runtime/test_context_factory_invariant.py
execution_mode: code_change
owned_files:
- src/mission_runtime/context.py
- src/mission_runtime/resolution.py
- tests/mission_runtime/test_context_factory_invariant.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and the binding contracts. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:

1. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — specifically **FR-009**
   (ExecutionContext builder-hardening) and **C-001** (no new authority).
2. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — **IC-01** (the SSOT spine),
   decisions **D-2** (the FR-009 rule) and **D-6** (the read/write-symmetry seam).
3. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` — the
   **C-IC01** contract (the four MUST/MUST-NOT obligations you are implementing against).
4. `docs/engineering_notes/context-factory-readwrite-symmetry/00-SYNTHESIS.md` — §3 (construction is
   already single-sited), §4 (fragment reversal), §5 (the write-projection boundary contract verbatim).

## Objective

Name the **single** `ExecutionContext` factory `build_execution_context`, **freeze** the composite,
assert the **build-time invariant**, and **declare the write-projection boundary contract** so the
deferred write-side (#1716 / #1878, Mission B) later adopts against a *frozen seam — not a rewrite*.

This is the trustworthy-context precondition for WP02–WP05 and WP09. It is **adoption, not
construction** (C-001): there is already exactly one production `ExecutionContext(` call
(`src/mission_runtime/resolution.py:739`, inside `resolve_action_context`) plus one
post-construction mutator (`:800-808`, the WP-bearing branch). You are *naming* that site, *freezing*
its product, and making it the *sole construction door* — you are NOT building a new resolver, root
authority, or error type, and you are NOT adding a new public symbol.

Concretely:

- Introduce `build_execution_context(...)` as the **package-private** sole factory funneling the
  `resolution.py:739` construction site and resolving the `:800-808` post-build mutation by
  assembling the WP-bearing context **in one shot** (function-over-form).
- Make `ExecutionContext` an immutable (frozen) composite — assigning `target_branch` (or any field)
  on a built context must raise.
- Assert `context.target_branch == branch_ref.target_branch` at build; on mismatch raise
  `ActionContextError("CONTEXT_INVARIANT_VIOLATION", …)`. **Do NOT normalize** (D-2) and **do NOT**
  retire the flat substrate (larger #1619 grain, deferred).
- `resolve_action_context` delegates construction to `build_execution_context`.
- `branch_naming` stays a **collaborator** the factory *calls* — it is NOT absorbed (#2012 bounded
  context — D-6).

> ⚠️ **branch_name is the WP lane branch — do NOT assert `branch_name == branch_ref.target_branch`.**
> The spec's original FR-009 wording (`branch_name == branch_ref.target_branch`) is **superseded by
> D-2**: `branch_name` legitimately differs from the mission target branch (it is the lane branch).
> The invariant is over `target_branch`, never `branch_name`. C-IC01 makes this explicit.

## Context (binding discipline)

- **Function-over-form + verification-by-deletion.** The proof that the factory is the sole door is
  that the `:800-808` post-build mutator is *deleted* and the full suite stays green — not that a new
  abstraction was added on top of the old mutable path. Do not leave the mutator in place behind a
  flag.
- **TDD-first.** Write `test_context_factory_invariant.py` first (T001/T002), watch it fail, then make
  it pass. The invariant test (`CONTEXT_INVARIANT_VIOLATION`) and the immutability test must both fail
  before the production change lands.
- **Topology-true fixtures (NFR-002).** Any fixture that builds a context uses production-shaped data:
  a **full 26-char ULID** `mission_id`, and where a context is built for a coord/submodule case, a
  **real coord-worktree** / **real submodule** (`.git` FILE) — **NO fabricated short ids**, no
  synthetic single-repo stand-in for the coord/submodule classes. For this WP most assertions are
  pure (construct a context, assert invariant/immutability), so the ULID realism is the load-bearing
  part; do not invent a 3-char slug.
- **Quality gates (NFR-004).** New/changed code passes `ruff` + `mypy` with **zero** issues,
  **complexity ≤ 15**, **no suppressions** (`# noqa` / `# type: ignore` are not allowed to reach
  green — fix the code). If freezing surfaces a long construction function, extract small deterministic
  helpers rather than letting `build_execution_context` exceed the complexity ceiling.
- **C-001: adopt, do not build a new authority.** No new public symbol; the factory is package-private
  (lean API, ADR-06-07-1).

## Subtasks

### T001 — TDD: build-time CONTEXT_INVARIANT_VIOLATION test
- Add `tests/mission_runtime/test_context_factory_invariant.py`.
- Write a test that drives `build_execution_context` (or `resolve_action_context` if the factory is
  only reachable through it) with inputs that yield `context.target_branch != branch_ref.target_branch`
  and asserts it raises `ActionContextError` with `code == "CONTEXT_INVARIANT_VIOLATION"`.
- Use a full 26-char ULID `mission_id` in the fixture (e.g. a realistic `01KV...`), never a short id.
- **Validation:** the test FAILS on HEAD (no invariant yet) — run
  `python -m pytest tests/mission_runtime/test_context_factory_invariant.py -k invariant`.

### T002 — TDD: ExecutionContext immutability test
- In the same test module, assert that mutating a built context (e.g.
  `ctx.target_branch = "other"`) raises (`FrozenInstanceError` / `AttributeError` from the frozen
  dataclass).
- **Validation:** the test FAILS on HEAD (composite still mutable, `resolution.py:793-801` /
  `:800-808` mutates after construction).

### T003 — Freeze the ExecutionContext composite
- Make `ExecutionContext` in `src/mission_runtime/context.py` a frozen dataclass (or otherwise
  construct-once / immutable). Adjust constructor call sites only as needed to feed all fields at
  construction.
- **file:line:** `src/mission_runtime/context.py` (the `ExecutionContext` class definition).
- **Validation:** T002 now passes; `mypy` clean on `context.py`.

### T004 — Assert target_branch == branch_ref.target_branch at build
- Inside `build_execution_context`, before/at return, assert
  `context.target_branch == branch_ref.target_branch`; on mismatch raise
  `ActionContextError("CONTEXT_INVARIANT_VIOLATION", <message naming both values>)`.
- Do **not** assert against `branch_name` (D-2 — lane branch differs).
- **file:line:** `src/mission_runtime/resolution.py` (the new factory body, funneling `:739`).
- **Validation:** T001 now passes.

### T005 — Assemble the WP-bearing context in one shot (no post-freeze write)
- Resolve the `resolution.py:800-808` post-construction mutation **AND** the `:813`
  `commands["workflow"] = …` dict-write by computing the WP-bearing fields (including the
  `commands["workflow"]` entry) *before* construction and feeding them into the single
  `build_execution_context` call. **Delete** the post-build mutator **and** the `:813` dict-write
  (verification-by-deletion).
  > ⚠️ A frozen dataclass does NOT block in-place dict mutation, so the `:813`
  > `context.commands["workflow"] =` write would not raise and the suite could stay green with it left
  > in place — it is the same "mutate a built context" anti-pattern and must be folded into
  > construction too, or the single-construction-door claim is half-done.
- **file:line:** `src/mission_runtime/resolution.py:739` (construction), `:800-808` (attribute mutator
  to remove), and `:813` (`commands["workflow"] =` dict-write to fold into construction).
- **Validation:** no remaining assignment to a built `ExecutionContext` (attribute **or** the
  `commands["workflow"]` dict-write); `grep` confirms one construction door.

### T006 — Full-suite sweep; fix any mutator the freeze surfaces
- Run the full suite (parallel per CLAUDE.md: `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p
  no:cacheprovider`). Freezing the composite can surface other callers that mutate a built context;
  fix each by constructing through the factory (function-over-form), never by re-introducing
  mutability.
- **Validation:** full suite green; `ruff check .` and `mypy` clean on the touched modules.

### T037 — Name `build_execution_context` + declare the write-projection boundary contract
- Ensure `build_execution_context` is the **sole** construction door and that `resolve_action_context`
  delegates to it. Keep it **package-private** (no new entry in a public `__all__`; C-001 / lean API).
- Add the **write-projection boundary contract** as a docstring on the factory (and, if a module
  `__all__` / module docstring is the right home, note it there) stating verbatim intent:
  > Write surfaces compose names/paths/identity from a factory-projected `IdentityFragment` +
  > `BranchRefFragment` (+ workspace/surface); they **MUST NOT** re-derive `mission_id` / `mid8` /
  > `primary_root` independently. `branch_naming` is the grammar collaborator; the factory is the
  > identity/topology authority that feeds it.
- **file:line:** `src/mission_runtime/resolution.py` (factory docstring) and
  `src/mission_runtime/context.py` (composite docstring if appropriate).
- **Validation:** the boundary-contract text is present and discoverable by the future write-side WP;
  `branch_naming` is still called as a collaborator (not inlined/absorbed).

## Branch Strategy

Planning artifacts were generated on **feat/read-path-error-fidelity**. During
`/spec-kitty.implement` this WP may branch from a dependency-specific base, but completed changes
**merge back into feat/read-path-error-fidelity** unless the human explicitly redirects the landing
branch. The execution workspace (worktree) is the one `spec-kitty implement WP01` resolves from
`lanes.json` — do not reconstruct the path by hand.

## Definition of Done

- [ ] `tests/mission_runtime/test_context_factory_invariant.py` added; both T001 (invariant) and T002
      (immutability) failed before the fix and pass after (TDD-first witnessed).
- [ ] `build_execution_context` is the **single** construction door for `ExecutionContext`; the
      `resolution.py:800-808` post-build mutator **and** the `:813` `commands["workflow"] =` dict-write
      are **deleted** / folded into construction (verification-by-deletion).
- [ ] `resolve_action_context` delegates construction to `build_execution_context`.
- [ ] `ExecutionContext` is frozen/immutable — mutating a built context raises (**C-IC01:** immutable
      post-build).
- [ ] Building with `target_branch != branch_ref.target_branch` raises
      `ActionContextError("CONTEXT_INVARIANT_VIOLATION", …)` (**C-IC01:** invariant).
- [ ] The build invariant does **NOT** demand `branch_name == branch_ref.target_branch` (**C-IC01:**
      lane branch legitimately differs; D-2).
- [ ] No new context type and the flat substrate is **not** retired (**C-IC01:** adopt, do not build —
      C-001).
- [ ] The write-projection boundary contract (D-6) is declared on the factory (docstring) for the
      deferred write-side to adopt against.
- [ ] `branch_naming` remains a collaborator the factory calls — NOT absorbed.
- [ ] `ruff check .` clean, `mypy` clean on `context.py` + `resolution.py`, every touched function at
      **complexity ≤ 15**, **no suppressions** added.
- [ ] Full suite green (parallel run) after the freeze (T006).

## Risks / reviewer guidance

- **The freeze surfaces hidden mutators.** Freezing `ExecutionContext` is the whole point — but it
  will likely expose other code that assigns to a built context. The correct fix is *always*
  construct-through-the-factory, never re-mutability. Reviewer: reject any patch that keeps the
  `:800-808` write alive behind a conditional.
- **Complexity ceiling.** Folding the WP-bearing assembly into one construction call can push
  `build_execution_context` over complexity 15. Extract pure helpers (lookup/build/emit phases) and
  test them directly — do not raise the ceiling or suppress C901.
- **Do not assert on `branch_name`.** The single most likely contract mistake. The invariant is over
  `target_branch` only (D-2). A reviewer must verify there is no `branch_name == ...` assertion.
- **C-001 boundary.** No new public symbol, no new resolver/error type. The factory is package-private.
  `CONTEXT_INVARIANT_VIOLATION` is a new *code on the existing `ActionContextError`*, not a new type.
- **branch_naming stays out.** Absorbing `branch_naming` would re-open the #2012 bounded context —
  out of scope. The factory only *calls* it.

## Activity Log

- _(empty — append implementation notes during /spec-kitty.implement)_
- 2026-06-16T20:10:04Z – claude:opus:python-pedro:implementer – shell_pid=2260157 – Assigned agent via action command
- 2026-06-16T20:50:42Z – user – shell_pid=2260157 – Claim for WP01 implementation
- 2026-06-16T20:50:43Z – user – shell_pid=2260157 – Implementing factory+freeze+invariant+boundary
- 2026-06-16T20:55:34Z – claude:opus:python-pedro:implementer – shell_pid=2260157 – Ready: factory+freeze+invariant+boundary; build_execution_context sole construction door; :800-808 mutator + commands[workflow] dict-writes folded into one-shot build; frozen composite; CONTEXT_INVARIANT_VIOLATION on target_branch mismatch (not branch_name, D-2); write-projection boundary contract declared; branch_naming collaborator; no new public symbol C-001. ruff=0, mypy clean(3), new tests 6/6 RED-first->green; blast-radius 560 passed; agent/integration/context/missions 2318 passed, 9 pre-existing worktree-env/sparse failures confirmed on clean HEAD via stash.
- 2026-06-16T20:56:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=2420540 – Started review via action command
- 2026-06-16T21:02:44Z – user – shell_pid=2420540 – Review passed (renata): invariant on target_branch only (D-2); frozen composite; sole build_execution_context factory; verification-by-deletion of :800-808 mutator + dict-writes; package-private (C-001); branch_naming collaborator; ruff/mypy/C901 clean; pre-existing worktree-env failures stash-confirmed
