---
work_package_id: WP04
title: Read path consults stored topology (structural #2062) + differential gate
dependencies:
- WP03
requirement_refs:
- FR-006
- FR-010
tracker_refs:
- "2062"
- "2069"
planning_base_branch: feat/single-planning-surface-authority
merge_target_branch: feat/single-planning-surface-authority
branch_strategy: Planning artifacts for this mission were generated on feat/single-planning-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-planning-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "556727"
history:
- Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/_read_path_resolver.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/mission_read_path.py
- tests/missions/test_surface_resolution_equivalence.py
role: implementer
tags: []
---

# WP04 — Read path consults the STORED topology (structural #2062) + differential gate (IC-04)

## Profile load (REQUIRED FIRST STEP)

Before touching any code, **load the `python-pedro` implementer profile** from the project
doctrine (`.kittify/doctrine/.../agent_profile/python-pedro.*`, or via the governed
profile-load surface). Adopt its identity, governance scope, boundaries, and initialization
declaration. This WP is **implementer-only**: do NOT self-review — the reviewer is
`reviewer-renata` (a separate role).

In your init declaration, state that you understand this is the **structural #2062 close**:
the read path must stop letting `CoordState.MATERIALIZED` (an on-disk `stat`) decide the
surface, and instead resolve from the **stored** `MissionTopology` (WP01 enum, WP02 stored
field, WP03 pure resolver). The binding operator principle (C-004): *"if storing topology
re-opens #2062, that proves our prior #2062 fix was non-structural."* The prior declared-coord
band-aid (`_declares_coordination_branch` gate) is REPLACED, not layered over — the on-disk
husk must be **structurally not consulted**.

---

## Objective

Make the read-path surface resolver consult the **stored** topology so a flattened mission
(`meta.json` topology = `SINGLE_BRANCH`/`LANES`, with a stale `-coord` husk still on disk)
resolves **PRIMARY** on every read leg for every handle form — and extend the differential
equivalence gate to prove it (a pure stored-topology cell AND the retained live on-disk row).

Two deliverables:

1. **FR-006 — read path consults stored topology (structural #2062).** In
   `src/specify_cli/missions/_read_path_resolver.py`, the read path MUST resolve the surface from
   the **stored** topology so `CoordState.MATERIALIZED` (the disk `stat` at lines 265-271) is **no
   longer the deciding signal**. A mission whose stored topology is `SINGLE_BRANCH`/`LANES` resolves
   PRIMARY **regardless of a stale `-coord` husk on disk**.

   **Read the topology ONCE at the boundary; pass it as a PARAMETER (do NOT read disk inside the
   pure helper).** `_resolve_existing_for_slug` (lines 242-282) is documented **PURE-PATH** ("no
   git, no subprocess" — and it reads no `meta.json` today). The stored `topology` lives in
   `meta.json`, which is **already read once** by `read_primary_meta` at the
   `resolve_handle_to_read_path` boundary (lines 687-688) — the SAME read that yields
   `coordination_branch`/`declares_coordination`. **Extract the stored `topology` from that existing
   `primary_meta` dict at the boundary** and **thread it as a new `topology` parameter** down the
   read-path call chain — `resolve_handle_to_read_path` → `_resolve_mission_read_path` →
   `_resolve_existing_for_slug` (and `_resolve_not_found`). The signature of
   `_resolve_existing_for_slug` GAINS a `topology` parameter; it MUST NOT open `meta.json` (or call
   `load_meta` / `_declares_coordination_branch` / any disk read for topology) inside its body — its
   no-I/O contract is preserved. **Smuggling a `meta.json` read into the pure helper is a
   correctness defect and a DoD failure**, not an acceptable shortcut.

   This **REPLACES** the prior declared-coord band-aid (`_declares_coordination_branch`,
   lines 92-101, consulted in the fail-closed gate at lines 274-280 and 538-543) — the on-disk
   husk is structurally not consulted, so #2062 cannot re-open (C-004 binding). Correct/remove
   the stale `:262-264` comment ("No branch is supplied here, so the absent-coord case stays
   UNMATERIALIZED…") that documents the defect (an on-disk-existence decision) as intentional.

2. **FR-010 — differential gate: stored-topology pure cell + retained on-disk legs.** In
   `tests/missions/test_surface_resolution_equivalence.py`:
   - **(a) ADD a PURE input→output cell** feeding `(mission_id, topology)` for **all four**
     `MissionTopology` values, asserting the returned `ExecutionContext` surface fields (PRIMARY
     vs coordination placement). Zero FS/git fixtures (it exercises WP03's
     `resolve_context_for_mission`).
   - **(b) RETAIN** the on-disk `flattened-stale-coord` topology × **every** handle form
     (`<slug>-<mid8>`, bare-mid8, full ULID, bare human slug), asserting **all** legs return
     PRIMARY — until those legs are deleted.
   - The existing `type(a) is type(b)` AND `error_code` assertion in `_assert_equivalent`
     (lines 200-228) **MUST NOT be weakened**. The pure cell is an **ADDITIONAL** proof, never a
     REPLACEMENT for the live on-disk proof (C-002, NFR-001).

**#2062 close scope — READ LEG ONLY (renata SF-5):** WP04 closes **only the READ leg** of #2062.
The spec carries #2062 across a read leg (this WP) **and** a status-write / emit leg (WP05). WP04
therefore MUST NOT claim "#2062 fixed" outright. What WP04 proves is the **READ-leg live repro
green** (quickstart **R1**, all 4 handle forms resolving PRIMARY). #2062's **TERMINAL close is
gated** on WP05's status-emit convergence **and** WP07's green suite. The issue-matrix verdict for
#2062 stays **NON-TERMINAL (`in-mission`)** until that full chain lands — do not mark #2062 done /
terminal at this WP.

**Scope guards:**
- Do **NOT** touch `src/mission_runtime/resolution.py` (WP03 owns the pure resolver + derivation
  retirement), `cli/commands/agent/mission.py` (WP05 write path), or `missions/_substantive.py`
  (WP07 `is_committed` collapse). Import `MissionTopology` / `resolve_context_for_mission` from
  the WP01/WP03 seam; do not redefine them.
- Preserve **C-006**: the create-window (#1718) and coord-deleted (#1848) states stay
  **probe-discriminated** (`probe_coord_state` + the branch signal). The stored topology does
  NOT answer "is the coord worktree materialized / is the branch alive?". Keep
  `StatusReadPathNotFound` / `CoordinationBranchDeleted` / the #2065 read-side contract intact.
- **#1970 campsite (touched lines only):** opportunistically clean adjacent debt on lines this
  WP actually edits — do not broaden into the named carved extractions.

---

## Context

### Ground truth (verified by reading the files 2026-06-22)

`src/specify_cli/missions/_read_path_resolver.py`:

- **`CoordState`** enum (lines 160-186) with `MATERIALIZED` / `EMPTY` / `UNMATERIALIZED` /
  `DELETED` / `NONE`, and **`probe_coord_state`** (lines 188-226) — the shared probe. The probe
  is the **transient on-disk×git discriminator** (C-006), NOT a topology classifier; it stays.
- **`_declares_coordination_branch`** (lines 92-101) — reads `meta.json` for a non-empty
  `coordination_branch` string. This is the **prior band-aid** consulted in the two fail-closed
  gates (see below). FR-006 REPLACES its decision role with the stored topology.
- **`_resolve_existing_for_slug`** (lines 242-282) — the anchor. The
  `CoordState.MATERIALIZED ⇒ return coord_feature_dir(...)` decision at **lines 265-271** keys
  the surface choice on an on-disk `stat`. The fail-closed gate at **lines 272-281** combines
  `coord_worktree_materialized` + `_declares_coordination_branch(primary_candidate)`.
- **The stale comment** at **lines 262-264** — *"No branch is supplied here, so the / absent-coord
  case stays UNMATERIALIZED (no git rev-parse) — the DELETED / arm lives at the surface_resolver
  layer (WP05)."* Documents the on-disk-existence decision as intentional; FR-006 requires it
  corrected/removed. **Verify the exact line numbers in your branch before editing** (code drifts);
  cite the verified lines in your diff.
- **`_resolve_not_found`** (lines 441-555) — the fail-closed / diagnostic tail, keyed on
  `probe_coord_state(...)` + `_declares_coordination_branch` (the `fail_closed` predicate, lines
  538-543). The `EMPTY ⇒ PRIMARY` (Option B) and `DELETED ⇒ CoordinationBranchDeleted` arms (C-006
  transient states) are preserved — only the topology classification moves to stored.
- **`resolve_handle_to_read_path`** (lines 607-755) — THE guarded read-side seam (`require_exists`
  forwarded). It reads the primary `meta.json` via `read_primary_meta` (lines 558-604) — where the
  **stored `topology`** field is available to thread into the decision (WP02 minted it; WP03 made
  it authoritative). The `:721-740` DELETED hard-fail (C-006) stays.

`src/specify_cli/mission_read_path.py` — the **back-compat shim**: re-exports
`_resolve_mission_read_path` under the original public name `resolve_mission_read_path` (deletion
tracked as #2048). If the resolution signature/decision changes, keep the shim re-export valid
and the `__getattr__` compat-attr contract intact (no resolver logic in the shim — lines 1-8).

`tests/missions/test_surface_resolution_equivalence.py` — the **C-004 deletion safety gate**:

- `_assert_equivalent` (lines 200-228) is the **load-bearing** comparison: dirs agree via
  `Path.resolve()` equality; errors agree via `type(a) is type(b)` AND `error_code` equality.
  **Do not weaken it.**
- `_build_topology` (lines 263-306) materialises realistic on-disk shapes. **Today there is no
  `flattened`-with-stale-coord-husk topology and no `topology` field in the written meta**
  (`_write_meta` writes only `mission_id` + optionally `coordination_branch`). You ADD the
  flattened arm + the `topology` field.
- `_entry_points` (lines 314-324) compares `resolve_handle_to_read_path(require_exists=True)`,
  `resolve_status_surface_with_anchor(...).read_dir`, and `MissionStatus.load(...).read_dir`.
- `_MATRIX` (lines 390-440) is currently all-GREEN (13/0 from prior mission 01KVN754). You ADD
  rows (flattened-stale-coord × 4 handle forms) and a NEW pure cell test — do not delete or
  re-flip existing rows.
- Production-shaped identity is established (lines 128-134): a real 26-char ULID, `mid8` = first
  8 chars. **Reuse this discipline** — no toy slugs (realistic-test-data standing rule).

### The flattened-stale-coord repro (quickstart.md R1 / R0)

Read `kitty-specs/single-planning-surface-authority-01KVPR00/quickstart.md` — **R1** is the
live read-leg repro and **R0** is the pure-resolver recipe. R1's on-disk shape:

```
kitty-specs/<slug>-<mid8>/meta.json            -> {"mission_id": ..., "topology": "single_branch"}
kitty-specs/<slug>-<mid8>/status.events.jsonl  -> canonical = approved
.worktrees/<slug>-<mid8>-coord/kitty-specs/<slug>-<mid8>/status.events.jsonl -> stale = planned
```

R1 pass condition: for handle in `{<slug>-<mid8>, bare-mid8, full-ULID, bare-human-slug}`, the
surface leg, the `require_exists=True` read_path leg, AND the aggregate leg ALL return PRIMARY —
**because the stored topology drives the read path** (the husk is not consulted). The read_path
leg "was STALE-COORD: the #2062 bug".

### Why a stored-topology read (FR-006 / C-004), not another band-aid

The prior fix made the read path consult `_declares_coordination_branch` (a `meta.json` read) to
avoid trusting a bare on-disk husk. But the **MATERIALIZED** arm (lines 265-271) still returns the
coord dir purely because `coord_root.exists()` and `feature_dir.exists()`. For a **flattened**
mission whose `meta.json` still carries a `coordination_branch` value but whose **stored
topology** is `SINGLE_BRANCH`/`LANES`, the band-aid does not save us — the materialized husk wins.
FR-006 makes the **stored topology** the gate: a `SINGLE_BRANCH`/`LANES` topology resolves PRIMARY
**before** the husk-existence check fires, so the husk is structurally irrelevant — the structural
close (#2062 cannot re-open); the declared-coord predicate's decision role is retired.

### What stays (C-006 — do NOT regress)

The stored topology classifies the **shape** (the 4 enum cells); it does NOT encode transient
on-disk×git states. Keep probe-discriminated: **create-window (#1718)** (topology
`COORD`/`LANES_WITH_COORD`, worktree not yet materialized → still PRIMARY via the UNMATERIALIZED
arm) and **coord-deleted (#1848)** (declared branch gone → still hard-fails
`CoordinationBranchDeleted`).

---

## Subtasks

### T020 — Read topology ONCE at the boundary, pass it as a PARAMETER into `_resolve_existing_for_slug` (FR-006)
- **Read the stored topology ONCE at the `resolve_handle_to_read_path` boundary — do NOT add a
  disk read to the pure helper.** `read_primary_meta` (lines 687-688) **already reads** the primary
  `meta.json` and returns `primary_meta`. Extract the stored **`topology`** value from that SAME
  `primary_meta` dict (no additional `meta.json` read; no new `load_meta` call). Then **thread it as
  a new `topology` parameter** down the read-path call chain: `resolve_handle_to_read_path` →
  `_resolve_mission_read_path` → `_resolve_existing_for_slug` (and `_resolve_not_found`).
- **`_resolve_existing_for_slug` gains a `topology` parameter** (signature change). It MUST stay
  **PURE-PATH**: it MUST NOT open `meta.json`, call `load_meta`, call `_declares_coordination_branch`,
  or otherwise read disk for topology inside its body — the topology arrives as an argument. Smuggling
  a disk read into the pure helper is **forbidden** (it breaks the documented no-I/O contract and is a
  DoD failure).
- With the topology in hand inside the helper, a `SINGLE_BRANCH`/`LANES` stored topology resolves
  **PRIMARY** *before* the `CoordState.MATERIALIZED` arm (lines 265-271) can return the coord dir
  (classify via WP01 `MissionTopology` / WP03's `routes_through_coordination` predicate).
- Import `MissionTopology` (and the predicate / `resolve_context_for_mission` if you project
  through the seam) from the WP01/WP03 surfaces — do **not** redefine them.
- The decision MUST be: **stored topology is the gate**. `CoordState.MATERIALIZED` (a disk
  `stat`) is no longer the deciding signal for a `SINGLE_BRANCH`/`LANES` mission. The probe still
  runs for the transient C-006 states (create-window / coord-deleted), but does not override a
  stored `SINGLE_BRANCH`/`LANES` topology into a coord read.
- **Preserve the legacy/no-topology path (FR-003 shell contract):** a mission whose `meta.json`
  has no stored `topology` yet (un-backfilled legacy) falls back to the existing probe-based
  resolution **once** — the stored value is authoritative when present, the legacy derivation is
  the one-time fallback. Do not crash on a missing `topology` key.

### T021 — Replace the declared-coord band-aid + correct the stale `:262-264` comment (FR-006, C-004)
- The fail-closed gates that consult `_declares_coordination_branch`
  (`_resolve_existing_for_slug` lines 274-280; `_resolve_not_found` `fail_closed` lines 538-543)
  must have their **topology decision** driven by the stored topology, not by the presence of a
  `coordination_branch` string + a materialized husk. The on-disk husk is structurally not
  consulted for a `SINGLE_BRANCH`/`LANES` mission.
- **Correct/remove the stale comment** at lines **262-264** ("No branch is supplied here…") —
  it documents the on-disk-existence decision as intentional; after FR-006 the decision is the
  stored topology. Replace it with a comment stating the read consults the stored topology (the
  husk is not the deciding signal); cite the verified line in the diff.
- If `_declares_coordination_branch` becomes dead after this (no remaining caller), remove it and
  its `__all__`/import references (the `test_no_dead_symbols` gate will otherwise flag it).
  If it is still consulted by a C-006 transient path, keep it and document the narrowed role.
- Keep the `mission_read_path.py` shim's `_resolve_mission_read_path` re-export and
  `__getattr__` compat contract valid (no signature break the shim cannot forward).

### T022 — ADD the pure stored-topology equivalence cell (FR-010a, NFR-005)
- In `tests/missions/test_surface_resolution_equivalence.py`, add a **NEW** test (a pure
  input→output cell) that feeds `resolve_context_for_mission(mission_id, topology)` (WP03's pure
  resolver) for **all four** `MissionTopology` values and asserts the returned `ExecutionContext`
  surface fields:
  - `SINGLE_BRANCH` / `LANES` → PRIMARY placement (`routes_through_coordination` False; no coord
    surface).
  - `COORD` / `LANES_WITH_COORD` → coordination placement (`routes_through_coordination` True).
- **ZERO** FS/git fixtures (no `tmp_path` meta, no repo init, no `load_meta` monkeypatch) — the
  resolver is pure (it mirrors quickstart R0). Use a **production-shaped** 26-char ULID
  `mission_id` (reuse the module's `MISSION_ID` discipline; no toy slug).
- This cell **ADDS** a proof; it does **NOT** replace the on-disk row (T023). Place it as its own
  `test_*` function (do not fold it into `test_entry_points_agree_per_cell`, whose canonical
  authority is the on-disk surface resolver).
- **No new file (create_intent contract):** the pure cell is a new `test_*` function ADDED to the
  **existing, owned** `tests/missions/test_surface_resolution_equivalence.py` — so `create_intent`
  stays empty (no new-file declaration needed). Do **NOT** spin the cell out into a separate new
  test module: that would be an undeclared file creation (the gate requires any genuinely-new file
  in `create_intent`). If, for some reason, a genuinely-new file is unavoidable, it MUST be declared
  in `create_intent` first — but the canonical placement is the existing owned equivalence file.

### T023 — RETAIN/ADD the on-disk flattened-stale-coord row × every handle form (FR-010b, NFR-001)
- Add a `flattened-stale-coord` arm to `_build_topology` (lines 263-306): primary
  `kitty-specs/<slug>-<mid8>/meta.json` carrying **`topology: "single_branch"`** (+ the
  `flattened` provenance flag and the residual `coordination_branch` value, to model the real
  husk) AND a **materialized but stale** `.worktrees/<slug>-<mid8>-coord/...` mission dir with a
  divergent status (mirroring quickstart R1). `_write_meta` must now write the `topology` field —
  extend it (and the existing `_build_topology` arms can keep their behavior; only the new arm
  needs the stored topology).
- Add `_MATRIX` rows for `flattened-stale-coord` × **every** handle form: `<slug>-<mid8>`,
  bare-mid8 (`MID8`), full ULID (`MISSION_ID`), and the bare human slug (`MISSION_SLUG`). Each
  must assert **all** entry-point legs return the **PRIMARY** dir (`xfail_reason=None` —
  expected GREEN once T020/T021 land; if you stage the test first it may xfail-strict until the
  impl lands, but the WP is DONE only when these rows are GREEN, not xfail).
- **Cover ALL THREE read legs, not just `_read_path_resolver` (squad scope expansion —
  cross-leg convergence).** The status-surface read leg traverses THREE engines, not one:
  `_read_path_resolver` (this WP), `coordination/surface_resolver.resolve_status_surface_with_anchor`
  (owned by WP03, which threads stored topology into it), and
  `coordination/status_transition._read_contract_from_transaction_target` (WP05). The
  `_entry_points` comparison (lines 314-324) **already** invokes the `surface_resolver` leg via
  `resolve_status_surface_with_anchor(...).read_dir` alongside the `require_exists=True` read_path
  leg and the aggregate leg. For every `flattened-stale-coord` row × every handle form, the gate
  MUST assert that the **`surface_resolver.resolve_status_surface_with_anchor(...).read_dir` leg
  ALSO returns PRIMARY** from the stored topology — alongside the existing `_read_path_resolver`
  leg. All legs MUST **AGREE** and resolve PRIMARY from stored topology; the convergence is proven
  **across legs**, not on the `_read_path_resolver` leg alone. (No change to `surface_resolver`
  source — WP03 owns it; this is a test-side assertion that its threaded-topology leg agrees.)
- The bare-human-slug handle resolves the composed primary dir via
  `resolve_bare_modern_mission_dir_name` (lines 889-934) — ensure the fixture's primary dir name
  carries the mid8 tail so that resolver finds it.
- **Do NOT weaken `_assert_equivalent`** (lines 200-228). The `type(a) is type(b)` + `error_code`
  assertion stays intact across all legs (it is what enforces the cross-leg agreement). The on-disk
  row proves the live behavior; it is RETAINED until those legs are deleted (a later mission),
  never replaced by the pure cell.

### T024 — Live repro + mutation note + static-analysis clean (NFR-001, NFR-004, C-002)
- **Live repro (NFR-001 / C-002 — binding):** run the quickstart **R1** recipe against a real
  throwaway tmp git repo (flattened `meta.json` topology `single_branch` + stale `-coord` husk)
  and **witness** all read legs (surface, `require_exists=True` read_path, aggregate) resolving
  **PRIMARY** for all **4** handle forms. #2062 is NOT fixed without a witnessed live repro —
  static reading is insufficient (standing live-evidence rule). Capture the run output in the WP
  review evidence.
- **Mutation note (non-fakeable proof the gate has teeth) — TWO independent mutations, one per
  read leg:** the on-disk `flattened-stale-coord` rows must turn **RED** under EACH of the
  following independent reverts, proving BOTH read legs are independently load-bearing (Paula's
  concession point — neither leg is decorative):
  - **(i) `_read_path_resolver` leg.** Temporarily revert T020 so the read path **re-infers** the
    surface from `CoordState.MATERIALIZED` (the pre-FR-006 behavior). The on-disk
    `flattened-stale-coord` rows go RED (the `require_exists=True` read_path leg returns the stale
    coord dir, diverging from the surface's PRIMARY). This proves the `_read_path_resolver` fix is
    load-bearing. Revert the mutation.
  - **(ii) `surface_resolver` leg.** Temporarily revert ONLY `surface_resolver`'s decision back to
    the `coordination_branch is None` / `probe_coord_state` re-inference — i.e. drop WP03's
    stored-topology threading into `resolve_status_surface_with_anchor` — while **leaving WP03's
    `_read_path_resolver` fix (T020/T021) in place**. The on-disk `flattened-stale-coord` rows go
    RED on the `surface_resolver.resolve_status_surface_with_anchor(...).read_dir` leg (it returns
    the stale coord dir while the read_path leg still returns PRIMARY → the legs diverge → the
    differential gate fails). This proves the `surface_resolver` leg is **independently**
    load-bearing and that WP03's `surface_resolver` topology threading is the deciding signal, not
    decorative. Revert the mutation.
  - Record BOTH mutation results in the review notes. Note: mutation (ii) reverts WP03-owned
    `surface_resolver` source transiently for the witness only — do NOT commit it; WP03 owns that
    source. Both mutations MUST be reverted before finishing.
- Run `ruff check .` and `mypy` on all changed files: **zero** issues/warnings, complexity ≤15,
  no new `S1192` (hoist any literal appearing ≥3× to a module constant), **no** new `# noqa` /
  `# type: ignore` / per-file ignore. Extract a small helper if a function nears the complexity
  ceiling rather than suppress.

---

## Branch Strategy

Planning artifacts for this mission were generated on `feat/single-planning-surface-authority`.
During `/spec-kitty.implement` this WP may branch from a dependency-specific base (**WP03 must be
`approved`/`done` first** — it owns the pure `resolve_context_for_mission` resolver and the
retired derivations this WP's read leg consumes), but completed changes must merge back into
`feat/single-planning-surface-authority` unless the human explicitly redirects the landing
branch. Run `move-task` / review / approve transitions from the **mission's status surface** (the
mission is flattened — carry the live-evidence rule throughout; flatten/coord friction is expected
per NFR-001 and the spec's dogfooding-hazard note). If the lane's `kitty-specs` copy is missing,
restore it from the lane base before driving status transitions.

---

## Definition of Done (non-fakeable)

A reviewer MUST be able to confirm each item **from the diff + a real run**, not from prose:

1. **Read path consults the STORED topology (FR-006, C-004):** in
   `_read_path_resolver.py`, `_resolve_existing_for_slug` (and the legs it feeds) resolve the
   surface from the stored `MissionTopology`, NOT from `CoordState.MATERIALIZED`. A
   `SINGLE_BRANCH`/`LANES` stored topology resolves **PRIMARY** even with a materialized `-coord`
   husk on disk. The prior `_declares_coordination_branch` band-aid's **decision role** is
   removed (the husk is structurally not consulted). The stale `:262-264` comment is
   corrected/removed (cite the verified line).

1a. **Topology arrives as a PARAMETER; the pure helper reads no disk (FR-006 grounding):** the
   diff shows `_resolve_existing_for_slug` GAINING a `topology` parameter (signature change), with
   the value read ONCE from the existing `primary_meta` dict at the `resolve_handle_to_read_path`
   boundary (lines 687-688) and threaded down via `_resolve_mission_read_path`. The reviewer MUST
   confirm the helper's body adds **no** `meta.json` / `load_meta` / `_declares_coordination_branch`
   / disk read for topology — its documented no-I/O ("no git, no subprocess") contract is intact. A
   disk read smuggled into the pure helper is **blocking**.

2. **Pure stored-topology cell present + additive (FR-010a, NFR-005):** the new pure cell
   (T022) feeds `resolve_context_for_mission` for **all 4** `MissionTopology` values with a
   **production-shaped ULID** and **zero** FS/git fixtures, asserting PRIMARY vs coordination
   `ExecutionContext` surface fields. It is a SEPARATE `test_*` function — it ADDS a proof, it
   does NOT replace the on-disk row.

3. **On-disk flattened-stale-coord row GREEN × every handle form (FR-010b, NFR-001):** the
   `_MATRIX` carries `flattened-stale-coord` rows for `<slug>-<mid8>`, bare-mid8, full ULID, AND
   bare human slug, each asserting **all** legs return the **PRIMARY** dir. These rows are GREEN
   (not xfail) on the final diff. `_assert_equivalent`'s `type(a) is type(b)` + `error_code`
   assertion is **unweakened** (lines 200-228 intact).

4. **READ-leg live repro witnessed (NFR-001 / C-002):** the quickstart R1 recipe is run against a
   real tmp git repo and witnesses all **read** legs resolving PRIMARY across all 4 handle forms;
   the evidence is captured. No "#2062 fixed" claim rests on static reading. **WP04 closes only the
   READ leg of #2062** — it does NOT claim #2062 terminally fixed. The #2062 issue-matrix verdict
   stays **NON-TERMINAL (`in-mission`)**; #2062's terminal close is gated on WP05's status-emit
   convergence + WP07's green suite.

5. **Mutation note recorded (gate has teeth):** the review evidence shows that re-inferring the
   surface from `CoordState.MATERIALIZED` turns the on-disk `flattened-stale-coord` rows RED —
   proving the retained on-disk row is load-bearing, not decorative. The mutation is reverted.

6. **C-006 preserved:** the create-window (#1718) UNMATERIALIZED→PRIMARY path and the
   coord-deleted (#1848) `CoordinationBranchDeleted` hard-fail still fire; `probe_coord_state` +
   the branch signal still discriminate the transient on-disk×git states; the #2065 read-side
   contract is intact. The pre-existing GREEN matrix rows (no-coord, coord-fresh, coord-behind,
   coord-empty, coord-deleted, ambiguous) remain GREEN (NFR-003 behavior-preserving).

7. **NFR-004 clean:** `ruff check .` and `mypy` report zero issues/warnings on changed files;
   complexity ≤15; no new `S1192`; no suppression added to pass. `mission_read_path.py` shim's
   re-export + `__getattr__` compat contract remain valid.

8. **Scope respected:** `resolution.py` (WP03), `cli/commands/agent/mission.py` (WP05), and
   `missions/_substantive.py` (WP07) are UNTOUCHED; `MissionTopology` /
   `resolve_context_for_mission` are imported from the WP01/WP03 seam, not redefined.

---

## Risks

1. **Re-adding a band-aid instead of the structural fix (C-004 violation).** Threading the stored
   topology but still letting `CoordState.MATERIALIZED` win in some branch leaves #2062 latent.
   **Mitigation:** the mutation note (T024/DoD-5) — reverting to a MATERIALIZED decision must turn
   the on-disk rows RED; if it does not, the stored-topology gate is not actually the deciding
   signal.

2. **Regressing the C-006 transient states.** Letting the stored topology answer "is the coord
   worktree materialized / is the branch alive?" would break the create-window (#1718) and
   coord-deleted (#1848) paths. **Mitigation:** stored topology classifies the **shape** only;
   `probe_coord_state` + the branch signal still own the transient discrimination. Run the #1718
   / #1848 guard tests.

3. **Weakening the differential gate.** Loosening `_assert_equivalent`, marking the on-disk rows
   xfail-and-leaving-them, or replacing the on-disk row with the pure cell would void the C-004
   deletion gate / the live-evidence proof. **Mitigation:** the pure cell is ADDITIVE; the on-disk
   rows must be GREEN (not xfail) on the final diff; the assertion body is untouched.

4. **Closing #2062 on static reading (C-002 violation).** **Mitigation:** the DoD requires a
   witnessed real flattened-mid-flight repro (quickstart R1) before any "fixed" claim.

5. **Un-backfilled legacy mission crashing on a missing `topology` key.** **Mitigation:** the
   read path falls back to the existing probe-based derivation **once** when `topology` is absent
   (FR-003 shell contract) — present stored value is authoritative; absent is the one-time
   legacy fallback.

6. **Shim breakage (#2048).** Changing the resolver signature/decision can break the
   `mission_read_path.py` re-export or its architectural allowlists. **Mitigation:** keep the
   `_resolve_mission_read_path` re-export and `__getattr__` compat-attr contract valid.

---

## Reviewer Guidance (reviewer-renata)

Verify against **code + a live run**, never prose. Concretely:

1. **Structural read (FR-006/C-004):** read the diff at `_resolve_existing_for_slug`
   (lines ~242-282). Confirm the surface decision is driven by the **stored topology**, and that
   `CoordState.MATERIALIZED` is no longer the deciding signal for a `SINGLE_BRANCH`/`LANES`
   mission. Confirm the `_declares_coordination_branch` band-aid's decision role is removed (and
   the symbol removed if now dead, or its narrowed role documented). Confirm the stale `:262-264`
   comment is corrected/removed — an unverified "pre-existing" claim for a line this WP edits is
   **blocking**, not a warning.
   **Topology-as-parameter (grounding check — blocking):** confirm `_resolve_existing_for_slug`
   GAINED a `topology` parameter and that the value is read ONCE from the existing `primary_meta`
   dict at the `resolve_handle_to_read_path` boundary (lines 687-688) — NOT re-read from
   `meta.json` inside the pure helper. The helper's body must add **no** `meta.json` / `load_meta` /
   `_declares_coordination_branch` / disk read for topology; its no-I/O contract must be intact. A
   disk read smuggled into the pure helper is **blocking**.

2. **Pure cell additive (FR-010a):** open the new pure test — confirm it feeds
   `resolve_context_for_mission` for ALL 4 topology values with a real ULID and **zero** FS/git
   fixtures, and that it is a SEPARATE function (not a replacement for the on-disk row). Run it
   isolated.

3. **On-disk row GREEN × 4 handles (FR-010b/NFR-001):** confirm `_MATRIX` carries
   `flattened-stale-coord` rows for `<slug>-<mid8>`, bare-mid8, full ULID, AND bare human slug,
   each GREEN (not xfail), each asserting all legs → PRIMARY. Confirm `_assert_equivalent`
   (lines 200-228) is **unweakened**. Run the matrix isolated.

4. **Live evidence + mutation note (NFR-001/C-002):** require the witnessed quickstart-R1 live
   repro output AND the mutation note (a MATERIALIZED-decision revert turns the on-disk rows RED).
   Reject any "#2062 fixed" claim resting on static reading. **Confirm the #2062 verdict is scoped
   to the READ leg:** WP04 witnesses the read-leg repro green only; it must NOT mark #2062 terminal.
   The #2062 issue-matrix verdict must stay **NON-TERMINAL (`in-mission`)** — terminal close is
   gated on WP05's status-emit convergence + WP07's green suite. A terminal "#2062 fixed" verdict at
   this WP is **blocking**.

5. **C-006 intact:** run the #1718 create-window and #1848 coord-deleted guard tests; confirm
   `probe_coord_state` + branch-signal discrimination survives and `CoordinationBranchDeleted`
   still fires. Confirm the pre-existing GREEN matrix rows stay GREEN.

6. **Statics (NFR-004):** `ruff check .` + `mypy` zero issues on changed files; complexity ≤15;
   no new `S1192`; no new suppression. Shim compat contract valid.

7. **Scope:** confirm `resolution.py`, `cli/commands/agent/mission.py`, and `_substantive.py` are
   untouched, and `MissionTopology` / `resolve_context_for_mission` are imported, not redefined.

Incorrect doc paths or unverified "pre-existing/out-of-scope" claims for lines this WP edits are
**blocking**, not warnings.

## Activity Log

- 2026-06-22T16:21:09Z – claude:opus:python-pedro:implementer – shell_pid=482541 – Assigned agent via action command
- 2026-06-22T16:59:29Z – claude:opus:python-pedro:implementer – shell_pid=482541 – FR-006 read path consults WP02 stored MissionTopology (threaded as param from resolve_handle_to_read_path boundary; pure helper reads no disk). FR-010 pure cell (4 topologies) + flattened-stale-coord row x4 handles all 3 legs PRIMARY. LIVE R1 repro witnessed: read_path+surface+aggregate all PRIMARY x {composed,bare-mid8,ULID,bare-human-slug}. Mutation(i) read_path + (ii) surface_resolver both turn rows RED. Caught+fixed a live no-silent-fallback regression (ambiguous 083 masked by bare-modern fold). #2062 verdict NON-TERMINAL/in-mission (read leg only). #1718/#1848 guards green. ruff+mypy clean, complexity<=15.
- 2026-06-22T17:00:54Z – claude:opus:reviewer-renata:reviewer – shell_pid=556727 – Started review via action command
- 2026-06-22T17:09:34Z – user – shell_pid=556727 – Approved cycle 1. FR-006 stored-topology read-leg structural #2062 close: topology read ONCE at boundary via pure stored_topology_from_meta, threaded as param; pure helper reads no disk (only Path.exists stats); SINGLE_BRANCH/LANES returns PRIMARY before MATERIALIZED arm. FR-010 pure cell (4 topologies, zero FS) + flattened-stale-coord x4 handles all 3 legs PRIMARY GREEN; _assert_equivalent unweakened. Fixture re-shaping LEGITIMATE (matches canonical R1/FR-005 — no coordination_branch; husk-in-meta variant carved to WP05). No-silent-fallback VERIFIED (identity resolver probed first; MissionSelectorAmbiguous propagates before bare-modern fold). Live R1 repro re-run by reviewer: 12/12 legs PRIMARY x4 handles. Mutation re-run: gate disable -> 4/4 rows RED. C-006 #1718/#1848 guards green (28). ruff+mypy clean, complexity<=15. #2062 verdict NON-TERMINAL/in-mission. Scope: owned files + sanctioned boy-scout ratchet seed-line drift (composite key content-anchored).
