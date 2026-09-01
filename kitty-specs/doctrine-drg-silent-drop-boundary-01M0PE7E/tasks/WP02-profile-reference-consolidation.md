---
work_package_id: WP02
title: Profile-reference consolidation + re-ledger (#3629 p1, p3)
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-013
planning_base_branch: fix/doctrine-drg-silent-drop-boundary
merge_target_branch: fix/doctrine-drg-silent-drop-boundary
branch_strategy: Planning artifacts for this mission were generated on fix/doctrine-drg-silent-drop-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/doctrine-drg-silent-drop-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
- T009
- T010
- T011
- T012
history:
- at: '2026-08-23T00:00:00Z'
  actor: tasks
  note: WP created
agent_profile: python-pedro
authoritative_surface: src/doctrine/agent_profiles/
create_intent:
- src/specify_cli/upgrade/migrations/m_3_3_1_context_sources_consolidation.py
- tests/doctrine/agent_profiles/test_context_sources_migration.py
execution_mode: code_change
owned_files:
- src/doctrine/agent_profiles/profile.py
- src/doctrine/agent_profiles/schema_models.py
- src/doctrine/agent_profiles/__init__.py
- src/doctrine/schemas/agent-profile.schema.yaml
- src/doctrine/drg/migration/extractor.py
- src/doctrine/drg/migration/hand_authored_overlay.py
- scripts/generate_schemas.py
- scripts/doctrine/inline_reference_inventory.py
- packs/built-in/agent_profiles/**
- packs/built-in/agent_profile.graph.yaml
- src/specify_cli/upgrade/migrations/m_3_3_1_context_sources_consolidation.py
- tests/doctrine/test_profile_model.py
- tests/doctrine/test_shipped_profiles.py
- tests/doctrine/drg/test_model_strictness_roundtrip.py
- tests/charter/test_emit_delivery_bind.py
- tests/doctrine/agent_profiles/test_supply_chain_profile_bindings.py
- tests/doctrine/drg/migration/test_extractor.py
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/doctrine/agent_profiles/test_context_sources_migration.py
- tests/doctrine/fixtures/valid-profile.agent.yaml
- tests/specify_cli/bulk_edit/test_occurrence_map_field_paths.py
- CHANGELOG.md
- pyproject.toml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro`
+ `spec-kitty charter context --action implement --json`). Apply + state what you
applied. Shadow venv: `export PATH="$PWD/.venv/bin:$PATH"`.

## Objective

Remove the redundant, mostly-inert `context-sources.*` profile surface and
consolidate on the canonical top-level `*-references` surface — atomically, so the
repo stays green — migrating the 25 shipped profiles and every consumer, and
regenerating the golden DRG with a **deliberate, ledgered** python-pedro/DIRECTIVE_034
delivery decision. This is #3629 part 1 (+ the part-3 doc-nit).

**This is the heavy WP.** Read `research/context-sources-drg-projection.md` and
`research/post-plan-brownfield-squad.md` (findings F2–F6) before starting.

## Critical facts from research (do not re-derive)

- The renderer that delivers profile text to a dispatched agent
  (`src/charter/context_renderers/profile_sections.py`) reads the **top-level
  `*-references`** fields, NOT `context-sources.*`. The one live `context-sources`
  path is the extractor projecting `context-sources.directives → requires`
  (`extractor.py:920-929`).
- For all 25 shipped profiles, every `context-sources.{directives,tactics,
  toolguides,styleguides}` id is **already** on the matching `*-references` field
  ⇒ for the shipped set the migration is effectively deletion (green-by-construction).
  The migration's data-moving branch is therefore only exercised by a **divergent
  user-profile fixture** (T011).
- **`additional` is NOT pure-drop** (F3): reviewer-renata's
  `context-sources.additional` carries `adversarial-evidence-disposition`, the only
  place that string exists, pinned by
  `tests/doctrine/agent_profiles/test_supply_chain_profile_bindings.py:158`.
- **C-006 delivery delta** (F4): `hand_authored_overlay.py` gives python-pedro
  a `suggests→DIRECTIVE_034` link with a `when` clause (locate the
  `agent_profile:python-pedro` + `DIRECTIVE_034` SUGGESTS entry — ~L1674, NOT
  L585 which is an unrelated DDD `requires` edge). Once T004 projects
  `directive-references→requires`, 034 (in pedro's `directive-references`) becomes a
  requires-diamond → `progressive_disclosure.py:186` suppresses the suggested link.
  This MUST be resolved deliberately and ledgered — never silent.

## Subtasks

### T004 — Extractor: project agent_profile edges from `*-references`
- In `extractor.py:906-942`, replace the `context-sources.directives → requires`
  loop with projection from top-level `directive-references`; keep the existing
  `tactic-references → requires`; add `toolguide-references`/`styleguide-references`
  → `suggests` projection (diagram-daisy authors `toolguide-references`).
- Reconcile `hand_authored_overlay.py` for pedro/034: **choose one** and record it
  in the composition ledger — (a) exclude 034 from pedro's `directive-references→
  requires` projection so the overlay `suggests→034` link is preserved, OR (b) drop
  the now-redundant overlay `suggests→034` edge. Default: (a) preserve current
  delivery (least behaviour change). State the choice in the WP history + ledger.

### T005 — Remove `context-sources` from models + schema + `__all__`
- Delete `ContextSources` and the `context_sources` attribute from
  `profile.py`; delete `AgentContextSources` + attribute from `schema_models.py`;
  drop the `context-sources` block ($ref + def) from `agent-profile.schema.yaml`;
  remove `ContextSources` from `agent_profiles/__init__.py` `__all__` (C-007).
- Pydantic `extra="forbid"` then rejects any profile authoring `context-sources`
  at load — the intended fail-loud boundary.

### T006 — Update non-test consumers
- `scripts/generate_schemas.py:485-492` — drop the `agent_context_sources`
  annotation block (else schema-regen annotates a nonexistent def).
- `scripts/doctrine/inline_reference_inventory.py:166-193` — retire
  `_collect_context_sources()` (dead after removal).
- **Missed consumer (post-tasks G4)**: `tests/doctrine/fixtures/valid-profile.agent.yaml`
  authors a `context-sources` block and is loaded by
  `test_profile_schema_validation.py` + `test_doctor_doctrine.py` — remove the
  block from the fixture so those loaders keep passing (removal would otherwise red
  them silently, violating FR-006).
- **F15 doc/example hygiene**: refresh stale `context-sources.*` field-path
  examples in `src/doctrine/schemas/occurrence-map.schema.yaml:65,71`,
  `src/doctrine/templates/occurrence-map-template.yaml:47`,
  `src/specify_cli/bulk_edit/diff_check.py:264`, and verify
  `tests/specify_cli/bulk_edit/test_occurrence_map_field_paths.py:368,377` (uses
  the path as an occurrence-map literal — confirm it does not assert profile-schema
  validity; adjust if it does). Doc references under `docs/` may be folded here or a
  follow-up issue filed.

### T007 — Upgrade migration
- New `src/specify_cli/upgrade/migrations/m_3_3_1_context_sources_consolidation.py`
  (follow the pattern of `m_2_2_0_profile_context_deployment.py`; use
  `get_agent_dirs_for_project`-style config-aware helpers where relevant).
  **Version note (post-tasks G5)**: `m_3_2_6`…`m_3_3_0` migrations already ship at
  HEAD, so a `m_3_2_6_*` name would mis-order. Confirm the runner's ordering /
  idempotency contract and name for the next **unreleased** version (`m_3_3_1_*`),
  aligned with the version bump below.
- **Set-merge (not append)** `context-sources.{directives,tactics,toolguides,
  styleguides}` into the matching `*-references` (they are supersets already —
  dedup by id). Add a dup-guard assertion.
- **Re-home** `context-sources.additional` bindings deliberately: map
  `adversarial-evidence-disposition` (reviewer-renata) to an explicit ref
  (directive/tactic) or update the pinning test accordingly — do not silently drop.
- Drop `doctrine-layers` (layer names, no NodeKind) and any remaining `additional`
  free-text with a logged note.

### T008 — Migrate the 25 shipped profiles
- Apply the migration to `packs/built-in/agent_profiles/*.agent.yaml`: remove
  every `context-sources` block; ensure refs live on `*-references`. Confirm
  `grep -rl "context-sources" packs/built-in/agent_profiles/` returns nothing.

### T009 — Regenerate golden graph + composition ledger
- Regenerate `packs/built-in/agent_profile.graph.yaml` via
  `spec-kitty doctrine regenerate-graph` (NEVER hand-edit the generated file).
- Reconcile against `hand_authored_overlay.py`. Add a composition-ledger entry for
  the pedro directive requires-edge delta (9→10) per `test_golden_count_ban.py`
  (or add a walk-gate asserting pedro's post-migration traversal outcome, which
  discharges the ledger rule).

### T010 — Update asserting tests
- Update every test that constructs `ContextSources` or asserts on
  `context_sources.*`: `test_profile_model.py`, `test_shipped_profiles.py`,
  `test_model_strictness_roundtrip.py`, `test_emit_delivery_bind.py` (:577,:677
  fixtures → `directive-references`), `test_supply_chain_profile_bindings.py:158`
  (the re-homed binding), `test_extractor.py:135`, `test_extractor_projection.py:535`.

### T011 — Divergent-profile fixture + snapshot + C-006 golden-diff
- New `tests/doctrine/agent_profiles/test_context_sources_migration.py`:
  - A **divergent user-profile fixture** whose `context-sources.{directives,tactics}`
    contain ≥1 id **absent** from `*-references`; assert post-migration those ids
    appear on `*-references` (exercises the data-moving branch T007 — the shipped
    profiles cannot, being green-by-construction).
  - A **frozen pre-migration snapshot** of each shipped profile's `context-sources`
    ids; assert no id is lost after migration.
  - **C-006 golden-diff**: regenerate `agent_profile.graph.yaml` in the test (or
    compare committed vs regenerated); assert the per-`agent_profile:*` edge-set
    diff is empty **except** the ledgered pedro/034 delta.

### T012 — Doc-nit (IC-6, #3629 p3)
- Update the `extractor.py:557` docstring ("no golden-count update was required")
  to reflect this WP's re-ledger. Land last, after the ledger settles.

## Branch Strategy

Planning base + merge target: `fix/doctrine-drg-silent-drop-boundary`. Worktrees
per computed lane from `lanes.json` at implement time.

## Definition of Done

- `context-sources` gone from models/schema/`__all__`; authoring it → load-time
  rejection. All ≥8 consumers updated; no silent breakage.
- Migration set-merges refs, re-homes the `additional` binding, drops layer/free
  fields; divergent-fixture test proves the data-moving branch; snapshot proves no
  loss.
- `agent_profile.graph.yaml` regenerated (not hand-edited) + ledger entry for
  pedro/034; C-006 golden diff empty except that delta.
- `ruff` + `mypy --strict` clean; no new suppressions. Terminology guard green.
- **DIR-009 (post-tasks G6)**: `CHANGELOG.md` carries a breaking-change entry
  (`context-sources` removed from the agent-profile schema; migration pointer), and
  `pyproject.toml` version is bumped (required for any `__init__.py`/schema change).
- **Atomicity (G11)**: this WP's removal↔migration↔regen triad (T004/T005/T008/
  T009/T010) MUST land together — splitting leaves the 25 shipped profiles
  unloadable (`extra="forbid"`). Do not split the core.
- Touched functions remain ≤15 cyclomatic complexity (NFR-004); extract helpers in
  the extractor projection / migration rather than growing a branch.
- Targeted greens: `pytest tests/doctrine/agent_profiles/ tests/doctrine/drg/migration/test_extractor.py tests/doctrine/drg/migration/test_extractor_projection.py tests/doctrine/test_profile_model.py tests/doctrine/test_shipped_profiles.py tests/charter/test_emit_delivery_bind.py tests/architectural/test_golden_count_ban.py -q`.

## Risks / reviewer guidance

- **Ownership**: this WP owns `extractor.py`. WP03 must not edit it (keep org-tier
  code in `org_pack_loader.py`). If WP03 needs extractor.py, sequence it after this.
- Reviewer: reject a migration that only deletes `context-sources` without the
  divergent-fixture test (green-by-construction trap, F6). Verify the pedro/034
  decision is explicit + ledgered, not silent. Confirm the golden regen used the
  CLI, not a hand edit.
