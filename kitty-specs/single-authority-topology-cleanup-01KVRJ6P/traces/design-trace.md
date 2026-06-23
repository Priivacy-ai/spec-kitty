# Design Trace — single-authority-topology-cleanup-01KVRJ6P

**Purpose:** a running log of the DESIGN itself — the decisions, the invariants kept, the
forward-alignment to the #2090 SSOT — so we can assess afterward whether the design held
under implementation (behavior-neutrality survived, #2090-readiness held, KEEP set respected,
the one correctness win proven).

---

## The design (seeded 2026-06-23)

**Frame:** behavior-neutral cleanup + dedup consuming the landed MissionTopology SSOT
(PR #2086). Zero correctness regression on backfilled missions; **one** intentional
correctness improvement (FR-004 topology=None absorption extends the #2062 fix to
un-backfilled missions).

### Core design moves
- **CommitTargetKind eradication (FR-001/002):** `.kind` carried one decision bit, read in
  one place (`routes_through_coordination`). Collapse `topology → routes_through_coordination(topology) → bool`;
  the enum disappears; `CommitTarget` stays a ref-only VO (C-007). `FLATTENED` was write-only
  dead (AST-verified); the `flattened` provenance meta-flag survives (C-006).
- **topology=None absorption (FR-004):** acquire a concrete, non-optional `MissionTopology`
  at the read-path boundary (`read_topology`/`classify_from_meta`); collapse the ~8
  `topology is None` husk-arms. The correctness win + the migration-gate dissolution.
- **Dedup (FR-005/006/007):** C1 predicate+frozenset (6→1, 4→1); C2 polymorphic `load_meta`
  (3 contracts); C6 `task_helpers` shadow → re-export. NFR-004 floor ~750–1000 LOC.
- **Residue authority (FR-008/012):** converge accept + merge + auto_rebase gates onto ONE
  `is_coordination_artifact_residue_path` — residue becomes a single authority.

### KEEP set (load-bearing invariants — the anti-over-reduction guard)
C-001 husk short-circuit (`surface_resolver:667-678`, df79f76f4 data-loss fix); C-002
genuine-fallback relays (read-stored-first); C-003 5-hop feature-dir path; C-004 corrupt-meta
typed-raise; C-005 transient probes (#1718/#1848); C-006 flattened meta-flag; C-007 ref-only
VO; C-011 runtime_bridge worktree_root; **C-012 write-side death-spiral twin carved to #1716**.
(randy verified all live + correctly pinned; "wanted to cut more, KEEP forbade.")

### Forward-alignment to #2090 (the resolve_target SSOT)
- alphonso (post-tasks): the mission **sets up #2090 cleanly** — it converges on the existing
  `MissionArtifactHome`/`artifact_home_for` seam (the embryonic `resolve_target`), preserves
  every #2090 KEEP item, threads a concrete non-optional topology (what the pure projection
  needs), and derives residue from one authority. The `.kind` removal does NOT lose info
  #2090's `(kind×intent)` keying needs (that lives in the untouched `MissionArtifactKind`).
- **Must-not-do** (would force #2090 rework): don't reconvert `is_coordination_owned` with a
  fabricated `.kind` shim — derive from stored topology; don't model FLATTENED as
  `coord==primary` (use `CommitTarget | None`); don't introduce a 2nd residue/predicate name;
  don't fold mid8-persistence / the write-side twin (C-012).

### Design risks surfaced (to validate in implement)
- **Mutation blind-spot (paula):** the differential gate proves "legs agree," not "topology→
  surface mapping is correct." Mitigated by an **absolute per-topology assertion** (WP01 cell +
  the WP04-reworked `test_pure_stored_topology_projects_surface_placement`). Watch this hold.
- **Behavior-neutral vs behavior-CHANGING cells:** `is_coordination_artifact_residue_path` is
  always-true today; FR-008's rework makes it topology-gated → the flat-mission residue path
  CHANGES (not neutral). The neutrality oracle must not mask this (paired flat→False cell).
- **Conditional FR-013 resolved:** `CommitResult` is disjoint from `.kind` (the #1891 bug is
  the un-serializable Path) → standalone, co-located in lane B only for file-sharing.

## During / after implement — APPEND BELOW
<!-- Assess: did behavior-neutrality survive (differential gate + full suite green on the
     merged branch)? was the one correctness win (FR-004) provable on a live un-backfilled
     repro? did the #2090-readiness claims hold (the residue authority stayed a clean topology
     projection)? was any KEEP item accidentally collapsed? did the absolute-mapping pin catch
     anything? Net LOC vs the NFR-004 floor. -->

### During implement (2026-06-23, flattened LANES mission)

- **Behavior-neutrality held under review, with TWO real catches by the adversarial
  review loop** (validates the per-WP review as a gate, not a rubber stamp):
  1. **WP09** — the C2 sweep silently changed `task_utils/support.load_meta`'s
     malformed contract from *raise* → `{}` (delegated to the `on_malformed="empty"`
     adapter). A behavior regression in a `task_helpers`-re-exported helper. Caught;
     cycle-2 restored *raise* (`on_malformed="raise"`, missing→`TaskCliError`) + the
     malformed-arm test. **Design lesson:** the "absorb 3 contracts into one
     polymorphic reader" (FR-006) makes it *easy* to pick the wrong absorbing arg and
     silently shift a contract — the per-site contract test (both arms, observable
     return) is the load-bearing guard, exactly as the test-DoD specified.
  2. **WP03 — a genuine PLAN-SEQUENCING FLAW the sizing/anti-laziness squads missed.**
     The mechanical `kind=PRIMARY` drop (FR-001a, WP03/14/15) assumed
     `CommitTarget.kind` had a default — it did NOT (`ref: str` / `kind: CommitTargetKind`,
     both required). So `CommitTarget(ref=…)` was a runtime `TypeError` + 2 mypy
     `call-arg` errors in the intermediate state (broken until WP16 removes the field).
     **The drop-before-field-removal order needs a default-before-drop step.** Fix: a
     transitional `kind = CommitTargetKind.PRIMARY # removed by WP16` default added as a
     justified out-of-map edit to `context.py` (same-lane, dependency-ordered after
     WP02). **Design lesson for #2090 + the WP04/WP16 split:** "tidy the predicate
     before collapsing `.kind`" (WP02) should ALSO have made the field optional — a
     mechanical drop of a no-default field is never behavior-neutral on its own. The
     three coherence welds were right; this fourth ordering constraint
     (default-before-drop) was implicit and unstated. Worth encoding if the strangler
     pattern recurs.

- **The residue-authority pre-fix (72d88a8dc) proved its worth twice:** it both
  unblocked the (coord-era) record-analysis gate AND gave WP13's FR-012 convergence the
  complete residue set for free (WP13 approved, draws from the single authority).

_(continue appending during/after implement — assess FR-004 live repro at WP06, KEEP
set at WP17, net LOC at close)_
