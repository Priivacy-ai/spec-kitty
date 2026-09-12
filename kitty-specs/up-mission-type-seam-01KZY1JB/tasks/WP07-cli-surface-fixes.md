---
work_package_id: WP07
title: 'Four CLI-surface fixes: charter mission-type list, mission-type show, doctrine mission-type list, activate warnings'
dependencies:
- WP05
- WP06
requirement_refs:
- C-005
- FR-006
- FR-007
- FR-008
- FR-009
- NFR-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 5 - CLI-surface fixes (IC-07, the mission's last WP)
assignee: ''
agent: claude
history:
- at: '2026-08-13T00:00:00Z'
  actor: system
  action: Prompt generated during /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/charter/mission_type.py
- src/specify_cli/cli/commands/mission_type.py
- src/specify_cli/cli/commands/doctrine.py
- src/specify_cli/cli/commands/charter/activate.py
- tests/cli/test_charter_mission_type_commands.py
- tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py
- tests/cli/test_doctrine_commands.py
- tests/cli/test_charter_activate_warning.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Four CLI-surface fixes

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` and behave according to its guidance
before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Stop each of the four consumer surfaces from tolerating-and-lying about a non-built-in mission
type, using WP03's layered lookup and WP04's real projected fields. This is the mission's last WP
— it depends on WP05 (activation must actually succeed for a non-built-in type before these
display surfaces have anything real to show) and WP06 (see "Why WP06 is a dependency" below,
beyond what plan.md's IC-07 bullet literally lists).

**Why WP06 is a dependency, beyond plan.md's literal IC-07 text**: plan.md's IC-07 Sequencing
bullet lists only IC-01/IC-02/IC-03 as dependencies. But IC-07's own Test surface bullet says:
"`tests/cli/test_charter_activate_warning.py` specifically extended for the 'resolution failure
surfaces, not silently treated as no removed steps' edge case from spec.md's Edge Cases section."
That edge case is: "What happens when `charter activate`'s step-removal warning path (FR-009) is
evaluated for a mission type whose previous `action_sequence` cannot be resolved at all (e.g. was
itself the CL-003 empty-sequence error case)? It must surface that resolution failure rather than
silently treating 'cannot resolve' as 'no steps were removed.'" Testing this concretely requires
`MissionTypeEmptyActionSequenceError` (WP06) to already exist. This WP's `wps.yaml` entry
therefore lists WP06 as a direct dependency — a deliberate refinement over plan.md's literal text,
not a contradiction of it.

**Four fixes, each independently re-verified live during planning (verify again before you start —
line numbers drift)**:

1. **FR-006**: `charter_mission_type_list`
   (`src/specify_cli/cli/commands/charter/mission_type.py`, live-verify — plan.md cites `49-84`, the
   "unknown"-layer tolerate branch at `74-83`) — replace the `source_layer: "unknown"` branch with
   a real per-id layer lookup. This command needs a **per-id source layer**
   (`"built-in"|"org"|"project"`) — `resolve_mission_type_context` gives an action sequence and a
   *governance* provenance, but the roster's own layer for a given id is a property of WP03's new
   layered repository, not of the governance-profile resolver. Reach the new factory (or a lookup
   method on the object it returns) directly.
2. **FR-007**: `show_mission_type`
   (`src/specify_cli/cli/commands/mission_type.py`, live-verify — plan.md cites `1450-1520`) — this
   function has **three independently-verified problem sites**, per the binding operator ruling
   (`reviews/plan.ruling.md`, PLAN-FRESH2-001, severity 4 — this finding is the reason the plan
   phase HALTed once; do not repeat the mistake of fixing only one site):
   - **(1)** the `mt is None` → `typer.Exit(1)` branch (live-verify — plan.md cites `1487-1490`),
     which wrongly hard-fails for a genuinely-activated-but-non-built-in type because it queries
     the built-in-only `MissionTypeRepository.default()` (live-verify — plan.md cites line `1485`)
     instead of the layered lookup.
   - **(2)** the JSON-output branch's hardcoded `"source_layer": "built-in"` literal (live-verify —
     plan.md and the ruling both cite line `1531`).
   - **(3)** the human-readable Panel branch's own, **independently**-hardcoded `"[cyan]Source
     Layer:[/cyan] built-in"` literal (live-verify — the ruling specifically cites line `1543`, the
     **default, non-`--json` path that User Story 1 AC3 exercises**). Sites (2) and (3) are two
     separate lying sites, not one, because the JSON branch and the Panel branch each build their
     output list from scratch rather than sharing one already-computed `source_layer` value —
     **fixing (2) alone leaves (3) unfixed and would silently fail User Story 1 AC3's actual
     acceptance scenario** (which uses the default, non-JSON output). Fix all three sites.
3. **FR-008**: `doctrine mission-type list`
   (`src/specify_cli/cli/commands/doctrine.py`, live-verify — plan.md cites `_collect_built_in_mission_types`/
   `mission_type_list` at `1028-1069`) — extend the `rows` collection (live-verify — plan.md cites
   assignment at line `1067`) to include org/project entries, matching the command's own
   pre-existing docstring promise (live-verify — plan.md cites `1058-1059`; the docstring already
   documents built-in→org→project layering — you are implementing what it already claims, not
   rewriting the docstring).
4. **FR-009**: `_emit_step_removal_warnings`
   (`src/specify_cli/cli/commands/charter/activate.py`, live-verify — plan.md cites `151-192`) —
   replace the bare `except Exception: current_seq = []` (live-verify — plan.md cites `180-181`)
   and the `MissionTypeRepository.default().get(artifact_id)` call (live-verify — plan.md cites
   line `183`) with layer-aware resolution: for a non-built-in type, resolve through the same
   layered path WP03/WP04 established, and — per the edge case above — if resolution itself fails
   (e.g. WP06's `MissionTypeEmptyActionSequenceError`), let that surface rather than silently
   treating "cannot resolve" as "no steps were removed."

## Context & Constraints

- **Contract preservation (read plan.md's "Contract Movement" table in full before touching any of
  the four surfaces)**: none of these four fixes change field names, JSON shape, or the trigger
  condition for a warning — only *values* change from placeholder/wrong to real. Specifically:
  `charter mission-type list`'s output columns/JSON keys are unchanged, only the `source_layer`
  and `action_sequence` values are corrected; `mission-type show`'s exit-1 case for a genuinely
  unresolvable type is unchanged (still exit 1, still lists registered ids) — only the
  previously-mis-failing "activated org type" case is fixed; `doctrine mission-type list`'s
  contract is unchanged (the docstring already describes the target behavior) — only the `rows`
  collection call changes; `_emit_step_removal_warnings`'s warning text and trigger condition are
  unchanged — only the previously-blind non-built-in case now actually evaluates.
- **This WP is the mission's integration point** — by the time you start, WP03 (layered lookup),
  WP04 (pack_context threading), WP05 (activation scan), and WP06 (loud-fail) must all be
  `approved`/`done`. If any dependency-readiness check fails when you attempt to claim this WP, do
  not work around it — that is the gate doing its job.
- **This is where User Story 1's full end-to-end regression (SC-001) is finally assembled**: "An
  org-pack mission type with a populated `action_sequence`, activated in a test project, resolves
  through `mission create`, `charter mission-type list`, `mission-type show`, and `doctrine
  mission-type list` with correct, non-empty, non-`"unknown"` output at every one of those four CLI
  surfaces — verified by an end-to-end regression test exercising all four." Write this test in
  this WP — it is the mission's capstone proof.
- **Terminology**: no `feature*` alias.
- **Known open-PR collision on `src/specify_cli/cli/commands/doctrine.py` (T018)**: two live, open,
  non-draft upstream PRs independently modify this exact file as of planning time — PR
  [#3166](https://github.com/Priivacy-ai/spec-kitty/pull/3166) ("feat(doctrine): ETag skip +
  Artifactory version for HTTPS fetch") and PR
  [#2719](https://github.com/Priivacy-ai/spec-kitty/pull/2719) ("feat: doctrine org init from
  local/git template"). Before starting T018, re-run `gh pr list --search "doctrine.py in:file"`
  (or, more reliably, `gh pr list --state open --json number,title,files --limit 200` filtered for
  `cli/commands/doctrine.py`) to confirm whether these PRs have merged or new ones have opened
  against this file, and re-verify the `_collect_built_in_mission_types`/`mission_type_list` line
  numbers and surrounding code shape against `main`'s current state rather than trusting this
  prompt's or plan.md's already-cited line numbers to still hold — both PRs may have merged or
  drifted by the time this WP is implemented.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-up-mission-type-seam-01KZY1JB`. During `/spec-kitty.implement` this WP may branch
  from a dependency-specific base, but completed changes must merge back into
  `kitty/mission-up-mission-type-seam-01KZY1JB` unless the human explicitly redirects the landing
  branch.
- **Planning base branch**: `kitty/mission-up-mission-type-seam-01KZY1JB`
- **Merge target branch**: `main`
- **Known `lanes.json` cycle — verify the self-heal ran, on the canonical implement path**: WP07
  sits in `lanes.json`'s `lane-a` (together with WP02 and WP03), which the write_scope_overlap
  collapse rule created because WP02 shares files with both WP03 and WP07. Because that merged lane
  spans the mission's full temporal extent, `lane-a`'s `depends_on_lanes` (`[lane-b, lane-c,
  lane-planning]`) and `lane-b`'s/`lane-c`'s own `depends_on_lanes` (`[lane-a]`) form a real cycle
  — see `wps.yaml`'s header comment for the full mechanism. `worktree_allocator.py`'s
  `_merge_dependency_lane_tips` mechanically git-merges dependency-lane tips at worktree-allocation
  time, and it runs on the reuse path too (`worktree_allocator.py:194-207`) specifically to catch up
  a dependency lane approved *after* the worktree was created — a documented, precedented
  self-healing mechanism (issue #1684; the WP05/WP09 double-hit on mission 01KTYGTE is the cited
  prior incident it was built for), not an unmitigated landmine. WP07's own WP-level
  `dependencies: [WP05, WP06]` already gates its claim/start until those WPs are approved/done, so
  by the time WP07 can actually be claimed, `lane-b`'s and `lane-c`'s branches are guaranteed to
  exist and the idempotent catch-up merge should succeed cleanly on the ordinary
  `spec-kitty implement WP07` path — no special handling should be needed. As a verification-only
  sanity check, not a substitute for that guarantee: after running `spec-kitty implement WP07`,
  resolve `lane-b`'s and `lane-c`'s actual branch names inside the resulting worktree —
  `git branch -a --list '*lane-b*'` and `git branch -a --list '*lane-c*'` — then confirm
  `git merge-base --is-ancestor <resolved lane-b branch> HEAD` and the equivalent for `lane-c`'s
  resolved branch both hold (i.e. each lane's tip commit landed as an ancestor of HEAD, meaning the
  catch-up merge actually happened). If either does not hold, that is evidence of a genuine
  allocator bug — report it upstream against
  `worktree_allocator.py`; it is never a license to bypass `spec-kitty implement WP07` or
  hand-construct the workspace directly against the mission coordination branch. Per CLAUDE.md's
  Execution Workspace Strategy, `spec-kitty implement WP##` is the only supported way to prepare a
  workspace — agent commands must consume the resolved workspace path, not reconstruct it.

## Subtasks & Detailed Guidance

> **Red-first commit ordering (C-011, ATDD-First Discipline — binding)**: for each of T016-T019,
> write or extend the subtask's test FIRST, run it against the current (pre-fix) code, and confirm
> it fails for the specific reason that subtask's fix corrects — not merely that it fails. Only
> then implement the fix and confirm the test turns GREEN. This mirrors WP03 (T005, "Red-first")
> and WP05 (T012 step 1, explicit fail-first instruction) elsewhere in this mission. Each subtask
> below states the concrete pre-fix failure mode the RED test must demonstrate.

### Subtask T016 – Fix `charter_mission_type_list`'s `"unknown"` branch (FR-006)

- **Purpose**: report the real resolution layer per id.
- **Steps**:
  1. **Red-first**: write (or extend) the test asserting a per-id real layer (`"built-in"` /
     `"org"` / `"project"`) for an activated non-built-in type; run it against the current code and
     confirm it fails because `source_layer` is still the hardcoded `"unknown"` tolerate value.
  2. Replace the `source_layer: "unknown"` tolerate branch with a per-id layer lookup against WP03's
     layered repository; confirm the JSON/table output shape (field names, types) is unchanged.
  3. Confirm the test from step 1 now passes.
- **Files**: `src/specify_cli/cli/commands/charter/mission_type.py`,
  `tests/cli/test_charter_mission_type_commands.py`.
- **Parallel?**: Can proceed alongside T017/T018/T019 (different files), land together for review
  coherence.

### Subtask T017 – Fix `show_mission_type`'s three sites (FR-007)

- **Purpose**: the PLAN-FRESH2-001 severity-4 finding's full remediation — all three sites, not one.
- **Steps**:
  1. **Red-first**: write the test first, asserting on BOTH the `--json` output AND the default,
     non-`--json` Panel output for the same activated non-built-in type (in the same test, or two
     tests that both must pass). Run it against the current code and confirm it fails at all three
     sites for their distinct reasons: site (1) hard-fails with `typer.Exit(1)` because it queries
     only `MissionTypeRepository.default()`; site (2)'s JSON output reports the hardcoded
     `"source_layer": "built-in"` literal instead of the real layer; site (3)'s Panel output
     independently reports the hardcoded `"[cyan]Source Layer:[/cyan] built-in"` literal instead of
     the real layer. Confirm the test would still fail if only site (2) were fixed and site (3) were
     left as-is — this is the exact "two independently-hardcoded lying sites, not one" gap
     PLAN-FRESH2-001 HALTed the plan phase over; a test that passes after fixing only site (2) is
     not a valid red-first pin for this subtask.
  2. Fix site (1): the `mt is None` branch queries the layered lookup (not just
     `MissionTypeRepository.default()`) before hard-failing, so an activated non-built-in type
     succeeds.
  3. Fix site (2): the JSON branch's `source_layer` value comes from the real resolved layer.
  4. Fix site (3): the Panel branch's `"[cyan]Source Layer:[/cyan] built-in"` literal is replaced
     with the same real resolved layer — **do this as a genuinely separate edit from site (2)**,
     confirming both branches read from one shared, already-computed `source_layer` value rather
     than each hardcoding their own.
  5. Confirm the test from step 1 now passes in full — both the `--json` and default Panel
     assertions.
- **Files**: `src/specify_cli/cli/commands/mission_type.py`,
  `tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py`.
- **Parallel?**: Can proceed alongside T016/T018/T019.
- **Notes**: This is the highest-risk subtask in this WP — the plan phase HALTed once over exactly
  this "two independently-hardcoded lying sites, not one" finding. Do not let a "fix the JSON
  branch, ship it" instinct repeat that mistake. The red-first test in step 1 is what makes this
  mistake mechanically detectable rather than merely instructed-against.

### Subtask T018 – Fix `doctrine mission-type list`'s layering (FR-008)

- **Purpose**: implement the layering the command's own docstring already promises.
- **Steps**:
  1. **Red-first**: write the test asserting org/project entries appear in `doctrine mission-type
     list`'s output (with correct `source_layer` values) for a non-built-in type that is merely
     *registered* (not necessarily activated). Run it against the current code and confirm it fails
     because the `rows` collection today only calls `_collect_built_in_mission_types()` — org/project
     entries are simply absent from the output, not mislabeled.
  2. Extend the `rows` collection (currently only `_collect_built_in_mission_types()`) to also
     enumerate org/project entries via WP03's layered repository, with a correct `source_layer` per
     row; confirm this is a *listing* operation (all ids across all layers regardless of
     activation), not an activation-scoped one — do not accidentally scope it to only activated
     types.
  3. Confirm the test from step 1 now passes.
- **Files**: `src/specify_cli/cli/commands/doctrine.py`, `tests/cli/test_doctrine_commands.py`.
- **Parallel?**: Can proceed alongside T016/T017/T019.

### Subtask T019 – Fix `_emit_step_removal_warnings` for non-built-in types + the resolution-failure edge case (FR-009)

- **Purpose**: warn about in-flight missions affected by removed steps regardless of which layer
  the type came from, and surface a resolution failure rather than silencing it.
- **Steps**:
  1. **Red-first**: write the edge-case test FIRST — a mission type whose previous
     `action_sequence` cannot be resolved at all (construct a scenario where WP06's
     `MissionTypeEmptyActionSequenceError` would fire) — asserting this resolution failure
     **surfaces** (propagates or is reported). Run it against the current code and confirm it fails
     because the bare `except Exception: current_seq = []` silently swallows the failure and treats
     it as "no steps were removed" instead of surfacing it.
  2. Replace the bare `except Exception: current_seq = []` and the built-in-only `.get(artifact_id)`
     call with layer-aware resolution using WP03/WP04's layered path.
  3. Confirm the test from step 1 now passes — the resolution failure surfaces rather than being
     silently swallowed.
  4. Confirm the existing warning text and trigger condition (a step was removed) are unchanged for
     the cases that already worked.
- **Files**: `src/specify_cli/cli/commands/charter/activate.py`,
  `tests/cli/test_charter_activate_warning.py`.
- **Parallel?**: Can proceed alongside T016/T017/T018; this is the subtask that specifically needs
  WP06's exception class to exist (see Objectives above for why WP06 is a dependency).

### Subtask T020 (capstone) – SC-001 end-to-end regression test

- **Purpose**: the mission's own headline success criterion, assembled last.
- **Steps**: author an org-pack mission-type YAML (id, display_name, `action_sequence` with at
  least one step) under a scratch project-layer or org-layer pack root; activate it
  (`charter activate mission-type <id>`); run `mission create --mission-type <id>`; assert the
  created mission's action sequence and template set are non-empty and match the org-pack's
  declared steps exactly; run `charter mission-type list` and assert `source_layer` is correct
  (not `"unknown"`); run `mission-type show <id>` (both `--json` and default output) and assert it
  succeeds with the correct fields; run `doctrine mission-type list` and assert the type appears
  with the correct layer. All four surfaces, one test (or a tightly-grouped set), matching User
  Story 1's own Independent Test description verbatim.
- **Files**: wherever this mission's existing tests already have end-to-end CLI-invocation
  infrastructure — check `tests/cli/test_charter_mission_type_commands.py` first since it's already
  in this WP's `owned_files`; if a genuinely separate end-to-end file is warranted, that is a
  judgment call for the implementer, but prefer landing it in an existing owned file over creating
  a new one.
- **Parallel?**: No — depends on T016–T019 all being in place.
- **Notes on red-first**: T020 is an integration capstone over T016-T019's already-fixed surfaces,
  not a standalone fix — it does not have its own pre-fix RED state to pin (by the time it runs,
  T016-T019 are done). If practical, first run T020's scenario against a pre-WP07 checkout (or
  before any of T016-T019 are applied) to confirm it fails end-to-end (e.g. `charter mission-type
  list` still reports `"unknown"`, `mission-type show` still hard-fails or lies about the layer),
  then confirm it passes once T016-T019 all land — this gives SC-001 the same RED→GREEN evidence
  trail as the rest of the mission, even though T020 itself is assembled last.

## Test Strategy

- **Per-AC / per-SC**: this WP proves **SC-001** in full (T020, the capstone), **SC-003** ("100%
  of existing built-in mission-type behavior across the four CLI surfaces... is unchanged" —
  re-run the existing test suites for all four surfaces unmodified except for this mission's own
  new tests, cross-checked against WP04's golden-parity extension), and User Story 1 AC1/AC3
  directly.
- **Test surface**: `tests/cli/test_charter_mission_type_commands.py`,
  `tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py`,
  `tests/cli/test_doctrine_commands.py`, `tests/cli/test_charter_activate_warning.py` — one test
  per surface exercising an activated non-built-in type end-to-end, plus T020's capstone.
- **Commands**: `uv run pytest tests/cli/test_charter_mission_type_commands.py
  tests/specify_cli/cli/commands/test_mission_type_template_set_cli.py
  tests/cli/test_doctrine_commands.py tests/cli/test_charter_activate_warning.py -v`
- **Red-first / commit ordering (C-011)**: each of T016-T019 writes or extends its test first,
  proves it RED against the pre-fix code for the specific reason its fix corrects, then implements
  the fix and confirms GREEN — see each subtask's Steps above for the concrete pre-fix failure mode.
  T020's capstone is an integration proof over the already-fixed surfaces rather than its own
  standalone RED pin (see its Notes). A reviewer verifies RED-then-GREEN evidence for T016-T019
  the same way they do for WP03/WP05/WP06 elsewhere in this mission.

## Risks & Mitigations

- **Risk (the mission's own documented near-miss)**: fixing `show_mission_type`'s JSON branch
  (site 2) and believing FR-007 is done, leaving the Panel branch (site 3) — the actual default
  output path User Story 1 AC3 exercises — still lying. **Mitigation**: T017's explicit dual-branch
  test requirement; this is the exact finding (PLAN-FRESH2-001) that HALTed the plan phase once.
- **Risk**: `doctrine mission-type list`'s fix accidentally scopes to only activated types (making
  it activation-scoped like `resolve_mission_type_context`) rather than a true all-layers listing.
  **Mitigation**: T018's explicit note distinguishing listing from activation-scoping.
- **Risk**: the FR-009 resolution-failure edge case is tested against a generic exception rather
  than the real `MissionTypeEmptyActionSequenceError` from WP06. **Mitigation**: T019 step 2's
  explicit instruction to construct the real scenario, not a stand-in.
- **Risk**: JSON/output contract drift (new/renamed field). **Mitigation**: plan.md's Contract
  Movement table is the binding reference; re-read it before finalizing any output-shape change.

## Gate Set (this WP's Definition of Done)

- **`fast-tests-cli` + `integration-tests-cli`** (`--cov=src/specify_cli/cli`) — all four fixed
  commands are directly in scope.
- **`diff-coverage` (critical-path, 90%, `[ENFORCED]`)** — note: `src/specify_cli/cli/*` is not
  itself named in plan.md's `critical_paths` array (only `src/doctrine/*` and `src/charter/*` are)
  — but this WP's own `fast-tests-cli` job-level coverage still applies, and every new/changed
  branch across the four fixes should carry a directly-testing unit test regardless (CLAUDE.md's
  Sonar Expectations: "every new branch/helper needs tests in the same PR" applies as engineering
  discipline independent of which CI job enforces it).
- **`arch-adversarial`** — this WP may possibly touch `src/charter/missions.py` (a facade
  re-export), conditional on whether WP03 resolved its factory-shape choice toward the bare-function
  shape (see plan.md's "The Seam" section) — if so, `tests/architectural/test_charter_facades_reexport_doctrine.py`
  is directly relevant; confirm with WP03's actual landed shape before assuming either way.
- **Typer 0.26 JSON error surface** — directly relevant: all four fixed commands support `--json`
  today and must keep emitting the same JSON error shape on failure.
- **`patch() target validation`, `Bandit`, `pip-audit`, `commitlint`** — always-on in `lint`.
- **markdown lint / architecture-docs consistency** — not directly relevant to this WP's own diff
  (no markdown changed here), but still run as part of the always-on `lint` job.
- `make lint` locally before handing off.

## Review Guidance

- **Specifically re-verify PLAN-FRESH2-001's fix**: confirm BOTH the JSON output and the default
  Panel output of `mission-type show <activated-non-built-in-type>` report the correct layer, not
  just one.
- Confirm `doctrine mission-type list` lists non-activated non-built-in types too (a true
  all-layers roster listing), not only activated ones.
- Confirm `_emit_step_removal_warnings`'s resolution-failure edge case genuinely surfaces (raises
  or is reported), not swallowed by a broader `except Exception` left over from before this WP's
  fix.
- Confirm the SC-001 capstone test (T020) exercises all four surfaces in one coherent scenario
  matching User Story 1's Independent Test description.
- Confirm plan.md's Contract Movement table's "preserved or versioned" column holds for every one
  of the four fixes — no field renamed, no JSON shape changed.
- **Check red-first compliance for T016-T019 (and T020's pre/post evidence)**: for each of
  T016-T019, confirm the test was written/extended and demonstrably failed against the pre-fix code
  for the specific reason that subtask's fix corrects (not merely "a test exists"), before the fix
  landed — mirroring the red-first verification pattern WP03/WP05/WP06 already use elsewhere in
  this mission. Reject a PR that shows only "tests pass now" with no RED evidence for these four
  subtasks.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-13T00:00:00Z – system – Prompt created.
