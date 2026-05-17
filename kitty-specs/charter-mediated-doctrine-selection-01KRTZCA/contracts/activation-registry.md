# Contract — Activation Registry

> Mission: `charter-mediated-doctrine-selection-01KRTZCA`
> Companions: [selection-schema.md](selection-schema.md), [mission-type-profile.md](mission-type-profile.md)

The activation registry is the **context-scoped mode** activation surface — a list of `(activation_context, doctrine_pack_id, artifact_id, artifact_kind?)` tuples scoping artifact activation to specific `(mission_type, action)` contexts. It lives on the charter (project, org pack, or mission-type profile).

---

## Input Contract

### Operator-facing YAML shape

Within a fenced YAML block in `charter.md`, or within `org-charter.yaml`, or within `governance-profile.yaml`:

```yaml
activations:
  - activation_context:
      action: write_comment
    doctrine_pack_id: project
    artifact_id: caveman-comments
    artifact_kind: styleguide      # optional disambiguator

  - activation_context:
      mission_type: software-dev
      action: implement
    doctrine_pack_id: built-in
    artifact_id: python-conventions
    artifact_kind: styleguide
```

### Pydantic shape (`charter.activations.ActivationEntry`)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `activation_context` | `dict[str, str]` | yes | Keys `mission_type` and `action` are recognised; either or both may be absent (= wildcard) |
| `doctrine_pack_id` | `str` | yes | One of: `project`, `built-in`, or a configured org-pack name |
| `artifact_id` | `str` | yes | Must exist in the named pack at resolve time |
| `artifact_kind` | `str \| None` | no | One of the 8 `DoctrineService` property names |

### Vocabulary closures

`activation_context.mission_type` MUST be a member of:

```
{"software-dev", "documentation", "research", "plan", "any", "generic"}
```

`activation_context.action` MUST be a member of:

```
{
  "specify", "plan", "tasks", "implement", "review", "merge", "accept",
  "charter.interview", "charter.generate", "charter.context"
}
```

Vocabulary lives in `charter.activations.ALLOWED_MISSION_TYPES` and `charter.activations.ALLOWED_ACTIONS`. Single source of truth.

### Wildcards

`any` and `generic` in either slot are treated as wildcards (match anything). Absence of the key is equivalent to wildcard.

---

## Output Contract

### Resolver call

```python
from charter.activations import resolve_for_context, ActivationEntry

matches = resolve_for_context(
    entries,                        # list[ActivationEntry] (merged from all 3 sources)
    mission_type="software-dev",
    action="implement",
)
# matches: list[ActivationEntry] — subset of entries whose contexts match
```

Matching semantics:

- `mission_type` slot: `entry.activation_context.get("mission_type")` is absent, `"generic"`, `"any"`, or `== current_mission_type`.
- `action` slot: same with `action`.
- Both slots must match for the entry to be included.

### Rendered prompt stanza (FR-007)

Per matched entry, the renderer emits one line into the implement-prompt governance payload:

> When you `<action>` in a `<mission_type>` mission, run `spec-kitty charter context --include <artifact_kind>:<artifact_id>` and apply the returned rule.

When `artifact_kind` is absent, the resolver looks up the artifact's kind via `DoctrineService` and includes it; if the artifact doesn't exist, see Failure Modes.

When `mission_type` is wildcard, the stanza reads "When you `<action>`, run `...`". Same for `action` wildcard.

---

## Failure Modes

| Failure | Behaviour |
|---------|-----------|
| `activation_context.mission_type = "dev"` (typo, not in vocabulary) | `pydantic.ValidationError` at parse time (`test_activation_entry_validates_membership_of_vocabulary`) |
| `activation_context.action = "compile"` (not in vocabulary) | `pydantic.ValidationError` at parse time |
| `doctrine_pack_id = "missing-pack"` (not in `config.yaml`) | Resolver hard-fails with "pack `missing-pack` not configured" (FR-015) |
| `artifact_id = "does-not-exist"` (no such artifact in the named pack) | Resolver hard-fails with "artifact `does-not-exist` not found in pack `<pack-id>`" |
| Two entries with identical contexts targeting the same `(mission_type, action)` | Policy: **concatenate** — emit one stanza per matched entry in declaration order. The operator may tighten one context to disambiguate. |
| `artifact_kind` set to a kind not in `DoctrineService` | `pydantic.ValidationError` at parse time (Literal validation) |
| Empty `activations:` list | No stanzas emitted; no error |
| `activations:` absent from charter | Treated as empty list; no stanzas emitted |

---

## Backward Compatibility Guarantee

- Charters that pre-date this mission and lack an `activations:` block parse unchanged. No context-scoped stanzas emitted.
- Org packs that pre-date this mission and lack `activations:` produce no activations.
- The 23-test ATDD suite at `tests/specify_cli/next/test_wp_prompt_governance_contract.py` continues to pass — it never asserted on context-scoped stanzas.
- `governance.yaml` adds an `activations:` block only when non-empty; otherwise omitted (NFR-005 byte-stability).

---

## Architectural Test Gates

- `tests/architectural/test_activation_registry_schema.py::test_activation_entry_schema_exists_and_carries_required_fields`
- `tests/architectural/test_activation_registry_schema.py::test_activation_context_mission_type_vocabulary_is_closed`
- `tests/architectural/test_activation_registry_schema.py::test_activation_context_action_vocabulary_is_closed`
- `tests/architectural/test_activation_registry_schema.py::test_activation_entry_validates_membership_of_vocabulary`
- `tests/architectural/test_trigger_registry_coverage.py::test_every_declared_trigger_is_in_the_registered_set`
- `tests/architectural/test_trigger_registry_coverage.py::test_registered_triggers_constant_is_a_frozenset_for_immutability`

---

## Note on Trigger Registry vs Activation Vocabulary

`charter.activations.ALLOWED_ACTIONS` (10 entries) and `tests/architectural/test_trigger_registry_coverage.py::_REGISTERED_TRIGGERS` (15 entries) are **two different sets** with a deliberate overlap.

- **`ALLOWED_ACTIONS`** is what an operator may write in an `activations:` block.
- **`_REGISTERED_TRIGGERS`** is what an artifact author may declare in a `triggers:` block (and what the prompt builder emits as action labels).

`_REGISTERED_TRIGGERS = ALLOWED_ACTIONS ∪ {write_comment, write_docstring, rename_identifier, add_dependency}`.

The four fine-grained tokens are artifact-driven (e.g. a styleguide declares `triggers: [write_comment]` to surface a fetch stanza when the agent is about to write a comment). They are intentionally NOT in `ALLOWED_ACTIONS` because operators schedule activations at the mission-step level, not the per-line-of-code level.
