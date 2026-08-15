# Design-Decisions Tracer — modular-per-package-ci

## DD-01 (WP01): reusable-workflow extraction ripples through the CI-model guards

**Context.** WP01 extracted `kernel-tests` into `.github/workflows/module-kernel.yml`
(`on: workflow_call`) invoked as a `uses:` caller inside `ci-quality.yml`. This is decision
D1(a). The POC's real purpose was to de-risk the "highest-effort integration point" the research
flagged: the architectural CI-model guards that parse `ci-quality.yml`'s job graph.

**Finding (the load-bearing one).** When a job becomes a `uses:` caller, its `steps:` (and therefore
its `--cov` emitters, positional test paths, markers, and "runs tests" property) physically move into
the called workflow. The guards key those properties off the caller job's inline steps, so they all
mis-read the caller as emitting nothing / running no tests. **Six guards trip, one root cause:**

| Guard (test) | Assertion that breaks | Owned by |
|---|---|---|
| `test_ci_collection_completeness::test_every_test_node_is_collected_on_a_push_to_main` | 344 `tests/kernel` nodes orphaned (no push job collects them) | WP01 ✅ FIXED |
| `test_coverage_consumer_needs::test_coverage_consumers_depend_only_on_emitters` | `diff-coverage.needs` includes `kernel-tests`, now seen as non-emitting | *(unscoped)* |
| `test_workflow_coherence::test_diff_cover_critical_paths_are_cov_backed_live` | `src/kernel/*` critical path now "unbacked" (emitter moved out of ci-quality) | *(unscoped)* |
| `test_workflow_coherence::test_every_filter_glob_is_live` | new `kernel` glob `.github/workflows/module-kernel.yml` flagged "dead" | *(unscoped)* |
| `test_src_filter_coverage::test_every_named_group_gates_a_test_running_job_live` | `kernel` group gates no test-running job (caller seen as non-test) | *(unscoped)* |
| `test_src_filter_coverage::test_catch_all_ignore_lists_mirror_owned_roots_live` | `tests/kernel` "owned by no shard" | *(unscoped)* |

**Fix applied (WP01, committed, tested).** The collection model now resolves reusable-workflow
delegation: `WorkflowModel.job_uses` records a job's local `uses:` target, and `active_job_keys`
marks the called workflow's jobs active whenever the push-gated caller is active (so the module's
gate is "on push" via its caller). Focused unit tests + the RED-first extraction test pass; the 3
guards in WP01's declared surface (`test_ci_collection_completeness`, `test_ci_quality_path_filters`,
`test_coverage_root_collisions`) are green; ruff + mypy clean.

**Scope feedback (feeds WP03).** WP01 declared only 3 guard files; the POC proved the affected
surface is broader — `test_coverage_consumer_needs.py`, `test_workflow_coherence.py`, and
`test_src_filter_coverage.py` also need delegation-awareness. WP03 ("update the CI-model guards")
should own the full set. (Also confirmed: `test_release_ci_ownership.py` named in planning does not
exist in-tree — drop it; the real set is the six above.)

**Two viable completion designs (for the guard-refactor step):**
- **(A) Resolve delegation per consumer** (what WP01's collection fix does): keep `module-kernel.yml`
  first-class in `WORKFLOW_FILES`; teach each remaining guard to attribute a caller job's
  emitter/path/test-running role from its delegate. Localized, but repeated in ~5 places.
- **(B) Splice at parse time**: treat a `uses:`-only reusable workflow as *not* an independent suite
  runner (exclude from `discover_pytest_workflows`), and splice its steps into the caller job when
  building `ci-quality.yml`'s model/gates, so the refactor is transparent to every consumer. Cleaner
  conceptually; needs a cross-file resolution and care to avoid double-counting the module's own
  gate.

**Recommendation.** Do the remaining guard work as a dedicated, full-arch-suite-CI-verified step
(guards touch frozen-baseline-adjacent invariants; `docs/development` says don't run the full arch
suite locally — push and let CI run `tests/architectural/`). Lean (B) for cohesion; (A) is the proven
incremental path. This is expected POC output, not a defect: WP01 has de-risked and mapped the cost.

**Status.** WP01 kept `in_progress` (NOT `for_review`): the extraction + collection fix are correct
and committed, but 5 guards remain red, so the WP is honestly not green (red-first / no green-wash).

---

## DD-02 (WP03): design (B) implemented — all guards green (RESOLVED)

Design **(B)** was chosen and implemented in `_gate_coverage.py` (commit `cb76c5f0b`): `_splice_local_uses`
inlines a local `uses:` caller's delegate steps at parse time (in both `load_workflow_model` and
`parse_workflow`), so every consumer sees ci-quality's `kernel-tests` caller as if it ran the delegate
inline. `module-kernel.yml` is dropped from `WORKFLOW_FILES` and excluded from
`discover_pytest_workflows` (reusable-only workflows) so its gate is not double-counted. The optional
`kernel` filter-group entry for `module-kernel.yml` was reverted (it tripped `filter-glob-live`).

**Verified green locally** (all 6 DD-01 guards + the double-count and orphan backstops):
- 56 passed — `test_coverage_consumer_needs`, `test_workflow_coherence`, `test_src_filter_coverage`,
  `test_coverage_root_collisions`, `test_ci_quality_path_filters`, **`test_same_tier_uniqueness`** (proves
  no double-counted gate).
- 50 passed — `test_ci_collection_completeness` (no orphaned kernel nodes; WP01 delegation tests hold).

ruff + mypy clean. **The full `tests/architectural/` suite must still run on CI** to confirm no
frozen-baseline regression (per `docs/development`, not run locally).

**Remaining WP03 work — doctrine + packs extraction (mechanical, low-risk now).** The splice is generic,
so extracting more modules is now pattern-work. Design note: keep ONE reusable workflow per *job* so the
caller preserves the original job id and its downstream `needs:` (the splice attaches to a single caller):
`packs` → `module-packs.yml` (lift `fast-tests-corpus`, single job, exactly like kernel); `doctrine` →
`module-doctrine-fast.yml` + `module-doctrine-integration.yml` (the two legs `fast-tests-doctrine` /
`integration-tests-doctrine` are separately `needs:`-referenced, so they must stay two distinct caller
jobs, not one two-job workflow). Verify the same guard set after each extraction.
