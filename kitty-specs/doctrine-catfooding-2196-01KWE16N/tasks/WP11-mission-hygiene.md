---
work_package_id: WP11
title: §8 Mission Hygiene
dependencies:
- WP01
requirement_refs:
- FR-013
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T047
- T048
- T049
- T050
- T051
- T052
phase: Phase 2 - Extend Conversions (LB)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1833897"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/styleguides/built-in/
create_intent:
- src/doctrine/tactics/built-in/ownership-map-leeway.tactic.yaml
- src/doctrine/tactics/built-in/reviewer-implementer-role-separation.tactic.yaml
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/styleguides/built-in/planning-and-tracking.styleguide.yaml
- src/doctrine/tactics/built-in/ownership-map-leeway.tactic.yaml
- src/doctrine/tactics/built-in/reviewer-implementer-role-separation.tactic.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP11 – §8 Mission Hygiene

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

Extend one existing styleguide and author two new tactics for §8 of the Quality & Tech-Debt Standing Orders:

1. **planning-and-tracking.styleguide.yaml (SOLE OWNER, extend)**: add the issue-matrix discipline content + the §2 tracker-hygiene bullet (relocated from §2 per spec). WP11 is the sole owner of this file — WP09 must NOT edit it.
2. **Tactic (NEW)** — `ownership-map-leeway.tactic.yaml`: operationalizes the "no-overlap is the real guard" principle for ownership maps in tasks/WPs. Must align with the existing tasks-packages/tasks mission-step prompt language.
3. **Tactic (NEW)** — `reviewer-implementer-role-separation.tactic.yaml`: captures the reviewer≠implementer rule. Must REFERENCE (not restate) the wiring already in `mission-runtime.yaml` and the review/implement mission-step prompts.

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T047 output) — must read planning-and-tracking.styleguide, tiered-standards.styleguide, mission-runtime.yaml, and review/implement mission-step prompts; must quote verbatim tiered-standards lines + mission-runtime profile assignments and confirm new tactics reference-not-restate (SHOULD-TIGHTEN 6)
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for new/extended artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12; run against the extended styleguide and both new tactics)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges in extended styleguide + new tactics
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §8 of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **C-003 (SOLE OWNER)**: WP11 is the sole owner of `planning-and-tracking.styleguide.yaml`. WP09 must NOT edit this file. Any §2 tracker-hygiene content that belongs here must be added by WP11, not WP09.
- **Existing coverage to READ**:
  - `planning-and-tracking.styleguide.yaml`: read fully before extending. Note what is already covered (partial issue-matrix discipline, partial tracker hygiene).
  - `tiered-standards.styleguide.yaml`: read fully. The tiered-rigour content is COMPLETE — reference it, do NOT restate or extend it.
  - `src/doctrine/missions/*/mission-runtime.yaml`: confirms role wiring (reviewer-renata for review step, python-pedro for implement). The role-separation tactic REFERENCES this; it does not restate or override it.
  - Review/implement mission-step prompts in `src/doctrine/missions/mission-steps/software-dev/`: these operationalize the role-separation. Read before authoring T050.
- **Ownership-map-leeway alignment**: the "no-overlap is the real guard" language exists verbatim in the tasks-packages and tasks mission-step prompts (`src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md`, `src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md`). The tactic REFERENCES those prompts — it does NOT restate or supersede the "no-overlap" rule with a different formulation.
- **Role-separation: no new operationalization needed**: the review/implement profile routing is already wired in mission-runtime.yaml. The tactic adds the doctrine layer (the "why" and the constraint) but does not introduce new wiring. Adding redundant wiring would create a split-brain with mission-runtime.yaml.
- **Tracker-hygiene bullet (from §2)**: the §2 standing orders included a tracker-hygiene item ("at spec time: every addressed issue → issue-matrix + claim + tracker comment naming the mission"). This belongs in planning-and-tracking.styleguide.yaml, not in 025 (which is §2 campsite). WP09 should have left this for WP11.
- **PD-2**: inline DRG edges only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T047 – [C-001] Overlap-audit §8

- **Purpose**: Mandatory overlap-audit. Read all four named artifacts; record coverage and gaps before authoring.
- **Steps**:
  1. Read `src/doctrine/styleguides/built-in/planning-and-tracking.styleguide.yaml` in full. Note: what issue-matrix discipline is already encoded? What is the current state of tracker-hygiene content? Record.
  2. Read `src/doctrine/styleguides/built-in/tiered-standards.styleguide.yaml` in full. Confirm it is complete — record that tiered-rigour will be REFERENCED, not extended/restated.
  3. Read `src/doctrine/missions/software-dev/mission-runtime.yaml` (or wherever the canonical mission-runtime lives). Note `reviewer-renata` as review-step profile and `python-pedro` as implement-step profile. Record that role-separation is OPERATIONALIZED here — the new tactic references, does not restate.
  4. Read the review and implement mission-step prompts in `src/doctrine/missions/mission-steps/software-dev/`. Note the profile assignments and confirm the role-separation wiring is present.
  5. Read the tasks-packages and tasks mission-step prompts for the "no-overlap is the real guard" ownership-map language.
  6. Write augment-vs-create decisions:
     - planning-and-tracking.styleguide: EXTEND (issue-matrix discipline + tracker-hygiene bullet).
     - tiered-standards.styleguide: REFERENCE ONLY (do NOT extend or restate).
     - Role separation: operationalized in mission-runtime — author a tactic that references it.
     - Ownership-map-leeway: not in doctrine yet → author tactic aligned with prompt language.
  7. **Verbatim text requirement (SHOULD-TIGHTEN 6)**: record in the Activity Log:
     - The SPECIFIC lines from `tiered-standards.styleguide.yaml` that encode the tiered-rigour content (verbatim, not paraphrased). State explicitly that these lines are the authoritative surface and the new tactics REFERENCE them, not restate or extend them.
     - The SPECIFIC lines from `mission-runtime.yaml` (or the mission-step prompts) that define the profile assignments (`reviewer-renata` for review, `python-pedro` for implement). Confirm that the role-separation tactic references these lines as its authority, not introducing a new or parallel wiring. A reviewer uses these verbatim quotes to mechanically confirm the new tactics do not restate or contradict the existing authoritative surface.
- **Files**: None (audit only).
- **Parallel?**: No — must be first.

### Subtask T048 – Extend planning-and-tracking.styleguide.yaml

- **Purpose**: Add the issue-matrix discipline and the §2 tracker-hygiene bullet to the styleguide. WP11 is SOLE owner.
- **Steps**:
  1. Open `src/doctrine/styleguides/built-in/planning-and-tracking.styleguide.yaml`.
  2. Add (or extend existing section on) **issue-matrix discipline**: at spec time, every issue the mission addresses must be listed in the mission's issue-matrix with the verdict (in-scope/out-of-scope/deferred). In-scope issues get a claim (assigned to the operator) and a tracker comment naming the mission.
  3. Add **tracker-hygiene bullet** (relocated from §2): at spec time, every addressed issue → issue-matrix + claim (assign operator) + tracker comment naming the mission. This is the canonical location for this rule.
  4. Do NOT restructure or remove existing content.
  5. Add a cross-reference to `tiered-standards.styleguide` (do NOT add content from it — just a reference).
- **Files**: `src/doctrine/styleguides/built-in/planning-and-tracking.styleguide.yaml` (extend existing)
- **Parallel?**: No — T049/T050 can start after this.
- **Notes**: This file is SOLE-OWNED by WP11. If WP09 accidentally edited it, the T047 audit diff will surface that; flag it before proceeding.

### Subtask T049 – Author ownership-map-leeway tactic

- **Purpose**: Encode the "no-overlap is the real guard" ownership principle as a doctrine tactic, aligned with the existing mission-step prompt language.
- **Steps**:
  1. Read `src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md` and `src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md` — locate the "no-overlap is the real guard" language verbatim. Record it.
  2. Create `src/doctrine/tactics/built-in/ownership-map-leeway.tactic.yaml`.
  3. `id: ownership-map-leeway`, `title: "Ownership Map Leeway"`.
  4. Body: The strict prohibition on editing files outside `owned_files` causes implementers to work around the ownership map (e.g. duplicate logic, leave TODOs, defer related fixes). The real guard is **no-overlap between WPs' owned surfaces** — as long as two WPs do not own the same file, leeway to edit adjacent files with a rationale is allowed. The tactic: (a) implementers may edit files adjacent to their owned surface if they record a rationale and confirm no WP owns that file in the current task decomposition; (b) no-overlap is the hard constraint; strict prohibition of any cross-boundary edit is the anti-pattern (causes #1766-style workarounds).
  5. Cross-reference the mission-step prompts: "This tactic aligns with the 'no-overlap is the real guard' language in the tasks-packages and tasks mission-step prompts."
  6. Add inline DRG edge: `suggests: [urn:styleguide:planning-and-tracking]`.
- **Files**: `src/doctrine/tactics/built-in/ownership-map-leeway.tactic.yaml` (create new)
- **Parallel?**: [P] Can proceed in parallel with T050 after T047-T048 are complete.
- **Notes**: The tactic must use the same "no-overlap is the real guard" formulation as the prompts — not a paraphrase that introduces drift.

### Subtask T050 – Author reviewer-implementer-role-separation tactic

- **Purpose**: Encode the reviewer≠implementer rule as a doctrine tactic. REFERENCE the mission-runtime.yaml wiring — do NOT restate or override it.
- **Steps**:
  1. Create `src/doctrine/tactics/built-in/reviewer-implementer-role-separation.tactic.yaml`.
  2. `id: reviewer-implementer-role-separation`, `title: "Reviewer/Implementer Role Separation"`.
  3. Body: the reviewer and implementer roles must be distinct agents/sessions for any given WP. An agent that implemented a WP must not also review it. The canonical profile assignments for Spec Kitty missions are: implementer role → `python-pedro` (or mission-type-specific implementer profile); reviewer role → `reviewer-renata`. These assignments are operationalized in `mission-runtime.yaml` and the review/implement mission-step prompts — this tactic provides the doctrine-layer rationale and constraint.
  4. Add a cross-reference: "The operationalized profile assignments are in `src/doctrine/missions/software-dev/mission-runtime.yaml` and the review/implement mission-step prompts."
  5. Add inline DRG edges: `suggests: [urn:styleguide:planning-and-tracking]`.
- **Files**: `src/doctrine/tactics/built-in/reviewer-implementer-role-separation.tactic.yaml` (create new)
- **Parallel?**: [P] Can proceed in parallel with T049.
- **Notes**: Do NOT add new profile wiring or override mission-runtime.yaml. The tactic explains *why* (role separation prevents review bias), not *how* (that is mission-runtime.yaml's job).

### Subtask T051 – Author inline DRG edges

- **Purpose**: Verify all three artifacts' DRG edges are in place; confirm `graph.yaml` unchanged.
- **Steps**:
  1. `planning-and-tracking.styleguide.yaml`: confirm `suggests` edge to `tiered-standards` styleguide and to the two new tactics.
  2. `ownership-map-leeway.tactic.yaml`: confirm `suggests: [planning-and-tracking]`.
  3. `reviewer-implementer-role-separation.tactic.yaml`: confirm `suggests: [planning-and-tracking]`.
  4. Confirm `graph.yaml` NOT modified (PD-2).
- **Files**: Minimal edge edits to the three artifact files (if not already added inline during T048-T050).
- **Parallel?**: No.

### Subtask T052 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate new/extended artifact YAMLs.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the extended `planning-and-tracking.styleguide.yaml` and the two new tactics (`ownership-map-leeway`, `reviewer-implementer-role-separation`). Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. Confirm `tiered-standards.styleguide.yaml` UNCHANGED (reference only).
  5. Confirm `mission-runtime.yaml` UNCHANGED (reference only).
  6. Confirm `planning-and-tracking.styleguide.yaml` extended (not replaced).
  7. Confirm `graph.yaml` UNCHANGED; agent-profile wiring DEFERRED to WP12.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after T048, T049, and T050.
- `pytest tests/architectural/test_no_legacy_terminology.py -q`.
- `git diff --stat HEAD` — confirm only the three owned files are modified.

## Risks & Mitigations

- **Sole-owner violation**: WP09 accidentally editing `planning-and-tracking.styleguide.yaml`. Run `git log --oneline src/doctrine/styleguides/built-in/planning-and-tracking.styleguide.yaml` after WP09 lands to verify it has only one author (WP11).
- **Tiered-standards restatement**: copying tiered-standards content into planning-and-tracking.styleguide. Cross-reference only.
- **Role-separation wiring duplication**: adding profile assignments to the tactic that are already in mission-runtime.yaml. The tactic must not replicate wiring — reference only.

## Review Guidance

- T047 audit reads all four named artifacts with explicit verdicts. Activity Log contains: (a) verbatim `tiered-standards.styleguide.yaml` lines with statement that new tactics reference-not-restate; (b) verbatim `mission-runtime.yaml` profile assignment lines with statement that role-separation tactic references this wiring and does not introduce new/parallel wiring.
- planning-and-tracking.styleguide has issue-matrix discipline + tracker-hygiene bullet.
- tiered-standards.styleguide UNCHANGED.
- mission-runtime.yaml UNCHANGED.
- Ownership-map-leeway tactic uses "no-overlap is the real guard" language.
- Role-separation tactic references mission-runtime.yaml; no new wiring.
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED; agent-profile wiring deferred to WP12.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:06:27Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Assigned agent via action command
- 2026-07-01T10:20:05Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Ready for review: §8 planning-and-tracking extended (issue-matrix discipline + tracker-hygiene bullet); ownership-map-leeway.tactic.yaml + reviewer-implementer-role-separation.tactic.yaml authored with inline DRG edges; all DoD gates green; graph.yaml and tiered-standards UNCHANGED; agent-profile wiring deferred to WP12.
- 2026-07-01T10:20:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=1833897 – Started review via action command
- 2026-07-01T10:25:30Z – user – shell_pid=1833897 – Review PASS (reviewer-renata). planning-and-tracking.styleguide extended with issue-matrix discipline + relocated tracker-hygiene bullet (WP11 sole-owns; +3 tactic/tiered refs). tiered-standards.styleguide, mission-runtime.yaml, graph.yaml ALL zero-diff/empty-log = UNCHANGED. ownership-map-leeway uses verbatim 'no-overlap is the real guard' formulation cited to tasks-packages/tasks prompts. reviewer-implementer-role-separation quotes mission-runtime implementer-ivan/reviewer-renata verbatim, references-not-restates, redundant-wiring listed as failure mode (no split-brain). DRG edges via canonical references: block; shipped_graph_valid green, doctor doctrine healthy (0 skipped/0 invalid), terminology guard green. Diff scope = 3 owned files (WP01 docs are dependency-merge). Anti-pattern checklist all PASS/N-A. Minor non-blocking: T047 verbatim quotes recorded in artifact notes rather than Activity Log; substance verified independently.
