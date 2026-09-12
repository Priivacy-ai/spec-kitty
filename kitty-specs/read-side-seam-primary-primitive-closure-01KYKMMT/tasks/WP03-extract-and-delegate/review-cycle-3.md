---
affected_files:
- path: src/specify_cli/retrospective/writer.py
- path: src/specify_cli/missions/_read_path_resolver.py
- path: tests/retrospective/test_home_resolution_single_authority.py
- path: tests/specify_cli/missions/test_primary_read_delegation.py
- path: tests/specify_cli/cli/commands/test_coord_status_commit_2155.py
cycle_number: 3
mission_slug: read-side-seam-primary-primitive-closure-01KYKMMT
reproduction_command: 'PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest
  tests/specify_cli/missions/test_primary_read_delegation.py tests/retrospective/test_home_resolution_single_authority.py
  tests/specify_cli/cli/commands/test_coord_status_commit_2155.py -q -p no:randomly'
reviewed_at: '2026-07-28T18:40:00Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP03
---

# WP03 Review Cycle 2 — APPROVED

> Artifact numbering note: this is the **second** review cycle. `review-cycle-2.md`
> is a phantom emitted by the known review-cycle-N double-increment (it carries
> `reviewer_agent: unknown` / `verdict: rejected` wrapping my cycle-1 body). This
> file is the truthful latest artifact. No existing artifact was edited or deleted.

Fix commit `e023fc0bf`. All four cycle-1 blockers are closed and all three
non-blocking folds are taken. I re-derived every load-bearing claim myself; I did
not accept the commit body's numbers.

---

## B1 — the NFR-009 cycle is genuinely closed. Both trace directions confirmed.

**Green.** `tests/specify_cli/missions/test_primary_read_delegation.py` → **12 passed**.
`test_read_dir_never_enters_the_public_wrapper_for_any_kind` reports **zero** wrapper
entries across 6 fixtures × 16 `MissionArtifactKind` members = **96 traced `read_dir`
calls**.

**Red.** A zero-count instrument is worthless until it is shown to report non-zero, so
I reverted the fix at runtime **without touching the worktree**: a pytest plugin exec'd
the pre-fix source (`git show e023fc0bf^:src/specify_cli/retrospective/writer.py`) into a
throwaway module and rebound `specify_cli.retrospective.writer.resolve_retrospective_home`
to the old body. `read_dir` resolves that name through a *function-local*
`from specify_cli.retrospective.writer import resolve_retrospective_home`, i.e. via the
module attribute at call time, so the rebind is picked up by the production path.

Result:

```
AssertionError: read_dir entered the public wrapper 6 time(s) (NFR-009 cycle):
  [(flat, RETROSPECTIVE), (coord-materialized, RETROSPECTIVE), (coord-husk, RETROSPECTIVE),
   (coord-deleted, RETROSPECTIVE), (coord-empty, RETROSPECTIVE), (backfilled, RETROSPECTIVE)]
1 failed, 11 passed
```

**Exactly 6**, one per fixture, all `RETROSPECTIVE`, clean `AssertionError`, and — as in
cycle 1 — still **no `RecursionError`**, which is precisely why the WP's own designated
stop-signal could not be trusted here.

**The trace is code-object scoped, not binding scoped.** `wrapper_code =
primary_feature_dir_for_mission.__code__`, matched with `frame.f_code is wrapper_code`.
The red run *proves* this rather than asserting it: the 6 entries were produced by the
writer module's own function-local `from … import primary_feature_dir_for_mission`
binding — a different binding object from the test module's top-level one — and the
instrument still caught every one. The wrapper is undecorated, so `__code__` is its own.

---

## B1 adversarial — no new cycle, no new bypass, and no OTHER kind can harbour this defect

**(a) The leaf is still importable-but-unexported.** `_compose_primary_feature_dir` is
absent from `__all__` (`_read_path_resolver.py:1692-1704` lists only
`primary_feature_dir_for_mission` among the two). V3 holds.

**(b) The new call cannot re-enter `read_dir`.** The leaf body is a pure L3 join:
`assert_safe_path_segment(mission_slug)` then
`get_main_repo_root(repo_root) / KITTY_SPECS_DIR / mission_slug`. No seam import, no
resolver call. I re-confirmed it is byte-identical to the pre-WP03 wrapper body
(`77226250f^:src/specify_cli/missions/_read_path_resolver.py:1288-1292`).

**(c) `read_dir` has exactly ONE kind-specific short-circuit — fully enumerated.** The
method body is:

```python
if kind is MissionArtifactKind.RETROSPECTIVE:
    ...
    return retrospective_dir
return resolve_artifact_surface(self.repo_root, self.mission_slug, kind).path
```

No `elif`, no second chokepoint. So the only way another kind could reach the wrapper is
*through* `resolve_artifact_surface`. I traced that subtree statically as well as
empirically:

- `resolve_artifact_surface` → `resolve_planning_read_dir` (PRIMARY leg calls the leaf,
  T016) → `_backfilled_primary_dir` → `_classify_artifact_surface` →
  `_resolve_coordination_branch` / `_resolve_mission_id` / `resolve_mid8` — **all four
  `resolution.py` callers re-pointed to the leaf by T016** (verified in the lane diff).
- The one remaining wrapper call inside the reachable module set is
  `coordination/surface_resolver.py:739` — but it lives in
  `resolve_status_surface_with_anchor`, which `resolve_artifact_surface` does **not**
  call. The other `resolve_status_surface` consumer, `_resolve_status_surface_dir`, is
  reached only from `_assemble_core_fragments`, also off the `read_dir` chain.

**Answer to the question asked: no.** `RETROSPECTIVE` was the sole kind short-circuit and
the sole latent cycle; nothing else beneath `read_dir` reaches the wrapper. The 96-call
empirical trace over the full `CoordState` fixture space (flat / materialized / husk /
deleted / empty / backfilled) agrees with the static enumeration.

---

## B3 — the write-leg delta is gone. Verified live on a real backfilled fixture.

Not read off the source. I built the fixture with the test module's own `_backfilled`
builder (real `git init` repo, bare `<slug>` dir present, composed `<slug>-<mid8>` dir
absent) and **independently re-derived** the pre-WP03 answer — `get_main_repo_root(repo)
/ KITTY_SPECS_DIR / canonical`, *not* by calling the leaf — so the comparison is not
circular:

| quantity | value |
|---|---|
| canonical fold | `primary-read-delegation-fixture-01KYKMMT` |
| **write leg** (`resolve_retrospective_home`) | `…/kitty-specs/primary-read-delegation-fixture-01KYKMMT` |
| **pre-WP03, independently re-derived** | *(identical)* |
| `_compose_primary_feature_dir(canonical)` | *(identical)* |
| bare recovered dir | `…/kitty-specs/primary-read-delegation-fixture` |
| `read_dir(PRIMARY_METADATA)` | bare dir (seam still recovers) |
| canonicalizer calls per write-leg invocation | **1** |

So: `write_leg == pre_WP03 == leaf`, `write_leg != bare_dir` (no inherited backfill
recovery), and a **single** handle fold — the `leaf=7/planning=2` double-fold I measured
in cycle 1 is gone. NFR-001's accepted delta is back to routed reads only.

One observation I explicitly did **not** treat as a WP03 defect: on a backfilled mission
`read_dir(RETROSPECTIVE)` now returns the composed dir while `read_dir(PRIMARY_METADATA)`
returns the recovered bare dir. That asymmetry is **pre-existing** — `_backfilled_primary_dir`
in `resolution.py` is untouched by this lane (the lane's only `resolution.py` delta is the
four T016 callee-name substitutions) — and WP03's obligation was to *restore* it, which it
did. Attributing/closing it belongs to whichever WP routes the retrospective site.

---

## B4 / B2 — recorded

The `## WP03` section is landed on the planning branch (`a0109eeaf`), carrying the
cycle-1 finding, the divergence table, and the fifth-foundation-site record. Confirmed
present at `research/expected-reds.md:100` with the B1 and B2 subsections. Adjudicated as
handled by the orchestrator; not re-litigated here.

---

## The ex-bug-enforcing guard now bites

`tests/retrospective/test_home_resolution_single_authority.py` (pre-existing, outside
WP03's `owned_files`) previously asserted `"primary_feature_dir_for_mission" in names` —
that assertion was *itself* enforcing the regression. It now requires the leaf and
forbids the wrapper.

**Bite test.** `_module_source` reads `module.__file__`, so a plugin repointed
`writer.__file__` at the pre-fix snapshot, making the guard adjudicate the old body:

```
FAILED test_writer_authority_gates_on_primary_partition_kind
E  assert '_compose_primary_feature_dir' in
     {'_canonicalize_primary_read_handle', 'is_primary_artifact_kind', 'primary_feature_dir_for_mission'}
```

As shipped: **4 passed**. So the pin reds on exactly the reversion it exists to catch.

**Rationale judged, not the fact of touching.** The edit is forced by correctness: the
prior assertion mandated the very call that closes the cycle, so T016's obligation and
this test were in direct contradiction — the file could not stay untouched. It is a
*tightening* (adds a `not in` guard alongside the replaced `in` guard), not a relaxation,
and `test_every_placement_module_routes_through_the_authority` still passes, so no
authority coverage was traded away. Same class as the WP01 allow-list edits already
adjudicated as forced. Accepted; the `owned_files` gap is planning debt, not a WP03 defect.

---

## The three folds

**N1 — red-first proof is genuinely non-circular now.** It monkeypatches
`sys.modules[__name__].primary_feature_dir_for_mission`, which is exactly the binding the
positive `test_backfill_recovery_is_the_one_accepted_divergence` calls bare. The patch is
load-bearing: the positive test (green) pins `seam == wrapper == bare_dir`, so *without*
the patch the proof's `assert wrapper == fx.primary_dir` would red. Two tests, opposite
expectations, same fixture, both green — that is only possible if the patch is really
changing the resolved body.

**N2 — Class-C fixture binds distinct mocks.** `leaf_stub` and `wrapper_stub` are separate
`MagicMock`s, the wrapper returns a deliberately distinguishable
`/synthetic/wrapper-regression/…`, and `stubs["primary_feature_dir_for_mission"].call_count
== 0` is asserted in **both** the coord (3-call) and flat (2-call) topologies. A leg that
regressed onto the wrapper would break the convergence assertion rather than silently
matching. **5 passed.**

**N3 — stale docstring corrected** at `_read_path_resolver.py:1441-1447`; it now names the
leaf and states why the wrapper must not be used.

---

## Reconciliation — verified, not accepted on report

| gate | claimed | measured |
|---|---|---|
| `ruff check` (5 changed files) | 0 | **exit 0, "All checks passed!"** |
| `mypy` (project config: `strict = true`) on 3 changed `src/` files | clean | **"Success: no issues found in 3 source files"** |
| six C-008 gates | 168 passed / 3 failed | **168 passed / 3 failed** |
| regression slice | 1629 passed | **964 passed / 1 skipped / 0 failed** on `tests/retrospective/ tests/specify_cli/missions/ tests/mission_runtime/ tests/post_merge/` |

The 3 gate reds are **node-identical** to WP01's recorded expectations — zero new:

1. `test_coord_read_residuals_closeout.py::test_fr007_arm_live_identity_scan_is_clean`
2. `test_trio_seam_only.py::test_trio_imports_route_only_through_seam_wrappers`
3. `test_trio_seam_only.py::test_allowed_read_path_resolver_names_are_currently_used`

Per the C-008 hard constraint I ran targeted node sets only — never the full
`tests/architectural/` suite.

---

## Cycle-1 Verified items — confirmed not regressed

V1/V2 (census 46/43/3): the only `src/` deltas in this fix are one call line + two
docstring/comment blocks in `writer.py` and one docstring in `_read_path_resolver.py` —
no call-site count changes, and the leaf/wrapper frozenset the scanner targets is
unchanged. V3 (leaf unexported): re-confirmed above. V4: the harness was *strengthened*
(distinct mocks), not weakened. V5–V8: gates and lint re-run green above.

---

## Anti-pattern checklist

| # | Item | Verdict |
|---|---|---|
| 1 | Dead code | PASS — leaf has 12 production callers |
| 2 | Synthetic-fixture test | PASS — real git repos throughout the trace and equivalence cells |
| 3 | Silent empty return | PASS |
| 4 | FR coverage | **PASS** — FR-002/FR-003/FR-021 and now NFR-009 |
| 5 | Frozen surface | PASS |
| 6 | Locked decision | **PASS** — the `read_dir` call graph is acyclic, proved both directions |
| 7 | Shared-file ownership | PASS — both out-of-map edits carry per-site rationale and are forced |
| 8 | Production fragility | **PASS** — termination no longer depends on the `PRIMARY_METADATA` constant |

---

## Not blocked on (for a later WP, recorded not raised)

- `_AUTHORITY_NAMES` in `test_home_resolution_single_authority.py` still lists
  `primary_feature_dir_for_mission`, which no placement module calls any more. Harmless
  today (`writer.py` satisfies the set via the other two names) and the symbol is deleted
  in WP08 — a WP07/WP08 sweep item, not a defect here.
- The backfilled-mission `RETROSPECTIVE` vs `PRIMARY_METADATA` read asymmetry described
  under B3 — pre-existing, correctly restored rather than changed by this WP.

**Verdict: APPROVED.** WP04–WP07 are unblocked.
