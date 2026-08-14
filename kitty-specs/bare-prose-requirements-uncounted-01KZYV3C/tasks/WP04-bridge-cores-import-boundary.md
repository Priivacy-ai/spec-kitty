---
work_package_id: "WP04"
subtasks:
  - "T019"
title: "Architectural Import-Boundary Test for runtime_bridge_cores.py"
task_type: "implement"
phase: "Phase 1 - Foundation (parallel with WP02, WP03)"
execution_mode: "code_change"
owned_files:
  - "tests/architectural/test_bridge_cores_import_boundary.py"
authoritative_surface: "tests/architectural/"
create_intent:
  - "tests/architectural/test_bridge_cores_import_boundary.py"
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
---

# Work Package Prompt: WP04 – Architectural Import-Boundary Test for `runtime_bridge_cores.py`

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, or select via `spec-kitty agent profile list` for an
`implement`-typed WP on `tests/architectural/`.

---

## Objectives & Success Criteria

Implement IC-08 (plan.md, C-007): pin `runtime_bridge_cores.py`'s self-declared
"zero-dependency leaf" invariant by construction — stdlib + `runtime.next.decision`
only — so a future cross-package import (including one this mission's own WP05 might
accidentally introduce) is caught mechanically, not by convention.

Success: the new test passes against the current, unmodified
`src/runtime/next/runtime_bridge_cores.py`; a synthetic non-stdlib,
non-`runtime.next.decision` import inserted into a scratch copy fails the same test.

## Context & Constraints

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

- `pytest tests/architectural/test_bridge_cores_import_boundary.py -q`.
- Manually verify the negative case once during development (temporarily add a bad
  import to a scratch copy, confirm the test fails, then revert) — do not commit the
  negative-case scratch edit.

## Risks & Mitigations

- Low; a mechanical AST-walk test with an existing repo-wide precedent pattern to copy
  directly.

## Review Guidance

- Confirm the test actually parses the real file path (not a copy/mock) so it reflects
  the live module.
- Confirm the stdlib-vs-non-stdlib distinction is correct for `re`, `dataclasses`,
  `typing`, `collections.abc`, etc. (all stdlib) vs. anything under `specify_cli.*` or
  third-party packages (non-stdlib, must fail unless it's `runtime.next.decision`).

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
