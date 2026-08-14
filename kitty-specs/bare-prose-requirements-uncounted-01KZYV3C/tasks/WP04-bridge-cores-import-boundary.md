---
work_package_id: "WP04"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
  - "T019"
title: "Baseline Capture & Architectural Import-Boundary Test for runtime_bridge_cores.py"
task_type: "implement"
phase: "Phase 0/1 - Baseline & Foundation (sequential, first)"
execution_mode: "code_change"
owned_files:
  - "tests/architectural/test_bridge_cores_import_boundary.py"
authoritative_surface: "tests/architectural/"
create_intent:
  - "tests/architectural/test_bridge_cores_import_boundary.py"
dependencies: []
agent_profile: ""
role: ""
agent: ""
model: ""
assignee: ""
shell_pid: ""
history:
  - at: "2026-08-14T02:50:21Z"
    actor: "system"
    action: "Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)"
  - at: "2026-08-14T00:00:00Z"
    actor: "claude"
    action: "Fix 1 (issue #3396 fixer pass, ledger SK-24): folded WP01 (Baseline Capture & Pre-Existing Failure Audit, T001-T007) into this WP — WP01 was execution_mode planning_artifact with owned_files [], which finalize-tasks/compute_lanes cannot represent. WP04 absorbs WP01 and now runs first, alone; WP02 and WP03 depend on WP04 instead of WP01 but remain parallel with each other. See tracer-design-decisions.md for the full placement rationale."
---

# Work Package Prompt: WP04 – Baseline Capture & Architectural Import-Boundary Test for `runtime_bridge_cores.py`

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, or select via `spec-kitty agent profile list` for an
`implement`-typed WP on `tests/architectural/`.

---

## Objectives & Success Criteria

**This WP now carries two objectives, folded together by the Fix 1 restructure (issue
#3396 fixer pass, ledger SK-24) — WP01's baseline capture (T001-T007) runs FIRST, as a
sequential prefix, before T019's test-file addition, since the baseline must be
captured before ANY change lands, including this WP's own new test file.**

**Objective A (T001-T007, folded from WP01) — Baseline Capture & Pre-Existing Failure
Audit**: Establish this mission's real RED/GREEN starting point **before any code
change lands**, per plan.md's "Baseline Capture on `ab15225ea`" section — verbatim
procedure, not the CLI-computed (and here, wrong) `planning_base_branch`. Done means: a
recorded red-test-ID list from `ab15225ea`, an explicit diff verdict against issue
#3284's ~23-known-red-on-`main` set, and (if any newly-discovered pre-existing failure
exists) an upstream GitHub issue filed before it is treated as accepted baseline — per
the charter's Pre-existing Failure Reporting Rule. No production code changes happen in
T001-T007; the deliverable is a recorded finding, appended to
`tracer-tooling-friction.md` and/or `tracer-approach.md`.

**Objective B (T019, WP04's original scope) — Architectural Import-Boundary Test**:
Implement IC-08 (plan.md, C-007): pin `runtime_bridge_cores.py`'s self-declared
"zero-dependency leaf" invariant by construction — stdlib + `runtime.next.decision`
only — so a future cross-package import (including one this mission's own WP05 might
accidentally introduce) is caught mechanically, not by convention.

Success: (A) the recorded red set, #3284 diff verdict, and any filed issue links are
present in `tracer-tooling-friction.md`; (B) the new test passes against the current,
unmodified `src/runtime/next/runtime_bridge_cores.py`, and a synthetic non-stdlib,
non-`runtime.next.decision` import inserted into a scratch copy fails the same test.

## Context & Constraints

- **Baseline capture (T001-T007) constraints, folded from WP01**: Read
  `.kittify/charter/charter.md`'s Pre-existing Failure Reporting Rule and the "⚠️
  Test-run baseline-red gotcha" section of `CLAUDE.md` before starting. Read plan.md's
  "Baseline Capture on `ab15225ea`" section in full — it contains the exact procedure
  and the falsifiability note (PLAN-VERIFY-003) about verifying commit shapes live, not
  from a stale count. **This mission's real baseline is `ab15225ea`** (tip of
  `origin/op/3394-requirement-citation-scope`), NOT `main`. `spec-kitty plan --json`'s
  own `planning_base_branch` field is wrong for this mission's topology (documented
  tooling gap — see `tracer-tooling-friction.md`). Do not trust that CLI-reported value
  for this one mission.
- Read plan.md's C-007 section and its "Architecture" subsection on
  `BareProseRequirementFacts` — this test protects exactly the invariant that section
  depends on.
- `runtime_bridge_cores.py`'s own module docstring (lines 1-68) already states this
  invariant; its current top-of-file imports (lines 70-77) are confirmed stdlib +
  `runtime.next.decision` only.
- This WP does **not** modify `runtime_bridge_cores.py` — it only adds a test that
  reads it.
- **ATDD/C-011 applicability (mirrors WP02's and WP08's own disclosure)**: this WP ships
  a new architectural test with no accompanying production behaviour change, so charter
  C-011's literal failing-first-separate-commit form does not apply — there is no
  user-observable behaviour to pin RED against. The test's own negative-case
  verification (a synthetic bad import manually confirmed, once during development, to
  fail the test, then reverted — see Test Strategy) is the substitute regression
  evidence. This is a tasks-authoring judgment call, same as WP02's; record it as such
  if challenged in review.
- Follow the existing repo-wide precedent shape for this kind of test:
  `tests/architectural/test_kernel_no_doctrine_import.py`,
  `tests/architectural/test_charter_no_specify_cli_import.py`,
  `tests/architectural/test_clock_import_ban.py` — read one of these for the AST-walk
  pattern to copy, not invent from scratch (charter's "use canonical sources" rule).

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `pr/bare-prose-requirements-uncounted`;
  completed changes must merge back into `pr/bare-prose-requirements-uncounted`
  (base `op/3394-requirement-citation-scope` @ `ab15225ea`).
- **Planning base branch**: `pr/bare-prose-requirements-uncounted`.
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

## Subtasks & Detailed Guidance

**Run T001-T007 to completion FIRST, as their own commit-free verification pass,
before starting T019** — the baseline must be captured before any change (including
this WP's own new test file) lands.

### Subtask T001 – Create the baseline worktree

- **Purpose**: Isolate the `ab15225ea` checkout from the mission's own working tree.
- **Steps**: `git worktree add /tmp/baseline-ab15225ea ab15225ea` (or an isolated clone
  if a worktree is inconvenient in this environment).
- **Files**: None (git metadata only).
- **Parallel?**: No.

### Subtask T002 – Install dependencies

- **Purpose**: A fresh checkout needs its own environment.
- **Steps**: `cd /tmp/baseline-ab15225ea && uv sync --all-extras`.
- **Notes**: Do not skip `--all-extras` — some targeted test surface directories
  depend on optional extras.

### Subtask T003 – Run the Targeted Test Surface

- **Purpose**: Measure the actual baseline red set, not an assumed one.
- **Steps**:
```bash
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/specify_cli/test_requirement_mapping.py \
  tests/specify_cli/test_requirement_mapping_coord_surface.py \
  tests/next/ tests/specify_cli/next/ tests/runtime/ \
  -n 8 --dist loadfile -q
```
- **Notes**: **NEVER `-n auto`** — deadlocks this 24-core box (repo-wide documented
  trap, `CLAUDE.md`). Always `-n 8 --dist loadfile`.

### Subtask T004 – Record the red set

- **Purpose**: Durable evidence for the #3284 diff and for later WPs' own RED
  verification to compare against.
- **Steps**: Capture the red count and every failing test ID verbatim (copy the pytest
  summary output).

### Subtask T005 – Diff against issue #3284

- **Purpose**: Plan.md explicitly forbids assuming the `ab15225ea` red set matches
  #3284's `main`-measured ~23-known-red set — `ab15225ea` carries #3395's unreviewed
  ~863-line rewrite that `main` does not.
- **Steps**: Compare T004's list against #3284's named tests by ID. State explicitly,
  in `tracer-tooling-friction.md` (append, do not recreate), whether the sets match. If
  they diverge, name the delta.

### Subtask T006 – File upstream issues for new pre-existing reds

- **Purpose**: Charter's Pre-existing Failure Reporting Rule — binding, not advisory.
- **Steps**: For any red test not already covered by a filed, referenced upstream
  issue, open a new GitHub issue with the command run, the failure summary, and why it
  is believed pre-existing (not introduced by this mission's not-yet-started changes),
  **before** treating it as accepted baseline.

### Subtask T007 – Verify commit shape between `ab15225ea` and current tip

- **Purpose**: PLAN-VERIFY-003's falsifiability note — the durable claim is "zero
  implementation-shaped commits above `ab15225ea`," not a fixed hash/count (which goes
  stale with every planning commit).
- **Steps**: `git log --oneline ab15225ea..<current-tip>` and confirm every commit is
  `spec(...)` / `fix(spec: ...)` / `reviews(spec: ...)` / `plan(...)` / meta-add shaped.

### Subtask T019 [P] – Add the import-boundary test

- **Purpose**: Mechanical protection of C-007's invariant.
- **Steps**: Create `tests/architectural/test_bridge_cores_import_boundary.py`. Parse
  `src/runtime/next/runtime_bridge_cores.py` via `ast.parse`, walk `Import`/`ImportFrom`
  nodes, and assert every non-stdlib import target is `runtime.next.decision` (or a
  submodule of it). Use Python's own stdlib-module list (`sys.stdlib_module_names` on
  3.11+, or an equivalent allowlist) to distinguish stdlib from non-stdlib.
- **Files**: New file, `tests/architectural/test_bridge_cores_import_boundary.py`.
- **Parallel?**: Yes — this WP's only file is new and read-only against the file it
  inspects; safe alongside WP02 and WP03.
- **Notes**: Landing this before WP05 edits `runtime_bridge_cores.py` means WP05's own
  new imports (if any) are checked by construction as they are added.

## Test Strategy

- **T001-T007**: No new automated test is added. The "test" is the recorded pytest run
  itself (T003/T004), which every later ATDD-first WP re-verifies RED against.
- **T019**: `pytest tests/architectural/test_bridge_cores_import_boundary.py -q`.
  Manually verify the negative case once during development (temporarily add a bad
  import to a scratch copy, confirm the test fails, then revert) — do not commit the
  negative-case scratch edit.

## Risks & Mitigations

- Misattributing a genuinely new regression as "pre-existing baseline" (T001-T007) —
  mitigated by the explicit #3284-diff requirement (T005) and the mandatory upstream
  filing (T006).
- Low risk on T019; a mechanical AST-walk test with an existing repo-wide precedent
  pattern to copy directly.

## Review Guidance

- Confirm the recorded red set, the #3284 diff verdict, and any filed issue links
  (T001-T007) are all present in `tracer-tooling-friction.md` before approving.
  Confirm `-n 8 --dist loadfile` was used, not `-n auto`.
- Confirm the T019 test actually parses the real file path (not a copy/mock) so it
  reflects the live module.
- Confirm the stdlib-vs-non-stdlib distinction is correct for `re`, `dataclasses`,
  `typing`, `collections.abc`, etc. (all stdlib) vs. anything under `specify_cli.*` or
  third-party packages (non-stdlib, must fail unless it's `runtime.next.decision`).

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
- 2026-08-14 – claude – Fix 1 (issue #3396 fixer pass): folded WP01's T001-T007
  (Baseline Capture & Pre-Existing Failure Audit) into this WP per operator-authorised
  restructure. See tracer-design-decisions.md for placement rationale.
