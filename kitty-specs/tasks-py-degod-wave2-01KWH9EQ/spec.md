# Mission Specification: Tasks Degod Wave 2: Render Seam + Relocation

**Mission Branch**: `degod-follow-ups` (mission `tasks-py-degod-wave2-01KWH9EQ`, coord branch `kitty/mission-tasks-py-degod-wave2-01KWH9EQ`)
**Created**: 2026-07-02
**Status**: Draft (post-spec squad findings folded 2026-07-02)
**Input**: Issue #2305 handover debrief (Wave 2 of the tasks.py degod program, parent epic #2173) + live re-census against merged upstream/main `381db8d5f`, plus domain-matched boyscouting from #2034. A 4-lens post-spec adversarial squad (sizing / fakeability / code-truth / structure) corrected the census and hardened the DoDs; see `post-spec-squad-findings.md`.

## Context

Wave 1 (mission `tasks-py-degod-01KWF08S`, PR #2303, merged as `381db8d5f`) decomposed the
`agent tasks` god-command's decision logic into pure tested cores behind injected ports and
thinned every fat command body — behavior byte-identical, guarded by the CLI contract
harnesses. It **deliberately deferred** two goals to this mission (spec Deferred section):
the Render-seam unification and the whole-file shim relocation with its LOC ceiling.
During Wave 1, `tasks.py` grew to **4569 LOC**: decision logic left for the cores while
the orchestrators, glue helpers, and port-seam adapter classes accumulated in the file.

**Re-census facts (merged main, 2026-07-02, squad-verified) — supersede all debrief line
references and the pre-squad draft of this spec:**

- `src/specify_cli/cli/commands/agent/tasks.py` = 4569 LOC, 112 top-level defs.
- **JSON emission sites: 13 total distinct call sites** — 12 compact
  `print(json.dumps(...))` sites (lines 508, 546, 559, 2477, 2805, 3349–3350
  (one multiline call), 3474, 3488, 3585, 3665, 3863, 4557) **plus** one
  `return json.dumps(payload, indent=2)` status leg at line 1235. No aliased
  `from json import dumps` forms exist today.
- **Symbol taxonomy** (the honest relocation inventory):
  - 5 `_do_<cmd>` orchestrators: `_do_move_task` (2082), `_do_mark_status` (2641),
    `_do_finalize_tasks` (3122), `_do_map_requirements` (3677), `_do_status` (4431).
  - **61 family glue helpers across FIVE families**: 23 `_mt_*`, 11 `_mr_*`, 14 `_st_*`,
    9 `_ms_*`, and 4 `_ft_*` (finalize — `_ft_resolve_context`/`_ft_validate`/
    `_ft_apply_writes`/`_ft_output`).
  - 5 per-family State dataclasses: `_MoveTaskState` (1249), `_MarkStatusState` (2325),
    `_FinalizeState` (2924), `_MapReqState` (3188), `_StatusState` (3893).
  - 5 per-family port factories: `_default_move_task_ports`, `_default_map_requirements_ports`,
    `_default_status_ports`, `_default_mark_status_ports`, `_default_finalize_ports`.
  - 4 port-seam adapter classes: `_MoveTaskCoordRouter` (1120), `_MapReqCoordRouter` (1172),
    `_StatusRender` (1222), `_MarkStatusCoordRouter` (2356).
  - **~30 genuinely cross-family shared helpers** with no home in a per-family split —
    e.g. `_output_result`/`_output_error` (56 in-file call sites), `_find_mission_slug`
    (10 sites, patched 66× in tests), `_ensure_target_branch_checked_out` (10 sites,
    patched 50×), `_coord_topology_active`, `_skip_target_branch_commit`,
    `resolve_primary_branch`, `_validate_ready_for_review` (patched 12×),
    `_check_unchecked_subtasks` (patched 12×).
- **Contract harnesses (the parity guard is TWO files, 43 cases combined):**
  - `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py` — 27 cases: 10
    `--help` fixtures asserted **byte-exact**; the JSON legs are **shape-checked**
    (`_shape()` collapses values/ordering), NOT byte-checked.
  - `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py` — 16 cases,
    including **T004/T005: the #2300 skip-vs-refuse divergence pins** (move_task coord
    skip-exit-0 arm with wrong-leg detector; mark_status/map_requirements refuse-exit-1
    arm), and the **branch-coverage ratchet** `_BRANCH_COVERAGE_FLOORS`
    (move_task 65% / status 48% / map_requirements 46%) whose
    `_mutating_function_line_ranges()` walks `tasks.py`'s AST **by function name** —
    it is line-range-coupled to the fat wrappers living in `tasks.py`.
- Ports content lives in `src/specify_cli/agent_tasks_ports.py` (381 LOC — top-level
  placement is deliberate and docstring-recorded: non-CLI consumers import without
  loading the agent Typer package); `src/specify_cli/cli/commands/agent/tasks_ports.py`
  is a 7-line re-export shim.
- Pure cores (all at `src/specify_cli/cli/commands/agent/`): `tasks_transition_core.py`
  (573), `tasks_status_view.py` (233), `tasks_mapping_core.py` (156).
- **Patch-seam surface**: ~370 `patch("...agent.tasks.<sym>")` call sites across ~40
  distinct symbols (367 by grep), plus 37 `monkeypatch.setattr` targeting tasks and
  121 `from ...agent.tasks import` statements in tests. Highest-traffic symbols:
  `locate_project_root` ×67, `_find_mission_slug` ×66, `_ensure_target_branch_checked_out`
  ×50, `get_mission_type` ×26, `feature_status_lock` ×23, `get_main_repo_root` ×19.
  Orchestrators call these by **bare name** today — a module-level re-export alone does
  NOT preserve patch interception after relocation (see FR-002/Domain Language "seam
  bridge").
- The `mission.py` degod template solved the seam-bridge problem with **lazy
  parent-module attribute routing** (`from ...agent import mission as _mission` inside
  functions; all infra calls go through `_mission.<attr>` — 40+ occurrences across its
  sibling modules, no module-level back-import, no cycle). Its final shim registers
  command callables via `app.command(name=...)(fn)`; siblings declare no `__all__` and
  pass the dead-symbol gate.
- A self-review-fallback precedence guard (`_self_review_fallback_option_error`) exists
  (imported at 150, called at 1367 inside `_mt_resolve_targets`).
- #2034 residual: no `ci-quality.yml` gate selects `-m unit` or `-m contract`; 257 of
  26,612 collected tests are selected by no marker gate repo-wide. The tasks domain is
  already near-clean: all 39 tasks-domain test files carry `pytestmark`; ~1 file is
  gate-invisible (`[unit, git_repo]` without `fast`). The pre-existing orphan ratchet
  `tests/architectural/test_gate_coverage.py` freezes ~9.8k orphans in
  `_gate_coverage_baseline.json` (refreshable via `--update-baseline` — a widening risk
  FR-009 must close for this domain).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - tasks.py becomes a true registration shim (Priority: P1)

A maintainer opening `src/specify_cli/cli/commands/agent/tasks.py` finds only thin
`@app.command` registration wrappers (plus the four already-small bodies and the
deliberate seam-bridge/re-export surface). The five command families' orchestrators,
glue helpers, State dataclasses, and port factories live in focused sibling modules; the
cross-family shared helpers live in a named shared module; the port-seam adapter classes
live in a dedicated adapters module. Navigating, reviewing, and changing one command no
longer requires scrolling a 4569-line file, and the whole-file size is enforced by an
architectural gate so the god-file cannot silently regrow.

**Why this priority**: This is the mission's charter — the whole-file shim-relocation
goal deferred from Wave 1. The file's size is the remaining structural debt; the per-move
risk is low but the volume (~3150 LOC) demands its own reviewed mission.

**Independent Test**: After relocation, both contract harnesses (43 cases) pass
unmodified, the byte-freeze suite (see US2) is green, the full tasks-domain test surface
passes with patch interception preserved, and the whole-file LOC gate passes at the
recorded ceiling; a synthetic violation (a dummy function pushing the file over the
ceiling) turns the gate red.

**Acceptance Scenarios**:

1. **Given** merged main `381db8d5f` behavior pinned by the two contract harnesses and
   the byte-freeze suite, **When** all five command families, the shared helpers, and
   the adapter classes are relocated to sibling modules, **Then** all 43 harness cases
   and every byte-freeze case pass unmodified, and the ~370 patch-seam call sites still
   **intercept** the production call path (not merely resolve).
2. **Given** the relocated layout, **When** the architectural LOC gate runs, **Then**
   `tasks.py` is at or under the recorded ceiling, the ceiling is `min(achieved, 1400)`,
   and the rationale records the delta from the 4569 baseline.
3. **Given** a future change re-adding orchestration bulk to `tasks.py`, **When** CI
   runs, **Then** the LOC gate fails (proven non-vacuous by a self-mutation test).
4. **Given** each relocation WP, **When** an orchestrator moves out of `tasks.py`,
   **Then** the branch-coverage ratchet in the coord harness is **re-pointed to the
   relocated function in the same WP** — never deleted, never floor-lowered.

---

### User Story 2 - One rendering authority for command output (Priority: P2)

A maintainer changing how an `agent tasks` subcommand emits JSON touches exactly one
seam: the Render port. No inline `json.dumps` remains in the tasks command surface; the
single `indent=2` status leg is served by the same parameterized seam (the
`_StatusRender` subclass override collapses). An AST-based gate keeps the count at zero
across the whole command-surface directory, including aliased and rebound forms.

**Why this priority**: This is the render-seam unification deferred from Wave 1 — the
remaining split-brain between the Render port and 13 ad-hoc emission sites. Smaller than
Stream B but it closes a rival-seam class (#2173 discipline: one production adapter per
port).

**Independent Test**: The byte-freeze suite (one byte-exact case per emission site,
frozen BEFORE any routing change) stays green through the seam unification; an AST census
shows 0 inline `json.dumps` in the command surface; the AST gate goes red on each
synthetically inserted evasion form.

**Acceptance Scenarios**:

1. **Given** byte-freeze characterization tests capturing the exact current bytes of all
   13 emission sites (12 compact + the `indent=2` leg) committed and green BEFORE any
   routing change, **When** the 12 compact sites are routed through
   `Render.json_envelope`, **Then** every byte-freeze case still passes (compact
   separators preserved).
2. **Given** the `indent=2` status leg (line 1235), **When** the Render seam gains a
   parameterized indent (or an indented-envelope capability), **Then** the status
   byte-freeze case still passes and the `_StatusRender(RealRender)` override is deleted.
3. **Given** a new code path emitting JSON via `json.dumps(...)`, `from json import
   dumps`, `import json as <alias>; <alias>.dumps(...)`, or a rebound local
   (`d = json.dumps; d(...)`), **When** the AST gate runs, **Then** it fails with an
   actionable message naming the offending site — each form has its own self-mutation
   proof.

---

### User Story 3 - Tasks-domain tests are CI-visible (boyscout, Priority: P3)

A contributor adding a test to the tasks domain cannot author it into CI-invisibility:
every file matching the committed tasks-domain glob carries CI-selected markers, the
orphan-ratchet baseline cannot re-absorb them, and the upstream marker-gap issue (#2034)
is refreshed with the 2026-07-02 re-census so the repo-wide fix can be planned on current
facts.

**Why this priority**: Domain-matched campsite cleaning (charter standing order 2). The
mission adds new test files and gates; authoring them into an invisible marker class
would be self-defeating. The squad found the domain near-clean already (~1 invisible
file), so this is honestly small. The repo-wide structural CI fix stays out of scope.

**Independent Test**: A committed marker-census artifact lists every file matching the
tasks-domain glob with the CI gate that selects it (zero unselected); the orphan-ratchet
baseline contains no entry under the glob; #2034 carries the refreshed census comment.

**Acceptance Scenarios**:

1. **Given** the committed tasks-domain glob (see FR-009), **When** the marker census
   runs, **Then** every matching test file (existing + added by this mission) is selected
   by at least one CI gate, evidenced by a committed census artifact.
2. **Given** the orphan ratchet `_gate_coverage_baseline.json`, **When** the mission's
   test files land, **Then** no path under the tasks-domain glob is added to the
   baseline (absorbing them via `--update-baseline` is a violation, not a fix).
3. **Given** the 2026-07-02 re-census, **When** the mission reaches review, **Then**
   #2034 has a comment with the refreshed facts and recommended structural options.

---

### Edge Cases

- **Patch interception loss (the dominant relocation hazard)**: a relocated orchestrator
  calling infra by bare name resolves in the SIBLING's namespace — `@patch("...agent.tasks.<sym>")`
  no longer intercepts even though a re-export keeps the name importable; defensively-patched
  tests (no `assert_called`) then pass green while real side effects fire. The seam bridge
  (FR-002) exists precisely for this; "the tests pass" is not sufficient evidence.
- **Branch-coverage ratchet false-red**: the coord harness ratchet resolves
  `move_task`/`status`/`map_requirements` line ranges from `tasks.py`'s AST by name;
  thinning those wrappers collapses the measured range → red on a correct move. The
  remedy is re-pointing the ratchet target in the same WP (FR-012) — deleting or
  floor-lowering it is forbidden.
- **Import cycle from adapter relocation**: adapters subclass port classes AND are
  needed by command modules — the dedicated `tasks_command_adapters.py` breaks the
  cycle; any deviation records why no cycle arises. The lazy parent-module routing keeps
  family siblings acyclic (no module-level back-import).
- **`_StatusRender` relocate-then-delete rework**: the render-seam work (FR-005/FR-006)
  must be sequenced before or with the status-family relocation so the class is deleted,
  not moved-then-deleted (a wasted move + a second seam re-point).
- **Golden delta on a "pure" move**: any contract-harness or byte-freeze delta means a
  botched move — the move is reverted and re-done. Re-pointing the coverage ratchet's
  AST target (FR-012) is NOT fixture adjustment; changing an expected-output fixture to
  absorb a behavior diff IS, and is forbidden.
- **AST gate false positives/negatives**: docstring mentions of `json.dumps` (line 1225)
  must not trip the gate (call-node inspection, not text); evasion forms (alias, rebind,
  move-next-door into an unscanned module) must (directory-glob scope + per-form
  self-mutation cases).
- **LOC ceiling honesty**: the recorded enforcement ceiling is `min(achieved, 1400)`.
  If the honest relocated size exceeds 1400, that is an escalation to the operator with
  the delta-from-4569 analysis — never a self-certified re-baseline.
- **Typer/rich version skew**: contract `--help` fixtures are typer-version-coupled —
  the venv must match `uv.lock` before running or re-freezing anything (Wave 1 trap).
- **Coord-authority writes**: this is a `topology: coord` mission — acceptance-matrix,
  issue-matrix, and review artifacts the gates read live on the coordination branch, not
  the primary checkout (Wave 1 close friction).

## Domain Language

- **Registration shim**: a command module containing only `@app.command` wrappers that
  delegate to relocated orchestrators, plus the deliberate seam-bridge/re-export surface.
- **Command family**: one subcommand's orchestrator + glue helpers + State dataclass +
  port factory. Five families: move_task (`_mt_*`), map_requirements (`_mr_*`), status
  (`_st_*`), mark_status (`_ms_*`), finalize_tasks (`_ft_*`).
- **Shared helper**: a cross-family helper (e.g. `_output_result`, `_find_mission_slug`)
  serving multiple command families; relocates to the shared module, never duplicated
  per family.
- **Seam bridge**: the mechanism that keeps `@patch("...agent.tasks.<sym>")` tests
  INTERCEPTING after relocation. Default (the `mission.py` template mechanism): relocated
  code performs a lazy in-function `from specify_cli.cli.commands.agent import tasks as
  _tasks` and calls infra via `_tasks.<attr>`, so the patched module attribute IS the
  called object. "Re-point the patches" is reserved for symbols that are themselves
  defined-and-relocated (their `agent.tasks.*` patch target disappears). A bare
  module-level re-export alone is NOT a seam bridge.
- **Render seam / Render port**: the injected output boundary (`Render.json_envelope` /
  `Render.human`); **one** production adapter serves all sites (indent parameterized).
- **Contract harnesses**: `test_tasks_cli_contract.py` (27 cases) +
  `test_tasks_cli_contract_coord.py` (16 cases, incl. the #2300 divergence pins T004/T005
  and the branch-coverage ratchet). 43 cases combined.
- **Byte-freeze suite**: NEW characterization tests (this mission, FR-005 pre-step)
  asserting the exact stdout bytes of each of the 13 JSON emission sites — the byte-level
  parity contract the shape-checked harness legs do not provide.
- **Gate-visible**: selected by at least one CI marker/path gate in `ci-quality.yml`.
- Canonical term is **Mission**; `--mission` is the only primary CLI flag form (charter
  Terminology Canon binds all moved and new code).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Relocate all **five** command families out of `tasks.py` into per-family sibling modules under `src/specify_cli/cli/commands/agent/` — each family's move-set is its orchestrator + its glue helpers + its State dataclass + its `_default_*_ports` factory (move_task: `_do_move_task` + 23 `_mt_*` + `_MoveTaskState` + factory; map_requirements: `_do_map_requirements` + 11 `_mr_*` + `_MapReqState` + factory; status: `_do_status` + 14 `_st_*` + `_StatusState` + factory; mark_status: `_do_mark_status` + 9 `_ms_*` + `_MarkStatusState` + factory; finalize_tasks: `_do_finalize_tasks` + 4 `_ft_*` + `_FinalizeState` + factory). | US1 | High | Open |
| FR-002 | Preserve patch **interception** across every relocation via the seam bridge: relocated code routes infra calls through lazy parent-module attribute access (`_tasks.<attr>`, the `mission.py` template mechanism) by default; symbols that are themselves defined-and-relocated get their test patches re-pointed in the same WP. Each relocation WP carries the affected symbol×patch-count inventory (from the ~40-symbol census) as its seam checklist, plus a positive interception check (the patched attribute is the object production calls) for defensively-patched seams. | US1 | High | Open |
| FR-003 | Relocate the **~30 cross-family shared helpers** (led by `_output_result`/`_output_error`, `_find_mission_slug`, `_ensure_target_branch_checked_out`) into a named shared sibling module with the same seam-bridge obligations; no helper is duplicated per family; no shared helper remains in `tasks.py` unless it is part of the registration surface itself. | US1 | High | Open |
| FR-004 | Relocate the port-seam adapter classes (`_MoveTaskCoordRouter`, `_MapReqCoordRouter`, `_MarkStatusCoordRouter` — and `_StatusRender` only if FR-006 has not already deleted it) into a dedicated `tasks_command_adapters.py`, with a recorded no-cycle argument for any deviation. | US1 | High | Open |
| FR-005 | **Byte-freeze first, then route**: commit byte-exact characterization tests for all 13 JSON emission sites (12 compact + the `indent=2` leg) against the pre-change tree, THEN route the 12 compact sites through the Render port with the byte-freeze suite green throughout. | US2 | High | Open |
| FR-006 | Parameterize the Render seam's indent (or add an indented-envelope capability) so the `indent=2` status leg uses the generic seam and the `_StatusRender(RealRender)` override is deleted; the status byte-freeze case stays green. | US2 | High | Open |
| FR-007 | Add an AST-based architectural gate asserting 0 inline `json.dumps` calls across the command-surface **directory glob** (`src/specify_cli/cli/commands/agent/` including all new sibling/adapter modules), covering all evasion forms — attribute call, `from json import dumps`, module alias, and local rebinding — with a self-mutation proof per form. | US2 | High | Open |
| FR-008 | Reduce `tasks.py` to thin `@app.command` registration wrappers, the four already-small bodies (`list_tasks`, `add_history`, `validate_workflow`, `list_dependents`), and the deliberate seam-bridge/re-export surface; decide and execute the disposition of the 7-line `cli/commands/agent/tasks_ports.py` re-export shim with rationale recorded (full unshim of other files stays with #2289–#2293). New sibling modules follow the template precedent (no `__all__` required — the charter's `__all__` convention binds `src/charter/` and `src/kernel/` only). | US1 | High | Open |
| FR-009 | Make the tasks-domain test surface gate-visible with non-gameable evidence: commit the tasks-domain glob (`tests/tasks/**`, `tests/specify_cli/cli/commands/agent/test_tasks*`, plus every test file this mission adds), produce a committed marker-census artifact mapping each matching file to its selecting CI gate (zero unselected), fix the ~1 invisible file, and assert that no path under the glob is present in (or added to) `_gate_coverage_baseline.json`. | US3 | Medium | Open |
| FR-010 | Refresh #2034 upstream with the 2026-07-02 re-census (257/26,612 marker-invisible repo-wide; original failure list largely fixed/re-marked; current gate inventory) and the recommended structural options — the repo-wide fix itself is out of scope. *(Initial refresh comment posted at spec time; final census posted at review.)* | US3 | Medium | Open |
| FR-011 | Add a `tests/architectural/` whole-file LOC gate for `tasks.py`: enforcement ceiling = `min(achieved, 1400)`; the gate ships with a non-vacuity self-mutation test; the recorded rationale states the achieved LOC and the delta from the 4569 baseline. An achieved size above 1400 is an operator escalation, never a self-certified re-baseline. | US1 | High | Open |
| FR-012 | Re-point the coord-harness branch-coverage ratchet (`_BRANCH_COVERAGE_FLOORS` / `_mutating_function_line_ranges`) to each relocated orchestrator **in the same WP as its move**; deleting the ratchet, lowering its floors, or leaving it measuring the thinned wrapper is forbidden. Ratchet re-pointing is expressly NOT "fixture adjustment". | US1 | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior parity, honestly defined | At every commit of every WP: (a) all 43 contract-harness cases pass unmodified; (b) the 10 `--help` fixtures remain byte-exact; (c) the byte-freeze suite (13 cases, FR-005) remains byte-exact; (d) expected-output fixtures are never adjusted to absorb a diff (revert-and-redo instead); (e) ratchet re-pointing per FR-012 is the sole sanctioned harness edit. | Correctness | High | Open |
| NFR-002 | Seam interception preserved | 100% of the ~370 `patch("...agent.tasks.<sym>")` call sites (~40 distinct symbols) still **intercept the production call path** after each relocation — evidenced per WP by the FR-002 seam checklist + interception check, not merely by "tests pass"; zero weakened or deleted assertions. | Correctness | High | Open |
| NFR-003 | Static gates | `ruff` and `mypy --strict` report zero issues on every changed src file, and strict mypy is run on changed src+test files **together** (Wave 1 lesson: attr-defined errors only surface with both in scope). | Maintainability | High | Open |
| NFR-004 | Whole-file ceiling | `tasks.py` total LOC ≤ the FR-011 enforcement ceiling (`min(achieved, 1400)`); measured by the gate in CI. | Maintainability | High | Open |
| NFR-005 | Targeted validation cost | Each WP declares and runs its targeted test surface — which MUST include `test_tasks_cli_contract_coord.py` for any WP touching commit routing or a `_do_*` orchestrator — not the full 26k suite; the full-suite gate is reserved for mission-level post-merge validation (charter Testing Requirements). | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | #2300 divergence untouched | The coord+protected skip-vs-refuse divergence (`move_task` skips-exit-0 via the `_skip_target_branch_commit` pre-gate; `mark_status`/`map_requirements` refuse-exit-1 through the shared `_protected_branch_status_commit_error`) is preserved verbatim. Its pins are `test_tasks_cli_contract_coord.py` T004/T005 (incl. the wrong-leg detector) — mandatory in the targeted set of every WP that touches commit routing. Relocation must not route the three commands through a helper arrangement that adds or drops the pre-gate for any of them. | Scope | High | Open |
| C-002 | Base is merged main | The mission bases on upstream/main `381db8d5f` (Wave 1 merged, including the `d8a0c8c8f` stabilization); all debrief line references are superseded by the squad-verified re-census in this spec. | Technical | High | Open |
| C-003 | Executable contract | This is a pure-parity refactor: the two contract harnesses + the byte-freeze suite + the new non-vacuous gates are the executable contract (ATDD-first per charter C-011 in its parity form — the byte-freeze suite is committed red-first-style BEFORE the routing change it guards, and every gate is proven red on a synthetic violation before it counts). | Process | High | Open |
| C-004 | #2173 seam discipline | No new rival seams: one production adapter per port; ports injected at the builder/shell boundary via the default-param idiom; the frozen context objects never carry live adapters. | Architectural | High | Open |
| C-005 | Terminology canon | All moved and new code, docstrings, and messages use `Mission`/`--mission` (never `feature`/`--feature` except pre-existing hidden aliases); the terminology guard (`tests/architectural/test_no_legacy_terminology.py`) passes before every push. | Governance | Medium | Open |
| C-006 | Gate non-vacuity | Every gate added (FR-007 AST gate, FR-011 LOC gate) ships with a concrete floor, self-mutation/synthetic-violation tests (per evasion form for FR-007), and shrink-only ratchet semantics where an allowlist/baseline exists — including the FR-009 prohibition on absorbing tasks-domain paths into `_gate_coverage_baseline.json` (DIRECTIVE_043); no mission-diff-scoped assertions. | Governance | High | Open |
| C-007 | Pre-existing failures reported | Any pre-existing test failure encountered is reported as a GitHub issue before being treated as baseline (charter Pre-existing Failure Reporting Rule); Wave 1's known pre-existing RED arch gates are cross-base-verified, not absorbed. | Process | Medium | Open |

### Key Entities

- **Command family module**: sibling module owning one family's orchestrator + glue +
  State dataclass + port factory; the relocation unit of Stream B.
- **Shared helpers module**: the named home for the ~30 cross-family helpers; the
  squad-identified missing piece of the per-family split.
- **Adapters module** (`tasks_command_adapters.py`): owns the port-seam adapter classes;
  exists to break the ports ↔ command-modules cycle risk.
- **Seam bridge**: lazy parent-module attribute routing preserving patch interception
  (see Domain Language).
- **Byte-freeze case**: one recorded CLI invocation with byte-exact expected stdout for
  one JSON emission site.
- **Marker-census artifact**: the committed mapping of each tasks-domain test file to
  the CI gate that selects it; the boyscout deliverable's evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `tasks.py` is at or under the FR-011 enforcement ceiling
  (`min(achieved, 1400)` LOC), enforced by a CI-visible architectural gate that fails on
  a synthetic violation; the recorded rationale states the delta from 4569.
- **SC-002**: 0 inline `json.dumps` (all evasion forms) across the command-surface
  directory glob, enforced by a CI-visible AST gate with a per-form self-mutation proof.
- **SC-003**: 43/43 contract-harness cases pass unmodified AND 13/13 byte-freeze cases
  are byte-identical on the mission's final commit vs the mission base — zero behavioral
  diffs, with the ratchet re-pointed (FR-012), not weakened.
- **SC-004**: 100% of the ~370 patch-seam call sites (~40 symbols) intercept the
  production call path post-relocation, evidenced by the per-WP seam checklists and
  interception checks; zero deleted or weakened assertions.
- **SC-005**: The committed marker-census artifact shows 0 tasks-domain files (per the
  committed glob) selected by no CI gate; `_gate_coverage_baseline.json` contains no
  path under the glob; #2034 carries the refreshed re-census comment.
- **SC-006**: Zero `ruff`/`mypy --strict` findings on changed files (src+tests checked
  together); terminology guard green.

## Assumptions

- The `mission.py` degod (`kitty-specs/decompose-mission-god-module-01KVXHF8/`) is the
  accepted relocation template — including its actual seam mechanism (lazy parent-module
  attribute routing) and its no-`__all__`-on-siblings precedent.
- The dedicated `tasks_command_adapters.py` is the default adapter home (import-cycle
  avoidance); consolidation elsewhere requires a recorded no-cycle argument.
- **Planning guidance (squad-adjusted sizing)**: expect **8–10 WPs**, not the debrief's
  5 — the shared-helpers module and the seam-bridge/adapters foundation are their own
  WPs before any family move; the render-seam WP is sequenced before or with the
  status-family move (the `_StatusRender` ordering edge case); the boyscout is small.
- The repo-wide #2034 structural fix (marker gate redesign or global auto-marking) is a
  separate mission; this mission only makes its own domain clean and refreshes the facts.
- Tracker hygiene per charter: #2305 claimed (operator assigned, mission-naming comment
  posted 2026-07-02); #2034 partial-claim comment with re-census posted 2026-07-02.

## Campsite Folds (domain-matched, pre-plan squad 2026-07-02)

Per charter standing order 2 (fold only domain-matched debt), the pre-plan related-issues
squad identified exactly three folds — everything else in #1931/#2071 is out-of-domain
and stays with its epic:

- **#2306** (filed per C-007): `test_untrusted_path_containment` is RED on the mission
  base — Wave 1's `inventory.md` records the `tasks.py` sink at `:1325`, actual is
  `:1326`. Fold: 1-line inventory correction as a pre-step; the inventory row then moves
  with the move_task family relocation (FR-001/FR-002 seam checklist item).
- **mypy strict inline folds** (no separate issue; NFR-003 scope): `test_tasks.py:26`
  `attr-defined` on `_get_latest_review_cycle_verdict` (re-point the import in the WP
  that relocates the symbol) and `test_tasks.py:1028` redundant-cast (1-line removal in
  the first WP touching that file).

**Parallel-work state (recorded so it isn't re-investigated):** zero active collisions
as of 2026-07-02 — no open upstream PR or live branch touches the tasks surface;
`design/degod-tasks-2116` is merged dead lineage. Latent risks fenced by comments:
#2300 (do-not-start-until-Wave-2-lands warning posted), #2289 (`tasks_ports.py`
ownership note posted), #2034 (dormant; assignee has no open PRs). Expect stale-assertion
analyzer false-positive noise at every WP merge (#2031 — analyzer is intra-file only).

## Non-Goals / Deferred

- **#2300** — skip-vs-refuse unification (behavior change; own mission; C-001 guards it).
- **Repo-wide marker-gate redesign** (#2034 structural fix beyond the tasks domain).
- **The unshim cluster #2289–#2293** — except the single `tasks_ports.py` shim
  disposition (FR-008).
- **New ports or port extractions** (#2173 Phase 1/Phase 2 work — canonicalizer gate,
  MissionResolver port — are their own missions).
- **Any decision-logic change** — the pure cores from Wave 1 are consumed as-is.
- **Relocating `agent_tasks_ports.py` from its top-level placement** — squad-verified as
  deliberate and rationale-recorded, not a wart.
