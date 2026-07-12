# Tasks: Runtime-Bridge God-Module Decomposition

**Mission**: runtime-bridge-degod-01KX8M1C · **Closes** #2531 · **Branch**: `design/runtime-bridge-degod`
**Inputs**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) (FR-002 gate) · [contracts/](./contracts/)

10 work packages. **WP01 (parity oracle) + WP02 (compat guard) are blocking safety nets** built on unmodified source before any extraction (C-004). Extractions WP03–WP10 all edit `runtime_bridge.py` (moving symbols out) → a **serial spine**; the allocator collapses them on the shared parent. Every extraction WP re-runs the WP01 oracle + WP02 guard as its acceptance gate. Identity/coord (WP10) is cut last.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | `canonical(decision, repo_root)` masking (MASK timestamp/ULIDs; PATH-NORMALIZE workspace_path/prompt_file/reason/origin.mission_path to per-run repo_root) | WP01 | ∥ WP02 |
| T002 | 3-entry harness: drive `decide_next`/`query_current_state`/`answer_decision` against a fresh `copytree` snapshot; run-advance real (ULID masked) | WP01 | — | [D] |
| T003 | CAPTURE-and-assert side effects (sync emit, coord commit, retrospective, answer-path emit `:3410`/commit `:3427`, engine `_append_event`/`_write_snapshot`) | WP01 | — | [D] |
| T004 | Per-entry fixture sub-ledgers: 29 Decision sites + both guards × 3 mission families (incl. both fail-closed defaults + `tasks` legacy-union); **coverage floor as a checkable count assertion** | WP01 | — | [D] |
| T005 | `reason`-normalizer meta-test (collapses path noise, NOT a semantic delta) | WP01 | — | [D] |
| T006 | Seed NFR-006 timing harness; prove the oracle GREEN on unmodified source at full floor | WP01 | — | [D] |
| T007 | Inventory the ~50 patched private symbols (4 idioms) mapped to their reaching entry point | WP02 | ∥ WP01 |
| T008 | Guard (A) behavioral sentinel per symbol, **driven through its reaching entry** (query/answer-only symbols driven there) | WP02 | — | [D] |
| T009 | Guard (B) static AST: identity re-export check + **forbid function-scope re-imports of compat names** | WP02 | — | [D] |
| T010 | Prove the compat guard GREEN on unmodified source | WP02 | — | [D] |
| T011 | Create `runtime_bridge_engine.py`; move the **grep-complete** `_internal_runtime` privates (`_read_snapshot`/`_load_frozen_template`@`:1322`/`:1375`/`_append_event`/`_write_snapshot`/`plan_next`) | WP03 | — |
| T012 | `_advance_run_state_after_composition` body → adapter (≤15); thin residual compat delegate for its 8-patch/9-attr surface | WP03 | — | [D] |
| T013 | Arch guard: no core reaches engine internals; add the #2531 decomposition pointer (FR-007) | WP03 | — | [D] |
| T014 | Guarded re-export of moved patched symbols; oracle + compat guard stay green | WP03 | — | [D] |
| T015 | Create `runtime_bridge_retrospective.py`; move the self-contained learning-capture cluster | WP04 | — |
| T016 | Seam unit tests; re-export patched symbols; oracle + compat green | WP04 | — | [D] |
| T017 | Create `runtime_bridge_io.py`; move feature-runs index / template discovery / run lifecycle / OC builder | WP05 | — |
| T018 | `gather_artifact_presence` fact-port (feeds FR-009) | WP05 | — | [D] |
| T019 | Lift the pure `resolve_commit_target` out of `_wrap_with_decision_git_log:226–261` | WP05 | — | [D] |
| T020 | Port unit tests (stubbed I/O); re-export; oracle + compat green | WP05 | — | [D] |
| T021 | Create `runtime_bridge_cores.py`; move tasks.md parse (`:343–473`, zero-dep) + `_extract_wp_heading` | WP06 | — |
| T022 | `ArtifactPresenceSnapshot` + pure `evaluate_guards(snapshot)` collapsing both guards; **preserve the fail-closed default** (guard_failures identical incl. order — SC-007) | WP06 | — | [D] |
| T023 | Reduce `_check_requirement_mapping_ready` (CC≈22) ≤15 | WP06 | — | [D] |
| T024 | Pure unit tests (in-memory, no I/O); re-export; oracle + compat green | WP06 | — | [D] |
| T025 | `DecisionEnvelope` + `step_or_blocked` (blocked/query/terminal pure; **step branch port-injected** via `prompt_exists` predicate); collapse the 29 Decision sites + 4× triad | WP07 | — |
| T026 | Own the query/answer materialize: reduce `_map_runtime_decision` (CC≈33) + `query_current_state` (CC≈16) + the 4 `_build_*_query_decision` builders ≤15 | WP07 | — | [D] |
| T027 | Pure unit tests; re-export; oracle + compat green (esp. the 14 query/answer sites) | WP07 | — | [D] |
| T028 | Create `runtime_bridge_composition.py`; move dispatch + run-state advance | WP08 | — |
| T029 | Isolate the `_should_dispatch_via_composition` **selection** seam (FR-008 — clean for gates #2535 WP14; import no gates code); both-branch fixture | WP08 | — | [D] |
| T030 | re-export; oracle + compat green | WP08 | — | [D] |
| T031 | `DecideNextContext` frozen dataclass (~14 fields) | WP09 | — |
| T032 | Rewrite `decide_next_via_runtime` as bootstrap/dependency-gate/composition-dispatch/decision-materialize early-return chain ≤15 (sub-sequence fallback if a single WP can't reach ≤15) | WP09 | — | [D] |
| T033 | Assert residual ≤15; oracle + compat green | WP09 | — | [D] |
| T034 | Create `runtime_bridge_identity.py`; move coord-branch naming / mission-ULID / primary-feature-dir (hottest fracture, fattest coverage) | WP10 | — |
| T035 | KEEP-IN-PLACE `_wrap_with_decision_git_log`; lazy-accessor for sibling-called identity symbols | WP10 | — |
| T036 | Assert NFR-005 residual-LOC target + NFR-006 timing parity; **zero `# noqa: C901` remain**; final oracle + compat green | WP10 | — |

## Work Packages

### WP01 — Parity oracle (WP-0a, BLOCKING safety net)
- **owned_files**: `tests/runtime/test_bridge_parity.py`, `tests/runtime/_bridge_oracle.py`, `tests/runtime/fixtures/bridge/README.md` · **dependencies**: none
- **requirement_refs**: FR-002, NFR-001, NFR-006, C-004 · **acceptance**: oracle green on unmodified source at the full coverage floor (checkable count)
- **safeguards**: this is the mission's safety net — a hollow oracle is also green; the coverage floor MUST be asserted. Drive ALL 3 entries. Never stub `next_step`.
- [x] T001 · [ ] T002 · [ ] T003 · [ ] T004 · [ ] T005 · [ ] T006

### WP02 — Compat-surface guard (WP-0b, BLOCKING safety net)
- **owned_files**: `tests/runtime/test_bridge_compat_surface.py` · **dependencies**: none
- **requirement_refs**: FR-012, C-004 · **acceptance**: guard green on unmodified source; every symbol's sentinel proven to fire (no false-green)
- **safeguards**: a sentinel driven through the wrong entry silently never fires — map each symbol to its reaching entry.
- [x] T007 · [ ] T008 · [ ] T009 · [ ] T010

### WP03 — Engine-adapter (FR-013)
- **owned_files**: `src/runtime/next/runtime_bridge_engine.py`, `src/runtime/next/runtime_bridge.py`, `tests/runtime/test_bridge_engine.py` · **dependencies**: WP01, WP02
- **requirement_refs**: FR-013, FR-007, FR-001, FR-006 · **acceptance**: all engine-privates concentrated (grep-complete); `_advance_run_state` ≤15; oracle + compat green
- **safeguards**: grep-complete site list (incl. `:1322`/`:1375`); the residual keeps only the compat delegate, logic is adapter-owned.
- [x] T011 · [ ] T012 · [ ] T013 · [ ] T014

### WP04 — Retrospective seam
- **owned_files**: `src/runtime/next/runtime_bridge_retrospective.py`, `src/runtime/next/runtime_bridge.py`, `tests/runtime/test_bridge_retrospective.py` · **dependencies**: WP01, WP02
- **requirement_refs**: FR-001, FR-006 · **acceptance**: seam extracted; oracle + compat green (incl. captured retrospective side-effect)
- [x] T015 · [ ] T016

### WP05 — Clean I/O ports
- **owned_files**: `src/runtime/next/runtime_bridge_io.py`, `src/runtime/next/runtime_bridge.py`, `tests/runtime/test_bridge_io.py` · **dependencies**: WP01, WP02
- **requirement_refs**: FR-001, FR-003, FR-006 · **acceptance**: ports extracted; `gather_artifact_presence` + `resolve_commit_target` present; oracle + compat green
- [x] T017 · [ ] T018 · [ ] T019 · [ ] T020

### WP06 — Pure cores + guard inversion (FR-009)
- **owned_files**: `src/runtime/next/runtime_bridge_cores.py`, `src/runtime/next/runtime_bridge.py`, `tests/runtime/test_bridge_cores.py` · **dependencies**: WP01, WP02, WP05
- **requirement_refs**: FR-009, FR-003, FR-004, NFR-003 · **acceptance**: `evaluate_guards` pure; fail-closed default + guard_failures order preserved (SC-007); pure unit tests no-I/O; oracle + compat green
- **safeguards**: the two fail-closed defaults + `tasks` legacy-union are the highest-risk relocation fixtures.
- [x] T021 · [ ] T022 · [ ] T023 · [ ] T024

### WP07 — Decision-builder + query/answer materialize (FR-011)
- **owned_files**: `src/runtime/next/runtime_bridge_cores.py`, `src/runtime/next/runtime_bridge.py`, `tests/runtime/test_bridge_decision_builder.py` · **dependencies**: WP01, WP02, WP06
- **requirement_refs**: FR-011, FR-004 · **acceptance**: 29 Decision sites collapsed; `_map_runtime_decision`/`query_current_state`/query builders ≤15; step-branch port-injected; oracle green on the 14 query/answer sites
- **safeguards**: shares `runtime_bridge_cores.py` with WP06 (serial — depends WP06). `step_or_blocked` step branch is port-injected (Path.is_file in `Decision.__post_init__`).
- [x] T025 · [ ] T026 · [ ] T027

### WP08 — Composition dispatch + FR-008 selection seam
- **owned_files**: `src/runtime/next/runtime_bridge_composition.py`, `src/runtime/next/runtime_bridge.py`, `tests/runtime/test_bridge_composition.py` · **dependencies**: WP03, WP07
- **requirement_refs**: FR-008, FR-004, FR-001 · **acceptance**: dispatch extracted; `_should_dispatch_via_composition` isolated + both-branch fixture; oracle + compat green
- **safeguards**: FR-008 — leave the selection a clean seam for gates #2535 WP14; import NO gates code.
- [x] T028 · [ ] T029 · [ ] T030

### WP09 — decide_next phase-split (FR-010)
- **owned_files**: `src/runtime/next/runtime_bridge.py`, `tests/runtime/test_bridge_decide_next.py` · **dependencies**: WP06, WP07, WP08
- **requirement_refs**: FR-010, FR-005, FR-004 · **acceptance**: 4-phase early-return chain; residual `decide_next_via_runtime` ≤15; oracle + compat green
- **safeguards**: if a single WP can't reach ≤15, use the noted sub-sequence fallback (don't re-add `# noqa`).
- [x] T031 · [ ] T032 · [ ] T033

### WP10 — Identity/coord port (LAST)
- **owned_files**: `src/runtime/next/runtime_bridge_identity.py`, `src/runtime/next/runtime_bridge.py`, `tests/runtime/test_bridge_identity.py` · **dependencies**: WP03, WP04, WP05, WP06, WP07, WP08, WP09
- **requirement_refs**: FR-001, FR-003, FR-004, FR-005, NFR-005, NFR-006 · **acceptance**: identity extracted; **zero `# noqa: C901` remain repo-wide in the module family**; NFR-005 residual-LOC + NFR-006 timing asserted; final oracle + compat green
- **safeguards**: hottest fracture (scars #2091/#1978/#1918/#1814/#2069; malformed coord → `git worktree` exit-128). KEEP-IN-PLACE `_wrap_with_decision_git_log`; lazy-accessor for sibling-called identity symbols.
- [ ] T034 · [ ] T035 · [ ] T036
