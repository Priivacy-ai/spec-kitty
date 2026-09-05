---
work_package_id: WP01
title: Duplicate-pair trigger query sets
dependencies: []
requirement_refs:
- FR-001
- FR-002
planning_base_branch: kitty/mission-skill-trigger-routing-suite-01KYVRB9
merge_target_branch: kitty/mission-skill-trigger-routing-suite-01KYVRB9
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-skill-trigger-routing-suite-01KYVRB9. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-skill-trigger-routing-suite-01KYVRB9 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
history:
- timestamp: '2026-07-31T13:37:19Z'
  agent: planner-priti
  action: WP prompt generated via staged tasks-outline/tasks-packages
agent_profile: implementer-ivan
authoritative_surface: conformance/skills/trigger-queries/
create_intent:
- conformance/skills/trigger-queries/ad-hoc-profile-load-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-doctrine-profile-load-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spec-kitty-runtime-next-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spec-kitty-runtime-review-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-run-review-wp-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spec-kitty-implement-review-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-run-implement-review-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spec-kitty-git-workflow-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-admin-git-workflow-duplicate-pair-queries.yaml
execution_mode: code_change
model: ''
owned_files:
- conformance/skills/trigger-queries/ad-hoc-profile-load-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-doctrine-profile-load-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spec-kitty-runtime-next-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-run-next-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spec-kitty-runtime-review-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-run-review-wp-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spec-kitty-implement-review-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-run-implement-review-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spec-kitty-git-workflow-duplicate-pair-queries.yaml
- conformance/skills/trigger-queries/spk-admin-git-workflow-duplicate-pair-queries.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Duplicate-Pair Trigger Query Sets

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Author the 10 `conformance/skills/trigger-queries/*-duplicate-pair-queries.yaml` files — one per skill in the five legacy/spk duplicate pairs — each with ≥8 `shouldTrigger` and ≥8 `nearMiss` phrases, and each pair's near-miss set containing at least one phrase byte-identical to its twin's should-trigger set (FR-002's duplicate-pair direction).

## Context

This is the mission's foundation lane (lane-a). Nothing else in the mission can be authored correctly without these 10 files existing at their exact, final paths first: WP03's `behavioral-manifest.yaml` references every one of these paths by name (`querySetPath`), and WP02 (also lane-a, sequenced after this WP) borrows should-trigger phrases from four of these ten files for the run-family near-miss sets. **Do not rename any file after WP02 or WP03 begins** — both depend on these exact filenames.

The five pairs (`data-model.md` "Duplicate pairs"):

1. `ad-hoc-profile-load` ↔ `spk-doctrine-profile-load`
2. `spec-kitty-runtime-next` ↔ `spk-run-next`
3. `spec-kitty-runtime-review` ↔ `spk-run-review-wp`
4. `spec-kitty-implement-review` ↔ `spk-run-implement-review`
5. `spec-kitty-git-workflow` ↔ `spk-admin-git-workflow`

**Naming convention** (research.md §8): `<skill-id>-duplicate-pair-queries.yaml`, applied uniformly to all 10 files (not just the 3 skills that also have a run-family purpose file in WP02).

**File shape** (data-model.md "Trigger Query Set"):

```yaml
id: <skill-id>                 # matches the skill id under test
source: "docs/rubric/skills-trigger-taxonomy.md"
threshold: 0.5                  # shape-parity only; the manifest case's own
                                 # threshold wins at run time (research.md §1)
shouldTrigger:                  # >= 8 entries (MIN_QUERIES_PER_AXIS, trigger.ts:66)
  - "..."
nearMiss:                       # >= 8 entries; at least one entry is
                                 # byte-identical to a phrase in the twin's
                                 # shouldTrigger set (FR-002)
  - "..."
```

Each skill's real `name`/`description` frontmatter lives at
`src/doctrine/skills/<skill-id>/SKILL.md` in this repository — **read it before
writing queries** for that skill. Should-trigger phrases must plausibly invoke
that skill's actual stated purpose; near-miss phrases (other than the borrowed
twin phrase) must be topically adjacent but not the skill's own purpose.

### A note on ATDD sequencing (C-011) for this WP specifically

C-011 (charter, binding) requires a failing-first test committed before the
real content, verified RED on this WP's own first commit and GREEN on its
final commit. The mission's *canonical*, checked-in verification script for
this requirement — `conformance/scripts/check-trigger-queryset-shape.mjs` —
is **not** available to you: it is WP03's deliverable (lane-b), and WP03
depends on this WP, not the reverse. You cannot invoke a script that does not
exist yet in your own worktree.

**Resolution** (this is a task-file-level clarification, not a spec.md
change — the equivalent of the plan's own six flagged findings): Subtask T002
below has you write a small, throwaway inline assertion (not a committed
script — nothing under `conformance/scripts/**` is in this WP's
`owned_files`) that encodes the same hard-gate rule
(`shouldTrigger.length >= 8 && nearMiss.length >= 8`) directly against a
placeholder fixture, prove it fails (RED), then prove the real 10 files
satisfy it (GREEN) before your final commit. This is your **local** ATDD
proof for your own deliverable. WP03 later performs the **canonical**,
mission-level FR-001 RED→GREEN→falsification proof (quickstart.md §1) against
these same files using its own checked-in script — that is the proof that
actually discharges FR-001's stated verification command. Do not skip your
own local proof on the theory that WP03 will "really" test it later; your
local proof is what stands behind your own commit history per C-011.

## Subtask T001: Confirm DIR-012 tracker assignment

**Purpose**: DIR-012 (charter, warn-only but flagged "ACTION REQUIRED at
implement time" in `plan.md`'s Charter Check) requires the seed issue to be
assigned to the Human-in-Charge before implementation starts.

**Steps**:
1. Check whether `https://github.com/MOES-Media/spec-kitty/issues/25` is
   assigned to the Human-in-Charge (e.g. `gh issue view 25 --repo
   MOES-Media/spec-kitty --json assignees`).
2. If unassigned, assign it (or ask the Human-in-Charge to) before proceeding
   to T002. Record the outcome (assignee, or "already assigned") in this WP's
   history/activity log via `spec-kitty agent tasks add-history`.
3. Always cite this issue by its full URL
   (`https://github.com/MOES-Media/spec-kitty/issues/25`) — a bare
   hash-number shorthand triggers `discover_issue_references` verdict
   requirements at review time, so avoid that shorthand form entirely, even
   in passing mentions.

**Files**: none (process gate only).
**Validation**: assignee recorded in the work log before T002's commit.

## Subtask T002: ATDD RED proof (local, inline) — commit first

**Purpose**: Prove, before any real query-set content exists, that a
too-small query set is distinguishable from a valid one — your own
failing-first proof for this WP's deliverable (see "A note on ATDD
sequencing" above).

**Steps**:
1. `mkdir -p conformance/skills/trigger-queries` (idempotent if WP02 or a
   prior run already created it).
2. Write a placeholder fixture with only 1 entry per axis:
   ```sh
   cat > conformance/skills/trigger-queries/placeholder-queries.yaml <<'EOF'
   id: placeholder
   source: "docs/rubric/skills-trigger-taxonomy.md"
   threshold: 0.5
   shouldTrigger: ["only one query"]
   nearMiss: ["only one query"]
   EOF
   ```
3. Run this inline shape check (throwaway, not committed under
   `conformance/scripts/`) and confirm it reports failure:
   ```sh
   python3 -c "
   import yaml, sys, glob
   ok = True
   for f in glob.glob('conformance/skills/trigger-queries/*.yaml'):
       d = yaml.safe_load(open(f))
       if len(d.get('shouldTrigger', [])) < 8 or len(d.get('nearMiss', [])) < 8:
           print(f'{f}: FAIL (shouldTrigger={len(d.get(\"shouldTrigger\",[]))}, nearMiss={len(d.get(\"nearMiss\",[]))})')
           ok = False
   sys.exit(0 if ok else 1)
   "
   echo "RED exit code: \$?"   # MUST be 1
   ```
4. Commit this RED state (`placeholder-queries.yaml` + a note in the WP
   history that the RED check was run and its exit code) as its own commit.
   Record the commit SHA via `spec-kitty agent tasks add-history` — this is
   the SHA a reviewer checks RED against on `planning_base_branch`.

**Files**: `conformance/skills/trigger-queries/placeholder-queries.yaml` (temporary, removed in T008).
**Validation**: inline check exits 1, naming the placeholder file and both axes.

## Subtask T003: Pair 1 — `ad-hoc-profile-load` ↔ `spk-doctrine-profile-load`

**Purpose**: Author both files with mutual near-miss borrowing.

**Steps**:
1. Read `src/doctrine/skills/ad-hoc-profile-load/SKILL.md` and
   `src/doctrine/skills/spk-doctrine-profile-load/SKILL.md` frontmatter.
2. Write `ad-hoc-profile-load-duplicate-pair-queries.yaml`: ≥8 should-trigger
   phrases plausible for `ad-hoc-profile-load`'s stated purpose; ≥8 near-miss
   phrases, at least one byte-identical to a should-trigger phrase you are
   about to write into `spk-doctrine-profile-load-duplicate-pair-queries.yaml`.
3. Write `spk-doctrine-profile-load-duplicate-pair-queries.yaml` symmetrically:
   at least one near-miss phrase byte-identical to one of
   `ad-hoc-profile-load`'s should-trigger phrases.
4. Double-check the borrowed strings are **byte-identical** (copy-paste, not
   re-typed) — `check-twin-phrasing.mjs` (WP03) does an exact string match.

**Files**: 2 new YAML files, ~20-30 lines each.
**Validation**: both files have ≥8/axis; each contains at least one
byte-identical borrowed phrase from the other's should-trigger set.

## Subtask T004: Pair 2 — `spec-kitty-runtime-next` ↔ `spk-run-next`

Same procedure as T003 for this pair. **Note**: `spk-run-next` is also a
run-family member — WP02 will later create
`spk-run-next-run-family-queries.yaml` as a *separate* file with a different
near-miss purpose (borrowing from `spk-run-review-wp` and
`spk-run-implement-review` instead of from `spec-kitty-runtime-next`). Do not
conflate the two purposes into one file; do not let this file's near-miss set
drift toward run-family phrasing — it is duplicate-pair only.

**Files**: `spec-kitty-runtime-next-duplicate-pair-queries.yaml`,
`spk-run-next-duplicate-pair-queries.yaml`.
**Validation**: same as T003.

## Subtask T005: Pair 3 — `spec-kitty-runtime-review` ↔ `spk-run-review-wp`

Same procedure as T003. `spk-run-review-wp` is also a run-family member (see
T004's note — same caveat applies).

**Files**: `spec-kitty-runtime-review-duplicate-pair-queries.yaml`,
`spk-run-review-wp-duplicate-pair-queries.yaml`.
**Validation**: same as T003.

## Subtask T006: Pair 4 — `spec-kitty-implement-review` ↔ `spk-run-implement-review`

Same procedure as T003. `spk-run-implement-review` is also a run-family
member (same caveat as T004/T005).

**Files**: `spec-kitty-implement-review-duplicate-pair-queries.yaml`,
`spk-run-implement-review-duplicate-pair-queries.yaml`.
**Validation**: same as T003.

## Subtask T007: Pair 5 — `spec-kitty-git-workflow` ↔ `spk-admin-git-workflow`

Same procedure as T003. Neither of these two is a run-family member — no
special caveat.

**Files**: `spec-kitty-git-workflow-duplicate-pair-queries.yaml`,
`spk-admin-git-workflow-duplicate-pair-queries.yaml`.
**Validation**: same as T003.

## Subtask T008: Local GREEN verification, cross-reference self-check, cleanup, commit

**Purpose**: Prove the 10 real files satisfy the shape gate and the
cross-reference requirement locally, remove the RED placeholder, and commit
the GREEN state.

**Steps**:
1. Remove the placeholder: `rm conformance/skills/trigger-queries/placeholder-queries.yaml`.
2. Re-run T002's inline shape check against all 10 real files — confirm exit
   `0`.
3. Run this inline twin-phrasing self-check (throwaway, mirrors what
   `check-twin-phrasing.mjs` will do in WP03 — do not commit it):
   ```sh
   python3 -c "
   import yaml
   pairs = [
     ('ad-hoc-profile-load', 'spk-doctrine-profile-load'),
     ('spec-kitty-runtime-next', 'spk-run-next'),
     ('spec-kitty-runtime-review', 'spk-run-review-wp'),
     ('spec-kitty-implement-review', 'spk-run-implement-review'),
     ('spec-kitty-git-workflow', 'spk-admin-git-workflow'),
   ]
   ok = True
   for a, b in pairs:
       da = yaml.safe_load(open(f'conformance/skills/trigger-queries/{a}-duplicate-pair-queries.yaml'))
       db = yaml.safe_load(open(f'conformance/skills/trigger-queries/{b}-duplicate-pair-queries.yaml'))
       if not (set(da['nearMiss']) & set(db['shouldTrigger'])):
           print(f'{a} -> {b}: no near-miss match found'); ok = False
       if not (set(db['nearMiss']) & set(da['shouldTrigger'])):
           print(f'{b} -> {a}: no near-miss match found'); ok = False
   print('OK' if ok else 'FAIL')
   "
   ```
4. Commit the 10 real files (placeholder removed) as this WP's final commit.
   Run `spec-kitty agent tasks mark-status T001 T002 T003 T004 T005 T006 T007
   T008 --status done` to record completion in the event log.
5. Record in the mission work log: RED commit SHA (T002), GREEN commit SHA
   (this subtask), and the twin-phrasing self-check output.

**Files**: removes the placeholder; no new files (the 10 real files were
created in T003-T007).
**Validation**: inline shape check exits 0 on all 10 files; twin-phrasing
self-check reports OK for all 5 pairs.

## Definition of Done

- 10 `*-duplicate-pair-queries.yaml` files exist under
  `conformance/skills/trigger-queries/`, each with ≥8 `shouldTrigger` and ≥8
  `nearMiss` entries.
- For each of the 5 pairs, at least one near-miss phrase in each file is
  byte-identical to a should-trigger phrase in its twin's file (verified both
  directions).
- The placeholder RED fixture is removed; no residual scratch files remain.
- RED commit SHA (T002) and GREEN commit SHA (T008) are both recorded in the
  mission work log.
- `spec-kitty agent tasks mark-status` has been run for T001-T008.
- DIR-012 assignment status recorded.

## Risks

- **Asymmetric cross-reference** (A borrows from B but not vice versa) —
  mitigated by T008's explicit both-directions self-check; WP03's
  `check-twin-phrasing.mjs` re-checks this independently and will fail the
  mission-level FR-002 proof if this WP's self-check was wrong or skipped.
- **Filename drift** — WP02 and WP03 depend on these exact filenames
  (`<skill-id>-duplicate-pair-queries.yaml`). Renaming any file after this WP
  merges breaks WP03's manifest authoring silently until `skills run` fails
  to find the file.
- **Re-typed (not copied) borrowed phrases** — a phrase that is *similar but
  not byte-identical* will pass a human read but fail
  `check-twin-phrasing.mjs`'s exact string match in WP03. Always copy-paste.

## Reviewer Guidance

- Confirm RED was actually run and committed before GREEN (C-011) — check
  the two recorded commit SHAs, not just the final diff.
- Confirm all 10 files are present at the exact filenames listed in
  `owned_files` above.
- Independently spot-check at least 2 of the 5 pairs for a byte-identical
  borrowed phrase (open both files, diff the strings) rather than trusting
  the WP's own self-check output.
- Confirm no file touches anything under `src/doctrine/skills/**` (SKILL.md
  edits are out of scope for the entire mission — C-001, Scope Guard).
- Confirm `kitty-specs/` is not touched by any commit in this WP's lane.

## Implementation Command

```sh
spec-kitty agent action implement WP01 --agent claude
```

## Activity Log

- 2026-08-01T22:07:54Z – claude – T001: DIR-012 tracker check — https://github.com/MOES-Media/spec-kitty/issues/25 was unassigned at check time; assigned to MOES-Media (login resolves to Jeroen Nouws, Human-in-Charge) via gh issue edit. Confirmed via gh issue view: assignees=[MOES-Media].
- 2026-08-01T22:09:22Z – claude – T002: ATDD RED committed at 961245751943722b92fe1d9192fe7723d155f5b1 (placeholder-queries.yaml, 1 entry/axis). Inline shape check (throwaway python3, mirrors trigger.ts:403-422 MIN_QUERIES_PER_AXIS=8 gate) exits 1 against this commit, reporting shouldTrigger=1 nearMiss=1. Verified check is not vacuous: same check against a constructed 8/8 valid fixture exits 0.
- 2026-08-01T22:12:19Z – claude – T003-T007: authored all 10 duplicate-pair query sets (commits 99e05482b, be190a9ca, f3ce5263e, ce0a0dfb8, 933a4139c). Each pair locally verified: >=8/axis via inline python3 shape check, and both-direction byte-identical twin-phrase overlap via inline set-intersection self-check, one pair at a time as each was authored (pair1=8/8+8/8, pair2=8/8+8/8, pair3=8/8+8/8, pair4=8/8+8/8, pair5=9/8+8/8).
- 2026-08-01T22:13:43Z – claude – T008: GREEN committed at 748e088503a7b9f92ff56ce421c845eccabc753d (placeholder removed). Re-ran T002's inline shape check against all 10 real files at this commit: exit 0 (all files >=8/axis; spec-kitty-git-workflow has 9 shouldTrigger). Twin-phrasing self-check (both directions, all 5 pairs) exit 0: ad-hoc-profile-load<->spk-doctrine-profile-load, spec-kitty-runtime-next<->spk-run-next, spec-kitty-runtime-review<->spk-run-review-wp, spec-kitty-implement-review<->spk-run-implement-review, spec-kitty-git-workflow<->spk-admin-git-workflow. Anti-vacuity: verified both checkers against a constructed rejection case each (7-entry axis; zero-overlap poisoned pair) and confirmed exit 1 in both cases before trusting the exit-0 GREEN result. RED commit was 961245751943722b92fe1d9192fe7723d155f5b1 (T002).
