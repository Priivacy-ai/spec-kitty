# Collapse Boundary-Integrity Blueprint — `status/aggregate.py` `CoordAuthorityUnavailable` convergence

**Author:** architect-alphonso · **Date:** 2026-06-21
**Mission:** `mission-surface-resolver-safety-net-01KVN754` (the #2040 strangler-finish / R3 collapse)
**Scope:** adjudicate the ADR-deferred hard boundary — the aggregate's `CoordAuthorityUnavailable`
translation — under the operator's binding Option B decision (coord-empty → loud primary fallback).
**Governing ADR:** `architecture/3.x/adr/2026-06-19-1-coord-empty-surface-fallback.md` (amended to B, 2026-06-21).

> Verified against source on branch `feat/mission-surface-resolver-safety-net`:
> `src/specify_cli/status/aggregate.py`, `src/specify_cli/coordination/surface_resolver.py`,
> `src/specify_cli/missions/_read_path_resolver.py`, `src/mission_runtime/resolution.py`,
> `src/specify_cli/cli/commands/agent/status.py`, and the public-contract tests
> (`tests/status/test_aggregate_surface_resolution.py`,
> `tests/specify_cli/missions/test_handle_equivalence_matrix.py`,
> `tests/missions/test_surface_resolution_equivalence.py`).

---

## TL;DR — the decision that shapes the re-spec

**Recommendation 1 = (a) CONVERGE, but it is a *narrowed* convergence that Option B makes nearly free.**

Under Option B the aggregate's `CoordAuthorityUnavailable`-for-**coord-empty** **disappears at its
own source**: the resolver no longer raises a fail-closed signal for coord-empty (it returns the
primary dir + a loud warning), so there is *nothing left for the aggregate to translate* in that
state. The aggregate's `_resolve_read_dir` simply receives a primary directory and returns it — the
`except StatusReadPathNotFound -> CoordAuthorityUnavailable` arm is never entered for coord-empty.

What survives is **coord-deleted only** (`CoordinationBranchDeleted`, #1848 — stays hard-fail by
operator decree). For that single remaining state the aggregate still translates the resolver's
fail-closed signal. The decision therefore reduces to: *what does the aggregate raise for
coord-deleted, and does that one cell drain the equivalence matrix?*

**Adopt: converge the aggregate onto the resolver's typed error for the coord-deleted hard-fail**
— let `MissionStatus.load` **propagate `CoordinationBranchDeleted` (carrying
`error_code == "COORDINATION_BRANCH_DELETED"`) unchanged**, rather than wrapping it in the
error-code-less `CoordAuthorityUnavailable`. Keep `CoordAuthorityUnavailable` as a **retained,
still-exported** boundary type for the genuinely-aggregate-specific failure (`MissionMetadataUnavailable`
is already separate; the slug guard is separate) but stop manufacturing it from the resolver's
coord-deleted signal. This is the surgical change that drains the coord-deleted equivalence cells
**by aligning the error type, not by softening the hard-fail**.

This is feasible *because Option B removed the coord-empty cells from the equation* — convergence no
longer has to reconcile two different hard-fail states through one aggregate type. See §1 for the
per-cell drain table and the public-contract migration this requires.

---

## 1. Aggregate exception-type convergence — the central decision

### 1.1 What Option B does to the data flow (verified)

The translation seam lives at `aggregate.py:343-363` (`_resolve_read_dir`):

```python
try:
    resolved_dir = resolve_surface_dir_or_typed_error(repo_root, mission_slug, on_missing_meta=primary_candidate)
except StatusReadPathNotFound as exc:
    raise CoordAuthorityUnavailable(mission_slug=..., coord_candidate=exc.coord_candidate, primary_candidate=exc.primary_candidate) from exc
if is_under_worktrees_segment(resolved_dir) and not resolved_dir.exists():
    return primary_candidate
return resolved_dir
```

`resolve_surface_dir_or_typed_error` (`_read_path_resolver.py:514`) wraps `resolve_status_surface`,
which is the **single** authority where the coord-empty / coord-deleted decisions are made
(`surface_resolver.py:735` coord-empty → `CoordinationWorktreeEmpty`; `:716` coord-deleted →
`CoordinationBranchDeleted`). Both subclass `StatusReadPathNotFound`, so today **both** funnel into
the aggregate's single `except` arm and become `CoordAuthorityUnavailable`.

**Today the aggregate's `CoordAuthorityUnavailable` is reachable ONLY via the resolver's
`StatusReadPathNotFound` family** — i.e. exclusively for coord-empty and coord-deleted (the
create-window/no-coord/missing-meta paths all route through `on_missing_meta` → primary, never
raising). This is the load-bearing fact: `CoordAuthorityUnavailable` is *not* an independent
aggregate concept; it is purely a re-spelling of the resolver's two fail-closed states.

**Under Option B, coord-empty stops raising at `surface_resolver.py:735`.** The amended ADR is
explicit: coord-empty "stops raising `CoordinationWorktreeEmpty`/`STATUS_READ_PATH_NOT_FOUND` and
instead returns the primary dir + warning." Therefore:

- `resolve_status_surface` returns the **primary surface path** for coord-empty.
- `resolve_surface_dir_or_typed_error` returns that **primary directory**.
- `_resolve_read_dir` returns it; **the `except` arm is never entered for coord-empty.**
- `MissionStatus.load(...).read_dir` == primary dir for coord-empty. **No `CoordAuthorityUnavailable`.**

So the coord-empty half of the boundary collapses *for free* — the aggregate doesn't need a code
change to stop raising on coord-empty; it inherits the resolver's new behavior through the existing
delegator. **The only edit coord-empty forces on the aggregate is removing the now-dead assumption
in the docstrings/tests that coord-empty hard-fails** (see §3 MUST-NOT-regress and the test
migration below).

### 1.2 The residue: coord-deleted (stays hard-fail) — this is the whole remaining decision

For coord-deleted the resolver still raises `CoordinationBranchDeleted`
(`error_code = "COORDINATION_BRANCH_DELETED"`). It still arrives at the aggregate's `except
StatusReadPathNotFound` arm (the subclass relationship is unchanged) and is **still** wrapped to
`CoordAuthorityUnavailable` — which carries **no `error_code`**.

That wrap is exactly what keeps the `coord-deleted/slug-mid8` equivalence cell RED
(`_XFAIL_COORD_DELETED_SEAM_OUT_OF_SCOPE`): surface raises `CoordinationBranchDeleted /
COORDINATION_BRANCH_DELETED`, aggregate raises `CoordAuthorityUnavailable / None`. Type AND code
diverge.

### 1.3 The three options, scored

**Option (a) — CONVERGE the aggregate onto the resolver's typed error. [RECOMMENDED]**

Change `_resolve_read_dir` so the coord-deleted signal **propagates unchanged** instead of being
re-wrapped:

```python
try:
    resolved_dir = resolve_surface_dir_or_typed_error(repo_root, mission_slug, on_missing_meta=primary_candidate)
except CoordinationBranchDeleted:
    raise                      # coord-deleted hard-fail: propagate the resolver's typed error verbatim
except StatusReadPathNotFound as exc:
    # residual fail-closed (genuinely-missing surface with require-exists semantics, if any survive)
    raise CoordAuthorityUnavailable(...) from exc
```

- The aggregate now raises **`CoordinationBranchDeleted` (code `COORDINATION_BRANCH_DELETED`)** for
  coord-deleted — *identical type and code to the surface*. The hard-fail is **preserved** (operator
  constraint honored); only the *spelling* of the exception converges.
- `CoordAuthorityUnavailable` is **retained and still exported** (public API churn minimized) but is
  now only reachable for any residual `StatusReadPathNotFound` that is neither coord-empty (gone)
  nor coord-deleted (propagated). After Option B that residual is effectively empty in practice —
  but keeping the arm is defensive and avoids a `except`-removal that would change behavior on an
  unanticipated future fail-closed path. (A follow-on may delete it once proven dead; not this
  mission — see §4.)

**Cells (a) drains** (against the canonical `resolve_status_surface_with_anchor`):
- `coord-deleted/slug-mid8` — **drains** (surface `CoordinationBranchDeleted/COORDINATION_BRANCH_DELETED`
  now == aggregate `CoordinationBranchDeleted/COORDINATION_BRANCH_DELETED`). The third leg,
  `resolve_mission_read_path`, currently resolves to a **primary directory** for the slug-mid8
  coord-deleted case (per `_XFAIL_COORD_DELETED_SEAM_OUT_OF_SCOPE` live observation), so this cell
  needs the read-path leg fixed too — see the read-path note below.
- `coord-empty/slug-mid8` — **drains via Option B**, not via the aggregate edit: surface stops
  raising (returns primary dir), aggregate returns primary dir, read-path returns primary dir →
  all three agree on the **primary directory**. (The xfail constant
  `_XFAIL_COORD_EMPTY_SEAM_OUT_OF_SCOPE` is retired.)
- `coord-empty/bare` and `coord-deleted/bare` — **drain via Option B + the already-fixed #2046
  read-path mid8 cascade**: all three legs resolve the primary dir (the
  `_XFAIL_BARE_AGGREGATE_COORD_AUTHORITY_OUT_OF_SCOPE` divergence — aggregate raising while surface
  raised — disappears once neither surface nor aggregate raises on coord-empty; for coord-deleted
  bare the surface still raises `CoordinationBranchDeleted` and the aggregate now propagates the
  same, so they agree on the typed error, while read-path must also raise it — see read-path note).

> **Read-path leg caveat (load-bearing for full drain).** The differential gate compares THREE legs:
> `resolve_handle_to_read_path` (read-path), `resolve_status_surface_with_anchor` (surface),
> `MissionStatus.load` (aggregate). For the **coord-deleted** cells to drain to a typed-error match,
> the read-path leg must ALSO surface `CoordinationBranchDeleted` (or at least the same
> error_code under `require_exists=True`) rather than returning a primary directory. Today
> `resolve_handle_to_read_path` → `resolve_mission_read_path` does **not** consult branch existence,
> so coord-deleted resolves primary. **This mission must decide whether to teach the read-path leg
> the coord-deleted hard-fail** (a `_coord_branch_exists` check inside `_resolve_not_found`, gated
> on `require_exists`) — otherwise the coord-deleted cells drain on the surface↔aggregate pair but
> the read-path leg still diverges and the cell stays RED. **Recommendation: yes, fold the
> coord-deleted read-path check in** — it is the same hard-fail the resolver already implements; the
> divergence is purely that one of the three duplicate resolvers never learned it. This is squarely
> in the "collapse the duplication" remit of #2040 and is the difference between *draining* the
> coord-deleted cells and *re-documenting* them as xfail. The create-window invariant is unaffected
> (coord-deleted is `not coord_root.exists() and branch deleted`, orthogonal to the
> declared-but-unmaterialised create window which keeps a *live* branch).

**Option (b) — keep `CoordAuthorityUnavailable` as the aggregate boundary type, but give it the
matching `error_code` and directory so the cell drains without a type change.**

- Add `error_code = "COORDINATION_BRANCH_DELETED"` to `CoordAuthorityUnavailable` and carry it
  through. The equivalence gate asserts `type(a) is type(b) AND a.error_code == b.error_code`
  (`_assert_equivalent`, verified at test:210) — so **(b) does NOT drain any cell**: the *types*
  still differ (`CoordinationBranchDeleted` vs `CoordAuthorityUnavailable`). The gate is
  type-identity, not code-identity. (b) only helps if we *also* weaken the gate to compare codes
  only — which the test docstring explicitly forbids ("an assertion WP06 may not weaken").
- **Rejected.** It does not satisfy the gate, requires either a gate weakening (regression of the
  C-004 deletion safety net) or leaves the cells RED anyway. It also keeps two boundary types alive
  for one hard-fail state — the exact duplication #2040 is collapsing.

**Option (c) — leave coord-deleted cells as permanent documented xfails.**

- This is the *status-quo* outcome WP06 chose under the original hard-fail policy. It is defensible
  only if the aggregate seam is genuinely out of the mission's scope. **But the operator has pulled
  R3 collapse INTO this mission**, and the coord-empty half of the divergence evaporates under
  Option B, leaving only the coord-deleted spelling. Choosing (c) now would mean shipping the
  expanded-scope mission while leaving the one remaining, cheap, type-convergence cell undrained —
  under-reaching against the stated goal of finishing the strangler.
- **Rejected as the default**, but retained as the *fallback* if the read-path coord-deleted leg
  proves to carry hidden create-window risk during implementation (see §4). In that case the
  surface↔aggregate convergence still ships (Option a for those two legs) and only the read-path
  leg stays documented-xfail — a strictly smaller residue than today.

### 1.4 Net recommendation for (1)

Adopt **(a)**: under Option B, the aggregate stops manufacturing `CoordAuthorityUnavailable` from
the resolver's fail-closed signal. Coord-empty drains because the resolver no longer raises;
coord-deleted drains because the aggregate now **propagates** the resolver's `CoordinationBranchDeleted`
verbatim (hard-fail preserved, type/code converged). Fold the same coord-deleted check into the
read-path leg so all three entry points agree. Retain `CoordAuthorityUnavailable` as an exported
type for defensive residual fail-closed but stop using it as the coord-state translation.

**Public-contract migration this forces (must be in the same slice):**
- `cli/commands/agent/status.py` catches `(CoordAuthorityUnavailable, MissionMetadataUnavailable)`
  at three sites (`:165`, `:200`). Add `CoordinationBranchDeleted` to those `except` tuples so the
  CLI still fails closed with `typer.Exit(1)` and the structured message. `CoordinationBranchDeleted`
  already carries a rich `next_step`, so the operator message **improves** (names repair/flatten).
- `tests/status/test_aggregate_surface_resolution.py::test_coord_empty_is_a_separate_hard_fail_cell`
  (test:216) currently asserts `pytest.raises(CoordAuthorityUnavailable)` for coord-empty. Under
  Option B this **must invert** to assert `ms.read_dir == primary_dir` **and** that the loud warning
  fired. Rename to `test_coord_empty_resolves_primary_with_warning`.
- `tests/specify_cli/missions/test_handle_equivalence_matrix.py::test_fail_closed_window_yields_coord_authority_unavailable_for_all_handles`
  (test:588) — this fixture builds the **coord-empty** shape (coord root materialised, mission dir
  absent, primary declares coordination_branch). Under Option B it no longer yields
  `CoordAuthorityUnavailable`; it yields the primary dir + warning. Re-point it.
- Add a **new** aggregate test asserting `MissionStatus.load` raises `CoordinationBranchDeleted`
  (code `COORDINATION_BRANCH_DELETED`) for coord-deleted — the converged boundary contract.
- `tests/missions/test_surface_resolution_equivalence.py` — retire
  `_XFAIL_COORD_EMPTY_SEAM_OUT_OF_SCOPE`, `_XFAIL_BARE_AGGREGATE_COORD_AUTHORITY_OUT_OF_SCOPE`, and
  `_XFAIL_COORD_DELETED_SEAM_OUT_OF_SCOPE` as the corresponding cells go GREEN. **Do not** delete the
  `strict=True` machinery or weaken `_assert_equivalent` — the gate stays intact; only the per-cell
  xfail markers drop. (The `coord-empty` fixture `_build_topology` will now expect a *primary* dir
  outcome, not a typed error — update the matrix expectation, not the assertion shape.)

---

## 2. Option B's effect on the topology-authority model

### 2.1 The model shift

Before: **coord-as-sole-truth** for any coord-declared mission once the worktree root exists — a
materialised-but-empty coord was a *refusal*, because primary was presumed stale/split-brain.

After (Option B): **primary is a legitimate fallback authority for the coord-empty state,
conditioned on observability.** The model is now *tiered*:

1. **coord worktree materialised AND populated** → coord is sole truth (unchanged).
2. **coord declared, worktree NOT materialised** (create→first-write window) → primary authoritative,
   benign, silent (unchanged, #1718).
3. **coord declared, worktree materialised but EMPTY** (coord-empty) → **primary authoritative, but
   LOUD** (the new behavior). Liveness preserved; staleness made observable.
4. **coord declared, branch DELETED, worktree absent** (coord-deleted) → **hard-fail**, never primary
   (unchanged, #1848 — data loss).
5. **no coordination_branch** → primary sole truth (unchanged).

The unifying invariant the collapsed single resolver must encode:

> **INVARIANT (topology authority under Option B).** The status surface is the coord worktree's
> mission dir **iff** that dir exists on disk. Otherwise the primary checkout is authoritative —
> *unless* the declared coordination branch has been **deleted** from git (data-loss state), in
> which case the resolver fails closed (`CoordinationBranchDeleted`). When the primary checkout is
> selected as a *fallback* from a declared-coord topology whose worktree root is materialised but
> empty (state 3), the resolver MUST emit a structured, operator-visible warning at the fallback
> point. Silence is permitted only for the benign primary states (2 and 5).

This is a single boolean cascade — `coord_dir.exists()` → coord; else `branch_exists?` → (yes:
primary, +warning if root materialised; no: hard-fail). It lives **once**, in
`resolve_status_surface_with_anchor`, and every other leg consumes it (the C-004 collapse goal).

### 2.2 What MUST be preserved (the load-bearing distinctions)

- **create→first-write window resolves primary** (#1718). State 2 above. Guarded by
  `test_create_first_write_window_resolves_primary`,
  `test_unmaterialized_coord_create_window_resolves_primary`,
  `test_create_window_unmaterialized_coord_resolves_primary`. The aggregate's
  `is_under_worktrees_segment(dir) and not dir.exists()` gate (`aggregate.py:361`) is the
  call-site authority for this and MUST remain — Option B does not touch the *unmaterialised* path.
- **no-coord → primary** (state 5). Unchanged.
- **coord-deleted → hard-fail** (state 4). The operator's explicit non-softening constraint. The
  `_coord_branch_exists` rev-parse split (`surface_resolver.py:716`) is the load-bearing
  discriminator between state 3 (empty, now fallback) and state 4 (deleted, hard-fail). It must NOT
  be collapsed away when removing the coord-empty raise.
- **The loud warning is load-bearing and observable** (state 3). The amended ADR makes a test
  asserting the warning fires a binding requirement ("a test asserts it fires on the coord-empty
  path; the fallback must be observable, not best-effort"). The warning is **not** a `logging.debug`
  — it must be structured and operator-visible (the resolver currently emits *no* logging at all —
  `grep` confirms zero `logger`/`warn` in `surface_resolver.py` — so this is net-new infrastructure
  the mission must add; see §3).

---

## 3. What MUST NOT be deleted / regressed in the collapse

1. **The C-004 differential equivalence gate itself.** `_assert_equivalent`'s type-AND-code identity
   (`test:203-221`) and the `strict=True` xfail machinery (`_apply_xfail`) are the regression net for
   the whole strangler. Drain *cells* (drop xfail markers as they go GREEN); never weaken the
   assertion shape or convert a cell to `pytest.skip`. A premature green must still XPASS-fail.
2. **The #1718 create→first-write window → primary invariant.** Three named tests guard it. Option B
   touches *coord-empty* (worktree materialised), NOT the create window (worktree absent). Do not let
   a warning-emission refactor leak into the unmaterialised path.
3. **The coord-deleted hard-fail (`CoordinationBranchDeleted`, #1848).** Operator-binding. The
   `_coord_branch_exists` discriminator and the `not coord_root.exists()` guard must stay. The
   `error_code = "COORDINATION_BRANCH_DELETED"` distinct routing key must survive (it is how callers
   route the data-loss recovery).
4. **The lenient acceptance-lane carve-out (FR-010 guard-blessed).** The amended ADR §"Stale
   reference correction" records that `acceptance` *deliberately* retains the lower
   `resolve_mission_read_path` with an explicit mid8 — "the lenient acceptance-lane carve-out,
   blessed by the FR-010 selection guard." The collapse MUST NOT route the acceptance lane through
   the hard-failing surface; doing so would break acceptance reads. Preserve the carve-out and its
   guard entry.
5. **The loud-warning observability (state 3).** Net-new: the resolver emits no logging today. The
   mission must add a structured warning at the coord-empty fallback point AND a test that asserts it
   fires (binding per the amended ADR). Losing the warning silently re-introduces the #1589/#1821
   split-brain hazard the original hard-fail feared — the warning is the *entire* justification for
   reversing to fallback. It is not optional polish.
6. **`CoordAuthorityUnavailable` as an exported public symbol** (`status/__init__.py:147,209`).
   Even under convergence, keep the type exported and the CLI `except` tuples catching it (alongside
   the newly-propagated `CoordinationBranchDeleted`) so downstream importers and the `agent status`
   CLI do not break. We are changing *when it is raised*, not deleting the symbol — a symbol deletion
   would be a separate, larger breaking change (see §4).
7. **The single-resolution invariant (FR-036, #1772).** The collapse must not re-introduce a second
   resolution pass; coord-empty fallback returns the already-resolved primary anchor, it does not
   re-invoke the coord-aware resolver.

---

## 4. Residual genuinely-deferred items — do NOT pull these in

1. **Deleting `CoordAuthorityUnavailable` entirely.** Convergence makes it *nearly* dead (only a
   defensive residual `except StatusReadPathNotFound` arm keeps it). Proving that arm is unreachable
   and removing the symbol + its CLI handlers + its three public-contract tests is a separate
   breaking-API change with its own deprecation surface. **Defer to a follow-on** that owns a public
   API deprecation window. Pulling it in now risks an under-tested symbol removal mid-collapse.
   *Reason:* the value of this mission is the *behavioral* convergence (coord-empty fallback +
   coord-deleted type alignment); symbol cleanup is orthogonal churn.

2. **Re-routing the `acceptance` lane onto the unified surface resolver.** The FR-010-blessed lenient
   carve-out is deliberate. Collapsing it is a *policy* change about how strict acceptance reads
   should be, not a duplication-removal. **Out of scope.** *Reason:* it is a separate guarded decision
   with its own guard entry; touching it would expand the blast radius beyond the resolver collapse.

3. **The `mission_runtime.resolution` boundary's own error taxonomy.** The runtime boundary
   translates the read-path leg's `error_code` to `ActionContextError` (`resolution.py:186-197`),
   already preserving codes (the `runtime-boundary` equivalence cell is GREEN). If the read-path leg
   learns coord-deleted (recommended in §1.3), the runtime boundary will automatically surface
   `ActionContextError(code="COORDINATION_BRANCH_DELETED")` — **no runtime change needed**, and no
   new runtime taxonomy work. Do NOT open the runtime boundary's exception model in this mission.
   *Reason:* it already does the right thing by construction; touching it is gratuitous.

4. **The #2046 read-path mid8 cascade for bare slugs.** Already **closed and fixed** (amended ADR
   §"Stale reference correction"; the four `coord-*/bare` cells are now its regression guard, not
   open work). This mission *verifies* it via the differential characterization test; it does not
   re-implement it. *Reason:* re-doing closed work is waste; the cells are characterization, not
   construction.

5. **Broadening the warning to a generic staleness-detection framework.** The amended ADR scopes the
   loud warning to **coord-empty only**. Do not generalize it into a cross-topology staleness monitor
   or add warnings to the benign primary states (2, 5) — that would be noise and scope creep.
   *Reason:* the ADR's scope is explicit and binding ("Applies to the coord-empty state only").

---

## Appendix — verified equivalence-cell state transitions (canonical = `resolve_status_surface_with_anchor`)

| Cell (topology \| handle)        | Today (pre-Option-B)                                                  | After this mission (Option B + Rec 1a)                                  | Drains? |
|----------------------------------|-----------------------------------------------------------------------|------------------------------------------------------------------------|---------|
| no-coord/bare, /slug-mid8        | GREEN (primary dir)                                                    | GREEN (unchanged)                                                      | n/a     |
| coord-fresh/*, coord-behind/*    | GREEN (coord dir, except mid8-blind bare already fixed)               | GREEN (unchanged)                                                      | n/a     |
| create→first-write               | GREEN (primary)                                                       | GREEN (unchanged — #1718 preserved)                                    | n/a     |
| **coord-empty/slug-mid8**        | RED: surface `CoordWorktreeEmpty`/SRPNF, agg `CoordAuthUnavail`/None  | **GREEN: all three → primary dir + warning**                          | **yes** |
| **coord-empty/bare**             | RED: agg `CoordAuthUnavail` while surface raises                      | **GREEN: all three → primary dir + warning**                          | **yes** |
| **coord-deleted/slug-mid8**      | RED: surface `CoordBranchDeleted`, agg `CoordAuthUnavail`, rp→primary | **GREEN: surface+agg `CoordBranchDeleted`; rp must learn it too**     | **yes\*** |
| **coord-deleted/bare**           | RED: agg `CoordAuthUnavail` while surface raises                      | **GREEN: surface+agg `CoordBranchDeleted`; rp must learn it too**     | **yes\*** |
| ambiguous-mid8, runtime-boundary | GREEN                                                                  | GREEN (unchanged)                                                      | n/a     |

`*` coord-deleted cells drain **iff** the read-path leg also surfaces `CoordinationBranchDeleted`
under `require_exists=True` (the §1.3 read-path note). If implementation reveals create-window
risk in that leg, fall back to Option (c) for the read-path leg ONLY — surface↔aggregate still
converge, leaving a strictly smaller documented residue than today.
