---
work_package_id: WP01
title: FOUNDATION — handle-safe PRIMARY read seam (caller-canonicalize bare mid8/slug at resolve_planning_read_dir; primitive stays blind)
dependencies: []
requirement_refs:
- FR-011
tracker_refs:
- '#2136'
- '#2119'
planning_base_branch: fix/3.2.3-coord-surface-regressions
merge_target_branch: fix/3.2.3-coord-surface-regressions
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.3-coord-surface-regressions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.3-coord-surface-regressions unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 0 - Foundation (lands FIRST; every PRIMARY read/write inherits handle-safety)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1706450"
history:
- at: '2026-06-25T19:36:37Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (planner-priti)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/_read_path_resolver.py
create_intent:
- architecture/3.x/adr/2026-06-25-1-terminal-artifact-durable-home-teardown.md
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
- tests/missions/test_surface_resolution_equivalence.py
- architecture/3.x/adr/2026-06-25-1-terminal-artifact-durable-home-teardown.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 — FOUNDATION: handle-safe PRIMARY read seam

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the best
match for `task_type: implement` on `authoritative_surface:
src/specify_cli/missions/_read_path_resolver.py`.

---

## Objective

**Make the PRIMARY *read* entry point handle-safe by canonicalizing in the CALLER, while keeping
the topology-blind primitive blind.** Today the kind-aware read seam `resolve_planning_read_dir`
(`src/specify_cli/missions/_read_path_resolver.py:1244`) feeds a **raw** handle straight into the
topology-blind primitive on its PRIMARY-partition leg at `:1306`:

```python
if is_primary_artifact_kind(kind):
    return primary_feature_dir_for_mission(repo_root, mission_slug)   # :1306 — raw handle!
```

`primary_feature_dir_for_mission` (`:1212`) is **deliberately handle-blind by contract**
(docstring `:1213`) — it does a raw literal compose at `:1240`
(`get_main_repo_root(...) / KITTY_SPECS_DIR / mission_slug`). So a bare `mid8` (e.g.
`01kvym1w`) or a bare human `slug` passed at `:1306` composes a *different* directory than the
canonical `<slug>-<mid8>` — a silent divergence. #2136 names this "the same root behind #2119".

**⚠️ DO NOT canonicalize INSIDE `primary_feature_dir_for_mission` — it is infinite recursion.**
`_canonicalize_bare_modern_handle` (`:418`) calls `primary_feature_dir_for_mission` at `:454`
(verify live), so folding canonicalization into the primitive recurses forever. The primitive
MUST stay handle-blind. The live exemplars `:1204`/`:1208` and `:820` show the correct shape:
they canonicalize **in the caller** via `_canonicalize_bare_modern_handle` and pass the
*canonical* handle DOWN to the blind compose. WP01 mirrors that exemplar on the read seam.

**Ownership split (no overlap with WP03):** WP01 owns the **READ-leg** canonicalization in
`_read_path_resolver.py` (`resolve_planning_read_dir:1306`). The **WRITE-leg** canonicalization at
the retrospective placement sites (`writer.py`, `lifecycle_events.py`, the two
`retrospective_terminus.py`) is owned by **WP03** (FR-001/003) — those are WP03's `owned_files`,
not WP01's. Both reuse the SAME shared helper `_canonicalize_bare_modern_handle`. No file overlap.

**This is the FOUNDATION WP for the read side. WP02 (kind/authority) and WP03 (write consolidation
+ write-leg canonicalization) build ON it.**

## The fix (live-verified on `e36547461` / HEAD)

| Anchor | Line | Verified |
|--------|------|----------|
| `def resolve_planning_read_dir(...)` (the seam WP01 edits) | `_read_path_resolver.py:1244` | ✅ |
| raw PRIMARY-leg call into the blind primitive (the bug) | `:1306` | ✅ `return primary_feature_dir_for_mission(repo_root, mission_slug)` |
| `def primary_feature_dir_for_mission(...)` — STAYS BLIND (do NOT edit its body) | `:1212` | ✅ blind by contract (docstring `:1213`) |
| recursion proof: `_canonicalize_bare_modern_handle` calls the primitive | `:454` | ✅ `primary_feature_dir_for_mission(repo_root, handle)` — seam-internal canon = infinite recursion |
| `def _canonicalize_bare_modern_handle(repo_root, handle)` (REUSE) | `:418` | ✅ |
| `def _canonicalize_handle(...)` (identity machinery REUSE) | `:467` | ✅ `mission_id`→`mid8`→numeric→`slug` |
| `class MissionSelectorAmbiguous(Exception)` | `:42` | ✅ |
| caller-canonicalization exemplars (COPY their call shape) | `:1204`/`:1208`, `:820` | ✅ caller canonicalizes, passes canonical handle to blind compose |

The cure: canonicalize **in `resolve_planning_read_dir`'s PRIMARY leg** by reusing the EXISTING
`_canonicalize_bare_modern_handle` (`:418`) — which internally calls `_canonicalize_handle`
(`:467`) — **NO parallel/bespoke resolver** (C-006), and **NO edit to the blind primitive's body**.
The `meta.json`-present and unresolvable-handle short-circuit legs of
`_canonicalize_bare_modern_handle` MUST stay no-ops (back-compat). **No-silent-fallback** (C-009 /
WP07 regression): an ambiguous handle MUST propagate `MissionSelectorAmbiguous`, never a silent pick.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) **FR-011** + **NFR-005** + **SC-007**, and **C-006** (no parallel
  resolver; no silent fallback).
- [data-model.md](../data-model.md) "Entity — handle-safe PRIMARY entry points".
- [contracts/terminal-artifact-teardown-contract.md](../contracts/terminal-artifact-teardown-contract.md) **C0**.
- [research.md](../research.md) **Decision 7** (caller-canonicalization; seam-internal rejected as recursion).

**Negative scope:**
- **Do NOT canonicalize inside `primary_feature_dir_for_mission` (`:1212`) — infinite recursion**
  (`_canonicalize_bare_modern_handle:418` → `primary_feature_dir_for_mission:454`). The primitive
  STAYS handle-blind; do not touch its body.
- Do NOT introduce a new identity resolver — reuse `_canonicalize_bare_modern_handle` (C-006).
- Do NOT reintroduce a silent fallback (C-009 — this is the WP07 regression class).
- Do NOT touch the retrospective WRITE sites (`writer.py`, `lifecycle_events.py`, the two
  `retrospective_terminus.py`) — the WRITE-leg canonicalization is WP03's (FR-001/003), not WP01's.
- Do NOT change the `meta.json`-present or unresolvable-handle short-circuit legs.

## Branch Strategy

- **Strategy**: `foundation-lane` — lands FIRST; WP02/WP03 build on the handle-safe seam.
- **Planning base branch**: `fix/3.2.3-coord-surface-regressions`
- **Merge target branch**: `fix/3.2.3-coord-surface-regressions`

> WP01 OWNS `missions/_read_path_resolver.py` exclusively (the READ-leg canonicalization). No
> other WP touches it. **WP03 owns the WRITE-leg canonicalization** at the retrospective placement
> sites (`writer.py`, `lifecycle_events.py`, the two `retrospective_terminus.py`) — disjoint files,
> no overlap; both reuse the shared `_canonicalize_bare_modern_handle` helper. The ADR
> (`architecture/3.x/.../2026-06-25-1-...md`) lands with WP01 (its handle-safety Binding A is
> authored here; the placement + teardown bindings are refined as WP02/03/04 land).

## Subtasks & Detailed Guidance

### Subtask T011 — Red-first handle-equivalence + ambiguity matrix THROUGH the read seam (NFR-005 / SC-007)

- **Purpose**: Prove RED on the current raw read leg, through the REAL entry point
  `resolve_planning_read_dir` (NOT the blind primitive directly — drive the seam the bug lives in).
- **Files**: extend `tests/missions/test_surface_resolution_equivalence.py`.
- **Steps (red-first — DIRECTIVE_034)**:
  1. Build a fixture with a canonical PRIMARY dir `kitty-specs/<slug>-<mid8>/` carrying a real
     ULID `meta.json` (real-format ids: ULID 26 chars, mid8 = first 8 lowercase). Realistic
     test data — no handcrafted placeholders.
  2. Drive `resolve_planning_read_dir(repo_root, handle, kind=<a PRIMARY-partition kind>)` (the
     PRE-EXISTING entry point whose PRIMARY leg hits the blind primitive at `:1306`) three ways:
     a bare `mid8` handle, a bare `slug` handle, the pre-resolved `<slug>-<mid8>`.
  3. Assert **RED on current code**: the bare-`mid8` and bare-`slug` calls resolve to a
     *different* dir than the pre-resolved one (the raw-handle divergence at `:1306`).
  4. Add the **ambiguity** leg: two missions whose handles collide on the bare token → assert
     `resolve_planning_read_dir` raises `MissionSelectorAmbiguous` (never silently picks).
  5. Record the red-run evidence (run on pre-WP01 code; observe divergence). After T012, flip
     to GREEN: all three resolve to the SAME canonical dir; ambiguous still raises.
- **Notes**: a bare-slug-only fixture that is already canonical masks the divergence — use a
  genuine `<slug>-<mid8>` canonical dir so the bare handle has somewhere wrong to go. Driving the
  blind primitive directly would NOT exercise the cure (the primitive stays blind by contract) —
  drive the READ SEAM.

### Subtask T012 — Canonicalize the bare handle in the read seam's PRIMARY leg (caller-side)

- **Purpose**: Re-point `resolve_planning_read_dir`'s PRIMARY leg (`:1306`) through
  `_canonicalize_bare_modern_handle` BEFORE it calls the blind primitive — **the primitive stays
  blind**.
- **Files**: `src/specify_cli/missions/_read_path_resolver.py:1304-1306` (the `is_primary_artifact_kind`
  branch of `resolve_planning_read_dir`).
- **Steps**:
  1. In the `if is_primary_artifact_kind(kind):` branch (`:1304-1306`), BEFORE calling
     `primary_feature_dir_for_mission`, canonicalize the handle:
     `canonical = _canonicalize_bare_modern_handle(repo_root, mission_slug)` (reuse the in-module
     helper at `:418`). Mirror exactly how the live exemplars already wrap it — `:1204`/`:1208`
     (`_resolve_*` reading primary meta) and `:820` (`read_primary_meta`) are the closest exemplars;
     copy their call shape.
  2. Pass the canonical handle DOWN to the blind compose:
     `return primary_feature_dir_for_mission(repo_root, canonical)`. Do **NOT** edit
     `primary_feature_dir_for_mission`'s body — it remains handle-blind by contract (`:1213`).
  3. Confirm `_canonicalize_bare_modern_handle` already propagates `MissionSelectorAmbiguous`
     from `_canonicalize_handle` (`:467`) — do NOT swallow it; let it surface (C-009).
- **Notes**: this is the read-leg twin of the WP03 write-leg canonicalization (both reuse the same
  helper at disjoint call sites). The reused helper is already proven by the live exemplars
  (`:820`/`:1204`/`:1208`), so the behavior is not novel — only its application point is new.
  Leave the STATUS-partition leg (`candidate_feature_dir_for_mission`, `:1308`) UNTOUCHED — it
  already canonicalizes internally via `_resolve_mission_read_path`.

### Subtask T013 — Back-compat no-op proof (the short-circuit legs stay unchanged)

- **Purpose**: Prove the fix is a no-op for already-canonical / unresolvable handles.
- **Files**: `tests/missions/test_surface_resolution_equivalence.py` (additional cases).
- **Steps** (all driven through `resolve_planning_read_dir` on a PRIMARY-partition kind):
  1. A canonical `<slug>-<mid8>` handle → resolves to exactly the same dir as before (no-op).
  2. An unresolvable handle (no matching mission, no `meta.json`) → behaves EXACTLY as the
     pre-WP01 code (the unresolvable leg of `_canonicalize_bare_modern_handle` returns the
     handle unchanged → literal compose, same as today). Assert byte-identical resolution.
  3. A `meta.json`-present mission → the present-leg short-circuit is untouched.
  4. **Primitive-still-blind proof:** a direct call to `primary_feature_dir_for_mission(repo_root,
     <bare handle>)` STILL diverges (composes the literal bare name) — confirming the cure lives in
     the caller, not the primitive, and the primitive's blind contract is preserved.
- **Notes**: NFR-005 requires the `meta.json`-present and unresolvable-handle legs unchanged AND
  the blind primitive unchanged; this subtask is the proof.

### Subtask T014 — Author the ADR

- **Purpose**: Record the contract decision (DIRECTIVE_003).
- **Files**: new `architecture/3.x/adr/2026-06-25-1-terminal-artifact-durable-home-teardown.md`.
- **Steps**:
  1. Follow `architecture/README.md` template.
  2. **Binding A (authored here):** terminal artifacts resolve to the durable, **handle-safe**
     PRIMARY home via the `MissionArtifactKind` partition AND the handle-safe seam (#2136).
  3. Stub **Binding B** (persist-before-destroy teardown) as a forward reference to WP04 —
     WP04 does not own the ADR, so capture both bindings here; precedents #2101/#2090 (placement),
     #1716 (read twin).
- **Notes**: one ADR for the whole mission; WP01 owns it because the foundation lands first.

### Subtask T015 — Blast-radius regression sweep

- **Purpose**: `resolve_planning_read_dir` feeds planning reads, status, merge, and acceptance; the
  blind primitive has ~40 direct callers, so confirm none regress.
- **Files**: (no logic — test execution + audit recorded in the activity log).
- **Steps**:
  1. Run the full `tests/missions/` suite + `tests/integration/` locally (CI-only shards —
     run them HERE, the read seam is high-blast-radius).
  2. Grep direct callers of `primary_feature_dir_for_mission` and confirm they fall into exactly
     two groups: (a) callers that already pre-canonicalize (the live exemplars `:454`/`:820`/`:1204`/
     `:1208` and the WP03 write sites) — unaffected; (b) callers passing an already-canonical handle —
     unaffected (the primitive stays blind, so its contract is unchanged). No caller relied on the
     OLD raw-handle divergence at `:1306` (that was the bug).

## Test Strategy

- `PWHEADLESS=1 pytest tests/missions/test_surface_resolution_equivalence.py -q` — RED first,
  GREEN after; capture the red-run evidence.
- Full `tests/missions/` + `tests/integration/` locally (blast-radius).
- `ruff check src/specify_cli/missions/_read_path_resolver.py` + `mypy --strict` — zero issues, no
  suppressions. Keep the touched function at `maxCC ≤ 15` (NFR-004).

## Definition of Done

- [ ] `resolve_planning_read_dir`'s PRIMARY-partition leg (`:1306`) canonicalizes the bare handle
  via `_canonicalize_bare_modern_handle@418` BEFORE calling `primary_feature_dir_for_mission`
  (caller-side, mirroring the live exemplars `:1204`/`:1208`/`:820` — no parallel resolver, C-006).
- [ ] `primary_feature_dir_for_mission@1212` is **unchanged** (handle-blind by contract `:1213`) —
  NO canonicalization folded into its body (recursion-safety: `:418`→`:454`), proven by T013 step 4.
- [ ] Through `resolve_planning_read_dir` (PRIMARY kind): bare-`mid8` ≡ bare-`slug` ≡ `<slug>-<mid8>`
  all resolve to the SAME canonical PRIMARY dir; an ambiguous handle raises `MissionSelectorAmbiguous`
  (no silent fallback — C-009 / WP07).
- [ ] The `meta.json`-present and unresolvable-handle short-circuit legs are byte-identical
  (NFR-005), proven by T013.
- [ ] WP01 touches ONLY `_read_path_resolver.py` (read leg) — the WRITE sites are WP03's; no overlap.
- [ ] Red-first evidence captured (divergence on unfixed read seam, equivalence after).
- [ ] ADR `2026-06-25-1-terminal-artifact-durable-home-teardown.md` authored (Binding A here,
  Binding B forward-referenced to WP04).
- [ ] Full `tests/missions/` + `tests/integration/` green; ruff + `mypy --strict` clean, no suppressions;
  `maxCC ≤ 15`.

## Risks & Mitigations

- **Infinite recursion (the architectural trap):** mitigated by the negative scope — canonicalize
  in the CALLER (`resolve_planning_read_dir:1306`), NEVER inside `primary_feature_dir_for_mission`
  (which `_canonicalize_bare_modern_handle:418` calls at `:454`). The blind primitive stays blind;
  T013 step 4 proves it. Reviewer MUST reject a seam-internal canonicalization diff.
- **Read-seam blast radius:** `resolve_planning_read_dir` feeds planning reads/status/merge/accept;
  mitigated by (a) reusing the EXISTING helper the live exemplars (`:820`/`:1204`/`:1208`) already
  invoke (proven, not novel); (b) preserving the short-circuit legs (canonical/unresolvable → no-op);
  (c) leaving the STATUS-partition leg untouched; (d) running the full `tests/missions/` +
  `tests/integration/` suites HERE.
- **Silent-fallback regression (WP07 / C-009):** mitigated by the explicit ambiguity assertion
  in T011 — reviewer MUST confirm `MissionSelectorAmbiguous` surfaces, not a silent pick.
- **False-green from a bare-slug fixture:** mitigated by T011 using a genuine `<slug>-<mid8>`
  canonical dir so the bare handle has a *wrong* place to resolve, driven THROUGH the read seam.

## Review Guidance

- **Confirm the primitive `primary_feature_dir_for_mission@1212` body is UNCHANGED** — reject any
  diff that folds canonicalization into it (infinite recursion: `:418`→`:454`). The cure lives in
  the caller (`resolve_planning_read_dir:1306`).
- Confirm the canonicalization REUSES `_canonicalize_bare_modern_handle@418` at the caller — no new
  resolver (C-006). Reject any bespoke identity logic.
- Confirm `MissionSelectorAmbiguous` propagates (no silent pick) — ask for the ambiguity-leg
  assertion.
- Confirm red-first: the matrix proved divergence on the unfixed READ seam
  (`resolve_planning_read_dir`, not the blind primitive directly) (revert the src, observe the
  bare-handle resolving to the wrong dir, restore GREEN). Green-before-and-after is rejected.
- Confirm WP01 did NOT touch the WRITE sites (WP03 owns those) and the back-compat legs are
  unchanged (T013); the full `tests/missions/` + `tests/integration/` suites pass.

## Activity Log

- 2026-06-25T19:36:37Z – system – Prompt created via /spec-kitty.tasks (planner-priti); FR-011 foundation.
</content>
- 2026-06-25T20:59:12Z – claude:opus:python-pedro:implementer – shell_pid=1651843 – Assigned agent via action command
- 2026-06-25T21:17:26Z – claude:opus:python-pedro:implementer – shell_pid=1651843 – Ready: caller-canonicalization at the read seam (resolve_planning_read_dir PRIMARY leg via _canonicalize_primary_read_handle composing the two existing canonicalizers); primitive stays blind; equivalence + ambiguity + no-op + primitive-blind tests green; tests/missions/ 541 + tests/integration/ 508 pass; ruff/mypy --strict/C901 clean; ADR 2026-06-25-1 authored
- 2026-06-25T21:18:23Z – claude:opus:reviewer-renata:reviewer – shell_pid=1706450 – Started review via action command
- 2026-06-25T21:26:26Z – user – shell_pid=1706450 – renata APPROVE: caller-canonicalization sound, primitive stays blind, equivalence test mutation-probed RED, gates clean
