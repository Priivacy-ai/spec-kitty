---
work_package_id: WP04
title: New Testing Tactics
dependencies: []
requirement_refs:
- FR-006
- FR-007
planning_base_branch: feature/doctrine-enrichment-bdd-profiles
merge_target_branch: feature/doctrine-enrichment-bdd-profiles
branch_strategy: Planning artifacts for this feature were generated on feature/doctrine-enrichment-bdd-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/doctrine-enrichment-bdd-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
agent: "claude:sonnet:curator-carla:implementer"
shell_pid: "82277"
history:
- timestamp: '2026-04-26T08:49:24Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
execution_mode: code_change
owned_files:
- src/doctrine/tactics/shipped/testing/acceptance-test-first.tactic.yaml
- src/doctrine/tactics/shipped/testing/atdd-adversarial-acceptance.tactic.yaml
- src/doctrine/tactics/shipped/testing/black-box-integration-testing.tactic.yaml
- src/doctrine/tactics/shipped/testing/formalized-constraint-testing.tactic.yaml
- src/doctrine/tactics/shipped/testing/function-over-form-testing.tactic.yaml
- src/doctrine/tactics/shipped/testing/mutation-testing-workflow.tactic.yaml
- src/doctrine/tactics/shipped/testing/no-parallel-duplicate-test-runs.tactic.yaml
- src/doctrine/tactics/shipped/testing/quality-gate-verification.tactic.yaml
- src/doctrine/tactics/shipped/testing/tdd-red-green-refactor.tactic.yaml
- src/doctrine/tactics/shipped/testing/test-boundaries-by-responsibility.tactic.yaml
- src/doctrine/tactics/shipped/testing/testing-select-appropriate-level.tactic.yaml
- src/doctrine/tactics/shipped/testing/test-minimisation.tactic.yaml
- src/doctrine/tactics/shipped/testing/test-pyramid-progression.tactic.yaml
- src/doctrine/tactics/shipped/testing/test-to-system-reconstruction.tactic.yaml
- src/doctrine/tactics/shipped/testing/zombies-tdd.tactic.yaml
- src/doctrine/tactics/shipped/testing/bug-fixing-checklist.tactic.yaml
- src/doctrine/tactics/shipped/testing/test-readability-clarity-check.tactic.yaml
authoritative_surface: src/doctrine/tactics/shipped/testing/
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

This WP owns `src/doctrine/tactics/shipped/testing/` end-to-end: move 15 existing testing tactics from the `shipped/` root into `testing/`, then create 2 new testing tactics.

**Step 1 — Move 15 existing testing tactics** from `shipped/` root to `shipped/testing/` (see list below). Do NOT modify YAML content.

**Step 2 — Create 2 new testing tactics**: `bug-fixing-checklist` and `test-readability-clarity-check`.

**NFR-003 baseline**: After this WP, `len(repo.load_all())` must equal WP01 baseline + 4 (from WP02+03) + 2 (from this WP) = baseline + 6.

Create `testing/` if WP01 has not merged: `mkdir -p src/doctrine/tactics/shipped/testing/`

**Tactics to move from root → `testing/`** (15 files):
```
acceptance-test-first.tactic.yaml
atdd-adversarial-acceptance.tactic.yaml
black-box-integration-testing.tactic.yaml
formalized-constraint-testing.tactic.yaml
function-over-form-testing.tactic.yaml
mutation-testing-workflow.tactic.yaml
no-parallel-duplicate-test-runs.tactic.yaml
quality-gate-verification.tactic.yaml
tdd-red-green-refactor.tactic.yaml
test-boundaries-by-responsibility.tactic.yaml
testing-select-appropriate-level.tactic.yaml
test-minimisation.tactic.yaml
test-pyramid-progression.tactic.yaml
test-to-system-reconstruction.tactic.yaml
zombies-tdd.tactic.yaml
```

---

## Subtask T015 — Create `bug-fixing-checklist.tactic.yaml`

**File**: `src/doctrine/tactics/shipped/testing/bug-fixing-checklist.tactic.yaml`

**Core principle**: Write a failing test to reproduce the defect *before* touching production code. This is the test-first bug-fixing discipline.

```yaml
schema_version: "1.0"
id: bug-fixing-checklist
name: Test-First Bug Fixing Checklist
purpose: >
  Resolve defects through a disciplined sequence that prevents speculative fixes,
  ensures the defect is reproducible as a test, and verifies no regressions are
  introduced. Applicable to any language or framework. Do not skip steps under
  time pressure — shortcuts in bug fixing cause regressions.
steps:
  - title: Understand the defect before acting
    description: >
      Read the bug report completely. Confirm what SHOULD happen and what ACTUALLY
      happens. If either is unclear, gather more information before proceeding.
      Do not open a code editor until you can state both in one sentence each.
  - title: Write a failing test that reproduces the defect
    description: >
      Before modifying any production code, write an automated test that fails
      because of the defect. The test documents the expected behavior and proves
      you can reproduce the problem deterministically. If you cannot write such a
      test, the defect is not yet understood well enough to fix.
      No exceptions: this step is mandatory even under time pressure.
  - title: Confirm the test fails for the right reason
    description: >
      Run only the new test. Verify it fails with the error that reflects the
      defect — not a test setup error or a different assertion. A test that fails
      for the wrong reason will pass after a wrong fix.
  - title: Implement the minimal fix
    description: >
      Make the smallest change that causes the failing test to pass. Avoid
      refactoring, adding features, or "improving" adjacent code during a bug fix
      unless the bug cannot be fixed without it. Document the root cause in a
      comment if it would not be obvious to a future reader.
  - title: Verify the full test suite
    description: >
      Run the complete test suite. Any newly failing test indicates a regression
      introduced by the fix. Fix regressions before marking the defect as resolved —
      a fix that breaks something else is not a fix.
  - title: Document the fix
    description: >
      In the commit message or PR description: state the root cause, the fix applied,
      and any edge cases the new test does not yet cover. Link to the bug report or
      ticket.
failure_modes:
  - "Fixing without a reproduction test — the fix may be correct today but regress silently in a future change."
  - "Writing the test after the fix — tests written after a passing fix are confirmation tests, not regression tests; they do not prove the fix was necessary."
  - "Refactoring during a bug fix — introduces unrelated risk; do it in a separate commit after the fix is verified."
  - "Running only the new test — regressions in other parts of the system are invisible until production."
notes: >
  Adapted from patterns.sddevelopment.be.
references:
  - name: Test-First Development
    type: directive
    id: DIRECTIVE_034
    when: Bug fixing is a test-first activity; the reproduction test is the failing test in the red-green cycle
  - name: Test and Typecheck Quality Gate
    type: directive
    id: DIRECTIVE_030
    when: The full test suite must pass before a fix is considered complete
```

---

## Subtask T016 — Create `test-readability-clarity-check.tactic.yaml`

**File**: `src/doctrine/tactics/shipped/testing/test-readability-clarity-check.tactic.yaml`

**Core principle**: Tests that enable accurate system reconstruction without external documentation prove their quality as living specifications. This is the dual-perspective reconstruction method.

```yaml
schema_version: "1.0"
id: test-readability-clarity-check
name: Test Readability and Clarity Check
purpose: >
  Validate whether a test suite effectively documents system behavior by attempting
  to reconstruct system understanding purely from test code. Tests that allow
  accurate reconstruction without external documentation serve as executable
  specifications. Use during code review, documentation audits, or when a new
  team member needs to understand a system. Not applicable to pure unit tests for
  trivial pure functions.
steps:
  - title: Read only the test code
    description: >
      Set aside all other documentation (README, specs, ADRs). Read the test suite
      as if it were the only available description of the system. For each test, note
      what behavior it describes and what it implies about system capabilities.
  - title: Reconstruct system understanding from tests
    description: >
      From the tests alone, write a short description of: what the system does (its
      capabilities), what the system does NOT do (boundaries), and what invariants hold
      (rules that are always enforced). This reconstruction is your working model.
  - title: Compare reconstruction against specification
    description: >
      Read the actual specification (or domain knowledge). Identify gaps between your
      reconstruction and the true system behavior. Each gap is a documentation finding:
      a behavior that exists in the system but is invisible in the test suite.
  - title: Classify findings
    description: >
      For each gap: (1) Missing coverage — a behavior exists but no test describes it;
      (2) Misleading test — a test describes a behavior incorrectly or too abstractly;
      (3) Naming failure — the test exists but its name does not communicate the behavior.
      Prioritize missing coverage (highest risk) over naming failures (lowest risk).
  - title: Report and act
    description: >
      Present findings to the implementer or reviewer. For missing coverage: add tests.
      For misleading tests: rename or rewrite. For naming failures: rename. The goal is
      that the next person who reads the test suite should not need this check.
failure_modes:
  - "Skipping step 2 (the reconstruction) — comparing directly against the spec defeats the purpose; the reconstruction surfaces blind spots the spec reader would miss."
  - "Treating 100% code coverage as a proxy for readability — coverage measures execution, not comprehension."
  - "Flagging every test that uses technical language — some technical detail is unavoidable; flag only where a business-level reader cannot infer the intent."
notes: >
  Adapted from practitioner experience; original approach documented in the
  quickstart-agent-augmented-development reference library.
  This tactic is particularly effective when onboarding new team members or when
  preparing a system for handover. A system whose tests pass this check has
  executable documentation that stays current automatically.
references:
  - name: Behavior-Driven Development
    type: tactic
    id: behavior-driven-development
    when: BDD scenarios are the highest-readability form of test; use BDD if reconstruction consistently fails
  - name: Test Boundaries by Responsibility
    type: tactic
    id: test-boundaries-by-responsibility
    when: After identifying coverage gaps, use this tactic to determine the correct level at which to add missing tests
```

---

## Subtask T017 — Verify both tactics pass schema validation

```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from doctrine.tactics.repository import TacticRepository
r = TacticRepository()
all_tactics = r.load_all()
for id_ in ['bug-fixing-checklist', 'test-readability-clarity-check']:
    assert id_ in all_tactics, f'{id_} not found'
    print(f'OK: {id_}')
"
pytest -m doctrine -q
```

**Validation checklist**:
- [ ] Both YAML files exist in `src/doctrine/tactics/shipped/testing/`
- [ ] Both tactic IDs resolve in the repository
- [ ] `notes` attribution line present in both
- [ ] No local filesystem paths in shipped YAML
- [ ] `pytest -m doctrine -q` is green

---

## Branch Strategy

No dependencies. Merges into `feature/doctrine-enrichment-bdd-profiles`.

```bash
spec-kitty agent action implement WP04 --agent claude
```

---

## Definition of Done

- 2 new YAML files exist in `shipped/testing/`
- Both are language-agnostic — no Java/Python/JS specifics in steps
- Both load via the tactic repository
- Doctrine test suite green

## Reviewer Guidance

- Verify `bug-fixing-checklist` steps enforce test-first order (test before fix, never after)
- Verify `test-readability-clarity-check` steps describe the reconstruction sequence in correct order
- Confirm no language-specific tooling is prescribed in steps (tool names allowed only in `notes`)

## Activity Log

- 2026-04-26T12:13:53Z – claude:sonnet:curator-carla:implementer – shell_pid=82277 – Started implementation via action command
- 2026-04-26T12:15:59Z – claude:sonnet:curator-carla:implementer – shell_pid=82277 – 15 testing tactics moved + 2 new testing tactics created; tactic count 84; 1133 doctrine tests green
- 2026-04-26T12:16:34Z – claude:sonnet:curator-carla:implementer – shell_pid=82277 – Review passed: 15 testing tactics renamed (100% similarity), bug-fixing-checklist and test-readability-clarity-check created with correct IDs and schema. Language-agnostic content verified. 17/17 testing tactics load correctly. Doctrine tests green.
- 2026-04-26T13:10:24Z – claude:sonnet:curator-carla:implementer – shell_pid=82277 – Done override: Feature merged to feature/doctrine-enrichment-bdd-profiles (squash merge commit 7383936b2)
