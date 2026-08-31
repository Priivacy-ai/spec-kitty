# Mission Specification: Org-Charter Activations Runtime Wiring

**Mission Branch**: `design/org-charter-activations-2365`
**Created**: 2026-07-04
**Status**: Draft (rev 2 — post-spec squad folds: alphonso design + paula sizing, both opus)
**Input**: Issue [#2365](https://github.com/Priivacy-ai/spec-kitty/issues/2365) (P0, bug/doctrine) — "org-charter.yaml activations (OrgCharterPolicy.activations, origin requirement 008 / WP06) are parsed/merged but never wired into runtime charter context."

## Problem Statement *(context)*

An org/departmental doctrine pack can declare action-scoped `activations:` in its `org-charter.yaml`. The registry field `OrgCharterPolicy.activations` is **parsed, schema-validated, folded across the `extends:` chain, and deduplicated** by `_fold_policies` — and then **discarded**: no runtime consumer reads `merged_policy.activations`. Declaring `activations:` in an org pack has **zero runtime effect**. Every consuming engagement repo must hand-copy an equivalent `activations:` block into its own `charter.md`, which does not scale and drifts from the pack's intent.

**Where activations actually surface (verified post-spec — the reporter's mental model was off).** Activations render **only** in the **text** bootstrap stanza (`"Selected activations:"`), reached via `_render_activation_block` → `render_activation_stanza` → `resolve_for_context`. They do **not** populate the `charter context --json` structured `directives`/`tactics` arrays — those are fed by the DRG action-doctrine bundle (`build_charter_context_json` → `_load_action_doctrine_bundle` → `_collect_typed_artifacts`), which has zero activation wiring. Activations appear under `--json` only because the CLI splices `result.text` into the envelope's `context.text` field. **Project-local activations behave identically today** — they too surface only in the text stanza. This mission therefore brings org activations to **parity with project activations on the text stanza**; it does **not** invent a structured JSON activations surface (that would be a separate enhancement affecting both sources — see C-004 / Deferred Items).

**Also bootstrap-only (verified).** `_render_activation_block` runs only in bootstrap mode (`first_load`, effective depth ≥ 2). The compact/repeat-load path (`_render_compact_governance`) renders no activation stanza for project *or* org entries. This is pre-existing behavior; the org union inherits it (zero regression) and does not add compact-mode rendering. It is why the issue repro had to clear `context-state.json`.

**Root cause (traced to origin).** The origin mission `charter-mediated-doctrine-selection-01KRTZCA` specified this propagation explicitly — **its propagation requirement (numbered 008 there): "Org-charter schema MUST allow `activations:` entries. They propagate to consumers via standard pre-fill"**, and its `contracts/activation-registry.md` lists `org-charter.yaml` as a valid activation source. But the propagation half was **dropped, not deferred**: WP02 wired only the project `charter.md` path into `GovernanceConfig.activations`; WP06 wired only the org-pack-internal fold (T028); nobody wired WP06's output into the consumption path. A cross-WP integration seam missed at tasks-finalize.

**This is a recurring class.** Third occurrence of "org-pack data merged internally but never reaches the render/consumption path": [#1465](https://github.com/Priivacy-ai/spec-kitty/issues/1465) (`required_<kind>` render-drop, fixed), [#1242](https://github.com/Priivacy-ai/spec-kitty/issues/1242) (org charter present-but-not-surfaced, fixed), now #2365. The remediation closes the specific gap **and** installs a durable behavioral invariant against a fourth recurrence.

**Established precedent to honor (do not redesign).** The codebase already solved the identical org∪project split for `required_<kind>` → `selected_<kind>` via a **resolve-time union**, kept resolve-time precisely because the `charter` layer cannot import `specify_cli.doctrine.org_charter` (ADR 2026-03-27-1) and to keep `governance.yaml` project-pure:
- `_read_org_required_selections(repo_root)` (`charter/context.py:732-765`) — raw re-scan of each pack's `org-charter.yaml`, first-seen union across packs in config order.
- `_load_doctrine_selection(repo_root)` (`charter/context.py:768-813`) — unions org selections into project `selected_<kind>`.

The fix mirrors this shape's **union/order semantics** for `activations`. It does **not** add a generate-time path (no org content written into `governance.yaml`) — a second, divergent shadow path forbidden by the 3.2.x "no new shadow paths" goal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Org-declared activations reach consumers automatically (Priority: P1)

As an org/departmental doctrine-pack maintainer, I declare `activations:` in my pack's `org-charter.yaml` so that every consumer repo automatically surfaces those action-scoped activation entries in the charter-context bootstrap prompt at the matching mission step — without each consumer hand-copying the block into its own `charter.md`.

**Why this priority**: This is the entire defect. Without it the registry field is inert and org packs cannot ship action-scoped doctrine — the P0 release-blocking behavior.

**Independent Test**: Ship an org pack with one `activations:` entry, register it in a consumer repo (`doctrine.org.packs`) that has **no** project-local `activations:` block, resolve `build_charter_context(...)` in **bootstrap mode** (no cached `context-state.json`, or depth ≥ 2) for the matching action, and confirm the org-declared entry appears in the rendered `"Selected activations:"` **text stanza** (`result.text` / the `--json` `context.text` field). Reusable harness: `tests/charter/test_context_org_governance.py` (`_write_org_pack` + `_write_config`).

**Acceptance Scenarios**:

1. **Given** an org pack `org-charter.yaml` with an `activations:` entry whose `activation_context` matches `{mission_type, action}`, **and** a consumer repo with no project-local `activations:` block, resolved in bootstrap mode, **When** `build_charter_context(...)` renders, **Then** the org-declared entry appears in the `"Selected activations:"` text stanza of `result.text`.
2. **Given** the same setup on pre-fix code, **When** the same resolution runs, **Then** the stanza omits the org entry — proving the red-first repro through the pre-existing bootstrap entry point (not through `render_activation_stanza`/`resolve_for_context`).

---

### User Story 2 - The merged-but-never-rendered class cannot recur (Priority: P2)

As a platform maintainer, I want a durable regression invariant that fails whenever org-pack activation data is merged but not surfaced through the charter-context bootstrap render, so a fourth recurrence of this class (after #1465, #1242, #2365) is caught in CI rather than shipped.

**Why this priority**: Three recurrences in one subsystem is a pattern. A behavioral invariant is the standing counter-measure and the mission's anti-regression teeth.

**Independent Test**: The regression test forces **bootstrap mode** (omits `context-state.json` / passes depth ≥ 2), asserts the behavioral guarantee (org activation reaches the text stanza), not a literal code shape — so it survives refactors and does not false-green in compact mode.

**Acceptance Scenarios**:

1. **Given** the regression test run against pre-fix code in bootstrap mode, **Then** it fails (org activation absent from the rendered stanza).
2. **Given** the same test against post-fix code, **Then** it passes, asserting no internal function names or line shapes (refactor-stable).

---

### User Story 3 - Malformed org activations are surfaced, not silently dropped (Priority: P3)

As an org-pack maintainer, I want a **structurally malformed** `activations:` entry in a **present** `org-charter.yaml` to raise a clear error at resolution — matching the project-side behavior (`_apply_activations_block` raises `ValueError`) — rather than being silently swallowed.

**Why this priority**: Silent-drop is the "make degraded input quietly work" anti-pattern the charter forbids. Note this deliberately **diverges** from the mirrored `_read_org_required_selections`, whose blanket `except (OSError, YAMLError, ValueError): continue` silently skips — that error-handling is NOT mirrored (only union/order is; see C-002). Distinguish **missing pack on disk → skip** (diagnostic handled upstream) from **malformed entry in a present pack → raise**.

**Independent Test**: Register an org pack whose `org-charter.yaml` is present but contains a structurally invalid activation entry; confirm resolution raises a clear, pack-named error through the real rescan path (not a stub), rather than dropping the entry.

**Acceptance Scenarios**:

1. **Given** a present org pack with an `activations:` entry missing a required field, **When** the charter context resolves in bootstrap mode, **Then** `ActivationEntry.model_validate` raises a clear error naming the offending pack/entry, propagated out of the render (not swallowed).

### Edge Cases

- **Exact-duplicate entry** in both org pack and project `charter.md` (same 4-tuple identity) → deduped to one; no double-render.
- **Distinct** org and project entries → both present; project entries retain first-seen order, org entries appended.
- **Multiple packs** each declaring activations → first-seen union across packs in config order, dedup on the shared 4-tuple key (matching `_read_org_required_selections`; **not** the `extends:`-chain last-wins of `_fold_policies`).
- **Compact / repeat-load mode** → activations are first-load-only **by pre-existing design**; the org union inherits that visibility. No compact-path activation rendering is added or expected (do not chase a phantom compact wire).
- **No org pack present** → behavior byte-identical to today (project-only activations); zero regression for non-org repos.
- **Malformed org `activations:` on a present pack** → raise (US3); **missing pack on disk** → skip with upstream diagnostic.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Resolve-time union of org activations onto the text stanza | As an org-pack maintainer, I want org-declared `activations:` unioned into the resolved bootstrap text stanza at `_render_activation_block`, mirroring `_load_doctrine_selection` for `required_<kind>`, so consumers surface them without hand-copying. | High | Open |
| FR-002 | First-seen union + 4-tuple dedup | As a maintainer, I want the union deduped by the identity `(activation_context, doctrine_pack_id, artifact_id, artifact_kind)`, org∪project, preserving project first-seen order (first-seen across packs in config order — not `_fold_policies` chain semantics), so duplicates never double-render. | High | Open |
| FR-003 | Single shared identity-key implementation | As a maintainer, I want the 4-tuple identity key relocated from `org_charter.py` **down into `charter.activations`** (single caller at `org_charter.py:450`), shared by both the `org_charter` fold and the `charter`-layer resolve union, so the two paths cannot drift. | Medium | Open |
| FR-004 | Validate org activations pre-try (no silent drop) | As an org-pack maintainer, I want malformed org activation entries validated (`ActivationEntry.model_validate`) and the error propagated — with the org read placed **before** `_render_activation_block`'s `except Exception: return ""` (beside `_load_governance_activations`, context.py:2679) so the raise escapes to `build_charter_context`. Union/order semantics mirror `_read_org_required_selections`; its silent-skip error handling is explicitly **not** mirrored. | Medium | Open |
| FR-005 | Recurrence-class regression invariant | As a platform maintainer, I want a refactor-stable behavioral test (bootstrap-mode-forced) asserting org-pack activations reach the charter-context text stanza, so the merged-but-never-rendered class (#1465/#1242/#2365) is structurally guarded against a fourth recurrence. | High | Open |
| FR-006 | Shared org-charter document reader | As a maintainer, I want a single `_iter_org_charter_docs(repo_root)` (pack-enumerate → load → parse) consumed by **both** the `required_<kind>` union and the new activations union, so the fix does not leave a **third** hand-rolled raw-rescan copy — the exact duplication class that caused #2365. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first through the pre-existing bootstrap entry point | Every behavior claim is proven by a test that fails on pre-fix `HEAD` and passes post-fix, exercised through `build_charter_context(...).text` (or the `charter context` CLI) in **bootstrap mode** with a real org pack on disk. Forbidden red-first entry points (they green-before-and-after): `render_activation_stanza`, `resolve_for_context`, and any direct `ActivationEntry`-list construction. | Correctness | High | Open |
| NFR-002 | No new shadow path | No org-pack content is written into project `governance.yaml`; the union is resolve-time only. Verified by asserting an org-only activation is absent from the written `governance.yaml` yet present in the resolved text stanza. | Reliability | High | Open |
| NFR-003 | Zero regression for non-org repos | A repo with no org pack resolves activations byte-identically to pre-fix behavior. | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Layer boundary (ADR 2026-03-27-1) | The `charter` layer MUST NOT import `specify_cli.doctrine.org_charter`. The resolve-side reader raw-scans `org-charter.yaml` (charter-layer `_enumerate_org_pack_paths`, no `specify_cli` import); the shared identity key lives in `charter.activations` so `org_charter` imports *down* into it. Verified clean: `org_charter.py:44` already imports `ActivationEntry` from `charter.activations`. | Technical | High | Open |
| C-002 | Honor the precedent — union/order only | Mirror the `required_<kind>` resolve-time-union **shape and order semantics** (`_read_org_required_selections`/`_load_doctrine_selection`). Do NOT mirror its silent-skip error handling (FR-004 overrides). Do not invent a generate-time fold or parallel registry. | Technical | High | Open |
| C-003 | Preserve existing registry contract | Do not redesign `ActivationEntry` / `resolve_for_context` / `GovernanceConfig.activations`. Wire the missing source into the existing contract only. | Technical | High | Open |
| C-004 | Text-stanza scope only | In scope: org activations reach the `"Selected activations:"` **text stanza** (parity with project activations). OUT of scope: a structured `activations` key in `build_charter_context_json`'s payload, and compact-mode activation rendering — both affect project + org equally and are separate enhancements (Deferred Items). | Technical | High | Open |

### Key Entities

- **`ActivationEntry`** (`charter.activations`): action-scoped record — `activation_context {mission_type, action}`, `doctrine_pack_id`, `artifact_id`, `artifact_kind`. Charter-layer-owned; `model_validate`-able.
- **`OrgCharterPolicy.activations`** (`specify_cli.doctrine.org_charter`): the folded org-pack registry list — parsed/deduped today, consumed by nothing.
- **`GovernanceConfig.activations`** (`charter`): project-local list from `charter.md`, consumed by `_load_governance_activations` → `render_activation_stanza`.
- **Identity key** `(activation_context, doctrine_pack_id, artifact_id, artifact_kind)`: dedup identity, to be unified into one shared function in `charter.activations` (FR-003).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a consumer repo with **no** project-local `activations:` block, resolved in bootstrap mode, an org-pack-declared activation with matching `{mission_type, action}` appears in the `"Selected activations:"` text stanza of `build_charter_context(...).text` (currently: absent → target: present). Asserted through the bootstrap render, not `render_activation_stanza`/`resolve_for_context`.
- **SC-002**: Org∪project union deduplicates exact-4-tuple duplicates to one entry; distinct project and org entries are both present; project first-seen order is preserved.
- **SC-003**: A structurally malformed activation entry in a **present** org pack raises a clear, pack-named error at resolve time (propagated past the defensive `except`); a **missing** pack is skipped with the upstream diagnostic.
- **SC-004**: A refactor-stable, bootstrap-mode-forced regression test fails on pre-fix `HEAD` and passes post-fix, permanently guarding the merged-but-never-rendered class; `governance.yaml` verified org-pure (NFR-002); non-org repos byte-identical (NFR-003).

## Deferred Items *(out of scope — filed as follow-ups)*

- **Structured `activations` array in `charter context --json`**: today neither project nor org activations appear in the JSON `directives`/`tactics` arrays (DRG-fed) nor as a dedicated `activations` key. Surfacing them structurally is a separate enhancement affecting both sources. → file follow-up under #1799.
- **Compact-mode activation rendering**: activations are bootstrap-only by pre-existing design for both sources. → note on the follow-up.
- The issue-close comment for #2365 MUST correct the reporter's `--json`-arrays expectation and point at the delivered text-stanza surface + the follow-up.
