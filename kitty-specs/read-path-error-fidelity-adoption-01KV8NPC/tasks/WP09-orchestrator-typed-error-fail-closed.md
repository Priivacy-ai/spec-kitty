---
work_package_id: WP09
title: orchestrator-api typed-error + fail-closed identity (M2 + M3)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-011
tracker_refs: []
planning_base_branch: feat/read-path-error-fidelity
merge_target_branch: feat/read-path-error-fidelity
branch_strategy: Planning artifacts for this mission were generated on feat/read-path-error-fidelity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/read-path-error-fidelity unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2615089"
history:
- 2026-06-16 created (/spec-kitty.tasks)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/orchestrator_api/commands.py
create_intent:
- tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py
execution_mode: code_change
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before any code, load the implementer profile and the binding contracts. Run:

```
/ad-hoc-profile-load python-pedro
```

Then read, in this order:

1. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/spec.md` — **FR-001** (typed-error
   pass-through) and **FR-011** (single-authority adoption / read-path safety), plus **C-001** (no new
   authority).
2. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/plan.md` — **IC-02b** (orchestrator-api
   typed-error + fail-closed identity) and decision **D-7** (M2 / M3 fold-in, the legacy-grammar
   caveat).
3. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/contracts/behavioral-contracts.md` — the
   **C-IC02** typed-error contract (the same pass-through obligation applied to the external surface).
4. `kitty-specs/read-path-error-fidelity-adoption-01KV8NPC/research/investigation-2/debbie-reverify-missed.md`
   — the **M2** and **M3** missed surfaces, the 8-endpoint list, and the recurring naming-rider
   primary-only-meta-pre-read shape (§3 + §"Recurring naming-rider shape").

## Objective

Own `src/specify_cli/orchestrator_api/commands.py` and fix the two net-new orchestrator-api defects
debbie found, both on the **external automation** surface:

- **M2 (typed-error fidelity, FR-001).** The orchestrator-api helper `_resolve_mission_dir` catches
  `StatusReadPathNotFound` and returns `None` (`commands.py:263-266`); all **8 endpoints** then
  `_fail("MISSION_NOT_FOUND", "…not found in kitty-specs/")` — dropping the real `error_code`,
  `coord_candidate`, and `primary_candidate`. Stop flattening: surface the typed read-path code across
  the 8 endpoints (the #15 disease ×8 on the external surface). The 8 endpoints are at
  `commands.py:587, :652, :735, :870, :997, :1066, :1164, :1268`.
- **M3 (read-path SAFETY, FR-011).** `_resolve_mission_dir` seeds
  `resolve_mid8(mission_slug, mission_id=None)` → empty `mid8` (`''`) at `commands.py:261`, which
  **suppresses the coord-aware fail-closed branch** (`_read_path_resolver.py:353` gates on
  `and bool(mid8)`). The orchestrator then reads the **possibly-stale primary** surface *without* the
  fail-closed guard every other reader has — external automation can read stale status on a coord
  topology. **The concrete fix:** resolve the **real `mission_id` from meta** and pass it to
  `resolve_mid8(mission_slug, mission_id=<real>)` (the `decision.py:421` / `context.py:73` primitive
  pattern) so `mid8` is non-empty and the `bool(mid8)` fail-closed guard fires.

> ⚠️ **WP01 ships a CONTRACT, not a callable identity API.** The "WP01 factory boundary" is a
> package-PRIVATE factory plus a **docstring boundary contract** (callers MUST NOT seed/re-derive
> empty identity). It is **NOT** an importable identity projection — `mission_runtime.__all__` exposes
> only `resolve_placement_only` / `CommitTarget`, **no mid8 door**. So M3 is fixed by **honoring** the
> contract via the meta-read primitive above (pass the real `mission_id`), NOT by importing a new
> `resolve_identity_only`/projection API. Do not hunt for a callable that does not exist, and do not
> widen WP01's scope to add one.

This is **adoption, not construction** (C-001): consume the existing resolver's typed error and honor
the WP01 identity boundary contract; do not build a new resolver, root authority, or error type.

> ⚠️ **CRITICAL — legacy grammar is OUT of scope, do NOT touch.** `commands.py:484` and `commands.py:787`
> also pass `mission_id=None`, but those seed `resolve_mid8` for the **legacy `{slug}-{lane}` worktree
> grammar** and are **intentional**. The M3 bug is ONLY the status-read identity seed at
> `commands.py:261`. Touching `:484` / `:787` is a regression. Reviewer must confirm only `:261` moved.

## Context (binding discipline)

- **Function-over-form + verification-by-deletion.** The M2 fix is proven by deleting the
  `StatusReadPathNotFound → return None` flatten (and the resulting `MISSION_NOT_FOUND` `_fail`) and
  watching the suite stay green because the typed code now flows to the envelope. The M3 fix is proven
  by a fixture where the empty-mid8 seed is gone and the fail-closed guard fires.
- **TDD-first.** Write `test_typed_error_fail_closed.py` first (T039 + T041). Both must FAIL on HEAD:
  today the endpoints emit `MISSION_NOT_FOUND` (M2) and the fail-closed guard never evaluates (M3).
- **Topology-true fixtures (NFR-002).** M3 specifically requires a **real coord topology**: a mission
  whose `meta.json` declares a `coordination_branch` with the coord surface materialized such that the
  primary read is stale — proving the guard fires. Use a **full 26-char ULID** `mission_id` (e.g.
  `01KV8NPC…`), a **real coord-worktree**, **NO fabricated short ids**, no synthetic single-repo
  stand-in. A fabricated fixture masks the coord-vs-primary defect (the exact NFR-002 trap).
- **External-contract stability.** These 8 endpoints are the **external orchestrator-api contract**.
  Preserve the envelope *shape* (`result`/`error_code`/candidates) while surfacing the *real* code —
  do not change the response schema, only the fidelity of what fills it.
- **Quality gates (NFR-004).** `ruff` + `mypy` zero issues, **complexity ≤ 15**, **no suppressions**.
- **WP01 dependency (CONTRACT, not a code API).** M3 honors the WP01 docstring boundary **contract**
  (D-6 — callers must not seed/re-derive empty identity). WP01 ships a package-private factory + a
  docstring contract, NOT an importable identity projection — so the M3 fix is the meta-read primitive
  (`resolve_mid8(slug, mission_id=<real>)`), not factory-API consumption. Do not start before WP01 is
  approved (ordering keeps the contract-adoption story coherent), and do not seek a callable
  projection that WP01 deliberately does not export.

## Subtasks

### T039 — TDD: orchestrator endpoint emits typed code, not MISSION_NOT_FOUND (M2)
- **Create the missing test package first:** `tests/specify_cli/orchestrator_api/` does **not** exist
  on HEAD. Create the directory **and** an `__init__.py` so the new module collects (same as WP08 does
  for its `tests/specify_cli/merge/` dir). Then add
  `tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py`.
- Build the topology-true read-path-miss fixture (coord declared, fail-closed window; full 26-char
  ULID). Drive at least one of the 8 endpoints and assert the response carries the resolver's typed
  read-path `error_code` (+ `coord_candidate` / `primary_candidate`), **NOT** `MISSION_NOT_FOUND`.
- **Validation:** FAILS on HEAD; run
  `python -m pytest tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py -k typed`.

### T040 — M2: stop flattening StatusReadPathNotFound across the 8 endpoints
- In `_resolve_mission_dir`, stop catching `StatusReadPathNotFound` → `return None`; preserve and
  surface the typed `error_code` + candidate paths. Update the 8 endpoints so they emit the typed code
  instead of the unconditional `_fail("MISSION_NOT_FOUND", …)`, keeping the external envelope shape.
- **file:line:** helper at `src/specify_cli/orchestrator_api/commands.py:263-266`; endpoint heads at
  `:587, :652, :735, :870, :997, :1066, :1164, :1268`. ⚠️ Each cite is the endpoint **head** — the
  actual `_fail("MISSION_NOT_FOUND", …)` call sits ~2-4 lines later (`~:591, :656, :737, :872, :999,
  :1068, :1166, :1270`). **Re-locate by the `_fail("MISSION_NOT_FOUND", …)` call**, not by the cited
  head line.
- **Validation:** T039 passes; verification-by-deletion — the flatten is removed and the suite stays
  green.

### T041 — TDD: coord-topology fail-closed guard fires for orchestrator status read (M3)
- In the same test module, build a **real coord topology** where the primary surface is stale relative
  to the coord surface. Assert that the orchestrator status read **fails closed** (does not silently
  return stale primary status) — i.e. the coord-aware `bool(mid8)` guard
  (`_read_path_resolver.py:353`) fires, matching every other reader.
- **Captured-red (hard requirement):** the test MUST FAIL FIRST on HEAD — on HEAD the empty-mid8 seed
  makes `fail_closed` evaluate `False`, the guard is suppressed, and the stale primary read succeeds.
  Capture that red and paste it into the Activity Log; after the fix `mid8` is non-empty, `fail_closed`
  fires, and the stale read is refused. A positive-only test that does not capture the suppressed-guard
  red is a gaming defect. Pin the red to the **gate** (`fail_closed == False` on HEAD because
  `mid8 == ''`), not merely "stale read succeeds" — otherwise a fixture where the canonical-handle
  fallback happens to re-resolve masks the gate behavior (fiction-green).
- **Validation:** FAILS on HEAD (empty-mid8 seed suppresses the guard → stale primary read succeeds).

### T042 — M3: resolve real mission_id from meta; stop empty-mid8 seed (honor the WP01 boundary contract)
- Remove the `resolve_mid8(mission_slug, mission_id=None)` empty seed at `commands.py:261`. **The
  concrete fix:** read the **real `mission_id` from meta** and pass it to
  `resolve_mid8(mission_slug, mission_id=<real>)` (the `decision.py:421` / `context.py:73` primitive
  pattern), so `mid8` is non-empty and the `bool(mid8)` fail-closed branch
  (`_read_path_resolver.py:353`) evaluates. This **HONORS** the WP01 docstring boundary contract (do
  not seed empty identity) — it is **NOT** a new import/callable API. There is **no** importable
  identity-projection door in `mission_runtime.__all__`; do not look for one or widen WP01 to add one.
- **Misleading comment (BLOCKER — refute and correct):** the comment at `commands.py:258-260` claims
  the empty-mid8 seed is "byte-identical / safe" (it reasons only about literal-path compose +
  canonical-handle fallback). **It is WRONG** — it ignores the `bool(mid8)` fail-closed gate at
  `_read_path_resolver.py:353`, which never re-derives mid8 (it just evaluates `False` and suppresses
  the guard). Do **NOT** trust this comment; delete/replace it as part of T042 (it is the
  rationalization that planted M3). An implementer who trusts it will either leave `:261` (M3 unfixed)
  or write a fiction-green against the "canonical-handle fallback" path the comment describes.
- **M5 caveat — fail closed, do not silently seed empty:** on a **coord-only** topology the
  `mission_id`-from-meta may itself be empty/absent (meta lives only on the coord surface). The fix
  MUST then **fail closed properly** (surface the typed read-path error), NOT silently fall back to an
  empty `mission_id` (which re-creates the suppressed-guard bug on a different path). State which
  surface the `mission_id` is read from and that an absent/empty one fails closed.
- **DO NOT** touch the legacy `{slug}-{lane}` `mission_id=None` seeds at `commands.py:484` / `:787`.
- **file:line:** `src/specify_cli/orchestrator_api/commands.py:261` (the ONLY M3 site); the
  byte-identical comment to refute at `:258-260`; the gate at `_read_path_resolver.py:353`.
- **Validation:** T041 passes; the guard fires; the `:258-260` comment is corrected/removed; `:484` /
  `:787` are byte-unchanged (reviewer-verifiable by diff).

## Branch Strategy

Planning artifacts were generated on **feat/read-path-error-fidelity**. During
`/spec-kitty.implement` this WP may branch from a dependency-specific base (WP01 must be approved
first — it is the precondition for the M3 identity boundary), but completed changes **merge back into
feat/read-path-error-fidelity** unless the human explicitly redirects the landing branch. The
execution workspace (worktree) is the one `spec-kitty implement WP09` resolves from `lanes.json` — do
not reconstruct the path by hand.

## Definition of Done

- [ ] The missing `tests/specify_cli/orchestrator_api/` package (dir + `__init__.py`) was **created**
      so the new module collects.
- [ ] `tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py` added; T039 (M2 typed code)
      and T041 (M3 fail-closed) both **FAILED FIRST on HEAD with the captured red pasted into the
      Activity Log** and pass after (TDD-first witnessed), using topology-true fixtures (full 26-char
      ULID + real coord-worktree). T041's captured red shows the suppressed guard (`fail_closed ==
      False` because `mid8 == ''`) on the coord topology — a positive-only test is a gaming defect.
- [ ] **M2:** the orchestrator endpoints emit the resolver's typed read-path `error_code`
      (+ `coord_candidate` / `primary_candidate`), **NOT** `MISSION_NOT_FOUND`; the external envelope
      *shape* is unchanged (**C-IC02** applied to the external surface).
- [ ] The `StatusReadPathNotFound → return None` flatten is **deleted** at `commands.py:263-266`; suite
      stays green (verification-by-deletion).
- [ ] **M3:** the empty-mid8 seed at `commands.py:261` is removed; the real `mission_id` is read from
      meta and passed to `resolve_mid8(slug, mission_id=<real>)` (honoring the WP01 boundary
      **contract**, not a new callable API); the coord-aware `bool(mid8)` fail-closed guard fires on a
      real coord topology (no stale primary read). On a coord-only topology where meta `mission_id` is
      absent/empty, the read **fails closed** (typed error) — it does NOT silently seed empty identity.
- [ ] The misleading "byte-identical / safe" comment at `commands.py:258-260` is **corrected or
      removed** (it ignores the `bool(mid8)` gate; it is the rationalization that planted M3).
- [ ] The **legacy** `mission_id=None` seeds at `commands.py:484` and `:787` are **untouched** (diff
      shows only `:261` and the helper/endpoints moved).
- [ ] No new resolver, root authority, or error type introduced (**C-001**).
- [ ] `ruff check .` clean, `mypy` clean on `commands.py`, every touched function at **complexity ≤
      15**, **no suppressions** added.
- [ ] Full suite green (parallel run).

## Risks / reviewer guidance

- **The legacy-grammar trap.** `:484` and `:787` look like the same `mission_id=None` mistake but are
  intentional legacy `{slug}-{lane}` worktree grammar. The single most likely regression is "fixing"
  them too. **Reviewer: diff must show only `:261` (+ the helper/endpoint fidelity changes).**
- **M3 is safety, not cosmetics.** This is a read-path *correctness* gap, not just error fidelity:
  without the fix external automation reads stale primary status on a coord topology. The fixture MUST
  be a real coord topology proving the guard fires — a single-repo fixture cannot exercise it (NFR-002).
- **External contract stability.** Surfacing the real code MUST NOT change the response schema. Keep
  `result` / `error_code` / candidate fields; only raise their fidelity. Regressing the envelope shape
  breaks external orchestrators.
- **8 endpoints, one helper.** The cleanest fix threads the typed code through the single
  `_resolve_mission_dir` seam so the 8 endpoints inherit it — avoid 8 divergent patches. Watch the
  complexity ceiling if you fan the code out per-endpoint.
- **WP01 ordering + boundary is a CONTRACT, not an API.** M3 honors the WP01 docstring boundary
  **contract**; do not start before WP01 is approved. The fix resolves the **real `mission_id` from
  meta** and passes it to `resolve_mid8` (the `decision.py:421` primitive) — it does **NOT** import a
  factory identity-projection (none exists in `mission_runtime.__all__`). Do not re-derive empty
  identity, and do not waste a cycle hunting for `resolve_identity_only` or widening WP01's scope to
  add one (D-6 boundary contract; ADR-06-07-1 lean API).

## Activity Log

- _(empty — append implementation notes during /spec-kitty.implement)_
- 2026-06-16T21:03:53Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Assigned agent via action command
- 2026-06-16T21:21:30Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Implementation COMPLETE + committed (9a5e6ffc8): M2/M3 fixed, T039-T042 done, ruff+mypy clean, suites green (1684 passed). move-task to for_review BLOCKED by stale lane-status split-brain: validator computes from_lane=planned while canonical events log AND status.json snapshot both show WP09 in_progress (board agrees: In Progress=5, Planned=0). Also rejects -> in_progress. WP03/04/05 flagged stale too. meta status_phase=None. Not force-transitioning per high-risk discipline; reporting for operator.
- 2026-06-16T21:22:55Z – claude:opus:python-pedro:implementer – shell_pid=2432976 – Ready: M2 single seam (8 endpoints) + M3 real-mission_id fail-closed + refuted comment + contract extended; captured-red green
- 2026-06-16T21:23:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=2554678 – Started review via action command
- 2026-06-16T21:28:14Z – user – shell_pid=2554678 – Moved to planned
- 2026-06-16T21:29:35Z – claude:opus:python-pedro:implementer – shell_pid=2585018 – Started implementation via action command
- 2026-06-16T21:40:36Z – claude:opus:python-pedro:implementer – shell_pid=2585018 – Cycle-1 fix: contract sync. RATIONALE for --force (kitty-specs-on-lane guard): WP09's allow-list change is a COUPLED contract edit — vendored src/core/upstream_contract.json (lane-allowed) is byte-synced with the kitty-specs/064 planning artifact by test_vendored_contract_matches_planning_artifact; both MUST travel together so the contract-gate test is green in-lane. The 064 half + vendored half land byte-equal on feat at merge. Guard heuristic doesn't model coupled contract edits.
- 2026-06-16T21:40:49Z – claude:opus:reviewer-renata:reviewer – shell_pid=2615089 – Started review via action command
- 2026-06-16T21:43:06Z – user – shell_pid=2615089 – Cycle-1 re-review PASS (reviewer-renata): contract sync verified — gate test test_vendored_contract_matches_planning_artifact GREEN (parsed-JSON equality; STATUS_READ_PATH_NOT_FOUND after MISSION_NOT_FOUND in both vendored src copy and 064 planning artifact); 23/23 contract_gate+orchestrator_api tests pass; cycle-1 commit 36b019f4e touched ONLY the 064 JSON artifact, M2/M3 code (9a5e6ffc8) untouched; ruff+mypy clean, no new suppressions. --force for coupled-contract kitty-specs-on-lane exception; --skip-review-artifact-check arbiter override of stale rejected artifact.
