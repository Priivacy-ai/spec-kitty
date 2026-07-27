# Adversarial Review: Spec & Design Decisions
# Charter Pack Activation Layer

**Reviewer**: Adversarial Spec Reviewer (Claude Sonnet 4.6)
**Date**: 2026-05-31
**Focus**: Spec quality, design decision coherence, data model correctness

---

## BLOCKING (must address before tasks)

**1. Storage location contradiction: `charter.md` vs `config.yaml`**

Files: `spec.md` (Domain Language, Journey 1, Journey 2, Assumption bullet), `research.md` §1 and §5, `plan.md` Technical Context, `data-model.md` PackContext table

`spec.md` defines "charter pack" as "stored at `.kittify/charter/charter.md`". Journey 1 says upgrade "writes the default charter pack to `.kittify/charter/charter.md`". The Assumption says "activation state is stored in a dedicated section [of `charter.md`]".

`research.md` §1 explicitly decides the opposite: "Write activation state changes directly to `.kittify/config.yaml`." `plan.md` Technical Context says Storage is "`.kittify/config.yaml` (activation state)". `data-model.md` gives every PackContext field a `config.yaml` column.

These are incompatible. The charter `from_config()` reads exclusively from `config.yaml` — `charter.md` is never parsed. Journey 1 and the Assumption are simply wrong relative to the research decision. A developer reading the spec would implement YAML-section parsing in `charter.md`; the research implementer would write to `config.yaml`. The resulting code would fail to communicate and the activation state would never be read.

**Resolution**: spec.md must be corrected to say activation state lives in `.kittify/config.yaml`. The `charter.md` dual-purpose assumption must be removed. Journey 1 must be rewritten to describe what upgrade actually does to `config.yaml`.

---

**2. `filter_graph_by_activation` is kind-level; per-kind frozensets are artifact-ID-level; neither is extended to bridge the gap**

Files: `src/charter/drg.py` lines 639–663, `data-model.md` PackContext table, `spec.md` FR-031 through FR-037, success criterion 10

`filter_graph_by_activation` / `_node_is_activated` checks: `"directives" in pack_context.activated_kinds`. This tells whether the *directives* kind as a whole is enabled. It does NOT check whether a specific directive ID (e.g. `python-style-guide`) is in `pack_context.activated_directives`.

The data model adds eight new `frozenset[str] | None` fields to `PackContext` — `activated_directives`, `activated_tactics`, etc. The "hard restriction" model operates at the artifact-ID level: "only those artifacts are available."

Nowhere in the spec, plan, research, or data model is there a requirement to extend `_node_is_activated` to consult these per-kind frozensets. FR-032 says "the merged DRG … is filtered by the project's charter activation state" — but wiring the existing `filter_graph_by_activation` call sites satisfies the letter of FR-032 without the function ever seeing `activated_directives`. The existing function would keep all directive nodes (because "directives" is in `activated_kinds`) even if `activated_directives = {"python-style-guide"}` should exclude `clean-code`.

FR-031 says "`activated_kinds` is read by every artifact resolution path" — that is already the case. It says nothing about reading `activated_directives` etc. Success criterion 10 says grep for `activated_kinds` consumers — none of the per-kind fields are mentioned.

The entire Pattern-A wiring (directives, tactics, styleguides, toolguides) would be wired but still not enforce artifact-ID-level hard restriction because `_node_is_activated` has no spec to change.

**Resolution**: Either (a) explicitly specify extending `_node_is_activated` to check per-kind frozensets when non-None, with a requirement for the extension and an acceptance criterion that tests it, or (b) drop the per-kind frozensets entirely and rely on `activated_kinds` for kind-level gating only (removing the "only those artifacts" claim at artifact-ID level). Shipping both systems with no bridge between them guarantees the hard-restriction model silently does nothing for Pattern-A kinds.

---

**3. The three-state invariant (`None` / empty frozenset / non-empty frozenset) is broken by the existing `from_config()` implementation**

Files: `data-model.md` §CharterPack Invariant, `src/charter/pack_context.py` lines 196–199 and 209–212

`data-model.md` declares: "An empty `frozenset` means 'nothing activated for this kind' (explicit restriction to empty set)." This is described as one of three distinct states.

`pack_context.py._read_activated_kinds()` line 197: `if isinstance(raw, list) and raw:` — the `and raw` clause means an empty list in `config.yaml` (`activated_kinds: []`) falls through to the built-in default, NOT to an empty frozenset. The same pattern must be implemented for the new per-kind fields — but if it is, the "explicit empty restriction" state is impossible to represent via YAML `[]`.

An implementer following the data-model invariant literally would implement new readers that return `frozenset()` for an empty list, contradicting the existing behavior (which treats `[]` as absent). This silent divergence will cause test failures and behavioral inconsistencies. Users who write `activated_directives: []` to mean "nothing available" would actually get all built-ins.

**Resolution**: Remove the "empty frozenset means explicit restriction" state from the data model invariant and document that `[]` in YAML is treated as absent (all built-ins). If explicit empty restriction is needed, define a sentinel value. Alternatively, change the reader implementation and document it — but that changes existing `activated_kinds` semantics and requires a migration test.

---

**4. The `spec.md` backup path in Journey 2 contradicts C-008 within the same document**

Files: `spec.md` Journey 2, `spec.md` C-008

Journey 2: "creates a timestamped backup at `.kittify/charter/charter.md.bak`". This is a flat file with no timestamp in the name.

C-008: "Upgrade backup filenames must include a timestamp to avoid silently overwriting a prior backup on repeated upgrades."

`.kittify/charter/charter.md.bak` contains no timestamp. Running upgrade twice would silently overwrite the first backup. `research.md` and `data-model.md` correctly use `.kittify/charter/backups/charter-{timestamp}.md`. The spec's Journey 2 must be corrected.

---

**5. `ActivationKind` Key Entities definition is fatally truncated**

Files: `spec.md` Key Entities table

The Key Entities table defines `ActivationKind` as: "Enumeration: `mission_type`, `profile`, `directive`, `tactic`". That is 4 values. The spec defines 9 activatable kinds throughout. `profile` appears here but does not appear in the Activation Kinds Reference table (where `agent_profile` is used). `styleguide`, `toolguide`, `paradigm`, `procedure`, `mission_step_contract` are entirely missing.

An implementer using this table as the authoritative enum definition would build a 4-value enum, breaking all 9-kind commands. The term `profile` used here conflicts with `agent_profile` / `agent-profile` used everywhere else.

**Resolution**: Correct the Key Entities table to list all 9 kinds using canonical names consistent with the CLI kind table and `data-model.md`.

---

**6. `CascadeScope` covers only 3 of 8 non-mission-type kinds; the other 5 are not cascade-addressable by name**

Files: `data-model.md` CascadeScope table, `plan.md` CascadeScope Literal, `spec.md` FR-007/FR-008

`data-model.md` CascadeScope table defines named cascade values: `profiles`, `directives`, `tactics` (and `all`, `none`). `plan.md` Literal: `"none" | "all" | "profiles" | "directives" | "tactics"`.

FR-007 says `--cascade all|<kind>[,<kind>...]` accepts comma-separated lists of activation kinds. The activation kinds include `styleguide`, `toolguide`, `paradigm`, `procedure`. But the CascadeScope table has no entries for these. A user wanting `--cascade styleguides` cannot do so without using `all`.

Journey 4 example uses `--cascade agent_profile,tactic` — `agent_profile` is not a named CascadeScope value (only `profiles` is listed). The CLI contracts say `--cascade: all, profiles, directives, tactics, or comma-separated subset` — missing styleguides, toolguides, paradigms, procedures.

**Resolution**: Align `CascadeScope` named values with all 9 CLI kind names, or explicitly constrain FR-007 to the 3 named cascade targets plus `all`.

---

## SIGNIFICANT (should address before implementation)

**7. The upgrade migration algorithm does NOT populate per-kind artifact ID lists; it only writes `activated_kinds`**

Files: `research.md` §5 Upgrade Algorithm, `spec.md` FR-001, C-004

FR-001: "A default charter pack … listing all artifacts available in the built-in doctrine pack." C-004: "no artifact may be silently dropped by upgrading."

The upgrade algorithm in `research.md` writes to `activated_kinds` and `mission_type_activations` only. It does not write to `activated_directives`, `activated_tactics`, etc. After migration, every per-kind field is `None` — meaning "all built-ins available" by the data-model invariant.

Success criterion 1 says "`charter list` confirms all built-in artifacts across all nine activation kinds are activated." If per-kind fields are `None`, `charter list` would show "All built-ins (default)" for each kind, not an enumerated list. The `src/charter/packs/default.yaml` is described as containing full artifact lists, but the migration algorithm reads it only to write to `activated_kinds` — it does not write individual artifact IDs from it.

---

**8. Deactivating from `None` state (no explicit activation set) requires an unspecified "materialization" step**

Files: `data-model.md` charter deactivate flow, `contracts/charter-deactivate-cli.md` Behavior step 3

When a kind has no explicit activation set (`None` state — all built-ins available), the deactivate flow says "remove `id` from the activation set for `kind`." But there is no activation set to remove from. The activate flow addresses this: "if None: initialize to all built-ins, then add." No equivalent is specified for deactivate.

The contract exit code table says exit 1 for "artifact not in activated set." Under `None` semantics, is any artifact "in" the set? If yes, deactivate would need to enumerate all built-ins, materialize an explicit set, then remove the target — expensive and potentially unsafe if the built-in list changes. If no, deactivating an artifact available via fallback is an error, which is unintuitive.

---

**9. C-006 — "same process and transaction as the claim transition" — is not enforceable on a filesystem**

Files: `spec.md` C-006

"The WP start precondition check must execute in the same process and transaction as the claim transition; it may not be deferred." YAML files do not participate in transactions. Two concurrent `agent action implement` calls can both read the same `PackContext`, both see the profile as active, and both proceed. The spec should define what "atomicity" means here (file lock, optimistic read-modify-write with retry, or sequential process execution) or drop the word "transaction."

---

**10. FR-011 WP template reference scan is absent from the consistency-check contract behavior**

Files: `spec.md` FR-011, `contracts/charter-pack-consistency-check-cli.md` Behavior

FR-011: "`charter pack consistency-check` validates … every artifact referenced by WP templates or base prompt templates is activated." The contract's Behavior section has 4 steps. There is no step that scans WP task files, frontmatter, or base prompt templates. The `ConsistencyReport` data model has no field for "artifacts referenced in WP templates but not activated." This entire half of FR-011 has zero implementation specification.

---

**11. NFR-001 threshold is p99 in spec, p95 in plan**

Files: `spec.md` NFR-001, `plan.md` Performance Goals

`spec.md` NFR-001: "≤ 100ms p99." `plan.md` Performance Goals: "≤ 100ms p95." A benchmark passing at p95 with p99 at 150ms would satisfy `plan.md` but fail `spec.md`. One document must be authoritative.

---

**12. Consistency check conflates two different gaps; `ConsistencyReport` has no field for the second**

Files: `contracts/charter-pack-consistency-check-cli.md` Behavior step 3, `spec.md` FR-011

Behavior step 3 checks: "Is the referenced artifact in the activated set?" It does NOT check the inverse: "Is a tactic that is NOT referenced by any activated artifact cluttering the activation set (orphaned)?" That is the "orphaned artifact" definition in the Domain Language. No check for orphaned artifacts appears in the consistency check contract, despite the spec defining what an orphaned artifact is. The `ConsistencyReport` data model has no field for this violation type.

---

## MINOR / POLISH

**13. Duplicate success criteria numbering**: `spec.md` has two items labeled `10.` and two labeled `11.`.

**14. `data-model.md` describes `PackContext` as "Pydantic frozen dataclass"**: `src/charter/pack_context.py:67` uses stdlib `@dataclass(frozen=True)`, not Pydantic. Different mechanics for defaults, field ordering, constructor generation.

**15. `mission_step_contract` → `"mission_steps"` naming gap in `drg.py` vs `pack_context.py`**: `drg.py:592` `_SINGULAR_TO_PLURAL` maps to `"mission_steps"`; `pack_context.py:58` `_BUILTIN_ARTIFACT_KINDS` contains `"mission_step_contracts"`. Ownerless `mission_step_contract` nodes silently drop in default mode. Spec inherits this defect without addressing it.

**16. `CharterPackManager.activate` flow materializes "all built-ins" from unspecified source**: "If None: initialize to all built-ins, then add." Which list is "all built-ins"? `DoctrineService.<repo>.list()` at activation time? `src/charter/packs/default.yaml`? These could differ if the doctrine pack changes. Unspecified.

**17. Wiring acceptance criteria grep commands are underspecified**: Item 5 says grep must return "at least one" non-test caller, but research.md identifies 4 call sites. Item 6's grep cannot be expressed as a simple string search — requires static analysis, not grep.

**18. `mission-type` dispatch not specified in `CharterPackManager`**: The data model shows `mission-type` maps to `mission_type_activations` YAML key (different from all other kinds). `CharterPackManager.activate(kind, id, ...)` takes `kind` as parameter. How the manager dispatches on `kind == "mission-type"` to write the different key is unspecified.

---

## VERIFIED (claims that check out)

- `filter_graph_by_activation` is fully implemented in `src/charter/drg.py:666` with zero production callers — dead-code diagnosis accurate
- `PackContext.activated_kinds` is populated by `from_config()` and consumed by `_node_is_activated` in `drg.py:663` — the only production consumer
- `charter_activate.py.activate_mission_type_override()` writes to `.kittify/overrides/mission-types/<id>.yaml`; `PackContext.from_config()` reads exclusively from `config.yaml` — reader gap root cause accurately described
- `MissionStepRepository` correctly identified as having zero production callers via `charter.mission_steps` facade
- `TYPE_CHECKING` import in `src/doctrine/missions/mission_step_repository.py:43` violates C-004 as described
- `_read_activated_kinds` fallback to all 8 built-in kinds when key is absent is correct backward-compat behavior
- `m_3_2_7` is last migration; `m_3_2_8` is valid next number
- ruamel.yaml round-trip comment preservation confirmed in `m_3_2_7`
- C-001 layer rule enforcement correctly applied — all `charter` imports in `src/doctrine/` use `TYPE_CHECKING` guards
- `DoctrineService` takes no `pack_context` parameter — all repositories unfiltered, confirming Pattern B/C findings

---

## SUMMARY TABLE

| Severity | Count | Top item |
|----------|-------|----------|
| BLOCKING | 6 | Storage location contradiction: `charter.md` vs `config.yaml` |
| SIGNIFICANT | 6 | `filter_graph_by_activation` is kind-level; per-kind frozensets are ID-level; no spec bridges the gap |
| MINOR / POLISH | 6 | Duplicate success criteria numbering; `PackContext` described as Pydantic when stdlib dataclass |
| VERIFIED | 10 | Dead-code diagnosis accurate; reader gap root cause confirmed; migration numbering valid |

**Most dangerous trap**: The spec adds per-artifact-ID activation fields to `PackContext` and requires wiring `filter_graph_by_activation` — but the filter function only reads `activated_kinds` (kind-level). Wiring it satisfies every acceptance criterion while the hard-restriction model at artifact-ID level silently does nothing for Pattern-A kinds. An implementer cannot discover this from the spec alone.
