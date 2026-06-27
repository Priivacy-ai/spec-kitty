# Specification: Implement-Loop Coord-Authority Completion

**Mission slug**: `implement-loop-coord-authority-completion-01KW2E7A`
**Mission type**: software-dev
**Target branch**: `design/coord-authority-remediation-2160`
**Status**: Draft (revised post-spec adversarial squad; awaiting plan)

## Purpose

Close the remaining live children of the #2160 coord-topology artifact-authority
epic so the implement/review/merge loop agrees with the writers on a single
canonical authority path for work-package artifacts — and harden the
architectural gate so the residual census it reports is actually complete.

Since #2106 (write-surface coherence) moved planning artifacts — including
`spec.md` and the per-WP `tasks/` directory — to the **primary** surface for
*all* topologies, the implement/review/merge loop still resolves the work-package
task directory through **coordination-aware** resolvers. For a coordination-topology
mission that lands on the empty `-coord` husk (which now carries only status
events), so `tasks status`/`list_tasks`, `implement`, `review`, `finalize_tasks`,
the for-review WP auto-finder, the workspace WP index, and the post-merge
`_mark_wp_merged_done` read the wrong location. This is the same split-brain class
that #2154/#2155 closed for the write/commit legs in Phase 1 (PR #2181); this
mission closes it for the implement-loop **read** legs.

This mission **CLAIMS** and drives to terminal: **#2115** (implement-loop
task-read residual cluster), **#2140** (verify/close the already-remediated
`is_committed` spec-read), and **#2183** (resolution-gate discriminator hygiene
fold). It is the follow-on the dir-read ratchet already names as the
"#1716 implement-loop write-surface mission."

## Background and current state (verified — operator + post-spec squad)

- **Canonical seam exists.** `resolve_planning_read_dir(repo_root, slug, kind=...)`
  (`src/specify_cli/missions/_read_path_resolver.py`) is the kind-aware split:
  PRIMARY-partition kinds (incl. `SPEC`, `WORK_PACKAGE_TASK`) resolve to the
  primary surface for all topologies; STATUS-partition kinds (`STATUS_STATE`,
  `ISSUE_MATRIX`, `ACCEPTANCE_MATRIX`, `ANALYSIS_REPORT`) stay coordination-aware.
  The gate/verify commands already route through it; the implement/review/merge
  loop does **not**.
- **The "7 residuals" census was incomplete (squad + fan-out-verified undersizing).**
  The dir-read ratchet's AST scanner matches only the two-hop form
  `d = resolver(...); d / "tasks"`; it is **structurally blind** to the inline form
  `resolver(...) / "tasks"`. A fan-out FR-008 sweep over all 111 coord-aware call
  sites in `src/specify_cli/` (see research.md) found the true in-loop ROUTE surface
  is ~20 functions across four clusters, ~3× the named six. **`lanes.json` is
  PRIMARY-partition (LANE_STATE)** — a `lanes.json` read off a coord-aware resolver
  is the same coord-topology bug class as a `tasks/` read.
- **Scope boundary (operator decision 2026-06-26 — split).** This mission owns the
  **implement/review-loop read surface**: `cli/commands/agent/` (tasks.py,
  workflow.py), `workspace/context.py` + `context/resolver.py` + `task_utils/`, the
  dependency-graph / WP-frontmatter readers, and the gate hardening. The
  **`merge/` + `lanes/` + `core/worktree_topology` `lanes.json` cluster** (~7
  functions, incl. the `merge/done_bookkeeping.py` tasks read) is split into a
  **sibling mission under #2160** — this mission *pins* those residuals (with the
  sibling ticket ref), it does not route them. **`meta.json` identity reads** off
  coord (e.g. `next_cmd.py`) are a distinct identity-read class (mostly guarded by
  the `implement.py:1018` primary-anchor fallback; coord husk has no `meta.json`,
  authoritative comment `implement.py:1020-1028`) → **separate identity-read ticket**,
  out of scope here.
- **Gate blind spot, two-fold.** The dir-read scan walks only `cli/commands/` (+
  `acceptance/`), so residuals outside it (e.g. the merge/lanes cluster) are invisible;
  and the inline-call shape is invisible everywhere. Both architectural gates pass
  green over both blind spots. Hardening the scanner (inline-shape aware, whole-`src`
  scope) is therefore in-scope here so the ratchet can pin/triage the full set.
- **#2140 already remediated by #2106 (squad CONFIRMED-UNREACHABLE).** `is_committed`
  (`src/specify_cli/missions/_substantive.py`) is single-surface; its only
  production caller (`mission_setup_plan.py:361`, via
  `_planning_read_dir(artifact_type="spec")`) feeds a primary-resolved spec. No
  live false-negative is constructible. Residual debt is only a stale docstring
  and a missing caller-contract regression pin.
- **#2183 mechanically scoped + floor math is stale.** `ROUTED_CANONICALIZER_FLOOR
  = 27` while the in-code comment records the live routed count as **31** (guarded
  by a strict-inequality). Routing the #2115 residuals and adopting the
  `_canonicalize_bare_modern_handle` fold both raise the live count past 35 — so
  the floor must be **computed from the post-fix live census and set strictly
  below it**, never hardcoded to 31.

## User Scenarios & Testing

### Primary scenario — coordination-topology status/list read
1. An agent runs `spec-kitty agent tasks status` (or `tasks list`) for a
   coordination-topology mission whose planning artifacts live on the primary
   surface (post-#2106).
2. **Today:** the work-package `tasks/` directory resolves through a
   coordination-aware resolver, lands on the `-coord` husk (status events only,
   no `tasks/`), and hard-fails "Tasks directory not found".
3. **After:** `tasks/` resolves via the seam (`kind=WORK_PACKAGE_TASK`) to the
   primary surface; status events continue to resolve coordination-aware; the
   command reports correct work-package status.

### Scenario — implement / review / claimable-preview / for-review auto-find
1. An agent runs `implement WP##`, `review` (with or without a WP arg), or a
   claimable-WP preview against a coordination-topology mission.
2. **Today:** the work-package task reads (including `_find_first_for_review_wp`
   and the workspace WP index) resolve the husk → degraded/`None`/"WP not found".
3. **After:** WP-task reads resolve primary; review-cycle sub-artifacts stay
   coordination-aware (matched read/write pair — see C-008).

### Scenario — gate hardening pins the merge-path residual (handed to the sibling)
1. The hardened scanner (inline-shape aware, whole-`src` scope) now sees
   `merge/done_bookkeeping.py::_mark_wp_merged_done` and the `merge/`+`lanes/`
   `lanes.json` reads.
2. **This mission:** pins them in `_DIR_READ_KNOWN_RESIDUALS` with the sibling-mission
   ticket reference (FR-008/FR-015) — the ratchet now *sees* them where it was blind
   before. The sibling mission routes them and removes the pins.

### Scenario — is_committed contract (regression close of #2140)
1. `setup_plan` checks whether the spec is committed for a coordination-topology
   mission.
2. **Today (already correct):** the spec read resolves primary; `is_committed`
   reports correctly.
3. **After:** a regression test pins the contract with a **negative** assertion
   (`is_committed` returns False for a husk spec path with no `spec.md`), so a
   reversion to a coord-resolved read is caught; the docstring matches reality.

### Edge cases
- Coordination branch declared in `meta.json` but deleted from git → the existing
  structured hard-fail (#1848) is preserved on the coordination-aware status leg;
  routing the tasks leg to PRIMARY must not bypass it (no silent stale-primary
  fallback).
- Flat / single-branch topology → reads already resolve primary; unchanged
  (regression-guarded).
- A **mixed-read** site (one `feature_dir` feeding both a `tasks/` read and a
  status-events read) must be split per-leg; a one-line `feature_dir` swap to
  PRIMARY would break the status read (hidden #2155 re-opener).

### Testability
Each routed call site gets RED-first per-site coverage attached at the
pre-existing entry point, backed by one shared fixture: a coordination-topology
mission with a real `meta.json` (`coordination_branch` set), a status-only `-coord`
husk (no `tasks/`), and the `tasks/WP*.md` files on the primary surface. The
fixture **MUST NOT patch any function in the topology-resolution stack** — it
exercises the live resolvers end-to-end (the resolver-stubbing anti-pattern at
`tests/.../test_done_bookkeeping_seam.py:353` is explicitly forbidden). Each
per-site test asserts **both** legs: tasks-from-primary AND status-from-coord.

## Domain Language

| Canonical term | Meaning | Avoid |
|----------------|---------|-------|
| Authority path | The single physical location all writers, validators, committers agree is canonical for an artifact kind | "the right dir" |
| Kind-aware seam | `resolve_planning_read_dir(kind=...)` — routes PRIMARY kinds to primary, STATUS kinds to coord | — |
| PRIMARY-partition | Kinds (incl. `WORK_PACKAGE_TASK`, `SPEC`) resolving to primary for all topologies | — |
| STATUS-partition | Kinds (status events/state, matrices) remaining coordination-aware | — |
| Coord husk | The post-#2106 coordination worktree carrying only status events, no planning artifacts | "coord dir" |
| Mixed-read site | A call site deriving BOTH a PRIMARY-kind read and a STATUS-kind read from one `feature_dir` | — |
| Inline-call shape | `resolver(...) / "name"` (one expression) — the AST shape the scanner was blind to | — |
| Residual | A call site reading a PRIMARY-kind artifact off a coordination-aware resolver | — |
| Fold seam | A canonicalizer helper (`_canonicalize_primary_read_handle`, `_canonicalize_bare_modern_handle`) treated as canonical by the resolution gate | — |

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `tasks status` and `list_tasks` (`cli/commands/agent/tasks.py`) resolve the work-package `tasks/` directory via `resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`; the status-events read remains coordination-aware (mixed-read split, not a one-line `feature_dir` swap). | Proposed |
| FR-002 | `implement`, `review`, `_resolve_review_context`, `_preview_claimable_wp_for_mission`, and `_find_first_for_review_wp` (`cli/commands/agent/workflow.py`, incl. inline-shape reads at 2110/2116/2121/2124) route their WP-task reads through the seam. `_preview_claimable_wp_for_mission`/`discovery.py` is split so PRIMARY and STATUS partitions are derived separately (signature change permitted). | Proposed |
| FR-003 | The `finalize_tasks` dir-read leg (`cli/commands/agent/tasks.py:2276`) resolves through the seam; its STATUS-partition reads (bootstrap) remain coordination-aware. | Proposed |
| FR-004 | The dependency-graph / WP-frontmatter readers route their PRIMARY-kind reads through the seam: `tasks_dependency_graph.py:118` (`build_dependency_graph`), `tasks_parsing_validation.py:935` (research-artifact read), `context/resolver.py:163` (MissionContext WP-frontmatter), and the WP-frontmatter leg of `validate_tasks.py:113`. | Proposed |
| FR-005 | The `workspace/context.py` work-package cluster routes its PRIMARY-kind reads through the seam — `build_normalized_wp_index:666` (`tasks/`), `resolve_workspace_for_wp`/`resolve_feature_worktree` (`:752/:790/:853`, `lanes.json` = LANE_STATE), the `:470` WP-frontmatter leg, and `task_utils/support.py:309` (`locate_work_package`). STATUS-partition legs remain coordination-aware. The coord-aware twin resolver `resolve_feature_dir_for_slug` is not consolidated (C-007); only its PRIMARY-kind call sites are re-pointed. | Proposed |
| FR-006 | STATUS-partition reads (status events/state, issue/acceptance matrices, analysis report) continue to resolve coordination-aware, unchanged across all touched sites. | Proposed |
| FR-007 | The dir-read literal-ban ratchet scanner is hardened to flag the inline-call shape `resolver(...) / "<dir|.md>"` whose callee is a topology-routed resolver, and its scan scope is widened to **all of `src/specify_cli/`** (not just `cli/commands/`). A mandatory self-test asserts a synthetic pre-fix snippet (coord-aware resolver + inline `/ "tasks"`) is flagged. | Proposed |
| FR-008 | The whole-`src` scan surfaces the full residual set (see research.md FR-008 sweep); each surfaced site is either **routed** (this mission's loop surface), or **pinned** in `_DIR_READ_KNOWN_RESIDUALS` with a tracking-issue reference — **no silent skip**. The out-of-scope clusters are pinned to their owning tickets: the `merge/`+`lanes/`+`core/worktree_topology` `lanes.json` cluster → **#2185**; the `meta.json` identity-read class (`next_cmd.py` et al.) → **#2186**; the `scripts/tasks/tasks_cli.py` legacy-reader sites → **#2167**; other out-of-loop reads (`agent_utils/status.py:120`, `widen/state.py:63`, `manifest.py`, `doctrine_synthesizer`, `dossier`, `verify_enhanced`, `_identity_audit`) → their own pins/tickets. | Proposed |
| FR-009 | As each residual is routed, its `_DIR_READ_KNOWN_RESIDUALS` entry is removed **in the same commit** that re-points the call site (per-site RED-first test proves the link); the corresponding coord-authority sanctions in `resolution_gate_allowlist.yaml` shrink accordingly. Removing a pin without routing is a violation. | Proposed |
| FR-010 | The `is_committed` docstring (`_substantive.py`) is refreshed to describe the primary-surface read, and a caller→`is_committed` contract regression test pins the behavior with a **negative** assertion (returns False for a coord-husk spec path lacking `spec.md`) — closing #2140. The test must not mandate a multi-leg OR (C-004). | Proposed |
| FR-011 | `is_def_use_canonical` (`tests/architectural/test_resolution_authority_gates.py`) recognizes the `_canonicalize_bare_modern_handle` fold seam; the four hand-sanctioned allowlist entries (`resolve_handle_to_read_path:950/972/1023`, `_stored_topology_best_effort:1208`) become auto-routed and the permanent allowlist shrinks from 7 to 3 — closing #2183. | Proposed |
| FR-012 | `ROUTED_CANONICALIZER_FLOOR` (and any coord-authority/canonicalizer baseline) is recomputed from the **post-fix live routed census** and set strictly below it; it is not hardcoded to 31. The shrink-only twin-guard passes. | Proposed |
| FR-013 | The dead symbol `FEATURE_CONTEXT_UNRESOLVED_CODE` (`_read_path_resolver.py`) is removed behavior-preservingly (not exported, not imported by any source). | Proposed |
| FR-014 | A shared coordination-topology test fixture (real `meta.json` coord topology + status-only husk + `tasks/WP*.md` on primary, **no patching of the topology-resolution stack**) backs RED-first per-site coverage proving each routed site reads WP files from primary AND its status read from coord. | Proposed |
| FR-015 | The two split-out tracking issues are filed under #2160 and each cited in its matching `_DIR_READ_KNOWN_RESIDUALS` pin: **#2185** (sibling mission — `merge/`+`lanes/`+`core/worktree_topology` `lanes.json` cluster incl. `done_bookkeeping.py:237`) and **#2186** (identity-read-routing — `meta.json` reads off coord incl. the unguarded `next_cmd.py:187/253/631` telemetry drop). *(Issues filed 2026-06-26; remaining obligation is the pin citation during implementation.)* | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Architectural-gate floors move monotonically tighter only; `ROUTED_CANONICALIZER_FLOOR` is set to the post-fix live census minus a documented margin (strictly below live); the shrink-only twin-guard passes. | Floors never loosen; twin-guard green | Proposed |
| NFR-002 | New and touched code passes `ruff` and `mypy` with zero issues/warnings; cyclomatic complexity ≤ 15 per function (no new `# noqa` / `# type: ignore`). | 0 findings; complexity ≤ 15 | Proposed |
| NFR-003 | Every new branch/helper added or refactored has direct, focused tests in the same work package. | New-code coverage gate passes | Proposed |
| NFR-004 | The CI-only shards (`tests/architectural/`, `tests/integration/`, `tests/git/`) plus the terminology guard pass locally before the mission PR is opened. | All named shards green locally | Proposed |
| NFR-005 | A pre-merge full-gate dry-run is executed **on the merged local branch** (after `spec-kitty merge`, before `gh pr create`) to validate the widened scan, the inline-shape detection, and the recomputed floors; the **verbatim** gate output is pasted into the PR body (gate-unmask-cannot-self-validate). | Verbatim output in PR body, merged-branch run | Proposed |
| NFR-006 | No behavioral change to STATUS-partition reads — demonstrated by the existing status/matrix test suites remaining green without modification. | Status tests unchanged + green | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | STATUS-partition reads stay coordination-aware; do not force-all-primary (re-opens #2155 and the #1718/#1848 transients). Every mixed-read site is split per-leg, never swapped wholesale. | Active |
| C-002 | No silent fallback on an ambiguous or coordination-deleted handle — the existing structured-error / hard-fail path (#1848) is preserved; routing the tasks leg must not introduce a silent stale-primary fallback. | Active |
| C-003 | `primary_feature_dir_for_mission` stays handle-blind; canonicalization happens at the caller via the seam, never inside the primary resolver. | Active |
| C-004 | `is_committed` remains a single-surface check; the regression pin must not mandate a multi-leg OR over coord+primary surfaces. | Active |
| C-005 | The #2183 discriminator change and the dead-symbol removal are strictly behavior-preserving. | Active |
| C-006 | Reference-only issues (#2160, #2017, #1716, #1878, #2173, #1619) must not be claimed or closed; only #2115, #2140, #2183 are claimed. | Active |
| C-007 | The `candidate_feature_dir_for_mission` / `resolve_feature_dir_for_slug` near-duplicate **resolver consolidation** stays out of scope (needs a behavioral-envelope study); this mission re-points PRIMARY-kind call sites that use them, but does not merge the resolvers. | Active |
| C-008 | Review-cycle sub-artifacts (`baseline-tests.json`, rejected-review-cycle, arbiter, baseline — `workflow.py:2614/2647`, `review/cycle.py`, `review/arbiter.py`, `review/baseline.py`) keep their reads coordination-aware so they stay a matched read/write pair; only the WORK_PACKAGE_TASK (WP*.md definition) reads route to primary. Routing review-cycle reads without co-moving their writers would manufacture a new split-brain. | Active |
| C-009 | The `merge/`+`lanes/`+`core/worktree_topology` `lanes.json` cluster (#2185) and the `meta.json` identity-read class (#2186) are OUT of this mission. This mission only *pins* them in the ratchet; it must not route them — and must not touch `merge/`, `lanes/`, or `core/worktree_topology` source. | Active |

## Success Criteria

- **SC-001**: A coordination-topology mission finalized after #2106 returns correct
  results from every **implement/review-loop** read surface owned by this mission —
  `tasks status`, `tasks list`, `implement`, `review` (with and without a WP arg),
  claimable preview, workspace WP index, dependency-graph — with zero "Tasks
  directory not found" / "WP not found" failures. (The merge-path `done` transition
  is the sibling mission's SC.)
- **SC-002**: After the scanner is hardened (inline-shape aware, whole-`src` scope),
  `_DIR_READ_KNOWN_RESIDUALS` contains only explicitly-ticketed out-of-loop
  residuals (zero in-loop residuals), and the self-test proves the scanner catches
  the inline shape.
- **SC-003**: The resolution-gate permanent allowlist shrinks from 7 hand-sanctioned
  entries to 3; the routed-canonicalizer floor equals the post-fix live census
  minus the documented margin; the shrink-only twin-guard passes.
- **SC-004**: Issues #2115, #2140, and #2183 are closed with terminal issue-matrix
  verdicts; the reference-only epics remain open.
- **SC-005**: Every routed call site is covered by a per-site test proven red against
  pre-fix code (pre-fix failure mode documented inline; PR body shows the RED run)
  and green after; the full architectural/integration/git shards pass locally and
  on CI.

## Key Entities

- **`resolve_planning_read_dir(repo_root, slug, kind)`** — the kind-aware authority
  seam; the single routing chokepoint all PRIMARY-kind reads adopt.
- **dir-read ratchet scanner** (`tests/architectural/test_gate_read_literal_ban.py`)
  — hardened for inline-call shape + whole-`src` scope + self-test.
- **`_DIR_READ_KNOWN_RESIDUALS`** — drains to in-loop-empty as the mission lands.
- **`resolution_gate_allowlist.yaml`** + **`is_def_use_canonical`** — the resolution
  authority gate; learns the second fold seam (#2183).
- **Coordination-topology fixture** — shared, un-stubbed test asset (status-only
  husk + primary `tasks/`) backing RED-first per-site coverage.

## Assumptions

- The squad-verified finding that #2140 has no constructible live false-negative
  holds; #2140 work is verification + negative-assertion regression-pin +
  docstring. If planning discovers a live false-negative, escalate scope.
- The defect is latent on this repository today (existing coord missions predate
  #2106 and still carry `tasks/`; post-#2106 missions are flattened) — the fixture
  must synthesize the post-#2106 coord-topology shape to reproduce it.
- Widening the scan to all of `src/specify_cli/` will surface residuals beyond the
  loop; FR-008 mandates triaging them (route or ticket-and-pin), so the final
  residual inventory is discovered at plan time, not pre-known. Lane boundaries
  must absorb this discovery step.
- The gate hardening (inline-shape detection, whole-`src` scope) and floor raises
  take effect only after the mission merges; they cannot self-validate within the
  mission's own diff (hence NFR-005's merged-branch verbatim dry-run).

## Out of Scope

- STATUS-partition read routing (correct on coordination today).
- Write-arm / target-branch / finalize **write** resolvers (already primary-pinned)
  and review-cycle sub-artifact reads/writes (C-008 keeps them coord-matched).
- The `candidate_feature_dir_for_mission` / `resolve_feature_dir_for_slug` resolver
  **consolidation** (C-007 — separate behavioral-envelope study).
- The **`merge/`+`lanes/`+`core/worktree_topology` `lanes.json` cluster** (~7 fns incl.
  `done_bookkeeping.py:237`) → **sibling mission #2185** (under #2160); pinned here,
  not routed. This mission must not edit `merge/`, `lanes/`, or `core/worktree_topology`.
- The **`meta.json` identity-read class** off coord (`next_cmd.py` et al.) → **#2186**;
  pinned here, not routed.
- `_read_path_resolver` topology-classification internals.
- #1622 (`coordination.status_service` dead-symbol module debt), #1623 (`doctor.py`
  split).
- Any facet of the #2017 guard-friction umbrella beyond what resolves as a
  side-effect of routing the residuals.
- Routing any whole-`src` residual that is NOT an implement-loop / PRIMARY-kind
  read — those are pinned-and-ticketed (FR-008), not fixed here.
