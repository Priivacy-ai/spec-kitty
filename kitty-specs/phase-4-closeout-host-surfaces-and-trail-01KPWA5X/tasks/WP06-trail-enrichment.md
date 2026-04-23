---
work_package_id: WP06
title: 'Trail Enrichment: Mode Derivation + Correlation + Enforcement'
dependencies:
- WP05
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
- T032
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "21940"
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/modes.py
- src/specify_cli/invocation/record.py
- src/specify_cli/invocation/writer.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/invocation/errors.py
- src/specify_cli/cli/commands/advise.py
- src/specify_cli/cli/commands/do_cmd.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/cli/commands/profiles_cmd.py
- src/specify_cli/cli/commands/invocations_cmd.py
- tests/specify_cli/invocation/test_modes.py
- tests/specify_cli/invocation/test_correlation.py
- tests/specify_cli/invocation/test_invocation_e2e.py
tags: []
---

# WP06 — Trail Enrichment: Mode Derivation + Correlation + Enforcement

## Objective

Implement three coupled changes inside the invocation runtime, all additive and all local-first-preserving:

1. **Mode derivation (FR-008)** — derive `ModeOfWork` from the CLI entry command; record it on the `started` event as an additive optional field.
2. **Correlation contract (FR-007)** — append-only `artifact_link` / `commit_link` events on the invocation JSONL, driven by new `--artifact` (repeatable) / `--commit` (singular) flags on `profile-invocation complete`. Ref-normalisation: repo-relative when under checkout, absolute fallback otherwise.
3. **Tier 2 mode enforcement (FR-009)** — `complete_invocation` reads the started-event mode and rejects `--evidence` on `advisory` / `query` invocations with a typed `InvalidModeForEvidenceError`, before any write.

These three changes are merged into one WP because they share the `src/specify_cli/invocation/` module tree and the `src/specify_cli/cli/commands/advise.py` file (which hosts `advise`, `ask`, and `profile-invocation complete` — non-splittable under the owned_files rule).

## Context

- **Baseline**: Phase 4 core runtime landed + 3.2.0a5 closeout slice. `ProfileInvocationExecutor.invoke` and `complete_invocation` are stable; the Tier 2 `promote_to_evidence` path is already wired.
- **Design records**: [ADR-001](../decisions/ADR-001-correlation-contract.md), [ADR-002](../decisions/ADR-002-mode-derivation.md).
- **Data model**: [data-model.md](../data-model.md) §1–§7.
- **Contracts**: [contracts/profile-invocation-complete.md](../contracts/profile-invocation-complete.md).
- **Invariants** (must all hold after this WP):
  - Tier 1 write (`started`) happens before any new code path executes — no blocking I/O added before `write_started`.
  - No existing JSONL line is mutated (C-004).
  - Propagator sync-gate short-circuit stays before any new policy/mode logic (C-002, FR-012).
  - CLI subcommand topology unchanged (C-008).

## Branch Strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. WP06 depends on WP05 (strict Tranche A → Tranche B).

## Subtask Guidance

### T026 — `modes.py` with `ModeOfWork` + `derive_mode()` + unit tests

**Purpose**: Define the closed-set enum and the deterministic derivation helper; unit-test the derivation table.

**File to create**: `src/specify_cli/invocation/modes.py`

**Module content**:

```python
"""ModeOfWork enum and deterministic derivation from CLI entry command.

See ADR-002-mode-derivation.md for the rationale and acceptance mapping.
"""
from __future__ import annotations

from enum import Enum


class ModeOfWork(str, Enum):
    ADVISORY = "advisory"
    TASK_EXECUTION = "task_execution"
    MISSION_STEP = "mission_step"
    QUERY = "query"


_ENTRY_COMMAND_MODE: dict[str, ModeOfWork] = {
    # Invocation-openers
    "advise": ModeOfWork.ADVISORY,
    "ask": ModeOfWork.TASK_EXECUTION,
    "do": ModeOfWork.TASK_EXECUTION,
    # Mission-step drivers (invoked via `spec-kitty next --agent ...`)
    "next.specify": ModeOfWork.MISSION_STEP,
    "next.plan": ModeOfWork.MISSION_STEP,
    "next.tasks": ModeOfWork.MISSION_STEP,
    "next.implement": ModeOfWork.MISSION_STEP,
    "next.review": ModeOfWork.MISSION_STEP,
    "next.merge": ModeOfWork.MISSION_STEP,
    "next.accept": ModeOfWork.MISSION_STEP,
    # Query commands (no InvocationRecord opened today, but mode is recorded
    # for future use and for enforcement consistency)
    "profiles.list": ModeOfWork.QUERY,
    "invocations.list": ModeOfWork.QUERY,
}


def derive_mode(entry_command: str) -> ModeOfWork:
    """Derive ModeOfWork from a CLI entry command.

    Args:
        entry_command: One of the keys in the _ENTRY_COMMAND_MODE mapping.

    Returns:
        The corresponding ModeOfWork.

    Raises:
        KeyError: if entry_command is not registered. Callers MUST catch and
            surface a clear CLI error — a mistyped entry_command indicates a
            programming error at the CLI layer, not an operator error.
    """
    return _ENTRY_COMMAND_MODE[entry_command]
```

**Unit test file**: `tests/specify_cli/invocation/test_modes.py`

```python
"""Unit tests for derive_mode() from CLI entry command."""
from __future__ import annotations

import pytest

from specify_cli.invocation.modes import ModeOfWork, derive_mode


@pytest.mark.parametrize(
    ("entry_command", "expected"),
    [
        ("advise", ModeOfWork.ADVISORY),
        ("ask", ModeOfWork.TASK_EXECUTION),
        ("do", ModeOfWork.TASK_EXECUTION),
        ("next.specify", ModeOfWork.MISSION_STEP),
        ("next.plan", ModeOfWork.MISSION_STEP),
        ("next.tasks", ModeOfWork.MISSION_STEP),
        ("next.implement", ModeOfWork.MISSION_STEP),
        ("next.review", ModeOfWork.MISSION_STEP),
        ("next.merge", ModeOfWork.MISSION_STEP),
        ("next.accept", ModeOfWork.MISSION_STEP),
        ("profiles.list", ModeOfWork.QUERY),
        ("invocations.list", ModeOfWork.QUERY),
    ],
)
def test_derive_mode_table(entry_command: str, expected: ModeOfWork) -> None:
    assert derive_mode(entry_command) == expected


def test_derive_mode_unknown_raises() -> None:
    with pytest.raises(KeyError):
        derive_mode("not-a-real-command")


def test_mode_enum_str_round_trip() -> None:
    """ModeOfWork is a str-Enum so JSONL round-trip works."""
    assert ModeOfWork.ADVISORY.value == "advisory"
    assert str(ModeOfWork.ADVISORY) in {"ModeOfWork.ADVISORY", "advisory"}
```

### T027 — Extend `InvocationRecord`; thread `mode_of_work` through `executor.invoke`

**Purpose**: Additive optional field on the `started` shape; executor accepts and records it.

**File to modify**: `src/specify_cli/invocation/record.py`

**Change**: add optional field `mode_of_work: str | None = None` to the `InvocationRecord` dataclass/pydantic model. Must serialise such that `None` is omitted from JSON output (the shipped record uses `model_dump()`; ensure `exclude_none=True` is in play or filter in the writer).

**File to modify**: `src/specify_cli/invocation/executor.py`

**Changes**:
- Extend `ProfileInvocationExecutor.invoke(...)` with a new keyword argument `mode_of_work: ModeOfWork | None = None`.
- In the record construction (around `record = InvocationRecord(...)`), set `mode_of_work=mode_of_work.value if mode_of_work else None`.
- Import `ModeOfWork` from `.modes`.

**Invariant check**: the `mark_loaded=False` invariant on `build_charter_context` MUST remain. Do not touch that call.

### T028 — `append_correlation_link()` + `normalise_ref()` in `writer.py`

**Purpose**: Append-only writer method for `artifact_link` / `commit_link` events, with shared ref-normalisation.

**File to modify**: `src/specify_cli/invocation/writer.py`

**Add helper** (module-level function):

```python
def normalise_ref(ref: str, repo_root: Path) -> str:
    """Repo-relative when resolved path is under repo_root; absolute fallback.

    See data-model.md §6.
    """
    try:
        resolved = Path(ref).resolve()
    except (OSError, RuntimeError):
        return ref
    root = repo_root.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(resolved)
```

**Add method** on `InvocationWriter`:

```python
def append_correlation_link(
    self,
    invocation_id: str,
    *,
    kind: str = "artifact",
    ref: str | None = None,
    sha: str | None = None,
    at: str | None = None,
) -> None:
    """Append an artifact_link or commit_link event to the invocation JSONL.

    Exactly one of ``ref`` or ``sha`` must be provided:
    - ``ref`` → ``{"event": "artifact_link", "kind": <kind>, "ref": <ref>, ...}``
    - ``sha`` → ``{"event": "commit_link", "sha": <sha>, ...}``

    Raises:
        InvocationError: if the invocation JSONL does not exist.
        ValueError: if neither or both of ref/sha are supplied.
    """
    if (ref is None) == (sha is None):
        raise ValueError("Exactly one of ref or sha must be provided")
    path = self.invocation_path(invocation_id)
    if not path.exists():
        raise InvocationError(f"Invocation record not found: {invocation_id}")
    at = at or datetime.datetime.now(datetime.UTC).isoformat()
    entry: dict[str, object] = {
        "event": "artifact_link" if ref is not None else "commit_link",
        "invocation_id": invocation_id,
        "at": at,
    }
    if ref is not None:
        entry["kind"] = kind
        entry["ref"] = ref
    else:
        entry["sha"] = sha
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        raise InvocationWriteError(
            f"Failed to append correlation event: {e}"
        ) from e
```

**No changes** to `write_started` or `write_completed` — their invariants stay.

### T029 — `InvalidModeForEvidenceError` + `complete_invocation` enforcement

**Purpose**: Typed error + pre-write enforcement gate for Tier 2 promotion.

**File to modify**: `src/specify_cli/invocation/errors.py`

**Add**:

```python
from specify_cli.invocation.modes import ModeOfWork


class InvalidModeForEvidenceError(InvocationError):
    """--evidence supplied on an invocation whose mode_of_work disallows
    Tier 2 promotion (advisory or query). See FR-009 / ADR-001."""

    def __init__(self, invocation_id: str, mode: ModeOfWork) -> None:
        self.invocation_id = invocation_id
        self.mode = mode
        super().__init__(
            f"Cannot promote evidence on invocation {invocation_id}: "
            f"mode is {mode.value}; Tier 2 evidence is only allowed on "
            f"task_execution or mission_step invocations."
        )
```

**File to modify**: `src/specify_cli/invocation/executor.py::complete_invocation`

**New execution sequence** (replace the existing body while preserving all current behaviours):

```python
def complete_invocation(
    self,
    invocation_id: str,
    outcome: str | None = None,
    evidence_ref: str | None = None,
    artifact_refs: list[str] | None = None,
    commit_sha: str | None = None,
) -> InvocationRecord:
    # Step 1: Read started event for mode enforcement.
    started_mode = self._read_started_mode(invocation_id)

    # Step 2: Enforce mode gate on evidence promotion (FR-009).
    if evidence_ref is not None and started_mode in {ModeOfWork.ADVISORY, ModeOfWork.QUERY}:
        raise InvalidModeForEvidenceError(invocation_id, started_mode)

    # Step 3: Append completed event (existing behaviour).
    completed = self._writer.write_completed(
        invocation_id, self._repo_root,
        outcome=outcome, evidence_ref=evidence_ref,
    )

    # Step 4: Tier 2 evidence promotion (existing behaviour; unchanged).
    if evidence_ref is not None:
        # ... existing path normalisation + promote_to_evidence ...
        ...

    # Step 5 (NEW): Append artifact_link events.
    for raw_ref in artifact_refs or []:
        normalised = normalise_ref(raw_ref, self._repo_root)
        self._writer.append_correlation_link(
            invocation_id, kind="artifact", ref=normalised,
        )

    # Step 6 (NEW): Append commit_link event.
    if commit_sha is not None:
        self._writer.append_correlation_link(
            invocation_id, sha=commit_sha,
        )

    # Step 7: Propagate completed (existing behaviour).
    if self._propagator is not None:
        self._propagator.submit(completed)
    # Also propagate correlation events. Policy (WP07) decides projection.
    # For WP06, submit them; WP07 will add the policy gate.
    # NOTE: if WP07 has not landed yet, _propagate_one projects correlation
    # events unconditionally once auth passes. This is a transient state that
    # WP07 corrects. Tests in WP07 verify the gated behaviour.

    return completed
```

**Helper `_read_started_mode`** — add to executor:

```python
def _read_started_mode(self, invocation_id: str) -> ModeOfWork | None:
    """Read mode_of_work from the started event. Returns None for pre-mission records."""
    path = self._writer.invocation_path(invocation_id)
    if not path.exists():
        raise InvocationError(f"Invocation record not found: {invocation_id}")
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    first = json.loads(first_line)
    raw = first.get("mode_of_work")
    return ModeOfWork(raw) if raw else None
```

### T030 — CLI wiring for advise / ask / do / complete in `advise.py` and `do_cmd.py`

**Purpose**: Thread mode derivation at each CLI entry point and add correlation flags to `complete`.

**File to modify**: `src/specify_cli/cli/commands/advise.py`

**For the `advise` command handler**:
- Import: `from specify_cli.invocation.modes import derive_mode`.
- In the handler, before calling `executor.invoke(...)`, add: `mode = derive_mode("advise")`.
- Pass `mode_of_work=mode` to the `invoke()` call.

**For the `ask` command handler**:
- Same pattern, `derive_mode("ask")`.

**For the `profile_invocation_app.command("complete")` handler**:
- Add two new typer parameters:
  ```python
  artifact: list[str] = typer.Option(
      None,
      "--artifact",
      help="Path (repo-relative or absolute) of an artifact produced by this invocation. Repeatable.",
  ),
  commit: str | None = typer.Option(
      None,
      "--commit",
      help="Git commit SHA most directly produced by this invocation. Singular.",
  ),
  ```
- Pass these into `executor.complete_invocation(... artifact_refs=artifact or [], commit_sha=commit)`.
- Extend the JSON response envelope:
  ```python
  response = {
      "result": "success",
      "invocation_id": invocation_id,
      "outcome": outcome,
      "evidence_ref": completed.evidence_ref,
      "artifact_links": [normalise_ref(a, repo_root) for a in (artifact or [])],
      "commit_link": commit,
  }
  ```
- On `InvalidModeForEvidenceError`, print a `rich`-formatted error and `raise typer.Exit(2)`.

**File to modify**: `src/specify_cli/cli/commands/do_cmd.py`

- Add `derive_mode("do")` before the executor invoke call.
- Pass `mode_of_work=mode` to `executor.invoke(...)`.

### T031 — CLI wiring for query + mission-step paths

**Purpose**: Thread mode for query and mission-step command surfaces.

**Files to modify**:
- `src/specify_cli/cli/commands/profiles_cmd.py` — `profiles list`: no InvocationRecord is opened, but if any path constructs one in the future, it should use `derive_mode("profiles.list")`. Add a comment noting this is the documented mapping and leave a TODO marker for the future use.
- `src/specify_cli/cli/commands/invocations_cmd.py` — same treatment; `derive_mode("invocations.list")` documented as reserved.
- `src/specify_cli/cli/commands/next_cmd.py` — when `next` dispatches a mission-step invocation that opens an InvocationRecord (if such a path exists at baseline; if not, leave a TODO), thread `derive_mode(f"next.{action}")`. Verify by reading the baseline `next_cmd.py` — the current 3.2.0a5 does not open invocations from `next`; the agent handles that out-of-process. Confirm and document.

**Note**: T031 is mostly documentation/placeholder in the 3.2.x baseline. It earns its keep by locking in the naming convention (`next.<action>`) so future work can extend cleanly. Do not invent behaviour that isn't in the baseline.

### T032 — Integration tests

**Purpose**: End-to-end coverage for mode derivation, correlation, enforcement, and backwards compatibility.

**File to create**: `tests/specify_cli/invocation/test_correlation.py`

**Test cases**:

```python
"""FR-007 — append_correlation_link + ref normalisation."""
from pathlib import Path
import json
import subprocess
import pytest

from specify_cli.invocation.writer import InvocationWriter, normalise_ref


def test_normalise_ref_in_checkout(tmp_path: Path) -> None:
    inside = tmp_path / "subdir/file.txt"
    inside.parent.mkdir(parents=True)
    inside.write_text("x")
    assert normalise_ref(str(inside), tmp_path) == "subdir/file.txt"


def test_normalise_ref_outside_checkout(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "out.log"
    elsewhere.write_text("x")
    result = normalise_ref(str(elsewhere), tmp_path)
    assert Path(result).is_absolute()


def test_normalise_ref_verbatim_fallback(tmp_path: Path) -> None:
    # A nonsense path returns verbatim.
    assert normalise_ref("not/a/real/path\x00", tmp_path) == "not/a/real/path\x00"


def test_append_artifact_link_writes_event(tmp_path: Path) -> None:
    # ... set up a writer with a started event; call append_correlation_link ...
    pass  # full fixture in the implementation
```

**File to extend**: `tests/specify_cli/invocation/test_invocation_e2e.py`

**Add test cases**:

1. `test_started_event_records_mode_advisory` — open `advise`, verify `mode_of_work == "advisory"` on the first JSONL line.
2. `test_started_event_records_mode_task_execution` — `ask` + `do` both record `task_execution`.
3. `test_complete_with_two_artifacts_and_commit` — `complete --artifact a --artifact b --commit sha` appends two `artifact_link` events then one `commit_link` event after `completed`.
4. `test_complete_artifact_ref_normalisation_in_checkout` — in-checkout path persists repo-relative.
5. `test_complete_artifact_ref_outside_checkout` — out-of-checkout path persists absolute.
6. `test_complete_rejects_evidence_on_advisory` — `complete --evidence path` on advisory invocation raises `InvalidModeForEvidenceError`; no `completed` event appended; no evidence artifact created.
7. `test_complete_rejects_evidence_on_query` — query-mode invocation rejected similarly.
8. `test_complete_allows_evidence_on_task_execution` — task_execution passes; evidence artifact created as today.
9. `test_complete_allows_evidence_on_mission_step` — mission_step passes.
10. `test_complete_on_pre_mission_record_allows_evidence` — an invocation with no `mode_of_work` field in the started event (legacy) is not rejected.
11. `test_sync_disabled_no_propagation_errors` — with sync disabled, all events written locally; `propagation-errors.jsonl` empty or absent (NFR-007 / SC-008 pre-check for WP07).

Use existing test fixtures as patterns; the baseline test file already exercises `started` + `completed` under sync-disabled conditions.

## Definition of Done

- [ ] `src/specify_cli/invocation/modes.py` exists with `ModeOfWork`, `_ENTRY_COMMAND_MODE`, `derive_mode`.
- [ ] `InvocationRecord` has an additive optional `mode_of_work` field; `None` is omitted from JSON output.
- [ ] `InvocationWriter.append_correlation_link()` + `normalise_ref()` implemented; append-only invariant preserved (C-004).
- [ ] `InvalidModeForEvidenceError` defined in `errors.py`; pre-write enforcement in `complete_invocation`; rejected calls leave no new JSONL lines.
- [ ] CLI wiring for advise/ask/do/complete + do + placeholder wiring for query/next commands.
- [ ] JSON response from `complete` includes `artifact_links` (list) and `commit_link` (str or null).
- [ ] `test_modes.py` and `test_correlation.py` pass; `test_invocation_e2e.py` extended with 11 new cases, all passing.
- [ ] `mypy --strict src/specify_cli/invocation/ src/specify_cli/cli/commands/advise.py src/specify_cli/cli/commands/do_cmd.py` passes.
- [ ] NFR-001 timing check: `started` event write P95 ≤ 5 ms on local FS (extended test asserts).
- [ ] No existing JSONL line mutated in any test scenario.

## Risks

- **Advise.py size creep**: adding flags + mode wiring may push `advise.py` past comfortable reading length. Mitigation: extract CLI helpers into a private module within `src/specify_cli/cli/commands/` if needed (any new file would be WP06-owned).
- **Propagator over-projecting correlation events**: T029 submits correlation events to the propagator; without WP07's policy gate, they project unconditionally to SaaS (for authenticated+sync-enabled checkouts). This is a transient state. Mitigation: WP06 merges before WP07 in the same Tranche B sequence; WP07 immediately follows. Acknowledge the transient overprojection in the commit message so reviewers understand why.
- **Advisory invocations with evidence — partial completed states**: if the operator passes `--evidence` on an advisory invocation, the invocation stays open after rejection. The operator must rerun `complete` without `--evidence`. Test 6 (test_complete_rejects_evidence_on_advisory) verifies this.
- **mypy strict regressions**: adding a new field to `InvocationRecord` may require updating every downstream construction site. Run `mypy --strict` early and fix iteratively.
- **JSONL read race in `_read_started_mode`**: reading `splitlines()[0]` works because the file is append-only and the first line is stable. No locking required.

## Reviewer Guidance

Reviewer should:
- Read `modes.py` end-to-end; confirm the derivation table matches ADR-002.
- Diff `executor.py` to confirm `invoke()` changes are additive (default None) and `complete_invocation` ordering is: read mode → enforce → write completed → promote evidence → append artifact_links → append commit_link → propagate.
- Diff `writer.py` to confirm `append_correlation_link` is append-mode and exists-check-first.
- Run the new test files and confirm all 11 e2e cases plus the correlation + modes units pass.
- Confirm `mypy --strict` is clean.
- Confirm no change to `write_started`, `write_completed`, `promote_to_evidence`, or the sync-gate in `_propagate_one`.
- Confirm the CLI help text for `complete` documents `--artifact` (repeatable) and `--commit` (singular) accurately.

## Activity Log

- 2026-04-23T05:54:34Z – claude:sonnet-4-6:implementer:implementer – shell_pid=19754 – Started implementation via action command
- 2026-04-23T06:03:04Z – claude:sonnet-4-6:implementer:implementer – shell_pid=19754 – Trail enrichment complete: mode derivation, correlation flags, Tier 2 enforcement. All tests green. Mypy strict clean on WP06-owned code. 37 tests pass (14 modes + 8 correlation + 15 e2e).
- 2026-04-23T06:03:24Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=21940 – Started review via action command
