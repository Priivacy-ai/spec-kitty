# Implementation Plan — Charter-Mediated Doctrine Selection (Mission B)

> Mission: `charter-mediated-doctrine-selection-01KRTZCA`
> Mission ID: `01KRTZCA58EM8RFPVDHYBZQSF8`
> Spec: [spec.md](spec.md) | Data model: [data-model.md](data-model.md) | Contracts: [contracts/](contracts/)
> Branch: `feat/org-doctrine-layer` → `feat/org-doctrine-layer`
> Mission type: software-dev
> ATDD baseline commit: `bd95f1f5`

---

## 1. Architectural Design

### 1.1 The selection plumbing in one sentence

The charter is the **sole authority** for which doctrine artifacts are active. Doctrine remains a pure knowledge-retrieval store. Runtime callers (`src/specify_cli/`) reach doctrine **only through `src/charter/` facades**.

```
src/specify_cli/  ── imports ──>  src/charter/  ── imports ──>  src/doctrine/  ── imports ──>  src/kernel/
   (runtime)                       (charter)                    (knowledge store)               (atomic primitives)
```

This is a tightening of ADR `2026-03-27-1`. The architectural ratchet is
`tests/architectural/test_runtime_charter_doctrine_boundary.py`; it landed at
commit `bd95f1f5` with a 13-file baseline allowlist. As migration WPs (WP07
here) move each runtime caller to a `charter.<facade>` import, the allowlist
shrinks. Final size MUST be ≤ 2 documented exceptions (acceptance criterion
3 + C-004).

### 1.2 Two activation modes, two storage shapes

The mission introduces **two orthogonal activation modes** that the charter records and the resolver renders:

| Mode | Schema shape | Resolver behaviour |
|------|--------------|-------------------|
| **Global** | `selected_<kind>: [<id>, ...]` per kind on `DoctrineSelectionConfig`; mirrored as `required_<kind>` on `OrgCharterPolicy` | Renders inline body (or fetch + when-doing stanza on token-budget overflow) **in every** governance payload |
| **Context-scoped** | `activations:` list of `ActivationEntry(activation_context={mission_type?, action?}, doctrine_pack_id, artifact_id, artifact_kind?)` | Renders a "when you `<action>` in a `<mission_type>` mission, run `spec-kitty charter context --include <kind>:<id>` and apply" stanza, **only** when the resolver's current `(mission_type, action)` matches |

The two modes are independent storage layers. A charter may use either, both, or neither. The activation registry lives on the **charter** (not on artifacts) so the same shared artifact can be activated in different contexts by different charters without forking.

### 1.3 The runtime → charter → doctrine boundary, mechanically

Charter exposes **six new facade modules** (FR-012, all under `src/charter/`):

| Facade module | Re-exports (doctrine.* surface) | Consumer runtime files |
|---------------|----------------------------------|------------------------|
| `charter/profiles.py` | `AgentProfile`, `AgentProfileRepository`, `Role`, `DEFAULT_ROLE_CAPABILITIES` | `invocation/registry.py`, `invocation/router.py` |
| `charter/mission_steps.py` | `MissionStep`, `MissionStepContract`, `MissionStepContractRepository` | `mission_loader/registry.py`, `mission_loader/contract_synthesis.py`, `mission_step_contracts/executor.py` |
| `charter/drg.py` | `DRGEdge`, `DRGGraph`, `DRGNode`, `Relation`, `NodeKind`, `load_graph`, `merge_layers`, `resolve_context`, `ResolvedContext` | `calibration/walker.py`, `glossary/drg_builder.py`, `mission_step_contracts/executor.py` |
| `charter/primitives.py` | `PrimitiveExecutionContext`, `execute_with_glossary` | `missions/__init__.py` |
| `charter/resolution.py` | `ResolutionResult`, `ResolutionTier` | `runtime/resolver.py` |
| `charter/versioning.py` | `check_bundle_compatibility`, `get_bundle_schema_version` | `cli/commands/charter.py`, `cli/commands/charter_bundle.py`, `upgrade/migrations/m_3_2_6_charter_bundle_v2.py` |

These are **thin re-exports**, not new abstractions (FR-012 is migration plumbing — the "real" selection-aware charter API surface lives in `charter.context` and the new `charter.activations` / `charter.mission_type_profiles` modules). Charter facades may freely import from `doctrine.*`; they encapsulate the existing imports the runtime currently makes directly.

`SchemaUtilities` (today imported from `doctrine.shared.schema_utils` by `bulk_edit/occurrence_map.py`) is a generic schema helper. Per the boundary audit, **promote it to `kernel/`** rather than route it through charter — it's a leaf helper that doesn't belong in either layer's domain.

### 1.4 Where the activation registry lives, where it does not

The activation registry is **charter-side** state. The schema (`ActivationEntry`,
`ALLOWED_MISSION_TYPES`, `ALLOWED_ACTIONS`) lives in a new module
`src/charter/activations.py`. Doctrine has no awareness of activations — that
direction would invert the layering. When the resolver in
`charter/context.py` builds the implement-prompt governance payload, it calls
`charter.activations.resolve_for_context(activations, mission_type, action)`
to filter the list down to entries whose `activation_context` matches the
current `(mission_type, action)` pair, then renders each into a "when doing"
stanza alongside the existing globally-selected artifact bodies.

### 1.5 Mission-type profile resolution

A new module `src/charter/mission_type_profiles.py` provides:

- `load_profile(mission_type: str) -> MissionTypeProfile | None` — loads `src/doctrine/missions/<mission_type>/governance-profile.yaml`. Returns `None` if no such file exists.
- `resolve_governance(repo_root: Path, feature_dir: Path) -> GovernancePayload` — reads `feature_dir/meta.json mission_type`, picks the matching profile, unions its declarations with project + org selections, and hard-fails when both the profile is missing AND the project has no declarations (FR-011, journey 4).

The shipped profiles live under `src/doctrine/missions/<type>/governance-profile.yaml` (one per mission_type: `software-dev`, `documentation`, `research`, `plan`). They are doctrine-side **data** (not code) — doctrine still owns artifact storage; the new files are just YAML payloads the charter loader consumes.

### 1.6 Backward compatibility

- Charters lacking new fields parse as today (NFR-005). All new fields default to empty lists / `None`.
- The 23-test ATDD suite at `tests/specify_cli/next/test_wp_prompt_governance_contract.py` MUST stay green throughout.
- The `_OPTIONAL_EMPTY_OMIT_KEYS` allow-list in `src/charter/schemas.py` is extended with the 5 new `selected_<kind>` keys so existing serialised `governance.yaml` files stay byte-identical when the new fields are empty (preserves Mission A's NFR-005 byte-stability contract).
- Org charters lacking `required_<kind>` / `activations:` propagate as today — empty unions, no behaviour change.

---

## 2. Component Changes

### 2.1 `src/charter/schemas.py` — selection schema extension

Extend `DoctrineSelectionConfig` with five new `selected_<kind>` fields (FR-001):

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `selected_styleguides` | `list[str]` | `[]` | Global activation of styleguide artifacts |
| `selected_toolguides` | `list[str]` | `[]` | Global activation of toolguide artifacts |
| `selected_procedures` | `list[str]` | `[]` | Global activation of procedure artifacts |
| `selected_agent_profiles` | `list[str]` | `[]` | Global activation of agent-profile artifacts |
| `selected_mission_step_contracts` | `list[str]` | `[]` | Global activation of mission-step-contract artifacts |

Existing three (`selected_paradigms`, `selected_directives`, `selected_tactics`) are kept unchanged. After this extension, the parity check in `test_artifact_selection_completeness.py::test_every_doctrine_kind_has_a_charter_selected_field` passes against the 8 properties on `DoctrineService` (`directives`, `tactics`, `styleguides`, `toolguides`, `paradigms`, `procedures`, `mission_step_contracts`, `agent_profiles`).

Extend `_OPTIONAL_EMPTY_OMIT_KEYS` with the 5 new keys for NFR-005 byte-stability.

### 2.2 `src/specify_cli/doctrine/org_charter.py` — org schema mirror

Extend `OrgCharterPolicy` with eight `required_<kind>` fields (FR-002) — one for every artifact kind. `required_directives` exists today; the seven new ones are:

`required_paradigms`, `required_tactics`, `required_styleguides`, `required_toolguides`, `required_procedures`, `required_agent_profiles`, `required_mission_step_contracts`.

Extend `apply_org_charter_to_interview` (FR-003) to union every `required_<kind>` into `interview_data.selected_<kind>` non-destructively (existing entries preserved; duplicates not added). The existing `required_directives` union logic is the template.

Extend `load_org_charter_policies` merge semantics — each `required_<kind>` field merges as union-preserving-first-seen-order (mirror current `required_directives` behaviour).

Add `activations` field to `OrgCharterPolicy` (FR-008) so org packs can ship context-scoped activations. The org-merge step concatenates activations across packs (last duplicate wins on `(activation_context, doctrine_pack_id, artifact_id, artifact_kind)` key).

### 2.3 `src/charter/sync.py` and `src/charter/extractor.py` — extraction

Extend the YAML row applier `_apply_selection_row` in `extractor.py` (FR-004) to read every `selected_<kind>` field from the charter's fenced YAML resolution-hints block. Pattern mirrors today's `selected_paradigms` / `selected_directives` / `selected_tactics` handling.

Add an `_apply_activations_block` handler that reads the top-level `activations:` list and populates a new `activations` field on `GovernanceConfig` (or a sibling top-level model — to be confirmed during WP02 implementation, but the data shape is fixed). Round-trip through `governance.yaml` is required: the field round-trips as a list of dicts matching `ActivationEntry.model_dump()`.

### 2.4 `src/charter/context.py` — rendering

Add five new `_render_selected_<kind>` helpers (FR-005) matching the shape of the existing `_render_profile_directives` and `_render_profile_tactics`. Each renders ID + body inline by default, or ID + fetch + when-doing stanza when token-budget overflow triggers. They are called from `build_charter_context` after the existing directive/tactic renderers.

Add an `_render_activation_stanza` helper (FR-007). It takes an `ActivationEntry` and the current `(mission_type, action)` context and emits one prompt line:

> "When you `<action>` in a `<mission_type>` mission, run `spec-kitty charter context --include <kind>:<id>` and apply the returned rule."

The resolver call site filters the registry to matching entries first (wildcard matching: `generic` in either slot matches any concrete value in that slot), then renders each match.

Add the `org_root` provenance bookkeeping for selected artifacts so the prompt carries `source: org` / pack-name metadata for org-distributed artifacts (acceptance criterion in `test_case_2_org_pack_styleguide_appears_in_consumer_prompt`).

### 2.5 `src/charter/activations.py` — NEW

The activation registry surface. Contents:

- `ActivationEntry(BaseModel)` — Pydantic model with `activation_context: dict[str, str]`, `doctrine_pack_id: str`, `artifact_id: str`, `artifact_kind: str | None = None`.
- `ALLOWED_MISSION_TYPES: frozenset[str]` = `{"software-dev", "documentation", "research", "plan", "any", "generic"}`.
- `ALLOWED_ACTIONS: frozenset[str]` = the canonical agent-action vocabulary (see §2.10 trigger registry).
- `resolve_for_context(entries: list[ActivationEntry], *, mission_type: str, action: str) -> list[ActivationEntry]` — returns entries whose `activation_context` matches `(mission_type, action)`, treating `generic`/`any` in either slot as a wildcard.
- Pydantic field validators on `activation_context` enforce membership in `ALLOWED_MISSION_TYPES` / `ALLOWED_ACTIONS`. Construction with a typo raises `ValidationError` (tested by `test_activation_entry_validates_membership_of_vocabulary`).

### 2.6 Charter facade modules — NEW × 6

`src/charter/profiles.py`, `mission_steps.py`, `drg.py`, `primitives.py`, `resolution.py`, `versioning.py`. Each is a 5–10 line `from doctrine.<x> import <Y>` + `__all__ = [...]` re-export, matching the audit's Phase 2 sketch. No behavioural change; pure layer plumbing.

### 2.7 `src/charter/mission_type_profiles.py` — NEW

Loader + resolver for shipped mission-type profiles (FR-010, FR-011):

- `MissionTypeProfile(BaseModel)` — top-level `mission_type: str`, plus the same selection/activation fields as `DoctrineSelectionConfig` + `activations`.
- `load_profile(mission_type: str) -> MissionTypeProfile | None`.
- `resolve_governance(repo_root: Path, feature_dir: Path) -> GovernancePayload` — meta.json read + profile lookup + union + hard-fail. Hard-fail message names the unknown mission_type (`test_resolve_governance_hard_fails_for_unknown_mission_type` pins this).

### 2.8 Shipped mission-type profiles — NEW × 4

Four new files (FR-010):

| Path | Mission type | Initial content |
|------|--------------|-----------------|
| `src/doctrine/missions/software-dev/governance-profile.yaml` | `software-dev` | Mirrors today's `software-dev-default` template-set selections (initial baseline; can be tuned in follow-up missions) |
| `src/doctrine/missions/documentation/governance-profile.yaml` | `documentation` | Documentation-flavoured defaults — empty `selected_directives`, `template_set: documentation-default` (or `null`), one default activation for `(documentation, implement) → fetch documentation-template-styleguide` |
| `src/doctrine/missions/research/governance-profile.yaml` | `research` | Minimal — research missions inherit very little governance by default |
| `src/doctrine/missions/plan/governance-profile.yaml` | `plan` | Minimal — plan missions inherit very little governance by default |

The exact field values for documentation / research / plan are doctrine-side data tuning, not code; they can be expanded in follow-up missions. The mission requires each to declare its own `mission_type` matching the directory name (pinned by `test_profile_yaml_declares_its_mission_type`).

### 2.9 13 runtime files — migration

The 13 files in the boundary ratchet allowlist swap `from doctrine.<x> import <Y>` to `from charter.<facade> import <Y>` per the facade table in §1.3. Each file rewrite + corresponding allowlist removal is one commit (C-003). (Plus 1 new module `src/kernel/schema_utils.py` from the SchemaUtilities promotion in T040; the allowlist ratchet still counts only the 13 migrating runtime files. Total paths touched in WP07: 14.)

Special case: `bulk_edit/occurrence_map.py`'s `SchemaUtilities` consumer migrates to `kernel.schema_utils` (after promoting the module out of `doctrine.shared`), not via charter.

Borderline cases: the three `versioning` consumers (`cli/commands/charter.py`, `cli/commands/charter_bundle.py`, `upgrade/migrations/m_3_2_6_charter_bundle_v2.py`) are themselves charter-CLI surfaces. Per C-004 they MAY remain in the allowlist as documented exceptions if HiC accepts, capping the final size at ≤ 2. Default plan: migrate all three to `charter.versioning` (cleaner), leaving the allowlist at 0; HiC may downgrade to ≤ 2 during implementation if either of the migrations turns out to be lossy.

### 2.10 Trigger registry initial population (C-005, HiC-facing decision)

See [data-model.md §7](data-model.md#7-trigger-registry-fr-009--canonical-definition) for the canonical vocabulary definition, the `_REGISTERED_TRIGGERS = _ALLOWED_ACTIONS ∪ {write_comment, write_docstring, rename_identifier, add_dependency}` union formula, the mandatory `src/charter/activations.py` re-export contract, and the cross-check architectural test that prevents drift. C-005 is satisfied by that pinned set (15 trigger tokens / 10 action tokens) — implementation must consume the vocabulary via that single source, not by restating it.

### 2.11 Missing-pack policy change (C-006, FR-015)

Today's pack-registry loader silently filters out missing `local_path` entries (Mission A behaviour). FR-015 + `test_case_2_consumer_without_fetched_pack_fails_loudly` change this to hard-fail with a message naming the pack and the missing path.

Implementation point: `specify_cli.doctrine.config.load_pack_registry` (or its consumer in `charter.context.build_charter_context`) gains a strict mode. When a configured pack's `local_path` does not exist, the loader raises `PackNotFoundError` (or similar) carrying the pack name + path. C-006 requires the org-doctrine-layer user docs to be updated to call out the change — owned by WP09 documentation work.

### 2.12 Operator UX (FR-016, FR-017, FR-018, C-007)

New CLI surfaces in `src/specify_cli/cli/commands/doctrine.py`:

- `spec-kitty doctrine new <kind> <name>` — writes a stub `<name>.<kind>.yaml` in `.kittify/doctrine/<kind>/` (project default) or `<pack_path>/<kind>s/` when `--pack <path>` is given. Stub carries the required schema fields populated with sentinels.
- `spec-kitty doctrine validate <path>` — validates a single artifact YAML or a doctrine directory tree against the canonical schemas; exits 0 on valid, non-zero on invalid. Reuses the validation logic from `spec-kitty doctrine pack validate`.

Extend `spec-kitty doctor doctrine`:

- Add a "Selections" section listing, for every kind, the active globally-selected artifacts (project + org + mission-type-profile union), each with its resolved pack source (`built-in`, `project`, `org:<pack-name>`).

Glossary promotion (C-007): the 10 candidate entries in `glossary/contexts/doctrine.md` (Charter-Mediated Selection, Global Selection, Context-Scoped Selection, Activation Registry, Activation Context, Doctrine Pack ID, Trigger Registry, Charter Facade, Mission-Type Profile, `selected_<kind>` / `required_<kind>`) flip from `Status: candidate` to `Status: canonical`. Acceptance gate before merge.

---

## 3. Sequencing & Risks

### 3.1 Phasing

The 9 WPs land in dependency order; finalize-tasks will assign lanes based on the dependency graph below.

```
WP01 (schemas) ──┬──> WP02 (sync extract) ──> WP04 (selection render) ──┬──> WP06 (org pre-fill) ──┐
                 │                                                       │                          ├──> WP09 (operator UX + glossary)
                 │                                                       │                          │
                 └──> WP03 (facades) ──> WP07 (runtime migration) ───────┘                          │
                                                                                                    │
                          WP05 (activation render + trigger registry) ──> WP08 (mission profiles) ──┘
```

Dependencies:

- WP02 needs WP01's schema fields.
- WP04 needs WP02's extraction populating the fields.
- WP05 needs WP04's renderer scaffold (re-uses the fetch-stanza helper).
- WP06 needs WP01's `required_<kind>` fields.
- WP07 needs WP03's facades.
- WP08 needs WP04 + WP05 to land first so mission-type profiles can declare both selections and activations.
- WP09 (operator UX) needs WP04's schema to scaffold against.

### 3.2 Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Token-budget overflow when many globally-selected artifacts land in one prompt | HIGH | Reuse the existing `_shared_fetch_stanza_lines` substitution machinery (NFR-001). Per-kind renderers participate in substitution. `test_wp_prompt_build_latency.py` is the gate. |
| Activation registry collision (two entries match the same `(mission_type, action)`) | MEDIUM | Policy: concatenate — emit one stanza per match in declaration order. Operator can resolve by tightening one of the contexts. Documented in WP05's contract. |
| Missing-pack policy change breaks existing flows where users have stale `config.yaml` | MEDIUM | C-006 mandates user-doc update. Add a clear migration note. The error message itself names the pack and the missing path so the fix is obvious. |
| Boundary migration introduces import cycles between charter facades and existing charter modules | MEDIUM | Facades re-export only public doctrine symbols. Charter modules that today import `from doctrine.X` continue to do so directly (the boundary rule applies only to runtime). Phase 2 in the audit explicitly avoids the cycle. |
| Mission-type profiles ship empty for research / plan and cause regressions in those mission types | LOW | Initial profiles are minimal but valid (declare `mission_type` + empty fields). Profile is hard-fail-on-unknown — but it returns the profile if found, so a minimal-but-present profile is the correct shape. |
| Charter facades duplicate symbols already exposed by `charter.context` / `charter.template_resolver` | LOW | Facades expose **types and repositories** the runtime needs for type annotations and lookups. The richer charter API (resolved governance payloads) stays in `charter.context`. The two coexist. |
| Glossary candidate→canonical flip catches new terms not aligned with implementation | LOW | Promotion happens in WP09 after the implementation lands. Term definitions in the spec are already aligned. |
| Mission B WPs land in parallel and stomp on `charter/context.py` | MEDIUM | Single owner (`python-pedro`) for all WPs touching `context.py`. WP04 and WP05 both touch it but in distinct rendering blocks; WP04 runs first, WP05 extends afterward. |

### 3.3 Worktree / lane planning hint for finalize-tasks

Expected lane decomposition (final assignment by `finalize-tasks`):

- **Lane A** — Schemas + extraction + global rendering: WP01 → WP02 → WP04
- **Lane B** — Facades + boundary migration: WP03 → WP07
- **Lane C** — Activation + mission profiles: WP05 → WP08
- **Lane D** — Org pre-fill (depends on lane A's WP01): WP06
- **Lane E** — Operator UX + glossary (depends on lane A + lane D): WP09

Three to five lanes total. WP06 may merge into Lane A if finalize prefers tighter sequencing.

---

## 4. Test Strategy

### 4.1 ATDD as the canonical executable spec (C-002)

The 7-file ATDD suite landed at `bd95f1f5` is the **acceptance gate**. Mission is complete when:

| Test file | Currently | Target |
|-----------|-----------|--------|
| `tests/integration/test_user_doctrine_artifact_lifecycle.py` | 1/4 (workaround only) | 4/4 |
| `tests/integration/test_org_pack_artifact_lifecycle.py` | 0/4 | 4/4 |
| `tests/architectural/test_artifact_selection_completeness.py` | 0/3 | 3/3 |
| `tests/architectural/test_trigger_registry_coverage.py` | 2/2 (vacuous) | 2/2 (non-vacuous) |
| `tests/architectural/test_runtime_charter_doctrine_boundary.py` | 1/1 (allowlist=13) | 1/1 (allowlist ≤ 2) |
| `tests/architectural/test_activation_registry_schema.py` | 0/4 | 4/4 |
| `tests/missions/test_mission_type_profile_resolution.py` | 0/14 | 14/14 |

Per C-002, the 7 ATDD files are **not modified** during the mission (they are the spec). If an assertion proves unrealistic, the file is amended in a separate prior commit with explicit justification.

### 4.2 Regression guards (NFR-005, NFR-004)

The following test surfaces MUST remain green throughout:

- `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 (the prior mission's ATDD)
- `tests/architectural/test_layer_rules.py` — 8/8 (layer rule ratchet)
- `tests/architectural/test_pytest_marker_convention.py` — 1/1
- `tests/architectural/test_pytest_marker_correctness.py` — 2/2
- `tests/architectural/test_wp_prompt_build_latency.py` — 2/2 (NFR-002 latency budget)
- `tests/contract/` — 237 / 1 skip / 0 fail

### 4.3 Marker discipline

All new tests created during the mission carry the appropriate pytest mark per `test_pytest_marker_convention.py`. Unit tests → `@pytest.mark.unit`; architectural → `@pytest.mark.architectural`; integration → `@pytest.mark.integration` + (where applicable) `@pytest.mark.git_repo`.

### 4.4 Backward compatibility tests

Each WP that extends a Pydantic schema includes a regression test that an empty-field instance round-trips through `governance.yaml` byte-identically to today (NFR-005). The `_OPTIONAL_EMPTY_OMIT_KEYS` extension is the mechanism.

### 4.5 Acceptance flow

1. Each WP turns its named ATDD tests from red to green (Definition of Done lists them per WP).
2. The boundary ratchet shrinks monotonically as WP07 lands.
3. Mission-review (`spec-kitty-mission-review` per acceptance criterion 8) passes with no CRITICAL or HIGH findings.

---

## 5. Plan-Time Decisions

These are HiC-facing decisions resolved during planning that downstream WPs MUST honour without re-litigating.

| Decision | Resolution | Rationale |
|----------|-----------|-----------|
| Trigger registry initial population (C-005) | 11 verbs + 4 fine-grained tokens per §2.10 | Matches FR-009 enumeration; pinned by `test_activation_registry_schema.py` + `test_trigger_registry_coverage.py` |
| Missing-pack policy (FR-015) | Hard-fail with named-pack-and-path error | C-006 mandate; ATDD test pins it |
| Activation collision policy | Concatenate (emit one stanza per match in declaration order) | Simplest correct semantic; operator-tightenable |
| `SchemaUtilities` location | Promote to `kernel/` | Genuine generic helper; cleaner than routing through charter |
| Versioning facade migration | Migrate all three callers; allow up to 2 documented exceptions if migration is lossy | C-004 caps allowlist at 2; default attempt is full migration |
| Mission-type profile fallback | Hard-fail with named-mission-type error; no `software-dev-default` fallback | FR-011 + ATDD test |
| Glossary promotion timing | At end of WP09 after implementation lands | Promotion validates terms against shipped behaviour |
| Org pack `activations:` field | Supported (FR-008); merged across packs with last-duplicate-wins semantics | Mirrors `governance_policies` merge today |

---

## 6. References

- Spec: [spec.md](spec.md)
- Data model: [data-model.md](data-model.md)
- Contracts: [contracts/](contracts/)
- Investigation: [docs/development/doctrine-artifact-selection-preflight.md](../../docs/development/doctrine-artifact-selection-preflight.md)
- Boundary audit: [docs/development/runtime-charter-doctrine-boundary.md](../../docs/development/runtime-charter-doctrine-boundary.md)
- Original proposed scope: [docs/development/mission-b-proposed-scope.md](../../docs/development/mission-b-proposed-scope.md)
- ATDD baseline commit: `bd95f1f5`
- Glossary: [glossary/contexts/doctrine.md](../../glossary/contexts/doctrine.md)
- ADR: [architecture/2.x/adr/2026-03-27-1-pytestarch-architectural-dependency-testing.md](../../architecture/2.x/adr/2026-03-27-1-pytestarch-architectural-dependency-testing.md)
