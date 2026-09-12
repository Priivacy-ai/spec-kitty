# Expected reds — mission `read-side-seam-primary-primitive-closure-01KYKMMT`

**Authored per WP, append-only.** Each WP owns exactly one `## WPnn` section. Do **not** rewrite
another WP's section — WP01 and WP02 run in parallel lanes, and WP08 reconciles the union of all
sections (its T039 step 6).

> **Why this file lives on the planning branch, not in a lane.** `research/expected-reds.md` sits
> under `kitty-specs/`, and `move-task`'s pre-flight guard blocks `kitty-specs/` changes on a lane
> branch ("planning artifacts must live on `fix/read-side-seam-primary-primitive-closure`") — the
> same rule that makes `finalize-tasks` reject `owned_files` under `kitty-specs/`. The WP prompts
> asked implementers to write here, which is not possible from a lane; **the orchestrator lands
> each section on the planning branch** from the implementer's reported content or by re-deriving
> it from the gate. WP02's implementer correctly refused to `--force` past the guard.

## WP02 — read-side bypass census, terminal shape

**Gate**: `tests/architectural/test_no_read_side_bypass.py::test_no_read_side_bypass_outside_sanctioned_and_allow_listed`
**Status**: **RED by design** (US8 / FR-023). WP02 grew the censused callees 2 → 4 and landed the
end-state sanction set, so the gate now flags every not-yet-routed consumer site. This red is the
mission's acceptance signal; **WP08 T039 greens it.**

**Enumerated finding set — 32 findings** (WP04 4 · WP05 10 · WP06 10 · WP07 8). Re-derived from the gate
itself, not copied. Per-primitive: 31 `primary_feature_dir_for_mission` + 1
`resolve_feature_dir_for_mission`.

**The ratchet each routing WP is held to**: after your WP, this set equals the set below **minus
exactly the sites you routed** — **zero additions**. The node stays red until WP08, so this
per-site diff is the only real signal available to WP04–WP07. A new finding is a regression even
though the node's red/green state did not change.

| Site (`rel_path:line`) | Primitive | Greened by |
|---|---|---|
| `src/runtime/next/runtime_bridge.py:1244` | `primary_feature_dir_for_mission` | WP07 |
| `src/runtime/next/runtime_bridge.py:260` | `primary_feature_dir_for_mission` | WP07 |
| `src/runtime/next/runtime_bridge_identity.py:118` | `primary_feature_dir_for_mission` | WP07 |
| `src/specify_cli/acceptance/__init__.py:860` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/agent_tasks_ports.py:266` | `primary_feature_dir_for_mission` | WP04 |
| `src/specify_cli/cli/commands/accept.py:270` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/cli/commands/agent/mission_feature_resolution.py:145` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/cli/commands/agent/mission_finalize.py:1645` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/cli/commands/agent/tasks_move_task.py:301` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/cli/commands/agent/tasks_move_task.py:699` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/cli/commands/agent/workflow.py:889` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/agent/workflow.py:897` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/agent/workflow_executor.py:1986` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/agent/workflow_executor.py:520` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/agent/workflow_executor.py:680` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/implement.py:1449` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/implement.py:274` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/implement.py:430` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/implement.py:603` | `primary_feature_dir_for_mission` | WP05 |
| `src/specify_cli/cli/commands/mission_type.py:1069` | `primary_feature_dir_for_mission` | WP04 |
| `src/specify_cli/cli/commands/mission_type.py:610` | `primary_feature_dir_for_mission` | WP04 |
| `src/specify_cli/cli/commands/next_cmd.py:190` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/cli/commands/next_cmd.py:269` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/cli/commands/next_cmd.py:671` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/coordination/commit_router.py:657` | `primary_feature_dir_for_mission` | WP07 |
| `src/specify_cli/decisions/emit.py:71` | `resolve_feature_dir_for_mission` | WP04 |
| `src/specify_cli/merge/executor.py:1437` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/retrospective/writer.py:85` | `primary_feature_dir_for_mission` | WP06 |
| `src/specify_cli/status/aggregate.py:499` | `primary_feature_dir_for_mission` | WP07 |
| `src/specify_cli/status/aggregate.py:522` | `primary_feature_dir_for_mission` | WP07 |
| `src/specify_cli/status/aggregate.py:543` | `primary_feature_dir_for_mission` | WP07 |
| `src/specify_cli/status/aggregate.py:791` | `primary_feature_dir_for_mission` | WP07 |

**Cross-check on the corrected arithmetic (A3)**: 34 in-scope sites − 3 in-scope FR-005 foundation
sites (`core/paths.py` ×2, `core/git_ops.py`), now carried by WP02's foundation-sanction seed =
**31 routable**, which is exactly the primary-primitive finding count above. The fourth FR-005
foundation site (`coordination/surface_resolver.py:739`) is the separately-counted sanctioned
single-authority site and was never inside the 34.

### Foreign honest-red P0s — NOT this mission's business (C-010)

| Test | Issue | Why it is red | Rule |
|---|---|---|---|
| `tests/sync/test_sync_consent_default_deny.py` (5 failing) | **#3031** | Red **by design** — honest-red P0 pin per ADR `2026-07-17-1`. Marked `fast`, so it appears in every lane. Surface is `sync/routing.py` / `is_sync_enabled_for_checkout` — the **sync fan-out** sense of "routing", zero overlap with placement. | **Do not touch. Do not green-wash.** Its own docstring flags further #3031 work as not yet pinned, so more may land mid-mission. |

Classification is **by surface, not by timing**: a red is this mission's business only if it touches
a placement/read-path surface the mission owns, or is a demonstrable regression from this mission's
diff.

**Second expected red (T010.3 / NFR-008, cycle-1 fix).** The Live census summary table now
declares the **post-migration end state** rather than the in-flight tree, so
`test_ledger_summary_counts_reconcile_with_the_allow_list_and_themselves` mismatches on the
`Total real call sites` row for both `resolve_feature_dir_for_mission` (declares 7, live finds 8)
and `primary_feature_dir_for_mission` (declares 3, live finds 34), from commit `feb88514f`
onward. **WP08 is the greening owner** — as WP04–WP07 route the remaining sites the live count
converges on the declared end state, and WP08's closeout is what makes the two agree again. The
test asserts the mismatch is limited to **exactly these two primitives** by error-message prefix
rather than hardcoded counts, so it stays meaningful as the live numbers shift during WP04–WP07.

**Lane isolation note (for whoever reconciles the union).** Each lane's red count is measured
against a tree that does **not** contain the other lanes' work: WP01's `168 passed / 3 failed`
was measured without WP02's gate changes, and WP02's `188 passed / 1 failed` without WP01's.
Neither is wrong; they are simply different trees. Verified: WP01's fix commit `6c9ec7f7e` is
**not** an ancestor of lane-b, and lane-b's diff is exactly its two owned files. The aggregate
red set therefore only materialises at merge — which is precisely what WP08 T039 step 6
(reconcile the union of all `## WPnn` sections) exists to check.

## WP03 — extraction + delegation (cycle-1 remediated)

**Half A equivalence** — reviewer-verified: census **46 total / 43 routed / 3 unrouted**, identical
pre/post on both trees; zero call-site changes outside `_read_path_resolver.py` and
`mission_runtime/resolution.py`.

**Half B divergence table** — six real-repo fixtures against `primary_feature_dir_for_mission`:

| Fixture | seam vs blind compose | Attribution |
|---|---|---|
| flat_no_coord · coord_materialized · mission_absent | identical | anchoring |
| coord_husk · coord_branch_deleted · coord_worktree_empty | identical, **no raise** | husk |
| **backfilled** | **seam recovers the existing bare-`<slug>` dir; blind compose returns a non-existent composed path** | **backfill recovery — the ONE accepted divergence (NFR-001)** |

Ambiguous handles now propagate `MissionSelectorAmbiguous` from the wrapper — attributed as
**raising** (C-009: a loud structured error over a silently wrong compose).

### Cycle-1 finding (B1, NFR-009) — a real cycle, invisible to the WP's own stop-signal

The first commit introduced
`read_dir(RETROSPECTIVE) → resolve_retrospective_home → primary_feature_dir_for_mission →
placement_seam(...).read_dir(PRIMARY_METADATA)`. **No `RecursionError` fired** because
`PRIMARY_METADATA`'s leg does not re-enter — **termination was a property of that constant, not of
the call graph**. Both the implementer's designated stop-signal and the orchestrator's verification
were structurally incapable of observing it; an independent reviewer found it by call-graph tracing.

**Fix**: `retrospective/writer.py:85` now calls the module-private leaf
`_compose_primary_feature_dir` directly (forced out-of-map edit — WP06's file, but the cycle existed
immediately and could not wait).

**Proof, by tracing not by absence-of-crash**: `sys.setprofile` on the wrapper's own **code object**
(catching every module binding, not one module's attribute) across **6 fixtures × 16
`MissionArtifactKind` members = 96 traced `read_dir` calls → zero wrapper entries**. Proven
**non-vacuous** by reverting the fix and re-running: exactly **6** wrapper entries appeared, one per
fixture, all on `RETROSPECTIVE`, with a clean `AssertionError` and **still no `RecursionError`**.

**Write-leg delta (B3) — removed.** `resolve_retrospective_home` feeds `canonical_record_path`; under
the delegation it had silently inherited the seam's backfill recovery *and* double-folded the handle.
Re-pointing at the leaf restores it byte-identical to pre-WP03: equal to
`_compose_primary_feature_dir`, not equal to the seam's recovered dir, single canonicalize call.

### Foundation-site record (B2) — a FIFTH foundation site

`retrospective/writer.py:85` (`resolve_retrospective_home`) joins the FR-005 / SC-014 set alongside
`core/paths.py` ×2, `core/git_ops.py`, `coordination/surface_resolver.py`. It sits **beneath**
`PlacementSeam.read_dir`'s `RETROSPECTIVE` chokepoint (`resolution.py:1454`), so routing it through
`read_dir(RETROSPECTIVE)` is unbounded recursion, not a refactor. It must call the leaf directly and
**permanently — including after WP08 deletes the wrapper**. WP06 verifies; WP06 does **not** route it.

A standing regression guard now enforces this:
`tests/retrospective/test_home_resolution_single_authority.py` previously pinned the call to the
wrapper *by name* — that assertion was itself enforcing the regression. It now requires the leaf and
forbids the wrapper, verified red under the reverted state.

### ⚠ Reconciliation owed (raised by WP03, not owned by it)

WP02's ledger still lists `specify_cli/retrospective/writer.py :: resolve_retrospective_home` among
the **31 unrouted `primary_feature_dir_for_mission` sites**. That row is now **stale**: the site calls
the leaf, and per FR-005/NFR-009 its verdict is **`sanction-infra` (verify-only)**, not
`migrate-fail-loud`. Consequence: the enumerated finding set drops **32 → 31** once lane-b and lane-c
merge, and the file/site tallies drop with it. **WP06 owns this single-row correction** (see
`tasks.md` §6); WP08's end-state reconciliation absorbs the count.


## WP04 — topology-routed reads + residuals

**Routed (3 sites)** *(justification correction per WP04 review: `agent_tasks_ports.py:266`'s
nearest downstream read is `spec.md`, not `meta.json` — the kind `PRIMARY_METADATA` is still correct
since all PRIMARY kinds resolve identically, but the earlier "meta.json downstream" note was wrong)*: `agent_tasks_ports.py:266` (`RealFsReader.primary_anchor_dir`),
`mission_type.py:610` (`close_cmd`), `mission_type.py:1069` (`_resolve_mission_handle`) — all
`PRIMARY_METADATA`, each justified by a `meta.json` read one or two lines downstream. The 7
`resolve_feature_dir_for_mission` **stay-lenient** sites were confirmed against WP02's existing
allow-list rows; no code change.

**Ratchet**: finding set **32 → 28**. The 32 → 31 step was WP03's `retrospective/writer.py:85`
fix (recorded in its own section); WP04's own delta is exactly its 3 routed sites. **Zero
additions.**

**T024 test-coverage note (WP04 review):** the one-of-two hole is genuinely closed (reviewer
verified by reading), but there is **no committed behavioural test** — both phase tests monkeypatch
the helpers, and the static gate's message subjects only `get_mission_type(feature_dir)`, so it would
have gone green had only that read been routed. WP08/aggregate should add: a documentation mission on
a coord husk writes `gap-analysis.md` into the PRIMARY dir.

**#2886 CLOSED (T024)**: both `_run_documentation_wiring` reads now resolve through a single
`placement_seam(repo_root, slug).read_dir(PRIMARY_METADATA)` call, and the `gap-analysis.md`
write shares that same resolved dir (SC-007 scenario 2). `test_coord_read_residuals_closeout.py`
**11/11 green** — the red→green transition WP01 set up by removing the `#2214` pin.
**#2707 verified STALE** — already fixed by merged PR #2689; the tracker issue is open but the
code fix has landed.

**T025 husk pin**: non-zero case (3 real `migrate-fail-loud` sites). Pinned red-first in
`tests/specify_cli/missions/test_topology_routed_read_migration.py` for two sites directly; the
third (`close_cmd`) is covered by pre-existing integration tests. **Correction per WP04's review:
reverting WP04's OWN routed line is 9/9 GREEN** — the routing is answer-identical by construction
(the wrapper's WP03 body already *is* `read_dir(PRIMARY_METADATA)`), so no behavioural red-first is
possible for it. The 4-of-9 reds come from reverting the separate #2120 primary re-anchor, not this
WP's change; the husk guarantee is genuinely pinned but that evidence is not WP04's own. A stale test
(`test_tasks_ports.py::test_canonicalizer_fold_is_co_located_inside_the_adapter_method`) pinned
the old wrapper-call shape and was remediated to the seam idiom — `DIRECTIVE_041` **STALE**.

### ⚠ Reconciliation owed #1 — `decisions/emit.py:71`: two authorities disagree

WP02's ledger classifies this site **`migrate-fail-loud` / `STATUS_STATE`**. But
`test_resolution_authority_gates.py`'s **coord-authority** gate (WP01-owned) independently
sanctions the *same call* as a **PERMANENT legitimate coord-owned write bypass**
(`_COORD_WRITE_BY_DESIGN`, allow-list entry, `COORD_AUTHORITY_WRITE_FLOOR`). Verified
empirically: routing it reds **4** tests in that gate (`test_coord_authority_by_design_modules_classified_write`,
`test_every_allowlist_entry_has_live_match`, `test_coord_authority_gate_floor` 3→4,
`test_allowlist_no_stale_entries`).

WP04 owns neither file, so it **reverted the attempt and left the site unrouted** — the right
call. **One of the two ledgers is wrong about this site** and it must be adjudicated before
anyone routes it. This is the single remaining `resolve_feature_dir_for_mission` finding, so it
is also why the ratchet reads 28 and not 27.

### ⚠ Reconciliation owed #2 — WP03's extraction made a WP02 non-vacuity assertion fail

`test_no_read_side_bypass.py::test_sanctioned_modules_are_non_vacuous_for_the_newly_censused_primitive`
now fails:

```
src/mission_runtime/resolution.py is sanctioned but has ZERO real
'primary_feature_dir_for_mission' call sites -- its exclusion would be vacuously
'proved' by a previously-censused primitive's finding only
```

**This is the test working exactly as designed**, not a defect in it. WP03's T016 re-pointed
`resolution.py`'s four internal calls at the extracted leaf, so that sanctioned module no longer
calls the primitive at all — and WP02's per-primitive non-vacuity assertion correctly **refuses to
be vacuously satisfied** by the two historical primitives. It is the anti-vacuity machinery
catching a real change in the tree.

**Owner: WP08.** It is a legitimate consequence of the extraction, it is independent of any
routing WP's diff (verified: `git diff HEAD -- src/mission_runtime/resolution.py` is empty in
lane-d), and WP08 already owns the end-state reconciliation of the sanctioned set. **Every routing
WP will see this red — it is expected and not theirs.** The end-state fix is to drop
`resolution.py` from the sanctioned set for this primitive, since post-extraction it genuinely has
no such call sites.


## WP05 — trio routed, gate greened

**Gate**: `tests/architectural/test_trio_seam_only.py`. **Status: GREEN** (22/22 passed).
Discharges WP01's recorded expected-red #2 and #3
(`test_trio_imports_route_only_through_seam_wrappers`,
`test_allowed_read_path_resolver_names_are_currently_used`) — both were red-by-design
pending this WP's routing; both now pass, verified green *because the positive
assertion holds*, not because a set went empty: planting a leaf-primitive import
(`primary_feature_dir_for_mission`) in `workflow.py` reds both nodes; reverting
restores green (re-run three times during this WP, same result each time).

**10 sites routed** (per-site kind table; downstream filename column is what
justified the kind — a wrong kind is census-invisible by construction, so this is
the only artifact a reviewer can check it against):

| Site | Kind | Downstream justification |
|---|---|---|
| `workflow.py::_analysis_report_gate_dir` | `ANALYSIS_REPORT` | reads `analysis-report.md` (`src/specify_cli/analysis_report.py::ANALYSIS_REPORT_FILENAME`) |
| `workflow.py::_mission_id_for_claim` | `PRIMARY_METADATA` | `resolve_mission_identity` reads `meta.json` (`src/specify_cli/mission_metadata.py`) |
| `workflow_executor.py::implement_sparse_checkout_preflight` | `PRIMARY_METADATA` | `resolve_mission_identity` reads `meta.json` |
| `workflow_executor.py::implement_resolve_mission_type` | `PRIMARY_METADATA` | `get_mission_type` reads `meta.json`'s `mission_type` field (`src/specify_cli/mission.py`) |
| `workflow_executor.py::review_finalize_and_print` | `PRIMARY_METADATA` | `resolve_mission_identity` reads `meta.json` |
| `implement.py::find_wp_file` | `WORK_PACKAGE_TASK` | globs `tasks/WP*.md` |
| `implement.py::_load_primary_anchored_mission_meta` | `PRIMARY_METADATA` | `load_meta` reads `meta.json` |
| `implement.py::_planning_artifact_source_dir` | `PRIMARY_METADATA` | resolves the mission-dir anchor only (the established "resolve a handle to its canonical dir name" idiom — ledger's 6-site slug-canonicalization note) |
| `implement.py::_build_implement_json_payload` | `PRIMARY_METADATA` | `resolve_mission_identity` reads `meta.json` for the `--json` payload's `mission_slug`/`mission_number`/`mission_type` |
| `acceptance/__init__.py::_primary_anchor_feature_dir` | `PRIMARY_METADATA` | anchors `AcceptanceSummary.feature_dir` on the primary identity surface (`meta.json`), never a specific artifact's content |

No trio file imports `primary_feature_dir_for_mission` or
`_canonicalize_primary_read_handle` any longer (confirmed by AST-import grep across
all 8 trio files — the only remaining mentions of either name are prose comments,
not `ImportFrom` nodes).

**5 comments corrected** (workflow_executor.py x3, acceptance/__init__.py x2 — the
#2824 residual). Each now states the true distinction: the *kind-blind* resolvers
(`resolve_feature_dir_for_mission` / `candidate_feature_dir_for_mission`) can select
the coord husk; the *kind-aware seam* short-circuits a PRIMARY-partition kind to
PRIMARY before any coord probe, so it cannot. The `acceptance/__init__.py:1021-1023`
comment (the actual #2824 defect-description residual — the functional fix landed in
`6923d1d40`) previously claimed `lanes.json` is read from the coordination worktree;
corrected to state `LANE_STATE` (`lanes.json`) is itself a PRIMARY-partition kind
(C-001) and is read correctly off the PRIMARY anchor, while `acceptance-matrix.json`
(`ACCEPTANCE_MATRIX`, a genuine COORD-partition kind) is resolved separately inside
`_check_lane_gates` → `_evaluate_acceptance_matrix`, not from the argument this
comment sits beside. None of the 5 corrected comments re-asserts that `lanes.json`
belongs on COORD.

**Zero-additions ratchet** (against
`test_no_read_side_bypass_outside_sanctioned_and_allow_listed`, still red by design
until WP08): live offender count is **21**. Reconciled: 32 (this file's WP02 count)
− 10 (this WP's routed sites) − 1 (`retrospective/writer.py::resolve_retrospective_home`,
already reclassified `sanction-infra` by WP03's cycle-1 fix per this file's WP03
section) = 21. None of the 21 live offenders match any of the 10 sites this WP
routed — zero additions, confirmed by direct diff against the live failure list.

**Discovered gaps, reported not fixed** (neither in WP05's `owned_files`; not
edited):

1. `test_no_read_side_bypass.py::test_sanctioned_modules_are_non_vacuous_for_the_newly_censused_primitive`
   fails: `src/mission_runtime/resolution.py` is sanctioned but shows zero real
   `primary_feature_dir_for_mission` call sites. Root cause: WP03's T016 re-pointed
   `resolution.py`'s four internal composition sites at the extracted leaf
   `_compose_primary_feature_dir` directly (correctly, to avoid the wrapper/seam
   recursion cycle T019's delegation would otherwise create) — but this ledger's
   own "Sanctioned set" prose (§ "Method (WP02 this revision...)") still describes
   `resolution.py` as calling the public wrapper "four sites: the
   mid8/coordination-branch/topology/mission-id resolution helpers", which is now
   stale. Cross-WP (WP02 vs WP03) reconciliation gap, orchestrator-confirmed
   WP08-owned. `tests/architectural/test_no_read_side_bypass.py` is WP02's file —
   not touched.
2. `tests/specify_cli/cli/commands/test_coordination_doctor.py::test_stranded_check_bare_handle_false_negative_under_raw_resolver`
   fails with `RecursionError`. Root cause: this test monkeypatches
   `_read_path_resolver.resolve_planning_read_dir` to simulate "pre-fix raw
   resolver" behaviour by calling `primary_feature_dir_for_mission` from inside the
   patch — but post-WP03-T019, `primary_feature_dir_for_mission` delegates to
   `placement_seam(...).read_dir(PRIMARY_METADATA)`, which calls the (now-patched)
   `resolve_planning_read_dir` internally, closing a self-referential loop the test
   fixture's simulation technique no longer safely avoids. Confirmed **not** a WP05
   regression: reproduced red in an isolated `git worktree` at this lane's true
   starting commit `01ee37a8c` (before any WP05 edit or the WP02-lane merge),
   so it is inherited from WP03's already-approved delegation, unrelated to any of
   the 4 files WP05 owns. Not touched (out of `owned_files`; root-caused to WP03,
   test-fixture-only — not reachable via any real, non-monkeypatched call path).

**#2465 scope check** (workflow.py resolver-proliferation consolidation, reported
as a GitHub comment, no closing keyword): after this WP's routing, `workflow.py` no
longer has four parallel feature-dir resolvers. `resolve_feature_dir_for_mission`
and `candidate_feature_dir_for_mission` have zero import/call sites (prose-only
mentions); `primary_feature_dir_for_mission`'s last 2 sites are routed by this WP;
`_canonical_status_feature_dir` remains as a one-line delegation to
`resolve_handle_to_read_path` (the STATUS-partition entry point, reused by
`workflow_executor.py` at 3 sites). Net: exactly two named, documented entry points
now cover every mission-directory read in the trio's shell/executor split — the
consolidation #2465 asks for fell out of routing naturally. Not closed (WP05 did not
audit the whole codebase); flagged for the operator/issue owner to confirm.

## WP06 — agent-CLI and lifecycle-shell cluster routed

Routed 9 of 10 assigned sites through `placement_seam(...).read_dir(<kind>)`; the 10th
(`retrospective/writer.py:85`) is verify-only (WP03's foundation site). Kinds:
`mission_feature_resolution.py::_safe_load_meta` (PRIMARY_METADATA),
`mission_finalize.py::finalize_tasks` (**WORK_PACKAGE_TASK**),
`tasks_move_task.py::_mt_resolve_targets` (PRIMARY_METADATA),
`tasks_move_task.py::_mt_issue_matrix_facts` (**SPEC** — the `primary_feature_dir` arg only
checks `spec.md`; `issue-matrix.md` reads from the separate already-COORD `feature_dir` param),
`accept.py::_stamp_birth_cutover_for_accept` (PRIMARY_METADATA),
`next_cmd.py` ×3 (PRIMARY_METADATA), `merge/executor.py::_run_lane_based_merge_locked`
(PRIMARY_METADATA).

**Ratchet, real-baseline diff** (scratch worktree at pre-WP06 `9a5cd9aea`): 31 → 22 offenders,
exactly the 9 routed sites removed, zero additions.

**Ledger row corrected** (§6-authorized single row): `retrospective/writer.py ::
resolve_retrospective_home` removed from the 31-site expected-red list → `sanction-infra`
(verify-only), citing WP03. **Not** added to `_FOUNDATION_SANCTION_SEED` (WP02's file; WP08 T039
folds it).

**writer.py:85 verified**: calls `_compose_primary_feature_dir`; the standing guard reds when
mutated back to the wrapper (non-vacuous); both leaves it calls import no `read_dir`/seam — no
cycle.

**Prompt disagreement recorded**: the WP prompt guessed `accept.py` "touches analysis reports";
the actual downstream read is `meta.json`, so `PRIMARY_METADATA` was used. Reported per the WP's
own "report disagreements" instruction.

**Collateral test remediations** (DIRECTIVE_041 remediate-not-delete): two patch-seam tests
rewired to the real seam (`test_tasks_move_task_seam.py`, `test_accept_birth_cutover_seam.py`)
because the `_tasks.<attr>` / `accept.primary_feature_dir_for_mission` patch targets no longer
exist. Behaviour preservation: new `test_lifecycle_read_seam_migration.py` (19 tests).

## WP07 — runtime bridge + status/aggregate.py routed; four foundation sites recorded

**Scope**: T032 (runtime-bridge cluster), T033 (`status/aggregate.py`), T034
(`commit_router.py` + the four FR-005 foundation sites). Commit
`162ac4b1a`.

**Lane setup note**: lane-g was allocated with only lane-c (WP03) merged as a
dependency; lane-b (WP02, approved but not yet merged anywhere) was missing
entirely, leaving the OLD 2-primitive ledger/gate in the tree. Merged
`kitty/mission-read-side-seam-primary-primitive-closure-01KYKMMT-lane-b` into
lane-g before starting (clean merge, 2 files, no conflicts) to get WP02's
terminal 4-primitive shape. Flagging in case other lanes hit the same gap.

### Per-site routing table (site → verdict → kind → downstream filename)

| Site | Verdict | Kind | Downstream filename justifying the kind |
|---|---|---|---|
| `runtime/next/runtime_bridge.py::_mission_routes_through_coordination` (was `:260`) | migrate-fail-loud | `PRIMARY_METADATA` | `specify_cli/migration/backfill_topology.py::read_topology` reads `meta.json` off the returned dir |
| `runtime/next/runtime_bridge.py::_dn_bootstrap` (was `:1244`) | migrate-fail-loud | `PRIMARY_METADATA` | `specify_cli/mission.py::get_mission_type` reads `meta.json`'s `mission_type` field |
| `runtime/next/runtime_bridge_identity.py::_primary_runtime_feature_dir` (`:118`) | migrate-fail-loud | `PRIMARY_METADATA` | callers `_resolve_coordination_branch`/`_resolve_mission_ulid` read `meta.json` via `load_meta_or_empty` |
| `specify_cli/coordination/commit_router.py::_resolve_mid8` (`:657`) | migrate-fail-loud | `PRIMARY_METADATA` | `specify_cli/mission_metadata.py::load_meta` reads `meta.json`'s `mission_id` |
| `specify_cli/status/aggregate.py::MissionStatus._find_meta_path` leg 1 (was `:499`) | migrate-fail-loud | `PRIMARY_METADATA` | builds `raw_meta = primary_dir / meta.json` for the literal-slug happy path |
| `specify_cli/status/aggregate.py::MissionStatus._find_meta_path` leg 3 (was `:543`, the `.name` leg) | migrate-fail-loud | `PRIMARY_METADATA` | builds `canonical_primary / meta.json`; seam's backfill-recovery leg makes this resolve an EXISTING dir |
| `specify_cli/status/aggregate.py::MissionStatus.save` diagnostic leg (was `:791`) | migrate-fail-loud | `PRIMARY_METADATA` | `MissionMetadataUnavailable`'s `meta_path`/`primary_candidate` diagnostic fields |
| `specify_cli/status/aggregate.py::MissionStatus._find_meta_path` leg 2 (`:522`, `bare_dir_name` from `resolve_bare_modern_mission_dir_name`) | **left unrouted — permanent fixture** | n/a | see below |

**7 of WP07's 8 findings routed.** `:522` deliberately NOT routed — see next section.

### `:522` — why it stays unrouted, and how it is affirmatively checked

`tests/architectural/resolution_gate_allowlist.yaml`'s `canonicalizer:` section
carries a PERMANENT entry (predates this mission — authored by the
`read-side-placement-seam-migration-01KYHP67` mission's WP05, still present
verbatim):

```yaml
- qualname: MissionStatus._find_meta_path
  rationale: "WP05 SANCTION: bare_dir_name is returned by resolve_bare_modern_mission_dir_name
    ... This is a feature_dir.name-equivalent ... Already-canonical by provenance."
  file: src/specify_cli/status/aggregate.py
  token: composed_primary = primary_feature_dir_for_mission ( repo_root , bare_dir_name )
```

`tests/architectural/test_resolution_authority_gates.py::test_canonicalizer_permanent_allowlist_is_exactly_3`
asserts this is one of EXACTLY 3 permanent entries after WP07 — i.e. WP01
already decided, forward-looking, that this exact call shape survives WP07
unrouted. `CANONICALIZER_PRIMITIVE_NAMES` (the canonicalizer scanner's callee
allowlist) recognises only `primary_feature_dir_for_mission` and
`_compose_primary_feature_dir` by literal name — renaming the callee to
`placement_seam(...).read_dir(...)` (a `read_dir` call, neither name) would
make the site vanish from that scan entirely, orphaning the pinned entry and
redding `test_every_allowlist_entry_has_live_match`'s staleness twin-guard —
a WP01-owned gate WP07 has no sanctioned exception to edit. Verified this is
the CURRENT, real behaviour (not a hypothetical): attempted the rename,
confirmed `test_resolution_authority_gates.py` failure, reverted.

**Affirmative-check proof (Reviewer Guidance #1)**: ran a verification probe
(ephemeral, deleted after — not committed) importing
`test_no_read_side_bypass.py`'s own `_scan_read_bypass(source, module)`
scanner, planting a fresh non-compliant `candidate_feature_dir_for_mission(...)`
call immediately next to the `:522` line inside `_find_meta_path`. Result:
**baseline 2 findings → 3 findings after the plant (+1, exactly the planted
call)**. The whole-tree read-side-bypass scan is live and non-vacuous over
this function even though `:522` itself is a permanent, by-design exception —
"it is checked now" is true of the surrounding function, not (and never
claimed to be) of this one pinned call.

### `:543` backfilled-fixture evidence (T033(b), US3 scenario 3)

`tests/specify_cli/status/test_aggregate_read_seam_migration.py::test_find_meta_path_backfilled_mission_resolves_existing_bare_dir`:
built a real git repo with a bare `<slug>` primary dir (backfilled — no
`-<mid8>` suffix on disk) and a composed `<slug>-<mid8>` coord branch. Red-first
evidence embedded in the test itself: the historical blind composition
(`_compose_primary_feature_dir`, still the exact pre-WP03 body) resolves the
literal composed dir, asserted **not to exist** — reproducing the bug T033(b)
closes. The routed `:543` call shape
(`placement_seam(repo, composed_handle).read_dir(PRIMARY_METADATA)`, exercised
directly since end-to-end `_find_meta_path` reaches `:522`'s bare-modern-slug
leg first on this exact fixture — verified empirically, documented in the
test's own docstring) resolves the **existing bare-slug dir**, not the
non-existent composed one. All 3 assertions pass.

### `_find_meta_path`'s four-site discriminator spelling (T033(c))

Used the ledger's own `(rel_path, qualname, primitive, site_token)` 4-tuple
verbatim — the SAME shape `tests/architectural/test_no_read_side_bypass.py`'s
`_ledger_stay_lenient_index`/`_ledger_foundation_index` parse and
`test_index_discriminator_represents_a_four_site_qualname` exercises as its
own acceptance fixture. Did not invent a second addressing convention.

**New WP02 gap found and reported (not worked around)**:
`test_index_discriminator_represents_a_four_site_qualname` hardcodes a LIVE
scan of `status/aggregate.py` expecting exactly 4 findings in
`MissionStatus._find_meta_path` (1 `candidate_feature_dir_for_mission` + 3
`primary_feature_dir_for_mission`) — i.e. it assumes ALL THREE
`primary_feature_dir_for_mission` sites stay unrouted forever, which
contradicts T033(a)/(b)'s explicit mandate for THIS WP to route two of them.
After routing, the live scan finds only 2 (the permanent `:522` fixture +
the pre-existing `candidate_feature_dir_for_mission` site) — the test reds.
Classified as WP02 test-authoring gap (DIRECTIVE_041: the fixture's
live-tree dependency doesn't survive the very migration it exists to
validate), not a WP07 regression — the fixture's OWN later section already
proves the 4-column key shape disambiguates same-primitive multi-site
qualnames using synthetic rows, independent of how many real sites remain.
Recommend WP02/WP08 rewrite this test against a frozen synthetic source
string (the technique the test's own `synthetic_rows` section already uses)
so it no longer depends on live, migration-mutable file content.

### Four FR-005 foundation sites — recorded, NOT re-pointed (deviation from the WP07 prompt, with evidence)

The WP07 prompt instructs re-pointing `core/paths.py::get_feature_target_branch`,
`core/paths.py::resolve_merge_target_branch`, `core/git_ops.py::resolve_target_branch`,
and `coordination/surface_resolver.py::resolve_status_surface_with_anchor` at
the module-private `_compose_primary_feature_dir` leaf. **Attempted this exactly
as instructed; it breaks a WP02-owned gate at COLLECTION time and was reverted.**

Reproduction: re-pointing these 4 calls' callee from `primary_feature_dir_for_mission`
to `_compose_primary_feature_dir` collapses `tests/architectural/test_no_read_side_bypass.py`'s
`_FOUNDATION_SANCTION_SEED` (a hardcoded Python tuple INSIDE that file, not the
YAML) to zero live matches for all 4 entries' `token_substring="primary_feature_dir_for_mission ("`,
raising `tests.architectural._ratchet_keys.DescriptorResolutionError` during
test COLLECTION (not one red test — the entire file fails to collect, ~50
tests unreachable). WP07's sanctioned out-of-map exception (tasks.md §6) covers
only `tests/architectural/resolution_gate_allowlist.yaml`'s token line — a
DIFFERENT file, for the CANONICALIZER gate, not the read-side-bypass gate's
`_FOUNDATION_SANCTION_SEED`. Confirmed the canonicalizer gate itself is NOT the
blocker: `CANONICALIZER_PRIMITIVE_NAMES` already recognises both
`primary_feature_dir_for_mission` and `_compose_primary_feature_dir`, and none
of these 4 sites carry a canonicalizer-allowlist entry today (their handle arg
is already `_canonicalize_primary_read_handle`-folded, so `is_def_use_canonical`
passes regardless of which of the two names is called) — re-running
`test_resolution_authority_gates.py` after the attempted re-point: 44/44 still
passed. The break is isolated to `test_no_read_side_bypass.py`'s
`_FOUNDATION_SANCTION_SEED`, which WP07 has no authority to touch.

**Resolution**: reverted the callee rename; left all 4 call sites 100%
unchanged (same callee, same args, same behaviour) and added a rationale
comment above each recording it as an FR-005/NFR-009 foundation site, with an
explicit note that the leaf re-point is deferred to WP08 (which already
deletes the public wrapper these 4 sites import, and so must re-point them —
and update `_FOUNDATION_SANCTION_SEED`'s tokens — in the same pass; WP08 has
no ownership conflict there since it is the file's designated end-state
owner per tasks.md's WP08 section).

**Structural (not crash-based) acyclicity proof**: built a real git-repo
fixture and traced `mission_runtime.resolution.PlacementSeam.read_dir`'s own
code object via `sys.setprofile` (the identical technique WP03's own
expected-reds.md section documents) while calling all four foundation-site
functions. Result: `read_dir` IS invoked once per call (via each site's
existing call to the still-delegating `primary_feature_dir_for_mission`
wrapper) but its call-stack depth never exceeds 1 — i.e. `read_dir` is never
RE-ENTERED while already executing, across all four sites. This is the
positive, depth-bounded claim (not "no RecursionError raised") NFR-009
requires.

**Census confirmation** (quickstart.md §1 recipe, re-derived fresh): all four
sites present, call shape unchanged —
`core/paths.py:748` (`get_feature_target_branch`),
`core/paths.py:807` (`resolve_merge_target_branch`),
`core/git_ops.py:452` (`resolve_target_branch`),
`coordination/surface_resolver.py:752` (`resolve_status_surface_with_anchor`).
`_FOUNDATION_SANCTION_SEED`'s existing 3 per-site descriptors (core/paths.py x2,
core/git_ops.py x1) and `_READ_SANCTIONED_MODULES`'s whole-module entry for
`coordination/surface_resolver.py` were confirmed to already match this
census exactly — no gap to report there (WP02 landed these correctly).

### Zero-additions ratchet

Read-side bypass gate (`test_no_read_side_bypass_outside_sanctioned_and_allow_listed`)
findings: **31 → 24** (re-derived live, not the ledger's stale "32" figure —
the live scan found 31 at WP07's start, matching quickstart.md §1's own
"re-derive, never trust a written count" instruction). Routed exactly 7 of
WP07's 8 assigned sites (`:522` excepted, by design, above). **Zero new
findings** — confirmed via the AST census recipe (34→27 sites / 19→16 files
for `primary_feature_dir_for_mission` specifically, exactly −7).

### Husk-comment corrections (SC-009, this WP's 2 of the mission's 8)

Both `runtime/next/runtime_bridge.py::_mission_routes_through_coordination`
and `runtime/next/runtime_bridge_identity.py::_primary_runtime_feature_dir`
carried a comment implying "the coord-aware resolver fail-closes for a
materialized-but-empty coord worktree" as the reason to anchor on the
topology-blind primary. Corrected in the same commits as their routed call
sites: the KIND-BLIND resolver (`candidate_feature_dir_for_mission`)
genuinely can land on the husk; the KIND-AWARE seam cannot, because for a
PRIMARY-partition kind (`PRIMARY_METADATA`) the decision layer short-circuits
to the primary anchor for every topology and coord state, before any coord
probe. True warning preserved, false implication removed.

### Gate exit codes (foreground, this WP's tree)

| Gate | Exit code | Notes |
|---|---|---|
| `ruff check <8 changed files>` | 0 | clean |
| `mypy --strict src/specify_cli src/charter src/doctrine` | 0 | 1088 files, zero issues (`src/runtime/*` is out of this command's scope per the project's own mypy invocation — untouched by this WP's gate) |
| `pytest tests/specify_cli/status/ tests/specify_cli/coordination/ tests/mission_runtime/ -q` | 0 | 1065 passed |
| 6 named C-008 gates together | 1 | 188 passed / 6 failed — 3 pre-existing (WP01's own recorded `test_fr007_arm_live_identity_scan_is_clean` / 2 trio nodes, all WP04/WP05 territory, zero WP07 files involved), 1 pre-existing WP02/WP03 interaction gap (`test_sanctioned_modules_are_non_vacuous_for_the_newly_censused_primitive` — `mission_runtime/resolution.py` no longer calls `primary_feature_dir_for_mission` after WP03's leaf extraction, so WP02's non-vacuity claim for that primitive is stale; not a WP07 file), 1 new-but-not-mine (main ratchet, expected — 24 remaining findings), 1 new WP02 test-authoring gap discovered by this WP (`test_index_discriminator_represents_a_four_site_qualname`, reported above) |

No allow-list YAML token edit was needed this WP (the one place §6 anticipated
it — `:522`'s canonicalizer entry — was correctly left untouched since the
call itself was correctly left unrouted).

## ⚠ Mission regression — the `read_dir` cycle class re-manifested in a stale test (WP03 fallout, WP08-owned)

`tests/specify_cli/cli/commands/test_coordination_doctor.py::test_stranded_check_bare_handle_false_negative_under_raw_resolver`
**RecursionError**. Three routing agents reported it as "pre-existing" — **they were wrong**, and
the error is instructive: they checked their *lane* base (which already contains WP01–WP03), not
the true `upstream/main` merge-base. **Classified honestly here: GREEN at the true base
`765cdcc59`, RED from WP03's delegation onward.** It is a mission regression, not a baseline red
("pre-existing on lane-X" ≠ pre-existing).

**The cycle** (a fourth manifestation of WP03's class):
```
_raw (test:1084) → primary_feature_dir_for_mission → read_dir → resolve_artifact_surface
  → resolve_planning_read_dir   ← the test MONKEYPATCHES this to _raw → back to the wrapper → ∞
```
The test installs `primary_feature_dir_for_mission` as a "raw resolver" and patches
`resolve_planning_read_dir` to route through it. Pre-WP03 the wrapper was a pure leaf, so
`_raw → wrapper` returned directly. WP03's Half-B delegation makes the wrapper re-enter `read_dir`,
which the patch routes back to `_raw` — infinite.

**It is TEST-ONLY, not a production cycle.** WP03's reviewer proved `read_dir` production-acyclic
across 16 kinds (only `RETROSPECTIVE` re-entered, and that was fixed). No production path uses the
wrapper as `resolve_planning_read_dir`; in production `resolve_planning_read_dir`'s PRIMARY leg
calls the **leaf** `_compose_primary_feature_dir`. The test's "raw resolver" premise is what WP03
invalidated — the raw composition is now the leaf, not the wrapper. **STALE test (`DIRECTIVE_041`).**

**Why WP03's review missed it**: WP03's behaviour-preservation scope was `tests/merge/`,
`coordination/`, `status/`, `missions/` — it did **not** include `tests/specify_cli/cli/commands/`.
The production cycle analysis was correct and complete; the test-scope was not. WP03's approval
stands (production is cycle-free).

**Owner: WP08.** It deletes the public wrapper, at which point this test breaks regardless (the
name vanishes). WP08's fix: re-point the test's `_raw` helper (`test_coordination_doctor.py:1084`)
at `_compose_primary_feature_dir` — the actual raw leaf — restoring the test's real intent (a raw
composition that produces the stranded-check false-negative). Added to WP08's known-work.
**Every routing WP sees this red; it is expected and not theirs.**

## ⚠ Reconciliation items accumulated for WP08 (WP02's gate reaches end-state only at WP08)

Recorded so WP08 folds them in one pass and no routing WP works around WP02's file:
1. **Non-vacuity** (WP04): `test_sanctioned_modules_are_non_vacuous_for_the_newly_censused_primitive`
   reds because WP03 drained `resolution.py`'s primitive calls → drop `resolution.py` from the
   sanctioned set for `primary_feature_dir_for_mission`.
2. **Foundation-seed collection error** (WP07): re-pointing the four FR-005 sites at the leaf breaks
   `_FOUNDATION_SANCTION_SEED` (a hardcoded tuple in WP02's `test_no_read_side_bypass.py`) with a
   `DescriptorResolutionError` at **collection** (~50 tests). WP07 correctly **reverted and deferred**
   — WP08 re-points the four sites AND updates the seed together (this is the M1 build-break from the
   plan squad, arriving on schedule).
3. **Index-discriminator contradiction** (WP07): `test_index_discriminator_represents_a_four_site_qualname`
   hardcodes the three `_find_meta_path` sites as unrouted-forever, contradicting WP07 routing them.
   WP08 reconciles.
4. **`decisions/emit.py:71` — ADJUDICATED by WP04's reviewer (opus), WP02 is right.** Routing it
   is **directory-identical in every cell** (coord-materialized, coord-branch-no-worktree,
   deleted-coord); the *only* delta is the exception type on deleted-coord (`ActionContextError` →
   `CoordinationBranchDeleted`) — precisely the fail-loud gain WP02's ledger claims. The two
   authorities are **not** in semantic conflict: the coord-authority sanction ("legitimate
   coord-owned write, bypasses `commit_for_mission` by design") stays true after routing. What
   breaks is **machinery** — the allow-list entry is keyed on a frozen token naming the legacy
   primitive, and `COORD_AUTHORITY_WRITE_FLOOR = 4` counts *kind-blind* calls, so the gate
   **obliges a deprecated primitive to keep being used** — the identical name-vs-kind discrimination
   defect WP01's own cycle-1 fixed on the write arm. **End state (gate-owner work, WP08):** teach the
   coord leg the seam idiom (recognise `read_dir(<COORD kind>)` as a coord-owned write), re-token the
   YAML entry, retire/transfer the floor per the `DIRECTIVE_043` precedent — **then** route it. WP04's
   refusal to route unilaterally was correct and required.


## WP08 — wrapper deletion + closeout (T035–T039), all 6 reconciliation items resolved

**Structural claim (T035, SC-001) — CONFIRMED (orchestrator-verified)**: `from
specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission` raises
`ImportError`. Deleted outright — no rename, no `__getattr__` shim, dropped from `__all__`.

**Read-side census — GREEN (orchestrator-verified 52/52)**. Six named C-008 gates green together
(195/195). Only remaining foreign red is #3031 (out of scope by surface, C-010).

**T036 drain**: `_canonicalize_primary_read_handle` drained from **12 no-op call sites / 8 files**
(each redundant — the seam's PRIMARY leg folds the same handle internally, idempotently). Left for
the 5 permanent foundation files + `resolution.py`'s internal self-references.

**T037**: `agent/tasks.py` re-export deleted (PATCHWORK, zero production callers). Only one of the
two anticipated tests was still live (WP06 had already replaced the other in its T029).

**T038**: `surface_resolution_audit/inventory.md` **hand-edited** (rekey script NOT run, #3011). 16
resolver-internal rows removed (covered by the terminal census), 1 foundation row kept+re-tokened,
1 leaf-definition row added. `_MIN_DISCOVERED_ROWS` floor retired 20→15 (DIRECTIVE_043 — authority
transferred to the terminal census).

### Reconciliation items — per-item verdict
1. **M1 build-break — closed, + a 5th site.** Four named foundation sites re-pointed at
   `_compose_primary_feature_dir` **in the wrapper-deletion commit** with `_FOUNDATION_SANCTION_SEED`
   tokens + the YAML canonicalizer entry updated together. A **5th** site
   (`status/aggregate.py`'s permanent canonicalizer fixture) was **structurally forced** into the
   same re-point (it called the wrapper too) — re-tokened per the WP03 `77226250f` precedent. A new
   `_LEAF_PRIMITIVE_ALIASES` map classifies these leaf-call entries under the
   `primary_feature_dir_for_mission` primitive for per-primitive bookkeeping. *(Reviewer must
   confirm this alias only classifies already-sanctioned entries and does not hide a
   non-sanctioned leaf call — bite test required.)*
2. **Non-vacuity drop — closed, + one extra.** `resolution.py` dropped as instructed; **also
   `coordination/surface_resolver.py`**, made vacuous by item #1's own re-point (discovered
   empirically, not pre-listed — it is WP08's own action that caused it).
3. **Index-discriminator — closed.** Rewritten against a **frozen synthetic source string** (per
   WP07's recommendation): its live-file four-site fixture could not survive the migration it
   validated (post-deletion the file carries zero primitive calls).
4. **RecursionError stale test — closed.** `_raw` re-pointed at the leaf. STALE per DIRECTIVE_041 —
   production was always acyclic.
5. **`decisions/emit.py:71` — ALLOW-LISTED, not routed.** Filed **#3055** for the gate-owner
   follow-up (teach the coord-authority gate the seam idiom, transfer `COORD_AUTHORITY_WRITE_FLOOR`).
   This makes `resolve_feature_dir_for_mission` **fully reconciled** (declared == live, 8 sites/7
   files; removed from the permanent-exemption tuple). `primary_feature_dir_for_mission`'s exemption
   is now **permanent** (a deleted primitive can never show a live call site; declared 3 vs live 0,
   recorded as intentionally-permanent per the DIRECTIVE_043 floor→census transfer).
6. **T024 — ADDED.** `test_documentation_wiring_on_coord_husk_writes_gap_analysis_to_primary` drives
   the real seam against a coord-husk fixture, asserting `gap-analysis.md`'s target is the PRIMARY dir.

**Gates (implementer, foreground)**: ruff 0 (37 files); mypy --strict 0 (1088 files); six C-008
gates 0 (195/195); status/coordination/mission_runtime/audit suites 0 (1065); standalone
`audit.py` 0 (was failing pre-inventory-edit).

## WP01 — architectural gate expectations

**Scope**: T001–T007 (`test_resolution_authority_gates.py`,
`resolution_gate_allowlist.yaml`, `test_gate_read_literal_ban.py`,
`test_trio_seam_only.py`, `test_coord_read_residuals_closeout.py`,
`_gate_coverage_baseline.json`, `_golden_count_baseline.json`). **Zero
changes under `src/`.**

**Reconciled against a live run of all six C-008 gates** (`PWHEADLESS=1
SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest test_no_read_side_bypass.py
test_resolution_authority_gates.py test_gate_read_literal_ban.py
test_coord_read_residuals_closeout.py test_trio_seam_only.py
test_no_write_side_rederivation.py -q`, lane-a): **168 passed / 3 failed / 0
collection errors** — the 3 failures are exactly the 3 nodes below, no
unpredicted red.

| # | Node id | Finding (rel_path :: qualname) | FR | Greened by | Why expected |
|---|---|---|---|---|---|
| 1 | `test_coord_read_residuals_closeout.py::test_fr007_arm_live_identity_scan_is_clean` | `src/specify_cli/cli/commands/agent/mission_setup_plan.py::_run_documentation_wiring` (flag: `get_mission_type(feature_dir)`) | FR-014 | WP04 | T005 retired the `#2214` allow-list pin (`_IDENTITY_CALLSHAPE_KNOWN_RESIDUALS`) that tolerated this one-hop residual, together with the test asserting the pin exists. The live arm still (correctly) flags the site — it is not yet routed. |
| 2 | `test_trio_seam_only.py::test_trio_imports_route_only_through_seam_wrappers` | 7 sites still import `_canonicalize_primary_read_handle` / `primary_feature_dir_for_mission` from `_read_path_resolver`: `workflow.py::<module>`, `workflow_executor.py::<module>`, `acceptance/__init__.py::<module>` (top-level imports), `implement.py::find_wp_file`, `implement.py::_load_primary_anchored_mission_meta`, `implement.py::_planning_artifact_source_dir`, `implement.py::_build_implement_json_payload` | FR-004/FR-005 | WP05 | T006 shrank `_SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES` to `{resolve_handle_to_read_path}` (a tightening, Ledger M5). This is a **pre-existing** gate (zero code change to itself) that now structurally enforces the shrink. |
| 3 | `test_trio_seam_only.py::test_allowed_read_path_resolver_names_are_currently_used` | same reacquisition set as #2 | FR-004/FR-012 | WP05 | T006's replacement for the self-nullifying exemption (Ledger M6 — the retired `blessed - used - {"resolve_handle_to_read_path"}` shape was the empty set by construction once `blessed` shrank to one name, vacuously green regardless of what the trio imported). The new positive assertion reds on the identical still-imported leaf primitives until WP05 routes all four trio rewrite targets. |

**T001/T002 gate-defect fixes (not widenings)**: `_PRIMARY_FOLD_CALLSHAPE_FUNCS`'s
two consumption sites (`callshape_violations` here; `test_no_status_leg_rerouted_to_primary`
above) now UNION a kind-discriminated helper (`_names_bound_from_primary_read_dir`, via
`mission_runtime.is_primary_artifact_kind` — never a hardcoded kind list) instead of widening
the frozenset by callee name (Ledger M7 — a callee-name widening would have sanctioned
`STATUS_STATE` reads through the same seam call, producing a false positive on
`test_no_status_leg_rerouted_to_primary`; verified that node does **not** acquire a new failure
from this change). `test_write_arm_resolvers_anchor_meta_on_primary` now asserts the positive
`reads_via_primary` signal it used to discard (Ledger M8); making it positive against the REAL
write-arm surfaces (`core/paths.py::get_feature_target_branch`,
`core/git_ops.py::resolve_target_branch`, `mission_finalize.py::finalize_tasks`) surfaced a
genuine pre-existing detection gap — all three are thin adapters over
`read_target_branch_from_meta` and never match the literal `anchor(...) / "meta.json"` BinOp
shape.

**Review-cycle-1 (B1) found that gap only HALF-closed.** The initial fix (`_anchor_invoked_in`)
recognised the thin-adapter shape only when anchored on the exact **deleted** wrapper name
`primary_feature_dir_for_mission`, while its docstring claimed the seam branch was "the
surviving spelling after WP08". That branch requires a literal `/ "meta.json"` join no real
surface has, so it could never match its own subjects: the moment WP08 deletes the wrapper the
positive assertion would have gone **unrecorded-red** — in WP06 (`mission_finalize.py:1645`
sits inside `finalize_tasks`, a WP06 routing target) and again in WP08 (`core/paths.py` ×2 and
`core/git_ops.py` forced off the name) — emitting a message instructing the implementer to
"POSITIVELY anchor on `primary_feature_dir_for_mission`". That is a gate **obliging a deleted
primitive to keep being used**: the very inversion T003 retires on the read arm, rebuilt on the
write arm.

Cycle-1 closed it by adding `_primary_partition_seam_invoked_in` — the seam-idiom counterpart
of `_anchor_invoked_in`, **kind**-discriminated (via `_is_primary_partition_read_dir_call`)
rather than **name**-discriminated, recognising a PRIMARY-partition `<seam>.read_dir(kind)`
call anywhere in the function, which is the actual post-WP08 shape. Verified by AST mutation
against the live tree on all three surfaces:

| Mutant | Required | Result (all 3 surfaces) |
|---|---|---|
| baseline | green | `(False, True)` ✓ |
| → candidate resolver | bites | `(False, False)` ✓ |
| → unrelated third resolver (M8 case) | bites | `(False, False)` ✓ |
| **→ post-migration seam idiom** | **GREEN** | **`(False, True)`** ✓ *(was `(False, False)` — the B1 defect)* |
| → `read_dir(STATUS_STATE)`, same shape | bites | `(False, False)` ✓ *(kind discipline holds)* |

Locked in by two new self-tests
(`test_write_arm_recognises_primary_seam_thin_adapter_post_migration_shape`,
`test_write_arm_primary_seam_thin_adapter_kind_discipline_holds`). Both the pre-migration and
post-migration thin-adapter shapes are now covered — **fixed, not carried as a red.**

**T003/T004 floor retirement (FR-007, DIRECTIVE_043 required)**: retired
`CANONICALIZER_FLOOR` (was 44) and `ROUTED_CANONICALIZER_FLOOR` /
`_MARGIN` (were 40 / 4) together with `test_canonicalizer_gate_floor` /
`test_routed_count_floor`. Live re-derived census at retirement
(quickstart.md §1 recipe, re-run fresh): **46 total canonicalizer call sites,
43 routed** (both figures had already drifted from the stale 44/40 recorded
in-tree — unrelated `src/` growth between missions). This is a **retirement**,
not a re-pin: after Step 2 the floors' only remaining subject population is
resolver-internal + named-sanctioned code, where a raw handle is correct by
contract, so a floor obliging continued use would invert its own purpose.
**DIRECTIVE_043 adjudication**: non-vacuity is preserved by **transfer**, not
abandoned — `tactic:architectural-gate-non-vacuity`'s routed-count-floor
element moves to WP02's read-side bypass census above (its own concrete
floor, per-primitive non-vacuity, alias resistance, shrink-only allow-list).
`test_coord_read_residuals_closeout.py`'s floor **import** + both equality
pins + the two bound checks (the whole `test_routed_canonicalizer_floor_
matches_recorded_census` test — zero coverage beyond the retired floor's own
derivation) retired in the **same commit** — otherwise `ImportError` at
collection, ~20 tests (DIRECTIVE_034). Also corrected the module's
off-by-one identity read-site census in the same pass (FR-016): **24** live,
not the recorded 22 (re-derived via the module's own
`_count_read_call_sites`; unrelated drift since that figure was written).

**T007 baselines**: `_gate_coverage_baseline.json` (orphan baseline,
`--update-baseline`) refrozen — `total_tests` 32346 → 33948, `duplicate_
test_count` 924 → 1046 (repo-wide drift unrelated to this WP's ~10-test net
delta; `orphan_test_count`/`orphan_files` unchanged at 0/`[]`).
`_golden_count_baseline.json` (selection baseline) needed **no change** —
none of this WP's additions introduce a new `len(x) == n` golden-count shape
(the retired floor tests used `>=`/`>`/`<=`, never `==`).

**Contradictions with the WP prompt** (reported, not silently resolved):
(1) T003's "corresponding block in `resolution_gate_allowlist.yaml`" does not
exist — that YAML's `canonicalizer:` allow-list (3 permanent entries) is a
separate, still-live def-use correctness gate, untouched; (2) T005's
"off-by-one" was actually **+2** (22 → 24), not literally one — same drift
class as the canonicalizer census above; (3) `tests/architectural/
test_inline_meta_read_gate.py` (not owned by WP01) carries a stale docstring
precedent-citation to `ROUTED_CANONICALIZER_FLOOR` — a comment-only mention,
left untouched (out of WP01's `owned_files` and task list), flagged here for
a future cleanup pass.
