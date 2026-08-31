# Contract — Selection Schema

> Mission: `charter-mediated-doctrine-selection-01KRTZCA`
> Companions: [activation-registry.md](activation-registry.md), [mission-type-profile.md](mission-type-profile.md), [charter-facade-modules.md](charter-facade-modules.md)

The selection schema is the **global mode** activation surface — a list of artifact IDs per artifact kind that the charter declares as always-active. It lives at two layers: the project charter (`DoctrineSelectionConfig`) and the org charter (`OrgCharterPolicy`).

---

## Input Contract

### Project-level (charter.md → `DoctrineSelectionConfig`)

**Operator-facing surface:** a fenced YAML block in `.kittify/charter/charter.md`:

```yaml
selected_directives: [<id>, ...]              # already supported
selected_tactics: [<id>, ...]                 # already supported
selected_paradigms: [<id>, ...]               # already supported
selected_styleguides: [<id>, ...]             # NEW (FR-001)
selected_toolguides: [<id>, ...]              # NEW
selected_procedures: [<id>, ...]              # NEW
selected_agent_profiles: [<id>, ...]          # NEW
selected_mission_step_contracts: [<id>, ...]  # NEW
available_tools: [<tool>, ...]                # already supported
template_set: <name>                          # already supported
```

**Parser surface:** `charter.extractor.Extractor._apply_selection_row`. Each new field is read by extending the existing `_get_list_value` calls.

### Org-level (`org-charter.yaml` → `OrgCharterPolicy`)

**Operator-facing surface:** within a doctrine pack's `org-charter.yaml`:

```yaml
schema_version: "1"
org_name: <pack-name>
required_directives: [<id>, ...]              # already supported
required_tactics: [<id>, ...]                 # NEW
required_paradigms: [<id>, ...]               # NEW
required_styleguides: [<id>, ...]             # NEW
required_toolguides: [<id>, ...]              # NEW
required_procedures: [<id>, ...]              # NEW
required_agent_profiles: [<id>, ...]          # NEW
required_mission_step_contracts: [<id>, ...]  # NEW
```

**Parser surface:** `specify_cli.doctrine.org_charter.load_org_charter_policy`.

---

## Output Contract

### Project-level

`governance.yaml` round-trips every non-empty `selected_<kind>` list with values verbatim:

```yaml
doctrine:
  selected_styleguides:
    - caveman-comments
```

Empty lists are **omitted** from `governance.yaml` per the `_OPTIONAL_EMPTY_OMIT_KEYS` allow-list (NFR-005 backward compatibility).

### Org-level

`apply_org_charter_to_interview(interview_data, repo_root)` unions every `required_<kind>` from the merged org policy into `interview_data.selected_<kind>`. Non-destructive — existing entries preserved, duplicates dropped.

Return value: `list[str]` of human-readable messages (one per kind with new entries), example:

> "Pre-selected 1 styleguide(s) from org charter required_styleguides."

### Resolver-level (FR-005)

`charter.context.build_charter_context(repo_root, action=..., profile=...)` produces a payload whose text carries, for each globally-selected artifact:

- The artifact ID
- Either the artifact body inline OR (on token-budget overflow) a fetch + when-doing stanza naming the artifact ID

Org-distributed artifacts additionally carry provenance: either `source: org` or the pack name in the rendered section.

---

## Failure Modes

| Failure | Behaviour |
|---------|-----------|
| Charter selects an unknown ID (`selected_styleguides: [does-not-exist]`) | Resolver hard-fails with a message naming the unknown ID and the kind. Matches `_validate_paradigm_selection` semantic from prior work. |
| Org pack declares `required_<kind>` for a non-existent kind | Pydantic rejects with `extra="forbid"` validation error at parse time. |
| Selection field type mismatch (e.g. `selected_styleguides: "caveman"` as scalar) | Pydantic coerces strings via `_get_list_value` (comma-split fallback for charter-md path); strict type error for `org-charter.yaml`. |
| `selected_<kind>` and `<kind>` (without prefix) both set in the same row | Per `_apply_selection_row` precedence: the prefixed key wins, the unprefixed key is silently ignored (matching existing `selected_directives` vs `directives` semantic). |
| Empty list set explicitly | Treated as "no selection"; omitted from `governance.yaml`. |
| Field absent | Defaults to `[]`; no behaviour difference from explicit empty. |

---

## Backward Compatibility Guarantee

- A charter that pre-dates this mission and lacks any of the new `selected_<kind>` fields parses **unchanged**. Defaults make every new field empty.
- A `governance.yaml` produced by the new extractor with all new fields empty is **byte-identical** to a `governance.yaml` produced by the old extractor (NFR-005). Guaranteed by extending `_OPTIONAL_EMPTY_OMIT_KEYS` with the 5 new keys.
- An `org-charter.yaml` that pre-dates this mission and lacks any of the new `required_<kind>` fields parses **unchanged**. Org policy merge produces the same output.
- The 23-test ATDD suite at `tests/specify_cli/next/test_wp_prompt_governance_contract.py` continues to pass without modification.

---

## Architectural Test Gates

Every change to this contract MUST keep the following tests green:

- `tests/architectural/test_artifact_selection_completeness.py::test_every_doctrine_kind_has_a_charter_selected_field`
- `tests/architectural/test_artifact_selection_completeness.py::test_every_doctrine_kind_has_an_org_required_field`
- `tests/architectural/test_artifact_selection_completeness.py::test_selection_and_required_field_names_are_consistent`
