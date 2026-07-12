# Feature Specification: Runtime-Bridge God-Module Decomposition

**Mission**: runtime-bridge-degod-01KX8M1C
**Closes**: #2531 · **Epics**: #1619 (runtime/state overhaul), #2173 (infra-logic separation)
**Siblings** (same shape): #2056 `agent/mission.py`, #2057 `merge.py`, #2059 `doctor.py`, #2464 `agent/workflow.py`

## Summary

`src/runtime/next/runtime_bridge.py` is the single largest module in the repo —
**3,813 LOC** (+49% since the 2026-05 CaaCS audit). Radon shows **9 functions
over the complexity ceiling of 15**, including two `# noqa: C901`-suppressed
guards (`_check_cli_guards:1057` CC≈17, `_check_composed_action_guard:1515`
CC≈45), the ~535-line `decide_next_via_runtime:2524` orchestrator (CC≈32–50),
and — unnamed by the original issue — the decision-materialize pillar
`_map_runtime_decision:3555` (CC≈33).

This mission gives it the **Ports+cores** treatment per #2173: inject the
I/O-bearing seams behind **narrow ports**, extract the parsing/mapping/gating
logic as pure **cores**, concentrate `_internal_runtime` engine access in one
**engine-adapter**, and collapse the pervasive duplication (29 open-coded
`Decision(...)` constructions) into a canonical **Decision-builder** — leaving
`runtime_bridge.py` a thin orchestration surface. It is a **behavior-preserving
structural refactor**: the `spec-kitty next` / `decide_next()` contract does not
change, guarded by a characterization suite whose equality contract this spec
defines explicitly (the load-bearing safety net).

## User Scenarios & Testing

### Primary scenario (maintainer changes composition-dispatch logic)
A maintainer changes how a composed action dispatches. Today that logic is
buried in the ~570-LOC composition cluster and the CC≈45 guard. After this
mission it lives in a focused, named, directly unit-testable core the maintainer
edits and runs in isolation — no full runtime spin-up.

### Behavioral-parity scenario (the load-bearing guarantee)
For every fixture in the enumerated characterization matrix, `decide_next()`
produces the **same decision after normalization** (masking non-deterministic
fields) as before the refactor, run against a frozen repo snapshot with side
effects stubbed/captured. No operator or agent observes any change.

### Pure-core scenario
The tasks.md-parsing, decision-builder, and guard-evaluation cores are imported
and unit-tested in isolation with plain in-memory inputs — no filesystem, no
`meta.json`, no git.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Extract `runtime_bridge.py`'s cohesive seams: **I/O-bearing** seams as narrow **ports** (identity/coordination resolution incl. `meta.json` + coord-branch naming; `feature-runs.json` compat-index; template/pack discovery; run lifecycle) and **decision/parsing/mapping** logic as **cores** — pure where it can be (tasks.md parsing, decision-builder, guard evaluation), port-injected where I/O is intrinsic. | Proposed |
| FR-002 | **The research pass is a hard gate before any extraction.** It MUST emit, in `research.md`: (a) the final seam boundaries + module layout + import DAG; (b) the **parity equality/normalization contract** (which fields are masked/pinned — see NFR-001); (c) the **enumerated characterization fixture matrix per each of the 3 public entry points** with a coverage floor (every `Decision(...)` site + every guard branch reached from its owning entry) — plus a **normalizer meta-test** proving the masking collapses noise but NOT semantic deltas; (d) the **monkeypatch-preservation strategy** per patched private symbol, each **mapped to its reaching entry point** (see FR-012). No extraction PR starts until these exist. | Proposed |
| FR-003 | Ports inject I/O so the cores that CAN be pure take plain data and are unit-testable **without** filesystem/git/`meta.json` access. Purity means **no-I/O + port-injected** — **not** "no `specify_cli` import" (runtime and specify_cli are co-equal production packages; there is no arch gate between them). | Proposed |
| FR-004 | **Every** function currently over the complexity ceiling (the ~8 strictly >15 plus the 3 `# noqa: C901` markers) is reduced to **≤ 15**, with all suppressions **removed** (not relocated). Explicitly incl.: `_check_cli_guards`, `_check_composed_action_guard`, `decide_next_via_runtime`, **`_map_runtime_decision` (CC≈33, `:3555`)**, **`query_current_state` (CC≈16, `:3199`)**, **`_check_requirement_mapping_ready` (CC≈22)** — each mapped to an owning IC at /plan (no orphan offender). | Proposed |
| FR-005 | `runtime_bridge.py` becomes a **thin orchestration/composition surface** composing the extracted ports+cores+adapter. | Proposed |
| FR-006 | **Each extracted seam carries focused tests**: pure cores unit-tested in isolation; ports + engine-adapter contract-tested against stubs. | Proposed |
| FR-007 | A **top-of-file decomposition pointer** referencing #2531 is added, matching the sibling convention (#2056/#2057/#2059/#2464). | Proposed |
| FR-008 | The **composition-dispatch selection** decision — `_should_dispatch_via_composition:1264` (NOT the fs-guard `_check_composed_action_guard`) — is isolated as a clean, testable core, leaving a seam a future consumer can route through **without** this mission coupling to it. (Coordination: unblocks gates mission #2535 WP14; import no gates code here.) | Proposed |
| FR-009 | Collapse the two guards via an **`ArtifactPresenceSnapshot` port + a pure `evaluate_guards(snapshot)` core**: the port gathers the fs/status/bulk-edit/requirement-mapping facts; the pure core decides. This satisfies FR-004 + NFR-003 for the guards by construction. The guard's documented **fail-closed default is preserved** — guard-failure lists are identical before/after (SC-007). | Proposed |
| FR-010 | Split `decide_next_via_runtime` into first-class phases — **bootstrap / dependency-gate / composition-dispatch / decision-materialize** — each returning `Decision | None`, threading shared locals through a frozen `DecideNextContext` dataclass (mirroring #2464's `implement`/`review` precedent). The residual is a linear early-return chain ≤ 15. | Proposed |
| FR-011 | Introduce a canonical **Decision-builder / step-or-blocked materializer** core, collapsing the **29 open-coded `Decision(...)` constructions** (19 blocked) and the `_state_to_action → _build_prompt_or_error → step-or-blocked` triad duplicated at 4 sites. The **blocked branch is pure**; the **step branch is port-injected** — `Decision.__post_init__` (`decision.py:129`) runs `Path(prompt).is_file()`, so the builder takes a **prompt-exists predicate** rather than doing the stat itself (keeps it deterministic + testable; the step branch is port-injected, not filesystem-pure). Single highest CC lever. | Proposed |
| FR-012 | **Preserve the private-symbol test surface.** **~50 distinct private symbols** (research §Compat) are imported and `monkeypatch.setattr(runtime_bridge, <name>)`-patched by tests today; a naive top-level re-import defeats that **silently** (false-green — an intra-seam call resolves via the seam's own global, so the patch no-ops and the test passes by coincidence). Each relocated-but-still-patched symbol MUST remain reachable via `runtime_bridge.<name>` (re-export **and**, for names a sibling module calls, the `_wf`-style lazy accessor; `__all__` governs only `import *` and does NOT preserve the private surface). Verified by a two-part guard test (behavioral sentinel + static AST anti-shadowing check). | Proposed |
| FR-013 | Concentrate **all** `_internal_runtime.engine` **private-symbol** access in **one engine-adapter seam** — `_read_snapshot`/`_append_event`/`_write_snapshot`/`plan_next` **and** `_load_frozen_template` (grep-complete: incl. `:1322`/`:1375`, not only the decide_next sites). No "core" reaches engine internals; `_advance_run_state_after_composition` (CC≈23, duplicates the engine's `next_step` branch) is an adapter helper reduced ≤15 (reconcile the residual-vs-adapter placement here — adapter-owned logic, thin residual delegate). | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Behavioral parity across **all three public entry points** — `decide_next_via_runtime`, `query_current_state`, `answer_decision_via_runtime` (only 15 of the 29 `Decision(...)` sites are in `decide_next`; the other 14 are query/answer-only) — verified by a characterization suite with an explicit equality contract. | Each frozen fixture snapshot runs against a fresh copy; the returned `Decision` is compared after **masking** non-deterministic fields (`timestamp` `:2542`, `run_id`/`decision_id` ULIDs) and **path-normalizing** `workspace_path`/`prompt_file`/`reason`/`origin.mission_path` to **that run's own repo_root**. Side effects (run advance, sync-event emit, coord-branch decision-event commit, retrospective) are **captured and asserted** (not merely stubbed) so a change to *what* is emitted/committed is caught. Post-normalization decisions + captured side-effects identical before/after; all `runtime/next` tests green. | Proposed |
| NFR-002 | Complexity — every function in `runtime_bridge.py` and the new seam modules is ≤ 15. | `ruff --select C901` reports **zero** offenders; **zero** `# noqa: C901` remain (the 9 current offenders, named in FR-004, all cleared). | Proposed |
| NFR-003 | Pure-core testability. | Each core designated pure (tasks.md parse, decision-builder, `evaluate_guards`) has ≥1 direct unit test with in-memory inputs and **no I/O**. | Proposed |
| NFR-004 | No new public surface. | No new CLI command/flag, no new public API; internal seam modules only. | Proposed |
| NFR-005 | Size reduction of the god-module. | `runtime_bridge.py` drops to a thin surface; the concrete target is **set by the FR-002 research** (sibling #2464 landed ~40% of the original as the residual — guidance, not a frozen constant). | Proposed |
| NFR-006 | Performance parity on the hot path. | `decide_next()` shows **no measurable latency regression** from the added indirection (a before/after timing check on the characterization matrix stays within noise). | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **Behavior-preserving** — pure structural refactor; decision logic is relocated, never changed. | Active |
| C-002 | **Ports+cores per #2173** — inject I/O as ports, keep decision/parsing/mapping cores pure where intrinsic-I/O allows. Purity = **no-I/O + port-injected**, not "no-`specify_cli`-import". | Active |
| C-003 | Follow the sibling convention (#2057 `merge.py`, #2464 `workflow.py`) — **flat responsibility-named modules** (not a `ports/`|`cores/` subdir split) + top-of-file decomposition pointer; preserve the `runtime.next.runtime_bridge` import path (~13 prod + ~40 test sites). | Active |
| C-004 | **Characterization-first (extract-then-inject)** — the golden `decide_next()` characterization lock (with the NFR-001 normalization contract) lands as the FIRST work package, before any extraction; no C901 function is edited in place without it green. | Active |
| C-005 | Do **not** adopt or depend on the gates mission (#2535) `resolve_gates` seam — unlanded. FR-008 only leaves the selection a clean seam. | Active |
| C-006 | **Sequencing (light)** — nominally Wave-4-ish, but the named siblings do NOT restructure this file: the trio degod (#2545) rewrites `cli/commands/agent/workflow.py` (lists #2531 out of scope); `orchestrator_api` is a separate directory. The shared `runtime/next/` surface (`_internal_runtime`, `decision.py`) is **consumed, not restructured**, here — so exposure is a few ambient point-fixes to rebase, not a competing restructure. Coordinate, don't block. | Active |
| C-007 | **No new import cycle** — `decision.py:428` already lazily imports the orchestrator while `runtime_bridge:36` imports `decision` at top level; keep that edge lazy and add no `decision → runtime_bridge_*` top-level import. | Active |

## Key Entities (starting hypothesis — FR-002 research confirms)

- **Ports (I/O)**: identity/coordination resolution (`meta.json` + coord-branch naming — hottest fracture line, cut LAST); `feature-runs.json` compat-index (textbook narrow port); template/pack discovery; run lifecycle.
- **Engine-adapter (FR-013)**: the single home for `_internal_runtime.engine` private access.
- **Pure cores**: tasks.md parsing (`:343–473`, the flagship pure leaf); **Decision-builder / step-or-blocked materializer** (FR-011); **`evaluate_guards(snapshot)`** (FR-009).
- **Port-injected cores (impure-intrinsic)**: `_map_runtime_decision` step-branches (prompt/action I/O via `decision.py`); operational-context builder.
- **Thin residual**: `decide_next_via_runtime` as a 4-phase early-return chain over `DecideNextContext` (FR-010).

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | `runtime_bridge.py` is reduced to a thin orchestration surface (per the FR-002 research target). |
| SC-002 | **Zero** `# noqa: C901` remain; `_check_cli_guards`, `_check_composed_action_guard`, `decide_next_via_runtime`, `_map_runtime_decision`, and every other current >15 function are ≤ 15. |
| SC-003 | Across the per-entry fixture matrix, **all three public entry points'** decisions AND their captured side-effects are **identical after the NFR-001 normalization**, run against frozen snapshots. |
| SC-004 | Every designated pure core passes a direct unit test in isolation (no I/O). |
| SC-005 | The decomposition pointer is present and the seam modules follow the flat sibling-convention layout; the `runtime.next.runtime_bridge` import path is preserved. |
| SC-006 | A guard test proves `monkeypatch.setattr(runtime_bridge, <each patched private symbol>)` still reaches the moved seam **driven through that symbol's reaching entry point** (decide_next / query / answer — a symbol reached only via query/answer must be driven there, else the sentinel silently never fires) — no false-green (FR-012). |
| SC-007 | For a fixture exercising each guard branch, the guard-failure list is **identical** before/after the `evaluate_guards` extraction (FR-009 — the fail-closed default is preserved). |
| SC-008 | The FR-002 research artifact exists and contains the normalization contract, enumerated fixture matrix, monkeypatch strategy, and final seam boundaries **before** the first extraction WP is authored. |

## Assumptions

- The FR-002 research pass fixes seam boundaries, the parity normalization contract, the fixture matrix, and the monkeypatch strategy — these are gates, not nice-to-haves.
- Sibling #2464 (`workflow.py` → 1482 + `workflow_cores.py` 479 + `workflow_executor.py` 1856) is the layout + `DecideNextContext` + lazy-accessor template.
- 60 function-local lazy imports already isolate the I/O seams at module load, so ports extract near-mechanically.

## Out of Scope

- Any **behavioral/functional change** to decision logic — pure structural refactor only.
- Adopting the gates-mission (#2535) `resolve_gates` seam — that inversion is gates WP14, after this mission.
- The broader runtime/state overhaul beyond `runtime_bridge.py` (root epic #1619) and the `orchestrator_api` degod (its own Wave-3 slice).
