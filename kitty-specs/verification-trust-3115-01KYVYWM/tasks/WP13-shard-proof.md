---
work_package_id: WP13
title: 'The shard proof: 13 enumerated node-ids under a shard matching CI, quoting the job'
dependencies:
- WP03
- WP05
- WP07
- WP12
requirement_refs:
- FR-011
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T040
- T041
- T042
- T043
history: []
authoritative_surface: scripts/
execution_mode: code_change
owned_files:
- scripts/verify_shard_3115.sh
create_intent:
- scripts/verify_shard_3115.sh
tags: []
tracker_refs: []
---

# WP13 — The shard proof

**Owns exactly one file**, and it is a committed, re-runnable **script**:
`scripts/verify_shard_3115.sh`. The script performs the shard proof — it constructs the two shard
invocations, runs them to files, and prints the per-node-id reconciliation. Its **recorded output** is
the deliverable alongside it. **The prose evidence goes into the mission dossier, written by the
orchestrator on the mission branch**, because `kitty-specs/` may not be written from a lane
(`src/specify_cli/policy/commit_guard.py:84-89`, C-010). The PR body quotes from that record; it is not
a substitute for it. `issue-matrix.json` is likewise the orchestrator's, on the mission branch.

**Blocked by**: WP03, WP05, **WP07** (was WP08, which is retired), WP12. Deliberately **not** blocked on
WP06 or WP14 — **FR-010's budget must not hold the shard proof hostage.**

> ## Ownership resolution (orchestrator, post-tasks)
>
> This WP was authored with `owned_files: []` per the plan's "measurement WP" framing. That is a
> **hard failure**, not a soft one: `build_wp_manifests` (`ownership/validation.py:354-358`) builds a
> manifest only `if fm.execution_mode and fm.owned_files`, so `compute_lanes`
> (`lanes/compute.py:331-336`) raises `LaneComputationError: Executable WP 'WP13' has no ownership
> manifest`, uncaught on both the dry-run (`mission_finalize.py:1062-1073`) and write
> (`:1236`) paths. `execution_mode: planning_artifact` does not rescue it — the WP is skipped before
> the mode is read. Omitting `owned_files` is worse: `infer_ownership` over this body yields
> `tests/cli/**`, `tests/sync/**` and a `src/` path, overlapping five other WPs.
>
> This also corrects the post-plan squad's finding M4, which reasoned that empty ownership yields a
> singleton lane. It does not; it is an error.
>
> **First resolution, and why it was withdrawn.** The post-tasks pass gave WP13
> `docs/development/shard-proof-3115.md`. **That was wrong**, and the post-tasks adversarial squad
> converged on it as this dossier's single CRITICAL. A new page under `docs/` is not one file — it is
> four:
>
> - **Frontmatter** (`doc_status`, `updated`, plus `description:` and `related:`), enforced by
>   `tests/docs/test_docs_structural_lint.py` (`frontmatter_required_fields=("doc_status", "updated")`
>   at `:144`) and by `scripts/docs/description_length_check.py` /
>   `scripts/docs/related_validator.py`, both run `--strict` on every PR.
> - A **`docs/development/toc.yml`** nav entry.
> - A regeneration of **`docs/development/3-2-page-inventory.yaml`** — otherwise
>   `_check_page_inventory_completeness` (`scripts/docs/check_docs_freshness.py:669-697`) emits
>   `INVENTORY-INCOMPLETE` at `severity="error"` for *"markdown file under docs/ is not in the
>   inventory"*.
> - A regeneration of **`docs/development/3-2-docs-retrieval-index.yaml`** — `_check_docs_index_drift`
>   (`:767-812`) emits `DOCS-INDEX-DRIFT`, also `severity="error"`.
>
> Every one of those rulers is a **blocking step of `.github/workflows/docs-freshness.yml`**, which
> runs on every `pull_request`. And **WP13 cannot discharge them in-lane**: `toc.yml` and
> `3-2-page-inventory.yaml` are WP04's `owned_files` and `lane-d`'s `write_scope`, WP13 is `lane-l`.
> WP04 regenerates in `parallel_group` 1; WP13's page would arrive in group 3 — *after* the only
> owner had merged — so the drift would be guaranteed and unfixable without inventing ownership after
> planning.
>
> **Resolved by moving the artefact to `scripts/`.** `scripts/verify_shard_3115.sh` is uniquely owned,
> sits outside `kitty-specs/` so a lane may write it, overlaps no other WP, and carries **no docs
> obligation whatsoever**: every docs ruler in this repo walks `docs/` and only `docs/` —
> `related_validator.py:97`, `description_length_check.py:137`,
> `relative_link_fixer.py:387`, `check_docs_freshness.py`'s `docs_root.rglob("*.md")`, and
> `docs_structural_lint.py`'s `DEFAULT_DOCS_ROOT = "docs"`. **WP01 already owns
> `scripts/repro_3115_render_width.sh` on exactly this basis.** And a script is the better artefact
> anyway: the shard proof is a *measurement*, and a measurement a successor can re-run beats a
> paragraph a successor has to believe.
>
> **One consequence to state honestly:** this WP no longer closes on the pre-review gate's
> `no_coverage` path for the reason originally recorded. It owns a `scripts/` file, so the changed-file
> set is non-empty; the gate will map it to zero *test* targets instead. The printed line may still
> read `no_coverage`, and it is still not a pass — the manual evidence named below is what stands in
> for it. Record that reasoning in the transition note.
>
> Superseded detail from the authoring pass follows, kept because it enumerates the alternatives:
>
>
> **This is transcribed as the plan wrote it and it is not implementable as frontmatter.** The plan
> states *"**owned_files**: none (measurement WP)"* and assigns WP13 to `lane-l` with
> `depends_on_lanes: lane-c, lane-e, lane-g, lane-k`, `parallel_group 3`. **The tooling cannot produce
> that lane**, and the failure is a hard error rather than the singleton lane the post-plan squad's M4
> finding assumed:
>
> - `build_wp_manifests` (`src/specify_cli/ownership/validation.py:354-358`) builds a manifest **only**
>   `if fm.execution_mode and fm.owned_files` — a WP with an empty `owned_files` gets **no manifest**.
> - `compute_lanes` (`src/specify_cli/lanes/compute.py:331-336`) then raises
>   `LaneComputationError: Executable WP 'WP13' has no ownership manifest.` — reached from both
>   `_apply_ownership_inference`'s dry-run path (`mission_finalize.py:1062-1073`) and the write path
>   (`:1236`), **uncaught in either**.
> - **`execution_mode: planning_artifact` does not rescue it** — measured: `build_wp_manifests` skips
>   the WP before the mode is ever consulted, so the same error is raised. (Both `planning_artifact`
>   WPs in `test-stabilization-and-debt-pass-01KSF9HJ` declare a real `docs/` file.)
> - **Omitting `owned_files` entirely is worse**: `infer_ownership` over this WP's body yields
>   `['src/specify_cli/cli/commands/agent/tasks_move_task.py:937-962',
>   'tests/architectural/test_tid251_enforcement.py', 'tests/cli/**', 'tests/sync/**']`, which
>   overlaps WP05, WP06, WP07, WP09 and WP14 and would fail `validate_no_overlap`.
>
> **The two candidate resolutions, neither of which this file takes on its own authority:**
>
> 1. **Declare one uniquely-owned evidence artefact outside `kitty-specs/`** (a lane may not write
>    `kitty-specs/` — C-010) — e.g. `docs/development/shard-proof-3115.md`, with a matching
>    `create_intent` entry. **Cost**: it is scope the plan never authorised, and it changes *why* the
>    gate no-ops — the workspace would resolve, and `no_coverage` would then come from the
>    changed-file path (`tasks_move_task.py:965-980`) mapping a docs file to zero test targets, exactly
>    as on WP14 outcome B. **The "expected `no_coverage`" note below survives either way**, but its
>    stated reason changes.
> 2. **Fold WP13's measurement into an existing lane** (its evidence is a PR-body artefact, and
>    `issue-matrix.json` is written by the orchestrator on the mission branch regardless). **Cost**: it
>    stops being an independently-reviewable package and loses the `blocked_by` edge that keeps it
>    behind WP12.
>
> Until one is chosen, **`/spec-kitty.tasks` finalisation will exit non-zero on this WP.** The plan's
> own rule applies — *"if `/spec-kitty.tasks` produces a lane grouping different from the table above,
> the table is wrong and the computed grouping wins, but the divergence is reported"* — and this is the
> divergence, reported. It is the same class as risk **R16**: *the lane graph diverges from the plan
> and nothing catches it until dispatch.*

## The deliverable: `scripts/verify_shard_3115.sh`

**A committed, re-runnable script, plus its recorded output.** Not a wrapper that prints "OK".

- It **constructs both shard invocations** — the sync shard and the cli shard — with the file and
  `--ignore` selection **copied from `.github/workflows/ci-quality.yml:1124-1133` (sync) and
  `:1540-1546` (cli)**, `--dist loadfile`, and `-m "fast and not windows_ci"`.
- It writes **full output to a file and reads the tail of the file** (NFR-003). It **never pipes a
  suite whose exit status it intends to trust**, and it **never** reports `exit 0` as a result.
- It **echoes the run's own `gw0..gwN` header line**, its `--cov` state and its **collected count**,
  so the distribution is quoted from the run rather than inferred from the runner label (NFR-001).
- It **enumerates the 13 node-ids below** and prints **one line per case with its outcome**, taken
  from the run's own report — so a case deselected by the marker or swallowed by one of the four
  `--ignore`s is **visible as an absence** rather than absorbed into a shard-level tally.
- It **refuses to report a green on an empty collection.** `|| test $? -eq 5` in `ci-quality.yml:1545`
  makes an empty collection a green job; the script must assert a **non-zero collected count** and
  fail loudly otherwise. **NFR-008**: it prints its input count beside any "all passed".
- It runs on a developer machine and on CI without editing. **NFR-004** is honoured by construction:
  the two shards are run **one after the other, never concurrently** — `tests/sync` and `tests/cli`
  sessions spawn real daemons and `pgrep`/port-scan, and siblings reap each other's (16 recorded false
  reds). The script states the wall-clock window of each shard so a collision is reconstructable.

The script is **not** a substitute for the enumerated reconciliation below — it is the thing that
produces it reproducibly. Its committed output is the evidence; the narrative goes to the dossier via
the orchestrator.

## Expected gate no-op, stated in advance

WP13 owns **one file, and it is not a test file**, so the pre-review regression gate's changed-file
path (`src/specify_cli/cli/commands/agent/tasks_move_task.py:965-980`) maps it to **zero test targets**
and the gate will print `Pre-review regression gate: no_coverage — skipping the gate cheaply`.
(Ownership is now non-empty, so `_mt_resolve_pre_review_workspace` at `:937-962` **does** resolve — the
`no_coverage` arrives by the changed-file route, exactly as on WP14 outcome B, not by the
workspace-resolution route.)

**That line is expected and is not evidence of anything.** WP13's `for_review` transition note **must say
so in those words** and **name the manual evidence standing in for it**: the two shard runs below,
**with their job names, conclusions and collected counts**, and the script's recorded output. *A
transition note that lets the `no_coverage` line stand unremarked is the "mechanism reporting success
for having done nothing" shape, one layer up* — which is the thing this mission exists to stop.

## Definition of done — every element of NFR-001, or it is not a measurement

**Nothing below is relaxed by the move to `scripts/`.** Every obligation this WP carried as a docs
page it carries as a script plus a recorded run.

### T040 — the distribution, in full

- **Worker count quoted from the run's own xdist `gw0..gwN` header**, **never inferred from the runner
  label**.
- `--dist loadfile`.
- Marker selection `-m "fast and not windows_ci"`.
- **The exact file and `--ignore` selection copied from `ci-quality.yml:1124-1133` (sync) and
  `:1540-1546` (cli)** — not from memory. The sync shard's four `--ignore`s are
  `tests/sync/test_orphan_sweep.py`, `…daemon_orphan_classification.py`, `…daemon_cleanup_boundary.py`,
  `…issue_1071_singleton_reconfirmation.py`.
- **Whether `--cov` was on.**
- **The collected test count.**
- **NFR-004**: `tests/sync` and `tests/cli` sessions are **not** run in parallel on one machine — they
  spawn real daemons and `pgrep`/port-scan, so sibling sessions reap each other's. 16 recorded false
  reds.

### T041 — the 13 cases, by node-id, each outcome quoted from the run's own report

This WP previously checked only the shard's *properties*, so a case deselected by the marker or
swallowed by one of the four `--ignore`s was **invisible**, with `|| test $? -eq 5` underneath. Taken
from `#3115`'s own "Affected tests" list and resolved against `pytest --collect-only -q` at
`bb2020fea9`:

| # | Node-id (or group) | Reconciliation this WP owes |
|---|---|---|
| 1 | `tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent` | Exact; the WP01 falsifier's own case. File collects **4** |
| 2 | `tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent` | Exact. File collects **12** |
| 3-6 | `tests/cli/commands/test_sync_doctor_consent_health_3030.py` — the issue says **4 param cases**. At `bb2020fea9` the file's only parametrised test is `test_doctor_names_the_action_for_each_project_local_fault_kind`, which collects **3**: `[unparseable-…-REPAIR THE FILE'S SYNTAX]`, `[wrong_shape-…-MAKE THE DOCUMENT A MAPPING]`, `[unusable-…-CORRECT THE FIELD VALUE]`. File total: **15** collected | **A real discrepancy, to be reconciled and not absorbed.** The issue's fourth case is either a since-removed parametrisation or a fourth non-param case in that file. WP13 quotes the collected set, names which, and **either identifies the fourth node-id or records its absence as a named exclusion with the reason**. *Reporting "3 of 4 passed" without saying which is missing does not close this* |
| 7 | `tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve` | Exact |
| 8-9 | `tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll` — the issue says **2**; the class collects **7** at `bb2020fea9` | WP13 **names which two the issue meant, or runs all seven and says so, quoting each outcome**. *"`TestPurgeAll` passed" without naming the cases does not satisfy this* |
| 10-12 | `tests/sync/test_consent_write_refusal_3030.py` — the issue says **3 param cases**. The only 3-wide parametrisation in that file at `bb2020fea9` is `test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-in]` / `[opt-out]` / `[server]`. **File total: 29 collected**, including two 8-wide parametrisations (`test_no_setter_rebuilds_the_index_from_an_empty_document`, `test_every_setter_still_writes_a_readable_index`) | WP13 **confirms this identification against the collected set, or names the three it ran and why**. **Corrected post-tasks**: the earlier **69** in this row was an *aggregate* across more than one file, not this file's total. Re-measured with `pytest --collect-only -q` on that single file: **`29 tests collected`** |
| 13 | `tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after` | The sync half's own case. **Its outcome is reported whether or not WP06 converged**; a red here is FR-010's business, **not a reason to withhold the shard result** |

**Three of these rows are unresolved node-id ambiguities the plan records as explicit reconciliation
obligations — rows 3-6, 8-9 and 10-12. Do not invent node-ids to make a flat list of 13.** Each is
closed by *naming what was collected and what was run*, or by *naming the absence as a deliberate
exclusion with its reason*.

### T042 — absences, repetition, and the job

- **Any enumerated node-id absent from the collected set is named and explained** — marker-deselected,
  swallowed by one of the four `--ignore`s, or renamed since the issue was written — and an absence is
  closable **only** by naming it as a deliberate exclusion with its reason.
- **All 13 pass, run twice** (SC-009), **with each run's collected count quoted**.
- **Any CI claim names the job** (`fast-tests-cli`, `fast-tests-sync`), **its conclusion**
  (`success` / `skipped` / `failure`) **and its collected count**. **A claim that `fast-tests-sync`
  passed is rejected if that job's conclusion was `skipped`.** *A workflow conclusion is not evidence*
  — a workflow is green when its path-filtered jobs are skipped.
- **A shard-level `N passed` with no per-node-id reconciliation does not satisfy this WP**, because
  `|| test $? -eq 5` (`ci-quality.yml:1545`) makes an **empty collection a green job**.

### T043 — the gate note, and re-measurement

- The `for_review` transition note states the `no_coverage` line is **expected**, states that it
  arrives by the **changed-file** route rather than the workspace-resolution one, and names the manual
  evidence standing in for it (see above).
- **Re-measured at the merge commit if WP12, WP06 or WP14 lands after WP13's first pass.** WP06 and
  WP14 own `tests/sync/tracker/test_saas_client.py`, which carries **node-id 13**. WP13 is deliberately
  **not** blocked on them — but **a pass taken before they land states the commit it was taken at**, and
  **node-id 13's outcome is re-quoted afterwards**. Re-running `scripts/verify_shard_3115.sh` is what
  makes that cheap, which is the point of committing it.

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-002**: if the shard runs in a `git worktree`, state `PYTHONPATH=$WT/src` or a
dedicated venv created **inside** the worktree — otherwise the run imports the live tree and the
isolation only *looks* performed. **NFR-003**: output to a file, tail of the file read; quote the count
line, never "exit 0"; **an empty output file is no measurement**. **NFR-008**: every count line carries
its collected count.

### Known pre-existing failures — name them and move on

`tests/architectural/test_tid251_enforcement.py` (4 tests) ·
`test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out` · the
two `test_safe_commit_cmd::…_3033` ·
`test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed` ·
`test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load) · subprocess
daemon tests reporting `ModuleNotFoundError: No module named 'typer'` (environmental). **Do not chase,
do not fix in-PR, do not retry to green.**

## Files other agents hold

**Everything except `scripts/verify_shard_3115.sh`.** In particular: `docs/development/toc.yml`,
`docs/development/3-2-page-inventory.yaml` and `docs/development/3-2-docs-retrieval-index.yaml` are
**WP04's** and **this WP adds no page under `docs/`** — that is the whole reason the artefact is a
script. `docs/development/testing-parallel.md` is **WP01's**. `issue-matrix.json` and everything under
`kitty-specs/` is the **orchestrator's, on the mission branch** — lanes deliver evidence; the
orchestrator records verdicts. Every file this WP measures — the five `578a659162` files, the two
`tests/sync/` files, `tests/sync/tracker/test_saas_client.py` — is **read-only** here: WP13 *runs* the
suite, it does not edit it. `src/**` is nobody's.
