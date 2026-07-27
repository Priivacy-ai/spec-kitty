---
work_package_id: WP09
title: §2 Campsite Cleaning + Debt Paydown
dependencies:
- WP01
- WP02
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
- T042
phase: Phase 2 - Extend Conversions (LB)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1957373"
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
- src/doctrine/directives/built-in/025-boy-scout-rule.directive.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – §2 Campsite Cleaning + Debt Paydown

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

Extend one existing directive for §2 of the Quality & Tech-Debt Standing Orders:

**DIRECTIVE_025 (extend)** — `025-boy-scout-rule.directive.yaml`: add the domain-matched-fold-at-point-cut atom and 024/040 cross-links. **Do NOT author a duplicate campsite directive** — 025 already covers the core boy-scout rule. The uncovered atoms are the domain-matched fold trigger and the debt-paydown sequencing; extend 025 with these.

Critical scope boundaries:
- **planning-and-tracking.styleguide.yaml**: the §2 tracker-hygiene bullet is RELOCATED to §8/WP11. WP09 must NOT edit `planning-and-tracking.styleguide.yaml` — that file is SOLE-OWNED by WP11.
- **frozen-baseline-shrink-only-ratchet tactic**: owned by WP02. WP09 REFERENCES it via DRG edges but does NOT edit the tactic file.
- **brownfield-onboarding.paradigm.yaml**: owned by WP08. WP09 REFERENCES it via DRG edges but does NOT edit the paradigm file.
- **024 and 040 directives**: WP09 adds cross-links FROM 025 TO 024/040. WP09 does NOT edit 024 or 040 — only 025 is in `owned_files`.

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T038 output) — must explicitly read 025, 024, 040, and planning-and-tracking.styleguide; must quote verbatim the existing DIRECTIVE_025 text and state why the new atom is distinct (SHOULD-TIGHTEN 6)
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for extended artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12; run against extended 025 directive)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges in extended 025 (referencing ratchet tactic + brownfield paradigm via `suggests`)
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §2 of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **Depends on WP02**: WP09's DRG edges reference the `frozen-baseline-shrink-only-ratchet` tactic authored by WP02. WP09 should run after WP02 is approved (or use a forward-reference URN and accept that WP12's regen validates it).
- **Depends on WP08 (soft)**: WP09 references `brownfield-onboarding.paradigm.yaml` which WP08 extends. Coordinate so WP08 lands its paradigm extension before WP09's DRG edges are validated, or use a forward-reference.
- **Augment-vs-create decision (pre-decided per research.md D-2)**: extend 025 (not create). The uncovered atoms are: (a) domain-matched-fold-at-point-cut — when you encounter a tech-debt item during a mission, fold it if its domain matches the current mission scope (not all debt, not at random); (b) debt-paydown sequencing — resolve critical/blocking debt before non-blocking; (c) campsite metaphor extension to planning contexts (fold foldable issues at planning point-cuts, not just during implementation).
- **C-003**: `owned_files` = 025 only. 024, 040, `frozen-baseline-shrink-only-ratchet.tactic.yaml`, `brownfield-onboarding.paradigm.yaml`, and `planning-and-tracking.styleguide.yaml` are NOT in owned_files. Adding a DRG edge that points to them is fine; editing them is not.
- **No duplicate campsite directive**: do not create a new directive with the campsite/boy-scout theme. Extend 025.
- **PD-2**: inline DRG edges in 025 only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T038 – [C-001] Overlap-audit §2

- **Purpose**: Mandatory overlap-audit for §2. The audit must read 025, 024, 040, and planning-and-tracking.styleguide explicitly and record what atoms are already covered vs. uncovered.
- **Steps**:
  1. Read `src/doctrine/directives/built-in/025-boy-scout-rule.directive.yaml` in full. Record what it already covers.
  2. Read `src/doctrine/directives/built-in/024-locality-of-change.directive.yaml`. Record adjacency.
  3. Read `src/doctrine/directives/built-in/040-recurring-bug-structural-intervention.directive.yaml`. Record adjacency.
  4. Read `src/doctrine/styleguides/built-in/planning-and-tracking.styleguide.yaml`. Note the tracker-hygiene content; confirm this is SOLE-OWNED by WP11 (do NOT edit this file).
  5. Run `grep -r "domain.matched\|fold.*point.cut\|debt.paydown\|ratchet\|frozen.baseline" src/doctrine/ --include="*.yaml" -l` — record hits.
  6. Write augment-vs-create decision:
     - 025 covers the core boy-scout rule (leave code cleaner than you found it) → EXTEND (do not create).
     - 024 covers locality of change → adjacent, cross-link only.
     - 040 covers recurring-bug structural intervention → adjacent, cross-link only.
     - Uncovered atoms: domain-matched-fold-at-point-cut; debt-paydown sequencing in planning context.
     - Tracker-hygiene: RELOCATED to WP11; do NOT touch here.
  7. **Verbatim text requirement (SHOULD-TIGHTEN 6)**: quote the SPECIFIC lines from `025-boy-scout-rule.directive.yaml` that describe what the directive currently covers. Record these lines verbatim in the Activity Log. Then explicitly state why the new "domain-matched-fold-at-point-cut" atom is DISTINCT from those lines — what the existing text covers vs. what the new atom adds (the scope boundary between the existing rule and the new atom). This quote + distinction must appear in the Activity Log before T039 begins; a reviewer will mechanically confirm no duplication by comparing the verbatim 025 text against the new extension.
- **Files**: None (audit only).
- **Parallel?**: No — must be first.

### Subtask T039 – Extend 025 with domain-matched-fold atom + cross-links

- **Purpose**: Add the uncovered atoms to DIRECTIVE_025. Edit 025 only.
- **Steps**:
  1. Open `src/doctrine/directives/built-in/025-boy-scout-rule.directive.yaml`.
  2. Add a new section or extend the existing body with the **domain-matched-fold-at-point-cut atom**: when you encounter a tech-debt item during a mission's planning point-cut (post-spec, post-plan, post-tasks review), fold it into the current mission's scope IF and ONLY IF its domain matches the current mission's primary domain. Items outside the domain boundary are filed as issues and deferred — they are not folded at this point-cut.
  3. Add debt-paydown sequencing note: resolve critical/blocking tech-debt items before non-blocking aesthetic items; priority follows the impact on correctness or velocity, not the ease of fixing.
  4. Add 024 and 040 cross-links in prose ("see also DIRECTIVE_024 for locality-of-change discipline; DIRECTIVE_040 for structural intervention on recurring bugs").
  5. Do NOT rewrite or restructure the existing 025 content — only extend.
- **Files**: `src/doctrine/directives/built-in/025-boy-scout-rule.directive.yaml` (extend existing)
- **Parallel?**: No — T040 depends on this.
- **Notes**: Do NOT touch `planning-and-tracking.styleguide.yaml` here — tracker-hygiene content belongs in WP11.

### Subtask T040 – Wire cross-references via DRG edges and confirm scope boundaries

- **Purpose**: Add inline DRG edges to the extended 025 directive; confirm scope boundary violations are absent.
- **Steps**:
  1. In the extended 025 YAML, add inline DRG edges:
     - `suggests: [urn:directive:DIRECTIVE_024, urn:directive:DIRECTIVE_040]` (the adjacent directives).
     - `suggests: [urn:tactic:frozen-baseline-shrink-only-ratchet]` (from WP02 — forward reference or already landed).
     - `suggests: [urn:paradigm:brownfield-onboarding]` (from WP08 — forward reference or already landed).
  2. Confirm the tracker-hygiene bullet is NOT added to 025 here (it belongs in `planning-and-tracking.styleguide.yaml` under WP11).
  3. Confirm `planning-and-tracking.styleguide.yaml` has NOT been modified.
  4. Confirm `brownfield-onboarding.paradigm.yaml` has NOT been modified (owned by WP08).
  5. Confirm `frozen-baseline-shrink-only-ratchet.tactic.yaml` has NOT been modified (owned by WP02).
- **Files**: `src/doctrine/directives/built-in/025-boy-scout-rule.directive.yaml` (DRG edge edits)
- **Parallel?**: No.
- **Notes**: Forward references to artifacts from other WPs (ratchet tactic, brownfield paradigm) are valid in inline edges. They will be validated at WP12's graph regen.

### Subtask T041 – Verify inline DRG edges

- **Purpose**: Final check that all DRG edges are present and `graph.yaml` is unchanged.
- **Steps**:
  1. Open 025 YAML; confirm all four `suggests` edges are present.
  2. Confirm `graph.yaml` has NOT been modified (PD-2).
  3. Record in Activity Log.
- **Files**: No files changed.
- **Parallel?**: No.

### Subtask T042 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate the extended directive YAML.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the extended `025-boy-scout-rule.directive.yaml`. Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. Confirm no new duplicate campsite directive was created.
  5. Confirm `planning-and-tracking.styleguide.yaml` unchanged (SOLE-OWNED by WP11).
  6. Confirm `graph.yaml` UNCHANGED; agent-profile wiring DEFERRED to WP12.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after T039.
- `pytest tests/architectural/test_no_legacy_terminology.py -q`.
- `git diff --stat HEAD` — confirm only `025-boy-scout-rule.directive.yaml` is modified.

## Risks & Mitigations

- **Accidental planning-and-tracking.styleguide.yaml edit**: the single highest risk. The tracker-hygiene content is tempting to add here because it feels like §2; it belongs in WP11. Running `git diff --stat` after T039 is the verification.
- **Duplicate directive**: Do NOT create a new directive for §2. Extend 025.

## Review Guidance

- T038 audit explicitly reads and verdicts all four artifacts (025, 024, 040, planning-and-tracking.styleguide). Activity Log contains verbatim DIRECTIVE_025 lines (the existing content) and an explicit statement of why the new "domain-matched-fold-at-point-cut" atom is distinct — the reviewer uses this to mechanically confirm no duplication.
- Domain-matched-fold atom added to 025 body; 024/040 cross-links in prose.
- DRG edges: `suggests` to 024, 040, ratchet tactic, brownfield paradigm.
- `planning-and-tracking.styleguide.yaml` UNCHANGED.
- No new campsite directive created.
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED; agent-profile wiring deferred to WP12.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:25:21Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1858719 – Assigned agent via action command
- 2026-07-01T10:33:52Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1858719 – Ready for review: DIRECTIVE_025 extended with domain-matched-fold-at-point-cut atom, debt-paydown sequencing, 024/040 cross-links, and 4 DRG references (DIRECTIVE_024, DIRECTIVE_040, frozen-baseline-shrink-only-ratchet, brownfield-onboarding). Overlap audit recorded. All gates green: doctor 0/0, DRG test +terminology test pass. Only 025 changed (27 insertions). graph.yaml unchanged, profile wiring deferred to WP12.
- 2026-07-01T10:34:35Z – claude:opus:reviewer-renata:reviewer – shell_pid=1903079 – Started review via action command
- 2026-07-01T10:41:12Z – user – shell_pid=1903079 – Moved to planned
- 2026-07-01T10:46:34Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1943573 – Started implementation via action command
- 2026-07-01T10:49:28Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1943573 – Cycle 1: verbatim 025 overlap-audit recorded per review
- 2026-07-01T11:10:00Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1943573 – **T038 OVERLAP-AUDIT (verbatim record — cycle-1 remediation per reviewer-renata)**

  **Verbatim pre-existing DIRECTIVE_025 lines that delimit what 025 already covers:**

  `scope` field: "Applies to the files and modules already modified for the current task, and to the failing tests, lint findings, and type errors surfaced within them. It does not license broad refactors or edits outside the touched area."

  `procedures[0]` field: "When a touched area has a failing test, lint finding, or type error, fix it by default rather than deferring it or attributing it to pre-existing state."

  **Why the new domain-matched-fold-at-point-cut atom is DISTINCT from those lines:**
  The verbatim scope above is reactive and implementation-time: it triggers only when a failure is already surfaced within files the current task has already touched, and it explicitly prohibits edits outside the touched area. The new atom operates in a different temporal phase (planning point-cut: post-spec, post-plan, or post-tasks) and uses a different trigger (domain-boundary match against the current mission's primary domain, not already-touched-file membership). It may deliberately pull in items outside the currently-touched surface when the domain overlaps — the opposite of the touched-area constraint the verbatim scope imposes. These are non-overlapping: existing 025 = reactive, implementation-time, files-already-modified gate; new atom = proactive, planning-phase, domain-match gate. Zero text duplication; genuinely new atom.

  **024/040 adjacency note:**
  DIRECTIVE_024 (Locality of Change) constrains the blast radius of new work during implementation — it does not address planning-phase campsite folding or domain-match triage. DIRECTIVE_040 (Recurring Bug Structural Intervention) covers structural fixes for recurring failures — it does not address planning-point-cut domain-matched debt triage. Neither directive covers the planning-phase, domain-gated folding behavior introduced by the new atom. Both are cross-linked FROM 025 via `references`; neither was edited (C-003).

  **Augment-vs-create verdict:** EXTEND DIRECTIVE_025 — do not create a new directive. The core boy-scout intent (leave touched areas cleaner by default) is already housed in 025. The uncovered atoms (domain-matched-fold-at-point-cut; debt-paydown sequencing at planning point-cuts) are natural extensions of the same campsite principle applied earlier in the mission lifecycle. Authoring a new directive would produce an orphaned artifact with the same intent and title, creating a duplicate authority problem (C-001). Decision: EXTEND 025.
- 2026-07-01T10:53:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=1957373 – Started review via action command
- 2026-07-01T10:57:32Z – user – shell_pid=1957373 – Cycle 1: verbatim T038 audit recorded; 025 extension unchanged and correct
