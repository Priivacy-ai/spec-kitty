---
work_package_id: WP01
title: ADR Authoring and Registration
dependencies: []
requirement_refs:
- C-002
- C-003
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-011
- NFR-002
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Canonical Authority
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: scribe-sally
authoritative_surface: docs/adr/
create_intent: []
execution_mode: planning_artifact
model: ''
owned_files:
- docs/adr/3.x/index.md
- docs/development/3-2-page-inventory.yaml
- docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md
- docs/adr/3.x/2026-08-21-*-retire-doctrine-term-charter-is-the-canonical-vocabulary.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – ADR Authoring and Registration

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `scribe-sally`
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

- A new spec-kitty-style ADR exists in `docs/adr/3.x/` recording the terminology decision as the
  **single canonical authority** — self-sufficient: a reader with no other context can state the
  decision, the three-way distinction, surviving vocabulary, scope boundary (incl. the operator-typed
  identifier split), compatibility policy, glossary decisions, and the exact Terminology Canon line.
- `2026-07-15-1` is marked `Superseded` in its status frontmatter with a pointer to the new ADR;
  its body is byte-for-byte untouched (C-003).
- The ADR is registered: era index row + page-inventory lockfile updated by the freshen script, and
  `--check` passes.
- **Success metric**: quickstart check 3 (self-sufficiency) is passable from the ADR alone;
  quickstart check 2 (registration) passes.

---

## Context & Constraints

**Mission**: `retire-doctrine-term-01M0JMK9` — retire the user-facing term "doctrine" in favor of
"charter". This mission is **planning-only** (C-001): it records the decision and plans the
retirement; it renames nothing user-facing.

**Read before starting** (all in `kitty-specs/retire-doctrine-term-01M0JMK9/`):

- `spec.md` — FR-001..FR-011, NFRs, constraints C-001..C-005
- `plan.md` — IC-01 (this WP), Charter Check, Parallel Work Analysis
- `contracts/adr-content-contract.md` — the nine mandatory content items (your authoring checklist)
- `data-model.md` §2 — the three-way distinction definitions (charter bundle / active charter /
  inactive charter) and surviving kind vocabulary
- `research.md` — R1 (ADR conventions), R3 (glossary decisions), R4 (compatibility policy)
- `quickstart.md` — checks 2–3 are your verification surface

**Constraints to honor**:

- **C-001 (planning-only)**: no surface renames, no `src/` or agent-directory changes. The only
  files this WP touches are the new ADR, `2026-07-15-1`'s status frontmatter, and the two
  registration surfaces (index + lockfile) via the freshen script.
- **C-002**: registration goes through `python -m scripts.docs.freshen_adr_inventory` (module form)
  — never hand-edit `docs/adr/3.x/index.md` or the lockfile.
- **C-003**: `2026-07-15-1` is amended in its **status frontmatter only**. The body — including any
  historical use of the word "doctrine" — is a legacy snapshot and stays byte-for-byte untouched.
- **Anti-goals** (content contract): do not pin versions in the scope statement; do not mark any
  ADR other than `2026-07-15-1` as superseded; do not re-decide the operator-approved shape.

**Architectural decisions to honor**:

- The ADR **supersedes the terminology portion** of `2026-07-15-1` (doctrine-offers /
  charter-activates / runtime-consumes) and **reconciles** with `2026-07-18-1` (charter cascade) —
  state both relationships explicitly.
- The ADR is the root of authority for everything downstream: WP02's classification rules,
  WP03's guard-arming intent (content-contract item 9), and M1's verbatim execution all cite it.

---

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/retire-doctrine-term; completed changes must merge back into feat/retire-doctrine-term.
- **Planning base branch**: `feat/retire-doctrine-term`
- **Merge target branch**: `feat/retire-doctrine-term`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T001 – Author the new ADR with all nine mandatory content items

- **Purpose**: The ADR is the single canonical authority for the terminology decision (FR-001).
  Every downstream artifact — inventory, methodology, stacked plan, and the M1 mission itself —
  cites it. It must be self-sufficient (NFR-002): readable with zero other context.
- **Steps**:
  1. Verify the next free ADR number: `ls docs/adr/3.x/ | sort` — latest existing is
     `2026-08-20-1`, so the new file is
     `docs/adr/3.x/2026-08-21-N-retire-doctrine-term-charter-is-the-canonical-vocabulary.md`
     with N = 1 unless a `2026-08-21-*` file already exists (re-check at creation time).
  2. Copy the structure from `docs/architecture/adr-template.md` (spec-kitty ADR style: status
     frontmatter, context, decision, consequences). Status: `Accepted` (the operator approved the
     decision; this ADR records it — research R1).
  3. Write the nine mandatory content items, in this order (checklist from
     `contracts/adr-content-contract.md`):
     1. **The decision** (FR-001): "charter" is the canonical user-facing term for what was called
        "doctrine"; "doctrine" is retired from all user-facing surfaces. State it in one paragraph,
        unambiguously.
     2. **The three-way distinction** (FR-002): define *charter bundle* (the pack of doctrine
        artifacts shipped/installed), *active charter* (what is activated in a project's config),
        and *inactive charter* (installed but not activated) — using the definitions from
        `data-model.md` §2. Include an explicit disambiguation note: the Python package
        `src/charter/` is an internal identifier (X1, out of scope) and unrelated to the
        user-facing term.
     3. **Surviving kind vocabulary** (FR-003): the artifact kinds that keep their names —
        `directive`, `tactic`, `styleguide`, `toolguide`, `procedure`, `paradigm` — plus the
        non-charter-activatable kinds (`template`, `asset`, `anti_pattern`) and the
        charter-activatable vocabulary tokens (agent profile, glossary pack, mission step contract).
        Source: `data-model.md` §2 and the AGENTS.md kind-vocabulary table.
     4. **Scope boundary + operator-typed identifier split** (FR-004): user-facing surfaces are in
        scope; internal identifiers (`src/` code, module names, function names) are out of scope
        (C-005). Then the operator-typed split, stated explicitly: **skill names are in scope and
        get hidden aliases** (e.g. `spk-doctrine-*` → `spk-charter-*`); **profile IDs and directive
        IDs are out of scope as a named exception** (they are operator-typed identifiers, not
        user-facing prose). This split was folded in from the post-plan coverage squad (HIGH
        finding) — do not leave it implicit.
     5. **Compatibility policy** (FR-005): during 3.x, old skill names remain as **hidden aliases
        that emit a deprecation warning**; by 4.0 the old names are **gone** (no alias, no
        warning — removal). No version pins in the scope statement.
     6. **Relationship to prior ADRs**: supersedes the terminology portion of
        `2026-07-15-1` (doctrine-offers / charter-activates / runtime-consumes); reconciles with
        `2026-07-18-1` (charter cascade). Name both with their filenames.
     7. **FR-011 glossary decisions**: record the four sub-decisions from `research.md` R3 —
        (a) which glossary entries are renamed, (b) which gain "doctrine" as a legacy alias with a
        deprecation note, (c) the exact Terminology Canon line text M1 will add to AGENTS.md
        verbatim, (d) the legacy-snapshot marking rule for historical artifacts. M1 must be able to
        *execute* these, not re-decide them (FR-010).
     8. **The exact Terminology Canon line** for M1 to add verbatim — quote it in a code block so
        there is zero ambiguity about wording.
     9. **Guard-arming intent** (C-004): state that the terminology guard
        (`tests/architectural/test_no_legacy_terminology.py`) will be armed in M1 with a
        file-level frozen exemption baseline, and that the detailed design lives in this mission's
        `methodology.md` (WP03). The ADR carries the *intent*; methodology carries the *design*.
  4. Keep the ADR tight: decision + rationale, not a restatement of the whole spec. Target
     ~150–250 lines.
- **Files**: create `docs/adr/3.x/2026-08-21-N-retire-doctrine-term-charter-is-the-canonical-vocabulary.md`
  (N per step 1). Read-only inputs: `docs/architecture/adr-template.md`,
  `contracts/adr-content-contract.md`, `data-model.md`, `research.md`.
- **Parallel?**: No — T002's pointer line needs this file's final name.
- **Notes**: If any of the nine items turns out to be under-determined by the mission artifacts,
  STOP and report it as an open item — do not invent a decision (FR-010 depends on the ADR fixing
  everything M1 needs).


### Subtask T002 – Amend 2026-07-15-1 status frontmatter (Superseded + pointer)

- **Purpose**: The old ADR's terminology framing (doctrine-offers / charter-activates /
  runtime-consumes) is superseded by the new ADR. Marking it keeps the ADR corpus honest — a
  reader must not find two conflicting authorities.
- **Steps**:
  1. Open `docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md`.
  2. In the **status frontmatter only**: change `Proposed` → `Superseded` and add a pointer line
     to the new ADR's filename (the final name from T001). Follow the frontmatter conventions of
     neighboring ADRs in `docs/adr/3.x/` (check how other superseded ADRs record their pointer —
     e.g. a `superseded_by:` field if the convention exists, otherwise a note line in the
     frontmatter).
  3. **Do not touch the body.** Every byte after the closing frontmatter delimiter stays exactly as
     is — including historical uses of "doctrine" (C-003: legacy snapshot).
  4. Verify: `git diff docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md`
     must show changes **only** inside the frontmatter block. If any body line appears in the diff,
     revert and redo.
- **Files**: `docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md`
  (frontmatter only).
- **Parallel?**: No — needs T001's final filename.
- **Notes**: Do NOT mark any other ADR superseded (anti-goal). `2026-07-18-1` is *reconciled*, not
  superseded — it stays at its current status.

### Subtask T003 – Register the ADR via the freshen script and verify with --check

- **Purpose**: The docs-freshness CI gate requires every ADR to be registered in the era index and
  the page-inventory lockfile. Hand-editing either surface is prohibited (C-002) — the canonical
  script owns both.
- **Steps**:
  1. Run the freshen script in module form from the repo root:
     ```bash
     python -m scripts.docs.freshen_adr_inventory
     ```
  2. Inspect the diff it produces: `docs/adr/3.x/index.md` (new era-index row for the new ADR) and
     `docs/development/3-2-page-inventory.yaml` (lockfile entry). Both changes come from the
     script — do not hand-edit either file. If the script also touches unrelated entries, review
     why before keeping them (stale lockfile from prior work is possible; keep only what the new
     ADR requires unless the script's own logic demands more).
  3. Verify: `python -m scripts.docs.freshen_adr_inventory --check` exits clean (no drift).
- **Files**: `docs/adr/3.x/index.md`, `docs/development/3-2-page-inventory.yaml` (script-owned).
- **Parallel?**: No — needs T001's file on disk.
- **Notes**: If the script fails or reports unexpected drift, do not work around it by hand-editing
  — report the failure (charter: trace the source and file an upstream gap; never improvise a
  substitute).


### Subtask T004 – Self-sufficiency pre-check + frontmatter-only diff verification

- **Purpose**: Catch NFR-002 (self-sufficiency) and C-003 (frontmatter-only amendment) failures
  before review, when they are cheap to fix. WP05 runs the *independent* pass; this is the author's
  own pre-check.
- **Steps**:
  1. Walk `contracts/adr-content-contract.md`'s nine-item checklist against the finished ADR. For
     each item, confirm it is present and unambiguous. Mark any gap and fix it in place.
  2. Self-sufficiency dry run (quickstart check 3, author version): read **only** the new ADR and
     answer the six questions — (1) What is the decision? (2) What are the three distinct things
     "charter" refers to, and how do they differ? (3) Which artifact kinds survive unchanged?
     (4) What is in scope vs out of scope, including the operator-typed identifier split?
     (5) What happens to old skill names in 3.x and by 4.0? (6) What exact Terminology Canon line
     does M1 add to AGENTS.md? If any answer requires consulting another file, the ADR is not
     self-sufficient — fix it.
  3. Re-verify T002's constraint: `git diff` on the old ADR shows frontmatter-only changes.
  4. Re-run `python -m scripts.docs.freshen_adr_inventory --check` — still clean after all edits.
- **Files**: none new (verification only).
- **Parallel?**: No — runs after T001–T003.
- **Notes**: This pre-check does not replace WP05's independent reviewer pass (Standing Order #8:
  reviewer ≠ implementer). It only keeps the author's own bar honest.

---

## Verification (no new tests — docs-only mission, C-001)

This WP writes no code and adds no tests. Targeted verification surface:

```bash
# Registration clean (quickstart check 2):
python -m scripts.docs.freshen_adr_inventory --check

# Old ADR diff is frontmatter-only (C-003):
git diff docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md

# Guard still green (this WP must not trip the terminology guard):
pytest tests/architectural/test_no_legacy_terminology.py -q
```

The guard check matters: the new ADR's *body* discusses the word "doctrine" as a subject. If the
guard scans `docs/` and flags the new ADR, that is a real finding — report it (the guard's
exclusion rules are M1's concern to arm, not this WP's to work around). Do NOT add the new ADR to
any exclusion list in this mission.

---

## Risks & Mitigations

- **Self-sufficiency failure (NFR-002/SC-001)** → nine-item checklist at authoring time (T001) +
  six-question dry run (T004); WP05's independent pass is the final gate.
- **Old ADR body drift (C-003)** → T002 step 4 and T004 step 3 both verify via `git diff`; a body
  line in the diff is an automatic redo.
- **Freshen gate trip (docs-freshness CI)** → registration only via the canonical script (C-002);
  `--check` after every edit round.
- **Guard flags the new ADR's discussion of "doctrine"** → expected possible finding; report, do
  not exclude (guard arming is M1's design per methodology.md).

---

## Review Guidance

- Reviewer checkpoints for `/spec-kitty.review`:
  1. All nine content-contract items present and unambiguous (walk the checklist).
  2. The operator-typed identifier split is stated explicitly (skill names in scope with aliases;
     profile IDs + directive IDs out of scope as a named exception).
  3. The Terminology Canon line is quoted verbatim in a code block — M1 will copy it exactly.
  4. Old ADR diff is frontmatter-only; body byte-for-byte untouched.
  5. Index + lockfile changes came from the freshen script; `--check` clean.
  6. No anti-goal violations: no surface renames, no version pins in scope, no other ADR
     superseded.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).
> Append new entries at the END. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
> (timestamp = current UTC via `date -u "+%Y-%m-%dT%H:%M:%SZ"`).

- 2026-08-21T00:00:00Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP01 --to <status>` to change WP status.
