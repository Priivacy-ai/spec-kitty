---
work_package_id: WP02
title: Executor org-tier threading + gate-binding lockstep
dependencies:
- WP01
requirement_refs:
- C-001
- C-002
- FR-001
- FR-002
- FR-005
- NFR-001
- NFR-002
planning_base_branch: pr/up-org-doctrine-consumers-01M05YAB
merge_target_branch: pr/up-org-doctrine-consumers-01M05YAB
branch_strategy: Planning artifacts for this mission were generated on pr/up-org-doctrine-consumers-01M05YAB. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/up-org-doctrine-consumers-01M05YAB unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
history:
- at: '2026-08-16T19:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/mission_step_contracts/executor.py
- src/specify_cli/review/gate_bindings.py
- tests/specify_cli/mission_step_contracts/test_executor.py
- tests/specify_cli/mission_step_contracts/test_executor_activation.py
- tests/review/test_gate_bindings.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Executor org-tier threading + gate-binding lockstep

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

## ⚠️ MANDATORY LOCKSTEP CONSTRAINT — READ BEFORE STARTING

**`src/specify_cli/review/gate_bindings.py:168` (`_build_repository`) and
`src/specify_cli/mission_step_contracts/executor.py:160` (`StepContractExecutor.__init__`)
MUST both be fixed in this single work package. Do not implement one and defer the other to a
follow-up — there is no follow-up WP for this file pair.**

Why this is non-negotiable: `_build_repository`'s own docstring says "Construct the contract
repository the way the executor does," and `load_gate_bindings` (same file) says it uses "the
same repository the executor uses" — an explicit mirroring contract. If the executor becomes
org-tier-aware (this WP's FR-001) and `gate_bindings.py` does not, an org-pack step contract's
`gates:` block will resolve delegations correctly at dispatch time but **silently never fire
its review-transition gate** (`tasks_move_task.py` consumes `load_gate_bindings`). That is a
strictly worse outcome than today's uniform blindness — it converts "org-tier is invisible
everywhere" into "org-tier resolves for delegation but the safety gate silently no-ops,"
which nobody would notice without reading source. This is the exact silent-failure shape the
whole mission (#3516) exists to close. If you find yourself tempted to split this WP because
one half feels done first, do not — implement T005 and T007 together and verify both before
moving on.

> **Tooling note**: this WP's frontmatter `requirement_refs` cannot list `SC-001`/`SC-002`/
> `SC-003` — `spec-kitty agent tasks map-requirements` only accepts `FR-`/`NFR-`/`C-` prefixed
> refs (confirmed live during this mission's task generation), not `SC-`. Those three success
> criteria fully apply to this WP (see T008/T010 below) despite being absent from the
> structured field.

## Objective

Fix the mission's primary defect pair (User Story 1 — an org-tier step contract's delegations
resolve at dispatch time) and, in the same package, the gate-binding half of User Story 3 (an
org-tier step contract's `gates:` block fires at WP review-transition time). Three FRs land
here: FR-001 (executor threads `org_dirs` into the contract repository), FR-002 (executor
threads a resolved `org_root` into the DRG loader), FR-005 (gate_bindings mirrors FR-001's
repository construction exactly).

## Context

### Dependency: WP01's `resolve_org_dirs`

This WP imports `resolve_org_dirs(repo_root: Path, subdir: str) -> list[Path]` from
`src/doctrine/drg/org_pack_config.py` (landed by WP01 — must be merged/available before you
start). Call it with `subdir="mission_step_contracts"` at both FR-001 and FR-005's sites. Do
not re-implement its logic inline — that would recreate exactly the kind of caller-drift this
mission exists to close.

### The resolver-shape distinction — this WP uses BOTH shapes, do not conflate them

- **FR-001 and FR-005** use the **list shape** (`org_dirs: list[Path]`, via WP01's
  `resolve_org_dirs`) — consumed by `MissionStepContractRepository`, a
  `BaseDoctrineRepository` subclass.
- **FR-002** uses the structurally distinct **single-path shape** (`org_root: Path | None`) —
  consumed by `charter._drg_helpers.load_validated_graph`. This is **not** `resolve_org_dirs`'s
  job and does not go through it. Resolve it inline per contract C-2 (below). Conflating these
  two shapes is a mistake the mission's own spec had to explicitly correct once (spec.md
  D-000(2)) — do not attempt to pass `org_dirs` (a list) where `org_root` (a single path) is
  expected, or vice versa.

### FR-001 — current code (`executor.py:151-162`, `StepContractExecutor.__init__`)

```python
def __init__(
    self,
    *,
    repo_root: Path,
    contract_repository: MissionStepContractRepository | None = None,
    invocation_executor: ProfileInvocationExecutor | None = None,
    graph: DRGGraph | None = None,
) -> None:
    self._repo_root = repo_root
    self._contracts = contract_repository or MissionStepContractRepository(
        project_dir=repo_root / ".kittify" / "doctrine" / "mission_step_contracts"
    )
    self._invocation_executor = invocation_executor or ProfileInvocationExecutor(repo_root)
    self._graph = graph
```

Change the `MissionStepContractRepository(...)` construction to also pass
`org_dirs=resolve_org_dirs(repo_root, "mission_step_contracts")`. Preserve the existing
`contract_repository` override parameter (tests and callers that inject a repository directly
must keep working unchanged — this is a fallback default, not the only construction path).

### FR-002 — current code (`executor.py:179`, inside `execute()`)

```python
graph = self._graph or load_validated_graph(context.repo_root)
```

Per contract C-2 (`contracts/org-tier-resolution-contract.md`), resolve a single `org_root`
inline, immediately before this line, using the exact first-match pattern already established
by `charter/action_doctrine_bundle.py:_resolve_action_bundle` (lines ~90-97) — **do not**
invent a new shared helper for this; the spec's FR-003 only mandates a shared helper for the
list shape:

```python
effective_org_root: Path | None = None
for _name, candidate in _enumerate_org_pack_paths(context.repo_root):
    if candidate.exists():
        effective_org_root = candidate
        break
```

Then change the `load_validated_graph` call to
`load_validated_graph(context.repo_root, org_root=effective_org_root)`. Import
`_enumerate_org_pack_paths` from `charter.org_pack_discovery` — it is exported despite its
underscore prefix (present in that module's `__all__`) and already imported cross-module by
`action_doctrine_bundle.py`, so this is established precedent, not a new pattern.

This resolution is **first-match only** — if more than one org pack is configured, only the
first whose path exists on disk contributes to the DRG (C-004, out of scope to fix; inherited
limitation of `load_validated_graph` itself).

### FR-005 — current code (`gate_bindings.py:165-168`)

```python
def _build_repository(repo_root: Path) -> MissionStepContractRepository:
    """Construct the contract repository the way the executor does."""
    return MissionStepContractRepository(project_dir=repo_root.joinpath(*_PROJECT_CONTRACTS_SUBPATH))
```

Change this to also pass `org_dirs=resolve_org_dirs(repo_root, "mission_step_contracts")` —
the identical call FR-001 makes. The function's own docstring already promises this mirroring;
you are making the promise true.

### Constraint C-001 — activation filtering is unchanged

`filter_graph_by_activation` and `PackContext.from_config` (already applied downstream of the
graph load in `executor.py:182-186`) must not change. FR-002 only makes org-tier DRG nodes
*reachable*; whether a reachable node is *usable* remains governed by existing activation
scoping. T009 below exists specifically to prove this stays true, not merely assume it.

### Constraint C-002 — do not touch site 2

`src/doctrine/missions/step_contracts.py:308` (`resolve_step_contract_ids`'s bare
`MissionStepContractRepository()` default) is explicitly **out of scope**. Its own docstring
documents built-in-only as deliberate, and `ResolvedMissionType.step_contracts` (the field it
populates) has zero production consumers. Do not "fix" it while you're in the neighborhood.

## Subtasks

### T005 — FR-001: thread `org_dirs` into the executor's repository construction

Edit `StepContractExecutor.__init__` (`executor.py:151-162`) as described above. Import
`resolve_org_dirs` from `doctrine.drg.org_pack_config` at the top of the file (module-level
import — this is not a lazy/local import; check the file's existing import style and match it).

### T006 — FR-002: thread a resolved `org_root` into the DRG loader

Edit `StepContractExecutor.execute` (`executor.py:179`) as described above (contract C-2,
first-match inline resolution). Import `_enumerate_org_pack_paths` from
`charter.org_pack_discovery`.

### T007 — FR-005: mirror the executor's construction in gate_bindings [LOCKSTEP with T005]

Edit `_build_repository` (`gate_bindings.py:165-168`) as described above. Use the **same**
`resolve_org_dirs(repo_root, "mission_step_contracts")` call T005 uses — not a copy, the exact
same helper and the exact same `subdir` string, so a future change to either site is forced to
touch the shared helper instead of silently diverging again.

### T008 — Red-first regression: FR-001/FR-002 (SC-001, SC-002)

In `tests/specify_cli/mission_step_contracts/test_executor.py`, add a fixture-driven org-pack
scenario mirroring `_write_org_directive_fixture`'s shape
(`tests/charter/test_org_scan_dirs_activation_regression.py:62`) — a flat-layout synthetic org
pack: `<org_root>/mission_step_contracts/<id>.step-contract.yaml` for the contract, plus
`<org_root>/<stem>.graph.yaml` for the DRG fragment the contract's `delegates_to` cites.

Two required assertions, both **before/after measurements**, not exception-absence checks:

- **SC-002**: `MissionStepContractRepository.get_by_action(...)` for the org-only contract
  returns `None` on the pre-fix code path (verify this red-first: check out this test against
  the pre-fix commit in isolation, per the mission's Verification Bar, and confirm it fails
  there before you consider T005/T007 correct) and the contract object post-fix.
- **SC-001**: assert a DRG node-count delta from `load_validated_graph`. **The reproducible
  number in this checkout is 347 → 348** (one synthetic org directive node added) — this was
  verified live during this mission's spec/plan authoring sessions. **Do not assert 347 → 350**
  — that number came from the original GitHub issue's probe against a different,
  not-present-in-this-checkout org pack, and is not reproducible here. If the built-in graph's
  node count has drifted from 347 by the time you run this, assert the **delta** (`with_org -
  without_org == 1`), not either literal baseline — the mechanism being proven is "one org node
  becomes visible," not a specific absolute count.

Also extend `test_executor_activation.py` if it shares fixtures with `test_executor.py` — check
before duplicating fixture-builder code.

### T009 — Activation-interaction test (C-001 proof)

In `tests/specify_cli/mission_step_contracts/test_executor_activation.py`, add a test proving
C-001: the org-tier DRG node from T008's fixture is visible pre-activation-filter, and is
correctly **excluded** post-filter when the org pack/artifact is not activated in
`PackContext`. This must be an explicit assertion in both directions (visible when activated,
excluded when not) — not an assumption that "the existing activation tests still pass" is
sufficient, since none of those tests exercise an org-tier node today.

### T010 — Shared-fixture FR-005 test (SC-003, gate-bindings third)

In `tests/review/test_gate_bindings.py`, add a test using the **same** synthetic org-pack
fixture T008 built (reuse it — import or share the fixture-builder function/module rather than
re-authoring a second copy; SC-003 specifically requires "one synthetic org-pack fixture,
exercised by three separate test functions... not three independently-authored fixtures that
could silently diverge" — the third test function is FR-006/FR-006a's in WP03, which will also
need to reuse this same fixture, so place it somewhere importable from
`tests/specify_cli/mission_step_contracts/`, `tests/review/`, `tests/runtime/`, and
`tests/unit/mission_loader/` without crossing a test-layer boundary the architectural suite
would reject — a shared `conftest.py` fixture or small fixture-builder module is the right
shape; decide the exact location and leave a clear docstring pointer so WP03's author can find
it without re-reading this WP's diff).

Extend the org pack with a `gates:` block on its step contract's `review` step (per User Story
3's Independent Test). Assert `load_gate_bindings(repo_root, mission, action)` returns that
contract's gates (non-empty) — not `[]` — using only the org-tier contract, no project-tier
duplicate present.

## Branch Strategy

Both planning and merge target are `pr/up-org-doctrine-consumers-01M05YAB`. Allocate via
`spec-kitty implement WP02` (depends on WP01 — do not start until WP01's `resolve_org_dirs` is
available in your worktree's base). This mission's `meta.json` records `target_branch: main`
while the actual planning/merge branch is `pr/up-org-doctrine-consumers-01M05YAB` — a known
mismatch; do not improvise around it if a command refuses, flag it instead.

## Definition of Done

- FR-001, FR-002, FR-005 all implemented; `_build_repository` and `StepContractExecutor.__init__`
  both changed in this same package (lockstep verified).
- T008's tests independently confirmed RED against the pre-fix commit, GREEN on your fix
  (reviewer re-runs this, not just reads a CI checkmark — per the mission's Test Strategy).
- T009 proves C-001 in both directions (activated visible, deactivated excluded).
- T010 proves FR-005 using the **same** fixture as T008, not a separate one.
- `pytest tests/specify_cli/mission_step_contracts/ tests/review/test_gate_bindings.py -v`
  green.

## Risks / Reviewer guidance

- **The lockstep pair is the primary review risk.** A reviewer should specifically confirm
  both `executor.py` and `gate_bindings.py` changed in this PR's diff for this WP — if only one
  did, reject and send back regardless of how correct the implemented half looks.
- **Neither `executor.py` nor `gate_bindings.py` is in this repo's enforced diff-cover
  critical-path list** (`.github/workflows/ci-quality.yml`'s `critical_paths` array covers
  `src/doctrine/*`, `src/charter/*`, `src/runtime/next/*` — not
  `src/specify_cli/mission_step_contracts/*` or `src/specify_cli/review/*`) and neither has a
  dedicated coverage job. A coverage gate will **not** catch a regression here — T008/T009/T010
  passing red-first-then-green is the actual backstop (NFR-001). Do not treat "coverage gate is
  green" as evidence this WP is correct; it isn't measuring this WP at all.
- Do not assert the literal `347`/`348` as hardcoded magic numbers without a comment explaining
  they are this-checkout-specific and the delta (not the baseline) is what's actually load-bearing.
- Watch for import-cycle risk: `executor.py` importing from `doctrine.drg.org_pack_config` and
  `gate_bindings.py` doing the same should both already be valid directions (specify_cli →
  doctrine is permitted); if either import fails with a cycle, that is a real finding to report,
  not something to work around with a local/lazy import unless the existing file already uses
  that style elsewhere.
