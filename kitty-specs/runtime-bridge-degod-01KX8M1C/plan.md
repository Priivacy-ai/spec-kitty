# Implementation Plan: Runtime-Bridge God-Module Decomposition

**Branch**: `design/runtime-bridge-degod` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)
**Input**: [spec.md](./spec.md) · **Research (FR-002 gate)**: [research.md](./research.md) — seam boundaries, parity contract, fixture matrix, compat strategy are FIXED there.

## Summary

Decompose the 3,813-LOC `src/runtime/next/runtime_bridge.py` into **6 flat
responsibility-named seam modules + a thin residual** (per the #2464 sibling),
via **Ports+cores** (#2173). It is a **behavior-preserving** refactor guarded by
two safety nets built first as separate blocking deliverables — **WP-0a** a
3-public-entry (`decide_next` / `query_current_state` / `answer_decision`)
**parity characterization oracle** with capture-and-assert side effects
(research §Parity) and **WP-0b** a per-entry **compat-surface guard** for the
50-symbol monkeypatch surface (research §Compat). Extraction proceeds in the
coupling-ordered sequence with the hot identity/coord port cut last.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing `src/runtime/next/` (`_internal_runtime` engine, `decision.py`); the #2464 `workflow.py` decomposition as the layout/`DecideNextContext`/lazy-accessor template; `pytest` (characterization + compat guards); `ruff --select C901` + radon (complexity gate)
**Storage**: N/A — refactor; `meta.json` / `feature-runs.json` / `tasks.md` are read through the extracted ports, not changed
**Testing**: `pytest` — WP-0a parity oracle (masked, frozen-snapshot, 3 public entries with capture-and-assert side effects + a `reason`-normalizer meta-test), WP-0b compat-surface guard (per-entry behavioral sentinel + static AST anti-shadowing), per-seam unit tests (pure cores in isolation; ports/adapter against stubs), and the full `runtime/next` suite staying green
**Target Platform**: Linux/macOS CLI library
**Project Type**: single
**Performance Goals**: no measurable `decide_next()` latency regression from added indirection (NFR-006)
**Constraints**: behavior-preserving (C-001); every function ≤15 with zero `# noqa: C901` (NFR-002); no new public surface (NFR-004); preserve the `runtime.next.runtime_bridge` import path + the 50-symbol private patch surface (FR-012); no new import cycle (C-007)
**Scale/Scope**: ~10–11 WPs (WP-0 split into WP-0a parity oracle + WP-0b compat guard — two distinct big deliverables); one 3,813-LOC module → 6 seam modules (`runtime_bridge_{engine,cores,io,composition,retrospective,identity}.py`) + a thin residual (~35–40% per the #2464 precedent; exact target confirmed in research)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** ✅ — one engine-adapter owns all `_internal_runtime.engine` private access (FR-013); one Decision-builder collapses the 29 open-coded constructions (FR-011).
- **Architectural alignment** ✅ — Ports+cores per #2173; flat sibling-convention layout per #2464; import path preserved (C-003).
- **DDD + tiered rigour** ✅ — pure cores (tasks.md parse, `evaluate_guards`, Decision-builder) get high rigour + isolation unit tests; ports/adapter contract-tested against stubs.
- **ATDD-first** ✅ — the WP-0a characterization lock (3-entry parity oracle + fixture ledger, proven green on unmodified source) and the WP-0b compat guard precede every extraction (C-004).
- **Campsite-first** ✅ — this mission *is* the campsite for the repo's largest god-module; no functional work rides along.
- **No legacy fallback** ✅ — behavior-preserving relocation, no compatibility branch on decision logic (C-001).

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)
```
kitty-specs/runtime-bridge-degod-01KX8M1C/
├── plan.md · spec.md · research.md (FR-002 gate)
├── data-model.md            # new types: ArtifactPresenceSnapshot, DecisionEnvelope, DecideNextContext, port/adapter interfaces
├── contracts/
│   ├── parity-oracle.md      # the characterization safety net (normalization + fixtures + side-effect isolation)
│   └── compat-surface.md     # the 50-symbol monkeypatch preservation + guard test
├── quickstart.md            # maintainer workflow with the decomposed modules
└── tasks.md                 # /spec-kitty.tasks output
```

### Source Code (repository root)
```
src/runtime/next/
├── runtime_bridge.py            # THINNED residual: 4-phase decide_next_via_runtime, query/answer, DecideNextContext,
│                                #   guarded compat re-export block, __all__, #2531 pointer
├── runtime_bridge_engine.py     # NEW (FR-013): sole home of _internal_runtime.engine privates
├── runtime_bridge_cores.py      # NEW (pure): tasks.md parse; ArtifactPresenceSnapshot+evaluate_guards (FR-009); Decision-builder (FR-011)
├── runtime_bridge_io.py         # NEW (ports): feature-runs index, template discovery, run lifecycle, OC, gather_artifact_presence, resolve_commit_target
├── runtime_bridge_composition.py# NEW: dispatch + run-state advance + FR-008 selection seam
├── runtime_bridge_retrospective.py # NEW: learning-capture
├── runtime_bridge_identity.py   # NEW: hot identity/coord port (cut LAST)
└── decision.py                  # unchanged (its :428 lazy edge stays lazy — C-007)

tests/runtime/
├── test_bridge_parity.py        # WP-0a characterization oracle (3 entries, masked, frozen snapshots, capture-and-assert)
├── test_bridge_compat_surface.py# WP-0b compat guard (per-entry behavioral sentinel + AST anti-shadowing)
└── test_bridge_<seam>.py        # per-seam unit tests
```

**Structure Decision**: Flat responsibility-named modules (not a `ports/`|`cores/` subdir), preserving the `runtime.next.runtime_bridge` import path used by ~13 prod + ~40 test sites.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns follow the research §Seams coupling-ordered extraction sequence. This is a
> single-god-module refactor: nearly every WP edits `runtime_bridge.py` (moving symbols
> out), so the lanes are inherently a **serial spine** — the allocator will collapse
> them on the shared parent file. Value is the decomposition, not parallelism.

### IC-01a — Parity oracle (WP-0a, BLOCKING)
- **Purpose**: Build the `decide_next()` parity oracle across **all 3 public entry points** (`decide_next_via_runtime`/`query_current_state`/`answer_decision_via_runtime`) and prove it green on **unmodified** source at the full coverage floor. Implements contracts/parity-oracle.md: masking contract with per-run `repo_root` normalization + the `reason`-normalizer meta-test; **capture-and-assert** side effects (sync emit, coord commit, retrospective, the answer-path emitter, engine `_append_event`/`_write_snapshot`); the 22–26 per-entry fixture sub-ledgers with the every-site/every-guard-branch coverage floor. Also seeds the **NFR-006 before/after timing harness** on the matrix.
- **Acceptance**: green on unmodified source **AND** the coverage floor asserted as a checkable count (sites/guard-branches reached ≥ floor) — a hollow oracle is also green on unmodified source, so green alone is insufficient.
- **Requirements**: FR-002, C-004; NFR-001; NFR-006 (harness); enables all. **Depends-on**: none (first).
- **Risks**: the whole mission's safety depends on this; if the oracle under-covers (esp. the query/answer-only sites incl. `_map_runtime_decision` CC33), extractions can silently drift. Coverage floor is binding.

### IC-01b — Compat-surface guard (WP-0b, BLOCKING)
- **Purpose**: Build the two-part compat guard (contracts/compat-surface.md) over the 50 symbols and prove it green on unmodified source. **Per-entry behavioral sentinel** — each symbol mapped to its reaching entry (`decide_next`/`query`/`answer`) and its sentinel driven through **that** entry (a single-entry sentinel is itself false-green for query/answer-only symbols) — plus the static AST identity + no-function-scope-reimport guard.
- **Requirements**: FR-012; SC-006. **Depends-on**: none (parallel to IC-01a; both block all extraction). The "biggest land-ability risk" — its own deliverable, own acceptance.
- **Risks**: single-entry sentinel false-green; intra-seam shadowing.

### IC-02 — Engine-adapter (FR-013)
- **Purpose**: Extract `runtime_bridge_engine.py` as the sole home of the `_internal_runtime` privates (`_read_snapshot`/`_load_frozen_template`/`_append_event`/`_write_snapshot` from `.engine`; `plan_next` from `.planner`). **Site list is grep-complete, not a sample** — MUST include `_load_frozen_template` at `:1322` (`_resolve_step_binding`) and `:1375` (`_resolve_step_agent_profile`) in addition to `:1800`/`:1840`/`:2606`/`:3261`/`:3416`; FR-013 requires ALL engine-private access concentrated here, so an arch-guard test asserts no other module imports engine internals. `_advance_run_state_after_composition` (CC23; duplicates the engine's `next_step` branch) is **adapter-owned logic** — its body moves to the adapter (≤15), with a **thin residual delegate** kept at `runtime_bridge._advance_run_state_after_composition` for its heavy patch/attr compat surface (supersedes the old KEEP-IN-PLACE framing).
- **Requirements**: FR-013; FR-004 (`_advance_run_state_after_composition`); FR-006. **Depends-on**: IC-01a, IC-01b.
- **Risks**: engine-boundary correctness; arch guard that no core reaches engine internals.

### IC-03 — Retrospective seam
- **Purpose**: Extract `runtime_bridge_retrospective.py` (self-contained learning-capture cluster). Low-coupling, front-loads confidence.
- **Requirements**: FR-001, FR-006. **Depends-on**: WP-0 (IC-01a + IC-01b).

### IC-04 — Clean I/O ports
- **Purpose**: Extract `runtime_bridge_io.py`: feature-runs index, template/pack discovery, run lifecycle, OC builder, the `gather_artifact_presence` fact-port (feeds FR-009), and the lifted pure `resolve_commit_target` (from `_wrap_with_decision_git_log:226–261`).
- **Requirements**: FR-001, FR-003, FR-006. **Depends-on**: WP-0 (IC-01a + IC-01b). (60 lazy imports make these near-mechanical.)

### IC-05 — Pure cores + guard inversion (FR-009)
- **Purpose**: Extract `runtime_bridge_cores.py` pure leaves — tasks.md parse (`:343–473`, incl. `_extract_wp_heading:343` CC21) and the `ArtifactPresenceSnapshot`+`evaluate_guards(snapshot)` inversion collapsing **all three** guard offenders: `_check_cli_guards:1057`, `_check_composed_action_guard:1515`, **and `_check_requirement_mapping_ready:1122` (CC22)**, which is a CLI-guard sub-helper folded into the same fact-port/pure-core inversion. **Preserve the fail-closed default** (guard-failure list identical incl. order — SC-007).
- **Requirements**: FR-009, FR-004 (`_check_cli_guards`, `_check_composed_action_guard`, `_check_requirement_mapping_ready`, `_extract_wp_heading`), NFR-003; SC-007. **Depends-on**: WP-0 (IC-01a + IC-01b), IC-04 (the fact-port).
- **Risks**: the fail-closed defaults + `tasks` legacy-union are the highest-risk relocation fixtures.

### IC-06 — Decision-builder + decision-materialize (FR-011)
- **Purpose**: `DecisionEnvelope`+`step_or_blocked` core (blocked/query/terminal pure; **step branch port-injected** via a `prompt_exists` predicate — `Decision.__post_init__:129` stats disk, so the step branch cannot be pure; see data-model.md) collapsing the 29 open-coded `Decision(...)` sites + the 4× triad. **This IC owns the decision-materialize offenders: `_map_runtime_decision:3555` (CC33, 10 sites on the answer path) and the 4 `_build_*_query_decision` sites reached from `query_current_state` — collapsing them into the builder is what drives `_map_runtime_decision` and `query_current_state:3199` (CC16) ≤15.** The single highest CC lever.
- **Requirements**: FR-011, FR-004 (`_map_runtime_decision`, `query_current_state`). **Depends-on**: WP-0 (IC-01a + IC-01b).

### IC-07 — Composition dispatch + FR-008 selection seam
- **Purpose**: Extract `runtime_bridge_composition.py`: dispatch + run-state advance + the isolated `_should_dispatch_via_composition` **selection** seam (FR-008 — leave it clean for gates #2535 WP14; import no gates code).
- **Requirements**: FR-008, FR-004. **Depends-on**: IC-02 (engine-adapter), IC-06 (Decision-builder).

### IC-08 — `decide_next` phase-split (FR-010)
- **Purpose**: Rewrite the residual `decide_next_via_runtime:2524` (CC50) as a **bootstrap / dependency-gate / composition-dispatch / decision-materialize** early-return chain over the `DecideNextContext` dataclass; residual ≤15. If reducing to ≤15 in a single WP proves tight, fall back to a documented sub-sequence (phase-by-phase) — but every phase lands ≤15.
- **Requirements**: FR-010, FR-004 (`decide_next_via_runtime`), FR-005. **Depends-on**: IC-05, IC-06, IC-07.

### IC-09 — Identity/coord port (LAST)
- **Purpose**: Extract `runtime_bridge_identity.py` — the hottest fracture line (scars #2091/#1978/#1918/#1814/#2069; correctness path — malformed coord branch → `git worktree` exit-128). Cut last, behind the fattest golden coverage. **Assert NFR-006 here**: re-run the IC-01a before/after timing harness on the full matrix and confirm no measurable `decide_next()` latency regression (or explicitly record the waiver).
- **Requirements**: FR-001, FR-003; NFR-006 (assert). **Depends-on**: IC-01a … IC-08 (last).
- **Risks**: highest-regression seam; identity-trio compat symbols kept-in-place per research §Compat.

## Notes for /tasks

1. **WP-0a + WP-0b are both blocking gates** — no extraction WP starts until BOTH the parity oracle (3 entries, coverage floor asserted) and the compat guard (per-entry sentinel) are green on unmodified source (C-004/SC-008).
2. **Compat preservation is per-WP, not one-shot** — every extraction that moves a patched symbol must add the guarded re-export (and lazy-accessor for sibling-called names) + keep the compat guard green. KEEP-IN-PLACE `_wrap_with_decision_git_log`; `_advance_run_state_after_composition` moves its logic to the engine adapter (IC-02) with a thin residual compat delegate.
3. **Serial spine** — WPs linearize on `runtime_bridge.py`; expect the allocator to collapse to ~1 lane. Do not fabricate parallelism.
4. Each WP re-runs the parity oracle (must stay green) — it is the extraction's acceptance gate, alongside the seam's own unit tests.
5. NFR-005 residual-LOC target is confirmed in research (~35–40%); assert it at IC-08/IC-09.
6. **FR-008** — the composition-dispatch selection core (`_should_dispatch_via_composition`) needs a **both-branch fixture** (dispatch / no-dispatch) in its IC-07 unit tests.
7. **C-007 import-cycle guard** — add a regression test asserting no `decision → runtime_bridge_*` top-level import and that the `decision.py:428` edge stays lazy (no IC owns C-007 otherwise).
8. **`reason`-normalizer meta-test** ships with WP-0a (proves masking collapses path noise but not a semantic `reason`/field delta).
9. **Count drift fixed** — live radon shows **8 functions strictly over 15** (not "9"); `_finalized_task_board_override_step` sits at exactly 15 (= ceiling, not over). There are **3** `# noqa: C901` markers, not two — `decide_next_via_runtime:2524` also carries one (cleared by IC-08). Full FR-004 offender → IC map:

| Offender | CC | Owning IC |
|----------|----|-----------|
| `decide_next_via_runtime:2524` | 50 | IC-08 |
| `_check_composed_action_guard:1515` | 48 | IC-05 |
| `_map_runtime_decision:3555` | 33 | IC-06 |
| `_advance_run_state_after_composition:1800` | 23 | IC-02 |
| `_check_requirement_mapping_ready:1122` | 22 | IC-05 |
| `_extract_wp_heading:343` | 21 | IC-05 |
| `_check_cli_guards:1057` | 19 | IC-05 |
| `query_current_state:3199` | 16 | IC-06 |
