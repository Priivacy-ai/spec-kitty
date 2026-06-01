# Research: Org Doctrine Profile Integrity Activation Closure

This document captures the issue-derived research and architectural decisions for the mission. It intentionally pulls the relevant context from #1111, #1557, #1583, and #1584 so planning can proceed without reopening the issue threads.

---

## Source Issue Context

### #1111 - Release epic context

The parent epic tracks 3.2.0 charter/doctrine launch work. Most original launch-blocker slices are now closed, including lifecycle freshness, shipped DRG freshness, git policy, dashboard glossary resilience, organisation-layer DRG, monorepo charter visibility, composable workflow sequencing, and external governance references.

The remaining release-relevant work is concentrated in the charter activation and org-pack correctness path:

- #1557: complete deferred charter activation behavior from PR #1535.
- #1583: add a proper DRG relation for profile inheritance.
- #1584: make invalid org-pack profiles visible to repositories and diagnostics.

### #1557 - Charter activation follow-on

PR #1535 shipped the activation surface across nine doctrine artifact kinds, default pack support, consistency checks, and lifecycle gates. It deliberately deferred:

- cascade activation and deactivation,
- artifact ID validation on `charter activate`,
- production wiring for OperationalContext,
- cleanup items from adversarial review.

The issue records the concrete gap: `--cascade` is parsed but does not perform scoped graph traversal; no-cascade warning behavior is inverted or incomplete; invalid activation IDs can be written to config; OperationalContext exists but returns empty values and has no production call sites.

### #1583 - DRG profile lineage relation

Org doctrine packs need to express that an agent profile specializes another profile. The example motivating this mission is a domain-specific data-model analyst profile that inherits from a built-in analyst profile.

The current DRG relation vocabulary does not include a structural lineage relation. `delegates_to` is semantically wrong because it means runtime work handoff, not inheritance. `enhances` is less wrong but still imprecise. This forces org packs into lossy mappings and risks corrupting graph traversal semantics.

Decision needed: add `specializes_from` or a more general `extends` relation. The mission defaults to `specializes_from` because it matches the existing agent profile field and is precise for the immediate use case.

### #1584 - Profile load diagnostics

During rc30 to rc32 upgrade, org-pack agent profiles using now-disallowed `context-sources` keys failed validation. The loaded profile list was shorter, while the caller had no retained diagnostic path after construction. This made `doctor doctrine` appear healthy when only DRG counts were considered.

The observed failure mode is not simply "no warning ever exists"; repository construction may emit transient warnings. The durable problem is that consumers of `list_all()` cannot discover what was skipped unless they independently glob the pack directory and diff against returned IDs.

Decision needed: retain structured load diagnostics in the repository and expose them to doctor output.

---

## R-001 - Relation Name for Profile Lineage

**Decision**: Add `specializes_from` as the first-class DRG relation for agent profile lineage.

**Rationale**:

- The agent profile schema already uses `specializes_from`, so the graph relation matches the domain language users see in profile YAML.
- It avoids overloading `delegates_to`, which remains runtime work handoff.
- It is more precise than `enhances`, which does not imply inheritance or lineage.

**Alternative considered**: `extends`.

`extends` is more general and could apply to tactics or paradigms later. It is not chosen for this mission because no current issue requires cross-kind extension semantics, and broadening the term now would invite unplanned graph behavior. Future work may add `extends` separately or alias it after a research mission.

**Consequences**:

- DRG fixtures and validation tests must include at least one profile-to-profile `specializes_from` edge.
- Delegation traversal tests must prove lineage edges are not interpreted as runtime handoff.

---

## R-002 - Invalid Profile Handling Model

**Decision**: Keep `list_all()` valid-only, and add a durable diagnostic surface for skipped profiles.

**Rationale**:

- Returning invalid profiles as degraded objects would require a new runtime contract: can they be listed, assigned, activated, or rendered? That is too broad for a release-closure mission.
- Valid-only `list_all()` preserves existing callers.
- A diagnostic API makes invisible loss observable without letting invalid profiles enter runtime selection.

**Expected diagnostic fields**:

- `layer`: one of built-in, org, project.
- `path`: repository-relative or absolute path suitable for operator action.
- `profile_id`: parsed ID when present before validation fails; otherwise null.
- `error`: concise validation or parse error summary.

**Consequences**:

- Doctor can present a pack as degraded even when valid profiles and graph counts exist.
- Activation validation can distinguish "unknown ID" from "known file failed to load" when feasible.

---

## R-003 - Doctor Doctrine Health Semantics

**Decision**: `doctor doctrine` should surface invalid profile diagnostics in both human and JSON output, but it should remain a diagnostic command rather than a hard gate.

**Rationale**:

- The existing command is documented as a diagnostic with exit code 0. Changing exit behavior would be a bigger operator contract change.
- Human output must still make the degraded state visible.
- JSON output gives automation a stable way to fail CI if a project chooses to gate on invalid profiles.

**Consequences**:

- Tests should assert JSON fields, not only formatted text.
- Human output can evolve, but it must contain pack/layer/path/error enough for action.

---

## R-004 - Activation Validation Before Mutation

**Decision**: All activation commands that take an artifact ID validate the ID before writing activation state.

**Rationale**:

- #1557 shows current behavior can write arbitrary strings into config.
- Once invalid profiles are observable, the user should get a clearer result: unknown ID, invalid profile, or inactive dependency.
- Non-mutating failure is required to keep activation state trustworthy.

**Consequences**:

- Tests must compare config bytes before and after a failing activation.
- Error messages should point to `charter list --show-available` or `doctor doctrine` depending on failure type.

---

## R-005 - Cascade Semantics

**Decision**: Preserve explicit cascade scope from CLI to service and use graph/catalog references to determine cascade targets.

**Rationale**:

- #1557 records that collapsing `--cascade agent-profile,tactic` to boolean loses the user's requested scope.
- Cascade must be deterministic and auditable. Operators should know exactly what was activated, skipped by scope, deactivated, or skipped because it is shared.

**Consequences**:

- `--cascade all` is explicit; absence of `--cascade` never means all.
- Deactivation requires shared-reference analysis before mutation.

---

## R-006 - OperationalContext Scope

**Decision**: Wire OperationalContext only where this mission already needs it: work package claim/review lifecycle and `next` runtime decision boundaries.

**Rationale**:

- #1557 explicitly says OperationalContext is specced but not wired.
- A full retrofit across every context-aware resolver is larger than this release-closure slice.
- Populating it at the entry points removes the dead extension point and gives later context-aware activation work a stable carrier.

**Consequences**:

- Guard methods must be tested with real production-like context, not all-None stubs.
- Dead-symbol allowlist entries should be removed once call sites exist.

---

## R-007 - Agent Profile Context Selector Reachability

**Decision**: Make `charter context --include agent-profile:<id>` work by normalizing hyphenated selector kinds to their canonical doctrine kind before dispatch, and advertise the kind in help.

**Observed gap**:

- `build_charter_context_include()` (`src/charter/context.py`) lowercases the kind but does not convert hyphens to underscores. `_render_doctrine_artifact_include()` keys its renderer table on `agent_profile` (underscore), while every user-facing surface (e.g. `charter activate`) documents and accepts the hyphenated `agent-profile`.
- The result is that `--include agent-profile:<id>` raises `Unsupported --include selector kind 'agent-profile'`, even though the renderer for `agent_profile` exists. Operators currently reach profiles only via the Python API (`DoctrineService.agent_profiles`) or by reading the profile YAML directly.
- The `--include` help text lists `directive|styleguide|section` but never mentions agent profiles, so the capability is undiscoverable even in its working underscore form.

**Rationale**: The fix is a normalization + discoverability gap, not a new renderer. A single hyphen->underscore normalization of the selector kind aligns `--include` with the activation verbs and unblocks the documented `agent-profile` form (and `mission-step-contract`) without changing activation semantics.

**Consequences**:

- Add CLI coverage asserting human and `--json` rendering for `--include agent-profile:<id>`.
- Confirm normalization does not regress existing underscore/lowercase selectors.

---

## R-008 - Charter Catalog Completeness (`charter list --all`)

**Decision**: Add `charter list --all` that lists every available artifact per kind across built-in, org-pack, and project layers, and extend `CharterPackManager.list_available()` to include non-built-in artifacts.

**Observed gap**:

- `charter list` exposes only `--show-available`. Its availability source, `CharterPackManager.list_available()` (`src/charter/pack_manager.py`), scans only the built-in doctrine filesystem; the `ctx` parameter is explicitly ignored ("reserved for future org-pack support").
- Packaged artifacts (org-pack, project) are therefore invisible in the catalog, so an operator cannot see the full set of artifacts they could activate.

**Rationale**: This mission already makes org-pack profile state trustworthy (FR-005..FR-010) and validates activation IDs against the active catalog (FR-011). A catalog listing that silently omits the same packaged artifacts is inconsistent with that catalog-integrity goal. `--all` gives operators the complete activatable surface, annotated by source layer.

**Consequences**:

- `list_available()` must resolve org/project roots (reusing the same resolution used by activation validation) and annotate source layer.
- `--all` implies and supersedes `--show-available`; tests cover a fixture pack so non-built-in artifacts appear with their layer.

---

## R-009 - Refactoring & Cleanup Opportunities (do these first)

A critical read of the code paths behind FR-022..FR-026 shows the new findings are **symptoms of kind-vocabulary fragmentation**, not isolated bugs. Doing the small consolidation below first turns each FR into a one-line dispatch change instead of another special-case patch, and prevents the same gaps reappearing for sibling kinds (e.g. `mission-step-contract`).

### Observed state: one concept, five tables, three spellings

The set of doctrine artifact kinds is declared independently in at least five places, in three incompatible spellings:

| Location | Spelling | Shape | Used by |
|----------|----------|-------|---------|
| `doctrine/artifact_kinds.py` `ArtifactKind` (`_PLURALS`, `_PATTERNS`) | underscore singular (`agent_profile`) | **canonical** enum + plural + glob | doctrine layer (zero-dependency) |
| `charter/activations.py` `_SINGULAR_TO_PLURAL_KIND` / `normalize_artifact_kind()` | underscore singular -> plural | singular->plural map | activation registry resolution |
| `charter/pack_manager.py` `YAML_KEY_MAP` | **hyphen** (`agent-profile`, `mission-type`) | CLI token -> config YAML key | `charter activate` / `deactivate` |
| `charter/pack_manager.py` `_KIND_TO_DOCTRINE_DIR` | **hyphen** | CLI token -> (built-in dir, suffix) | `list_available()` |
| `cli/commands/charter/list_cmd.py` `_KIND_ORDER` | **hyphen** | display order | `charter list` |
| `charter/context.py` renderers dict + `_render_generic_artifact_include` candidate tuple | underscore singular | kind -> (service attr, label, renderer) | `charter context --include` |

`_PLURALS` (artifact_kinds) and `_SINGULAR_TO_PLURAL_KIND` (activations) are byte-for-byte the same data. `_PATTERNS` (artifact_kinds) equals the suffix column of `_KIND_TO_DOCTRINE_DIR`. None of the charter tables reference `ArtifactKind`.

### Root cause of FR-022 / FR-023

`charter context --include` (`build_charter_context_include`) lowercases the kind but applies **no hyphen->underscore normalization**, and its renderer table is keyed on the underscore form. Operators type the hyphenated `agent-profile` (the form `charter activate` documents and accepts), so it falls through to `Unsupported --include selector kind`. Note the existing `normalize_artifact_kind()` would **not** fix this either: it only maps singular->plural, not hyphen->underscore. So the canonical normalizer is itself incomplete for the operator token.

### Recommended cleanups (sequence before the FR work)

- **CL-1 — One operator-token normalizer.** Extend the canonical kind layer (preferably `doctrine.artifact_kinds`, with a thin `from_operator_token()` / hyphen-aware accessor) so a single function maps the operator hyphen token (`agent-profile`, `mission-step-contract`) to the canonical `ArtifactKind`, and route `charter context --include`, `activate`, `deactivate`, and `list` through it. Resolves FR-023; makes FR-022 a dispatch fix. Keep `mission-type` handled explicitly (see CL-4).
- **CL-2 — Collapse the context `--include` kind table onto the registry.** Replace the hand-maintained renderers dict + duplicated candidate-kind tuple in `context.py` so the supported kinds derive from the canonical set. This guarantees `agent-profile` (FR-022) *and* its siblings are reachable through the same path, instead of patching one kind.
- **CL-3 — Decouple layer from kind in `_KIND_TO_DOCTRINE_DIR`.** Today the constant bakes the `built-in` path segment into each entry and re-declares the file suffix that `ArtifactKind.glob_pattern` already owns. Split kind -> (base dir, glob from `ArtifactKind`) from the layer segment so `list_available()` can iterate {built-in, org, project} roots in a loop. This makes FR-025/FR-026 a clean traversal rather than a second hardcoded table.
- **CL-4 — Account for `mission-type` living outside `ArtifactKind`.** The charter surfaces cover **9** kinds; `ArtifactKind` enumerates 8 doctrine artifact kinds (plus `template`, minus `mission_type`). Mission types are a separate subsystem. Any consolidation must treat the charter kind set as `ArtifactKind` artifact kinds **plus** the explicit `mission-type` token, so planning does not assume one enum covers all nine. Flagging this prevents a refactor that silently drops or mis-routes mission-type.
- **CL-5 — `list_available()` signature carries layer roots as data, not `ctx`.** The `ctx` parameter is explicitly unused ("reserved for future org-pack support") — FR-026 is that future. Per C-008, resolve org/project roots in `specify_cli` (as `charter context` already does for `org_root`) and pass them in as data; do not reach into `specify_cli` from `charter`.

### Scope discipline

These are **enabling** refactors scoped to the kind-vocabulary surfaces this mission already edits. They are not a license to rewrite the activation engine, the DRG, or the broader doctrine loader. If CL-1..CL-3 prove larger than a contained change during planning, the fallback is the minimal patch (hyphen-normalize in `--include` only, add a parallel org/project scan) with a follow-on cleanup ticket — but the consolidated approach is preferred because it removes the drift that produced both findings.

---

## Deferred Research

- #1333 should become a follow-on mission for doctrine template discovery and DRG-backed template resolution.
- #1040 remains a design-spike / research-mission candidate for full ADR primitives. This mission only benefits from the existing idea of schema-registered policy artifacts; it does not implement ADR tooling.
