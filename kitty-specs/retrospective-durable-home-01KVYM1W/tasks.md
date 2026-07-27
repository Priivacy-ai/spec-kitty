# Tasks: Teardown-Surface Hardening + Retrospective Durable Home

**Mission ID:** 01KVYM1WS4M2FG00WGJV04N879
**Slug:** retrospective-durable-home-01KVYM1W
**Target branch:** fix/3.2.3-coord-surface-regressions
**Base:** upstream/main `e36547461` (post-#2133/#2114/#2134/#2135 — no open-PR gate)
**Input:** [spec.md](./spec.md) · [plan.md](./plan.md) · [data-model.md](./data-model.md) · [research.md](./research.md) · [contracts/terminal-artifact-teardown-contract.md](./contracts/terminal-artifact-teardown-contract.md)

> **One slice, six WPs.** FR-011 (handle-safe PRIMARY entry points) is the FOUNDATION, split into a
> READ leg (WP01, `resolve_planning_read_dir:1306`) and a WRITE leg (WP03, the 6 placement sites) —
> both caller-canonicalize the bare handle BEFORE the topology-blind `primary_feature_dir_for_mission`
> compose (the primitive STAYS blind: canonicalizing inside it is infinite recursion, `:418`→`:454`).
> The kind/authority and consolidation WPs build ON it via `dependencies`. FR-006 is **STRUCK**
> (DONE-by-merge #2129; regression-reference only — no code in scope). Every anchor below was
> **live-verified against `e36547461`/HEAD** before writing.

---

## Overlap-Trap Resolutions (Decision Documentation — DIRECTIVE_003)

The `owned_files` no-overlap rule (`spec-kitty agent mission finalize-tasks --validate-only`)
flags only **concurrent** WP pairs; **dependency-ordered (sequential) pairs are exempt**
(`src/specify_cli/ownership/validation.py:198-207`). The three traps are resolved as:

1. **Trap 1 — FR-004 (teardown seam) + FR-005 (persist-before-destroy) edit the SAME new seam.**
   → **MERGED into ONE WP (WP04).** The seam's whole purpose IS persist-before-destroy; splitting
   them would force two WPs to own the new `coordination/teardown.py` + the three call sites + the
   `test_executor_coverage.py:616` update. One cohesive WP creates the seam and attaches its
   invariant in a single review.

2. **Trap 2 — FR-010 (hoist `retrospective.yaml` literal) touches the SAME files as FR-001/003**
   (`writer.py`, both `retrospective_terminus.py`, `lifecycle_events.py`). → **FR-010 is its OWN WP
   (WP06) that `depends: [WP03]`.** The dependency edge makes WP03↔WP06 sequential → overlap-exempt
   on the shared retrospective files, so the hoist stays isolated (it crosses the shared-package
   boundary and warrants its own review) without an illegal concurrent overlap.

3. **Trap 3 — FR-008 (dead helpers) + FR-009 (stale prose) both touch `mission_type.py`, and
   FR-004's teardown call site is ALSO `mission_type.py:910`.** → **FR-008 + FR-009 fold into WP04**
   (the WP that already owns `mission_type.py` via the teardown seam). One WP owns the whole file;
   no second WP claims it. The tidy edits are line-disjoint from the teardown region and ride along
   safely.

4. **Trap 4 (post-squad) — FR-011 read leg (WP01) vs write leg (WP03).** The handle-canonicalization
   cure cannot live inside `primary_feature_dir_for_mission` (infinite recursion: that primitive is
   called by `_canonicalize_bare_modern_handle:418` at `:454`). It is therefore caller-side at the
   PRIMARY entry points: **WP01 owns the READ leg** (`resolve_planning_read_dir:1306`, inside
   `_read_path_resolver.py`) and **WP03 owns the WRITE leg** (the 6 retrospective placement sites).
   Both reuse the SAME shared helper at **disjoint files** — no `owned_files` overlap.

5. **Trap 5 (post-squad) — WP04 persist depends on WP03.** WP04's seam persists the retrospective via
   the WP03 write sites; without WP03 those sites still resolve the coord worktree, so persist would
   write into the worktree it then destroys. → **WP04 `depends: [WP01, WP03]`** (was `[WP01]`); the
   edge re-sequences WP04 after WP03's lane.

**Net effect:** every `owned_files` set is disjoint across all *concurrent* pairs; the only shared
ownership (WP03↔WP06 on the retrospective files) is dependency-ordered and therefore legal.

---

## WP Dependency Graph

```
WP01 (FR-011 foundation, handle-safe READ seam)
 ├─► WP02 (FR-002 RETROSPECTIVE kind + authority)
 │     └─► WP03 (FR-001/003 + FR-011 write-leg: consolidate 6 home sites)
 │           ├─► WP06 (FR-010 filename-literal hoist)
 │           └─► WP04 (FR-004/005/008/009 teardown seam + persist-before-destroy + tidy)
 └────────────► WP04 (also depends on WP01)

WP05 (FR-007 recovery-command repoint) — no deps, fully parallel
```

| WP | Title | FRs | Depends | Owned surface (authoritative) | Parallelism |
|----|-------|-----|---------|-------------------------------|-------------|
| WP01 | FOUNDATION — handle-safe PRIMARY read seam (caller-canonicalize at `resolve_planning_read_dir:1306`; primitive stays blind) | FR-011 | — | `missions/_read_path_resolver.py` | root |
| WP02 | RETROSPECTIVE kind + primary-anchored authority | FR-002 | WP01 | `mission_runtime/artifacts.py` | after WP01 |
| WP03 | Consolidate the 6 retrospective home sites + WRITE-leg handle-canon | FR-001, FR-003, FR-011(write) | WP01, WP02 | `retrospective/` + `post_merge/` + `runtime/next/.../retrospective_terminus.py` + `tests/retrospective/test_record_committable_1771.py` | after WP02 |
| WP04 | Shared teardown seam + persist-before-destroy + tidy | FR-004, FR-005, FR-008, FR-009 | WP01, **WP03** | `coordination/teardown.py` (new) + `merge/executor.py` + `cli/commands/merge.py` + `cli/commands/mission_type.py` | after WP03; parallel w/ WP05 |
| WP05 | Recovery-command repoint (#1890) | FR-007 | — | `cli/commands/_coordination_doctor.py` + `coordination/surface_resolver.py` + SOURCE `SKILL.md` + 2 re-pinned tests (`test_surface_resolver_coord_empty_warning.py`, `test_surface_resolver.py`) | fully parallel |
| WP06 | `retrospective.yaml` filename-literal hoist | FR-010 | WP03 | `core/constants.py` + the literal sites (sequential w/ WP03) | after WP03 |

---

## Requirement → WP coverage

| FR | WP | Notes |
|----|----|-------|
| FR-001 | WP03 | placement on durable PRIMARY home; live-coord `".worktrees" not in resolved.parts` |
| FR-002 | WP02 | `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS` unit assertion |
| FR-003 | WP03 | 6 home sites → one authority; GREP/AST enumerating structural test |
| FR-004 | WP04 | one shared teardown seam in `coordination/`; anti-rename structural test |
| FR-005 | WP04 | persist-before-destroy OUTSIDE the swallow; destroy-step fault injection; UPDATE `test_executor_coverage.py:616` |
| ~~FR-006~~ | WP04 (T048) | **STRUCK** — DONE-by-merge #2129. NO product code; mapped to WP04 only as the regression-reference home (a guard test locking the already-shipped #2129 sibling-survival invariant). See the WP04 "upstream gap" note: the validator has no struck-FR exclusion. |
| FR-007 | WP05 | 8 `src/` phantom sites → `doctor workspaces --fix`; `src/`-scoped count-agnostic grep-guard; 2 test-side assertions re-pinned (T055, DIR-041) |
| FR-008 | WP04 | remove 2 dead helpers (prove zero callers) |
| FR-009 | WP04 | fix 2 stale comments (`mission_type.py:642`, `:607`) |
| FR-010 | WP06 | hoist filename literal (8 literals + 2 `.tmp`) to one const in `core/constants.py` |
| FR-011 | WP01 (read leg) + WP03 (write leg) | caller-canonicalize the bare handle BEFORE the blind compose — WP01 owns `resolve_planning_read_dir:1306`, WP03 owns the 6 write sites; primitive `primary_feature_dir_for_mission` STAYS blind (recursion: `:418`→`:454`); equivalence matrix through the read seam |

---

## Subtask Index

### WP01 — FOUNDATION: handle-safe PRIMARY read seam (FR-011 / #2136) — caller-canonicalize; primitive stays blind

- [x] T011 Red-first handle-equivalence + ambiguity matrix THROUGH `resolve_planning_read_dir` (bare-mid8 ≡ bare-slug ≡ `<slug>-<mid8>`; ambiguous → raises) (WP01)
- [x] T012 Caller-canonicalize bare handle in `resolve_planning_read_dir`'s PRIMARY leg (`:1306`) via `_canonicalize_bare_modern_handle@418` — primitive STAYS blind (recursion: `:418`→`:454`) (WP01)
- [x] T013 Back-compat no-op proof: `meta.json`-present + unresolvable-handle legs unchanged; primitive-still-blind proof (WP01)
- [x] T014 Author ADR `2026-06-25-1-terminal-artifact-durable-home-teardown.md` (WP01)
- [x] T015 Full `tests/missions/` + `tests/integration/` regression + blast-radius check (WP01)

### WP02 — RETROSPECTIVE kind + primary-anchored placement authority (FR-002)

- [x] T021 Add `RETROSPECTIVE` enum member to `MissionArtifactKind@24` (WP02)
- [x] T022 Add `RETROSPECTIVE` to `_PRIMARY_ARTIFACT_KINDS@85` (WP02)
- [x] T023 Unit assertion `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS` + `is_primary_artifact_kind(RETROSPECTIVE)` True (WP02)

### WP03 — Consolidate the 6 retrospective home sites + WRITE-leg handle-canon (FR-001/003/011-write)

- [x] T031 Live-coord behavioral test: `".worktrees" not in resolved.parts`, lands at `kitty-specs/<slug>/` (WP03)
- [x] T032 GREP/AST enumerating structural test (no hardcoded count; 7th-site fails) (WP03)
- [x] T033 Re-point sites #1–#2: `writer.py:48`, `post_merge/retrospective_terminus.py:68` → authority (WP03)
- [x] T034 Re-point sites #3–#5: `lifecycle_events.py:336/:411/:480` → authority (WP03)
- [x] T035 Re-point site #6: `runtime/next/.../retrospective_terminus.py:76` `_record_path_str` payload → authority (WP03)
- [x] T036 Payload-parity + flattened no-regression assertions; LEAVE `writer.py:60` `_legacy_record_path` (WP03)
- [x] T037 RE-PIN `test_record_committable_1771.py:60` (DIR-041): add `".worktrees" not in parts` on a coord-divergent fixture (kill the #1771 false-green twin) (WP03)

> WP03 also owns the **WRITE-leg handle-canonicalization** (FR-011 write half): each of T033–T035
> canonicalizes its handle via `_canonicalize_bare_modern_handle` BEFORE composing through the
> topology-blind `primary_feature_dir_for_mission` (WP01 owns the READ leg `:1306`; WP03 owns the
> WRITE leg at these sites — same shared helper, disjoint files, no overlap).

### WP04 — Shared teardown seam + persist-before-destroy + tidy (FR-004/005/008/009)

- [x] T041 Extract `_teardown_coordination_topology` seam into `coordination/teardown.py`; LAZY/function-local retrospective-persist import (mirror `retrospective/gate.py:201`); do NOT add to `coordination/__init__.__all__`; docstring confirms ADR Binding B (WP04)
- [x] T042 Re-point the 3 call sites onto the seam: `executor.py:795`, `merge.py:270`, `mission_type.py:910` (WP04)
- [x] T043 Anti-rename structural test: zero PRODUCTION `CoordinationWorkspace.teardown(` outside the seam (`src/specify_cli/**` + `src/runtime/**`, EXCLUDE `tests/**` + seam file; no per-call allow-list; 10 legit test calls survive) (WP04)
- [x] T044 Persist OUTSIDE the swallow; discard persist-hook ahead of the `_discard_mission` CALL at `:623` (preserve destroy→verify→flatten); UPDATE `test_executor_coverage.py:616` (WP04)
- [x] T045 Destroy-step fault-injection proof on merge + close/`--discard` paths (WP04)
- [x] T046 FR-008: remove dead helpers `_list_active_worktrees@78`/`_print_active_worktrees@313` (prove zero callers) (WP04)
- [x] T047 FR-009: fix stale comments `mission_type.py:642` (merge.py:1568) + `:607` (prefix-match prose) (WP04)
- [x] T048 FR-006 regression-reference lock (#2129 sibling-survival; NO product code) (WP04)

### WP05 — Recovery-command repoint (FR-007 / #1890)

- [x] T051 Count-agnostic grep-guard test scoped to **`src/`** (8 sites; NOT docs/architecture/kitty-specs/tests) — fails on any surviving `agent worktree repair` (WP05)
- [x] T052 Repoint `_coordination_doctor.py` ×4 (`:220/:293/:338/:345`) → `doctor workspaces --fix` (WP05)
- [x] T053 Repoint `surface_resolver.py` ×3 (`:109/:119/:782`) → `doctor workspaces --fix` (WP05)
- [x] T054 Repoint SOURCE `SKILL.md:509` → `doctor workspaces --fix` (WP05)
- [x] T055 RE-PIN the 2 test-side phantom assertions (DIR-041): `test_surface_resolver_coord_empty_warning.py:127` + `test_surface_resolver.py:276` → `doctor workspaces --fix` (WP05)

### WP06 — `retrospective.yaml` filename-literal hoist (FR-010)

- [x] T061 Define `RETROSPECTIVE_FILENAME` const in `core/constants.py` (boundary-safe shared home) (WP06)
- [x] T062 Hoist the 8 string literals across the 6 `.py` files onto the const (WP06)
- [x] T063 Compose the 2 `.tmp` f-string prefixes (`writer.py:148/:424`) from the const (WP06)
- [x] T064 Single-definition assertion test for the filename const (WP06)
</content>
