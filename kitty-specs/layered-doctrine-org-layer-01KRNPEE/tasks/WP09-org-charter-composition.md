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
- T046
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

**Files**: `src/charter/interview.py` (modify), `src/specify_cli/cli/commands/charter.py` (minor wiring)

**Purpose**: Before the interactive interview starts, inject org charter defaults into the
interview answers so they appear pre-filled but remain modifiable.

**In `charter.py`'s `interview()` function**, after `repo_root` is resolved but before the
interactive prompts begin:

```python
from specify_cli.doctrine.org_charter import load_org_charter_policies

org_policy = load_org_charter_policies(repo_root)
if org_policy.interview_defaults or org_policy.required_directives:
    # Pre-fill interview answers file with org defaults
    _apply_org_charter_pre_fill(repo_root, org_policy)
```

**`_apply_org_charter_pre_fill(repo_root, policy)`** (new helper, in `charter.py`):
1. Load existing `answers.yaml` if it exists (or start empty).
2. For each key in `policy.interview_defaults`: if the key is NOT already set in `answers.yaml`,
   set it to the org default. (Do not overwrite an answer the user has already given.)
3. For `policy.required_directives`: union into the existing `selected_directives` list.
4. Write back to `answers.yaml`.

**Important**: this is a non-destructive pre-fill. If `answers.yaml` already has a value for
a key, the org default does NOT overwrite it. This ensures running `charter interview` a
second time (to update answers) does not silently revert project-specific choices.

**Human output**: if any pre-fills were applied, print a summary before the interactive
prompts begin:
```
[org charter] Pre-filled 3 interview defaults from 'security' pack.
[org charter] Pre-selected 2 directives from 'security' pack required_directives.
```

---

## Subtask T046 — Org charter elements in `charter context --json`

**File**: `src/charter/context.py` (owned by WP07 — coordinate with WP07 implementer)

**Note**: `context.py` is owned by WP07. This subtask adds org charter data to the context
JSON output. Implement as a separate helper that WP07 wires into `context.py`, or implement
directly if WP07 is already merged.

Add an `"org_charter"` key to the `charter context --json` output:

```json
{
  "org_charter": {
    "present": true,
    "packs": [
      {
        "pack_name": "security",
        "governance_policies": [
          {"field": "human_in_command", "value": true, "enforcement": "advisory"}
        ],
        "required_directives": ["sec-001-threat-modelling"]
      }
    ]
  }
}
```

If no org packs are configured or none have `org-charter.yaml`, `"org_charter": {"present": false}`.

Source attribution: `"source": "org"` on each governance policy entry.

**Implementation**:
1. Call `load_org_charter_policies(repo_root)` to get the merged policy.
2. Also call `load_doctrine_org_config(repo_root)` to get per-pack names for attribution.
3. Serialise per pack (not just the merged result) so operators can see which pack contributes which policy.

The existing JSON output structure must not change — `"org_charter"` is a new top-level key,
additive only.

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
- [ ] `load_org_charter_policies()` correctly merges N packs in declaration order
- [ ] `charter interview` prints pre-fill summary and applies defaults non-destructively
- [ ] `charter context --json` includes `"org_charter"` key (present/absent + per-pack detail)
- [ ] All tests in `test_org_charter.py` pass
- [ ] Projects without `doctrine.org.packs` config: `load_org_charter_policies()` returns empty policy; `charter interview` behaves identically to today

## Risks

- The pre-fill writes to `answers.yaml` before the interactive session. If `charter interview` is
  interrupted midway, the pre-fill is already written. This is acceptable — re-running the interview
  should be idempotent. Test the re-run case explicitly.
- `context.py` is owned by WP07; coordinate to avoid merge conflicts on the `"org_charter"` key
  addition. WP09 should merge after WP07.

## Reviewer Guidance

1. Confirm pre-fill is truly non-destructive: a second `charter interview` on a project with
   existing answers does not revert any project-specific choice to the org default.
2. Confirm `load_org_charter_policies()` with zero configured packs returns an empty policy
   (not `None`, not an error) — this is the zero-effect backward-compat guarantee.
3. Confirm the `"org_charter"` JSON key is additive — existing `charter context --json`
   consumers see no breaking change.
