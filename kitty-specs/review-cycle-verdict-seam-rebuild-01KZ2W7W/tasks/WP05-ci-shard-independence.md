---
work_package_id: WP05
title: CI shard independence
dependencies:
- WP02
requirement_refs:
- FR-016
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T019
- T020
- T021
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: .github/workflows/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
- tests/architectural/ci_topology_census.json
- tests/architectural/test_ci_quality_path_filters.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 - CI shard independence

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

`fast-tests-review` is the only CI shard that runs `tests/review/` with
`--cov=src/specify_cli/review` — this mission's own primary write surface. It is
gated on `fast-tests-status`'s `result`, and `fast-tests-status` is the shard #3157
(fixed by WP02) keeps red. Until that gating is removed, **this mission cannot
measure its own diff-coverage gate**: one unrelated shard failure starves the
coverage signal for the exact code this mission changes.

This is not a P3 cleanup despite its position late in the plan's user-story
ordering — FR-016/SC-010 name it a **hard prerequisite for measuring this
mission at all** (spec.md User Story 7). It must land before any WP whose
correctness this mission wants CI to actually verify.

**The measured shape, carried forward from a prior adversarial round — do not
treat as solved by fixing one edge, and do not treat the list below as
exhaustive**: the workflow currently has result-gated edges in **two
classes**, and this WP must remove **both**, not just the one touching
`fast-tests-review`. **This mission has already pinned three wrong numbers in
this exact spot once (NFR-007's own history); do not repeat that mistake by
treating the job names below as a closed list to check off** — the closing
criterion is the rule in T019/T020/T021 (a grep with zero remaining hits
outside named non-shard aggregator exceptions), not a count of named jobs:

- **Class 1 — any job gated on a predecessor's `result != 'failure'`.** A
  prior pass named six `fast-tests-*` jobs here and stopped — that list was
  itself incomplete. A full grep of the workflow (`needs\.[\w-]+\.result\s*!=
  \s*'failure'`) finds edges on jobs the earlier pass never enumerated at
  all, in addition to the six originally named:
  - Originally named: `fast-tests-status` ← `needs.fast-tests-sync.result !=
    'failure'`; `fast-tests-review` ← `needs.fast-tests-status.result !=
    'failure'`; `fast-tests-next` ← `needs.fast-tests-status.result !=
    'failure'`; `fast-tests-lanes` ← `needs.fast-tests-status.result !=
    'failure'` **and** `needs.fast-tests-merge.result != 'failure'`;
    `fast-tests-dashboard` ← `needs.fast-tests-status.result != 'failure'`;
    `fast-tests-upgrade` ← `needs.fast-tests-status.result != 'failure'`.
  - Previously unnamed, found by grep: `fast-tests-doctrine` ←
    `needs.kernel-tests.result != 'failure'`; `fast-tests-core-misc` ←
    `needs.kernel-tests.result != 'failure'` **and**
    `needs.fast-tests-doctrine.result != 'failure'`; `fast-tests-charter` ←
    `needs.kernel-tests.result != 'failure'` **and**
    `needs.fast-tests-doctrine.result != 'failure'`; `fast-tests-agent` ←
    `needs.kernel-tests.result != 'failure'` **and**
    `needs.fast-tests-doctrine.result != 'failure'`; `mission-loader-coverage`
    ← `needs.fast-tests-next.result != 'failure'` (not `fast-tests-`
    prefixed, but a coverage-shard job gated the identical way).
  - **Do not re-derive this list by hand and stop there either** — grep the
    live workflow yourself (T019) rather than trusting either enumeration
    above; workflow files change, and a third hand-typed count is exactly
    what this note exists to prevent.
- **Class 2 — `integration-tests-*` gated on their `fast-tests-*` counterpart's
  `result == 'success'`.** Sixteen jobs, one edge each: `integration-tests-agent`,
  `-doctrine`, `-charter`, `-sync`, `-sync-real-port`, `-merge`, `-missions`,
  `-post-merge`, `-release`, `-status`, `-review`, `-next`, `-lanes`,
  `-dashboard`, `-upgrade`, `-cli`.

A prior pass on this mission fixed one edge and called it done; a second squad
found the others still standing, including several on jobs it had never
named. **Fixing the named jobs is not compliance.** Every job gated on a
predecessor's `.result` — named above or not — must stop conditioning its own
execution on that predecessor's outcome; it should still *run*, and its own
result should still be visible, regardless of whether the predecessor passed
or failed. (Running regardless of predecessor result is different from
ignoring a real code dependency: if `fast-tests-status` produces no artifact
`fast-tests-review` needs, that is a separate defect to flag, not a reason to
keep the gate.)

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story 7
  (FR-016, FR-018, FR-019), User Story 6 (FR-014, this WP's dependency)
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-03 ("CI
  shard independence")
- `.github/workflows/ci-quality.yml` — the workflow this WP edits. Read the whole
  `fast-tests-*` / `integration-tests-*` block (roughly lines 984-2800) before
  touching anything; the `needs:` lists encode real artifact dependencies
  (checkout, cache, coverage XML upload) that must NOT be severed — only the
  `.result != 'failure'` / `.result == 'success'` conditions in the `if:` blocks
  are in scope.
- `tests/architectural/ci_topology_census.json` — the existing construction-derived
  topology census (mission `ci-topology-shrink`, NFR-006). Read its `_comment` and
  `rule` keys; this WP's new check follows the same "derived, not hand-maintained"
  discipline rather than inventing a second, competing census.
- `tests/architectural/test_ci_quality_path_filters.py` — the file this WP extends.
  Read `_load_workflow`, `_job`, `_path_filters` (lines ~1-45) for the existing
  YAML-parsing helpers; reuse them, do not hand-roll a second workflow parser.

**Dependency**: WP02 must land first — it fixes #3157's dated fixture and shares
`tests/_arch_shard_map.py` with WP01 (file-granularity ownership: WP05 does not
touch that file, WP02 does).

**Constraints (binding)**:
- Do not remove a `needs:` job-dependency edge (the DAG ordering / artifact
  handoff) — only the `if:`-level `.result` condition gating execution.
- Do not change which files each shard's dorny path filter selects — this WP
  changes gating, not scope.
- `mypy --strict` / `ruff` clean on the new Python test file; zero suppressions.

## Subtask T019 — Decouple every shard job from a predecessor's `result != 'failure'`

- **Purpose**: Remove every Class 1 edge — not only the six jobs a prior pass
  named — so `fast-tests-review` runs and reports coverage for
  `src/specify_cli/review` even when an upstream shard is red, and so no
  other coverage shard (e.g. `fast-tests-doctrine`, `fast-tests-charter`,
  `fast-tests-agent`, `fast-tests-core-misc`, `mission-loader-coverage`) is
  left silently gated the same way.
- **Steps**:
  1. Do not work from the Objective's named-job list alone — grep the live
     workflow yourself first: `grep -nE "needs\.[[:alnum:]_-]+\.result\s*!=\s*
     'failure'" .github/workflows/ci-quality.yml`, then map each hit to its
     enclosing job (e.g. by scanning upward for the nearest top-level job key)
     to build your own authoritative list before editing anything. The
     Objective's named-job list is a known starting point, not the closing
     definition — treat any hit your own grep finds, named there or not, as
     in scope.
  2. For each job your grep finds, remove the `&& needs.<predecessor>.result
     != 'failure'` line(s) from the job's `if: >-` block.
  3. Leave the job's `needs: [...]` array untouched — the checkout/cache/build
     ordering these jobs rely on is a real dependency, only the result-gating
     condition is removed.
  4. Leave the `always()` and the dorny path-filter clause
     (`needs.changes.outputs.<x> == 'true' || github.event_name == 'push'`) in
     each `if:` block exactly as-is — those are unrelated gates (filter-based
     scoping, not result-gating) and are out of scope.
  5. Re-run `yamllint`/`actionlint` if available locally, or at minimum
     `python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/ci-quality.yml').read_text())"`
     to confirm the file still parses after each edit.
  6. Re-run the same grep from step 1 after your edits and confirm it returns
     zero matches — not "zero matches among the jobs I already knew about."
     A nonzero result after your edits means either a missed job or a
     job outside this WP's understanding of "shard job"; investigate rather
     than filtering it out of the count.
- **Files**: `.github/workflows/ci-quality.yml`
- **Validation checklist**:
  - [ ] `grep -nE "needs\.[[:alnum:]_-]+\.result\s*!=\s*'failure'"
        .github/workflows/ci-quality.yml` returns zero matches (re-run after
        editing, not just against the originally named six jobs).
  - [ ] Every edited job's `needs:` array is byte-identical to before the edit.
  - [ ] The workflow file still parses as valid YAML.
- **Edge Cases**: `fast-tests-lanes`, `fast-tests-core-misc`,
  `fast-tests-charter`, and `fast-tests-agent` each carry **two** predecessor
  result-gates in one `if:` block — both must be removed in the same edit,
  not just the first one a naive single-pattern `grep -l` finds.

## Subtask T020 — Decouple `integration-tests-*` from their `fast-tests-*` counterpart

- **Purpose**: Remove all sixteen Class 2 edges, so an `integration-tests-*`
  shard runs and reports regardless of whether its `fast-tests-*` counterpart
  passed.
- **Steps**:
  1. For each of the sixteen jobs named in the Objective
     (`integration-tests-agent`, `-doctrine`, `-charter`, `-sync`,
     `-sync-real-port`, `-merge`, `-missions`, `-post-merge`, `-release`,
     `-status`, `-review`, `-next`, `-lanes`, `-dashboard`, `-upgrade`, `-cli`),
     remove the `&& needs.<counterpart>.result == 'success'` line from its
     `if: >-` block.
  2. `integration-tests-cli` also carries an unrelated release-gating
     condition (`needs.build-wheel.result == 'success'`, a different job
     entirely, used by a distinct downstream job) — do not touch that line;
     only the `fast-tests-cli.result == 'success'` line inside
     `integration-tests-cli`'s own block is in scope.
  3. As with T019, leave `needs:` arrays and dorny filter clauses untouched.
  4. As in T019, do not stop at the named sixteen — re-grep
     (`grep -nE "needs\.[[:alnum:]_-]+\.result\s*==\s*'success'"
     .github/workflows/ci-quality.yml`) after editing and account for every
     remaining hit; the sixteen named here were independently confirmed
     exhaustive for Class 2 by that same grep, but re-verify it yourself
     rather than trusting this prompt's count, per the same discipline T019
     applies to Class 1's list.
- **Files**: `.github/workflows/ci-quality.yml`
- **Validation checklist**:
  - [ ] `grep -n "result == 'success'" .github/workflows/ci-quality.yml` shows no remaining match whose LHS is one of the sixteen `fast-tests-*` counterparts inside an `integration-tests-*` job's own `if:` block.
  - [ ] The unrelated `needs.build-wheel.result == 'success'` gate elsewhere in the file is untouched.
  - [ ] `git diff --stat .github/workflows/ci-quality.yml` shows no line-count drift beyond the removed gate lines (no accidental reformatting).
- **Edge Cases**: `integration-tests-sync` and `integration-tests-sync-real-port`
  both gate on `fast-tests-sync.result == 'success'` — two distinct jobs sharing
  one counterpart name; both edges must be removed, and they are easy to
  under-count if you search by counterpart name instead of by job.

## Subtask T021 — Add a topology assertion so a new result-gated edge reds

- **Purpose**: Without a standing check, a future PR can silently reintroduce
  exactly this coupling (e.g. a new shard added by copy-pasting an existing
  job's `if:` block). This subtask makes that regression fail CI instead of
  waiting for the next adversarial squad to find it by hand.
- **Steps**:
  1. In `tests/architectural/test_ci_quality_path_filters.py`, add a new test
     function (e.g. `test_no_shard_gates_execution_on_a_predecessor_result`)
     using the existing `_load_workflow()` / `_job()` helpers already in that
     file (see lines ~1-45).
  2. Walk every job in `data["jobs"]`; for each, inspect the `if:` string
     (when present) for either gating pattern: a regex matching
     `needs\.[\w-]+\.result\s*(!=\s*'failure'|==\s*'success')`.
  3. Assert the set of jobs matching either pattern is **empty**. Do not
     hard-code an allowlist of "these jobs are fine" — an empty set is the
     entire point; any non-empty result is the regression this test exists to
     catch.
  4. Register the new test's coverage in `tests/architectural/ci_topology_census.json`
     if that census's `worklist`/`rule` mechanism requires a row for a new
     architectural check (follow the same "derived, not hand-typed" pattern the
     file's own `_comment` documents — regenerate via the tool the census names
     rather than hand-editing the JSON, if such a tool covers this file; if the
     census only tracks `src/specify_cli/*` directory coverage-shard ownership
     and has no slot for a workflow-topology assertion, state that explicitly in
     this WP's Activity Log rather than forcing an entry that does not fit).
  5. Confirm the test fails (red) against a deliberately-reintroduced gate — add
     one temporarily, run the test, confirm it catches it, then remove the
     temporary gate before committing (ATDD-first, C-011).
- **Files**: `tests/architectural/test_ci_quality_path_filters.py`,
  `tests/architectural/ci_topology_census.json` (only if the register step
  applies)
- **Validation checklist**:
  - [ ] The new test passes against the post-T019/T020 workflow.
  - [ ] The new test fails when a `.result != 'failure'` or `.result ==
        'success'` gate is manually reintroduced into any job's `if:` block
        (proven during development, not asserted).
  - [ ] The test does not use an allowlist that would silently permit a new
        gated job.
- **Edge Cases**: A job's `if:` may be a plain string, a `>-` folded block
  scalar, or absent entirely (defaults to always-run) — the regex scan must
  handle all three without raising on a job with no `if:` key.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. This WP branches from WP02's
landed base (it depends on WP02's fixture fix and shares no files with it).
Completed changes merge back into `pr/review-verdict-write-integrity-01KZ1CGF`
unless the human explicitly redirects the landing branch.

## Definition of Done

- **No result-gated edge remains on any shard job** — this is a rule the
  reviewer re-derives, not a count to check off. Concretely:
  `grep -nE "needs\.[[:alnum:]_-]+\.result\s*(!=\s*'failure'|==\s*'success')"
  .github/workflows/ci-quality.yml` returns hits **only** on named non-shard
  aggregator jobs (today: `consumer-compatibility`'s unrelated
  `needs.build-wheel.result == 'success'` gate, a release-packaging
  dependency, not a coverage shard — enumerate any other such exception you
  find explicitly, by name, in this WP's Activity Log; do not silently expand
  this exception list without naming what you added and why). A hardcoded
  edge count in this bullet is exactly what NFR-007 exists to forbid — this
  mission has already pinned three wrong counts elsewhere (WP01's writer/
  resolver/reader census) and one wrong count in this very WP's own first
  draft (the "22" this bullet used to assert, which both undercounted Class 1
  by eight edges and did not even sum correctly against its own per-class
  breakdown). T021's topology assertion is the standing, re-derivable form of
  this same rule — it must be what the reviewer trusts, not a list in this
  file.
- Every edited job's `needs:` array and dorny path-filter condition is
  unchanged — only the `.result` gating clauses are removed.
- The new topology assertion in `test_ci_quality_path_filters.py` passes on
  the current workflow and reds when any result-gating clause is reintroduced.
- `fast-tests-review` runs and reports coverage for `src/specify_cli/review`
  independent of `fast-tests-status`'s outcome — this is the independent test
  named in tasks.md and must be demonstrated, not just inferred from the diff.
- `mypy --strict` and `ruff` are clean on the touched test file.
- The workflow YAML parses and, if `act`/local workflow linting is available,
  passes it.
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Undercounting the edge set**: a prior pass on this mission fixed one edge
  and stopped; a second pass fixed six jobs and stopped, still missing eight
  more edges on jobs (`fast-tests-doctrine`, `fast-tests-core-misc`,
  `fast-tests-charter`, `fast-tests-agent`, `mission-loader-coverage`) neither
  pass had named. Mitigate by **re-deriving the edge set from a fresh grep of
  the live workflow** (T019/T020 step 1) every time, rather than trusting any
  hand-typed list in this file — including the ones in this file's own
  Objective section, which are a known starting point, not a closing
  definition. A regex that misses a folded-string `if:` block or unusual
  spacing is a real risk too; mitigate that specific risk by testing your
  regex against a deliberately-folded `if: >-` block during development, not
  by falling back to a hand-typed list instead of a regex.
- **Severing a real dependency by mistake**: removing a `needs:` array entry
  (rather than just the `.result` condition) would break artifact handoff
  (e.g. coverage XML consumed by `diff-coverage`). Mitigate by diffing only the
  `if:` blocks and confirming `needs:` arrays are byte-identical pre/post edit.
- **A new job added mid-WP by an unrelated concurrent change**: the topology
  assertion (T021) is what prevents this from silently regressing after this
  WP lands — treat its own robustness (no allowlist, no per-job exemption) as
  load-bearing, not incidental.

## Reviewer Guidance

- Confirm the reviewer independently re-derives the full result-gated edge
  set by running the T019/T020 grep against the workflow file themselves,
  rather than trusting the diff's line count or this prompt's named-job
  list — a partial fix that only touches the six originally-named `fast-
  tests-*` jobs (missing `fast-tests-doctrine`, `fast-tests-core-misc`,
  `fast-tests-charter`, `fast-tests-agent`, `mission-loader-coverage`) is the
  most likely shortcut and must be rejected, as must one that only touches
  the `fast-tests-review` edge (the one directly blocking this mission's own
  coverage).
- Confirm no `needs:` array changed — only `if:` condition lines.
- Confirm the new architectural test in `test_ci_quality_path_filters.py`
  was proven red against a reintroduced gate during development (ask for the
  before/after run, or re-add a gate locally and confirm it catches it).
- Confirm `fast-tests-lanes`, `fast-tests-core-misc`, `fast-tests-charter`,
  and `fast-tests-agent` (each two edges) and `integration-tests-sync` /
  `integration-tests-sync-real-port` (two jobs, one counterpart) were not
  undercounted.
- Confirm the reviewer does not accept a PR description's restated edge count
  at face value — the DoD's own completion criterion is the grep returning
  zero non-aggregator hits, not a number.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP05 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
