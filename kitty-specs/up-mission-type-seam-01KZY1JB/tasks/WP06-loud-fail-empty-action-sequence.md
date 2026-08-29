---
work_package_id: WP06
title: Loud failure for empty action sequence — the dominant-risk fix, two ordered red/green commits
dependencies:
- WP04
requirement_refs:
- FR-004
- NFR-002
- NFR-005
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
phase: Phase 4 - Loud-fail for empty action sequence (IC-05, NFR-005 red-first)
assignee: ''
agent: claude
history:
- at: '2026-08-13T00:00:00Z'
  actor: system
  action: Prompt generated during /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/activation/mission_type_profiles.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/mission_type_profiles.py
- tests/charter/test_mission_type_profiles.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Loud failure for empty action sequence — the dominant-risk fix, two ordered red/green commits

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` and behave according to its guidance
before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

**This is the mission's own stated reason for existing (CL-003).** Today, an org-pack
mission-type YAML carrying only `schema_version`/`id`/`display_name` (no `action_sequence`) loads
CLEAN with `action_sequence = None`, which `_resolve_action_slot`'s
`return list(mission.action_sequence or [])` line (live-verify — plan.md cites line `807`)
silently degrades to `[]`. A mission of that type would resolve "successfully" and plan
**nothing** — no error anywhere. This gap only becomes *reachable* once WP03/WP04 land (before
this mission, a non-built-in type couldn't resolve at all — it hard-failed with
`UnknownMissionTypeError` instead). This WP closes that gap with a named, loud, specific
exception, landing in the same PR that first makes the silent-degrade path reachable, so CL-003's
"silent, planless success" never actually reaches an operator.

**Success criteria**:

1. A new named exception class, `MissionTypeEmptyActionSequenceError` (or an equivalent name you
   settle on — keep it descriptive and consistent with the existing pattern), following the
   existing `UnknownMissionTypeError` pattern already in `src/charter/activation/mission_type_profiles.py`
   (class at live-verified line ~193, raised for an analogous configuration-inconsistency case at
   ~738 and ~799 — live-verify all three).
2. The new raise site sits inside `_resolve_action_slot`, specifically the branch that currently
   returns `list(mission.action_sequence or [])` when `mission.action_sequence` is `None`/empty
   **for a non-built-in-layer resolution**. Raise `MissionTypeEmptyActionSequenceError` naming the
   mission-type id and the layer it was resolved from — e.g. "mission type `qa` resolved from
   layer `org` has an empty action sequence."
3. **NFR-005's binding two-ordered-commits requirement** (see below) — this is not optional
   process ceremony, it is mechanically verified by reviewers.
4. `mission create` against a misconfigured org/project type propagates the *same exception type*
   (asserted via `isinstance`, never message substring-matching) — User Story 2 AC2.

## Context & Constraints — NFR-005, read this section before writing any code

> The regression test pinning today's silent empty-action-sequence degradation (FR-004) MUST be
> committed RED against the pre-fix behavior before the commit that introduces the loud-failure
> fix, as **two separate commits in that order**. Reviewers verify RED on the pre-fix commit and
> GREEN on the final commit — but that two-endpoint check alone cannot distinguish two separate
> ordered commits from one combined test+fix commit, which would also pass it trivially.
> Verification MUST go further: reviewers identify the commit SHA that introduces the CL-003
> regression test, check it out in isolation (without the fix commit), and confirm the test fails
> there, so the red-before-fix ordering claim is mechanically falsifiable rather than resting on
> implementer honesty.

**This means, literally**:

- **Commit 1 (RED)**: add the regression test to `tests/charter/test_mission_type_profiles.py`
  that asserts resolving a non-built-in-layer type with no `action_sequence` raises
  `MissionTypeEmptyActionSequenceError` (or whatever name you choose — pick it in this commit,
  since the test references it). This test MUST fail at this commit, because the exception class
  and its raise site do not exist yet — the current code still returns `[]` silently.
  Commit this alone. Do not include the fix in the same commit, even if your diff tool would make
  it trivial to combine them.
- **Commit 2 (GREEN)**: add the exception class and its raise site inside `_resolve_action_slot`.
  This commit alone makes Commit 1's test pass. State explicitly in this commit's message which
  prior commit SHA it makes green (e.g. "Fixes the RED test from <sha>").
- **Do not squash these two commits together at any point before review.** A reviewer will
  literally `git checkout <commit-1-sha>` and re-run the test to confirm it fails there. If you
  squash, this mechanical verification becomes impossible and NFR-005 is violated regardless of
  what the final diff looks like.
- Say so explicitly in both commit messages — a reviewer should not have to guess which commit is
  the red-first test and which is the fix (this also satisfies the mission's commitlint gate,
  which plan.md notes needs conventional-commit-shaped messages stating this).

## Context & Constraints — everything else

- **This WP depends on WP04** (transitively WP03) — the layered lookup and `pack_context`
  threading must exist first, or a non-built-in type cannot resolve (non-`None`) at all, and this
  WP's raise site could never fire.
- **NFR-002 (no silent success)** — this WP is the mission's canonical example of NFR-002 in
  action: the new raise site must never degrade back to `[]` under any code path.
- **File overlap with WP04 is expected and fine** — both WPs touch
  `src/charter/activation/mission_type_profiles.py` and `tests/charter/test_mission_type_profiles.py`, but
  WP06 depends on WP04, so they are sequenced, not concurrent (see this mission's `wps.yaml` header
  comment on the ownership-map-leeway convention: file overlap is fine across a dependency edge).
- **User Story 2 AC2's "same class of error" requirement** — `mission create` against the
  misconfigured type must propagate `MissionTypeEmptyActionSequenceError` (or your chosen name),
  asserted via `isinstance`, never message substring-matching. Trace the call path from `mission
  create` through to `_resolve_action_slot` to confirm the exception genuinely propagates rather
  than being caught-and-re-wrapped somewhere in between.
- **Terminology**: no `feature*` alias.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-up-mission-type-seam-01KZY1JB`. During `/spec-kitty.implement` this WP may branch
  from a dependency-specific base, but completed changes must merge back into
  `kitty/mission-up-mission-type-seam-01KZY1JB` unless the human explicitly redirects the landing
  branch.
- **Planning base branch**: `kitty/mission-up-mission-type-seam-01KZY1JB`
- **Merge target branch**: `main`

## Subtasks & Detailed Guidance

### Subtask T013 – RED commit: the empty-action-sequence regression test

- **Purpose**: NFR-005's mandatory first, failing commit.
- **Steps**:
  1. Decide the exception class name (`MissionTypeEmptyActionSequenceError` is the spec's suggested
     name — use it unless you have a strong, documented reason not to).
  2. Write a test in `tests/charter/test_mission_type_profiles.py`: construct a scratch org (or
     project) mission-type pack whose YAML has `schema_version`/`id`/`display_name` but no
     `action_sequence`; activate it; resolve it through `resolve_mission_type_context` (or directly
     through `_resolve_action_slot`, whichever the existing test file's convention favors); assert
     `MissionTypeEmptyActionSequenceError` is raised, and that its message names both the
     mission-type id and the layer ("org" or "project").
  3. Run the test and confirm it FAILS (the exception class doesn't exist yet, or the current code
     path returns `[]` without raising).
  4. Commit this test alone, with a commit message stating it is the RED half of NFR-005's ordered
     pair.
- **Files**: `tests/charter/test_mission_type_profiles.py`.
- **Parallel?**: No — this must be committed and confirmed-red before T014 begins.

### Subtask T014 – GREEN commit: the exception class and its raise site

- **Purpose**: NFR-005's mandatory second, passing commit.
- **Steps**:
  1. Add the exception class to `src/charter/activation/mission_type_profiles.py`, following
     `UnknownMissionTypeError`'s existing pattern (constructor signature, `__str__`/message
     formatting — mirror its shape).
  2. Add the raise site inside `_resolve_action_slot`, replacing the silent
     `list(mission.action_sequence or [])` degradation for non-built-in-layer resolutions with a
     raise of the new exception, naming the mission-type id and layer.
  3. Confirm the built-in-layer case is unaffected — built-in types are exhaustively covered by
     `MissionTypeRepository.default()`'s own roster, which always has a populated
     `action_sequence` by construction (shipped content); do not introduce a new hard-fail path for
     built-in types that didn't exist before.
  4. Run T013's test and confirm it now passes.
  5. Commit this alone, with a commit message stating which prior commit SHA (T013's) it makes
     green.
- **Files**: `src/charter/activation/mission_type_profiles.py`.
- **Parallel?**: No — depends on T013's commit existing first.

### Subtask T015 – `mission create` propagation test (User Story 2 AC2)

- **Purpose**: prove the exception type (not just message) propagates through `mission create`.
- **Steps**: write a test asserting `mission create` against the same misconfigured org/project
  type raises (or surfaces as a CLI failure backed by) `MissionTypeEmptyActionSequenceError`,
  asserted via `isinstance` on the underlying exception — trace the actual call path to confirm no
  intermediate `except Exception` swallows and re-wraps it into a generic error.
- **Files**: `tests/charter/test_mission_type_profiles.py` (or a more appropriate existing test
  file if `mission create`'s own test suite lives elsewhere — check first;
  `tests/charter/test_mission_type_profiles.py` is this WP's assigned owned test file, so prefer
  landing this test there unless doing so would be a poor fit for the existing file's scope).
- **Parallel?**: Can proceed after T014's commit lands (needs the real exception class to assert
  against).

## Test Strategy

- **Per-AC / per-SC**: **SC-002** — "An org-pack mission type with an empty `action_sequence`
  fails loudly (named error identifying mission-type id and layer) at resolution time, with a
  red-first regression test proving the failure was silent before the fix and loud after" — this
  WP's T013/T014 pair is the literal mechanism. User Story 2 AC1 (the resolver-level raise) and
  AC2 (the `mission create`-level propagation, same exception type).
- **Test surface**: `tests/charter/test_mission_type_profiles.py` (extended further, on top of
  WP04's extensions).
- **Commands**: `uv run pytest tests/charter/test_mission_type_profiles.py -v`

## Risks & Mitigations

- **Risk**: squashing the two commits before review, defeating NFR-005's mechanical
  verifiability. **Mitigation**: explicit prohibition above; state both commit SHAs' relationship
  in commit messages.
- **Risk**: the new raise site accidentally fires for a built-in type (regression). **Mitigation**:
  T014 step 3's explicit check; the golden-parity test from WP04/T010 is the backstop.
- **Risk**: `mission create`'s call path catches and re-wraps the exception, defeating User Story 2
  AC2's `isinstance` requirement. **Mitigation**: T015's explicit call-path trace.

## Gate Set (this WP's Definition of Done)

- **`fast-tests-charter` + `integration-tests-charter`** (`--cov=charter --cov-fail-under=55`).
- **`diff-coverage` (critical-path, 90%, `[ENFORCED]`)** over `src/charter/*` — the new exception
  class and raise site both need direct test coverage.
- **`arch-adversarial`** — must not regress any architectural gate.
- **`commitlint`** — this WP's two-ordered-commits requirement makes commit message shape
  especially load-bearing; both commits must be conventional-commit-shaped AND state the red/green
  relationship in prose.
- **`Typer 0.26 JSON error surface`, `patch() target validation`, `Bandit`, `pip-audit`** —
  always-on in `lint`.
- `make lint` locally before handing off.

## Review Guidance

- **Mechanically verify NFR-005**: `git log --oneline` this WP's commits, identify the RED commit
  SHA, `git checkout <that-sha>` (or `git show <that-sha>^:tests/charter/test_mission_type_profiles.py`
  plus the pre-fix source) and re-run the new test to confirm it fails in isolation, without the
  fix commit applied. Do not accept "RED on pre-fix, GREEN on final" alone as sufficient — that
  two-endpoint check cannot distinguish ordered commits from one combined commit (this is the
  exact failure mode NFR-005 exists to catch).
- Confirm the exception message names both the mission-type id and the layer.
- Confirm `mission create`'s propagation test asserts on exception type, not message substring.
- Confirm built-in-type behavior is unaffected (cross-check against WP04's golden-parity test).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-13T00:00:00Z – system – Prompt created.
