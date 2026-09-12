# Implementation Plan: Doctrine DRG Silent-Drop Boundary Fix

**Branch**: `fix/doctrine-drg-silent-drop-boundary` | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-drg-silent-drop-boundary-01M0PE7E/spec.md`

## Summary

Close four instances of the "declared-but-inert" doctrine/DRG family — where an
artifact is authored, schema-validated, and reported healthy yet silently never
takes effect — by making each declaration→consumption boundary **derived from a
single source, fail-loud, and test-pinned**:

1. **#3608** — derive the resolver's DRG node-kind set from the canonical
   `NodeKind` enum (kill the hand-copy) + a drift-guard test.
2. **#3629 part 1** — remove the redundant/inert `context-sources.*` profile
   surface and consolidate on the canonical top-level `*-references` surface
   (migration + update 25 shipped profiles).
3. **#3629 part 2** — verify the already-landed governance-profile fail-loud guard
   (`d8beee2761`) covers the org tier; close the item.
4. **#3530 + operator direction** — fix the `org_roots=` seam that silently drops
   `drg/fragment.yaml` (executor + `action_doctrine_bundle` callers), then verify
   chain delivery on the real `packs/internal/` (spec-kitty-internal) org pack.

Plus the #3629 part-3 doc-nit. The approach is brownfield-surgical: each concern
is a small, testable change against an existing seam; no new dependencies, no new
shadow paths.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: none new — existing stdlib + pydantic (models/schema), ruamel.yaml (pack/profile YAML), the in-repo `doctrine`/`charter`/`specify_cli` packages. **No dependency added, upgraded, or removed** → supply-chain planning section N/A.
**Storage**: files only — YAML doctrine artifacts under `packs/`, `.kittify/`, and the DRG serialized graphs; no database.
**Testing**: pytest (unit + `tests/integration/`, `tests/doctrine/`, `tests/architectural/`); run targeted, never the full suite in-session (see charter/CLAUDE.md). Terminology guard `tests/architectural/test_no_legacy_terminology.py` before push.
**Target Platform**: cross-platform CLI (Linux/macOS/Windows) — Python library + CLI, no runtime service.
**Project Type**: single project (library + CLI); source under `src/`, tests under `tests/`.
**Performance Goals**: N/A — correctness/fail-loud mission; no latency/throughput target. DRG build stays within current bounds (no new full-corpus scans).
**Constraints**: zero new `# noqa`/`# type: ignore`/per-file ignores (NFR-001); touched functions ≤15 cyclomatic complexity (NFR-004); every new branch/helper gets a focused test in the same WP (NFR-002); no behaviour change to what reaches a dispatched agent today (C-006).
**Scale/Scope**: ~6 code areas, ~25 shipped profile YAMLs migrated, 1 migration, ~5 test modules. Bounded; #3514 and #3511 explicitly out (C-007).

## Constitution Check (Charter)

*GATE: must pass before Phase 0 and re-checked after Phase 1.*

Charter present (`.kittify/charter/charter.md`); `software-dev-default` template, tools git/mypy/pytest/ruff/spec-kitty. Relevant binding items and how the plan complies:

| Charter item | Compliance in this plan |
|---|---|
| Canonical sources / single authority (G2) | Core of the mission: derive `_DRG_NODE_KINDS` from `NodeKind` (IC-1); collapse two profile-reference surfaces to one (IC-2). |
| No new shadow paths | No new resolvers/enumerations; every fix consolidates onto an existing canonical seam. |
| Fail-loud / no silent drop | IC-1 (unknown kind), IC-3 (bad selection), IC-4 (fragment drop + warning suppression) all convert silence to derivation or a loud signal. |
| ATDD-first / red-first | Each WP writes the failing test first (drift-guard, org-tier fail-loud, executor-seam delivery, chain-delivery) before the fix. |
| Terminology canon | Mission-not-Feature; run the terminology guard pre-push (NFR-003). |
| No suppressions to pass gates | NFR-001 binds; fixes are real, not silenced. |
| `__all__` convention (C-007 charter) | Any new public helper added to the module `__all__`. |

No charter violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-drg-silent-drop-boundary-01M0PE7E/
├── plan.md              # this file
├── spec.md              # committed
├── research.md          # Phase 0 (this command) — consolidates the squad findings
├── data-model.md        # Phase 1 (this command) — schema/model + DRG-shape changes
├── quickstart.md        # Phase 1 (this command) — how to verify each fix
├── contracts/
│   └── failloud-seams.md # Phase 1 — the behavioural (fail-loud) contracts per seam
├── research/            # pre-plan squad findings (committed)
│   └── context-sources-drg-projection.md
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── synthesizer/topic_resolver.py        # IC-1: _DRG_NODE_KINDS derive-from-enum
│   ├── _drg_helpers.py                       # IC-4: org_roots seam folds drg/fragment.yaml; warning honesty
│   ├── action_doctrine_bundle.py            # IC-4: caller wiring (org_fragments)
│   └── context_renderers/profile_sections.py # IC-2: reads *-references (delivery, unchanged behaviour)
├── doctrine/
│   ├── drg/models.py                         # IC-1: canonical NodeKind (source of truth; not edited)
│   ├── drg/migration/extractor.py            # IC-2 (project from *-references :906-942), IC-3 (built-in + NEW org-tier governance-profile guard), IC-6 (doc-nit :557)
│   ├── drg/migration/hand_authored_overlay.py# IC-2: reconcile pedro suggests→034 vs new requires (F4)
│   ├── agent_profiles/profile.py             # IC-2: remove ContextSources.* fields
│   ├── agent_profiles/schema_models.py       # IC-2: remove AgentContextSources.* fields
│   └── agent_profiles/__init__.py            # IC-2: drop ContextSources from __all__ (C-007) (F2)
├── doctrine/schemas/agent-profile.schema.yaml# IC-2: drop context-sources block
scripts/
├── generate_schemas.py                       # IC-2: drop agent_context_sources annotation :485 (F2)
└── doctrine/inline_reference_inventory.py    # IC-2: retire _collect_context_sources :166 (F2)
├── specify_cli/
│   ├── mission_step_contracts/executor.py    # IC-4: caller wiring (org_fragments)
│   └── upgrade/migrations/                    # IC-2: profile context-sources→*-references migration
packs/
├── built-in/agent_profiles/*.agent.yaml      # IC-2: 25 profiles migrated to *-references
├── built-in/agent_profile.graph.yaml         # IC-2: regenerate (regenerate-graph, not hand-edit) + ledger (F5)
└── internal/                                 # IC-4: README refresh; #3530 class-b fixture
tests/
├── architectural/                            # IC-1 behaviour-pinned drift-guard; IC-2 golden re-ledger (test_golden_count_ban)
├── doctrine/drg/migration/                   # IC-2 projection + divergent-profile fixture, IC-3 built-in + org-tier fail-loud
├── doctrine/fixtures/                         # IC-5 NEW 2nd minimal org pack (class-a)
├── charter/ or specify_cli/                  # IC-4 executor/action-bundle valid-fragment red test
└── integration/                              # IC-5 chain-delivery: internal (class-b) + 2nd fixture (class-a)
```

**Structure Decision**: Single-project library layout (existing). Changes are
localized to the doctrine/charter seams listed; no new packages or top-level
dirs. Tests live beside the existing suites for each touched module.

## Implementation Concern Map

*The `/spec-kitty.tasks` command translates these concerns into work packages.
Each concern is independently testable (red-first) and small.*

*Amended after the post-plan brownfield squad (see `research/post-plan-brownfield-squad.md`; findings F1–F15).*

| IC | Concern | Issue | Key files | Depends on | Risk |
|----|---------|-------|-----------|------------|------|
| **IC-1** | Derive `_DRG_NODE_KINDS` from `NodeKind` **reusing the SSOT twin `merge.py:504` `_NODE_KIND_PREFIXES`**; drift-guard that **pins membership-gate behaviour** (monkeypatch a `NodeKind` member → recognized), not set-equality; confirm dropped URN kinds resolve | #3608 | `topic_resolver.py` (+ maybe import from `drg/models` or reuse merge twin); new behaviour test | — | Low — value==prefix structurally safe (`DRGNode._validate_urn`) [F7] |
| **IC-2** | Remove `context-sources.*`; consolidate on `*-references`; extractor projects from `*-references`; migrate 25 profiles; **update the full ≥8 consumer set** (`agent_profiles/__init__.py` `__all__`, `generate_schemas.py:485`, `inline_reference_inventory.py`, `test_emit_delivery_bind.py`, `test_supply_chain_profile_bindings.py`, 6+ profile tests); **migrate reviewer-renata's `additional: adversarial-evidence-disposition` binding deliberately** (not drop); **set-merge migration (not append)** with dup-guard; **regenerate `agent_profile.graph.yaml` + reconcile `hand_authored_overlay.py`**; **golden re-ledger** for the pedro/034 delta | #3629 p1 | `profile.py`, `schema_models.py`, `agent-profile.schema.yaml`, `extractor.py:906-942`, `agent_profiles/__init__.py`, `scripts/generate_schemas.py`, `scripts/doctrine/inline_reference_inventory.py`, `packs/built-in/agent_profiles/*.agent.yaml`, `packs/built-in/agent_profile.graph.yaml`, `hand_authored_overlay.py`, migration + the consumer tests + a **divergent user-profile fixture** | — | **High** — blast radius; C-006 has a real pedro/034 delivery change to handle [F2–F6] |
| **IC-3** | (a) Add end-to-end `generate_graph` raise test for built-in guard, close #3629 p2 built-in; (b) **IMPLEMENT** net-new **org-tier governance-profile scope extraction + fail-loud guard + tests** (no org-tier path exists today) | #3629 p2 | `extractor.py` (+ org loader path for governance-profiles), `tests/doctrine/drg/migration/` + org-tier test | — | **Medium/High** — org tier is net-new code, not verify [F8, F9] |
| **IC-4** | **Option (b): thread `org_fragments=load_org_drg(repo_root, strict=False)` at `executor.py:362` + `action_doctrine_bundle.py:192` only** (mirror the 4 correct dual-callers; do NOT fix at the seam — double-fold + mis-tier); confirm delivery despite the executor pre-probe (`:347-360`); do NOT widen to the `:245` DoctrineService seam; refresh `packs/internal` README | #3530 / operator | `executor.py`, `action_doctrine_bundle.py`, `packs/internal/README.md` + a **valid-fragment** red test | — | Medium — precedented pattern; guard the pre-probe warning [F1, F11–F13] |
| **IC-5** | Chain-delivery verification: (b) built-in + spec-kitty-internal (fragment-drop) via the executor/action-bundle seam; **(a) built-in + internal + a 2nd minimal org fixture** asserting pack #2's fragment node/edge reaches the merged graph (multi-org-pack fold); misconfigured-variant fails loud; close #3530 | #3530 | `tests/integration/` + `tests/doctrine/fixtures/` (new minimal org pack) | IC-4 | Medium — 2 fixtures; class-a + class-b [F10, F11] |
| **IC-6** | Golden re-ledger doc-nit — **must reflect IC-2's re-ledger**; sequence **after** IC-2 | #3629 p3 | `extractor.py:557` docstring | IC-2 | Trivial [F14] |

## Parallel Work Analysis

### Dependency Graph

```
IC-1 (SSOT + behaviour-pinned drift-guard) ─┐
IC-4 (thread org_fragments at 2 callers) ────┤ independent, parallel
IC-2 (profile consolidation + re-ledger) ────┤
   └─► IC-6 (doc-nit reflects IC-2 re-ledger) │  [needs IC-2]
IC-3 (built-in e2e test + org-tier implement)┘
                                              │
IC-4 ─────────────────────────────────────────► IC-5 (chain: class-b internal + class-a 2nd fixture)  [needs IC-4]
```

- **Sequential**: IC-5 depends on IC-4 (fragments must reach the consumer before
  the chain test can assert delivery). IC-6 depends on IC-2 (its docstring must
  describe IC-2's golden re-ledger).
- **Parallel streams**: IC-1, IC-2, IC-3, IC-4 touch largely disjoint files and
  can proceed concurrently.
- **File-conflict avoidance**: IC-2 and IC-3 both touch `extractor.py` (IC-2 the
  profile projection `:906-942`; IC-3 the governance-profile extraction + a new
  org-tier path). Serialize the `extractor.py` edits or assign both to one lane;
  IC-6's docstring edit lands last. IC-2 owns the `agent_profile.graph.yaml`
  golden regen — no other IC may regenerate it concurrently.

### Coordination Points

- After IC-4 lands, IC-5 builds the chain fixture and asserts delivery + fail-loud.
- Integration check: full targeted runs of `tests/doctrine/`, `tests/integration/`
  (org-pack + three-layer), `tests/architectural/` (drift-guard + terminology)
  before hand-off. Never the full suite in-session.

## Complexity Tracking

*No charter violations — none.*

## Engineering Alignment (confirmed — post-squad)

- Tech stack fixed; no new dependencies.
- **IC-4 approach = option (b)** (squad F1, decisive): thread
  `org_fragments=load_org_drg(repo_root, strict=False)` at `executor.py:362` and
  `action_doctrine_bundle.py:192` only. Do **not** fix at the `org_roots=` seam —
  it double-folds for the 4 callers that already pass both `org_roots`+`org_fragments`
  and mis-tiers org content into the built-in precedence layer. Scope the fix to
  the `:192` edge seam; do not widen to the `:245` DoctrineService seam.
- **IC-2 is under-scoped in the original plan** (squad F2–F6):
  - Consumer set is ≥8 (not 1); update `__all__`, schema-gen, inventory collector,
    and all asserting tests in the WP.
  - `additional` is **not** pure-drop: migrate reviewer-renata's
    `adversarial-evidence-disposition` binding deliberately (it is pinned by
    `test_supply_chain_profile_bindings.py:158`).
  - **C-006 has a real delivery change**: python-pedro/DIRECTIVE_034 (overlay
    `suggests→034` gets suppressed once 034 becomes a requires-diamond). Handle
    deliberately + ledger it; do not let it happen silently.
  - Migration is **set-merge (not append)** (`directive-references` already ⊇
    `context-sources.directives` for all 25 profiles) with a dup-guard.
  - **Regenerate `agent_profile.graph.yaml`** (`spec-kitty doctrine
    regenerate-graph`, never hand-edit) + reconcile `hand_authored_overlay.py`;
    add a composition-ledger row (or a walk-gate) for the pedro 9→10 delta.
  - Because shipped profiles are green-by-construction, FR-005's migration branch
    is proven only by a **divergent user-profile fixture** (ids not on
    `*-references`) + a frozen pre-migration snapshot; C-006 is pinned to the
    golden `agent_profile.graph.yaml` diff.
- **IC-3 expanded (operator decision)**: implement net-new org-tier
  governance-profile scope extraction + fail-loud guard + tests (no org-tier path
  exists today); plus an end-to-end `generate_graph` raise test for the built-in
  guard before closing #3629 p2.
- **IC-5 (operator decision)**: keep spec-kitty-internal (class-b fragment-drop)
  AND add a 2nd minimal org fixture to pin the multi-org-pack fold (class-a),
  asserting pack #2's fragment reaches the merged graph. (`merge_three_layers`
  already iterates all fragments — `merge.py:1251` — so class-a is only provable
  with ≥2 org packs.)
- **IC-1**: reuse the SSOT twin at `merge.py:504`; the drift-guard pins
  membership-gate behaviour (monkeypatch a `NodeKind` member), not tautological
  set-equality.
