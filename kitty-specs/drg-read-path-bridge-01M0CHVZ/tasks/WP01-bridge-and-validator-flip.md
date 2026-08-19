---
work_package_id: WP01
title: Bridge org fragment edges into cascade + atomic validator flip
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: mission/drg-read-path-bridge-01M0CHVZ
merge_target_branch: mission/drg-read-path-bridge-01M0CHVZ
branch_strategy: Planning artifacts for this mission were generated on mission/drg-read-path-bridge-01M0CHVZ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/drg-read-path-bridge-01M0CHVZ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-drg-read-path-bridge-01M0CHVZ
base_commit: ab15441bed489ff85d7d2e9fab495062fec1a695
created_at: '2026-08-19T14:22:22.951834+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- at: '2026-08-19T14:10:00+00:00'
  actor: claude
  note: WP created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_drg_helpers_fragment_bridge.py
- tests/specify_cli/doctrine/test_pack_validator_fragment_finding.py
execution_mode: code_change
owned_files:
- src/charter/_drg_helpers.py
- src/charter/drg.py
- src/specify_cli/cli/commands/charter/activate.py
- src/specify_cli/cli/commands/charter/deactivate.py
- src/specify_cli/doctrine/pack_validator.py
- tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py
- tests/charter/test_drg_helpers_fragment_bridge.py
- tests/specify_cli/doctrine/test_pack_validator_fragment_finding.py
role: implementer
tags: []
tracker_refs:
- '3572'
- '3573'
---

## ⚡ Do This First: Load Agent Profile

Load your profile: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). ATDD red-first; `mypy --strict` + **zero** new suppressions (C-005); complexity ≤ 15; realistic test data; `charter` must not import `specify_cli`.

## Objective

Make org `requires`/`suggests` edges authored **only** in a pack's
`drg/fragment.yaml` cascade at `charter activate/deactivate`, by routing the org
layer through the **existing** `merge_three_layers` from inside
`charter/_drg_helpers.py::load_validated_graph`. Re-scope the D-005 graphless
warning to fire only when a pack ships neither a root graph nor a fragment, and
reconcile the `pack validate` finding **in the same change** so the tool never
says "this fragment won't be read" while the runtime reads it. This single WP is
the SC-001..SC-004 deliverable and lands atomically (C-001 / NFR-003).

Closes #3572 and folds #3573.

## Context (read before touching code)

- **Bridge seam**: `src/charter/_drg_helpers.py::load_validated_graph` (~L58) folds
  only root-level `*.graph.yaml` via `merge_layers` in the per-root loop. Its D-005
  warning branch (~L153) fires for any on-disk root with no root-level graph.
- **Reuse target (DO NOT modify — C-002)**:
  `src/doctrine/drg/merge.py::merge_three_layers` (~L1143) already resolves edge
  endpoints (`_resolve_edge_endpoint`) and de-dups cross-fragment edges
  (`_OrgEdgeCollector`), returning a `DRGGraph` whose `.edges` carry the fragment
  `requires`/`suggests` edges. Signature:
  `merge_three_layers(built_in: DRGGraph, org_fragments: list[OrgDRGFragment], project: DRGGraph | None) -> DRGGraph`.
- **Loader**: `src/charter/drg.py::load_org_drg` (~L167) returns
  `list[OrgDRGFragment]` by calling `load_org_pack` per configured pack.
  `load_org_pack` **raises `OrgPackMissingError`** when `<pack>/drg/fragment.yaml`
  is absent. **PROBED**: a root-graph-only pack therefore makes `load_org_drg`
  raise — so the cascade caller cannot call it strictly without regressing the
  green root-graph tests.
- **Layer boundary (C-005)**: `src/charter/` must not import `specify_cli`. The
  `specify_cli` caller supplies the fragments; `_drg_helpers` only accepts the
  param. `OrgDRGFragment` is importable via `charter.drg` /
  `doctrine.drg.org_pack_loader` (both below the boundary).
- **Diagnostic invariance (NFR-001)**: do **not** touch the four diagnostic callers
  of `merge_three_layers` (`lint.py`, `_status_collectors.py`, `_doctrine_collect.py`,
  `_profile_health_render.py`) or `load_org_drg`'s strict default.
- **Contracts**: `contracts/load_validated_graph.md`, `contracts/pack_validator_finding.md`.
  **Design decisions**: research.md D1–D6.

## Subtasks

### T001 — RED-first: flip the pinning test (FR-005, C-011)

In `tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py`, transform
`TestGraphlessPackWithFragmentEdgeIsInvisibleToCascade::test_requires_edge_in_fragment_yaml_does_not_cascade`
into the positive contract:

- Rename the class to reflect the new behaviour (e.g.
  `TestFragmentYamlEdgeCascades`) and rewrite the docstring (it is no longer a
  disclosed limitation).
- Keep the same fixture (`fragment-only-pack` with `A requires B` in
  `drg/fragment.yaml`).
- **Flip the assertions**:
  - `assert "b-directive" in activated` (was `not in`).
  - `assert "Cascade-activated" in result.output` (was `not in`).
  - Assert **no** graphless warning fires — replace the
    `"ships no root-level DRG graph"` assertion with its negation: assert no
    caplog record contains that phrase for this pack (the pack ships a
    `drg/fragment.yaml`, so it is not graphless — FR-004).
- **Commit this test RED first** (first commit of the lane): run it and confirm it
  FAILS on the current base before implementing T002–T006. This is the executable
  red→green ATDD contract the reviewer checks.

**Validation**: `PWHEADLESS=1 python -m pytest tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py -k FragmentYamlEdgeCascades -q` → RED before T003/T005, GREEN after.

### T002 — `load_org_drg(strict=…)` resilient per-pack load (research.md D3)

In `src/charter/drg.py::load_org_drg`, add `strict: bool = True`:

- `strict=True` (default) — behaviour **identical** to today (delegates to
  `load_org_pack`, which raises `OrgPackMissingError` on a missing
  `drg/fragment.yaml`). Diagnostic callers keep this → NFR-001.
- `strict=False` — for each configured pack, skip it when
  `<pack_root>/drg/fragment.yaml` does not exist (contributes no fragment layer);
  otherwise load it via `load_org_pack`. Preserve the true `layer_index` from the
  full-registry `enumerate` (a skipped pack does not renumber its siblings).
- Update the docstring; keep `mypy --strict` clean. `load_org_drg` stays in
  `charter.drg.__all__`.

**Unit test** (`tests/charter/test_drg_helpers_fragment_bridge.py`, new): a config
with one root-graph-only pack →
`load_org_drg(root, strict=True)` raises `OrgPackMissingError`;
`load_org_drg(root, strict=False)` returns `[]`. A config with one fragment pack →
both return the fragment (non-vacuity: strict=False still loads present fragments).

### T003 — Bridge `load_validated_graph(org_fragments=…)` (FR-001/002/003, research.md D1)

In `src/charter/_drg_helpers.py::load_validated_graph`, add keyword-only
`org_fragments: list[OrgDRGFragment] | None = None`. Compose:

```python
built_in = load_built_in_graph()
root_merged = built_in
for root in roots:
    if root and root.exists() and has_graph_files(root):
        root_merged = merge_layers(root_merged, load_graph_or_dir(root))
        continue
    # (warning branch re-scoped in T004)
project = load_graph_or_dir(project_dir) if has_graph_files(project_dir) else None
if org_fragments:
    merged = merge_three_layers(built_in=root_merged, org_fragments=org_fragments, project=project)
else:
    merged = merge_layers(root_merged, project)
assert_valid(merged)
return merged
```

- Import `merge_three_layers` from `doctrine.drg.merge` and `OrgDRGFragment` from
  `doctrine.drg.org_pack_loader` (or via `charter.drg`) — never from `specify_cli`.
- The `else` branch must be **byte-behaviourally identical** to today's path so
  build-time / no-fragment callers are unaffected (FR-003).
- Do not re-implement endpoint/dedup logic (C-002) — `merge_three_layers` owns it.

**Unit test** (same new file): build a built-in + one `OrgDRGFragment` carrying
`A requires B`; assert the returned `DRGGraph.edges` contains that resolved edge
(reachability), and that omitting `org_fragments` yields the pre-existing graph
unchanged (FR-003 inertness).

### T004 — Re-scope the D-005 graphless warning (FR-004, C-003, research.md D2)

In the per-root loop, fire the warning only when the root ships **neither** a
root-level `*.graph.yaml` **nor** a `drg/fragment.yaml`:

```python
if root and root.exists() and not (root / "drg" / "fragment.yaml").exists():
    _LOGGER.warning(...)   # existing message, unchanged wording
```

Preserve the exact log message and logger name (`charter._drg_helpers`) so the
`TestGraphlessOrgPackDegradesGracefully` assertion (a truly graphless pack) still
matches. Only the trigger narrows (degrade posture preserved — C-003).

**Validation**: `TestGraphlessOrgPackDegradesGracefully` stays green (genuinely
graphless pack still warns); the flipped T001 test sees no warning.

### T005 — Thread the cascade call sites (FR-001)

Pass fragments alongside the `org_roots` already resolved:

- `src/specify_cli/cli/commands/charter/activate.py` L315 and L409:
  `graph = load_validated_graph(repo_root, org_roots=org_roots, org_fragments=load_org_drg(repo_root, strict=False))`
- `src/specify_cli/cli/commands/charter/deactivate.py` L165: same shape.
- Import `load_org_drg` from `charter.drg` (already the import source in these
  modules' neighbourhood). Keep it lazy/local if that matches the existing import
  style at each call site.

This is what makes T001 go GREEN (the integration test drives `charter activate`).

**Validation**: the full `test_org_cascade_chain.py` file is GREEN (15→ still all
pass, with the flipped test now asserting cascade).

### T006 — Reconcile the validator (FR-006, C-001, NFR-003, research.md D5)

In `src/specify_cli/doctrine/pack_validator.py::_check_drg_root_graph_missing`
(~L653–688):

- **Re-scope**: return no finding when the pack ships a `drg/fragment.yaml`
  (its DRG is now read via the bridge). Keep flagging a genuinely-unread
  `drg/*.graph.yaml`-only pack (no root graph, no fragment). Mirror T004's
  predicate.
- **Re-message**: replace the false blanket "reads the pack root directly, not
  drg/ fragments — this pack's DRG content will not be read as authored" with an
  accurate statement of the runtime read-set (pack-root `*.graph.yaml` **and**
  `drg/fragment.yaml`), naming `drg/*.graph.yaml` as the unread shape. Also fix the
  two docstring references (~L121, ~L361) if they repeat the stale blanket claim.
- **Land in the SAME commit as T003** (atomic — no intermediate state where
  `pack validate` contradicts the runtime).

**Unit test** (`tests/specify_cli/doctrine/test_pack_validator_fragment_finding.py`,
new): a `drg/fragment.yaml`-bearing pack (no pack-root graph) → **no**
`drg_root_graph_missing` finding; a `drg/*.graph.yaml`-only pack → finding still
present.

### T007 — Regression sweep + single golden re-ledger (NFR-001/002)

- `grep -rn` the affected test surfaces for golden/count assertions that move when
  fragment edges become cascade-visible (cascade-reach counts, `charter list` /
  `doctor doctrine` snapshots). Capture any real delta in **one** update with a
  written rationale in the commit message; if nothing moves, state that explicitly.
- Assert diagnostic invariance: run the diagnostic surfaces and confirm output is
  unchanged (the four `merge_three_layers` callers are untouched).
- Run targeted suites green:
  `tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py`,
  `tests/charter/`, `tests/specify_cli/doctrine/`,
  `tests/architectural/test_layer_rules.py`,
  `tests/architectural/test_runtime_charter_doctrine_boundary.py`, and
  `tests/architectural/test_no_legacy_terminology.py`.

**Validation**: all targeted suites green; `ruff check` + `mypy --strict` clean on
touched files with zero new suppressions.

## Branch Strategy

Planning/base branch and final merge target are both
`mission/drg-read-path-bridge-01M0CHVZ` (single_branch). `/spec-kitty.implement`
allocates the execution worktree from `lanes.json`; complete the work there and it
merges back into `mission/drg-read-path-bridge-01M0CHVZ`. The mission branch later
becomes a PR to `main` — never a direct push to `origin/main`.

## Definition of Done

- SC-001: a `drg/fragment.yaml`-only `A requires B` pack cascade-activates B (0
  silently-dropped fragment edges).
- SC-002: a fragment-only pack emits no graphless warning; a truly graphless pack
  still warns.
- SC-003: `pack validate` emits no "will not be read" finding for a fragment pack;
  a `drg/*.graph.yaml`-only pack still flagged.
- SC-004: diagnostic output unchanged; any cascade-reach delta in one reviewed
  golden update.
- Validator flip and runtime bridge in the same commit (C-001/NFR-003); reuse of
  `merge_three_layers` (no forked dedup — C-002); `charter` free of `specify_cli`
  imports (C-005); ruff + mypy --strict clean, zero new suppressions.
- Red→green proven: T001 RED on base, GREEN on final; root-graph cascade tests
  stay green.

## Reviewer guidance

- Confirm the ATDD ordering: the flipped test was committed RED before the bridge.
- Confirm `merge_three_layers` / `_resolve_edge_endpoint` / `_OrgEdgeCollector` are
  **unmodified** (C-002) and no diagnostic caller changed (NFR-001).
- Confirm the `org_fragments`-omitted path is behaviourally identical to today
  (FR-003) — check the `else: merge_layers(root_merged, project)` branch.
- Confirm the warning re-scope and validator re-scope key off the **same**
  predicate ("neither root graph nor `drg/fragment.yaml`").
- Confirm the validator message no longer makes a claim the runtime contradicts,
  and the `drg/*.graph.yaml`-only finding is retained (dead-content protection).
- Confirm no `# noqa` / `# type: ignore` added; `src/charter/` has no
  `specify_cli` import.
