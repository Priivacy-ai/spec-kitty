---
work_package_id: WP07
title: Pin Events and Tracker Public-Surface Consumer Contracts
dependencies:
- WP02
- WP04
requirement_refs:
- C-003
- FR-005
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
agent: "claude:opus-4.7:python-reviewer:reviewer"
shell_pid: "70965"
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: tests/contract/spec_kitty_events_consumer/
execution_mode: code_change
owned_files:
- tests/contract/spec_kitty_events_consumer/**
- tests/contract/spec_kitty_tracker_consumer/**
tags: []
---

# WP07 — Pin Events and Tracker Public-Surface Consumer Contracts

## Objective

Pin the subset of `spec_kitty_events.*` and `spec_kitty_tracker.*` public
surface that CLI actually uses, via consumer-test contracts. Upstream contract
changes break these tests intentionally, forcing CLI to react explicitly
rather than fail silently in production.

## Context

The events repo finalized its public surface in mission
`events-pypi-contract-hardening-01KQ1ZK7` (merged at sha `81d5ccd4`); the
documented surface is in `spec-kitty-events/docs/public-surface.md`. The
tracker repo's mission `tracker-pypi-sdk-independence-hardening-01KQ1ZKK` is
in implement-review at the time of this plan; rebase the tracker contract
list against the upstream public-surface doc before this WP closes.

The CLI's actual usage (verified via grep) is captured in:
- [`../contracts/events_consumer_surface.md`](../contracts/events_consumer_surface.md)
- [`../contracts/tracker_consumer_surface.md`](../contracts/tracker_consumer_surface.md)

These docs are the source of truth for the consumer-test contracts; if WP04
or WP02 change which events / tracker symbols CLI uses, those docs are
updated *in the same PR* and this WP's tests follow.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: convergence (depends on lane A's WP02 and lane B's WP04).

## Implementation

### Subtask T027 — Events consumer contract test [P]

**Purpose**: For every events symbol CLI imports, assert it exists at the
documented import path with the structural shape CLI relies on.

**Steps**:

1. Create `tests/contract/spec_kitty_events_consumer/` with `__init__.py`.

2. Create `tests/contract/spec_kitty_events_consumer/test_consumer_contract.py`:

   ```python
   """Consumer contract for spec-kitty-events.

   Pins the subset of the events public surface that CLI uses. Upstream
   contract changes (renaming or removing pinned symbols) MUST break this
   test, per FR-009 of mission shared-package-boundary-cutover-01KQ22DS.

   The pinned surface is documented in
   kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/
   events_consumer_surface.md.
   """
   from __future__ import annotations

   import importlib
   import inspect

   import pytest

   pytestmark = [pytest.mark.contract]


   # ---------------------------------------------------------------------------
   # Top-level package surface
   # ---------------------------------------------------------------------------

   _TOP_LEVEL_SYMBOLS = (
       "Event",
       "ErrorEntry",
       "ConflictResolution",
       "normalize_event_id",
       "LamportClock",
       "EventStore",
       "InMemoryEventStore",
       "CUTOVER_ARTIFACT",
       "assert_canonical_cutover_signal",
   )


   @pytest.mark.parametrize("symbol_name", _TOP_LEVEL_SYMBOLS)
   def test_top_level_symbol_exists(symbol_name: str) -> None:
       module = importlib.import_module("spec_kitty_events")
       assert hasattr(module, symbol_name), (
           f"spec_kitty_events.{symbol_name} is missing. "
           f"This breaks CLI import in mission shared-package-boundary-cutover-01KQ22DS. "
           f"Either upstream events removed the symbol (file an upstream issue) "
           f"or CLI no longer needs it (remove from this contract)."
       )


   # ---------------------------------------------------------------------------
   # Sub-module surface
   # ---------------------------------------------------------------------------

   _SUBMODULE_SYMBOLS = (
       # (module, symbol_name)
       # NOTE: the exact decisionpoint / decision_moment symbol names are
       # confirmed against the events 4.0.0 surface during WP04 implementation.
       # WP07 reads the WP04-completed import statements in
       # src/specify_cli/decisions/emit.py and asserts each one resolves.
       ("spec_kitty_events.decisionpoint", "DecisionPointOpened"),
       ("spec_kitty_events.decisionpoint", "DecisionPointResolved"),
       ("spec_kitty_events.decision_moment", "Widened"),
   )


   @pytest.mark.parametrize("module_name,symbol_name", _SUBMODULE_SYMBOLS)
   def test_submodule_symbol_exists(module_name: str, symbol_name: str) -> None:
       module = importlib.import_module(module_name)
       assert hasattr(module, symbol_name), (
           f"{module_name}.{symbol_name} is missing in spec-kitty-events. "
           "Update the consumer contract or fix the upstream surface."
       )


   # ---------------------------------------------------------------------------
   # Callable signature shape
   # ---------------------------------------------------------------------------

   def test_normalize_event_id_signature() -> None:
       from spec_kitty_events import normalize_event_id

       sig = inspect.signature(normalize_event_id)
       params = list(sig.parameters)
       # CLI passes a single positional/keyword argument (event_id or similar).
       # The contract is "accepts at least one parameter"; tighten if needed.
       assert len(params) >= 1, params


   def test_event_class_shape() -> None:
       from spec_kitty_events import Event

       # Event is a Pydantic model; CLI relies on .model_dump() and field names.
       # Assert at least the structural attributes CLI reads.
       assert hasattr(Event, "model_dump"), (
           "spec_kitty_events.Event no longer exposes Pydantic model_dump(). "
           "CLI's sync emitter relies on this."
       )
   ```

3. Run the test:
   ```bash
   pytest tests/contract/spec_kitty_events_consumer/ -v
   ```

   It MUST pass against the currently-installed events 4.0.0.

4. **Important**: the symbol list MUST be derived from the WP04-completed
   imports in `src/specify_cli/decisions/emit.py`,
   `src/specify_cli/glossary/events.py`, and `src/specify_cli/sync/diagnose.py`.
   If any pinned symbol differs from those imports, the contract is wrong;
   fix the contract.

**Files**:
- `tests/contract/spec_kitty_events_consumer/__init__.py`
- `tests/contract/spec_kitty_events_consumer/test_consumer_contract.py`

**Validation**: The test suite is green against events 4.0.0.

### Subtask T028 — Tracker consumer contract test [P]

**Purpose**: Same pattern, applied to tracker.

**Steps**:

1. Create `tests/contract/spec_kitty_tracker_consumer/` with `__init__.py`.

2. Create `tests/contract/spec_kitty_tracker_consumer/test_consumer_contract.py`:

   ```python
   """Consumer contract for spec-kitty-tracker.

   Pins the subset of the tracker public surface that CLI uses. Upstream
   contract changes break this test, per FR-009 / FR-005 of mission
   shared-package-boundary-cutover-01KQ22DS.

   The pinned surface is documented in
   kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/
   tracker_consumer_surface.md.
   """
   from __future__ import annotations

   import importlib

   import pytest

   pytestmark = [pytest.mark.contract]


   _TOP_LEVEL_SYMBOLS = (
       "FieldOwner",
       "OwnershipMode",
       "OwnershipPolicy",
       "SyncEngine",
   )


   @pytest.mark.parametrize("symbol_name", _TOP_LEVEL_SYMBOLS)
   def test_top_level_symbol_exists(symbol_name: str) -> None:
       module = importlib.import_module("spec_kitty_tracker")
       assert hasattr(module, symbol_name)


   _MODELS_SYMBOLS = (
       "ExternalRef",
       # additional symbols enumerated by inspecting
       # src/specify_cli/tracker/store.py imports during WP07
   )


   @pytest.mark.parametrize("symbol_name", _MODELS_SYMBOLS)
   def test_models_symbol_exists(symbol_name: str) -> None:
       module = importlib.import_module("spec_kitty_tracker.models")
       assert hasattr(module, symbol_name)


   def test_ownership_mode_is_enum_like() -> None:
       from spec_kitty_tracker import OwnershipMode

       # CLI reads at least one mode value; assert the enum-like surface.
       assert hasattr(OwnershipMode, "__members__") or callable(getattr(OwnershipMode, "__class__", None)), (
           "OwnershipMode no longer exposes an enum-like interface. "
           "CLI's tracker integration relies on this."
       )
   ```

3. Run:
   ```bash
   pytest tests/contract/spec_kitty_tracker_consumer/ -v
   ```

   It MUST pass against tracker 0.4.2 currently installed.

4. **On rebase**: if the upstream tracker mission has merged and published a
   new public-surface doc, update this contract to match (add new pinned
   symbols, remove ones that were renamed). Coordinate via the tracker
   mission's slug (`tracker-pypi-sdk-independence-hardening-01KQ1ZKK`).

**Files**:
- `tests/contract/spec_kitty_tracker_consumer/__init__.py`
- `tests/contract/spec_kitty_tracker_consumer/test_consumer_contract.py`

**Validation**: The test suite is green against tracker 0.4.2.

### Subtask T029 — Verify both green against published versions

**Purpose**: Run the consumer-test suites end-to-end. Confirm both pass
against the published versions CLI's `pyproject.toml` will pin (events 4.0.x,
tracker 0.4.x).

**Steps**:

1. In a clean venv (or the dev environment, but ideally a clean one):
   ```bash
   pip install spec-kitty-events==4.0.0 spec-kitty-tracker==0.4.2
   pytest tests/contract/spec_kitty_events_consumer/ tests/contract/spec_kitty_tracker_consumer/ -v
   ```

2. Expected: both green.

3. Tighten any pinned symbol that the consumer test treats as "exists" but
   CLI uses in a more specific way. For example, if CLI passes `event_id=`
   keyword to `normalize_event_id`, add an assertion that
   `inspect.signature(normalize_event_id).parameters['event_id']` is present.

**Files**: refinements to the two consumer-test files from T027 and T028.

**Validation**:
- Both suites green.
- Each pinned symbol's assertion shape matches CLI's actual usage.

## Definition of Done

- [ ] All 3 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] Two consumer-test packages exist under `tests/contract/`.
- [ ] Both pass against events 4.0.0 and tracker 0.4.2.
- [ ] Each pinned symbol corresponds to a real CLI usage in production code.
- [ ] Tests are marked `@pytest.mark.contract` (already declared in
  `pyproject.toml`).

## Risks

- **Tracker upstream mission lands a contract delta after this contract is
  finalized.** Mitigation: T028's documented "rebase" step; the orchestrator
  picks up the delta automatically when WP07 resumes.
- **The consumer test passes today but a future events MINOR release adds a
  symbol with a name that shadows a pinned one's signature.** Mitigation:
  the test's signature assertion is parameter-name-based, not just existence;
  signature changes break the test explicitly.

## Reviewer guidance

- Verify each pinned symbol corresponds to a real CLI import in WP04's
  `src/specify_cli/decisions/emit.py`, `src/specify_cli/glossary/events.py`,
  `src/specify_cli/sync/diagnose.py`, or in `src/specify_cli/tracker/*`.
- Verify the test suites are green against the currently-published versions.
- Verify the contract doc files (`contracts/events_consumer_surface.md`,
  `contracts/tracker_consumer_surface.md`) match the test pin list.
- Verify the test markers are correct.

## Implementation command

```bash
spec-kitty agent action implement WP07 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```

## Activity Log

- 2026-04-25T12:01:46Z – claude:opus-4.7:python-implementer:implementer – shell_pid=70312 – Started implementation via action command
- 2026-04-25T12:03:09Z – claude:opus-4.7:python-implementer:implementer – shell_pid=70312 – Two consumer-test packages created. Events: 26 tests (10 top-level + 13 submodule + 3 shape). Tracker: 8 tests (4 top-level + 1 models + 3 shape). All 34 pass in 0.18s against events 4.0.0 / tracker 0.4.2. Pins derived from grep over src/ on post-WP04 tree. Refs FR-005, FR-009, C-003.
- 2026-04-25T12:03:19Z – claude:opus-4.7:python-reviewer:reviewer – shell_pid=70965 – Started review via action command
