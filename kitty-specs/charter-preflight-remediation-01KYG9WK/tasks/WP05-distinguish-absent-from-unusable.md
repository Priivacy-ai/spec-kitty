---
work_package_id: WP05
title: Distinguish absent from present-but-unusable
dependencies:
- WP04
requirement_refs:
- FR-005
planning_base_branch: fix/charter-preflight-remediation
merge_target_branch: fix/charter-preflight-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-preflight-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-preflight-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
phase: Phase 5 - Reporting clarity
history:
- at: '2026-07-26T23:24:39Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_runtime/preflight/cli.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/charter_runtime/preflight/cli.py
- tests/specify_cli/charter_preflight/test_cli.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Distinguish absent from present-but-unusable

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status`).
- **You must address all feedback** before your work is complete.

---

## Start by checking whether there is anything to build

**T024 exists to stop you building something that already exists.**

The spec's own checklist records this: *"FR-005 may already be satisfied. The distinction between
'absent' and 'present but unusable' might exist in the current state vocabulary. It is specified as a
requirement because the operator-facing surfaces conflate them; plan should check whether the
underlying model already makes the distinction and only the reporting drops it."*

`FreshnessSubState.state` already carries `missing` and `invalid` as distinct values, and
`_compute_charter_source` sets `detail="charter.yaml exists but cannot be parsed"` on the `invalid`
branch. Strong prior: **the model already distinguishes; the reporting conflates.** If that holds,
this WP is a presentation change, not a vocabulary change.

Adding a new state to the vocabulary when the existing one already carries the information would be
gratuitous churn on a governance surface. Do the investigation first.

## Objectives & Success Criteria

Complete when an operator can tell, from the output alone, whether they have:

- **no charter at all** (nothing to fix — likely a greenfield project), versus
- **a charter that exists but is not in the form the gate requires** (something to fix)

on every operator-facing surface.

## Context & Constraints

**FR-006 interaction — do not newly block greenfield.** A project with no charter at all keeps its
current advisory, non-blocking treatment. Making the two states *distinguishable* must not make the
absent state *blocking*. WP06 verifies this, but do not create the problem here.

**Stay in your lane.** `computer.py` is WP02's file and `runner.py` is WP03's. If your investigation
concludes the fix genuinely requires a change in one of those, that is a finding to report — do not
silently reach into another WP's owned files. A narrow, well-justified out-of-map edit with a
recorded rationale is acceptable; a redesign of someone else's module is not.

## Branch Strategy

- **Planning base**: `fix/charter-preflight-remediation`
- **Merge target**: `fix/charter-preflight-remediation`

---

## Subtasks

### T024 — Determine whether the vocabulary already distinguishes

**Purpose**: establish what is actually missing before changing anything.

> **Pre-verified starting point (orchestrator, post-WP03/WP04).** Verify these rather than
> rediscovering them; then go beyond them.
>
> 1. **The vocabulary IS surfaced.** `preflight/cli.py:119` renders
>    `f"{check.state.upper()}  {check.name}: {check.detail}"`, so the state name reaches the operator.
>    `invalid` also carries a real detail (*"charter.yaml exists but cannot be parsed; …"*). On that
>    axis — absent vs unusable — FR-005 looks **already satisfied**.
> 2. **But both `missing` branches carry NO detail at all.** `computer.py:320` (`_compute_charter_source`)
>    and `:366` (`_compute_synced_bundle`) return `state="missing"` with `last_change` and
>    `remediation` only — no `detail`. The operator therefore sees a bare
>    `MISSING  charter_source: None`.
> 3. **So the real gap is F1 vs F2, not absent vs unusable.** A project that never had a charter (F1)
>    and a legacy-bundle project that has one in the old form (F2) both render identically. The spec's
>    Edge Cases require F2 *not* to read as "no charter at all" — today it cannot read as anything
>    else, because it renders nothing.
>
> This reframes the WP: it is probably not a new state value, and probably not a rendering change to
> `cli.py`. It is most likely giving the `missing` branches a truthful `detail` that distinguishes
> "no charter here" from "charter present, not in the required form" — which requires knowing which
> of the two you are in. Confirm that before designing anything.

**Note on ownership**: `computer.py` is WP02's file. If T024 confirms the fix belongs there, that is a
narrow, justified out-of-map edit — record a one-line rationale, exactly as WP03 did for the same
file. Do not redesign anything else in it.

**Steps**:
1. Trace a project in fixture shape **F1** (no charter at all) through the preflight and record the
   exact operator-visible output.
2. Trace a project in shape **F4** (`charter.yaml` present, unparseable) and record its output.
3. Compare. Answer precisely:
   - Do the underlying states differ? (Expected: `missing` vs `invalid`.)
   - Does the operator-visible output differ?
   - If the states differ but the output does not, where exactly is the distinction lost?
4. Also check F2 (legacy bundle, no `charter.yaml`) — arguably a third category: a charter exists in
   the project, just not in the required form. Determine how it currently reports and whether the
   spec's two-way distinction is sufficient for it.
5. Write the answer down before touching code.

**Files**: investigation only

**Validation**:
- The report names the exact location where the distinction is lost, or states clearly that the
  output already distinguishes and FR-005 is already satisfied
- If already satisfied: say so, add the regression test in T026, and do not manufacture a change

### T025 — Surface the distinction

**Purpose**: make the difference visible to the operator.

Scope depends on T024. If the distinction is already in the model, this is a presentation change in
`preflight/cli.py`.

**Steps**:
1. Ensure the rendered output makes the two states unambiguous — an operator should not have to know
   the internal state vocabulary to tell them apart.
2. The `detail` field already carries explanatory text for the `invalid` case
   (*"charter.yaml exists but cannot be parsed"*). Make sure it actually reaches the operator; if it
   is being dropped in rendering, that is likely the whole fix.
3. Keep the F2 case clear: a legacy-bundle project should not read as "no charter at all", because
   the operator does have one and will be confused by that phrasing.
4. Do not add a new state value unless T024 proved the model genuinely cannot express the
   distinction.

**Files**: `src/specify_cli/charter_runtime/preflight/cli.py`

**Validation**:
- F1 and F4 produce visibly different output
- F2 does not read as "no charter at all"
- No new state value added unless T024 justified it

### T026 — Verify distinguishability on every surface

**Steps**:
1. Assert F1 and F4 produce distinguishable output on the preflight surface.
2. Assert the same for the operator-facing charter diagnostics WP04 converged, so the distinction is
   not lost on a different surface.
3. Assert F1 remains **non-blocking** (FR-006). This is the guard against making a clarity change
   into a behaviour regression.

**Files**: `tests/specify_cli/charter_preflight/test_cli.py`

**Validation**:
- Both states distinguishable everywhere an operator can look
- F1 still advisory, still non-blocking

---

## Definition of Done

- [ ] T024's investigation recorded, naming where the distinction is lost (or stating it is not)
- [ ] F1 and F4 produce visibly different operator output
- [ ] F2 does not read as "no charter at all"
- [ ] F1 remains non-blocking
- [ ] No new state value introduced unless justified by T024
- [ ] `uv run ruff check <changed files>` exits 0
- [ ] `uv run mypy --strict` shows no new errors versus the merge base

## Reviewer Guidance

1. **Read T024's findings first.** If the implementer added a new state value without T024 proving
   the existing vocabulary was insufficient, reject — that is churn on a governance surface.
2. **Check F1 did not become blocking.** This is the one way a clarity change turns into a
   regression. Run the F1 fixture through the gate yourself.
3. **Read the actual output strings** for F1, F2 and F4. Would an operator who does not know the
   codebase correctly tell these apart? That is the bar, not whether an assertion passes.
4. **Check for out-of-map edits** to `computer.py` or `runner.py`. Narrow and justified with a
   recorded rationale is acceptable; anything larger should have been reported as a finding instead.
