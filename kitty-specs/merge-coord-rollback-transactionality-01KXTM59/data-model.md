# Data Model — Phase 1

This is internal merge machinery: no HTTP/GraphQL contracts, no persisted entities beyond the one
optional `MergeState` field below. The "state transition" of interest is the coord-branch coherence
lifecycle, captured as an invariant.

> **Post-plan revision (architect-alphonso HIGH).** The strand set is derived from the **committed
> coordination ref**, NOT from a live committed-vs-working worktree diff. `_restore_final_bookkeeping_snapshots`
> restores **primary `repo_root`** paths (`bookkeeping_projection.py`), never the coordination
> worktree — so a committed-vs-working diff computed *at the #2786 mark point* (inside
> `_revert_coord_done_commit`, which runs **before** the later restore) would see both sides `done`,
> return an **empty delta, write no marker, and silently drop the strand** — the exact failure this
> mission closes. The committed ref is the reliable authority at any mark point; the "approved" side
> is known **by construction** (the rollback's intent). See D7 (revised) in research.md.

## Entity: `pending_coord_reconcile` marker (field on `MergeState`)

Persisted via the existing `save_state` to the **canonical per-mission runtime state**
`.kittify/runtime/merge/<mission_id>/state.json` (NOT the legacy `.kittify/merge-state.json`, which
`get_state_path(mission_id=None)` uses only for CLI `--abort`/`--resume` back-compat; heal + doctor
MUST load the per-mission runtime path). Typed `dict[str, Any] | None` — a plain dict;
`MergeState.from_dict` rehydrates JSON objects as dicts and drops unknown keys, so **no migration**
is required for pre-existing state files.

| Key | Type | Meaning | Source |
|---|---|---|---|
| `coord_ref` | `str` | Fully-qualified coordination branch ref carrying the stranded commit | `resolve_placement_only(...kind=STATUS_STATE).ref` |
| `captured_sha` | `str` | Coord-branch HEAD sha captured *before* the `done` bookkeeping commit (the `git revert` base) | executor pre-bake capture |
| `coord_worktree` | `str` | Absolute path to the coordination worktree the repair operates in (env via `_make_merge_env`). *Not* "byte-restored" — the coord worktree is **not** touched by `_restore_final_bookkeeping_snapshots`; the committed `done` is undone by a forward `git revert`. | `CoordinationWorkspace.worktree_path` |
| `stranded_wp_ids` | `list[str]` | The **specific** WP(s) this merge marked `done` that remain `done` on the **committed coord ref** after rollback (⇒ incoherent vs the intended `approved`). NOT a static list; NOT a live worktree diff. | `_durable_done_wps_on_coordination_ref(candidate_wps=<this merge's pre-target done write-set>)` |
| `revert_error` | `str \| None` | Diagnostic: the swallowed revert error (#2786) or the bake failure (#2367-B); `None` if unavailable | caught exception text |
| `detected_at` | `str` | ISO-8601 UTC timestamp the strand was marked | stamped at mark time |

**Derivation contract for `stranded_wp_ids` (load-bearing, anti-fakeable):**
- Candidate set = **this merge's own pre-target done write-set** (the WPs it committed `done` during
  this merge) — NOT all done WPs, and **NOT `run.all_wp_ids`** (the natural but WRONG value — on a
  *resume* it includes WPs a prior attempt legitimately baked `done`, so the heal would `git revert` a
  legitimately-done WP). This excludes a genuinely-pre-existing-`done` WP (spec edge-case: "a
  genuinely-done WP before the abort must survive") **by construction**.
- **Run-state provenance (WP03):** `_MergeRunState` currently carries only `all_wp_ids` — there is **no**
  field for the pre-target done write-set. WP03 MUST add one, captured at the
  `_record_merged_wps_done_for_merge` bake site, and pass *it* (not `all_wp_ids`) as `candidate_wps`.
- **Non-fakeable test (WP02 owner-level + WP03):** the only fixture that distinguishes the correct
  candidate set from `all_wp_ids` is a **pre-existing-`done` WP** (done *before* this merge) alongside a
  this-merge strand → `stranded_wp_ids` contains only the this-merge WP; the pre-existing-done WP is
  **excluded**. A fixture whose "coherent" WP is only-ever-`approved` does NOT catch an `all_wp_ids`
  implementation (it's excluded either way). This fixture is a DoD checkbox, not prose.
- Membership = still reduces to `DONE` on the **committed coordination ref**
  (`_durable_done_wps_on_coordination_ref` reads `EventLogReadContract.coordination_branch_ref(...)`).
  A never-committed "coherent" WP (only ever `approved`) is not done-on-ref ⇒ excluded.
- Together these satisfy the ≥2-WP non-fakeability fixture (reviewer-renata): in a fixture with one
  stranded WP and one coherent WP, `stranded_wp_ids == [the_stranded_one]` — a hardcoded `["WP01"]`
  or an over-broad `all_wp_ids` both fail.

**Validation rules**
- `stranded_wp_ids` MUST be non-empty when the marker is present (an empty strand is not a strand —
  the marker is only written when `_durable_done_wps_on_coordination_ref` over this merge's write-set
  is non-empty).
- `coord_ref` / `coord_worktree` MUST resolve; the marker is written from the same resolved
  placement the rollback used (no re-resolution drift).
- Marker presence is advisory only — repair/doctor **re-derive** the strand set from the committed
  ref (D6); a stale marker over a now-coherent ref heals to a no-op clear.

## Shared coherence owner (paula-patterns HIGH / alphonso Q1)

The strand-derivation and the repair are **coordination-domain** knowledge and get exactly one home,
consumed by all three call-sites (no three-way drift → the #2786-C seed):

- `coordination`-layer **`coord_incoherent_done_wps(coord_ref, candidate_wps) -> list[str]`** — thin
  wrapper over `_durable_done_wps_on_coordination_ref`; called by the marker-persist site, the
  resume heal-gate, and the doctor check. (Do NOT re-implement the reduction in `merge/executor.py`
  private helpers — that leaks coord-reduction semantics into the merge layer.)
- The **repair primitive** (`git revert` of the stranded commit, env via `_make_merge_env`) is homed
  as a coordination-layer function consumed by both executor-resume and `doctor --fix` — NOT an
  executor-private that a diagnostic command reaches into (dependency inversion / DIR-044). It MUST
  **function-locally** import `_make_merge_env` from `lanes.merge` (module-top import creates the cycle
  `merge.executor → coordination.coherence → lanes.merge → merge.config`; executor.py:474 already uses
  the lazy pattern). The reader half re-derives via `coordination.status_service.EventLogReadContract`
  — zero `merge` imports, layer-clean.

**Marker enumeration (paula HIGH — the doctor gap).** `load_state(repo_root, mission_id=None)` **raises**
`MergeAmbiguousStateError` on ≥2 active states, but a stranded marker persists across missions and
`doctor coordination` must enumerate **all** of them. There is no "list all markers" API. WP02 MUST add
`iter_pending_coord_reconcile_markers(repo_root) -> Iterable[MergeState]` in `state.py` (scanning
`.kittify/runtime/merge/*/state.json`, its own path authority) with a focused test; WP04 consumes it —
NOT re-implementing the runtime-path scan inside the doctor (that would be a second path authority /
DIR-044 breach). Without this, the enumeration falls between WP02 and WP04's `owned_files`.

**Two-readers note (paula LOW→MED).** `coord_incoherent_done_wps` is **the** strand authority;
`_durable_done_wps_on_coordination_ref` (done_bookkeeping.py) stays as the resume-dedup reader only.
Both reduce coord-`DONE` via the same `EventLogReadContract`; converging them is a documented **follow-up**,
not in scope — recorded so the class does not re-seed one layer away.

## Repair transport (alphonso Q4 — AC-B3/AC-F1)

The repair is a **forward `git revert`** of the stranded coord commit (as `_revert_coord_done_commit`
already implements), env via `_make_merge_env`. It does **NOT** use `git/ref_advance.py::advance_branch_ref`
— moving the coord ref back to `captured_sha` is a non-fast-forward move that `advance_branch_ref`
**refuses by design** (`RefAdvanceNonFastForwardError`). No raw `git update-ref` (AC-B3).

> **WP03 implementation deviation (documented, tracked as [#2797]).** The single strand-**derivation**
> authority (`coord_incoherent_done_wps`) is shared by mark + heal + doctor as planned. But the raw
> `git revert` **transport** ended up in **two** legs — `merge/executor.py::_revert_coord_done_commit`
> (the #2711 in-merge lockstep, unconditional/clean-tree) and `coordination/coherence.py::repair_coord_strand`
> (WP02's resume/doctor leg, strand-gated/dirty-tree). Delegating the former to the latter breaks the
> pinned `test_executor_option_a_revert_helpers_2711.py`, and a clean shared-transport helper crosses WP
> ownership boundaries. Both reviewers concur this is a transport-dedup residual, **not** a re-opening of
> the #2786-C derivation drift (the derivation authority stays single). #2797 unifies the transport +
> narrows the heal's `git reset --hard` to a scoped `git checkout HEAD -- <status paths>` (defense-in-depth).

## Invariant (class-closing, FR-008 / SC-005)

> **INV-COORD-ROLLBACK**: After any merge rollback, either the coordination branch is coherent (no
> WP from this merge's write-set still reduces to `DONE` on the committed coord ref while its intended
> lane is `approved`) **or** a `pending_coord_reconcile` marker exists naming the stranded WP(s).

No rollback path may leave the coord ref with a stranded `done` *and* marker-absent. The FR-008 guard
is **behavioral, not a source grep**: it must red under a *runtime-stubbed* mark (stub
`_persist_coord_reconcile_marker`/`coord_incoherent_done_wps` to a no-op, drive a real bake-path
strand, assert the checker finds a stranded-done WP AND marker-absent). A guard that stays green under
a runtime-stubbed mark is a tautology and is rejected.

**Enumeration (paula-patterns — root-cause, not two-sites; corrected post-tasks: SEVEN sites).** The
same `_restore_final_bookkeeping_snapshots` "restore-without-revert" shape appears at **seven**
call-sites in `executor.py`: **407, 536, 670, 691, 701, 757, 786** (verified by grep; `INV-6` in the
module docstring names this rollback pattern). Live coord strands come from the **pre-target** path
(≈397→407) plus the revert-failure branch (≈500-514), because `done_marked_before_target` (≈350-352)
gates coord topology to the pre-target ordering.

- Site **≈691** (post-target `_record_merged_wps_done_for_merge` failure) sits **inside**
  `if not run.done_marked_before_target:` (≈679) → **dead-for-coord** (assert this gating).
- Site **≈701** (`_project_status_bookkeeping_to_target` failure in `_phase_record_done_and_project`)
  sits **OUTSIDE** that guard → runs under **coord** topology, after the target advanced, and does
  **not** revert the committed coord `done` → a **live #2786-shape coord strand** (double-confirmed
  by reviewer-renata + python-pedro). It MUST be routed through the marking primitive and treated as a
  live site, not merely enumerated.

FR-008 MUST enumerate the sites **programmatically** (AST/regex over the call-sites, never a hardcoded
count — the count drifts as WP03 inserts helpers), assert ≈691's topology-gating, and assert ≈701 is
coord-reachable-and-routed. The preferred structural close is to co-locate the coherence-mark at the
`_restore_final_bookkeeping_snapshots` **primitive** (a thin `_restore_and_guard_coord_coherence(...)`
**every** caller routes through, incl. 701) so a future restore site cannot strand silently — this is
**inner** (not the phase-driver wrapper INV-5 forbids). WP03-T010 routing is the *primary* mechanism;
the two hand-picked marks are reached *through* it (no double-mark).

## Out-of-scope reconciliation fence (alphonso Q5)

The transient `done` emit fired through `emit_status_transition_transactional`
(validate→persist→materialize→views→**SaaS**). A `git revert` coherently reverts the **tracked**
coord artifacts (`status.events.jsonl` + materialized `status.json`), so committed materialization
self-heals — but the **outbound SaaS/dashboard emit cannot be un-sent**. This mission **fences that
out**: the hosted projection may transiently show `done` for a rolled-back WP until the next
authoritative emit reconciles it (SaaS is advisory / eventually-consistent). Recorded as an explicit
scope fence in Complexity Tracking, not a silent omission. A compensating SaaS reconciliation is a
separate follow-up if product deems the transient projection unacceptable.

## Coherence lifecycle (state transition)

```
coherent ──(bake done commit lands, then rollback strands it on the committed ref)──► stranded+marked
stranded+marked ──(merge --resume | doctor --fix, while a strand still reduces DONE-on-ref)──► coherent, marker cleared
stranded+marked ──(resume runs but ref already coherent, e.g. crash after heal before clear)──► no-op, marker cleared
coherent ──(happy-path merge, NFR-001)──► coherent  (byte-identical; no marker ever written)
```

Idempotency (NFR-002): the `stranded+marked → coherent` and `already-coherent → no-op clear` edges
converge — running resume/`--fix` N times yields a byte-stable coord `status.events.jsonl` (raw
bytes, not a reduction-equality softening) and the marker cleared exactly once.
