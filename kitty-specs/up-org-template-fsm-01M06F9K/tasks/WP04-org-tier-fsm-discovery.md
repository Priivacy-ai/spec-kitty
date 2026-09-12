---
work_package_id: WP04
title: Org tier in both FSM discovery walks, all three wiring sites
dependencies:
- WP02
requirement_refs:
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-003
- NFR-004
planning_base_branch: up-org-template-fsm
merge_target_branch: up-org-template-fsm
branch_strategy: Planning artifacts for this mission were generated on up-org-template-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into up-org-template-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase 2 - FSM discovery
history:
- at: '2026-08-17T00:02:22Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/runtime/next/_internal_runtime/discovery.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/_internal_runtime/discovery.py
- src/runtime/next/runtime_bridge_io.py
- src/specify_cli/mission_loader/command.py
- tests/next/test_internal_runtime_coverage.py
- tests/runtime/test_bridge_io.py
- tests/unit/mission_loader/test_command.py
- tests/integration/test_mission_run_command.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Org Tier in Both FSM Discovery Walks

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this
prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` and `authoritative_surface: src/runtime/next/_internal_runtime/discovery.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review.
Address every feedback item and update the Activity Log as you go.

---

## ⚠️⚠️ FILE COLLISION WITH WP06 — READ BEFORE TOUCHING `runtime_bridge_io.py`

**WP06 also edits `src/runtime/next/runtime_bridge_io.py`.** This is the single `owned_files`
overlap in the whole mission (`plan.md`'s "owned_files note"). It is a **file collision, not a
functional dependency**:

- **This WP (WP04)** edits `_build_discovery_context` and `_runtime_template_key`'s `project_tiers`
  construction.
- **WP06** edits `_template_key_for_file` and `_resolve_runtime_template_in_root` — different
  functions in the same file.

WP06 depends on this WP in the dependency graph **specifically so the two WPs never edit this file
concurrently** — not because WP06's diagnostic logic has a real functional need for this WP's tier
logic to exist first (though FR-011's "malformed `mission.yaml` at the org tier" test fixture does
need an org tier position to exist to be meaningful, which this WP provides). **Do not let anyone
"optimize" WP04 and WP06 back into parallel work packages** — if you are coordinating multiple
lanes/agents, this WP must land (be merged/approved) before WP06 starts.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

This WP is **IC-04** from `plan.md`'s Implementation Concern Map. It mirrors WP03's template-chain
org tier into FSM mission discovery, which has its own, separately forked walks:

- **Walk A**: `src/runtime/next/_internal_runtime/discovery.py`'s generic engine loader
  (`DiscoveryContext`, `_build_tiers`, `discover_missions_with_warnings`).
- **Walk B**: `src/runtime/next/runtime_bridge_io.py`'s `_runtime_template_key`.

Both must source `org_roots` via `charter.drg.resolve_org_roots(repo_root)` at **three** real
production `DiscoveryContext` construction sites (DEC-006), not the two an earlier, informal
research pass named:

1. `runtime_bridge_io.py`'s own `_build_discovery_context` — the single construction site both
   `get_or_start_run` and `_start_ephemeral_query_run` pass into `start_mission_run(context=...)`,
   which is what actually feeds Walk A's `discover_missions`/`_build_tiers` machinery for
   `spec-kitty next`.
2. `src/specify_cli/mission_loader/command.py`'s own, **independently duplicated**
   `_build_discovery_context` — its docstring says explicitly *"Mirror
   `runtime_bridge._build_discovery_context`... we duplicate the construction here so this module
   does not depend on a private surface."* This is the real production entry point for `mission run
   <key>` (`run_custom_mission`), exercised by `tests/integration/test_mission_run_command.py`, one
   of the two suites the mission-loader `>=90%` coverage gate runs.
3. `_runtime_template_key`'s own `project_tiers` list (Walk B) — a **separate**, hand-rolled tier
   list that does not go through `_build_tiers` at all; it needs its own org-tier insertion.

`src/runtime/next/_internal_runtime/engine.py:176`'s bare `DiscoveryContext()` (a drift-detection
fallback when no context is supplied, with no `repo_root` to resolve org packs against) is
**explicitly out of scope** — do not add org-root population there.

**Success criteria** (per `plan.md`'s Verification Design table):

- **FR-007**: `DiscoveryContext` gets an `org_roots: list[Path]` field; `_build_tiers` inserts an
  `("org", ..., context.org_roots)` tier immediately after `"project_legacy"`, before
  `"user_global"`.
- **FR-008**: `org_roots` is populated via `charter.drg.resolve_org_roots(repo_root)` at both real
  Walk A construction sites (site 1 and site 2 above); `mission run <key>` discovers an org-pack
  fixture at tier `"org"`.
- **FR-009**: `_runtime_template_key`'s `project_tiers` list gets the org tier inserted immediately
  after the existing `.kittify/missions` (project-legacy) entry, before `user_global`/`builtin`.

## Context & Constraints

Read before starting:
- `.kittify/charter/charter.md` — governing charter.
- `kitty-specs/up-org-template-fsm-01M06F9K/spec.md` — DEC-004, DEC-006, User Story 3 (with its
  exact Independent Test and four Acceptance Scenarios), FR-007, FR-008, FR-009, NFR-003, NFR-004,
  SC-003, SC-008.
- `kitty-specs/up-org-template-fsm-01M06F9K/plan.md` — IC-04's Purpose/Risks; the "NFR-003
  Compliance Without a Gate" section (reproduced below); Plan-Time Verification's citations for
  `discovery.py:90-97,201-245`, `runtime_bridge_io.py:230-241,325-351`, and
  `mission_loader/command.py:73-99,187-200`.

**This mission is dogfooded inside spec-kitty's own repository — a PUBLIC repo based on `main`.**
No host paths, no usernames, no absolute local paths in any committed file — sweep your diff before
finishing.

### Use `charter.drg.resolve_org_roots` via the existing lazy-import pattern

Same discipline as WP03: **never import `doctrine.*` directly from `specify_cli` or `runtime`.**
`discovery.py` and `runtime_bridge_io.py` already use the lazy `from charter.drg import
resolve_org_roots` shape elsewhere in the codebase for other symbols
(`runtime_bridge_io.py:106,582,641,681` — same file, same pattern, different imports); mirror it
for `resolve_org_roots` too. `mission_loader/command.py` should use the identical lazy pattern.

### NFR-003 — `src/runtime/next/**` has no automated gate for this discipline

`tests/architectural/test_runtime_charter_doctrine_boundary.py`'s `_RUNTIME_ROOT` is hardcoded to
`src/specify_cli` and does **not** scan `src/runtime/next/**` at all (filed as **#3522**). A green
CI run on this WP's PR is **not evidence** that `discovery.py` and `runtime_bridge_io.py` route
their org-root lookups through `charter.drg.resolve_org_roots` rather than a direct `doctrine.*`
import.

**Compliance here is verified by review, not by CI**:
1. At implementation time, manually confirm both files import `resolve_org_roots` via `from
   charter.drg import resolve_org_roots` (lazy), not `from doctrine.drg.org_pack_config import
   resolve_org_roots` directly.
2. **Your PR description MUST state explicitly** that `src/runtime/next/**`'s facade discipline for
   this WP's changes was confirmed by manual review, not by an automated gate, and **must name
   issue #3522** as the reason no gate caught it. Do not let a reviewer read "CI is green" and
   conclude NFR-003 holds — say so in the PR text itself.

### Mission-loader coverage gate

`src/specify_cli/mission_loader/command.py` (the third wiring site) is inside the **enforced ≥90%
mission-loader coverage gate** (`.github/workflows/ci-quality.yml:1437-1462`,
`--cov-fail-under=90`, scoped to `src/specify_cli/mission_loader`). The test for this site must
actually exercise `run_custom_mission`/`_build_discovery_context` and must land where that coverage
run collects from — `tests/unit/mission_loader/test_command.py` or
`tests/integration/test_mission_run_command.py` — not only inside `tests/next/` or
`tests/runtime/`, which that coverage run does not scan.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

Implementation command (with dependencies):
```bash
spec-kitty agent action implement WP04 --agent <name>
```

## Subtasks & Detailed Guidance

### Subtask T019 – Red-first `DiscoveryContext`/`_build_tiers` test

**Purpose**: Prove the "before" state for FR-007.

**Steps**:
1. In `tests/next/test_internal_runtime_coverage.py` (which already imports `DiscoveryContext` and
   `discover_missions_with_warnings` directly), assert `DiscoveryContext` currently has **no**
   `org_roots` field (e.g. `assert "org_roots" not in DiscoveryContext.model_fields` or equivalent
   pre-fix probe).
2. Assert `_build_tiers` on a context with a `project_dir` set currently produces tiers named
   `["explicit", "env", "project_override", "project_legacy", "user_global", "project_config",
   "builtin"]` — no `"org"` tier present.

**Files**: `tests/next/test_internal_runtime_coverage.py`.

**Parallel?**: Yes, alongside drafting T021/T022/T023 (different file).

### Subtask T020 – Add `org_roots` field + `_build_tiers` insertion

**Purpose**: Implement FR-007.

**Steps**:
1. In `src/runtime/next/_internal_runtime/discovery.py`, add `org_roots: list[Path] =
   Field(default_factory=list)` to `class DiscoveryContext(BaseModel)`, mirroring the shape of the
   existing `builtin_roots` field.
2. In `_build_tiers(context)`, insert a new tuple `("org", <some origin label>, context.org_roots)`
   into the returned list, **immediately after** the `"project_legacy"` tuple and **before** the
   `"user_global"` tuple. Re-verify the live function body yourself — do not assume this prompt's
   line citations are still exact.
3. Confirm T019's test now shows the `"org"` tier present at the correct position, and that a
   fixture with `org_roots` populated is discovered with `selected=True` at tier `"org"` (User
   Story 3, Acceptance Scenario 1).

**Files**: `src/runtime/next/_internal_runtime/discovery.py`.

**Parallel?**: No — depends on T019.

### Subtask T021 – Populate `org_roots` in `runtime_bridge_io.py`'s `_build_discovery_context`

**Purpose**: Implement FR-008's first real wiring site — this is the construction site that
actually feeds Walk A's engine for `spec-kitty next` in production (both `get_or_start_run` and
`_start_ephemeral_query_run` build their `context` via this function and pass it into
`start_mission_run(context=...)`).

**Steps**:
1. In `src/runtime/next/runtime_bridge_io.py:_build_discovery_context(repo_root)`, add the lazy
   import `from charter.drg import resolve_org_roots` inside the function body.
2. Populate `org_roots=list(resolve_org_roots(repo_root))` (or equivalent) on the returned
   `DiscoveryContext(...)`, alongside the existing `project_dir=repo_root, builtin_roots=[...]`
   arguments.
3. No `try/except Exception` around the `resolve_org_roots(...)` call (same DEC-005 discipline as
   WP03).
4. Add/extend a test exercising `_build_discovery_context` directly (or via `get_or_start_run`)
   proving `org_roots` reflects an org-pack fixture's roots.

**Files**: `src/runtime/next/runtime_bridge_io.py`, `tests/runtime/test_bridge_io.py`.

**Parallel?**: No — depends on T020 (the field must exist for this to be meaningful).

### Subtask T022 – Wire the DEC-006 third site

**Purpose**: Implement FR-008's second real wiring site — `mission run <key>` must also see the
org tier, not just `spec-kitty next`.

**Steps**:
1. In `src/specify_cli/mission_loader/command.py:_build_discovery_context(repo_root)` (its own,
   independently-duplicated construction — do **not** try to make it call
   `runtime_bridge_io.py`'s version instead; its docstring explains this duplication is
   intentional, to avoid depending on a private surface), add the same lazy `charter.drg` import
   and populate `org_roots` the same way as T021.
2. Write a test exercising `run_custom_mission` (`mission_loader/command.py:73`) end-to-end with an
   org-pack fixture, confirming the mission is discovered at tier `"org"` — User Story 3,
   Acceptance Scenario 4 ("proving the third wiring site is live, not just the generic engine").
3. **This test MUST land inside `tests/unit/mission_loader/test_command.py` or
   `tests/integration/test_mission_run_command.py`** so it counts toward the mission-loader
   `>=90%` coverage gate — see the "Mission-loader coverage gate" note above. Verify this by
   running the actual coverage command the gate uses (check
   `.github/workflows/ci-quality.yml:1437-1462` for the exact invocation) and confirming your new
   code is exercised, not just present.

**Files**: `src/specify_cli/mission_loader/command.py`, `tests/unit/mission_loader/test_command.py`
and/or `tests/integration/test_mission_run_command.py`.

**Parallel?**: No — depends on T020, can proceed in parallel with T021 (different files).

### Subtask T023 – Insert org tier into `_runtime_template_key`'s `project_tiers` (Walk B)

**Purpose**: Implement FR-009.

**Steps**:
1. In `src/runtime/next/runtime_bridge_io.py:_runtime_template_key(mission_type, repo_root)`,
   locate the hand-rolled `project_tiers: list[list[Path]]` construction (currently 5 entries:
   explicit, env, `.kittify/overrides/missions`, `.kittify/missions` (project-legacy),
   `_project_config_pack_paths(repo_root)` — re-verify the live order/count yourself).
2. Insert a new entry for the org tier **immediately after** the `.kittify/missions`
   (project-legacy) entry, sourced via `resolve_org_roots(repo_root)` (either by calling it
   directly with the same lazy `charter.drg` import, or by reusing `context.org_roots` from T021's
   populated `_build_discovery_context(repo_root)` call already present earlier in this function —
   pick whichever avoids a duplicate `resolve_org_roots` call and document which you chose).
3. Confirm an org-pack `mission.yaml` now resolves over the built-in `mission-runtime.yaml` for a
   mission type the org pack also ships (User Story 3, Acceptance Scenario 2 — SC-003 part 2).

**Files**: `src/runtime/next/runtime_bridge_io.py`, `tests/runtime/test_bridge_io.py`.

**Parallel?**: No — depends on T021 (if reusing its populated context) or can be independent if
calling `resolve_org_roots` directly; either way, do this after T020 so the vocabulary (`"org"`
tier concept) is established.

### Subtask T024 – Precedence test (Acceptance Scenario 3)

**Purpose**: Prove project/legacy still outranks org in both walks, not just that org exists.

**Steps**:
1. Using the org-pack fixture from earlier subtasks, additionally place a
   `.kittify/missions/<m>/mission.yaml` project-legacy file for the same mission key.
2. Assert the project-legacy file wins over the org-pack file in **both** Walk A
   (`discover_missions_with_warnings`) and Walk B (`_runtime_template_key`) — position parity of
   precedence, not just tier existence.

**Files**: `tests/next/test_internal_runtime_coverage.py`, `tests/runtime/test_bridge_io.py`.

**Parallel?**: No — depends on T020 and T023.

### Subtask T025 – Position-parity test (NFR-004/SC-008)

**Purpose**: The single test that actually catches drift between WP03's template-resolver org tier
and this WP's FSM org tier — not code review alone.

**Steps**:
1. Write one parametrized test asserting the org tier sits at the **identical relative position**
   (immediately after project/legacy, immediately before machine-global) across all four sites:
   `doctrine/resolver.py`, `specify_cli/runtime/resolver.py`, FSM Walk A, FSM Walk B.
2. This test is **only meaningfully green once WP03's FR-003/FR-004 have also landed** — if you are
   implementing this WP before WP03 (no hard dependency edge forces WP03 first, per `tasks.md`'s
   Dependency & Execution Summary), this test will fail on the WP03 side. Flag this explicitly in
   your Activity Log if you hit it, and confirm with the orchestrator whether WP03 should land
   first before you finish this subtask.

**Files**: place this in whichever test module most naturally imports all four sites — a new
focused test function is acceptable in `tests/next/test_internal_runtime_coverage.py` or
`tests/runtime/test_bridge_io.py`, whichever already imports the relevant symbols with less
friction.

**Parallel?**: No — do this last, after T020-T024.

### Subtask T026 – NFR-001/SC-004 regression test (FSM side)

**Purpose**: Prove the fail-soft guarantee holds on the FSM discovery side too, mirroring WP03's
T017 for the template side.

**Steps**:
1. Write a regression test proving a malformed `.kittify/config.yaml` still resolves built-in FSM
   discovery (both Walk A and Walk B) with zero org roots contributed, both before and after this
   WP's change (pre-existing property per DEC-005 — a guard, not a delta).

**Files**: `tests/next/test_internal_runtime_coverage.py` and/or `tests/runtime/test_bridge_io.py`.

**Parallel?**: No — do this after the core wiring (T020-T023) lands.

## Test Strategy

```bash
pytest tests/next/test_internal_runtime_coverage.py tests/runtime/test_bridge_io.py -q
pytest tests/unit/mission_loader/test_command.py tests/integration/test_mission_run_command.py -q
```
`src/doctrine/*` and `src/runtime/next/*` are enforced diff-coverage critical paths
(`.github/workflows/ci-quality.yml:3349`, `--fail-under=90` on changed lines) — FR-007, FR-008
(partially), FR-009 fall under this gate. `src/specify_cli/mission_loader/command.py` falls under
the separate, always-enforced mission-loader-coverage job (see above).

## Risks & Mitigations

- **Three wiring sites, not two** — the easiest mistake is fixing only the two sites an earlier,
  informal research pass named and missing `mission_loader/command.py`, leaving `mission run <key>`
  blind to the org tier while `spec-kitty next` sees it. T022 exists specifically to catch this.
- **File collision with WP06** — see the callout at the top of this prompt. Do not run this WP
  concurrently with WP06.
- **NFR-003 compliance** — no automated gate; your PR description must state review-based
  confirmation explicitly, naming #3522.

## Review Guidance

A reviewer should confirm:
1. All three wiring sites are populated (T021, T022, T023) — grep for `resolve_org_roots` calls
   across the three files to confirm.
2. The PR description explicitly states NFR-003 compliance was confirmed by manual review, names
   #3522, and does not rely on "CI is green" as proof.
3. T022's mission-loader test actually lands where the coverage gate collects from — run the gate's
   real command locally if unsure, do not assume placement is correct from the file path alone.
4. T025's position-parity test names all four sites and is either green (if WP03 already landed) or
   explicitly flagged as pending WP03 in the Activity Log.
5. No `try/except Exception` wraps any `resolve_org_roots(...)` call.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-08-17T00:02:22Z – system – Prompt created.

## Regression safety — NFR-005 / SC-007, and it is not optional

**A project with no org pack configured must behave byte-identically to before.** That is the
overwhelmingly common case, it is the one nobody wrote this mission about, and a regression there
would break every existing user of the tool to serve a feature none of them use yet.

This work package inserts a new tier into a live resolution path, so it owns that risk directly.
Before finishing, prove it: resolve the same asset in a project with **no** `doctrine.org.packs`
entries, before and after your change, and show the winning tier and resolved path are unchanged.
A sibling work package (WP01) carries the same duty as its own subtask — follow that shape.

`resolve_org_roots` returns an empty list when nothing is configured, so the new tier should be a
no-op rather than an error path. Show that it is, rather than assuming it.
