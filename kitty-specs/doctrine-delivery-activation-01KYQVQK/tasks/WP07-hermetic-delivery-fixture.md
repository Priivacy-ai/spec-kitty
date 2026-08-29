---
work_package_id: WP07
title: Hermetic delivery-test fixture
dependencies: []
requirement_refs:
- FR-009
planning_base_branch: feat/doctrine-delivery-activation
merge_target_branch: feat/doctrine-delivery-activation
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-activation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-activation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-delivery-activation-01KYQVQK
base_commit: 1e187793a47fa24aeeabfb0ec6e0436a65bacd5d
created_at: '2026-07-30T05:38:05.211132+00:00'
subtasks:
- T027
- T028
phase: Phase 3 - Hermetic test fixture (Lane C, land-early)
history:
- at: '2026-07-29T22:08:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/charter/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/charter/test_every_load_delivery.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Hermetic delivery-test fixture

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work
package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!** Check the `review_ref` field in the event log (via
`spec-kitty agent status` or the Activity Log below) and address all feedback before your work is complete.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Make `tests/charter/test_every_load_delivery.py`'s `project` fixture hermetic to the invoking developer's
  local ambient state: `first_load` must be `True` on the first load inside the fixture regardless of
  whether the real checkout used as the copy source happens to have an existing
  `.kittify/charter/context-state.json`.
- **Land EARLY** relative to WP01/WP04 — this fixture backs their ATDD cycles
  (`tests/charter/test_every_load_delivery.py` is in WP01/WP03's own verification command list per
  `quickstart.md`). A red-for-the-wrong-reason failure here would be mistaken for WP01/WP04's own
  regression if this WP lands late.

## Context & Constraints

- Plan: [plan.md](../plan.md) IC-09 · Ledger: [pre-planning-ledger.md](../pre-planning-ledger.md) Scout 2
  "Item 4 — Hermetic fixture" + orchestrator synthesis D9 ("WP08 first / de-flake").
- **Grounding (verified during this planning pass, in this checkout):**
  - The `project` fixture (`tests/charter/test_every_load_delivery.py:63-84`) does `src = _repo_root()`
    (lines 55-60, walks up from the test file to find the checkout root by locating `.kittify/charter/` +
    `pyproject.toml`), then at **line 75**: `shutil.copytree(src / ".kittify" / "charter", dst_kittify /
    "charter")`. This copies EVERYTHING under `.kittify/charter/`, including the gitignored
    `context-state.json` (`.gitignore:88` confirms it's gitignored; confirmed present in THIS checkout at
    `.kittify/charter/context-state.json`, ~204 bytes, as of this grounding pass).
  - `_prepare_context_state` (`src/charter/activation/context.py:696`) reads `repo_root / ".kittify" / "charter" /
    "context-state.json"` to determine `first_load`. In a populated local checkout, the COPIED file makes
    `first_load=False` on what the test expects to be a virgin project, so
    `test_artefact_on_first_load_is_present_on_second_load`'s `assert first.mode == "bootstrap"`
    (test line 112) fails **locally only**. A fresh CI checkout has no such ambient file, so CI stays green
    — a classic local-only false-red (memory: this is the same failure family as the ".worktrees dot-path
    arch false-green" gotcha — behavior that differs by ambient local state vs. a fresh checkout).
  - **Matrix**: 7 of the file's 9 test functions use the `project` fixture — `TestEveryLoadTextDelivery`
    (2 tests), `TestBootstrapRendersExtendedKinds` (1 test), `TestJsonEveryLoadDelivery` (2 tests),
    `TestShippedCliDelivery` (2 tests). The other 2 (`TestGrainCallersForwardMissionType`,
    `TestScopeRouterForwardsGrain`) use bare `tmp_path` directly and are unaffected.
- **The fix** (pick option (a) — see rationale below): change line 75 to
  `shutil.copytree(src / ".kittify" / "charter", dst_kittify / "charter",
  ignore=shutil.ignore_patterns("context-state.json"))`. The ledger also records a second valid option —
  unlink the file after a plain copy (`(dst_kittify / "charter" / "context-state.json").unlink(missing_ok=True)`)
  — but prefer the `ignore_patterns` form: it never materializes the stale file at all, rather than
  materializing-then-deleting, and reads as the more obviously-correct intent to a future maintainer.
- **This WP does NOT touch `_prepare_context_state` or any other `context.py` production code.** The bug is
  entirely in the TEST fixture's setup — a real fresh checkout never has this file, so production behavior
  is already correct. Resist any temptation to add a defensive check inside `_prepare_context_state` itself;
  that would mask a genuinely different first-load-detection bug behind a test-only workaround.

## Branch Strategy

- **Strategy**: Planning artifacts generated on feat/doctrine-delivery-activation; during implement this WP
  may branch from a dependency-specific base but merges back into feat/doctrine-delivery-activation unless
  the human redirects.
- **Planning base branch**: feat/doctrine-delivery-activation
- **Merge target branch**: feat/doctrine-delivery-activation

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T027 – Fixture excludes/resets `context-state.json`

- **Purpose**: Make the `project` fixture hermetic to the invoking developer's local ambient state.
- **Steps**:
  1. Confirm the failure reproduces BEFORE making any change: run the DoD command below in this checkout
     (which, per the grounding above, already has an ambient `.kittify/charter/context-state.json`) and
     capture the pre-fix failure (`first.mode != "bootstrap"`) as red evidence for the Activity Log.
  2. In `tests/charter/test_every_load_delivery.py`, change line 75's `shutil.copytree(src / ".kittify" /
     "charter", dst_kittify / "charter")` to add `ignore=shutil.ignore_patterns("context-state.json")`.
  3. Add a one-line comment directly above the call explaining WHY, so a future editor doesn't "clean up"
     the ignore pattern thinking it's dead weight: the source checkout's `.kittify/charter/context-state.json`
     is gitignored ambient state recording prior `spec-kitty` invocations; copying it would leak the
     invoking developer's local history into what every test in this file expects to be a virgin project.
  4. Re-run the DoD command and confirm green.
- **Files**: `tests/charter/test_every_load_delivery.py`.
- **Parallel?**: Yes — independent of every other WP in this mission; this is why it is scheduled to land
  FIRST/EARLY.
- **Notes**: Do not add a defensive check inside `_prepare_context_state` itself (see Context) — the fix
  belongs entirely in the fixture's `shutil.copytree` call.

### Subtask T028 – Verify hermeticity across the full `test_every_load_delivery` matrix

- **Purpose**: Prove the fix isn't narrowly tailored to the one test that happens to assert `first.mode ==
  "bootstrap"` — all 7 fixture-using tests must be robust to ambient local state, not just the one that
  currently reproduces the failure most visibly.
- **Steps**:
  1. Run the full file's suite (DoD command below) with the ambient `.kittify/charter/context-state.json`
     PRESENT (today's default in this checkout) and confirm all 9 tests pass.
  2. Additionally, run it with that file TEMPORARILY absent (rename it aside, e.g. to `/tmp/...`, run the
     suite, then restore it exactly) to confirm the result is IDENTICAL either way — this is the actual
     hermeticity proof (same outcome regardless of ambient state), not merely "green once."
  3. Restore the real checkout's `context-state.json` exactly as it was (or perform step 2 against a
     disposable clone) so this WP's own campsite stays clean — do not leave the file deleted or modified as
     a side effect of verification.
- **Files**: `tests/charter/test_every_load_delivery.py` (verification only; no further edits expected
  beyond T027).
- **Parallel?**: With T027 (same file; T028 verifies T027's fix, sequenced immediately after).
- **Notes**: This is also the WP's own regression-proof against reintroducing the bug — record BOTH runs'
  pass/fail (ambient-present and ambient-absent) in the Activity Log as the acceptance evidence, not just
  the final green.

## Definition of Done

```bash
uv run pytest tests/charter/test_every_load_delivery.py -q
uv run pytest tests/charter/test_every_load_delivery.py -q -k "first_load or bootstrap"
```

Plus the manual ambient-state toggle described in T028 step 2 (not CI-automatable as a single command —
record both runs' results in the Activity Log). Do NOT run the full `tests/architectural/` or `tests/charter/`
suites beyond this file locally — targeted node-ids only (repo policy; CI owns the full sweep).

## Risks & Mitigations

- Risk is minimal (ledger: "minimal") — the only real risk is scope creep into `context.py`'s production
  `_prepare_context_state`; resist that, the bug is fixture-only.
- Land EARLY: if WP01 or WP04 start their ATDD cycles before this WP merges, they may misdiagnose this
  fixture's local false-red as their own regression — flag this WP's priority to the operator/orchestrator
  explicitly if sequencing slips.

## Reviewer Guidance

- Confirm the fix is the `ignore_patterns` call at line 75 (or the unlink-after-copy alternative), not a
  change to `_prepare_context_state` or any other production code path.
- Confirm the Activity Log records BOTH the pre-fix red repro AND the T028 ambient-state-toggle verification
  — a green-only report without the red-first evidence does not meet this repo's ATDD-first discipline.
- Confirm no other file in the mission's touched set silently started depending on this fixture's PRE-fix
  (buggy) behavior (e.g. a test elsewhere that accidentally relied on `first_load=False` from a stale copy).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>` (UTC timestamp, append at the
end, never prepend or insert in the middle — the acceptance system reads the LAST entry as current state).

**Initial entry**:

- 2026-07-29T22:08:45Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP07 --to <status>` to
change WP status.
