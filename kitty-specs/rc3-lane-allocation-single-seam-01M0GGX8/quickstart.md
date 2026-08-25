# Quickstart — verifying M8 (Lane-allocation single-seam)

Prereqs: `export PATH="$PWD/.venv/bin:$PATH"` (shadow-venv footgun — bare `spec-kitty`/`python` run the
wrong fork via the pyenv shim). Targeted tests only; the full suite is CI's authority.

## WP2 — the shared allocation seam (FR-001/002/003)

```bash
# Seam unit + all-four-routes coverage
.venv/bin/python -m pytest tests/specify_cli/lanes/ -k "lane_base or resolve_lane_base or unhonorable" -q
# NFR-001 backward-compat: base=None parentage byte-identical on every route
.venv/bin/python -m pytest tests/specify_cli/lanes/ -k "base_none or parentage" -q
```
Expect: `--base <ref>` honored on fresh-coord AND fresh-legacy; `UnhonorableBaseError` (route named) on
reuse / crash_recovery / dependency_lane / detached_base; no fabricated success line.

## WP3 — anti-bypass guard (FR-007)

```bash
.venv/bin/python -m pytest tests/architectural/test_lane_allocation_single_seam.py -q
```
Expect: passes with the seam in place; fails (naming file:line) if an inline parent-ref computation is
introduced outside `resolve_lane_base_or_refuse`.

## WP1 — authoritative topology predicate residual (#3460)

```bash
.venv/bin/python -m pytest tests/specify_cli/coordination/ -k "topology_predicate or single_authority" -q
# Regression guard: the emit-annotation exclusion is preserved (#2939)
.venv/bin/python -m pytest tests -k "flat_topology_annotation_still_lands" -q
```

## WP4 — read-side degrade companion (#3462)

```bash
.venv/bin/python -m pytest tests/mission_runtime/ -k "read_dir_or_degrade" -q
# #1848 data-loss re-raise preserved
.venv/bin/python -m pytest tests -k "coordination_branch_deleted or 1848 or data_loss" -q
```

## WP5 — #3536 no-coord refusal

```bash
.venv/bin/python -m pytest tests/coordination/ -k "3536 or no_coord_remedy or protected_branch_refused" -q
```
Expect: lanes/single-branch protected-target refusal → followable remedy (no "coordination branch"
instruction); coord-topology refusal remedy unchanged.

## Guardrail regression sweep (targeted, after WP2 and WP4)

```bash
# Real test names verified against main (post-plan squad, debugger): reuse_self_heal / dep_merge_rollback
# match ZERO tests — use the substrings below instead.
.venv/bin/python -m pytest tests -k "2993 or planning_artifacts or crash_recovery or sparse_checkout or dependency_tip or (1915 or rolls_back)" -q
# #2993: tests/lanes/test_issue_2993_lane_planning_ancestry.py::test_lane_worktree_does_not_descend_from_planning_artifacts
# #1915: tests/lanes/test_worktree_allocator_atomicity.py::test_1915_later_dep_conflict_rolls_back_earlier_dep_merge
```

## Full lint/type gate (pre-push)

```bash
.venv/bin/ruff check . && .venv/bin/mypy src/
.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q   # prose touched
```
