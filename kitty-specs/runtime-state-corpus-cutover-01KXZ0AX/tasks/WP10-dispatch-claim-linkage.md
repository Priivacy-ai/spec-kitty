---
work_package_id: WP10
title: Dispatch→claim linkage + backfill re-seed
dependencies:
- WP09
requirement_refs:
- FR-013
- FR-014
planning_base_branch: feat/runtime-state-corpus-cutover
merge_target_branch: feat/runtime-state-corpus-cutover
branch_strategy: Planning artifacts for this mission were generated on feat/runtime-state-corpus-cutover. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/runtime-state-corpus-cutover unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
- T041
- T042
agent: "claude"
shell_pid: "512547"
shell_pid_created_at: "1784575185.83"
history:
- timestamp: '2026-07-20T08:39:02Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
create_intent:
- tests/specify_cli/status/test_resolved_binding_linkage.py
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/invocation/record.py
- src/specify_cli/migration/backfill_runtime_state.py
- tests/specify_cli/status/test_resolved_binding_linkage.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

**Before any other action, load your agent profile so you inherit the correct identity,
governance scope, and boundaries for this work package.**

```bash
spec-kitty charter context --action implement --profile python-pedro
```

You are **`python-pedro`** — a Python-specialist implementer working in `role: implementer`.
Apply TDD/ATDD discipline, type safety (`mypy --strict`), and idiomatic Python 3.11+ practice.
Honour the charter's Quality & Tech-Debt Standing Orders: red-first tests, campsite cleaning,
canonical sources, no suppression. If the charter and this prompt ever disagree, the charter
wins — flag the drift rather than silently choosing.

---

## Objective

Close the **dispatch→claim linkage** (IC-08 / FR-014): thread the *genuinely dispatch-resolved*
`model` + `agent_profile` (+`invocation_id`) from the invocation/Op path into the implement and
review commands, record it as the WP's **resolved binding** at each claim seam, and extend the
backfill to re-seed historical resolved bindings under a **new** seed namespace. Then re-run the
dogfood backfill so IC-07's reader (WP11) reads populated resolved slots corpus-wide.

This is the mission's **largest scope-growth** WP: it spans the invocation layer, the command
surface, the claim seams, the reducer/emit annotation path, and the backfill. The single
load-bearing rule threaded through every subtask: **the recorded resolved `model`/`profile`/`role`
MUST originate from the dispatch resolver or `resolve_profile`/`resolved_agent()` — NEVER a copy of
the frontmatter `agent_profile` string** (C-007 / INV-6). Where a genuine model is unavailable on a
path, record it **explicitly absent**, never fabricated or frontmatter-coerced (SC-011).

WP09 has already landed the resolved-binding **vocabulary** (the `role`/`agent_profile`
(+`agent_profile_version`)/`model`/`provider` slots on `WPInnerStateDelta`, the reducer
`_RUNTIME_SLOTS` + `_apply_annotation_delta` fold, and the C-009 field-authority ADR). This WP
consumes that vocabulary — it does not re-add it.

---

## Context & grounding

Read these before editing. The linkage decision is **operator-forced** (Q1, 2026-07-20): full
model-actual now, over the leaner resolve-at-seam.

- **plan.md → IC-08** ("Dispatch→claim linkage", "Emit shape (annotation + actor, reconciled)",
  "Historical binding non-seed (C-011)"): the claim seam has ONLY the bare `--agent` string +
  frontmatter-coerced values; the genuine resolution lives on the dispatch/Op path; thread it in.
  Emit BOTH an annotation (latest-wins at both claim points) AND enrich the structured `actor`.
  Keep authored historical recommendations out of resolved-actual events and correct any earlier
  deterministic fabricated seed rows by exact ID.
- **spec.md → US6 + FR-013/FR-014 + C-007/C-011 + SC-008/SC-011.** FR-014 is this WP's spine
  (dispatch→claim linkage). FR-013's "recorded value MUST come from `resolve_profile`/
  `resolved_agent()`, never the frontmatter string" is the hard constraint. SC-011: genuine
  dispatch-resolved `model`, explicitly absent where unavailable, never fabricated.
- **research.md → D-10 and D-12.** D-12 is the linkage decision: the claim seam has only the bare
  `--agent` string (`workflow.py:918,:1368`); `resolved_agent()` derives from frontmatter
  (`wp_metadata.py:418`); genuine resolution (`RoutingRecommendation`, `registry.resolve`) lives
  only in `invocation/executor.py` (~:149/:265 recommendation, :249/:258 `registry.resolve`),
  keyed by `invocation_id` in `invocation/record.py` with no WP-lane back-ref. Emit-shape
  reconciliation: annotation (reducer's `policy_metadata` claim fold fires only on
  `planned→claimed`, `reducer.py:102`, so review-claim would be missed) AND structured `actor`.
  Historical authored-to-resolved fabrication (C-011) is forbidden by the accepted ADR.
- **data-model.md → INV-6 and INV-8.** INV-6: a recorded resolved `agent_profile`/`role`/`model`
  originates from the resolver/dispatch, never a frontmatter copy. INV-8: after multiple pick-ups,
  the reconstructed resolved identity equals the most recent transition's actual, with 0 bytes
  written to `tasks/WP##.md`.
- **contracts/resolved-binding.md → "Vocabulary (IC-08)"** ("Source (dispatch→claim linkage)",
  "Written", "Historical non-seed (C-011)", "Absence is valid"): legacy authored-only WPs remain
  unresolved until a genuine resolver-backed runtime event exists.

**Verified code anchors (post-#2817 tree):**

| Surface | Anchor | Role |
|---------|--------|------|
| `invocation/executor.py` | `_compute_recommendation` (:47/:265); `RoutingRecommendation | None` payload field (:149); `self._registry.resolve` (:249/:258); `invocation_id = _new_ulid()` (:244) | the genuine model+profile resolution + Op id |
| `invocation/record.py` | `OpStartedEvent` — `invocation_id`, `profile_id`, `action` (schema v2) | resolved profile recorded, keyed by `invocation_id` |
| `cli/commands/agent/workflow.py` | `implement()` (:915) `--agent` (:918); `review()` (:1365) `--agent` (:1368) | the claim commands — only the bare `--agent` string today |
| `cli/commands/agent/workflow_executor.py` | `implement_claim_transition` (:857, `resolved_agent()` :900); `review_claim_transition` (:1420) | the two claim seams that emit |
| `status/emit.py` | `emit_status_transition` `# NOSONAR` (:507); `emit_inner_state_changed` (:888, annotation, no fan-out); `build_claim_policy_metadata` (:220) | emit surfaces (out-of-map — WP04-owned) |
| `status/reducer.py` | `_RUNTIME_SLOTS` (:39); `_apply_annotation_delta` (:117); claim fold `planned→claimed` only (:102) | WP09 already added the resolved slots |
| `migration/backfill_runtime_state.py` | `_seed_id` (:232); idempotency drop (:512-519) → returns `"skip"` when `seeded_count == 0` | re-seed under a new namespace |

**Why the linkage is forced (the split-brain the naive path creates).** The claim command today
receives only `--agent` — a bare tool string. `resolved_agent()` (`wp_metadata.py:418`) then
*derives* an assignment from the **frontmatter** `agent_profile`. If we recorded that derived value
as the WP's "resolved binding", we would be copying static authored intent into a dynamic
event-sourced slot — manufacturing a brand-new split-brain, the precise anti-pattern #2093 forbids
(C-007). The genuine resolution — which profile the router/registry actually resolved, and which
model the routing catalog actually recommended — exists only on the dispatch/Op path
(`invocation/executor.py`), keyed by `invocation_id`, with **no back-reference** to the WP lane.
This WP builds that back-reference: thread the dispatch-resolved values into the claim command so
the claim-time emit records the *true* binding.

**Why BOTH an annotation and an enriched actor (emit-shape reconciliation, D-12).** The reducer's
claim fold (`reducer.py:102`) writes runtime slots from `policy_metadata` **only** on the
`planned→claimed` transition. A **review-claim** is `for_review→in_review` — it never hits that
fold, so a binding recorded only via the claim `policy_metadata` path would be invisible at
review-claim, and the "latest-wins" identity would freeze at the implementer's binding. Emitting an
`InnerStateChanged` **annotation** at each claim point sidesteps the fold restriction (annotations
fold latest-wins regardless of lane). Separately, the SaaS fan-out (IC-09/WP12) rides the
transition's structured **`actor`** — so the binding must ALSO enrich the actor. Neither channel
alone is sufficient: annotation drives local reconstruction (IC-07/WP11), actor drives SaaS.

---

## Subtasks

### T037 — Thread the resolved binding from dispatch into the implement/review commands

Add a sanctioned channel on `cli/commands/agent/workflow.py` to carry the *genuinely
dispatch-resolved* `model` + `agent_profile` (+`invocation_id`) into `implement()` (:915) and
`review()` (:1365) — new `--model` / `--profile` / `--invocation-id` typer options (or an
equivalent sanctioned side-channel). Source these values from the invocation layer
(`invocation/executor.py` `RoutingRecommendation`'s winning candidate model at ~:149/:265;
`registry.resolve` at :249/:258; the resolved `profile_id` recorded in `invocation/record.py`
keyed by `invocation_id`).

- Where `--invocation-id` is supplied, resolve the binding by reading the Op record
  (`invocation/record.py`) rather than trusting caller-passed strings blindly.
- **NEVER** derive these from the frontmatter `agent_profile` string or `resolved_agent()`'s
  frontmatter-coerced values for the *recorded resolved* value (C-007 / INV-6). Frontmatter is
  authored intent only.
- Keep the command signatures backward-compatible: all three new options default to `None`
  (a claim invoked without dispatch context is still legal — see T038's explicit-absent path).
- Complexity: `implement()`/`review()` are already large — do NOT inline resolution branches;
  extract a small `_resolve_dispatch_binding(...)` helper (pure, testable) that returns a typed
  `ResolvedBinding | None`.
- **Typed carrier.** Prefer a small frozen dataclass (`ResolvedBinding` with
  `role`/`agent_profile`/`agent_profile_version`/`model`/`provider`) over passing five loose
  strings through the command → seam → emit chain. It keeps `mypy --strict` honest and lets the
  explicit-absent model (T038) be a first-class `model: str | None` rather than a magic sentinel
  scattered across call sites. Place it where both the invocation layer and the claim seams can
  import it without a runtime→charter→doctrine boundary violation.
- **Precedence.** When `--model`/`--profile` are passed AND an `--invocation-id` resolves a
  different value, the Op record is authoritative (it is the genuine resolution); a mismatch is
  worth a warning but the recorded value stays resolver-sourced.

### T038 — Consume the resolved binding at the claim seams (explicit-absent honesty)

Consume the threaded binding at the two claim seams in
`cli/commands/agent/workflow_executor.py` — `implement_claim_transition` (:857) and
`review_claim_transition` (:1420) — and at the `cli/commands/agent/tasks_move_task.py` reassign
emit (:1916).

- Build the resolved-binding delta (`role`/`agent_profile`(+version)/`model`/`provider`) from the
  T037-threaded values, produced by the dispatch resolver / `resolve_profile` / `resolved_agent()`
  — never a frontmatter copy (INV-6).
- **Explicit-absent (SC-011):** where a genuine model is unavailable for a path (e.g. a claim with
  no dispatch context, or `RoutingRecommendation` returned `None`), record the model slot as
  **explicitly absent** (a sentinel/`None` the reader can distinguish), never fabricated and never
  copied from frontmatter. The reducer/reader must be able to tell "no resolved model recorded"
  apart from "resolved to model X".
- The `role` at each seam is the *actual* role that ran (implementer at implement-claim, reviewer
  at review-claim), not the authored recommendation.

### T039 — Emit the binding: `InnerStateChanged` annotation (both claim points) + enriched actor

Emit the resolved binding at BOTH claim points so latest-wins reduction holds across the
lifecycle:

- **Annotation:** emit an `InnerStateChanged` annotation (via `emit_inner_state_changed`,
  `emit.py:888`) carrying the WP09 resolved-binding delta fields, at implement-claim AND
  review-claim. This is mandatory because the reducer's claim fold reads `policy_metadata` only on
  `planned→claimed` (`reducer.py:102`); a review-claim (`for_review→in_review`) would miss it if we
  relied on the claim-fold path alone.
- **Structured actor:** ALSO enrich the transition's structured `actor` (`{role, profile, tool,
  model}`) so the IC-09 SaaS fan-out (WP12) can ride it. **Thread this via a small helper** (e.g.
  `_build_resolved_actor(...)` on the emit side) — do **NOT** inflate the tracked `# NOSONAR` on
  `emit_status_transition` (`emit.py:507`); the actor-enrichment logic lives in the helper, not in
  new positional params on that hub.
- Emit BOTH, not either — the annotation drives the local latest-wins reconstruction (IC-07/WP11),
  the actor drives the SaaS fan-out (IC-09/WP12).
- **Actor shape.** The enriched actor is the `{role, profile, tool, model}` structured form that
  `spec_kitty_events` 6.1.0 `StatusTransitionPayload.actor` already accepts (`Union[str, Dict]`) —
  so no shared-package change is needed here (IC-09/WP12 owns the local `str → str | dict` widening
  of the emit signatures). Do NOT widen `StatusEvent.actor` in THIS WP; produce the structured actor
  in the helper and let WP12 carry the type-surface plumbing. If WP12 has not yet widened the
  signature when this WP lands, keep the actor a `str` and record the structured binding ONLY via
  the annotation (the annotation alone satisfies IC-07's reconstruction); leave a `# TODO(WP12)`
  breadcrumb rather than a half-typed dict that would corrupt on `from_dict`'s `str(...)` coercion.

### T040 — Enforce historical binding provenance (C-011 closeout correction)

The accepted C-009 field-authority ADR makes authored recommendation and resolved actual distinct.
`migration/backfill_runtime_state.py` therefore MUST NOT seed authored frontmatter
`role`/`agent_profile`/`model` as a historical resolved binding. A legacy mission without genuine
resolver-backed evidence remains empty on the resolved side.

- Remove the authored-binding fields/helper and all resolved-binding seed/verify paths from the
  migration engine.
- Prove an authored-only legacy WP produces no resolved-binding annotation and still verifies green.
- Remove earlier deterministic `_seed_id(mission_id, wp_id, "resolved_binding")` rows from the
  dogfood corpus only after validating their annotation shape; preserve every non-seed annotation.
- Do not rematerialize unrelated stale snapshot content: no historical snapshot contained a resolved
  binding, so restore those bytes after the event-log correction.
- **Never-claimed WPs.** A WP with no claim anchor carries no honest resolved binding; skip it (warn,
  do not fail) — the same edge the base backfill already honours for the `"claim"` seeds.

### T041 — Correct the dogfood corpus without fabricating runtime identity

Audit **this repo's own `kitty-specs/`** and remove only deterministic authored-derived
`resolved_binding` seed rows. Validate every matched row's shape before rewriting.

```bash
uv run --extra test python -m pytest -p no:cacheprovider tests/specify_cli/status/test_resolved_binding_linkage.py
# then run the deterministic seed-ID corpus audit/correction
```

- **Acceptance:** no deterministic authored-derived resolved-binding seed ID remains; all non-seed
  annotations remain byte-preserved.
- This is a **data correction** (`kitty-specs/**/status.events.jsonl`), NOT a new source of runtime
  identity. Historical snapshots that never contained resolved binding stay byte-identical.
- Idempotent: re-running the audit finds zero matching rows.

### T042 — Tests (ATDD): write red-first in `tests/specify_cli/status/test_resolved_binding_linkage.py`

Author focused, red-first tests (create-intent file):

1. **INV-6 / C-007 — resolver-sourced, never frontmatter:** drive implement-claim with a
   dispatch-resolved binding threaded via T037; assert the recorded resolved
   `agent_profile`/`role`/`model` equals the *resolver/`resolved_agent()`/dispatch* value and is
   NOT a copy of the frontmatter `agent_profile` string (construct a fixture where the two differ,
   so a frontmatter copy would fail the assertion).
2. **SC-008 / INV-8 — latest-wins across claim points:** drive implement-claim (profile P1 /
   model M1) then review-claim (profile P2 / model M2); assert the reduced snapshot resolved slots
   equal P2/M2 (the most recent actual), with **0 bytes** written to `tasks/WP##.md`.
3. **SC-011 — explicit-absent model path:** drive a claim with no dispatch-resolved model; assert
   the resolved `model` slot is recorded **explicitly absent** (distinguishable from a real model),
   never fabricated and never frontmatter-coerced.
4. **C-011 — no historical fabrication:** assert an authored-only legacy WP produces no
   resolved-binding seed, remains empty in the resolved view, and still verifies green.

Run per-file with `uv run` (never bare `python` — it resolves a sibling checkout → false greens).

---

## Branch Strategy

Planning artifacts were generated on `feat/runtime-state-corpus-cutover`; completed changes merge
back into `feat/runtime-state-corpus-cutover`.

**MERGE-UNIT with WP11 (IC-07 reader).** The T041 provenance correction and WP11's
`reconstruct_wp_view` reader land together so no reader can observe authored intent masquerading as
runtime actual. Sequence: WP09 (vocabulary) → **WP10 (linkage + correction)** → WP11 (reader).
Depends on **WP09** (the resolved-binding vocabulary
this WP consumes must exist first).

---

## Test strategy

Run tests **per-file** with `uv run` and a timeout — never the whole `tests/architectural/` dir
(it hangs), never bare `python`:

```bash
uv run --extra test python -m pytest -p no:cacheprovider \
  tests/specify_cli/status/test_resolved_binding_linkage.py
# claim-seam / emit regressions touched out-of-map:
uv run --extra test python -m pytest -p no:cacheprovider \
  tests/specify_cli/cli/commands/agent/  # scope to affected files
# historical binding provenance:
uv run --extra test python -m pytest -p no:cacheprovider \
  tests/specify_cli/migration/  # scope to backfill tests
# invariant (per-file, timeout):
timeout 300 uv run --extra test python -m pytest -p no:cacheprovider \
  tests/architectural/test_2093_authority_invariant.py
```

Every new branch/helper (`_resolve_dispatch_binding`, the explicit-absent path, the actor helper,
the historical non-seed path) gets a focused test in this same WP (DIR-005 / ATDD-first).

---

## Definition of Done

- **FR-014** satisfied: the genuinely dispatch-resolved model + profile (+version) are threaded
  from `invocation/executor.py` into `implement`/`review` and recorded at the claim seams.
- **FR-013** satisfied for the recorded value: resolved `role`/`agent_profile`/`model` are
  event-sourced at each pick-up, folded latest-wins.
- **C-007 / INV-6:** every recorded resolved value comes from the dispatch resolver /
  `resolve_profile` / `resolved_agent()`, **never** a copy of the frontmatter `agent_profile`
  string. Proven by a test where authored ≠ resolved.
- **C-011:** authored recommendations never seed resolved actuals; exact deterministic fabricated
  seed rows are absent from the corpus and non-seed runtime annotations are preserved.
- **SC-008 / INV-8:** latest-wins across implement-claim → review-claim, with 0 bytes written to
  `tasks/WP##.md`.
- **SC-011:** the resolved `model` is the genuine dispatch-resolved value, or **explicitly absent**
  where unavailable — never fabricated, never frontmatter-coerced.
- **Emit shape:** the binding is emitted as an `InnerStateChanged` **annotation** at BOTH claim
  points AND enriches the structured transition `actor` — via a **helper**; the tracked `# NOSONAR`
  on `emit_status_transition` is **NOT inflated** (no new positional params on that hub).
- **T041 data correction** landed: 1,154 fabricated rows removed from 185 mission logs by exact seed
  identity; unrelated historical snapshot bytes preserved.
- **Quality:** `ruff` + `mypy --strict` clean with **no** new `# noqa` / `# type: ignore` /
  per-file ignores; complexity ≤15 on every touched function (thread new logic through small
  helpers — `_resolve_dispatch_binding`, the actor helper, the seed builder — never inline).
- All new tests green per-file via `uv run`; the #2093 invariant still passes (unchanged by this WP,
  but confirm no regression).
- **WP09 dependency honoured:** this WP consumes the resolved-binding vocabulary (delta slots +
  reducer fold) and the C-009 ADR that WP09 landed — it does not re-add or re-open them. If a needed
  slot is missing, that is a WP09 gap to flag upstream, not a local re-implementation.
- **No repo-root write (C-003 / INV-5):** the re-seed and every claim-seam emit resolve their write
  target via `canonicalize_feature_dir`; a regression confirms no `status.events.jsonl` lands at
  repo root.

---

## Risks & out-of-map edits

This is the biggest scope-growth WP in the mission (invocation layer + command surface + claim
seams + backfill). Keep **resolver-sourcing strict** — the single easiest regression is copying a
frontmatter string into an event, which manufactures the exact new split-brain #2093 forbids.

**OUT-OF-MAP edits this WP makes** (all sequential — these files' owners run in earlier WPs, so the
edits do not collide; each is a targeted addition, not a rewrite):

| File | Owner | This WP's edit | Rationale |
|------|-------|----------------|-----------|
| `src/specify_cli/status/emit.py` | WP04 | add the resolved-binding annotation emit at the claim seams + a `_build_resolved_actor` helper for actor enrichment | WP04 (the flag-removal owner) runs earlier; the actor helper keeps the NOSONAR hub un-inflated |
| `src/specify_cli/cli/commands/agent/workflow_executor.py` | WP04 | consume the threaded binding at `implement_claim_transition` + `review_claim_transition` | WP04 removes the flag branch first; this adds the resolve-and-emit at the same seams |
| `src/specify_cli/cli/commands/agent/tasks_move_task.py` | WP05 | build the resolved-binding delta on the reassign emit (:1916) | WP05 removes the flag branch + routes the ownership reader first |
| `kitty-specs/**` | WP03 | the T041 deterministic fabricated-seed removal | WP03 owns the dogfood corpus; exact-ID correction preserves all non-seed annotations |

Other risks:

- **Provenance trap (C-011):** copying authored recommendations into resolved slots fabricates runtime
  truth. Mitigated by the non-seed test plus exact-ID corpus audit.
- **NOSONAR inflation:** adding actor params to `emit_status_transition` would inflate the tracked
  suppression. Thread via the helper instead.
- **Explicit-absent honesty:** the reader must distinguish "no model recorded" from "model X" —
  choose a sentinel that survives JSONL round-trip and is not confused with a real model string.
- **Merge-unit coupling:** land the provenance correction with WP11 so every consumer observes the
  same authored-versus-resolved boundary.

---

## Reviewer guidance

Verify, specifically:

1. **No frontmatter copy into events (C-007 / INV-6):** trace every recorded resolved
   `role`/`agent_profile`/`model` back to `invocation/executor.py`'s resolution,
   `resolve_profile`, or `resolved_agent()` — confirm NONE is a copy of the frontmatter
   `agent_profile` string. The T042 authored≠resolved fixture must fail if a copy is introduced.
2. **New seed namespace, not `"claim"`:** confirm the re-seed mints
   `_seed_id(…, "resolved_binding")` and that the backfill returns `"wrote"` (not `"skip"`) on a
   corpus already holding the `"claim"` seeds.
3. **Latest-wins at BOTH claim points:** confirm the annotation is emitted at implement-claim AND
   review-claim (not only `planned→claimed`), and the reduced snapshot reflects the most recent
   actual after a review-claim.
4. **Explicit-absent honesty (SC-011):** confirm the no-dispatch-context path records the model as
   explicitly absent, never fabricated, never frontmatter-coerced.
5. **NOSONAR not inflated:** confirm `emit_status_transition`'s parameter surface is unchanged and
   the actor enrichment lives in a helper.
6. **Byte-stability:** confirm the claim seams write 0 bytes to `tasks/WP##.md` (INV-8).

## Activity Log

- 2026-07-20T18:29:42Z – claude – shell_pid=414961 – Assigned agent via action command
- 2026-07-20T19:17:31Z – claude – shell_pid=414961 – Ready for review: dispatch->claim resolved-binding linkage + emit + backfill re-seed (T037-T042). Pre-review gate skipped (arch-dir 300s timeout); per-file evidence: test_resolved_binding_linkage.py 11 passed, migration backfill 61+5 passed, emit/reducer/wp_state 111 passed, #2093 invariant 6 passed, orchestrator 67 passed, boundary gates 9 passed, dead-symbol/module green (only pre-existing SYNC_DISABLE_ENV_VARS from #2814), ruff+mypy clean. Re-seed committed on feat (185 missions, 1154 resolved_binding events).
- 2026-07-20T19:19:51Z – claude – shell_pid=512547 – Started review via action command
- 2026-07-20T19:22:08Z – user – shell_pid=512547 – Approved: C-007 by construction (no frontmatter param), SC-011 sentinel non-vacuous, C-011 wrote-not-skip, 185-mission re-seed excl self
- 2026-07-21T14:34:36Z – codex – Closeout correction: the accepted C-009 ADR supersedes the C-011 re-seed approval; 1,154 authored-derived rows were removed by exact deterministic ID and historical authored-only bindings remain unresolved.
