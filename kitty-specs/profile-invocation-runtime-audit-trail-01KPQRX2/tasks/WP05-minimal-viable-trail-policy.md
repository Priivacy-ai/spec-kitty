---
work_package_id: WP05
title: MinimalViableTrailPolicy + Tier Promotion API
dependencies:
- WP01
requirement_refs:
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "14394"
history:
- date: '2026-04-21'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/invocation/record.py
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/record.py
- tests/specify_cli/invocation/test_record.py
tags: []
---

# WP05 — MinimalViableTrailPolicy + Tier Promotion API

## Objective

Finalize the `MinimalViableTrailPolicy` as a frozen dataclass with all three tiers fully
specified, implement `tier_eligible()` and `promote_to_evidence()` helpers, and export
them from the package's public API. This WP answers FR-017 at the code level.

**Implementation command**:
```bash
spec-kitty agent action implement WP05 --agent claude
```

## Branch Strategy

Planning base: `main`. Merge target: `main`.
Execution worktree: allocated by `lanes.json`.

## Context

WP01 created `record.py` with a stub `MINIMAL_VIABLE_TRAIL_POLICY` dict. WP05 replaces
that stub with a proper frozen dataclass and adds the tier eligibility and promotion functions.

This WP runs in parallel with WP02/WP03/WP04 — it only touches `record.py` and its tests.

---

## Subtask T019 — Finalize MinimalViableTrailPolicy

**Purpose**: Replace the stub dict with a proper frozen dataclass carrying all three tier definitions.

**Steps**:

1. In `src/specify_cli/invocation/record.py`, replace the stub with:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class TierPolicy:
    name: str
    mandatory: bool
    description: str
    storage_path: str
    promotion_trigger: str = ""

@dataclass(frozen=True)
class MinimalViableTrailPolicy:
    """
    The three-tier minimal viable trail contract.
    Every Spec Kitty action's audit trail requirements.

    Tier 1 (every_invocation): mandatory. One InvocationRecord in local JSONL before executor returns.
    Tier 2 (evidence_artifact): optional. EvidenceArtifact when invocation produces checkable output.
    Tier 3 (durable_project_state): optional. kitty-specs/ / doctrine artifact only for domain-state changes.
    """
    tier_1: TierPolicy
    tier_2: TierPolicy
    tier_3: TierPolicy

MINIMAL_VIABLE_TRAIL_POLICY = MinimalViableTrailPolicy(
    tier_1=TierPolicy(
        name="every_invocation",
        mandatory=True,
        description=(
            "One InvocationRecord written locally before executor returns. "
            "Applies to all advise / ask / do invocations."
        ),
        storage_path=".kittify/events/profile-invocations/{profile_id}-{invocation_id}.jsonl",
    ),
    tier_2=TierPolicy(
        name="evidence_artifact",
        mandatory=False,
        description=(
            "Optional EvidenceArtifact for invocations that produce checkable output. "
            "Created when caller passes --evidence to profile-invocation complete."
        ),
        storage_path=".kittify/evidence/{invocation_id}/",
        promotion_trigger="caller sets evidence_ref on profile-invocation complete",
    ),
    tier_3=TierPolicy(
        name="durable_project_state",
        mandatory=False,
        description=(
            "Promotion to kitty-specs/ or doctrine artifacts only when invocation "
            "changes project-domain state. Applies to specify, plan, tasks, merge, accept only."
        ),
        storage_path="kitty-specs/{mission_slug}/",
        promotion_trigger="spec, plan, tasks, merge, accept commands only",
    ),
)
```

**Files**: `src/specify_cli/invocation/record.py` (modify the stub section)

---

## Subtask T020 — Tier Eligibility + Evidence Promotion Functions

**Purpose**: `tier_eligible()` determines which tiers an invocation qualifies for. `promote_to_evidence()` creates a Tier 2 artifact.

**Steps**:

1. Add to `record.py`:

```python
from dataclasses import dataclass as _dataclass
from pathlib import Path

@dataclass(frozen=True)
class TierEligibility:
    tier_1: bool = True    # always True — every invocation has Tier 1
    tier_2: bool = False   # True if evidence_ref is set on completed event
    tier_3: bool = False   # True if action is in TIER_3_ACTIONS

# Actions that qualify for Tier 3 (durable project state changes)
TIER_3_ACTIONS: frozenset[str] = frozenset({
    "specify", "plan", "tasks", "merge", "accept",
})

def tier_eligible(record: InvocationRecord) -> TierEligibility:
    """Determine which trail tiers apply to a completed InvocationRecord."""
    return TierEligibility(
        tier_1=True,
        tier_2=record.evidence_ref is not None,
        tier_3=record.action in TIER_3_ACTIONS,
    )


@_dataclass
class EvidenceArtifact:
    invocation_id: str
    directory: Path
    evidence_file: Path
    record_snapshot: Path

def promote_to_evidence(
    record: InvocationRecord,
    evidence_base_dir: Path,
    content: str,
) -> EvidenceArtifact:
    """
    Create a Tier 2 EvidenceArtifact at evidence_base_dir/<invocation_id>/.

    Creates:
      - evidence_base_dir/<invocation_id>/evidence.md  (caller-supplied content)
      - evidence_base_dir/<invocation_id>/record.json  (snapshot of invocation record)
    """
    import json
    artifact_dir = evidence_base_dir / record.invocation_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = artifact_dir / "evidence.md"
    record_file = artifact_dir / "record.json"
    evidence_file.write_text(content, encoding="utf-8")
    record_file.write_text(json.dumps(record.model_dump(), indent=2), encoding="utf-8")
    return EvidenceArtifact(
        invocation_id=record.invocation_id,
        directory=artifact_dir,
        evidence_file=evidence_file,
        record_snapshot=record_file,
    )
```

**Files**: `src/specify_cli/invocation/record.py`

---

## Subtask T021 — Export from `__init__.py` + Extend Tests

**Purpose**: Expose the policy and tier functions via the public package API. Extend `test_record.py` to cover the new functionality.

**Steps**:

1. Update `src/specify_cli/invocation/__init__.py`:
```python
from specify_cli.invocation.record import (
    InvocationRecord,
    MINIMAL_VIABLE_TRAIL_POLICY,
    TierEligibility,
    TierPolicy,
    TIER_3_ACTIONS,
    tier_eligible,
    promote_to_evidence,
    EvidenceArtifact,
)
from specify_cli.invocation.executor import ProfileInvocationExecutor, InvocationPayload
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.writer import InvocationWriter
from specify_cli.invocation.errors import (
    InvocationError,
    ProfileNotFoundError,
    RouterAmbiguityError,
    ContextUnavailableError,
    InvocationWriteError,
)
```

2. Add to `tests/specify_cli/invocation/test_record.py`:

```python
from specify_cli.invocation.record import (
    MINIMAL_VIABLE_TRAIL_POLICY,
    tier_eligible,
    promote_to_evidence,
    InvocationRecord,
    TIER_3_ACTIONS,
)

def test_mvt_policy_is_frozen():
    import pytest
    with pytest.raises(Exception):  # FrozenInstanceError
        MINIMAL_VIABLE_TRAIL_POLICY.tier_1 = None  # type: ignore

def test_mvt_policy_tier_1_is_mandatory():
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_1.mandatory is True
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_2.mandatory is False
    assert MINIMAL_VIABLE_TRAIL_POLICY.tier_3.mandatory is False

def test_tier_eligible_tier1_always_true():
    record = InvocationRecord(event="started", invocation_id="test", profile_id="p", action="implement")
    eligibility = tier_eligible(record)
    assert eligibility.tier_1 is True

def test_tier_eligible_tier2_requires_evidence_ref():
    record_no_ev = InvocationRecord(event="completed", invocation_id="test", profile_id="p", action="implement")
    record_with_ev = InvocationRecord(event="completed", invocation_id="test", profile_id="p", action="implement", evidence_ref=".kittify/evidence/test/")
    assert tier_eligible(record_no_ev).tier_2 is False
    assert tier_eligible(record_with_ev).tier_2 is True

def test_tier_eligible_tier3_for_specify():
    record = InvocationRecord(event="completed", invocation_id="test", profile_id="p", action="specify")
    assert tier_eligible(record).tier_3 is True

def test_tier_eligible_tier3_not_for_advise():
    record = InvocationRecord(event="completed", invocation_id="test", profile_id="p", action="advise")
    assert tier_eligible(record).tier_3 is False

def test_promote_to_evidence_creates_files(tmp_path):
    record = InvocationRecord(
        event="completed", invocation_id="01KPQRX2EVGMRVB4Q1JQBAZJV3",
        profile_id="cleo", action="implement",
    )
    artifact = promote_to_evidence(record, tmp_path, "# Evidence\n\nThis is evidence.")
    assert artifact.evidence_file.exists()
    assert artifact.record_snapshot.exists()
    assert artifact.evidence_file.read_text() == "# Evidence\n\nThis is evidence."

def test_tier3_actions_contains_expected():
    assert "specify" in TIER_3_ACTIONS
    assert "plan" in TIER_3_ACTIONS
    assert "advise" not in TIER_3_ACTIONS
```

**Files**:
- `src/specify_cli/invocation/__init__.py`
- `tests/specify_cli/invocation/test_record.py` (extend)

**Acceptance**:
- [ ] `MINIMAL_VIABLE_TRAIL_POLICY` is a frozen `MinimalViableTrailPolicy` instance
- [ ] All tier tests pass
- [ ] `promote_to_evidence` creates two files in the evidence directory
- [ ] `mypy --strict` clean

## Definition of Done

- [ ] `MINIMAL_VIABLE_TRAIL_POLICY` is a frozen dataclass, not a dict stub
- [ ] `tier_eligible()` and `promote_to_evidence()` are exported from `specify_cli.invocation`
- [ ] All new tests pass
- [ ] `mypy --strict` clean on `record.py`

## Risks

- **Frozen dataclass mutation attempt**: Python's `FrozenInstanceError` is raised on attribute assignment. The test confirms this. If using `@dataclass(frozen=True)`, assignment raises `FrozenInstanceError` (a subclass of `AttributeError`), not `TypeError`. Check the exact exception type in the test.

## Reviewer Guidance

1. Verify `MINIMAL_VIABLE_TRAIL_POLICY` is a frozen dataclass instance, not a dict.
2. Verify `tier_3` only triggers for actions in `TIER_3_ACTIONS` — not for `advise`, `ask`, `do`.
3. Verify `promote_to_evidence` creates exactly two files and nothing else.
4. Verify `__init__.py` exports are complete (all public symbols listed).

## Activity Log

- 2026-04-21T12:35:23Z – claude:sonnet-4-6:implementer:implementer – shell_pid=6359 – Started implementation via action command
- 2026-04-21T12:37:51Z – claude:sonnet-4-6:implementer:implementer – shell_pid=6359 – WP05 complete: MinimalViableTrailPolicy + tier_eligible + promote_to_evidence
- 2026-04-21T12:38:08Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=14394 – Started review via action command
