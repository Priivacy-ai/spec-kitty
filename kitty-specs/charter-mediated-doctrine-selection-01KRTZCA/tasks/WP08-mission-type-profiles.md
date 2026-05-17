---
work_package_id: WP08
title: Mission-Type Governance Profiles (4 shipped profiles + resolver hard-fail)
dependencies:
- WP04
- WP05
requirement_refs:
- FR-010
- FR-011
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
- T047
agent: "claude:opus-4-7:reviewer-renata:reviewer"
agent_profile: python-pedro
authoritative_surface: src/charter/mission_type_profiles.py
execution_mode: code_change
owned_files:
- src/charter/mission_type_profiles.py
- src/doctrine/missions/software-dev/governance-profile.yaml
- src/doctrine/missions/documentation/governance-profile.yaml
- src/doctrine/missions/research/governance-profile.yaml
- src/doctrine/missions/plan/governance-profile.yaml
- tests/charter/test_mission_type_profiles.py
role: implementer
history: []
tags: []
shell_pid: "1774534"
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Ship one `governance-profile.yaml` per canonical mission type (`software-dev`, `documentation`, `research`, `plan`) at `src/doctrine/missions/<type>/governance-profile.yaml`. Add the loader + resolver in `src/charter/mission_type_profiles.py`. Hard-fail on unknown mission_type with no project override per FR-011 — no `software-dev-default` silent fallback.

After this WP, a documentation mission gets documentation governance and a research mission gets research governance, with project + org selections layered on top.

---

## Context

Today every mission inherits `software-dev-default` template-set content regardless of mission_type. This is journey 4's documented leak. The fix is doctrine-side data (4 YAML files) + charter-side code (loader + resolver).

`charter.context` already reads `meta.json` for mission identity (via `resolve_canonical_repo_root` and friends). This WP adds a thin layer that branches on `mission_type` before assembling the governance payload.

See:
- [plan.md §1.5, §2.7, §2.8](../plan.md)
- [data-model.md §6, §9](../data-model.md)
- [contracts/mission-type-profile.md](../contracts/mission-type-profile.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP08 --agent claude`

---

## Subtasks

### T041 — Create `src/charter/mission_type_profiles.py`

```python
"""Mission-type-scoped governance profile loader + resolver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

from charter.activations import ActivationEntry

__all__ = ["MissionTypeProfile", "load_profile", "resolve_governance"]


CANONICAL_MISSION_TYPES = ("software-dev", "documentation", "research", "plan")
_DOCTRINE_MISSIONS_ROOT = Path(__file__).resolve().parents[2] / "doctrine" / "missions"


class MissionTypeProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_type: Literal["software-dev", "documentation", "research", "plan"]
    template_set: str | None = None
    selected_directives: list[str] = Field(default_factory=list)
    selected_tactics: list[str] = Field(default_factory=list)
    selected_paradigms: list[str] = Field(default_factory=list)
    selected_styleguides: list[str] = Field(default_factory=list)
    selected_toolguides: list[str] = Field(default_factory=list)
    selected_procedures: list[str] = Field(default_factory=list)
    selected_agent_profiles: list[str] = Field(default_factory=list)
    selected_mission_step_contracts: list[str] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    activations: list[ActivationEntry] = Field(default_factory=list)


def load_profile(mission_type: str) -> MissionTypeProfile | None:
    """Load src/doctrine/missions/<mission_type>/governance-profile.yaml.

    Returns None if the file does not exist (caller decides hard-fail policy).
    """
    profile_path = _DOCTRINE_MISSIONS_ROOT / mission_type / "governance-profile.yaml"
    if not profile_path.exists():
        return None
    data = YAML(typ="safe").load(profile_path.read_text(encoding="utf-8"))
    return MissionTypeProfile.model_validate(data)


class UnknownMissionTypeError(ValueError):
    pass


def resolve_governance(repo_root: Path, feature_dir: Path):
    """Read meta.json mission_type, load matching profile, hard-fail when unknown."""
    meta_path = feature_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    mission_type = meta.get("mission_type")
    if not mission_type:
        raise UnknownMissionTypeError(
            f"meta.json at {meta_path} missing mission_type key."
        )

    profile = load_profile(mission_type)

    # Check for project override — if project has selections, that's enough.
    # Implementation reads the project charter via charter.context helpers.
    project_has_overrides = _project_has_doctrine_overrides(repo_root)

    if profile is None and not project_has_overrides:
        raise UnknownMissionTypeError(
            f"No governance profile found for mission_type '{mission_type}' "
            f"and project charter declared no selected_* overrides. Either "
            f"add src/doctrine/missions/{mission_type}/governance-profile.yaml "
            f"or declare selected_* fields in .kittify/charter/charter.md."
        )

    # Delegate to charter.context.build_charter_context with the resolved profile.
    from charter.context import build_charter_context
    payload = build_charter_context(
        repo_root,
        action="implement",
        profile=None,
        mark_loaded=False,
        # Pass profile activations + selections into the context resolver.
        # Exact mechanism is implementation detail.
    )
    # Annotate with mission_type so the ATDD assertion can read it.
    setattr(payload, "mission_type", mission_type)
    return payload


def _project_has_doctrine_overrides(repo_root: Path) -> bool:
    """True iff the project charter declares any selected_<kind> entry."""
    governance_yaml = repo_root / ".kittify" / "charter" / "governance.yaml"
    if not governance_yaml.exists():
        return False
    text = governance_yaml.read_text(encoding="utf-8")
    return "selected_" in text and "doctrine:" in text
```

### T042 — Ship `src/doctrine/missions/software-dev/governance-profile.yaml`

```yaml
mission_type: software-dev
template_set: software-dev-default
selected_directives: []
selected_tactics: []
selected_paradigms: []
selected_styleguides: []
selected_toolguides: []
selected_procedures: []
selected_agent_profiles: []
selected_mission_step_contracts: []
available_tools: []
activations: []
```

This mirrors today's behaviour — when an existing software-dev mission resolves, it gets the `software-dev-default` template-set (preserving backward compatibility for fixtures relying on the current default content).

### T043 — Ship `src/doctrine/missions/documentation/governance-profile.yaml`

```yaml
mission_type: documentation
# template_set intentionally null — documentation missions resolve their own.
# Mission can be tuned in follow-up missions; this baseline ensures
# `software-dev-default` does NOT leak in (FR-011 / journey 4).
selected_directives: []
selected_tactics: []
selected_paradigms: []
selected_styleguides: []
selected_toolguides: []
selected_procedures: []
selected_agent_profiles: []
selected_mission_step_contracts: []
available_tools: []
activations: []
```

### T044 — Ship `src/doctrine/missions/research/governance-profile.yaml`

```yaml
mission_type: research
selected_directives: []
selected_tactics: []
selected_paradigms: []
selected_styleguides: []
selected_toolguides: []
selected_procedures: []
selected_agent_profiles: []
selected_mission_step_contracts: []
available_tools: []
activations: []
```

### T045 — Ship `src/doctrine/missions/plan/governance-profile.yaml`

```yaml
mission_type: plan
selected_directives: []
selected_tactics: []
selected_paradigms: []
selected_styleguides: []
selected_toolguides: []
selected_procedures: []
selected_agent_profiles: []
selected_mission_step_contracts: []
available_tools: []
activations: []
```

### T046 — Wire `resolve_governance` into mission-context pipeline

Identify the call site where the mission's governance payload is built for the implement prompt (today: `charter.context.build_charter_context` consumed by `runtime` or by `agent action implement`). Insert a `resolve_governance` call that runs first, contributes its profile selections + activations to the union, and produces the final payload.

The exact wiring point is implementation detail; the test assertion is the contract — `resolve_governance(repo_root, feature_dir).text` must not contain `software-dev-default` when mission_type is documentation.

### T047 — Hard-fail on unknown mission_type

Verified by T041's `UnknownMissionTypeError`. The message MUST contain the unknown mission_type verbatim:

```
No governance profile found for mission_type 'totally-made-up-mission-type' and project charter declared no selected_* overrides.
```

Pinned by `test_resolve_governance_hard_fails_for_unknown_mission_type`.

---

## Definition of Done

- ✅ `tests/missions/test_mission_type_profile_resolution.py` — 14/14 (parametrised × 4 mission types + 2 single tests + 4 yaml-shape + 4 load-profile)
- ✅ All 4 `governance-profile.yaml` files exist and declare matching `mission_type`
- ✅ `load_profile("software-dev")` returns a non-None `MissionTypeProfile` for each canonical type
- ✅ `resolve_governance` for a documentation mission produces text without `software-dev-default`
- ✅ `resolve_governance` for an unknown mission_type raises with the value named
- ✅ `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 stays green
- ✅ `tests/architectural/test_layer_rules.py` — 8/8 stays green

---

## Risks

| Risk | Mitigation |
|------|------------|
| `software-dev` profile baseline is empty and breaks existing fixtures | Profile carries `template_set: software-dev-default` — same content as today. NFR-005 gate is the 23-test ATDD suite. |
| Documentation profile is empty and produces a too-thin prompt | Acceptable for this mission; follow-up missions tune content. Hard-fail on unknown is the structural guarantee; per-profile content is iterable. |
| `_project_has_doctrine_overrides` heuristic produces false positive/negative | Replace heuristic with explicit Pydantic parse of governance.yaml and check field presence. Use the same loader the context resolver uses. |
| `meta.json` missing mission_type for legacy projects → hard-fail breaks them | Document migration in WP09 user docs. Possibly bootstrap a default at upgrade time (follow-up). |

---

## Reviewer Guidance

- Verify each shipped profile declares its `mission_type` matching the directory name (pinned by test).
- Verify the documentation profile produces a payload that does NOT contain "software-dev-default".
- Verify the hard-fail message names the unknown mission_type verbatim.
- Verify the parametrised tests run × 4 for each canonical mission type.

## Activity Log

- 2026-05-17T18:12:35Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1770351 – Started implementation via action command
- 2026-05-17T18:20:47Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1770351 – 4 governance-profile.yaml files + charter.mission_type_profiles loader + 14/14 mission-type profile resolution tests green; UnknownMissionTypeError hard-fail on unknown mission_type; 23/23 wp_prompt_governance contract regression green; layer rule clean (no specify_cli imports)
- 2026-05-17T18:21:59Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1774534 – Started review via action command
