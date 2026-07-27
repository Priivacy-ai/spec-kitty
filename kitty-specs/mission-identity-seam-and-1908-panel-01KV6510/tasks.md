# Tasks: Mission-identity naming seam & #1908 panel hardening

**Mission**: mission-identity-seam-and-1908-panel-01KV6510
**Branch**: `mission/mission-identity-seam-and-1908-panel` (planning base = merge target; PR to `upstream/main`)
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Research**: [research.md](research.md)

## Overview

10 work packages, TDD-first. **WP01 is the foundation** — it adds/fixes the entire
canonical seam in `lanes/branch_naming.py` (idempotent compose, in-place `mid8_from_slug`
demotion + authoritative `resolve_mid8`, legacy-faithful `worktree_dir_name`/`worktree_path`,
bare `mission_dir_name`/coord derivations, shared golden-value table); everything else *consumes*
its API. Cluster A routing WPs (WP02–WP06, WP10) route ALL scattered call sites + the
`coordination/` AND `missions/` parallel composers + every `mid8_from_slug` value-caller through the
seam. WP09 turns on the **literal-ban ratchet** (recurrence-shape: name-guess + inline `endswith`
dedup) once all routing lands. Cluster B (WP07/WP08) is independent.

**Post-tasks adversarial squad (2026-06-15) widened scope** (operator: fold-in + in-place demotion +
own all callers): folded the 2 missions/ composers into WP06, added WP10 for the ~12 `mid8_from_slug`
parse-callers, corrected WP02's site location, added `orchestrator_api:771`, hardened the fakeable
DoDs (#1949 regression-lock, #1917 arg-probe, #1916 incomplete-identity fixture), redesigned the WP09
ratchet around the actual recurrence shape, and added a NFR-001 diff-scan.

**Bounded surface (NFR-001):** the consolidation set (seam + routed call-site files + the missions/
composers + the mid8 parse-callers + Cluster B + tests); **zero** hunks in `status/` (except
`aggregate.py`) / `task_utils/` reducer internals — enforced by WP09's diff-scan. **Idempotency-
preserving** — routing emits byte-identical names (legacy-faithful both modes) so there is **no
on-disk worktree/coord churn for any mission**, asserted against WP01's shared golden-value table.

## Dependencies

```
WP01 (seam core) ─┬─→ WP02 (#1978 P1) ───────────┐
                  ├─→ WP03 (allocator+#1915) ─────┤
                  ├─→ WP04 (other lanes/) ────────┤
                  ├─→ WP05 (workspace/orch/tasks) ─┼─→ WP09 (literal-ban ratchet)
                  ├─→ WP06 (coordination/+missions/ unify) ┤
                  └─→ WP10 (mid8 parse-callers) ──┘
WP07 (#1917)  ── independent
WP08 (#1916)  ── independent
```
- WP02/03/04/05/06/10 each depend on **WP01** (need the seam API: `resolve_mid8`, the bare/coord
  primitives, the golden table); they own disjoint files → parallel.
- WP09 depends on **WP02+WP03+WP04+WP05+WP06+WP10** (the ratchet + NFR-001 scan fail until every
  name-guess, inline-dedup, false-compose f-string AND parse-caller is routed/removed).
- WP07, WP08 independent (no seam dependency).
- **Sequencing:** WP02 (#1978, P1) is the dogfooding driver — this mission's own slug embeds its mid8, so its merge depends on it; prioritize WP01→WP02.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Idempotent compose in `mission_branch_name`/`_required` (strip-reappend only when embedded==mid8(mission_id)) (#1949) | WP01 | |
| T002 | Demote `mid8_from_slug` to non-authoritative (decline on ambiguous 8-char tail) (#1918) | WP01 | |
| T003 | Canonical-first / legacy-failover resolve path + one-shot deprecation warning (FR-004) | WP01 | |
| T004 | Add `worktree_dir_name()` (== `lane_branch_name` minus prefix) + emit-don't-guess `worktree_path()` (#1899 grammar) | WP01 | |
| T005 | Round-trip/property test over (slug,mission_id) cases; TDD failing-first for #1949/#1918 | WP01 | |
| T006 | ruff/mypy clean + targeted seam tests | WP01 | |
| T007 | Failing regression: mid8-embedded-slug merge preflight false-negative (#1978) | WP02 | |
| T008 | `cli/commands/merge.py:1231` (`_check_mission_branch`) fallback → `mission_branch_name_required` | WP02 | |
| T009 | `merge/preflight.py:86` separate false-compose → seam (squad-corrected location) | WP02 | |
| T010 | `runtime/next/runtime_bridge.py:109` false-compose + its `mid8_from_slug` callers → seam | WP02 | |
| T011 | merge tests green (embedded + legacy) | WP02 | |
| T012 | Route `worktree_allocator.py:127` f-string → `worktree_path()` | WP03 | |
| T013 | Failing regression: multi-dep lane-merge non-atomic rollback (#1915) | WP03 | |
| T014 | Make `_merge_dependency_lane_tips` atomic (snapshot ref; reset on any conflict) | WP03 | |
| T015 | allocator tests green | WP03 | |
| T016 | Route `lanes/merge.py:83` → `worktree_path()` | WP04 | [P] |
| T017 | Route `lanes/recovery.py:392/593/608` → `worktree_path()` | WP04 | [P] |
| T018 | Route `lanes/lifecycle_sync.py:150/157` → `worktree_path()` | WP04 | [P] |
| T019 | Route `lanes/implement_support.py:120` → `worktree_path()` | WP04 | [P] |
| T020 | lanes/ routing tests green | WP04 | |
| T021 | Route `workspace/context.py:310/811/847/867` → `worktree_path()` | WP05 | [P] |
| T022 | Route `orchestrator_api/commands.py:475` AND `:771` → `worktree_path()` + its mid8 caller → resolve_mid8 | WP05 | [P] |
| T023 | Route `cli/commands/agent/tasks.py:1333` worktree + `:844` compose → seam | WP05 | |
| T024 | WP05 routing tests green | WP05 | |
| T025 | `coordination/workspace._compose_mission_dir` → delegate to seam | WP06 | |
| T026 | `coordination/transaction._mission_specs_dir_name` → delegate to seam | WP06 | |
| T027 | `coordination/status_transition._transaction_dir_name` → delegate to seam | WP06 | |
| T028 | `coordination/surface_resolver._coord_mid8` → delegate to seam | WP06 | |
| T029 | byte-identical-name + status/coord read-path regression tests | WP06 | |
| T030 | Failing regression: `implement --base=--flag` parsed as option (#1917) | WP07 | |
| T031 | `_validate_base_ref` insert `--` before the value | WP07 | |
| T032 | base-ref test green | WP07 | |
| T033 | Failing regression: `accept --no-commit` writes `.kittify/config.yaml` (#1916) | WP08 | |
| T034 | Move `ensure_identity` off the readiness path to a write-authorized boundary | WP08 | |
| T035 | Retire `_filter_accept_owned_project_config` + its caller | WP08 | |
| T036 | accept readiness side-effect-free test green | WP08 | |
| T037 | Literal-ban ratchet (3 idioms: name-guess + assign-then-join + inline `endswith(f"-{mid8}")` dedup) outside the seam (#1899) | WP09 | |
| T038 | NFR-001 diff-scan + red→green proof (all 3 idioms) + full architectural/lanes suites | WP09 | |
| T039 | `missions/_create.coordination_branch_name` → seam `coord_branch_name` (live coord-branch composer) | WP06 | |
| T040 | `missions/_read_path_resolver._compose_mission_dir` + `feature_dir_resolver` → seam `mission_dir_name`+`resolve_mid8` | WP06 | |
| T041 | Route `status/aggregate.py` + `cli/commands/decision.py` mid8 value-callers → `resolve_mid8` | WP10 | |
| T042 | Route `cli/commands/agent/{mission,workflow,status,context}.py` mid8 value-callers → `resolve_mid8` | WP10 | |
| T043 | mid8-caller routing tests (embedded resolves / coincidental declines) + gates | WP10 | |

---

## Phase 1 — Seam foundation

### WP01 — Canonical seam core (compose/parse/worktree grammar + failover)
- **Goal**: Make `lanes/branch_naming.py` the genuine single authority: idempotent compose (#1949), demoted `mid8_from_slug` (#1918), canonical-first/legacy-failover resolve path (FR-004), `worktree_dir_name()`/`worktree_path()` grammar (#1899), round-trip property test.
- **Priority**: P1 (foundation) · **Requirements**: FR-001, FR-003, FR-004, FR-005, FR-009, NFR-003 · **Deps**: none
- **Independent test**: property test asserts `compose` fixpoint + round-trip for embedded-matches/embedded-mismatch/coincidental-tail/legacy-NNN; legacy path emits one warning.
- **Prompt**: [tasks/WP01-seam-core.md](tasks/WP01-seam-core.md) · ~480 lines

- [x] T001 Idempotent compose in `mission_branch_name`/`_required` (#1949) (WP01)
- [ ] T002 Demote `mid8_from_slug` to non-authoritative (#1918) (WP01)
- [ ] T003 Canonical-first / legacy-failover resolve path + warning (FR-004) (WP01)
- [ ] T004 Add `worktree_dir_name()` + `worktree_path()` (#1899 grammar) (WP01)
- [ ] T005 Round-trip/property test; TDD failing-first for #1949/#1918 (WP01)
- [ ] T006 ruff/mypy + targeted seam tests (WP01)

## Phase 2 — Route call sites through the seam (parallel; each deps WP01)

### WP02 — #1978 merge false-compose → `mission_branch_name_required` (P1 driver)
- **Goal**: Stop the merge-blocking false-negative for mid8-embedded slugs across all three false-compose sites.
- **Priority**: P1 · **Requirements**: FR-002, FR-009 · **Deps**: WP01
- **Independent test**: a mission whose slug embeds its mid8 passes merge preflight; legacy missions still resolve.
- **Prompt**: [tasks/WP02-1978-merge-false-compose.md](tasks/WP02-1978-merge-false-compose.md) · ~330 lines

- [x] T007 Failing regression: embedded-slug preflight false-negative (#1978) (WP02)
- [x] T008 `merge.py:1231` fallback → `mission_branch_name_required` (WP02)
- [x] T009 `merge/preflight.py::_check_mission_branch` → seam (WP02)
- [x] T010 `runtime_bridge.py:109` false-compose → seam (WP02)
- [x] T011 merge tests green (embedded + legacy) (WP02)

### WP03 — Worktree allocator routing + #1915 lane-merge atomicity
- **Goal**: Route the allocator's worktree f-string through the seam; make multi-dep lane merge atomic.
- **Priority**: P1 · **Requirements**: FR-005, FR-001, FR-006, FR-009 · **Deps**: WP01
- **Independent test**: allocator emits identical worktree names via the seam; a later-dep conflict rolls back fully (no orphaned earlier-dep merge commit).
- **Prompt**: [tasks/WP03-allocator-and-1915.md](tasks/WP03-allocator-and-1915.md) · ~340 lines

- [ ] T012 Route `worktree_allocator.py:127` f-string → `worktree_path()` (WP03)
- [ ] T013 Failing regression: multi-dep non-atomic rollback (#1915) (WP03)
- [ ] T014 Make `_merge_dependency_lane_tips` atomic (WP03)
- [ ] T015 allocator tests green (WP03)

### WP04 — Route remaining `lanes/` worktree-dir sites
- **Goal**: Route the worktree-dir name-guesses in the other `lanes/` modules through the seam.
- **Priority**: P2 · **Requirements**: FR-005, FR-001, FR-009 · **Deps**: WP01
- **Independent test**: each routed site emits byte-identical names; targeted tests green.
- **Prompt**: [tasks/WP04-lanes-worktree-sites.md](tasks/WP04-lanes-worktree-sites.md) · ~300 lines

- [ ] T016 `lanes/merge.py:83` → `worktree_path()` (WP04)
- [ ] T017 `lanes/recovery.py:392/593/608` → `worktree_path()` (WP04)
- [ ] T018 `lanes/lifecycle_sync.py:150/157` → `worktree_path()` (WP04)
- [ ] T019 `lanes/implement_support.py:120` → `worktree_path()` (WP04)
- [ ] T020 lanes/ routing tests green (WP04)

### WP05 — Route workspace/orchestrator/tasks worktree + compose sites
- **Goal**: Route the remaining worktree-dir sites + the hand-rolled compose in `agent/tasks.py` through the seam.
- **Priority**: P2 · **Requirements**: FR-005, FR-001, FR-003, FR-009 · **Deps**: WP01
- **Independent test**: byte-identical names; `tasks.py:844` no longer hand-rolls the endswith dedup.
- **Prompt**: [tasks/WP05-workspace-orch-tasks-sites.md](tasks/WP05-workspace-orch-tasks-sites.md) · ~300 lines

- [ ] T021 `workspace/context.py:310/811/847/867` (incl. assign-then-join) → `worktree_path()` (WP05)
- [ ] T022 `orchestrator_api/commands.py:475` AND `:771` → `worktree_path()` + mid8 caller → resolve_mid8 (WP05)
- [ ] T023 `agent/tasks.py:1333` worktree + `:844` compose + mid8 callers → seam (WP05)
- [ ] T024 WP05 routing tests green (golden table) (WP05)

### WP06 — Unify ALL parallel composers (`coordination/` + `missions/`, #1878 slice)
- **Goal**: Delegate EVERY duplicate composer (4 coordination/ + `_create.coordination_branch_name` + `_read_path_resolver._compose_mission_dir` + `feature_dir_resolver`) to the seam so exactly one algorithm exists.
- **Priority**: P1 · **Requirements**: FR-010, FR-001, FR-009 · **Deps**: WP01
- **Independent test**: coordination/mission dir/branch names byte-identical (no churn); status/coord read-path + mission-create tests green; no `endswith`/`[:8]`/`f"{slug}-{mid8}"` survives.
- **Prompt**: [tasks/WP06-coordination-unify.md](tasks/WP06-coordination-unify.md) · ~420 lines

- [ ] T025 `coordination/workspace._compose_mission_dir` → seam (WP06)
- [ ] T026 `coordination/transaction._mission_specs_dir_name` → seam (WP06)
- [ ] T027 `coordination/status_transition._transaction_dir_name` → seam (WP06)
- [ ] T028 `coordination/surface_resolver._coord_mid8` → seam (WP06)
- [ ] T039 `missions/_create.coordination_branch_name` → seam `coord_branch_name` (WP06)
- [ ] T040 `missions/_read_path_resolver._compose_mission_dir` + `feature_dir_resolver` → seam (WP06)
- [ ] T029 byte-identical (all 6) + read-path + mission-create regression tests (WP06)

### WP10 — Route remaining `mid8_from_slug` parse-callers to `resolve_mid8`
- **Goal**: Close the in-place-demotion blast radius — route the value-callers in the 6 owned files (`status/aggregate.py`, `cli/commands/decision.py`, `agent/{mission,workflow,status,context}.py`) to the authoritative `resolve_mid8`.
- **Priority**: P2 · **Requirements**: FR-004, FR-001, FR-009 · **Deps**: WP01
- **Independent test**: per caller, embedded-mid8 resolves via `resolve_mid8`; coincidental tail no longer mis-resolves; no new fail-close.
- **Prompt**: [tasks/WP10-mid8-parse-callers.md](tasks/WP10-mid8-parse-callers.md) · ~110 lines

- [ ] T041 `status/aggregate.py` + `cli/commands/decision.py` mid8 value-callers → `resolve_mid8` (WP10)
- [ ] T042 `agent/{mission,workflow,status,context}.py` mid8 value-callers → `resolve_mid8` (WP10)
- [ ] T043 mid8-caller routing tests (embedded resolves / coincidental declines) + gates (WP10)

## Phase 3 — Independent Cluster B fixes

### WP07 — #1917 base-ref `--` separator
- **Goal**: `_validate_base_ref` passes the value after `--` so a leading-dash value is a ref, not an option.
- **Priority**: P3 · **Requirements**: FR-007, FR-009 · **Deps**: none
- **Prompt**: [tasks/WP07-1917-base-ref-separator.md](tasks/WP07-1917-base-ref-separator.md) · ~180 lines

- [ ] T030 Failing regression: `implement --base=--flag` (#1917) (WP07)
- [ ] T031 Insert `--` before the value in `_validate_base_ref` (WP07)
- [ ] T032 base-ref test green (WP07)

### WP08 — #1916 accept-gate `ensure_identity` off the readiness path
- **Goal**: `accept --no-commit`/readiness is side-effect-free; retire the dirty-exclusion stopgap.
- **Priority**: P3 · **Requirements**: FR-008, FR-009 · **Deps**: none
- **Prompt**: [tasks/WP08-1916-accept-identity.md](tasks/WP08-1916-accept-identity.md) · ~220 lines

- [ ] T033 Failing regression: `accept --no-commit` writes `.kittify/config.yaml` (#1916) (WP08)
- [ ] T034 Move `ensure_identity` off readiness → write-authorized boundary (WP08)
- [ ] T035 Retire `_filter_accept_owned_project_config` + caller (WP08)
- [ ] T036 accept readiness side-effect-free test green (WP08)

## Phase 4 — Enforce

### WP09 — Literal-ban ratchet (name-guessing + inline mid8-dedup forbidden outside the seam)
- **Goal**: A repo-wide ratchet that fails the 3 recurrence idioms (worktree/branch name-guess incl. assign-then-join + inline `endswith(f"-{mid8}")` dedup) outside the seam, plus a NFR-001 diff-scan, so the regression class cannot recur.
- **Priority**: P1 · **Requirements**: FR-005, FR-001, FR-009 · **Deps**: WP02, WP03, WP04, WP05, WP06, WP10
- **Independent test**: re-adding any of the 3 idioms outside `branch_naming.py` fails the ratchet (verify red per idiom, then revert).
- **Prompt**: [tasks/WP09-literal-ban-ratchet.md](tasks/WP09-literal-ban-ratchet.md) · ~200 lines

- [x] T037 Literal-ban ratchet test, 3 idioms (#1899) (WP09)
- [x] T038 NFR-001 diff-scan + red→green proof + full architectural/lanes suites (WP09)

---

## MVP
WP01→WP02 is the MVP (the seam + the P1 merge-blocker / dogfooding driver). The
remaining routing (WP03–WP06, WP10) + Cluster B (WP07/08) + the ratchet (WP09) complete
the consolidation.
