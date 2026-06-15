# Charter-Mediated Doctrine Selection (Mission B)

> Mission ID: `01KRTZCA58EM8RFPVDHYBZQSF8`
> Mission slug: `charter-mediated-doctrine-selection-01KRTZCA`
> Target branch: `feat/org-doctrine-layer`
> Mission type: software-dev
> Created: 2026-05-17

---

## Overview

This mission makes the charter the single authority deciding which doctrine artifacts apply, in which contexts, for any given mission run. Doctrine becomes a pure knowledge-retrieval store; the runtime reaches doctrine artifacts only through charter-exposed facades; multiple doctrine packs may be configured; the charter holds a registry of `(activation_context, doctrine_pack_id, artifact_id)` tuples for context-scoped activations plus per-kind `selected_<kind>` lists for global activations.

The mission folds three pre-existing workstreams into one delivery: the original "Mission B" mission-type profiles (B-WP01–WP02 from `docs/development/layered-doctrine-resolution-design.md`), the per-artifact selection schema and trigger registry from the pre-flight (`docs/development/doctrine-artifact-selection-preflight.md`), and the runtime → charter → doctrine boundary enforcement from the audit (`docs/development/runtime-charter-doctrine-boundary.md`). The three share contracts and would have to land in lock-step anyway.

The canonical executable spec is the 7-file ATDD suite that landed in `bd95f1f5` (see [Acceptance Criteria](#acceptance-criteria)). Mission work is complete when the 29 failing-first assertions all turn green, the boundary ratchet's allowlist drops to its documented final size, the marker-presence + marker-correctness gates stay green, and the layer-rule architectural tests stay green.

---

## User Journeys

### Journey 1 — Project-layer user-authored doctrine artifact

> "I author a `caveman-comments.styleguide.yaml` saying all code comments should be written as a caveman would. I drop it into `.kittify/doctrine/styleguide/`. I add `selected_styleguides: [caveman-comments]` to my charter. During the next mission run, the implementer's prompt contains the caveman rule body (or a fetch + when-doing stanza naming it). I did not need to write a wrapper directive."

**Actors:** Project owner (charter author), implementing agent
**Preconditions:** Mission A's three-layer doctrine model is in place. The project's charter is the standard `.kittify/charter/charter.md`.

After this mission:
1. The user creates `.kittify/doctrine/styleguide/caveman-comments.styleguide.yaml` against the published schema.
2. The user adds `selected_styleguides: [caveman-comments]` to a fenced YAML block in `charter.md`.
3. `spec-kitty charter sync` extracts the new field into `governance.yaml`.
4. The implementer's prompt — produced by `_build_wp_prompt` — carries the caveman styleguide body (or fetch + when-doing stanza on token-budget overflow) under a new `Selected styleguides` section.

### Journey 2 — Org-pack distributed doctrine artifact

> "Our 'very-serious-developers' org maintains a `caveman-comments.styleguide.yaml` in our internal doctrine pack. Our org charter declares `required_styleguides: [caveman-comments]`. Team members add the pack to their `.kittify/config.yaml` `doctrine.org.packs`. Each team member's mission runs surface caveman without any per-project setup."

**Actors:** Org governance lead (pack maintainer), team-member developer, implementing agent
**Preconditions:** Mission A's org-pack infrastructure. Org publishes its pack via git / HTTPS / API.

After this mission:
1. Org publishes pack; team adds `doctrine.org.packs` entry.
2. `apply_org_charter_to_interview` unions `required_styleguides` (and `required_<kind>` for every kind) from the org-charter into the project's `selected_styleguides`.
3. The implementer's prompt surfaces the org styleguide with `source: "org"` provenance — identical end-to-end behaviour to Journey 1, with the styleguide sourced from the org pack instead of the project's own `.kittify/doctrine/`.
4. ID collisions with built-in or with other org packs fire `DoctrineLayerCollisionWarning` (extending Mission A's existing collision surface to styleguides).

### Journey 3 — Context-scoped activation ("when doing X, fetch Y")

> "I want caveman to apply *only* when writing code comments — not when writing CLI help text. I add an entry to the charter activation registry: `(action: write_comment, doctrine_pack_id: project, artifact_id: caveman-comments)`. During implement runs, when the agent is about to write a code comment, the prompt contains a 'when you write a code comment, run `spec-kitty charter context --include styleguide:caveman-comments` and apply' stanza."

**Actors:** Project owner, implementing agent
**Preconditions:** Journey 1 in place; trigger registry populated with the canonical agent-action tokens.

After this mission:
1. The user adds an `activations:` list to `charter.md` with the tuple above.
2. `charter sync` persists the registry.
3. `build_charter_context(action="implement", mission_type="software-dev")` resolves entries matching the current context and emits the conditional fetch stanza.
4. The agent reads the stanza and runs the fetch on the trigger event.

### Journey 4 — Mission-type-scoped governance

> "I run a documentation mission. The implementer's prompt does NOT include `software-dev-default` directives. It includes documentation-specific governance from the shipped `documentation` mission-type profile."

**Actors:** Project owner, implementing agent
**Preconditions:** Mission B's mission-type profiles ship under `src/doctrine/missions/<type>/governance-profile.yaml` for software-dev, documentation, research, plan.

After this mission:
1. `meta.json` declares `mission_type: documentation`.
2. Resolver loads the documentation profile, unions it with project + org selections.
3. Prompt is documentation-specific. No `software-dev-default` fallback.
4. A mission with an unknown `mission_type` and no project-declared selections produces a hard failure (not a silent fallback).

### Journey 5 — Boundary enforcement (architectural)

> "I'm reviewing a PR that adds a new file under `src/specify_cli/`. The author added `from doctrine.agent_profiles import AgentProfile`. CI fails with a clear message telling them to switch to `from charter.profiles import AgentProfile`. The author makes the swap; CI goes green."

**Actors:** Contributor, reviewer, CI architectural gate
**Preconditions:** WP01 of this mission ships the boundary ratchet test with the 13-file baseline allowlist.

After this mission:
1. Any new `from doctrine.*` import in a non-allowlisted `src/specify_cli/` file fails `test_runtime_charter_doctrine_boundary.py`.
2. As migration WPs migrate the 13 baseline files, the allowlist shrinks; final state is documented (likely 2 charter-bundle versioning callers as accepted exceptions).
3. The `src/specify_cli/doctrine/` subpackage stays exempt — it's the pack-management surface, by design.

---

## Domain Language

| Term | Canonical meaning |
|---|---|
| **Charter-Mediated Selection** | Architectural pattern: charter is the sole authority deciding which doctrine artifacts apply. See glossary. |
| **Global Selection** | Activation mode: artifact is active for every WP prompt regardless of action / mission_type. Expressed via `selected_<kind>` / `required_<kind>`. |
| **Context-Scoped Selection** | Activation mode: artifact is active only for a specific `(mission_type, action)` context. Expressed via the Activation Registry. |
| **Activation Registry** | Charter-level list of `(activation_context, doctrine_pack_id, artifact_id)` tuples. |
| **Activation Context** | `{mission_type, action}` dict — both fields accept the wildcard `generic`. |
| **Doctrine Pack ID** | Stable identifier of a doctrine pack. Special values: `project`, `built-in`. |
| **Trigger Registry** | Frozen set of canonical agent-action tokens the prompt builder recognises. Membership is checked by `test_trigger_registry_coverage.py`. |
| **Charter Facade** | A `src/charter/<facade>.py` module that re-exports a doctrine surface for runtime callers. |
| **Mission-Type Profile** | Shipped `governance-profile.yaml` per mission_type at `src/doctrine/missions/<type>/`. |
| **selected_&lt;kind&gt; / required_&lt;kind&gt;** | The schema-field naming convention for global selection. 8 kinds; project gets `selected_*`, org gets `required_*`. |
| **Runtime → Charter → Doctrine boundary** | Architectural invariant: production modules under `src/specify_cli/` (excluding `src/specify_cli/doctrine/`) MUST NOT import `doctrine.*` directly. |

Avoid: "registry of triggers" (use Trigger Registry), "doctrine policy" (use Global Selection).

---

## Functional Requirements

| ID | Statement | Status |
|---|---|---|
| FR-001 | `DoctrineSelectionConfig` MUST expose `selected_<kind>` for every artifact kind in `DoctrineService`: `directives`, `tactics`, `styleguides`, `toolguides`, `paradigms`, `procedures`, `agent_profiles`, `mission_step_contracts`. `list[str]` of artifact IDs, defaulting to `[]`. | Proposed |
| FR-002 | `OrgCharterPolicy` MUST mirror FR-001 with `required_<kind>` per kind. Defaults to `[]`. | Proposed |
| FR-003 | `apply_org_charter_to_interview` MUST union each `required_<kind>` into the project's `selected_<kind>` non-destructively (existing entries preserved; duplicates not added). | Proposed |
| FR-004 | `spec-kitty charter sync` MUST extract `selected_<kind>` fields from fenced YAML blocks in `charter.md` into `governance.yaml`. Round-trip MUST preserve all kinds. | Proposed |
| FR-005 | `build_charter_context(action=..., profile=...)` MUST render every globally-selected artifact (across all 8 kinds) into the governance payload, inline body or fetch + when-doing stanza on token-budget overflow. New `_render_selected_<kind>` per kind. | Proposed |
| FR-006 | Charter MAY declare an `activations:` list of `(activation_context, doctrine_pack_id, artifact_id, optional artifact_kind)` tuples. `activation_context` is a dict with `mission_type` ∈ `{software-dev, documentation, research, plan, generic}` and `action` ∈ canonical action vocabulary or `generic`. `doctrine_pack_id` accepts `project`, `built-in`, or a configured pack name. | Proposed |
| FR-007 | `build_charter_context` MUST resolve activation entries matching the current `(mission_type, action)` (with `generic` as wildcard in either slot) and emit a "When you `<action>` in a `<mission_type>` mission, run `spec-kitty charter context --include <kind>:<id>` and apply the returned rule" stanza per match. | Proposed |
| FR-008 | Org-charter schema MUST allow `activations:` entries. They propagate to consumers via standard pre-fill. | Proposed |
| FR-009 | A Trigger Registry MUST exist as a canonical frozenset of agent-action tokens — at minimum `specify`, `plan`, `tasks`, `implement`, `review`, `merge`, `accept`, `charter.interview`, `charter.generate`, `charter.context`, plus fine-grained tokens (e.g. `write_comment`, `write_docstring`, `rename_identifier`, `add_dependency`). `test_trigger_registry_coverage.py` enforces no dead triggers. | Proposed |
| FR-010 | Shipped mission-type profiles MUST exist at `src/doctrine/missions/<type>/governance-profile.yaml` for `software-dev`, `documentation`, `research`, `plan`. Each declares default `selected_<kind>` and default `activations:` for that mission type. | Proposed |
| FR-011 | Charter resolver MUST read `meta.json mission_type`, pick the matching profile, and union its declarations. When no matching profile exists AND project has no declarations, resolution MUST hard-fail with clear message — no silent fallback to `software-dev-default`. | Proposed |
| FR-012 | Charter facade modules MUST exist at `src/charter/profiles.py`, `mission_steps.py`, `drg.py`, `primitives.py`, `resolution.py`, `versioning.py` — each re-exporting (or thinly wrapping) doctrine surfaces named in the audit. | Proposed |
| FR-013 | The 13 runtime files in `docs/development/runtime-charter-doctrine-boundary.md` (Appendix) MUST be migrated to import from `charter.<facade>` instead of `doctrine.*`. Exceptions MUST be documented and remain in a shrunken allowlist. | Proposed |
| FR-014 | `DoctrineLayerCollisionWarning` MUST extend to all 8 artifact kinds. Today's emission covers directives, tactics, agent_profiles only; Mission B extends to styleguides, toolguides, paradigms, procedures, mission_step_contracts. | Proposed |
| FR-015 | When `.kittify/config.yaml` `doctrine.org.packs` references a pack whose `local_path` does not exist, charter-context build MUST fail loudly naming the pack and the missing path — no silent skip. Policy change from Mission A. | Proposed |
| FR-016 | `spec-kitty doctrine new <kind> <name>` scaffolding command MUST exist. Writes a stub `<name>.<kind>.yaml` populated with required schema fields, in the right location (project-layer default; `--pack <path>` flag for pack-layer). | Proposed |
| FR-017 | `spec-kitty doctrine validate <path>` command MUST exist as a project-layer analogue of `spec-kitty doctrine pack validate`. Validates a single artifact YAML or a doctrine directory tree against the schemas. | Proposed |
| FR-018 | `spec-kitty doctor doctrine` MUST gain a "Selections" section listing, for each kind, the active globally-selected artifacts (project + org + mission-type profile) with their resolved pack source. | Proposed |

## Non-Functional Requirements

| ID | Statement | Threshold | Status |
|---|---|---|---|
| NFR-001 | WP prompt stays under the 32,000-character token budget from the prior mission. New selections + activations participate in fetch-substitution. | WP prompt ≤ 32,000 chars across layered-doctrine-org-layer-01KRNPEE WPs. | Proposed |
| NFR-002 | `_build_wp_prompt` latency stays within 1.5× the post-wp-prompt-governance-payload baseline. No N+1 walks or synchronous network calls in new resolver work. | `test_wp_prompt_build_latency.py` continues to pass (8s budget). | Proposed |
| NFR-003 | The 7-file ATDD spec at `bd95f1f5` MUST pass. 29 currently-failing assertions all green; boundary ratchet's allowlist shrunk to documented final size; 2 trigger-coverage tests remain green. | 7 files, target = all tests pass. | Proposed |
| NFR-004 | No new architectural-layer violation. `kernel ← doctrine ← charter ← specify_cli` invariants stay enforced. | 8/8 layer-rule tests pass. | Proposed |
| NFR-005 | Backward compatibility — charters lacking new fields behave as today. No `selected_styleguides` ⇒ empty styleguide selection (not error). No `activations:` ⇒ zero context-scoped entries. Existing fixtures continue to work without modification. | All 23 prior ATDD tests at `test_wp_prompt_governance_contract.py` remain green. | Proposed |
| NFR-006 | Glossary alignment. Every new domain term appears in `glossary/contexts/doctrine.md` with a canonical entry. | 10 new terms (Charter-Mediated Selection, Global Selection, Context-Scoped Selection, Activation Registry, Activation Context, Doctrine Pack ID, Trigger Registry, Charter Facade, Mission-Type Profile, selected_&lt;kind&gt;/required_&lt;kind&gt;). | Proposed |

## Constraints

| ID | Statement | Status |
|---|---|---|
| C-001 | The dependency direction `kernel ← doctrine ← charter ← specify_cli` (ADR `2026-03-27-1`) is non-negotiable. Charter facades may import from doctrine; runtime callers MUST NOT after migration. | Proposed |
| C-002 | The 7-file ATDD spec (`bd95f1f5`) is the canonical executable spec. Implementation MUST satisfy existing assertions verbatim. If an assertion is unrealistic, revise in a separate prior commit with explicit justification. | Proposed |
| C-003 | The boundary ratchet test MUST stay green throughout. Each migration WP that removes a file from the allowlist also removes its direct-import in the same commit. | Proposed |
| C-004 | The 13-file baseline MAY end with at most 2 documented exceptions (charter-bundle versioning callers if HiC accepts them). All other entries MUST be migrated. | Proposed |
| C-005 | Trigger registry initial population (FR-009) is a HiC-facing decision made at plan-time. Resolved set MUST appear in `plan.md` before implementation begins. | Proposed |
| C-006 | The policy change in FR-015 (hard-fail on missing pack) is a behaviour change from Mission A's silent skip. Mission MUST update org-doctrine-layer user docs to call out the change. | Proposed |
| C-007 | Glossary entries for the 10 new terms MUST be promoted from `candidate` to `canonical` before acceptance. | Proposed |

## Goals

- Make the charter the single authority for doctrine-artifact selection across all 8 kinds.
- Enable both global ("always active") and context-scoped ("when doing X in mission type Y") activation modes.
- Ship mission-type-specific governance profiles so a documentation mission no longer inherits software-dev governance.
- Enforce the runtime → charter → doctrine boundary with an architectural ratchet that prevents regression.
- Update operator UX (`doctrine new`, `doctrine validate`, `doctor doctrine` Selections) so user-authored doctrine artifacts are discoverable and auditable.

## Non-Goals

- Adding new doctrine artifact kinds. The 8 kinds defined by `DoctrineService` are the scope.
- Changing the doctrine-pack format. Mission A's pack contract stands.
- Rewriting `charter sync` from scratch. The extractor learns new fields; overall shape unchanged.
- Mission UI for managing activations or selections. CLI scaffolding (`doctrine new`) is in scope; interactive UIs are not.
- Charter write guards (original Mission B WP04 — symlinked `charter.md`). Deferred.
- `governance_references` (original Mission B WP03 — external authority documents). `authority_paths` from the prior mission covers the adjacent need. Deferred.

## Out-of-Scope (deferred to follow-ups)

- Auto-generation of mission-type profiles from charter content.
- Web/TUI dashboard surfacing activation registry contents.
- Migration of `tests/` files importing doctrine directly.
- `tests/specify_cli/` import migration.

---

## Acceptance Criteria

The mission is accepted when all of the following are true on the target branch:

1. **ATDD spec green.** The 7-file suite landed in `bd95f1f5`:
   - `tests/integration/test_user_doctrine_artifact_lifecycle.py` — 4/4
   - `tests/integration/test_org_pack_artifact_lifecycle.py` — 4/4
   - `tests/architectural/test_artifact_selection_completeness.py` — 3/3
   - `tests/architectural/test_trigger_registry_coverage.py` — 2/2 (already pass; stays green)
   - `tests/architectural/test_runtime_charter_doctrine_boundary.py` — pass with allowlist size ≤ 2
   - `tests/architectural/test_activation_registry_schema.py` — 4/4
   - `tests/missions/test_mission_type_profile_resolution.py` — 14/14
2. **No regression** in:
   - `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23
   - `tests/architectural/test_layer_rules.py` — 8/8
   - `tests/architectural/test_pytest_marker_convention.py` — 1/1
   - `tests/architectural/test_pytest_marker_correctness.py` — 2/2
   - `tests/architectural/test_wp_prompt_build_latency.py` — 2/2
   - `tests/contract/` — 237 / 1 skip / 0 fail
3. **Boundary migration complete.** Allowlist on `test_runtime_charter_doctrine_boundary.py` shrunk from 13 entries to at most 2 documented exceptions.
4. **Charter facade modules ship.** `src/charter/profiles.py`, `mission_steps.py`, `drg.py`, `primitives.py`, `resolution.py`, `versioning.py` exist and export the symbols named in the audit.
5. **Mission-type profiles ship** for software-dev, documentation, research, plan. Resolver picks the right one based on `meta.json mission_type` with no `software-dev-default` fallback.
6. **Operator CLI surfaces ship.** `spec-kitty doctrine new <kind> <name>`, `spec-kitty doctrine validate <path>`, and the extended `spec-kitty doctor doctrine` Selections section.
7. **Glossary promoted.** 10 new entries in `glossary/contexts/doctrine.md` promoted from `candidate` to `canonical`.
8. **Post-merge mission review** passes via `spec-kitty-mission-review` with no CRITICAL or HIGH findings unresolved.

---

## References

- `docs/development/doctrine-artifact-selection-preflight.md` — full user-journey investigation
- `docs/development/runtime-charter-doctrine-boundary.md` — boundary audit + migration plan
- `docs/development/mission-b-proposed-scope.md` — the original 7-WP proposed scope (this spec adopts the single-mission variant)
- `docs/development/layered-doctrine-resolution-design.md` — the original Mission A + Mission B blueprint
- `glossary/contexts/doctrine.md` — 10 new domain terms landed in `candidate` status
- `tests/architectural/test_runtime_charter_doctrine_boundary.py` — boundary ratchet (passes with 13-file baseline)
- 7-file ATDD suite committed at `bd95f1f5` — the canonical executable spec
- ADR `architecture/2.x/adr/2026-03-27-1-pytestarch-architectural-dependency-testing.md` — layer rule
