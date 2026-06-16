# Implementation Plan: Naming/Identity Routing Rider

**Branch**: `feat/naming-rider-3-2-1` (stacked on `design/naming-identity-ssot-alignment`; PRs to `main`)
| **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)
**Input**: `kitty-specs/naming-identity-routing-rider-01KV7SFD/spec.md`
**Governing intent**: [`docs/release-goals/3.2.x.md`](../../docs/release-goals/3.2.x.md) G2 — the
deliberate low-risk opener of the "strangle core domains onto SSOTs" cycle.

## Summary

Route the live mission-identity derivation sites onto the **existing** canonical seam — specifically the
**failover-aware authoritative entrypoint** (`resolve_mid8`/`resolve_transaction_mid8`, the 3.2.0
"name proposes, authority disposes" mechanic), not bare `mid8()` — extend the architectural ratchet to a
repo-wide regression **tripwire** that also forbids bypassing that entrypoint, route the #2000 compose
sites, fix the #1888 phantom-path bug, and verify-and-close #1971-tail. **No new authority is built.**
Phase 0 + the adversarial scope review (`scope-review/SCOPE-REVIEW-SYNTHESIS.md`) corrected the surface:
**~15 short-id route-sites (5 missed by the first grep), 0 fragment-adopt sites, #2000 compose-routing,
#1888 real fix, #1971-tail verify-close** — with **#1993 / #1900 / #1899-tail dropped or deferred to a
follow-on mission** (the `resolve_lanes_dir` idea was a C-001 violation; lanes.json is already
centralized). A research squad on **issue #2007** (Robert's 3.2.0 training bugs) then folded in a bounded
**command-contract-drift guard** (its Focus A) as a sibling of the ratchet — IC-06 — while its read-path/
error-fidelity adoption class is recorded as the **next named focus** (its own mission), not this one.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing `specify_cli.lanes.branch_naming` seam (`mid8`, `resolve_mid8`,
`mission_branch_name`, `worktree_dir_name`, `worktree_path`), `mission_runtime.context.IdentityFragment`;
typer/rich CLI surface; ruamel.yaml.
**Storage**: N/A (filesystem only — `kitty-specs/<mission>/lanes.json`, `.worktrees/`; no schema change).
**Testing**: pytest. **Behavioral / function-over-form** (NFR-002) + **verification-by-deletion**
(C-004); the literal-ban architectural-consistency ratchet (`tests/architectural/test_no_worktree_name_guess.py`)
is the **sole intentional form-coupled test**. TDD-first for behavioral fixes (C-003).
**Target Platform**: Linux/macOS/Windows dev environments (the spec-kitty CLI).
**Project Type**: single project (`src/specify_cli/`, `src/runtime/`, `src/mission_runtime/`).
**Performance Goals**: none — routing must be behavior-neutral (NFR-001 byte-parity).
**Constraints**: bounded conflict surface (named seam/consumer files only, NFR-004); idempotency-preserving,
no on-disk worktree/coord churn (NFR-005); ruff + mypy clean, complexity ≤ 15, no suppressions (C-006);
no new authority/SSOT (C-001).
**Scale/Scope**: ~10 route-sites + ~2 static composes + 1 seam extraction (~10 adoption sites) + 1 ratchet
extension + 2 verify-and-close. Bounded.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* — Charter present
(`.kittify/charter/charter.md`, compact mode).

- **Canonical sources / no-improvise (DDD canonical seam):** ✅ PASS — the mission *adopts* the existing
  seam and explicitly forbids building a parallel one (C-001). This is the charter principle made literal.
- **Terminology Canon (Mission not feature; status commit not ceremony):** ✅ PASS — no domain renames;
  prose uses canonical terms. (kitty-specs/ is exempt from the guard, but the prose complies anyway.)
- **Tiered coding standards / Sonar:** ✅ PASS by design — pure routing + small seam extraction; ruff +
  mypy clean, complexity ≤ 15, no suppressions (C-006); every new branch/helper gets a focused test.
- **Test integrity (never delete a test to pass; behavioral over structural):** ✅ PASS — function-over-form
  + verification-by-deletion is the core test discipline; the only form-coupled test is the ratchet, by design.

No charter violations → **Complexity Tracking is empty**.

## Project Structure

### Documentation (this mission)

```
kitty-specs/naming-identity-routing-rider-01KV7SFD/
├── plan.md              # This file
├── research.md          # Phase 0 — verified call-site inventory + C-002 resolution
├── data-model.md        # Phase 1 — identity value-objects & seam entities
├── quickstart.md        # Phase 1 — verification scenarios (deletion + ratchet)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

(No `contracts/` — this mission ships no API/event surface; it is an internal routing/adoption refactor.)

### Source Code (repository root)

```
src/specify_cli/
├── lanes/branch_naming.py        # THE SEAM — failover-aware resolve_* entrypoints (consumed; edited only by IC-05 option (b))
├── dashboard/scanner.py          # route via resolve_mid8 → `or None` (IC-02) + ratchet coverage (IC-01)
├── status/aggregate.py           # route via resolve_mid8 (returns "" ) (IC-02)
├── git/sparse_checkout.py        # route via mid8() — guaranteed-full id (IC-02)
├── cli/commands/doctor.py        # route ×2 — already try/except, conscious decision (IC-02)
├── cli/commands/implement.py     # route fallback (IC-02)
├── cli/commands/agent/mission.py # route raw_mid[:8] (IC-02, scope-review addition)
├── cli/commands/agent/workflow.py# route mid[:8] (IC-02, scope-review addition)
├── cli/commands/mission_type.py  # route ..._id_meta[:8] (IC-02, scope-review addition)
├── doctrine_synthesizer/apply.py # route ×2 via mid8() (IC-02)
├── context/mission_resolver.py   # route via mid8() (IC-02)
├── core/mission_creation.py      # #2000 compose → mission_dir_name (IC-03)
├── core/worktree.py              # #2000 compose ×2 → worktree_dir_name (IC-03)
├── core/paths.py                 # locate_project_root authority — verify only (#1971-tail, IC-04)
└── ownership/validation.py       # #1888 real existence-check fix (IC-04)
src/runtime/next/_internal_runtime/retrospective_terminus.py  # route via mid8() (IC-02)
src/mission_runtime/resolution.py # route str(raw_mission_id)[:8] (IC-02, scope-review addition)
src/specify_cli/retrospective/generator.py                    # route mid[:8] (IC-02, scope-review addition)

tests/architectural/test_no_worktree_name_guess.py            # ratchet: AST short-id detector + bypass rule (IC-01/IC-05)
tests/ (behavioral)                                           # characterization + parity tests per IC
```

**Structure Decision**: Single project; the seam is consumed, not rebuilt. **IC-05 (option b) is the sole
owner of `branch_naming.py`** — it demotes `mid8()`→`_mid8` and makes `resolve_mid8` the only public door;
IC-02/IC-03 then route to that final shape. The lanes-path is already centralized in `persistence.py` —
**no `resolve_lanes_dir` is built** (it would violate C-001).

## Complexity Tracking

*No charter violations — none.*

## Ownership & sequencing (prevents `branch_naming.py` overlap)

- **`branch_naming.py` is consumed read-only by IC-02 and IC-03** (the failover-aware `resolve_*`
  entrypoints + `mission_dir_name`/`worktree_dir_name` already exist). It is **edited only by IC-05** (the
  `mid8` → `_mid8` demotion, option b) → **single source owner**. IC-02/IC-03 must land *after* IC-05's
  rename so they route to the final `resolve_mid8`/`_mid8` shape. No linearization conflict.
- **#2000 compose sites** (`core/mission_creation.py`, `core/worktree.py`) are IC-03's; the `lanes/recovery.py`
  two-WP collision is **gone** (IC-03 no longer touches lanes).
- **`ownership/validation.py`** is IC-04's alone (#1888 fix).
- **`dashboard/scanner.py`** is touched by IC-02 (route the derivation) and IC-01 (ratchet *test* only,
  in `tests/`) — no source-file overlap.
- Suggested order: **IC-01 first** (lands the tripwire + the bypass rule with the full allow-list, so every
  later routing WP proves itself by *removing* its allow-list entry), then **IC-05** (settle the failover
  entrypoint so IC-02 routes to the final target), then IC-02 / IC-03 in parallel, then IC-04 (independent).

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

> **IC map revised 2026-06-16 after the adversarial scope review**
> (`scope-review/SCOPE-REVIEW-SYNTHESIS.md`). IC-03 retired (the #1993 lanes-dir seam was a C-001
> violation / non-problem → deferred); IC-03 now carries #2000 compose-routing; IC-04 promotes #1888 to a
> real fix; IC-01/IC-02 resized. The `lanes/recovery.py` two-WP collision is gone.

### IC-01 — Identity ratchet tripwire (architectural-consistency)

- **Purpose**: add a **new AST short-id slice detector** to the ratchet (it currently detects name
  *composes*, not slices), covering bare mission-`mid8` slices repo-wide **including
  `dashboard/scanner.py`**, on a name allow-list that **shrinks** as sites are routed. This is real new
  test code, not a one-line tweak. The detector also encodes the **failover-bypass rule** (FR-010): a
  correctness-path mid8 derivation that does NOT go through the failover-aware entrypoint
  (`resolve_mid8`/`resolve_transaction_mid8`) is a finding — bare `mid8()`/`mission_id[:8]` on a
  correctness path is the bypass the ratchet now forbids.
- **Relevant requirements**: FR-004, FR-010, NFR-003, SC-001, SC-005.
- **Affected surfaces**: `tests/architectural/test_no_worktree_name_guess.py` (test only).
- **Sequencing/depends-on**: lands first; the allow-list is the IC-02 routing checklist.
- **Risks**: AST cannot distinguish `mission_id` from `invocation_id` → name allow-list, so `str(x)[:8]`/
  `mid[:8]`/`raw_mid[:8]` shapes are hard to catch — **verification-by-deletion is the real guarantee, the
  ratchet is a tripwire** (state this in the test). Must not trip on `invocation_id[:8]`. The honesty note
  must name the deferred `feature_dir.parent.parent` repo-root class (~9 sites) so SC-001 isn't over-read.

### IC-02 — Short-id route adoption (~15 sites, contract-aware)

- **Purpose**: route the **~15** live short-id shadow sites through the **failover-aware authoritative
  entrypoint** — `resolve_mid8` / `resolve_transaction_mid8` (FR-010), *not* bare `mid8()` — and **delete**
  the inline derivations (FR-009), preserving byte-parity via a **per-site contract table** (FR-008);
  verify `IdentityFragment` is the only context-held derivation (FR-002). Bare `mid8()` is reserved for
  sites with a guaranteed-full declared `mission_id` and no failover need (internal/seam use).
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-008, FR-009, FR-010, NFR-001, SC-002, SC-003.
- **Affected surfaces**: the 10 originally inventoried + the 5 scope-review additions:
  `mission_runtime/resolution.py:171` (`str(raw_mission_id)[:8]`), `cli/commands/agent/mission.py:772`
  (`raw_mid[:8]`), `cli/commands/mission_type.py:643` (`…_id_meta[:8]`), `cli/commands/agent/workflow.py:292`
  (`mid[:8]`), `retrospective/generator.py:112` (`mid[:8]`). Consumes `branch_naming.py` (no edit).
- **Contract landmines (use `resolve_mid8`/`or None`, NOT bare `mid8()`):** `status/aggregate.py:250` (`""`),
  `dashboard/scanner.py:438` (`None`), `doctor.py:3070/3162` (already `try/except` — conscious decision),
  `implement.py:386` (prefers `meta["mid8"]`). Safe for direct `mid8()`: `sparse_checkout.py`,
  `doctrine_synthesizer/apply.py:745/831`, `context/mission_resolver.py:163`, `retrospective_terminus.py:69`.
- **Sequencing/depends-on**: IC-01 (removes its allow-list entries as proof). Characterization test per
  contract-sensitive site **before** substitution (TDD, C-003).

### IC-03 — #2000 compose-routing (re-targeted)

- **Purpose**: route the real #2000 compose sites — `core/mission_creation.py:321`,
  `core/worktree.py:367/370` — through `mission_dir_name`/`worktree_dir_name`. (The defect is the
  *compose*; these already call `mid8()`.) **No lanes-dir seam** (#1993 deferred — lanes.json is already
  centralized in `persistence.py`; a `resolve_lanes_dir` would violate C-001).
- **Relevant requirements**: FR-005, NFR-001, NFR-004, SC-002, SC-004.
- **Affected surfaces**: `core/mission_creation.py`, `core/worktree.py`. Consumes `branch_naming.py`
  (the parser/compose functions exist at `branch_naming.py:771`+ — no new helper needed).
- **Sequencing/depends-on**: IC-01 (these sites are in the ratchet allow-list).
- **Risks**: byte-parity on the composed dir/branch names (NFR-001).

### IC-04 — Verify-and-close + the #1888 bug fix

- **Purpose**: (a) **#1971-tail verify-and-close** — confirm the `locate_project_root` chain converges on
  `core/paths.py` and add a regression test that **disproves the `SPECIFY_REPO_ROOT`/worktree split-brain
  the ticket asserts** (+ pin the benign `__init__.py` no-arg divergence); (b) **#1888 real fix** — add the
  missing **existence check** to `ownership/validation.py` (TDD: failing repro of the phantom-path pass
  first), retiring the silent-pass bug.
- **Relevant requirements**: FR-006, FR-007, SC-004.
- **Affected surfaces**: `ownership/validation.py` (+ its tests) for #1888; `core/paths.py` /
  `core/project_resolver.py` / `__init__.py` (verify only — do NOT touch the intentional deferred-import
  shims) + a regression test for #1971-tail.
- **Sequencing/depends-on**: none (independent of IC-02/IC-03; different files).
- **Risks**: #1888 is a behavioral change — TDD-first, and confirm the existence check doesn't reject
  legitimate not-yet-created paths (scope it to declared owned paths that must exist at validation time).

### IC-05 — Failover mechanic as the SSOT entrypoint (operator decision 2026-06-16 = option **b**)

- **Purpose**: make the 3.2.0 **canonical-first / legacy-failover-with-warning** mechanic the *single
  public door*. **Demote bare `mid8()` → internal `_mid8`**; `resolve_mid8` becomes the only public mid8
  entry (`resolve_transaction_mid8`/`resolve_mission_branch` the branch/transaction doors). IC-01's ratchet
  enforces the no-bypass rule. (Option (a) was declined in favor of the cleaner single-door SSOT.)
- **Relevant requirements**: FR-010.
- **Blast radius (verified — 6 bare `mid8()` callers):**
  - **Internal to the seam → rename to `_mid8`** (IC-05 owns): `branch_naming.py:206,257,473` + the def +
    drop `mid8` from `__all__` / keep `_mid8` private.
  - **The 2 #2000 composes** `core/worktree.py:367` + `core/mission_creation.py:321` — the `mid8()` call is
    *removed* by **IC-03** routing them through `worktree_dir_name`/`mission_dir_name` (do NOT also rename
    there — IC-03 deletes the call).
  - **1 consumer** `lanes/worktree_allocator.py:169` — routed to `resolve_mid8` by **IC-02**.
- **Affected surfaces**: `branch_naming.py` (sole owner — the only WP that edits the seam) +
  `tests/architectural/test_no_worktree_name_guess.py` (bypass rule, with IC-01).
- **Sequencing/depends-on**: lands **before IC-02/IC-03** so they route to the final `_mid8`/`resolve_mid8`
  shape; settle with IC-01 so the ratchet encodes the final door.
- **Risks**: preserve the one-shot `DeprecationWarning` + `reset_legacy_failover_warning` test seam;
  byte-parity; ensure `resolve_mid8("", mission_id=full_id)` covers the mission-id-only callers (it does —
  empty slug ⇒ no embedded tail ⇒ returns `mission_id[:8]`).

### IC-06 — Command-contract-drift guard (#2007 Focus A, folded in by operator decision 2026-06-16)

- **Purpose**: stop agents probing nonexistent CLI surfaces — a sibling architectural-consistency guard to
  IC-01's ratchet. (a) Repoint the **15 drifted SOURCE references**; (b) add the **command-snippet CI
  guard**; (c) fix the reproducing surface hints (#13 → `doctor workspaces --fix`; #16/#1891 contract
  doc/reword).
- **Relevant requirements**: FR-011, FR-012, FR-013, SC-006.
- **Affected surfaces**: SOURCE only — `src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md` (11
  hits), `src/doctrine/skills/spec-kitty-mission-system/SKILL.md` (1), `src/doctrine/missions/mission-steps/
  software-dev/plan/prompt.md` (3 behavioral); `tests/architectural/test_docs_cli_reference_parity.py` +
  `scripts/docs/_typer_walker.py` reuse (the guard). **No overlap** with IC-01..IC-05 source files.
- **Sequencing/depends-on**: independent of the routing ICs (different files); can land in parallel. The
  guard's allow-list starts empty (ratchet) once the 15 repoints land.
- **Risks**: false positives on placeholder snippets (`<mission>`, `…`) and valid bool auto-negation
  (`--no-mark-loaded`) — path-level validation first (catches all 12 hard hits), flag-level as a
  follow-on tier with the false-positive budget. Edit SOURCE templates, never the generated agent copies.
- **Explicitly NOT here**: adding `--json` to `agent action implement/review` (a code-contract change) and
  the #2007 **read-path/error-fidelity adoption** class (#4/#8/#12/#14/#15) — both are the **next focus's**
  own mission, not this guard.

## Phase 0 — complete (+ adversarial scope review)

`research.md` + `scope-review/SCOPE-REVIEW-SYNTHESIS.md`: verified inventory; `coordination/`-already-routed
and `locate_project_root`-already-consolidated upheld; **#1993 lanes-dir bet retired** (C-001 violation /
non-problem → deferred to a follow-on mission); **+5 missed sites**; **#2000 re-targeted**; **#1888 promoted to a real
fix**; **#1899-tail (phantom) / #1900 (deferred) dropped**; operator directive folded in as **IC-05**
(failover mechanic as the formal entrypoint).

## Phase 1 — complete

`data-model.md` (identity value-objects + the failover-aware entrypoints) and `quickstart.md`
(verification scenarios: behavioral parity, verification-by-deletion, ratchet allow-list shrink +
failover-bypass, #1888 repro, #1971-tail split-brain test). No `contracts/` (no external surface).

## Post-design Charter re-check

No new gaps — the plan only *consumes* the existing seam, formalizes its failover entrypoint, adds one
architectural test, one bug fix, and compose-routing. **C-001 is strengthened** by retiring the
`resolve_lanes_dir` second-authority idea. Gates still **PASS**.

## Brownfield pre-tasks checks (standing gate, recorded 2026-06-16)

- **Split-brain / LOC scan:** this mission *reduces* split-brain (its whole point); it introduces none.
  `doctor.py` (3319 LOC) and `implement.py` (1356) are pre-existing god-modules but are touched **only**
  by one-line routing edits (doctor.py:3070/3162, implement.py:386) — **do not expand them**; their split
  is a separate tracked concern (#1623-class), explicitly out of scope. The seam `branch_naming.py` (845)
  is consumed, healthy.
- **Due-deprecation check:** `branch_naming.py`'s legacy-failover `DeprecationWarning` is the
  **intentional** canonical-first/legacy-failover-with-warning pattern (3.2.0 mission) — **keep**. One
  adjacent due-ish deprecation **flagged but NOT folded**: `implement.py:891` `--feature` hidden alias
  belongs to the **#1060** internal-`--feature` retirement (partial) — folding it would expand this
  bounded rider and muddy the surface; leave it to #1060. The `runtime/next/` shim deprecations
  (`decision.py`, `_runtime_pkg_notice.py`) are the 3.3.0 shared-package-boundary removal, not touched here.
- **Foldable-issue search:** the fold set (#2000/#1971/#1993/#1888/#1900/#1899-tail) is settled by the
  prior tracker sweep; the Phase 0 inventory surfaced **no new foldable issues**. The deferred set
  (#1832/#1716/#1827/#1619/#1891) stays deferred per C-005.

## Branch contract (restated)

Current branch: `feat/naming-rider-3-2-1`. Planning/base branch: `feat/naming-rider-3-2-1` (stacked on
the doc-only `design/naming-identity-ssot-alignment`). Lane worktrees merge into `feat/naming-rider-3-2-1`;
that branch is PR'd to `main`. `branch_matches_target` = true.

## Next

`/spec-kitty.tasks` — decompose the **six** ICs into work packages, sequenced **IC-05 → IC-01 → {IC-02,
IC-03} → IC-04**, with **IC-06 parallel** (independent files): IC-05 demotes `mid8`→`_mid8` (sole
`branch_naming.py` owner); IC-01 ratchet + bypass rule; IC-02 ~15-site routing via `resolve_mid8` +
contract table; IC-03 #2000 compose-routing (removes 2 `mid8()` calls); IC-04 #1971-tail verify-close +
#1888 fix; IC-06 #2007-Focus-A command-drift guard (SOURCE repoints + snippet CI guard). Only IC-05 edits
`branch_naming.py`; IC-06 touches only doctrine SOURCE + the docs-parity test.
