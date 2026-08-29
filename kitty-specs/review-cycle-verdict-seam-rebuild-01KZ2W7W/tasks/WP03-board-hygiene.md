---
work_package_id: WP03
title: Board hygiene
dependencies: []
requirement_refs:
- FR-018
- FR-019
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T010
- T011
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py
- tests/specify_cli/invocation/test_registry_builtin_activation_parity.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP03 - Board hygiene

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Two pre-existing mainline reds, unrelated to the verdict seam, are in scope
here only because DIRECTIVE_025 (Boy Scout Rule — "filed as issues and
deferred, never silently absorbed") makes them charter-legal riders on this
mission rather than a broad refactor smuggled in under DIRECTIVE_024. Both are
confirmed red on this branch today, live:

1. **`test_command_exposes_exact_flag_surface[acceptance-verdict]`**
   (`tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py`)
   fails with:
   ```
   AssertionError: `acceptance-verdict` flag surface drifted from the frozen contract.
       missing: []
       extra:   ['--description', '--execute', '--negative-invariant', '--no-execute', '--scope', '--verification-command']
   ```
   The `acceptance-verdict` command (`src/specify_cli/cli/commands/agent/
   acceptance_verdict.py:364`) grew six new flags for negative-invariant
   registration/execution (FR-007/FR-008 of a different, already-landed
   mission — `--negative-invariant`, `--description`,
   `--verification-command`, `--scope`, `--execute`/`--no-execute`) without the
   frozen-contract golden test being re-pinned. Introduced by commits
   `b04da00e1` ("Write-side placement seam: deterministic matrix/tracer writers
   + row-aware merge driver (#3076)") and `e56122706` ("feat: post-consolidation
   write surface + deterministic authoring finish") — confirm these via `git
   log --oneline -S negative_invariant -- src/specify_cli/cli/commands/agent/
   acceptance_verdict.py` yourself before citing them in your re-pin, in case a
   later commit has since amended the flag surface further.

2. **`test_excluded_builtin_absent_from_routing_and_context`**
   (`tests/specify_cli/invocation/test_registry_builtin_activation_parity.py`)
   fails with:
   ```
   AssertionError: assert 'Profile-Cited Directives (reviewer-renata):' in
   'Governance:\n  - Template set: software-dev-default\n...\n# Governance
   payload: 1 sections substituted with fetch commands (budget=32000).'
   ```
   The test asserts a **rendered-text marker** (`_directives_marker(profile_id)`,
   the literal string `"Profile-Cited Directives (<id>):"`) is present in the
   governance-context render for an activated builtin. When the render's token
   budget is exceeded, the context seam substitutes a compact fetch-command
   stub for one or more sections — the assertion then fails not because
   activation was wrong, but because the **rendered prose got truncated**. The
   test is asserting a byte-for-byte text shape that a budget-dependent
   renderer does not guarantee, when what it actually wants to prove is
   whether the profile *resolved* (was activated) at all.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story
  7 (FR-018, FR-019), and the Revision History row correcting an earlier draft
  that named FR-016/FR-017 (in-domain) instead of the actual out-of-domain
  pair, FR-018/FR-019
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-13
  ("Board hygiene") — "the only genuinely droppable concern," and its note
  that `tests/specify_cli/invocation/` sits **outside** the affected-suites
  list, so NFR-001's node-id floor cannot observe a regression there — this WP
  must self-verify via direct pytest runs, not rely on the affected-suites diff
  to catch a mistake here.
- `tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py` —
  read `_EXPECTED_FLAGS` (the frozen per-command flag dict, starting around
  line 101) and `test_command_exposes_exact_flag_surface`
  (`@pytest.mark.parametrize("command", sorted(_EXPECTED_FLAGS))`, around line
  221) in full before editing.
- `src/specify_cli/cli/commands/agent/acceptance_verdict.py:364-420` — the
  `acceptance_verdict` command's full `typer.Option(...)` parameter list;
  cross-check every flag name and its help text against what you re-pin.
- `tests/specify_cli/invocation/test_registry_builtin_activation_parity.py` —
  read the module docstring ("R3 — dispatch routing and governance context
  AGREE on built-in activation") and `_directives_marker` (around line 53),
  `test_excluded_builtin_absent_from_routing_and_context` (around line 124),
  and `test_no_activation_key_admits_all_builtins_in_routing` (around line
  144, currently passing — do not break it).
- `src/charter/activation/context.py`'s `build_charter_context` and
  `src/specify_cli/invocation/registry.py`'s `ProfileRegistry` — the two
  surfaces this test's docstring says must "AGREE on built-in activation";
  `ProfileRegistry.list_all()` is the routing-side source of truth this WP's
  re-pin must keep using for the activation assertion.

**Constraints (binding)**:
- **Re-pin, do not weaken.** Both fixes must re-establish a check that still
  catches the class of drift it originally existed to catch — a re-pin that
  merely deletes the failing assertion (e.g. removing the flag-surface check,
  or asserting nothing about activation) is not compliance.
- **The re-pin must fail on removal, not just addition.** T010 explicitly
  requires this — a frozen-contract check that only reds when a flag is added
  and silently passes when one is dropped is half a contract.
- **This WP is genuinely droppable** per plan.md — but if taken, both items
  must be finished; do not land T010 alone and leave T011 for a later pass.

## Subtask T010 — Re-pin the acceptance-verdict frozen flag contract with per-flag rationale

- **Purpose**: Bring `_EXPECTED_FLAGS["acceptance-verdict"]` back in sync with
  the command's actual flag surface, with each added flag traceable to the
  commit that introduced it — so the next drift is caught immediately instead
  of accumulating silently across two more landings.
- **Steps**:
  1. Confirm the exact commit(s) that introduced each of the six extra flags
     via `git log --oneline -S '"--negative-invariant"' -- src/specify_cli/
     cli/commands/agent/acceptance_verdict.py` (repeat per flag if a single
     `git log -S negative_invariant` search does not cleanly attribute all
     six to one commit).
  2. In `tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py`,
     update `_EXPECTED_FLAGS["acceptance-verdict"]` to include all six:
     `--negative-invariant`, `--description`, `--verification-command`,
     `--scope`, `--execute`, `--no-execute`.
  3. Add a comment directly above the `acceptance-verdict` entry naming each
     added flag and its introducing commit hash — e.g. `# --negative-invariant,
     --description, --verification-command, --scope, --execute/--no-execute
     added by b04da00e1 / e56122706 (FR-007/FR-008, negative-invariant
     registration)`. This is the "per-flag rationale" tasks.md names; a bare
     frozenset update with no provenance comment does not satisfy it.
  4. Add or extend a test (or a documented assertion within the existing
     parametrized test) proving the re-pin fails on **removal** as well as
     addition — e.g. a focused unit test that constructs a fake expected-set
     missing one of the six flags and asserts the comparison logic flags it as
     `missing`, not just `extra`. The existing
     `test_command_exposes_exact_flag_surface` already asserts symmetric
     difference (`missing`/`extra` both reported per its docstring at line
     226-229), so confirm this property already holds and add a narrow
     regression test demonstrating it explicitly for this command, rather than
     assuming the existing assertion shape is sufficient without proof.
- **Files**: `tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py`
- **Validation checklist**:
  - [ ] `pytest tests/specify_cli/cli/commands/agent/test_mission_cli_golden_contract.py -q`
        passes in full, including
        `test_command_exposes_exact_flag_surface[acceptance-verdict]`.
  - [ ] Each of the six added flags has a commit-hash comment.
  - [ ] A deliberately-removed flag from `_EXPECTED_FLAGS["acceptance-verdict"]`
        (tested temporarily) makes the check fail with a `missing:` entry, not
        pass silently.
  - [ ] `src/specify_cli/cli/commands/agent/acceptance_verdict.py` is
        untouched — this is a test-only re-pin, not a command change.
- **Edge Cases**: If a flag's introducing commit cannot be cleanly isolated
  (e.g. squashed history), state the best-attributable commit and note the
  attribution is approximate in the added comment — do not fabricate a
  precise hash you have not verified.

## Subtask T011 — Make the parity check assert resolved activation, not budget-dependent text

- **Purpose**: Fix the check to test what it actually means to test — whether
  a builtin profile is activated and resolvable — without being sensitive to
  whether the context renderer's token budget happened to substitute a
  fetch-command stub for the section that would otherwise contain the literal
  marker string.
- **Steps**:
  1. Reproduce first: run
     `pytest tests/specify_cli/invocation/test_registry_builtin_activation_
     parity.py -q` and confirm `test_excluded_builtin_absent_from_routing_and_
     context` fails with the budget-substitution text shown in the Objective,
     while `test_no_activation_key_admits_all_builtins_in_routing` passes.
  2. Locate a **budget-independent** signal of resolution — the module
     docstring's own framing is "with an explicit `activated_agent_profiles`
     that EXCLUDES a built-in, that built-in is absent from BOTH the routing
     catalog... AND the governance context." Rather than string-searching
     rendered prose for `_directives_marker(profile_id)`, assert against
     `build_charter_context`'s **structured** return value (or an
     intermediate resolution result it exposes before rendering to text) for
     whether the profile's directive references were resolved — read
     `charter/context.py` and `charter/profile_resolution.py` to find the
     pre-render resolution set (`_reset_agent_profile_cache` is already
     imported in this test file; look for a sibling accessor that exposes
     "which profiles resolved" without going through rendered text).
  3. If no such structured accessor exists yet, the smallest correct fix is to
     raise the test's configured render budget high enough that section
     substitution does not trigger for this specific fixture (a `budget=`
     parameter or equivalent, if `build_charter_context` accepts one) — this
     keeps the assertion textual but removes the budget-dependence, which is
     the literal defect tasks.md names ("asserts resolved activation, not
     budget-dependent text" — a raised, fixed budget for a small fixture is a
     legitimate way to make the assertion budget-independent, provided it is
     not simply "raise it until today's fixture happens to fit," which would
     silently re-break the moment the fixture grows).
  4. Keep the excluded-builtin assertions (`_EXCLUDED_BUILTIN not in
     routing_ids`, `_directives_marker(_EXCLUDED_BUILTIN) not in excluded_text`)
     — those are unaffected; only the **activated**-builtin assertion is
     broken by truncation, since an *absent* marker is unambiguous but a
     *present* marker can be a false negative under budget substitution.
- **Files**: `tests/specify_cli/invocation/test_registry_builtin_activation_parity.py`
- **Validation checklist**:
  - [ ] `test_excluded_builtin_absent_from_routing_and_context` passes.
  - [ ] `test_no_activation_key_admits_all_builtins_in_routing` still passes,
        unmodified in intent.
  - [ ] The fix does not merely raise the budget until the current fixture
        happens to fit with no margin — state in the Activity Log what margin
        the chosen approach leaves, or confirm the structured-resolution
        approach was used instead (preferred).
  - [ ] `src/charter/activation/context.py` and `src/specify_cli/invocation/registry.py`
        are unmodified unless a structured accessor genuinely does not exist
        yet and this WP's scope is judged to require adding one — if so, keep
        that addition minimal and call it out explicitly in the PR, since it
        would be new production surface in a "board hygiene" WP.
- **Edge Cases**: Confirm the fix does not accidentally make the check pass
  when the excluded builtin's directives leak through under a *different*
  budget-substitution boundary — the negative assertions must stay honest, not
  just newly permissive on the positive side.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. This WP is a root WP with no
dependencies; worktrees are allocated per lane from `lanes.json` at
`spec-kitty implement WP03` time. Completed changes merge back into
`pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch.

## Definition of Done

- `test_command_exposes_exact_flag_surface[acceptance-verdict]` passes, with
  each newly-recognized flag traceable to its introducing commit (T010).
- The re-pin demonstrably fails on flag removal, not only addition (T010).
- `test_excluded_builtin_absent_from_routing_and_context` passes without
  relying on a token budget large enough to avoid section substitution by
  accident (T011).
- `test_no_activation_key_admits_all_builtins_in_routing` remains green.
- `mypy --strict` and `ruff` clean on both touched files.
- Neither `acceptance_verdict.py` nor the charter/invocation production
  modules changed, unless T011 genuinely required a minimal structured
  accessor — in which case that addition is called out explicitly and kept as
  small as the fix allows.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Re-pinning to "whatever currently passes" without provenance.** Mitigate
  by requiring the commit-hash comment per flag (T010) rather than a bare
  frozenset update.
- **Fixing the activation-parity test by simply deleting the failing
  assertion.** Mitigate by keeping (or replacing with an equivalent
  structured check) the same "activated builtin resolves" property the
  original assertion intended, per the Reviewer Guidance below.
- **A budget-margin fix that silently re-breaks the moment the fixture's
  profile gains one more directive reference.** Mitigate by preferring the
  structured pre-render accessor over a numeric budget bump, and if a budget
  bump is used anyway, documenting the margin.

## Reviewer Guidance

- Confirm each of the six re-pinned flags carries a commit-hash comment, not
  just a wider frozenset.
- Confirm a temporarily-removed flag from the expected set makes the check
  fail with a `missing:` report — ask for this proof if it is not already
  demonstrated in the PR.
- Confirm the activation-parity fix tests *resolution*, not merely a wider
  token budget that happens to avoid truncation today — ask what happens if
  the fixture's profile gains a second directive reference.
- Confirm neither `acceptance_verdict.py` nor `charter/context.py` /
  `invocation/registry.py` changed, unless explicitly justified and minimal.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP03 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
