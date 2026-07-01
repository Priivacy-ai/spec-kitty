---
work_package_id: WP13
title: 'Capstone: Compile the Spec Kitty Charter'
dependencies:
- WP12
requirement_refs:
- FR-014
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T058
- T059
- T060
- T061
- T062
- T063
phase: Phase 4 - Capstone
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2283133"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: .kittify/charter/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .kittify/charter/
- .kittify/config.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP13 – Capstone: Compile the Spec Kitty Charter

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

Compile the Spec Kitty Charter from the activated catfooding doctrine set. This is the **catfooding** outcome: Spec Kitty governs its own development with the doctrine it ships to consumers.

**Sequence is load-bearing (C-007 + `contracts/capstone-compile.md`):**
1. Confirm preconditions (DRG tests green, doctor healthy, existing charter read).
2. Activate catfooding artifacts (`charter activate --cascade` → writes `.kittify/config.yaml`).
3. Mirror activation into interview `answers.yaml` (named manual sub-step — no auto-bridge).
4. Generate (`charter generate` → renders `charter.md` + `references.yaml`).
5. Reconcile existing v1.1.5 charter (not clobber).
6. Final acceptance.

**Any reversal of steps 2 and 4 (generate-before-activate) yields a shallow reference closure and is a contract violation.**

**Acceptance gates (SC-001 through SC-005, NFR-003, C-007):**
- [ ] `charter.md` + `references.yaml` regenerated from the activated set; version past 1.1.5
- [ ] Reference closure non-shallow: every activated catfooding artifact's `requires`/`suggests` edges resolve in `references.yaml`
- [ ] `spec-kitty doctor doctrine --json` healthy after compile
- [ ] `spec-kitty charter list` shows all 8 sections represented (SC-001)
- [ ] No pre-existing v1.1.5 content clobbered (SC-003)
- [ ] #2196 is a functional epic with children covering all 8 sections (SC-004)
- [ ] `docs/development/quality-and-tech-debt-standing-orders.md` present + inventoried (SC-005)

## Context & Constraints

- **Section source**: FR-014, `contracts/capstone-compile.md` (read the contract before starting — it is the authoritative sequence reference).
- **Depends on WP12**: the single `graph.yaml` regen must be complete and DRG tests green before WP13 starts.
- **Existing charter**: `.kittify/charter/charter.md` v1.1.5 exists. Read it before generating. The compile is a RECONCILE, not a greenfield. Existing sections must be preserved/merged; the version must be bumped past 1.1.5.
- **Activation ≠ generation**: `charter activate` writes `.kittify/config.yaml` and updates activation state. It does NOT render `charter.md`. `charter generate` renders the charter from `answers.yaml` + the activation-filtered DRG closure. Both steps are required; neither is a substitute for the other.
- **answers.yaml manual mirror (named sub-step)**: there is no automatic bridge from `charter activate` to `interview/answers.yaml`. After activation, you must manually open `.kittify/charter/interview/answers.yaml` and add the catfooding artifact IDs to the `selected_directives`, `selected_tactics`, `selected_styleguides`, `selected_procedures`, `selected_toolguides`, `selected_paradigms`, `selected_templates` fields. If this step is skipped, `charter generate` will render a charter that references none of the catfooding artifacts — the reference closure will be shallow.
- **Non-shallow closure (NFR-003)**: the `references.yaml` output must resolve the full transitive closure of `requires`/`suggests`/`refines` edges for every activated catfooding artifact — not just the directly selected IDs. If the closure is shallow, the DRG edge authoring in WP02-WP11 was for nothing.
- **C-007**: activate THEN generate. Never reverse. Confirmed in `contracts/capstone-compile.md`.
- **SC-001**: `spec-kitty charter list` must show at least one artifact per §1-§8. Map: §1 → adversarial-squad-cadence styleguide; §2 → 025 (extended); §3 → mission-tracer-files procedure; §4 → 041 (extended); §5a → DIRECTIVE_043 + architectural-gate-non-vacuity tactic; §5b → post-merge-arch-gate-adjudication procedure; §6 → DIRECTIVE_044 + canonical-source-unification tactic + terminology-guard toolguide; §7 → DIRECTIVE_045 + pr-agent-worktree-isolation tactic; §8 → planning-and-tracking styleguide (extended) + two new tactics.
- **Split seam**: if the mission has run long and WP13 is being executed as a follow-on, this WP is the clean cut point documented in research.md D-6. The charter machinery does not change; only its activation set changes.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T058 – Confirm preconditions

- **Purpose**: Verify that all WP12 gates have passed and the existing charter has been read, before making any changes.
- **Steps**:
  1. Confirm WP12 is `approved` or `done`: `spec-kitty agent tasks status`.
  2. Run `pytest tests/doctrine/drg/ -q` — must be green (freshness + cycle + relations).
  3. Run `spec-kitty doctor doctrine --json` — must be healthy (0 skipped, 0 invalid).
  4. Open and read `.kittify/charter/charter.md` in full — note the version number (should be v1.1.5 or similar). Note what sections are present. This is the baseline to reconcile against.
  5. Open and read `.kittify/charter/interview/answers.yaml` — note the current `selected_directives`, `selected_tactics`, etc. lists. These are the starting point for the manual mirror in T060.
  6. Open and read `.kittify/config.yaml` — note the current `activated_directives`, `activated_tactics`, etc. lists.
  7. Record all findings in the Activity Log before proceeding.
- **Files**: No files changed — verification + read only.
- **Parallel?**: No — must be first.
- **Notes**: If `pytest tests/doctrine/drg/ -q` fails, DO NOT proceed to T059. Return WP12 to the implementer with the failure details.

### Subtask T059 – Activate catfooding artifacts

- **Purpose**: Write the activation state into `.kittify/config.yaml` via `charter activate --cascade`. Activation does NOT render the charter.
- **Steps**:
  1. **First — confirm the exact cascade argument form**:
     ```bash
     spec-kitty charter activate --help
     ```
     Verify that `--cascade all` is the accepted argument (the pinned form used throughout this subtask). If `--help` shows a different accepted value for the cascade flag, use that form instead and note the deviation in the Activity Log.
  2. For each catfooding artifact kind/ID, run (using `--cascade all` — bare `--cascade` is unverified against the CLI parser):
     ```bash
     spec-kitty charter activate directive DIRECTIVE_043 --cascade all
     spec-kitty charter activate directive DIRECTIVE_044 --cascade all
     spec-kitty charter activate directive DIRECTIVE_045 --cascade all
     spec-kitty charter activate tactic architectural-gate-non-vacuity --cascade all
     spec-kitty charter activate tactic frozen-baseline-shrink-only-ratchet --cascade all
     spec-kitty charter activate tactic canonical-source-unification --cascade all
     spec-kitty charter activate tactic pr-agent-worktree-isolation --cascade all
     spec-kitty charter activate tactic ownership-map-leeway --cascade all
     spec-kitty charter activate tactic reviewer-implementer-role-separation --cascade all
     spec-kitty charter activate styleguide adversarial-squad-cadence --cascade all
     spec-kitty charter activate styleguide planning-and-tracking --cascade all
     spec-kitty charter activate toolguide terminology-guard --cascade all
     spec-kitty charter activate procedure mission-tracer-files --cascade all
     spec-kitty charter activate procedure post-merge-arch-gate-adjudication --cascade all
     ```
     (Adjust IDs to match the exact `id` fields in each artifact YAML. Use `spec-kitty charter list` to verify activation after each command, or activate in bulk and verify at the end.)
  3. Confirm `.kittify/config.yaml` `activated_*` lists contain the catfooding IDs after all activate commands.
  4. Do NOT run `charter generate` yet — activation must precede generation (C-007).
- **Files**: `.kittify/config.yaml` (activation state updated)
- **Parallel?**: No.
- **Notes**: The `--cascade all` flag activates the artifact AND all artifacts in its `requires`/`suggests` transitive closure. This is the mechanism that achieves non-shallow closure. If the cascade argument form is different (confirmed via `--help` in step 1), use that form — but always use an explicit cascade value, never bare `--cascade`.

### Subtask T060 – Mirror activation into answers.yaml (named manual sub-step)

- **Purpose**: Update `.kittify/charter/interview/answers.yaml` to include the catfooding artifact IDs so `charter generate` references them. There is no auto-bridge from `charter activate` to `answers.yaml`.
- **Steps**:
  1. **Precondition — seed `answers.yaml` if absent**: check whether `.kittify/charter/interview/answers.yaml` exists:
     ```bash
     ls .kittify/charter/interview/answers.yaml
     ```
     If the file does NOT exist, seed it by running:
     ```bash
     spec-kitty charter interview
     ```
     Walk through the interview and complete the flow — this creates `answers.yaml`. Do NOT assume the file pre-exists (it is not committed and may need to be created fresh for this project). Only proceed to step 2 once the file is confirmed present. If `spec-kitty charter interview` is not available or cannot create the file, hand-create `.kittify/charter/interview/answers.yaml` with the schema structure matching any existing project's `answers.yaml` (consult `spec-kitty charter --help` for the format).
  2. Open `.kittify/charter/interview/answers.yaml`.
  2. For each artifact kind, add the catfooding IDs to the relevant `selected_*` field:
     - `selected_directives`: add `DIRECTIVE_043`, `DIRECTIVE_044`, `DIRECTIVE_045`.
     - `selected_tactics`: add `architectural-gate-non-vacuity`, `frozen-baseline-shrink-only-ratchet`, `canonical-source-unification`, `pr-agent-worktree-isolation`, `ownership-map-leeway`, `reviewer-implementer-role-separation`.
     - `selected_styleguides`: add `adversarial-squad-cadence`, `planning-and-tracking`.
     - `selected_toolguides`: add `terminology-guard`.
     - `selected_procedures`: add `mission-tracer-files`, `post-merge-arch-gate-adjudication`.
  3. Do NOT remove existing entries in `answers.yaml` — only append.
  4. Save and verify the YAML is valid: `python -c "import yaml; yaml.safe_load(open('.kittify/charter/interview/answers.yaml'))"`.
- **Files**: `.kittify/charter/interview/answers.yaml` (selected lists extended)
- **Parallel?**: No — must run after T059.
- **Notes**: If this step is skipped, `charter generate` will produce a charter that references none of the catfooding artifacts. The reference closure will be shallow and SC-001 will fail. This is the single most failure-prone step in the capstone sequence.

### Subtask T061 – Generate the charter

- **Purpose**: Render `charter.md` + `references.yaml` from the updated `answers.yaml` and the activation-filtered DRG closure.
- **Steps**:
  1. Run:
     ```bash
     spec-kitty charter generate
     ```
  2. Verify that `charter.md` and `references.yaml` have been updated (check timestamps and content).
  3. Open `references.yaml` and verify it contains entries for the catfooding artifacts (not just the pre-existing v1.1.5 artifacts).
  4. Run `spec-kitty charter list` — confirm all 8 sections are represented. If a section is missing, check T060's `answers.yaml` edits and re-run.
- **Files**: 
  - `.kittify/charter/charter.md` (regenerated)
  - `.kittify/charter/references.yaml` (regenerated)
- **Parallel?**: No — must run after T060.
- **Notes**: If `charter generate` fails with a resolver error, check that the `answers.yaml` IDs match the artifact `id` fields exactly (case-sensitive).

### Subtask T062 – Reconcile with existing v1.1.5 charter

- **Purpose**: Ensure the regenerated `charter.md` supersedes v1.1.5 coherently — no pre-existing content clobbered, version bumped.
- **Steps**:
  1. Diff the new `charter.md` against the v1.1.5 baseline (use `git diff HEAD -- .kittify/charter/charter.md` or a manual diff of the content noted in T058).
  2. Confirm:
     - Version number is past 1.1.5 (e.g. 1.2.0 or per the charter generator's versioning scheme).
     - All sections present in v1.1.5 are still present (the new catfooding sections are additive).
     - No pre-existing directives/tactics/etc. have been dropped from the reference list.
  3. **MANDATORY reconcile (this step is always required — not contingent on "if it clobbers")**: `charter generate` is a bundle REGENERATE with `--force` semantics. It WILL overwrite `charter.md` with a fresh generation from the current `answers.yaml` and the activation-filtered DRG closure. It does NOT merge or preserve the existing v1.1.5 hand-authored content. Therefore, after generation, you MUST manually restore the v1.1.5 content that was present in the baseline read in T058. Diff the new `charter.md` against the v1.1.5 content and re-apply any sections, prose, decisions, or framing that are present in v1.1.5 but absent in the generated output. This step is always required — do NOT skip it on the assumption that generate "might merge" or that the generated output might already include v1.1.5 content.
  4. Run `spec-kitty charter list` again to confirm all 8 catfooding sections show (SC-001).
- **Files**: `.kittify/charter/charter.md` (mandatory manual reconciliation edits after generate)
- **Parallel?**: No — must run after T061.
- **Notes**: The primary failure mode is that `charter generate` clobbers the v1.1.5 content. It is not a "risk to mitigate" — it is the expected behavior. The v1.1.5 content read in T058 is the authoritative baseline for what must survive into the reconciled output. Have that content ready before running T061.

### Subtask T063 – Final acceptance

- **Purpose**: Verify all mission success criteria and acceptance gates.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (post-compile health check).
  2. `spec-kitty charter list` → all 8 sections represented (SC-001).
  3. **Non-shallow closure concrete invariant check**: confirm the reference closure is non-shallow by asserting that a `suggests`-only edge target — an artifact reachable ONLY transitively via a `suggests` edge from an activated directive, NOT directly listed in `answers.yaml` — appears in `references.yaml`. Perform this with a concrete, mechanical grep:
     ```bash
     # The architectural-gate-non-vacuity tactic is `suggested` by DIRECTIVE_043 but is NOT directly listed in answers.yaml.
     # After charter generate, it MUST appear in references.yaml if the closure is non-shallow:
     grep "architectural-gate-non-vacuity" .kittify/charter/references.yaml
     ```
     If this grep returns no match, the closure is shallow — `charter generate` rendered without the full transitive closure. Check that `--cascade all` was used in T059 and that `answers.yaml` was correctly updated in T060 before re-running generate. A shallow closure silently passes the charter but renders the WP02-WP11 DRG edge authoring inert. Record the grep output (match or no match) in the Activity Log.
  4. Verify `docs/development/quality-and-tech-debt-standing-orders.md` is present and inventoried (SC-005 — committed in WP01).
  5. Verify `scope-tracker` label removed from #2196 (SC-004 — done in WP01).
  6. Verify no duplicate directive authorities for pre-covered sections (SC-002): §4 has 041 extended (no new §4 directive), §2 has 025 extended (no new campsite directive), §8 references tiered-standards (no restatement), §7 references commit-history tactic (no re-authoring).
  7. Record final acceptance in Activity Log. Move WP to `for_review`.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `pytest tests/doctrine/drg/ -q` (T058 pre-condition).
- `spec-kitty doctor doctrine --json` (T058 + T063).
- `spec-kitty charter list` (T061 + T062 + T063).
- Manual diff of `charter.md` vs v1.1.5 baseline (T062).
- Open `references.yaml` and spot-check 3 catfooding artifacts for transitive edge resolution (T063).

## Risks & Mitigations

- **Generate-before-activate (C-007)**: if T059 and T060 are skipped or reversed, the closure will be shallow. The contract violation is detected in T063's non-shallow check.
- **answers.yaml mirror skipped (highest operational risk)**: `charter generate` will produce a charter without catfooding artifacts. The `charter list` check in T061 surfaces this immediately.
- **Greenfield clobber (expected behavior, not a risk to mitigate)**: `charter generate` WILL replace `charter.md` — this is by design (it regenerates from scratch). T062's mandatory reconcile step is the required response, not an optional mitigation. Have the v1.1.5 content from T058 ready BEFORE running T061 so reconciliation is immediate and complete.
- **Cascade depth**: `--cascade` must resolve `requires`/`suggests` edges transitively. If the cascade is shallow (only direct neighbors), some tactic/procedure artifacts may not appear in `references.yaml`. Test by checking that a procedure `required` by a directive appears in `references.yaml` even though the procedure was not directly listed in `answers.yaml`.

## Review Guidance

- T058 records the v1.1.5 charter's version and existing sections in Activity Log.
- Sequence: activate → mirror answers → generate → reconcile (C-007 compliant).
- `charter list` shows all 8 sections (SC-001).
- `references.yaml` is non-shallow: `grep "architectural-gate-non-vacuity" .kittify/charter/references.yaml` returns a match (this tactic is only transitively reachable via DIRECTIVE_043's `suggests` edge, never directly selected — its presence proves non-shallow closure). Grep output recorded in Activity Log.
- `charter.md` version past 1.1.5; pre-existing content intact.
- `doctor doctrine --json` healthy.
- SC-002 confirmed (no duplicate directive authorities).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T11:43:25Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=2091770 – Assigned agent via action command
- 2026-07-01T12:30:28Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=2091770 – Charter compiled: activate (043/044/045 directives + 6 tactics + 2 styleguides) → mirror answers.yaml → generate references.yaml → reconcile charter.md v1.2.0; closure non-shallow: architectural-gate-non-vacuity in references.yaml via DIRECTIVE_043→suggests DRG edge (SC-001 ✓); charter list shows 8+ artifact kinds (SC-002 ✓); doctor profile_health healthy ✓
- 2026-07-01T12:35:26Z – claude:opus:reviewer-renata:reviewer – shell_pid=2187483 – Started review via action command
- 2026-07-01T12:44:20Z – user – shell_pid=2187483 – Moved to planned
- 2026-07-01T13:07:01Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=2227992 – Started implementation via action command
- 2026-07-01T13:38:26Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=2227992 – Cycle 1: config.yaml truthfully CLI-activated via spec-kitty charter activate --cascade all (DIRECTIVE_044 compliant); activated_procedures + activated_toolguides keys now present; 8/8 directive-reachable catfooding artifacts resolve in references.yaml; 6 governed-but-not-charter-referenced explicitly noted + deferred (narrowed NFR-003, operator-accepted); charter.md reconciled to v1.2.0 preserving v1.1.5 substance; references.yaml gitignored + not committed; clean worktree
- 2026-07-01T13:39:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=2283133 – Started review via action command
