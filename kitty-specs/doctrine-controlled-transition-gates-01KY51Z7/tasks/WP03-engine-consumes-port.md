---
work_package_id: WP03
title: Pre-review engine consumes the port
dependencies:
- WP02
requirement_refs:
- FR-010
- FR-011
- FR-012
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 2 - Engine
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: "python-pedro"
authoritative_surface: src/specify_cli/review/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/pre_review_gate.py
- src/specify_cli/review/baseline.py
- tests/review/test_pre_review_gate_engine.py
- tests/review/test_pre_review_gate_integration.py
role: "implementer"
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Pre-review engine consumes the port

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface` (`src/specify_cli/review/`). A Python implementation lens (e.g. `python-pedro` / `implementer-ivan`) fits.

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

Refactor `pre_review_gate.py` into a **thin engine** that consumes an injected `ScopeSource` (from WP02)
for **both** baseline capture and the head run, remove the always-on `_gate_coverage` import (now lives
inside `GateCoverageScopeSource`), and make `baseline.py` use the single command authority via the port.

Complete when:

- **`pre_review_gate.py` consumes an injected `ScopeSource`** for baseline **and** head evaluation — the
  engine calls `scope_source.test_command()` / `file_to_scope()` / `parse_results()` rather than the
  hardcoded pytest/JUnit/census path. The engine becomes a **thin orchestrator**; the repo-shape-varying
  logic lives behind the port (FR-010, FR-012).
- **The always-on `import tests.architectural._gate_coverage` is removed** from `pre_review_gate.py` —
  it is reachable *only* inside `GateCoverageScopeSource` (WP02). The engine no longer imports it at
  module load or unconditionally at evaluation time.
- **`baseline.py` uses the port as the single test-command authority** (FR-011) — baseline capture runs
  the **same** command the head run uses (via the injected `ScopeSource`), so baseline↔head symmetry is
  structural, not coincidental. `_get_test_command` (`baseline.py:124`) is reconciled to route through
  the port rather than re-reading config independently.
- **An injected-`ScopeSource` seam** is in place so impl *selection* is activation-driven — the final
  selection lands in **WP09's** hook; WP03 provides the injection point (a parameter/factory the hook
  will call), it does **not** decide which impl by repo shape.
- **Incumbent tests migrated (not silenced)**: `test_pre_review_gate_engine.py` (the probe → private-
  internal contract) and `test_pre_review_gate_integration.py` (the runner), per the plan's
  "Existing tests to migrate" table.
- **#2330 pre-review-facet closure test**: a non-pytest layout runs its declared command through the
  engine and yields a real verdict (T015).

Independent test (per tasks.md): engine parity on the spec-kitty tree via `GateCoverageScopeSource`; a
non-pytest layout gated via `DeclaredCommandScopeSource`.

Requirements covered: **FR-010, FR-011, FR-012**. Related tracker: **#2595** (IC-02 continues here).

## Context & Constraints

- **Charter**: [`.kittify/charter/charter.md`](../../../.kittify/charter/charter.md) — ATDD-first,
  single-canonical-authority (the port is the sole command authority), test-remediation discipline
  (migrate incumbent tests red-then-forward, never delete-to-green).
- **Design authorities**: [data-model.md §1](../data-model.md) (port consumption), [contracts/scope-source-port.md](../contracts/scope-source-port.md)
  (port obligations 2-3: `changed_files` shared, sole command authority), [spec.md](../spec.md)
  FR-010/011/012, [plan.md IC-02](../plan.md) + the "Existing tests to migrate" table, [tasks.md WP03](../tasks.md),
  [post-plan-squad.md](../reviews/post-plan-squad.md) (P-F2 migration-red ≠ regression-red).
- **Depends on WP02** — the `ScopeSource` Protocol + both impls + relocated `resolve_pytest_command`
  must be `approved`/`done` before this WP is claimed (dependency gating). This WP *consumes* WP02's
  port; it must not re-declare the port or duplicate the impls.
- **Incumbent code this WP owns/edits**:
  - `src/specify_cli/review/pre_review_gate.py` — remove the always-on `_gate_coverage` import
    (`:106,167,185`); the scope-derivation helpers (`derive_test_scope` `:317`, `_src_dir_segment`
    `:250`, etc.) and the `--junitxml`/`-q` injection in `run_scoped_tests_at_head` (`:656`) moved to
    `GateCoverageScopeSource` in WP02 — the engine now drives them **through the port**. Keep
    `GateOutcome` (`:742-751`), `GateVerdict` (`:753`), `evaluate_with_scope` (`:765`) as the verdict
    classification surface (owned here), but source scope/command/parse from the injected `ScopeSource`.
  - `src/specify_cli/review/baseline.py` — `_get_test_command` (`:124`) and `capture_baseline` route
    through the port so baseline capture uses the same authority as the head run (FR-011).
- **What WP03 DOES vs does NOT do**: WP03 **deletes `_is_spec_kitty_source_repo`** (the source-repo
  probe in its own `pre_review_gate.py`) — dead once impl selection is activation-driven/injected
  (T013). But WP03 does **not** delete the `GateAuthoritiesUnavailable.is_consumer_repo` **field** or
  `_PRE_REVIEW_CONSUMER_REPO_REASON` — **keep the field** (WP09's reader in `tasks_move_task.py` still
  needs it until WP09 lands, and its T042 cleanup only removes the reader — the field's cross-file
  retirement is a fast-follow). It does **not** invert the hook or touch `tasks_move_task.py` (WP09);
  it does **not** build the registry (WP04) or bindings (WP05/06). WP03's boundary is: the engine +
  baseline consume the port, the probe is removed, and the two named tests migrate. Keep
  `GateAuthoritiesUnavailable` raised inside the internal impl (folded to a warn by the hook in WP09).
- **`changed_files` stays the shared SSOT** (FR-001, port obligation 2): the engine receives the
  merge-base+diff changed-files list and passes it to `file_to_scope` per element — it is not re-derived
  and not a port method.
- **Adjacent, OUT of scope — do not re-open**: #2801/#2573 (skip-flag/disable-env seam,
  `tasks_move_task.py:854-876`), #2803 (`review.test_command` resolution), #2741 (working-tree-diff bug
  — inherited, preserved by parity, not fixed).
- **Quality bars (NFR-006)**: `mypy --strict` + `ruff` zero issues; cyclomatic complexity **≤15** per
  function (the engine must get *thinner*, not fatter — extract helpers); **≥90%** new-code coverage. No
  `# noqa` / `# type: ignore` to pass.

## Branch Strategy

- **Strategy**: single mission branch (file-partitioned ownership; each hot file owned by exactly one WP)
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T011 – Refactor `pre_review_gate.py` to consume a `ScopeSource` (baseline + head)

- **Purpose**: Make the engine a thin orchestrator over the injected port; drop the always-on internal
  import (FR-010).
- **File**: `src/specify_cli/review/pre_review_gate.py`.
- **Steps**:
  - Change the engine entry points (`evaluate_pre_review_gate` / `evaluate_with_scope` and the head-run
    path) to take a `scope_source: ScopeSource` and drive scope/command/parse through it:
    `file_to_scope(path)` for each `changed_files` element, `test_command()` for the head argv,
    `parse_results(run_output)` for failures. The verdict *classification* (`GateOutcome`, the
    baseline diff → `NEW_FAILURES`/`NO_NEW_FAILURES`/`NO_COVERAGE`/`UNVERIFIED_BASELINE`) stays in the
    engine — the port supplies inputs, the engine decides the outcome.
  - **Remove the always-on `_gate_coverage` import** (`:106` constant usage, `:167` loader, `:185`
    `import_module`). Those now live *only* inside `GateCoverageScopeSource` (WP02). The engine must not
    import `tests.architectural._gate_coverage` at module load or unconditionally at eval time —
    reachability is via the injected port only (FR-009 structural closure begins here, completes in
    WP09).
  - Keep `evaluate_with_scope`'s "empty scope → `NO_COVERAGE`, never clean" invariant (`:797-798`) — a
    port returning no targets still yields a visible warn.
  - The engine runs `scope_source.test_command()` and produces a `RawRunResult` (the **unparsed** run
    — `returncode`/`stdout`/`stderr`/`output_artifact_path`), then hands it to
    `scope_source.parse_results(raw)` for the failure identities. The engine does NOT parse output
    itself — parsing is the port's job (WP02).
  - **Delete `_is_spec_kitty_source_repo`** (the source-repo probe) from `pre_review_gate.py` — dead
    once selection is injected (T013). **Keep** the `GateAuthoritiesUnavailable.is_consumer_repo`
    field for now (WP09's reader depends on it until WP09 lands; the field's cross-file retirement is a
    fast-follow, not this WP).
- **Complexity ≤15**: the engine should shrink. If a function creeps toward 16, extract a lookup/build/
  emit helper and unit-test it directly (T014).
- **Notes**: this is the head↔baseline symmetry keystone — both sides evaluate through the same injected
  port. Do not leave a second, hardcoded command path behind for baseline.

### Subtask T012 – `baseline.py` single test-command authority via the port

- **Purpose**: Baseline capture runs the **same** command as the head run, sourced from the port
  (FR-011) — no independent re-resolution.
- **File**: `src/specify_cli/review/baseline.py`.
- **Steps**: Route `_get_test_command` (`:124`) / `capture_baseline` through the injected `ScopeSource`
  so baseline capture uses `scope_source.test_command()` and `scope_source.parse_results()` — the same
  authority the head run uses. Preserve the current opt-in-and-visible behaviour: no command configured
  → capture is skipped with a **visible** notice (the incumbent "No review.test_command configured;
  skipping", ~`baseline.py:244`), which the engine surfaces as `NO_COVERAGE` (FR-012), never a silent
  green. For the portable impl, baseline is captured by running the declared command through the port
  and persisting parsed identities (the baseline-relative substrate WP02 T009 exercises).
- **Notes**: keep the `test_output_format` handling (`:143`) working — it is part of the declared-command
  parse contract. Do not change the on-disk `baseline-tests.json` shape unless the port's identities
  require it; if they do, keep it backward-readable.

### Subtask T013 – Injected-`ScopeSource` seam (activation-driven selection groundwork)

- **Purpose**: Provide the injection point so **WP09's hook** can select the impl by *activation*, not
  by repo shape (FR-009).
- **File**: `src/specify_cli/review/pre_review_gate.py` (and `baseline.py` as needed).
- **Steps**: Make `scope_source` an injected parameter (or a small factory the caller provides) on the
  engine + baseline entry points. WP03 must **not** decide which impl to instantiate based on
  `_is_spec_kitty_source_repo` or any repo-shape probe — the seam is *open* for the hook to fill. If a
  default is needed for existing call-sites to keep compiling, default to a factory that WP09 will
  replace; do not bake in a shape-based selector. Document (docstring + a test in T014) that impl
  selection is deferred to activation.
- **Notes**: this is the "final selection lands in WP09's hook" seam — keep it a clean parameter, not a
  hidden global. The negative guard (nothing here selects by repo shape) is testable.

### Subtask T014 – Migrate the engine + integration tests (migrate, not silence)

- **Purpose**: Bring the incumbent test corpus forward to the port contract without green-washing
  (P-F2: migration-red must be distinguishable from regression-red).
- **Files**: `tests/review/test_pre_review_gate_engine.py`, `tests/review/test_pre_review_gate_integration.py`
  (both owned).
- **Steps**:
  - `test_pre_review_gate_engine.py:100-127` asserts the `_is_spec_kitty_source_repo` **public** probe +
    `is_consumer_repo=True` contract. Migrate it to the **private-internal** contract: the probe is now
    an internal of `GateCoverageScopeSource` (WP02) and MUST NOT be a public selector. Rewrite the test
    to assert the engine drives the injected port and does not import `_gate_coverage` unconditionally.
    (Full retirement of the `is_consumer_repo`-message assertions co-lands with WP09's erroneous-
    activation closure — coordinate so WP03 does not assert a contract WP09 then deletes.)
  - `test_pre_review_gate_integration.py:171,228,391,955` exercises the real-git
    `run_scoped_tests_at_head` runner (and writes `pre_review_test_command:` / binds
    `_mt_run_pre_review_gate`). Migrate the **runner** portions to the port-driven engine here; the
    **hook-binding** portions (`_mt_run_pre_review_gate` name) migrate in **WP09** (thin alias). Split
    the file's concerns cleanly: what is engine/runner (WP03) vs what is hook (WP09).
  - Add focused tests for any extracted engine helper (Sonar new-branch rule) and for the
    injected-seam-not-a-shape-selector guard (T013).
- **Notes**: label every migration-red in the Activity Log as "moved because the consumer moved" so the
  reviewer does not read it as a regression. Do **not** delete assertions to make the suite green —
  rewrite them against the new contract.

### Subtask T015 – #2330 pre-review-facet closure test (non-pytest layout)

- **Purpose**: Prove a non-pytest / non-`src/specify_cli/` layout is genuinely gated by its declared
  command through the engine (the #2330 pre-review-facet closure, GUARD).
- **File**: `tests/review/test_pre_review_gate_engine.py` (or a sibling under `tests/review/`).
- **Steps**: Construct a simulated non-pytest checkout (no `tests/architectural/_gate_coverage.py`, a
  non-`src/specify_cli/` layout) with a declared `review.test_command`, inject a
  `DeclaredCommandScopeSource`, and assert the engine: (a) runs the declared command; (b) **parses** its
  output into a real verdict (a failing suite → blocking-capable `NEW_FAILURES`, NOT a silent
  `NO_COVERAGE`); (c) **never imports** `tests.architectural._gate_coverage`. Assert the import-never
  claim structurally (e.g. the module is absent from `sys.modules` after the run, or patch
  `importlib.import_module` to fail loudly if the internal name is requested).
- **Steps (pre-existing-not-blocked arm — R-F5 guard, ADD):** a `DeclaredCommandScopeSource` consumer
  whose declared suite is **red AT BASELINE**, run through the engine's head↔baseline diff, asserting
  the outcome is `NO_NEW_FAILURES` / **non-blocking**. Without this arm the false-positive-block
  regression (a pre-existing red suite blocking every transition) ships **untested** — it is currently
  asserted nowhere. Name it explicitly (`pre_existing_not_blocked`) in Review Guidance.
- **Notes**: this is the engine-level facet of SC-001; the *through-the-hook* + *erroneous-activation*
  closure is **WP09 T046**. Keep this one at the engine boundary. The "declared-command runs, output
  parsed, real verdict" assertion is the anti-#2330 core — do not settle for "the process ran."

## Test Strategy

- **ATDD red-first**: migrate/author T014 + T015 to red against the pre-refactor engine, then refactor
  T011-T013 until green. Distinguish migration-red (consumer moved) from regression-red (behaviour
  changed) in the Activity Log — a regression-red is a stop-and-fix, a migration-red is expected.
- **Run**:
  ```bash
  PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_pre_review_gate_engine.py tests/review/test_pre_review_gate_integration.py -q
  ```
  Real-git / real-runner integration tests may need a serial pass (`-n0`) if they use OS-global
  resources — follow the parallel-run rules in `docs/development/testing-parallel.md`.
- **Quality gates** (zero-issue, no suppressions):
  ```bash
  ruff check src/specify_cli/review/pre_review_gate.py src/specify_cli/review/baseline.py
  mypy --strict src/specify_cli/review/pre_review_gate.py src/specify_cli/review/baseline.py
  ```
- **Coverage**: ≥90% on the changed engine/baseline code; extracted helpers tested directly.
- **Named guards to make visible**: migrate-not-silence (T014); #2330 closure (T015 — declared command
  runs, output parsed, `_gate_coverage` never imported).
- **Baseline-red gotcha**: a broad local run will show pre-existing P0 reds that are NOT yours — classify
  before fixing (CLAUDE.md test-run baseline-red gotcha). Only failures red on this branch AND green on
  the merge-base are yours.

## Risks & Mitigations

- **Silent-import regression**: if the engine keeps *any* unconditional `_gate_coverage` import path, the
  #2534 pre-review-facet closure does not begin. Mitigation: T015 asserts the import never happens under
  the portable impl; grep the engine for the module name after the refactor.
- **Baseline↔head asymmetry (FR-011)**: leaving baseline on a separate hardcoded command reintroduces the
  drift the mission closes. Mitigation: T012 routes baseline through the same injected port; a test
  asserts both sides use the same command.
- **Over-reaching into WP09's surface**: deleting `is_consumer_repo` machinery or touching
  `tasks_move_task.py` here collides with WP09's `owned_files` and breaks the compat surface prematurely.
  Mitigation: WP03 keeps `GateAuthoritiesUnavailable` as-is and never edits the hook.
- **Green-washing migrated tests**: deleting assertions to pass is a charter violation (test-remediation
  discipline). Mitigation: rewrite against the new contract; label migration-red explicitly.
- **Complexity creep**: pushing port-driving logic inline fattens the engine. Mitigation: extract
  lookup/build/emit helpers, each ≤15 and unit-tested.

## Review Guidance

- **Engine is thin** — scope/command/parse come from the injected `ScopeSource`; the engine only
  classifies the verdict. No unconditional `_gate_coverage` import remains.
- **Baseline uses the port** — baseline capture and head run share one command authority (FR-011);
  no-command → visible `NO_COVERAGE`, never silent green.
- **Injected seam, not a shape-selector** — impl selection is deferred to WP09; nothing here picks an
  impl by repo shape (FR-009).
- **Tests migrated, not silenced** — the probe test asserts the private-internal contract; the
  integration runner tests are port-driven; hook-name bindings deferred to WP09; migration-red labelled.
- **#2330 closure at the engine** — non-pytest declared command runs, output parsed into a real verdict,
  `_gate_coverage` never imported.
- **Pre-existing-not-blocked (R-F5)** — the `pre_existing_not_blocked` arm (T015): a suite red at
  baseline diffed head↔baseline yields `NO_NEW_FAILURES` / non-blocking; reject the WP if this arm is
  missing.
- **Quality** — `mypy --strict` + `ruff` zero issues, complexity ≤15, ≥90% new coverage, no
  `# noqa` / `# type: ignore`.

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

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- {{TIMESTAMP}} – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.
