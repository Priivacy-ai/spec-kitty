---
work_package_id: WP07
title: '§7 Git/Workflow: Worktree Isolation + No-Version'
dependencies:
- WP01
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
phase: Phase 1 - New-Artifact Conversions (LA)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1895890"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/tactics/built-in/
create_intent:
- src/doctrine/tactics/built-in/pr-agent-worktree-isolation.tactic.yaml
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/tactics/built-in/pr-agent-worktree-isolation.tactic.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – §7 Git/Workflow: Worktree Isolation + No-Version

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

Author one new tactic for the second half of §7 of the Quality & Tech-Debt Standing Orders:

**Tactic** — `pr-agent-worktree-isolation`: two rules combined into one tactic (they are cohesive "PR agent discipline"):
1. Review/rebase agents that touch a PR must use `isolation: worktree` — non-isolated agents operating on a PR stage the PR diff into the active mission checkout (a cross-contamination defect).
2. Do not prescribe patch/version numbers in mission scope — versions are superimposed at release time by the operator.

The tactic also **references** `clean-linear-commit-history.tactic` for history compression — do NOT re-author that rule here.

§7 has four uncovered rules total. WP06 authored DIRECTIVE_045 (PRs-only + read-intent). WP07 authors this tactic for the remaining two rules.

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T029 output) — must include `clean-linear-commit-history.tactic`, git-flow.paradigm, 029, 033
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for new artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges authored in the tactic YAML
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §7 of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **C-001 overlap-audit scope**: this WP's audit must check `clean-linear-commit-history.tactic` (covers history compression), `git-flow.paradigm.yaml` (may cover worktree isolation?), `029-agent-commit-signing`, and `033-targeted-staging`. These are the four adjacent git artifacts named in research.md D-7 and FR-012.
- **History compression — REFERENCE ONLY**: the rule "compress branch history after mission lands" already lives in `clean-linear-commit-history.tactic`. This tactic must REFERENCE it (via a DRG edge and/or a prose cross-reference) but must NOT re-author the rule. Re-authoring would create a split-brain authority.
- **Worktree isolation rationale**: the concrete defect to name is: a non-isolated review/rebase agent stages the PR diff into the active mission checkout, causing cross-contamination. Real incident: PR #2151 leaked into #2119 respec. The tactic should name this defect class.
- **No-version-in-scope rationale**: assigning patch numbers in mission scope pre-empts the PO's release decision. The correct framing in scope documents is "focus area / milestone / follow-on," not "v0.X.Y."
- **C-004**: no `"feature branch"` in canonical voice.
- **PD-2**: inline DRG edges only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T029 – [C-001] Overlap-audit §7 (worktree-isolation + no-version leg)

- **Purpose**: Mandatory overlap-audit for this leg of §7. The audit scope is the four named adjacent git artifacts.
- **Steps**:
  1. Read `src/doctrine/tactics/built-in/clean-linear-commit-history.tactic.yaml` — confirm it covers history compression; record that compress-history is COVERED here (reference only, do not re-author).
  2. Read `src/doctrine/paradigms/built-in/git-flow.paradigm.yaml` — does it cover worktree isolation for PR-touching agents? Record findings.
  3. Read `src/doctrine/directives/built-in/029-agent-commit-signing.directive.yaml` — any worktree/no-version coverage? Record.
  4. Read `src/doctrine/directives/built-in/033-targeted-staging.directive.yaml` — any worktree/no-version coverage? Record.
  5. Run `grep -r "worktree.isolation\|isolat.*pr\|no.version\|version.*scope" src/doctrine/ --include="*.yaml" -l`.
  6. Write decision: worktree-isolation and no-version-in-scope are uncovered → create new tactic. History compression is covered by `clean-linear-commit-history.tactic` → reference only.
- **Files**: None (audit only — record in Activity Log).
- **Parallel?**: No — must be first.
- **Notes**: The audit must name each of the four artifacts checked with per-artifact verdicts.

### Subtask T030 – Author pr-agent-worktree-isolation tactic

- **Purpose**: Encode both the worktree-isolation rule and the no-version-prescription-in-scope rule in one cohesive "PR agent discipline" tactic. Cross-reference `clean-linear-commit-history.tactic` for history compression.
- **Steps**:
  1. Create `src/doctrine/tactics/built-in/pr-agent-worktree-isolation.tactic.yaml`.
  2. `id: pr-agent-worktree-isolation`, `title: "PR Agent Worktree Isolation and No-Version Prescription"`.
  3. Body (two rules, one tactic):
     - **Rule 1 — PR-touching agent isolation**: any review or rebase agent that touches a PR must use `isolation: worktree` (i.e. the `Agent(isolation: "worktree")` parameter in the agent harness). A non-isolated agent operating on a PR stages the PR diff into the active mission checkout, causing cross-contamination of branches. The canonical failure mode: a non-isolated review agent leaks a PR's changes into an unrelated mission's worktree.
     - **Rule 2 — No version prescription in scope**: do not assign patch/minor/major version numbers in mission scope documents. Versions are superimposed at release time by the product owner. In scope documents, frame work as "focus area," "milestone," or "follow-on" rather than "v0.X.Y." The PO's version decision is not within scope authoring authority.
     - **Cross-reference**: history compression after mission landing is governed by `clean-linear-commit-history.tactic`. Follow that tactic for commit-squash and rebase-onto-upstream; do not repeat its rules here.
  4. Add inline DRG edges:
     - `requires: [urn:directive:DIRECTIVE_045]` (this tactic operationalizes §7 rules from WP06's directive).
     - `refines: [urn:tactic:clean-linear-commit-history]` (this tactic is a sibling discipline; refines clarifies scope boundary).
- **Files**: `src/doctrine/tactics/built-in/pr-agent-worktree-isolation.tactic.yaml` (create new)
- **Parallel?**: No — T031 depends on this.
- **Notes**: Both rules belong in one tactic because they are cohesive "PR agent discipline" — splitting them further would produce micro-tactics with no standalone value. The `refines` edge to `clean-linear-commit-history` signals the scope split without creating a second authority.

### Subtask T031 – Verify inline DRG edges

- **Purpose**: Confirm the tactic's DRG edges are authored and `graph.yaml` is unchanged.
- **Steps**:
  1. Open the tactic file; confirm `requires: DIRECTIVE_045` and `refines: clean-linear-commit-history` edges are present.
  2. Confirm `graph.yaml` has NOT been touched (PD-2).
  3. Record in Activity Log.
- **Files**: No files changed — verification only.
- **Parallel?**: No.

### Subtask T032 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate the new tactic YAML.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the newly authored tactic (`pr-agent-worktree-isolation`). Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. Confirm T029 audit names all four adjacent artifacts with explicit verdicts.
  5. Confirm `graph.yaml` UNCHANGED; agent-profile wiring DEFERRED to WP12.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after T030.
- `pytest tests/architectural/test_no_legacy_terminology.py -q`.
- After T029, verify the Activity Log names all four adjacent artifacts (`clean-linear-commit-history.tactic`, `git-flow.paradigm.yaml`, `029`, `033`) with per-artifact verdicts.
- After T030, read the tactic body and confirm: (a) worktree-isolation rule describes the cross-contamination defect class; (b) no-version-in-scope rule describes the PO's authority boundary; (c) compress-history is cross-referenced, not restated.
- Confirm `requires: DIRECTIVE_045` edge points to WP06's directive.

## Risks & Mitigations

- **Re-authoring history compression**: the strongest risk is accidentally restating the `clean-linear-commit-history.tactic` content (commit-squash, rebase-onto-upstream) in this tactic. The tactic body must cross-reference the existing tactic with a DRG `refines` edge and a prose sentence; it must NOT copy or paraphrase the history compression steps.
- **Terminology (C-004)**: §7 git rules risk `"feature branch"` in canonical voice (describing PR branches). Use "PR branch," "mission branch," or "lane branch" instead.
- **Tactic coherence**: both rules (worktree-isolation + no-version) are genuine "PR agent discipline" — they belong together because they constrain how agents behave around PRs. If they feel heterogeneous, it is because they share the constraint that "agents should not over-reach PR scope"; keep them in one tactic rather than splitting into micro-tactics.
- **DRG edge forward reference**: `requires: DIRECTIVE_045` references WP06's directive. If WP06 has not landed, use the forward URN (`urn:directive:DIRECTIVE_045`). The DRG generator validates at WP12's regen time.

## Dependency Notes

- WP07 is parallelizable with WP06 (disjoint surfaces: WP06 owns the directive, WP07 owns the tactic). However, WP07's `requires: DIRECTIVE_045` edge is a forward reference until WP06 lands.
- WP07 enables WP12 (the tactic is a new DRG node that must be included in the single regen).

## Review Guidance

- T029 audit explicitly names and verdicts all four adjacent artifacts: `clean-linear-commit-history.tactic` (covered — reference only), `git-flow.paradigm.yaml`, `029`, `033`.
- Tactic body has BOTH rules: (1) PR-touching agent worktree isolation with the cross-contamination defect class named; (2) no-version-prescription-in-scope with the PO's authority boundary stated.
- Compress-history is cross-referenced (not restated) — the body says "see `clean-linear-commit-history.tactic`" and has a DRG `refines` edge.
- The cross-contamination failure example (a non-isolated agent leaking a PR diff into a mission checkout) is named concretely.
- `requires: DIRECTIVE_045` and `refines: clean-linear-commit-history` DRG edges present.
- No `"feature branch"` in canonical voice.
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED; agent-profile wiring deferred to WP12.

## Parallel Opportunities

WP07 is fully parallelizable with WP06 (owns the tactic; WP06 owns the directive). The `requires: DIRECTIVE_045` forward reference resolves at WP12's regen. WP07 is also parallel with WP04, WP05, WP08, WP09, WP10, WP11.

## Updating Status

Use `spec-kitty agent tasks move-task WP07 --to claimed` when starting. Record in Activity Log before `for_review`:
1. T029 audit: all four adjacent artifacts named with verdicts; compress-history confirmed covered.
2. Tactic body summary: both rules authored, cross-contamination example named, compress-history cross-referenced.
3. `requires: DIRECTIVE_045` and `refines: clean-linear-commit-history` edges confirmed present.
4. Doctor doctrine + terminology guard results (must be green).
5. Confirmation that `graph.yaml` was NOT regenerated and profile wiring is deferred to WP12.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:06:02Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Assigned agent via action command
- 2026-07-01T10:20:11Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Moved to for_review
- 2026-07-01T10:20:49Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – T029 audit: clean-linear-commit-history.tactic COVERED (compress-history → reference only, no re-author); git-flow.paradigm NO worktree-isolation or no-version coverage; DIRECTIVE_029 NO coverage (commit signing only); DIRECTIVE_033 NO coverage (targeted staging only). Grep: zero prior coverage of worktree-isolation/no-version-in-scope rules in src/doctrine/. Decision: create new tactic. T030: authored pr-agent-worktree-isolation.tactic.yaml — Rule 1 worktree isolation with cross-contamination defect class named (PR #2151→#2119); Rule 2 no version prescription with PO authority boundary stated; compress-history cross-referenced via DRG edge + prose (not restated). T031: DRG edges confirmed in YAML — DIRECTIVE_045 (requires, forward-ref WP06) and clean-linear-commit-history (refines, sibling scope boundary); graph.yaml NOT touched (PD-2). T032: doctor 0/0 OK; test_shipped_graph_valid 2 passed; test_no_legacy_terminology 3 passed; test_tactic_schema_valid green. test_references_resolve expected forward-ref fail on DIRECTIVE_045 (deferred to WP12). Commit: 0bddcee0e. Status: for_review.
- 2026-07-01T10:21:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=1843453 – Started review via action command
- 2026-07-01T10:28:05Z – user – shell_pid=1843453 – Moved to planned
- 2026-07-01T10:28:42Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1877122 – Started implementation via action command
- 2026-07-01T10:32:53Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1877122 – Cycle 1: removed redundant step-2 reference; root-vs-step compliance now passes
- 2026-07-01T10:33:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=1895890 – Started review via action command
- 2026-07-01T10:37:08Z – user – shell_pid=1895890 – Cycle 1: root-vs-step compliance fixed; only expected DIRECTIVE_045 forward-ref remains
