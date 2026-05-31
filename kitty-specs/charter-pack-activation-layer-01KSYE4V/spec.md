# Charter Pack Activation Layer

**Mission ID**: `01KSYE4VZ9V0S14NRC87XX92BP`
**Mission slug**: `charter-pack-activation-layer-01KSYE4V`
**Mission type**: software-dev
**Target branch**: `pr/charter-doctrine-mission-type-configuration`

---

## Overview

Phase 1 (`charter-doctrine-mission-type-configuration`) introduced mission-type configuration
in the doctrine layer and the first `charter activate mission-type` command. Three post-implementation
reviews identified that the work was architecturally sound but incomplete: the charter activation
state is written but never read, other doctrine artifact kinds (directives, tactics, styleguides,
toolguides, paradigms, procedures, agent profiles, mission step contracts) have no activation
mechanism, two WPs produced correctly-implemented components that are never called, and six
architectural tests fail on the branch.

This mission completes the intent. The charter module becomes the authoritative filtered view over
doctrine. A default charter pack ships with spec-kitty so that existing users retain all currently
available behavior under the new hard-restriction model. The upgrade pipeline gains safe migration
behavior. The activation surface extends to all nine doctrine artifact kinds, with explicit cascade
control and a consistency validation command.

---

## Domain Language

| Term | Definition | Avoid confusing with |
|------|-----------|----------------------|
| **charter pack** | The project's curated selection of doctrine artifacts, stored at `.kittify/charter/charter.md` | The charter file itself (which contains governance rules beyond activation) |
| **doctrine pack** | The catalog of artifacts available for activation; the built-in spec-kitty doctrine pack is the default baseline | The activated set |
| **pack context** | The resolved combination of an active charter pack and a doctrine pack; the context in which WP lifecycle decisions are made | Charter alone |
| **activation** | The act of explicitly selecting a doctrine artifact for use in this project | Enabling, turning on |
| **deactivation** | Removing a doctrine artifact from the project's selection | Disabling, deleting |
| **hard restriction** | When a charter has explicit activations for an artifact kind, only those artifacts are available; no implicit fallback to the full doctrine catalog | Soft restriction, recommendation |
| **cascade** | Propagating an activation or deactivation to referenced artifacts of other kinds | Automatic cascade (cascade is always explicit opt-in) |
| **orphaned artifact** | An artifact in the charter whose kind is no longer referenced by any other active artifact | Dead code |
| **activation kind** | One of the nine activatable axes — `mission-type`, `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, `agent_profile`, `mission_step_contract` (legacy) | DRG-internal node kinds (`action`, `glossary_scope`, `glossary`) which are graph infrastructure, not user-activatable |
| **consistency violation** | A charter pack that references an artifact absent from the active doctrine pack, or a WP that references an artifact absent from the charter pack | |

### Activation Kinds Reference

| CLI kind | Doctrine service property | Description |
|----------|--------------------------|-------------|
| `mission-type` | _(managed separately via `PackContext`)_ | Which mission types this project can run |
| `directive` | `directives` | Governance directives defining principles and constraints |
| `tactic` | `tactics` | Implementation tactics describing how directives are applied |
| `styleguide` | `styleguides` | Code style and format guidelines |
| `toolguide` | `toolguides` | Tool usage and integration guides |
| `paradigm` | `paradigms` | Design paradigms and architectural patterns |
| `procedure` | `procedures` | Step-by-step operational procedures |
| `agent_profile` | `agent_profiles` | LLM agent behavioral profiles for WP assignment |
| `mission_step_contract` | `mission_step_contracts` | Mission step execution contracts _(legacy; present for completeness)_ |

> **DRG-only node kinds** (`action`, `glossary_scope`, `glossary`) are internal graph infrastructure and are not user-activatable artifacts.

---

## User Journeys

### Journey 1 — New project receives default charter pack

A developer runs `spec-kitty upgrade` on a project that has no charter file. The upgrade
writes the default charter pack to `.kittify/charter/charter.md`. The terminal displays a
summary of what was written: all nine activation kinds, with all built-in artifacts listed
and marked as activated. The developer takes no further action; all previously available
behavior continues to work unchanged.

### Journey 2 — Existing project upgraded safely

A developer runs `spec-kitty upgrade` on a project that already has a charter file. The
upgrade detects the existing file, creates a timestamped backup at
`.kittify/charter/charter.md.bak`, merges the default pack entries for any activation
kind not yet present in the existing charter, and prints a prominent warning: "Your charter
file was updated. Please review `.kittify/charter/charter.md` before continuing, then
run `charter pack consistency-check` to confirm coherence." No activation entries that
were explicitly set by the user are overwritten.

### Journey 3 — Activating a mission type without cascade

A developer runs `charter activate mission-type research`. The mission type is added to the
charter's activated mission types. The command then prints a warning listing the agent profiles,
directives, tactics, styleguides, toolguides, paradigms, and procedures referenced by the
`research` mission type that are not currently activated, and suggests either running
`charter activate mission-type research --cascade agent_profile,tactic` or
`charter pack consistency-check` to review the full picture.

### Journey 4 — Activating with cascade

A developer runs `charter activate mission-type research --cascade agent_profile,tactic`. The
mission type is activated. All agent profiles referenced by `research` are also activated. All
tactics referenced by `research` are also activated. Directives, styleguides, toolguides,
paradigms, and procedures are not cascaded because those kinds were not included in `--cascade`.
The terminal confirms which artifacts were activated and which were skipped by scope.

### Journey 5 — Deactivating with cascade

A developer runs `charter deactivate mission-type software-dev --cascade agent_profile`. The
`software-dev` mission type is deactivated. The cascade then deactivates all agent profiles
that are exclusively referenced by `software-dev` (i.e., not referenced by any other currently
active mission type). Agent profiles shared with other active mission types are left untouched,
and the terminal lists which ones were skipped and why ("shared with: research").

### Journey 6 — Reviewing activation state

A developer runs `charter list`. The terminal shows all activated artifacts grouped by kind,
covering all nine activation kinds (mission-type, directive, tactic, styleguide, toolguide,
paradigm, procedure, agent_profile, mission_step_contract). Kinds with zero activated
artifacts are shown with an empty marker so the operator can see which axes are fully
restricted. Running `charter list --show-available` adds the full doctrine catalog alongside
the activated set, with visual distinction between activated and available-but-not-activated
artifacts.

### Journey 7 — Consistency check reveals a gap

A developer runs `charter pack consistency-check`. The command validates that every artifact
activated in the charter pack exists in the active doctrine pack, and that every artifact
referenced in WP templates or base prompt templates is also activated. The output describes
coherent axes as passing and lists any violations with the exact artifact identifier and a
suggested resolution command.

### Journey 8 — WP task finalization fails due to inactive profile

A developer runs `spec-kitty agent mission finalize-tasks` on a mission whose WP03 has
`agent_profile: researcher-robbie` in its frontmatter. The command detects that
`researcher-robbie` is not in the charter's activated profiles, prints a hard error
identifying the WP, the inactive profile, the currently activated profiles, and the exact
command to resolve it (`charter activate profile researcher-robbie`), and exits non-zero
without writing any artifacts.

### Journey 9 — WP start fails due to inactive profile

A developer runs `spec-kitty agent action implement WP03`. Before creating or entering the
worktree, the command checks that the WP's assigned profile is activated in the charter.
Since `researcher-robbie` is not activated, the command prints a hard error with the profile
name, the activated set, and the resolution command, then exits non-zero. No workspace is
created or modified.

### Journey 10 — Review prompt tactic resolution fails fast

During a `spec-kitty next` review dispatch, the runtime attempts to resolve the tactic
`test-to-system-reconstruction` from the charter's filtered tactic set. The tactic is not
activated. The runtime hard-fails with an error: the tactic identifier, the activated tactic
set (which may be empty), and the command to activate it. The review does not start.

---

## Functional Requirements

| ID | Description | Priority | Status |
|----|-------------|----------|--------|
| FR-001 | A default charter pack ships as a first-party artifact of spec-kitty, covering all nine activation kinds (mission-type, directive, tactic, styleguide, toolguide, paradigm, procedure, agent_profile, mission_step_contract) and listing all artifacts available in the built-in doctrine pack | Must | Proposed |
| FR-002 | `spec-kitty upgrade` on a project with no charter file writes the default charter pack and displays a summary of the activated artifacts | Must | Proposed |
| FR-003 | `spec-kitty upgrade` on a project with an existing charter file creates a timestamped backup before writing, merges default entries for any activation kind not yet present, and displays a prominent warning to review the resulting charter | Must | Proposed |
| FR-004 | `charter activate <kind> <id>` accepts all nine activation kinds: `mission-type`, `directive`, `tactic`, `styleguide`, `toolguide`, `paradigm`, `procedure`, `agent_profile`, `mission_step_contract` | Must | Proposed |
| FR-005 | `charter deactivate <kind> <id>` is a first-class command accepting all nine activation kinds | Must | Proposed |
| FR-006 | When `charter activate` or `charter deactivate` is run without `--cascade`, the command warns the user that artifacts of other kinds referenced by the target were not cascaded, and lists what was not cascaded | Must | Proposed |
| FR-007 | `--cascade all\|<kind>[,<kind>...]` (comma-separated list of activation kinds, or the shorthand `all`) on `charter activate` cascades activation to all artifacts of the selected kinds that the target artifact references | Must | Proposed |
| FR-008 | `--cascade all\|<kind>[,<kind>...]` on `charter deactivate` cascades deactivation to artifacts of the selected kinds that are **exclusively** referenced by the deactivated artifact; shared artifacts are left untouched and listed as skipped in the output | Must | Proposed |
| FR-009 | `charter list` displays all activated artifacts grouped by kind | Must | Proposed |
| FR-010 | `charter list --show-available` displays activated artifacts alongside all available artifacts from the doctrine pack, with visual distinction | Should | Proposed |
| FR-011 | `charter pack consistency-check` validates that every artifact in the charter pack exists in the active doctrine pack, and that every artifact referenced by WP templates or base prompt templates is activated | Must | Proposed |
| FR-012 | `charter pack consistency-check` produces actionable output: for each violation, the artifact identifier and a specific command to resolve it | Must | Proposed |
| FR-013 | The charter module's filtered DRG view is built on top of `doctrine.drg`'s unfiltered output; `doctrine.drg` itself is not modified | Must | Proposed |
| FR-014 | `charter.resolve_action_sequence` reads the mission-type activation state from the charter pack; the current silent no-op (writing an override file that is never read) is eliminated | Must | Proposed |
| FR-015 | `filter_graph_by_activation` is wired as the charter module's entry point for filtered DRG queries; it is called from the charter module, not from `doctrine.drg` | Must | Proposed |
| FR-016 | `MissionStepRepository` is wired to a production call site through the charter facade | Must | Proposed |
| FR-017 | `spec-kitty agent mission finalize-tasks` validates that every WP-assigned profile is present in the charter's activated profile set; any violation is a hard fail with the WP ID, the inactive profile, and the resolution command | Must | Proposed |
| FR-018 | `spec-kitty agent action implement` validates that the WP's assigned profile is activated in the charter before creating or entering a worktree; this is a non-optional precondition that hard-fails with an actionable error | Must | Proposed |
| FR-019 | DRG resolution and tactic lookup through the charter module hard-fail when the requested artifact is not in the activated set; errors include the artifact identifier, the activated set, and the resolution command | Must | Proposed |
| FR-020 | The C-004 architectural boundary violation in `src/doctrine/missions/mission_step_repository.py` is resolved; the module no longer imports from `charter.*` via `TYPE_CHECKING` | Must | Proposed |
| FR-021 | The `test_legacy_subpackage_is_gone` test false positive from namespace package semantics is corrected; the `find_spec` assertion is replaced with a source-file-only check | Must | Proposed |
| FR-022 | The eight tests in `test_template_governance_payload_contract.py` that reference deleted `command-templates/` paths are updated to the current doctrine layout | Must | Proposed |
| FR-023 | The `m_3_2_7_activate_builtin_mission_types` migration (WP12) is added to the dead-modules architectural test allowlist | Must | Proposed |
| FR-024 | The twelve newly-introduced public symbols currently missing from the dead-symbols allowlist are either wired to production call sites or explicitly added to the allowlist with justification | Must | Proposed |
| FR-025 | Test fixture files committed under tracked paths that cause the `test_no_tracked_test_feature_missions` architectural test to fail are removed or moved to untracked locations | Must | Proposed |
| FR-026 | The NFR-001 performance test is extended with a real-filesystem scenario that exercises actual YAML loading and `PackContext` construction against a non-mocked doctrine layout | Should | Proposed |
| FR-027 | A test is added that writes `mission_type_activations: [software-dev]` to a project config and asserts that `documentation`, `research`, and `plan` mission types are excluded from the resolved set | Must | Proposed |
| FR-028 | The stale `"mission_step_contracts"` kind string in `test_org_charter_pack_context.py` line 65 is corrected to the current canonical kind identifier | Must | Proposed |
| FR-029 | The subprocess call inside the `fast`-marked unit test is moved to an integration test with an appropriate mark | Should | Proposed |
| FR-030 | The vacuous assertion in the decision dispatch test is replaced with a meaningful invariant check | Should | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Charter activation resolution overhead at WP claim time, measured against a real filesystem doctrine layout (not a mock) | ≤ 100ms p99 | Proposed |
| NFR-002 | `spec-kitty upgrade` charter backup completes atomically; if the process is interrupted after backup but before write, the project is left in its original state | Zero data loss | Proposed |
| NFR-003 | `charter pack consistency-check` completes on the built-in doctrine pack | ≤ 2 seconds | Proposed |
| NFR-004 | All tests in the `fast`, `doctrine`, and `architectural` suites pass with zero failures after this mission | 0 failures | Proposed |
| NFR-005 | No existing `spec-kitty upgrade` behavior changes for users who do not have a charter file — only the addition of the default charter pack write | 100% backward-compatible | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | `doctrine.*` modules must not import from `charter.*` at module level or via `TYPE_CHECKING`; the C-004 architectural boundary is preserved and enforced by `tests/architectural/` | Binding |
| C-002 | `doctrine.drg` returns the full unfiltered dependency resolution graph; no filtering logic may be added to `doctrine.drg` itself | Binding |
| C-003 | A charter pack that references an artifact absent from the active doctrine pack is always a consistency violation; there is no silent fallback or degraded mode | Binding |
| C-004 | The default charter pack must list every artifact available in the built-in spec-kitty doctrine pack across all nine activation kinds at the time of the release that ships this mission; no artifact may be silently dropped by upgrading | Binding |
| C-005 | `charter deactivate --cascade` must never deactivate an artifact that is referenced by another still-active artifact of the same kind, regardless of cascade scope | Binding |
| C-006 | The WP start precondition check (assigned profile present in charter) must execute in the same process and transaction as the claim transition; it may not be deferred | Binding |
| C-007 | The `src/charter/packs/` directory is owned by the charter module; no other module may write to it | Binding |
| C-008 | Upgrade backup filenames must include a timestamp to avoid silently overwriting a prior backup on repeated upgrades | Binding |

---

## Success Criteria

1. A project with no charter file runs `spec-kitty upgrade` and receives the default charter pack; `charter list` confirms all built-in artifacts across all nine activation kinds are activated; no other behavior changes
2. Running `charter activate mission-type research` activates the mission type, emits the no-cascade warning, and the change is reflected in `charter list`
3. Running `charter deactivate mission-type software-dev --cascade agent_profile` deactivates `software-dev` and all exclusively-referenced agent profiles, while shared agent profiles remain activated and are listed as skipped
4. `charter pack consistency-check` detects and reports at least one planted violation within the 2-second budget, with a resolvable error message
5. A WP with an inactive profile assigned in frontmatter fails `finalize-tasks` with a non-zero exit code and a message identifying the WP, the inactive profile, and the resolution command
6. The same WP also fails `agent action implement` at precondition check, before any worktree is created
7. `charter.resolve_action_sequence` returns only activated mission types when `mission_type_activations` is explicitly set; the override file is no longer ignored
8. `filter_graph_by_activation` is called from the charter module in at least one live code path that affects a user-visible command
9. `MissionStepRepository` is instantiated and called from a production path accessible via a user-facing command
10. `pytest tests/architectural/` exits with 0 failures after all changes
11. `pytest tests/ -m "fast or doctrine"` continues to exit with 0 failures

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `CharterPack` | Container holding the project's activation selections across all nine activation kinds; serialized in the charter file |
| `PackContext` | Runtime combination of an active `CharterPack` and a `DoctrinePack`; the context in which WP lifecycle decisions are evaluated |
| `DoctrinePack` | The inventory of artifacts available for activation; defaults to the built-in spec-kitty doctrine pack |
| `ActivationKind` | Enumeration: `mission_type`, `profile`, `directive`, `tactic` |
| `ActivatedArtifact` | A reference to a specific doctrine artifact by kind and ID that has been selected in a charter pack |
| `CascadeScope` | The set of artifact kinds to include in a cascade operation: any combination of `profiles`, `directives`, `tactics`, or the shorthand `all` |
| `ConsistencyReport` | The output of `charter pack consistency-check`; lists violations, passing axes, and resolution commands |
| `CharterBackup` | A timestamped copy of an existing charter file created before an upgrade merge |

---

## Assumptions

- The built-in spec-kitty doctrine pack is the authoritative baseline for consistency checks; org-level and project-level doctrine layers may extend it but are not in scope for the default charter pack
- "Referenced by" relationships (used by cascade and consistency check) are derived from the doctrine artifact definitions, not from runtime usage; if a mission type's YAML definition lists a profile, that constitutes a reference
- The `charter.md` file serves dual purpose: governance rules (existing) and activation state (new); activation state is stored in a dedicated section to avoid conflicts with existing governance content
- A project may have zero activated artifacts for a given kind; this is a valid (though unusual) state representing full restriction — no artifacts of that kind are available
- Org-charter extension chains with `mission_type_activations` are not in scope for this mission; they are explicitly listed as unknown in the prior adversarial review

---

## Out of Scope

- Org-level or project-level doctrine pack support (only the built-in doctrine pack is the baseline for this mission)
- `charter activate` for artifact kinds beyond mission-type, profile, directive, and tactic (e.g., step templates, contract schemas)
- SaaS synchronization of charter pack state
- Visual / GUI charter management
- Automatic migration of WP frontmatter when a profile is deactivated
- Resolving the broader "doctrine mission-type list org/project layers" gap identified in the adversarial review (WP13 docstring overclaim)
