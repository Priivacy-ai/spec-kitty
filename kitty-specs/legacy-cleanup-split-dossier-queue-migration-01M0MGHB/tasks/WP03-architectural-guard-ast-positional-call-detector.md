---
work_package_id: WP03
title: Architectural Guard — AST Positional-Call Detector
dependencies: ["WP02"]
requirement_refs:
- FR-008
planning_base_branch: refactor/dossier-emitters-canonical-only-1058
merge_target_branch: refactor/dossier-emitters-canonical-only-1058
branch_strategy: Planning artifacts for this mission were generated on refactor/dossier-emitters-canonical-only-1058. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into refactor/dossier-emitters-canonical-only-1058 unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
phase: Phase 4 - guard test
history:
- at: '2026-08-22T12:25:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_dossier_emitter_positional_guard.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_dossier_emitter_positional_guard.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Architectural Guard — AST Positional-Call Detector

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter (or any user-defined profile), and behave according to its guidance
before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the
best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via
  `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items
  are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log
  explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in
the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

Add a new AST-based guard test (`tests/architectural/test_dossier_emitter_positional_guard.py`,
a brand-new file — this is the only WP in this mission that creates a file
rather than editing existing ones) that fails if any production code (`src/`)
calls `emit_artifact_indexed`, `emit_artifact_missing`, `emit_snapshot_computed`,
or `emit_parity_drift_detected` with a positional argument. This closes the
class of bug PR #1056 had to patch around (positional-argument shape drift) by
construction, not by convention — the exact mechanism spec.md's User Story 3
asks for, and the mechanism that makes WP01's parameter-promotion fix durable
rather than a one-time cleanup.

- **SC-004**: The new AST guard test passes clean against `src/` and demonstrably
  fails against a planted positional-call fixture (both directions exercised in
  the test itself).
- Modeled directly on this repo's own established AST-guard idiom — do not
  invent a new detection technique; reuse the pattern already proven in
  `tests/architectural/test_shared_package_boundary.py`'s `_forbidden_imports()`
  + planted-violation positive control, and
  `tests/architectural/test_guard_capability_call_sites.py`'s per-symbol
  allowlist pattern.

## Context & Constraints

- Charter: `.kittify/charter/charter.md` — "a gate-unmask cannot self-validate"
  is the binding rule this WP's positive control exists to satisfy (Standing
  Order #5, architectural gate discipline).
- Spec: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/spec.md`
  — read User Story 3 (spec.md, "A construction-time guard prevents the
  positional-call pattern from regrowing") and FR-008 in full.
- Plan: `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/plan.md`
  — "FR-008 guard test design" section gives the exact 4-step design this WP
  implements.
- Read `tests/architectural/test_shared_package_boundary.py` in full before
  starting — it is your direct structural template (planted.py/clean.py-style
  fixture pair, AST-walk detector, module scoping).
- **Verified real call sites** (as of specification; re-verify live before
  writing your clean-tree assertion, since WP01/WP02 may have shifted line
  numbers): `src/specify_cli/sync/dossier_pipeline.py` lines 101, 126, 175, 230
  (all four emitter calls, all keyword-only); `src/specify_cli/dossier/drift_detector.py`
  line 419 (the one call to `emit_parity_drift_detected`, keyword-only). All 5
  are already 100% keyword-argument today — your clean-tree assertion is
  expected to pass on day one.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated directly on
  `refactor/dossier-emitters-canonical-only-1058` (this mission's own target
  branch — not `main`). Execution worktrees are allocated per computed lane from
  `lanes.json`; completed changes merge back into
  `refactor/dossier-emitters-canonical-only-1058`.
- **Planning base branch**: `refactor/dossier-emitters-canonical-only-1058`
- **Merge target branch**: `refactor/dossier-emitters-canonical-only-1058`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T014 – AST detector function (FR-008)

- **Purpose**: The core detection logic — find every call in `src/` to one of
  the four dossier emitters that passes a positional argument.
- **Steps**:
  1. Write a detector function that walks `ast.parse()` over every `*.py` file
     under `src/`, using the same production-root scoping convention
     `test_shared_package_boundary.py` uses (look for its `_PRODUCTION_ROOTS`-
     style constant or equivalent path-walk and mirror it — do not invent a
     different scoping mechanism for consistency with the established pattern).
  2. Find `ast.Call` nodes whose `func` resolves — by simple name match, since
     these are module-level functions, not methods, so no attribute-chain
     resolution is needed — to one of: `emit_artifact_indexed`,
     `emit_artifact_missing`, `emit_snapshot_computed`,
     `emit_parity_drift_detected`.
  3. Flag any such call whose `node.args` (positional arguments) is non-empty.
  4. Return a structured list of violations (file path, line number, the
     matched function name) — matching whatever return shape
     `test_shared_package_boundary.py`'s detector uses, for consistency.
- **Files**: `tests/architectural/test_dossier_emitter_positional_guard.py`
  (new file).
- **Parallel?**: No — everything else in this WP depends on this function.
- **Notes**: Do not attempt full call-graph resolution or handle
  re-exported/aliased imports of these names — spec.md's own design scopes this
  to simple name matching, matching the four functions' actual usage pattern
  (module-level function calls, never via an alias in `src/` today).

### Subtask T015 – Clean-tree assertion test (FR-008)

- **Purpose**: Prove the detector reports zero violations against the real,
  unmodified `src/` tree — the expected, passing state on day one and after
  this mission's own changes.
- **Steps**:
  1. Write a test that runs T014's detector against the real `src/` directory
     (the actual repository tree, not a fixture) and asserts the violation list
     is empty.
  2. This assertion should pass immediately given the 5 verified real call
     sites are already 100% keyword-argument — if it does not pass, that is a
     signal either your detector has a bug (most likely: false-positive
     matching an unrelated call) or WP01/WP02 introduced a positional call
     somewhere, which would itself be a mission regression to fix before
     proceeding.
- **Files**: `tests/architectural/test_dossier_emitter_positional_guard.py`.
- **Parallel?**: No — depends on T014.
- **Notes**: This test's continued passing through this mission's own changes
  (T014-T017 landing after WP01/WP02) is itself evidence FR-004's parameter
  promotion did not turn any existing keyword call into a positional one.

### Subtask T016 – Positive-control test (FR-008)

- **Purpose**: Prove the detector actually fires rather than vacuously passing
  because nothing in `src/` happens to trip it — the charter's "a gate-unmask
  cannot self-validate" rule, and spec.md's own explicit self-mutation
  requirement (User Story 3's Independent Test).
- **Steps**:
  1. Using `tmp_path` (pytest's built-in fixture), write a throwaway fixture
     file containing a planted positional call, matching spec.md's own example
     exactly: `emit_artifact_indexed("m", "k", "c", "p", "h", 1)` (six bare
     positional arguments).
  2. Run T014's detector against **that fixture** (not against `src/`).
  3. Assert it reports **exactly one violation**, and that the violation
     identifies the planted call (file, line, function name) correctly.
  4. This is the proof the detector actually fires — mirror
     `test_shared_package_boundary.py`'s `planted.py`/`clean.py` pair structure
     exactly (same idea: a synthetic bad file the detector must catch, separate
     from the assertion against the real tree).
- **Files**: `tests/architectural/test_dossier_emitter_positional_guard.py`.
- **Parallel?**: No — depends on T014; independent of T015 in principle but
  keep sequential per this WP's "no `[P]`" policy.
- **Notes**: This test IS this WP's red-first proof (spec.md Acceptance
  Scenario 3: "Given the guard is reverted (deleted or its detector logic
  gutted to always return 'no violations'), When CI runs the full test suite,
  Then at least one test fails") — no additional scaffolding is needed beyond
  this positive-control assertion. Gutting the detector to always report "no
  violations" is precisely what this test exists to catch.

### Subtask T017 – Guard-file docstring/structure polish

- **Purpose**: Match this repo's established documentation convention for
  architectural guard tests, so a future reader immediately recognizes the
  pattern (the same reason `test_shared_package_boundary.py` and
  `test_guard_capability_call_sites.py` carry explanatory module/class
  docstrings).
- **Steps**:
  1. Add a module-level docstring explaining: what this guard protects against
     (positional-argument drift on the 4 dossier emitters, the PR #1056
     regression class), why it exists (spec.md User Story 3 / FR-008), and a
     one-line pointer to the sibling pattern
     (`tests/architectural/test_shared_package_boundary.py`).
  2. Add docstrings to the detector function and each test method explaining
     purpose (mirroring T014-T016's own "Purpose" lines above).
  3. Final structural review: confirm the file has no unused imports, the
     detector function is reasonably named, and the whole file stays well
     under the Sonar complexity ceiling of 15 per function (`CLAUDE.md` §Sonar
     Expectations) — an AST-walk detector can accumulate branching quickly if
     written naively; extract helper functions if any single function
     approaches the ceiling.
- **Files**: `tests/architectural/test_dossier_emitter_positional_guard.py`.
- **Parallel?**: No — final subtask, depends on T014-T016 all being written.
- **Notes**: Estimated total file size ~150-200 lines (detector + clean-tree
  assertion + positive-control fixture + docstrings) per plan.md's PR Shape
  estimate — if your draft is meaningfully larger, look for logic that belongs
  in the detector function rather than duplicated across test methods.

## Test Strategy

- **Scope** (NFR-003): run
  `PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_dossier_emitter_positional_guard.py -q`
  standalone first, then the full targeted surface:
  `PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/ -q`.
- Both new tests (T015's clean-tree assertion, T016's positive control) must
  pass. T016 additionally doubles as this WP's own red-first proof — no
  separate "prove the guard is load-bearing" scaffolding is needed.
- Baseline gate: after this WP's commit, re-run the T001 (WP01) targeted
  surface and diff against the recorded baseline — only newly-red tests beyond
  the baseline are this WP's own regressions to fix before WP04 starts.

## Risks & Mitigations

- **False positives** (detector flags an unrelated call that happens to share
  a name, e.g. a differently-scoped local function also named
  `emit_artifact_indexed`) → scope the AST walk to `src/` only (never `tests/`
  or third-party code) and rely on simple top-level name matching as spec.md's
  design specifies; if a genuine false positive surfaces, narrow the match
  rather than widening an allowlist.
- **Vacuous pass** (detector technically runs but never actually finds
  anything, even the planted violation) → T016 is the direct mitigation; do
  not skip or weaken it.
- **Detector complexity creep** → see T017's Sonar note; extract helpers early
  rather than after the fact.

## Review Guidance

- Confirm the detector is scoped to `src/` only, not the whole repo.
- Confirm T016's planted call matches spec.md's own example (or an equivalent
  clearly-positional 6-argument call) and that the assertion checks for
  **exactly one** violation, not just "at least one" (over-permissive
  assertions can mask a detector that over-fires elsewhere).
- Confirm the file's docstrings actually explain the "why," not just the
  "what" — a future maintainer reading this file cold should understand the
  PR #1056 connection without re-reading spec.md.
- Confirm this file's `create_intent` is honored — it is a genuinely new file,
  not a rename/move of an existing one.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as
the current state. If entries are out of order, acceptance will fail even when
the work is complete.

**Initial entry**:

- 2026-08-22T12:25:40Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use
`spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped
while maintaining lexical ordering.
