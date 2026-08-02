---
work_package_id: WP04
title: 'crosslayer.yml CI workflow: static PR gate + cadence scaffold (lane-b part 3)'
dependencies: []
requirement_refs:
- FR-004
- FR-005
- C-002
planning_base_branch: kitty/mission-crosslayer-composition-suite
merge_target_branch: kitty/mission-crosslayer-composition-suite
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-crosslayer-composition-suite. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-crosslayer-composition-suite unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-crosslayer-composition-suite-01KYJA33
base_commit: 478b4d5f37ffb869eb0b49fba534a338bb1f27bb
created_at: '2026-07-27T21:47:12.656709+00:00'
subtasks:
- T018
- T019
- T020
- T021
- T022
agent: claude
history:
- timestamp: '2026-07-27T19:45:23Z'
  event: created
  by: /spec-kitty.tasks-outline (planner-priti)
agent_profile: node-norris
authoritative_surface: .github/workflows/
create_intent:
- .github/workflows/crosslayer.yml
- conformance/crosslayer/README.md
- tests/cross_cutting/misc/test_crosslayer_workflow.py
- .github/workflows/ci-quality.yml
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/crosslayer.yml
- conformance/crosslayer/README.md
- tests/cross_cutting/misc/test_crosslayer_workflow.py
- .github/workflows/ci-quality.yml
role: implementer
tags: []
tracker_refs: []
---

# WP04 — crosslayer.yml CI workflow: static PR gate + cadence scaffold

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the
frontmatter, and behave according to its guidance before parsing the rest of
this prompt.

- **Profile**: `node-norris`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the
best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Author `.github/workflows/crosslayer.yml`: a static PR-gate job (every PR,
`garrison-hq/muster-action@<pinned-sha>` against FR-004's manifest,
path-filtered to both `conformance/**` and
`src/doctrine/agent_profiles/built-in/**`) plus a cadence-job scaffold
(`schedule:` + `workflow_dispatch:`, secrets from GitHub Actions repository
secrets only, zero real cases until WP05/lane-c lands). This is a **new**
workflow file, isolated from the shared `.github/workflows/conformance.yml`
by design — never edit that shared file. This WP has no dependency on WP01,
WP02, or WP03's source — only on their **paths**, all fixed in advance by
plan.md's Project Structure.

## Context (read first)

- Spec: `kitty-specs/crosslayer-composition-suite-01KYJA33/spec.md`
  — FR-004 (CI wiring clause), FR-005 (infra-only, not case content);
  Dependencies & Assumptions (workflow-file collision avoidance,
  `conformance/README.md` collision avoidance, the M1 post-spec finding on
  trigger-path scope).
- Plan: `kitty-specs/crosslayer-composition-suite-01KYJA33/plan.md`
  — IC-04 (this WP's source concern, including its own risk notes about an
  empty cadence job and the shared-file collision surfaces).

**Path-filter requirement, stated precisely**: the static job's trigger
paths must cover **both** `conformance/**` **and**
`src/doctrine/agent_profiles/built-in/**` — not just the former. A
profile-only PR that changes an agent profile must see and be able to fix
the persona-drift check its own diff affects (regenerating the committed
persona under `conformance/crosslayer/personas/` is a `conformance/**` edit,
so that PR's author can make the fix even though it did not originate this
mission); a PR touching neither path must never see this job at all.

**Never touch**: `.github/workflows/conformance.yml` (M3's PR #30 modifies
it; a collision here would block concurrent work), `conformance/README.md`
(also M3-touched, and inside C-002's general allow-list unless explicitly
excluded — this mission documents itself in `conformance/crosslayer/README.md`
instead), `conformance/scripts/check-manifest-completeness.mjs` (M3-touched,
unrelated to this mission).

## Subtasks

### T018 — Verify the real `muster-action` input schema and pinned SHA convention

**Purpose**: This mission's spec requires CI to invoke
`garrison-hq/muster-action@<pinned-sha>` — the same cache-warm-equivalent
pattern `conformance.yml` already uses — not a bare `npx`. Confirm the actual
shipped input names before writing the step that depends on them (do not
assume a briefed shape is correct without checking).

**Steps**:
1. Inspect the real `garrison-hq/muster-action` repository's `action.yml` at
   whatever pinned commit/tag this fork's own `conformance.yml` already uses
   (`grep -n "muster-action" .github/workflows/conformance.yml` to find the
   exact pin this fork already trusts — reuse it, do not introduce a new,
   unreviewed pin).
2. Confirm the actual input names (`command`/`args`/`version`/etc.) against
   that real file, not a design briefing.
3. Record the confirmation (or correction) in the work log.

**Files**: none (verification only).
**Validation**: work log states either "confirmed: matches
`conformance.yml`'s existing usage" or "corrected: real input names are
X/Y/Z", with the source consulted.

---

### T019 — Author `.github/workflows/crosslayer.yml`

**Purpose**: The static PR gate and the cadence scaffold, in one new file.

**Steps**:
1. Static job: triggers on `pull_request` (any branch), path-filtered to
   `conformance/**` and `src/doctrine/agent_profiles/built-in/**` (both, per
   the M1 post-spec finding above). Steps: checkout (match this fork's
   existing pin convention, `grep -rn "actions/checkout@"
   .github/workflows/*.yml`), `garrison-hq/muster-action@<pinned-sha>`
   against `conformance/crosslayer/manifest.yaml --static-only`, then the two
   one-line drift-check call sites:
   `bash conformance/scripts/check-persona-drift.sh` (WP01's script) and
   `bash conformance/scripts/check-sop-extract-drift.sh` (WP03's script,
   this WP's own sibling file).
2. Cadence job: `schedule:` trigger plus `workflow_dispatch:` for on-demand
   manual runs. `MUSTER_ENDPOINT`/`MUSTER_API_KEY` sourced from GitHub
   Actions **repository secrets only** — never a manifest value, never
   argv, never a log line. Runs FR-005's cases once they exist.
3. **Zero real cases exist yet** (WP05/lane-c is blocked on M3 and on this
   WP + WP02 merging first). If the cadence job globs a
   `cases/rule-survival-*.yaml`/`erosion-control-*.yaml` pattern that
   currently matches nothing, `muster crosslayer run` may exit `0` trivially
   (no cases = no failures). **Add an explicit inline YAML comment** at that
   step stating this plainly — a green cadence job before WP05 lands must
   never be mistaken for FR-005 being satisfied. This is not optional
   documentation; it is the guard against a specific, previously-seen
   failure mode (an unexercised detector read as a passing one).
4. No `secrets:` reference anywhere in the static job — it must remain fully
   offline/zero-network and runnable on a fork PR with zero repository
   secrets available.

**Files**: `.github/workflows/crosslayer.yml` (new).
**Validation**: covered by T021; inline comment from step 3 confirmed present
by inspection.

---

### T020 — Author `conformance/crosslayer/README.md`

**Purpose**: This mission's own documentation, entirely separate from the
shared top-level `conformance/README.md` (never edited by this mission).

**Steps**:
1. Document this suite's manifest layout, the two lint/rule-survival check
   classes, and how a contributor runs the static check locally.
2. Do not touch `conformance/README.md` under any circumstance.

**Files**: `conformance/crosslayer/README.md` (new).
**Validation**: `git diff --stat conformance/README.md` shows no changes.

---

### T021 — Workflow structure, trigger wiring & pinning-test proof (locally provable; real CI run tracked separately)

**Scope note (T021 split, 2026-07-31 — mirrors WP02's T012 1a/1b pattern)**:
T021 originally bundled two genuinely different things under one subtask:
(a) proof this WP's own workflow file is structurally correct and its
guard-suite pinning is real and green — fully provable from this lane
alone — and (b) an actual GitHub Actions run against a real PR, which
cannot exist until WP01's/WP02's/WP03's lanes are merged onto the same
branch as this WP's `crosslayer.yml`. Bundling both under one subtask
deadlocked mission-level approval: approving WP04 requires T021 "done",
T021's CI half requires the lanes merged, and merging requires WP04
approved first. This subtask is now scoped to (a) only, honestly
markable done today; (b) is tracked as its own named post-merge action in
`tasks/PRE-MERGE-ACTIONS.md` (item 7), carrying this subtask's original
"real CI verification" text **verbatim** so the requirement is relocated to
where it can be honestly satisfied, not softened or dropped.

**Steps** (all provable today, from this lane alone):
1. Confirm `crosslayer.yml`'s `on:` block: `pull_request` triggers,
   path-filtered to `conformance/**` and
   `src/doctrine/agent_profiles/built-in/**` (T019); `schedule:` +
   `workflow_dispatch:` for the cadence job (T020).
2. Confirm the static job's steps invoke
   `garrison-hq/muster-action@<pinned sha>` against FR-004's manifest and
   both drift-check call sites (`check-persona-drift.sh`,
   `check-sop-extract-drift.sh`), and that no `secrets:` reference appears
   anywhere in the static job (T018/T019).
3. Confirm `tests/cross_cutting/misc/test_crosslayer_workflow.py` — the
   14-test structural pytest suite pinning this workflow's trigger paths,
   static-job step wiring, cadence-job secrets sourcing, and the
   zero-real-cases comment — collects under CI's exact selector (`pytest
   tests/e2e/ tests/cross_cutting/ -m "not distribution and not
   windows_ci"`) and passes: run `uv run python3 -m pytest
   tests/cross_cutting/misc/test_crosslayer_workflow.py -q` and record the
   real exit code and pass count.
4. Confirm the MEDIUM-2 inner-gate fix at lane-d `cfddb951b`: trace a PR
   whose only changed file is `crosslayer.yml` end to end through
   `ci-quality.yml`'s `changes` job — the outer `on.pull_request.paths`/
   `on.push.paths` admits it, `crosslayer.yml` is now a member of the `e2e`
   dorny filter group so `needs.changes.outputs.e2e` evaluates `'true'`
   (false before the fix), and `e2e-cross-cutting`'s `if` (which gates on
   `needs.changes.outputs.{e2e,core_misc,execution_context}`) evaluates true
   (false before the fix) — so the job, and its 14 pinned tests, actually
   runs on the merge-blocking PR path, not only on push. Record both the
   before/after evaluation and the guard-suite re-run count (65 passed)
   that confirmed no regression.

**Files**: none new.
**Validation**: 14/14 `test_crosslayer_workflow.py` tests pass; the
before/after `e2e`/`e2e-cross-cutting` trace is recorded with exact
true/false values on each side of `cfddb951b`.

**Real CI verification — moved to `tasks/PRE-MERGE-ACTIONS.md` item 7.**
This is no longer part of T021's Definition-of-Done gate; see that item for
the original, unmodified text (Purpose, Steps 1-4, Files, Validation) and
its own honest blocked-status requirement.

---

### T022 — WP04 verification gate (Definition of Done + per-lane C-002)

**Owned-files/scope-gate widening (C-011 remediation)**: this WP's
`owned_files`/`create_intent` originally admitted only the two CI/README
deliverables, with no path a C-011-compliant failing-first test could live
at. That is a task-file defect, not a reason to skip ATDD-first discipline
— `owned_files`, `create_intent`, and the per-lane C-002 gate below are
widened to admit exactly one additional file,
`tests/cross_cutting/misc/test_crosslayer_workflow.py` (the structural
pytest suite pinning this WP's user-observable behavior: trigger paths,
static-job step wiring, cadence-job secrets sourcing, the zero-real-cases
comment). Nothing else under `tests/` is opened up.

**Second widening (M7 WP04 review, MEDIUM-2 remediation)**: `owned_files`/
`create_intent` and the per-lane C-002 gate below are widened again to admit
`.github/workflows/ci-quality.yml`, so this WP can add
`.github/workflows/crosslayer.yml` to that file's own `on.pull_request.paths`/
`on.push.paths` lists — otherwise a PR editing only `crosslayer.yml` would
re-run none of the 14 tests pinning it, the exact gap mission
`ci-suite-map-bind` FR-012 exists to close. Not left as unassigned prose:
this WP claims the edit rather than leaving it for an unnamed maintainer.

**Steps** (run in order):
```bash
git diff --stat                                              # ONLY the four owned_files entries changed
git diff --stat .github/workflows/conformance.yml             # MUST show no changes
git diff --stat conformance/README.md                         # MUST show no changes
grep -n "secrets:" .github/workflows/crosslayer.yml            # MUST appear only in the cadence job, never the static job
git diff --name-only <mission-base>...<this-lane-branch> > /tmp/wp04-c002-diff.txt
if grep -qx "conformance/README.md" /tmp/wp04-c002-diff.txt; then echo "C-002 violation"; exit 1; fi
! (grep -v '^conformance/' /tmp/wp04-c002-diff.txt | grep -v '^kitty-specs/' | grep -v '^\.github/workflows/crosslayer\.yml$' | grep -v '^tests/cross_cutting/misc/test_crosslayer_workflow\.py$' | grep -v '^\.github/workflows/ci-quality\.yml$' | grep -q .)
```
The last two lines are this WP's **per-lane C-002 check**, this WP's own
responsibility before requesting review; the cross-lane assembled-diff run
happens again at mission review as the backstop.

## Definition of Done

- [ ] C-011 (ATDD-first): `tests/cross_cutting/misc/test_crosslayer_workflow.py`
      committed RED (failing) before any implementation commit, confirmed
      GREEN at the final commit; both runs' exit codes recorded, and
      collection under CI's exact selector
      (`pytest tests/e2e/ tests/cross_cutting/ -m "not distribution and not windows_ci"`)
      proven
- [ ] T018's input-schema verification recorded in the work log
- [ ] `crosslayer.yml` triggers on PR, path-filtered to both
      `conformance/**` and `src/doctrine/agent_profiles/built-in/**`
- [ ] Static job has no `secrets:` reference; cadence job sources
      `MUSTER_ENDPOINT`/`MUSTER_API_KEY` from repository secrets only
- [ ] Both drift-check call sites (`check-persona-drift.sh`,
      `check-sop-extract-drift.sh`) wired as one-liners
- [ ] Cadence job carries an explicit inline comment stating it has zero real
      cases until WP05/lane-c lands
- [ ] `conformance/crosslayer/README.md` authored; shared
      `conformance/README.md` untouched
- [ ] T021's locally-provable proof recorded: workflow triggers/static-job
      wiring confirmed, `test_crosslayer_workflow.py` 14/14 passing, and the
      `cfddb951b` inner-gate trace (`e2e`/`e2e-cross-cutting` false→true)
      confirmed on both sides. (T021's real-CI-run half is tracked
      separately — see `PRE-MERGE-ACTIONS.md` item 7 — and is not part of
      this WP's Definition of Done.)
- [ ] Per-lane C-002 check (T022) passes against this WP's own lane diff
- [ ] No file outside `owned_files` modified; `.github/workflows/conformance.yml`
      and `conformance/README.md` untouched

## Risks

- **Empty cadence job read as evidence FR-005 works**: this is the single
  biggest risk this WP creates for the rest of the mission. The inline
  comment (T019 step 3) exists specifically so a reviewer or operator does
  not mistake "cadence job is green" for "FR-005 is satisfied" before WP05
  lands.
- **Shared-file collision**: `conformance.yml` and `conformance/README.md`
  are both out of scope; a careless edit to either reproduces exactly the
  concurrent-work collision this mission's own Dependencies section goes to
  some length to avoid.
- **Fabricating a CI run**: do not report a green `run_id` that was not
  independently confirmed via `gh run view`. This requirement now lives at
  `PRE-MERGE-ACTIONS.md` item 7 (relocated out of T021 by the 2026-07-31
  split); if lane integration has not happened yet when that item is acted
  on, report the blocker honestly per its own step 3, verbatim from the
  original T021 text.

## Reviewer guidance

- **Reject if** `secrets:` appears anywhere in the static job.
- **Reject if** the path filter covers only `conformance/**` and omits
  `src/doctrine/agent_profiles/built-in/**`.
- **Reject if** the cadence job's zero-case state is not called out with an
  explicit inline comment.
- **Reject if** `.github/workflows/conformance.yml` or
  `conformance/README.md` shows any diff.
- **Reject if** T021's CI run cannot be independently confirmed via
  `gh run view` when claimed as green.
- Confirm the per-lane C-002 check (T022) was actually run.

Implementation command: `spec-kitty agent action implement WP04 --agent claude`

## Activity Log

- **T018 (muster-action input-schema verification)**: confirmed —
  `conformance.yml`'s existing usage matches the shape this WP needs.
  `grep -n "muster-action" .github/workflows/conformance.yml` shows
  `garrison-hq/muster-action@b40681a514f9500f5958b4f9f3efeacd30aae6ca # v1`
  invoked with `with: {command: 'skills run', args: 'conformance/skills/manifest.yaml',
  version: '1.1.0'}`. Input names (`command`/`args`/`version`) reused
  as-is; no new/unreviewed pin introduced. `actions/checkout` pin reused
  identically: `actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6`.
- **C-011 (ATDD-first) remediation**: this WP's `owned_files`/`create_intent`
  as authored admitted only `.github/workflows/crosslayer.yml` and
  `conformance/crosslayer/README.md` — no path a failing-first test could
  live at. Widened both lists (and the T022 per-lane C-002 gate) to also
  admit `tests/cross_cutting/misc/test_crosslayer_workflow.py`, scoped
  narrowly to that one file. A RED commit (the test alone, workflow file
  absent) was made before any implementation commit on the lane-d branch;
  confirmed failing via
  `uv run python -m pytest tests/cross_cutting/misc/test_crosslayer_workflow.py -m "not distribution and not windows_ci"`
  (13 failed / 1 passed, exit 1). CI-collection proven via the exact
  selector `pytest tests/e2e/ tests/cross_cutting/ -m "not distribution and not windows_ci" --collect-only`,
  which lists all test functions (14 once GREEN). Final GREEN confirmed at
  14 passed, exit 0. Four checks were falsified directly (path-filter
  omission, secrets injection into the static job, `--write` reintroduction
  on the sop-extract-drift call site, zero-real-cases comment removal) —
  each reverted, confirmed the corresponding test(s) failed, then restored.
- **ci-quality.yml path-gap — FIXED (M7 WP04 review, MEDIUM-2)** — **PARTIAL;
  see the follow-up entry below for the corrected, complete picture.**
  Originally recorded below as "out of WP04 scope" and left for an unnamed
  maintainer. The review correctly rejected that: this mission's own C-003
  remediation already says "unassigned-to-a-lane is not the same as unowned —
  leaving it as free-floating prose degrades into nobody running it." A
  separate, narrower gap than first described was confirmed: `ci-quality.yml`'s
  `on.pull_request.paths`/`on.push.paths` enumerate six workflow files by
  name (`ci-quality.yml`, `ci-windows.yml`, `drift-detector.yml`,
  `release.yml`, `release-readiness.yml`,
  `check-spec-kitty-events-alignment.yml`, per FR-012's own doctrine
  comment), and `crosslayer.yml` was not among them, with no
  `.github/workflows/**` wildcard anywhere in the repo to catch it by
  default — so a PR editing only `crosslayer.yml` would re-run none of the
  14 tests pinning it. Fixed by adding
  `.github/workflows/crosslayer.yml` to both lists (this WP's own file, now
  claimed rather than left unowned); `owned_files`/`create_intent` and the
  T022 per-lane C-002 gate above widened accordingly. Verified: YAML still
  parses, and the guard suite
  (`test_ci_quality_path_filters`, `test_gate_coverage_parse_model`,
  `test_suite_jobs_gate_blocking`, `test_workflow_dist_lint`,
  `test_plugin_validate_workflow`, `test_release_ci_ownership`) re-run
  green. (Earlier text below, describing this as out-of-scope, is retained
  for the record but is superseded by this entry.) **This entry's own "FIXED"
  claim was itself incomplete — it closed only the outer admission gate, not
  the inner job-level gate. Corrected below.**
- **ci-quality.yml path-gap — the entry above closed only HALF the gap (M7
  WP04 review, MEDIUM-2, second remediation pass)**: the entry above added
  `.github/workflows/crosslayer.yml` to `ci-quality.yml`'s top-level
  `on.pull_request.paths`/`on.push.paths`. That is necessary but not
  sufficient, and claiming "Fixed by adding `.github/workflows/crosslayer.yml`
  to both lists" was not true for the PR path — it only described what the
  outer paths change does, not what actually gates test execution.
  `ci-quality.yml` has a second, inner filter layer: the `changes` job
  (dorny/paths-filter, lines ~144-500) computes named groups from the
  changed-file set, and the `e2e-cross-cutting` job's own `if` only runs
  when `needs.changes.outputs.e2e == 'true' || core_misc == 'true' ||
  execution_context == 'true'` (plus the `push` short-circuit). Traced by
  walking a PR whose only changed file is `.github/workflows/crosslayer.yml`
  through both layers, not by re-parsing YAML or re-running the (green but
  blind-to-this-gap) guard suite: (1) outer `on.pull_request.paths` admits
  the PR — `.github/workflows/crosslayer.yml` was already listed there by the
  first remediation. (2) The `changes` job's `dorny/paths-filter` step
  evaluates every named group against that one changed file: `e2e`
  (`.github/workflows/ci-quality.yml`, `tests/e2e/**`,
  `tests/cross_cutting/**`) — false; `core_misc` (`ci-quality.yml`,
  `ci-windows.yml`, `drift-detector.yml`, `release.yml`, plus src/tests
  cones) — false; `execution_context` (four `src/` cones + one test file) —
  false; the `unmatched` fail-closed catch-all requires `ANY_SRC == 'true'`
  (a `src/**` change), which a workflow-only diff never produces — false. So
  every output `e2e-cross-cutting`'s `if` reads is false. (3) With
  `needs.changes.outputs.e2e`, `.core_misc`, and `.execution_context` all
  false and `github.event_name == 'pull_request'` (not `push`), the `if`
  short-circuits to false and the job — and the 14 tests it runs — is
  **skipped**. So the PR-side (merge-blocking) half of the gap was never
  closed by the first remediation; only the `push` half was, because the
  job's `if` also has an unconditional `github.event_name == 'push'` branch
  that does not depend on any `changes` output. **Real fix**: add
  `.github/workflows/crosslayer.yml` to the `e2e:` filter group at
  `ci-quality.yml`'s `changes` job (the dorny filter block, `e2e:` key),
  alongside `core_misc`'s existing pattern for the same problem — its own
  inline comment documents it: *"The other suite-running workflows route to
  the architectural guard shard via this group (FR-012 two-layer, second
  layer)."* `crosslayer.yml` is exactly such a sibling suite-running
  workflow; it needed to appear in **both** layers, and only the outer one
  had been done. Re-traced the same PR-only-changes-crosslayer.yml path
  after the fix: `e2e` now evaluates true (literal path-list membership,
  no wildcard needed), so `needs.changes.outputs.e2e == 'true'` is true,
  the job's `if` is true, and `e2e-cross-cutting` **runs** on the PR path.
  Guard suite (`test_ci_quality_path_filters`, `test_gate_coverage_parse_model`,
  `test_suite_jobs_gate_blocking`, `test_workflow_dist_lint`,
  `test_plugin_validate_workflow`, `test_release_ci_ownership`, run via
  `uv run pytest` since the system interpreter lacks `respx`): 65 passed,
  same count as the mission's recorded baseline. Also regenerated this
  mission's `wps.yaml` WP04 `owned_files`/`create_intent` and `lanes.json`
  lane-d `write_scope` (previously still listing only `crosslayer.yml` and
  `conformance/crosslayer/README.md`, disagreeing with this file's own
  frontmatter and the T022 gate) — `lanes.json` regenerated through the real
  `compute_lanes` + `write_lanes_json` path (not hand-edited), matching how
  the sibling `status.json` fix used the canonical reducer instead of a
  hand-edited snapshot.
- **ci-quality.yml path-gap (out of WP04 scope) — superseded, see entry
  above**: confirmed by reading
  `.github/workflows/ci-quality.yml`'s top-level `on.pull_request.paths`/
  `on.push.paths` (lines 3-60) — neither list contains `conformance/**` nor
  `AGENTS.md`. A PR touching only `conformance/scripts/check-sop-extract-drift.sh`
  would not trigger `ci-quality.yml`'s `tests/e2e/ tests/cross_cutting/`
  job, so WP03's unit tests pinning that script would not re-run against a
  script-only edit. This WP does not fix it: `ci-quality.yml` is not in
  `owned_files`/`create_intent` for any WP in this mission, and this WP's
  own `crosslayer.yml` gate (path-filtered to `conformance/**` +
  `src/doctrine/agent_profiles/built-in/**`) still runs and still catches
  drift for that exact case via the bare `check-sop-extract-drift.sh` call
  site — only `ci-quality.yml`'s own unit-test re-run would be missed, and
  that workflow's path-filter ownership belongs to whoever maintains
  `ci-quality.yml`, not this mission.
- **T021 (real CI verification) — BLOCKED pending lane integration.**
  `git worktree list` at implementation time shows lane-a
  (`kitty/mission-crosslayer-composition-suite-01KYJA33-lane-a`, WP01),
  lane-b (`...-lane-b`, WP02), and lane-c (`...-lane-c`, WP03) all still on
  their own, separate, unmerged lane branches — none has merged into this
  mission's coordination branch
  (`kitty/mission-crosslayer-composition-suite-01KYJA33`), let alone the
  mission target branch. This WP's `crosslayer.yml` calls
  `conformance/scripts/check-persona-drift.sh` (WP01), `conformance/crosslayer/manifest.yaml`
  (WP02), and `conformance/scripts/check-sop-extract-drift.sh` (WP03) —
  none of those three artifacts exist on any branch this WP's own commits
  sit on. A real GitHub Actions run of `crosslayer.yml` right now would
  fail immediately (missing files), which would not be evidence of a real
  defect in this WP's own workflow — it would only be evidence of the
  known, expected lane-isolation gap. **No `run_id` is invented or
  claimed.** What is missing, concretely, before T021 can be completed for
  real: WP01's lane-a merge (personas + `check-persona-drift.sh`), WP02's
  lane-b merge (`manifest.yaml` + cases + control + C-001 fixture), and
  WP03's lane-c merge (`sop-extract.md` + `check-sop-extract-drift.sh`)
  must all land on a single pushed branch alongside this WP's
  `crosslayer.yml`, and a real PR against that combined branch must then be
  opened so the workflow's `pull_request` trigger actually fires. Static,
  locally-runnable proof of this WP's own file (the pytest suite above) is
  complete and GREEN; T021's real-CI half is honestly deferred, not
  fabricated.

**2026-07-31 — T021 split (post-approval-blocker remediation)**: the
paragraph above is retained verbatim as the original honest-blocked record.
T021 itself is now redefined to cover only the locally-provable half (see
the T021 section's "Scope note"); the real-CI-run half described above is
relocated, with its original wording intact, to `PRE-MERGE-ACTIONS.md`
item 7. Re-confirmed at split time: `test_crosslayer_workflow.py` 14/14
passing (`uv run python3 -m pytest
tests/cross_cutting/misc/test_crosslayer_workflow.py -q` → `14 passed`), and
the `cfddb951b` inner-gate trace holds as described (outer paths admit a
crosslayer.yml-only PR; `e2e` dorny group and `e2e-cross-cutting`'s `if`
both evaluate false before that commit and true after).
