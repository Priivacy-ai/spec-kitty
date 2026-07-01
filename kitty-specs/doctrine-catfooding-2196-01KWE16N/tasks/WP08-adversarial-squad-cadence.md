---
work_package_id: WP08
title: §1 Adversarial Squad Cadence
dependencies:
- WP01
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
phase: Phase 2 - Extend Conversions (LB)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1791167"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/styleguides/built-in/
create_intent:
- src/doctrine/styleguides/built-in/adversarial-squad-cadence.styleguide.yaml
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/styleguides/built-in/adversarial-squad-cadence.styleguide.yaml
- src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – §1 Adversarial Squad Cadence

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

Author one new styleguide and extend one existing paradigm for §1 of the Quality & Tech-Debt Standing Orders:

1. **Styleguide (NEW)** — `adversarial-squad-cadence`: captures the **cadence recommendation only** ("run a bounded multi-profile squad at every planning point-cut — post-spec, post-plan, post-tasks, and at sizing — as strong guidance, not a gate"). Must NOT be `enforcement: required`. Must REFERENCE `adversarial-squad-deployment.procedure` for the playbook and point-cut table — do NOT re-author them. Folds experiment #2094 (cite in provenance, close on land).
2. **Paradigm (EXTEND)** — `brownfield-onboarding.paradigm.yaml`: add a cross-link to the new cadence styleguide. WP08 is sole owner of this file per C-003; WP09 will REFERENCE the paradigm but must NOT edit it.

**C-006 (hard constraint)**: §1 MUST NOT be `enforcement: required`. The shipped `adversarial-squad-deployment.procedure` declares itself *optional* and names "hard-wiring the squad as a gate" as an anti-pattern. A required §1 directive or styleguide would contradict shipped doctrine and is a review rejection.

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T033 output) — must read both the procedure and the paradigm
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for new artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12; run against both the new styleguide and the extended paradigm)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges authored in styleguide + paradigm extension
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §1 of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **Existing coverage to READ before authoring**:
  - `src/doctrine/procedures/built-in/adversarial-squad-deployment.procedure.yaml` — read this fully. Note the "optional and charter-activated" language and the anti-pattern list. This procedure owns the playbook and point-cut table; WP08's styleguide REFERENCES it, not restates it.
  - `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml` — read before extending. Preserve all existing content. Add only the cadence cross-link.
- **C-003 (shared-target lock)**: WP08 is sole owner of `brownfield-onboarding.paradigm.yaml`. WP09 (§2) references the paradigm in its DRG edges but must NOT edit the paradigm file. Any change to the paradigm file must flow through WP08.
- **Experiment #2094**: the multi-squad pre-flight cadence experiment. Cite in the styleguide's provenance/metadata; close #2094 on land with a tracker comment referencing this mission.
- **Styleguide kind**: a styleguide can carry guidance without `enforcement: required`. The `enforcement` field (if the schema supports it for styleguides) must be `optional` or omitted — never `required` (C-006).
- **Do NOT re-author the playbook**: the cadence recommendation says "when to squad up"; the procedure owns "how to run the squad." The styleguide should describe the cadence (what trigger events prompt a squad) and cross-reference the procedure for the execution details.
- **PD-2**: inline DRG edges only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T033 – [C-001] Overlap-audit §1

- **Purpose**: Mandatory overlap-audit (C-001 / DIRECTIVE_003). Read the procedure and paradigm that already partially cover §1; record the cadence-recommendation gap.
- **Steps**:
  1. Read `src/doctrine/procedures/built-in/adversarial-squad-deployment.procedure.yaml` fully. Note: (a) it is declared optional; (b) it owns the playbook and point-cut table; (c) "hard-wiring the squad as a gate" is named as an anti-pattern. Record this verbatim in the Activity Log.
  2. Read `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml` fully. Note whether it has any cadence-recommendation content. Record.
  3. Run `grep -r "cadence\|squad.*cadence\|point.cut.*squad" src/doctrine/ --include="*.yaml" -l` — record hits.
  4. Write augment-vs-create decision: the procedure owns the playbook/point-cut table; the paradigm owns brownfield onboarding context. Neither has a standalone *cadence recommendation* (the "when to squad up" guidance). The uncovered atom is the cadence recommendation → author new styleguide. The paradigm needs a cross-link → extend (do NOT replace).
- **Files**: None (audit only — record in Activity Log).
- **Parallel?**: No — must be first.
- **Notes**: The verbatim quote from the procedure about "optional" and "gate-hardwiring anti-pattern" must appear in the Activity Log — reviewers use it to verify C-006 compliance.

### Subtask T034 – Author adversarial-squad-cadence styleguide

- **Purpose**: Encode the cadence recommendation as a styleguide (not a required directive) that references the procedure for execution details.
- **Steps**:
  1. Create `src/doctrine/styleguides/built-in/adversarial-squad-cadence.styleguide.yaml`.
  2. Follow the styleguide YAML schema. Do NOT set `enforcement: required` (C-006).
  3. `id: adversarial-squad-cadence`, `title: "Adversarial Squad Cadence"`.
  4. Provenance/metadata: cite issue #2094 ("folds experiment #2094 — multi-squad pre-flight cadence; close on land").
  5. Body must cover:
     - **What the cadence is**: run a bounded multi-profile adversarial squad at each planning point-cut. Canonical trigger points: post-spec, post-plan, post-tasks, and at mission sizing. The squad is guidance, not a gate — a mission is not blocked for skipping it.
     - **Cadence depth**: 3-5 profile perspectives per squad is typical; more is diminishing returns. A 20-30 min bounded squad is preferable to an unbounded sprawl.
     - **What it is NOT**: this styleguide does not own the squad playbook (profile selection, point-cut table, model discipline) — those live in `adversarial-squad-deployment.procedure`. This styleguide adds only the "when and why" layer.
     - **Cross-reference**: for execution details (squad playbook, profile roster, point-cut table, anti-patterns), see `adversarial-squad-deployment.procedure`.
  6. Add inline DRG edges: `suggests: [urn:procedure:adversarial-squad-deployment, urn:paradigm:brownfield-onboarding]`.
- **Files**: `src/doctrine/styleguides/built-in/adversarial-squad-cadence.styleguide.yaml` (create new)
- **Parallel?**: No — T035 depends on this.
- **Notes**: Close #2094 on land with a tracker comment: "Closes #2094: the multi-squad pre-flight cadence is now encoded as doctrine in the adversarial-squad-cadence styleguide (mission doctrine-catfooding-2196)."

### Subtask T035 – Extend brownfield-onboarding.paradigm.yaml

- **Purpose**: Add a cross-link from the brownfield paradigm to the new cadence styleguide. WP08 is sole owner of this file; preserve all existing content.
- **Steps**:
  1. Open `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml`.
  2. Add a brief cross-reference (in the body's existing context, or as a new section) pointing to the adversarial-squad-cadence styleguide as the recommended cadence discipline for brownfield onboarding.
  3. Add inline DRG edge: `suggests: [urn:styleguide:adversarial-squad-cadence]` (if not already present).
  4. Do NOT restructure, rewrite, or remove any existing content from the paradigm. The change must be purely additive.
- **Files**: `src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml` (extend existing)
- **Parallel?**: No — must run after T034.
- **Notes**: WP09 (§2) references this paradigm in its DRG edges. If WP09 is being worked in parallel, coordinate to ensure WP08 lands the paradigm extension before WP09's DRG edges are validated (or accept a forward-reference that WP12 resolves).

### Subtask T036 – Author inline DRG edges

- **Purpose**: Verify all DRG edges are in place for the styleguide and the paradigm extension; confirm `graph.yaml` is unchanged.
- **Steps**:
  1. Confirm `adversarial-squad-cadence.styleguide.yaml` has `suggests` edges to `adversarial-squad-deployment` procedure and `brownfield-onboarding` paradigm.
  2. Confirm `brownfield-onboarding.paradigm.yaml` has `suggests` edge to `adversarial-squad-cadence` styleguide.
  3. Confirm `graph.yaml` has NOT been regenerated (PD-2).
  4. Record in Activity Log.
- **Files**: No new files — edge verification only.
- **Parallel?**: No — must run after T034+T035.

### Subtask T037 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate new artifact YAMLs.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the newly authored styleguide (`adversarial-squad-cadence`) and the extended paradigm (`brownfield-onboarding`). Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. Confirm styleguide does NOT have `enforcement: required` (C-006 hard constraint).
  5. Confirm the procedure's playbook and point-cut table are NOT restated in the styleguide body.
  6. Confirm #2094 is cited in the styleguide provenance.
  7. Confirm `graph.yaml` UNCHANGED; agent-profile wiring DEFERRED to WP12.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after T034 and again after T035.
- `pytest tests/architectural/test_no_legacy_terminology.py -q`.
- Manual check: open the styleguide YAML and confirm no `enforcement: required` field.

## Risks & Mitigations

- **C-006 violation (highest risk for this WP)**: accidentally setting `enforcement: required` on the styleguide. Check the schema carefully; if the styleguide kind supports an `enforcement` field, it must be absent or `optional`. If the kind does not support `enforcement`, confirm the field is not present at all. A reviewer will check this field explicitly.
- **Playbook re-authoring**: copying the procedure's playbook (squad profile selection, point-cut definitions, anti-pattern list) into the styleguide body creates a split-brain authority. The styleguide body must contain only the cadence recommendation and cross-references; the procedure owns the playbook. If you find yourself writing "profile selection order" or "anti-pattern: over-squadding" in the styleguide, those are the procedure's content — remove and reference instead.
- **Paradigm clobber**: any rewrite of `brownfield-onboarding.paradigm.yaml` that restructures, removes, or replaces existing content is a C-003 violation. The change must be purely additive. Run `git diff src/doctrine/paradigms/built-in/brownfield-onboarding.paradigm.yaml` after T035 and confirm no deletions appear.
- **#2094 provenance missing**: the folds-experiment record must survive in the styleguide YAML. If the schema supports a `provenance` or `notes` field, use it. If not, embed the citation in the body as a prose sentence (e.g., "This styleguide folds experiment #2094 (multi-squad pre-flight cadence; closed on land).").

## Dependency Notes

- WP08 (brownfield paradigm) must complete before WP09 validates its DRG edges (WP09 references the paradigm).
- WP08 is parallelizable with WP02, WP04, WP05, WP06, WP07, WP10, WP11 (disjoint surfaces).
- WP08 enables WP12 (two new/extended DRG nodes in the single regen).

## Review Guidance

- T033 audit quotes the procedure's "optional" and "gate-hardwiring anti-pattern" language verbatim.
- Styleguide does NOT have `enforcement: required`; body does NOT restate the playbook.
- #2094 cited in styleguide provenance.
- `brownfield-onboarding.paradigm.yaml` extended additively — no existing content removed.
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED; agent-profile wiring deferred to WP12.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:06:10Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Assigned agent via action command
- 2026-07-01T10:14:59Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Ready for review: adversarial-squad-cadence styleguide (scope:operations, enforcement omitted C-006) + brownfield-onboarding paradigm extended additively. DRG edges inline. graph.yaml unchanged. All 3 gates green.
- 2026-07-01T10:15:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=1791167 – Started review via action command
- 2026-07-01T10:19:06Z – user – shell_pid=1791167 – Review passed: C-006 satisfied (no enforcement:required key — only prose; optional/never-a-gate invariant preserved, Gate-hardwiring named as anti-pattern, references adversarial-squad-deployment.procedure not restated). #2094 cited in provenance. DRG edges via references block (sibling-consistent) + additive paradigm ref; graph.yaml untouched (deferred WP12). Diff scope = 2 owned files only. Gates re-run green: doctor doctrine exit0/18-18 valid; test_shipped_graph_valid 2 passed; test_no_legacy_terminology 3 passed.
