---
work_package_id: WP09
title: Org Charter Composition
dependencies:
- WP05
- WP07
requirement_refs:
- FR-023
- FR-025
- FR-026
- FR-027
- FR-028
- FR-029
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T042
- T043
- T050
agent: codex
history:
- date: '2026-05-15'
  event: created
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/doctrine/org_charter.py
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/org_charter.py
- src/charter/interview.py
- tests/specify_cli/doctrine/test_org_charter.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load architect-alphonso
```

This WP defines a new composition model (charter + org layer). The architect profile helps
ensure the interface design is clean and consistent with the broader multi-pack architecture.

---

## Objective

Implement tiered charter composition: an org pack may include `org-charter.yaml` declaring
governance policy that applies to all projects on the machine. Specifically:

1. `OrgCharterPolicy` — Pydantic model for `org-charter.yaml`
2. `load_org_charter_policies(repo_root)` — loads and merges policies from all configured packs
3. Charter interview pre-fill — `charter interview` pre-fills answers from org defaults
4. `charter context --json` — includes org charter governance elements with source attribution

Advisory lint (T047) and doctor listing (T048) for org charter are implemented in WP07 using
`load_org_charter_policies()` from this WP.

Enforcement in this mission is **advisory-only**. No hard errors or workflow blocks are
produced for org charter policy deviations.

---

## Context

The org pack directory may contain an `org-charter.yaml` at its root alongside `directives/`,
`tactics/`, etc. This file is optional; packs without it contribute only doctrine artifacts.

`org-charter.yaml` schema:

```yaml
schema_version: "1"
org_name: "Acme Corp — Security Baseline"

interview_defaults:
  human_in_command: true
  security_review: "Required for auth/data access missions"
  deployment_policy: "Staging first; production requires human approval"

required_directives:
  - sec-001-threat-modelling
  - sec-002-dependency-scanning

governance_policies:
  - field: "human_in_command"
    value: true
    enforcement: advisory
  - field: "autonomous_mode"
    value: "disallowed"
    enforcement: advisory
```

When multiple packs declare `org-charter.yaml`, they are merged in pack declaration order
(later pack wins on `interview_defaults` key collision; `required_directives` are unioned;
`governance_policies` are concatenated and deduplicated by `field` + `value`).

The charter interview (`src/charter/interview.py`) loads answers from
`.kittify/charter/interview/answers.yaml`. Pre-fill injects org defaults into that file
before the interactive prompts, so they appear as pre-selected but modifiable.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP09 --agent codex`

---

## Subtask T042 — `OrgCharterPolicy` model and `load_org_charter_policies()`

**File**: `src/specify_cli/doctrine/org_charter.py` (new)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel

class GovernancePolicy(BaseModel):
    field: str
    value: str | bool
    enforcement: str = "advisory"   # only "advisory" is active in this mission

class OrgCharterPolicy(BaseModel):
    schema_version: str = "1"
    org_name: str | None = None
    interview_defaults: dict[str, str | bool] = {}
    required_directives: list[str] = []
    governance_policies: list[GovernancePolicy] = []

def load_org_charter_policy(pack_path: Path) -> OrgCharterPolicy | None:
    """Load org-charter.yaml from a single pack root. Returns None if absent."""
    ...

def load_org_charter_policies(repo_root: Path) -> OrgCharterPolicy:
    """Load and merge org-charter.yaml from all configured packs in declaration order.

    Returns a merged OrgCharterPolicy. Returns an empty policy if no packs are
    configured or none have org-charter.yaml.
    """
    ...
```

**Merge semantics** in `load_org_charter_policies()`:
1. Load `PackRegistry` from `load_doctrine_org_config(repo_root)`.
2. For each pack (in declaration order): load `OrgCharterPolicy` from `pack.local_path / "org-charter.yaml"`. Skip packs without the file.
3. Merge: `interview_defaults` — dict update (later pack keys win); `required_directives` — union (preserve order, deduplicate); `governance_policies` — concatenate, deduplicate by `(field, value)` keeping last.
4. Return merged policy. If no packs had `org-charter.yaml`, return `OrgCharterPolicy()` (empty, all defaults).

---

## Subtask T043 — Charter interview pre-fill

**Files**: `src/charter/interview.py` (modify), `src/specify_cli/doctrine/org_charter.py` (add helper)

**Purpose**: Before the interactive interview starts, inject org charter defaults into the
interview answers so they appear pre-filled but remain modifiable.

**Important**: `src/specify_cli/cli/commands/charter.py` is owned by WP07. Do NOT modify it
in this WP. All pre-fill logic lives in `interview.py` and `org_charter.py` (both WP09-owned).
The wiring from `charter.py` into `interview.py` is an existing call — `interview.py` gains
a new early-return hook that `charter.py` does not need to know about.

**Add to `org_charter.py`** — a self-contained pre-fill function:

```python
def apply_org_charter_pre_fill(repo_root: Path) -> list[str]:
    """Non-destructively pre-fill interview answers from configured org charter policies.

    Returns a list of human-readable messages describing what was pre-filled.
    Returns empty list if no org packs are configured or none have org-charter.yaml.
    """
    from specify_cli.doctrine.config import load_pack_registry
    registry = load_pack_registry(repo_root)
    if not registry.packs:
        return []

    merged_policy = load_org_charter_policies(repo_root)
    if not merged_policy.interview_defaults and not merged_policy.required_directives:
        return []

    answers_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"
    yaml = YAML()
    existing: dict = {}
    if answers_path.exists():
        existing = yaml.load(answers_path) or {}

    messages = []
    prefilled = 0
    for key, value in merged_policy.interview_defaults.items():
        if key not in existing:
            existing[key] = value
            prefilled += 1

    existing_directives: list = existing.get("selected_directives", [])
    new_required = [d for d in merged_policy.required_directives if d not in existing_directives]
    if new_required:
        existing["selected_directives"] = existing_directives + new_required
        messages.append(f"Pre-selected {len(new_required)} directives from org charter required_directives.")

    if prefilled:
        messages.append(f"Pre-filled {prefilled} interview defaults from org charter.")

    if messages:
        answers_path.parent.mkdir(parents=True, exist_ok=True)
        yaml.dump(existing, answers_path)

    return messages
```

**Modify `interview.py`**: at the start of the interview flow (before presenting any question
to the user), call `apply_org_charter_pre_fill(repo_root)` and print any returned messages:

```python
from specify_cli.doctrine.org_charter import apply_org_charter_pre_fill

pre_fill_messages = apply_org_charter_pre_fill(repo_root)
for msg in pre_fill_messages:
    console.print(f"[dim][org charter] {msg}[/dim]")
```

Locate the correct injection point in `interview.py` — it should be after `repo_root` is
resolved but before the first question is presented. The pre-fill is a pure YAML side-effect;
it does not change the interactive flow.

**Non-destructive invariant**: if `answers.yaml` already has a value for a key, the org
default does NOT overwrite it. Running `charter interview` a second time on a project with
existing answers must not silently revert project-specific choices to org defaults.

---

## Subtask T050 — Unit tests

**File**: `tests/specify_cli/doctrine/test_org_charter.py` (new)

| Test | Setup | Expected |
|---|---|---|
| `test_load_single_pack_policy` | Pack with valid `org-charter.yaml` | Returns `OrgCharterPolicy` with correct fields |
| `test_load_missing_charter` | Pack with no `org-charter.yaml` | Returns `None` |
| `test_merge_interview_defaults_precedence` | Two packs with overlapping `interview_defaults` key | Last pack wins |
| `test_merge_required_directives_union` | Two packs with overlapping directive IDs | Union, no duplicates |
| `test_merge_governance_policies_dedup` | Two packs with identical `(field, value)` policy | Deduplicated to one |
| `test_load_org_charter_policies_empty` | No packs configured | Returns empty `OrgCharterPolicy()` |
| `test_pre_fill_does_not_overwrite` | Existing `answers.yaml` has a value; org default differs | Existing value preserved |
| `test_pre_fill_sets_missing_keys` | `answers.yaml` missing a key; org default set | Default applied |
| `test_pre_fill_required_directives_union` | `answers.yaml` has `[dir-a]`; org requires `[dir-b]` | Result is `[dir-a, dir-b]` |
| `test_context_json_org_charter_present` | Org pack with `org-charter.yaml` | `"org_charter": {"present": true, ...}` |
| `test_context_json_org_charter_absent` | No org packs | `"org_charter": {"present": false}` |

---

## Definition of Done

- [ ] `OrgCharterPolicy` model validates `schema_version`, `interview_defaults`, `required_directives`, `governance_policies`
- [ ] `apply_org_charter_pre_fill()` in `org_charter.py` is self-contained; does not modify `charter.py`
- [ ] `load_org_charter_policies()` correctly merges N packs in declaration order
- [ ] `charter interview` prints pre-fill summary (from `interview.py` injection point) and applies defaults non-destructively
- [ ] All tests in `test_org_charter.py` pass
- [ ] Projects without `doctrine.org.packs` config: `apply_org_charter_pre_fill()` is a no-op; `charter interview` behaves identically to today

## Risks

- The pre-fill writes to `answers.yaml` before the interactive session. If `charter interview` is
  interrupted midway, the pre-fill is already written. This is acceptable — re-running the interview
  should be idempotent. Test the re-run case explicitly.
- `interview.py` is a complex interactive module; find the correct injection point (before the first
  presented question, after `repo_root` is resolved) and test that the pre-fill message appears in
  the expected position in the output.

## Reviewer Guidance

1. Confirm pre-fill is truly non-destructive: a second `charter interview` on a project with
   existing answers does not revert any project-specific choice to the org default.
2. Confirm `load_org_charter_policies()` with zero configured packs returns an empty policy
   (not `None`, not an error) — this is the zero-effect backward-compat guarantee.
3. Confirm the `"org_charter"` JSON key is additive — existing `charter context --json`
   consumers see no breaking change.
