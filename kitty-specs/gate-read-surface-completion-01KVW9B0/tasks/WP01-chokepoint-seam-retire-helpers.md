---
work_package_id: WP01
title: Chokepoint seam adoption + retire bespoke primary-anchor helper pair
dependencies:
- WP00
requirement_refs:
- FR-004
- FR-009
tracker_refs:
- '#2107'
- '#2085'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation (Lane A spine)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4022146"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_gate_read_chokepoint.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission.py
- tests/specify_cli/cli/commands/agent/test_gate_read_chokepoint.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Chokepoint seam adoption + retire bespoke primary-anchor helper pair

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on
`authoritative_surface: src/specify_cli/cli/commands/agent/`.

---

## Objective

Establish the **single kind-aware read chokepoint** that every gate command will
consume, and **retire the bespoke primary-anchor helper pair** in `mission.py` onto
it. This is the **foundation** of Lane A: WP02–WP06 converge their gate-read sites
onto the seam this WP confirms.

The seam already exists — `resolve_planning_read_dir(repo_root, mission_slug, *, kind)`
at `src/specify_cli/missions/_read_path_resolver.py:1244` (live-verified: it splits
PRIMARY-partition kinds → `primary_feature_dir_for_mission` vs STATUS-partition kinds
→ the topology-aware `candidate_feature_dir` at `:1302-1308`). **Do NOT introduce a new
resolver** (C-001/C-006). The kind lookup already exists too: `_ARTIFACT_TYPE_TO_KIND`
at `mission.py:1106` (`_artifact_kind_for` at `:1120`, with a no-silent-default raise at
`:1124`).

The work is **adoption + retirement without behavior drift**: provide ONE module-level
chokepoint helper in `mission.py` that wraps `_artifact_kind_for` + `resolve_planning_read_dir`,
and fold the bespoke primary-anchor helper pair onto it.

This is brownfield consolidation — **one canonical seam, N callers, no parallel impl**
(FR-009).

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-004, FR-009; C-001, C-005, C-006.
- [plan.md](../plan.md) IC-01.
- [data-model.md](../data-model.md) "Kind → read surface" rule + the planning-read site
  map rows 12-13 (`mission.py:1308,1327`).
- [contracts/gate-read-seam.md](../contracts/gate-read-seam.md) the seam contract +
  G-4 (no command reconstructs a planning-read path).
- [research.md](../research.md) Decision 1 (seam exists; adoption not invention),
  Decision 2 (4 workarounds, this WP retires the helper pair).

The bespoke pair (live-verified):
- `_resolve_mission_dir_name_primary_anchored` (`mission.py:1288-1325`) — the workhorse:
  resolves a mission handle → primary-checkout dir NAME, anchoring to
  `primary_feature_dir_for_mission` with a PRIMARY-ONLY `.is_dir()` existence check, and
  canonicalizes the handle. Propagates `MissionSelectorAmbiguous`.
- `_primary_anchored_feature_dir` (`mission.py:1327-1357`) — the Path-returning companion;
  returns `None` (caller falls back to the coord-aware resolver) when no explicit handle.

These two anchor planning reads to the primary surface ad-hoc. Post-WP01 they must route
through the canonical seam so `finalize-tasks`/`check-prerequisites` (already-primary,
NOT residual — leave their semantics) and the residual sites (WP02/04) share ONE locus.

**Negative scope**: do NOT add migration logic (C-004, forward-only). Do NOT change the
STATUS read leniency (C-002 — those stay coord-aware). Do NOT introduce a parallel
resolver (C-001).

## Branch Strategy

- **Strategy**: `shared-lane` (Lane A — the gate-read spine; sequential on `mission.py`)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> `lanes.json` (written at finalize-tasks) governs the actual lane. **WP01 OWNS
> `mission.py` for Lane A.** WP02/WP04 also edit distinct `mission.py` regions
> (setup_plan / record-analysis) but depend on WP01 and serialize behind it; their
> `mission.py` edits are well-justified out-of-map edits recorded with a one-line
> rationale. The no-overlap `owned_files` rule guards parallel collisions; the
> WP01→WP02→WP04 dependency chain serializes the shared file.

## Subtasks & Detailed Guidance

### Subtask T001 – Add the canonical read chokepoint helper

- **Purpose**: One module-level function in `mission.py` that maps `(artifact_type)` →
  kind → read dir via the seam — the single locus every gate read consumes.
- **Files**: `src/specify_cli/cli/commands/agent/mission.py`.
- **Steps**:
  1. Add a module-level helper near the `_ARTIFACT_TYPE_TO_KIND` map (`:1106`) and
     `_artifact_kind_for` (`:1120`):
     ```python
     def _planning_read_dir(repo_root: Path, mission_slug: str, *, artifact_type: str) -> Path:
         """Resolve the read dir for a planning artifact via the single kind-aware seam.

         The canonical chokepoint (FR-004/FR-009): a PRIMARY-kind artifact resolves to
         the primary ``target_branch`` dir for ALL topologies; a STATUS/bookkeeping kind
         resolves to its placed surface (coord under coord topology). No gate command may
         reconstruct this via topology routing or a bespoke primary-anchor helper.
         """
         from specify_cli.missions._read_path_resolver import resolve_planning_read_dir

         kind = _artifact_kind_for(artifact_type)
         return resolve_planning_read_dir(repo_root, mission_slug, kind=kind)
     ```
  2. Keep the import import-late (module already does this for resolver imports — match
     the local style).
- **Notes**: `_artifact_kind_for` already raises on an unmapped `artifact_type` (no silent
  default, `:1124`) — preserve that. Do NOT add a `kind=` default anywhere.

### Subtask T002 – Retire `_primary_anchored_feature_dir` onto the seam

- **Purpose**: Fold the Path-returning helper onto the chokepoint so the planning-read
  anchor flows through ONE locus (FR-009 (c)/(d)).
- **Files**: `src/specify_cli/cli/commands/agent/mission.py` (`_primary_anchored_feature_dir`,
  `:1327-1357`).
- **Steps**:
  1. Re-implement `_primary_anchored_feature_dir` to delegate to `_planning_read_dir`
     for the planning-artifact partition while preserving its two load-bearing behaviors:
     (a) returns `None` when no explicit handle (so the caller falls back to the
     coord-aware resolver — KEEP this contract); (b) propagates `MissionSelectorAmbiguous`
     (never silently resolves an ambiguous handle — C-009).
  2. Where the helper currently calls `primary_feature_dir_for_mission` directly, route
     through `resolve_planning_read_dir(..., kind=...)` instead (the seam wraps that
     primitive for primary kinds — verified at `_read_path_resolver.py:1306`), so there
     is no parallel primary-anchor path left.
- **Notes**: This helper is the **planning-authoring surface companion** to finalize-tasks'
  input read — both must anchor to the SAME primary surface. The seam preserves that
  (PRIMARY kind → `primary_feature_dir_for_mission`). Verify the `None`-on-no-handle and
  ambiguity-propagation paths are byte-equivalent in behavior.

### Subtask T003 – Retire `_resolve_mission_dir_name_primary_anchored` (the workhorse)

- **Purpose**: Collapse the second member of the pair so no bespoke primary-anchor
  resolution survives (FR-009).
- **Files**: `src/specify_cli/cli/commands/agent/mission.py`
  (`_resolve_mission_dir_name_primary_anchored`, `:1288-1325`).
- **Steps**:
  1. Trace every caller of `_resolve_mission_dir_name_primary_anchored` (grep the module).
     Identify which need a dir NAME vs a Path.
  2. For callers reading a PLANNING artifact: route through `_planning_read_dir` /
     `_primary_anchored_feature_dir`. For the handle-canonicalization-only concern (the
     `.is_dir()` existence probe + `_canonicalize_handle`), KEEP that logic if it is NOT a
     planning-artifact read — it is handle resolution, not a planning path join. Do not
     over-reach: the FR-009 retirement targets the **planning-read** path reconstruction,
     not handle canonicalization.
  3. If, after routing the planning-read callers through the seam, the workhorse is reduced
     to pure handle canonicalization, narrow its docstring/name to reflect that (it is no
     longer a "primary-anchored planning-read" helper). If it becomes dead, remove it.
- **Notes**: Be conservative. The KEEP set in data-model.md (`check-prerequisites`,
  `finalize-tasks` verify, record-analysis WRITE) is already-primary and NOT residual —
  do not change their read SURFACE, only ensure they consume the one chokepoint where they
  read a planning artifact. The `#11 / #1718 / #1692` create-window comment at `:1305-1307`
  documents a KEEP transient (C-003) — preserve that fail-open-on-empty-coord intent (the
  seam's PRIMARY branch already honors it by reading primary directly).

### Subtask T004 – Confirm no parallel primary-anchor path remains (FR-009 audit)

- **Purpose**: Prove the consolidation — one seam, no surviving bespoke planning-read.
- **Files**: `src/specify_cli/cli/commands/agent/mission.py` (audit, no new logic).
- **Steps**:
  1. Grep `mission.py` for direct `primary_feature_dir_for_mission(` calls that feed a
     planning-artifact read; each must now go through `_planning_read_dir` (or be a
     declared KEEP — record-analysis write target, which is OK).
  2. Grep for `/ "spec.md"`, `/ "plan.md"`, etc. direct joins in gate-command entry
     functions — there should be none after WP01-04 (this WP retires the helper-pair
     contribution; WP06's ratchet will enforce the absence). Note any residual for the
     downstream WP that owns it (setup_plan → WP02; record-analysis/map-requirements → WP04).
  3. Record the audit result in the WP activity log so the WP06 ratchet author knows the
     consolidated baseline.

### Subtask T005 – Red-first chokepoint behavioral test (DIRECTIVE_034)

- **Purpose**: Prove the chokepoint resolves PRIMARY for a coord-topology mission's
  planning kind and STATUS-placed for a status kind — red-first via the helper.
- **Files**: new `tests/specify_cli/cli/commands/agent/test_gate_read_chokepoint.py`
  (or the nearest existing module — locate it; do not create a parallel tree).
- **Steps (red-first — DIRECTIVE_034)**:
  1. Write the test through the **pre-existing entry point** — `_planning_read_dir` and
     `_primary_anchored_feature_dir` (NOT `resolve_planning_read_dir` directly — that would
     be testing the seam, not the adoption). Assert:
     - `_planning_read_dir(repo, slug, artifact_type="spec")` on a **coord-topology**
       fixture → resolves the **primary** `target_branch` dir (NOT the coordination
       worktree).
     - For a STATUS-partition artifact_type, it resolves the placed (coord) surface.
     - A **flattened** fixture: both → `target_branch` (NFR-001 unchanged).
  2. **Add a behavioral assertion through an EXISTING caller** (reviewer-renata
     remediation): pick a pre-existing caller of the retired helper pair
     (`_primary_anchored_feature_dir` / `_resolve_mission_dir_name_primary_anchored`) and
     assert it still returns the SAME primary dir post-retirement (proves the retirement
     preserved behavior at a real call site, not only at the new helper). The
     `None`-on-no-handle fallback and `MissionSelectorAmbiguous` propagation MUST be
     asserted through that caller too.
  3. **Prove RED by reverting the new helper's BODY — NOT by relying on an ImportError**
     (reviewer-renata remediation; standing memory: ImportError-red ≠ red-first). Concretely:
     temporarily revert `_primary_anchored_feature_dir`'s body to the **pre-retirement
     primary-anchor call** (the bespoke `primary_feature_dir_for_mission` ad-hoc path), run
     the test, and confirm the behavioral assertion goes RED — the helper EXISTS, it is its
     body that is being proven. Restore, confirm GREEN. A "red" that is an ImportError on a
     not-yet-created symbol captures nothing and is rejected.
  3. **Composed-`<slug>-<mid8>` fixture (NFR-002 hazard)**: the primary dir MUST be named
     `<slug>-<mid8>` (a bare-slug dir is canonicalized and masks the coord/primary
     divergence — false green). Use a real 26-char ULID `mission_id` and its real 8-char
     `mid8`. Example: `mission_id="01KVW9B0XFXPKTBE77QT3KRSW8"`, `mid8="01kvw9b0"`,
     dir `gate-read-surface-completion-01kvw9b0`. NEVER a short fake slug.

## Test Strategy

- `pytest tests/specify_cli/cli/commands/agent/test_gate_read_chokepoint.py -q`.
- New helper MUST have tests in this WP (Sonar new-code coverage).
- `ruff check src/specify_cli/cli/commands/agent/mission.py` and
  `mypy src/specify_cli/cli/commands/agent/mission.py` — zero issues, zero warnings,
  no suppressions.

## Definition of Done

- [ ] `_planning_read_dir` chokepoint helper added, wrapping `_artifact_kind_for` +
  `resolve_planning_read_dir`; no new resolver introduced (C-001).
- [ ] `_primary_anchored_feature_dir` retired onto the seam; `None`-on-no-handle and
  `MissionSelectorAmbiguous` propagation preserved.
- [ ] `_resolve_mission_dir_name_primary_anchored` planning-read callers routed through
  the seam; handle-canonicalization-only logic kept or narrowed; dead code removed.
- [ ] FR-009 audit recorded: no parallel primary-anchor planning-read path survives in
  `mission.py` (residual setup_plan/record-analysis sites flagged for WP02/WP04).
- [ ] Red-first chokepoint test green; RED proven by **reverting the retired helper's BODY**
  to the pre-retirement primary-anchor call (NOT an ImportError on a missing symbol);
  composed `<slug>-<mid8>` fixture (NFR-002).
- [ ] A behavioral assertion through an EXISTING caller of the retired helper confirms the
  retirement preserved behavior (same primary dir; `None`-on-no-handle + ambiguity
  propagation intact) at a real call site.
- [ ] Flattened-mission read unchanged (NFR-001).
- [ ] ruff + mypy clean on the touched file; no suppressions.

## Risks & Mitigations

- **Over-retirement**: the workhorse mixes planning-read anchoring with handle
  canonicalization. Mitigation: only the planning-read path moves to the seam; canonical
  handle resolution stays (T003).
- **KEEP-transient regression (C-003)**: the create-window comment (`#1718`) means
  finalize-tasks must read primary even with an empty coord worktree. Mitigation: the
  seam's PRIMARY branch reads primary directly — preserves the fail-open intent. Add an
  assertion if feasible.
- **Shared `mission.py` (4125 LOC)**: WP02/WP04 edit other regions. Mitigation: WP01 owns
  the file; downstream WPs serialize behind the dependency edge.

## Review Guidance

- Confirm NO new resolver (C-001) — the chokepoint wraps the existing
  `resolve_planning_read_dir`.
- Confirm the helper-pair retirement preserved the `None`-on-no-handle fallback and
  ambiguity propagation (a regression here silently mis-resolves selectors).
- Confirm the red-first test used a composed `<slug>-<mid8>` primary dir, not a bare slug
  (else it is a false-green — ask for the red-run evidence).
- Confirm RED was proven by reverting the retired helper's **body** (not an ImportError on a
  missing symbol) AND that a behavioral assertion runs through an existing caller — a test
  that only exercises the new helper, red-via-ImportError, captures nothing.
- Confirm the FR-009 audit note lists the residual setup_plan/record-analysis sites for
  the downstream WPs (anti-"fixed N of M").

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T15:12:32Z – claude:opus:python-pedro:implementer – shell_pid=3970233 – Assigned agent via action command
- 2026-06-24T15:13:03Z – claude:opus:python-pedro:implementer – shell_pid=3971628 – Assigned agent via action command
- 2026-06-24T15:25:54Z – claude:opus:python-pedro:implementer – shell_pid=3971628 – FR-009 audit (T004): one chokepoint _planning_read_dir; both retired helpers route through it (mission.py:1344,1396). No parallel primary-anchor planning-read path survives in mission.py. Remaining direct primary_feature_dir_for_mission calls are DECLARED KEEP, not residual: _safe_load_meta:884 (meta.json mid8 read, already primary), record-analysis WRITE:2021 (data-model KEEP), finalize-tasks input read:3021 (data-model 'OK not residual'). Residual planning-READ sites for downstream WPs: setup_plan spec.md (mission.py:2224 -> WP02/IC-02), record-analysis double-resolution (mission.py:1980 -> WP04/IC-04). Direct dir/'spec.md' joins (1411,1782,2265-66,3072) are the legitimate post-resolution dir/artifact join, not path reconstruction.
- 2026-06-24T15:26:43Z – user – shell_pid=3971628 – WP01 chokepoint+retire helpers: advancing to claimed
- 2026-06-24T15:26:45Z – user – shell_pid=3971628 – WP01 chokepoint+retire helpers: advancing to in_progress
- 2026-06-24T15:28:18Z – user – shell_pid=3971628 – advance to claimed (re-walk after lane reset)
- 2026-06-24T15:28:20Z – user – shell_pid=3971628 – advance to in_progress (re-walk after lane reset)
- 2026-06-24T15:28:28Z – claude:opus:python-pedro:implementer – shell_pid=3971628 – WP01 ready for review: kind-aware chokepoint _planning_read_dir + retired primary-anchor helper pair onto the seam (no new resolver C-001; None-on-no-handle + ambiguity propagation preserved); FR-009 audit recorded; red-first body-revert proof on composed slug-mid8 fixture; ruff+mypy clean on new code.
- 2026-06-24T15:29:48Z – user – shell_pid=3971628 – Lane-b code d92cded60; status from main
- 2026-06-24T15:29:50Z – claude:opus:reviewer-renata:reviewer – shell_pid=4022146 – Started review via action command
- 2026-06-24T15:36:23Z – user – shell_pid=4022146 – Review passed (reviewer-renata): C-001 confirmed — _planning_read_dir wraps existing resolve_planning_read_dir+_kind_for_artifact, NO new resolver. Independent red-first proof: reverting chokepoint body to coord-aware candidate_feature_dir_for_mission makes BOTH new-helper AND existing-caller (_primary_anchored_feature_dir) tests resolve the -coord husk instead of primary -> 3 RED, restored -> 7 GREEN (content-anchored, not ImportError). Not dead code: callers at mission.py:1350/1402, consumed by check-prerequisites:1904 + finalize-tasks:2962. Behavior preserved: None-on-no-handle + MissionSelectorAmbiguous->ActionContextError + handle-canonicalization KEPT (asserted via existing caller). FR-009 audit accurate — only residual primary_feature_dir_for_mission calls are spec-sanctioned KEEPs (884 meta read, 2027 record-analysis WRITE, 3027 finalize input). mypy: 3 no-any-return errors CONFIRMED pre-existing on base d45773098 (lines 1025/2586/4125 -> shift to 1025/2633/4172); new helper mypy+ruff clean, no suppressions. Pre-existing unrelated failures in test_feature_finalize_bootstrap.py (lane-collapse) reproduce on base, zero coupling to WP01 symbols — non-blocking.
