---
work_package_id: WP02
title: Decision record and README
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-006
- NFR-001
- C-001
planning_base_branch: kitty/mission-sk-skills-static-conformance
merge_target_branch: kitty/mission-sk-skills-static-conformance
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-sk-skills-static-conformance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-sk-skills-static-conformance unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
history:
- timestamp: '2026-07-26T23:20:00Z'
  event: created
  by: /spec-kitty.tasks-outline (planner-priti)
agent_profile: curator-carla
authoritative_surface: conformance/
create_intent:
- conformance/DECISIONS.md
- conformance/README.md
execution_mode: code_change
model: ''
owned_files:
- conformance/DECISIONS.md
- conformance/README.md
role: curator
tags: []
tracker_refs: []
---

# WP02 — Decision record and README

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter, and behave according to its guidance before parsing the rest of
this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the
best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Author `conformance/DECISIONS.md` (the programme's D1–D5 decision record,
with every `src/cli/index.ts` citation re-derived against muster's exact
`v1.1.0` tag) and `conformance/README.md` (local invocation, the two-step
cache-warm-then-offline procedure, the pinned muster version, and the two
documented latent muster gaps). Both are pure documentation under
`conformance/**` — no code, no `src/doctrine/**` change, no muster change.

**This WP has a hold-open condition** (see Subtask T010): its prose may be
authored in full now, but it cannot be marked done/approved until a real
GitHub Actions run of `.github/workflows/conformance.yml` (WP03's deliverable,
a different lane) exists to supply the CI `run_id` and wall-clock minutes for
the README's timing entry. This is a documented plan.md decision, not an
oversight — do not invent or estimate a number to close it early.

## Context (read first)

- Spec: `kitty-specs/sk-skills-static-conformance-01KYG7GE/spec.md`
  — FR-004, FR-006, NFR-001; Acceptance Scenarios 4, 5, 10; Dependencies &
  Assumptions ("Citation drift" paragraph)
- Plan: `kitty-specs/sk-skills-static-conformance-01KYG7GE/plan.md`
  — IC-04, IC-05; Work-Package Outline's WP02 section (intra-WP order and
  hold-open condition, verbatim)
- Research: `kitty-specs/sk-skills-static-conformance-01KYG7GE/research.md`
  — §2 (citation re-derivation, the verified mapping table — this is your
  starting point, already double-checked once), §7 (CI timing,
  measured-not-asserted policy)
- Data model: `kitty-specs/sk-skills-static-conformance-01KYG7GE/data-model.md`
  — `DecisionRecordEntry`, Invariants Summary (citation-resolves-against-tag
  row, CI-wall-clock-measured row)
- Mission seed: `gh issue view 22 --repo MOES-Media/spec-kitty` §11 — the
  full D1–D5 text (persona adapter vs. projector; the behavioral-endpoint
  seam; rule-extraction authoring; mission placement across repos; the
  rubric surface), each with its evidence and recommendation. Carry this
  **verbatim in substance**, not paraphrased down to a summary.

**Hard rules for the whole WP**:

1. Touch ONLY the two files in `owned_files` — this WP's share of **C-001**
   (no spec-kitty runtime code changes).
2. **Intra-WP order is binding**: `conformance/DECISIONS.md` must be
   committed before `conformance/README.md` is authored — the README
   documents facts DECISIONS.md establishes (the pinned version, the
   manifest's shape, the completeness check's existence, the decision
   record's own location). Do T008 to completion and commit before starting
   T009.
3. Every `src/cli/index.ts` citation in `DECISIONS.md` must resolve against
   the pinned `v1.1.0` **git tag** in the muster repository
   (`/home/jeroennouws/dev/garrison-hq/muster`), not muster's current HEAD.
   research.md §2 already re-derived and verified these four:
   - Manifest-relative path resolution (D4's rationale, FR-001):
     `src/cli/index.ts:993` (was cited as `:1316` against HEAD)
   - Static case pass/fail rule (FR-005): `src/cli/index.ts:956` (was `:1279`)
   - Bare-cast manifest parsing, no schema validation (FR-006 gap):
     `src/cli/index.ts:996` (was `:1319`)
   - Behavioral cases unconditionally skipped (correction #4):
     `src/cli/index.ts:1010` (was `:1330-1334`)
   `src/adapters/skills/schema.ts:18-33` and
   `src/adapters/skills/validate.ts:18-24` citations are confirmed
   byte-identical at `v1.1.0` and carry over unchanged. T007 below is a
   one-more-time confirmation of this table (tags are immutable — this is
   not new research), not a re-derivation from scratch.
4. NFR-001 is **measured, never asserted**: no placeholder number, no
   estimated ceiling, no invented `run_id` may be committed anywhere in
   `README.md`. If the real CI run has not happened yet when T008/T009 are
   authored, leave the timing entry as an explicit, visible TODO (e.g. a
   table row reading `TBD — pending first real conformance.yml run`) rather
   than omitting the row or guessing a value.

## Subtasks

### T007 — Re-confirm the citation re-derivation table (binding constraint 4)

**Purpose**: One more check against the immutable `v1.1.0` tag before it is
committed into a decision record, per plan.md's IC-04 sequencing note.

**Steps**:
1. In `/home/jeroennouws/dev/garrison-hq/muster`, run
   `git rev-parse v1.1.0` and confirm it still resolves (tags are immutable,
   so this should be unchanged from research.md §2's `6bdb070`).
2. Spot-check each of the four re-derived lines in research.md §2 against
   `git show v1.1.0:src/cli/index.ts` at the stated line numbers (993, 956,
   996, 1010) — confirm the quoted content still matches.
3. Confirm no additional `src/cli/index.ts` citation exists anywhere in the
   D1–D5 text beyond these four (D2's citations reference
   `src/cli/index.ts:1367-1444` and `:245-248,1610` — re-derive these two
   against `v1.1.0` as well if you are transcribing D2's evidence verbatim;
   `src/crosslayer/composition.ts`, `src/adapters/rfc1/schema.json`,
   `src/adapters/openclaw-sop/manifest.ts`, and
   `src/adapters/memory-utilization/index.ts` citations are outside the
   HEAD-vs-tag drift's known scope per research.md §2 but were not
   individually spot-checked there — spot-check any additional
   `src/cli/index.ts` line you find before committing it).

**Files**: none (verification only).
**Validation**: work log records the confirmed tag SHA and confirms all
`src/cli/index.ts` citations to be used in T008 resolve against it.

---

### T008 — Author `conformance/DECISIONS.md` (IC-04, FR-004)

**Purpose**: Commit the programme's D1–D5 decision record as the durable,
versioned authority for why the programme is shaped the way it is.

**Steps**:
1. Create `conformance/DECISIONS.md` with one section per decision (D1–D5),
   each carrying: the decision statement, options considered, evidence (with
   file:line citations — using T007's confirmed `v1.1.0` line numbers, not
   the HEAD-computed ones from the seed issue), and the recommendation.
2. Source the D1–D5 text from `gh issue view 22 --repo MOES-Media/spec-kitty`
   §11 (or the programme plan it was drawn from) — carry it **verbatim in
   substance**: full evidence bullets, the "what would change my mind"
   closing note for each decision where present, not a compressed summary.
3. Replace every `src/cli/index.ts:1316`, `:1279`, `:1319`, `:1330-1334`
   citation with T007's confirmed `v1.1.0`-exact line numbers (993, 956, 996,
   1010 respectively). Leave `src/adapters/skills/*`,
   `src/crosslayer/composition.ts`, `src/adapters/rfc1/schema.json`,
   `src/adapters/openclaw-sop/manifest.ts`, and
   `src/adapters/memory-utilization/index.ts` citations as-is unless T007
   found drift.
4. Add a short header noting this file is the programme's single canonical
   decision record for the muster ⇄ spec-kitty agent-conformance programme,
   and that citations are pinned against muster `v1.1.0`.
5. Commit this file before starting T009.

**Files**: `conformance/DECISIONS.md` (new).
**Validation**: all five decisions present with evidence and recommendation;
every `src/cli/index.ts` citation matches T007's confirmed table; the file is
committed as its own step before README authoring begins.

---

### T009 — Author `conformance/README.md` (IC-05, FR-006)

**Purpose**: Document local invocation, the two-step procedure, the pinned
version, and the two known muster gaps — everything a contributor needs
before opening a PR.

**Preconditions**: T008 committed.

**Steps**:
1. Create `conformance/README.md` covering:
   - The exact local pre-PR command (quickstart.md §5):
     ```sh
     npx --offline @garrison-hq/muster@1.1.0 skills run conformance/skills/manifest.yaml \
       && node conformance/scripts/check-manifest-completeness.mjs \
       && echo "conformance: both checks green"
     ```
   - The two-step cache-warm-then-offline-run procedure (quickstart.md §1):
     `npm install --no-save @garrison-hq/muster@1.1.0` (network enabled,
     one-time) **or** a pinned `devDependency` restored via `npm ci`, then the
     network-disabled `skills run` invocation.
   - The pinned muster version in use: `1.1.0` (exact, never a range).
   - The two documented latent muster gaps, stated plainly (not fixed here,
     per the scope guard):
     1. The manifest is parsed with a bare TypeScript cast — no Ajv/schema
        validation at runtime (`src/cli/index.ts:996` at `v1.1.0`).
     2. `expectations.violations` is never compared by muster — only
        `expectations.ok` is (`src/cli/index.ts:956` at `v1.1.0`); a
        populated `violations:` list in the manifest is documentation only.
   - A link/reference to `conformance/DECISIONS.md` as the programme's
     decision record.
   - A CI timing section with a table row for `run_id` and wall-clock
     minutes, explicitly marked `TBD — pending first real conformance.yml
     run` if T010 has not yet completed. **Never** a guessed number.
2. Do not assert a numeric CI-latency ceiling anywhere — NFR-001 is
   measured, not asserted (hard rule 4 above).

**Files**: `conformance/README.md` (new).
**Validation**: contains the exact local command, the two-step procedure with
both alternatives, the pinned version string `1.1.0`, both known gaps stated
plainly, and either a real timing entry (if T010 is already satisfiable) or
an explicit `TBD` placeholder — never a blank row and never an invented
number.

---

### T010 — Hold-open gate: fill in the real CI timing entry

**Purpose**: Close NFR-001's measured-not-asserted obligation with a real
number, once one exists.

**This subtask is a Definition-of-Done gate, not a file-ownership dependency
on WP03.** WP02 does not depend on WP03 in `wps.yaml` — lane-b (WP03) starts
and can complete independently and in parallel with WP01/WP02, exactly as
plan.md's Work-Package Outline intends. This subtask exists so that WP02's
own completion is not accidentally signed off before the number it needs is
real.

**Steps**:
1. Do not mark WP02 done/approved until a real GitHub Actions run of
   `.github/workflows/conformance.yml` (produced by WP03) has completed,
   green, on this mission's PR.
2. Once that run exists, record its exact `run_id` and actual wall-clock
   minutes in `conformance/README.md`'s timing table, replacing the `TBD`
   placeholder from T009 — mirroring the exact pattern in
   `docs/plans/testing/ci-job-timings.md` (a specific `run_id`, a specific
   minutes figure, explicitly not an asserted ceiling). The `run_id` and
   minutes recorded here MUST be byte-identical to the values WP03's T013
   recorded in its own work log — cross-reference before committing.
3. If a fork-PR-shaped run is feasible to observe, confirm in the same README
   note that the job required no secret (C-002, AC-3).
4. Commit this one-line/one-row update.

**Files**: `conformance/README.md` (amend the timing table only).
**Validation**: the timing table cites a real `run_id` and a real minutes
figure sourced from an actual GitHub Actions run — never a placeholder,
never an estimate.

## Definition of Done

- [ ] T007's citation re-confirmation recorded in the work log
- [ ] `conformance/DECISIONS.md` carries all five decisions (D1–D5) verbatim
      in substance, with evidence and recommendation, committed before
      README authoring began
- [ ] Every `src/cli/index.ts` citation in `DECISIONS.md` resolves against
      the `v1.1.0` tag exactly (993, 956, 996, 1010 for the four
      research.md §2 lines; any additional `src/cli/index.ts` citation
      individually spot-checked per T007 step 3)
- [ ] `conformance/README.md` documents the exact local command, the
      two-step cache-warm-then-offline procedure (both alternatives), the
      pinned version `1.1.0`, and both known latent muster gaps
- [ ] No numeric CI-latency ceiling is asserted anywhere in `README.md`
- [x] **Not marked done** until the CI timing table cites a real `run_id`
      and real wall-clock minutes from an actual green `conformance.yml` run
      (T010) — a `TBD` placeholder blocks final approval, it does not
      satisfy it
- [x] run_id/minutes cross-checked against WP03's T013 work-log entry for
      exact match
- [ ] No file outside `owned_files` is modified

## Risks

- **Premature closure**: the strongest risk on this WP is treating T009's
  `TBD` placeholder as "close enough" and approving before T010's real number
  exists. This is explicitly disallowed — see the hold-open condition above
  and plan.md's Verification Strategy step 4.
- **Citation transcription error**: copying line numbers from research.md §2
  into prose by hand risks a typo. Mitigated by T007's confirmation pass
  immediately before commit and by copying exact numbers rather than
  re-typing from memory.
- **Cross-WP timing dependency**: T010 depends on WP03 (a different lane)
  having a real green CI run. This is a documented mission-level sequencing
  fact (plan.md), not a `wps.yaml` dependency edge — do not add
  `WP03` to this WP's `dependencies` list; that would force lane-b to block
  lane-a's authoring start, which plan.md explicitly does not want.

## Reviewer guidance

- **Reject if** `README.md`'s CI timing table contains any number that is
  not traceable to a real, named GitHub Actions `run_id`.
- **Reject if** `DECISIONS.md` was committed after `README.md`, or in the
  same commit — the intra-WP order (DECISIONS.md first) is binding.
- **Reject if** any `src/cli/index.ts` citation in `DECISIONS.md` still shows
  a HEAD-computed line number (`1316`, `1279`, `1319`, `1330-1334`) instead
  of the `v1.1.0`-exact ones (993, 956, 996, 1010).
- **Reject if** the D1–D5 text has been compressed to a summary that drops
  the evidence bullets or the recommendation — "verbatim in substance" means
  a reviewer should not need to open the seed issue to understand any
  decision's reasoning.
- Confirm `git diff --stat` shows changes in exactly the two `owned_files`
  entries and nothing else.

Implementation command: `spec-kitty agent action implement WP02 --agent claude`
