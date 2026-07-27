# Contract — Mission-Type Governance Profile

> Mission: `charter-mediated-doctrine-selection-01KRTZCA`
> Companions: [selection-schema.md](selection-schema.md), [activation-registry.md](activation-registry.md)

A mission-type profile is a shipped doctrine-side YAML file at `src/doctrine/missions/<type>/governance-profile.yaml` declaring the default selections and activations for missions of that type. The charter resolver picks the matching profile based on `meta.json mission_type`, then unions its declarations with project + org selections.

---

## Input Contract

### On-disk shape

File path: `src/doctrine/missions/<mission_type>/governance-profile.yaml`

Required for every canonical mission type: `software-dev`, `documentation`, `research`, `plan`.

```yaml
mission_type: documentation        # REQUIRED — must match parent directory name
template_set: documentation-default  # optional
selected_directives: []
selected_tactics: []
selected_styleguides: []
selected_toolguides: []
selected_paradigms: []
selected_procedures: []
selected_agent_profiles: []
selected_mission_step_contracts: []
available_tools: []
activations: []                    # list[ActivationEntry] — see activation-registry.md
```

### Pydantic shape (`charter.mission_type_profiles.MissionTypeProfile`)

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `mission_type` | `Literal["software-dev", "documentation", "research", "plan"]` | yes | — |
| `template_set` | `str \| None` | no | `None` |
| `selected_<kind>` (8 fields) | `list[str]` | no | `[]` |
| `available_tools` | `list[str]` | no | `[]` |
| `activations` | `list[ActivationEntry]` | no | `[]` |

Pydantic `model_config = ConfigDict(extra="forbid")`.

### Loader call

```python
from charter.mission_type_profiles import load_profile

profile = load_profile("documentation")   # MissionTypeProfile | None
```

Returns `None` if the file does not exist.

### Resolver call

```python
from charter.mission_type_profiles import resolve_governance

payload = resolve_governance(repo_root, feature_dir)
# payload.text -> rendered governance text for the mission
# payload.mission_type -> the resolved mission_type
```

The resolver:

1. Reads `feature_dir / "meta.json"` and extracts `mission_type`.
2. Calls `load_profile(mission_type)`.
3. If profile is `None` AND the project charter has no declarations of its own, hard-fails with a message naming the unknown mission_type.
4. Otherwise unions the profile's `selected_<kind>` and `activations` with the project's + org's, then renders.

---

## Output Contract

### Successful resolution

A `GovernancePayload` (or `CharterContextResult`) carrying:

- `text: str` — the rendered governance section the implement prompt embeds. MUST NOT contain `software-dev-default` content when `mission_type != "software-dev"`.
- `mission_type: str` — equal to the resolved `meta.json mission_type`.

### Hard-fail on unknown mission type (FR-011)

```python
>>> resolve_governance(repo_root, feature_with_meta_mission_type="totally-made-up")
Traceback (most recent call last):
  ...
UnknownMissionTypeError: No governance profile found for mission_type
    'totally-made-up' and project charter declared no overrides. Either
    add src/doctrine/missions/totally-made-up/governance-profile.yaml or
    declare selected_* fields in .kittify/charter/charter.md.
```

Exact exception class is implementation detail (`ValueError` subclass acceptable); message MUST contain the unknown `mission_type` value verbatim (pinned by `test_resolve_governance_hard_fails_for_unknown_mission_type`).

---

## Failure Modes

| Failure | Behaviour |
|---------|-----------|
| Profile file exists but top-level `mission_type` mismatches directory | `test_profile_yaml_declares_its_mission_type` fails (architectural gate). Implementation MUST detect at load time and raise. |
| `meta.json` missing `mission_type` key | Resolver hard-fails with "meta.json missing mission_type key" |
| Profile file YAML invalid | Pydantic `ValidationError`; loader propagates |
| Profile declares unknown `selected_<kind>` ID | Same as project-level selection: resolver hard-fails at render time |
| Profile and project charter declare conflicting `template_set` | Project wins (project overrides profile for `template_set`); a warning is emitted |
| Profile declares `mission_type` outside the closed Literal | `pydantic.ValidationError` at load time |
| `meta.json mission_type = "software-dev"` but no profile file exists | Hard-fail per FR-011 (no silent fallback). Mission is required to ship all 4 profiles, so this represents a regression. |

---

## Backward Compatibility Guarantee

- **Behavioural change** from today: `software-dev-default` is no longer the silent fallback for non-software missions. This is the intent of FR-011 and journey 4.
- Pre-mission projects whose `meta.json` declares `mission_type: software-dev` continue to work — the new `software-dev` profile ships with content matching today's `software-dev-default` selections.
- Pre-mission projects whose `meta.json` is missing or carries an unknown `mission_type` will hard-fail. **Migration note**: operators must add a `mission_type` to existing missions. This is owned by the WP08 / WP09 user-doc work.
- The 23-test ATDD suite at `tests/specify_cli/next/test_wp_prompt_governance_contract.py` continues to pass because every fixture mission has `mission_type: software-dev` and the new `software-dev` profile mirrors the prior behaviour.

---

## Architectural Test Gates

- `tests/missions/test_mission_type_profile_resolution.py::test_mission_type_ships_governance_profile_yaml` (parametrised × 4)
- `tests/missions/test_mission_type_profile_resolution.py::test_load_profile_returns_mission_type_profile` (parametrised × 4)
- `tests/missions/test_mission_type_profile_resolution.py::test_resolve_governance_picks_documentation_profile_for_documentation_mission`
- `tests/missions/test_mission_type_profile_resolution.py::test_resolve_governance_hard_fails_for_unknown_mission_type`
- `tests/missions/test_mission_type_profile_resolution.py::test_profile_yaml_declares_its_mission_type` (parametrised × 4)

14 parametrised assertions total — all must pass.
