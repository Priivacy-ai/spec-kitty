# Mission Specification: M7 — ExecutionMode / enum consolidation

**Mission**: M7 (rc3 fail-loud friction burndown; Wave-1 lead — lands before M6/M4)
**Status**: SPECIFIED — operator decisions resolved; mission created; ready for `/spec-kitty.plan`
**Home ticket**: #3416 — WIDEN to include ExecutionMode as a **separated** acceptance block · coupled to #3590 / M6 (M6 depends on M7)
**Authored by**: analyst-annie, 2026-08-20 · verified against `main` · re-grounded against `upstream/main` @ `c44b4bcf87` on 2026-08-21 (every file:line citation re-checked on the current HEAD)

---

## Problem & impact (BLUF)

Three distinct classes are all named `ExecutionMode`, and two of them collide on a
`code_change` token that means **contradictory** things. The footgun: a reader sees
`ExecutionMode.code_change` and cannot tell, from the name, which axis they are on.

Verified on `main`:

| # | Enum | Members | Axis it models | Status |
|---|------|---------|----------------|--------|
| 1 | `specify_cli.ownership.models.ExecutionMode` (StrEnum) | `code_change` / `planning_artifact` | **What a WP produces** (source/test change vs planning artifact) | **LIVE**, widely consumed |
| 2 | `mission_runtime.context.ExecutionMode` (enum.Enum) | `worktree` / `code_change` | **How an action's context resolves** (lane worktree vs in-place checkout) | Members **DEAD** — no consumers — yet **surface-pinned** |
| 3 | `spec_kitty_events.status.ExecutionMode` (str, Enum) | `worktree` / `direct_repo` | **Status-payload execution mode** | **LIVE** (external PyPI package) |

The contradiction: in enum #1, `code_change` = "this WP changes code" (opposite of
`planning_artifact`). In enum #2, `code_change` = "resolves against an in-place / direct
checkout" (opposite of `worktree`). Same token, orthogonal meanings. Worse, enum #2 models
the **same axis** as enum #3 (worktree vs direct-checkout) but (a) names its second member
`code_change` instead of `direct_repo`, and (b) has zero member consumers — it is a dead,
mis-named local duplicate of the external enum #3's axis.

Impact: latent mis-comparison risk (a `code_change` verdict on one axis read as the other —
the same class of footgun the charter's `primary`/`merge` canon calls out), a canonical-source
violation (two enums for one axis, one class name for three), and a dead symbol that is
nonetheless declared "canonical execution-state surface" and pinned by an architectural test.

**Verification evidence (against `main`):**
- Enum #1 consumers: `core/worktree.py:196,204,206`, `workspace/context.py:798,800`,
  `ownership/{inference,validation,__init__}.py`, `lanes/implement_support.py:76`,
  `lanes/compute.py:328`, `cli/commands/agent/mission_parsing.py:245`.
- Enum #2: no importers of the symbol outside `src/mission_runtime/`; no `.WORKTREE` /
  `.CODE_CHANGE` member references anywhere. It **is** exported via
  `mission_runtime/__init__.py` `__all__` and **pinned** by
  `tests/architectural/test_mission_runtime_surface.py:53` as canonical surface
  (ADR `docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md`).
- Enum #3: live at `cli/commands/agent/tasks_transition_core.py:229` — `ExecutionMode("direct_repo")`.

This is a **code-hygiene / canonical-source** mission: retire the dead enum, resolve the token
collision, single authority per axis, class-name clash removed, behavior unchanged.

---

## In scope

- **Retire the dead enum #2** (`mission_runtime.context.ExecutionMode`) — including its `__all__`
  export, the surface-test pin, and an ADR-2026-06-07-1 note. It is surface-declared, so this is a
  **governance-gate change** (update `tests/architectural/test_mission_runtime_surface.py:53` and the
  ADR in the same change), **not** a bare delete.
- **Rename the live ownership enum #1** from `ExecutionMode` to a distinct name (e.g.
  `WorkProductKind` / `WorkPackageOutputKind`) so no two live classes share the name `ExecutionMode`;
  update every consumer. Its members (`code_change`/`planning_artifact`) keep their string values so WP
  frontmatter stays wire-compatible — this is a **class rename, not a value change**.
- **Single authority per axis**: the renamed enum #1 owns "what a WP produces"; the external enum #3
  owns the worktree-vs-direct axis (enum #2 is deleted, not merged). **The three enums do NOT unify** —
  they model three distinct axes.
- **Reserve room for M6.** M6 (#3590) depends on M7 (M7 lands first) and will ADD a non-diff
  completion-mode member to the renamed ownership enum. The rename and the guard test must **permit**
  that additive member without modification.
- A **re-drift guard test** preventing reintroduction of a second local WP-execution enum or the
  retired symbol — written to allow M6's additive member.

## Out of scope

- The five-**Severity**-enum ladder of #3416 — a separate, higher-coupling consolidation. ExecutionMode
  is co-located under #3416 as a **separated acceptance block**, not folded into the Severity work and
  not gated behind it.
- Changing the **members** of the external `spec_kitty_events.status.ExecutionMode` — cross-package
  boundary; out of reach of this repo (see Risks).
- Any behavioral change to lane routing, worktree resolution, or status payloads.
- **Authoring** the M6 non-diff completion-mode member itself — M7 only reserves room for it; M6 adds it.

---

## Functional Requirements

| ID | Title | Requirement | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Retire dead enum | Remove `mission_runtime.context.ExecutionMode` and its re-export; update the canonical-surface test (`test_mission_runtime_surface.py:53`) and ADR-2026-06-07-1 note to reflect the removal (governance-gate change). | High | Open |
| FR-002 | Rename ownership enum | Rename `ownership.models.ExecutionMode` to a distinct class name; update all consumers; **member string values unchanged** (frontmatter stays wire-compatible). | High | Open |
| FR-003 | Resolve name & token clash | After the mission, no two live classes are named `ExecutionMode`, and no single token (`code_change`) names two contradictory axes. | High | Open |
| FR-004 | Single authority per axis | The worktree-vs-direct axis is served by exactly one enum (external #3); "what a WP produces" is served by exactly one (renamed #1). | High | Open |
| FR-005 | Behavior preserved | All existing consumers of enums #1 and #3 compile and behave identically; no lane/worktree/status-payload behavior changes. | High | Open |
| FR-006 | Re-drift guard, M6-open | A guard test fails if a second local `worktree`/`code_change` enum is reintroduced or the retired symbol reappears in the mission_runtime surface — but **permits** M6 adding a non-diff completion-mode member to the renamed ownership enum. | Medium | Open |

## Acceptance criteria (Given/When/Then)

1. **Dead enum retired (governance-gate)** — **Given** `main` has three `ExecutionMode` classes,
   **When** M7 lands, **Then** `grep -rn "class ExecutionMode" src/` returns **zero** results,
   `mission_runtime/__init__.py` no longer exports the symbol,
   `test_mission_runtime_surface.py` no longer pins it, and ADR-2026-06-07-1 records the retirement.
2. **Ownership enum renamed, values intact** — **Given** the rename, **When** M7 lands, **Then** the
   ownership class carries its new name, every consumer resolves it, and the member string values
   (`code_change`, `planning_artifact`) are unchanged so existing WP frontmatter still parses.
3. **No name or token collision remains** — **Given** the retirement + rename, **When** a reader reads
   any live `ExecutionMode` reference, **Then** it resolves only to the external `spec_kitty_events`
   class, and no live enum pairs `worktree` with `code_change`.
4. **Consumers unchanged in behavior** — **Given** a green merge-base baseline, **When** M7 lands,
   **Then** the same suite is green with no consumer-behavior diffs (ownership inference/validation,
   worktree resolution, `tasks_transition_core` wire-probe all produce identical results).
5. **Guard permits M6** — **Given** M7's guard test, **When** M6 later adds a non-diff completion-mode
   member to the renamed ownership enum, **Then** the guard stays green; **When** a contributor
   reintroduces a local `worktree`/`code_change` enum or re-adds the retired symbol to the surface,
   **Then** the guard goes red.
6. **Static gates clean** — **Given** the change, **Then** `ruff` and `mypy --strict` are clean with no
   new suppressions.

---

## Key design decisions

- **The three enums do NOT unify.** Enum #1 models "what a WP produces"; #2/#3 model "how/where
  execution resolves". Merging #1 with the others would recreate the exact collision. Only #2 and #3
  share an axis — and #3 (external, live) already owns it, so #2 is deleted, not merged.
- **Delete #2, don't rename it.** Zero member consumers; removal is correct, and renaming a dead symbol
  is pure churn.
- **Rename #1, keep its values.** The class name is the residual footgun once #2 is gone; renaming the
  class (not the values) removes the clash with the external package while keeping WP frontmatter
  wire-compatible.
- **Retirement is a governance-gate action.** Enum #2 is pinned by a passing arch test + ADR; both are
  updated in the same change (campsite-first on the surface it touches).
- **M6 headroom by design.** M6 lands after M7 and adds a non-diff completion-mode member to the renamed
  enum; M7's rename and guard are written to accommodate that additive change without rework.

---

## Resolved decisions (were open questions)

- **(a) Ticket placement — RESOLVED: widen #3416**, adding ExecutionMode as a **separated acceptance
  block** so it is not gated behind the five-Severity ladder.
- **(b) Approach — RESOLVED: retire dead enum #2 + rename live ownership enum #1** (no full unification;
  three distinct axes). #2's retirement is a governance-gate change (arch test + ADR), not a plain delete.
- **(c) Sequencing vs M6 — RESOLVED: M7 lands first; M6 depends on M7.** M6 will ADD a non-diff
  completion-mode member to the renamed ownership enum — M7 reserves room and its guard test permits the
  addition (AC-5).

---

## Risks

- **External `spec_kitty_events` package boundary.** Enum #3 lives in a published PyPI package and cannot
  be changed from this repo. The surviving live `ExecutionMode` name will be the external one; the
  `direct_repo`/`code_change` axis-naming history persists across the boundary and can only be reconciled
  via cross-package coordination, not within M7.
- **Governance-gate / surface-pinned symbol.** Retiring enum #2 touches `test_mission_runtime_surface.py`
  and ADR-2026-06-07-1. Treat the ADR/surface update as in-scope, not collateral; expect the architectural
  gate to flag it until updated.
- **Rename blast radius.** Renaming the ownership class touches ~8 consumer modules; a missed reference is
  a compile break, not a silent behavior change (mypy catches it). Member values are held constant to
  protect frontmatter compatibility.
- **Behavior-preservation burden.** Pure hygiene mission — any consumer-behavior diff is a defect. Requires
  a green merge-base baseline to attribute reds correctly (baseline-red gotcha applies).
- **M6 coupling.** M6 depends on M7 and extends the renamed enum. If M7's guard is written too strictly it
  will block M6 — AC-5 explicitly requires the guard to permit M6's additive member.

## Issues

- **#3416** — home ticket (five-Severity-enum ladder); WIDENED to include ExecutionMode as a separated
  acceptance block.
- **#3590 / M6** — depends on M7; will add a non-diff completion-mode member to the renamed ownership enum.
- ADR `docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md` — updated when enum #2 is retired.

## Cross-mission coordination (rc3 integration check)

- **Downstream consumers (M7 lands first).** BOTH **M6** (adds a non-diff completion-mode member to the renamed enum) AND **M4** (its #3590 detector consumes `infer_execution_mode`, whose members this mission renames) depend on M7. Sequence M7 before both; the drift-guard test must permit M6's additive member while still catching re-drift.
