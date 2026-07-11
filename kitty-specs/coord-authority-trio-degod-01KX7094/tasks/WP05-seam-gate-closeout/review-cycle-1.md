---
affected_files: []
cycle_number: 1
mission_slug: coord-authority-trio-degod-01KX7094
reproduction_command:
reviewed_at: '2026-07-11T10:09:37Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
---

# WP05 Review — Cycle 1 — CHANGES REQUESTED

Reviewer: reviewer-renata (opus). Independent verification against the WP05 DoD
(FR-004 / FR-007 / SC-002) and T027–T030.

## Summary

The two new architectural gates are **well-built and genuinely non-vacuous** —
I independently plant-and-caught both and they bite (evidence below). Ruff,
mypy, characterization (73 passed), zero trio `noqa:C901`, and the three lenient
read contracts (zero `require_exists=True` in the trio) all check out.

**BUT the closeout gate itself is not met.** T029 / the Definition of Done
require `tests/architectural/` to be **green**. It is not:

```
FAILED tests/architectural/test_untrusted_path_containment.py::test_audit_passes_on_fixed_tree
FAILED tests/architectural/test_untrusted_path_containment.py::test_all_discovered_rows_appear_in_inventory
2 failed, 867 passed, 4 skipped in 487.29s
```

The WP05 commit message dismisses these as *"2 pre-existing failures
(test_untrusted_path_containment.py) ... documented pre-existing in the sibling
guard's own docstring, confirmed unrelated by stash-verification."* **That
characterization is incorrect.** These failures are introduced **by this
mission** and the closeout WP must resolve them (or route them back to WP02)
before the arch dir is green.

## Blocking Issue — mission-introduced arch regression, not pre-existing

`tests/architectural/untrusted_path_audit/audit.py` is an undercount/overcount
tripwire over `feature_dir / wp_slug` FS-sink joins, keyed against
`inventory.md`. The trio decomposition (WP02) **moved** those joins out of
`agent/workflow.py` into the new split files but nobody updated `inventory.md`:

Undercount (discovered sinks MISSING from inventory) — all in files this mission
created:
- `cli/commands/agent/workflow_cores.py:372` — `has_prior_rejection`, `sub_artifact_dir = feature_dir / wp_slug`
- `cli/commands/agent/workflow_executor.py:868` — `implement_try_render_fix_mode_prompt`, `sub_artifact_dir = feature_dir / wp_slug`
- `cli/commands/agent/workflow_executor.py:931` — `implement_capture_baseline`, `baseline_artifact = feature_dir / wp_slug / ...`
- `cli/commands/agent/workflow_executor.py:1467` — `_review_baseline_context_lines`, `rv_baseline_path = rv_feature_dir / wp_slug / ...`

Overcount (ghost inventory rows whose sink was moved away by the split):
- `cli/commands/agent/workflow.py:921` — `_has_prior_rejection` (now `workflow_cores.py:372`)
- `cli/commands/agent/workflow.py:1621` — `implement` (now in `workflow_executor.py`)

### Why "pre-existing / unrelated by stash-verification" is wrong
- `git cat-file -e kitty/mission-coord-authority-trio-degod-01KX7094:.../workflow_cores.py`
  → **absent on the mission base**. The failing sinks live in files that exist
  *only* because of this mission's decomposition.
- `git log <base>..HEAD -- tests/architectural/untrusted_path_audit/inventory.md`
  → **empty**. The inventory was never reconciled with the moved joins.
- Stash-verification only removed WP05's *own* test files; the WP02 decomposition
  is already merged into lane-e's base, so the failure persists and merely *looks*
  "unrelated to WP05's diff." It is a mission regression, not a base-branch one.

This is exactly the class of cross-WP arch failure the WP05 closeout exists to
catch — it correctly fixed WP01's `test_no_tmp_paths_in_tests` /
`test_no_new_orphan_surfaces` / `test_split_preserves_zero_orphans` failures, but
missed (and then mislabeled) the WP02-caused untrusted-path-containment failures.

### Required fix
Reconcile `tests/architectural/untrusted_path_audit/inventory.md` so the audit is
green: run `python tests/architectural/untrusted_path_audit/audit.py`, add the 4
new rows for `workflow_cores.py:372` + `workflow_executor.py:868/931/1467` (with
real source/sink_op/disposition/rationale columns, mirroring the pre-split
workflow.py rows the joins came from), and remove/re-anchor the 2 ghost
`workflow.py:921/1621` rows. Then re-run the full `tests/architectural/` suite and
confirm 0 failed. If the operator judges inventory ownership belongs to WP02
rather than the WP05 closeout, route it there — but the mission cannot present a
green arch dir until this is done, and WP05 is the gate WP that must not sign off
on a red arch suite.

## Verified GREEN (for the record)

1. **Seam-only gate NON-VACUOUS (T027)** — independently planted a real
   `from specify_cli.core.constants import KITTY_SPECS_DIR` and
   `from specify_cli.missions._read_path_resolver import resolve_feature_dir_for_slug`
   into `workflow_cores.py`; `test_trio_imports_route_only_through_seam_wrappers`
   FAILED naming both (`workflow_cores.py:35`/`:36`). Reverted clean. The
   allowlist-integrity and blessed-name-usage guards keep it honest.
2. **No-I/O gate NON-VACUOUS (T028)** — independently planted a real
   `open(path).read()` + `subprocess.run(...)` into `acceptance/summary_core.py`;
   `test_cores_perform_no_unallowlisted_io` FAILED naming both with
   content-anchored composite keys. Reverted clean. Classification is genuine
   `ast.Call` call-syntax detection (not an import-scan): `subprocess` imported
   *inside* the planted function was still caught. The 8 self-check plants
   (read_text/write_bytes/open/subprocess/os.system/sqlite3/network) all pass.
3. **WP01 arch fixes (T029)** — `test_no_tmp_paths_in_tests`,
   `test_no_new_orphan_surfaces`, `test_split_preserves_zero_orphans` now pass;
   the `test_trio_json_envelope.py` fix is minimal (docstring prose reword away
   from the literal `/tmp/` substring + CI shard routing) — **no assertions
   deleted**, `_assert_skeleton` pins unchanged. Good.
4. **Zero trio `noqa:C901`** — confirmed (rg over all 8 trio files → none).
5. **Characterization** — 73 passed. Ruff + mypy clean on all changed files.
6. **3 read contracts intact (T030)** — zero `require_exists=True` in the trio;
   no lenient site flipped fail-closed.

Fix the `inventory.md` reconciliation, get `tests/architectural/` to 0 failed,
and this is an easy approve — the gates themselves are solid.
