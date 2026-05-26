---
work_package_id: WP11
title: 'Wave A LD-2: parametrise augmentation field tests (FR-008, stretch)'
dependencies: []
requirement_refs:
- FR-008
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: 5187f101c48a18347b5f382ffc151b3045e600c8
created_at: '2026-05-25T14:47:29.032251+00:00'
subtasks:
- T034
- T035
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1939171"
history:
- by: claude
  at: '2026-05-25T14:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: tests/doctrine/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- tests/doctrine/test_augmentation_fields.py
- tests/doctrine/test_tactic_augmentation_fields.py
- tests/doctrine/test_styleguide_augmentation_fields.py
- tests/doctrine/test_paradigm_augmentation_fields.py
- tests/doctrine/test_procedure_augmentation_fields.py
- tests/doctrine/test_agent_profile_augmentation_fields.py
priority: P2
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Pure test-refactor work.

## Objective

Consolidate the 5 per-kind augmentation field test files (`tests/doctrine/test_{tactic,styleguide,paradigm,procedure,agent_profile}_augmentation_fields.py`) — each ~50 lines, each covering the same 4 cases (neither/enhances-only/overrides-only/both) — into a single parametrised `tests/doctrine/test_augmentation_fields.py`.

This closes LD-2 from the architectural review.

**Stretch WP**: per NFR-004, drops out if WP count exceeds 10. Independent of WP05-08, so parallel-safe.

## Branch strategy

- Planning base branch: mission lane branch
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- [`spec.md`](../spec.md) FR-008 (stretch).
- [`docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`](../../../docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md) §2 LD-2.
- Existing source: 5 test files at `tests/doctrine/test_*_augmentation_fields.py`. Each tests the cross-field validator `_augmentation_intent_is_exclusive` against a different Pydantic model.

## Subtask details

### T034 — Author the parametrised test

Create `tests/doctrine/test_augmentation_fields.py`:

```python
"""Cross-field validator for ``overrides``/``enhances`` on 5 doctrine artifact kinds.

Consolidates the per-kind test files (LD-2 in the architectural review). The
parametrisation matrix encodes one row per artifact kind; each row's fixture
supplies a model class, a minimal valid sample YAML, and the kind name used in
the validator's error message.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from doctrine.tactics.models import Tactic
from doctrine.styleguides.models import Styleguide
from doctrine.paradigms.models import Paradigm
from doctrine.procedures.models import Procedure
from doctrine.agent_profiles.profile import AgentProfile


# (model_class, sample_minimal_yaml_dict, kind_name_in_error_message)
AUGMENTATION_MATRIX = [
    pytest.param(
        Tactic,
        {"id": "sample-tactic", "schema_version": "1.0", "name": "Sample", "steps": [{"title": "step"}]},
        "tactic",
        id="tactic",
    ),
    pytest.param(
        Styleguide,
        # ... minimal valid styleguide
        "styleguide",
        id="styleguide",
    ),
    pytest.param(
        Paradigm,
        # ... minimal valid paradigm
        "paradigm",
        id="paradigm",
    ),
    pytest.param(
        Procedure,
        # ... minimal valid procedure
        "procedure",
        id="procedure",
    ),
    pytest.param(
        AgentProfile,
        # ... minimal valid agent profile (note: uses profile_id, not id)
        "agent_profile",
        id="agent_profile",
    ),
]


@pytest.mark.parametrize("model_cls, sample, kind", AUGMENTATION_MATRIX)
def test_neither_field_set_loads(model_cls, sample, kind):
    """Backward compatibility — existing fixtures without overrides/enhances still load."""
    model_cls(**sample)


@pytest.mark.parametrize("model_cls, sample, kind", AUGMENTATION_MATRIX)
def test_enhances_only_loads(model_cls, sample, kind):
    """Pack author declares augmentation intent."""
    model_cls(**{**sample, "enhances": f"some-built-in-{kind}"})


@pytest.mark.parametrize("model_cls, sample, kind", AUGMENTATION_MATRIX)
def test_overrides_only_loads(model_cls, sample, kind):
    """Pack author declares replacement intent."""
    model_cls(**{**sample, "overrides": f"some-built-in-{kind}"})


@pytest.mark.parametrize("model_cls, sample, kind", AUGMENTATION_MATRIX)
def test_both_set_raises(model_cls, sample, kind):
    """Mutual exclusion — both fields together is an error."""
    with pytest.raises(ValidationError) as exc_info:
        model_cls(**{**sample, "overrides": "x", "enhances": "y"})
    assert "mutually exclusive" in str(exc_info.value)
    assert kind in str(exc_info.value)
```

You may need to adjust the sample-YAML dicts per the actual minimal-valid shape of each model (verify against mission #122 WP05's per-kind test files which encoded these).

### T035 — Delete the 5 per-kind test files

```bash
git rm tests/doctrine/test_tactic_augmentation_fields.py
git rm tests/doctrine/test_styleguide_augmentation_fields.py
git rm tests/doctrine/test_paradigm_augmentation_fields.py
git rm tests/doctrine/test_procedure_augmentation_fields.py
git rm tests/doctrine/test_agent_profile_augmentation_fields.py
```

Run pytest to verify count parity:
```bash
PWHEADLESS=1 .venv/bin/pytest tests/doctrine/test_augmentation_fields.py -v 2>&1 | tail -10
```

Expected: 20 test cases collected (4 cases × 5 kinds). All pass.

## Definition of Done

- [ ] `tests/doctrine/test_augmentation_fields.py` exists with the parametrised matrix.
- [ ] The 5 old per-kind test files are deleted.
- [ ] `pytest tests/doctrine/test_augmentation_fields.py -v` reports ≥ 20 test cases, all pass.
- [ ] Each of the 4 cases covers all 5 artifact kinds.
- [ ] `ruff check tests/doctrine/test_augmentation_fields.py` clean.

## Risks

- **Sample-YAML minimal shape**: each model has different required fields. If the parametrise fixtures aren't minimal-valid, the `test_neither_field_set_loads` case will fail across the board.
- **AgentProfile uses `profile_id`**: that model has a different identifier field name. Adjust the fixture sample for that row.

## Reviewer guidance

1. Verify test count = 20 (4 × 5).
2. Confirm the 5 old files no longer exist (`ls tests/doctrine/test_*_augmentation_fields.py` returns only the consolidated file).
3. Spot-check the error-message assertion for the AgentProfile row — its error message uses `profile_id` substitution, not `id`.

## Activity Log

- 2026-05-25T14:47:29Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1920014 – Assigned agent via action command
- 2026-05-25T14:51:29Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1920014 – LD-2 augmentation tests parametrised; 5 files → 1 file
- 2026-05-25T14:52:00Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1939171 – Started review via action command
- 2026-05-25T14:53:40Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1939171 – Review passed: 20/20 parametrised tests, 5 old files deleted, ~91 LOC saved
