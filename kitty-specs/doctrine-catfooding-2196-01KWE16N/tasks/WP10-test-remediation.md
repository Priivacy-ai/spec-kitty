---
work_package_id: WP10
title: §4 Test Remediation (Lightest)
dependencies:
- WP01
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T043
- T044
- T045
- T046
phase: Phase 2 - Extend Conversions (LB)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1879167"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/directives/built-in/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/directives/built-in/041-tests-as-scaffold-not-friction.directive.yaml
- src/doctrine/styleguides/built-in/testing-principles.styleguide.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – §4 Test Remediation (Lightest)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `doctrine-daphne`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

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
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

**This is the lightest conversion WP.** Extend one existing directive and add one cross-link for §4:

1. **DIRECTIVE_041 (extend, minimal)** — add ONLY the "live evidence over static-fixed / carry OPEN until live repro" atom. This is the single atom confirmed absent from all existing §4-adjacent artifacts (041, 034, testing-principles.styleguide, test-first-bug-fixing.procedure).
2. **testing-principles.styleguide.yaml (cross-link only)** — add a cross-reference from 041 to the styleguide (and optionally from the styleguide back to 041). No new content authored in the styleguide body.

**Hard constraint — no triple authority (research.md D-7)**: the "red-first / pre-existing entry point, not the fix's new API" refinement already lives **verbatim in DIRECTIVE_034-test-first-development (lines 16-22)**. Adding it to 041 OR to `test-first-bug-fixing.procedure` would create a 034↔041↔procedure triple authority — a split-brain defect. WP10 must REFERENCE DIRECTIVE_034 in prose for the red-first rule, NOT restate it.

**No new §4 directive**: do not author a new directive for §4. Extend 041 only.

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T043 output) — must read 041, 034 lines 16-22, testing-principles.styleguide, test-first-bug-fixing.procedure
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for extended artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12; run against extended 041 directive and testing-principles styleguide)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges in extended 041 (cross-link to testing-principles and DIRECTIVE_034)
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §4 of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **Confirmed atom coverage (research.md D-7)**:
  - `041-tests-as-scaffold-not-friction`: covers three-verdict remediation, red-first discipline, no-retry-to-green, realistic test data. Does NOT cover "live evidence over static-fixed."
  - `034-test-first-development` (lines 16-22): covers the red-first "pre-existing entry point, not the fix's new API" refinement verbatim. This is the atom WP10 must NOT restate.
  - `testing-principles.styleguide`: covers production-shaped test data, stale-assertion remediation. Adjacent to §4.
  - `test-first-bug-fixing.procedure`: covers the bug-fix workflow with test-first. Adjacent.
  - **Absent from all**: "live evidence over static-fixed" — a bug witnessed in a real run is NOT fixed just because the code looks fixed; carry the bug OPEN until live repro proves it fixed. This is the single atom WP10 adds.
- **C-001 (mandatory)**: the audit must read all four artifacts listed above and record findings before authoring.
- **"Live evidence over static-fixed" definition**: after a fix is committed, the bug is not closed until it is reproduced (and confirmed absent) in a live run. Static code reading — "the code looks fixed" — does not constitute evidence. The bug stays OPEN until a live repro run produces the expected (fixed) behavior.
- **DIRECTIVE_034 reference**: the prose in 041's body should cross-reference DIRECTIVE_034 for the red-first "pre-existing entry point" discipline — one sentence such as "For the pre-existing-entry-point red-first discipline (bugfix test must be red against pre-fix code via the pre-existing entry point, not the fix's new API), see DIRECTIVE_034."
- **C-003**: `owned_files` = 041 + testing-principles.styleguide. Do NOT edit 034 or `test-first-bug-fixing.procedure`.
- **PD-2**: inline DRG edges only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T043 – [C-001] Overlap-audit §4

- **Purpose**: Mandatory overlap-audit. Read all four §4-adjacent artifacts; record precise coverage to confirm the "live evidence over static-fixed" atom is the sole gap.
- **Steps**:
  1. Read `src/doctrine/directives/built-in/041-tests-as-scaffold-not-friction.directive.yaml` in full. Note which §4 atoms are already encoded. Record.
  2. Read `src/doctrine/directives/built-in/034-test-first-development.directive.yaml` **specifically lines 16-22** (or the entire file). Identify and record verbatim the red-first "pre-existing entry point, not the fix's new API" text. This atom is COVERED by 034 → do NOT add to 041 or the procedure.
  3. Read `src/doctrine/styleguides/built-in/testing-principles.styleguide.yaml`. Note coverage. Record.
  4. Read `src/doctrine/procedures/built-in/test-first-bug-fixing.procedure.yaml`. Note coverage. Record.
  5. Confirm "live evidence over static-fixed" (carry OPEN until live repro) is absent from all four.
  6. Write decision: extend 041 with ONLY the live-evidence atom; add cross-link to 034 and testing-principles; no new §4 directive; do NOT edit 034 or the procedure.
- **Files**: None (audit only).
- **Parallel?**: No — must be first.
- **Notes**: The verbatim red-first text from 034 must appear in the Activity Log to demonstrate the triple-authority risk was identified.

### Subtask T044 – Extend DIRECTIVE_041 with live-evidence atom

- **Purpose**: Add the single uncovered atom to DIRECTIVE_041. Minimal, targeted extension.
- **Steps**:
  1. Open `src/doctrine/directives/built-in/041-tests-as-scaffold-not-friction.directive.yaml`.
  2. Add ONE new rule/atom to the body: **"Live evidence over static-fixed"** — a bug is not considered fixed until it is confirmed absent in a live reproduction run. After committing a fix, carry the bug tracker item OPEN until a live run produces the expected (fixed) behavior. A code inspection that "looks fixed" does not constitute evidence. Only a live run closes the loop.
  3. Add a prose cross-reference to DIRECTIVE_034 for the red-first pre-existing-entry-point discipline (one sentence; do NOT copy 034's text into 041).
  4. Do NOT restructure or rewrite existing 041 content — only extend.
- **Files**: `src/doctrine/directives/built-in/041-tests-as-scaffold-not-friction.directive.yaml` (extend existing)
- **Parallel?**: No — T045 depends on this.
- **Notes**: This subtask adds exactly ONE atom. If you find yourself adding more §4 rules, re-read T043's audit output — other rules are already covered.

### Subtask T045 – Cross-link to testing-principles.styleguide

- **Purpose**: Add a cross-reference from the extended 041 to `testing-principles.styleguide.yaml`, and add an inline DRG edge.
- **Steps**:
  1. In `041-tests-as-scaffold-not-friction.directive.yaml`, add an inline DRG edge: `suggests: [urn:styleguide:testing-principles, urn:directive:DIRECTIVE_034]`.
  2. Optionally, open `testing-principles.styleguide.yaml` and add a brief cross-reference back to 041 (one line in the body, or a DRG `suggests` edge to `041`). Do NOT add new content to the styleguide body; a DRG edge is sufficient.
  3. Do NOT add the live-evidence atom to the styleguide body — it belongs in 041.
- **Files**: 
  - `src/doctrine/directives/built-in/041-tests-as-scaffold-not-friction.directive.yaml` (DRG edges)
  - `src/doctrine/styleguides/built-in/testing-principles.styleguide.yaml` (cross-link only — minimal)
- **Parallel?**: No.
- **Notes**: If the styleguide's schema allows a `suggests` edge to 041, prefer that over an inline prose sentence.

### Subtask T046 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates. Extra attention: verify the triple-authority guard.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate the extended directive YAML.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the extended `041-tests-as-scaffold-not-friction.directive.yaml` and the modified `testing-principles.styleguide.yaml`. Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. Confirm ONLY the live-evidence atom was added to 041 — no other new §4 rules.
  5. Confirm 034 content was NOT copied into 041 (read both files side-by-side if uncertain).
  6. Confirm `034-test-first-development.directive.yaml` was NOT edited.
  7. Confirm `test-first-bug-fixing.procedure.yaml` was NOT edited.
  8. Confirm no new §4 directive was created.
  9. Confirm `graph.yaml` UNCHANGED; agent-profile wiring DEFERRED to WP12.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after T044.
- `pytest tests/architectural/test_no_legacy_terminology.py -q`.
- `git diff --stat HEAD` — confirm ONLY `041-tests-as-scaffold-not-friction.directive.yaml` and `testing-principles.styleguide.yaml` are modified. If `034-test-first-development.directive.yaml` or `test-first-bug-fixing.procedure.yaml` appear in the diff, a scope boundary was violated.
- Confirm the "live evidence over static-fixed" atom is present in 041 by grepping: `grep -A3 "live.evidence\|static.fixed\|carry.*OPEN" src/doctrine/directives/built-in/041-tests-as-scaffold-not-friction.directive.yaml`.
- Confirm `DIRECTIVE_034` is cross-referenced (in prose or DRG edge) but NOT paraphrased in 041's body.

## Risks & Mitigations

- **Triple authority (highest risk for this WP)**: Adding the red-first "pre-existing entry point" atom from DIRECTIVE_034 into 041 or into `test-first-bug-fixing.procedure` would create a 034↔041↔procedure triple authority split-brain. The mitigation: T043 must record the verbatim 034 lines 16-22 in the Activity Log; T046 must confirm 034 and the procedure are unchanged.
- **Over-extension**: WP10 adds exactly ONE atom. If you find yourself adding more §4 rules (e.g. "realistic test data" or "no-retry-to-green"), re-check T043 — those rules are already in 041 and adding them again creates duplication.
- **New §4 directive**: authoring a new directive for §4 would create a split-brain with 041. Do NOT. The research and spec both confirm that 041 is the correct extension surface and no new §4 directive is warranted.
- **testing-principles.styleguide edit scope**: WP10 owns the styleguide for cross-link purposes only. Do NOT add the live-evidence atom to the styleguide body — it belongs exclusively in 041. The styleguide edit (if any) is one DRG edge.

## Dependency Notes

- WP10 is parallelizable with WP02, WP04, WP05, WP06, WP07, WP08, WP11 (disjoint surfaces).
- WP10 enables WP12 (the extended 041 has new DRG edges that must appear in the single regen).

## Review Guidance

- T043 audit records the verbatim red-first text from 034 lines 16-22.
- 041 body has EXACTLY ONE new atom ("live evidence over static-fixed"); no 034 content copied in.
- `suggests: [testing-principles, DIRECTIVE_034]` edges in 041.
- 034 and `test-first-bug-fixing.procedure.yaml` UNCHANGED.
- No new §4 directive created.
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED; agent-profile wiring deferred to WP12.

## Parallel Opportunities

WP10 is parallelizable with all other LA/LB WPs (disjoint surfaces: 041 and testing-principles.styleguide are not owned by any other WP). WP10 can start as soon as WP01 is `approved`.

## Updating Status

Use `spec-kitty agent tasks move-task WP10 --to claimed` when starting. Record in Activity Log before `for_review`:
1. T043 audit: verbatim 034 lines 16-22 recorded; "live-evidence-over-static-fixed" confirmed absent from all four artifacts.
2. Exactly ONE atom added to 041 (the live-evidence atom).
3. DIRECTIVE_034 cross-referenced in 041 prose for red-first rule.
4. `git diff --stat` confirms only 041 and testing-principles.styleguide modified.
5. Doctor doctrine + terminology guard results (must be green).
6. No new §4 directive created; 034 and test-first-bug-fixing.procedure unchanged.
7. Agent-profile wiring deferred to WP12; `graph.yaml` unchanged.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:06:19Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Assigned agent via action command
- 2026-07-01T10:16:20Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Ready for review: §4 live-evidence atom added to DIRECTIVE_041; DRG edges to DIRECTIVE_034+testing-principles; triple-authority guard verified; all 3 gates green; 034 and procedure unchanged; graph.yaml deferred to WP12
- 2026-07-01T10:16:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=1799445 – Started review via action command
- 2026-07-01T10:21:33Z – user – shell_pid=1799445 – Moved to planned
- 2026-07-01T10:22:26Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1847032 – Started implementation via action command
- 2026-07-01T10:35:00Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1847032 – **T043 overlap-audit (C-001) — cycle-1 remediation**: verbatim 034 red-first record and per-artifact coverage findings follow.

  **DIRECTIVE_034 lines 16–22 — verbatim (procedures: and integrity_rules: red-first bullets):**

  ```
  procedures:
    - When fixing a bug, write a reproduction test first that fails, then apply the fix.
    - Reproduce the bug through the PRE-EXISTING (stable) entry point — the command, public
      function, or seam that exists on the unfixed code — never through the fix's
      not-yet-written API. A reproduction test must go red BECAUSE THE BUG MANIFESTS in the
      assertion (the wrong value/status/path/state), not because a new symbol or parameter
      the fix introduces is missing (ImportError/TypeError at collection).
    - Prove red-first — run the reproduction test against the unfixed code and confirm it
      fails for the right reason, then apply the fix and confirm green. New-API unit tests
      are fine as contract coverage, but they are not the bug-capture.
  integrity_rules:
    - Production code must not be written ahead of a failing test that motivates it.
    - Skipping the test-first cycle requires explicit justification in the commit or PR.
    - A bug-reproduction test that can only run AFTER the fix exists (it imports the fix's
      new symbol or passes its new parameter) captures the fix's shape, not the bug — it is
      invalid; rewrite it to drive the stable entry point, and move any new-API import to
      lazy/in-test scope so the reproduction still collects and fails red on the unfixed code.
  ```

  **Per-artifact coverage findings (grep: "live.evidence\|static.fixed\|carry.*OPEN" against all four):**
  - `041-tests-as-scaffold-not-friction.directive.yaml` — covers three-verdict remediation, red-first discipline, no-retry-to-green, realistic test data. "live evidence over static-fixed" / "carry OPEN until live repro": **ABSENT → gap confirmed.**
  - `034-test-first-development.directive.yaml` (lines 16–22 above) — covers the "PRE-EXISTING entry point" and "Prove red-first" pre-fix discipline. "live evidence over static-fixed": **ABSENT → gap confirmed. Atom is covered by 034 for pre-fix phase; not restated in 041.**
  - `testing-principles.styleguide.yaml` — covers production-shaped test data, stale-assertion remediation. "live evidence over static-fixed": **ABSENT → gap confirmed.**
  - `test-first-bug-fixing.procedure.yaml` — covers bug-fix workflow with test-first gate. "live evidence over static-fixed": **ABSENT → gap confirmed.**

  **Distinction — why this is not a duplicate of 034 (no triple authority):**
  - DIRECTIVE_034 lines 16–22 = **pre-fix phase**: how to write the failing reproduction test before the fix exists — stable entry point, test must go red because the bug manifests, not because a new API symbol is missing. This atom is COVERED by 034 and must NOT be restated in 041 or the procedure.
  - 041's new atom ("live evidence over static-fixed") = **post-fix phase**: after the fix is committed, the bug tracker item is NOT closed until a live run confirms the bug is absent. Static code inspection ("the code looks fixed") does not count as evidence. The item stays OPEN until live repro produces the expected (fixed) behavior.
  - These are distinct temporal phases (pre-fix reproduction vs post-fix closure), distinct concerns (test authoring vs tracker hygiene), and distinct authority surfaces. No triple authority exists. 041 cross-references 034 in one prose sentence for the pre-fix rule rather than restating it.
  - **Decision**: extend 041 with ONLY the live-evidence atom; cross-reference 034 in prose; no new §4 directive; 034 and test-first-bug-fixing.procedure left unedited.
- 2026-07-01T10:28:15Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1847032 – Cycle 1: verbatim 034 overlap-audit recorded per review
- 2026-07-01T10:28:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=1879167 – Started review via action command
- 2026-07-01T10:31:30Z – user – shell_pid=1879167 – Cycle 1: verbatim T043 audit now recorded; code unchanged and correct
