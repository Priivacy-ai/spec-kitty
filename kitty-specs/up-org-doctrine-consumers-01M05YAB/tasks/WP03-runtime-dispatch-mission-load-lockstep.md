---
work_package_id: WP03
title: Runtime dispatch / mission-load lockstep + delegation surfacing
dependencies:
- WP01
requirement_refs:
- C-004
- FR-006
- FR-007
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: pr/up-org-doctrine-consumers-01M05YAB
merge_target_branch: pr/up-org-doctrine-consumers-01M05YAB
branch_strategy: Planning artifacts for this mission were generated on pr/up-org-doctrine-consumers-01M05YAB. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/up-org-doctrine-consumers-01M05YAB unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
history:
- at: '2026-08-16T19:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/runtime/next/runtime_bridge_composition.py
- src/specify_cli/mission_loader/command.py
- tests/runtime/test_bridge_composition.py
- tests/unit/mission_loader/test_command.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Runtime dispatch / mission-load lockstep + delegation surfacing

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## ⚠️ MANDATORY LOCKSTEP CONSTRAINT — READ BEFORE STARTING

**`src/specify_cli/mission_loader/command.py:237` (`_resolve_contract_refs`) and
`src/runtime/next/runtime_bridge_composition.py:284` (`_resolve_runtime_contract_for_step`)
MUST both be fixed in this single work package. Do not implement one and defer the other.**

(Note: the current on-disk line number for `_resolve_runtime_contract_for_step`'s `def` is
252, not 284 — the file has shifted slightly since spec authoring; the function itself, its
docstring, and its behavior are unchanged. Locate it by name, not by line number.)

Why this is non-negotiable: `_resolve_contract_refs`'s own docstring states explicitly "This
keeps loader semantics aligned with the runtime so an id that resolves here will resolve at
runtime too." If `_resolve_runtime_contract_for_step` (runtime dispatch) becomes org-tier-aware
and `_resolve_contract_refs` (mission-load validation) does not — or vice versa — a legitimate
org-tier `contract_ref` becomes **accepted at one point and rejected at the other**
(`MISSION_CONTRACT_REF_UNRESOLVED`). The mission's own spec (User Story 2) states this
explicitly: "A partial fix here... is worse than no fix — it converts a consistent 'always
invisible' into an inconsistent 'sometimes invisible,' which is harder to diagnose." A
uniformly-blind org tier is a known, debuggable limitation; an inconsistent one is a bug report
waiting to happen. Implement T011 and T012 together and prove both resolve identically (T013,
T014) before considering either done.

> **Tooling note**: this WP's frontmatter `requirement_refs` lists `FR-006`, not `FR-006a`, and
> omits `SC-003`/`SC-004` — not because they don't apply (they do; FR-006a is this WP's second
> lockstep half and SC-003/SC-004 are its measurements, both discussed throughout this prompt),
> but because `spec-kitty agent tasks map-requirements` rejects both shapes today: letter-suffixed
> `FR-NNNa` refs fail its `^(?:FR|NFR|C)-\d+$` format check (uppercases to `FR-006A`, then
> rejects — confirmed live during this mission's own task generation), and `SC-` is not a
> recognized prefix at all. This is a real, spec-declared requirement id (spec.md's own
> Requirement-id discipline explicitly lists "FR-001–008 (incl. FR-006a)") that the mapping
> tool cannot represent structurally — worth a follow-up fix, not something to route around by
> inventing a different id. Treat FR-006a as fully in-scope for this WP regardless of what the
> frontmatter field can hold.

## Objective

Three FRs land in this package: FR-006 (runtime dispatch resolves an org-tier `contract_ref`),
FR-006a (mission-load validation resolves the identical `contract_ref` identically), and FR-007
(surface previously-silently-discarded unresolved delegation candidates as a WARNING log — not
part of the lockstep pair functionally, but forced into this package because its edit site
shares a file with FR-006 — see the File-Collision Fold-In note below).

## Context

### Dependency: WP01's `resolve_org_dirs`

Both FR-006 and FR-006a call `resolve_org_dirs(repo_root, "mission_step_contracts")` from
`src/doctrine/drg/org_pack_config.py` (WP01) — the same helper and same `subdir` string WP02's
FR-001/FR-005 use. Do not re-implement it.

### FR-006 — current code (`runtime_bridge_composition.py`, `_resolve_runtime_contract_for_step`, currently at line 252)

```python
def _resolve_runtime_contract_for_step(
    *,
    repo_root: Path,
    run_dir: Path,
    mission: str,
    step_id: str,
) -> Any | None:
    ...
    try:
        from doctrine.missions.step_contracts import (
            MissionStepContractRepository,
        )
        ...
        template = _engine_adapter._load_frozen_template(run_dir)
    except Exception:
        return None

    from runtime.next import runtime_bridge as _rb  # noqa: PLC0415

    normalized = _rb._normalize_action_for_composition(step_id)
    for step in template.steps:
        if step.id != step_id and step.id != normalized:
            continue
        contract_ref = step.contract_ref.strip() if step.contract_ref else None
        if contract_ref:
            repository = MissionStepContractRepository(
                project_dir=repo_root
                / KITTIFY_DIR
                / "doctrine"
                / "mission_step_contracts"
            )
            return lookup_contract(contract_ref, repository)
        ...
```

Change the `MissionStepContractRepository(...)` construction to also pass
`org_dirs=resolve_org_dirs(repo_root, "mission_step_contracts")`. Import `resolve_org_dirs`
from `doctrine.drg.org_pack_config` — match this function's existing style of importing
`MissionStepContractRepository` lazily inside the `try` block (the file's docstring explains
this is deliberate: "``mission run`` and ``next`` normally execute in separate CLI
processes"). Confirmed reachable for any mission type, not just `software-dev` — verified in
this mission's spec authoring (D-002): `_should_dispatch_via_composition` is mission-generic,
despite a stale comment elsewhere claiming a hard guard on `mission == "software-dev"`. Do not
narrow your fix to only apply for `software-dev` based on that stale comment.

### FR-006a — current code (`mission_loader/command.py:204-260`, `_resolve_contract_refs`)

```python
def _resolve_contract_refs(
    *,
    mission_key: str,
    template: MissionTemplate,
    source_path: str,
    repo_root: Path,
) -> LoaderError | None:
    """Resolve every step's ``contract_ref`` against the on-disk repository.
    ...
    This keeps loader semantics aligned with the runtime so an id that resolves here will
    resolve at runtime too.
    """
    from charter.mission_steps import (
        MissionStepContractRepository,
    )

    repository: MissionStepContractRepository | None = None
    for step in template.steps:
        if step.contract_ref is None:
            continue
        if repository is None:
            repository = MissionStepContractRepository(
                project_dir=repo_root
                / ".kittify"
                / "doctrine"
                / "mission_step_contracts"
            )
        if repository.get(step.contract_ref) is None:
            return LoaderError(...)
    return None
```

Change the `MissionStepContractRepository(...)` construction to also pass
`org_dirs=resolve_org_dirs(repo_root, "mission_step_contracts")` — the **same call** FR-006
makes. Note this file imports `MissionStepContractRepository` from `charter.mission_steps`
(a different import path than FR-006's `doctrine.missions.step_contracts` — verify both paths
resolve to the same class before assuming this is a typo; if they are genuinely different
re-export paths for the same class, that's fine and pre-existing, not something to "fix" here).

### FR-007 — File-Collision Fold-In (why it's in this WP, and a scoping decision you must follow)

`_dispatch_via_composition` (FR-007's edit site, `runtime_bridge_composition.py:489`) lives in
the **same file** as `_resolve_runtime_contract_for_step` (FR-006's edit site). Under this
mission's `owned_files` pairwise-disjoint constraint, FR-007 cannot become an independent work
package without colliding with this WP's ownership of that file — so it is folded in here. This
is **not** a functional lockstep requirement (FR-007's WARNING logging works whether or not
FR-006 has landed) — it is purely a file-ownership consequence.

**Implementation scoping decision — read before you look at `data-model.md`:**
`data-model.md`'s Phase-1 design sketch shows FR-007 implemented as two new properties
(`has_unresolved_delegations`, `all_unresolved_candidates`) added to `StepContractExecutionResult`
in `src/specify_cli/mission_step_contracts/executor.py`. **Do not add those properties.**
`executor.py` is WP02's owned file, not this WP's, and WP02/WP03 both depend only on WP01 (they
are meant to be independently schedulable/parallel per plan.md's own sizing note) — adding a
property to a file owned by a concurrent, non-dependency-ordered WP would either collide at
merge time or force an undocumented WP03→WP02 dependency neither this WP's frontmatter nor
WP02's declares. Instead, implement FR-007 by iterating `result.steps` directly inside
`_dispatch_via_composition` — `StepContractStepResult.step_id` and
`.unresolved_candidates` already exist today (D-005; `executor.py` lines ~99-110, unchanged by
either WP) and are sufficient to build the exact WARNING contract C-3 specifies without
touching `executor.py` at all:

```python
for step in getattr(result, "steps", ()) or ():
    unresolved = getattr(step, "unresolved_candidates", ())
    if unresolved:
        logger.warning(
            "step %s (contract %s) has unresolved delegation candidate(s): %s",
            step.step_id,
            getattr(result, "contract_id", "<unknown>"),
            ", ".join(unresolved),
        )
```

Use `getattr(..., default)` defensively the same way the existing code a few lines below does
for `invocation_ids` — this file's own comment explains why: "test mocks (MagicMock) and real
`StepContractExecutionResult` instances both flow through cleanly." Place this loop immediately
after the existing `logger.info("composed %s/%s emitted %d invocation(s): %s", ...)` block
(currently ~line 585-591), mirroring that block's placement per contract C-3.

- **Level**: `WARNING`, never `ERROR` — non-blocking. A correctly-cited-but-activation-filtered
  candidate is a valid, if inert, state (D-005), not necessarily an authoring mistake.
- **Cardinality**: exactly one WARNING per step with 1+ unresolved candidates (not one per
  candidate, not one per contract).
- **Message fields**: step id, contract id, unresolved candidate string(s) — all three, per
  FR-007's explicit requirement.

## Subtasks

### T011 — FR-006: thread `org_dirs` into runtime dispatch's repository construction

Edit `_resolve_runtime_contract_for_step` in `runtime_bridge_composition.py` as described
above.

### T012 — FR-006a: mirror it in mission-load validation [LOCKSTEP with T011]

Edit `_resolve_contract_refs` in `mission_loader/command.py` as described above. Same
`resolve_org_dirs` call, same `subdir` value as T011.

### T013 — Shared-fixture regression test: FR-006 (SC-003)

In `tests/runtime/test_bridge_composition.py`, add a test using the **same synthetic org-pack
fixture WP02 built** for its FR-001/FR-005 tests (SC-003 requires one shared fixture across
three test functions — find WP02's fixture-builder location, which WP02's prompt instructed it
to place somewhere importable from `tests/runtime/` and `tests/unit/mission_loader/`; if WP02
has not yet landed in your worktree's merge base, check with the orchestrator before
re-authoring a duplicate fixture — a second, drifted fixture defeats the entire point of SC-003).
Author a custom mission template with a step declaring an org-tier `contract_ref`. Confirm
`_resolve_runtime_contract_for_step` returns the org-tier contract object (not `None`).

### T014 — Shared-fixture regression test: FR-006a + identical-failure proof (SC-003, User Story 2 AS3)

In `tests/unit/mission_loader/test_command.py`, using the same shared fixture as T013:

- Confirm `_resolve_contract_refs` returns `None` (no `LoaderError`) for the same org-tier
  `contract_ref` template used in T013.
- **User Story 2, Acceptance Scenario 3**: with the org pack **removed/not configured**,
  confirm both `_resolve_contract_refs` (this test) and `_resolve_runtime_contract_for_step`
  (T013) fail **identically** — same `MISSION_CONTRACT_REF_UNRESOLVED` / dispatch-fallback
  outcome. This is the proof that lockstep actually holds, not merely that both happen to pass
  independently. You may need to coordinate this as one assertion spanning both test modules
  (e.g. a shared parametrized case, or two tests that both reference the same
  "org-pack-absent" fixture variant) — the point is the absent-case behavior must be
  demonstrably identical, not asserted separately with different fixtures that could silently
  diverge.

### T015 — FR-007: WARNING logging in `_dispatch_via_composition`

Implement the inline `result.steps` iteration described above. Do not add properties to
`executor.py` (see the Implementation scoping decision above).

### T016 — FR-007 `caplog` test (SC-004)

In `tests/runtime/test_bridge_composition.py`, add a `caplog`-based test with **both** cases in
the same test function (per SC-004 — a future change must not be able to break the negative
case while the positive case still passes):

- **Positive**: a step contract with one candidate that cannot resolve (e.g. a nonexistent
  directive id in `delegates_to.candidates`) → exactly one WARNING-level record, naming the
  step id, contract id, and the unresolved candidate string.
- **Negative**: a step contract where every candidate resolves → **zero** WARNING records in
  the same test run.

## Branch Strategy

Both planning and merge target are `pr/up-org-doctrine-consumers-01M05YAB`. Allocate via
`spec-kitty implement WP03` (depends on WP01 only — WP02 and WP03 are designed to be
independently schedulable in parallel; do not assume WP02 has landed, per the Implementation
scoping decision above). This mission's `meta.json` records `target_branch: main` while the
actual planning/merge branch is `pr/up-org-doctrine-consumers-01M05YAB` — a known mismatch; do
not improvise around it if a command refuses, flag it instead.

## Definition of Done

- FR-006, FR-006a both implemented; `_resolve_runtime_contract_for_step` and
  `_resolve_contract_refs` both changed in this same package (lockstep verified).
- T013/T014 prove identical resolution AND identical absent-org-pack failure using one shared
  fixture, not two independently-authored ones.
- FR-007's WARNING logging implemented via inline `result.steps` iteration — `executor.py` is
  **not** touched by this WP.
- T016's positive/negative cases both pass in the same test function.
- `pytest tests/runtime/test_bridge_composition.py tests/unit/mission_loader/test_command.py -v`
  green.

## Risks / Reviewer guidance

- **The lockstep pair is the primary review risk** — confirm both `runtime_bridge_composition.py`
  and `mission_loader/command.py` changed in this PR's diff for this WP.
- **Coverage**: `runtime_bridge_composition.py` (FR-006/FR-007) is in the enforced critical-path
  `diff-cover --fail-under=90` gate (`src/runtime/next/*`). `mission_loader/command.py`
  (FR-006a) is **not** in that critical-path array but has its **own dedicated** job:
  `--cov=src/specify_cli/mission_loader --cov-fail-under=90`
  (`tests/unit/mission_loader/` + `tests/integration/test_mission_run_command.py`, NFR-004).
  Confirm your changes keep both gates green — this is one of the two WPs in this mission with
  a hard, CI-enforced coverage floor tied directly to its files (WP04/WP05's `src/charter/*`
  is the other critical-path area; WP02's files have no such gate).
- Confirm the deviation from `data-model.md`'s property-based FR-007 sketch (this prompt's
  Implementation scoping decision) is intentional, not an oversight — the externally observable
  behavior (SC-004's WARNING shape) is identical either way; only the internal implementation
  location differs, specifically to preserve WP02/WP03 file-ownership independence.
- Do not silently narrow FR-006's fix to `software-dev` missions based on the stale
  `mission == "software-dev"` comment elsewhere in this module family (D-002) — it does not
  describe the actual dispatch predicate.
