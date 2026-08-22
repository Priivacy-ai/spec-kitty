---
work_package_id: WP03
title: Ordering and Methodology Analysis
dependencies:
- WP02
requirement_refs:
- C-004
- FR-008
subtasks:
- T009
- T010
- T011
- T012
phase: Phase 3 - Methodology
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: planner-priti
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Ordering and Methodology Analysis

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

- `methodology.md` exists in the mission directory, stating **in what order and why** the
  retirement proceeds:
  - the **surface ordering** with a per-choice rationale tied to a concrete risk, and the
    invariant that must hold at each stack level (I0–I6);
  - the **terminology-guard arming design** — file-level frozen exemption baseline, shrink-only
    ratchet, self-mutation test (Standing Order #5), the stated blind spot, and string-fragment
    construction for alias tests;
  - the **per-surface verification assignment** — exactly one named mechanism per class outside
    the guard's scan roots (S5/S6/S8/S9 + S4's and S7's out-of-root portions) per C-004;
  - **catfooding conflict management** (C1–C6) plus alias introduction/removal verification and
    per-wave re-baselining (INV-I1).
- **Success metric**: quickstart check 7 — a reviewer challenges each ordering choice and finds a
  stated rationale + per-level invariant for every one (US3-AS1).

---

## Context & Constraints

**Mission**: `retire-doctrine-term-01M0JMK9` — planning-only (C-001). This WP writes the
methodology that makes the stacked plan (WP04) executable: ordering, invariants, guard design,
verification assignment, and conflict management.

**Read before starting** (all in `kitty-specs/retire-doctrine-term-01M0JMK9/`):

- `data-model.md` §5 — invariants I0–I6 and the C1–C6 conflict set (already fixed; this WP
  writes them up with rationale, not re-decides them)
- `research.md` — R2 (guard state at base), R8 (atomic authority flip / C1), R9 (M6 removal
  mission)
- `contracts/stacked-plan-schema.md` — what WP04 will consume from this methodology
- `inventory.md` (WP02) — the OC-## classes and counts your ordering rationale cites
- WP01's ADR — content-contract item 9 (guard-arming intent) is the authority this design
  elaborates

**Constraints to honor**:

- **C-004 (verification completeness)**: the guard scans `src/tests/docs` only. Every class
  outside those roots (S5/S6/S8/S9, plus the out-of-root portions of mixed-root classes S4 and
  S7 — `data-model.md` §1) needs exactly one named verification mechanism — the
  guard alone is not a complete safety net, and this WP must say what completes it.
- **Standing Order #5 (non-vacuous gates)**: the armed guard must have a concrete floor, a
  shrink-only ratchet, and a self-mutation test. A guard that can be silently weakened is not
  armed — it is decoration.
- **No re-deciding**: the shape (5 active + 1 deferred), the invariants, and the conflict set are
  operator-approved / research-fixed. This WP's job is *rationale + mechanism detail*. If you
  believe an invariant is wrong, STOP and report it as an open item — do not quietly change it.

**Architectural decisions to honor**:

- The **atomic authority flip** (research R8 / conflict C1) is the load-bearing design: glossary
  rewrite + charter-bundle update + guard arming land in **one mission/PR** (M1, with the
  guard-arming WP last) so there is no window where the old word is forbidden and the
  replacement is not yet canonical (INV-I2).
- **Guard state at base** (research R2, verified live): `_FORBIDDEN_TERMS` covers only
  ceremony + status-writing terms; `_SCAN_ROOTS` = `src/tests/docs`; exclusions are
  path-fragment based with **no per-file exemption mechanism for active surfaces**. Arming is
  new machinery, not a config tweak — the design must say what gets built.

---

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/retire-doctrine-term; completed changes must merge back into feat/retire-doctrine-term.
- **Planning base branch**: `feat/retire-doctrine-term`
- **Merge target branch**: `feat/retire-doctrine-term`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T009 – Surface ordering with per-choice rationale + invariants I0–I6

- **Purpose**: Answer "in what order, and why" (FR-008). The ordering is not a preference list —
  each step exists because an earlier step makes it safe, and each level has an invariant that
  must hold before the next begins.
- **Steps**:
  1. Write the surface ordering as a numbered sequence of stack levels, from authority (M1:
     glossary + charter bundle + guard arming — the atomic flip) through the rename waves (M2–M5,
     per-surface) to removal (M6, deferred to 4.0). Use the OC-## classes from `inventory.md`
     as the concrete content of each level.
  2. For **each** ordering choice, write a rationale paragraph tied to a concrete risk: what
     breaks if this step happened earlier/later/parallel? Examples of the risk shapes to name:
     - authority-first: renaming surfaces before the glossary/bundle is canonical means every
       wave re-decides vocabulary (FR-010 violation);
     - atomic flip: splitting glossary + bundle + guard across PRs opens the C1 conflict window
       (old word forbidden, replacement not yet canonical);
     - guard before waves: without the armed guard, each wave can regress terminology silently;
     - removal last (M6): aliases must exist and be proven unused before anything is deleted.
  3. State the invariant that must hold **at each stack level** (I0–I6 from `data-model.md` §5):
     name the invariant, what it asserts, and how it is checked (which mechanism — guard run,
     audit re-run, assignment-table check). I0 is the pre-state (base), I6 the terminal state
     (4.0, post-M6).
  4. Close with a one-paragraph "why this order is the only safe order" summary — the reviewer's
     challenge surface (US3-AS1).
- **Files**: lands in `methodology.md` Section 2 (file written incrementally; T012 assembles).
- **Parallel?**: No — the rationale cites inventory evidence (WP02) and the ADR's guard intent
  (WP01).
- **Notes**: Do not invent new invariants or reorder the fixed set — write up I0–I6 as given,
  with rationale. If an invariant's checking mechanism is under-specified in `data-model.md`,
  name the gap and propose the check as part of this section (that is mechanism detail, which
  is this WP's job).

### Subtask T010 – Guard-arming design (frozen baseline, ratchet, self-mutation test)

- **Purpose**: Elaborate WP01's ADR guard-arming intent (content-contract item 9) into a design
  M1 can implement without new decisions. The guard at base has no per-file exemption mechanism
  for active surfaces (research R2) — this design says what gets built.
- **Steps**:
  1. **File-level frozen exemption baseline**: specify the mechanism — a committed data file
     (name it, e.g. alongside the guard test) mapping exempt file paths → frozen hit counts at
     arming time. The baseline is *frozen*: it only shrinks (counts decrease as waves retire
     occurrences); growing a count or adding a file is rejected.
  2. **Shrink-only ratchet**: define the check — on each run, current per-file counts for
     baseline files must be ≤ frozen counts; any increase fails the guard with a message naming
     the file and the delta. The ratchet is what makes the baseline a ratchet, not a snapshot.
  3. **Self-mutation test** (Standing Order #5): specify the test that proves the guard is not
     vacuous — e.g. a test that (a) asserts `_FORBIDDEN_TERMS` contains the retired term,
     (b) injects a synthetic violation in a temp file under a scan root and asserts the guard
     logic flags it, (c) asserts the baseline file's checksum/shape is intact. Name each
     assertion; M1 implements them verbatim.
  4. **Stated blind spot**: the ratchet cannot see count *growth inside baseline files* beyond
     what the frozen counts allow — state this explicitly and assign it to per-wave
     re-baselining (INV-I1, T012) rather than pretending the ratchet is total.
  5. **String-fragment construction for alias tests**: during 3.x the old skill names remain as
     hidden aliases with deprecation warnings (FR-005). Specify how the guard/alias tests
     construct their probe strings from fragments (so the test file itself does not contain a
     literal forbidden term and trip its own guard) — e.g. `"doc" + "trine"` concatenation, and
     where the fragment constants live.
- **Files**: lands in `methodology.md` Section 3 (assembled in T012).
- **Parallel?**: No — cites the ordering's atomic-flip rationale (T009) and inventory counts
  (the baseline is seeded from the audit).
- **Notes**: This is a *design* section — no code in this mission (C-001). The bar is: M1's
  implementer writes the guard changes from this section alone, with zero new decisions.


### Subtask T011 – Per-surface verification assignment (S5/S6/S8/S9 + S4's and S7's out-of-root portions)

- **Purpose**: C-004 — the guard's scan roots are `src/tests/docs`; classes outside those roots
  would be unverified by the guard alone. This section assigns **exactly one named mechanism**
  to each out-of-root class so verification is complete by construction.
- **Steps**:
  1. Build the assignment table: one row per out-of-root surface class — S5, S6, S8, S9,
     plus the out-of-root portions of mixed-root classes S4 and S7 (per `data-model.md` §1
     note; cross-check which OC-## classes from `inventory.md` fall in each).
  2. For each row, name exactly one mechanism. Candidate mechanisms (choose per class; the
     choice is this WP's to make, with rationale):
     - **NFR-001 mechanical audit re-run** (the `git grep` procedure from WP02) — the default
       for prose surfaces;
     - **freshen `--check`** (docs-freshness gate) — for ADR/index/lockfile surfaces;
     - **schema conformance check** against `contracts/*.md` — for mission-artifact surfaces;
     - **per-mission occurrence-map compliance** (the bulk-edit gate's diff-compliance review) —
       for rename-wave surfaces;
     - **named independent review pass** (squad lens + operator) — for authority surfaces where
       mechanical checks cannot judge sufficiency.
  3. For each row, state: the class (S#), the OC-## classes it covers (IDs from `inventory.md`),
     the mechanism, when it runs (which stack level / which mission's merge gate), and what a
     failure blocks.
  4. Verify completeness: every OC-## class in `inventory.md` is covered by either the guard
     (in-root) or exactly one row of this table. Any class with no mechanism is a C-004
     violation — an open item, not a gap to leave.
- **Files**: lands in `methodology.md` Section 4 (assembled in T012).
- **Parallel?**: No — consumes the inventory's OC-## set (WP02).
- **Notes**: "Exactly one" is deliberate — multiple mechanisms per class blur accountability. If
  a class genuinely needs two, the table records one *primary* mechanism and notes the secondary
  as supporting (the primary is what the merge gate checks).

### Subtask T012 – Catfooding conflict management (C1–C6) + alias verification; assemble methodology.md

- **Purpose**: This repo dogfoods itself — the rename program runs while the product is in use,
  so conflicts between waves and live usage are expected. This section manages them (C1–C6 from
  `data-model.md` §5), specifies alias verification, and assembles the full artifact.
- **Steps**:
  1. Write up each conflict C1–C6: what it is, why the ordering/invariants prevent or contain
     it, and who detects it if it occurs (which mechanism from T011 or the guard). C1 is the
     atomic-flip conflict — its containment is M1's single-PR structure (T009).
  2. **Alias introduction verification** (3.x): per-subcommand tests — for each renamed skill
     command, a test that the old name still resolves (hidden alias) AND emits the deprecation
     warning. Specify: where these tests live, how they construct probe strings (T010 step 5),
     and what "per-subcommand" enumerates (the alias set from the ADR's scope boundary).
  3. **Alias removal verification** (4.0, M6): the old names are gone — verified by audit
     (mechanical re-run finds zero alias definitions) plus the per-subcommand tests inverted
     (old name now errors). M6 is deferred to 4.0; this section specifies the check so M6's spec
     can cite it (FR-010).
  4. **Per-wave re-baselining** (INV-I1): after each rename wave merges, the frozen baseline
     shrinks to the new counts and `inventory.md`'s snapshot is re-cut at the wave's merge
     commit. Specify: who triggers it (the wave mission's closeout), what artifact changes
     (baseline file + a new inventory snapshot section or successor file), and how drift is
     recorded rather than silently absorbed.
  5. **Assemble `methodology.md`**: create the file with frontmatter (`artifact: methodology`,
     `mission: retire-doctrine-term-01M0JMK9`, `generated_at`) and the four sections in order —
     §1 Scope & inputs (cites ADR + inventory), §2 Ordering & invariants (T009), §3 Guard-arming
     design (T010), §4 Verification assignment (T011), §5 Conflict management & alias
     verification (this subtask). Add a closing "reviewer challenge guide" paragraph pointing at
     the ordering-rationale section (US3-AS1's surface).
- **Files**: create `kitty-specs/retire-doctrine-term-01M0JMK9/methodology.md`.
- **Parallel?**: No — assembles T009–T011.
- **Notes**: Keep mechanism names consistent with `inventory.md` and the ADR — this is the third
  of four interlocking artifacts; terminology drift between them is exactly what the program
  exists to eliminate.


---

## Verification (no new tests — docs-only mission, C-001)

This WP writes no code and adds no tests. Targeted verification surface (quickstart check 7):

- **Invariant completeness**: I0–I6 each appear in `methodology.md` §2 with a stated assertion
  and a named checking mechanism.
- **Verification completeness (C-004)**: the §4 table has one row per out-of-root class
  (S5/S6/S8/S9 + S4's and S7's out-of-root portions), each with exactly one named mechanism;
  every OC-## class in `inventory.md` is covered by the guard or a table row.
- **Standing Order #5**: §3 contains all three elements — concrete floor (frozen baseline),
  shrink-only ratchet, self-mutation test — plus the stated blind spot.

A reviewer's challenge pass (US3-AS1): pick any ordering choice in §2 and demand the rationale;
a choice without a concrete-risk paragraph is a failed check.

---

## Risks & Mitigations

- **Guard design fails Standing Order #5 (vacuous gate)** → the three elements + blind spot are
  explicit required sections (T010 steps 1–4); review guidance checks each by name.
- **Out-of-root classes left unverified (C-004)** → T011's completeness step: every OC-## class
  covered by guard or exactly one table row; an uncovered class is a hard open item.
- **Re-deciding operator-approved content** → the "no re-deciding" constraint is stated up front;
  invariants and conflict set are written up as fixed, with gaps reported as open items rather
  than quietly changed.
- **Design too thin for M1 to implement from** → the bar is stated (T010 notes): M1's
  implementer writes the guard changes from §3 alone with zero new decisions; WP05's M1
  spec-readiness dry run (T019) is the end-to-end proof.

---

## Review Guidance

- Reviewer checkpoints for `/spec-kitty.review`:
  1. Every ordering choice in §2 has a concrete-risk rationale paragraph; the "only safe order"
     summary is present.
  2. I0–I6 all stated with assertion + checking mechanism; no invariant silently dropped or
     reordered.
  3. §3 has frozen baseline + shrink-only ratchet + self-mutation test + stated blind spot +
     string-fragment construction — all five, by name.
  4. §4 table: one row per S5/S6/S8/S9 + S4's and S7's out-of-root portions, exactly one primary
     mechanism each, OC-## coverage complete.
  5. §5 covers C1–C6, alias introduction (3.x) and removal (4.0/M6) verification, and per-wave
     re-baselining with a named trigger.
  6. Mechanism names are consistent with `inventory.md` and the ADR (no drift between
     artifacts).

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).
> Append new entries at the END. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
> (timestamp = current UTC via `date -u "+%Y-%m-%dT%H:%M:%SZ"`).

- 2026-08-21T00:00:00Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP03 --to <status>` to change WP status.
