---
affected_files: []
cycle_number: 1
mission_slug: charter-mediated-doctrine-selection-01KRTZCA
reproduction_command:
reviewed_at: '2026-05-17T18:25:17Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP08
---

# WP08 Review Feedback — Cycle 1 (REJECT)

**Mission:** `charter-mediated-doctrine-selection-01KRTZCA`
**WP:** WP08 — Mission-Type Profiles
**Reviewer:** reviewer-renata (claude:opus-4-7)
**Commit reviewed:** `363070cd` ("feat(WP08): mission-type governance profiles (4 shipped YAML + charter.mission_type_profiles loader)")

---

## Verdict: REJECT — BLOCKER

T046 ("Wire `resolve_governance` into the mission-context pipeline") is **not implemented**. The new `charter.mission_type_profiles.resolve_governance` function is **dead code**: it has zero call sites anywhere in `src/`. The 14 ATDD tests at `tests/missions/test_mission_type_profile_resolution.py` exercise the function directly, which is not the same as wiring it into the runtime prompt pipeline.

This is the textbook "no live caller" anti-pattern flagged by the `spec-kitty-mission-review` skill: a new module + full tests + zero callers in production code paths = the feature does not exist at runtime, regardless of test quality.

---

## Evidence

### 1. Diff scope — `charter/context.py` (and any wiring entry-point) is NOT in the WP08 diff

```
src/charter/mission_type_profiles.py                                | 370 +++++
src/doctrine/missions/documentation/governance-profile.yaml         |  23 +
src/doctrine/missions/plan/governance-profile.yaml                  |  22 +
src/doctrine/missions/research/governance-profile.yaml              |  22 +
src/doctrine/missions/software-dev/governance-profile.yaml          |  22 +
5 files changed, 459 insertions(+)
```

No edits to `src/charter/context.py`, `src/specify_cli/next/prompt_builder.py`, `src/specify_cli/cli/commands/agent/action.py`, `src/specify_cli/runtime/`, or any other entry-point that builds the implement prompt.

### 2. Live-caller verification — zero hits

```bash
$ rg "mission_type_profiles" src/
src/charter/mission_type_profiles.py:# ``src/charter/mission_type_profiles.py`` lives 2 dirs deep ...
src/doctrine/missions/plan/governance-profile.yaml:# Schema: `charter.mission_type_profiles.MissionTypeProfile`
src/doctrine/missions/research/governance-profile.yaml:# Schema: `charter.mission_type_profiles.MissionTypeProfile`
src/doctrine/missions/software-dev/governance-profile.yaml:# Schema: `charter.mission_type_profiles.MissionTypeProfile`
src/doctrine/missions/documentation/governance-profile.yaml:# Schema: `charter.mission_type_profiles.MissionTypeProfile`
```

Every match is either the module's own docstring or a YAML schema-pointer comment. **No `import` statement, no function call, anywhere in `src/`.** The module is not even re-exported from `src/charter/__init__.py`.

### 3. Namespace collision compounds the problem

There are now **two** functions named `resolve_governance` in the codebase:

| Location | Signature | Callers in `src/` |
|---|---|---|
| `charter.resolver.resolve_governance` (pre-existing) | `(repo_root, *, tool_registry=..., fallback_template_set=...) -> GovernanceResolution` | `charter/compact.py`, `specify_cli/runtime/doctor.py`, `specify_cli/next/prompt_builder.py` |
| `charter.mission_type_profiles.resolve_governance` (NEW, WP08) | `(repo_root, feature_dir) -> GovernancePayload` | **0** |

Signatures differ (the new one is not a drop-in), the return types differ, and the new function is never re-exported from `charter/__init__.py`. A future maintainer reading `from charter import resolve_governance` will see only the resolver-flavoured version and have no clue the mission-type-scoped one exists.

### 4. T046 is unambiguous

Per `kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/tasks/WP08-mission-type-profiles.md`:

> ### T046 — Wire `resolve_governance` into mission-context pipeline
> Identify the call site where the mission's governance payload is built for the implement prompt (today: `charter.context.build_charter_context` consumed by `runtime` or by `agent action implement`). **Insert a `resolve_governance` call that runs first, contributes its profile selections + activations to the union, and produces the final payload.**

The implementer's defense quoted only the second sentence ("The exact wiring point is implementation detail; the test assertion is the contract"). That sentence narrows *where* to insert the call; it does **not** waive the requirement to insert one. The first sentence is the deliverable, and it was skipped.

The implementer notes that `charter/context.py` is not in `owned_files`. That is true and does not exempt T046 — every other task in this mission (WP04, WP05, WP06) extended modules outside the strict `owned_files` list when the task contract required it (e.g., WP04 wired `build_charter_context`, WP06 extended `OrgCharterPolicy`). If `owned_files` blocked T046, the work package should have been bounced back during planning, not silently shipped with the wiring stripped out.

### 5. The FR-011 ATDD passes — but on synthetic input, not the live pipeline

`test_resolve_governance_picks_documentation_profile_for_documentation_mission` calls `resolve_governance(...)` directly. The assertion that "documentation missions don't get `software-dev-default`" is satisfied **only** if a future caller invokes this exact function. Today no caller does, so a real documentation mission flowing through the implement prompt pipeline is still routed through `charter.resolver.resolve_governance` → `software-dev-default` fallback, exactly the regression FR-011 / journey 4 was meant to prevent.

---

## What's right (keep these on the next cycle)

- 4 governance-profile.yaml files are schema-valid, each declares its own `mission_type`, all live under `src/doctrine/missions/<type>/`.
- `software-dev/governance-profile.yaml` preserves `template_set: software-dev-default` for back-compat with the 23-test ATDD at `tests/specify_cli/next/test_wp_prompt_governance_contract.py`. The other three correctly leave `template_set: null` so the FR-011 leak is impossible *if and when* the resolver is actually called.
- `UnknownMissionTypeError(ValueError)` is correctly raised with the unknown `mission_type` verbatim and a remediation hint pointing at `src/doctrine/missions/<type>/governance-profile.yaml` and `.kittify/charter/governance.yaml`.
- `MissionTypeProfile` uses `model_config = ConfigDict(extra="forbid")` so typos surface at load time.
- The 14 ATDD assertions at `tests/missions/test_mission_type_profile_resolution.py` are green.
- Layer rule clean: no `specify_cli` imports in `src/charter/mission_type_profiles.py`; `charter → doctrine` direction respected via filesystem-relative `_DOCTRINE_MISSIONS_ROOT`.

These are real deliverables and they should not be redone — just keep them and add the wiring.

---

## Required Fix (for cycle 2)

1. **Pick an entry-point and insert the call.** The two viable wiring points based on existing usage of the *other* `resolve_governance`:
   - **Preferred:** `src/specify_cli/next/prompt_builder.py` — already imports `from charter.resolver import resolve_governance`. Add a *first-pass* call to `charter.mission_type_profiles.resolve_governance(repo_root, feature_dir)` to obtain the mission-type-scoped `GovernancePayload`, then union its selections with the rest of the resolution before the existing `resolve_governance` runs. This is the prompt the implementer-agent actually consumes.
   - **Alternative:** `src/charter/context.py::build_charter_context`. If you take this route, `build_charter_context` must accept a `feature_dir` (today it works at repo-root scope) so the mission-type lookup has a meta.json to read.

2. **Resolve the namespace collision.** Two viable options:
   - Rename the new function to something unambiguous (e.g., `resolve_mission_type_governance`) so a future `from charter import resolve_governance` is unambiguous.
   - Or re-export both from `charter/__init__.py` with distinct names and add an integration test that asserts the mission-type-scoped one is invoked first.

3. **Add an integration test that proves the wiring is live.** A unit test of `resolve_governance` is necessary but not sufficient. Add a test in `tests/integration/` (or extend `tests/specify_cli/next/test_wp_prompt_governance_contract.py`) that:
   - Stages a fixture mission with `meta.json: {"mission_type": "documentation"}`.
   - Invokes the actual prompt-build entry-point (`prompt_builder.build_prompt(...)` or equivalent, **not** `resolve_governance` directly).
   - Asserts the resulting prompt text **does not** contain `software-dev-default`.

   That is the only way to prove FR-011 / journey 4 holds in production, not just in a unit-test sandbox.

4. **Update the implementer's WP report** to drop the "intentionally NOT modified" defense and document the actual wiring point chosen.

---

## Reviewer note on scope

This rejection is narrow: only T046 (wiring) and a follow-up integration test are missing. T041, T042–T045, and T047 are all green. Cycle 2 should be a small, focused diff (likely <50 lines in `prompt_builder.py` or `context.py` plus one integration test) on top of the existing commit, not a re-do.

— reviewer-renata
