---
work_package_id: WP05
title: Verification and Closeout
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- C-001
- C-002
- C-004
- FR-010
- FR-011
- NFR-001
- NFR-002
- NFR-003
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 5 - Verification Gate
history:
- at: '2026-08-21T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: kitty-specs/retire-doctrine-term-01M0JMK9/
create_intent:
- kitty-specs/retire-doctrine-term-01M0JMK9/verification-report.md
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/retire-doctrine-term-01M0JMK9/verification-report.md
role: reviewer
tags: []
task_type: review
tracker_refs: []
---

# Work Package Prompt: WP05 – Verification and Closeout

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `reviewer-renata`
- **Role**: `reviewer`
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

- All seven `quickstart.md` checks pass with **recorded live evidence**:
  1. guard green; 2. ADR registration clean + old-ADR diff frontmatter-only;
  3. ADR self-sufficiency (named independent reviewer); 4. mechanical audit re-run +
     inventory arithmetic; 5. stacked-plan completeness (every OC-## exactly once);
  6. M1 spec-readiness dry run (0 new decisions); 7. methodology invariant check
     (I0–I6 + one named mechanism per out-of-root class).
- `verification-report.md` exists in the mission directory: per-check command, output excerpt,
  pass/fail, timestamp — the durable merge evidence (the plan's "review evidence in the PR",
  made reviewable).
- **C-001 confirmed held**: no surface was renamed by this mission — the diff of the whole
  mission touches only the ADR pair, the two registration surfaces (script-owned), and the four
  mission artifacts.
- **Success metric**: SC-001..SC-004 all green in the report; the merge-gate summary table is
  fully pass.

---

## Context & Constraints

**Mission**: `retire-doctrine-term-01M0JMK9` — planning-only (C-001). This WP is the merge gate:
it proves SC-001..SC-004 with live evidence before the mission can merge.

**Read before starting** (all in `kitty-specs/retire-doctrine-term-01M0JMK9/`):

- `quickstart.md` — the seven-check runbook (your checklist, in order)
- `spec.md` — SC-001..SC-004 (what each check proves)
- The four deliverables under verification: the new ADR + amended `2026-07-15-1` (WP01),
  `inventory.md` (WP02), `methodology.md` (WP03), `stacked-plan.md` (WP04)
- `contracts/adr-content-contract.md` — the nine-item checklist for check 3

**Constraints to honor**:

- **Reviewer ≠ implementer (Standing Order #8)**: this WP verifies; it does not rewrite. If a
  check fails because a deliverable is wrong, the finding goes back to the owning WP (recorded
  in the report + reported to the operator) — you do not fix another WP's artifact here.
  Exception: trivial formatting fixes inside `verification-report.md` itself are yours.
- **No green-washing**: a check passes only with recorded live evidence — the actual command,
  an output excerpt (not "it passed"), and a timestamp. A pass without evidence is a failed
  check.
- **Independence for check 3**: the ADR self-sufficiency pass requires a *named independent*
  reviewer — the author of WP01 does not perform it. The report records who stated what
  (SC-001: post-implement squad lens + operator at PR review).

**Architectural decisions to honor**:

- The report is the **named home for merge evidence** — durable, in-repo, reviewable. It
  complements (does not replace) the PR description's evidence summary.
- Drift is recorded, never absorbed (INV-I1): if the audit re-run (check 4) differs from
  `inventory.md`'s base, the delta is recorded with both SHAs.

---

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/retire-doctrine-term; completed changes must merge back into feat/retire-doctrine-term.
- **Planning base branch**: `feat/retire-doctrine-term`
- **Merge target branch**: `feat/retire-doctrine-term`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T016 – Quickstart checks 1–2: guard green + ADR registration

- **Purpose**: Prove the mechanical merge gates — the terminology guard is still green (this
  mission must not have tripped it) and the ADR registration is clean.
- **Steps**:
  1. **Check 1 — guard green**: run
     ```bash
     pytest tests/architectural/test_no_legacy_terminology.py -q
     ```
     Record the command, the tail of the output (pass count / any failures), and a timestamp.
     If red: determine whether the failure is this mission's (e.g. the new ADR's body
     discussing "doctrine" — a real finding for M1's guard-arming design) or pre-existing
     (baseline-red policy: verify against the merge base before attributing). Record the
     attribution in the report either way.
  2. **Check 2 — ADR registration**: run
     ```bash
     python -m scripts.docs.freshen_adr_inventory --check
     ```
     Record command + output (must be clean). Then verify the old ADR's diff is
     frontmatter-only:
     ```bash
     git diff <base>..HEAD -- docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md
     ```
     (or `git diff` against the mission's base commit) — every changed line must be inside the
     frontmatter block. Record an excerpt showing the status change + pointer line and that no
     body lines changed.
  3. Write both results into `verification-report.md` (create the file now with frontmatter:
     `artifact: verification-report`, `mission: retire-doctrine-term-01M0JMK9`,
     `generated_at`) — one section per check: command, output excerpt, pass/fail, timestamp.
- **Files**: create `kitty-specs/retire-doctrine-term-01M0JMK9/verification-report.md`
  (checks 1–2 sections).
- **Parallel?**: No — runbook order; both checks append to the same report.
- **Notes**: These two checks are also what CI will re-run at merge — a local pass here is
  necessary but the PR's CI run is the final word; note that in the report.

### Subtask T017 – Quickstart check 3: ADR self-sufficiency (named independent reviewer)

- **Purpose**: SC-001 / NFR-002 — the ADR is self-sufficient: a reader with no other context
  can state everything downstream missions need. This is the check that cannot be done by the
  author (Standing Order #8).
- **Steps**:
  1. Identify the named independent reviewer(s): the post-implement squad lens (advisory) and
     the operator at PR review. If a squad is deployed for this mission, use its ADR-lens
     member; the operator's pass happens at PR review — coordinate so both passes are recorded.
  2. The reviewer reads **only** the new ADR (no inventory, no methodology, no plan) and
     answers the six questions:
     1. What is the decision?
     2. What are the three distinct things "charter" refers to (bundle / active / inactive),
        and how do they differ?
     3. Which artifact kinds survive unchanged, and which tokens are charter-activatable?
     4. What is in scope vs out of scope — including the operator-typed identifier split
        (skill names vs profile IDs / directive IDs)?
     5. What happens to old skill names in 3.x, and by 4.0?
     6. What exact Terminology Canon line does M1 add to AGENTS.md (verbatim)?
  3. Record in the report: reviewer name(s), each answer, and a pass/fail per question
     (fail = the answer required consulting another file or was ambiguous). Any failure is a
     finding routed back to WP01's artifact — recorded, not fixed here.
  4. Also record the nine-item content-contract checklist result (walk
     `contracts/adr-content-contract.md` against the ADR) as supporting evidence.
- **Files**: `verification-report.md` (check 3 section).
- **Parallel?**: No — the report is one file; also, this check gates nothing mechanically but
  must be complete before closeout.
- **Notes**: If the operator's pass is still pending at PR review when this WP completes,
  record the squad-lens result now and mark the operator pass as *pending with named owner* —
  do not claim SC-001 green until both are recorded.


### Subtask T018 – Quickstart check 4: audit re-run + inventory arithmetic

- **Purpose**: SC-002 / NFR-001 — the inventory is complete and reproducible: a fresh
  mechanical audit accounts for every hit, and the completeness arithmetic holds.
- **Steps**:
  1. Re-run the mechanical audit at the **current** base:
     ```bash
     git rev-parse HEAD   # current SHA (compare against inventory.md base_commit)
     git grep -ic 'doctrine' -- $(git ls-files) | sort -t: -k2 -rn
     ```
  2. Compare against `inventory.md` Section 2 (raw record at its `base_commit`):
     - If the SHAs match: the raw records must be identical. Any difference is an inventory
       error → finding routed to WP02.
     - If the SHAs differ (catfooding drift): record both SHAs and the delta (files added /
       removed / count changes) per INV-I1 — drift is recorded, never silently absorbed. The
       arithmetic check below still applies to the inventory's own base.
  3. Verify the **completeness arithmetic** in `inventory.md`: re-add the OC-## row counts and
     the X-row counts; confirm `total_hits = sum(OC) + sum(X)` and `unclassified = 0`. Record
     the re-added numbers in the report (a reviewer must be able to check your addition).
  4. Record command(s), output excerpts, the arithmetic re-addition, and pass/fail in
     `verification-report.md`.
- **Files**: `verification-report.md` (check 4 section).
- **Parallel?**: No — runbook order.
- **Notes**: Do not "fix" inventory counts here to make the arithmetic pass — if it fails,
  that is a WP02 finding. The report's job is to prove or disprove, not to repair.

### Subtask T019 – Quickstart checks 5–6: plan completeness + M1 spec-readiness dry run

- **Purpose**: SC-003 (every occurrence class assigned exactly once) and SC-004 / FR-010
  (M1 spec-ready with zero new decisions) — the two checks that make the planning-only
  strategy real.
- **Steps**:
  1. **Check 5 — stacked-plan completeness**: from `inventory.md` Section 3, take the full
     in-scope OC-## set; from `stacked-plan.md` Section 3, take the assignment table. Verify:
     - every in-scope OC-## appears exactly once (assigned or deferred-with-rationale);
     - no OC-## appears twice; no table row references an ID absent from the inventory;
     - each mission's `retires` field matches its table rows.
     Record the ID sets used and the match result in the report.
  2. **Check 6 — M1 spec-readiness dry run**: independently of WP04's Section 4 record,
     attempt the M1 spec skeleton yourself from `stacked-plan.md` (M1 entry) + ADR +
     `inventory.md` S2/S5 rows + `methodology.md` §3/§5. For each element (purpose, scope
     classes, glossary rewrite content, bundle update, Terminology Canon line, guard-arming
     design), mark determined (with citation) or gap. Compare your result against WP04's
     recorded dry run — agreement strengthens the evidence; disagreement is a finding (record
     both). Pass condition: zero gaps, M1 `open_items` empty.
  3. Record both checks in `verification-report.md` with the ID sets / element tables and
     pass/fail.
- **Files**: `verification-report.md` (checks 5–6 sections).
- **Parallel?**: No — runbook order.
- **Notes**: Your dry run is a *second opinion* on WP04's — independence matters here exactly
  as it does in check 3. If you find a gap WP04 missed, that is the highest-value finding in
  this mission (FR-010's sharp edge).


### Subtask T020 – Quickstart check 7: methodology invariant check; finalize verification-report.md

- **Purpose**: Close the loop — verify the methodology's structural completeness (US3-AS1 /
  C-004), confirm C-001 held across the whole mission, and finalize the report as the merge
  evidence.
- **Steps**:
  1. **Check 7 — methodology invariant check** against `methodology.md`:
     - I0–I6 all present in §2, each with a stated assertion and a named checking mechanism;
     - every ordering choice in §2 has a concrete-risk rationale paragraph (spot-check at
       least the atomic-flip choice and the removal-last choice in depth);
     - §3 contains all five guard-design elements by name (frozen baseline, shrink-only
       ratchet, self-mutation test, stated blind spot, string-fragment construction);
     - §4 table: one row per out-of-root class (S5/S6/S8/S9 + S4's and S7's out-of-root
       portions), exactly one primary mechanism each, and every OC-## class covered by guard or
       table row (C-004).
     Record the checklist result in the report.
  2. **C-001 confirmation**: review the mission's full diff (base commit → HEAD): it must
     touch only — the new ADR, `2026-07-15-1` (frontmatter only), the two script-owned
     registration surfaces, and the four mission artifacts (`inventory.md`,
     `methodology.md`, `stacked-plan.md`, this report). Any other changed file is a C-001
     violation → finding. Record the file list in the report.
  3. **Finalize `verification-report.md`**: add a closing summary table — one row per
     success criterion (SC-001..SC-004) mapping to its check(s), overall pass/fail, and the
     list of open findings (if any) with their routed owner (WP01–WP04). Add the merge-gate
     statement: all checks green + C-001 held ⇒ mission ready for review/merge; any open
     finding ⇒ not ready, with the blocking item named.
- **Files**: `verification-report.md` (check 7 section + summary table — the file is
  complete after this subtask).
- **Parallel?**: No — final subtask; consumes all prior check results.
- **Notes**: The report's summary table is what the operator reads at PR review — keep it to
  one screen: criterion, check, result, evidence pointer (section in this report).

---

## Verification (no new tests — docs-only mission, C-001)

This WP writes no code and adds no tests. Its own verification surface is the report itself:
every check section contains command + output excerpt + pass/fail + timestamp, and the summary
table maps SC-001..SC-004 to checks. A report section missing any of those four elements is an
incomplete check (treat as failed).

---

## Risks & Mitigations

- **Green-washing a check** → the four-element evidence rule (command, excerpt, result,
  timestamp); a pass without recorded live evidence is a failed check by definition.
- **Self-sufficiency pass run by the author (NFR-002)** → T017 requires a named independent
  reviewer; the report records who stated what. Operator pass pending ⇒ SC-001 not claimed
  green.
- **Audit drift between inventory base and verification base** → T018 records both SHAs and
  the delta (INV-I1: recorded, not absorbed); arithmetic is checked against the inventory's
  own base.
- **Fixing another WP's artifact from here (role bleed)** → findings are routed to the owning
  WP and recorded; only `verification-report.md` itself is this WP's writable surface.

---

## Review Guidance

- Reviewer checkpoints for `/spec-kitty.review` (this WP's output is the merge evidence):
  1. All seven check sections present, each with command + output excerpt + pass/fail +
     timestamp.
  2. Check 3 records a named independent reviewer (not the WP01 author); operator pass
     recorded or explicitly pending with named owner.
  3. Check 4 shows the re-added arithmetic (not just "it matches").
  4. Checks 5–6 show the actual ID sets / element tables used — reproducible by a reader.
  5. C-001 file list matches the mission diff exactly; no surface renamed anywhere.
  6. Summary table: SC-001..SC-004 each mapped to checks with overall result; open findings
     (if any) named with routed owner.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).
> Append new entries at the END. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
> (timestamp = current UTC via `date -u "+%Y-%m-%dT%H:%M:%SZ"`).

- 2026-08-21T00:00:00Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP05 --to <status>` to change WP status.
