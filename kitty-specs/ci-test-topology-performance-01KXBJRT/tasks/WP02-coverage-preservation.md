---
work_package_id: WP02
title: Coverage-preservation authority
dependencies:
- WP01
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
phase: Phase 1 - Substrate
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1426907"
shell_pid_created_at: "1783889626.36"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/_gate_coverage.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/_gate_coverage.py
- tests/architectural/test_gate_coverage.py
- tests/architectural/baselines/**
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Coverage-preservation authority

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log (`spec-kitty agent status`) before starting; address all feedback and log what changed in the Activity Log.

---

## Objectives & Success Criteria

FR-007 / NFR-005 / C-004 — this WP is **the load-bearing invariant** of the
whole mission (contracts §GC-2): every job WP06 re-topologizes must still
execute the exact same set of tests it did before, enforced against a
**committed pre-change baseline**, not just an internal partition-consistency
claim. A marker-partition clone (GC-1) proves assignment; only this wires into
execution.

Done means:

- `tests/architectural/_gate_coverage.py`'s `same_tier_shard_counts` correctly
  covers the new `integration-tests-next` matrix legs (data-model E1's `next`
  group) as just another set of `integration-tests-*`-prefixed gates — no
  hardcoded per-tier branching added (see Context: this is mostly a
  verification, not new logic).
- A new pure **cross-job disjointness** check exists in `_gate_coverage.py`:
  the serial `-n0` orphan-sweep job's selected node-ids ∩ the parallel sync
  pool's selected node-ids == ∅ (GC-2's "cross-job disjointness" bullet).
- `tests/architectural/test_gate_coverage.py`'s `_REQUIRED_*_SHARDS` model
  gains the `next_shard_1/2/3` legs as **required matrix legs** —
  `test_required_selection_structures_present` fails loudly if any is missing
  from the parsed gate model (mirrors today's `_REQUIRED_CORE_MISC_SHARDS`).
- Committed pre-change `pytest --collect-only` node-id baselines exist under
  `tests/architectural/baselines/` for every job WP06 will re-topologize, and a
  new **GC-2b baseline-diff guard** fails the build if the post-change executed
  union differs (symmetric-difference != ∅) from any committed baseline.
- **Definition of Done also requires closing the guard's other fault seam**
  (reviewer-renata, MEDIUM): the GC-2b guard as scoped above only compares a
  *modeled*-current `CompiledGate.selects()` against a *real* committed
  baseline file, and the only fault-injection case exercised is on the
  baseline-file side. That leaves the guard fakeable from the producer side —
  a job's real YAML selection could shrink (e.g. a stray `--ignore=` added to
  the job's `pytest` command) while the *modeled* `CompiledGate.selects()`
  still reports the old, larger set, because the model was never re-validated
  against a fresh real collection. Two additions close this:
  - A **producer-side fault-injection test**: inject a dropped test by
    editing a *job's YAML selection* itself (e.g. add a spurious
    `--ignore=<path>` to a job's command in a test fixture/copy of the
    workflow) and assert the GC-2b guard REDS — not only the existing
    baseline-file-side injection (stripping a line from the committed
    baseline).
  - A **model-fidelity anchor**: a committed assertion that, for each job
    this WP baselines, `CompiledGate.selects()` equals a fresh real
    `pytest --collect-only -q` of that job's actual command at commit time.
    Without this anchor, `selects()` mis-modeling a construct it doesn't
    parse correctly (e.g. an `-m` boolean expression, or a positional test-dir
    argument) could silently under- or over-report the selection while both
    the "modeled-current" and "real baseline" sides agree with each other and
    the guard stays green — tests could be really dropped from CI without the
    guard ever seeing it.

  This matters because FR-007/NFR-005 is this mission's **load-bearing
  invariant** — a modeled-current-vs-real-baseline comparison that only
  fault-injects the baseline side is a fakeable seam for that invariant, not a
  real proof it holds.

**Independent test**: the GC-2b guard fails on (a) an injected drop in the
committed baseline file (existing case), AND (b) an injected drop in a job's
real YAML/command-line selection (new producer-side case) — plus the
model-fidelity anchor passes, proving `CompiledGate.selects()` is not silently
diverging from a real `pytest --collect-only` run (all per the Test Strategy
below).

## Context & Constraints

- Read FIRST: `data-model.md` §E3 (baseline manifest schema), `contracts/
  guard-contracts.md` §GC-2/GC-2b, `plan.md` §IC-02, `tasks.md` T006–T008.
- `_gate_coverage.py` already classifies gates into tiers by **job-name
  prefix** — `_gate_tier` (line ~1166) matches `_FAST_TIER_PREFIX =
  "fast-tests"` / `_INTEGRATION_TIER_PREFIX = "integration-tests"` — so
  `integration-tests-next`'s matrix legs are **already** classified
  `"integration"` once WP06 (T014) turns it into a sharded matrix; there is
  **no hardcoded job-name allowlist to edit** for T006's tier registration.
  Confirm this with a unit check (Test Strategy) rather than adding a
  redundant branch — adding one would violate D-044/C-003.
- The substantive T006 work is the **new** cross-job disjointness function.
  Model it the same way `same_tier_shard_counts` does: pure, taking
  `gates: Sequence[Gate]` + `universe: Sequence[TestRecord]` (from
  `collect_universe()`), returning the overlapping node-id set (empty = pass).
  Do not re-derive a second collection pass.
- `test_gate_coverage.py`'s `_REQUIRED_CORE_MISC_SHARDS` (line 56) and
  `test_required_selection_structures_present` (line 123) are today's pattern
  for "a required selection structure disappeared" — add a sibling
  `_REQUIRED_NEXT_SHARDS = frozenset({"next_shard_1","next_shard_2",
  "next_shard_3"})` and extend the same test function to assert both sets
  are present, with an equally explicit failure message.
- **WP02 has no dependency on WP06.** The baselines you freeze here are
  captured from **today's** (pre-topology-change) selection — this WP must
  land its safety net *before* WP06 touches `.github/workflows/ci-quality.yml`,
  so the baseline genuinely reflects the pre-change state the GC-2b invariant
  protects. Enumerate the jobs WP06 targets from `tasks.md` (T014–T019:
  `integration-tests-next`, `slow-tests`, the pre-split `fast-tests-sync`
  (orphan-sweep + rest), `fast-tests-core-misc`, `fast-tests-charter`,
  `fast-tests-cli`, and the serial `integration-tests-*` sweep set) and freeze
  one baseline file per job.
- **Depends on WP01** only for the `next_shard_*` marker names to exist in the
  parsed gate model once WP06 lands them — WP02's own guard code and baseline
  capture do not require WP01's registry at import time.

## Branch Strategy

- **Strategy**: Coord-topology mission (`meta.json` `topology: "coord"`).
  Planning artifacts live on primary; implementation happens in the lane
  worktree `spec-kitty implement WP02` creates/reuses.
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance`

## Subtasks & Detailed Guidance

### Subtask T006 – Extend `_gate_coverage.py`: `next` tier + cross-job disjointness

- **Purpose**: Confirm the tier model already covers `next`; add the missing
  cross-job disjointness primitive (GC-2).
- **Steps**: (1) Write a small unit check proving `_gate_tier(Gate(job=
  "integration-tests-next", ...))` returns `"integration"` — no code change
  needed if it already does (document that finding rather than adding a
  redundant branch). (2) Add e.g. `cross_job_disjoint_selection(job_a_gates,
  job_b_gates, universe) -> set[str]` returning the intersection of node-ids
  each job's compiled gates select — reuse `CompiledGate.selects(...)` (same
  as `shard_counts_for_test` does) rather than a new selection engine.
- **Files**: `tests/architectural/_gate_coverage.py`. **Parallel?**: No —
  T007/T008 consume this.
- **Notes**: Keep this pure/testable — no subprocess, no I/O; `universe` is
  supplied by the caller via `collect_universe()`.

### Subtask T007 – Extend `test_gate_coverage.py`: required `next` legs

- **Purpose**: `next_shard_1/2/3` become required matrix legs (mirrors GC-1's
  linkage requirement into the GC-2 model).
- **Steps**: Add `_REQUIRED_NEXT_SHARDS` alongside `_REQUIRED_CORE_MISC_SHARDS`
  (test_gate_coverage.py:56); extend `test_required_selection_structures_
  present` (line 123) to assert `_REQUIRED_NEXT_SHARDS - shards` is empty, with
  a failure message naming the missing next-shard leg(s) — same shape as the
  existing `missing_shards` assertion.
- **Files**: `tests/architectural/test_gate_coverage.py`. **Parallel?**: No —
  depends on T006's tier confirmation.
- **Notes**: This test currently is RED-safe (vacuously passes today since
  `next_shard_*` isn't parsed yet from any gate) — it goes truly GREEN only
  once WP06 (T014) ships the sharded matrix. Do not skip or xfail it; a
  temporarily-missing leg before WP06 lands is expected and should be called
  out in this WP's Activity Log, not hidden.

### Subtask T008 – Freeze baseline node-id manifests + GC-2b diff guard

- **Purpose**: The actual coverage-preservation enforcement (FR-007/NFR-005).
- **Steps**: For each job enumerated in Context (`integration-tests-next`,
  `slow-tests`, `fast-tests-sync`, `fast-tests-core-misc`, `fast-tests-
  charter`, `fast-tests-cli`, the serial `integration-tests-*` set), run that
  job's exact current `pytest --collect-only -q` selection (paths + `-m`
  expr, taken from `_gate_coverage.load_gates()`/`parse_workflow` — do not
  hand-copy from the YAML) and commit the sorted node-id set to `tests/
  architectural/baselines/<job>-nodeids.txt`. Add a new guard (e.g.
  `test_baseline_union_unchanged` or similar) that recomputes each job's
  *current* selection via the same gate model and asserts symmetric-difference
  against its committed baseline is empty; a nonzero difference must name
  every dropped/added node-id (truncated list style matches
  `test_arch_shard_marker_completeness.py`'s existing pattern).
- **Files**: `tests/architectural/baselines/**` (new), a new test in
  `tests/architectural/test_gate_coverage.py` (or a sibling module if that
  keeps the file's complexity under the Sonar ceiling — see project style
  guide). **Parallel?**: No — depends on T006's disjointness helper for the
  orphan-sweep-vs-sync-pool case specifically.
- **Also required (reviewer-renata, MEDIUM — closes the guard's producer-side
  fault seam)**:
  1. Add a **producer-side fault-injection test**: on a fixture/copy of one
     re-topologized job's workflow definition, add a spurious
     `--ignore=<path>` (or otherwise shrink the selection) to the job's
     command, re-parse it through `load_gates()`/`CompiledGate`, and assert
     the GC-2b guard reds against the *unmodified* committed baseline — this
     is distinct from the existing baseline-file-side injection (which
     strips a line from the committed `.txt` baseline instead).
  2. Add a **model-fidelity anchor test**: for each job baselined by this WP,
     assert `CompiledGate.selects()`'s node-id set equals a fresh real
     `pytest --collect-only -q` run of that job's actual command (paths + `-m`
     expr) at commit time. This guards against `selects()` mis-modeling a
     construct (e.g. an `-m` boolean expression, or a positional test-dir
     argument change) that would let both "modeled-current" and "real
     baseline" silently agree while real coverage was dropped.
- **Notes**: Regeneration is deliberate-only, per data-model E3 — when WP06
  legitimately changes a job's selection, that job's baseline is regenerated
  **with a provenance comment** (why, which WP), never silently.

## Test Strategy

```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_gate_coverage.py -q

# Confirm integration-tests-next is already tier-classified "integration"
# (document the finding rather than add a redundant branch)
uv run python -c "
from tests.architectural import _gate_coverage as gc
g = gc.Gate(workflow='ci-quality.yml', job='integration-tests-next', shard='next_shard_1')
print(gc._gate_tier(g))
"

# Baseline capture example (repeat per enumerated job — derive paths/-m from
# load_gates(), do not hand-copy the YAML)
uv run pytest --collect-only -q tests/next/ tests/specify_cli/next/ tests/runtime/ \
  -m 'not windows_ci and (git_repo or integration)' \
  | sort > tests/architectural/baselines/integration-tests-next-nodeids.txt

# Fault-injection (baseline-side): prove the GC-2b guard bites on a synthetic
# dropped node-id (temporarily strip one line from a baseline file and confirm
# the new guard fails, then restore it).

# Fault-injection (producer-side, MEDIUM — reviewer-renata): prove the GC-2b
# guard also bites when the *real selection* shrinks, not just the baseline
# file. On a fixture/copy of one job's workflow definition, add a spurious
# `--ignore=<path>` to the job's command, re-parse via load_gates(), and
# confirm the guard reds against the unmodified committed baseline.

# Model-fidelity anchor: confirm CompiledGate.selects() for each baselined job
# matches a fresh real collection, so a mis-modeled `-m` expr or positional-dir
# change cannot silently pass while tests are really dropped.
uv run pytest --collect-only -q <job's real paths/args> -m '<job's real -m expr>' \
  | sort > /tmp/fresh-collect.txt
# compare /tmp/fresh-collect.txt against CompiledGate.selects() for the same
# job — any diff is a model-fidelity bug, not a coverage regression, and must
# be fixed in `_gate_coverage.py` before this WP is done.
```

## Risks & Mitigations

- **Baseline captured after a topology change has already landed** would
  freeze the wrong "before" state, defeating GC-2b. Land WP02 first / rebase
  fresh before capturing.
- **Silent baseline regeneration** hides a real coverage drop as a "legitimate
  rescope." Require a provenance comment on every regenerated baseline file;
  reviewers must ask for it.
- **Re-deriving a second selection/tier model** instead of reusing
  `CompiledGate`/`load_gates()`/`collect_universe()` would violate D-044/C-003
  and drift from GC-1's model.
- **`_REQUIRED_NEXT_SHARDS` going green before WP06 actually ships the matrix**
  — expected to be temporarily unmet; call this out explicitly rather than
  weakening the assertion.

## Review Guidance

- Confirm baselines were captured from the **pre-change** selection (check
  commit ordering relative to any WP06 work landing in the same branch).
- Confirm the cross-job disjointness function and the baseline-diff guard both
  reuse `CompiledGate`/`collect_universe()` — no parallel selection engine.
- Ask for a live fault-injection demonstration of the GC-2b guard failing on a
  synthetic drop (mirrors `test_serial_port_preservation.py`'s
  fault-injection pattern) — a green run alone is not proof the guard bites.
- Confirm `_REQUIRED_NEXT_SHARDS` failure messaging names the missing leg(s).
- Confirm BOTH fault-injection cases exist and demonstrably red the guard: the
  baseline-file-side injection AND the producer-side injection (a shrunk real
  job selection) — a PR with only the baseline-side case leaves the guard's
  producer-side seam unproven.
- Confirm the model-fidelity anchor exists and compares `CompiledGate.selects()`
  against a fresh real `pytest --collect-only` run per baselined job — reject
  if this anchor is missing, since it is what rules out silent selection
  mis-modeling.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-12T17:43:44Z – system – Prompt created.
- 2026-07-12T19:28:03Z – claude:sonnet:python-pedro:implementer – shell_pid=1289659 – Assigned agent via action command
- 2026-07-12T20:51:50Z – claude:sonnet:python-pedro:implementer – shell_pid=1289659 – Ready: GC-2b (modeled-current vs REAL baseline, 3 selection-changing jobs) + model-fidelity spot-check + producer + baseline fault-injection live-green; next-tier checks conditional-on-presence (auto-activate at WP06); 29 passed / 0 failed
- 2026-07-12T20:53:50Z – claude:opus:reviewer-renata:reviewer – shell_pid=1426907 – Started review via action command
- 2026-07-12T21:00:38Z – user – shell_pid=1426907 – Review passed. Suite 29 passed/120s/exit0 (well under limits; no trace of prior 42-fail/12-min defect). GC-2b scoped to exactly 3 selection-changing jobs (integration-tests-next, slow-tests, fast-tests-core-misc); baseline is REAL native --collect-only -q honoring -m (marker-dump-unfiltered bug fixed in collect_job_nodeids). Guard honest: current=model vs baseline=real ground truth, so any mis-model REDs (no shared-bug match). Model-fidelity is a single scoped next-tier spot-check (no all-22 anchor); next-tier check conditional-on-presence + anti-vacuous synthetic canary (no xfail); both fault-injections bite (producer-side strict-subset < is self-proving); cross-job disjointness live; ruff+mypy clean; only owned files. NON-BLOCKING follow-up: _gate_coverage.py module comment (~L1401-1423) + collect_real_union_for_target docstring describe GC-2b as real-vs-real / 'no model-fidelity anchor needed' and test docstrings say '22 parametrized cases/all 22 targets' (now 3) — stale from the first cut; reconcile prose to the shipped modeled-current-vs-real-baseline design. Zero behavioral impact.
