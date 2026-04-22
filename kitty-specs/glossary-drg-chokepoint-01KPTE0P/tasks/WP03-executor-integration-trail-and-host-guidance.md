---
work_package_id: WP03
title: Executor Integration, Trail, and Host Guidance
dependencies:
- WP01
- WP02
requirement_refs:
- C-001
- C-005
- C-007
- C-008
- FR-005
- FR-008
- FR-010
- FR-011
- FR-012
- FR-014
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
- T022
- T023
- T024
history:
- date: '2026-04-22'
  event: created
  author: planner
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
mission_id: 01KPTE0P5JVQFWESWV07R0XG4M
mission_slug: glossary-drg-chokepoint-01KPTE0P
owned_files:
- src/specify_cli/invocation/executor.py
- src/specify_cli/invocation/writer.py
- tests/specify_cli/invocation/test_executor_glossary.py
- docs/trail-model.md
- docs/how-to/setup-codex-spec-kitty-launcher.md
- docs/**
tags: []
---

# WP03 — Executor Integration, Trail, and Host Guidance

## Objective

Wire `GlossaryChokepoint` into `ProfileInvocationExecutor.invoke()`, add `write_glossary_observation()` to the trail writer, implement the severity routing contract in code, update host guidance docs, verify the e2e suite.

This is the final integration WP — everything must work end-to-end after it lands.

## Branch Strategy

- **Planning/base branch:** `main`
- **Final merge target:** `main`
- **Execution worktree:** Allocated by `spec-kitty agent action implement WP03 --agent <name>`. Do not start until WP01 and WP02 are merged.
- **Start command:** `spec-kitty agent action implement WP03 --agent <name>`

## Context

### What WP01 and WP02 delivered (expected on main)

- `src/specify_cli/glossary/drg_builder.py` — `GlossaryTermIndex`, `build_index()`, `glossary_urn()`
- `src/specify_cli/glossary/chokepoint.py` — `GlossaryChokepoint`, `GlossaryObservationBundle`

### Key files to modify (WP03 owns these)

| File | Change |
|------|--------|
| `src/specify_cli/invocation/executor.py` | Extend `InvocationPayload.__slots__`, add chokepoint call + severity routing in `invoke()` |
| `src/specify_cli/invocation/writer.py` | Add `write_glossary_observation()` method |
| `docs/trail-model.md` | Document `"glossary_checked"` event type |
| `docs/how-to/setup-codex-spec-kitty-launcher.md` | Add `glossary_observations` field description |
| Other gstack host guidance doc (locate in docs/) | Add `glossary_observations` field description |

### Critical invariant (C-008)

`build_charter_context(... mark_loaded=False)` in `invoke()` must remain unchanged. The chokepoint runs AFTER `build_charter_context()` — do not reorder.

### Invoke sequence after WP03

```
invoke(request_text, profile_hint, actor)
  1. Resolve (profile_id, action)               [existing]
  2. build_charter_context(mark_loaded=False)   [existing]
  3. GlossaryChokepoint.run()                   ← T016, T017 (try/except)
  4. write_started(record)                      [existing]
  5. write_glossary_observation()               ← T019 (best-effort)
  6. propagator.submit()                        [existing]
  7. return InvocationPayload(glossary_observations=bundle)  ← T015
```

---

## Subtask T015 — Extend `InvocationPayload.__slots__` with `"glossary_observations"`

**Purpose:** Add the `glossary_observations` slot so `to_dict()` automatically includes the bundle.

**File:** `src/specify_cli/invocation/executor.py`

**Steps:**

1. Find `InvocationPayload.__slots__` (currently a tuple of string literals).
2. Append `"glossary_observations"` to the tuple:
   ```python
   __slots__ = (
       "invocation_id",
       "profile_id",
       "profile_friendly_name",
       "action",
       "governance_context_text",
       "governance_context_hash",
       "governance_context_available",
       "router_confidence",
       "glossary_observations",    # NEW — GlossaryObservationBundle, always set
   )
   ```
3. `to_dict()` iterates `self.__slots__` — no change needed there. It will automatically include `glossary_observations`.
4. The `__init__` uses `**kwargs` to set all slots. The caller must pass `glossary_observations=<bundle>` — this is done in T016.

**Validation:**
- [ ] `"glossary_observations" in InvocationPayload.__slots__`
- [ ] `InvocationPayload(... glossary_observations=<bundle>).to_dict()["glossary_observations"]` is accessible
- [ ] Existing slots unchanged

---

## Subtask T016 — Add chokepoint call to `ProfileInvocationExecutor.invoke()`

**Purpose:** Instantiate `GlossaryChokepoint` lazily and call `run()` in `invoke()` with a try/except boundary. Build the bundle that will be attached to `InvocationPayload`.

**File:** `src/specify_cli/invocation/executor.py`

**Steps:**

1. In `ProfileInvocationExecutor.__init__()`, add:
   ```python
   self._chokepoint: GlossaryChokepoint | None = None
   ```
   Import `GlossaryChokepoint` lazily inside the method body (not at module top) to avoid circular imports:
   ```python
   # At the top of the file (type-checking only):
   from __future__ import annotations
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from specify_cli.glossary.chokepoint import GlossaryChokepoint, GlossaryObservationBundle
   ```

2. In `invoke()`, after step 2 (`build_charter_context`) and before step 3 (`write_started`), insert:
   ```python
   # Step 3: Run glossary chokepoint (non-blocking, never raises to caller)
   from specify_cli.glossary.chokepoint import GlossaryChokepoint, GlossaryObservationBundle
   try:
       if self._chokepoint is None:
           self._chokepoint = GlossaryChokepoint(self._repo_root)
       bundle = self._chokepoint.run(request_text, invocation_id=invocation_id)
   except Exception as _exc:  # noqa: BLE001
       import logging as _logging
       _logging.getLogger(__name__).warning(
           "glossary chokepoint outer exception (invocation_id=%r): %r",
           invocation_id, _exc,
       )
       bundle = GlossaryObservationBundle(
           matched_urns=(), high_severity=(), all_conflicts=(),
           tokens_checked=0, duration_ms=0.0, error_msg=repr(_exc),
       )
   ```

3. Pass `bundle` to `InvocationPayload(... glossary_observations=bundle)` at the return (step 7).

**Validation:**
- [ ] `invoke()` returns `InvocationPayload` with `glossary_observations` set
- [ ] Any exception in chokepoint path returns an error-bundle, not a raised exception
- [ ] `build_charter_context(mark_loaded=False)` call unchanged (C-008)

---

## Subtask T017 — Implement severity routing in the bundle

**Purpose:** Ensure `bundle.high_severity` contains only `Severity.HIGH` conflicts and `bundle.all_conflicts` contains all findings. This is already implemented in `GlossaryChokepoint.run()` (WP02), but verify the contract here.

**File:** `src/specify_cli/invocation/executor.py`

**Steps:**

1. After the chokepoint call in T016, add an assertion comment (documentation-level):
   ```python
   # Severity routing contract (see spec FR-011, FR-012):
   # bundle.high_severity → surfaced inline to host via InvocationPayload
   # bundle.all_conflicts → written to JSONL trail in T019
   # No further filtering needed here — GlossaryChokepoint.run() already split by severity.
   ```
2. Confirm by reading `GlossaryChokepoint.run()` in `chokepoint.py`:
   ```python
   high_severity = tuple(c for c in all_conflicts if c.severity == Severity.HIGH)
   ```
   The filtering happens in `run()`, not here. WP03's job is to pass the bundle through unchanged.

**Validation:**
- [ ] `bundle.high_severity` contains only `Severity.HIGH` conflicts (verified in WP02 unit tests)
- [ ] `bundle.all_conflicts` contains all conflicts of all severities
- [ ] No additional filtering occurs in executor.py

---

## Subtask T018 — Add `write_glossary_observation()` to `InvocationWriter`

**Purpose:** Append a `"glossary_checked"` JSON line to the per-invocation JSONL file. Best-effort: all exceptions silently suppressed (same pattern as `_append_to_index()`).

**File:** `src/specify_cli/invocation/writer.py`

**Steps:**

1. Import the bundle type at the top (type-checking only to avoid circular imports):
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from specify_cli.glossary.chokepoint import GlossaryObservationBundle
   ```

2. Add method to `InvocationWriter`:
   ```python
   def write_glossary_observation(
       self,
       invocation_id: str,
       bundle: "GlossaryObservationBundle",
   ) -> None:
       """Append a 'glossary_checked' event to the invocation's JSONL file.

       Best-effort: all exceptions silently suppressed.
       Only writes if the bundle contains conflicts or an error.
       """
       # Skip clean invocations to avoid noise in the trail
       if not bundle.all_conflicts and bundle.error_msg is None:
           return
       try:
           path = self.invocation_path(invocation_id)
           if not path.exists():
               return  # invocation file must exist (write_started called first)
           entry: dict[str, object] = {
               "event": "glossary_checked",
               "invocation_id": invocation_id,
           }
           entry.update(bundle.to_dict())
           import json
           with path.open("a", encoding="utf-8") as f:
               f.write(json.dumps(entry) + "\n")
       except OSError:
           pass  # best-effort
   ```

**Key design note:** Only write if `bundle.all_conflicts` is non-empty OR `bundle.error_msg` is set. Clean invocations (no conflicts, no errors) do NOT append a `"glossary_checked"` line — this avoids trail noise.

**Validation:**
- [ ] Method exists and is callable
- [ ] Called with empty bundle → no file write (trail stays at 1 line)
- [ ] Called with a conflict bundle → appends a third line with `"event": "glossary_checked"`
- [ ] Raises no exception even if the invocation file doesn't exist (returns early)

---

## Subtask T019 — Wire `write_glossary_observation()` into `invoke()`

**Purpose:** After `write_started()`, call `write_glossary_observation()` (best-effort).

**File:** `src/specify_cli/invocation/executor.py`

**Steps:**

Insert after `self._writer.write_started(record)` (step 4 in the sequence):

```python
# Step 5: Write glossary observation to trail (best-effort)
try:
    self._writer.write_glossary_observation(invocation_id, bundle)
except Exception:  # noqa: BLE001
    pass  # trail write failure never blocks invocation
```

**Validation:**
- [ ] `write_glossary_observation()` is called after `write_started()`
- [ ] A filesystem error in `write_glossary_observation()` does not propagate to the caller
- [ ] The invocation completes normally regardless of trail write outcome

---

## Subtask T020 — Update Codex host guidance [parallel with T021, T022]

**Purpose:** Document the `glossary_observations` field and the rendering contract for the Codex host path (FR-014).

**File:** `docs/how-to/setup-codex-spec-kitty-launcher.md`

**Steps:**

1. Read the file to find the appropriate section (look for "InvocationPayload", "response", or "output" sections).
2. Add or update a section describing the `glossary_observations` field:

   ```markdown
   ## Glossary Observations (Phase 5+)

   When a project has active glossary terms, `spec-kitty advise/ask/do` returns a
   `glossary_observations` field in the invocation payload. Codex hosts should:

   ### Rendering contract

   1. Read `payload["glossary_observations"]["conflicts"]` — filter for `"severity": "high"`.
   2. If any high-severity conflicts exist, **prepend** an inline warning block before
      the governance context:

      ```
      ⚠ Glossary conflict detected:
        "<term>" — <conflict_type> (confidence: <confidence>)
        Use the canonical Spec Kitty term to avoid governance drift.
      ```

   3. Low and medium severity conflicts are written to the local invocation trail only.
      Do not render them inline.

   4. If `payload["glossary_observations"]["error_msg"]` is non-null:
      Log a warning but do not block execution. The invocation still carries valid
      governance context.

   5. If `payload["glossary_observations"]` is absent (pre-Phase 5 Spec Kitty):
      Continue normally with no glossary check.

   ### Example payload fragment

   ```json
   {
     "glossary_observations": {
       "matched_urns": ["glossary:d93244e7"],
       "high_severity_count": 1,
       "all_conflict_count": 1,
       "tokens_checked": 12,
       "duration_ms": 8.3,
       "error_msg": null,
       "conflicts": [
         {
           "urn": "glossary:d93244e7",
           "term": "lane",
           "conflict_type": "inconsistent",
           "severity": "high",
           "confidence": 0.85,
           "context": "request_text"
         }
       ]
     }
   }
   ```
   ```

3. Commit-level note: this doc change is purely additive (new section).

**Validation:**
- [ ] File updated with the `glossary_observations` rendering contract
- [ ] High-severity rendering example included
- [ ] `error_msg` handling documented

---

## Subtask T021 — Find and update gstack host guidance [parallel with T020, T022]

**Purpose:** Apply the same rendering contract update for the gstack host path.

**Steps:**

1. Search for the gstack guidance doc:
   ```bash
   grep -r "gstack" docs/ --include="*.md" -l
   grep -r "invocation" docs/ --include="*.md" -l | grep -v trail-model
   ```
2. If a gstack-specific guidance doc is found (e.g., `docs/how-to/setup-gstack-spec-kitty.md` or `docs/explanation/ai-agent-architecture.md`), add the same rendering contract section as T020.
3. If no gstack-specific doc exists, create `docs/how-to/setup-gstack-glossary-observations.md` with:
   - The rendering contract (same content as T020, adapted for gstack context)
   - A note that gstack reads `InvocationPayload.to_dict()["glossary_observations"]`
4. Do not add the gstack doc path to `owned_files` retroactively — note the actual path in the commit message.

**Validation:**
- [ ] Gstack guidance contains the `glossary_observations` rendering contract
- [ ] High-severity inline rendering described
- [ ] `error_msg` handling described

---

## Subtask T022 — Update `docs/trail-model.md` [parallel with T020, T021]

**Purpose:** Document the new `"glossary_checked"` event type under Tier 1.

**File:** `docs/trail-model.md`

**Steps:**

1. Find the Tier 1 section (around "Every Invocation (mandatory)").
2. Add a subsection or note:

   ```markdown
   ### Glossary Check Event (conditional, Tier 1)

   When a profile invocation detects glossary conflicts or a chokepoint error, a
   third line is appended to the same invocation JSONL file:

   ```
   .kittify/events/profile-invocations/{invocation_id}.jsonl
   ```

   The third line has `"event": "glossary_checked"` and contains:
   - `matched_urns`: list of `glossary:<id>` URNs found in the request text
   - `high_severity_count`: number of conflicts surfaced inline to the host
   - `all_conflict_count`: total conflicts detected (including low/medium, trail-only)
   - `tokens_checked`: number of tokens the chokepoint examined
   - `duration_ms`: chokepoint execution time
   - `error_msg`: non-null if the chokepoint failed internally

   **Clean invocations** (no conflicts, no errors) do NOT produce a `"glossary_checked"`
   line. The absence of this event means the chokepoint ran cleanly with no findings.

   Readers that do not recognise the `"glossary_checked"` event type may safely skip it.
   The `"started"` and `"completed"` event contract is unchanged.
   ```

**Validation:**
- [ ] `docs/trail-model.md` updated with the `"glossary_checked"` event documentation
- [ ] Clean-invocation behavior (no line written) is explicitly documented
- [ ] Backward-compat note for readers that don't know the new event type

---

## Subtask T023 — Run full e2e suite; fix breakages from new `to_dict()` key

**Purpose:** The new `"glossary_observations"` slot appears in `InvocationPayload.to_dict()`. Any test asserting the exact dict keys/contents will fail. Find and fix those tests.

**Steps:**

1. Run the existing invocation e2e test suite:
   ```bash
   cd /path/to/spec-kitty/repo && pytest tests/merge/test_profile_charter_e2e.py -v
   pytest tests/specify_cli/invocation/ -v
   ```
2. For each failing test:
   - If it asserts `payload.to_dict() == {...}` (exact match), add `"glossary_observations": ...` to the expected dict, OR change the assertion to use `payload.to_dict().get("invocation_id")` (key-specific check) to avoid tight coupling.
   - If it asserts `"glossary_observations" not in payload.to_dict()`, update the expectation.
3. Do NOT modify any test file outside `tests/specify_cli/invocation/` and `tests/merge/test_profile_charter_e2e.py` without checking with the reviewer first.

**Expected outcome:** All pre-existing tests pass; no new failures.

**Validation:**
- [ ] `pytest tests/merge/test_profile_charter_e2e.py` passes
- [ ] `pytest tests/specify_cli/invocation/` passes
- [ ] No tests deleted — only updated to account for the new key

---

## Subtask T024 — Write 3-event JSONL integration test

**Purpose:** Verify the full invoke() → trail-write path produces a JSONL file with the expected three events: `started`, `glossary_checked`, `completed`.

**File:** `tests/specify_cli/invocation/test_executor_glossary.py` (new)

**Implementation:**

```python
"""Integration tests for GlossaryChokepoint wiring in ProfileInvocationExecutor."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch


def _make_executor(tmp_path: Path):
    """Build a ProfileInvocationExecutor with stubs for registry, router, propagator."""
    from specify_cli.invocation.executor import ProfileInvocationExecutor
    from specify_cli.invocation.registry import ProfileRegistry
    from specify_cli.invocation.router import ActionRouter

    executor = ProfileInvocationExecutor.__new__(ProfileInvocationExecutor)
    executor._repo_root = tmp_path
    executor._chokepoint = None
    # Stub registry and router
    mock_profile = MagicMock()
    mock_profile.profile_id = "test-profile"
    mock_profile.name = "Test Profile"
    mock_profile.role = None
    mock_registry = MagicMock(spec=ProfileRegistry)
    mock_registry.resolve.return_value = mock_profile
    mock_router = MagicMock(spec=ActionRouter)
    mock_router.route.return_value = MagicMock(
        profile_id="test-profile", action="advise", confidence="exact"
    )
    from specify_cli.invocation.writer import InvocationWriter
    executor._registry = mock_registry
    executor._router = mock_router
    executor._writer = InvocationWriter(tmp_path)
    executor._propagator = None
    return executor


def test_invoke_payload_has_glossary_observations(tmp_path):
    executor = _make_executor(tmp_path)
    with patch("charter.context.build_charter_context") as mock_ctx:
        mock_ctx.return_value = MagicMock(text="ctx", mode="bootstrap")
        payload = executor.invoke("what is the status of WP01", actor="test")
    assert hasattr(payload, "glossary_observations")
    bundle = payload.glossary_observations
    assert bundle is not None
    assert bundle.tokens_checked >= 0


def test_invoke_to_dict_includes_glossary_key(tmp_path):
    executor = _make_executor(tmp_path)
    with patch("charter.context.build_charter_context") as mock_ctx:
        mock_ctx.return_value = MagicMock(text="ctx", mode="bootstrap")
        payload = executor.invoke("advise on next step", actor="test")
    d = payload.to_dict()
    assert "glossary_observations" in d


def test_invoke_with_chokepoint_exception_returns_error_bundle(tmp_path):
    """Chokepoint failure must not prevent invocation completion."""
    executor = _make_executor(tmp_path)
    # Inject broken chokepoint
    broken_cp = MagicMock()
    broken_cp.run.side_effect = RuntimeError("simulated failure")
    executor._chokepoint = broken_cp

    with patch("charter.context.build_charter_context") as mock_ctx:
        mock_ctx.return_value = MagicMock(text="ctx", mode="bootstrap")
        payload = executor.invoke("test request", actor="test")

    bundle = payload.glossary_observations
    assert bundle.error_msg is not None
    assert bundle.matched_urns == ()
    assert payload.invocation_id is not None  # invocation still completed


def test_clean_invocation_has_only_started_event(tmp_path):
    """A clean invocation (no conflicts) must NOT write a glossary_checked trail line."""
    executor = _make_executor(tmp_path)
    # Inject clean chokepoint (empty bundle, no conflicts)
    from specify_cli.glossary.chokepoint import GlossaryObservationBundle
    clean_bundle = GlossaryObservationBundle(
        matched_urns=(), high_severity=(), all_conflicts=(),
        tokens_checked=5, duration_ms=1.0,
    )
    clean_cp = MagicMock()
    clean_cp.run.return_value = clean_bundle
    executor._chokepoint = clean_cp

    with patch("charter.context.build_charter_context") as mock_ctx:
        mock_ctx.return_value = MagicMock(text="ctx", mode="bootstrap")
        payload = executor.invoke("clean request text", actor="test")

    events_dir = tmp_path / ".kittify" / "events" / "profile-invocations"
    jsonl_file = events_dir / f"{payload.invocation_id}.jsonl"
    lines = jsonl_file.read_text().strip().splitlines()
    events = [json.loads(l)["event"] for l in lines]
    assert events == ["started"]  # no glossary_checked for clean invocation


def test_conflict_invocation_writes_glossary_checked_event(tmp_path):
    """An invocation with a conflict must write a glossary_checked trail line."""
    executor = _make_executor(tmp_path)
    from specify_cli.glossary.chokepoint import GlossaryObservationBundle
    from specify_cli.glossary.models import (
        ConflictType, SemanticConflict, Severity, TermSurface
    )
    conflict = SemanticConflict(
        term=TermSurface("lane"),
        conflict_type=ConflictType.INCONSISTENT,
        severity=Severity.HIGH,
        confidence=0.9,
    )
    conflict_bundle = GlossaryObservationBundle(
        matched_urns=("glossary:d93244e7",),
        high_severity=(conflict,),
        all_conflicts=(conflict,),
        tokens_checked=10,
        duration_ms=5.0,
    )
    conflict_cp = MagicMock()
    conflict_cp.run.return_value = conflict_bundle
    executor._chokepoint = conflict_cp

    with patch("charter.context.build_charter_context") as mock_ctx:
        mock_ctx.return_value = MagicMock(text="ctx", mode="bootstrap")
        payload = executor.invoke("move the task to a new lane", actor="test")

    events_dir = tmp_path / ".kittify" / "events" / "profile-invocations"
    jsonl_file = events_dir / f"{payload.invocation_id}.jsonl"
    lines = jsonl_file.read_text().strip().splitlines()
    events = [json.loads(l)["event"] for l in lines]
    assert "started" in events
    assert "glossary_checked" in events
    glossary_event = next(json.loads(l) for l in lines if json.loads(l)["event"] == "glossary_checked")
    assert glossary_event["high_severity_count"] == 1
```

**Validation:**
- [ ] All 5 test functions pass
- [ ] The 3-event test (T024's final test) confirms `started` + `glossary_checked` in trail
- [ ] Clean invocation test confirms NO `glossary_checked` line
- [ ] `mypy --strict` on the test file → zero errors

---

## Definition of Done

- [ ] `InvocationPayload.__slots__` includes `"glossary_observations"` (T015)
- [ ] `ProfileInvocationExecutor.invoke()` calls `GlossaryChokepoint.run()` with try/except (T016)
- [ ] `bundle.high_severity` correctly contains only `Severity.HIGH` findings (T017, verified by WP02)
- [ ] `InvocationWriter.write_glossary_observation()` exists and is best-effort (T018)
- [ ] `invoke()` calls `write_glossary_observation()` after `write_started()` (T019)
- [ ] `docs/how-to/setup-codex-spec-kitty-launcher.md` updated with rendering contract (T020)
- [ ] Gstack host guidance updated (T021)
- [ ] `docs/trail-model.md` updated with `"glossary_checked"` event type (T022)
- [ ] Existing invocation e2e suite passes (T023)
- [ ] `tests/specify_cli/invocation/test_executor_glossary.py` exists and all tests pass (T024)
- [ ] `mypy --strict src/specify_cli/invocation/executor.py src/specify_cli/invocation/writer.py` → zero errors
- [ ] `ruff check` passes on all modified files

## Reviewer Guidance

1. Confirm `mark_loaded=False` in the `build_charter_context()` call is unchanged (C-008).
2. Verify the chokepoint call is AFTER `build_charter_context()` and BEFORE `write_started()`.
3. Verify `write_glossary_observation()` is AFTER `write_started()`.
4. Run the 3-event integration test manually and inspect the `.jsonl` file directly.
5. Confirm clean invocations (no conflicts) do NOT produce a `"glossary_checked"` trail line.
6. Read the Codex guidance update — confirm the inline rendering contract is clearly described.
7. Confirm no import cycle was introduced: `invocation.executor` → `glossary.chokepoint` should be a forward-import-only dependency (inside method body, not at module top).
