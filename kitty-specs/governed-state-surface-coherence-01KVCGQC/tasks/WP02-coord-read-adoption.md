---
work_package_id: WP02
title: '#2016 orchestrator coord-read adoption'
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- NFR-002
- NFR-005
tracker_refs:
- '#2016'
planning_base_branch: feat/governed-state-surface-coherence
merge_target_branch: feat/governed-state-surface-coherence
branch_strategy: Planning artifacts for this mission were generated on feat/governed-state-surface-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/governed-state-surface-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4139545"
history:
- 2026-06-18 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/orchestrator_api/commands.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- src/specify_cli/coordination/surface_resolver.py
- tests/specify_cli/regression/test_issue_1615_1616_1617_1618.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and binding context. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:
1. `kitty-specs/governed-state-surface-coherence-01KVCGQC/spec.md` — **FR-001..FR-004, NFR-002, NFR-005, C-001**.
2. `kitty-specs/governed-state-surface-coherence-01KVCGQC/research.md` — Goal A table + **decision D-1** (adopt the ONE `_coord_mid8` cascade; tier-3 `mid8_from_slug` is the operative tier for the coord-only topology).
3. The canonical seam to adopt: `src/specify_cli/coordination/surface_resolver.py::_coord_mid8` (~:363-415).

## Objective

`orchestrator_api/commands.py::_resolve_mission_dir` returns `None` for a **coord-only-with-tail-slug** mission (a mission present only as a coordination worktree, no primary `meta.json`). Root cause: it reimplements mid8 resolution with only the strict tier-2 `resolve_mid8(slug, mission_id)` keyed on **primary** meta; on a coord-only fixture `mission_id=None` → `resolve_mid8` declines → empty mid8 → the M5 fail-closed guard doesn't fire (`declares_coordination=False`) → it falls through to an empty-mid8 read-path miss → `None`.

**Fix = adopt the one sanctioned mid8 cascade** (`coordination/surface_resolver.py::_coord_mid8`): `meta.mid8` → `resolve_mid8(meta.mission_id)` → **`mid8_from_slug(slug)`** (the tier that resolves the coord-only topology — the canonical `<slug>-<mid8>` name embeds the disambiguator). This is an **adoption gap**, not a missing capability (#1868: adopt the seam, don't re-derive).

**Bindings:**
- **NFR-005:** consolidate onto ONE cascade — no second parallel resolver path remains. **Prefer extracting a small shared helper** that both `surface_resolver` and `_resolve_mission_dir` call, rather than duplicating the tier logic (hence `surface_resolver.py` is in `owned_files`).
- **FR-003:** preserve fail-closed — a handle with no declared identity AND no canonical tail still raises `StatusReadPathNotFound` (no fabricated path, no stale-primary read).
- **C-001 / NFR-002:** the red test fixture is coord-only with a **full 26-char ULID-derived** mid8 and a real coord-worktree path. **Do NOT seed a fake primary meta** to make it pass — that defeats the test.

## Subtasks

### T010 — Failing-first test (TDD)

**Purpose:** lock the defect before the fix. Note `tests/specify_cli/regression/test_issue_1615_1616_1617_1618.py::TestIssue1616OrchestratorApiCoordRead::test_coord_path_returned_when_coord_exists` is **already RED** on HEAD — confirm it, and strengthen the fixture to topology-true realism if needed.

**Steps:**
1. Run the existing class; confirm `test_coord_path_returned_when_coord_exists` fails (`got None`).
2. **Mandatory (not conditional):** upgrade the fixture mid8 to the first 8 chars of a real **full 26-char ULID** `<slug>-<mid8>` (realistic test data, NFR-005). Keep it coord-only (empty coord mission dir, **no meta.json**). A RED caused by a malformed/short fixture is NOT acceptable.
3. The RED assertion MUST capture the *cause*: assert that the pre-fix path is `None` **because** the orchestrator's derived `mid8` is empty (`""`) — e.g. assert the resolved mid8 is `""` before the fix, so the green-after proves tier-3 `mid8_from_slug` actually produced the 8-char mid8 (not some unrelated change).
4. Confirm `test_none_returned_when_mission_not_found` (tail-present, dir-absent → `None`) is present and currently green.

**Validation:** the coord-path test is RED specifically because derived mid8 is `""`; the not-found test is green.

### T011 — Adopt the cascade VALUE, not its raise (FR-001/FR-002, NFR-005) — ⚠️ legacy-safety critical

> ⚠️ **BINDING SAFETY (squad-debbie):** `_coord_mid8` **raises `StatusReadPathNotFound` when all tiers exhaust** (no tail + no declared id). The orchestrator MUST NOT inherit that raise unconditionally — a **legacy non-coord** mission (no `mission_id`, no `coordination_branch`, slug with no Crockford tail, e.g. `099-test-mission`) currently returns the **primary path** and MUST keep doing so. A naive verbatim adoption regresses it to a raise and breaks the live contract tests (`tests/contract/test_orchestrator_api.py::test_response_contains_mission_slug` + 3 more). The M5 comment's own invariant — *"legacy missions never declare coordination_branch, so they keep the primary-read path unchanged"* — must hold.

**Steps:**
1. Study `surface_resolver.py::_coord_mid8` — the 3-tier cascade (`meta.mid8` → `resolve_mid8(meta.mission_id)` → `mid8_from_slug`), which **raises** on exhaustion.
2. Extract a shared helper `resolve_declared_mid8(meta, slug) -> str` in `surface_resolver.py` that runs the 3 tiers and **returns `""` on exhaustion (does NOT raise)** — the raise decision belongs to each caller's topology gate. Refactor `_coord_mid8` to call this helper and apply its OWN fail-closed raise on `""` (preserving its current behavior exactly — `_coord_mid8`'s contract is unchanged).
3. In `_resolve_mission_dir`, derive mid8 via `resolve_declared_mid8(primary_meta_or_empty, slug)`. For the **coord-only-with-tail** topology tier-3 `mid8_from_slug` returns the real mid8 → coord path composes and returns. Keep the existing `declares_coordination`-gated M5 raise: `if not mid8 and declares_coordination: raise StatusReadPathNotFound(...)`. For a **legacy non-coord** handle (`mid8==""`, `declares_coordination=False`) the guard does NOT fire → fall through to `resolve_mission_read_path(root, slug, "")` → primary read (unchanged, non-raising — returns `None` if absent).
4. Remove ONLY the orchestrator's old strict-`resolve_mid8`-keyed-on-primary derivation, replacing it with the one `resolve_declared_mid8` call (NFR-005 — one cascade). Do NOT remove the `declares_coordination` topology gate.

**Validation:** `test_coord_path_returned_when_coord_exists` green; the legacy-no-coord case (T012b) still returns primary/`None` (no raise); no duplicated tier logic in `commands.py`.

### T012 — Preserve fail-closed AND legacy primary-read (FR-003) — two distinct cases

**Steps (pin BOTH cases — they are different):**
1. **Coord-declared, no resolvable mid8** (`declares_coordination=True`, cascade `""`): MUST raise `StatusReadPathNotFound` (typed, with `coord_candidate`/`primary_candidate`) — the M5 protection against reading a stale primary under a coord topology. Keep this.
2. **Legacy non-coord, no tail, no id** (`declares_coordination=False`, cascade `""`, e.g. `099-test-mission`): MUST return the **primary path / `None`** — NOT raise. This is the legacy contract debbie flagged.
3. **Tail-present, dir-absent** (`mid8` resolves but the dir doesn't exist): MUST return `None` (this is `test_none_returned_when_mission_not_found`).
4. Keep the M5 rationale intact (no empty-mid8 seed anti-pattern).

**Validation (T012b — add this regression):** add a test with a legacy fixture (slug `099-style` no-tail, meta.json with NO `mission_id`/`coordination_branch`) asserting `_resolve_mission_dir` returns the primary path (or `None` if absent), **does not raise**. Run `tests/contract/test_orchestrator_api.py` — all 4 named tests (`test_response_contains_mission_slug`, `test_command_field_uses_mission_era_name`, `test_mission_flag_works`, `test_mission_not_ready_error`) MUST stay green. Confirm `test_resolve_seam_fails_closed_on_coord_topology` (the stale-primary M5 case) stays green.

### T013 — Fold: `_fail -> NoReturn` (FR-004, S5747)

**Steps:**
1. `orchestrator_api/commands.py::_fail` (~:221) is typed `-> None` but always raises `typer.Exit`. Retype it `-> NoReturn` (import from `typing`).
2. The two `raise  # unreachable: _fail exits` lines (~:367, :370) become provably dead — **delete them**. mypy now proves the code after `_fail(...)` is unreachable.

**Validation:** mypy clean; the two unreachable raises are gone; no behavior change (the calls still exit).

### T014 — Quality gate + binding one-cascade assertion (NFR-005, F6)

**Steps:**
1. Run the full #2016 regression class + `tests/contract/test_orchestrator_api.py` + `tests/specify_cli/.../test_typed_error_fail_closed.py`.
2. **Binding NFR-005 check (not a manual grep):** add an assertion that `orchestrator_api/commands.py` contains exactly ONE mid8-derivation path — the `resolve_declared_mid8` call — and NO remaining direct `resolve_mid8(...)` call keyed on primary-only meta. Prefer a small source-level architectural test (read `commands.py` source, assert the old pattern is absent); a CI grep-gate is acceptable only if a test is impractical.
3. `ruff check` + `mypy` on `commands.py` + `surface_resolver.py`; complexity ≤15 (ruff C901, the local gate); zero new suppressions.

**Validation:** all green; the one-cascade assertion passes; ruff+mypy clean.

## Branch Strategy

Planning branch `feat/governed-state-surface-coherence`; merge target `main` (PR). Depends on **WP01** (the real edge: WP02 edits the mid8 cascade — the surface WP01's AST short-id ratchet polices — so D3 must be reconciled first). Execution worktree allocated per `lanes.json`.

## Definition of Done

- [ ] `test_coord_path_returned_when_coord_exists` green via the shared cascade (tier-3 `mid8_from_slug`), topology-true coord-only fixture (full 26-char ULID, NO fake primary meta — C-001), RED-cause pinned to empty mid8 (F12).
- [ ] **Legacy non-coord regression (T012b):** a no-tail/no-id mission returns primary/`None` (does NOT raise); `tests/contract/test_orchestrator_api.py` 4 named tests stay green (debbie).
- [ ] `resolve_declared_mid8` returns `""` on exhaustion (no raise); `_coord_mid8`'s own raise-on-`""` behavior unchanged; orchestrator keeps its `declares_coordination`-gated raise.
- [ ] Coord-declared + unresolvable mid8 still raises typed `StatusReadPathNotFound` (FR-003, M5); `test_resolve_seam_fails_closed_on_coord_topology` green.
- [ ] Exactly ONE mid8 cascade (NFR-005) — enforced by the T014 binding assertion, not just a grep.
- [ ] `_fail` retyped `NoReturn`; the two unreachable raises deleted (FR-004).
- [ ] ruff + mypy clean ≤15, zero new suppressions; full #2016 class green.
- [ ] Issue-matrix row for #2016 set to a verdict; #2016 carries a tracker comment naming mission `01KVCGQC` (SC-007).

## Reviewer Guidance

Confirm: the shared `resolve_declared_mid8` helper **returns `""` on exhaustion (does not raise)** so legacy non-coord missions keep their primary-read path (run `tests/contract/test_orchestrator_api.py` — must be green); the orchestrator's `declares_coordination`-gated raise is intact (coord-topology stale-primary protection); the fixture is coord-only with no fake primary meta (C-001); the one-cascade NFR-005 check is a binding assertion (not a skippable manual grep); `_fail -> NoReturn` makes the deleted raises provably dead. Reject if `_resolve_mission_dir` now raises for a no-tail/no-coord legacy mission.

## Activity Log

- 2026-06-18T06:20:20Z – claude:sonnet:python-pedro:implementer – shell_pid=4097986 – Assigned agent via action command
- 2026-06-18T06:30:51Z – claude:sonnet:python-pedro:implementer – shell_pid=4097986 – Orchestrator adopts shared resolve_declared_mid8 cascade (tier-3 mid8_from_slug) for coord-only-with-tail topology; helper returns '' on exhaustion (no raise) so legacy non-coord missions keep primary-read; _coord_mid8 raise + orchestrator declares_coordination M5 raise intact; _fail->NoReturn, 2 unreachable raises deleted; binding AST one-cascade assertion; ruff+mypy clean; 244 tests green incl 4 named contract tests.
- 2026-06-18T06:31:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=4139545 – Started review via action command
- 2026-06-18T06:35:53Z – user – shell_pid=4139545 – FR-001..004/NFR-002/NFR-005/C-001 verified via lane src (PYTHONPATH=src). Legacy-safety: resolve_declared_mid8 returns '' on exhaustion (no raise); _coord_mid8 keeps own raise; orchestrator keeps declares_coordination-gated M5 raise. All 13 contract tests green incl 4 named. 22/22 #2016 regression green: coord-only-with-tail fixture full 26-char ULID no fake primary meta, RED-cause pinned to empty mid8 via tier-3 mid8_from_slug. AST one-cascade test binding (fails on base commands.py which calls resolve_mid8). M5 + typed_error_fail_closed green. _fail->NoReturn, 2 unreachable raises deleted (mypy proves dead). ruff+mypy clean C901<=15, zero new suppressions. Owned-files-only (out-of-scope ratchet edits are WP01 dep commit).
