---
work_package_id: WP02
title: ScopeSource port + both implementations
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- NFR-004
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-controlled-transition-gates-01KY51Z7
base_commit: 994142d37ec6810151417cbe8534899d8d93b673
created_at: '2026-07-22T16:13:56.410293+00:00'
subtasks:
- T004
- T005
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Foundation
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent:
- src/specify_cli/review/scope_source.py
- tests/review/test_scope_source.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/scope_source.py
- src/specify_cli/review/_interpreter.py
- tests/review/test_scope_source.py
- tests/review/test_pre_review_gate_interpreter.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – ScopeSource port + both implementations

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface` (`src/specify_cli/review/`). A Python implementation lens (e.g. `python-pedro` / `implementer-ivan`) fits — this is the mission keystone and the highest-risk cut.

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

**Keystone / MVP.** Extract the repo-shape-varying scope concerns behind a `typing.Protocol` port, and
land its two implementations — one behaviour-preserving, one portable — so the pre-review gate becomes
layout-agnostic *without* the two impls diverging on the changed-file SSOT. This WP is behaviour-
preserving on its own and front-loads the mission's primary risk (parity of the internal impl).

Complete when:

- **`ScopeSource` Protocol** (`src/specify_cli/review/scope_source.py`, new) declares exactly the three
  repo-shape-varying methods: `test_command()`, `file_to_scope(path)`, `parse_results(run_output)`.
  "Which files changed" is **NOT** on the port — it is the shared canonical merge-base+diff input
  passed to the gate (FR-001). The port mirrors `OrgDoctrineSource`
  (`src/specify_cli/doctrine/sources/protocol.py:53`): `@runtime_checkable`, and **never raises for
  environmental problems** — surfaces them via return value.
- **`GateCoverageScopeSource`** reproduces today's exact behaviour on the Spec-Kitty tree
  (behaviour-preserving, NFR-001): the `_gate_coverage` census scope derivation, the pytest
  `--junitxml`/`-q` injection, the JUnit parse, and the `tests.architectural._gate_coverage` import —
  all encapsulated *inside this impl*. `_is_spec_kitty_source_repo` moves in as a **private internal**
  and **must NOT gate impl selection** (FR-009).
- **`DeclaredCommandScopeSource`** runs the doctrine-declared `review.test_command` over the whole
  suite (no per-file narrowing) and parses its output into a **baseline-relative** verdict: a *newly*
  failing test → `NEW_FAILURES` (blocking-capable); a *pre-existing* baseline failure → NOT blocked.
  A naive `returncode != 0` = ANY_FAILURES parser is **forbidden** (FR-003, NFR-004).
- **`resolve_pytest_command` moves into `_interpreter`** and is consumed *only* by
  `GateCoverageScopeSource`; the interpreter test migrates with it (T007).
- Tests (red-first, all): port contract + both impls (T008), two portable-fidelity fixtures (T009), a
  behaviour-parity micro-golden for the internal scope derivation (T010).

Independent test (per tasks.md): port + both impls unit-tested; **no-config → `NO_COVERAGE`** (visible
warn); the portable path **blocks on a newly-failing command** and does **NOT** block a pre-existing
baseline failure.

Requirements covered: **FR-001, FR-002, FR-003, FR-010, FR-011, FR-012**; **NFR-004** (portable
fidelity, in part). Tracker: **IC-02 = #2595**.

## Context & Constraints

- **Charter**: [`.kittify/charter/charter.md`](../../../.kittify/charter/charter.md) — ATDD-first,
  canonical-sources, single-canonical-authority. The port becomes the *single* test-command authority
  (FR-011), reconciling three drifting resolution sites.
- **Design authorities**: [data-model.md §1](../data-model.md) (port + both impls), [contracts/scope-source-port.md](../contracts/scope-source-port.md)
  (the binding interface + obligations), [spec.md](../spec.md) FR-001/002/003/010/011/012 + NFR-004,
  [plan.md IC-02](../plan.md), [tasks.md WP02](../tasks.md), [post-plan-squad.md](../reviews/post-plan-squad.md)
  (R-F5 baseline-relative, C-C3 config-key misnomer).
- **Pattern to mirror**: `OrgDoctrineSource` at `src/specify_cli/doctrine/sources/protocol.py:53` —
  `@runtime_checkable typing.Protocol`; docstring "Never raise for network/auth/server problems —
  surface them via `FetchResult(ok=False, …)`" (`protocol.py:16-17`). `ScopeSource` follows the same
  discipline: `test_command() -> None` is the no-config signal, **not** an exception.
- **Incumbent code this WP relocates (behaviour-preserving)** — all in
  `src/specify_cli/review/pre_review_gate.py`:
  - `_SRC_PACKAGE_PREFIX = "src/specify_cli/"` (`:104`), `_TESTS_PREFIX` (`:105`),
    `_GATE_COVERAGE_MODULE_NAME = "tests.architectural._gate_coverage"` (`:106`) — the census-narrowing
    inputs `file_to_scope` reproduces.
  - `_is_spec_kitty_source_repo(repo_root)` (`:153`) — the filesystem-presence probe; moves in as a
    **private internal** of `GateCoverageScopeSource`. **MUST NOT gate impl selection** — activation
    does that (WP09's hook). FR-009.
  - `_load_gate_coverage_module` (`:167`) / `importlib.import_module(_GATE_COVERAGE_MODULE_NAME)`
    (`:185`) — the internal import; lives **only** inside `GateCoverageScopeSource`.
  - `GateAuthoritiesUnavailable` (`:120-145`, raised at `:187,193`) — the "unverified scope" signal;
    the internal impl still raises it (WP03/WP09 fold it to a warn). **Do NOT delete `is_consumer_repo`
    here** — that campsite deletion is WP09's (T042); this WP only relocates.
  - `run_scoped_tests_at_head` (`:623`) uses `resolve_pytest_command([*test_targets,
    f"--junitxml={junit_path}", "-q"], repo_root=repo_root)` (`:656-659`) — the `--junitxml`/`-q`
    injection moves *inside* `GateCoverageScopeSource.test_command()` (data-model §1a), off the shared
    runner. `_parse_junit_xml` (defined at `baseline.py:151`) is `parse_results` for the internal impl.
  - `GateOutcome` (`:742-751`) and `GateVerdict` (`:753`) are **unchanged** (owned by WP03/WP09; do not
    edit `pre_review_gate.py` in this WP — it is not in `owned_files`). The port returns
    `BaselineFailure` tuples; verdict *classification* stays in the engine.
- **The command authority today lives in three places (FR-011 reconciliation target)**:
  1. baseline capture — `review/baseline.py:124` `_get_test_command(repo_root)` reads
     `review.test_command` (+ `test_output_format`) from `.kittify/config.yaml`.
  2. head run — `review/_interpreter.py:32` `resolve_pytest_command` (hardcoded pytest argv).
  3. the third override key — `review.pre_review_test_command` (`tasks_move_task.py:785`), which the
     squad verified actually feeds *scope override targets*, not a command (C-C3, misnomer).
  This WP makes the **port** the single authority for "what command proves the change." Consuming it
  from `baseline.py` is **WP03's** T012; aliasing the third key with a deprecation warning is **WP09's**
  T043. Do **not** touch `baseline.py` or `tasks_move_task.py` here (not in `owned_files`).
- **`changed_files` stays off the port** (FR-001): it is the shared merge-base+diff SSOT
  (`core.vcs.git.merge_base_changed_files`, surfaced via `tasks_move_task.py:927`), passed *in* to the
  gate — never a per-impl method, so the two impls cannot diverge on it.
- **Adjacent, OUT of scope — do not re-open**: #2803 (`review.test_command` resolution), #2741 (the
  working-tree-diff bug — inherited, not fixed).
- **Quality bars (NFR-006)**: `mypy --strict` + `ruff` zero issues; cyclomatic complexity **≤15** per
  function (extract helpers — the census narrowing is complex, keep each helper small); **≥90%**
  new-code coverage. Do **NOT** add `# noqa` or `# type: ignore` to pass — fix the code.

## Branch Strategy

- **Strategy**: single mission branch (file-partitioned ownership; each hot file owned by exactly one WP)
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T004 – Define the `ScopeSource` Protocol

- **Purpose**: The injectable contract covering **only** the concerns that vary by repo shape.
- **File (create)**: `src/specify_cli/review/scope_source.py`.
- **Steps**: Author a `@runtime_checkable class ScopeSource(Protocol)` with exactly
  `test_command(self) -> list[str] | None`, `file_to_scope(self, path: str) -> tuple[str, ...]`, and
  `parse_results(self, run_output: RawRunResult) -> tuple[BaselineFailure, ...]` (signatures from
  [contracts/scope-source-port.md](../contracts/scope-source-port.md) + data-model §1). `parse_results`
  takes a **NEW raw-run type** `RawRunResult(returncode, stdout, stderr, output_artifact_path: str |
  None)` — the *unparsed* product of running `test_command()`, **NOT** `HeadRunResult`. `HeadRunResult`
  is the already-**parsed** result (it carries `current_failures` and has no raw field), so it cannot be
  the parser's input; feeding it in would make the portable gate decorative. Define `RawRunResult` in
  `scope_source.py` (a small frozen dataclass). `GateCoverageScopeSource.parse_results` parses JUnit
  from `output_artifact_path`; `DeclaredCommandScopeSource.parse_results` parses the declared command's
  own output (stdout/stderr) — this raw→parsed split is what keeps the portable gate non-decorative.
- **Import-cycle setup (call this out)**: `scope_source.py` MUST start with `from __future__ import
  annotations` and import `_parse_junit_xml` / `GateAuthoritiesUnavailable` / `BaselineFailure` /
  `HeadRunResult` **LAZILY inside method bodies** (never at module top), because WP03 makes
  `pre_review_gate.py` and `baseline.py` import `ScopeSource` back — a two-way cycle. Keep those types
  in their current home and import them lazily; do NOT duplicate the dataclasses.
- **`changed_files` is deliberately absent** — document in the class docstring that it is the shared
  merge-base+diff SSOT passed to the gate, not a port method (FR-001). Add a one-line rationale so a
  future contributor does not "helpfully" add it back.
- **Port-wide invariant**: mirror `OrgDoctrineSource` — the docstring states methods **never raise for
  environmental problems**; `test_command() -> None` is the no-config signal.
- **Notes**: Protocol only — no implementations here. Keep it tiny and dependency-light so both impls
  and the engine (WP03) can import it without cycles. **Parallel?**: precedes T005/T006 (they implement
  it).

### Subtask T005 – `GateCoverageScopeSource` (internal, behaviour-preserving)

- **Purpose**: Reproduce today's exact Spec-Kitty behaviour behind the port — zero behaviour change
  (NFR-001, FR-002).
- **File**: `src/specify_cli/review/scope_source.py`.
- **`test_command()`** → the incumbent pytest argv, **injecting `--junitxml`/`-q` inside this impl**
  (moved from the shared runner at `pre_review_gate.py:656-659`), built via `resolve_pytest_command`
  (now homed in `_interpreter`, T007). Return `list[str]`.
- **`file_to_scope(path)`** → today's `_gate_coverage` census narrowing: the
  `_SRC_PACKAGE_PREFIX="src/specify_cli/"` composite routing + `_TESTS_PREFIX` targets (the derivation
  currently in `pre_review_gate.py` around `derive_test_scope`/`_src_dir_segment` `:250-317`). Reproduce
  the exact mapping — a changed file → its test targets — behaviour-preserving.
- **`parse_results(...)`** → `_parse_junit_xml` (`baseline.py:151`) semantics, reading the JUnit
  artifact from the `RawRunResult.output_artifact_path`.
- **Encapsulate the internals as PRIVATE**: `_load_gate_coverage_module`, the
  `import_module("tests.architectural._gate_coverage")` call, and `_is_spec_kitty_source_repo` become
  private internals of this class/module. A **PRIVATE copy of the runtime `_gate_coverage` import lives
  here** (FR-009). Keep
  `GateAuthoritiesUnavailable` raised on missing/foreign module (behaviour-preserving) — do NOT convert
  it to a warn here (that is the hook's job, WP09). **Do NOT delete `is_consumer_repo`** — WP09 owns
  that campsite deletion; relocating it as-is now would collide with WP09's `owned_files`.
- **`_is_spec_kitty_source_repo` MUST NOT gate impl selection** (FR-009): it may be *used inside* this
  impl (e.g. to fill `is_consumer_repo` on the exception, preserving today's message), but nothing in
  `scope_source.py` may choose *which* `ScopeSource` to instantiate based on it — activation decides
  that in WP09.
- **Complexity ≤15**: the census narrowing is the mission's most complex code. Extract small helpers
  (glob→target, src-dir segment, composite routing) — keep each function ≤15. Add focused unit tests
  for each extracted helper (Sonar new-branch-needs-tests rule) via T008/T010.
- **Notes**: this is *relocation*, not redesign — parity with the current derivation is the whole point.
  Capture the micro-golden (T010) from the current `pre_review_gate.py` derivation **before** moving the
  code, so the golden pins the OLD behaviour (avoid a self-referential oracle).

### Subtask T006 – `DeclaredCommandScopeSource` (portable, baseline-relative)

- **Purpose**: Gate a non-pytest / non-`src/specify_cli/` repo by its own declared command, with a
  **real, baseline-relative** verdict (FR-003, FR-010, NFR-004).
- **File**: `src/specify_cli/review/scope_source.py`.
- **`test_command()`** → `shlex.split(review.test_command)` read from `.kittify/config.yaml`, or `None`
  when unset (no-config → `NO_COVERAGE` warn, FR-012). Read the same config surface `baseline._get_test_command`
  reads (`baseline.py:124-148`) so the authority is consistent (FR-011) — do not invent a new key.
- **`file_to_scope(path)`** → `()` **always** — no per-file narrowing; the declared command runs the
  **whole suite** (layout-agnostic; deliberately does not relocate #2330's narrowing to a non-pytest
  repo).
- **`parse_results(run_output)`** → parse the declared command's real pass/fail into **per-failure
  identities** (`BaselineFailure`s), NOT a bare pass/fail bit. Exit code alone is insufficient identity
  for the baseline diff. A non-zero exit with **unparseable** output → the whole run counts as failing
  (surfaced, never swallowed). **Forbidden**: `parse_results = returncode != 0` (ANY_FAILURES) — it
  would block a consumer with a pre-existing red suite on *every* transition (a false-positive gate,
  squad R-F5).
- **Baseline-relative semantics (load-bearing, NFR-004)**: `NEW_FAILURES` keeps its incumbent meaning —
  *new vs baseline*. The portable path captures its baseline by running the **same declared command
  through the same port** (same `test_command()` / `parse_results()`) and persisting the parsed
  identities (like the internal path's `baseline-tests.json`); the gate diffs head vs that baseline. A
  failure present at baseline → pre-existing → does NOT block; absent at baseline but present at head →
  new → blocks. **This WP provides the parser and the identities**; the head↔baseline *diff/verdict
  classification* is the engine's (WP03) — expose `parse_results` so `baseline.py` (WP03 T012) and the
  head run consume one authority.
- **Obligation**: never imports `_gate_coverage`; never assumes pytest or a `src/specify_cli/` layout.
- **Complexity ≤15**: keep the parser small; extract an output-format dispatch helper if you support
  more than one (`test_output_format` in config, `baseline.py:143`).
- **Notes**: the two impls share the port but not `changed_files` — assert (in T008) that neither impl
  exposes a `changed_files` method, so the SSOT stays off the port.

### Subtask T007 – Move `resolve_pytest_command` into `_interpreter`; migrate the interpreter test

- **Purpose**: Make the pytest-invocation resolver an internal detail consumed *only* by
  `GateCoverageScopeSource`, not a cross-cut of the shared runner.
- **Files**: `src/specify_cli/review/_interpreter.py` (owned), `tests/review/test_pre_review_gate_interpreter.py`
  (owned — migrate, do not delete-to-green).
- **Steps**: `resolve_pytest_command` already lives in `src/specify_cli/review/_interpreter.py:32`
  (it is `__all__ = ["resolve_pytest_command"]`). Confirm its consumer is now
  `GateCoverageScopeSource.test_command()` (T005) rather than `run_scoped_tests_at_head`
  (`pre_review_gate.py:656`). If `_interpreter.py` needs adjustment so the internal impl is its sole
  consumer, make it here; keep the resolution order (uv-run-if-project-else-sys.executable, `:47-49`)
  behaviour-preserving. **Migrate** `test_pre_review_gate_interpreter.py:36-73` (asserts
  `resolve_pytest_command` branch behaviour) to point at the relocated seam — the port supersedes the
  old call path, but the *branch behaviour* (uv present + pyproject → uv run; else sys.executable) must
  still be tested. Migration-red ≠ regression-red: note in the Activity Log that these tests moved
  because the consumer moved, not because behaviour changed.
- **Notes**: Do NOT edit `pre_review_gate.py` (not owned). If `run_scoped_tests_at_head` must stop
  calling `resolve_pytest_command` directly, that call-site change is **WP03's** (it owns
  `pre_review_gate.py`); coordinate by having the internal impl expose the full argv via
  `test_command()` and let WP03 consume it. This WP's boundary is `_interpreter.py` + `scope_source.py`
  + the two owned tests.

### Subtask T008 – `test_scope_source.py` (port contract + both impls + no-config)

- **Purpose**: The red-first contract test for the port and both implementations.
- **File (create)**: `tests/review/test_scope_source.py`.
- **Steps** (author red-first, before/against the impls):
  - **Port contract**: assert both impls satisfy `isinstance(impl, ScopeSource)` (runtime-checkable) and
    expose exactly the three methods; assert neither exposes a `changed_files` method (SSOT-off-port
    guard, FR-001).
  - **`GateCoverageScopeSource`**: `test_command()` includes `--junitxml`/`-q` (injected inside the
    impl); `file_to_scope` reproduces census narrowing for representative paths; `parse_results` parses
    a sample JUnit XML into failures.
  - **`DeclaredCommandScopeSource`**: `test_command()` returns `shlex.split` of a configured
    `review.test_command`; **no-config → `test_command() -> None`** and the gate surfaces a visible
    `NO_COVERAGE` warn (GUARD — "no-config → visible NO_COVERAGE", never a silent green);
    `file_to_scope` always returns `()`; `parse_results` yields per-failure identities and treats an
    unparseable non-zero exit as whole-run-failing.
- **Run**: `PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_scope_source.py -q`.
- **Notes**: the no-config guard is a named mission guard — make it an explicit, independently named test
  so a reviewer can see it. ≥90% coverage of the new module comes primarily from here + T009 + T010.

### Subtask T009 – Portable-verdict fidelity fixtures (baseline-relative)

- **Purpose**: Prove the portable path is **baseline-relative**, not `ANY_FAILURES` (NFR-004, the named
  mission guard "portable-verdict baseline-relative fidelity — 2 fixtures").
- **File**: `tests/review/test_scope_source.py` (or a sibling fixture module under `tests/review/`).
- **Two fixtures (both red-first)**:
  1. **Newly-failing** — a non-pytest/non-JUnit consumer whose declared command's suite has a test
     *absent at baseline but failing at head* → `parse_results` + diff yields a blocking-capable
     `NEW_FAILURES` (proves results are *parsed*, not that the process merely ran).
  2. **Pre-existing failure** — a consumer whose suite is *already red at baseline* → the same red at
     head is classified pre-existing → **NOT blocked** (proves baseline-relative semantics, no
     false-positive block).
- **Portable fidelity**: use a genuinely non-pytest-shaped command (e.g. a shell script emitting a
  known non-JUnit format, or a fake command whose output the parser reads) so the fixtures prove the
  layout-agnostic path, not an accidentally-pytest one.
- **Notes**: the head↔baseline diff/classification may live in the engine (WP03); if so, exercise
  `parse_results` here for the *identity extraction*, and assert the classification in WP03's tests —
  but the two fixtures' *data* (newly-failing vs pre-existing) originate here so the port's contribution
  is proven. Name the fixtures explicitly (`newly_failing`, `pre_existing_failure`) — the reviewer
  looks for both.

### Subtask T010 – Behaviour-parity micro-golden for internal scope derivation

- **Purpose**: Pin `GateCoverageScopeSource`'s scope derivation to the OLD `pre_review_gate.py`
  behaviour so the relocation is provably behaviour-preserving (the mission guard "micro-parity for
  internal scope derivation").
- **File**: `tests/review/test_scope_source.py` (or a golden fixture under `tests/review/`).
- **Steps**: capture a **micro-golden** — a small set of representative changed-file inputs → expected
  `test_targets` — from the **current** `derive_test_scope` / `file_to_scope` behaviour *before* the
  code moves (avoid a self-referential oracle: snapshot the OLD derivation, then assert the new impl
  reproduces it). Cover: a `src/specify_cli/<pkg>/` file (composite routing), a `tests/**` file (direct
  target), a top-level `src/specify_cli/<file>.py` (no owning dir → `()`), and an excluded/catch-all
  path (empty scope → the caller's `NO_COVERAGE`). Assert the new impl yields identical targets.
- **Notes**: this is the *internal* parity guard; the *through-the-hook* parity golden captured from
  base `e4ef6e850` is WP08's (T037/T038) — do not duplicate it. Keep this micro and deterministic.

## Test Strategy

- **ATDD red-first**: author T008/T009/T010 to fail against the not-yet-written impls, then implement
  T004-T007 until green. Migration-red in `test_pre_review_gate_interpreter.py` (T007) is expected and
  must be labelled distinct from regression-red in the Activity Log.
- **Run** (parallel-safe locally):
  ```bash
  PYTHONPATH=$(pwd)/src PWHEADLESS=1 pytest tests/review/test_scope_source.py tests/review/test_pre_review_gate_interpreter.py -q
  ```
- **Quality gates** (all must be zero-issue, no suppressions):
  ```bash
  ruff check src/specify_cli/review/scope_source.py src/specify_cli/review/_interpreter.py
  mypy --strict src/specify_cli/review/scope_source.py
  ```
- **Coverage**: ≥90% new-code line coverage on `scope_source.py`; each extracted helper has a focused
  test executing its branches (Sonar new-branch rule).
- **Named guards to make visible**: no-config → `NO_COVERAGE`; baseline-relative fidelity (2 fixtures);
  SSOT-off-port (`changed_files` absent from both impls); micro-parity for the internal derivation.

## Risks & Mitigations

- **Behaviour-parity (highest risk)**: the internal impl must reproduce today's exact scope derivation +
  pytest/JUnit path or the whole strangler regresses at the base. Mitigation: T010 micro-golden captured
  from the OLD derivation; relocation not redesign.
- **Verdict-fidelity trap (#2330 relocation)**: the portable parser must turn a failing non-JUnit suite
  into blocking-capable `NEW_FAILURES`, never collapse to `NO_COVERAGE`. Mitigation: T009 newly-failing
  fixture; `parse_results` yields identities not a bit; ANY_FAILURES parser explicitly forbidden.
- **False-positive block for pre-existing-red consumers**: an absolute (non-baseline) verdict blocks on
  every transition. Mitigation: baseline-relative semantics + the pre-existing-failure fixture (T009).
- **Test-command SSOT drift (FR-011)**: three resolution sites hide drift. Mitigation: this WP makes the
  port the single authority; `DeclaredCommandScopeSource.test_command()` reads the same config surface
  as `baseline._get_test_command`; WP03/WP09 wire the remaining consumers.
- **Impl-selection leak (FR-009)**: `_is_spec_kitty_source_repo` must never choose the impl. Mitigation:
  it is a private internal only; add a test asserting nothing in `scope_source.py` selects an impl by
  repo shape (selection is activation-driven, WP09).
- **Cross-WP file collision**: do not edit `pre_review_gate.py`, `baseline.py`, or `tasks_move_task.py`
  (owned by WP03/WP09). Mitigation: expose everything the engine needs through the port surface.

## Review Guidance

- **Port shape exact** — three methods, `changed_files` absent, `@runtime_checkable`, mirrors
  `OrgDoctrineSource` (never raises for env; `None` = no-config).
- **Internal impl behaviour-preserving** — micro-golden green; `--junitxml`/`-q` injected inside the
  impl; a **PRIVATE copy of the runtime `_gate_coverage` import lives here** — the always-on import in
  `pre_review_gate.py` is removed by **WP03 T011**, so do NOT verify its absence at WP02 acceptance.
  (`_gate_coverage` is a runtime `importlib.import_module` after `sys.path.insert`, so relocating it
  needs no move of the `tests/` authority and creates no static cycle.) `_is_spec_kitty_source_repo`
  private and NOT a selector.
- **Portable impl baseline-relative** — both fidelity fixtures present and green; ANY_FAILURES parser
  absent; `file_to_scope` always `()`; no `_gate_coverage` import, no pytest assumption.
- **No-config → visible `NO_COVERAGE`** — explicit named test.
- **`is_consumer_repo` NOT deleted here** — that is WP09; this WP only relocates.
- **Quality** — `mypy --strict` + `ruff` zero issues, complexity ≤15, ≥90% new coverage, no `# noqa` /
  `# type: ignore`.

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
