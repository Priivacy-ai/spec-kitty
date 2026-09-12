# Issue matrix — doctrine-silence-guards-01KYFV7Q

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2680 | `graph.yaml` monolith sharded into per-kind fragments | verified-already-fixed | The shard landed in #2680. What survives is ~10 source sites still naming the dead path — that residue is **this mission's WP07** (FR-008), not a reopening. Evidence: `git grep "doctrine/graph\.yaml" src/` → 12 files. |
| #2957 | CI shard selection never collects several `tests/specify_cli/cli` files on main | fixed | Fixed by **WP10** (FR-013 / NFR-005 / SC-013 / IC-08). Root cause verified in-tree: `fast-tests-cli` and `integration-tests-cli` both gate on `needs.changes.outputs.cli == 'true'`, so on any main push whose diff misses the CLI paths, neither job runs. Evidence, re-measured 2026-07-27 on lane branch `kitty/mission-doctrine-silence-guards-01KYFV7Q-lane-j` at its WP10 tip (rebased onto the planning branch at `1764b4c0b`; lane shas are rewritten by rebase, and the gate re-derives every figure live), worst reachable filter state on a push to `main`: **before** 10 of 50 suite jobs started and **31,547 of 33,822** collected test nodes (1,966 of 2,174 files) ran in no job; **after** 49 of 50 suite jobs start and **0** nodes are uncollected. All four files #2957 names were uncollected before and are collected after. Enforced by `tests/architectural/test_ci_collection_completeness.py` — no baseline, no allowlist, no regeneration path. Taxonomy residue split out to **#2979** (see note below). |
| #2979 | Tests with no tier marker are invisible to CI's marker partition | deferred-with-followup | Split out of #2957 by WP10/T055, not folded in. WP10 closes the *topology* half (a job that never starts); the *taxonomy* half (a file no `-m` expression selects) needs a new always-on marker-completeness gate plus a repo-wide marker sweep, which is mission-sized. Two live instances recorded: `test_mark_status_authored_roster.py` (fixed in `1764b4c0b`) and `tests/release/test_dogfood_command_set.py` (contained by the `… or not fast` widening in WP10's topology-fix commit, still unmarked). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

## Note on #2957's terminal verdict

WP10 closes the **structural** defect — no test file goes uncollected on `main`. It does **not** fix
the reds that closure will surface; those are honest pre-existing reds under ADR `2026-07-17-1` and
are reported, not repaired here (WP10/T055). So #2957's terminal verdict is expected to be `fixed`
for the collection gap, with any surfaced reds filed separately rather than folded in. Satisfying the
gate by reclassifying a surfaced red as expected would be greenwashing, and is explicitly forbidden.

**Reached, 2026-07-27.** The verdict is `fixed` for the collection gap. Nothing was reclassified, no
baseline was regenerated and no allowlist was added — the gate offers none of the three. One red the
closure surfaced was fixed at its root on the planning branch rather than in this WP
(`1764b4c0b`, the missing tier markers on `test_mark_status_authored_roster.py`); the general class
behind it is filed as **#2979** rather than folded in. Full T055 report:
[`tasks/WP10-ci-collection-completeness.md`](tasks/WP10-ci-collection-completeness.md#activity-log).
