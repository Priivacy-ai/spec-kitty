---
work_package_id: WP04
title: Named gate-handler registry
dependencies:
- WP03
requirement_refs:
- FR-004
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
phase: Phase 2 - Engine
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: "python-pedro"
authoritative_surface: src/specify_cli/review/gate_registry.py
create_intent:
- src/specify_cli/review/gate_registry.py
- tests/review/test_gate_registry.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/gate_registry.py
- tests/review/test_gate_registry.py
role: "implementer"
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Named gate-handler registry

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface` (`src/specify_cli/review/gate_registry.py`). `implementer-ivan` or `python-pedro` are the natural fits.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

Introduce a **named gate-handler registry** — `GATE_REGISTRY` — that mirrors the shape of the
existing `GUARD_REGISTRY` (`src/specify_cli/mission_v1/guards.py:270`) and register today's
pre-review engine as the **first and only** handler, keyed to the `for_review` edge. This is a
pure indirection: the transition still runs exactly one handler producing exactly the current
verdict. It delivers **FR-004** (gates addressed by name, not by a hardcoded call) and lays the
dispatch seam that WP06 (binding resolution) and WP09 (the inverted hook) consume.

**Done when:**

- `src/specify_cli/review/gate_registry.py` exists and exports a `GateHandler` type alias, a
  `GATE_REGISTRY: dict[str, GateHandler]` mapping, and a lookup helper.
- `GATE_REGISTRY` contains **exactly one** entry — `"spec-kitty-pre-review"` — whose callable
  wraps `evaluate_pre_review_gate` (`src/specify_cli/review/pre_review_gate.py:853`) and is keyed
  to the `for_review` edge via its `GateHandler` metadata.
- Dispatching the registered handler reproduces the **current** `GateVerdict`
  (`pre_review_gate.py:754`) byte-for-byte for the same inputs — no behaviour change.
- `tests/review/test_gate_registry.py` proves registration, lookup, and single-handler dispatch
  parity — all authored **red-first**.
- `mypy --strict` and `ruff` are clean; every new function is complexity ≤ 15; new-code line
  coverage ≥ 90%.

**Explicit non-goals (GUARD):**

- **No verdict aggregation.** `aggregate_verdicts()` is WP08's owned surface. This WP dispatches
  one handler and returns its single verdict — do NOT introduce precedence, multi-verdict folding,
  or block/terminal logic here.
- **Exactly one handler** ships in half A. Do NOT speculatively register a second handler or
  a placeholder. The multi-handler paths are exercised only by WP08's synthetic tests.
- Do NOT touch `tasks_move_task.py` or invert the hook — WP09 owns the call-site migration. This
  WP only *defines* the registry; wiring it into the live transition path is WP09.

## Context & Constraints

- **Charter first.** Read `.kittify/charter/charter.md` before changing code. This mission is
  bound by ATDD-first (C-011), architectural-gate discipline (reuse canonical patterns), and
  single-canonical-authority. Load action-scoped doctrine with
  `spec-kitty charter context --action implement`.
- **Mission docs.** `kitty-specs/doctrine-controlled-transition-gates-01KY51Z7/spec.md` (FR-004,
  User Story 3), `plan.md` (IC-03), `data-model.md` §4 (`GateHandler` / `GATE_REGISTRY`),
  `contracts/transition-gate-hook.md` (how the registry is dispatched by the hook).
- **Pattern to mirror (canonical source — do NOT improvise).**
  `src/specify_cli/mission_v1/guards.py:270` defines `GUARD_REGISTRY: dict[str, Callable[...]]`
  as a module-level dict of name → callable, with an unknown-key error path that lists supported
  keys (`guards.py:373-378`). Mirror that shape: a module-level dict, a typed value, and a lookup
  that raises a clear error naming the missing key and listing the known keys.
- **The handler wraps, does not replace.** Per `data-model.md` §4, the first handler
  `_spec_kitty_pre_review_handler` wraps `evaluate_pre_review_gate`
  (`src/specify_cli/review/pre_review_gate.py:853`, returns a `GateVerdict`). WP03 already made the
  engine consume an injected `ScopeSource`; this WP calls the WP03 engine surface, it does not
  re-derive scope. Registry membership is the *callable source*; **activation** (WP06) decides
  whether the handler runs — that decision is NOT in this WP.
- **`GateHandler` contract.** Per `data-model.md` §4 and §8, a handler receives a
  `TransitionGateContext` (the changed-files SSOT, resolved `ScopeSource`, baseline, `repo_root`,
  `force`, and the edge lanes) and returns a `GateVerdict`. It is pure-ish and self-contained; it
  **never** calls `Exit()` — the hook (WP09) owns exit/aggregation. If `TransitionGateContext` is
  not yet defined by a prior WP, define the minimal frozen dataclass this WP needs in
  `gate_registry.py` — its **SINGLE home** (WP04-owned), **not** a sibling `_gate_context.py` —
  matching the `data-model.md` §8 field table, and note the seam so WP06/WP09 **import it, never
  redefine** it.
- **`GateHandler` carries edge metadata.** T018 requires the contract to name `(name, edge,
  callable)`. A bare `Callable` cannot answer "which edge is this keyed to." Model the handler as a
  small frozen dataclass — `GateHandler` is a frozen dataclass `(name, edge, run:
  Callable[[TransitionGateContext], GateVerdict])` — so `for_review` keying is data, not a comment.
  `GATE_REGISTRY` maps `name -> GateHandler`. The canonical dispatch form is
  `get_gate_handler(name).run(ctx)` (**NOT** a bare-callable / not `__call__`) — the handler is always
  invoked through its `run` attribute.
- **Complexity / typing.** Python 3.11+, `mypy --strict`, `ruff`, complexity ≤ 15/function. No
  `# noqa` / `# type: ignore` — fix the code. Repeated literals appearing ≥ 3 times become module
  constants (Sonar S1192): the handler name `"spec-kitty-pre-review"` and the edge
  `"in_progress->for_review"` are prime candidates — hoist them to named constants.
- **Tracker:** WP04 = epic #2535 sub-issue **#2596** (IC-03, "Register pre-review engine as the
  first named gate handler").

## Branch Strategy

- **Strategy**: single mission branch
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

All work happens in the WP04 execution workspace created by `spec-kitty implement WP04`; it
depends on WP03 (`[WP03]`), which must be `approved` or `done` before this WP can be claimed
(dependency gating). Run tests with `PYTHONPATH=$(pwd)/src`.

## Subtasks & Detailed Guidance

### Subtask T016 – `GATE_REGISTRY` named-handler registry

- **Purpose (FR-004):** Give gates an addressable name so the transition path can look up which
  handler(s) to run instead of hardcoding a call to `evaluate_pre_review_gate`.
- **Steps:**
  1. Create `src/specify_cli/review/gate_registry.py`.
  2. Declare `GATE_REGISTRY: dict[str, GateHandler]` as a module-level dict — mirror
     `mission_v1/guards.py:270` exactly in shape (module constant, typed value).
  3. Add a lookup helper `get_gate_handler(name: str) -> GateHandler` that raises a clear
     `KeyError`/custom error listing the registered names when the key is absent — mirror the
     unknown-guard error at `guards.py:373-378` (name the missing key AND the known keys).
  4. Hoist the handler name and edge string to module constants.
- **Files:** `src/specify_cli/review/gate_registry.py`.
- **Parallel?:** No — T017/T018 build on the types this subtask declares.
- **Notes:** Keep the module import-light. Import `evaluate_pre_review_gate` lazily inside the
  handler wrapper if a module-level import would create a cycle with `pre_review_gate.py`; prefer a
  top-of-module import if no cycle exists (verify with `ruff`/import). Do NOT import
  `tasks_move_task.py` — that is a downstream consumer, not an upstream dependency.

### Subtask T017 – Register `evaluate_pre_review_gate` as the first handler

- **Purpose (FR-004, NFR-001 groundwork):** Make the incumbent gate reachable *by name* with
  **no behaviour change** — one entry, dispatched where the hardcoded call is.
- **Steps:**
  1. Define `_spec_kitty_pre_review_handler(ctx: TransitionGateContext) -> GateVerdict` that
     unpacks the context and delegates to `evaluate_pre_review_gate`
     (`pre_review_gate.py:853`) with the WP03 injected-`ScopeSource` surface.
  2. Register it: `GATE_REGISTRY["spec-kitty-pre-review"] = GateHandler(name="spec-kitty-pre-
     review", edge="in_progress->for_review", run=_spec_kitty_pre_review_handler)`.
  3. The handler MUST NOT catch-and-swallow, MUST NOT `Exit()`, and MUST return the verdict the
     engine produces unchanged — fail-open and aggregation belong to WP08/WP09.
- **Files:** `src/specify_cli/review/gate_registry.py`.
- **Parallel?:** No.
- **Notes:** This is a **strangler** step — the goal is that dispatching `GATE_REGISTRY["spec-
  kitty-pre-review"].run(ctx)` yields the same `GateVerdict` the current direct call yields. Keep
  the edge keyed as `in_progress->for_review` (the `on_transition` key shape from
  `data-model.md` §3), matching the binding authored in WP05.

### Subtask T018 – `GateHandler` contract (name, edge, callable → verdict)

- **Purpose:** Give a handler enough structure to answer "what is my name" and "which edge am I
  keyed to" — required by WP06's join (retain bindings whose handler resolves) and WP09's
  edge-scoped dispatch.
- **Steps:**
  1. Define `GateHandler` as a frozen dataclass with `name: str`, `edge: str`, and
     `run: Callable[[TransitionGateContext], GateVerdict]`.
  2. Define the `GateHandler` type alias / value type used by `GATE_REGISTRY`'s annotation.
  3. Document the contract in the docstring: pure-ish, self-contained, never `Exit`s, returns a
     `GateVerdict`; the hook (WP09) owns exit + aggregation.
- **Files:** `src/specify_cli/review/gate_registry.py`.
- **Parallel?:** No — T016/T017 reference this type.
- **Notes:** If `TransitionGateContext` is not yet defined upstream, introduce the minimal frozen
  dataclass **here in `gate_registry.py` — its single home, not a sibling module** — matching
  `data-model.md` §8 (`changed_files`, `scope_source`, `baseline`, `repo_root`, `force`, `from_lane`,
  `to_lane`) and leave a comment marking it the shared hook↔handler payload so WP06/WP09 **import it,
  never redefine** it. Do not over-build fields the half-A path never reads.

### Subtask T019 – `test_gate_registry.py` (registration, lookup, single-handler dispatch parity)

- **Purpose (ATDD red-first):** Lock the registry contract and prove the single-handler dispatch
  reproduces the current verdict before the code exists.
- **Steps (author these RED first, then implement T016–T018 to green):**
  1. **Registration:** assert `GATE_REGISTRY` contains exactly one key `"spec-kitty-pre-review"`
     and that its value is a `GateHandler` with `edge == "in_progress->for_review"`. Assert the
     registry has **length 1** — this is the half-A single-handler guard, and it will fail loudly
     if a later WP leaks a second production handler in.
  2. **Lookup:** `get_gate_handler("spec-kitty-pre-review")` returns the handler; an unknown name
     raises an error whose message names the missing key and lists known keys.
  3. **Single-handler dispatch parity:** build a `TransitionGateContext` for a controlled input
     (fabricated/stubbed `ScopeSource` + baseline) and assert
     `GATE_REGISTRY["spec-kitty-pre-review"].run(ctx)` returns a `GateVerdict` equal to what
     calling `evaluate_pre_review_gate` directly with the same inputs returns. This proves the
     wrapper is a pass-through, not a re-implementation.
  4. **No-Exit guarantee:** assert the handler returns normally (does not raise `SystemExit`) even
     for a `NEW_FAILURES`-shaped verdict — blocking is the hook's job, not the handler's.
- **Files:** `tests/review/test_gate_registry.py`.
- **Parallel?:** Written first (red), then kept green.
- **Notes:** Do not assert against the real Spec-Kitty test tree — use a stubbed `ScopeSource` /
  fabricated verdict so the test is fast and deterministic. Full end-to-end parity through the hook
  is WP08/WP09's golden; this test only proves the *registry wrapper* is transparent.

## Test Strategy (mandatory — ATDD red-first)

- **Location:** `tests/review/test_gate_registry.py` (sibling to the existing
  `tests/review/test_*` suite).
- **Red-first:** author all four assertion groups (T019) before implementing T016–T018; confirm
  they fail for the right reason (module/attr missing), then implement to green.
- **Run:**
  ```bash
  PYTHONPATH=$(pwd)/src pytest tests/review/test_gate_registry.py -q
  PYTHONPATH=$(pwd)/src pytest tests/review/ -q            # no regressions in the review suite
  mypy --strict src/specify_cli/review/gate_registry.py
  ruff check src/specify_cli/review/gate_registry.py tests/review/test_gate_registry.py
  ```
- **Coverage:** ≥ 90% new-code line coverage on `gate_registry.py`, including the unknown-key error
  branch (exercise it directly).
- **Fixtures:** stub/fabricate `ScopeSource` and `GateVerdict` inputs; no real git, no real
  subprocess run.

## Risks & Mitigations

- **Scope creep into aggregation (WP08).** *Mitigation:* the length-1 registry assertion (T019.1)
  and the "no aggregation logic" guard keep this WP to pure indirection.
- **Import cycle** between `gate_registry.py` and `pre_review_gate.py`. *Mitigation:* prefer a
  top-level import; fall back to a lazy import inside the wrapper if `ruff`/import flags a cycle.
- **`TransitionGateContext` drift** if WP06/WP09 later redefine it. *Mitigation:* define the
  minimal shared dataclass matching `data-model.md` §8 and mark it the canonical hook↔handler
  payload so downstream WPs extend rather than fork.
- **Silent behaviour change** in the wrapper. *Mitigation:* T019.3 asserts verdict equality against
  a direct `evaluate_pre_review_gate` call.

## Review Guidance

- Confirm `GATE_REGISTRY` has **exactly one** entry and mirrors `GUARD_REGISTRY`'s module-level
  dict shape (`mission_v1/guards.py:270`).
- Confirm **no** aggregation / block / terminal / `Exit` logic exists in this WP (that is WP08/WP09).
- Confirm the dispatch-parity test compares against a direct `evaluate_pre_review_gate` call — a
  test that only asserts "a verdict came back" is insufficient (must prove *equality*).
- Confirm the unknown-key error names the missing key and lists known keys.
- Confirm `mypy --strict` + `ruff` clean, complexity ≤ 15, new-code coverage ≥ 90% incl. the error
  branch.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Initial entry**:

- {{TIMESTAMP}} – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP04 --to <status>` to change WP status.
