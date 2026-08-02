---
work_package_id: WP04
title: Cadence workflow, live control proof, evidence artifact, README
dependencies:
- WP03
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
planning_base_branch: kitty/mission-skill-trigger-routing-suite-01KYVRB9
merge_target_branch: kitty/mission-skill-trigger-routing-suite-01KYVRB9
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-skill-trigger-routing-suite-01KYVRB9. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-skill-trigger-routing-suite-01KYVRB9 unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
history:
- timestamp: '2026-07-31T13:37:19Z'
  agent: planner-priti
  action: WP prompt generated via staged tasks-outline/tasks-packages
agent_profile: node-norris
authoritative_surface: conformance/skills/
create_intent:
- .github/workflows/skill-trigger-routing.yml
- conformance/skills/README.md
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/skill-trigger-routing.yml
- conformance/skills/trigger-evidence/**
- conformance/skills/README.md
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – Cadence Workflow, Live Control Proof, Evidence Artifact, README

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `node-norris`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Author the `workflow_dispatch`-only cadence workflow, run the mission's
central live-model proof (FR-004's both-condition control-discrimination
sequence, User Story 3 / SC-002), produce and commit the first real evidence
artifact (FR-005), and author `conformance/skills/README.md` (FR-006, D-1,
the `[LIMITATION]` note).

## Context

**Verified finding, not in the plan's own six flagged findings — read this
before starting T025**: `plan.md`'s Project Structure section and
`research.md` §9 both describe `conformance/skills/README.md` as "M1's
existing file" to be "extended, not replaced." This is **factually wrong** —
verified by direct listing: `conformance/skills/` today contains only
`control/` and `manifest.yaml` (plus whatever WP01/WP02/WP03 added). No
`README.md` file exists anywhere under `conformance/skills/`. The file that
actually documents M1's static suite is `conformance/README.md` (the
top-level one, one directory up) — a different path. **You are creating
`conformance/skills/README.md` fresh, not extending anything.** This does not
change what FR-006 requires (spec.md never claimed the file pre-existed —
only `plan.md`/`research.md`'s narrative framing was wrong), so this is
carried as a task-file correction, not a spec.md amendment. Do not go looking
for prior content to preserve; there is none at this path.

**This WP depends on WP03**: the workflow invokes WP03's four scripts and the
pinned manifest by path; do not start until WP03 is merged and its script
paths are confirmed stable.

### FR-004's both-condition sequencing — this mission's central proof

This is the single most important verification sequence in the entire
mission (User Story 3, SC-002). Run in this exact order; do not skip the
dead-endpoint half even though it requires deliberately breaking the
endpoint. WP03's T018 already proved `check-control-discrimination.mjs`'s
logic against **synthetic** fixtures — this subtask (T022) proves it against
**real** data from a live `MUSTER_ENDPOINT`, which is what actually discharges
FR-004/SC-002:

```sh
# (a) Healthy condition first.
export MUSTER_ENDPOINT=<real, reachable endpoint>
export MUSTER_API_KEY=<real key, from env/secret, never committed>
npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json > /tmp/report-healthy.json
node conformance/scripts/check-control-discrimination.mjs /tmp/report-healthy.json --mode healthy
echo "healthy-mode exit code: $?"   # MUST be 0: passed:false, derived runsErrored:0

# (b) Rejection proof for the healthy check: healthy-mode assertions against
#     dead-endpoint data must fail, or the script isn't actually
#     distinguishing the two conditions.
export MUSTER_ENDPOINT=http://127.0.0.1:1   # deliberately unreachable
npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json > /tmp/report-dead.json
node conformance/scripts/check-control-discrimination.mjs /tmp/report-dead.json --mode healthy
echo "healthy-mode against dead data, exit code: $?"   # MUST be 1

# (c) Dead-endpoint condition, correct mode.
node conformance/scripts/check-control-discrimination.mjs /tmp/report-dead.json --mode dead-endpoint
echo "dead-endpoint-mode exit code: $?"   # MUST be 0: passed:false, derived runsErrored>0

# (d) Rejection proof for the dead-endpoint check: the inverse of (b).
node conformance/scripts/check-control-discrimination.mjs /tmp/report-healthy.json --mode dead-endpoint
echo "dead-endpoint-mode against healthy data, exit code: $?"   # MUST be 1

# (e) Omitted-mode usage error -- must never silently default.
node conformance/scripts/check-control-discrimination.mjs /tmp/report-healthy.json
echo "no --mode, exit code: $?"   # MUST be 2

# Restore before continuing:
export MUSTER_ENDPOINT=<real, reachable endpoint>
```

**Why all five assertions matter, not just the first**: `passed: false` is
true in **both** `/tmp/report-healthy.json` and `/tmp/report-dead.json` for
the control case, by construction (research.md §2 — near-miss trivially
passes at rate 0 in both cases, should-trigger trivially fails at rate 0 in
both cases). Only the derived `runsErrored(case)` sum — computed from
`shouldTriggerAxis.queryBreakdown[].runsErrored` +
`nearMissAxis.queryBreakdown[].runsErrored`, **never** a top-level field —
distinguishes them. Proofs (b) and (d) are what actually demonstrate the
script keys off `runsErrored`, not `passed` alone; proof (e) demonstrates the
script never silently assumes a mode. All five exit codes go in the mission
work log — this sequence **is** the SC-002 evidence, not an implementation
detail to summarize away.

## Subtask T021: Author `.github/workflows/skill-trigger-routing.yml`

**Purpose**: `workflow_dispatch`-only cadence workflow (C-002), muster pinned
exactly `1.2.1` (C-003), secrets via env only.

**Steps**:
1. Trigger block: `workflow_dispatch` only. **Do not** add a `schedule:`
   trigger even by copy-pasting from another workflow in this repo —
   schedule/cron wiring is explicitly out of scope, deferred to M8
   (`garrison-hq/muster-action#2`).
2. Step order, per `contracts/verification-scripts-cli-contract.md` "CI
   wiring":
   ```yaml
   - run: node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml
   - run: node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/
   - run: npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json > /tmp/report.json
   - run: node conformance/scripts/check-control-discrimination.mjs /tmp/report.json --mode healthy
   - run: <FR-003 skip-guard one-liner, asserting at least one non-control case is not skipped>
   - run: <evidence-summarization step — build conformance/skills/trigger-evidence/<run-timestamp>.json from /tmp/report.json per data-model.md's Evidence Artifact shape>
   - run: node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/<file>.json
   ```
   The `--mode dead-endpoint` invocation is **not** a CI step — CI only ever
   runs against a real, intentionally-healthy endpoint. That half of the
   proof is a one-time, by-hand step (T022 below), recorded in the work log.
3. Secrets: `MUSTER_ENDPOINT`/`MUSTER_API_KEY` as GitHub Actions repository
   secrets, injected as env vars at run time — never written to any file in
   this repo, no `.env` created.
4. Verify C-002 with a real YAML parse (not a text grep of the `on:` block
   alone — this programme has previously shipped both directions of this
   mistake):
   ```sh
   python3 -c "
   import yaml
   d = yaml.safe_load(open('.github/workflows/skill-trigger-routing.yml'))
   on = d.get('on', d.get(True, {}))   # PyYAML 1.1 parses bare 'on:' as boolean True key
   assert 'pull_request' not in on, 'pull_request trigger present'
   print('OK: no pull_request trigger')
   "
   ```
   Then construct the rejection case in a **scratch copy** (never the
   committed file): add `pull_request:` under `on:`, confirm the assertion
   fires, discard the scratch copy.
5. Verify C-003 (muster pinned exactly `1.2.1`, no floating range):
   ```sh
   command grep -c '@garrison-hq/muster@1\.2\.1' .github/workflows/skill-trigger-routing.yml
   command grep -c '@garrison-hq/muster@\^' .github/workflows/skill-trigger-routing.yml
   echo "second grep MUST return 0"
   ```

**Files**: `.github/workflows/skill-trigger-routing.yml` (new).
**Validation**: YAML-parsed `on:` block has no `pull_request` key (and the
constructed-scratch-copy rejection case fires); exact-pin grep count matches,
range-pin grep returns 0.

## Subtask T022: Run the FR-004 live both-condition sequence

**Purpose**: Execute the five-proof sequence in this prompt's Context section
above, for real, against a real endpoint.

**Steps**:
1. Run steps (a) through (e) exactly as written in the Context section.
2. Record all five exit codes, the two report files' `passed` and derived
   `runsErrored(case)` values for the control case, in the mission work log
   via `spec-kitty agent tasks add-history`.
3. Restore `MUSTER_ENDPOINT` to the healthy value before continuing to T023.
4. A run where the control case reports `runsErrored(case) > 0` against the
   *healthy* endpoint must be treated as an infrastructure failure of the run
   (endpoint flakiness, wrong model name, etc.), not a valid "control fails
   as expected" data point — do not proceed to T023 with such a run; retry
   against a genuinely healthy endpoint first.

**Files**: none (verification only; produces `/tmp/report-healthy.json` and
`/tmp/report-dead.json` for T023 to consume).
**Validation**: all five exit codes match (0, 1, 0, 1, 2) as specified.

## Subtask T023: Evidence-artifact summarization, first committed artifact

**Purpose**: Build the evidence-summarization step (referenced but left as a
"tasks-phase implementation detail" by `plan.md`'s Component & Data Flow),
and commit the first real `conformance/skills/trigger-evidence/<run-
timestamp>.json`.

**Steps**:
1. From `/tmp/report-healthy.json` (T022's healthy capture), build the
   evidence artifact per `data-model.md`'s exact shape and
   `contracts/evidence-artifact.schema.json`: `timestamp` (ISO-8601 UTC),
   `model` (whichever model actually produced the run — read from the
   manifest or `MUSTER_MODEL` override, never hardcoded), `endpointHost`
   (`new URL(MUSTER_ENDPOINT).host` — bare host only, never the full URL or
   a credential), and per-case `id`, `isControl`, `passed`,
   `shouldTrigger`/`nearMiss` axis summaries, and the derived `runsErrored`
   (present even when `0` — NFR-003 requires this field never be omitted).
2. This can be a small standalone Node script (your choice whether to check
   it in under `conformance/scripts/` as a fifth script or inline it into the
   workflow step — not fixed by the plan; if checked in, it is additive to
   this WP's `owned_files` and should be added there with a one-line
   rationale per the "small, well-justified out-of-map edit" allowance).
3. Write the file to
   `conformance/skills/trigger-evidence/<run-timestamp>.json`
   (`<run-timestamp>` = the run's own ISO-8601 timestamp, `:` replaced by
   `-` for filesystem safety).
4. Validate:
   ```sh
   node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/<file>.json
   echo "GREEN exit code: $?"   # MUST be 0
   ```
5. Commit the evidence file for real — FR-005 requires a **committed**
   artifact, never one left only in workflow logs or PR prose. This is the
   exact failure mode a sibling mission hit (a control recorded as "0/24" in
   prose that re-measured at "4/24" weeks later because its evidence lived
   in prose, never in a structured artifact) — do not repeat it.

**Files**: `conformance/skills/trigger-evidence/<run-timestamp>.json` (new).
**Validation**: schema-valid per `check-evidence-artifact-shape.mjs`,
committed to the branch (not left in `/tmp` or a workflow log only).

## Subtask T024: NFR-001, NFR-002, C-001 final proofs

**Purpose**: Close out the mission-wide non-functional and constraint
verifications that can only be finalized once every WP's changes exist.

**Steps**:
1. **NFR-001** (offline static path unaffected): diff the static suite's
   `--json` output before and after this mission's total changes:
   ```sh
   git stash   # or check out the pre-mission commit in a scratch clone
   npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/manifest.yaml --json > /tmp/static-before.json
   git stash pop   # restore this mission's changes
   npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/manifest.yaml --json > /tmp/static-after.json
   diff /tmp/static-before.json /tmp/static-after.json
   echo "diff exit code: $?"   # MUST be 0 (empty diff)
   ```
   (WP03's T020 step 3 already captured a mid-mission snapshot — use that as
   a cross-check, but the authoritative before/after pair is pre-mission vs.
   this WP's final state.)
2. **NFR-002** (credentials never committed), both directions:
   ```sh
   command grep -rE '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' conformance/skills/behavioral-manifest.yaml .github/workflows/skill-trigger-routing.yml
   echo "exit code: $?"   # MUST be 1 (no match)
   ```
   Rejection case (construct once, confirm, discard — never commit):
   ```sh
   echo 'api_key: "sk-THIS_SHOULD_NEVER_BE_COMMITTED_1234567890"' >> conformance/skills/behavioral-manifest.yaml
   command grep -rE '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' conformance/skills/behavioral-manifest.yaml .github/workflows/skill-trigger-routing.yml
   echo "rejection exit code: $?"   # MUST be 0 (match found)
   git checkout HEAD -- conformance/skills/behavioral-manifest.yaml   # NEVER git checkout . or rm -rf
   ```
3. **C-001** (diff scope — no `SKILL.md` edits):
   ```sh
   git diff --stat main -- src/doctrine/skills/
   echo "exit code / output: MUST be empty"
   ```
   Use `main` as the comparison base only if this mission's branch actually
   diverged from `main` at a sane merge-base; if this repo's branch strategy
   differs, use the mission's own `planning_base_branch` /
   `merge_target_branch` as reported by `spec-kitty agent context resolve`
   instead of assuming `main` literally.

**Files**: none (verification only).
**Validation**: NFR-001 diff empty; NFR-002 grep exits 1 (clean) and the
constructed rejection exits 0 (match found), then is discarded; C-001 diff
is empty.

## Subtask T025: Author `conformance/skills/README.md`

**Purpose**: Create (fresh — see Context above) the suite's documentation:
local invocation, pinned version, D-1 `[CONVENTION]` twin-phrasing note,
`[LIMITATION]` single-tool-bias note, FR-006 findings index.

**Steps**:
1. Local invocation section: how to run
   `npx --offline @garrison-hq/muster@1.2.1 skills run conformance/skills/behavioral-manifest.yaml --json`
   and how to run each of the four verification scripts, mirroring
   `quickstart.md`'s §8 "Full local pre-merge check."
2. `[CONVENTION]`-tagged section (D-1): the twin-phrasing methodology this
   mission invented (near-miss set of skill A contains its twin's
   should-trigger phrasing) — inline here because
   `docs/rubric/skills-trigger-taxonomy.md` (the intended long-term home,
   per D-1) lives in `garrison-hq/muster`, a separate repository this
   mission's own diff never touches. State plainly that this is a stopgap
   pending a small addendum PR to that file upstream.
3. `[LIMITATION]`-tagged section (research.md §3): distractor tools are
   structurally unavailable at muster `1.2.1` —
   `SkillsManifestBehavioralCase` has no field for them and
   `runBehavioralSkillCase` hardcodes exactly one `ToolDefinition` per case.
   State plainly that this suite's should-trigger axis can therefore only
   detect actively repellent descriptions, not fine-grained quality
   differences among plausible candidates, and that lifting this requires a
   muster-side manifest-schema change (tracked as a dependency note, same as
   D-1's rubric-addendum PR — not this mission's own diff).
4. FR-006 findings index: a "Findings" section, empty (no bare header with
   zero entries claimed as satisfying FR-006 — spec.md's own falsification
   condition) unless T022's live run actually surfaced a duplicate-pair or
   run-family case whose near-miss trigger rate exceeded its threshold. If
   it did, file a spec-kitty GitHub issue against `MOES-Media/spec-kitty`
   with the failing query-set file attached/linked, and index it here by its
   **full URL** (`https://github.com/MOES-Media/spec-kitty/issues/<n>`),
   never bare `#<n>`.
5. Verify the findings-index format mechanically:
   ```sh
   command grep -c 'github.com/MOES-Media/spec-kitty/issues/' conformance/skills/README.md
   ```
   (nonzero once at least one finding exists; this command legitimately
   returns 0 if T022's run found no over-threshold case — that is a valid,
   reportable outcome per spec.md SC-003, not a failure.)
6. Final full local pre-merge check (quickstart.md §8), run once end-to-end
   and recorded in the work log:
   ```sh
   node conformance/scripts/check-trigger-queryset-shape.mjs conformance/skills/trigger-queries/*.yaml \
     && node conformance/scripts/check-twin-phrasing.mjs conformance/skills/trigger-queries/ \
     && node conformance/scripts/check-evidence-artifact-shape.mjs conformance/skills/trigger-evidence/*.json \
     && command grep -rE '(sk-|api[_-]?key\s*[:=]\s*["\047][A-Za-z0-9]{16,})' conformance/skills/behavioral-manifest.yaml .github/workflows/skill-trigger-routing.yml; \
     [ $? -eq 1 ] && echo "conformance: all local checks green"
   ```
7. Commit `conformance/skills/README.md`, run
   `spec-kitty agent tasks mark-status T021 T022 T023 T024 T025 --status done`.

**Files**: `conformance/skills/README.md` (new).
**Validation**: findings-index grep count is consistent with T022's actual
result (0 if no over-threshold case, nonzero with real full-URL citations
otherwise); final pre-merge one-liner reports green.

## Definition of Done

- `.github/workflows/skill-trigger-routing.yml` exists, `workflow_dispatch`
  only (verified by real YAML parse, not text grep alone), muster pinned
  exactly `1.2.1` (both grep directions verified).
- All five FR-004 live-endpoint exit codes recorded (T022): 0, 1, 0, 1, 2.
- A real, committed evidence artifact exists under
  `conformance/skills/trigger-evidence/`, schema-valid, with `runsErrored`
  present (even if `0`) per case.
- NFR-001's before/after static-suite diff is empty; NFR-002's both-direction
  credential-grep proof is recorded; C-001's `SKILL.md` diff-scope check is
  empty.
- `conformance/skills/README.md` exists (created fresh, per the corrected
  Context above), with `[CONVENTION]`, `[LIMITATION]`, and findings-index
  sections.
- `spec-kitty agent tasks mark-status` run for T021-T025.
- This mission's `acceptance-matrix.json` (scaffolded by `finalize-tasks`) is
  updated with real evidence for every FR/NFR/C row this WP owns — no
  `"TODO: replace with a real acceptance criterion"` left in place for a row
  this WP's own verification commands actually exercised.

## Risks

- **Mistaking WP03's synthetic FR-004 proof for this WP's live proof** — do
  not skip T022 on the assumption WP03 "already proved it." WP03 only proved
  the script's logic; this WP proves the mission's actual claim.
- **Treating a dead-endpoint infrastructure failure as valid control-fails-
  as-expected data** — explicitly guarded in T022 step 4.
- **Assuming `conformance/skills/README.md` has prior content to preserve**
  — it does not; see Context above.
- **Schedule/cron creep** — copy-pasting a `schedule:` trigger from another
  workflow in this repo would violate the explicit out-of-scope guard.

## Reviewer Guidance

- Independently confirm all five T022 exit codes were actually produced by
  running the sequence yourself against the recorded report files (or a
  fresh live run), not merely reading the work-log claim.
- Open the committed evidence artifact directly and confirm `runsErrored` is
  present as its own field, distinct from `triggerRate`, for every case
  (NFR-003) — including cases where it is `0`.
- Confirm `conformance/skills/README.md` did not silently absorb or
  duplicate content from `conformance/README.md` (the separate, pre-existing
  top-level file) — they document different suites (static vs. behavioral).
- Confirm any filed finding in the README's index is a full URL, never bare
  `#NN`.
- Confirm `kitty-specs/` is not touched by any commit in this WP's lane.

## Implementation Command

```sh
spec-kitty agent action implement WP04 --agent claude
```

## Activity Log

- 2026-08-01T23:24:48Z – claude – T021-T025 complete. Job 1 fix (pre-WP04, commit e6cadee5c): spec.md/quickstart.md/WP03 task file's FR-003 one-liner corrected r.cases -> r.results (real muster --json shape confirmed against v1.2.1 source and a real run: {ok,total,passed,failed,skipped,results}, no top-level cases key); broken form throws TypeError and only coincidentally exits 1, corrected form runs to completion and discriminates correctly. T021 (38ceca693): .github/workflows/skill-trigger-routing.yml (workflow_dispatch only, C-002 verified by real YAML parse + scratch-copy pull_request rejection; muster pinned exactly 1.2.1, C-003 verified both grep directions + synthetic rejection) + conformance/scripts/build-evidence-artifact.mjs (documented out-of-map allowance) proven against 4 rejection cases + 1 synthetic GREEN. Later fixed (666978a40): removed a self-matching NFR-002 step whose own literal pattern text (and, in the comment, the literal credential-prefix substring) made the repo-wide NFR-002 grep match this workflow file itself -- a real vacuous-check bug caught before merge; re-verified NFR-002/C-002/C-003 clean after the fix. T022 (dd853b5cc): FR-004 live both-condition sequence run for real, gpt-4o-mini via https://api.openai.com/v1 (healthy) and http://127.0.0.1:9 (dead-endpoint): (a) --mode healthy vs healthy=exit 0 (passed:false,runsErrored:0); (b) --mode healthy vs dead=exit 1 (runsErrored:48, cross-wire rejection); (c) --mode dead-endpoint vs dead=exit 0 (passed:false,runsErrored:48); (d) --mode dead-endpoint vs healthy=exit 1 (runsErrored:0, cross-wire rejection); (e) no --mode=exit 2. runsErrored:48 = runsPerQuery(3)*16 queries, matching data-model.md's fully-dead-endpoint prediction exactly. No credential leaked into any log/scratch file (verified by key-prefix grep). T023 (dd853b5cc): first committed evidence artifact conformance/skills/trigger-evidence/2026-08-01T23-16-10.435Z.json, built via build-evidence-artifact.mjs from the real healthy report, schema-valid (check-evidence-artifact-shape.mjs OK, 14 cases), NFR-002-clean. This run also surfaced a genuine FR-006 finding -- 8 of 13 duplicate-pair/run-family cases at/above near-miss threshold -- filed as https://github.com/MOES-Media/spec-kitty/issues/43. T024: NFR-001 diff empty (pre-mission worktree at c36b727cf vs this WP's final state, both {ok:true,total:54,passed:54,failed:0,skipped:0}, byte-identical); NFR-002 both directions (clean exit 1, constructed rejection exit 0, discarded, git diff --exit-code confirmed no residue); C-001 git diff --stat main -- src/doctrine/skills/ empty. T025 (70805c732): conformance/skills/README.md authored fresh, [CONVENTION] (D-1 twin-phrasing) + [LIMITATION] (muster#82 single-tool bias, runBehavioralSkillCase src/cli/index.ts:1414-1465) + Findings (issue #43 by full URL) sections; findings-index grep=2; full local pre-merge one-liner green.
- 2026-08-02T00:18:59Z – claude – Re-review remediation (APPROVE-WITH-FOLLOWUPS), seven fixes this pass: (1) d3d71b9cb capture skills-run exit code instead of letting bash -e abort the job on a healthy run's legitimate exit 1 (muster#77); (2) 1db820696 warm the npm cache before npx --offline muster invocations (ENOTCACHED on a cold runner, reproduced+fixed against a genuinely empty ~/.npm cache); (3) 016f3a601 grant contents:write so the evidence-commit step's git push can succeed (was read-only, would 403), checked against protect-main.yml's github-actions[bot] allowlist; (4) b5275bdee stop the local pre-merge check printing green when a check failed (A&&B&&C&&D;[ $? -eq 1 ] collapsed any of A/B/C's failing exit 1 into D's legitimate exit 1); (5) fb14a7eb0 correct README's false claim that no step asserts on the bare skills-run exit code; (6) 99c66ae99 correct the FR-006 finding's causal attribution (withdrew the legacy-vs-spk-* naming claim, documented two confounds and one contaminated fixture, replaced with the narrower Does-NOT-handle-clause claim, also corrected as a comment on MOES-Media/spec-kitty#43); (7) 1033ab19a filled real acceptance-matrix.json criterion text/notes citing spec.md line numbers and restored FR-001's evidence field after an earlier acceptance-verdict call in this same pass had overwritten it with the placeholder 'same'.
- 2026-08-02T00:19:11Z – claude – Review finding F8 -- accepted-and-unfixed. The raw /tmp/report-healthy.json and /tmp/report-dead.json captures from T022's live FR-004 both-condition run are not committed anywhere in this repo (only ever written to /tmp), so the FR-004 cross-wire assertions (--mode healthy vs dead-endpoint data and vice versa) are not reproducible from committed data -- only the summarized evidence artifact (conformance/skills/trigger-evidence/2026-08-01T23-16-10.435Z.json, built from the healthy report only) is committed. Rationale for not fixing: the dead-endpoint report is generated against a deliberately broken endpoint as a one-time by-hand step (per this WP's own task file, never a CI step) and committing raw reports was never in FR-005's scope (FR-005 requires the summarized evidence-artifact shape, not raw muster --json output, and the raw report may embed transient infra timing data the schema does not cover) -- re-scoping FR-005 to also require raw-report retention was out of this pass's remit. Left as a known gap for a future pass or explicit spec amendment.
- 2026-08-02T00:19:21Z – claude – Review finding F9 -- accepted-and-unfixed. Bare cross-repo issue shorthand ('muster#82', without the garrison-hq/ owner prefix) appears at conformance/skills/README.md's [LIMITATION] section heading, alongside full-form 'garrison-hq/muster#77'/'garrison-hq/muster#82'/'garrison-hq/muster#76' references elsewhere in the same file and in conformance/scripts/check-control-discrimination.mjs -- an inconsistency in cross-repo reference form, not a broken link (this repo and garrison-hq/muster are different GitHub repos; only owner/repo#N autolinks on GitHub, so the bare form is inert text either way, same as the full form in a .mjs comment). Rationale for not fixing: cosmetic/consistency-only, no functional or gate impact, and check-control-discrimination.mjs is WP03's owned file, not WP04's -- normalizing it is out of this WP's owned_files scope without a WP03 amendment. Left as a documentation-consistency cleanup for a future pass.
- 2026-08-02T00:19:30Z – claude – Review finding WP03-LOW -- accepted-and-unfixed. conformance/scripts/check-control-discrimination.mjs:121-135 (WP03-owned, not WP04-owned): against a real skipped-case report, findControlCase() runs and fails to locate the control case before the skipped-case guard fires, so the error message misdirects to a manifest-authoring bug ('control case not found') when the actual cause is an unconfigured endpoint (all cases skipped). Exit code is 2 either way -- nothing false-passes, and FR-003's own skip-guard step in the workflow independently catches the unconfigured-endpoint case with a correct message before this script is ever invoked in CI. Rationale for not fixing: low severity (misleading message only, in a code path CI never actually reaches unguarded), and the file is outside WP04's owned_files -- reordering the guard checks is a WP03-scoped fix. Left as a known low-severity gap for a future pass or explicit WP03 follow-up.
