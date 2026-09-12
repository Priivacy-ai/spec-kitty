---
work_package_id: WP03
title: Org tier in both template resolvers
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-004
planning_base_branch: up-org-template-fsm
merge_target_branch: up-org-template-fsm
branch_strategy: Planning artifacts for this mission were generated on up-org-template-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into up-org-template-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Core defect fix
history:
- at: '2026-08-17T00:02:22Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/doctrine/resolver.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/resolver.py
- src/specify_cli/runtime/resolver.py
- tests/doctrine/test_resolver.py
- tests/runtime/test_resolver_unit.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Org Tier in Both Template Resolvers

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this
prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` and `authoritative_surface: src/doctrine/resolver.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review.
Address every feedback item and update the Activity Log as you go.

---

## ⚠️⚠️ MANDATORY PREREQUISITE — READ BEFORE TOUCHING ANY CODE

**WP01 must already be merged/approved before you start this WP.** This is not a formality — it is
a load-bearing ordering constraint from `plan.md`'s Implementation Concern Map:

> "IC-01 is its own concern and is a hard prerequisite for IC-03 (the org tier cannot be added to
> the `specify_cli` resolver in a way that agrees with the doctrine resolver until the two
> `_resolve_asset` tier-1 probes already agree)."

Concretely: `specify_cli/runtime/resolver.py:_resolve_asset` did not have a mission-scoped
override probe at tier 1 before WP01. `doctrine/resolver.py:_resolve_asset` did. If you add an org
tier (this WP's job — tier 3, between LEGACY and GLOBAL_MISSION) to both modules **while their tier
1 still disagrees**, you bake the existing disagreement in at a *higher* position than before — the
mission would ship an org tier on top of a still-forked foundation, compounding rather than fixing
the drift `plan.md` identifies as the mission's root cause.

**Before writing any code in this WP**: verify WP01 actually landed by confirming
`specify_cli/runtime/resolver.py:_resolve_asset` now has the mission-scoped override probe (it
should check `.kittify/overrides/missions/{mission}/{subdir}/{name}` before the global
`.kittify/overrides/{subdir}/{name}` fallback — the same shape `doctrine/resolver.py` already has).
If it does not, stop and flag this instead of proceeding — do not implement WP03's org tier against
an unconverged foundation, even if the dependency-gate technically let you claim this WP.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

This WP is **IC-03** from `plan.md`'s Implementation Concern Map — the mission's core defect fix.
It adds the org tier, sourced from `resolve_org_roots`, at the identical relative position (between
`LEGACY` and `GLOBAL_MISSION`) in **both** `doctrine/resolver.py` and
`specify_cli/runtime/resolver.py`'s `_resolve_asset` and `resolve_mission` functions.

**Success criteria** (per `plan.md`'s Verification Design table — the tier the after-state must
name, not merely "a passing test"):

- **FR-003**: `doctrine.resolver._resolve_asset` resolves an org-pack `spec-template.md` at
  `tier == ResolutionTier.ORG` (before this WP: falls through to `PACKAGE_DEFAULT`).
- **FR-004**: `specify_cli.runtime.resolver._resolve_asset` resolves the identical fixture at
  `tier == ResolutionTier.ORG` **through the production `resolve_configured_template` call**
  (before this WP: falls through to `PACKAGE_DEFAULT`).
- **FR-005**: both modules' `resolve_mission` functions resolve an org-pack `mission.yaml` at
  `tier == ResolutionTier.ORG`, same relative position as the template case.

## Context & Constraints

Read before starting:
- `.kittify/charter/charter.md` — governing charter.
- `kitty-specs/up-org-template-fsm-01M06F9K/spec.md` — DEC-001 through DEC-005, User Story 1
  (with its exact Independent Test), FR-003, FR-004, FR-005, SC-001.
- `kitty-specs/up-org-template-fsm-01M06F9K/plan.md` — IC-03's Purpose/Risks; Plan-Time
  Verification's citations.

**This mission is dogfooded inside spec-kitty's own repository — a PUBLIC repo based on `main`.**
No host paths, no usernames, no absolute local paths in any committed file — sweep your diff before
finishing.

### Three things that cost a round if rediscovered

1. **Use `charter.drg.resolve_org_roots` via the existing lazy-import pattern for the
   `specify_cli/runtime/resolver.py` half of this WP.** Five `src/specify_cli/**` call sites
   already do it — copy the exact shape, do not invent a new import style:
   - `src/specify_cli/cli/commands/charter/_layer_roots.py:16,31`
   - `src/specify_cli/cli/commands/_doctrine_asset.py:87,90`
   - `src/specify_cli/cli/commands/_doctrine_collect.py:239,339,497,946`
   - `src/specify_cli/cli/commands/profiles_cmd.py:106,108`
   - `src/specify_cli/invocation/org_profiles.py:63,66`

   **Never import `doctrine.*` directly from `specify_cli` or `runtime`.** A sibling PR was
   red-flagged by the architectural suite for exactly that on the same day this mission was
   specified, and had to route through this same facade. `doctrine/resolver.py`'s half needs **no
   facade** — it is already inside the doctrine layer and may import
   `doctrine.drg.org_pack_config.resolve_org_roots` directly, same as its sibling `doctrine.base`
   module.

2. **Do not wrap `resolve_org_roots` in `try/except Exception`.** `OrgPackSubdirEscapeError` and
   `OrgPackEnvVarUnsetError` (both `ValueError` subclasses, `src/doctrine/drg/org_pack_config.py:48,58`)
   are deliberately raised, with
   `tests/doctrine/test_org_pack_subdir.py::test_escape_is_not_swallowed_to_empty_registry`
   asserting they are not swallowed. `load_pack_registry` already fail-softs the
   malformed-YAML-config case internally (`org_pack_config.py:380-427`) — that is what satisfies
   the "a project could then no longer resolve the templates its repair commands need" concern, and
   it is pre-existing, not something you need to add a second `try/except` layer around. Wrapping
   `resolve_org_roots()` in a blanket `except Exception` would re-swallow the deliberate escape/env
   errors — a real regression against a tested security invariant, **while still passing this WP's
   own new tests** if you are not careful to also test that propagation directly (T017 below).

3. **`CharterTemplateResolver._tier_to_origin` needs an `ORG` entry** — this was WP02's job
   (FR-012), already landed by the time this WP starts. You do not need to touch
   `src/charter/template_resolver.py` in this WP.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

Implementation command (with dependencies):
```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Subtasks & Detailed Guidance

### Subtask T011 – Red-first `doctrine.resolver` org-tier test

**Purpose**: Prove the "before" state for FR-003/SC-001 (half A).

**Steps**:
1. In `tests/doctrine/test_resolver.py`, build a fixture: an org-pack directory containing
   `missions/software-dev/templates/spec-template.md`, activated via `doctrine.org.packs[].local_path`
   in `.kittify/config.yaml` (no project override).
2. Call `doctrine.resolver._resolve_asset("spec-template.md", "templates", project_dir,
   "software-dev")` (or the public `resolve_template` wrapper) and assert it currently falls through
   to `tier == ResolutionTier.PACKAGE_DEFAULT` (the built-in default), not the org-pack file.
3. Report the exact pre-fix result (path + tier) for the WP report.

**Files**: `tests/doctrine/test_resolver.py`.

**Parallel?**: Yes, alongside T013 (different module).

### Subtask T012 – Add org tier to `doctrine/resolver.py:_resolve_asset`

**Purpose**: Implement FR-003.

**Steps**:
1. In `src/doctrine/resolver.py:_resolve_asset`, add a same-layer direct import:
   `from doctrine.drg.org_pack_config import resolve_org_roots`.
2. Insert a new tier **between** the existing LEGACY check (tier 2) and the existing
   GLOBAL_MISSION check (tier 3, `~/.kittify/missions/...`) — re-verify the live tier ordering
   yourself before inserting, do not assume the line numbers this prompt cites are still current.
3. For each root returned by `resolve_org_roots(project_dir)`, probe
   `<org_root> / "missions" / <mission> / <subdir> / <name>`. First match wins (matching every
   other tier's first-match-wins semantics — `resolve_org_roots` itself already returns packs in
   declaration order, per `org_pack_config.py:458-466`; do not invent a new precedence rule for
   multiple org packs).
4. On a hit, return `ResolutionResult(path=candidate, tier=ResolutionTier.ORG, mission=mission)`.
5. On a miss (org root resolves but the file does not exist there), fall through to the next tier —
   no exception, matching every existing tier's behavior.
6. **No `try/except Exception` around the `resolve_org_roots(...)` call** — see Constraint #2
   above. If `OrgPackSubdirEscapeError`/`OrgPackEnvVarUnsetError` are raised, let them propagate.
7. Confirm T011's test now resolves at `tier == ResolutionTier.ORG`.

**Files**: `src/doctrine/resolver.py`.

**Parallel?**: No — depends on T011.

### Subtask T013 – Red-first production `resolve_configured_template` test

**Purpose**: Prove the "before" state for FR-004/SC-001 (half B) — User Story 1's literal
Independent Test, through the **production** lane, not `doctrine.resolver` directly.

**Steps**:
1. In `tests/runtime/test_resolver_unit.py`, build the identical org-pack fixture as T011 (same
   `local_path`, same `missions/software-dev/templates/spec-template.md` layout).
2. Call `resolve_configured_template("spec", project_dir, ctx)` with `mission_type="software-dev"`
   — the exact function `mission create` calls (`specify_cli/core/mission_creation.py:577` at the
   time this spec was written — re-verify the live call site if you need to trace it, but you do
   not need to touch `mission_creation.py` in this WP, it is an unchanged call site).
3. Assert it currently falls through to `tier == ResolutionTier.PACKAGE_DEFAULT`.

**Files**: `tests/runtime/test_resolver_unit.py`.

**Parallel?**: Yes, alongside T011.

### Subtask T014 – Add org tier to `specify_cli/runtime/resolver.py:_resolve_asset`

**Purpose**: Implement FR-004 — the production lane.

**Steps**:
1. In `src/specify_cli/runtime/resolver.py:_resolve_asset`, add the **lazy** import inside the
   function body (mirroring the existing lazy tier-5 pattern already in this file, and the five
   `specify_cli/**` call sites listed in Constraint #1 above):
   ```python
   from charter.drg import resolve_org_roots  # noqa: PLC0415 — lazy, mirrors existing pattern
   ```
2. Insert the org tier at the **same relative position** as T012 (between LEGACY and
   GLOBAL_MISSION), with identical probe/fallback logic: `<org_root> / "missions" / <mission> /
   <subdir> / <name>`, first-match-wins across org roots, no exception on a miss.
3. Same "no `try/except Exception`" constraint as T012.
4. Confirm T013's test now resolves at `tier == ResolutionTier.ORG` through the production
   `resolve_configured_template` call.

**Files**: `src/specify_cli/runtime/resolver.py`.

**Parallel?**: No — depends on T013, and depends on **WP01 already being merged** (see the
Mandatory Prerequisite section above).

### Subtask T015 – Mirror the org tier into `resolve_mission` (both modules)

**Purpose**: Implement FR-005 — mission-config resolution gets the identical guarantee templates
do.

**Steps**:
1. In both `doctrine/resolver.py:resolve_mission` and `specify_cli/runtime/resolver.py:resolve_mission`,
   insert the org tier at the same relative position: after the LEGACY tier, before the
   GLOBAL_MISSION tier (note: `resolve_mission`'s own tier numbering differs slightly from
   `_resolve_asset`'s — `resolve_mission` has 4 tiers total, with `GLOBAL_MISSION` as tier 3 and
   `PACKAGE_DEFAULT` as tier 4; re-verify the live tier structure yourself, do not assume this
   prompt's description is still exactly current).
2. Probe `<org_root> / "missions" / <name> / "mission.yaml"` for each root from `resolve_org_roots`.
3. Reuse the same import pattern as T012/T014 in each module (direct in `doctrine/resolver.py`,
   lazy `charter.drg` facade in `specify_cli/runtime/resolver.py`).
4. Add a parametrized test (in whichever of the two test files makes most sense — or both) that
   resolves an org-pack `mission.yaml` at `tier == ResolutionTier.ORG` in both modules, at the same
   relative position as T011/T013's template case.

**Files**: `src/doctrine/resolver.py`, `src/specify_cli/runtime/resolver.py`,
`tests/doctrine/test_resolver.py`, `tests/runtime/test_resolver_unit.py`.

**Parallel?**: No — depends on T012 and T014 both landing (needs both modules' `_resolve_asset`
org-tier pattern established first, to mirror the same shape into `resolve_mission`).

### Subtask T016 – Acceptance Scenario 2 test (project override still wins)

**Purpose**: Prove the org tier sits **below** the project override, not above it — User Story 1,
Acceptance Scenario 2.

**Steps**:
1. Using the same org-pack fixture as T011/T013, additionally place a project override at
   `.kittify/overrides/missions/software-dev/templates/spec-template.md`.
2. Assert the project override wins: `tier == ResolutionTier.OVERRIDE`, not `ORG`.

**Files**: `tests/doctrine/test_resolver.py` and/or `tests/runtime/test_resolver_unit.py`.

**Parallel?**: No — depends on T012/T014.

### Subtask T017 – NFR-001(b)/SC-004 regression test (fail-soft preserved)

**Purpose**: Prove the new org tier does not regress the pre-existing fail-soft/propagation
guarantees (DEC-005).

**Steps**:
1. Write a regression test proving a malformed `.kittify/config.yaml` (unreadable, invalid YAML, or
   invalid `doctrine.org.packs[]` shape) still resolves built-in templates through both
   `_resolve_asset` implementations, with **zero** org roots contributed — this should hold both
   before and after this WP's change (the property is pre-existing per DEC-005; this is a
   regression guard, not a before/after delta).
2. Separately, confirm (by direct assertion, not just by reading the code)
   `tests/doctrine/test_org_pack_subdir.py`'s existing "not swallowed" assertions for
   `OrgPackSubdirEscapeError`/`OrgPackEnvVarUnsetError` still pass **unmodified** after your change
   — run that file directly: `pytest tests/doctrine/test_org_pack_subdir.py -q`.

**Files**: `tests/doctrine/test_resolver.py` (new regression test); no edits to
`tests/doctrine/test_org_pack_subdir.py` (run it, do not modify it).

**Parallel?**: No — do this after T012/T014 land, to test against the real new code path.

### Subtask T018 – Docstring/prose sweep

**Purpose**: DIR-007 — keep docstrings honest about the tier count.

**Steps**:
1. Update `_resolve_asset` and `resolve_mission`'s docstrings in both modules to enumerate the
   now-6-tier chain (was 5-tier for `_resolve_asset`, was 4-tier for `resolve_mission` — the org
   tier adds one to each).
2. Grep this mission's touched files (and `docs/api/missions.md` if it documents the precedence
   chain) for stale `"5-tier"` prose and update it to `"6-tier"` where it now describes the chain
   this WP changed. Do not sweep unrelated files outside this WP's scope.

**Files**: `src/doctrine/resolver.py`, `src/specify_cli/runtime/resolver.py` (docstrings only);
`docs/api/missions.md` if it exists and documents this precedence chain (out of `owned_files` —
if you find it needs an edit, make a small, well-justified out-of-map edit with a one-line
rationale, per the mission's ownership rules).

**Parallel?**: No — do this last.

## Test Strategy

```bash
pytest tests/doctrine/test_resolver.py tests/runtime/test_resolver_unit.py tests/doctrine/test_org_pack_subdir.py -q
pytest tests/architectural/test_charter_sole_door_resolver_imports.py tests/architectural/test_runtime_charter_doctrine_boundary.py -q
```
`src/doctrine/*` is in the diff-coverage critical-path list (`--fail-under=90` on changed lines,
`.github/workflows/ci-quality.yml:3349`) — FR-003/FR-005's `doctrine/resolver.py` changes fall
under this gate. `src/specify_cli/runtime/resolver.py` (FR-004) does **not** — it still needs
focused unit tests per the Sonar new-code-coverage expectation, just without a numeric CI backstop.

## Risks & Mitigations

- **The single easiest mistake**: wrapping `resolve_org_roots()` in `try/except Exception` "for
  safety". Do not do this — see Constraint #2 above, and T017's explicit propagation test.
- **Position-parity risk**: this WP's org tier must land at the same relative position as WP04's
  FSM tiers. WP04 owns the cross-cutting parity test (NFR-004/SC-008) — it is not this WP's job to
  write that test, but this WP's insertion point must be correct for that later test to pass.
- **Prerequisite risk**: see the Mandatory Prerequisite section at the top of this prompt — do not
  skip verifying WP01 landed.

## Review Guidance

A reviewer should confirm:
1. WP01 was verifiably merged before this WP's changes were made (check git history / the
   mission-scoped probe exists in `specify_cli/runtime/resolver.py` before this WP's diff).
2. No `try/except Exception` wraps any `resolve_org_roots(...)` call in this diff.
3. `specify_cli/runtime/resolver.py`'s org-tier import is the lazy `from charter.drg import
   resolve_org_roots` form, not a direct `doctrine.*` import.
4. T011/T013's red-first failures are reported with the actual pre-fix tier
   (`PACKAGE_DEFAULT`), not just "it failed".
5. T016 proves org sits below project-override, above package-default — both directions checked.
6. T017's malformed-config regression test actually runs the malformed-config path, not just an
   empty-org-packs happy path.

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
