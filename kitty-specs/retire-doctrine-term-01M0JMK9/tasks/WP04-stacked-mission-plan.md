---
work_package_id: WP04
title: Stacked Mission Plan
dependencies:
- WP03
requirement_refs:
- FR-009
- FR-010
- NFR-003
subtasks:
- T013
- T014
- T015
phase: Phase 4 - Execution Stack
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: planner-priti
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Stacked Mission Plan

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `planner-priti`
- **Role**: `implementer`
- **Agent/tool**: (unset — operator assigns at dispatch)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Objectives & Success Criteria

- `stacked-plan.md` exists in the mission directory, conforming to
  `contracts/stacked-plan-schema.md`, containing:
  - **per-mission entries for M1–M6** (5 active + 1 deferred to 4.0 — the operator-approved
    shape), each with slug, purpose, inputs, outputs, `depends_on`, the OC-## classes it
    retires, `change_mode`, invariant-after, and `open_items`;
  - the **assignment table** mapping every in-scope OC-## from `inventory.md` to exactly one
    mission (or an explicit deferral with rationale) — SM-I1;
  - the **M1 spec-readiness verification** (SM-I2): M1's `open_items` is empty and its full
    spec is writable from this mission's artifacts alone.
- **Success metric**: quickstart check 6 — taking M1 (`charter-authority-flip`) and attempting
  to specify it using only this mission's artifacts requires **0 new operator decisions**
  (US4-AS3 / FR-010).

---

## Context & Constraints

**Mission**: `retire-doctrine-term-01M0JMK9` — planning-only (C-001). This WP expresses the
retirement as an executable stack of missions. The shape is **operator-approved** (decision
`01M0JWDEMKXQ5CMAE9PFEK8GF9`): 5 active + 1 deferred. Do not re-litigate granularity (IC-04
risk a).

**Read before starting** (all in `kitty-specs/retire-doctrine-term-01M0JMK9/`):

- `contracts/stacked-plan-schema.md` — the exact per-mission entry schema
- `plan.md` IC-04 + the stack table — the approved M1–M6 shape (reproduced below)
- `inventory.md` (WP02) — the OC-## classes + counts you assign
- `methodology.md` (WP03) — the ordering, invariants I0–I6, guard design, verification
  assignment your entries cite
- WP01's ADR — the vocabulary authority every mission entry references

**The approved stack shape** (from `plan.md`; slugs and purposes are fixed — you fill the
schema fields, not re-derive the shape):

| Mission | Slug | Purpose (fixed) |
|---------|------|-----------------|
| M1 | `charter-authority-flip` | glossary rewrite (FR-011) + charter-bundle update via `charter.yaml` + regeneration (+ Terminology Canon line) + guard arming (last WP, single PR). Retires docs-glossary + charter-bundle classes; arms the ratchet for all later waves. |
| M2 | `charter-cli-surface` | `spec-kitty doctrine` group (8 subcommands) + `doctor doctrine` → canonical names, hidden aliases + deprecation warnings, per-subcommand alias tests, **same-wave CI consumer updates**. Retires CLI-executable + scripted-consumer classes. |
| M3 | `charter-packs-source` | user-facing strings/titles in `packs/built-in/` (canonical source of all agent copies). Retires packs-source classes. |
| M4 | `charter-skills-artifacts` | `spk-doctrine-*` → new names + legacy alias skills during the window (old→new map recorded in M4's artifacts); agent dirs via migration/upgrade flow. Retires prompts-skills-agent-artifact classes (source: `src/doctrine/skills/`). |
| M5 | `charter-docs-prose` | `docs/` prose + root-level `AGENTS.md`; ADR titles stay legacy (C-003). Retires docs-prose + root-docs classes. |
| M6 *(deferred to 4.0)* | `charter-removal-audit` | strip aliases, run the NFR-001 zero-doctrine audit. Retires residual alias classes; verifies the 4.0 hard rule. |

**Constraints to honor**:

- **FR-010 (the sharp edge)**: M1 must be spec-ready from this mission's artifacts alone — its
  inputs (ADR, glossary gap list FR-011, bundle topology, guard design) must all be fully
  determined here. Any gap is an `open_items` entry that fails the WP (T015).
- **Bulk-edit discipline**: every rename wave M1–M5 is a `change_mode: bulk_edit` mission with
  its own scoped `occurrence_map.yaml` (8 standard categories) — recorded per mission entry.
  M1's guard-arming WP is additive code, not a rename occurrence; note that split in M1's
  entry. M6 is removal, not a rename wave (research R9).
- **SM-I3**: any mission retiring an S1/S8 class updates its scripted CI consumers in the same
  PR — recorded per mission entry (M2 is the canonical case).
- **No double assignment, no silent drop** (SC-003): every in-scope OC-## appears exactly once
  in the assignment table, or as an explicit deferral with rationale.

---

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/retire-doctrine-term; completed changes must merge back into feat/retire-doctrine-term.
- **Planning base branch**: `feat/retire-doctrine-term`
- **Merge target branch**: `feat/retire-doctrine-term`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T013 – Per-mission entries M1–M6 (all schema fields)

- **Purpose**: Turn the approved stack shape into schema-conformant entries that a future
  operator can take to `/spec-kitty.specify` one at a time, in order.
- **Steps**:
  1. For each of M1–M6, create an entry with **every** field from
     `contracts/stacked-plan-schema.md`: slug, purpose, inputs, outputs, `depends_on`,
     `retires` (OC-## class IDs), `change_mode`, invariant-after, `open_items`.
  2. Fill the fields from the mission artifacts — not from memory:
     - **inputs**: name the exact artifact + section (e.g. M1's inputs = WP01 ADR §glossary
       decisions + `inventory.md` S2/S5 rows + `methodology.md` §3 guard design). An input that
       does not exist yet is an `open_items` entry.
     - **outputs**: the surfaces changed + the verification evidence the mission must produce
       (cite `methodology.md` §4 mechanisms).
     - **depends_on**: the stack order (M1 → M2 → … → M5; M6 after all alias waves). State
       *why* each dependency exists (one clause, e.g. "M2 needs M1's armed ratchet so its
       rename cannot regress terminology").
     - **retires**: OC-## IDs from `inventory.md` — the same set you will use in T014's
       assignment table (keep them consistent; the table is the mechanical check).
     - **change_mode**: `bulk_edit` for M1–M5 (each with its own scoped
       `occurrence_map.yaml`, 8 standard categories); M6 is removal — record the mode the
       schema provides for it (research R9).
     - **invariant_after**: the I# from `methodology.md` §2 that must hold when this mission
       merges (e.g. M1 → I2: new vocabulary canonical AND guard armed, no conflict window).
     - **open_items**: anything not fully determined by this mission's artifacts. M1–M5 should
       end with **zero** open items (that is the point of FR-010); M6 may carry 4.0-timing
       items, each with rationale.
  3. Per-mission notes to include where relevant:
     - **M1**: the atomic-flip structure — glossary rewrite + bundle update + guard arming in
       ONE PR, guard-arming WP last (DIRECTIVE_048 / conflict C1). Note the split: rename
       occurrences vs additive guard code.
     - **M2**: same-wave CI consumer updates (SM-I3) — the scripted consumers of
       `spec-kitty doctrine` output must be updated in M2's PR, not later.
     - **M4**: the old→new skill-name map is recorded in M4's artifacts; legacy alias skills
       exist during the 3.x window and are stripped by M6.
     - **M5**: ADR titles stay legacy (C-003) — the rename covers prose, not historical
       artifact titles.
     - **M6**: deferred to 4.0; its spec can cite `methodology.md` §5's alias-removal
       verification verbatim.
  4. Keep entries parallel in structure — same field order, same level of detail for each
     mission (a reviewer should be able to diff M2 against M3 structurally).
- **Files**: lands in `stacked-plan.md` (file created and assembled here or in T015 — your
  choice; the artifact is complete only when all three subtasks' content is in it).
- **Parallel?**: No — consumes inventory (WP02) + methodology (WP03).
- **Notes**: If a schema field has no sensible value for a mission (e.g. M6's `change_mode`
  if the schema only models rename waves), record that as a schema gap in `open_items` with
  your proposed value — do not leave the field blank silently.


### Subtask T014 – Assignment table: every OC-## exactly once (SM-I1)

- **Purpose**: The mechanical completeness check for the whole program (SC-003). If an
  occurrence class is assigned to two missions, they will collide; if none, it silently never
  gets retired. This table is the proof that neither happens.
- **Steps**:
  1. Build the assignment table: one row per in-scope OC-## class from `inventory.md`
     (Section 3). Columns: OC-## ID, surface (S#), assigned mission (M1–M6) **or** `DEFERRED`
     with rationale, hit count (from the inventory), and a one-clause note where the assignment
     is non-obvious.
  2. Verify **exactly-once**: no OC-## ID appears in two rows; every in-scope OC-## from
     `inventory.md` has a row. Cross-check the counts: sum of assigned rows + deferred rows =
     total in-scope classes.
  3. Cross-check against T013: each mission's `retires` field lists exactly the OC-## IDs
     assigned to it in this table. Any mismatch is an error — fix the entry or the row,
     whichever is wrong against `inventory.md`.
  4. Deferrals: only M6-eligible residual alias classes may be deferred (to the 4.0 removal
     mission), and each deferral carries its rationale in the row. Deferring anything else is a
     scope decision this WP does not get to make — report it as an open item.
- **Files**: lands in `stacked-plan.md` (the assignment-table section).
- **Parallel?**: No — consumes T013's `retires` fields and the inventory.
- **Notes**: This table is what WP05's quickstart check 5 verifies mechanically. Make it
  machine-checkable: consistent IDs, no prose inside the ID columns.

### Subtask T015 – M1 spec-readiness verification (SM-I2); assemble stacked-plan.md

- **Purpose**: FR-010's end-to-end proof. If M1 cannot be specified from this mission's
  artifacts alone with zero new operator decisions, the whole planning-only strategy fails —
  M1 would become a re-decision mission.
- **Steps**:
  1. Perform the dry run: using **only** `stacked-plan.md` (M1 entry), WP01's ADR,
     `inventory.md` (S2/S5 rows), and `methodology.md` (§3 guard design, §5 alias
     verification), draft M1's spec skeleton — mission purpose, scope (which OC-## classes),
     the glossary rewrite content (from the ADR's FR-011 decisions), the bundle update
     (`charter.yaml` + regeneration), the Terminology Canon line (verbatim from the ADR), and
     the guard-arming design (from methodology §3). Do not write M1's actual spec — this is a
     readiness probe.
  2. For every element of the skeleton, mark: **determined** (cites an existing artifact
     section) or **gap** (requires a new decision). Record gaps as M1 `open_items` entries.
  3. **Pass condition**: zero gaps — M1's `open_items` is empty and every skeleton element
     cites an artifact. If any gap exists, trace it to the owning WP's artifact (ADR /
     inventory / methodology) and report which one is under-specified — do not paper over it
     with a decision made here (this WP plans the stack; it does not make M1's decisions).
  4. **Assemble `stacked-plan.md`**: create the file with frontmatter (`artifact:
     stacked-plan`, `mission: retire-doctrine-term-01M0JMK9`, `generated_at`) and sections per
     `contracts/stacked-plan-schema.md` — §1 Stack overview (the approved shape + ordering
     pointer to methodology §2), §2 Per-mission entries M1–M6 (T013), §3 Assignment table
     (T014), §4 M1 spec-readiness record (this subtask's dry-run result: determined/gap table
     + the zero-gaps statement).
- **Files**: create `kitty-specs/retire-doctrine-term-01M0JMK9/stacked-plan.md`.
- **Parallel?**: No — assembles T013/T014 and probes the whole artifact set.
- **Notes**: The dry-run record stays in the artifact (Section 4) — it is evidence for WP05's
  quickstart check 6, not throwaway scratch.


---

## Verification (no new tests — docs-only mission, C-001)

This WP writes no code and adds no tests. Targeted verification surface (quickstart checks 5–6):

- **Completeness (check 5)**: every in-scope OC-## from `inventory.md` appears exactly once in
  the assignment table (or as a deferral with rationale); each mission's `retires` field
  matches its table rows.
- **Spec-readiness (check 6)**: the Section 4 dry-run record shows every M1 skeleton element
  marked *determined* with an artifact citation; `open_items` for M1 is empty.

---

## Risks & Mitigations

- **FR-010 sharp edge — M1 not spec-ready** → T015 is an explicit dry-run gate with a recorded
  determined/gap table; any gap fails the WP and is traced to the owning artifact, not decided
  here.
- **Double assignment or silent drop of an OC-## (SC-003)** → T014's exactly-once check with
  count cross-check; deferrals restricted to M6-eligible residual alias classes with rationale.
- **Drift from the operator-approved shape** → the approved M1–M6 table is reproduced in this
  prompt as fixed context; entries fill schema fields, they do not re-derive slugs or purposes.
  Renaming a slug requires an explicit note with reason, never silent reshaping.
- **Schema gap (e.g. M6's change_mode)** → recorded as an `open_items` entry with a proposed
  value, never left blank silently.

---

## Review Guidance

- Reviewer checkpoints for `/spec-kitty.review`:
  1. All six entries carry every schema field; structure is parallel across missions.
  2. M1's entry states the atomic-flip single-PR structure with guard arming last, and the
     rename-vs-additive-code split.
  3. M2's entry records same-wave CI consumer updates (SM-I3).
  4. Assignment table: exactly-once, counts sum correctly, `retires` fields match the table.
  5. Section 4 dry-run record: zero gaps, every M1 element cited to an artifact section;
     `open_items` empty for M1–M5.
  6. No re-litigation of the approved shape (slugs/purposes match `plan.md`'s stack table).

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).
> Append new entries at the END. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
> (timestamp = current UTC via `date -u "+%Y-%m-%dT%H:%M:%SZ"`).

- 2026-08-21T00:00:00Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP04 --to <status>` to change WP status.
