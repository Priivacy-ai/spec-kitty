# Closeout comments — ci-topology-shrink-01KWQAVX

> **⚠️ POST AT MERGE — DO NOT POST NOW.** The mission is not merged and there is no PR yet.
> Posting "fixed" comments before the branch lands to `main` would be premature/misleading.
> The operator (or a later landing agent) posts these on `gh issue comment` **after** the PR
> merges, substituting the real `<PR link>` / `<merge sha>`. Use `unset GITHUB_TOKEN` if `gh`
> hits a scope error (keyring token has full `repo` scope).

---

## ⚠️ Shared-file coordinate — #2072

`#2072` also re-keys `tests/architectural/_gate_coverage_baseline.json` (the gate-coverage
ratchet baseline). WP06 refreshed this file at closeout:
`total_tests 28573 → 28709` (+136, the added WP02/WP05 invariants), `orphan_test_count 0`,
`duplicate_test_count 3550 → 707` (same-tier consolidation from the WP03 filter-group shrink),
`orphan_files []`.
**A later #2072 agent must rebase onto — not clobber — this refresh**; re-run
`uv run --extra test python -m tests.architectural._gate_coverage --update-baseline` after
merging both, rather than reverting to a stale snapshot.

---

## ⚠️ WP05 post-merge backfill obligations (owned-file edits, must happen post-merge)

Both edits are to `tests/release/ci_topology_timings_postshrink.json` (a WP05-owned file):

1. **Live timings backfill.** Replace `measured_source_run_id` (currently `null`) and
   `measured_critical_path_min` (currently `null`) with the run_id and observed core-misc
   critical-path minutes from **this PR's FIRST post-shrink `ci-quality` CI run**, and
   reconfirm the measured path is ≤ 13.6 min (NFR-001 ceiling). The committed value is a
   scrupulously-labeled structural **projection** (`projection_basis` set,
   `measured_*` null) — it must NOT be dressed as a measurement; the live number is the DoD.
2. **Escape-hatch honesty-note wording fix (LOW-sev).** The
   `escape_hatches_honesty_note` states `ci:full` / `ready-for-ci` "do NOT exist" — that is
   inaccurate: they DO exist in `ci-quality.yml` (≈ lines 1556-57 / 2509-10) as
   **draft/WIP-suppression overrides**, just not `run_all` full-coverage hatches. Correct the
   wording on the same backfill pass. Neither correction affects the C-006 / FR-009
   conclusions.

---

## ⛔ CLOSEOUT BLOCKER — NFR-007 full sweep is RED (must resolve before mission `done`)

WP06's own deliverables are green (gate-coverage baseline refreshed, orphan ratchet green,
issue-matrix terminal, CHANGELOG appended). **But the mandatory NFR-007 full
`tests/architectural/` sweep is RED** — `9 failed, 714 passed, 4 skipped` — so the mission
**cannot honestly reach `done`**. Adjudication of the 9 failures (base worktree at the mission
base `aa998ede7` used as the cross-base control; `origin/main` = `e67f0ab7` is an **ancestor**
of the mission base, so the base is fresh, not stale):

**A. 4× environmental false-reds (NOT a defect) — `test_tid251_enforcement.py`**
`test_raw_sha256_in_formerly_exempt_dir_is_flagged`, `test_annotated_sha256_is_allowed`,
`test_click_exceptions_probe_in_src_is_flagged`,
`test_click_exceptions_probe_in_raw_sha_owner_file_is_flagged`.
They shell out to `ruff`, which is in the `lint` extra, **not** the `test` extra. Running with
`uv run --extra test --extra lint pytest tests/architectural/test_tid251_enforcement.py` → **9
passed**. The CI arch job installs lint deps, so these are green on CI. No action.

**B. 1× foreign-merge / dead-module artifact (NOT this mission's code) —
`test_no_dead_modules.py::test_no_new_dead_modules_under_src`**
Flags `specify_cli.upgrade.migrations.m_3_2_4_derived_views_gitignore_backfill` as a new orphan.
Root cause: the lane's `test_no_dead_modules.py` had the `m_3_2_4` **allowlist entry removed**
(the removal hunk cites `model-discipline-dispatch-binding-01KWPW36 WP03` and #2370 — a
**different** mission's edit that arrived via a merge into the lane), while the lane still carries
the `m_3_2_4` **migration module**. On `origin/main` BOTH the module and the entry are **absent**
(consistent → passes). This is an inconsistency the operator resolves when the mission
rebases/merges onto current `origin/main` (module deleted there); it is not a ci-topology code
defect. **Verify green after merge-to-main.**

**C. ⛔ 4× GENUINE mission gap (BLOCKER, WP03 scope) — pre-existing sibling contract tests
assert the OLD ci-quality topology and were never updated**
- `test_ci_quality_path_filters.py::test_core_misc_integration_is_sharded_and_parallelized` —
  asserts `'architectural'` is a `fast/integration-tests-core-misc` matrix shard. WP03
  **de-serialized** the arch pole into a standalone always-on `arch-adversarial` job (the whole
  #2383 / FR-013 point), so it is no longer a core-misc shard. **Directly superseded by WP02's
  new `test_arch_pole_deserialized.py`.**
- `test_ci_quality_path_filters.py::test_core_misc_excludes_e2e_and_cross_cutting_suites` —
  asserts the literal `--ignore=tests/e2e` in the fast core-misc run script. WP03 parameterized
  the ignores into `${{ matrix.ignore_args }}`, so the literal is gone (moved, not removed). Stale
  literal-shape assertion — needs re-expression against `matrix.ignore_args`.
- `test_ci_quality_path_filters.py::test_execution_context_only_core_misc_runs_focused_parity_gate`
  and `test_ci_architectural_gate_coverage.py::test_status_change_sets_core_misc_bypasses_short_circuit`
  — assert the `needs.changes.outputs.core_misc }}" != "true"` short-circuit-guard string in the
  run script, which WP03's rewrite restructured.

These two files (`tests/architectural/test_ci_quality_path_filters.py`,
`test_ci_architectural_gate_coverage.py`) are **not in any WP's `owned_files`** (WP03 owns only
`.github/workflows/ci-quality.yml`) and appear in **no** campsite/attack-vector list — an
**undiscovered gap**: the mission rewrote the CI topology but left the pre-existing sibling
contract tests asserting the old topology. Per-WP review never caught it (WP03 review ran only
the WP02 8-invariant suite + the #2368 suite, never the full `tests/architectural/`). They pass
on the old-topology base and **will red on `origin/main` after the mission lands.**

**Required before mission `done` (WP03 scope, NOT WP06 — WP06 must not edit WP03-owned test
files):** update or delete (as superseded) the 4 stale assertions in
`test_ci_quality_path_filters.py` + `test_ci_architectural_gate_coverage.py` to match the new
de-serialized/sharded topology, then **re-run the full `tests/architectural/` sweep green** and
**re-refresh `_gate_coverage_baseline.json`** (deleting superseded test functions may shift
`total_tests` down — the refresh must run against the fully-green tree).

---

## #2378 — CI shard-side split: `fast-tests-core-misc` matrix subdivision

> Fixed in mission `ci-topology-shrink-01KWQAVX` (<PR link>, merged <merge sha>) under epic #1931.
>
> `fast-tests-core-misc` is now subdivided into **two disjoint, non-empty matrix shards**
> (WP03, commit `b4cb334e`), with the ignore-mirror kept consistent so a core-misc change no
> longer drags the whole misc bucket through one shard. The shard split is verified by the
> `#2368` substrate suite (57 passed, orphan 0) and the WP02 topology invariants (`shard_universe`
> asserts each shard is non-empty and their union equals the pre-split selection). Terminal at
> WP06 closeout.

## #1933 — CI group-side shrink: map unmapped src dirs to named filter groups

> Fixed in mission `ci-topology-shrink-01KWQAVX` (<PR link>, merged <merge sha>) under epic #1931.
>
> **Intent statement (C-006):** #1933's literal nightly-scheduled-full-suite is deliberately OUT
> of scope; this mission delivers the **shrink interpretation** — fast, targeted PR CI. WP01's
> construction-derived census enumerated the 32 unmapped `src/specify_cli/*` worklist dirs; WP03
> folded them into **six named composite `dorny/paths-filter` groups** (`auth_audit_git`,
> `lifecycle`, `agent_surface`, `closeout`, `governance`, `platform`), each registered atomically
> across all five surfaces (filters block, `changes.outputs.*`, the `unmatched` enumeration, and
> the `JOB_GROUPS` needs-lists). **All 32 worklist dirs are now routed** — a single-area PR runs
> only its focused shard(s) plus the always-on gates.
>
> **The shrink satisfies #1933's intent with no new blind spot (FR-009):** the escape hatches
> remain intact — `workflow_dispatch` `run_all` / `run_extended`, the nightly `schedule` cron
> (`17 2 * * *`), and the `unmatched` fail-closed catch-all — and the nightly `run_all` still
> **over-covers** every worklist dir plus the sub-`T_LOC` catch-all tail. The measured PR critical
> path is structurally ≤ 13.6 min (well under the ~15-min threshold), so **no thin nightly-schedule
> option was taken** (C-006 decision). Terminal at WP06 closeout.

## #2383 — Arch un-blind (P1): architectural + adversarial guards on 100% of src

> Fixed in mission `ci-topology-shrink-01KWQAVX` (<PR link>, merged <merge sha>) under epic #1931.
>
> The `arch-adversarial` job now runs **always-on** (`if: always()`, group-less) over **100% of
> `src/`**, and is **de-serialized** from `fast-tests-core-misc` — its `needs` edge is dropped, so
> the architectural/adversarial pole no longer sits on the core-misc critical path (the path
> collapses from `sum` to `max`, NFR-002). WP02's `arch_unblind` invariant (which red-flagged 13
> blind src dirs pre-mission) and the `arch_pole` de-serialization invariant are green on the
> merged tree. This closes the recurrence class behind the orphan-coverage bugs #2370 / #2379 by
> construction — no src dir can go arch-blind again. Terminal at WP06 closeout.

## #1931 — Epic rollup: CI failure-isolation + topology remediation

> Rollup terminal at closeout of mission `ci-topology-shrink-01KWQAVX` (<PR link>, merged
> <merge sha>).
>
> This mission closes the three constituent issues under this epic:
> - **#2378** — `fast-tests-core-misc` split into 2 disjoint shards.
> - **#1933** — 32 unmapped src dirs folded into 6 composite filter groups (shrink intent;
>   escape hatches + nightly over-cover intact).
> - **#2383** — always-on de-serialized architectural pole over 100% of src.
>
> Also fixed in-flight: the pre-existing **C-005 `mission-loader-coverage` coverage-drop** — it
> emits `--cov=src/specify_cli/mission_loader` yet was absent from `sonarcloud.needs`, so its
> coverage XML was silently dropped from the Sonar gate; WP03 added it to `sonarcloud.needs` and
> WP02's `coverage_consumer` invariant guards the class by construction. The full 8-invariant
> #2368 substrate suite plus the new NFR-002/003/005 + C-005 relations are green (NFR-007), and
> the gate-coverage ratchet baseline is refreshed (orphan 0). Out-of-scope items (#2283 / #2077 /
> #2071) remain deferred-with-followup on their own trackers per the C-004 scope fence.
