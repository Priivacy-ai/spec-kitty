# Implementation Plan: MissionResolver Port (2173 Phase 2)

**Branch**: `feat/mission-resolver-port-2173` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/mission-resolver-port-01KX1C05/spec.md`

> **Post-plan squad revision (2026-07-08).** A 3-lens brownfield squad (researcher-robbie,
> architect-alphonso, paula-patterns) reviewed this plan and forced four corrections, now applied
> (operator ruling: **full trunk**): (1) the port becomes the **single walk trunk** — all free-function
> callers + the canonicalizer reach it, not a 7th parallel path; (2) the injection seam moves to the
> **callers** of `_resolve_mission_slug` and threads an optional `resolver` param through the
> canonicalizer chain, with the Protocol defined in `mission_runtime` so **no new layer-ledger edge** is
> created; (3) the `legacy-<slug>` bootstrap sentinel is an explicit carve-out, not routed through the
> fail-closed port; (4) the Clock / #2139 / walker censuses are expanded to their true size. Squad detail
> in the `tracer-*.md` files.

## Summary

Make one `MissionResolver` the **single sanctioned `kitty-specs/` walk** and inject it end-to-end so the
builder's identity-resolution path is FS-free-testable via a `FakeMissionResolver` — the concrete `#1619`
unblock. The seam is threaded from the shell callers through the canonicalizer chain down to the one
walk; the free `resolve_mission` gains an optional `resolver` param so no read path bypasses it. Bind the
result with an ADR + a new AST call-site gate (seeded with the full ~16-walker census). Finish three
same-surface strangler residuals as sibling slices: the `#2139` `target_branch` reconcile (all
non-migration readers, not just 4), the Clock consolidation (with the extra copies + the S1192 stamp
cluster named), and InstalledVersion routing + the `#2447` doctrine-phantom fix.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: standard library only (`pathlib`, `dataclasses`, `typing.Protocol`); existing
first-party packages `specify_cli` and `mission_runtime`. No new runtime dependencies.
**Storage**: Filesystem — `kitty-specs/<mission>/meta.json` reads; the FS coupling the port abstracts.
**Testing**: `pytest`. A unit test drives the builder's **identity-resolution leg** with
`FakeMissionResolver` at **zero filesystem** (NFR-001, scoped precisely — see below); the full
`tests/architectural/` ratchet (NFR-002); a byte-identical timestamp characterization test (NFR-004);
structured-error tests for cold-miss/ambiguity (NFR-005). ATDD-first: the FS-free identity test is red
before the seam exists.
**Target Platform**: Linux / macOS developer + CI (the Spec Kitty CLI).
**Project Type**: single (Python CLI + library).
**Performance Goals**: none — the walk ships **uncached** by design (C-005); wall-clock unchanged.
**Constraints**: `ruff` + `mypy` zero new issues; complexity ≤ 15 on touched/extracted functions; no new
deps; ports on the shell never on the frozen context; no process-level cache; fail-closed-loud with no
`is None`/`or slug` branch (ADR `2026-07-01-1`); **no new `mission_runtime → specify_cli` layer-ledger
edge** (the Protocol lives in `mission_runtime`).
**Scale/Scope** (census-verified by the squad): one Protocol (`mission_runtime`) + 2 adapters
(`specify_cli.context`); thread `resolver` through the canonicalizer chain + **8 free-function caller
sites**; `#2139` = **≥9 non-migration readers** (route or explicitly triage); Clock = **14 isoformat
copies** (12 in `specify_cli` + 2 cross-package, triaged) → one, **preserve** 2 stamp + 2 datetime; plus
an ADJACENT S1192 stamp-literal cluster; 1 migration version read; ~16-walker AST-gate allowlist; 1 doc
row + 1 path-resolution guard; 1 ADR; 1 new gate.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter loaded (`software-dev-default`, DIR-001…DIR-013).

| Principle / Directive | Disposition |
|---|---|
| **Single canonical authority** | ✅ **Honestly achieved by the trunk scope** — the port is the sole walk; the free `resolve_mission` becomes an injectable delegate, all 8 callers + the canonicalizer route through it, and the AST gate + a free-function-caller audit bind it. |
| **Unification, not parity** | ✅ Operator ruling: full trunk, not a scoped 7th path. No split-brain left open. |
| **Architectural alignment / adopt-don't-duplicate** | ✅ Reuses `PlacementSeam`, the canonicalizer, `resolve_mid8`, the `x or Default()` DI idiom; **no new layer-ledger edge** (Protocol in `mission_runtime`). |
| **DDD + tiered rigour** | ✅ Core seam full rigour + FS-free identity test; glue (doc tail) proportionate. |
| **ATDD-first / red-first** | ✅ FR-004/NFR-001 identity test authored red first through the pre-existing builder entry point. |
| **No legacy resolver paths** (ADR `2026-07-01-1`) | ✅ Cold-miss fail-closed → `backfill-identity`; the `legacy-<slug>` bootstrap sentinel is a documented pre-identity carve-out, NOT a resolution fallback (D-07). |
| **Blind-primitive non-fold rule** (ADR `2026-06-26-1`) | ✅ Resolver threads *in front of* `primary_feature_dir_for_mission`; canonicalization not folded into the primitive (C-007). |
| **Campsite cleaning / Sonar** | ✅ Per-touched-file Sonar census at `/tasks`; SAFE items folded (see IC-04/IC-06), ADJACENT tracked. |

**No charter violations.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-resolver-port-01KX1C05/
├── plan.md · research.md · data-model.md · quickstart.md · contracts/
└── tracer-approach.md · tracer-design-decisions.md · tracer-tooling-friction.md
```

### Source Code (repository root)

```
src/mission_runtime/
├── (new) mission_resolver_port.py  # MissionResolver Protocol lives HERE (shell owns its port →
│                                   #   no new mission_runtime→specify_cli ledger edge)
└── resolution.py                   # SHELL: seam at CALLERS of _resolve_mission_slug
                                    #   (resolve_action_context :1384, mission_context_for,
                                    #    resolve_placement_only ~:866); thread `resolver` down;
                                    #   _resolve_mission_id :913 keeps its legacy-<slug> carve-out (D-07)

src/specify_cli/context/mission_resolver.py
                                    # FsMissionResolver + FakeMissionResolver (wrap _build_index);
                                    #   free resolve_mission gains optional `resolver=None` param
src/specify_cli/missions/_read_path_resolver.py
                                    # canonicalizer chain (:503 calls resolve_mission) threads `resolver`

src/specify_cli/                    # free-function caller audit (8): audit/engine.py:87,
│   selector_resolution.py:218, retrospect.py:124, agent_retrospect.py:72, mission_type.py:1051,
│   runtime/show_origin.py:231, acceptance/__init__.py:910, _read_path_resolver.py:503
├── (adopt) doctrine_synthesizer/apply.py:602/788, core/vcs/detection.py:169
├── #2139: context/resolver.py:82/236/269, retrospective/generator.py:1263, mission_branch_context.py:63,
│         _resolve_planning_branch.py:80, retrospective/reader.py:303, writer.py:398,
│         acceptance/__init__.py:1075/1696, tasks_parsing_validation.py:751 (≥9; triage dataclass-hydration KeyError reads)
├── Clock: 12 specify_cli isoformat copies + glossary/events.py:215 & runtime/.../retrospective_terminus.py:63
│         (cross-package → triage OUT-with-rationale or shared home); preserve task_utils/support.py:101 +
│         mission_parsing.py:257 (stamp), decisions/emit.py:64 + service.py:86 (datetime)
└── InstalledVersion: upgrade/migrations/m_2_1_4_enforce_command_file_state.py:55 → _CliStatusLike

docs/adr/3.x/2026-07-08-*-mission-resolver-port.md          # NEW ADR (FR-006)
tests/architectural/test_mission_resolver_walker_gate.py    # NEW AST gate, ~16-entry allowlist (FR-007)
src/doctrine/skills/spec-kitty-git-workflow/references/git-operations-matrix.md   # #2447
```

**Structure Decision**: The `MissionResolver` **Protocol lives in `mission_runtime`** (a new small
module) so the shell references only a local type and **no new `mission_runtime → specify_cli.context`
ledger edge** is created (squad-confirmed blocker: `test_layer_rules.py` `_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI`
omits `context`). The **adapters live in `specify_cli.context.mission_resolver`** beside the walk they
wrap and import the Protocol via the allowed downward `specify_cli → mission_runtime` (package-root)
direction. The default `FsMissionResolver` is constructed at the CLI/`specify_cli` entry boundary and
threaded down; `mission_runtime` shell functions accept a Protocol-typed `resolver` and pass it into the
already-ledgered `specify_cli.missions` canonicalizer. **Acceptance criterion: `test_layer_rules.py`
stays green with zero new ledger edge** — if implementation finds this infeasible, the fallback (add
`"context"` to the ledger with a rationale comment) requires an explicit operator note, since it grows a
ledger #2173 exists to drain.

**DDD rename (IC-00, operator-directed):** the frozen context class is `ExecutionContext`
(`mission_runtime/context.py:262`) but the ubiquitous term is `MissionExecutionContext` — it is already
the name in the class docstring (`context.py:11`), a parity-test assertion (`test_execution_context_parity.py:1545`),
and the **#1619 epic title**. It also **collides** with an unrelated `class ExecutionContext(StrEnum)`
(`core/context_validation.py:41`). This mission renames `mission_runtime.context.ExecutionContext →
MissionExecutionContext` (code follows ubiquitous language, DDD). The colliding **StrEnum is NOT renamed**
here (different type; flagged ADJACENT). FR-004's test targets the renamed class.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.* (`resolution.py` is a 1465-LOC god-module but
the injection is complexity-safe; extraction belongs to the #2173 decomposition track — OUT of scope.)

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-00 — DDD rename `ExecutionContext → MissionExecutionContext` (first; unblocks clean downstream naming)

- **Purpose**: Align the frozen composite's code name with the ubiquitous language (#1619 "mission execution context") and remove the collision with `core/context_validation.py::ExecutionContext(StrEnum)`.
- **Requirements**: FR-012.
- **Surfaces**: `mission_runtime/context.py:262` (class), the `ActionContext` alias (`:349`), the ~12 `from mission_runtime.context import ExecutionContext` sites + their usages (20 files total), and ADR prose (`2026-06-22-1`, `2026-06-03-1`). **Scoped occurrence classification** (do at `/tasks`): code_symbols = the composite class only; import_paths = the 12 import sites; tests_fixtures = test refs; user_facing_strings/docs = docstrings + ADR prose. **Exclusion (hard):** `core/context_validation.py::ExecutionContext(StrEnum)` — a different type, untouched.
- **Sequencing/depends-on**: FIRST — so IC-01/IC-02 use the corrected name. Land as its own WP.
- **Risks**: the StrEnum collision is the whack-a-symbol trap — rename must target only the `mission_runtime.context` composite; verify with the full `tests/architectural/` + arch surface gate (`test_mission_runtime_surface.py`, `test_execution_context_parity.py`) after. Bulk-edit-shaped: apply the occurrence-classification discipline even though the mission is not wholesale `change_mode: bulk_edit`.

### IC-01 — Resolver port + walk trunk (Protocol, adapters, free-fn delegate)

- **Purpose**: Define the Protocol (`mission_runtime`) + `FsMissionResolver`/`FakeMissionResolver` (`specify_cli.context`); make the free `resolve_mission` accept an optional `resolver` so the walk is injectable at its single site.
- **Requirements**: FR-001, FR-005; NFR-005.
- **Surfaces**: `mission_runtime/mission_resolver_port.py` (new), `specify_cli/context/mission_resolver.py`.
- **Depends-on**: none (foundational).
- **Risks**: fail-closed-loud (FR-005); no cache (C-005); zero new ledger edge.

### IC-02 — Thread the seam through the canonicalizer chain + shell callers (the trunk)

- **Purpose**: Thread `resolver` from the shell callers (`resolve_action_context`, `mission_context_for`, `resolve_placement_only`) through `_read_path_resolver` down to `resolve_mission`, so every read path uses the injected resolver — preserving canonicalization + topology-aware (coord/primary) reads.
- **Requirements**: FR-002, FR-003, FR-004; NFR-001.
- **Surfaces**: `mission_runtime/resolution.py` (:303/:913/:1036/:1384, `resolve_placement_only`), `missions/_read_path_resolver.py:503`, + adopt `doctrine_synthesizer/apply.py:602/788`, `core/vcs/detection.py:169`, + audit the **8 free-fn callers** (route or document each).
- **Depends-on**: IC-01.
- **Risks**: injection order (`_resolve_mission_slug` runs before `_assemble_core_fragments` — seam at callers, not inside the assembler); must NOT touch `build_execution_context` (pure) or the frozen context (C-006); must preserve the canonicalizer/topology read or regress split-brain fixes. **NFR-001 scoped precisely: the test proves the *identity-resolution leg* is FS-free via the Fake — the assembler's other FS legs (`get_main_repo_root`, `_resolve_coordination_branch`, `_resolve_status_surface_dir`, topology) are separate ports deferred to later #2173 phases, stated as such.**

### IC-03 — Legacy-sentinel reconciliation (D-07)

- **Purpose**: Keep `_resolve_mission_id`'s `legacy-<slug>` bootstrap/scaffold path as an explicit, documented pre-identity carve-out that does NOT flow through the fail-closed `resolve()`; add a regression test pinning the bootstrap behavior.
- **Requirements**: FR-005 (carve-out clause).
- **Surfaces**: `mission_runtime/resolution.py:944`.
- **Depends-on**: IC-02.
- **Risks**: silently routing bootstrap through fail-closed `resolve()` breaks mission-create/scaffold — the reconciliation is load-bearing.

### IC-04 — ADR + AST call-site gate (bind by construction) + Sonar seed

- **Purpose**: ADR recording the trunk decision + the ledger-dodge; new gate naming `FsMissionResolver` the sole sanctioned walker, allowlist **seeded with the full ~16-walker census** (incl. the anti-fold trio + migrations) so it doesn't red on introduction; a free-function-caller audit note so `resolve_mission` calls can't silently multiply.
- **Requirements**: FR-006, FR-007; NFR-002.
- **Surfaces**: `docs/adr/3.x/…`, `tests/architectural/test_mission_resolver_walker_gate.py`.
- **Depends-on**: IC-01/IC-02.
- **Risks**: allowlist token-keyed not line-numbered (F5); gate derives scope from `src/` (no blind spot); discriminate enumeration-of-all-missions vs single-dir access.

### IC-05 — `#2139` target_branch reconcile (all readers)

- **Purpose**: Route **all ≥9 non-migration** `target_branch` readers onto `read_target_branch_from_meta`; delete divergent `"main"`/`""`/`None` defaults; explicitly triage the dataclass-hydration `KeyError` reads (`context/models.py:83`, `lanes/models.py:200`) as intentional/OUT with rationale.
- **Requirements**: FR-008.
- **Surfaces**: the 4 named + `retrospective/reader.py:303`, `writer.py:398`, `acceptance/__init__.py:1075/1696`, `tasks_parsing_validation.py:751`.
- **Depends-on**: independent.
- **Risks**: whack-a-field — route all or triage explicitly, never a partial 4-of-9.

### IC-06 — Clock consolidation (+ Sonar stamp campsite) & InstalledVersion + `#2447`

- **Purpose**: Collapse the 12 `specify_cli` isoformat copies → one; **triage the 2 cross-package copies** (`glossary/events.py:215`, `runtime/.../retrospective_terminus.py:63`) — shared home or OUT-with-rationale, never silently stop at 12; preserve the 2 stamp + 2 datetime helpers (NFR-004). **SAFE campsite**: fix `mission_parsing.py:259`'s hardcoded `"%Y-%m-%dT%H:%M:%SZ"` to the shared constant. **ADJACENT (note, don't fold)**: the 4 redundant `TIMESTAMP_FORMAT`/`UTC_SECOND_TIMESTAMP_FORMAT` defs + 18-site S1192 literal. Route the migration version read through `_CliStatusLike`; repoint/remove the `#2447` phantom row + add the path-resolution guard.
- **Requirements**: FR-009, FR-010, FR-011; NFR-004.
- **Depends-on**: independent.
- **Risks**: folding stamp/datetime callers changes on-disk timestamps (NFR-004); doctrine is shipped — run terminology guard + `tests/architectural/` locally pre-push (F7).
