---
work_package_id: WP03
title: §5b Post-Merge Arch-Gate Adjudication
dependencies:
- WP01
- WP02
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 1 - New-Artifact Conversions (LA)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1888674"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/procedures/built-in/
create_intent:
- src/doctrine/procedures/built-in/post-merge-arch-gate-adjudication.procedure.yaml
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/procedures/built-in/post-merge-arch-gate-adjudication.procedure.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – §5b Post-Merge Arch-Gate Adjudication

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

Author one new doctrine procedure for §5b of the Quality & Tech-Debt Standing Orders:

**Procedure** — `post-merge-arch-gate-adjudication`: a procedure that operationalizes the §5b lesson that architectural gate failures found *after* a merge are often attributable to pre-existing conditions, not the landing diff — and gives concrete steps to diagnose which is which.

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T011 output)
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for new artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges authored in the procedure YAML
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §5b of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **Depends on WP02**: the procedure references DIRECTIVE_043 (from WP02). Author the `requires` DRG edge pointing to `urn:directive:DIRECTIVE_043`.
- **No existing coverage**: §5b (post-merge adjudication) has no existing procedure in `src/doctrine/procedures/built-in/`.
- **Key distinction the procedure must encode**: "pre-existing" means the failure already existed on the *mission base branch* (the branch the lanes merged from), not the lane base. A cross-base diff proves it.
- **CI-only shards**: some arch tests run only in CI (e.g. `integration-tests-core-misc`) and not in the `fast-tests-*` suites. The procedure must explicitly name running CI-only shards locally as a required step before concluding a failure is a regression.
- **PD-2 (graph.yaml)**: author inline DRG edges in the YAML only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T011 – [C-001] Overlap-audit §5b

- **Purpose**: Mandatory pre-authoring overlap-audit (C-001 / DIRECTIVE_003). Confirm no post-merge adjudication procedure exists.
- **Steps**:
  1. Run `grep -r "post.merge\|adjudication\|arch.gate.*fail" src/doctrine/ --include="*.yaml" -l` — record findings.
  2. Check `src/doctrine/procedures/built-in/` for any procedure that covers "after merge, check arch gates, diagnose pre-existing vs. regression" — record zero or partial coverage.
  3. Write augment-vs-create decision in Activity Log: §5b has no existing procedure; create new.
- **Files**: None (audit only).
- **Parallel?**: No — must be first.
- **Notes**: The audit must be explicit even if you are confident the result is "no coverage."

### Subtask T012 – Author post-merge-arch-gate-adjudication procedure

- **Purpose**: Create the procedure that tells contributors how to handle architectural gate failures found after merging lane branches.
- **Steps**:
  1. Create `src/doctrine/procedures/built-in/post-merge-arch-gate-adjudication.procedure.yaml`.
  2. Follow the procedure YAML schema (id, title, body, requires/suggests/refines). See existing procedures in `src/doctrine/procedures/built-in/` for format.
  3. Body must cover the following ordered steps:
     - **Step 1 — Full-gate sweep on the merged branch**: run the full `tests/architectural/` suite (not just the failing shard) on the merged coordination/main branch after all lanes are in.
     - **Step 2 — Cross-base pre-existing check**: diff the merged branch against the *mission base branch* (the branch from which lane worktrees were created, not the lane's own base). If the failing test also fails on the mission base, the failure is pre-existing, not a regression from this merge.
     - **Step 3 — Run CI-only shards locally**: `tests/integration/`, `tests/git/`, and the CI-only `integration-tests-core-misc` shard must be run locally before concluding a failure is a regression. A failure that only appears in CI but not locally against the fast-tests suite is usually a CI-only shard.
     - **Step 4 — Adjudicate**: if pre-existing → file a tracking issue and mark it as baseline before treating it as a blocker; if regression → fix before merging further.
  4. Keep the body ordered and numbered so contributors follow it step by step.
- **Files**: `src/doctrine/procedures/built-in/post-merge-arch-gate-adjudication.procedure.yaml` (create new)
- **Parallel?**: No — T013 depends on this.
- **Notes**: The key distinction is "mission base branch" vs. "lane base branch." The procedure must make this explicit because in coord topology, lane bases are often intermediate commits, not the true mission origin.

### Subtask T013 – Author inline DRG edges

- **Purpose**: Wire the procedure into the DRG by adding inline `requires` and `suggests` edges in the YAML.
- **Steps**:
  1. Add `requires: [urn:directive:DIRECTIVE_043]` to the procedure YAML (this procedure operationalizes the close-by-construction directive's gates).
  2. Add `suggests: [urn:tactic:architectural-gate-non-vacuity]` if the relationship is suggestive but not mandatory.
  3. Confirm `graph.yaml` has NOT been touched (PD-2).
- **Files**: `src/doctrine/procedures/built-in/post-merge-arch-gate-adjudication.procedure.yaml` (inline edge edits only)
- **Parallel?**: No — must run after T012.
- **Notes**: `urn:directive:DIRECTIVE_043` — verify this matches the `id` field set in T006.

### Subtask T014 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates (per `contracts/conversion-dod.md`).
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate the new procedure YAML.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the newly authored procedure (`post-merge-arch-gate-adjudication`). Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. Confirm inline DRG edges present in the procedure YAML.
  5. Confirm `graph.yaml` UNCHANGED (regen deferred to WP12).
  6. Confirm agent-profile wiring DEFERRED to WP12.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after T012 to catch schema issues early.
- `pytest tests/architectural/test_no_legacy_terminology.py -q` before `for_review`.
- Read the procedure body after authoring and mentally simulate a contributor following it: would Step 2's cross-base diff correctly identify a pre-existing failure vs. a regression? If ambiguous, tighten the body.
- Confirm the procedure references `DIRECTIVE_043` via the `requires` edge in T013 by opening the YAML and checking the field.

## Risks & Mitigations

- **"Pre-existing" ambiguity**: The procedure must define "mission base branch" precisely — the branch from which all lane worktrees were created (the `target_branch` in `meta.json`), not the intermediate lane base. If left vague, contributors compare against the wrong baseline and incorrectly classify regressions as pre-existing.
- **CI-only shards**: If the procedure omits naming CI-only shards explicitly, contributors will conclude CI failures are flakes rather than real regressions. Name `tests/integration/`, `tests/git/`, and the `integration-tests-core-misc` shard explicitly in the procedure body.
- **DRG edge forward reference**: the `requires: DIRECTIVE_043` edge references an artifact authored by WP02. If WP02 has not landed when WP03 is running, use the forward URN (`urn:directive:DIRECTIVE_043`) — the DRG generator validates it at WP12's regen time, not at inline-edge authoring time.

## Dependency Notes

- WP03 must run after WP02 is `approved` (the procedure's DRG edge requires WP02's directive to resolve).
- WP03 enables WP12 (the procedure is a new DRG node that must be included in the single regen).

## Review Guidance

- T011 overlap-audit record present in Activity Log with explicit "no existing coverage" verdict.
- Procedure body has four numbered steps in the correct order: full sweep → cross-base diff → run CI-only shards locally → adjudicate.
- "Pre-existing" is explicitly defined as "present on the mission base branch" (not the lane base). The procedure must state this distinction.
- CI-only shards named: `tests/integration/`, `tests/git/`, `integration-tests-core-misc` job.
- `requires: DIRECTIVE_043` DRG edge present in the procedure YAML.
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED (regen deferred to WP12 per PD-2).
- Agent-profile wiring deferred to WP12 (noted in Activity Log).

## Parallel Opportunities

WP03 runs after WP02 is `approved` (DRG dependency: this procedure's inline `requires` edge points to DIRECTIVE_043). Within this WP, T011 → T012 → T013 → T014 are sequential (no parallelism within this WP). WP03 is safe to run in parallel with WP04, WP05, WP06, WP07, WP08, WP09, WP10, WP11 once WP02 has cleared.

## Updating Status

Use `spec-kitty agent tasks move-task WP03 --to claimed` when starting. Record in Activity Log before `for_review`:
1. T011 audit record: artifacts checked (list them) + "no existing §5b procedure" verdict.
2. Procedure summary: four numbered steps authored; "mission base branch" distinction explicitly stated in procedure body.
3. CI-only shards named in procedure body (`tests/integration/`, `tests/git/`, `integration-tests-core-misc`).
4. Doctor doctrine check result (green/red; include the summary line from the JSON output).
5. Terminology guard result (green/red).
6. `requires: DIRECTIVE_043` edge confirmed present in the YAML.
7. Confirmation that `graph.yaml` was NOT regenerated and profile wiring is deferred to WP12.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).
> Do not pre-fill future entries. Append when you actually complete a step.
> Format: `YYYY-MM-DDTHH:MM:SSZ – <actor> – <description of action taken>`

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:25:10Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1858719 – Assigned agent via action command
- 2026-07-01T10:26:14Z – user – shell_pid=1858719 – Moved to claimed
- 2026-07-01T10:30:32Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1858719 – Ready for review: §5b post-merge-arch-gate-adjudication procedure authored. 4-step ordered body (full sweep → cross-base pre-existing check → CI-only shards locally → adjudicate). Mission base vs lane base distinction explicit. DIRECTIVE_043 and architectural-gate-non-vacuity refs inline. doctor doctrine: 0 skipped/0 invalid. test_shipped_graph_valid: 2 passed. terminology guard: 3 passed. graph.yaml unchanged, profile wiring deferred to WP12.
- 2026-07-01T10:31:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=1888674 – Started review via action command
- 2026-07-01T10:36:34Z – user – shell_pid=1888674 – Review passed (reviewer-renata). WP03 owned procedure post-merge-arch-gate-adjudication.procedure.yaml is complete & compliant: 4 ordered steps (full sweep -> cross-base pre-existing check -> CI-only shards local -> adjudicate); mission-base != lane-base distinction EXPLICIT in Step 2 + anti_patterns + notes (target_branch/meta.json vs lanes.json base); CI-only shards named (tests/integration, tests/git, integration-tests-core-misc); references: DIRECTIVE_043 + architectural-gate-non-vacuity via shipped type/id/reason convention; graph.yaml UNCHANGED (PD-2); overlap-audit confirms genuinely new. Gates: doctor doctrine healthy/0-skipped-0-invalid, test_shipped_graph_valid 2 passed, terminology guard 3 passed. Compliance suite (test_tactic_compliance.py): WP03 procedure PASSES; 1 pre-existing failure is architectural-gate-non-vacuity.tactic.yaml (WP02-owned, commit 50687f9f5, root-vs-step dup ref frozen-baseline-shrink-only-ratchet) -- OUT OF WP03 SCOPE, must be fixed under WP02 before WP12/merge.
