---
affected_files:
  - path: src/charter/mission_type_profiles.py
  - path: src/specify_cli/next/prompt_builder.py
  - path: tests/missions/test_mission_type_profile_resolution.py
  - path: tests/integration/test_mission_type_profile_live_wiring.py
cycle_number: 2
mission_slug: charter-mediated-doctrine-selection-01KRTZCA
reproduction_command: 'pytest tests/missions/test_mission_type_profile_resolution.py tests/integration/test_mission_type_profile_live_wiring.py tests/specify_cli/next/test_wp_prompt_governance_contract.py tests/integration/test_user_doctrine_artifact_lifecycle.py tests/integration/test_org_pack_artifact_lifecycle.py tests/charter/test_context_selection_render.py tests/charter/test_context_activation_render.py tests/architectural/test_artifact_selection_completeness.py tests/architectural/test_layer_rules.py tests/architectural/test_wp_prompt_build_latency.py'
reviewed_at: '2026-05-17T18:45:00Z'
reviewer_agent: claude:opus-4-7:reviewer-renata
verdict: approved
wp_id: WP08
---

# WP08 Review Feedback — Cycle 2 (APPROVE)

**Mission:** `charter-mediated-doctrine-selection-01KRTZCA`
**WP:** WP08 — Mission-Type Profiles
**Reviewer:** reviewer-renata (claude:opus-4-7)
**Commit reviewed:** `1058e21c` ("fix(WP08): wire resolve_mission_type_governance into prompt_builder (cycle 2)")

---

## Verdict: APPROVE

The cycle-1 BLOCKER (dead code — `resolve_governance` had zero callers in `src/`) is **closed**. Cycle-2 commit `1058e21c` ships a narrow, surgical fix that addresses exactly the rejection rationale without re-scoping. Cycle-1 substantive verdict on the underlying design (4 mission-type YAML profiles, `MissionTypeProfile` schema, `UnknownMissionTypeError` hard-fail, layer-rule compliance) stands and is preserved.

---

## Evidence

### 1. Cycle-2 delta is narrow (4 files, +271/-12)

```
src/charter/mission_type_profiles.py               |   8 +-
src/specify_cli/next/prompt_builder.py             |  50 +++++
tests/integration/test_mission_type_profile_live_wiring.py | 205 +++++++++++++++++++++
tests/missions/test_mission_type_profile_resolution.py     |  20 +-
```

No unrelated files touched. The cycle-1 substance (loader, YAMLs, hard-fail) is untouched except for the rename.

### 2. Rename complete — namespace collision resolved

- `resolve_governance` (the old name) appears **zero** times in `src/charter/mission_type_profiles.py`.
- `resolve_mission_type_governance` appears 3+ times in the module (public API name, `__all__`, docstring back-references).
- The bare name `resolve_governance` now unambiguously resolves to `charter.resolver.resolve_governance` (the pre-existing function), so the collision is gone.
- The cycle-1 ATDD test file references the new name only.

### 3. Live caller verification (CRITICAL — cycle-1 blocker)

```
$ rg "resolve_mission_type_governance" src/
src/charter/mission_type_profiles.py:    "resolve_mission_type_governance",
src/charter/mission_type_profiles.py:    ... (docstring back-references)
src/charter/mission_type_profiles.py:def resolve_mission_type_governance(repo_root: Path, feature_dir: Path) -> GovernancePayload:
src/specify_cli/next/prompt_builder.py:    resolve_mission_type_governance,
src/specify_cli/next/prompt_builder.py:    The mission-type resolver (``charter.mission_type_profiles.resolve_mission_type_governance``)
src/specify_cli/next/prompt_builder.py:        payload = resolve_mission_type_governance(repo_root, feature_dir)
```

**Hits OUTSIDE `src/charter/mission_type_profiles.py`:** 3 hits in `src/specify_cli/next/prompt_builder.py`. The dead-code blocker is closed.

### 4. Wiring is correct

`src/specify_cli/next/prompt_builder.py`:
- **Line 15–16:** Imports `resolve_mission_type_governance` and `UnknownMissionTypeError` from `charter.mission_type_profiles`.
- **Line 155:** `_build_wp_prompt` calls `_mission_type_governance_lines(repo_root, feature_dir)` FIRST.
- **Line 156:** Then calls `_governance_context(...)` (existing pipeline) — preserves the "runs first, contributes its selections to the union" cycle-1 directive.
- **Line 310–313:** `UnknownMissionTypeError` is explicitly **re-raised** (FR-011 hard-fail contract — no silent fallback to `software-dev-default`).
- **Line 314–315:** Generic `Exception` swallowed defensively so the downstream `charter.resolver.resolve_governance` can surface its own diagnostics. Defensible — the hard-fail surface (the only thing the FR-011 contract pins) is preserved.
- **Line 306–307:** When `feature_dir/meta.json` is absent, returns `None` (back-compat for the 23 pre-existing fixture tests in `test_wp_prompt_governance_contract.py` that predate WP08 wiring). The 23 tests stay green — confirmed below.

### 5. Integration test is a real end-to-end test

`tests/integration/test_mission_type_profile_live_wiring.py`:
- Module-level `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`.
- Stages a real fixture mission: writes `meta.json` with `{"mission_type": "documentation"}`, charter, WP file, lane manifest, real `git init`.
- Calls the **production entry point** `_build_wp_prompt(action="implement", ...)` — NOT the resolver directly.
- **Negative assertion (FR-011):** `"software-dev-default" not in prompt.lower()` — proves no leak.
- **Positive assertion (regression safety net):** `"Mission-Type Governance Profile: documentation" in prompt` — proves the new code path FIRED rather than the negative passing by coincidence.
- Both assertions pass with descriptive error messages that point future debuggers back to this review cycle.

### 6. All test sweeps green (92/92)

```
tests/missions/test_mission_type_profile_resolution.py ...... 14 passed
tests/integration/test_mission_type_profile_live_wiring.py ... 2 passed
tests/specify_cli/next/test_wp_prompt_governance_contract.py . 23 passed  (back-compat)
tests/integration/test_user_doctrine_artifact_lifecycle.py ... passed
tests/integration/test_org_pack_artifact_lifecycle.py ........ passed
tests/charter/test_context_selection_render.py ............... passed
tests/charter/test_context_activation_render.py .............. passed
tests/architectural/test_artifact_selection_completeness.py .. 3 passed
tests/architectural/test_layer_rules.py ...................... passed
tests/architectural/test_wp_prompt_build_latency.py .......... passed  (NFR-002)
TOTAL: 92 passed, 0 failed
```

### 7. Ruff clean

```
$ ruff check src/charter/mission_type_profiles.py src/specify_cli/next/prompt_builder.py \
             tests/missions/test_mission_type_profile_resolution.py \
             tests/integration/test_mission_type_profile_live_wiring.py
All checks passed!
```

### 8. Layer rule satisfied

```
$ rg "^from specify_cli" src/charter/mission_type_profiles.py
(no output)
```

The `charter` package does not depend on `specify_cli` — layer direction (`specify_cli -> charter`) is preserved.

---

## Carry-Forward from Cycle 1

The cycle-1 substantive verdict was: **the 4 mission-type YAML profiles, the `MissionTypeProfile` Pydantic schema, the `UnknownMissionTypeError` hard-fail surface, the layer-rule compliance, and the 14 ATDD tests at `tests/missions/test_mission_type_profile_resolution.py` are all APPROVED**. Cycle 2 leaves all of this intact (the only change to those artifacts is the rename `resolve_governance -> resolve_mission_type_governance`). No re-litigation required.

---

## Decision

**APPROVE.** Move `WP08` to `approved`.
