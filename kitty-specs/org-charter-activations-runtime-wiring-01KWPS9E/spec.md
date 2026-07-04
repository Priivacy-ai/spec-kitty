# Mission Specification: Org-Charter Activations Runtime Wiring

**Mission Branch**: `design/org-charter-activations-2365`
**Created**: 2026-07-04
**Status**: Draft
**Input**: Issue [#2365](https://github.com/Priivacy-ai/spec-kitty/issues/2365) (P0, bug/doctrine) — "org-charter.yaml activations (OrgCharterPolicy.activations, FR-008/WP06) are parsed/merged but never wired into runtime charter context."

## Problem Statement *(context)*

An org/departmental doctrine pack can declare action-scoped `activations:` in its `org-charter.yaml`. The registry field `OrgCharterPolicy.activations` is **parsed, schema-validated, folded across the `extends:` chain, and deduplicated** by `_fold_policies` — and then **discarded**: no runtime consumer reads `merged_policy.activations`. Declaring `activations:` in an org pack has **zero runtime effect** — `spec-kitty charter context --action <x>` never surfaces org-declared action-scoped directives/tactics. Every consuming engagement repo must hand-copy an equivalent `activations:` block into its own `charter.md`, which does not scale and drifts from the pack's intent.

**Root cause (traced to origin).** The origin mission `charter-mediated-doctrine-selection-01KRTZCA` specified this propagation explicitly — **FR-008: "Org-charter schema MUST allow `activations:` entries. They propagate to consumers via standard pre-fill"**, and its `contracts/activation-registry.md` lists `org-charter.yaml` as a valid activation-entry *source*. But the requirement's propagation half was **dropped, not deferred**: WP02 wired only the project `charter.md` path into `GovernanceConfig.activations`; WP06 wired only the org-pack-internal fold (T028); nobody wired WP06's output into the WP02/WP05 consumption path. A cross-WP integration seam was missed at tasks-finalize.

**This is a recurring class.** It is the **third** occurrence of "org-pack data merged internally but never reaches the render/consumption path" in this subsystem: [#1465](https://github.com/Priivacy-ai/spec-kitty/issues/1465) (`required_<kind>` render-drop, fixed), [#1242](https://github.com/Priivacy-ai/spec-kitty/issues/1242) (org charter present-but-not-surfaced, fixed), now #2365. The remediation therefore closes both the specific gap **and** installs a durable invariant against a fourth recurrence.

**Established precedent to honor (do not redesign).** The codebase already solved the identical org∪project split for `required_<kind>` → `selected_<kind>` via a **resolve-time union**, kept resolve-time precisely because the `charter` layer cannot import `specify_cli.doctrine.org_charter` (ADR 2026-03-27-1) and to keep `governance.yaml` project-pure:
- `_read_org_required_selections(repo_root)` (`charter/context.py`) — raw re-scan of each pack's `org-charter.yaml`, union across packs.
- `_load_doctrine_selection(repo_root)` (`charter/context.py`) — unions org selections into project `selected_<kind>`.

The fix mirrors this exact shape for `activations`. It does **not** add a generate-time path (no org content written into `governance.yaml`) — that would be a second, divergent shadow path, forbidden by the 3.2.x "no new shadow paths" goal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Org-declared activations reach consumers automatically (Priority: P1)

As an org/departmental doctrine-pack maintainer, I declare `activations:` in my pack's `org-charter.yaml` so that every consumer repo automatically surfaces those action-scoped directives/tactics at the matching mission step — without each consumer hand-copying the block into its own `charter.md`.

**Why this priority**: This is the entire defect. Without it the registry field is inert and org packs cannot ship action-scoped doctrine — the P0 release-blocking behavior.

**Independent Test**: Ship an org pack with one `activations:` entry, fetch it into a consumer repo that has **no** project-local `activations:` block, run `spec-kitty charter context --action <matching-action> --json`, and confirm the org-declared directive/tactic appears in the action-scoped arrays. This is fully testable end-to-end through the pre-existing `charter context` entry point.

**Acceptance Scenarios**:

1. **Given** an org pack `org-charter.yaml` with an `activations:` entry whose `activation_context` matches `{mission_type, action}`, **and** a consumer repo with no project-local `activations:` block, **When** `charter context --action <action>` resolves, **Then** the org-declared directive/tactic appears in the action-scoped `directives`/`tactics` arrays.
2. **Given** the same setup on pre-fix code, **When** the same resolution runs, **Then** the arrays are empty — proving the red-first repro through the pre-existing entry point.

---

### User Story 2 - The merged-but-never-rendered class cannot recur (Priority: P2)

As a platform maintainer, I want a durable regression invariant that fails whenever org-pack activation data is merged but not surfaced through `charter context`, so that a fourth recurrence of this class (after #1465, #1242, #2365) is structurally caught in CI rather than shipped.

**Why this priority**: Three recurrences in one subsystem is a pattern, not an accident. A behavioral invariant is the standing counter-measure and the mission's anti-regression teeth.

**Independent Test**: The regression test fails on pre-fix `HEAD` and passes post-fix; it asserts the behavioral guarantee (org activations reach `charter context`), not a literal code shape, so it survives refactors.

**Acceptance Scenarios**:

1. **Given** the regression test, **When** run against pre-fix code, **Then** it fails (org activation absent from resolved context).
2. **Given** the regression test, **When** run against post-fix code, **Then** it passes, and it does not assert internal function names or line shapes (refactor-stable).

---

### User Story 3 - Malformed org activations are surfaced, not silently dropped (Priority: P3)

As an org-pack maintainer, I want a malformed `activations:` entry in `org-charter.yaml` to raise a clear error at resolution, matching the project-side behavior (`_apply_activations_block` raises on bad entries) — rather than being silently swallowed by a raw-YAML re-scan.

**Why this priority**: Silent-drop is the exact "make degraded input quietly work" anti-pattern the charter forbids. Consistency with the project side prevents a maintainer from shipping a broken entry that vanishes without warning. Lower priority than the core wiring but a required-correctness property of it.

**Independent Test**: Feed an org pack with a structurally invalid activation entry; confirm resolution raises a clear, sourced error rather than dropping the entry and continuing.

**Acceptance Scenarios**:

1. **Given** an org `activations:` entry missing a required field, **When** `charter context` resolves, **Then** a clear error naming the offending pack/entry is raised (not a silent skip).

### Edge Cases

- **Exact-duplicate entry** declared in both org pack and project `charter.md` (same 4-tuple identity) → deduped to one; no double-render.
- **Distinct** org and project entries → both present; project entries retain first-seen order, org entries appended.
- **Multiple packs in the `extends:` chain** each declaring activations → unioned with last-duplicate-wins on identity, matching `_fold_policies`.
- **Compact-mode cache** (`context-state.json`) → the union must be reflected on genuine first-load, not masked by a stale cached action entry.
- **No org pack present** → behavior identical to today (project-only activations); zero regression for non-org repos.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Resolve-time union of org activations | As an org-pack maintainer, I want org-declared `activations:` unioned into the resolved charter context at `_render_activation_block`, mirroring `_load_doctrine_selection` for `required_<kind>`, so consumers surface them without hand-copying. | High | Open |
| FR-002 | Canonical 4-tuple dedup | As a maintainer, I want the union deduped by the identity `(activation_context, doctrine_pack_id, artifact_id, artifact_kind)`, org∪project, preserving project first-seen order, so duplicates never double-render. | High | Open |
| FR-003 | Single shared identity-key implementation | As a maintainer, I want the 4-tuple identity key to have ONE implementation shared by both the `org_charter` fold and the `charter`-layer resolve union (no second hand-rolled copy), so the two paths cannot drift. | Medium | Open |
| FR-004 | Validate org activations (no silent drop) | As an org-pack maintainer, I want malformed org activation entries validated (`ActivationEntry.model_validate`) and surfaced as an error at resolve time, consistent with project-side `_apply_activations_block`, so bad entries never vanish silently. | Medium | Open |
| FR-005 | Recurrence-class regression invariant | As a platform maintainer, I want a refactor-stable behavioral test asserting org-pack activations reach `charter context`, so the merged-but-never-rendered class (#1465/#1242/#2365) is structurally guarded against a fourth recurrence. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first through pre-existing entry point | Every behavior claim is proven by a test that fails on pre-fix `HEAD` and passes post-fix, exercised through the pre-existing `charter context` / `_render_activation_block` entry point — never through the fix's own new reader API. | Correctness | High | Open |
| NFR-002 | No new shadow path | No org-pack content is written into project `governance.yaml`; the union is resolve-time only. `governance.yaml` stays project-pure. Verified by asserting an org-only activation is absent from the written `governance.yaml` yet present in resolved context. | Reliability | High | Open |
| NFR-003 | Zero regression for non-org repos | A repo with no org pack resolves activations byte-identically to pre-fix behavior. | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Layer boundary (ADR 2026-03-27-1) | The `charter` layer MUST NOT import `specify_cli.doctrine.org_charter`. The resolve-side reader raw-scans `org-charter.yaml` like `_read_org_required_selections`; the shared identity key lives in the `charter` layer (`charter.activations`) so `org_charter` imports *down* into it. | Technical | High | Open |
| C-002 | Honor the established precedent | Mirror the `required_<kind>` resolve-time-union shape (`_read_org_required_selections` / `_load_doctrine_selection`); do not invent a generate-time fold or a parallel registry. | Technical | High | Open |
| C-003 | Preserve existing registry contract | Do not redesign `ActivationEntry` / `resolve_for_context` / `GovernanceConfig.activations`. Wire the missing source into the existing contract only. | Technical | High | Open |

### Key Entities

- **`ActivationEntry`** (`charter.activations`): an action-scoped activation record — `activation_context {mission_type, action}`, `doctrine_pack_id`, `artifact_id`, `artifact_kind`. Charter-layer-owned; validatable via `model_validate`.
- **`OrgCharterPolicy.activations`** (`specify_cli.doctrine.org_charter`): the folded org-pack registry list — parsed and deduped today, consumed by nothing.
- **`GovernanceConfig.activations`** (`charter`): the project-local activation list, populated from `charter.md`, consumed by `_load_governance_activations` → `resolve_for_context`.
- **Identity key** `(activation_context, doctrine_pack_id, artifact_id, artifact_kind)`: the dedup identity; currently duplicated implicitly, to be unified into one shared function (FR-003).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a consumer repo with **no** project-local `activations:` block, an org-pack-declared activation with matching `{mission_type, action}` appears in `charter context --action <action> --json` (currently: absent → target: present).
- **SC-002**: Org∪project union deduplicates exact-4-tuple duplicates to one entry; distinct project and org entries are both present; project first-seen order is preserved.
- **SC-003**: A malformed org activation entry raises a clear, pack-named error at resolve time (currently: no org path at all → target: validated-or-raised), matching project-side behavior.
- **SC-004**: A refactor-stable regression test fails on pre-fix `HEAD` and passes post-fix, permanently guarding the merged-but-never-rendered class; `governance.yaml` verified org-pure (NFR-002).
