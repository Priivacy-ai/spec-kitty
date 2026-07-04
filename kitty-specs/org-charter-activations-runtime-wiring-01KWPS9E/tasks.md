---
description: "Work package task list — Org-Charter Activations Runtime Wiring"
---

# Work Packages: Org-Charter Activations Runtime Wiring

**Inputs**: Design documents from `/kitty-specs/org-charter-activations-runtime-wiring-01KWPS9E/`
**Prerequisites**: plan.md (required), spec.md rev 2 (user stories), research.md

**Tests**: Red-first is mandatory (NFR-001) — every behavior claim proven through `build_charter_context(...).text` in bootstrap mode with a real org pack on disk, never through `render_activation_stanza`/`resolve_for_context`.

**Organization**: A single coherent work package. The fix is dominated by one file (`charter/context.py`) touched by every concern; splitting would force file-ownership overlap on a ~2-source-file change. Subtasks (`Txxx`) sequence the concern map (IC-01 → IC-02 → IC-03) with red-first ahead of production.

## Work Package Summary

| WP | Title | Priority | Dependencies | Subtasks | Est. Size |
|----|-------|----------|--------------|----------|-----------|
| WP01 | Org activations resolve-time wiring (shared seams + union + validation + durable invariant) | P0 | none | T001–T009 | ~2 src files + 4 test modules |

## Work Packages

---

## Work Package WP01: Org activations resolve-time wiring (Priority: P0)

**Goal**: Wire org-pack `activations:` into the runtime charter-context bootstrap text stanza via a resolve-time org∪project union at `_render_activation_block`, mirroring the `required_<kind>` precedent — consolidating the dedup identity key and org-charter document reader into single shared seams (so no third rescan copy accrues), validating org entries pre-`except`, and installing a bootstrap-mode-forced durable regression invariant against the merged-but-never-rendered class (#1465/#1242/#2365).

**Independent Test**: In a consumer repo with a registered org pack declaring an `activations:` entry and NO project-local `activations:` block, `build_charter_context(...).text` in bootstrap mode renders that entry in the `"Selected activations:"` stanza — failing on pre-fix HEAD, passing post-fix. `governance.yaml` verified org-pure; non-org repos byte-identical.

**Prompt**: `/tasks/WP01-org-activations-resolve-time-wiring.md`

**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, NFR-001, NFR-002, NFR-003, C-001, C-002, C-003, C-004

**Dependencies**: none

### Included Subtasks

- [ ] T001 [red-first] Author the FR-005 recurrence-class regression invariant `tests/charter/test_org_activations_reach_context.py`: org pack (`_write_org_pack`/`_write_config` harness) with an `activations:` entry + no project-local block → assert the entry surfaces in `build_charter_context(...).text` `"Selected activations:"` stanza in **bootstrap mode** (omit `context-state.json` / depth ≥ 2). Capture RED against pre-fix HEAD. Refactor-stable: assert stanza contents, not internal symbols.
- [ ] T002 [red-first] Author `tests/charter/test_org_activations_resolution.py`: union/dedup by 4-tuple identity (SC-002, org∪project, project first-seen order); malformed present-pack entry → raise (SC-003); missing pack → skip. Capture RED.
- [ ] T003 [FR-003] Relocate the 4-tuple identity key from `org_charter.py` (`_activation_identity_key`, ~:286-300) **down into `charter/activations.py`**; re-import at the single caller `org_charter.py` (~:450). Behavior-preserving; verify no `org_charter`-local dependency.
- [ ] T004 [FR-006] Extract shared `_iter_org_charter_docs(repo_root)` (pack-enumerate → load → parse) in `charter/context.py`; refactor `_read_org_required_selections` onto it (behavior-preserving; existing `required_<kind>` tests are the safety net). Add `tests/charter/test_iter_org_charter_docs.py`.
- [ ] T005 [FR-001/002/004] Add `_read_org_activations(repo_root)` consuming T004's reader: validate each entry via `ActivationEntry.model_validate` (raise on malformed present-pack; skip missing pack — NOT the precedent's silent skip, C-002 override); return validated list.
- [ ] T006 [FR-001/002] Union org activations into the list returned by `_load_governance_activations`, deduped on the shared key (T003), project first-seen order preserved — placed **before** `_render_activation_block`'s `except Exception: return ""` (beside line ~2679) so the FR-004 raise escapes to `build_charter_context`.
- [ ] T007 [NFR-002/003] Assert `governance.yaml` stays org-pure (org-only activation absent from written file yet present in stanza) and non-org repos resolve byte-identically. Extend `tests/charter/test_context_org_governance.py`.
- [ ] T008 Turn T001/T002 GREEN; run full `tests/charter/` + `tests/specify_cli/doctrine/test_org_charter*.py`; confirm the `required_<kind>` refactor (T004) left those paths green.
- [ ] T009 `ruff check` + `mypy` zero-issue on new + boy-scout-touched; complexity ≤ 15; no new literals ≥ 3× (S1192); no suppressions.

### Implementation Notes

- Attach point is load-bearing: the org read+validate+union must sit pre-`except` (T006) or FR-004's raise is swallowed.
- Text stanza only (C-004) — do NOT touch `build_charter_context_json` `directives`/`tactics` arrays or compact-mode rendering. Those are deferred (see spec Deferred Items).
- Layer boundary (C-001): `charter` must not import `specify_cli.doctrine.org_charter`; the shared key lives in `charter.activations` (down-layer), the reader raw-scans YAML like the precedent.

### Parallel Opportunities

- T001 and T002 (independent test modules) can be authored in parallel; T003 and T004 are near-independent (different files) but both precede T005/T006.

### Dependencies

- None (single starting package).

### Risks & Mitigations

- **`required_<kind>` regression** from the T004 extraction → keep it a pure behavior-preserving move; existing `_read_org_required_selections` tests gate it.
- **Compact-mode false-green** → T001 forces bootstrap mode explicitly.
- **Swallowed validation raise** → T006 pins pre-`except` placement; T002 asserts the raise propagates.
- **DIRECTIVE_041 / dead-symbol ratchet** on the relocated key → single caller re-import (T003), no orphan left behind.
