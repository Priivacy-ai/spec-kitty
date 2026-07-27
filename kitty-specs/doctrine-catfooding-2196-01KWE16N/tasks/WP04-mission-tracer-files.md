---
work_package_id: WP04
title: §3 Mission Tracer Files
dependencies:
- WP01
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
phase: Phase 1 - New-Artifact Conversions (LA)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1809552"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/procedures/built-in/
create_intent:
- src/doctrine/procedures/built-in/mission-tracer-files.procedure.yaml
- src/doctrine/templates/mission-tracer-files/tooling-friction.md
- src/doctrine/templates/mission-tracer-files/approach.md
- src/doctrine/templates/mission-tracer-files/design-decisions.md
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/procedures/built-in/mission-tracer-files.procedure.yaml
- src/doctrine/templates/mission-tracer-files/tooling-friction.md
- src/doctrine/templates/mission-tracer-files/approach.md
- src/doctrine/templates/mission-tracer-files/design-decisions.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – §3 Mission Tracer Files

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

Author one new procedure and a 3-file template scaffold for §3 of the Quality & Tech-Debt Standing Orders:

1. **Procedure** — `mission-tracer-files`: describes the seed→append→assess lifecycle for tracer files that provide a running log of tooling friction, approach evolution, and design decisions during a mission.
2. **Template scaffold** — three sparse templates under `src/doctrine/templates/mission-tracer-files/`: `tooling-friction.md`, `approach.md`, `design-decisions.md`.

This WP also **folds experiment #2095** (the tracer-files experiment): cite #2095 in the procedure's provenance field; close issue #2095 on land.

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T015 output)
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for new artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges authored in the procedure YAML
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §3 of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **Zero existing coverage**: grep confirms no tracer-file procedure or template in `src/doctrine/`. This is a clean new authoring.
- **Experiment #2095**: issue #2095 tracked the multi-tracer pre-flight experiment. The procedure is the doctrine-ification of that experiment. The procedure's provenance/metadata should cite #2095 explicitly. The issue must be closed (with a reference to this mission) when this WP lands.
- **Template purpose**: the three template files are sparse scaffolds — a heading structure and a few prompting questions per section. They are NOT essays. A contributor should be able to fill in a tracer file in under 5 minutes at each lifecycle point.
- **Lifecycle phases**: seed (at mission start), append (during implement), assess (at mission close).
- **Template location**: `src/doctrine/templates/mission-tracer-files/` (new directory under `src/doctrine/templates/`).
- **PD-2**: author inline DRG edges in procedure YAML only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T015 – [C-001] Overlap-audit §3

- **Purpose**: Mandatory overlap-audit before authoring (C-001). Confirm zero tracer-file coverage exists.
- **Steps**:
  1. Run `grep -r "tracer\|trace.*file\|tooling.friction\|design.decision" src/doctrine/ --include="*.yaml" -l` — record zero hits.
  2. Check `src/doctrine/procedures/built-in/` and `src/doctrine/templates/` for any tracer-adjacent artifacts.
  3. Write augment-vs-create decision: §3 has zero existing coverage → create new procedure + 3 templates.
- **Files**: None (audit only).
- **Parallel?**: No — must be first.

### Subtask T016 – Author mission-tracer-files procedure

- **Purpose**: Encode the seed→append→assess lifecycle as a procedure so agents and contributors know *when* and *how* to use the tracer files.
- **Steps**:
  1. Create `src/doctrine/procedures/built-in/mission-tracer-files.procedure.yaml`.
  2. Follow the procedure YAML schema (id, title, body, provenance, requires/suggests/refines).
  3. Set `id: mission-tracer-files`.
  4. Provenance/metadata: cite issue #2095 ("folds experiment #2095 — multi-tracer pre-flight cadence; close on land"). The provenance field format may vary by schema — use the field the schema supports (e.g. a `notes` or `provenance` field, or a comment in the body).
  5. Body structure:
     - **Seed (at planning/start)**: create the three files from the doctrine templates (`tooling-friction.md`, `approach.md`, `design-decisions.md`) in `traces/` under the mission's `kitty-specs/` directory. Fill in the initial context for each file (what tooling the mission touches, what approach is being tried, what design decisions have already been made in the spec/plan).
     - **Append (during implementation)**: at each significant decision point or when tooling friction is encountered, append a dated entry to the relevant tracer file. Entries should be brief (1-3 sentences) and timestamped.
     - **Assess (at mission close / before accept)**: review all three tracer files. Summarize insights in the mission retrospective. File any surfaced tooling-friction issues in the tracker.
  6. Add a note that the three tracer files are *optional experiment infrastructure* — they support the adversarial squad cadence and post-planning review, but their absence does not block acceptance.
- **Files**: `src/doctrine/procedures/built-in/mission-tracer-files.procedure.yaml` (create new)
- **Parallel?**: No — T017 can start after this.
- **Notes**: Cite #2095 explicitly in a way that survives as a permanent record. Close #2095 on land via a tracker comment referencing this mission.

### Subtask T017 – Author 3-file template scaffold

- **Purpose**: Provide the sparse template files contributors copy into their `traces/` directory when seeding tracer files.
- **Steps**:
  1. Create the directory `src/doctrine/templates/mission-tracer-files/` if it does not exist.
  2. Create three template files:
     - `tooling-friction.md`: heading "Tooling Friction Log" + a few prompting questions (e.g. "What tooling did you have to work around?", "What blocked you unexpectedly?") + a dated-entry placeholder.
     - `approach.md`: heading "Approach Evolution" + prompting questions (e.g. "What approach did you start with?", "What changed and why?") + a dated-entry placeholder.
     - `design-decisions.md`: heading "Design Decisions" + prompting questions (e.g. "What decision was made?", "What alternatives were considered?", "What was the rationale?") + a dated-entry placeholder.
  3. Each template should be 10-20 lines: a header, 2-4 prompting questions, and a single example entry stub. Do NOT write essays.
- **Files**: 
  - `src/doctrine/templates/mission-tracer-files/tooling-friction.md` (create new)
  - `src/doctrine/templates/mission-tracer-files/approach.md` (create new)
  - `src/doctrine/templates/mission-tracer-files/design-decisions.md` (create new)
- **Parallel?**: [P] Can proceed in parallel with T018 once T016 is committed.
- **Notes**: These are user-facing templates, not doctrine YAML. They do not go through the doctrine schema loader. The `doctor doctrine --json` gate does not apply to Markdown files in `templates/`.

### Subtask T018 – Author inline DRG edges

- **Purpose**: Wire the procedure into the DRG so the charter closure can traverse to it.
- **Steps**:
  1. Add inline DRG edges to `mission-tracer-files.procedure.yaml`:
     - `suggests: [urn:styleguide:adversarial-squad-cadence]` (the procedure supports the §1 cadence, authored by WP08; use a forward reference — the URN will resolve once WP08 commits).
  2. Optionally add `suggests: [urn:paradigm:brownfield-onboarding]` if the procedure is naturally invoked in the brownfield ramp-up context.
  3. Confirm `graph.yaml` has NOT been regenerated (PD-2).
- **Files**: `src/doctrine/procedures/built-in/mission-tracer-files.procedure.yaml` (inline edge edits)
- **Parallel?**: No — must run after T016.
- **Notes**: Forward references to artifacts authored by other WPs are valid in inline edges. The DRG generator validates them at regen time (WP12).

### Subtask T019 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate the new procedure YAML.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the newly authored procedure (`mission-tracer-files`). Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green.
  4. Confirm inline DRG edges present in procedure YAML.
  5. Confirm `graph.yaml` UNCHANGED.
  6. Confirm agent-profile wiring DEFERRED to WP12.
  7. Confirm issue #2095 is cited in the procedure (provenance).
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after T016 (procedure schema validation).
- `pytest tests/architectural/test_no_legacy_terminology.py -q` before `for_review`.
- Visual inspection: each template file is 10-20 lines with a heading, prompting questions, and an example entry stub.

## Risks & Mitigations

- **Over-writing templates**: templates should be sparse scaffolds, not documents. If a template exceeds ~25 lines, it has been over-authored.
- **Procedure scope creep**: the procedure describes the lifecycle of tracer files; it is NOT a project management guide. Keep the body focused on "when to seed, when to append, when to assess" rather than broader mission hygiene.

## Review Guidance

- T015 overlap-audit record in Activity Log: "zero existing tracer coverage — create new."
- Procedure has three clearly named lifecycle phases (seed/append/assess).
- Issue #2095 cited in procedure provenance.
- All three template files exist and are sparse (10-25 lines each).
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED; agent-profile wiring deferred to WP12.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:05:38Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Assigned agent via action command
- 2026-07-01T10:17:46Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Ready for review: procedure + 3 templates authored; all gates green (doctor/graph/terminology); #2095 cited in provenance; graph.yaml unchanged; agent-profile wiring deferred to WP12
- 2026-07-01T10:18:19Z – claude:opus:reviewer-renata:reviewer – shell_pid=1809552 – Started review via action command
- 2026-07-01T10:21:36Z – user – shell_pid=1809552 – Review passed (reviewer-renata). §3 mission-tracer-files procedure + 3 sparse templates (14 lines each, seed/append/assess lifecycle). WP04-owned commit 70529d69c touches exactly the 4 owned_files; other diff files are dependency-merge inherited. Overlap-audit confirmed independently: zero prior tracer coverage in src/doctrine/. #2095 cited in provenance (close-on-land). Inline DRG edges via canonical references: block (adversarial-squad-cadence forward-ref + brownfield-onboarding); graph.yaml UNCHANGED (PD-2). Agent-profile wiring deferred to WP12 (C-003). Gates green: doctor doctrine exit 0 / 18/18 valid / 0 skipped; test_shipped_graph_valid.py 2 passed; test_no_legacy_terminology.py 3 passed.
