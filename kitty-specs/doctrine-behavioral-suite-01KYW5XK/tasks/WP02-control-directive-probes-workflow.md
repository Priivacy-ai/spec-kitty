---
work_package_id: WP02
title: Discrimination control, directive-attached probes, and cadence workflow (lane-b)
dependencies: []
requirement_refs:
- FR-005
- FR-007
- C-001
- C-002
planning_base_branch: kitty/mission-doctrine-behavioral-suite
merge_target_branch: kitty/mission-doctrine-behavioral-suite
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-doctrine-behavioral-suite. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-doctrine-behavioral-suite unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
history: []
authoritative_surface: conformance/
create_intent:
- conformance/behavioral/control-manifest.yaml
- .github/workflows/behavioral.yml
execution_mode: code_change
owned_files:
- conformance/doctrine/010-specification-fidelity-requirement.yaml
- conformance/doctrine/039-lynn-cole-engineering-culture.yaml
- conformance/doctrine/044-canonical-sources-and-unification.yaml
- conformance/behavioral/control-manifest.yaml
- conformance/behavioral/scripts/**
- conformance/behavioral/evidence/**
- .github/workflows/behavioral.yml
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – Discrimination Control, Directive-Attached Probes, and Cadence Workflow

## Objective

Ship the discrimination-control manifest and its `runsErrored` helper
(FR-007), at least one behavioral scenario appended to each of three M3
directive manifests (FR-005), and the `workflow_dispatch`-only cadence
workflow that runs everything (C-001, C-002) — everything lane-b owns. This
WP has **zero cross-lane dependency on WP01**: its workflow drives
`muster sop run` via runtime globs (`conformance/behavioral/profiles/*.yaml`),
never a literal file list, so it needs no knowledge of WP01's actual
committed manifest content, only the naming convention spec.md already
fixes.

**Do not open any file under** `conformance/behavioral/tools/**`,
`conformance/behavioral/projected/**`, `conformance/behavioral/profiles/**`,
or `conformance/behavioral/README.md` — those are WP01's exclusive
write_scope, including for read-only acceptance checks (spec.md's own Lanes
section: "No WP in either lane opens a file under the other lane's
write_scope, including for read-only acceptance checks"). Any check that
needs both lanes' files (C-002's `ls` cross-check, the mission's Acceptance
Gate) runs **post-merge**, not inside this WP — see Definition of Done.

## Context

**Why this WP exists**: FR-007 closes the specific gap muster#76 named for
the skills adapter and this spec's Overview correction 7 reconfirmed for
`sop` independently — a dead endpoint and genuine grader discrimination are
byte-identical at the `exit code`/`report.passed` level; only walking
`report.verdicts[].runs[].error` distinguishes them. FR-005 attaches live
behavioral probes to the directive rules that matter most for judgment
calls, so they're checked against real model behavior, not only AGENTS.md
text presence. C-001/C-002 are the guardrails that keep this suite
cadence-only, credential-safe, and actually wired to real manifests (not an
`echo`-only job that satisfies the trigger constraint's letter while doing
nothing).

**Sequencing inside this WP**: T006–T008 (doctrine edits) are independent of
T009–T011 and of each other — any order. T010 depends on T009 existing
(`check-runs-errored.sh` is exercised against `control-manifest.yaml`'s own
report). T011 depends on T009+T010 (the workflow invokes both). RED-before-
GREEN per CHTR-011 applies per subtask exactly as in WP01 — e.g. a
`control-manifest.yaml` where both controls are accidentally *satisfiable*
(a rubric that isn't actually impossible) is a valid RED state to commit
before the real, correctly-rigged version.

**Read before starting**: spec.md FR-005, FR-007 (including both
elaboration sub-sections and the Path note), C-001, C-002, the Discrimination
Controls section, the Live-Model Plan, the Evidence Artifact section, and
the FR-007-both-condition-sequencing block in plan.md's Verification
Strategy.

### muster pin correction — identical to WP01's, repeated here because this WP is independently dispatched

**Never pin `@garrison-hq/muster@1.2.1`** in any command, script, or
workflow file this WP writes. `@1.2.1` has a live, reproduced defect
(`runComplianceProbeEntry` applies the rule-level `passThreshold` to a
single run's inner judge-vote check) that makes every pass-k/k-of-n judge
rule with a resolved threshold `≥ 2` permanently unpassable — exactly the
shape FR-005's judge-graded directive scenarios and FR-007's judge control
both are. The fix (`garrison-hq/muster` commit `db80a4295`,
`garrison-hq/muster#89`, closing `#88`) is released as **`v1.2.2`**
(confirmed via `git merge-base --is-ancestor db80a4295 v1.2.2` and `npm view
@garrison-hq/muster versions` listing `1.2.2` as the latest published
version, tagged 2026-08-01T23:33:20Z, one day after `v1.2.1`). Pin
`@garrison-hq/muster@1.2.2` (or the pinned `garrison-hq/muster-action`
equivalent once it exists) everywhere in `.github/workflows/behavioral.yml`
(T011) and `check-runs-errored.sh`'s own doc comments (T010). Grep your own
diff for the stale pin before considering this WP done:
`command grep -rn "muster@1\.2\.1\|muster-action@1\.2\.1" conformance/behavioral/ .github/workflows/behavioral.yml`
should return no matches.

### `sop`'s exit-code contract — verified at source, same fact WP01 relies on

`doSopRun` (`src/cli/index.ts:1665-1686`, unchanged at `v1.2.2`) returns
`report.passed ? 0 : 1`; there is no exit-`2` endpoint-fatal path (exit `2`
is reserved for an unreadable manifest file, checked before the client is
even built). `SOP_NOOP_CLIENT.chat()` unconditionally throws when
`MUSTER_ENDPOINT` is unset; that throw is contained per-run inside
`runSopManifestSuite`, so every run errors, every errored run counts as
`passed: false`, and `doSopRun` returns exit `1` — **never** exit `0` for a
dead or unset endpoint. This is the entire reason FR-007's `runsErrored`
walk exists: the exit code and `report.passed` are identical between "the
control correctly fired" and "the endpoint was dead," so this WP's
`check-runs-errored.sh` (T010) is not a nice-to-have, it is the only
mechanism that tells the two apart.

## Subtask T006: Append a behavioral scenario to `010-specification-fidelity-requirement.yaml` (FR-005)

**Purpose**: Add ≥1 `judge`-graded scenario to this already-merged M3
manifest without touching its existing `rules[]` entries' `ruleId`s.

**Steps**:
1. **RED first**: commit an addition that is schema-valid but still
   `gradingClass: binary` (no judge verdict yet) before the real judge-graded
   addition, per CHTR-011.
2. Append a new rule (new `ruleId`, e.g. `010-behavioral-1` — do not reuse or
   rename `010-r1`/`010-r2`) with `gradingClass: judge`, citing
   `docs/rubric/sop-rule-taxonomy.md` (or the directive's own source) per the
   existing `source.normative` convention in this file.
3. Same `sopFile:` as the existing manifest — do not introduce a new
   manifest file (FR-005 is explicit: "not a new manifest").

**Files**: `conformance/doctrine/010-specification-fidelity-requirement.yaml`
(edited — append only).

**Validation**:
- `MUSTER_ENDPOINT=<local endpoint> MUSTER_MODEL=<pinned model> MUSTER_API_KEY=<key> npx @garrison-hq/muster@1.2.2 sop run conformance/doctrine/010-specification-fidelity-requirement.yaml --json > /tmp/010.json; echo $?` → expect exit `0` or `1` (model-conditional — either is acceptable here, this FR is about the *shape* of the report, not a specific verdict).
- `jq -e '[.verdicts[].runs[].grades[] | select(.assertionKind == "judge")] | length > 0' /tmp/010.json` → expect `true`, exit `0`. **Do not use `select(.aggregation != null)`** — `SOPCaseVerdict.aggregation` is a required field set unconditionally on every verdict, judge or lint, so that predicate is always true and never discriminates (confirmed empirically during spec remediation: it returned `true`/exit `0` against both a judge-verdict fixture and a lint-only fixture).
- **Rejection case, run for real**: run the identical `jq -e` predicate
  against a static-only fixture report (regenerate `/tmp/010.json` from the
  pre-this-subtask committed manifest, i.e. before your judge addition) →
  expect exit `1`, proving the check actually requires the behavioral
  addition rather than passing on the manifest's pre-existing static-only
  shape.
- Confirm the two pre-existing rules `010-r1`/`010-r2` are byte-identical in
  the diff (only new `rules[]` entries were added): `git diff conformance/doctrine/010-specification-fidelity-requirement.yaml` should show only additions, no modified lines inside the two existing rule blocks.

## Subtask T007: Append a behavioral scenario to `039-lynn-cole-engineering-culture.yaml` (FR-005)

Same pattern as T006, applied to this file's own existing `ruleId`
convention and `sopFile:`. Run the identical `jq -e` verification (T006's
form) against this file's own report, including the rejection case against
this file's pre-existing static-only state.

**Files**: `conformance/doctrine/039-lynn-cole-engineering-culture.yaml`
(edited — append only).

## Subtask T008: Append a behavioral scenario to `044-canonical-sources-and-unification.yaml` (FR-005)

Same pattern as T006/T007, applied to this file. Run the identical
verification and rejection case against this file's own report.

**Files**: `conformance/doctrine/044-canonical-sources-and-unification.yaml`
(edited — append only).

## Subtask T009: `control-manifest.yaml` (FR-007)

**Purpose**: Author the discrimination-control manifest: a judge control
whose rubric demands an impossible property, and a behavioral control whose
system prompt orders the agent to perform the exact action the rule
forbids. Never merged into the main per-profile suite.

**Steps**:
1. **RED first**: commit a version where the "impossible" rubric is
   actually satisfiable by a normal reply (a genuine RED state — the control
   would falsely pass), before the real rigged-impossible version, per
   CHTR-011.
2. Judge control rule: rubric text demands something no real reply can
   satisfy (spec.md's own example: "the reply contains zero words").
3. Behavioral control rule: system prompt explicitly orders the forbidden
   action.
4. This file is never referenced by any profile manifest's `sopFile:` and is
   never included in the main-suite workflow job (T011) — only the
   control-suite job runs it.

**Files**: `conformance/behavioral/control-manifest.yaml` (new).

**Validation** (this is FR-007's own three-run sequence — run every step for
real, not merely described; restore credentials afterward, step 4):
1. **Healthy-endpoint run**, credentials explicit:
   `MUSTER_ENDPOINT=<local endpoint> MUSTER_MODEL=<pinned model> MUSTER_API_KEY=<key or dummy for a local endpoint with no auth> npx @garrison-hq/muster@1.2.2 sop run conformance/behavioral/control-manifest.yaml --json > /tmp/ctrl-healthy.json; echo $?` → expect exit `1` (both controls fail as designed). `jq '[.verdicts[].runs[] | select(.error != null)] | length' /tmp/ctrl-healthy.json` → expect `0`.
2. **Dead-endpoint run** (the falsification target — this is what proves the
   control can be told apart from a broken harness):
   `MUSTER_ENDPOINT=http://127.0.0.1:9/v1 MUSTER_MODEL=<pinned model> MUSTER_API_KEY=<key> npx @garrison-hq/muster@1.2.2 sop run conformance/behavioral/control-manifest.yaml --json > /tmp/ctrl-dead.json; echo $?` → expect exit `1` (same exit code!), but `jq '[.verdicts[].runs[] | select(.error != null)] | length' /tmp/ctrl-dead.json` → expect a value `> 0`.
3. **Third, one-time reproduction of the pre-fix muster#76 shape**: rerun
   step 1's command with all three `MUSTER_*` vars stripped entirely →
   expect exit `1`, `runsErrored > 0`, byte-for-byte indistinguishable at the
   top level from step 2 — proving the env-var omission is load-bearing, not
   cosmetic (this is the exact defect class an earlier draft of this
   mission's own FR-002/003/004/007 verification cells and User Scenario 2
   had, before a remediation pass caught and fixed it in all five places).
4. **Restore** `MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY` to your
   real working values before continuing any other work in this session.

## Subtask T010: `runsErrored` helper (FR-007)

**Purpose**: Package the `runsErrored` computation as a reusable script so
local falsification runs and the CI workflow (T011) share one
implementation, never duplicated inline logic that could drift.

**Steps**:
1. Write `conformance/behavioral/scripts/check-runs-errored.sh`: given a
   `muster sop run --json` report path, compute
   `jq '[.verdicts[].runs[] | select(.error != null)] | length' <report.json>`
   and print the count. **Path note**: this script lives under
   `conformance/behavioral/scripts/`, never `conformance/behavioral/
   tools/**` — that is WP01's exclusive write_scope; opening a path there
   from this WP would violate the mission's own lane-isolation rule even for
   a script whose *content* seems related to WP01's generator.
2. Wire it into both the local T009 validation runs above and the workflow
   (T011).

**Files**: `conformance/behavioral/scripts/check-runs-errored.sh` (new).

**Validation**:
- Run the script against `/tmp/ctrl-healthy.json` (from T009) → expect
  output `0`.
- Run it against `/tmp/ctrl-dead.json` → expect output `> 0` (matching the
  reproduced error text, e.g. `chat request to 127.0.0.1:9 failed: fetch
  failed`).
- **Rejection case**: run the script against a hand-built fixture JSON with
  zero `runs[].error` fields at all levels → expect output `0` even though
  the fixture's `passed` is `false` (proves the script counts errors, not
  failures — a genuinely non-compliant-but-reachable run must report `0`
  here, not a nonzero count).

## Subtask T011: Cadence workflow (C-001, C-002, FR-007's main-suite extension)

**Purpose**: Author `.github/workflows/behavioral.yml`: `workflow_dispatch`
only, two jobs (`main-suite`, `control-suite`), both computing
`check-runs-errored.sh` per case.

**Steps**:
1. **RED first**: commit a workflow with only the `on: workflow_dispatch`
   trigger and an `echo`-only job body before the real job steps, per
   CHTR-011 — this RED state is deliberately the "satisfies the trigger
   constraint's letter while doing nothing" shape C-002 explicitly calls out
   as insufficient, so the GREEN commit's diff makes that gap visible.
2. `on:` block has `workflow_dispatch` only — **never** `pull_request` or
   `schedule` (schedule is out of scope, M8).
3. `main-suite` job: invoke `muster sop run` (pinned `@1.2.2`, never
   `@1.2.1`) against every file matched by the glob
   `conformance/behavioral/profiles/*.yaml` and every FR-005-edited file
   under `conformance/doctrine/*.yaml` (the three literal paths T006–T008
   edited) — glob-driven for the profiles, not a hardcoded 5-name list, per
   plan.md IC-06. For each case, run `check-runs-errored.sh` and write the
   result into that case's `runsErrored` field in the evidence artifact
   (this closes the gap plan.md's Finding-adjacent elaboration flags: an
   earlier draft scoped the `runsErrored` write to control-suite only,
   which would let a real endpoint dying mid-cadence-run be misread as
   every profile failing its avoidance boundary). This job's own exit code
   is **not** gated on `runsErrored == 0` — a genuinely non-compliant model
   must still surface as a red run.
4. `control-suite` job: invoke `muster sop run` against
   `conformance/behavioral/control-manifest.yaml`, then
   `check-runs-errored.sh`, asserting **both** nonzero suite exit and
   `runsErrored == 0` as its own pass condition — never treat the control
   job's exit `1` as a build failure.
5. Both jobs read `MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY` from
   repository secrets, never a manifest value or argv literal (C-001).
6. No `schedule:` trigger, even via copy-paste from a different workflow
   file in this repo.

**Files**: `.github/workflows/behavioral.yml` (new).

**Validation**:
- **C-001**: `command grep -rE '(nvapi-[A-Za-z0-9]{8}|\bsk-[A-Za-z0-9_-]{20})' conformance/behavioral/*.yaml conformance/behavioral/profiles/*.yaml .github/workflows/behavioral.yml` → expect exit `1` (no match — this WP's own `conformance/behavioral/*.yaml`/`profiles/*.yaml` glob will only match files that exist in *this WP's own worktree*, i.e. `control-manifest.yaml`; do not attempt to glob WP01's `profiles/*.yaml` content from inside this WP's isolated worktree — see the post-merge note below). **Rejection case**: plant a fake key matching one of the two regexes in a scratch copy → expect exit `0` (match found), confirming the grep fires; discard the scratch copy, never commit it.
- **C-002 (trigger half only — the file-set cross-check is post-merge, see below)**: `yq -e '.on | has("pull_request") or has("schedule") | not' .github/workflows/behavioral.yml` → expect `true`, exit `0`. **Rejection case**: on a scratch copy, `yq -i '.on.pull_request.branches = ["main"]' /tmp/behavioral-scratch.yml` then rerun the same check against the scratch copy → expect `false`, exit `1`. Discard the scratch copy; never commit it.
- **C-002 (file-set cross-check — post-merge only, not this WP's own acceptance criterion)**: this WP's isolated worktree never contains WP01's committed `conformance/behavioral/profiles/*.yaml` files until both lanes merge onto `kitty/mission-doctrine-behavioral-suite`. **Do not attempt this check inside this WP's own worktree — it will fail for the wrong reason (missing files, not a real defect) and must not be treated as a rejection of this WP.** Record in this WP's Definition of Done that the check is deferred to the mission's post-merge Acceptance Gate (spec.md's Acceptance Gate Sequencing, phase 2): `ls conformance/behavioral/profiles/*.yaml conformance/behavioral/control-manifest.yaml` must match the workflow's referenced globs/paths exactly, run only after both lanes are on the shared target branch.
- **FR-007 main-suite `runsErrored` population**: review (procedural, not a
  one-liner — the main-suite job's exit code is intentionally not gated on
  this) that the workflow's `main-suite` job step invokes
  `check-runs-errored.sh` per case and writes the result into the evidence
  artifact, not only the `control-suite` job.

## Definition of Done

- [ ] T006/T007/T008: each of the three doctrine manifests has ≥1 new
      judge-graded scenario appended, existing `rules[]` entries untouched
      (diff-verified), the corrected `assertionKind`-walk predicate passes
      on the real file and fails on the pre-edit (rejection) fixture for
      each of the three files independently.
- [ ] T009: `control-manifest.yaml` committed; the full three-run FR-007
      sequence (healthy / dead / stripped-env) executed for real with
      credentials restored afterward; RED (satisfiable "impossible" rubric)
      commit precedes GREEN (genuinely rigged) commit.
- [ ] T010: `check-runs-errored.sh` committed; validated against both
      captured reports from T009 plus the zero-errors-but-failing rejection
      fixture.
- [ ] T011: workflow committed with `workflow_dispatch` only; C-001 grep
      gate passes on the real files and fires on the planted-key rejection
      fixture; C-002's trigger-half check passes and fires on the
      `pull_request:` rejection fixture; C-002's file-set cross-check and
      the mission's live-credentialed Acceptance Gate are **explicitly
      deferred to post-merge** in this WP's own record, not attempted (and
      falsely failed) here.
- [ ] **Mark status per subtask** via the current CLI's status-tracking
      command as each subtask lands, not batched at the end. After every
      status/history command, run `git status` and `git log --oneline -5`
      and record what was actually auto-committed — do not assume
      `mark-status`/`add-history` auto-commit, and do not assume
      `spec-commit` (if used) actually persists `status.events.jsonl`; verify
      each time.
- [ ] **Record acceptance verdicts as evidence lands, per FR/C**: FR-007 can
      be fully discharged inside this WP's own worktree (the three-run
      sequence needs only this WP's own `control-manifest.yaml`). FR-005 can
      be fully discharged per-file inside this WP's own worktree (each
      doctrine manifest is pre-existing and visible in any lane's worktree
      branched from this mission's base). C-002's file-set cross-check
      cannot — record it as `pending`, evidence-so-far = "workflow authored,
      globs verified against the naming convention spec.md fixes," remaining
      = "post-merge `ls` cross-check against WP01's actual committed
      files." Do not mark C-002 `pass` from inside this WP.
- [ ] No file outside this WP's `owned_files` was modified — in particular
      nothing under `kitty-specs/` (verify via `git diff --stat` against
      that path returning empty) and nothing under
      `conformance/behavioral/tools/**`, `projected/**`, `profiles/**`, or
      `README.md` (WP01's exclusive scope).

## Risks

- **The FR-007 derived-sum computation is this WP's highest-value
  correctness risk** — a bug in `check-runs-errored.sh` silently launders a
  dead-endpoint run as a valid discrimination proof. Mitigated by running
  the mandatory three-run sequence for real (T009's Validation) before
  FR-007 is marked done, not merely describing it.
- **muster pin regression** (identical risk to WP01, repeated because this
  WP is independently dispatched and may not have WP01's context loaded):
  grep the final diff for `1.2.1` before considering this WP done.
- **Attempting the post-merge-only checks inside this WP's isolated
  worktree**: C-002's file-set cross-check and the mission's live
  Acceptance Gate will genuinely fail here for a reason that has nothing to
  do with this WP's own correctness (WP01's files don't exist yet in this
  worktree). Do not treat that failure as a WP02 defect, and do not
  fabricate WP01's file list to make the check pass locally — defer it.

## Reviewer Guidance

Focus review on: (1) whether the FR-007 three-run sequence was actually
executed with real captured JSON (not merely asserted), including the
restore-credentials step; (2) whether `check-runs-errored.sh` is exercised
against a rejection fixture that has `passed: false` but zero errors,
proving it counts errors and not failures; (3) whether the workflow's
`main-suite` job also populates `runsErrored` per case, not only
`control-suite`; (4) whether C-002's file-set cross-check was correctly
*deferred* rather than incorrectly attempted-and-failed inside this WP; (5)
the muster pin is `1.2.2` everywhere in this WP's new files.

**Implementation command**: `spec-kitty agent action implement WP02 --agent <name>`
