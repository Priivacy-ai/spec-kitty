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
| WP01 | Org activations resolve-time wiring (shared seams + union + validation + durable invariant) | P0 | none | T001–T010 | ~2 src files + 4 test modules |

## Work Packages

---

## Work Package WP01: Org activations resolve-time wiring (Priority: P0)

**Goal**: Wire org-pack `activations:` into the runtime charter-context bootstrap text stanza via a resolve-time org∪project union at `_render_activation_block`, mirroring the `required_<kind>` precedent — consolidating the dedup identity key and org-charter document reader into single shared seams (so no third rescan copy accrues), validating org entries pre-`except`, and installing a bootstrap-mode-forced durable regression invariant against the merged-but-never-rendered class (#1465/#1242/#2365).

**Independent Test**: In a consumer repo with a registered org pack declaring an `activations:` entry and NO project-local `activations:` block, `build_charter_context(...).text` in bootstrap mode renders that entry in the `"Selected activations:"` stanza — failing on pre-fix HEAD, passing post-fix. `governance.yaml` verified org-pure; non-org repos byte-identical.

**Prompt**: `/tasks/WP01-org-activations-resolve-time-wiring.md`

**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, NFR-001, NFR-002, NFR-003, C-001, C-002, C-003, C-004

**Dependencies**: none

### Included Subtasks

- [x] T001 [red-first] FR-005 durable invariant `tests/charter/test_org_activations_reach_context.py`: reuse ONLY `_write_config` (not `_write_org_pack` — it writes an agent-profile pack, no activations); write a NEW `org-charter.yaml` with an `activations:` entry, no project-local block; force **bootstrap** via `build_charter_context` (no `context-state.json`, depth ≥ 2, NOT `_governance_text`/`advise` = compact); assert stanza contents. **RECORD pre-fix RED.**
- [x] T002 [red-first] `tests/charter/test_org_activations_resolution.py`: union/dedup (SC-002), malformed-present-pack raise (SC-003), missing-pack skip — via the REAL rescan, no stub. **RECORD pre-fix RED.**
- [x] T003 [char-test/FR-006] `tests/charter/test_iter_org_charter_docs.py` + a characterization test pinning the CURRENT `_read_org_required_selections`/`_load_doctrine_selection` org-union branch (`context.py:795-813`) — it has ZERO existing coverage; this is the safety net for T005. Gate T009 on it.
- [x] T004 [FR-003] Relocate `_activation_identity_key` (`org_charter.py:286`, no local dep) → `charter/activations.py`; re-import at `org_charter.py:44/:450`. `_fold_policies` tests gate import integrity.
- [x] T005 [FR-006 REQUIRED] Extract `_iter_org_charter_docs(repo_root)`; refactor `_read_org_required_selections` **onto it** (mandatory — fixes its pre-existing ~19–20 Sonar cognitive-complexity; guarded by T003). Campsite: add `_LOGGER.debug` before `_enumerate_org_pack_paths`'s silent `except` (`context.py:693`).
- [x] T006 [FR-001/002/004] `_read_org_activations(repo_root)` consuming T005's reader (runtime import `ActivationEntry`): `model_validate` each entry — raise on malformed present-pack, skip missing pack (NOT silent `continue`, C-002 override).
- [x] T007 [FR-001/002] Call `_read_org_activations` as a **SEPARATE** call in `_render_activation_block` (NEVER inside `_load_governance_activations` — its `except: return []` at `:2652` swallows the raise); union+dedup on shared key, project order preserved; place **before** the `if not activations: return ""` short-circuit (`:2680`) AND before the `except` (`:2692`).
- [x] T008 [NFR-002/003] Assert `governance.yaml` org-pure + non-org byte-identity. Extend `tests/charter/test_context_org_governance.py`.
- [x] T009 Turn T001/T002 GREEN; run `tests/charter/` + `tests/specify_cli/doctrine/test_org_charter*.py`; confirm T003 characterization + `required_<kind>` paths stayed green through T005.
- [x] T010 `ruff check` + `mypy` zero-issue on new + boy-scout-touched; complexity ≤ 15; no ≥3× literals (S1192); no suppressions.

### Implementation Notes

- **FR-004 double-swallow trap (load-bearing)**: the org read is a SEPARATE call in `_render_activation_block`; folding it into `_load_governance_activations` (own `except: return []`, `:2652`) OR placing it after the `except` (`:2692`) swallows the validation raise. Place the union before the `if not activations: return ""` short-circuit (`:2680`) so the org-only case renders (SC-001).
- Text stanza only (C-004) — do NOT touch `build_charter_context_json` `directives`/`tactics` arrays or compact-mode rendering (deferred; spec Deferred Items).
- Layer boundary (C-001): `charter` must not import `specify_cli.doctrine.org_charter`; the shared key lives in `charter.activations` (down-layer), the reader raw-scans YAML like the precedent.

### Parallel Opportunities

- T001/T002/T003 (independent test modules) can be authored in parallel; T004 and T005 are near-independent (different files) but both precede T006/T007.

### Dependencies

- None (single starting package).

### Risks & Mitigations

- **`required_<kind>` regression** from the T005 extraction → T003's characterization test (authored first) is the real safety net (the org-union branch had NO prior coverage — post-tasks squad finding).
- **Compact-mode false-green** → T001 forces bootstrap mode explicitly and avoids the `advise`/`_governance_text` compact harness.
- **FR-004 raise swallowed** → T007 pins the separate-call + pre-short-circuit placement.
- **OUT (tracked-home, NOT folded here)**: cross-module `"org-charter.yaml"` literal spread (7 files) + `f"required_{kind}"` S1192 in `org_charter.py` → follow-up ticket (see `adversarial-review.md`).
- **Swallowed validation raise** → T006 pins pre-`except` placement; T002 asserts the raise propagates.
- **DIRECTIVE_041 / dead-symbol ratchet** on the relocated key → single caller re-import (T003), no orphan left behind.
