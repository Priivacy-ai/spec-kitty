# Tasks: Implement-Loop Coord-Authority Completion

**Mission**: `implement-loop-coord-authority-completion-01KW2E7A`
**Branch**: `design/coord-authority-remediation-2160` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Routes the implement/review-loop PRIMARY-kind reads (`tasks/`, `WP*.md`, `lanes.json`,
WP-frontmatter) onto the kind-aware seam `resolve_planning_read_dir(kind=...)` for
coordination-topology missions; hardens the dir-read ratchet (inline-shape + whole-`src`
+ self-test); closes #2140 and folds #2183.

**Ownership / lane note:** WP02 owns `tests/architectural/test_gate_read_literal_ban.py`
(the dir-read ratchet + `_DIR_READ_KNOWN_RESIDUALS`). The routing WPs (WP03–WP06) each
**remove their own pins** from that file in the same commit they route (FR-009) — a
rationale-backed out-of-map edit — so they form a **sequential chain** (one lane) to avoid
a shared-file race. WP01 (fixture), WP08 (#2140), WP09 (dead-symbol) are parallel.
**C-009: never edit `merge/`, `lanes/`, or `core/worktree_topology` — those are #2185.**

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Build shared un-stubbed coord-topology fixture (status-only husk + primary tasks/+lanes.json) | WP01 | [P] | [D] |
| T002 | Fixture helpers: assert-reads-primary / assert-status-from-coord dual-leg asserters | WP01 | [D] |
| T003 | Fixture smoke test (flat + coord topologies materialize correctly) | WP01 | [D] |
| T004 | Add inline-call-shape detection arm to the dir-read AST scanner | WP02 | | [D] |
| T005 | Widen scan scope to all of `src/specify_cli/` | WP02 | | [D] |
| T006 | Mandatory self-test: synthetic inline pre-fix snippet flagged; routed snippet not flagged | WP02 | | [D] |
| T007 | Pin the full surfaced residual set; cite #2185 / #2186 / #2167 on out-of-scope pins | WP02 | | [D] |
| T008 | Recount + record the dir-read baseline census after widening | WP02 | | [D] |
| T009 | Route `tasks status` tasks/ read to seam (mixed-read per-leg split) | WP03 | | [D] |
| T010 | Route `list_tasks` (inline-shape) + `_map_requirements_feature_dir` reads to seam | WP03 | | [D] |
| T011 | Route `finalize_tasks` dir-read leg to seam (keep bootstrap STATUS coord) | WP03 | | [D] |
| T012 | Route `build_dependency_graph` IN-LOOP caller in tasks.py (do NOT change its signature) | WP03 | | [D] |
| T013 | Remove the tasks.py `_DIR_READ_KNOWN_RESIDUALS` pins (same commit) | WP03 | | [D] |
| T014 | RED-first per-site tests for the tasks.py sites (both legs) on the coord fixture | WP03 | | [D] |
| T015 | Split `discovery.py::preview_claimable_wp` signature → `planning_dir` + `status_dir` | WP04 | | [D] |
| T016 | Route `_preview_claimable_wp_for_mission` to pass the split dirs | WP04 | | [D] |
| T017 | Route `_resolve_review_context` (lanes.json + tasks/) + `_find_first_for_review_wp` (inline) | WP04 | | [D] |
| T018 | Route the `review` tasks/ leg; KEEP review-cycle sub-artifacts coord (C-008); avoid `:539-617` legacy block | WP04 | | [D] |
| T019 | Remove the workflow.py/discovery.py pins (same commit) | WP04 | | [D] |
| T020 | RED-first per-site tests (both legs; selection_reason unchanged on flat) | WP04 | | [D] |
| T021 | Route `build_normalized_wp_index:666` + `resolve_workspace_for_wp`/`resolve_feature_worktree` (lanes.json) | WP05 | | [D] |
| T022 | Split the `resolve_active_wp_for_branch:470` mixed read per-leg | WP05 | | [D] |
| T023 | Route `context/resolver.py:163` (primary-anchor pattern) + `task_utils/support.py:309` | WP05 | | [D] |
| T024 | Remove the workspace/context pins (same commit) | WP05 | | [D] |
| T025 | RED-first per-site tests (both legs) on the coord fixture | WP05 | | [D] |
| T026 | Route `tasks_dependency_graph.py:118` IN-LOOP caller (no signature change) | WP06 | | [D] |
| T027 | Route `tasks_parsing_validation.py:935` research-artifact read | WP06 | | [D] |
| T028 | Split the `validate_tasks.py:113` mixed read per-leg | WP06 | | [D] |
| T029 | Remove the dep-graph cluster pins (same commit) | WP06 | | [D] |
| T030 | RED-first per-site tests (both legs) | WP06 | | [D] |
| T031 | Teach `is_def_use_canonical` the `_canonicalize_bare_modern_handle` fold seam | WP07 | | [D] |
| T032 | Auto-route the 4 hand-sanctioned entries; shrink permanent allowlist 7→3 | WP07 | | [D] |
| T033 | Recompute `ROUTED_CANONICALIZER_FLOOR` strictly below post-fix live census | WP07 | | [D] |
| T034 | Gate self-mutation test covering the new discriminator branch | WP07 | | [D] |
| T035 | Refresh `is_committed` docstring to the primary-surface read | WP08 | [D] |
| T036 | Add negative-assertion caller-contract regression pin (False on husk path) | WP08 | [D] |
| T037 | Remove dead symbol `FEATURE_CONTEXT_UNRESOLVED_CODE` (prove zero importers) | WP09 | [D] |

---

## Work Packages

### WP01 — Shared coord-topology test fixture [P]

- **Goal**: One un-stubbed fixture (real `meta.json` coord topology + status-only `-coord`
  husk with no `tasks/`/`lanes.json` + `tasks/WP*.md` and `lanes.json` on primary) plus
  dual-leg asserters, so every routing WP proves tasks-from-PRIMARY AND status-from-COORD.
- **Priority**: P0 (foundational — WP03–WP06 depend on it). **Independent test**: fixture
  smoke test materializes both topologies; reproduces the husk divergence without patching.
- **Requirements**: FR-014, NFR-003.
- **Subtasks**: T001, T002, T003.
- **Risks**: must NOT patch the topology-resolution stack (the `test_done_bookkeeping_seam.py:353`
  anti-pattern); must synthesize the post-#2106 shape (latent on existing repo missions).
- **Dependencies**: none.

### WP02 — Dir-read ratchet hardening + residual pinning

- **Goal**: Teach the scanner the inline-call shape, widen scope to all `src/specify_cli/`,
  add the mandatory self-test, and pin the full surfaced residual set (out-of-scope sites
  cite #2185 / #2186 / #2167). Establishes the ratchet the routing WPs then drain.
- **Priority**: P0 (foundational; starts the ratchet chain). **Independent test**: gate
  green post-widening with the full pin set; self-test flags the synthetic inline snippet.
- **Requirements**: FR-007, FR-008, FR-015 (pin citations), NFR-001.
- **Subtasks**: T004, T005, T006, T007, T008.
- **Risks**: gate-unmask-cannot-self-validate — the widening only bites post-merge
  (NFR-005); pin every surfaced site (no silent skip).
- **Dependencies**: none. **Owns** `tests/architectural/test_gate_read_literal_ban.py`.

### WP03 — Route tasks.py loop reads

- **Goal**: Route the `tasks/` reads in `tasks status`, `list_tasks`, `finalize_tasks`,
  `_map_requirements_feature_dir`, and the in-loop `build_dependency_graph` caller; split
  mixed reads per-leg; remove the tasks.py pins.
- **Priority**: P1. **Independent test**: `tasks status`/`tasks list` on the coord fixture
  read `tasks/` from primary; status events still from coord.
- **Requirements**: FR-001, FR-003, FR-006, FR-009.
- **Subtasks**: T009, T010, T011, T012, T013, T014.
- **Risks**: mixed-read per-leg (C-001); do NOT change `build_dependency_graph`'s signature
  (T012 routes at the caller only).
- **Dependencies**: WP01, WP02.

### WP04 — Route workflow.py + discovery.py (signature split)

- **Goal**: Split `discovery.py::preview_claimable_wp` into `planning_dir` + `status_dir`
  (the WP09-trap fix), route `_preview_claimable_wp_for_mission`, `_resolve_review_context`,
  `_find_first_for_review_wp`, and the `review` tasks/ leg; keep review-cycle sub-artifacts
  coord (C-008); remove the workflow/discovery pins.
- **Priority**: P1. **Independent test**: claimable preview + review auto-find on the coord
  fixture resolve primary; `selection_reason` unchanged on flat; review-cycle reads coord.
- **Requirements**: FR-002, FR-006, FR-009.
- **Subtasks**: T015, T016, T017, T018, T019, T020.
- **Risks**: the single-arg MIXED read is the exact WP09 trap — SPLIT the signature, don't
  swap; avoid the `workflow.py:539-617` legacy-fallback block and the `feedback://` paths.
- **Dependencies**: WP01, WP03 (ratchet chain).

### WP05 — Route workspace/context + context/resolver + task_utils

- **Goal**: Route `build_normalized_wp_index`, `resolve_workspace_for_wp`/
  `resolve_feature_worktree` (lanes.json), the `resolve_active_wp_for_branch` mixed read,
  `context/resolver.py:163`, and `task_utils/support.py:309`; remove the pins.
- **Priority**: P1. **Independent test**: workspace WP index + lane resolution on the coord
  fixture read primary; status legs coord.
- **Requirements**: FR-005, FR-006, FR-009.
- **Subtasks**: T021, T022, T023, T024, T025.
- **Risks**: do NOT consolidate the coord-aware twin `resolve_feature_dir_for_slug` (C-007);
  the `:714` not-found message path must still resolve; `context/resolver.py` should adopt
  the `implement.py:1018` primary-anchor pattern, not a bare swap.
- **Dependencies**: WP01, WP04 (ratchet chain).

### WP06 — Route dependency-graph / WP-frontmatter readers

- **Goal**: Route the in-loop `build_dependency_graph` caller in
  `tasks_dependency_graph.py`, the `tasks_parsing_validation.py:935` research-artifact read,
  and the `validate_tasks.py:113` mixed read; remove the pins.
- **Priority**: P1. **Independent test**: dependency-graph + ready-for-review validation on
  the coord fixture read primary.
- **Requirements**: FR-004, FR-006, FR-009.
- **Subtasks**: T026, T027, T028, T029, T030.
- **Risks**: route `build_dependency_graph` at the in-loop caller only (no signature change
  — protects out-of-loop callers `merge/ordering:95`, `policy/merge_gates:238`).
- **Dependencies**: WP01, WP05 (ratchet chain).

### WP07 — Resolution gate: #2183 fold + floor recompute

- **Goal**: Teach `is_def_use_canonical` the `_canonicalize_bare_modern_handle` fold seam so
  the 4 hand-sanctioned entries auto-route; shrink the permanent allowlist 7→3; recompute
  `ROUTED_CANONICALIZER_FLOOR` strictly below the post-fix live census; cover the new branch.
- **Priority**: P2. **Independent test**: resolution-authority gate green; allowlist=3;
  floor < live; shrink-only twin-guard passes.
- **Requirements**: FR-011, FR-012, NFR-001, C-005.
- **Subtasks**: T031, T032, T033, T034.
- **Risks**: the other 3 permanent sanctions are raw-param (not self-fold) — keep them;
  floor must be computed AFTER routing (depends on WP06).
- **Dependencies**: WP06 (final routed census). **Owns** `test_resolution_authority_gates.py`,
  `resolution_gate_allowlist.yaml`.

### WP08 — #2140 close (is_committed) [P]

- **Goal**: Refresh the stale coord-worktree docstring; add a negative-assertion
  caller-contract regression pin (False on a husk spec path lacking `spec.md`); close #2140.
- **Priority**: P2. **Independent test**: the regression test is RED against a hypothetical
  coord-resolved reversion, GREEN now.
- **Requirements**: FR-010, C-004.
- **Subtasks**: T035, T036.
- **Risks**: pin must assert the negative, not a tautology; no multi-leg OR.
- **Dependencies**: WP01 (fixture).

### WP09 — Dead-symbol removal [P]

- **Goal**: Remove `FEATURE_CONTEXT_UNRESOLVED_CODE` from `_read_path_resolver.py`
  behavior-preservingly (prove zero importers; the bare string error code is untouched).
- **Priority**: P3. **Independent test**: grep proves no `import FEATURE_CONTEXT_UNRESOLVED_CODE`;
  suite green.
- **Requirements**: FR-013, C-005.
- **Subtasks**: T037.
- **Dependencies**: none.

---

## Close-out obligations (mission-level, not a WP)

- **NFR-005** — after `spec-kitty merge` (local), BEFORE `gh pr create`, on the **merged**
  branch, run the two architectural gates `-v` and paste the **verbatim** output into the
  PR body (the scan widening + floor raises only self-validate post-merge).
- **Lane-chain merge forecast (post-tasks squad, alphonso)** — `lanes.json` placed WP03–WP06
  in separate lanes (a/c/d/e/f), not one lane. They edit the same `_DIR_READ_KNOWN_RESIDUALS`
  literal as cross-lane out-of-map pin removals. Before merging the chain, run
  `spec-kitty merge --dry-run` and inspect the conflict forecast on
  `tests/architectural/test_gate_read_literal_ban.py` (removed pin blocks are disjoint so it
  should be clean; #1684 dep-tip propagation carries each prior lane's removals). If it
  conflicts, resolve in pin-removal order WP03→WP04→WP05→WP06.
- **NFR-004** — run `tests/architectural/`, `tests/integration/`, `tests/git/` + the
  terminology guard locally before PR.
- **FR-015** — confirm the #2185 / #2186 pins cite their issues; #2167 cites the scripts/tasks pins.
- Issue-matrix terminal verdicts for #2115 / #2140 / #2183.

## Dependencies (summary)

```
WP01 ─┬─> WP03 ─> WP04 ─> WP05 ─> WP06 ─> WP07
WP02 ─┘   (ratchet chain: each removes its own pins from WP02's file)
WP08 [P]   WP09 [P]
```
