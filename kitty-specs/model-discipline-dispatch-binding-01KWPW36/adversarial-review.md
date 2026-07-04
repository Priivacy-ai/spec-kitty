# Adversarial Review Log — Model-Discipline Dispatch Binding

Squad cadence at each planning point-cut. Model discipline applied (opus for design/sizing; sonnet for grounding). Read-only, isolated in the #2364 clone.

## Round 1 — Pre-spec grounding (2 × sonnet)

- **Code-truth**: gaps CONFIRMED on HEAD. Catalog defined-but-DEAD (no loader, no populated instance; whitelisted as schema-gen only). Dispatch seam consults no routing; `invoke()` returns a payload synchronously and **never spawns a model** → advisory-only ceiling. Charter `model_task_routing` reference dangles (not an ArtifactKind). **Critical correction:** the issue's cited `delivery/dispatcher.py` is the SaaS drain — the real seam is `cli/commands/dispatch.py` + `invocation/{executor,router,registry,modes}.py`.
- **Tracker**: no duplicate; #1799 correct parent; #2196/#2216 ruled out. #1049 (OPEN) is a real boundary risk (static per-step config vs doctrine task-class routing) — scoped against, not folded. Origin: schema shipped in mission 057 bootstrap, consumer never scoped. #1841 same pattern (cross-ref).

## Round 2 — Post-spec (2 × opus) → spec rev 2

- **alphonso (design)** — SOUND-WITH-CORRECTIONS. Folded:
  1. FR-001 undersizes "consult the catalog" — it's a model-*scoring* catalog (task_fit × weights × objective × tier_constraints), not a task-class→tier map; needs a loader + action→task_type map + evaluator. Tier vocabulary gap: no capability tier → **use `objective: quality_first` as the capability lever**.
  2. FR-002 (now FR-005) is a silent no-op unless the field lands on the **`profile.py` domain model** (kebab alias); schema is generated from `schema_models.py` (`extra='ignore'` drops unknown keys).
  3. FR-005 (now FR-007) premise wrong — `autonomous-operation-protocol` tactic **already exists**; fix is a **one-line DRG `suggests` edge**, split out from FR-003/006.
  4. FR-003 (now FR-006) mechanism omits the DRG edge (the real lever); references.yaml is generated. Concrete: kebab `model-task-routing.tactic.yaml` + graph node + directive `suggests` edge + **repoint the snake_case charter token**. Kind = **tactic** (confirmed, matches the sibling).
  5. US2 precedence contradictory ("reflects profile value" vs "surfaces both") → pinned: advisory emits catalog + profile as provenance-tagged candidates, enforces neither.
  6. C-001 caveat — `wp_metadata.py` `AgentAssignment.model` is an existing static WP selector; the "nothing consults model routing" claim overstated → acknowledged.
  7. FR-006 (now FR-009) invariant feasible + refactor-stable; pinned definitions (parse `→ \`token\`` all sections; resolve = references.yaml id-suffix match).
- **paula (sizing)** — UNDERSIZED ~3×. FR-001 hides loader + evaluator + payload (3 surfaces); action→task_type mapping is net-new and absent; FR-003/005 activation is a multi-file DRG + bundle-regen chain, not "two references.yaml rows"; SC fakeability (must vary-with-catalog, must load-via-DRG); #1049 boundary confirmed real. Honest split = 5-6 WPs.

## Scope ruling (operator, 2026-07-04)

**Full evaluator** — build the complete routing machinery (loader + action→task_type map + objective-function scorer + payload + profile field + tactic/DRG chain + populated catalog + invariant). ~5-6 WPs. Restructured FRs (FR-001..FR-009) reflect the real surfaces.

## Round 3 — Post-tasks (opus combined anti-laziness + sizing + Sonar) → WP rev 2 (folds applied)

VERDICT NEEDS-TIGHTENING → all folded before finalize:
1. **Phantom mechanism (highest)** — a catalog is NOT an ArtifactKind; there is no "activation convention". Real mechanism = package data `importlib.resources.files("doctrine.model_task_routing")/"catalog"/"model-to-task_type.yaml"`. Pinned as a shared WP01↔WP05 contract + an injectable `loader.load(catalog_path=None)` override (required for SC-001's vary-with-catalog anti-fake). Purged the phantom language from WP01/WP05/plan.md.
2. **Per-WP-green defect** — loader/task_class_map/evaluator are orphans until WP03 wires them into `invoke()`; the dead-modules arch gate would red WP01/WP02. Moved `test_no_dead_modules.py` ownership + de-allowlisting to WP03 (integration tip, T018); added orphan-tolerance notes to WP01/WP02; dead-modules invariant validated at the WP03 tip.
3. **WP03→WP05 dependency + integration test (T019)** — the shipped-catalog↔loader-default-path agreement was untested; added a no-override dispatch test proving they agree.
4. **Profile attribute pinned deterministically** — `preferred_model: str|None (alias "model")` + `effort: str|None (alias "effort")` on `profile.py`; avoids Pydantic `model_` namespace; WP02 reads `profile.preferred_model`/`profile.effort`.
5. **WP03 helper extraction mandated** — `_compute_recommendation(profile, action)` holds the loader+evaluator call + non-fatal envelope so `invoke()` stays ≤15 cognitive complexity.
6. **WP06 red-first procedure** — capture RED against the pre-WP05 base (stash graph.yaml/charter.md edits), then GREEN on the integrated branch.
7. **plan.md router.py stale line removed** — the recommendation is computed in `executor.py`; `router.py` is untouched by every WP.

Finalized: 6 lanes, acyclic, all validations pass.

## OUT — tracked home / follow-up

- `gated`/`required` override modes (need a mature catalog) — Non-Goal; future.
- #1049 static per-step config surface — separate track, stays open.
- Interactive Agent-tool delegation enforcement — host-level, not code-enforceable.

_To file at close: nothing new required beyond honoring the #1049/#1841 cross-refs in the PR body._
