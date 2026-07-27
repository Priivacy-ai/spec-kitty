# Phase 0 Research — Execution-State Canonical Domain Surface

All carried-forward decisions are resolved from the ratified design notes (`docs/engineering_notes/runtime_and_state_overhaul/`), not re-litigated. No `[NEEDS CLARIFICATION]` remain.

## R-1 — Canonical module name & placement

- **Decision**: A net-new top-level `src/mission_runtime/` umbrella package.
- **Rationale**: Decided (Stijn, 2026-06-03) in doc 06 §4 — Screaming Architecture (package names the domain) + Strangler Fig (new home grows alongside the old). Preferred over harden-in-place for domain clarity.
- **Constraint**: Must be registered in `_DEFINED_LAYERS` in both `tests/architectural/conftest.py` and `tests/architectural/test_layer_rules.py`, or `test_no_unregistered_src_packages` fails. Spine respected: `kernel ← doctrine ← charter ← specify_cli`; `runtime`/`glossary` siblings at charter level.
- **Alternatives rejected**: harden-in-place under `specify_cli/core/` (loses domain clarity, keeps ExecutionContext in the CLI layer).

## R-2 — ExecutionContext owner shape (this slice)

- **Decision**: Realize **Stage C** of doc 06 §5 — relocate `resolve_action_context` into `mission_runtime/` as a stable façade that delegates to today's resolver. Defer **Stage B** (commit-owning `ExecutionOperation`/`CommitTarget`) to the out-of-scope step 7.
- **Rationale**: doc 06 §5 lean path is **C → B**; `resolve_action_context` already fuses planning+execution actions (doc 16 H1). The commit-seam atomicity (B) is tied to CommitTarget (step 7), explicitly excluded by spec C-008. So this slice stops at C.
- **Consequence**: `ExecutionContext` is an immutable value object (read/write/dest/cwd/prompt fields) exposed by the façade; atomicity enforcement is not added here (already structurally enforced by `safe_commit` per doc 06 §6 note).

## R-3 — Migration order (Strangler)

- **Decision**: (1) full-sequence ratchet gate → (2) umbrella + layer registration → (3) façade relocation → (4) strangle residue/path-builders → (5) repo-wide facade enforcement → (6) MissionStatus consumption → (7) field-drop fold-in.
- **Rationale**: doc 06 §6 order, adapted to this slice's scope. Ratchet first (ATDD; gates everything). Destination (umbrella+façade) before routing consumers. Field-drop folded onto the runtime_bridge edit from step 4.

## R-4 — Status import-migration classification strategy

- **Decision**: Classify by distinct `status.<submodule>` import string (25 distinct, ~225 occurrences), not per-file at plan time. Each submodule gets a decision: **PROMOTE** (widely-needed types → facade `__all__`), **ROUTE** (mission-level read/write → `MissionStatus`), or **PRIVATE** (no external consumer → `_`-prefix). Final per-submodule decision confirmed during IC-05; the widened boundary test enforces completeness. See `occurrence_map.yaml`.
- **Exemptions**: `coordination/status_transition.py` and `coordination/transaction.py` (10 occurrences) are internal domain plumbing — KEEP (doc 06 §4; spec C-004).
- **Rationale**: 225 per-file entries would be stale on the first commit; the boundary test (FR-015) is the real completeness gate, the map is the decision framework (DIRECTIVE_035).

## R-5 — `core/execution_context.py` shim strategy

- **Decision**: After relocation, `core/execution_context.py` keeps a thin re-export shim (`from mission_runtime import resolve_action_context, ExecutionContext`) only while consumers migrate; removed once no importer references it (FR-003). No parallel implementation retained (NFR-002).
- **Rationale**: Strangler safety — keep imports working during migration, delete at the end. Randy-Reducer IC forbids leaving a permanent second path.

## R-6 — Direct-to-target mode in the ratchet

- **Decision**: The ratchet adds a third fixture: a direct-to-target mission run with no worktree, asserting the gate resolves the declared target branch and refuses unauthorized mainline writes (operator ruling; FR-012, FR-021, C-001/C-002).
- **Rationale**: The operator ruling (2026-06-07) makes direct-to-target a first-class mode; the gate must be mode-correct, so the ratchet must cover it.
