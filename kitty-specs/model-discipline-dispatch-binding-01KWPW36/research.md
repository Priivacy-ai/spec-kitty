# Research & Brownfield Checks — Model-Discipline Dispatch Binding

Consolidates pre-spec grounding (2× sonnet) + post-spec squad (alphonso+paula, opus) + post-planning brownfield. HEAD `71b2787e8`.

## 1. Code-state (gaps confirmed)

- Catalog **dead**: `model_task_routing/models.py` has no loader; whitelisted in `test_no_dead_modules.py:251` as schema-gen only; no populated instance.
- Dispatch seam: `ProfileInvocationExecutor.invoke()` (`executor.py:168-284`) returns `InvocationPayload` synchronously, **never spawns a model** (`:150,181`); no model slot (`:105-116`); no `task_type` concept (`grep task_type invocation/` → empty).
- Charter `model_task_routing` reference dangles (not an ArtifactKind; absent from generated `references.yaml`). `autonomous-operation-protocol` tactic **exists** (`graph.yaml:367`) but lacks an inbound directive `suggests` edge.
- **File-scope correction** (grounding): the issue's `delivery/dispatcher.py` is the SaaS drain, NOT the seam — real target is `invocation/{executor,router}.py` + `cli/commands/dispatch.py`.

## 2. Related issues (no duplicate, no blocker)

- **PRIMARY** #2364; **PARENT** #1799 (OPEN, confirmed); #2196/#2216 ruled out.
- **#1049** (OPEN) — static per-step model config (`agents.models.steps.*`); **complementary boundary**, scoped against (C-003), not folded. Stays a separate track.
- **#1841** (OPEN) — same "rule instructed not structurally bound" pattern (profile-load); cross-referenced in design, not folded.
- **#240** (CLOSED) — the 2.x model-discipline research ancestor (archived `docs/archive/2x/model-discipline-routing.md`).
- **#1438** (CLOSED, PR #1545) — schema/Pydantic parity fix; the schema this mission consumes. No consumer wiring then.
- **Origin**: mission 057 bootstrap (`623057f97`) shipped the schema; consumer never scoped.

## 3. Brownfield: dead-symbol / duplication / deprecation

- **Dead-symbol ratchet**: `model_task_routing.models` currently allowlisted; FR-001 removes it as the loader lands (the wiring is the fix). Watch the ratchet.
- **Duplication**: none introduced — one loader, one evaluator, one task-class map (new canonical seams).
- **Deprecation**: no deprecated surfaces touched. `invocation/*` current. NOTE the SEPARATE pre-existing base failure `test_no_dead_modules.py::test_no_new_dead_modules_under_src` (stale allowlist for migration `m_3_2_3_encoding_provenance_gitignore_backfill`, drifted via unshim #2292) — red on clean `upstream/main`, unrelated to this mission; flagged for a standalone campsite fix, NOT folded here.

## 4. Brownfield: generated-artifact / bundle regen risk

- `agent-profile.schema.yaml` is GENERATED from `schema_models.py` — regenerate, never hand-edit (C-005).
- `references.yaml` + `_LIBRARY`/synthesis-manifest are generated from the DRG — FR-006/007 add `suggests` edges then regenerate the bundle (a generated-lockfile step; reds CI if skipped, like the docs page-inventory pattern).

## 5. Campsite (#1931) — none

No domain-matched hygiene items; touched files carry no live TODO/FIXME/skip/xfail (grounding). The dead-module base failure (§3) is tracked separately, not a #1931 fold.

## 6. Design decisions resolved (spec rev 2)

| Decision | Resolution |
|---|---|
| Advisory vs enforced | Advisory-only — the seam never spawns a model (C-001) |
| Capability vs cost/latency tier | `objective: quality_first` + `weights.quality` = the capability lever (no schema change) |
| Profile field placement | `profile.py` domain model (kebab alias) + `schema_models.py` regen — not schema-only |
| Reference resolution | DRG `suggests` edge + token repoint (not manual references.yaml) |
| `autonomous-operation-protocol` | One-line suggests edge to the existing tactic (FR-007) |
| Scope | Full evaluator (operator ruling) — loader + map + scorer + payload + field + doctrine chain |
| #1049 | Complementary static-config track; out of scope |
