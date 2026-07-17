# Work Packages: Bundle-Freshness Content-Identity — Missing-File Robustness + Directive-Activation Visibility

**Inputs**: Design artifacts in `/kitty-specs/bundle-freshness-hash-input-and-activation-01KXR0M1/` (spec.md, plan.md, data-model.md)
**Prerequisites**: plan.md (required), spec.md, data-model.md
**Bundles**: GitHub #2758 + #2759. **Base**: stacked on `fix/2681-synthesized-drg-stale` (PR #2732).

**Organization**: Strictly-linear WP chain (single_branch). ATDD-first (C-011): each WP commits a red-first
test BEFORE implementation. Each WP is independently deliverable and testable.

**Prompt Files**: `/kitty-specs/bundle-freshness-hash-input-and-activation-01KXR0M1/tasks/WPxx-*.md`.

---

## Work Package WP01: Shared directive-resolution helper + synthesizer refactor (Priority: P1) 🎯 MVP

**Goal**: Extract the synthesizer's resolved-directive logic (`_synthesis.py:76-79`, absent→`[]` per #2577)
into ONE public charter-side helper `charter.compiler.resolve_synthesis_graph_directives(repo_root)`, and
refactor `_synthesis.py` to consume it — behavior-preserving. This establishes the single authority the
freshness hash and the synthesizer will share (FR-002/FR-004).
**Independent Test**: `pytest tests/charter/test_synthesis_graph_directives.py` (new helper: absent→`[]`,
present→resolved) AND `tests/charter/synthesizer/test_synthesize_path_parity.py` stays green (refactor is
behavior-preserving).
**Prompt**: `tasks/WP01-shared-directive-resolver.md`
**Requirements**: FR-002, FR-004

### Included Subtasks
- [ ] T001 (red-first) Test `resolve_synthesis_graph_directives`: absent `activated_directives` → `[]`; present → `resolve_config_activated_roots(...).directives`; ids derived from the resolver, not hardcoded.
- [ ] T002 Implement the helper in `src/charter/compiler.py` (public, add to `__all__`); refactor `_synthesis.py` so `selected_directives` + `drg_nodes` source from it; leave `selected_paradigms` inline (inert, unchanged).

### Dependencies
- None (foundational).

### Risks & Mitigations
- **Risk**: refactor changes synthesizer behavior. **Mitigation**: `test_synthesize_path_parity` must stay green; `drg_nodes` still built from the returned list (same-list invariant, `_synthesis.py:97-107`).

---

## Work Package WP02: Content-identity recipe — swap references.yaml → directive digest, fail-safe (Priority: P1)

**Goal**: In `src/charter/bundle.py`, remove `references.yaml` from `BUNDLE_CONTENT_HASH_FILES` (closes
#2758) and append a digest of the WP01 directive resolution (closes #2759 for directive activation), via a
**function-local** import of the helper (NFR-001), wrapping the resolver read to catch resolver exceptions
→ `None` (NFR-003/OQ-4). Reader/`promote`/`resynthesize` are unchanged (single-recipe propagation).
**Independent Test**: `pytest tests/charter/test_bundle_content_hash.py` + the flipped
`tests/specify_cli/charter_freshness/test_computer.py::test_synthesized_drg_stale_when_a_bundle_file_is_missing`.
**Prompt**: `tasks/WP02-content-identity-recipe.md`
**Requirements**: FR-001, FR-004, FR-005, FR-007, NFR-001, NFR-003, C-003

### Included Subtasks
- [ ] T003 (red-first) Recipe unit tests: missing `references.yaml` → NOT `None`/stale (#2758 flip); a directive-set change → hash moves; a no-op → hash stable; a drifted activated stem → `None` (NOT raise); malformed `config.yaml` → `None`; existing BOM/CRLF/non-UTF-8 guards stay green.
- [ ] T004 Implement: drop `references.yaml` from `BUNDLE_CONTENT_HASH_FILES`; append `hash_content("directives=" + ",".join(sorted(resolve_synthesis_graph_directives(repo_root))))` (function-local import) before the final combine; wrap the resolver read in `except (UnknownArtifactIdError, CharterPackConfigError, ValueError, OSError, UnicodeDecodeError): return None`; update docstring/comments. Do NOT touch `computer._BUNDLE_FILES` (C-003).

### Dependencies
- WP01 (consumes the shared helper).

### Risks & Mitigations
- **Risk**: module-level compiler import reorders `charter/__init__` and regresses the hot path. **Mitigation**: import the helper INSIDE `compute_bundle_content_hash` (function-local), matching the reader's deferred import (computer.py:422).
- **Risk**: broad `except` masks real bugs. **Mitigation**: scope the catch to the resolver read only (not the per-file loop / `hash_content`), with an inline rationale citing the never-raise contract (bundle.py:160).

---

## Work Package WP03: End-to-end freshness acceptance + migration + performance (Priority: P1)

**Goal**: Prove the mission end-to-end against `charter status`/`activate`/`deactivate`/`synthesize`
output: #2758 self-heals; directive activation is visible; non-graph kinds stay `fresh`; drifted-stem is
recoverable (no crash); no-op stable; legacy-`None` (FR-003) and recipe-migration (FR-007) self-heal as
distinct anchors; cross-caller bake; latency < 2s; all quality gates green.
**Independent Test**: `PWHEADLESS=1 pytest tests/specify_cli/charter_freshness/ tests/charter/synthesizer/test_performance_envelopes.py`.
**Prompt**: `tasks/WP03-freshness-acceptance.md`
**Requirements**: FR-003, FR-005, FR-006, FR-007, NFR-002, NFR-004

### Included Subtasks
- [ ] T005 (red-first) Acceptance: US1 (references absent → not stale, `charter status` output state+remediation); US2 (directive activate/deactivate → `stale` RED-on-base/GREEN; paradigm + tactic → `fresh`; no-op → unchanged; drifted-stem → recoverable `stale`, no crash; synthesize → `fresh`).
- [ ] T006 Migration + cross-caller: FR-003 (schema-"2" `None` self-heal) and FR-007 (schema-"3" recipe-mismatch one-time stale) as distinct anchors; confirm `promote`/`resynthesize` bake and `project_drg` preserves.
- [ ] T007 Perf + roster-stability + gates: extend `test_performance_envelopes.py` so the < 2s envelope reaches the graph-hash branch (catalog load); add the SC-004 roster-stability test (a built-in directive NOT in the activated set → hash unchanged); ≥90% diff coverage (specify_cli side self-policed); `ruff`/`mypy --strict`/terminology/dead-symbol gates green.

### Dependencies
- WP02.

### Risks & Mitigations
- **Risk**: paradigm/tactic-stays-`fresh` test is vacuous. **Mitigation**: perform a real config byte-change (activate a real paradigm/tactic id) and assert `fresh` on both base and post-fix.
- **Risk**: perf test doesn't exercise the new cost. **Mitigation**: assert the envelope reaches a non-`built_in_only` graph so the directive-digest/catalog branch runs.

---

## Dependency Graph

```
WP01 → WP02 → WP03   (strictly linear; single_branch)
```
