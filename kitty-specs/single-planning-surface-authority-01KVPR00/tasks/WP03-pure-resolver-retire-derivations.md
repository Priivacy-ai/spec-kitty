---
work_package_id: WP03
title: Pure resolve_context_for_mission SSOT resolver + retire both derivations
dependencies:
- WP01
- WP02
requirement_refs:
- FR-004
tracker_refs:
- "2069"
planning_base_branch: feat/single-planning-surface-authority
merge_target_branch: feat/single-planning-surface-authority
branch_strategy: Planning artifacts for this mission were generated on feat/single-planning-surface-authority. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/single-planning-surface-authority unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "471936"
history:
- Created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/resolution.py
create_intent:
- tests/mission_runtime/test_resolve_context_for_mission_pure.py
execution_mode: code_change
owned_files:
- src/mission_runtime/resolution.py
- src/runtime/next/runtime_bridge.py
- src/specify_cli/coordination/surface_resolver.py
role: implementer
tags: []
---

# WP03 — Pure `resolve_context_for_mission` SSOT resolver + retire BOTH live derivations (IC-03, SEAM keystone)

## Profile load (REQUIRED FIRST STEP)

Before touching any code, **load the `python-pedro` implementer profile** from the project
doctrine (`.kittify/doctrine/.../agent_profile/python-pedro.*` or via the governed profile-load
surface). Adopt its identity, governance scope, boundaries, and initialization declaration.
This WP is implementer-only. Do NOT self-review; reviewer is `reviewer-renata` (separate role).

State, in your init declaration, that you understand this is the **keystone seam WP** of the
mission: it is the single place the mission kills the parallel-inference death-spiral by
collapsing **three** independent topology-inference derivations onto the stored-topology
authority — the two `coordination_branch is None ⇒ FLATTENED` derivations
(`resolution.py:706-717` door-internal + `runtime_bridge.py:193-212` ladder) AND the
status-surface re-inference in `coordination/surface_resolver.resolve_status_surface_with_anchor`
(`surface_resolver.py:600`), which is consumed by the very `ExecutionContext` this WP's pure
resolver projects (`_assemble_core_fragments` → `StatusSurfaceFragment` → `ExecutionContext`). The
third derivation sits **inside the seam's own door** — leaving it alive makes SC-001's
"zero inference sites" grep false. Getting this WP wrong leaves the death-spiral alive.

---

## Objective

Stand up the **pure** SSOT resolver and retire **both** hand-rolled topology derivations:

1. **Add `resolve_context_for_mission(mission_id: str, topology: MissionTopology) -> ExecutionContext`**
   on the canonical `mission_runtime` seam (`src/mission_runtime/resolution.py`) as a **PURE
   projection** over the existing single construction door **`build_execution_context`**
   (`resolution.py:90-127`) — the package-private `ExecutionContext(**fields)` factory, which is
   itself PURE (functional core / imperative shell split). The resolver performs **NO filesystem
   or git I/O** (NFR-005). The **imperative shell** runs the FS/git fragment assembly
   (`_assemble_core_fragments`, or explicit fragment readers) AND reads `meta.json` for the WP02
   stored `topology`, then hands the resolver the **already-assembled fragments + `topology`**;
   the resolver projects `build_execution_context(**fields)` from those inputs. The resolver
   touches no disk. (FR-004)

2. **Honor C-003 (binding):** the resolver MUST be a **thin projection** over the PURE door
   **`build_execution_context`** — it feeds shell-assembled fragments into the one
   `ExecutionContext(` factory and returns the result. "One authority, two projections."
   `resolve_placement_only` (`resolution.py:761`) is the **analogous narrow-projection
   DISCIPLINE** to mirror — *not the same call layer*. CRITICAL DISTINCTION:
   `resolve_placement_only` is an **imperative-shell** entry point that itself calls
   `_assemble_core_fragments` (which performs FS/git I/O — `get_main_repo_root`,
   `_resolve_mission_id`, `_resolve_coordination_branch`, worktree assembly) and then projects
   the `destination_ref` CommitTarget out of those fragments. A **PURE**
   `resolve_context_for_mission` (NFR-005, zero FS/git) can therefore **only project the PURE
   door** — `build_execution_context` — receiving the assembled fragments FROM the shell; it
   does NOT itself call `_assemble_core_fragments`, `get_feature_target_branch`, or any reader.
   Copy `resolve_placement_only`'s *projection discipline* ("one authority, narrow projection, no
   parallel re-read"), NOT its layer (it sits one layer down, in the shell). Do **NOT** build a
   parallel resolver that re-reads `meta.json` / `lanes.json` / git.

3. **Retire ALL THREE live topology-inference derivations:**
   - **(a)** the derivation behind the construction door in
     `src/mission_runtime/resolution.py` — the `if coordination_branch is not None: …
     else: … CommitTargetKind.FLATTENED` block in `_assemble_core_fragments`
     (verified at **`resolution.py:706-717`**, fed by `_resolve_coordination_branch` at
     `:515`); AND
   - **(b)** the **second, independent** ladder in `src/runtime/next/runtime_bridge.py`
     (verified: `_mission_declares_coordination_branch` at **`:144-154`** + the
     `_coord_path.exists() ⇒ COORDINATION` / `elif declared_coord_topology` /
     `else … FLATTENED` ladder at **`:193-212`**, keying the decision on the
     disk-`stat` signal `_coord_path.exists()` that **C-004 forbids**); AND
   - **(c)** the **third, status-surface re-inference** in
     `src/specify_cli/coordination/surface_resolver.py` —
     `resolve_status_surface_with_anchor` classifies the status surface from
     `coordination_branch is None` (**`surface_resolver.py:600`**) plus the
     `probe_coord_state` probe (**`:614`**). It is consumed by
     `mission_runtime/resolution.py:_resolve_status_surface_dir` (`:586`/`:604`) →
     `_assemble_core_fragments` → `StatusSurfaceFragment` → the very `ExecutionContext`
     this WP's resolver projects. It is **behavior-correct today** (the `:600`
     `coord_branch is None ⇒ PRIMARY` gate fires BEFORE the disk probe, so a flattened
     mission resolves PRIMARY — #2065 converged the husk case), but it re-infers the
     surface SHAPE from `coordination_branch is None` rather than the **stored topology** —
     a parallel derivation inside the seam's own door that makes SC-001's grep false.

   Leaving **ANY** of the three alive is the parallel-inference death-spiral.

4. **Gate both retirements under LIVE proof (NFR-001 / C-002):** the WP04 differential gate and
   a real flattened-mid-flight repro must be green. Do NOT mark #2062-related behavior fixed on
   static reading alone.

**Scope guards:**
- Do **NOT** chase the `CommitTargetKind` **type** eradication (that is the behavior-neutral
  Mission B / C-007). This WP stops the two **derivations** that key on `coordination_branch is
  None` / disk-`stat`; the constructor field stays vestigial.
- Preserve the transient-state probes (**C-006**): the #1718 create-window and #1848
  coord-deleted states stay **probe-discriminated** (`probe_coord_state` + the branch signal),
  NOT subsumed by stored topology. The `_resolve_coordination_branch` meta-read (`:515`) is a
  meta reader, not the `is None ⇒ FLATTENED` inference — keep it as the source of the
  `coordination_branch` value the shell threads in; retire only the `is None ⇒ FLATTENED`
  decision built on top of it.

---

## Context

### Why this WP exists (FR-004 — the death-spiral kill)

Spec Kitty decides *where* a mission's planning artifacts live by **re-inferring the mission's
shape, ad-hoc, at many seams** from scattered on-disk and git signals. The
`coordination_branch is None ⇒ FLATTENED` pattern is hand-rolled in **at least two independent
places** that drift apart:

- **Door-internal derivation** — `_assemble_core_fragments`
  (`src/mission_runtime/resolution.py:706-717`): reads `coordination_branch` via
  `_resolve_coordination_branch` (`:515`), then branches
  `if coordination_branch is not None → CommitTarget(kind=COORDINATION)` else
  `→ CommitTarget(kind=FLATTENED)`. **VERIFIED** (lines read 2026-06-22).
- **Runtime-bridge ladder** — `runtime_bridge.py:144-212`:
  `_mission_declares_coordination_branch` (`:144-154`) re-reads `meta.json` for
  `coordination_branch`, then a separate ladder at `:193-212` keys the decision on
  `_coord_path.exists()` (a disk `stat`): `if _coord_path.exists() → COORDINATION`,
  `elif declared_coord_topology → COORDINATION`, `else → FLATTENED`. The
  `_coord_path.exists()` arm keys on the **on-disk worktree-existence signal C-004 forbids** —
  this is the second, independent inference. **VERIFIED** (lines read 2026-06-22).

WP01 (IC-01) added the `MissionTopology {SINGLE_BRANCH, LANES, COORD, LANES_WITH_COORD}` enum
and the `routes_through_coordination(target)` predicate to `src/mission_runtime/context.py`.
WP02 (IC-02) made `topology` a **stored** `meta.json` field (minted at create + backfill). With
the stored value authoritative, **both** of the above derivations become dead inference: the
shape is read, not guessed.

This WP is the **keystone**: it provides the pure projection both retirements route through.

### The projection DISCIPLINE (C-003) — `resolve_placement_only` (analogous, NOT same layer)

`resolve_placement_only(repo_root, mission_slug) -> CommitTarget` (`resolution.py:761-847`,
**VERIFIED**) is the existing "narrower entry point over the **same** resolution authority, NOT
a parallel resolver". It resolves `target_branch` once, runs the single
`_assemble_core_fragments` builder, and **projects out** the one `destination_ref` CommitTarget
that builder already computes.

**LAYER WARNING (alphonso SF-1) — do not conflate the two doors.** `resolve_placement_only`
projects over **`_assemble_core_fragments`**, which performs FS/git I/O (`get_main_repo_root`,
`_resolve_mission_id`, `_resolve_coordination_branch`, worktree assembly) — so it is an
**imperative-shell** function, NOT pure. `resolve_context_for_mission` must be **PURE**
(NFR-005). It therefore CANNOT mirror `resolve_placement_only`'s *call layer* (which itself does
disk reads); it can only project the **PURE** door **`build_execution_context`
(`resolution.py:90-127`)** — the `ExecutionContext(**fields)` factory — receiving the assembled
fragments + stored `topology` FROM the shell. What carries over is the **discipline** ("one
authority, narrow projection, no parallel re-read"), not the layer. The shell (e.g. a
`resolve_placement_only`-style caller, or `resolve_action_context`) does the
`_assemble_core_fragments` + `meta.json` topology read and threads the results in;
`resolve_context_for_mission` only calls `build_execution_context`.

### The single construction door

`build_execution_context(**fields) -> ExecutionContext` (`resolution.py:90-127`, **VERIFIED**)
is the package-private sole factory. There is exactly one `ExecutionContext(` call in
production (its body). It enforces the build-time invariant
`target_branch == branch_ref.target_branch` (raises `ActionContextError(
"CONTEXT_INVARIANT_VIOLATION", …)`). `resolve_context_for_mission` projects through this door —
it does not construct `ExecutionContext` directly and does not patch a built context (the
composite is frozen — `ExecutionContext`, `context.py:178`, **VERIFIED**).

### Functional core / imperative shell (NFR-005)

The resolver is the **functional core**: pure, inputs `(mission_id, topology)` (plus the shell-
assembled fragments / branch refs), output `ExecutionContext`, zero FS/git. It projects the PURE
door **`build_execution_context`** and nothing else. The **imperative shell** (the existing
`resolve_action_context` / `resolve_placement_only` callers, and their meta-reading helpers
`_resolve_mission_id`, `_resolve_coordination_branch`, `get_feature_target_branch`, plus
`_assemble_core_fragments` itself) does all FS/git: it parses/persists `meta.json` (including the
WP02 stored `topology`), **assembles the fragments**, and threads `id + topology` (plus the
already-resolved branch refs / surfaces / workspace) into the resolver. The resolver does NOT
call `_assemble_core_fragments` — that helper runs in the shell BEFORE the resolver, and its
output is one of the resolver's inputs (this is the SF-1 layer split). This is what makes the
pure unit test possible with **zero FS/git fixtures**.

### `topology` is an authoritative input (optional input-assertion)

`topology` arrives from the shell (read from `meta.json` per WP02). The resolver treats it as
authoritative. Add an **optional input-assertion** (fail-closed, C-003 spirit): when the
resolver is also handed the raw `coordination_branch` / lanes signals the shell already has, and
the **supplied** topology disagrees with what those signals would imply, **fail closed** with a
typed error naming both values — never silently prefer one. (This is an assertion guard, not a
re-derivation: the resolver does not read disk to compute the "resolved" side; it compares the
supplied topology against the shell-provided structured inputs.)

### Preserve transient probes (C-006)

The create-window (#1718: topology declares `COORD`/`LANES_WITH_COORD` but the coord worktree
is not yet materialized) and coord-deleted (#1848: declared coord branch deleted from git)
states are **orthogonal to the 4 enum cells**. They remain discriminated by the existing probe
(`probe_coord_state` + the branch signal) and keep raising `CoordAuthorityUnavailable` /
`CoordinationBranchDeleted` / the #2065 read-side contract. Do NOT let the stored topology
answer "is the coord worktree materialized / branch alive?" — that regresses #1718/#1848.

### Out of scope (do NOT do here)

- `CommitTargetKind` **type** eradication / its ~143 value-literal refs (Mission B / C-007).
- The 9 `.kind is COORDINATION` decision-site re-routing (WP01 owns the predicate; downstream
  WPs adopt it).
- Read-path adoption (WP04), write-authority adoption (WP05), map/finalize (WP06),
  `is_committed` collapse (WP07).
- Editing `context.py` (WP01 owns the enum/VO — **IMPORT `MissionTopology` /
  `routes_through_coordination` from it**) or `mission_creation.py` (WP02 owns the mint).

---

## Subtasks

### T015 — Add the pure `resolve_context_for_mission` projection (NFR-005, C-003)
- In `src/mission_runtime/resolution.py`, add
  `resolve_context_for_mission(mission_id: str, topology: MissionTopology) -> ExecutionContext`.
- Import `MissionTopology` (and `routes_through_coordination` if needed for the per-ref
  projection) **from `src/mission_runtime/context.py`** (WP01). Do not redefine them.
- Body is a **thin projection** over the PURE door **`build_execution_context`
  (`resolution.py:90-127`)** — the `ExecutionContext(**fields)` factory. The resolver receives
  the **already-assembled** structured inputs from the shell (identity / branch-ref / status-
  surface / workspace fragments + the supplied `topology`) and feeds
  `build_execution_context(**fields)`. It applies `routes_through_coordination(topology)` (or the
  per-ref equivalent) to select PRIMARY vs coordination placement from the supplied fragments —
  it does NOT re-read anything to compute that.
- **The resolver does NOT call `_assemble_core_fragments`, `get_feature_target_branch`,
  `get_main_repo_root`, `_resolve_mission_id`, `_resolve_coordination_branch`, or any reader.**
  Those are the SHELL's job (`resolve_placement_only` is the *discipline* to mirror, not the
  layer — it sits in the shell and itself does that FS/git assembly; see the LAYER WARNING in
  Context). The resolver projects `build_execution_context` ONLY.
- **PURE:** the function body contains **no** `open()`, `Path.read_text`, `load_meta`,
  `subprocess`, `git`, `*.exists()`, `*.stat()`, `_assemble_core_fragments`, or any other FS/git
  call. All such access stays in the shell. (NFR-005 — this is what T018's zero-fixture test
  proves.)
- The projected `ExecutionContext` is correct for **all four** `MissionTopology` values:
  - `SINGLE_BRANCH` / `LANES` → PRIMARY placement (`routes_through_coordination` false; no coord
    surface).
  - `COORD` / `LANES_WITH_COORD` → coordination placement (`routes_through_coordination` true).
- Add a clear docstring stating: pure projection over the door **`build_execution_context`**
  (C-003), zero FS/git (NFR-005), topology authoritative input, fragments supplied by the shell,
  and that it shares `resolve_placement_only`'s narrow-projection **discipline** while sitting
  one layer UP (the shell, e.g. `resolve_placement_only` / `resolve_action_context`, does the
  `_assemble_core_fragments` + `meta.json` topology read; this resolver projects only the pure
  factory).

### T016 — Add the optional input-assertion (fail-closed on mismatch)
- When the shell supplies both the `topology` AND the structured `coordination_branch` / lanes
  signals it already read, add a guard: if the supplied topology disagrees with what those
  structured inputs imply, raise a typed error (`ActionContextError("TOPOLOGY_INPUT_MISMATCH",
  …)` or the closest existing typed error) naming **both** the supplied and the
  signal-implied topology.
- This is an **assertion over shell-provided inputs**, NOT a disk re-derivation — the resolver
  stays pure. Make the guard optional (skipped cleanly when the corroborating signals are not
  supplied) so pure callers that pass only `(mission_id, topology)` are unaffected.

### T017 — Retire ALL THREE derivations onto the stored topology
- **(a) Door-internal (`resolution.py:706-717`):** replace the
  `if coordination_branch is not None … else CommitTargetKind.FLATTENED` derivation inside
  `_assemble_core_fragments` so the `destination_ref` topology classification is driven by the
  **stored topology** (threaded in by the shell), NOT by `coordination_branch is None`. Keep
  `_resolve_coordination_branch` (`:515`) as the **value reader** for the `coordination_branch`
  ref string (the shell still needs the ref); retire only the `is None ⇒ FLATTENED` **decision**
  built on top of it. Update the now-stale docstrings/comments at `:680-694` / `:711-714` that
  describe the retired WP08 `kind == FLATTENED` collapse.
  - **Signature delta (alphonso NIT-1 — pin this so the reviewer expects it):**
    `_assemble_core_fragments` currently has **no** `topology` parameter
    (`(repo_root, *, mission_slug, target_branch, cwd)`, `resolution.py:664-670`). To drive the
    classification from stored topology, **add a keyword-only `topology: MissionTopology`
    parameter** to `_assemble_core_fragments` AND thread it through its **two callers**:
    `resolve_placement_only` (`resolution.py:836`) and `resolve_action_context`
    (`resolution.py:884`). In both callers the value is sourced from the **shell's `meta.json`
    read** (the WP02 stored field), resolved alongside the existing `target_branch` read — NOT
    re-inferred from `coordination_branch`. These are same-file edits WP03 already owns
    (`resolution.py`); the reviewer should expect this 3-site signature change as part of the
    diff, not flag it as scope creep.
- **(b) Runtime-bridge (`runtime_bridge.py:144-212`):** retire
  `_mission_declares_coordination_branch` (`:144-154`) as a **decision** input and the
  `_coord_path.exists() ⇒ COORDINATION` ladder at `:193-212`. The `decision_target` /
  `worktree_root` classification MUST be driven by the **stored topology** (read once by the
  shell from `meta.json`), NOT by `_coord_path.exists()` (the C-004-forbidden disk `stat`).
  - **Preserve C-006:** the create-window vs coord-deleted vs materialized distinction that the
    `_coord_path.exists()` / `declared_coord_topology` branches currently conflate must remain
    **probe-discriminated** where it concerns "is the worktree materialized / branch alive"
    (the `worktree_root` selection + the `DecisionGitLogUnavailable` fail-closed path at
    `:223-229`). Only the **topology classification** of `decision_target.kind` moves to stored
    topology. Do NOT delete the fail-closed `DecisionGitLogUnavailable` behavior.
- **(c) Status-surface resolver (`surface_resolver.py:600`):** in
  `resolve_status_surface_with_anchor`, route the **surface classification** (PRIMARY vs
  coordination) through the **stored topology**, NOT the `coordination_branch is None`
  re-inference at `:600`. The stored topology is threaded in from the shell — it reaches this
  resolver via `_assemble_core_fragments` → `_resolve_status_surface_dir`
  (`resolution.py:586`/`:604`) → `resolve_status_surface` → `resolve_status_surface_with_anchor`,
  so add the keyword-only `topology: MissionTopology` parameter to each link in that chain
  (mirroring the alphonso NIT-1 signature delta in (a)) and decide PRIMARY-vs-coord SHAPE from
  `routes_through_coordination(topology)` (or the equivalent), not from `coordination_branch is
  None`. The reviewer should expect this multi-site signature change as part of the diff (these
  are files WP03 already owns: `surface_resolver.py` + `resolution.py`).
  - **CRITICAL C-006 preservation — `probe_coord_state` stays, probe-discriminated:** keep
    `probe_coord_state` (`:614`) ONLY for the **transient on-disk×git discrimination**. The two
    transient arms MUST stay intact and probe-driven:
    - the `CoordState.DELETED` hard-fail (`:623`, #1848 `CoordinationBranchDeleted`); AND
    - the `CoordState.EMPTY` loud-primary fallback (`:642`, #1716).
    The **stored topology** decides the coord-vs-primary SHAPE; the **probe** still decides the
    **transient on-disk state** (materialized / empty / deleted). Do NOT collapse the transients
    into the enum (C-006) — they are orthogonal to the 4 enum cells. A change that routes the
    DELETED hard-fail or the EMPTY loud-primary fallback through stored topology (instead of the
    probe) is a C-006 regression and a REJECTION.
- After all three: there are **zero** live decision sites keying on `coordination_branch is None`
  or `_coord_path.exists()` to classify topology/surface — INCLUDING `surface_resolver.py:600`
  (SC-001). The only surviving `coordination_branch`/`coord_branch` reads are value-reads and the
  C-006 transient-discrimination arms (the `probe_coord_state` DELETED/EMPTY checks), never a
  surface/topology classification.

### T018 — Pure zero-fixture unit test for the resolver (NFR-005, SC-002)
- Add a unit test (e.g. `tests/mission_runtime/test_resolve_context_for_mission_pure.py`) that:
  - Feeds `resolve_context_for_mission` a **production-shaped** `mission_id` (a real 26-char
    ULID, NOT a short handcrafted slug) and each of the **four** `MissionTopology` values, with
    the structured inputs constructed in-memory.
  - Asserts the returned `ExecutionContext` surface fields per topology: PRIMARY vs coordination
    placement (`artifact_placement` / `branch_ref.destination_ref` kind via
    `routes_through_coordination`), and the relevant surface/identity fields.
  - Uses **ZERO** filesystem and **ZERO** git fixtures — no `tmp_path` meta.json, no repo init,
    no monkeypatched `load_meta`. If the test needs a fixture to run, the resolver is not pure —
    fix the resolver, not the test.
  - Covers the T016 input-assertion: a supplied-vs-signal mismatch raises the typed error naming
    both topologies.

### T019 — Inference-pattern gate + static-analysis clean (SC-001, NFR-004)
- Add an architectural-style assertion (or extend the existing surface-resolver guard suite)
  that scans the production tree and proves the `coordination_branch is None` /
  `_coord_path.exists()` **topology/surface-inference** pattern has **zero live decision sites** —
  the only matches are value-reads (the `_resolve_coordination_branch` meta reader returning
  `None`), the C-006 transient-discrimination arms (the `probe_coord_state` DELETED/EMPTY checks),
  and tests, never a `⇒ FLATTENED/COORDINATION/PRIMARY` classification.
- **The gate MUST also assert `surface_resolver.py:600`'s `coord_branch is None` SURFACE-decision
  is retired** (alongside the `resolution.py:706-717` and `runtime_bridge.py:193-212` sites). The
  status-surface classification in `resolve_status_surface_with_anchor` must derive from stored
  topology; only the C-006 transient arms (`probe_coord_state` DELETED/EMPTY) may read
  `coord_branch`. **A grep/AST gate that passes while `surface_resolver.py:600` still makes a
  surface decision from `coordination_branch is None` is a vacuous-gate REJECTION** — the gate has
  not actually covered the third derivation and is reporting green falsely.
- **The gate MUST catch NEGATED and ALIASED spellings (renata N-2), not just the literal
  `coordination_branch is None`.** A grep for that one string passes **vacuously** while an
  equivalent inference survives under a different spelling. The gate must cover at minimum:
  `coordination_branch is None`, `coordination_branch is not None`, `not coordination_branch`,
  `coord_branch is None` / `coord_branch is not None` / `not coord_branch`,
  `_coord_path.exists()` (and `.exists()` / `.stat()` on any `*coord*` path variable), and
  bare-truthiness forms (`if coordination_branch:` / `if not coord_branch:`) **where the
  branch body classifies topology** (assigns `CommitTargetKind` / `MissionTopology` /
  `decision_target.kind`). **Prefer an AST-based check** (walk for `Compare`/`UnaryOp`/`BoolOp`
  nodes on a `coordination_branch`/`coord_branch`/`_coord_path` name whose enclosing branch
  produces a topology classification); an explicit **multi-pattern grep covering every alias
  above** is acceptable only if it demonstrably matches all the listed forms.
- **A too-narrow gate that passes vacuously is a REJECTION.** The test author MUST include a
  negative-control assertion (a fixture string containing a negated/aliased inference) proving
  the gate would FAIL if such a site were reintroduced — a gate that cannot fail is not a gate.
- Run `ruff check .` and `mypy` on all changed files: **zero** issues/warnings, complexity ≤15,
  no new `S1192` (hoist any literal appearing ≥3× to a module constant), **no** new `# noqa` /
  `# type: ignore` / per-file ignore. If a function approaches the complexity ceiling, extract a
  small pure helper rather than suppress.

---

## Branch Strategy

Planning artifacts for this mission were generated on `feat/single-planning-surface-authority`.
During `/spec-kitty.implement` this WP may branch from a dependency-specific base (WP01 + WP02
must be `approved`/`done` first — they own the enum and the stored field this WP consumes), but
completed changes must merge back into `feat/single-planning-surface-authority` unless the human
explicitly redirects the landing branch. Run `move-task` / review / approve transitions from the
mission's status surface (the mission is flattened — carry the live-evidence rule throughout;
flatten/coord friction is expected per NFR-001 and the spec's dogfooding-hazard note).

---

## Definition of Done (non-fakeable)

A reviewer MUST be able to confirm each item **from the diff + a real run**, not from prose:

1. **Resolver exists and is PURE (NFR-005, C-003):**
   `resolve_context_for_mission(mission_id: str, topology: MissionTopology) -> ExecutionContext`
   exists in `resolution.py`, projects through the PURE door **`build_execution_context`
   (`resolution.py:90-127`)** — feeding shell-assembled fragments into the one
   `ExecutionContext(` factory — imports `MissionTopology` from `context.py` (does not redefine
   it), and contains **no** FS/git call in its body (grep the function body for
   `open`/`read_text`/`load_meta`/`subprocess`/`git`/`exists`/`stat`/`_assemble_core_fragments`
   → zero hits). It shares `resolve_placement_only`'s narrow-projection **discipline** but is NOT
   at its layer: `resolve_placement_only` itself calls `_assemble_core_fragments` (FS/git);
   `resolve_context_for_mission` calls only `build_execution_context` and the shell supplies the
   fragments (projection, not parallel resolver, and not a re-read of the shell's I/O).

2. **Pure unit test, ZERO fixtures (SC-002):** T018's test feeds `(production-shaped mission_id,
   topology)` for **ALL 4** `MissionTopology` values and asserts the `ExecutionContext` fields,
   with **zero** FS/git fixtures (no `tmp_path` meta, no repo init, no `load_meta`
   monkeypatch). The test passes. The T016 input-assertion mismatch case is covered.

3. **ALL THREE derivations retired (SC-001):**
   - `resolution.py:706-717` no longer classifies topology from `coordination_branch is None`;
     it reads the stored topology.
   - `runtime_bridge.py:193-212` no longer classifies `decision_target.kind` from
     `_coord_path.exists()`; it reads the stored topology.
   - `surface_resolver.py:600` no longer classifies the status surface from
     `coordination_branch is None`; `resolve_status_surface_with_anchor` reads the stored topology
     (threaded via `_resolve_status_surface_dir`), and `probe_coord_state` is retained ONLY for
     the C-006 transient arms (`CoordState.DELETED` hard-fail `:623`, `CoordState.EMPTY`
     loud-primary `:642`).
   - The T019 inference-pattern gate proving the `coordination_branch is None` /
     `_coord_path.exists()` **inference** pattern — INCLUDING its negated/aliased spellings
     (`not coordination_branch`, `coord_branch is None`, `_coord_path.exists()`, etc.) AND
     including `surface_resolver.py:600` — has **zero live decision sites** is green, and carries a
     negative-control proving it can fail. The `_resolve_coordination_branch` value-reader, the
     C-006 transient arms, and tests are the only remaining matches.

4. **C-006 preserved:** the create-window (#1718) and coord-deleted (#1848) probe paths are
   intact — `probe_coord_state` + branch signal still discriminate transient on-disk×git states;
   `CoordAuthorityUnavailable` / `CoordinationBranchDeleted` / `DecisionGitLogUnavailable`
   (`runtime_bridge.py:223-229`) and the #2065 read-side contract still fire. Their guard tests
   are green (NFR-003 behavior-preserving for already-correct topologies).

5. **Live proof (NFR-001 / C-002):** the WP04 differential equivalence gate
   (`tests/missions/test_surface_resolution_equivalence.py`) — including the on-disk
   `flattened-stale-coord` row — is green, and a **real flattened-mid-flight repro** witnesses
   the retirements (not static reading). #2062-related behavior is NOT claimed fixed without the
   witnessed live repro.

6. **NFR-004 clean:** `ruff check .` and `mypy` report zero issues/warnings on changed files;
   complexity ≤15; no new `S1192`; no suppression added to pass.

7. **Scope respected:** `CommitTargetKind` type NOT deleted; the 9 `.kind` decision sites NOT
   re-routed here (downstream WPs); `context.py` and `mission_creation.py` NOT edited
   (owned by WP01/WP02 — imported from).

---

## Risks

1. **Accidental impurity (NFR-005).** The easiest failure is letting one `load_meta` /
   `*.exists()` leak into the resolver "for convenience". That silently re-couples it to disk and
   defeats the zero-fixture test. **Mitigation:** keep every read in the shell; the T018 test is
   the tripwire — if it needs a fixture, the resolver regressed.

2. **Retiring only some derivations (the death-spiral trap).** Retiring `resolution.py:706-717`
   but leaving `runtime_bridge.py:193-212` or `surface_resolver.py:600` (or any subset) keeps the
   parallel inference alive and re-opens the desync. `surface_resolver.py:600` is especially easy
   to miss because it is behavior-correct today — but a behavior-correct re-inference still makes
   SC-001's grep false and leaves a parallel derivation inside the seam's own door.
   **Mitigation:** the T019 grep gate fails unless **all three** are gone (and explicitly asserts
   `surface_resolver.py:600`); review all three diffs explicitly.

3. **Subsuming a transient probe into the enum (C-006 regression).** Routing the
   `_coord_path.exists()` / `declared_coord_topology` ladder's *worktree-materialization* check
   through stored topology would regress #1718 (create-window) / #1848 (coord-deleted).
   **Mitigation:** move ONLY the `kind` topology classification to stored topology; keep the
   probe deciding "materialized / alive". Preserve `DecisionGitLogUnavailable`.

4. **Stale docstrings asserting the retired WP08 `kind == FLATTENED` collapse**
   (`resolution.py:680-694`, `:711-714`) misleading future readers. **Mitigation:** update them
   to describe stored-topology classification.

5. **Closing #2062 on static reading (C-002 violation).** **Mitigation:** the DoD requires a
   witnessed live flattened repro + the green WP04 differential gate before any "fixed" claim.

---

## Reviewer Guidance (reviewer-renata)

Verify against **code + a live run**, never prose. Concretely:

1. **Purity (NFR-005):** grep the body of `resolve_context_for_mission` for
   `open`/`read_text`/`load_meta`/`subprocess`/`git`/`exists`/`stat`/`_assemble_core_fragments`
   — expect **zero**. Confirm it projects through the PURE door **`build_execution_context`
   (`resolution.py:90-127`)**, does NOT construct `ExecutionContext` directly, does NOT call
   `_assemble_core_fragments` / any reader, and does NOT re-read `meta.json`/`lanes.json`/git
   (C-003). It must share `resolve_placement_only`'s narrow-projection **discipline** while
   sitting ONE LAYER UP: `resolve_placement_only` (`resolution.py:761`) is itself the shell that
   calls `_assemble_core_fragments` (FS/git) — the pure resolver must NOT replicate that call,
   it consumes the shell-assembled fragments instead. A resolver that calls
   `_assemble_core_fragments` (or any reader) directly is a REJECTION (it is impure).
2. **Zero-fixture test (SC-002):** open T018's test — confirm NO `tmp_path` meta, NO repo init,
   NO `load_meta` monkeypatch; confirm all **4** topology values are exercised with a real ULID
   `mission_id`; confirm the input-assertion mismatch case raises the typed error naming both
   topologies. Run it isolated.
3. **All THREE derivations gone (SC-001):** read the diffs at `resolution.py:706-717`,
   `runtime_bridge.py:193-212`, AND `surface_resolver.py:600`. Confirm none classifies
   topology/surface from `coordination_branch is None` / `_coord_path.exists()`. For
   `surface_resolver.py`, confirm `resolve_status_surface_with_anchor` decides PRIMARY-vs-coord
   from the stored topology and that `probe_coord_state` (`:614`) is retained ONLY for the C-006
   transient arms (DELETED hard-fail `:623`, EMPTY loud-primary `:642`) — a change that routes
   those transient arms through stored topology is a C-006 regression, REJECT it. Run the T019
   inference-pattern gate — it must show zero live inference decision sites (including
   `surface_resolver.py:600`) AND cover negated/aliased spellings (`not coordination_branch`,
   `coord_branch is None`, `_coord_path.exists()`). **Reject a gate that only matches the literal
   `coordination_branch is None`, or that passes while `surface_resolver.py:600` still makes a
   surface decision** (it passes vacuously); confirm its negative-control proves it can fail. Also
   confirm `_assemble_core_fragments` and its two callers (`resolve_placement_only` `:836`,
   `resolve_action_context` `:884`) gained the `topology` parameter, and that the
   `_resolve_status_surface_dir` → `resolve_status_surface` → `resolve_status_surface_with_anchor`
   chain was threaded the `topology` too (alphonso NIT-1 signature delta — expected, not scope
   creep).
4. **C-006 intact:** confirm `probe_coord_state` + branch-signal discrimination survives;
   confirm `DecisionGitLogUnavailable` (`runtime_bridge.py:223-229`) still raises for declared
   coord topology with a failed construction; run the #1718 create-window and #1848
   coord-deleted guard tests.
5. **Live evidence (NFR-001/C-002):** require the green WP04 differential gate (incl. the
   on-disk `flattened-stale-coord` row) and a witnessed real flattened-mid-flight repro. Reject
   any "fixed" claim resting on static reading.
6. **Statics (NFR-004):** `ruff check .` + `mypy` zero issues on changed files; complexity ≤15;
   no new suppression.
7. **Scope:** confirm `CommitTargetKind` type is NOT deleted, the 9 `.kind` sites are NOT
   re-routed here, and `context.py` / `mission_creation.py` are untouched (imported from).

Incorrect doc paths or unverified "pre-existing/out-of-scope" claims for lines this WP edits are
**blocking**, not warnings.

## Activity Log

- 2026-06-22T15:40:34Z – claude:opus:python-pedro:implementer – shell_pid=442907 – Assigned agent via action command
- 2026-06-22T16:06:58Z – claude:opus:python-pedro:implementer – shell_pid=442907 – Pure resolve_context_for_mission projecting build_execution_context (zero FS/git, 4-topology zero-fixture test green). All 3 derivations retired onto stored topology: resolution.py door-internal, runtime_bridge ladder, surface_resolver:600 surface classification. T019 AST gate green (negated/aliased spellings + surface_resolver coverage + 4 negative-controls; zero live inference sites). C-006 #1718/#1848 transient guards GREEN (probe_coord_state DELETED/EMPTY preserved). ruff exit 0, mypy 0 errors on changed files. WP04 equivalence gate green. PRE-EXISTING (not mine, confirmed via stash): test_mission_runtime_surface::test_public_surface_matches_contract fails on lane base from WP01 __init__ drift. --force used per flat-mission preflight friction; 3 owned files conflict-free.
- 2026-06-22T16:08:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=471936 – Started review via action command
- 2026-06-22T16:15:01Z – user – shell_pid=471936 – APPROVED (renata, cycle 1): keystone seam holds. Pure resolve_context_for_mission projects build_execution_context with ZERO FS/git (T018 fixture-free 4-topology test green). ALL THREE derivations retired onto stored MissionTopology: resolution.py door (destination_kind_for_topology), runtime_bridge ladder (_coord_path.exists only selects worktree_root now), surface_resolver:600 (effective_topology decides shape). C-006 transients PRESERVED & RAN GREEN: #1848 CoordinationBranchDeleted, #1716 EMPTY loud-primary, #1718 create-window, DecisionGitLogUnavailable, WP04 equivalence gate (62 passed). T019 AST gate non-vacuous (3 negative controls). ruff clean, mypy clean on owned files. Scope respected (CommitTargetKind intact, context.py/mission_creation.py/__init__.py untouched). Known pre-existing WP01 __all__ contract drift confirmed not WP03. --force across benign lane-base divergence (3 owned files identical at base).
