---
work_package_id: WP03
title: Realistic Parallelism Preservation
dependencies: [WP02]
requirement_refs:
- FR-008
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks: [T016, T017, T018, T019, T020, T021]
agent: "claude:opus:reviewer:reviewer"
shell_pid: "14382"
history:
- at: '2026-04-06T13:45:48+00:00'
  actor: claude
  action: Created WP03 prompt during /spec-kitty.tasks
authoritative_surface: src/specify_cli/lanes/
execution_mode: code_change
owned_files:
- src/specify_cli/lanes/compute.py
- src/specify_cli/lanes/models.py
- tests/lanes/test_compute.py
- tests/lanes/test_models.py
- tests/lanes/test_collapse_report.py
---

# WP03 — Realistic Parallelism Preservation

## Objective

Refine the lane computation algorithm so that surface-heuristic merging (Rule 3) does not collapse WPs with provably disjoint file ownership. Add a CollapseReport data model that records every union event with its triggering rule and evidence, so operators can understand exactly why parallelism was reduced.

This WP addresses issue #423 (silent parallelism collapse).

## Context

### Current State

`compute_lanes()` uses a union-find with three rules (`compute.py:186-216`):
- **Rule 1** (line 189): Dependencies → same lane (correct by design)
- **Rule 2** (line 195): Overlapping owned_files → same lane (correct when globs genuinely overlap)
- **Rule 3** (line 204): Shared surface keywords → same lane (overly aggressive)

Rule 3 uses `_SURFACE_KEYWORDS` (lines 38-47) with broad substring matching. The word "api" matches the "api" surface; "sidebar" matches "app-shell". Two WPs with completely disjoint file ownership can be collapsed into one lane simply because both mention "api" in their body text.

There is no reporting mechanism to explain why WPs were collapsed. Tests at `test_compute.py:84-93` explicitly document the collapse behavior as expected.

### Target State

- Rule 3 only merges WPs when their owned_files overlap (not when they're provably disjoint)
- CollapseReport records every union event with rule name and evidence
- Independent-WP collapses are counted and surfaced
- Operators can read the report and understand exactly why any collapse happened

### Important: WP02 Must Complete First

This WP depends on WP02 because WP02 adds the `LaneComputationError` exception, the planning-artifact diagnostic, and the completeness assertion. WP03 builds on those foundations: it modifies the same union-find loop and extends the output model.

**Owned files note**: WP02 owns `compute.py` for its changes (assertions, error paths). WP03 owns `models.py` for the new data models and the new test file. Both WPs touch `compute.py`, but WP02's changes are in the filtering/assertion area (lines 170-220) while WP03's changes are in the union rules area (lines 186-216) and the return value construction. They share a lane by dependency, so no conflict.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`
- To start implementation: `spec-kitty implement WP03`

---

## Subtask T016: Add CollapseReport Data Model

**Purpose**: Create data structures to capture every union-find merge event.

**Steps**:

1. In `src/specify_cli/lanes/models.py`, add:
   ```python
   @dataclass(frozen=True)
   class CollapseEvent:
       """A single union-find merge event during lane computation."""
       wp_a: str
       wp_b: str
       rule: str          # "dependency", "write_scope_overlap", "surface_heuristic"
       evidence: str      # human-readable explanation

       def to_dict(self) -> dict[str, str]:
           return {"wp_a": self.wp_a, "wp_b": self.wp_b,
                   "rule": self.rule, "evidence": self.evidence}

   @dataclass
   class CollapseReport:
       """Summary of all union-find merge events during lane computation."""
       events: list[CollapseEvent]
       independent_wps_collapsed: int  # WPs with no dep relationship but same lane

       def to_dict(self) -> dict:
           return {
               "events": [e.to_dict() for e in self.events],
               "total_merges": len(self.events),
               "independent_wps_collapsed": self.independent_wps_collapsed,
               "by_rule": self._count_by_rule(),
           }

       def _count_by_rule(self) -> dict[str, int]:
           counts: dict[str, int] = {}
           for e in self.events:
               counts[e.rule] = counts.get(e.rule, 0) + 1
           return counts
   ```

**Files**: `src/specify_cli/lanes/models.py`

**Validation**: `CollapseReport().to_dict()` serializes correctly. `CollapseEvent` is frozen/hashable.

---

## Subtask T017: Record Collapse Events During Union-Find Rules

**Purpose**: Every union operation records a CollapseEvent with the triggering rule and evidence (FR-008).

**Steps**:

1. In `compute.py`, initialize the events list before the rules:
   ```python
   collapse_events: list[CollapseEvent] = []
   ```

2. Modify Rule 1 (lines 189-193) to record events:
   ```python
   for wp_id in code_wp_ids:
       for dep in dependency_graph.get(wp_id, []):
           if dep in uf._parent and uf.find(wp_id) != uf.find(dep):
               collapse_events.append(CollapseEvent(
                   wp_a=wp_id, wp_b=dep,
                   rule="dependency",
                   evidence=f"{wp_id} depends on {dep}",
               ))
           if dep in uf._parent:
               uf.union(wp_id, dep)
   ```

3. Modify Rule 2 (lines 195-202) to record events:
   ```python
   for wp_a, wp_b in find_overlap_pairs(code_manifests):
       if uf.find(wp_a) != uf.find(wp_b):
           overlap = _describe_overlap(code_manifests[wp_a], code_manifests[wp_b])
           collapse_events.append(CollapseEvent(
               wp_a=wp_a, wp_b=wp_b,
               rule="write_scope_overlap",
               evidence=overlap,
           ))
       uf.union(wp_a, wp_b)
   ```

4. Add helper `_describe_overlap(a: OwnershipManifest, b: OwnershipManifest) -> str` that identifies which specific glob pairs overlap. Use `_globs_overlap()` from `validation.py`.

5. Rule 3 recording is part of T018 (refined rule).

**Files**: `src/specify_cli/lanes/compute.py`

**Validation**: Test with dependent WPs → CollapseEvent with rule="dependency".

---

## Subtask T018: Refine Rule 3 — Gate on Non-Disjoint Ownership

**Purpose**: Surface-heuristic merging should only happen when WPs have non-disjoint file ownership (FR-009).

**Steps**:

1. Add helper function:
   ```python
   def _are_disjoint(manifest_a: OwnershipManifest, manifest_b: OwnershipManifest) -> bool:
       """Return True if no glob from A overlaps with any glob from B."""
       for glob_a in manifest_a.owned_files:
           for glob_b in manifest_b.owned_files:
               if _globs_overlap(glob_a, glob_b):
                   return False
       return True
   ```
   Import `_globs_overlap` from `ownership.validation`.

2. Replace Rule 3 (lines 204-216):
   ```python
   if wp_bodies:
       wp_surfaces: dict[str, list[str]] = {}
       for wp_id in code_wp_ids:
           body = wp_bodies.get(wp_id, "")
           wp_surfaces[wp_id] = infer_surfaces(body)

       for wp_a, wp_b in combinations(code_wp_ids, 2):
           surfaces_a = set(wp_surfaces.get(wp_a, []))
           surfaces_b = set(wp_surfaces.get(wp_b, []))
           if surfaces_a & surfaces_b:
               # Only merge if ownership is NOT provably disjoint
               ma = code_manifests.get(wp_a)
               mb = code_manifests.get(wp_b)
               if ma and mb and _are_disjoint(ma, mb):
                   continue  # Disjoint ownership — surface match is not enough
               shared = sorted(surfaces_a & surfaces_b)
               if uf.find(wp_a) != uf.find(wp_b):
                   collapse_events.append(CollapseEvent(
                       wp_a=wp_a, wp_b=wp_b,
                       rule="surface_heuristic",
                       evidence=f"shared surfaces {shared} with non-disjoint ownership",
                   ))
               uf.union(wp_a, wp_b)
   ```

3. This is a behavioral change. The test `test_compute.py:124-150` (`TestSurfaceGrouping`) will need updating: independent WPs with disjoint ownership should now remain in separate lanes despite shared surfaces.

**Files**: `src/specify_cli/lanes/compute.py`

**Validation**: WP A owns `src/a/**`, WP B owns `src/b/**`, both mention "api" → separate lanes (not collapsed).

---

## Subtask T019: Count Independent-WP Collapses

**Purpose**: Identify how many collapse events forced together WPs that have no direct or transitive dependency relationship.

**Steps**:

1. After computing all collapse events and building lane groups, cross-reference:
   ```python
   def _count_independent_collapses(
       events: list[CollapseEvent],
       dependency_graph: dict[str, list[str]],
   ) -> int:
       """Count events where wp_a and wp_b have no dep relationship."""
       count = 0
       # Build transitive closure of dependencies
       transitive = _transitive_deps(dependency_graph)
       for event in events:
           if event.rule == "dependency":
               continue  # By definition not independent
           a, b = event.wp_a, event.wp_b
           if b not in transitive.get(a, set()) and a not in transitive.get(b, set()):
               count += 1
       return count
   ```

2. Store result in `CollapseReport.independent_wps_collapsed`.

**Files**: `src/specify_cli/lanes/compute.py`

**Validation**: Two independent WPs collapsed by write-scope → count = 1. Two dependent WPs collapsed → count = 0.

---

## Subtask T020: Wire Collapse Report into Output

**Purpose**: Make the collapse report available in finalize-tasks JSON output and from compute_lanes return value.

**Steps**:

1. Modify `compute_lanes()` return. Two options:
   - Add `collapse_report: CollapseReport` field to `LanesManifest`
   - Return `tuple[LanesManifest, CollapseReport]`

   Prefer adding to `LanesManifest` for consistency (it already contains diagnostic data). Add as an optional field with a default empty report.

2. In `LanesManifest.to_dict()`, include:
   ```python
   if self.collapse_report and self.collapse_report.events:
       d["collapse_report"] = self.collapse_report.to_dict()
   ```

3. In `mission.py` finalize-tasks, surface in JSON output:
   ```json
   "lanes": {
     "computed": true,
     "count": 3,
     "collapse_report": {
       "total_merges": 4,
       "independent_wps_collapsed": 1,
       "by_rule": {"dependency": 2, "write_scope_overlap": 1, "surface_heuristic": 1}
     }
   }
   ```

4. In console output, print a summary when independent collapses > 0:
   ```
   ⚠ 1 independent WP pair collapsed into same lane. Run with --json to see details.
   ```

**Files**: `src/specify_cli/lanes/models.py`, `src/specify_cli/lanes/compute.py`, `src/specify_cli/cli/commands/agent/mission.py`

**Validation**: End-to-end test: feature with known collapse → JSON includes collapse_report.

---

## Subtask T021: Write Regression Tests

**Purpose**: Cover all WP03 changes with targeted tests.

**Tests to add/modify**:

1. **`tests/lanes/test_collapse_report.py`** (new):
   - `test_collapse_event_serialization`: CollapseEvent.to_dict() round-trips
   - `test_collapse_report_counts_by_rule`: correct per-rule counts
   - `test_empty_collapse_report`: no events → clean serialization

2. **`tests/lanes/test_compute.py`** (modify):
   - `test_disjoint_ownership_preserves_parallelism`: WP A `src/a/**`, WP B `src/b/**`, same surface → TWO lanes
   - `test_non_disjoint_with_surface_still_collapses`: overlapping ownership + shared surface → one lane
   - `test_collapse_events_recorded_for_dependency`: dep-based merge → event with rule="dependency"
   - `test_collapse_events_recorded_for_overlap`: overlap-based merge → event with rule="write_scope_overlap"
   - `test_independent_collapse_count`: independent WPs forced to same lane → count > 0
   - `test_dependent_collapse_not_counted_independent`: dependent WPs in same lane → count = 0
   - **UPDATE** `TestSurfaceGrouping` tests: tests that assumed disjoint WPs collapse by surface alone now need to assert separate lanes (or be rewritten with non-disjoint ownership)

3. **`tests/lanes/test_models.py`** (modify):
   - `test_lanes_manifest_with_collapse_report_round_trip`: serialization includes collapse_report

**Files**: `tests/lanes/test_collapse_report.py` (new), `tests/lanes/test_compute.py`, `tests/lanes/test_models.py`

---

## Definition of Done

- [ ] WPs with disjoint owned_files are NOT collapsed by shared surface keywords alone
- [ ] Collapse report records every union event with rule and evidence
- [ ] Independent-WP collapses are counted separately
- [ ] Collapse report appears in finalize-tasks JSON output
- [ ] Console output warns when independent collapses > 0
- [ ] Existing features with valid lanes.json still compute identically (except where Rule 3 refinement correctly produces more parallel lanes)
- [ ] All tests pass, mypy --strict clean on changed files

## Reviewer Guidance

- The key behavioral change is in Rule 3: surface matches no longer collapse WPs with disjoint ownership. Verify by reading `test_disjoint_ownership_preserves_parallelism`.
- Check that `_are_disjoint` correctly handles the edge case where one WP has no manifest in `code_manifests` (should not skip the merge in that case — absence of proof is not proof of disjointness).
- Run compute_lanes on existing features to verify C-005 (no regressions for mid-implementation features).

## Activity Log

- 2026-04-06T14:34:25Z – claude:sonnet:implementer:implementer – shell_pid=13562 – Started implementation via action command
- 2026-04-06T14:39:30Z – claude:sonnet:implementer:implementer – shell_pid=13562 – Ready for review: CollapseReport + Rule 3 disjoint-ownership gate. 127 tests pass. All 6 subtasks complete.
- 2026-04-06T14:39:51Z – claude:opus:reviewer:reviewer – shell_pid=14382 – Started review via action command
- 2026-04-06T14:41:58Z – claude:opus:reviewer:reviewer – shell_pid=14382 – Review passed: CollapseEvent/CollapseReport models correctly implemented with serialization round-trips. All 3 union rules record CollapseEvents. Rule 3 properly gated on disjoint ownership. Missing-manifest edge case handled defensively. Independent collapse counting uses transitive closure. Collapse report wired into both finalize-tasks JSON paths with console warning. Old test updated (not deleted) to assert separate lanes for disjoint ownership. 127 lane tests pass.
- 2026-04-06T17:29:20Z – claude:opus:reviewer:reviewer – shell_pid=14382 – Done override: Feature 065 already merged to main via spec-kitty merge. Worktrees cleaned up. Moving to done for event log completeness.
