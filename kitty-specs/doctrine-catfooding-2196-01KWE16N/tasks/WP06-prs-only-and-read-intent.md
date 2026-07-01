---
work_package_id: WP06
title: '§7 Git/Workflow: PRs-Only + Read-Intent'
dependencies:
- WP01
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
phase: Phase 1 - New-Artifact Conversions (LA)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2060235"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/directives/built-in/
create_intent:
- src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – §7 Git/Workflow: PRs-Only + Read-Intent

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

Author one new directive for the first half of §7 of the Quality & Tech-Debt Standing Orders:

**DIRECTIVE_045** — `prs-only-and-read-intent`: two rules:
1. All changes to origin/main must go through pull requests; the operator always merges PRs to origin/main manually (never `git push origin main`; never `gh pr merge` without operator instruction).
2. Before executing high-risk operations (merge, rebase, deletion of branches/files, force operations), read the mission spec and intent first. Never execute blindly from a task title alone.

Directive number 045 is pre-allocated per PD-1.

§7 has four uncovered rules in total. This WP covers two; WP07 covers the other two (worktree isolation + no-version-prescription-in-scope).

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T025 output) — must include git-flow.paradigm + 029 + 033 check
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for new artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges authored in the directive YAML
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §7 of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **C-001 overlap-audit scope (mandatory for §7)**: the audit must explicitly check `paradigms/built-in/git-flow.paradigm.yaml` AND directives 029 (`agent-commit-signing`) AND 033 (`targeted-staging`) in addition to searching broadly. These are the named adjacent git artifacts from `research.md` D-7 and FR-012.
- **Coverage map**: `029-agent-commit-signing` covers commit signing; `033-targeted-staging` covers staged hunks; `clean-linear-commit-history.tactic` covers history compression. None of these cover PRs-only/operator-merge or read-intent-before-high-risk-ops → these rules are genuinely new.
- **C-004**: §7's rules involve git workflow idioms. Do NOT use `"feature branch"` in canonical voice — if the directive needs to describe a PR branch (non-main branch), use the term "PR branch" or "mission branch." If `"feature branch"` must appear as an example of prohibited naming, quote it.
- **PD-1**: 045 is pre-allocated. Do not mint other numbers here.
- **PD-2**: inline DRG edges only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T025 – [C-001] Overlap-audit §7 (PRs-only + read-intent leg)

- **Purpose**: Mandatory overlap-audit for §7. The audit scope is wider than usual for §7 — must check the named adjacent git artifacts.
- **Steps**:
  1. Read `src/doctrine/directives/built-in/029-agent-commit-signing.directive.yaml` — does it cover PRs-only or read-intent? Record findings.
  2. Read `src/doctrine/directives/built-in/033-targeted-staging.directive.yaml` — same check.
  3. Read `src/doctrine/paradigms/built-in/git-flow.paradigm.yaml` — does it encode PRs-only/operator-merge or read-intent-before-high-risk-ops? Record findings.
  4. Run `grep -r "pr.only\|operator.merge\|read.intent\|high.risk" src/doctrine/ --include="*.yaml" -l` — record zero or partial hits.
  5. Write augment-vs-create decision: PRs-only/operator-merge and read-intent-before-high-risk-ops are uncovered by 029, 033, and git-flow.paradigm → create DIRECTIVE_045. Compress-history is already covered by `clean-linear-commit-history.tactic` → NOT authored here (WP07 references it).
- **Files**: None (audit only — record decisions in Activity Log).
- **Parallel?**: No — must be first.
- **Notes**: The audit must name each artifact checked and record its verdict. A reviewer will confirm this was done honestly.

### Subtask T026 – Author DIRECTIVE_045

- **Purpose**: Encode the two PRs-only and read-intent rules as a required directive.
- **Steps**:
  1. Create `src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml`.
  2. `id: DIRECTIVE_045`, `enforcement: required`, `title: "PRs-Only and Read-Intent Before High-Risk Operations"`.
  3. Body must state both rules:
     - **Rule 1 — PRs-only/operator-merge**: all changes to `origin/main` go through pull requests. Agents must never run `git push origin main` or `gh pr merge` without explicit operator instruction. The operator always merges to origin/main manually. `spec-kitty merge` merges to local main only — it does NOT push to origin/main. After `spec-kitty merge`, create a PR branch (`git checkout -b pr/<slug>`) and open a PR; do not push directly.
     - **Rule 2 — read-intent-before-high-risk-ops**: before executing any high-risk git operation (merge, rebase, deletion of branches or files, force operations), read the mission spec and current context first. Never execute from a task title or a quick description alone. If the intent is unclear, escalate rather than proceed.
  4. Add inline DRG edges: `suggests: [urn:tactic:pr-agent-worktree-isolation]` (from WP07 — forward reference; valid for inline edges).
- **Files**: `src/doctrine/directives/built-in/045-prs-only-and-read-intent.directive.yaml` (create new)
- **Parallel?**: No — T027 depends on this.
- **Notes**: Do NOT use `"feature branch"` in canonical voice (C-004). The directive must not re-author the history-compression rule (that is in `clean-linear-commit-history.tactic`).

### Subtask T027 – Verify inline DRG edges

- **Purpose**: Confirm the directive's inline edges are authored and `graph.yaml` is not touched.
- **Steps**:
  1. Open the directive file and confirm `suggests` edge to `urn:tactic:pr-agent-worktree-isolation` is present.
  2. Confirm `graph.yaml` has NOT been modified (PD-2).
  3. Record in Activity Log.
- **Files**: No files changed — verification only.
- **Parallel?**: No.

### Subtask T028 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate the new directive YAML.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the newly authored directive (`045-prs-only-and-read-intent`). Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. Confirm T025 audit record names 029, 033, and git-flow.paradigm explicitly.
  5. Confirm `graph.yaml` UNCHANGED; agent-profile wiring DEFERRED to WP12.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after T026.
- `pytest tests/architectural/test_no_legacy_terminology.py -q` — watch for `"feature branch"` in canonical voice (C-004).
- After T025, open the Activity Log and verify that 029, 033, and `git-flow.paradigm.yaml` are each named with an explicit per-artifact verdict — a reviewer will look for this.
- After T026, read the directive body and check: does it cover the PRs-only rule AND the read-intent rule? Both must be present.

## Risks & Mitigations

- **Terminology (C-004)**: §7 git workflow rules are the most likely section to accidentally use `"feature branch"` in canonical voice. The directive must use "PR branch" or "mission branch" for non-main branches. If `"feature branch"` must appear as a named anti-pattern, quote it: `"feature branch"` (in quotes or a code block).
- **Audit scope (§7-specific)**: The §7 overlap-audit scope is wider than other sections because §7 has more adjacent git artifacts. Forgetting to check `git-flow.paradigm.yaml` is a known gap that the research squad flagged (research.md D-7). The T025 audit must read it.
- **Directive covers two rules — confirm both are present**: Rule 1 (PRs-only/operator-merge) and Rule 2 (read-intent-before-high-risk-ops) must both appear in the directive body. A directive that only covers one rule is incomplete.
- **Scope boundary with WP07**: WP06 covers PRs-only + read-intent; WP07 covers worktree-isolation + no-version. Do not let the rule sets bleed across WPs. If you find yourself writing about worktree isolation or version prescription in WP06, move that content to WP07.

## Dependency Notes

- WP06 enables WP07 (WP07's tactic has a DRG edge that `requires` DIRECTIVE_045 authored here).
- WP06 is parallelizable with WP02, WP04, WP05, WP07, WP08, WP10, WP11 (disjoint surfaces).

## Review Guidance

- T025 audit explicitly names 029, 033, and git-flow.paradigm with per-artifact verdicts — three named verdicts required.
- Directive 045 has BOTH rules (PRs-only/operator-merge AND read-intent-before-high-risk-ops); a directive with only one rule is incomplete.
- `enforcement: required` is set (both rules are requirements, not guidance).
- No `"feature branch"` in canonical voice (check the entire body).
- `suggests: [urn:tactic:pr-agent-worktree-isolation]` DRG edge present (forward reference to WP07).
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED; agent-profile wiring deferred to WP12.
- Directive number is 045 per PD-1 pre-allocation.

## Parallel Opportunities

WP06 is parallelizable with WP02, WP04, WP05, WP07, WP08, WP09, WP10, WP11 (all own disjoint surfaces). WP07's tactic has a forward-reference DRG edge to DIRECTIVE_045 (authored here) — WP06 and WP07 can proceed in parallel; WP12 validates the edge at regen time.

## Updating Status

Use `spec-kitty agent tasks move-task WP06 --to claimed` when starting. Record in Activity Log before `for_review`:
1. T025 audit: per-artifact verdicts for 029, 033, and git-flow.paradigm (all three must be named).
2. Directive 045 number confirmed (PD-1 pre-allocation).
3. Both rules (PRs-only AND read-intent) authored in the directive body.
4. Doctor doctrine + terminology guard results (must be green).
5. Confirmation that `graph.yaml` was NOT regenerated and profile wiring is deferred to WP12.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:05:54Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Assigned agent via action command
- 2026-07-01T10:18:13Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Ready for review: DIRECTIVE_045 authored with both PRs-only/operator-merge (Rule 1) and read-intent-before-high-risk-ops (Rule 2) rules. T025 overlap-audit names 029/033/git-flow.paradigm explicitly - all three with per-artifact verdicts (no overlap). Directive number 045 per PD-1 pre-allocation. suggests edge to urn:tactic:pr-agent-worktree-isolation present. graph.yaml unchanged. doctor/terminology/test_shipped_graph_valid all green.
- 2026-07-01T10:18:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=1813803 – Started review via action command
- 2026-07-01T10:22:43Z – user – shell_pid=1813803 – Review passed (reviewer-renata). DIRECTIVE_045 covers BOTH Rule 1 (PRs-only/operator-merge, incl. spec-kitty-merge=local-only + PR-branch + revert-recovery) and Rule 2 (read-intent-before-high-risk-ops incl. escalation + never-delete-test). C-004: sole 'feature branch' occurrence is quoted/marked as a colloquial git idiom in canonical guidance (line 47). suggests: urn:tactic:pr-agent-worktree-isolation forward-ref present (dangles until WP12, expected). graph.yaml UNCHANGED (PD-2); WP06 own commit touches only 045-*.directive.yaml. Overlap-audit (T025) recorded in Activity Log with per-artifact verdicts for 029/033/git-flow.paradigm — independently confirmed non-overlapping (029=commit-signing, 033=targeted-staging, git-flow=branching compat paradigm); history-compression correctly EXCLUDED (owned by clean-linear-commit-history.tactic), no WP07 scope bleed. Gates green: doctor doctrine (18/18 valid, 0 invalid/skipped), test_shipped_graph_valid (2 passed), test_no_legacy_terminology (3 passed).
- 2026-07-01T11:24:48Z – user – shell_pid=1813803 – Moved to planned
- 2026-07-01T11:25:02Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=2043640 – Started implementation via action command
- 2026-07-01T11:28:25Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=2043640 – Cycle 1: 045 now valid YAML (was bare-backtick scalar); regenerate-graph --check no longer crashes
- 2026-07-01T11:28:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=2060235 – Started review via action command
- 2026-07-01T11:31:03Z – user – shell_pid=2060235 – Cycle 1: 045 now valid YAML; regenerate-graph --check clean; meaning unchanged
