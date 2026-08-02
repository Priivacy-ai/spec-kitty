---
work_package_id: WP02
title: Run-family and rigged-impossible-control query sets
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-004
planning_base_branch: kitty/mission-skill-trigger-routing-suite-01KYVRB9
merge_target_branch: kitty/mission-skill-trigger-routing-suite-01KYVRB9
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-skill-trigger-routing-suite-01KYVRB9. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-skill-trigger-routing-suite-01KYVRB9 unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
- T014
history:
- timestamp: '2026-07-31T13:37:19Z'
  agent: planner-priti
  action: WP prompt generated via staged tasks-outline/tasks-packages
agent_profile: implementer-ivan
authoritative_surface: conformance/skills/trigger-queries/
create_intent:
- conformance/skills/trigger-queries/spk-run-next-run-family-queries.yaml
- conformance/skills/trigger-queries/spk-run-review-wp-run-family-queries.yaml
- conformance/skills/trigger-queries/spk-run-implement-review-run-family-queries.yaml
- conformance/skills/trigger-queries/rigged-impossible-control-queries.yaml
execution_mode: code_change
model: ''
owned_files:
- conformance/skills/trigger-queries/spk-run-next-run-family-queries.yaml
- conformance/skills/trigger-queries/spk-run-review-wp-run-family-queries.yaml
- conformance/skills/trigger-queries/spk-run-implement-review-run-family-queries.yaml
- conformance/skills/trigger-queries/rigged-impossible-control-queries.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Run-Family and Rigged-Impossible-Control Query Sets

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Author the 3 `*-run-family-queries.yaml` files for the run-family cluster
(`spk-run-next`, `spk-run-review-wp`, `spk-run-implement-review`) with
3-way symmetric near-miss borrowing, plus the 1
`rigged-impossible-control-queries.yaml` discrimination-control fixture
(FR-004), following muster's `examples/` pattern rather than its `fixtures/`
pattern.

## Context

Depends on WP01: this WP's three run-family files borrow should-trigger
phrases from WP01's **duplicate-pair** files for the same three skills
(`spk-run-next-duplicate-pair-queries.yaml`,
`spk-run-review-wp-duplicate-pair-queries.yaml`,
`spk-run-implement-review-duplicate-pair-queries.yaml`) — those files must
already exist and be merged before you start. Do not re-derive should-trigger
phrasing for the run-family purpose from scratch; borrow the exact strings
WP01 already wrote for each skill's duplicate-pair should-trigger set
(research.md §8).

**Why two files per skill, not one**: `spk-run-next` (etc.) is simultaneously
a duplicate-pair member (near-miss borrows from its *legacy twin*,
`spec-kitty-runtime-next`, in WP01) and a run-family member (near-miss
borrows from its *two run-family siblings*, here). Mixing both near-miss
purposes into one 8-minimum array would make a resulting near-miss trigger
ambiguous between "confused with the legacy twin" and "confused with a
run-family sibling" — this is why WP01 and this WP write two distinct files
per shared skill, never one.

### Discrimination control (IC-03, FR-004)

`rigged-impossible-control-queries.yaml` must follow muster's own
`examples/` copy of the rigged-impossible fixture pattern (Decision D-3), not
its `fixtures/` copy — the `fixtures/` copy has a known, open defect
(`github.com/garrison-hq/muster/issues/73`: its near-miss axis self-matches
the literal `ZZZCONTROL` placeholder token against a description that also
contains `ZZZCONTROL`, which over-determines `passed: false` and proves
nothing about the grader). The manifest (WP03) will substitute this case's
tool name/description with muster's `RIGGED_IMPOSSIBLE_DESCRIPTION` at run
time (research.md §4) — that substituted description contains the literal
token `ZZZCONTROL-IMPOSSIBLE`. **Never let any `nearMiss` entry in this file
contain that substring** — doing so silently reintroduces muster#73's defect
in this mission's own fixture, and no automated check in this mission catches
it (T013's own text search is the only guard).

### A note on ATDD sequencing (C-011) — same resolution as WP01

`check-twin-phrasing.mjs` (WP03's deliverable) is not available in your
worktree; WP03 depends on this WP, not the reverse. T009 below has you write
a throwaway inline triple-cross-reference check (not a committed script) to
prove your own RED→GREEN sequence, exactly as WP01's T002/T008 did for the
pair case. WP03 performs the canonical, mission-level FR-002 proof afterward
against these same real files.

## Subtask T009: ATDD RED proof (local, inline, triple-mode) — commit first

**Purpose**: Prove, before any real run-family content exists, that an
under-populated cross-reference is distinguishable from a valid one.

**Steps**:
1. Write a placeholder fixture for the triple case:
   ```sh
   cat > conformance/skills/trigger-queries/placeholder-run-family-queries.yaml <<'EOF'
   id: placeholder-run-family
   source: "docs/rubric/skills-trigger-taxonomy.md"
   threshold: 0.5
   shouldTrigger: ["a","b","c","d","e","f","g","h"]
   nearMiss: ["unrelated filler 1","unrelated filler 2","unrelated filler 3","unrelated filler 4","unrelated filler 5","unrelated filler 6","unrelated filler 7","unrelated filler 8"]
   EOF
   ```
   (8/axis so this is a twin-phrasing RED, not a shape-gate RED — it must
   fail the *cross-reference* check specifically, not the count check WP01
   already covered.)
2. Run this inline triple-cross-reference check (throwaway) and confirm it
   reports failure — there is nothing for the placeholder to borrow from:
   ```sh
   python3 -c "
   import yaml
   d = yaml.safe_load(open('conformance/skills/trigger-queries/placeholder-run-family-queries.yaml'))
   others = [
     yaml.safe_load(open('conformance/skills/trigger-queries/spk-run-review-wp-duplicate-pair-queries.yaml'))['shouldTrigger'],
     yaml.safe_load(open('conformance/skills/trigger-queries/spk-run-implement-review-duplicate-pair-queries.yaml'))['shouldTrigger'],
   ]
   missing = [o for o in others if not (set(d['nearMiss']) & set(o))]
   print(f'{len(missing)} of 2 sibling sets have no borrowed phrase (expect 2)')
   "
   ```
3. Commit this RED state as its own commit. Record the SHA via
   `spec-kitty agent tasks add-history`.

**Files**: `conformance/skills/trigger-queries/placeholder-run-family-queries.yaml` (temporary, removed in T014).
**Validation**: inline check reports both sibling borrows missing (RED).

## Subtask T010: `spk-run-next-run-family-queries.yaml`

**Purpose**: Author the run-family file for `spk-run-next`.

**Steps**:
1. Read `conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml`
   (WP01) to reuse its `shouldTrigger` set unchanged (same skill, same
   plausible invocations — only the near-miss purpose differs between the
   two files).
2. `shouldTrigger`: copy from the duplicate-pair file (or re-derive
   equivalently plausible phrases if you judge the duplicate-pair set
   insufficiently distinct for this purpose — but prefer reuse for
   consistency).
3. `nearMiss`: ≥8 entries. At least one entry byte-identical to a phrase in
   `spk-run-review-wp-duplicate-pair-queries.yaml`'s `shouldTrigger` set
   (WP01), and at least one entry byte-identical to a phrase in
   `spk-run-implement-review-duplicate-pair-queries.yaml`'s `shouldTrigger`
   set (WP01).

**Files**: `spk-run-next-run-family-queries.yaml` (new).
**Validation**: ≥8/axis; near-miss set contains ≥1 phrase from each of the
other two siblings' duplicate-pair should-trigger sets.

## Subtask T011: `spk-run-review-wp-run-family-queries.yaml`

Same procedure as T010, for `spk-run-review-wp`. Its near-miss set borrows
from `spk-run-next-duplicate-pair-queries.yaml` and
`spk-run-implement-review-duplicate-pair-queries.yaml` (both WP01).

**Files**: `spk-run-review-wp-run-family-queries.yaml` (new).
**Validation**: same pattern as T010.

## Subtask T012: `spk-run-implement-review-run-family-queries.yaml`

Same procedure as T010, for `spk-run-implement-review`. Its near-miss set
borrows from `spk-run-next-duplicate-pair-queries.yaml` and
`spk-run-review-wp-duplicate-pair-queries.yaml` (both WP01).

**Files**: `spk-run-implement-review-run-family-queries.yaml` (new).
**Validation**: same pattern as T010.

## Subtask T013: `rigged-impossible-control-queries.yaml`

**Purpose**: Author the discrimination-control query set, `examples/`
pattern (D-3), never `fixtures/` pattern
(`github.com/garrison-hq/muster/issues/73`).

**Steps**:
1. `shouldTrigger`: 8 plausible, unrelated queries (queries a reasonable
   model would not associate with any tool at all — these exist so the
   *should-trigger* axis also has real content, even though grading against
   the substituted `"rigged-impossible-control"` tool name means nothing
   should genuinely trigger it).
2. `nearMiss`: 8 topically-adjacent variants of those same 8 queries
   (paraphrases, not near-duplicates of the tool's substituted description).
3. **Verify neither axis contains the substring `ZZZCONTROL`** anywhere
   (case-sensitive, whole-file search):
   ```sh
   command grep -n "ZZZCONTROL" conformance/skills/trigger-queries/rigged-impossible-control-queries.yaml
   echo "exit code: $?"   # MUST be 1 (no match)
   ```
   If this greps a match, rewrite the offending entry — do not proceed to
   T014 with a match present.

**Files**: `rigged-impossible-control-queries.yaml` (new).
**Validation**: ≥8/axis; zero occurrences of `ZZZCONTROL`.

## Subtask T014: Local GREEN verification, triple cross-reference self-check, cleanup, commit

**Purpose**: Prove the 3 real run-family files satisfy the 3-way
cross-reference locally, remove the RED placeholder, and commit the GREEN
state.

**Steps**:
1. Remove the placeholder:
   `rm conformance/skills/trigger-queries/placeholder-run-family-queries.yaml`.
2. Run this inline triple-cross-reference self-check (throwaway, mirrors
   what `check-twin-phrasing.mjs` will do in WP03 for run-family triples —
   do not commit it):
   ```sh
   python3 -c "
   import yaml
   triple = ['spk-run-next', 'spk-run-review-wp', 'spk-run-implement-review']
   dup = {s: yaml.safe_load(open(f'conformance/skills/trigger-queries/{s}-duplicate-pair-queries.yaml')) for s in triple}
   fam = {s: yaml.safe_load(open(f'conformance/skills/trigger-queries/{s}-run-family-queries.yaml')) for s in triple}
   ok = True
   for s in triple:
       for other in triple:
           if other == s:
               continue
           if not (set(fam[s]['nearMiss']) & set(dup[other]['shouldTrigger'])):
               print(f'{s} -> {other}: no near-miss match found'); ok = False
   print('OK' if ok else 'FAIL')
   "
   ```
3. Re-run the `ZZZCONTROL` grep from T013 one more time against the final
   committed content (defense in depth).
4. Commit the 4 real files (placeholder removed) as this WP's final commit.
   Run `spec-kitty agent tasks mark-status T009 T010 T011 T012 T013 T014
   --status done`.
5. Record RED commit SHA (T009) and GREEN commit SHA (this subtask) in the
   mission work log.

**Files**: removes the placeholder; no new files (created in T010-T013).
**Validation**: triple self-check reports OK for all 3 members × 2 siblings
each; `ZZZCONTROL` grep exits 1.

## Definition of Done

- 3 `*-run-family-queries.yaml` files exist, each ≥8/axis, each near-miss set
  containing a byte-identical phrase from each of the other two siblings'
  duplicate-pair should-trigger sets (WP01's files).
- `rigged-impossible-control-queries.yaml` exists, ≥8/axis, zero occurrences
  of `ZZZCONTROL` anywhere in the file.
- The placeholder RED fixture is removed.
- RED commit SHA (T009) and GREEN commit SHA (T014) both recorded in the
  mission work log.
- `spec-kitty agent tasks mark-status` run for T009-T014.

## Risks

- **2-way instead of 3-way cross-reference** — easy to under-populate (each
  member borrows from only one sibling instead of both) — mitigated by
  T014's explicit triple self-check; WP03's `check-twin-phrasing.mjs`
  re-checks independently.
- **`ZZZCONTROL` self-match reintroduction** (muster#73) — mitigated by
  T013's and T014's explicit text searches; this is not caught by any other
  automated check in this mission, so skipping this step silently ships the
  same defect this mission exists to avoid.
- **Stale should-trigger reuse** — if WP01's duplicate-pair should-trigger
  set for a shared skill changes after this WP starts, this WP's borrowed
  near-miss phrases may go stale. Re-verify byte-identity against WP01's
  *merged* files, not a cached copy, immediately before T014's commit.

## Reviewer Guidance

- Confirm RED was committed before GREEN (C-011).
- Independently verify at least one of the three run-family near-miss sets
  against both borrowed-from duplicate-pair files (open all three, confirm
  byte-identical substrings).
- Grep the control file yourself for `ZZZCONTROL` — do not trust the WP's
  self-report alone.
- Confirm no file touches `src/doctrine/skills/**` or `kitty-specs/`.

## Implementation Command

```sh
spec-kitty agent action implement WP02 --agent claude
```

## Activity Log

- 2026-08-01T22:22:31Z – claude – T009: ATDD RED committed at 380beab8c (placeholder-run-family-queries.yaml, 8/8 axis entries — passes shape gate, fails twin-phrasing). Inline triple-cross-reference check (throwaway python3) reports 2 of 2 sibling should-trigger sets have no borrowed phrase (expect 2). Anti-vacuity: same check against a constructed valid near-miss set (borrowing from both siblings) reports 0 of 2 missing, confirming the checker is not an always-fail check.
- 2026-08-01T22:24:45Z – claude – T010-T013: authored all 3 run-family query sets (commits 4759627be, 636a6022d, 2fb21060f) plus the rigged-impossible-control set (commit 7c6b87fcd, D-3 examples/ pattern). Each run-family file's shouldTrigger reused byte-for-byte from WP01's duplicate-pair file for the same skill; near-miss borrows exactly one byte-identical phrase from each of the other two run-family siblings' duplicate-pair shouldTrigger sets. T013's control file's first-draft comments spelled out the literal placeholder token the file must avoid; the mandated whole-file grep (not axis-scoped) caught this before commit and comments were reworded to describe the defect without reproducing the token — final commit's grep exits 1 (no match).
- 2026-08-01T22:24:49Z – claude – T014: GREEN committed at 56eb74618 (placeholder removed). Triple cross-reference self-check (all 3 run-family members x 2 siblings each = 6 ordered pairs) reports OK: spk-run-next<->spk-run-review-wp, spk-run-next<->spk-run-implement-review, spk-run-review-wp<->spk-run-implement-review, all bidirectional. Mechanical shape check on all 4 owned files: shouldTrigger=8 nearMiss=8 for each (spk-run-next-run-family, spk-run-review-wp-run-family, spk-run-implement-review-run-family, rigged-impossible-control). Whole-file ZZZCONTROL grep on the control file re-run at this commit: exit 1 (no match). Anti-vacuity: triple self-check verified against an in-memory poisoned member (zero-overlap near-miss set) reporting FAIL for both its pairs, confirming the checker is not an always-pass check. RED commit was 380beab8c (T009).
