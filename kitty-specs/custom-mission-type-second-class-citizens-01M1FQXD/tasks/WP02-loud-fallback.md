---
work_package_id: WP02
title: '#3831 loud fallback — CLI-visible signal when mission-type resolution falls back to software-dev'
dependencies: []
requirement_refs:
- FR-004  # descoped — traceability only, NOT implemented; see plan.md §"#3831 Split Verdict" and WP02 T006
- FR-005
- NFR-002
planning_base_branch: fix/custom-mission-type-second-class-3830
merge_target_branch: fix/custom-mission-type-second-class-3830
branch_strategy: Planning artifacts for this mission were generated on fix/custom-mission-type-second-class-3830; this mission ships as a single branch/one PR onto that existing branch (topology single_branch) — completed changes must merge back into fix/custom-mission-type-second-class-3830, never a dependency-specific or per-WP branch.
base_branch: kitty/mission-custom-mission-type-second-class-citizens-01M1FQXD
base_commit: 979b31591312ae46ed9556c6c0a93b04717783f3
created_at: '2026-09-02T11:26:35.297497+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Loud fallback
history:
- timestamp: '2026-09-02T00:00:00Z'
  agent: system
  action: Prompt generated via spec-kitty agent mission finalize-tasks
authoritative_surface: src/specify_cli/mission.py
create_intent:
- tests/specify_cli/cli/commands/test_mission_type_current_fallback_signal.py
execution_mode: code_change
owned_files:
- src/specify_cli/mission.py
- src/specify_cli/cli/commands/mission_type.py
- tests/specify_cli/cli/commands/test_mission_type_current_fallback_signal.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 – #3831 loud fallback

## Why this WP exists

`get_mission_for_feature`'s existing `warnings.warn` fallback (`mission.py:802`) already
signals *something* when a mission type isn't found and the loader defaults to
`software-dev` — it just doesn't reach a normal operator. The one CLI call site,
`mission_type.py`'s `current` command (`current_cmd`, the `get_mission_for_feature` call at
line 190), already has a loud CLI-error pattern for the two sibling exceptions raised from
the same `try` block right next to it: `console.print(f"[red]Error:[/red] {exc}")` for
`MissionNotFoundError` (line 194) and `console.print(f"[red]Failed to load active
mission:[/red] {exc}")` for `MissionError` (line 197), both via the shared
`specify_cli.cli.console.console` rich console already imported into that module.

This WP implements **FR-005 only** (NFR-002 non-regression comes with it). **FR-004 is
mapped to this WP for traceability only, not implementation** — the org-tier lookup is
descoped per the #3831 SPLIT verdict (`plan.md` §"#3831 Split Verdict", `research.md` §R3).
Do not implement FR-004 here or anywhere else in this mission; T006 below is a
documentation-only subtask that records the descope and the tracked follow-up issue so
FR-004 is honestly accounted for rather than silently dropped or falsely marked
implemented. See `plan.md` §Architecture — Seam Mapping's FR-005 elaboration for the full
binding reasoning on FR-005 itself — do not re-derive it.

**Scope boundary, binding**: `acceptance/__init__.py:1206` and `core/worktree.py:664` (the
other two `get_mission_for_feature` call sites) are explicitly **out of scope** for the
loud-CLI-surface half of this fix — they are not CLI command modules, have no console
object today, and inventing one for them is out of scope for FR-005. They keep receiving
the unchanged `warnings.warn` signal exactly as before. `mission.py`'s own `warnings.warn`
stays exactly as it is today for every caller — this fix adds a loud *surface* only at the
one CLI call site.

**Sequencing reconciliation (`wps.yaml` intentionally leaves `dependencies: []` here)**:
`plan.md` §Suggested Work Package Sequencing states mission-wide that "the campsite-clean
comment fix precedes all three" WPs. That intent is satisfied by WP01's T001 alone, not by
a cross-WP dependency edge on this WP: `plan.md` §Campsite-Clean Scope found zero
qualifying campsite-clean debt in this WP's own file set (`mission.py`,
`mission_type.py`) — there is no stale comment or debt here for a campsite-clean step to
fix, so a `dependencies: ["WP01"]` edge would force this WP to wait on the whole of WP01
(T001–T007) for no file-level reason, contradicting `plan.md`'s explicit framing of these
three WPs as independent and parallelizable. **Operational instruction, binding**: because
this mission ships as a single branch/one PR (`fix/custom-mission-type-second-class-3830`,
topology `single_branch` — see frontmatter above) and nothing else enforces commit order on
that shared branch, whoever dispatches or implements this WP must confirm WP01's T001 (the
campsite-clean comment commit correcting the stale `runtime_bridge_composition.py`/
`runtime_bridge.py` comments) has already landed on
`fix/custom-mission-type-second-class-3830` before starting this WP's own commits.

## Subtasks

### T001 — RED-FIRST repro: FR-005 (silent fallback, capture real CLI output)

Through the pre-existing entry point (`spec-kitty mission-type current` / `current_cmd`,
not a white-box unit call): drive it against a mission whose type is not found so
`get_mission_for_feature` falls back to `software-dev`. Reproduce, live, that today's
signal is only visible via `pytest.warns` — capture the command's **actual stdout/stderr
under default warning filters** (not `pytest.warns` alone) and confirm no operator-visible
signal is present today. This is the evidence bar SC-004 itself states — `pytest.warns`
alone only proves the warning is *raised*, not that an operator would ever see it.

### T002 — Implement the loud CLI-visible surface

At `mission.py`: expose the already-known fallback fact (whether by capturing the existing
warning around the one `get_mission_for_feature` call, or by `mission.py` exposing the
fallback fact alongside its unchanged `warnings.warn` — an implementation-level choice, not
a plan-level one). `mission.py`'s own `warnings.warn` at line 802 stays exactly as it is
today. At `mission_type.py`'s `current_cmd`: when the call at line 190 falls back, print a
loud message through the same `console` object already used for the two sibling exceptions
at lines 194/197, reusing that exact pattern (do not invent a new console/logging bridge).

### T003 — Tests proving the signal is present and absent (both directions)

In the new test file `tests/specify_cli/cli/commands/test_mission_type_current_fallback_signal.py`:
- Capture real CLI stdout/stderr under default warning filters for `current_cmd` when the
  fallback fires — confirm the loud signal is now present (per SC-004's evidence bar, same
  method as T001).
- Confirm the signal is **absent** when the fallback does not fire (mission type resolves
  normally) — this is the other direction NFR-005's non-vacuity discipline requires applied
  here: proving the signal can be both present and absent, not just proving it can appear
  once.

### T004 — NFR-002 non-regression proof

Confirm mission **selection** is unchanged by this fix — the same mission is resolved
before and after, only the fallback's visibility changes. `warnings.warn`'s own behavior
and the two out-of-scope call sites (`acceptance/__init__.py:1206`, `core/worktree.py:664`)
are unaffected — add/confirm a regression test if none already pins this.

### T005 — Gate run

Per `plan.md` §Gate Set:
- `make ruff/lint` on every file this WP touches.
- Targeted pytest: the mission-loader-relevant suites under `tests/specify_cli/` (test
  path, not the misleadingly-named `mission-loader-coverage` CI job — that job covers
  `src/specify_cli/mission_loader/`, a distinct package that does not contain
  `get_mission_for_feature`; the actual relevant coverage collector for `mission.py` is
  `fast-tests-missions`, no numeric floor).
- No diff-coverage numeric floor applies to `mission.py`/`mission_type.py`; new tests are
  still required by the charter's every-new-branch-needs-tests rule.
- Validate any `patch()` targets used in new/changed tests per the repo's patch-target
  hygiene gate.
- Before attributing any red to this WP, classify it against #3284's known-red baseline (23
  failures + 2 errors) and the #3283 shared test-venv lock — run the same test against
  `main`/the merge-base first. A red not covered by #3284 gets filed as its own GitHub issue
  (with the exact command, failure summary, and why it's believed pre-existing) before being
  treated as baseline — never silently waved through.

### T006 — Document the FR-004 descope (traceability only, no code)

FR-004 (org-tier lookup in `_mission_path_by_name`/`get_mission_for_feature`) is mapped to
this WP's `requirement_refs` for FR-coverage traceability only — spec.md declares it
conditionally ("IF the plan-phase investigation... finds the legacy `Mission` schema and
the org-tier `MissionType` schema compatible... If incompatible, this FR is descoped"), and
`plan.md`/`research.md` §R3 record the SPLIT verdict: incompatible, so FR-004 is descoped
from this mission. Do not write any org-tier-lookup code under this subtask. Instead:

- Confirm (do not re-litigate) `research.md` §R3's tracked-follow-up description: title
  "Bridge the legacy `Mission`/`mission.yaml` schema to the org-tier `MissionTypeProfile`
  system for `_mission_path_by_name`/`get_mission_for_feature`", scoped to resolving the
  three-schema reconciliation problem (legacy `MissionConfig`, org-tier
  `MissionTypeProfile`/`expected-artifacts.yaml`, `mission-runtime.yaml`'s independent step
  schema), reusing `resolve_existing_org_roots`/the existing org-roots precedence
  convention per C-002 — not a third org-tier-walking mechanism.
- This mission does **not** file that follow-up issue (per `research.md` §R3 — filing is
  left to a human/later mission). This subtask's only deliverable is making sure the
  descope is traceable: this WP file's own text (above) and the PR body's `Refs #3831`
  (never `Closes #3831` for a partial fix, per the SPLIT verdict).
- Confirm the follow-up is **not** folded into #2660 (different scope, per spec.md's
  "Relationship to #2660" section, carried forward unchanged).

## Definition of Done

- FR-005: the fallback is loud and CLI-visible at `current_cmd`, reusing the existing
  console pattern; `mission.py`'s `warnings.warn` is unchanged; the two non-CLI call sites
  are untouched.
- FR-004 (org-tier lookup) is **not** implemented in this WP — it is descoped per the
  SPLIT verdict; do not add it under the guise of "while I'm in here."
- Both directions proven (T003): signal present when fallback fires, absent when it
  doesn't — captured via real CLI stdout/stderr, not `pytest.warns` alone.
- NFR-002: mission selection itself is unchanged (T004).
- Gate Set items (T005) all green, or every red explicitly classified against #3284 with a
  filed issue for anything new.
