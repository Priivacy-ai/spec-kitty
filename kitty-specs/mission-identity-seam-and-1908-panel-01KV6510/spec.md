# Mission Specification: Mission-identity naming seam & #1908 panel hardening

**Mission ID**: `01KV6510YXX3HM222Y0YG5JY3M`
**Slug**: `mission-identity-seam-and-1908-panel-01KV6510`
**Type**: software-dev
**Addresses**: Cluster A — #1978, #1949, #1918, #1899 (epic #1868); Cluster B — #1915, #1917, #1916 (post-#1908 panel; meta-tracker #1929)

## Purpose

Two correctness/robustness clusters surfaced by adversarial review:

1. **Mission-identity naming seam (Cluster A).** The `slug ↔ mid8 ↔ branch/worktree-name`
   mapping is reimplemented ad-hoc in several places, each with its own
   idempotency or parsing bug. The now-closed #1860 was the *same* wrong-compose
   class on the status-read path — a recurring regression that signals a missing
   single authority. One of these bugs (#1978) currently **blocks `spec-kitty
   merge`**. Bind the mapping to one canonical seam (compose + parse, idempotent)
   and route the broken call sites through it.
2. **Post-#1908 panel hardening (Cluster B).** Three discrete robustness findings
   from the PR #1908 adversarial panel (tracked via the #1929 meta-checklist):
   lane-merge atomicity, base-ref argument hygiene, and an accept-gate identity
   side-effect. Each is a self-contained TDD fix.

> **Dogfooding note (drives sequencing):** this mission's own slug ends in its
> mid8 (`…-01KV6510`), so its own merge is exactly the #1978 case. #1978 is
> therefore the first/priority fix, and the mission may need a manual merge if it
> lands before #1978 is verified.

## Scope

### In scope
- **Cluster A — canonical seam (FULL consolidation, per paula-patterns review):**
  one authority in `lanes/branch_naming.py` that composes **and** parses branch,
  lane, **and worktree/coordination dir** names, keyed on the declared
  `(slug, mission_id)`, idempotency-preserving (a slug already embedding its mid8
  is left as-is — no strip-reappend churn). **Every** ad-hoc compose/parse site
  routes through it (no name-guessing f-strings). The seam bugs are fixed in place
  and the parallel implementations are unified:
  - compose idempotency — `mission_branch_name`/`_required` (#1949).
  - parse safety — `mid8_from_slug` **demoted to non-authoritative** detector;
    correctness paths pass `mission_id` (#1918, see FR-004).
  - worktree dir-name grammar `worktree_dir_name()` == `lane_branch_name(...)`
    minus the `kitty/mission-` prefix (single derived grammar) + a `worktree_path()`
    emit-don't-guess helper; **literal-ban** ratchet (#1899/FR-005).
  - **route ALL leak sites** through the seam (paula F-1/F-2/F-5): merge preflight
    + `cli/commands/merge.py` (#1978), `runtime/next/runtime_bridge.py` (false
    compose), `lanes/{worktree_allocator,merge,recovery,lifecycle_sync,implement_support}`,
    `workspace/context.py`, `orchestrator_api/commands.py`, `cli/commands/agent/tasks.py`,
    and the **parallel coordination impls** `coordination/{workspace._compose_mission_dir,
    transaction._mission_specs_dir_name, status_transition._transaction_dir_name,
    surface_resolver._coord_mid8}` (FR-010).
- **Cluster B — discrete fixes:**
  - `lanes/worktree_allocator.py::_merge_dependency_lane_tips` atomicity — #1915.
  - `cli/commands/implement.py` `_validate_base_ref` `--` separator — #1917.
  - accept-gate `ensure_identity` moved off the readiness path; retire the
    `_filter_accept_owned_project_config` stopgap — #1916.

### Out of scope
- The broader coord/main/lane execution-context unification (#1619/#1716) beyond
  what the naming seam requires.
- `lanes.json` schema changes beyond honoring the canonical `mission_branch`.
- Renaming the `mid8`/`mission_id`/`mission_slug` domain terms (identity model is
  fixed by mission 083; this mission only fixes the name *derivation/parsing*).
- Re-parenting/closing #1929 (it stays a meta-checklist).

## User Scenarios & Testing

**Primary actor:** a Spec Kitty operator / the runtime invoking merge, lane
allocation, accept, and worktree/branch resolution.

- **Scenario — merge a mid8-embedded mission (happy path, #1978):** operator runs
  `spec-kitty merge` on a mission whose slug already ends in its mid8 (like THIS
  mission). Trigger: preflight resolves the mission branch. Outcome: preflight
  uses the canonical `mission_branch` (`kitty/mission-<slug>-<mid8>`, or the
  already-embedded form) and finds the real branch — merge proceeds (today it
  false-negatives and blocks).
- **Scenario — compose a branch for an embedded slug (#1949):** `mission_branch_name(slug, mission_id)`
  where `slug` already ends in `mid8`. Outcome: the name is **not** double-appended
  (`…-<mid8>`, not `…-<mid8>-<mid8>`); composing then parsing round-trips.
- **Scenario — parse a coincidental slug (#1918):** `mid8_from_slug` on a modern
  slug whose final hyphen-segment is coincidentally 8 Crockford-base32 chars but
  is not a real mid8. Outcome: it does not falsely resolve; the dual-era heuristic
  raises/declines rather than returning a wrong mid8.
- **Scenario — worktree name twin (#1899):** worktree dir-name composition/parse
  obeys the same seam grammar; a 4th ratchet assertion guards it.
- **Scenario — multi-dependency lane merge rollback (#1915):** a lane with ≥2
  dependency lanes where an earlier dep merges clean and a later dep conflicts.
  Outcome: the rollback leaves the lane at its pre-merge state (no orphaned
  earlier-dep merge commit survives).
- **Scenario — base-ref arg hygiene (#1917):** `implement --base=--something`.
  Outcome: `git rev-parse --verify` receives the value after a `--` separator, so
  a leading-dash value is treated as a ref, not an option.
- **Scenario — accept readiness is side-effect-free (#1916):** `spec-kitty accept
  --no-commit` (readiness) on a project with no minted identity. Outcome: it does
  **not** write `.kittify/config.yaml` (no `ensure_identity` side effect, no
  dirtied tree); identity minting happens only on a write-authorized boundary.

### Rules / invariants
- **Round-trip (keyed on declared identity):** for any `(slug, mission_id)`,
  `compose` is a fixpoint and round-trips; the declared `mission_id` is the
  authority, the embedded tail is only confirmation (matches → idempotent; mismatch
  → fail-closed/decline). The bare-string `mid8_from_slug` is heuristic and never
  authoritative on a correctness path (paula F-3).
- **Canonical-first failover:** the resolver tries new-style resolution first and
  fails over to legacy (`NNN-`/bare) only on a miss, with a one-shot deprecation
  warning (FR-004). The legacy path is a warned compatibility branch, not a
  co-equal parser — so resolution stays deterministic across the dual era.
- **Single authority:** branch/lane/worktree/coordination-dir name composition and
  parsing have exactly one implementation (`branch_naming.py`); no call site
  re-derives names locally and no parallel algorithm exists (incl. `coordination/`).
- **Readiness is side-effect-free:** readiness/`--no-commit` paths MUST NOT mint or
  persist state (the canonical rule generalizing #1916; paula F-6).
- **TDD-first:** each bug gets a failing regression/repro test committed before
  its fix (these are defects).
- **Bounded surface:** changes confined to the naming seam module + the listed
  call sites (merge preflight, worktree allocator, implement base-ref, accept
  gate); no edits to unrelated runtime/status hot paths.

## Domain Language
- **mid8** — first 8 chars of the ULID `mission_id`; branch/worktree disambiguator.
- **mission_slug** — human kebab slug; may or may not already embed the mid8.
- **canonical branch** — `kitty/mission-<slug>-<mid8>` (the form recorded in
  `lanes.json.mission_branch`); when the slug already ends in `<mid8>` the
  embedded form is canonical (no double suffix).
- **naming seam** — the single authority that composes/parses branch + worktree
  names from `(slug, mid8)`.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A single canonical seam MUST compose AND parse branch, lane, and worktree/coordination-dir names, keyed on the declared `(slug, mission_id)`, idempotency-preserving (a slug already embedding its mid8 is left as-is). ALL compose/parse call sites MUST route through it — no ad-hoc f-strings or duplicate algorithms. | Draft |
| FR-002 | The merge mission-branch resolution (`cli/commands/merge.py` fallback + the preflight) MUST resolve via `mission_branch_name_required(slug, mission_id)` (which fail-closes), not a `kitty/mission-{slug}` f-string that drops `-{mid8}`, so merge no longer false-negatives for mid8-embedded slugs (#1978). `runtime/next/runtime_bridge.py`'s identical false-compose MUST be fixed the same way. | Draft |
| FR-003 | `mission_branch_name()`/`_required` MUST be idempotent: when the slug already carries its mid8 it MUST NOT double-append; strip-then-reappend is allowed only when the embedded tail matches `mission_id[:8]` (#1949). | Draft |
| FR-004 | The canonical reader/resolver MUST use **canonical-first, legacy-failover** logic: try the new style (declared `mission_id` / `slug+mid8`) first; only if that misses fall over to legacy (`NNN-`/bare) parsing, emitting a **one-shot deprecation warning** that nudges migration. `mid8_from_slug` is demoted **in place** to a best-effort, non-authoritative detector that declines on a coincidental 8-char tail with no `mission_id` rather than mis-resolving (#1918); an **authoritative** `resolve_mid8(slug, *, mission_id)` MUST be added for correctness-path use, and **all ~12 `mid8_from_slug` callers MUST be audited and routed** — value-uses to `resolve_mid8`, pure boolean-detector uses kept only where provably correct under the stricter decline. The two existing final-fallback consumers (`resolve_transaction_mid8`, `coordination.surface_resolver._coord_mid8`) MUST NOT newly fail-close for a genuine embedded-mid8 slug. | Draft |
| FR-005 | A `worktree_dir_name()` (and an emit-don't-guess `worktree_path()`) MUST be added to the seam. It MUST reproduce the **current** on-disk grammar exactly in BOTH modes — `mission_id=None` ⇒ legacy `{slug}-{lane}` (no mid8 appended, matching today's `f"{mission_slug}-{lane_id}"` call sites), `mission_id` present ⇒ the embedded `{slug}-{mid8}-{lane}` form — so routing causes **no on-disk worktree churn** for any mission, not only mid8-embedded slugs. A shared **golden-value name table** (one canonical `(slug, mission_id, lane_id)` → expected branch / lane-branch / worktree-dir / coord-dir / coord-branch) MUST be the binding byte-identical assertion shared by all routing WPs. A **literal-ban** ratchet MUST fail any name-guess outside the seam (#1899). | Draft |
| FR-010 | **Exactly one algorithm** MUST exist for the grammar. ALL parallel compose/parse/derive implementations MUST delegate to the seam: in `coordination/` (`workspace._compose_mission_dir`, `transaction._mission_specs_dir_name`, `status_transition._transaction_dir_name`, `surface_resolver._coord_mid8`) AND in `missions/` (`_create.coordination_branch_name` — the LIVE coord-branch composer run at every `mission create`, with its own `endswith` dedup — and `_read_path_resolver._compose_mission_dir` / `feature_dir_resolver`). The seam MUST expose a bare `<slug>-<mid8>` mission-dir primitive + coord-branch/coord-dir derivations so these have a real (non-lane-suffixed) delegation target (paula F-2; squad-verified gaps). | Draft |
| FR-006 | `_merge_dependency_lane_tips` MUST be atomic across multiple dependency lanes: if a later dep merge conflicts, the lane MUST be rolled back fully (no earlier-dep merge commit survives) (#1915). | Draft |
| FR-007 | `_validate_base_ref` MUST pass the `--base` value to `git rev-parse --verify` after a `--` end-of-options separator so a leading-dash value is treated as a ref (#1917). | Draft |
| FR-008 | The accept `--no-commit`/readiness path MUST NOT call `ensure_identity` (no `.kittify/config.yaml` write side effect); identity minting moves to a write-authorized boundary and the `_filter_accept_owned_project_config` stopgap is retired (#1916). | Draft |
| FR-009 | Each fix MUST be preceded by a committed failing regression test that reproduces the defect (TDD-first). | Draft |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | Conflict surface is the naming-seam consolidation set (intentionally cross-cutting per full-consolidation scope), NOT unrelated hot paths. | Diffs limited to: `lanes/branch_naming.py`; the routed call-site files (`lanes/{worktree_allocator,merge,recovery,lifecycle_sync,implement_support,compute}`, `cli/commands/{merge,implement,decision,agent/tasks,agent/mission,agent/workflow,agent/status,agent/context}.py`, `runtime/next/runtime_bridge.py`, `workspace/context.py`, `orchestrator_api/commands.py`, `coordination/{workspace,transaction,status_transition,surface_resolver}.py`, `missions/{_create,_read_path_resolver,feature_dir_resolver}.py`, `status/aggregate.py`); `acceptance/__init__.py` + `identity/project.py` + `sync/events.py` (Cluster B / readiness side-effect); and tests. **Zero** hunks in `status/` (other than `aggregate.py`) / `task_utils/` reducer/store internals — enforced by a diff-scan in WP09. | Draft |
| NFR-002 | No quality-gate regression. | `ruff`, `mypy`, and the full `tests/` suite pass with zero new issues; dead-symbol/ratchet baselines unchanged or reduced. | Draft |
| NFR-003 | The seam is verified by a round-trip/property test keyed on `(slug, mission_id)` (NOT bare strings — round-trip is unsatisfiable on the bare grammar, paula F-3). | A property test asserts `compose` is a fixpoint and round-trips for: embedded-tail==mid8(mission_id), embedded-tail≠mid8 (mismatch handling), coincidental-8-char-tail with no mission_id (detector declines), and legacy `NNN-` (no mid8). | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | TDD-first: never delete a test to pass; each fix lands with its failing-then-passing regression test (DIRECTIVE_003). | Active |
| C-002 | #1929 is a meta-checklist tracker — findings are parented under their functional epics (#1868/#1795/#1666/#1914), never under #1929. | Active |
| C-003 | PR-bound: lands via PR to `upstream/main`; never a direct push to `origin/main`. | Active |
| C-004 | Every addressed issue gets an issue-matrix row, a tracker comment naming this mission, and operator-assigned claim. | Active |
| C-005 | #1978 is sequenced early (this mission's own merge depends on it); be prepared to merge the mission manually if it lands first. | Active |

## Success Criteria
- SC-001: A mission whose slug embeds its mid8 (e.g. this one) merges via
  `spec-kitty merge` without a preflight false-negative.
- SC-002: Composing a branch/worktree name for an embedded slug yields no doubled
  mid8; the seam round-trips for embedded, non-embedded, and coincidental-8-char
  slugs.
- SC-003: A coincidental-8-char modern slug does not falsely resolve a mid8.
- SC-004: A multi-dependency lane merge that conflicts on a later dep leaves no
  orphaned earlier-dep merge commit.
- SC-005: `implement --base=--x` treats the value as a ref (no option injection).
- SC-006: `accept --no-commit` leaves the working tree clean (no identity write).
- SC-007: Full suite + ratchet/dead-symbol gates green; net change confined to the
  bounded surface.

## Key Entities
- **Naming seam module** — the single compose/parse authority.
- **Mission branch / worktree name** — derived artifacts of `(slug, mid8)`.
- **lanes.json `mission_branch`** — recorded canonical branch (authority for read).
- **Dependency-lane merge** — the atomic unit #1915 hardens.

## Assumptions
- The canonical branch convention is `kitty/mission-<slug>-<mid8>`, with the
  embedded form canonical when the slug already ends in `<mid8>` (per #1978/#1949).
- `lanes.json.mission_branch` is the recorded source of truth for the mission
  branch at merge time.
- The mission identity model (mid8/mission_id/mission_slug, mission 083) is fixed;
  only name derivation/parsing is in scope.

## Dependencies
- Epic #1868 (canonical seams) for Cluster A; functional epics #1795/#1666/#1914
  for Cluster B; meta-tracker #1929. Builds on the closed #1860 (same class) and
  the #1908 adversarial panel.
- **Advances #1878** (complete the coordination placement/identity strangler): the
  full-consolidation scope (paula F-2) routes the `coordination/` parallel
  compose/parse impls through the seam — this mission delivers the
  identity-naming-seam slice of that strangler. Reference #1878; do not close it.
