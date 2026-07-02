# WP02 Review — Cycle 1 — CHANGES REQUESTED

Reviewer: reviewer-renata. Verdict: **REJECT** (one blocking defect in the FR-010
proof). The port shape, adapters, injection proof, stratification invariants, and
the guard-outcome reframing itself are all sound — the block is narrowly the
**move_task pin**, which mislabels a coord-authority status read as a guard-only
read and would drive a split-brain regression in WP06.

---

## BLOCKING — Issue 1: the FR-010 `move_task:1138` pin is unsound (real parity break)

The proof pins `WORK_PACKAGE_TASK` for all three guard sites and labels
`move_task:1138` a "guard" read (test comment lines 418-429). It is not. Traced
against live `tasks.py`:

- **finalize_tasks:2373** — `feature_dir` (coord husk) feeds **only** `check_pre30_layout`
  (2376), then is **reassigned** at 2453. Guard-only. Adjacent primary read at 2384
  is `WORK_PACKAGE_TASK`. Pin is behavior-neutral. ✅ SOUND.
- **list_dependents:3568** — `feature_dir` (coord husk) feeds **only** the guard (3571),
  then is **reassigned** at 3578 to `resolve_planning_read_dir(WORK_PACKAGE_TASK)`.
  Guard-only. ✅ SOUND.
- **move_task:1138** — `_mt_feature_dir` (coord husk) feeds the guard (1140) **AND two
  real coord-authority reads**:
  - `1149`: `_read_transactional_wp_lane(feature_dir=_mt_feature_dir, …)` — reads the
    authoritative **event-log lane** (STATUS partition → must be the coord husk).
  - `1216`: `_persist_review_artifact_override_in_coord(coord_feature_dir=_mt_feature_dir, …)`.
  This value is **NOT guard-only.** Repointing `move_task:1138` from
  `resolve_feature_dir_for_mission` (coord husk) to `resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)`
  (primary) moves the status/event-log read from coord → primary. On a coord mission
  the primary `kitty-specs/` does not hold the authoritative event log → wrong/empty
  lane → **exactly the split-brain FR-010 exists to close.** This meets the "used
  downstream where coord-husk vs primary changes behavior → parity break" bar.

**Why this is a real (not hypothetical) hazard:** WP06's own prompt is already primed
to execute it — lines 56 and 80 instruct "migrate the read at `move_task:1138` →
`resolve_planning_read_dir(kind=…)` via FsReader, **byte-identical** (per the WP02
proof)." Following the pin literally repoints the shared `_mt_feature_dir` and breaks
the status read. Shipping this pin as "byte-identical" is false for move_task.

**The proof's own evidence contradicts the move_task pin:**
- Its rationale (test line 428) justifies `WORK_PACKAGE_TASK` because it "matches each
  site's adjacent primary read" — but cites only `finalize_tasks:2384` and
  `list_dependents:3578`. move_task has **no** adjacent primary read; its adjacent
  reads are all coord/status reads.
- `test_fr010_only_status_partition_kind_matches_the_blind_dir` shows `STATUS_STATE`
  is the **path-equal** (truly byte-identical) kind for the coord husk — which is what
  move_task's shared variable actually needs. The proof dismisses `STATUS_STATE` as
  "the WRONG choice for the pre30 guard," which is true for the two guard-only sites
  but wrong for move_task.
- The cited `add_history` precedent (2285, `TASKS_INDEX`→primary) is valid but its
  guard var `_ah_feature_dir` is **guard-only** (used only at 2285/2289). It licenses
  finalize/list_dependents; it does **not** license move_task where the var is the
  coord status read source.

`check_pre30_layout` is confirmed a genuine no-op on modern layout
(`if not is_legacy_format(feature_path): return`; read-only), so the guard-outcome
equivalence claim is sound in itself — the defect is applying a single one-size pin
across a site whose "guard" read is structurally the coord status read.

### Required remediation (in the WP02-owned proof/test file)
1. **Do not treat `move_task:1138` as a guard-read migration.** Either:
   - (a) pin the move_task guard to a **STATUS-partition kind** (`STATUS_STATE`), which
     the proof already shows is path-equal to the coord husk — preserving the status
     read; **or**
   - (b) require the move_task rewire to introduce a **separate** guard variable
     (kind-aware, primary) while `_mt_feature_dir` **stays** on
     `resolve_feature_dir_for_mission` (coord husk) for the reads at 1149/1216. State
     this explicitly so WP06 cannot wholesale-repoint line 1138.
2. **Correct the pin table** (test lines 418-429) to separate the two guard-only sites
   (finalize/list_dependents — safe `WORK_PACKAGE_TASK`) from move_task (shared coord
   status var).
3. **Add a red-first assertion** pinning the move_task hazard: that repointing the
   coord-husk status read to a primary kind is **not** byte-identical for the status
   read (so WP06 cannot collapse the two reads and pass).
4. Flag WP06 (lines 56/80) so its "byte-identical migrate 1138" instruction is
   reworded to match the corrected pin.

---

## NON-BLOCKING notes (address or acknowledge)

**Note A — `primary_anchor_dir` + the WP09-owned floor bump.** Not dead-speculative:
it mirrors the real co-located canonicalizer fold in `map_requirements` (2647-2648,
`primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))`) that WP07
rewires. It is uncalled today, but so are all four ports by WP02's design (documented
in the module docstring; `__all__` omitted to dodge the dead-symbol gate). The
`ROUTED_CANONICALIZER_FLOOR` 38→39 bump is an honest +1 (one genuine new routed
occurrence). Two asks:
- The bump edits **WP09-owned** files (`test_resolution_authority_gates.py`,
  `test_coord_read_residuals_closeout.py`). The before/after comments are honest, but
  notify WP09 to rebase — it does census-drain and re-pins this floor.
- Lock the consumer: WP07's prompt should name `primary_anchor_dir` as the port method
  for the 2647-2648 fold so it does not become genuinely dead.

---

## Confirmed PASS (standard checks)

- **Two-capability WRITE port, not fused**: `commit_status` → `emit_status_transition_transactional`
  (`GuardCapability`); `commit_artifact` → `commit_for_mission` (`MissionArtifactKind` +
  `ProtectionPolicy`, event-less). Distinct methods over real seams (verified bodies,
  not stubs). `not hasattr(router, "commit")` asserted.
- **Result types renamed** off `CommitResult` → `CommitStatusResult`/`CommitArtifactResult`
  (git/commit_helpers.py:424 collision avoided).
- **C-002** fold co-located intra-method in `RealFsReader.primary_anchor_dir`; static
  ordering test present.
- **C-005**: no `--ports` flag (surface-wide introspection test); `_do(*, ports=None)`
  idiom demonstrated.
- **C-001**: `FsReader` (READ) ≠ `CoordCommitRouter` (WRITE); disjoint method names asserted.
- **Single identity source**: `commit_status` takes only `TransitionRequest`, which
  carries `feature_dir`/`repo_root`/`mission_slug` — no hidden second identity source.
- **Fakes pure** (in-memory, no fs/subprocess). Tests green: 18 ports + 42 golden
  (untouched) + arch gates = **108 passed**. ruff + mypy clean, zero new suppressions.
  No edits to `tasks.py` command bodies.

Anti-pattern checklist: 1 Dead-code N/A (ports uncalled by design until WP06+, documented);
2 Synthetic-fixture PASS (FR-010 tests drive real resolvers + `check_pre30_layout` non-fakeably);
3 Silent-empty-return PASS; 4 FR-coverage **FAIL** (FR-010 move_task pin — Issue 1);
5 Frozen-surface PASS; 6 Locked-decision PASS; 7 Shared-file — WP09 gate files (Note A);
8 Production-fragility N/A.
