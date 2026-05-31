---
work_package_id: WP09
title: 'Pattern B+C: Flat Catalog + Direct Repository Wiring'
dependencies:
- WP02
- WP03
- WP08
requirement_refs:
- FR-016
- FR-033
- FR-034
- FR-037
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: Planning artifacts for this mission were generated on pr/charter-doctrine-mission-type-configuration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/charter-doctrine-mission-type-configuration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-pack-activation-layer-01KSYE4V
base_commit: 8f49c86548ac66c7fa6788cd1597b0538bc49f4a
created_at: '2026-05-31T14:19:44.927313+00:00'
subtasks:
- T039
- T040
- T041
- T042
- T043
agent: "claude:sonnet-4-6:python-pedro:implementer"
shell_pid: "319643"
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/charter/resolver.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter/generate.py
- src/specify_cli/doctrine/org_charter.py
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/charter_runtime/lint/checks/org_layer.py
- src/charter/mission_steps.py
- src/charter/resolver.py
- tests/charter/test_call_site_propagation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

You are **python-pedro** (Python implementer). Make only the changes described,
validate after each subtask, and do not touch files outside `owned_files`.

---

## Objective

Wire activation filtering into two code patterns that bypass the DRG path
handled in WP08:

- **Pattern B** — `paradigm` and `procedure` nodes exist as `NodeKind` values in
  the DRG but are discarded by `_classify_artifact_urns()` before activation can
  take effect. Filtering must also cover the flat catalog path:
  `DoctrineService.paradigms` / `.procedures` in `resolver.py`.
- **Pattern C** — `agent_profile` and `mission_step_contract` are resolved via
  direct repository, never via DRG. Filtering happens at the repository access
  point in `resolver.py`.

Also adds `MissionStepRepository` as a re-export from `src/charter/mission_steps.py`
and wires it into at least one production call site (FR-037, clears dead-symbol
flag in architectural tests).

**Satisfied requirements**: FR-016, FR-033, FR-034, FR-037.

**Layer rule**: `doctrine.*` must NEVER import from `charter.*`. `specify_cli.*`
may import from both. Do not add `from charter` inside `src/specify_cli/doctrine/`.

**ATDD rule**: Every test whose call target changes signature must be updated in
this WP to pass the new parameters explicitly.

---

## Context

**Pattern B — why two paths**:
Even after WP08 filters the DRG, `_classify_artifact_urns()` in `context.py`
(lines 318–332) discards `paradigm` / `procedure` nodes before the resolved bundle
is built. The operative filter for these kinds is therefore the flat catalog access
point: `DoctrineService.paradigms` and `.procedures` properties.

**Pattern C — direct repository**:
`agent_profile` and `mission_step_contract` never pass through the DRG. Their
access point is `DoctrineService.agent_profiles` (≈`resolver.py:257`). A simple
dict comprehension guard there is sufficient.

**Dead symbol — `MissionStepRepository`**:
`src/charter/mission_steps.py` exports `MissionStep`, `MissionStepContract`,
`MissionStepContractRepository`, and `MissionStepContractStep` but not
`MissionStepRepository`. The architectural test `test_no_dead_symbols.py` flags
it as defined but never used in production. Adding the re-export and one call
site clears the flag.

**Commit cadence**: T039+T040 together (DoctrineService / org-charter wiring),
then T041, then T042+T043 together.

---

## Subtasks

---

### T039 — Wire Pattern B: `generate.py` DoctrineService construction

**Requirement**: FR-016, FR-034 | **File**: `src/specify_cli/cli/commands/charter/generate.py`

1. Read the command handler around line 47. Locate the `DoctrineService(...)` constructor call.

2. Obtain the current `PackContext` and pass it:
   ```python
   ctx = ProjectContext.from_repo(repo_root)   # adapt to existing import style
   service = DoctrineService(pack_context=ctx.require_pack_context(), ...)
   ```

3. In `src/charter/resolver.py`, add an activation filter to the `paradigms` and
   `procedures` properties (if not already filtering):
   ```python
   @property
   def paradigms(self) -> dict[str, Paradigm]:
       all_paradigms = self._load_paradigms()
       if self._pack_context is not None and \
               self._pack_context.activated_paradigms is not None:
           return {k: v for k, v in all_paradigms.items()
                   if k in self._pack_context.activated_paradigms}
       return all_paradigms
   ```
   Apply the identical pattern to `.procedures` using `activated_procedures`.

**ATDD**: Update any test that constructs `DoctrineService` without `pack_context`
to explicitly pass `pack_context=None` so it reflects the updated signature.

**Validation**:
```bash
python -c "from specify_cli.cli.commands.charter.generate import *; print('OK')"
pytest tests/specify_cli/cli/commands/charter/ -x 2>&1 | tail -10
```

---

### T040 — Wire `org_charter.py` internal callers

**Requirement**: FR-016, FR-033 | **File**: `src/specify_cli/doctrine/org_charter.py`

`load_org_charter_policies()` at line 464 already has `pack_context: ... = None`.
The two internal call sites at lines 660 and 710 do not forward it.

1. Read `load_org_charter_policies()` and the two enclosing functions that call it
   (around lines 660 and 710) in full to understand the context chain.
2. Locate both call sites. Update each to forward `pack_context`:
   ```python
   load_org_charter_policies(repo_root, pack_context=pack_context)
   ```
3. If the enclosing function(s) do not yet have `pack_context` in their own
   signature, add `pack_context: PackContext | None = None` and thread it from
   their callers. Trace as far up the call chain as needed.
4. Verify no other call to `load_org_charter_policies` inside this file is missing
   `pack_context`:
   ```bash
   grep -n "load_org_charter_policies" src/specify_cli/doctrine/org_charter.py
   # Every non-def line must include pack_context=
   ```

---

### T041 — Wire `doctor.py:2332` + `org_layer.py:218,236`

**Requirement**: FR-016, FR-033

**Files**: `src/specify_cli/cli/commands/doctor.py`, `src/specify_cli/charter_runtime/lint/checks/org_layer.py`

**`doctor.py:2332`**: The call `load_org_charter_policies(repo_root)` is missing
`pack_context`. Fix:
```python
ctx = ProjectContext.from_repo(repo_root)   # or use existing ctx if in scope
policies = load_org_charter_policies(repo_root, pack_context=ctx.require_pack_context())
```
Check for any other bare calls in the same file and fix them too.

**`org_layer.py:218,236`**: These are linter check methods, not callers of
`load_org_charter_policies`. Add `pack_context: PackContext | None = None` to each
method signature at those lines:
```python
def check_org_layer(self, artifact_set: ..., pack_context: PackContext | None = None) -> ...:
```
Use `pack_context` inside the method body to filter `artifact_set` before the check,
following the same dict comprehension pattern as `DoctrineService.paradigms` in T039.
Import `PackContext` from `charter.pack_context` if absent.

**ATDD**: Update tests for the doctor org-charter path and `org_layer.py` linter
methods to pass `pack_context=None` (or a real `PackContext`).

**Validation**:
```bash
grep -n "load_org_charter_policies" src/specify_cli/cli/commands/doctor.py
# All non-def lines must include pack_context=
python -c "from specify_cli.charter_runtime.lint.checks.org_layer import *; print('OK')"
```

---

### T042 — Wire Pattern C: agent_profiles via `resolver.py`

**Requirement**: FR-033, FR-037 | **File**: `src/charter/resolver.py`

1. Read `DoctrineService.agent_profiles` (≈line 257) in full.

2. Add the activation filter:
   ```python
   @property
   def agent_profiles(self) -> dict[str, AgentProfile]:
       all_profiles = self._load_agent_profiles()
       if self._pack_context is not None and \
               self._pack_context.activated_agent_profiles is not None:
           return {k: v for k, v in all_profiles.items()
                   if k in self._pack_context.activated_agent_profiles}
       return all_profiles
   ```

3. Apply the same pattern to `mission_step_contracts` property (if it exists),
   filtering by `activated_mission_step_contracts`.

4. Verify that `self._pack_context` is properly stored during `DoctrineService.__init__`.
   If `DoctrineService` does not already store a `_pack_context` attribute (from T039),
   add it: `self._pack_context = pack_context`.

5. `pack_context=None` must leave behaviour identical to pre-WP09 (backward compat).
   The `if self._pack_context is not None and ... is not None:` double guard ensures
   that both absent context and absent per-kind config produce the unfiltered result.

**ATDD**: If `tests/charter/test_call_site_propagation.py` tests `agent_profiles`
access, verify it still passes. **Required**: add a test asserting that
`activated_agent_profiles=frozenset()` returns an empty dict when `DoctrineService` is
constructed with a `PackContext` holding that frozenset, and a test asserting that
`activated_agent_profiles=None` returns the full unfiltered dict (backward-compat).

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "from charter.resolver import DoctrineService; print('OK')"
```

---

### T043 — Add `MissionStepRepository` re-export + production call site

**Requirement**: FR-037 | **File**: `src/charter/mission_steps.py`

1. Read `src/charter/mission_steps.py`. Add the re-export:
   ```python
   from doctrine.missions.mission_step_repository import MissionStepRepository

   __all__ = [..., "MissionStepRepository"]
   ```

2. Read `doctrine.missions.mission_step_repository` to confirm the correct method
   signatures before writing any call site — do not guess.

3. Based on `research.md §4`, the natural caller is in `charter/mission_type_profiles.py`
   or `specify_cli/next/` where action sequences drive step execution. Read the target
   file before editing to ensure the call site integrates cleanly with surrounding logic.
   Add the call site there using the confirmed API:
   ```python
   from charter.mission_steps import MissionStepRepository
   repo = MissionStepRepository.default()
   steps = repo.resolve(mission_type_id, step_id, pack_context)
   ```
   Adapt to the actual method signature. The call must be reachable from a real
   code path (not inside a dead branch or commented stub).

**Verification**:
```bash
grep -r "MissionStepRepository" src/ --include="*.py" \
    | grep -v "test_" | grep -v "__all__" | grep -v "^.*import MissionStepRepository"
# Expected: ≥ 1 non-import non-all non-test line (the production call site)
```

**ATDD**: Run the architectural dead-symbol test:
```bash
pytest tests/architectural/test_no_dead_symbols.py -x -v 2>&1 | tail -15
# Expected: no MissionStepRepository finding
```

---

## Wiring Verification (Acceptance Criteria)

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty

# ≥ 3 require_pack_context() call sites covering all 3 patterns
grep -r "require_pack_context()" src/ --include="*.py" | wc -l

# All load_org_charter_policies callers forward pack_context
grep -r "load_org_charter_policies" src/ --include="*.py" | grep -v "def load_org"

# MissionStepRepository production call site exists
grep -r "MissionStepRepository" src/ --include="*.py" \
    | grep -v "__all__" | grep -v "import MissionStepRepository" | grep -v "test_"
```

---

## Definition of Done

- [ ] `pytest tests/ -x` passes (all patterns, all updated tests)
- [ ] `DoctrineService.paradigms` and `.procedures` apply activation filter when `pack_context` is set
- [ ] `DoctrineService.agent_profiles` (and `mission_step_contracts` if present) apply activation filter
- [ ] `MissionStepRepository` re-exported from `src/charter/mission_steps.py` with ≥ 1 production call site
- [ ] `org_layer.py` methods at lines 218 and 236 accept `pack_context: PackContext | None = None`
- [ ] All callers of `load_org_charter_policies` pass `pack_context` explicitly
- [ ] `grep -r "require_pack_context()" src/ --include="*.py"` returns ≥ 3 lines
- [ ] `pytest tests/architectural/test_no_dead_symbols.py -x` passes with no `MissionStepRepository` finding
- [ ] `ruff check src/specify_cli/cli/commands/charter/generate.py src/specify_cli/doctrine/org_charter.py src/specify_cli/cli/commands/doctor.py src/specify_cli/charter_runtime/lint/checks/org_layer.py src/charter/mission_steps.py src/charter/resolver.py` passes
- [ ] `grep -r "from charter" src/specify_cli/doctrine/ --include="*.py"` returns zero lines (layer rule upheld)

---

## Risks

- **`DoctrineService` constructor shape**: read the constructor before passing
  `pack_context`. If it uses a builder or `*args`, adapt — do not assume a keyword
  argument named `pack_context` exists.
- **Pattern B classification gap**: `_classify_artifact_urns()` may discard `paradigm`
  / `procedure` nodes regardless of WP08 filtering. The flat catalog filter in T039
  is the operative gate for these kinds. Confirm by tracing the data flow.
- **Additional `load_org_charter_policies` callers**: before committing T040–T041,
  run `grep -r "load_org_charter_policies" src/ --include="*.py" | grep -v "def load_org"`
  and fix any callers not listed in the research.
- **`MissionStepRepository` API**: read the source before writing the call site.
  Guessing method names creates silent coverage gaps.
- **Layer rule**: `specify_cli.doctrine.*` must not gain any new `from charter`
  import. All new `charter.*` imports belong in `specify_cli.*` or `charter.*` only.

---

## Reviewer Guidance

1. `DoctrineService.paradigms` / `.procedures` — dict comprehension with `activated_paradigms` / `activated_procedures` must be visible in `resolver.py`.
2. `DoctrineService.agent_profiles` — same pattern with `activated_agent_profiles`.
3. `grep -r "load_org_charter_policies" src/ --include="*.py" | grep -v "def load_org"` — every line must include `pack_context=`.
4. `grep -r "MissionStepRepository" src/ --include="*.py" | grep -v "__all__" | grep -v "import " | grep -v "test_"` — must return ≥ 1 line.
5. `grep -r "from charter" src/specify_cli/doctrine/ --include="*.py"` — must return zero lines.
6. `pytest tests/ -x` and `pytest tests/architectural/ -x` — both must exit 0.

## Activity Log

- 2026-05-31T14:19:45Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=6774 – Assigned agent via action command
- 2026-05-31T14:43:03Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=6774 – Ready for review: all 10 call-site propagation tests pass. test_agent_action_implement_passes_acknowledge_default_false is a pre-existing worktree-context false failure unrelated to WP09.
- 2026-05-31T14:47:27Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=205562 – Started review via action command
- 2026-05-31T15:08:39Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=205562 – Moved to planned
- 2026-05-31T15:10:29Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=319643 – Started implementation via action command
- 2026-05-31T15:10:46Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=319643 – Cycle-2: removed resolve_mission_steps from __all__ in charter/resolver.py
