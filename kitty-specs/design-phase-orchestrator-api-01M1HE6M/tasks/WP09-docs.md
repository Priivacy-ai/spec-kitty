---
work_package_id: WP09
title: Docs — orchestrator-api.md, host-boundary-rules.md, CHANGELOG.md
dependencies:
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
subtasks:
- T042
- T043
- T044
- T045
- T046
history: []
agent_profile: scribe-sally
authoritative_surface: docs/api/orchestrator-api.md
create_intent: []
execution_mode: planning_artifact
model: ''
owned_files:
- docs/api/orchestrator-api.md
- src/charter/offering/skills/spec-kitty-orchestrator-api-operator/references/host-boundary-rules.md
- docs/changelog/CHANGELOG.md
role: documentarian
tags: []
tracker_refs: []
---

# WP09 — Docs: orchestrator-api.md, host-boundary-rules.md, CHANGELOG.md

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `scribe-sally`
- **Role**: `documentarian`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Document all 11 new orchestrator-api verbs (SC-006) at the same detail
level as the existing 10 (request shape, response shape, error codes),
and update `host-boundary-rules.md`'s Boundary Decision Matrix so it no
longer implies an external host must cross into host-CLI territory to
drive design phases.

## Context

**This WP lands LAST, deliberately** (depends on WP03-WP08, all of them —
per plan.md, this documents the LANDED behavior, not the plan's prediction
of it). Do not write this doc from spec.md/plan.md alone — cross-check
every request/response shape against the ACTUAL code landed in WP03-WP08
(Gate Set item 9: "WP09's doc updates are cross-checked against the
actual verb behavior landed in WP03–WP08, not written from the spec
alone"). If any verb's actual landed shape differs from what the spec/plan
predicted, document the ACTUAL shape and flag the discrepancy in your
final report — do not silently paper over it by writing what the spec
said instead of what the code does.

**Files to update**:
- `docs/api/orchestrator-api.md` — new sections for all 11 verbs:
  `specify`, `plan`, `tasks`, `check-prerequisites`, `record-analysis`,
  `open-decision`, `resolve-decision`, `defer-decision`, `cancel-decision`,
  `design-status`, `answer-decision`. Match the existing 10-verb sections'
  format and detail level exactly (read the existing doc's structure
  before writing — do not invent a new format).
- `src/charter/offering/skills/spec-kitty-orchestrator-api-operator/references/host-boundary-rules.md`
  — add design-phase rows to the Boundary Decision Matrix. This is a
  markdown skill-reference doc, not a Python module — the `__all__`
  convention (charter C-007) does NOT apply here (see the mission-level
  note in `tasks.md` — this WP's edit is to prose/markdown, not a module).
- `docs/changelog/CHANGELOG.md` — entry for the 1.4.0 bump + the 11 new
  verbs, matching this file's existing entry format/style.

**Markdown lint applies** (`.markdownlint-cli2.jsonc` present at repo
root, Gate Set item 8) — run it against your changes before considering
this WP done.

## Subtask T042: ATDD note — the "RED" for this WP is doc-presence, not a pre-existing script

**Purpose**: State this WP's ATDD approach explicitly rather than papering
over the fact that no automated orchestrator-api-doc-consistency check
exists in this repo today (verified: `grep -rl "orchestrator-api.md"
tests/ scripts/` returns no dedicated doc-consistency test/script).

**Steps**:
1. Since plan.md § (h) states every WP (including WP09) follows the
   RED-then-GREEN pattern, and no pre-existing automated doc-consistency
   check exists to reuse, author a SMALL, genuinely-RED check as part of
   this WP rather than skipping the discipline: a short pytest test (or a
   `scripts/`-style check, whichever fits this repo's convention better —
   check for precedent of doc-presence tests elsewhere in `tests/` before
   choosing) asserting each of the 11 new verb names appears as a
   markdown heading in `docs/api/orchestrator-api.md`. This is RED before
   you write the doc content (the headings don't exist yet) and GREEN
   after.
2. **This is a judgment call, not something the plan pre-specified with a
   named existing check** — state explicitly in this WP's commit/report
   that this doc-presence check was authored FOR this WP (not reused from
   an existing one), since plan.md § (h)'s phrase "the markdown-lint +
   doc-consistency check" does not name a concrete existing script this
   repo already has. Flag this as a plan-vs-live-repo gap rather than
   silently inventing a check without saying so.
3. If you determine an existing check DOES cover this (re-search before
   assuming none exists) — use that instead and drop this subtask's
   authored version; document which you used.

**Files**: a small new test/check file (~20-40 lines) — pick a path consistent with this repo's conventions (e.g. under `tests/docs/` or `scripts/` if either directory already holds doc-consistency checks; otherwise the WP author's own reasonable choice, documented).

**Validation**: fails before WP09's doc content is written; passes after.

## Subtask T043: Write `docs/api/orchestrator-api.md` verb sections

**Purpose**: The core documentation deliverable.

**Steps**:
1. Read the existing doc's format for the 10 existing verbs (request
   shape, response shape including `data` field descriptions, error codes
   with their triggering conditions, at minimum one example invocation
   per verb).
2. Write one section per new verb, in the SAME format, sourced from the
   ACTUAL landed `commands.py` code (option names, `data` field names,
   `error_code` values) — not from spec.md's prose alone. Cross-check
   every field name against the real `@app.command` function signatures
   and `make_envelope`/`_fail` calls in WP03-WP08's landed diffs.
3. For `answer-decision` specifically: document the composite nature
   explicitly (persists the answer AND advances the DAG AND performs the
   three lifecycle/event-log side effects) — do not document it as if it
   were a simple single-purpose verb; a host integrator needs to know this
   one call does all of that.
4. For `record-analysis`: document the artifact-verified, time-bounded
   success semantics (NFR-004) — a host integrator needs to know success
   is determined by re-reading the artifact, not by the call's own
   return/raise/hang behavior, so they don't build retry logic that
   assumes the opposite.

**Files**: `docs/api/orchestrator-api.md` (~11 new sections, sized to match existing entries — likely 400-700 total new lines across all 11).

**Validation**: T042's doc-presence check passes; markdown-lint passes.

## Subtask T044: Update `host-boundary-rules.md` Boundary Decision Matrix

**Purpose**: Close the gap the spec's own Summary names: "an external host
driving design phases has no compliant path" — after this mission, it
does, and the doc must say so.

**Steps**:
1. Add design-phase rows to the Boundary Decision Matrix (the same table
   structure the existing WP-loop rows use), naming each new verb's
   boundary classification (orchestrator-api-compliant caller vs. host-CLI
   territory) — mirroring the existing rows' format exactly.
2. Remove or correct any existing prose in this doc that states or implies
   an external host MUST cross into host-CLI territory for
   specify/plan/tasks/analyze/decision-resolution — that statement is now
   false and must not survive this mission's docs pass.

**Files**: `src/charter/offering/skills/spec-kitty-orchestrator-api-operator/references/host-boundary-rules.md` (~30-60 line diff).

**Validation**: markdown-lint passes; manual read-through confirms no
stale "must cross into host-CLI territory" claim survives for the newly
covered verbs.

## Subtask T045: Update `docs/changelog/CHANGELOG.md`

**Purpose**: Standard changelog entry.

**Steps**:
1. Add an entry for the 1.4.0 orchestrator-api contract bump, naming the
   11 new verbs, matching this file's existing entry format/style (check
   the most recent 2-3 entries for the current convention before writing).
2. Include the `#3837` issue reference.

**Files**: `docs/changelog/CHANGELOG.md` (~10-20 line addition).

**Validation**: markdown-lint passes.

## Subtask T046: Cross-check against landed code + final lint pass

**Purpose**: Gate Set item 9 — architecture/docs consistency.

**Steps**:
1. Re-read WP03-WP08's actual landed diffs (not just their task files) and
   confirm every documented field name, error code, and option name in
   `orchestrator-api.md` matches the real code exactly.
2. Run the full markdown lint (`.markdownlint-cli2.jsonc`) against all
   three changed files.
3. Report any discrepancy found between what the spec/plan predicted and
   what actually landed — do not silently resolve a discrepancy by
   documenting the spec's prediction instead of the real behavior.

**Files**: none new — verification pass.

**Validation**: markdown-lint clean; a spot-check of at least 3 verbs'
documented `data` fields against the real `commands.py` code confirms
exact match.

## Write-Scope / Adjacent Open PRs

None of this WP's three files (`docs/api/orchestrator-api.md`,
`host-boundary-rules.md`, `docs/changelog/CHANGELOG.md`) are touched by
any of the three adjacent open PRs (#3842, #3826, #3836) — no same-file
rebase-risk note applies.

## `__all__` note (charter C-007)

Does not apply to this WP's files — both are markdown documents, not
Python modules under `src/charter/` or `src/kernel/`. (See the
mission-level note at the top of `tasks.md` for the full mission-wide
determination.)

## Definition of Done

- [ ] T042's doc-presence RED check authored and confirmed RED before doc
      content is written, GREEN after — with an explicit note on whether
      it reused an existing check or was authored fresh for this WP.
- [ ] All 11 new verbs documented in `orchestrator-api.md`, cross-checked
      against the ACTUAL landed code (not spec.md prose alone).
- [ ] `host-boundary-rules.md` Boundary Decision Matrix updated; no stale
      "must cross into host-CLI territory" claim survives for the newly
      covered verbs.
- [ ] `CHANGELOG.md` entry added, referencing #3837.
- [ ] Markdown lint clean on all three files.
- [ ] Any spec-vs-landed-code discrepancy found during cross-check
      reported explicitly, not silently resolved toward the spec's
      prediction.

Run: `spec-kitty agent action implement WP09 --agent <name>`

## Risks

- **Writing from the spec instead of the code**: the single most likely
  mistake in a docs WP is transcribing spec.md's predicted shapes instead
  of reading the actual landed `commands.py` — T046 exists specifically to
  catch this; do not skip it as "just a formality."
- **Stale boundary-rules prose**: an easy miss is updating the Matrix table
  but leaving old prose elsewhere in the same doc that still claims the
  gap exists — read the WHOLE file, not just the table.

## Reviewer Guidance

- Spot-check at least 3 documented verbs' `data` field names directly
  against the real `commands.py` code — do not trust the doc's own
  internal consistency as proof of code-accuracy.
- Confirm `record-analysis`'s documentation correctly conveys the
  artifact-verified success semantics (NFR-004) — a doc that describes
  simple "call succeeds or fails" semantics here would mislead a real host
  integrator into building the wrong retry logic.
- Confirm `host-boundary-rules.md` no longer contains any prose implying
  design phases require host-CLI crossing.
