# Implementation Plan: Tasks Degod Wave 2: Render Seam + Relocation

**Branch**: `degod-follow-ups` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)
**Input**: Mission specification from `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/spec.md` (rev 3 — post-spec squad + pre-plan related-issues squad folded)

## Summary

Pure-parity refactor finishing the tasks.py degod (#2305, epic #2173): Stream B relocates
the five command families (~orchestrator + glue + State + port factory each), the ~30
cross-family shared helpers, and the port-seam adapter classes out of the 4569-LOC
`tasks.py` into focused sibling modules using the proven `mission.py` seam-bridge idiom
(lazy `_tasks.<attr>` routing preserves the ~370 patch-seam call sites' interception);
Stream A collapses the `_StatusRender` override into a constructor-parameterized
`RealRender` and routes the 12 compact inline `print(json.dumps(...))` sites through the
Render port — guarded by a NEW byte-freeze suite committed BEFORE any routing change.
Two net-new architectural gates (AST 0-inline-dumps, whole-file LOC ceiling
`min(achieved, 1400)`) close the class by construction. Domain-matched boyscout: marker
census artifact + #2034 refresh + the #2306 inventory off-by-one fold.

## Technical Context

**Language/Version**: Python 3.11+ (charter-mandated; existing codebase)
**Primary Dependencies**: typer (CLI framework, `uv.lock`-pinned — golden `--help` fixtures are version-coupled), rich (console), stdlib `json`/`ast`; NO new dependencies
**Storage**: N/A (CLI source refactor; mission artifacts on the coordination branch)
**Testing**: pytest via in-process `typer.testing.CliRunner` (fast shard); the two contract harnesses (43 cases) + NEW byte-freeze suite (13 cases) + NEW gate self-mutation tests; `mypy --strict` on changed src+test files together; `ruff`; targeted per-WP surfaces per NFR-005 (coord harness mandatory for commit-router WPs)
**Target Platform**: cross-platform CLI (Linux/macOS/Windows 10+)
**Project Type**: single (src/specify_cli package)
**Performance Goals**: CLI operations < 2s (charter); relocations are import-time-neutral (lazy in-function imports, no new module-level work)
**Constraints**: byte-identical behavior at every commit (NFR-001); patch-seam interception preserved (NFR-002, ~370 call sites / ~40 symbols); #2300 divergence untouched (C-001, pinned by coord harness T004/T005); coord-topology mission (planning artifacts write to the coordination branch)
**Scale/Scope**: tasks.py 4569 → ≤1400 LOC (~3150 LOC relocated across 7 new sibling modules); 13 JSON emission sites; 2 new arch gates; 8–10 WPs (squad-sized)

## Charter Check

*GATE: evaluated against `.kittify/charter/charter.md` v1.3.0.*

| Charter rule | Status | Evidence |
|---|---|---|
| Single canonical authority (Principle 1, DIRECTIVE_044) | PASS | Render seam ends the 13-site emission split-brain; ONE production adapter (`RealRender`, indent-parameterized) — no `IndentedRender` second adapter (would violate C-004); shim disposition FR-008 reconciles rather than duplicates |
| Architectural alignment (DIRECTIVE_001) | PASS | Sibling-module layout copies the accepted `mission.py` degod template (verified live: `app.command(name=...)(fn)` registration + lazy `_mission.<attr>` seam routing, zero module-level back-imports) |
| ATDD-first (C-011, parity form / spec C-003) | PASS | Byte-freeze suite committed BEFORE the render routing change; every gate proven red on synthetic violations before it counts (DIRECTIVE_043 non-vacuity) |
| Adversarial squad cadence (Standing Order 1) | DONE for spec + pre-plan point-cuts; post-tasks squad scheduled after `/spec-kitty.tasks` |
| Campsite cleaning (Standing Order 2) | PASS | 3 domain-matched folds only (#2306 + 2 inline mypy); all #1931/#2071 children verified out-of-domain |
| Tracer files (Standing Order 3) | PASS | Seeded; squad decisions appended |
| Test remediation discipline (Standing Order 4, DIRECTIVE_041) | PASS | Ratchet re-point ≠ fixture adjust codified (FR-012 / NFR-001(e)); revert-and-redo on any parity delta |
| Arch gate discipline (Standing Order 5, DIRECTIVE_043) | PASS | Both new gates ship with self-mutation proofs; FR-009 forbids baseline widening |
| Git/workflow (Standing Order 7, DIRECTIVE_045) | PASS | Mission merges to local `degod-follow-ups`; PR to upstream `main` after; operator merges |
| Testing Requirements (targeted surfaces) | PASS | NFR-005 declares per-WP targeted surfaces; full suite reserved for post-merge mission validation |
| Terminology canon | PASS | C-005 + pre-push guard |

**No violations — Complexity Tracking not required.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/tasks-py-degod-wave2-01KWH9EQ/
├── plan.md                        # This file
├── research.md                    # Phase 0 output
├── data-model.md                  # Phase 1 output (module layout + move-sets + seam inventory)
├── quickstart.md                  # Phase 1 output (guard-running playbook)
├── contracts/
│   ├── parity-contract.md         # byte-freeze + harness + ratchet re-point rules
│   └── gate-contracts.md          # AST dumps gate + LOC ceiling gate specs
├── post-spec-squad-findings.md    # Squad records (post-spec + pre-plan)
├── issue-matrix.md                # Tracker rows
└── tasks.md                       # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── agent_tasks_ports.py                     # MODIFIED: RealRender gains constructor indent param; _StatusRender absorbed
└── cli/commands/agent/
    ├── tasks.py                             # SHRINKS 4569 → ≤1400: @app.command wrappers, 4 small bodies, seam-bridge/re-export surface
    ├── tasks_move_task.py                   # NEW: _do_move_task + 23 _mt_* + _MoveTaskState + _default_move_task_ports
    ├── tasks_map_requirements.py            # NEW: _do_map_requirements + 11 _mr_* + _MapReqState + _default_map_requirements_ports
    ├── tasks_status_cmd.py                  # NEW: _do_status + 14 _st_* + _StatusState + _default_status_ports
    ├── tasks_mark_status.py                 # NEW: _do_mark_status + 9 _ms_* + _MarkStatusState + _default_mark_status_ports
    ├── tasks_finalize.py                    # NEW: _do_finalize_tasks + 4 _ft_* + _FinalizeState + _default_finalize_ports
    ├── tasks_shared.py                      # NEW: ~30 cross-family helpers (_output_result/_output_error, _find_mission_slug, …)
    ├── tasks_command_adapters.py            # NEW: _MoveTaskCoordRouter, _MapReqCoordRouter, _MarkStatusCoordRouter
    ├── tasks_ports.py                       # FR-008 disposition (7-line shim: absorb or retain w/ rationale)
    ├── tasks_transition_core.py             # UNCHANGED (Wave 1 pure core)
    ├── tasks_status_view.py                 # UNCHANGED
    └── tasks_mapping_core.py                # UNCHANGED

tests/
├── architectural/
│   └── test_tasks_command_surface.py        # NEW: AST 0-inline-dumps gate + LOC ceiling + self-mutation proofs
├── specify_cli/cli/commands/agent/
│   ├── test_tasks_cli_contract.py           # UNCHANGED (27 cases)
│   ├── test_tasks_cli_contract_coord.py     # MODIFIED per WP: ratchet re-points ONLY (FR-012)
│   ├── test_tasks_json_bytes.py             # NEW: byte-freeze suite (13 cases, fixture-backed)
│   └── fixtures/tasks_cli/json/byte_contracts.json  # NEW: exact expected stdout per emission site
└── (census artifact per FR-009: kitty-specs/…/marker-census.md or tests/-side doc — tasks phase decides)
```

**Structure Decision**: single-project layout; all new command modules are siblings of
`tasks.py` under `src/specify_cli/cli/commands/agent/` (the `mission.py` template
precedent — verified live in research R1). `tasks_status_cmd.py` avoids colliding with
the existing `tasks_status_view.py` core. No `__all__` on new siblings (template
precedent; charter `__all__` MUST binds `src/charter/`+`src/kernel/` only).

## Key Design Decisions (from Phase 0 research — full detail in research.md)

1. **Render indent = constructor parameter on `RealRender`** (`RealRender(console=...,
   indent=2)`), NOT a Protocol signature change and NOT a second adapter class. Keeps the
   `Render` Protocol frozen, keeps ONE production adapter (C-004), deletes `_StatusRender`.
   `RealRender.json_envelope` already emits `json.dumps(payload)` with default separators —
   byte-identical to all 12 compact sites (verified R2).
2. **Seam bridge**: relocated code uses lazy in-function `from specify_cli.cli.commands.agent
   import tasks as _tasks` + `_tasks.<attr>(...)` for every symbol that tests patch on the
   `tasks` module — the exact live idiom of the template (R1). Symbols that are themselves
   relocated AND patched get their patches re-pointed in the same WP.
3. **LOC gate is a plain per-file ceiling** (read file, `len(splitlines()) <= ceiling`) —
   `composite_key` (CT1 #2072) is N/A for a whole-file scalar (no line-keyed allowlist);
   rationale recorded so the carry-forward isn't cargo-culted. Ratchets DOWN as relocation
   lands (start 4569, drop per WP, final `min(achieved, 1400)`).
4. **AST dumps gate** follows `test_protection_resolver_call_sites.py` (walk `ast.Call`
   nodes over the directory glob) + `test_commit_target_kind_guard.py`'s theater-test
   non-vacuity pattern — one synthetic-offender proof per evasion form (attr call,
   from-import, module alias, rebinding).
5. **Byte-freeze suite** reuses the existing `CliRunner` harness machinery with a NEW
   sibling fixture (`byte_contracts.json`) asserting `result.stdout == expected` exactly;
   never `len()==N` counts (CT5 #2076). Site→subcommand map is in research.md R5.
6. **Emission-site correction** (research R2/R5): the status `indent=2` "site" is the
   `_StatusRender.json_envelope` method (tasks.py:1222–1235) invoked by the print at
   tasks.py:4117 — status ALREADY routes through `ports.render`; FR-006 is purely
   collapse-the-subclass. The 12 compact sites are direct `print(json.dumps(...))` calls.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these
> into executable WPs — one concern may become multiple WPs; small concerns may merge.

### IC-01 — Byte-freeze contract suite (parity floor)

- **Purpose**: Pin the exact stdout bytes of all 13 JSON emission sites BEFORE anything moves — the byte-level contract the shape-checked harness legs never provided.
- **Relevant requirements**: FR-005 (pre-step), NFR-001(c), C-003, SC-003.
- **Affected surfaces**: NEW `tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py` + `fixtures/tasks_cli/json/byte_contracts.json`. Zero production changes.
- **Sequencing/depends-on**: none — FIRST concern; everything else is guarded by it.
- **Risks**: fixture realism (use production-shaped mission fixtures, not placeholders); venv must match `uv.lock` typer pin before freezing.

### IC-02 — Shared-helpers module + seam bridge (foundation)

- **Purpose**: Create `tasks_shared.py` housing the ~30 cross-family helpers with the lazy `_tasks.<attr>` seam bridge, establishing the interception-preserving pattern every family move copies.
- **Relevant requirements**: FR-003, FR-002, NFR-002; campsite folds (mypy attr-defined + redundant-cast when `test_tasks.py` is touched).
- **Affected surfaces**: NEW `tasks_shared.py`; `tasks.py` (re-export + delegation); the ~40-symbol seam inventory (data-model.md).
- **Sequencing/depends-on**: IC-01.
- **Risks**: highest-traffic patch symbols live here (`_find_mission_slug` ×66, `_ensure_target_branch_checked_out` ×50); the per-symbol keep-vs-re-point decision table (data-model.md) is the checklist; interception check per WP.

### IC-03 — Adapters module (cycle-break foundation)

- **Purpose**: Move the three coord-router adapter classes to `tasks_command_adapters.py` so family modules can import them without ports↔commands cycles.
- **Relevant requirements**: FR-004, C-004.
- **Affected surfaces**: NEW `tasks_command_adapters.py`; `tasks.py` re-exports; `agent_tasks_ports.py` untouched.
- **Sequencing/depends-on**: IC-01. (`_StatusRender` is NOT moved — IC-04 deletes it.)
- **Risks**: adapter symbols are patched in coord tests — seam checklist applies.

### IC-04 — Render seam unification

- **Purpose**: `RealRender` gains a constructor `indent` param; `_StatusRender` deleted; the 12 compact `print(json.dumps(...))` sites route through `ports.render.json_envelope` (default-param `render or RealRender()` for the port-less small bodies).
- **Relevant requirements**: FR-005, FR-006, C-004; byte-freeze green throughout.
- **Affected surfaces**: `src/specify_cli/agent_tasks_ports.py`; emission call sites across `tasks.py` (pre-relocation) or the family/shared modules (post-relocation — tasks phase fixes ordering); `_default_status_ports`.
- **Sequencing/depends-on**: IC-01; MUST land before or with the status-family move (the `_StatusRender` ordering edge).
- **Risks**: `_output_result`/`_output_error` (shared, 56 call sites) are the main routing seam — coordinate with IC-02 ownership.

### IC-05 — Family relocations (five moves)

- **Purpose**: Move each command family (orchestrator + glue + State + port factory) to its sibling module; `tasks.py` wrappers become thin delegates.
- **Relevant requirements**: FR-001, FR-002, FR-012, NFR-001/002; #2306 fold rides the move_task family move (inventory.md row update).
- **Affected surfaces**: NEW `tasks_move_task.py` / `tasks_map_requirements.py` / `tasks_status_cmd.py` / `tasks_mark_status.py` / `tasks_finalize.py`; `tasks.py`; `test_tasks_cli_contract_coord.py` ratchet re-points; `tests/architectural/untrusted_path_audit/inventory.md` (move_task).
- **Sequencing/depends-on**: IC-02 + IC-03 (foundations); status family additionally after IC-04.
- **Risks**: move_task is the largest (~526-LOC wrapper + 23 helpers) and carries the C-001 divergence wiring (`_skip_target_branch_commit` pre-gate) — coord harness T004/T005 mandatory in its targeted set; ratchet re-point per family in the SAME WP (FR-012).

### IC-06 — Architectural gates (AST dumps + LOC ceiling)

- **Purpose**: Close the god-file and inline-emission classes by construction, non-vacuously.
- **Relevant requirements**: FR-007, FR-011, C-006, SC-001/SC-002.
- **Affected surfaces**: NEW `tests/architectural/test_tasks_command_surface.py` (directory-glob AST gate, per-form self-mutation proofs, LOC ceiling with per-WP ratchet-down).
- **Sequencing/depends-on**: AST gate after IC-04 (needs 0 sites to assert); LOC ceiling can land early at 4569 and ratchet down per family move.
- **Risks**: gate scope must include ALL sibling modules (move-next-door evasion); ceiling honesty rule (`min(achieved, 1400)`, >1400 escalates).

### IC-07 — Registration-shim finalization + shim disposition

- **Purpose**: Final `tasks.py` state — wrappers + 4 small bodies + seam surface; `tasks_ports.py` 7-line shim disposition decided and executed (FR-008); final LOC ceiling recorded with delta-from-4569 rationale.
- **Relevant requirements**: FR-008, FR-011, NFR-004, SC-001.
- **Affected surfaces**: `tasks.py`, `tasks_ports.py`, the LOC gate ceiling constant.
- **Sequencing/depends-on**: all IC-05 moves complete.
- **Risks**: the shim has external importers to verify before absorbing (grep evidence in the WP).

### IC-08 — Boyscout: marker census + #2034 refresh

- **Purpose**: Committed census artifact mapping every tasks-domain-glob test file to its selecting CI gate (including the mission's new files); baseline-growth check; final #2034 comment naming #2283 as structural parent.
- **Relevant requirements**: FR-009, FR-010, SC-005.
- **Affected surfaces**: census artifact (location decided at tasks phase); `_gate_coverage_baseline.json` (assert-no-growth only); #2034 upstream comment.
- **Sequencing/depends-on**: after IC-01/IC-06 test files exist (the census must cover them); final comment at mission review.
- **Risks**: none material — pre-plan squad verified the domain currently fully gate-visible; the obligation is maintain-and-evidence.

## Progress Tracking

- [x] Phase 0: research.md (seam idiom verified live; Render API + byte-compat verified; gate patterns + primitives; emission-site map)
- [x] Phase 1: data-model.md (module layout, per-family move-sets, ~40-symbol seam inventory), contracts/ (parity + gates), quickstart.md
- [x] Charter Check: PASS, no violations
- [ ] Phase 2: /spec-kitty.tasks (NOT this command)
