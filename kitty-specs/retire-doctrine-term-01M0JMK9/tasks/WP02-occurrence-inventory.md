---
work_package_id: WP02
title: Occurrence Inventory — Mechanical Audit
dependencies:
- WP01
requirement_refs:
- C-003
- C-005
- FR-006
- FR-007
- NFR-001
subtasks:
- T005
- T006
- T007
- T008
phase: Phase 2 - Evidence Base
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Occurrence Inventory (Mechanical Audit)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
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

- `inventory.md` exists in the mission directory, conforming to
  `contracts/inventory-schema.md`, containing:
  - the **raw mechanical audit record** (per-file hit counts, unmodified output) at a recorded
    `base_commit`;
  - **OC-## occurrence classes** over the S1–S9 surface taxonomy — stable IDs, path patterns,
    counts, ≤3 representative examples each;
  - the **classification-out table** (X1 internal-identifier / X2 legacy-marked-historical /
    X3 quoted-data) with counts and the rule applied per row;
  - the **completeness arithmetic statement**: `total_hits = sum(OC rows) + sum(X rows)` with
    **0 unclassified** hits;
  - the **Section 5 out-of-repo deferral** (surfaces this repo cannot audit).
- **Success metric**: quickstart check 4 — a re-run of the mechanical audit finds 0 unclassified
  user-facing occurrences and the arithmetic holds (SC-002).

---

## Context & Constraints

**Mission**: `retire-doctrine-term-01M0JMK9` — planning-only (C-001). This WP builds the
evidence-based work list that every downstream rename mission (M1–M5) will execute against.

**Read before starting** (all in `kitty-specs/retire-doctrine-term-01M0JMK9/`):

- `contracts/inventory-schema.md` — the exact schema for `inventory.md` (frontmatter + 5 sections)
- `data-model.md` §1 — the S1–S9 surface taxonomy (your classification target)
- `data-model.md` §4 — the X1/X2/X3 classification-out definitions and rules
- `research.md` — R5 (audit procedure), R6 (canonical-source split: `packs/built-in/` is the
  canonical YAML source; `src/doctrine/<kind>/` is Python code), R7 (skills live at
  `src/doctrine/skills/`, 55 dirs incl. 7 `spk-doctrine-*`)
- WP01's ADR (once landed) — the scope decisions, especially the operator-typed identifier split

**Constraints to honor**:

- **NFR-001 (mechanical audit)**: the raw record is produced by commands, not by reading and
  summarizing. Evidence before conclusion — the raw per-file output is committed as-is; no
  sampling, no hand-tallies. The completeness statement's arithmetic is the pass condition.
- **String-level scope rule (OC-I3)**: scope is decided per occurrence *string*, not per file.
  User-facing strings inside `src/` are in scope (S1/S7); identifiers anywhere are X1. Worked
  example: the "Action Doctrine" heading string in
  `src/charter/context_renderers/bootstrap_text.py` is an S7 user-facing string (in scope), while
  the module path `src/charter/...` itself is an X1 identifier (out of scope).
- **C-003**: legacy-marked historical artifacts are X2, not in-scope occurrences — including
  `kitty-ops/` Op journals (immutable snapshots).
- **C-005**: internal identifiers are out of scope — the X1 class exists precisely so they are
  *recorded and excluded*, not silently ignored.

**Architectural decisions to honor**:

- The inventory is a **per-wave snapshot** (INV-I1): it records `base_commit` in frontmatter.
  Drift from concurrent catfooding is re-baselined per wave — never silently absorbed into counts.
- `assigned_mission` may be `TBD` in this inventory — WP04's assignment table finalizes it. The
  program's end state has no TBDs, but this artifact is allowed to carry them.

---

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/retire-doctrine-term; completed changes must merge back into feat/retire-doctrine-term.
- **Planning base branch**: `feat/retire-doctrine-term`
- **Merge target branch**: `feat/retire-doctrine-term`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T005 – Run the mechanical audit at the base commit; record raw hits

- **Purpose**: Produce the committed evidence that every classification decision is made against
  (NFR-001). Without this record, the inventory is an assertion; with it, it is auditable.
- **Steps**:
  1. Record the base commit: `git rev-parse HEAD` → this SHA goes into `inventory.md`
     frontmatter as `base_commit`.
  2. Enumerate tracked files: `git ls-files` (the audit covers the tracked tree, not untracked
     scratch).
  3. Run the case-insensitive per-file hit count for the term:
     ```bash
     git grep -ic 'doctrine' -- $(git ls-files) | sort -t: -k2 -rn
     ```
     (or the equivalent `git grep -ic 'doctrine'` piped through a per-file tally — record exactly
     which command form you used in the raw section). Keep **every** file with count > 0.
  4. Record the raw output unmodified in a fenced code block — file path, count, one per line.
     Do not round, truncate, or "clean up" the list. This block is the evidence of record.
  5. Compute `total_hits` = sum of all per-file counts. This number anchors the completeness
     arithmetic in T008.
- **Files**: output lands in `inventory.md` Section 2 (raw audit record) — the file itself is
  written in T008; keep the raw block in a scratch note until then.
- **Parallel?**: No — T006/T007 consume this record.
- **Notes**: If the hit volume is large, that is expected (the term is pervasive — it is the
  mission's whole reason for existing). Do not sample. If a file path contains characters that
  break naive parsing, record it verbatim and note the quirk; do not drop the row.

### Subtask T006 – Classify in-scope hits into OC-## occurrence classes (S1–S9)

- **Purpose**: Turn the raw hit list into a stable, addressable work list. OC-## IDs are what
  WP04's assignment table and the M1–M5 missions reference — they must be stable and
  unambiguous.
- **Steps**:
  1. For each file in the raw record, determine its surface class S1–S9 per `data-model.md` §1
     (e.g. S2 glossary, S5 charter bundle / AGENTS.md canon, S7 user-facing strings in `src/`,
     etc.). Use the canonical-source split (research R6/R7): `packs/built-in/` YAML is the
     canonical source surface; `src/doctrine/<kind>/` Python code is identifier territory.
  2. Group occurrences into **OC-## classes**: one class per (surface, path-pattern) pair that a
     single rename mission would plausibly handle in one pass. Assign stable IDs `OC-01`,
     `OC-02`, … in a deterministic order (surface number, then path).
  3. For each class record: ID, surface (S#), path pattern(s), hit count, and **≤3 representative
     examples** (file + line excerpt). Examples are for orientation — the count is what matters.
  4. Apply the **string-level scope rule (OC-I3)** per occurrence string: user-facing strings in
     `src/` stay in scope (S1/S7 classes); identifiers move to X1 (T007). When a file mixes both
     (e.g. `src/charter/context_renderers/bootstrap_text.py`), split its hits across the
     appropriate classes and note the split.
  5. Apply the **operator-typed identifier split** from WP01's ADR: skill names → in-scope
     classes (they get aliases); profile IDs and directive IDs → X1 with the named-exception
     rule cited.
  6. Every in-scope hit must land in exactly one OC-## class. Anything you cannot classify is an
     open item — record it, do not guess (0 unclassified is the pass condition).
- **Files**: classification table lands in `inventory.md` Section 3 (written in T008).
- **Parallel?**: No — consumes the T005 raw record.
- **Notes**: Class granularity is a judgment call, but the rule of thumb is: if two path patterns
  would be renamed by different missions or different `occurrence_map.yaml` categories, they are
  different classes. When in doubt, split finer — merging is harder to undo than splitting.


### Subtask T007 – Build the classification-out table (X1/X2/X3)

- **Purpose**: Out-of-scope hits are *recorded and excluded with a rule*, not silently ignored
  (C-005). The X table is what makes the scope boundary auditable and what keeps future waves
  from re-litigating "is this in scope?"
- **Steps**:
  1. For every hit NOT placed in an OC-## class, assign exactly one classification-out row:
     - **X1 — internal identifier**: module paths, function/class/variable names, import
       statements, `src/` code identifiers — including the operator-typed named exceptions
       (profile IDs, directive IDs) per WP01's ADR. Rule cited: C-005 + the ADR's scope boundary.
     - **X2 — legacy-marked historical**: immutable snapshots explicitly marked legacy — archived
       mission artifacts, `kitty-ops/` Op journals, historical ADR bodies (e.g. the body of
       `2026-07-15-1`). Rule cited: C-003.
     - **X3 — quoted data**: the term appearing as data being discussed/quoted (e.g. this
       mission's own spec/plan/inventory discussing "doctrine" as a subject, guard test fixtures
       that must contain the forbidden term). Rule cited: NFR-001 audit scope + guard design.
  2. For each row record: ID (X-01, X-02, …), class (X1/X2/X3), path pattern(s), hit count, the
     rule applied (with citation).
  3. Verify: every file in the T005 raw record is accounted for — its hits sum across OC rows
     and X rows to exactly the file's raw count. Any remainder is an unclassified hit → open
     item, not a rounding error.
- **Files**: X table lands in `inventory.md` Section 4 (written in T008).
- **Parallel?**: No — consumes the T005/T006 work.
- **Notes**: The guard's own test file and its fixtures are the canonical X3 case — they must
  keep containing the forbidden term or the guard is vacuous (Standing Order #5). Do not
  classify them in-scope "for completeness."

### Subtask T008 – Write inventory.md per the schema (incl. completeness arithmetic)

- **Purpose**: Assemble the evidence, classification, and exclusions into the schema-conformant
  artifact that WP03/WP04 consume and WP05 verifies.
- **Steps**:
  1. Create `kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md` following
     `contracts/inventory-schema.md` exactly:
     - **Frontmatter**: `artifact: inventory`, `mission: retire-doctrine-term-01M0JMK9`,
       `base_commit` (from T005), `generated_at`, plus any schema-required fields.
     - **Section 1 — Scope & method**: the audit command(s) used, the string-level scope rule
       (OC-I3), and a pointer to WP01's ADR for the authoritative scope decisions.
     - **Section 2 — Raw audit record**: the unmodified per-file hit output from T005 in a fenced
       code block, plus `total_hits`.
     - **Section 3 — OC-## occurrence classes**: the T006 table (ID, surface S#, path pattern(s),
       count, ≤3 examples).
     - **Section 4 — Classification-out table**: the T007 X rows (ID, class, path pattern(s),
       count, rule + citation).
     - **Section 5 — Out-of-repo surfaces**: the deferral list — surfaces this repo cannot audit
       (e.g. installed agent copies in consumer projects, SaaS UI strings if any live outside
       this repo). Each entry: surface, why it is out of reach here, which downstream mission or
       process owns it.
  2. Write the **completeness arithmetic statement**: `total_hits = sum(OC rows) + sum(X rows)`
     with the actual numbers, and `unclassified = 0`. Show the sums explicitly (a reviewer must
     be able to re-add them in seconds).
  3. Self-check against the schema: every required field present, table columns match, no
     TBD in any count (TBD is allowed only in `assigned_mission`, which WP04 finalizes).
- **Files**: create `kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md`.
- **Parallel?**: No — assembles T005–T007.
- **Notes**: Do not editorialize in the tables — counts and rules only. Rationale belongs in
  Section 1 or in WP03's methodology, not scattered through the evidence.


---

## Verification (no new tests — docs-only mission, C-001)

This WP writes no code and adds no tests. Targeted verification surface (quickstart check 4):

```bash
# Re-run the mechanical audit at the current base and compare against inventory.md:
git grep -ic 'doctrine' -- $(git ls-files) | sort -t: -k2 -rn

# Arithmetic check (re-add the tables):
#   total_hits == sum(OC row counts) + sum(X row counts), unclassified == 0
```

A reviewer re-running the audit at `base_commit` must reproduce the raw record; a re-run at a
later commit may differ (catfooding drift) — that difference is recorded per INV-I1, not
silently absorbed.

---

## Risks & Mitigations

- **Completeness circularity (NFR-001)** → the mechanical procedure is pinned: every file with
  count > 0 appears in the raw record; classification must account for every hit; the arithmetic
  statement is the pass condition. No sampling, no hand-tallies.
- **Path-level vs string-level misclassification** → OC-I3 applied per occurrence string; the
  `bootstrap_text.py` worked example (S7 in-scope heading vs X1 module path) is the reference
  case. Mixed files are split across classes with a note.
- **Count drift from concurrent catfooding** → `base_commit` recorded in frontmatter; the
  inventory is a per-wave snapshot (INV-I1). WP05 re-runs the audit and records drift explicitly.
- **Class granularity too coarse for M1–M5** → the split-finer rule of thumb (T006 step 2);
  WP04's assignment table is where granularity problems surface, and re-splitting an OC-## class
  before any mission consumes it is cheap.

---

## Review Guidance

- Reviewer checkpoints for `/spec-kitty.review`:
  1. Raw record is unmodified command output (fenced block), with the exact command(s) named in
     Section 1.
  2. Every file with count > 0 is accounted for across OC + X rows; the arithmetic statement's
     sums re-add correctly.
  3. OC-## IDs are stable and deterministic (surface, then path order); each class has ≤3
     examples.
  4. Every X row cites its rule (C-003 / C-005 / NFR-001 scope) — no unexplained exclusions.
  5. The operator-typed identifier split is applied (skill names in scope; profile IDs +
     directive IDs X1 with the named-exception citation).
  6. Section 5 deferrals name an owner for each out-of-repo surface.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).
> Append new entries at the END. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
> (timestamp = current UTC via `date -u "+%Y-%m-%dT%H:%M:%SZ"`).

- 2026-08-21T00:00:00Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP02 --to <status>` to change WP status.
