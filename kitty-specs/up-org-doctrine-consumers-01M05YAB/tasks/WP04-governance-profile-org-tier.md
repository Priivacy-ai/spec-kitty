---
work_package_id: WP04
title: Governance-profile org-tier threading
dependencies:
- WP01
requirement_refs:
- FR-004
- NFR-001
- NFR-002
planning_base_branch: pr/up-org-doctrine-consumers-01M05YAB
merge_target_branch: pr/up-org-doctrine-consumers-01M05YAB
branch_strategy: Planning artifacts for this mission were generated on pr/up-org-doctrine-consumers-01M05YAB. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/up-org-doctrine-consumers-01M05YAB unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
history:
- at: '2026-08-16T19:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/activation/mission_type_profiles.py
- tests/charter/test_mission_type_profiles.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Governance-profile org-tier threading

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## ⚠️ File-collision note (why WP05 depends on this WP)

**WP05 depends on this WP (WP04) purely because both edit
`src/charter/activation/mission_type_profiles.py` (and its test module,
`tests/charter/test_mission_type_profiles.py`) — a file collision, not a functional
dependency.** FR-004 (this WP) and FR-008 (WP05) are unrelated in behavior; `resolve_org_dirs`
(WP01) is the only thing WP05 actually needs from this WP's family of changes, and WP01 already
provides that directly. The dependency exists solely so the two WPs' `owned_files` don't
overlap while running concurrently — the finalizer exempts *dependency-ordered* (sequential)
pairs from its overlap check, which is why this works as a WP04→WP05 chain instead of true
parallel execution. **Do not treat this as evidence FR-008 needs anything from FR-004's
governance-slot logic** — it doesn't. If you are asked to "optimise" WP04/WP05 into parallel
work, refuse; that would produce two worktrees independently editing the same file with no
merge-ordering guarantee.

## Objective

Thread `org_dirs` through `_mission_type_profile_repository` → `MissionTypeProfileRepository.for_project`
so an org-tier `governance-profile.yaml` override is not silently invisible in the governance
text every `resolve_mission_type_context` call renders. This runs **eagerly** on every
mission-type context resolution (not deferred) — see the docstring context below for why that
matters.

## Context

### Dependency: WP01's `resolve_org_dirs`

Call `resolve_org_dirs(repo_root, "mission_types")` from `doctrine.drg.org_pack_config` (WP01).
Note the `subdir` value here is **`"mission_types"`**, different from WP02/WP03's
`"mission_step_contracts"` — this is not an `ArtifactKind` enum member (verified: no
mission-type member exists in `src/doctrine/artifact_kinds.py`'s `ArtifactKind`), which is
exactly why WP01's helper takes a plain `str` subdir rather than restricting to
`ArtifactKind.plural` values.

### Current code — `_mission_type_profile_repository` (`mission_type_profiles.py:1148-1168`)

```python
def _mission_type_profile_repository(
    repo_root: Path | None,
) -> MissionTypeProfileRepository:
    """Construct the overlay-aware profile repository.

    ``repo_root is None`` yields a **shipped-only** repository (built-in layer,
    no project overlay) — the shape used by the built-in resolution ATDD suite.
    A concrete ``repo_root`` wires the project overlay at
    ``.kittify/doctrine/mission_types/`` so per-type overrides ride the
    ``doctrine/base.py`` stack.
    ...
    """
    from charter.activation.mission_type_profile_repository import (
        MissionTypeProfileRepository,
    )

    if repo_root is None:
        return MissionTypeProfileRepository()
    return MissionTypeProfileRepository.for_project(repo_root)
```

`MissionTypeProfileRepository.for_project` **already accepts** `org_dirs: list[Path] | None =
None` (`src/charter/activation/mission_type_profile_repository.py:99-113`) — this is caller-side threading
only, exactly like FR-001. You are not modifying `MissionTypeProfileRepository` itself.

Change the `repo_root is not None` branch to:

```python
if repo_root is None:
    return MissionTypeProfileRepository()
from doctrine.drg.org_pack_config import resolve_org_dirs
return MissionTypeProfileRepository.for_project(
    repo_root, org_dirs=resolve_org_dirs(repo_root, "mission_types")
)
```

(Match the file's existing lazy-import style for `MissionTypeProfileRepository` — import
`resolve_org_dirs` the same way, or hoist both to a shared local import block if that reads
more naturally; either is fine as long as the existing "avoid a charter-internal import cycle"
rationale in the surrounding docstring stays true. Confirm no cycle is introduced — `doctrine`
sits below `charter` in the layer stack, so `charter → doctrine` is always a permitted
direction and should not need the lazy-import treatment for that reason alone, but match
existing style regardless for diff minimality.)

### The live call site this actually fixes — `_resolve_governance_slot` (`mission_type_profiles.py:766-825`)

You are not editing this function directly — it already calls
`_mission_type_profile_repository(repo_root)` at line 807, so your change to that function is
sufficient. But understand *why* this matters: `_resolve_governance_slot`'s own docstring
explains this "registration guard stays eager... there is no reason to defer it," and separately
that `provenance` is "computed **eagerly** here (`repo.get_provenance`), independent of the
governance union." Only the FR-013 type-grain/action-grain union is deferred via
`governance_thunk`. This means an org-tier override becomes visible on **every**
`resolve_mission_type_context` call for a registered type, not just when some lazy accessor is
invoked — which is exactly why D-004 (spec.md) calls this gap "live and reachable," not
theoretical.

### What you must NOT touch — `action_grain.py:220`

`charter/action_grain.py:220` is the **other** call site of
`_mission_type_profile_repository`-adjacent construction (it calls
`MissionTypeProfileRepository()` directly with no `repo_root`, hitting the built-in-only
branch). This is **deliberate** per the sibling mission `up-mission-type-seam-01KZY1JB`'s own
binding constraint: "`action_grain.py` deliberately stays built-in-only — it is a gate over
shipped content, not a resolution path." Do not widen it. T019 exists to guard against a future
regression here, not to change it now.

## Subtasks

### T017 — FR-004: thread `org_dirs` into `_mission_type_profile_repository`

Edit `_mission_type_profile_repository` (`mission_type_profiles.py:1148-1168`) as described
above.

### T018 — Regression test: org-tier governance override is visible (SC-006-adjacent, this mission's own measurement)

In `tests/charter/test_mission_type_profiles.py`, construct an org-pack
`<org_root>/mission_types/<type>/governance-profile.yaml` override (mirroring the flat-layout
fixture pattern from `_write_org_directive_fixture`,
`tests/charter/test_org_scan_dirs_activation_regression.py:62`, adapted for the
`mission_types` subdir and a `governance-profile.yaml` payload instead of a directive). Assert
`resolve_mission_type_context(...).governance_text` reflects the org override's content — not
the built-in baseline — for a registered mission type. This is a before/after measurement per
NFR-001: assert the built-in-only baseline text first (or via a control case with no org pack
configured), then assert it changes once the org file is added.

### T019 — Regression guard: `action_grain.py:220` stays untouched

Add or extend a test in `tests/charter/test_mission_type_profiles.py` (or find the existing
test covering `action_grain.py`'s built-in-only behavior, if one already exists — extend rather
than duplicate) confirming `action_grain.py`'s call path still resolves built-in-only even when
an org pack with a `mission_types` override is configured for the same project. This proves
your change to `_mission_type_profile_repository` did not accidentally widen
`action_grain.py`'s deliberately-narrower call site (it calls `MissionTypeProfileRepository()`
directly, not through your changed function, so this should already hold — this test exists to
make that fact durable against future refactors, not because you expect it to fail).

### T020 — Verify coverage and architectural gates locally

Run and confirm green:

```bash
pytest tests/charter/test_mission_type_profiles.py -v
pytest tests/architectural/test_layer_rules.py tests/architectural/ -k "sole_door" -q
```

`src/charter/activation/mission_type_profiles.py` is in the enforced critical-path `diff-cover
--fail-under=90` gate (`src/charter/*`). Per NFR-005, zero new allowlist/suppression entries
are permitted in the sole-door or layer-rule architectural suites — this WP introduces no new
cross-layer import direction (charter → doctrine is already established), so these gates should
pass unmodified; if either gate requires a new allowlist entry to pass, that is a signal
something is wrong with your import shape, not a signal to add the entry.

## Branch Strategy

Both planning and merge target are `pr/up-org-doctrine-consumers-01M05YAB`. Allocate via
`spec-kitty implement WP04` (depends on WP01 only). WP05 depends on this WP for file-collision
reasons (see the note above) — expect WP05 to start after this WP merges. This mission's
`meta.json` records `target_branch: main` while the actual planning/merge branch is
`pr/up-org-doctrine-consumers-01M05YAB` — a known mismatch; do not improvise around it if a
command refuses, flag it instead.

## Definition of Done

- FR-004 implemented: `_mission_type_profile_repository` threads `org_dirs` via WP01's helper
  with `subdir="mission_types"`.
- T018 proves the override is visible with a before/after measurement.
- T019 proves `action_grain.py:220` remains built-in-only.
- `pytest tests/charter/test_mission_type_profiles.py -v` green; architectural suites green
  with zero new allowlist entries.

## Risks / Reviewer guidance

- Low risk in isolation — this is a small, caller-side, single-function change (~10-15 LOC).
- The only material risk is the file collision with WP05 — confirm WP05's diff lands
  **after** this WP's, not concurrently, and that WP05's changes to
  `mission_type_profiles.py` touch `_resolve_expected_artifacts_slot` (a different function),
  not anything this WP changed.
- Confirm `action_grain.py:220` truly is untouched in your diff — this WP's scope is
  `_mission_type_profile_repository` only.
