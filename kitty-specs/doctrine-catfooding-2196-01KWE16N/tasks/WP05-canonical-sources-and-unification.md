---
work_package_id: WP05
title: §6 Canonical Sources + Unification
dependencies:
- WP01
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: design/doctrine-catfooding-2196
merge_target_branch: design/doctrine-catfooding-2196
branch_strategy: Planning artifacts for this mission were generated on design/doctrine-catfooding-2196. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doctrine-catfooding-2196 unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T023b
- T024
phase: Phase 1 - New-Artifact Conversions (LA)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1928552"
history:
- at: '2026-07-01T06:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/directives/built-in/
create_intent:
- src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml
- src/doctrine/tactics/built-in/canonical-source-unification.tactic.yaml
- src/doctrine/toolguides/built-in/terminology-guard.toolguide.yaml
- src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml
- src/doctrine/tactics/built-in/canonical-source-unification.tactic.yaml
- src/doctrine/toolguides/built-in/terminology-guard.toolguide.yaml
- src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – §6 Canonical Sources + Unification

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

Author three new doctrine artifacts for §6 of the Quality & Tech-Debt Standing Orders:

1. **DIRECTIVE_044** — `canonical-sources-and-unification`: three rules: (a) always use the canonical template/skill/CLI surface rather than improvising or copying older artefacts; (b) chase unification (one canonical surface authority), not parity with lackluster existing behavior; (c) a missing CLI command is a gap to file, not a signal to improvise a workaround. Directive number 044 is pre-allocated per PD-1.
2. **Tactic** — `canonical-source-unification`: concrete steps for applying the unification principle when a split-brain surface is found.
3. **Toolguide** — `terminology-guard`: describes when and how to run the legacy-terminology guard command. **This toolguide must quote-and-mark forbidden terms** (e.g. `"feature"`, `"ceremony"`) without using them in canonical voice (C-004). The toolguide is the operational surface for the guard invocation — it is NOT a restatement of the forbidden terms list.

**Conversion DoD (per `contracts/conversion-dod.md`):**
- [ ] Overlap-audit recorded (T020 output)
- [ ] `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (note: doctor-green is NOT schema proof for new artifacts)
- [ ] `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green (per-artifact schema validation — catches malformed YAML before WP12; run against all three new artifact YAMLs)
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py` → green
- [ ] Inline DRG edges authored in all three artifact YAMLs
- [ ] `src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md` companion file created; `terminology-guard.toolguide.yaml` carries `guide_path:` pointing to it (T023b)
- [ ] 🔜 Agent-profile `directives:` wiring DEFERRED to WP12 (C-003)
- [ ] 🔜 `graph.yaml` regeneration DEFERRED to WP12 (PD-2)

## Context & Constraints

- **Section source**: §6 of `docs/development/quality-and-tech-debt-standing-orders.md` (committed by WP01).
- **No existing coverage**: grep confirms no canonical-sources, unification-not-parity, or terminology-guard toolguide in `src/doctrine/`.
- **C-004 (critical for this WP)**: §6's own terminology-guard toolguide is the highest-risk surface for accidentally using forbidden terms in canonical voice. The toolguide describes *how to run the guard* and may *name* forbidden terms (e.g. listing them as examples), but must quote-and-mark them (`"feature"` in quotes, or in a code block, or explicitly labeled as "forbidden term example"). Using a forbidden term in running prose without qualification is a C-004 violation — the guard test will catch it.
- **Toolguide scope**: the toolguide describes the invocation: when to run it (before pushing doctrine/prose changes), what command to run (`pytest tests/architectural/test_no_legacy_terminology.py`), what a failure means, and how to fix it (reword, not exempt). It is NOT a policy document restating the terminology canon.
- **Unification vs. parity distinction**: the tactic must make this distinction concrete: "unification" means finding ONE canonical surface and routing everything through it; "parity" means adding the same feature to multiple divergent surfaces, preserving the split-brain. The directive and tactic must name the distinction explicitly.
- **PD-1**: 044 is pre-allocated. Do not mint 043, 045-049 here.
- **PD-2**: inline DRG edges only; do NOT regenerate `graph.yaml`.

## Branch Strategy

- **Strategy**: Coord topology. WP execution lanes branch from `kitty/mission-doctrine-catfooding-2196-01KWE16N`.
- **Planning base branch**: `design/doctrine-catfooding-2196`
- **Merge target branch**: `kitty/mission-doctrine-catfooding-2196-01KWE16N`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T020 – [C-001] Overlap-audit §6

- **Purpose**: Mandatory overlap-audit (C-001 / DIRECTIVE_003). Confirm no canonical-sources, unification-not-parity, or terminology-guard artifacts exist.
- **Steps**:
  1. `grep -r "canonical.source\|unification\|terminology.guard\|forbidden.term" src/doctrine/ --include="*.yaml" -l` — record findings.
  2. Check toolguides and directives for any existing §6-adjacent content.
  3. Write decision: §6 has zero existing doctrine coverage → create all three new artifacts.
- **Files**: None (audit only).
- **Parallel?**: No — must be first.

### Subtask T021 – Author DIRECTIVE_044

- **Purpose**: Encode the three canonical-sources-and-unification rules as a required directive.
- **Steps**:
  1. Create `src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml`.
  2. `id: DIRECTIVE_044`, `enforcement: required`, `title: "Canonical Sources and Unification"`.
  3. Body must state all three rules:
     - Rule 1 (use-canonical-sources): always use the canonical template/skill/command rather than copying older artefacts or improvising. Older missions and ad-hoc artefacts drift; the doctrine template is the single source of truth.
     - Rule 2 (unification-not-parity): when a split-brain surface is found, the correct response is to consolidate to ONE canonical surface authority — not to add the same behavior to multiple surfaces ("parity" preserves split-brain). Exception: do not drop load-bearing invariants without a migration path.
     - Rule 3 (missing-command-is-a-gap): a documented CLI command that is absent from the running tool is a gap to file upstream, not a workaround opportunity. If you find a missing command, trace its source and file an issue; do not silently hand-roll a substitute.
  4. Add inline DRG edges: `suggests: [urn:tactic:canonical-source-unification, urn:toolguide:terminology-guard]`.
- **Files**: `src/doctrine/directives/built-in/044-canonical-sources-and-unification.directive.yaml` (create new)
- **Parallel?**: No — T022/T023 can start after this.
- **Notes**: Do NOT mention `"feature branch"` or other forbidden terms in canonical voice. Directive number 044 is pre-allocated.

### Subtask T022 – Author canonical-source-unification tactic

- **Purpose**: Provide the concrete step-by-step for applying unification when a split-brain surface is found.
- **Steps**:
  1. Create `src/doctrine/tactics/built-in/canonical-source-unification.tactic.yaml`.
  2. Body (step-by-step):
     - Identify the canonical surface (the one the resolver, the CLI, or the doctrine system recognizes as authoritative).
     - Map all call sites / copies that should route through the canonical surface.
     - Route them — update references, remove duplicates.
     - Add a gate (or extend an existing gate) to enforce the canonical route going forward.
     - Do NOT simply add the same behavior to the non-canonical surface as "parity" — that preserves the split-brain.
  3. Add inline DRG edges: `requires: [urn:directive:DIRECTIVE_044]`.
- **Files**: `src/doctrine/tactics/built-in/canonical-source-unification.tactic.yaml` (create new)
- **Parallel?**: [P] Can proceed in parallel with T023 after T021 is scaffolded.

### Subtask T023 – Author terminology-guard toolguide

- **Purpose**: Describe when and how to invoke the legacy-terminology guard — the command, when to run it, what failure means, how to fix it.
- **Steps**:
  1. Create `src/doctrine/toolguides/built-in/terminology-guard.toolguide.yaml`.
  2. Follow the toolguide YAML schema (id, title, body, tool, requires/suggests/refines).
  3. `id: terminology-guard`, `tool: pytest`.
  4. Body:
     - **When to run**: before pushing any changes to `src/doctrine/` or user-facing prose.
     - **Command**: `pytest tests/architectural/test_no_legacy_terminology.py -q`
     - **What a failure means**: a forbidden term (e.g. the word `"feature"` in a non-quoted context, or `"ceremony"`) appeared in canonical prose. These terms are forbidden in the Terminology Canon.
     - **How to fix**: reword the prose to use the canonical term; do NOT add a suppression or exemption. Forbidden terms may appear *quoted-and-marked* (in code blocks, or explicitly labeled as "forbidden term: …") but never in running canonical prose.
  5. Add inline DRG edges: `requires: [urn:directive:DIRECTIVE_044]`.
- **Files**: `src/doctrine/toolguides/built-in/terminology-guard.toolguide.yaml` (create new)
- **Parallel?**: [P] Can proceed in parallel with T022 after T021 is scaffolded.
- **Notes (C-004 critical)**: This file MUST NOT use forbidden terms in canonical voice. When naming forbidden terms as examples, quote them: `"feature"`, `"ceremony"`. A C-004 failure on the terminology-guard toolguide itself would be ironic and will fail review.

### Subtask T023b – Author TERMINOLOGY_GUARD.md companion file

- **Purpose**: Built-in toolguides carry a `guide_path:` field pointing to a companion UPPERCASE markdown file (e.g. `contextive.toolguide.yaml` → `guide_path: src/doctrine/toolguides/built-in/CONTEXTIVE.md`). This companion is the human-readable guide the toolguide YAML references. `terminology-guard.toolguide.yaml` must carry `guide_path: src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md`; this subtask authors that file.
- **Steps**:
  1. Open `src/doctrine/toolguides/built-in/terminology-guard.toolguide.yaml` (authored in T023) and confirm it has a `guide_path: src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md` field. If the field is absent, add it now.
  2. Create `src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md`. This is a human-readable companion guide (Markdown, not YAML). Content should cover:
     - **Overview**: one-paragraph description of what the legacy-terminology guard does and why it exists (enforce the Terminology Canon; forbid terms like `"feature"`, `"ceremony"` in canonical prose).
     - **When to run**: before pushing any changes to `src/doctrine/` or user-facing prose.
     - **Command**:
       ```bash
       pytest tests/architectural/test_no_legacy_terminology.py -q
       ```
     - **Understanding failure output**: what a failure message looks like; where to find the offending term in the output.
     - **How to fix**: reword the prose to use the canonical term; do NOT add a suppression or exemption. Forbidden terms may appear quoted-and-marked (in code blocks, or explicitly labeled as "forbidden term: …") but not in running canonical prose.
     - **Schema note**: if the toolguide schema permits omitting `guide_path` (making the companion optional), note that clearly; in that case this file is still strongly preferred but the toolguide YAML remains valid without it.
  3. Keep the companion file concise (15-30 lines). It supplements the toolguide YAML body — it is NOT a policy document restating the entire Terminology Canon.
  4. C-004 applies: this file MUST NOT use forbidden terms in canonical voice. Named examples must be quoted-and-marked.
- **Files**: `src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md` (create new), `src/doctrine/toolguides/built-in/terminology-guard.toolguide.yaml` (add `guide_path` field if missing)
- **Parallel?**: No — must run after T023.
- **Notes**: This companion file is what the toolguide `guide_path` field resolves to. Without it, the `guide_path` reference is a dangling pointer. The schema may permit omitting `guide_path` (in which case the companion is optional but still preferred) — check the toolguide schema; if omission is valid, note it in the Activity Log and still author the companion for completeness.

### Subtask T024 – DoD verification

- **Purpose**: Run the per-conversion Definition of Done gates.
- **Steps**:
  1. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid. Note: doctor-green does NOT schema-validate new artifact YAMLs.
  2. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green. This validates the YAML schema of the three newly authored artifacts (DIRECTIVE_044, canonical-source-unification tactic, terminology-guard toolguide). Fix any failures here; do NOT defer to WP12.
  3. `pytest tests/architectural/test_no_legacy_terminology.py -q` → green. Pay particular attention to the toolguide and its companion — if either mentions forbidden terms in canonical voice it will fail.
  4. Confirm inline DRG edges present in all three artifact YAMLs.
  5. Confirm `src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md` exists (companion file for T023b) and that `terminology-guard.toolguide.yaml` carries a `guide_path:` field pointing to it (or, if the schema permits omitting `guide_path`, confirm this is noted in the Activity Log).
  6. Confirm `graph.yaml` UNCHANGED; agent-profile wiring DEFERRED to WP12.
- **Files**: No files changed — verification only.
- **Parallel?**: No — last subtask.

## Test Strategy

- `spec-kitty doctor doctrine --json` after each artifact creation.
- `pytest tests/architectural/test_no_legacy_terminology.py -q` — critical for T023 (the toolguide itself is the highest risk for C-004 violations in this WP).

## Risks & Mitigations

- **C-004 violation in the toolguide (highest risk)**: The terminology-guard toolguide is the most likely artifact in this WP to accidentally contain a forbidden term in canonical voice. Run `pytest tests/architectural/test_no_legacy_terminology.py -q` immediately after authoring T023. If it fails, the offending term is in the toolguide body — quote-and-mark it or rephrase.
- **Rule 2 misstatement**: "unification-not-parity" is a nuanced distinction. The risk is authoring it as "always prefer the canonical surface" (too vague) vs. the sharper "consolidate to ONE surface; do NOT add parity to N surfaces (parity preserves the split-brain)." The directive must name the anti-pattern explicitly and contrast it with the correct behavior.
- **Toolguide scope creep**: the toolguide describes the guard invocation (when, command, failure meaning, fix). It is NOT a policy document restating the Terminology Canon or listing all forbidden terms. If the toolguide body grows beyond ~20 lines, it has been over-authored.
- **Missing-command-is-a-gap rule clarity**: Rule 3 of DIRECTIVE_044 must distinguish between a command that is absent from the running CLI (a gap to file) and a command that is intentionally not implemented (out of scope). The directive body should describe the symptom: "documented command absent from running tool → file an upstream gap; do not silently hand-roll."

## Dependency Notes

- WP05 is parallelizable with WP02, WP04, WP06, WP07, WP08, WP10, WP11 (disjoint new files).
- WP05 enables WP12 (three new DRG nodes must appear in the single regen).

## Review Guidance

- T020 audit record in Activity Log.
- Directive 044 has all three rules stated clearly; number is 044; `enforcement: required`.
- Toolguide does NOT use forbidden terms in canonical voice; named examples are quoted-and-marked.
- `src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md` exists (companion file); `terminology-guard.toolguide.yaml` carries `guide_path:` pointing to it (or schema-permitted omission noted in Activity Log).
- `doctor doctrine --json` green; terminology guard green.
- `graph.yaml` UNCHANGED; agent-profile wiring deferred to WP12.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-07-01T06:14:46Z – system – Prompt generated via /spec-kitty.tasks
- 2026-07-01T10:05:46Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Assigned agent via action command
- 2026-07-01T10:21:35Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1724705 – Moved to for_review
- 2026-07-01T10:22:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=1847032 – Started review via action command
- 2026-07-01T10:33:18Z – user – shell_pid=1847032 – Moved to planned
- 2026-07-01T10:34:00Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1900272 – Started implementation via action command
- 2026-07-01T10:39:26Z – claude:sonnet:doctrine-daphne:implementer – shell_pid=1900272 – Cycle 1: corrected TERMINOLOGY_GUARD.md (guard is fixed-string scan, code blocks don't exempt). src scope = 4 owned files, gates green. --force: lane-branch kitty-specs drift from rebased base (guard-friction, not a src defect).
- 2026-07-01T10:40:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=1928552 – Started review via action command
- 2026-07-01T10:44:44Z – user – shell_pid=1928552 – Cycle 1: TERMINOLOGY_GUARD.md corrected; compliance suite clean
