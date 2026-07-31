# Tasks: Charter Delivery Finish and Context Degod

**Mission**: `charter-delivery-finish-context-degod-01KYT4BY` | **Branch**: `feat/charter-delivery-finish-context-degod`
**Planning base**: `feat/charter-delivery-finish-context-degod` | **Merge target**: `main` (via PR)

Design authority: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/). Post-spec + post-plan squad evidence in [notes/](notes/). Every WP is ATDD red-first (C-011) and reviewer ≠ implementer.

## Sequencing (load-bearing — see research.md Decision 8/10)

```
WP01 (US2 prose) ─┐
WP02 (US1 route) ─┼─→ WP04 (US3 leaf+cycle+parity baseline) → WP05 (US3 render) → WP06 (US3 service+completion)
WP03 (US1 gov+asset, ← WP02) ─┘
```
WP01 and WP02 are independent (parallel). WP03 depends on WP02. The US3 parity baseline (WP04) is captured **only after** WP01+WP02+WP03 are approved, and includes the empty-charter input (provenance proof). `context.py` is owned solely by WP06; WP04/WP05 make declared coupled out-of-map edits to it (sequential chain — no parallel collision).

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first per-stanza grammaticality test (4 clause shapes) | WP01 | |
| T002 | Normalize `when` clause into closed 6-verb set in `fetch_stanza_lines` | WP01 | |
| T003 | Fold thin `_render_fetch_stanza` wrapper into `fetch_stanza.py` | WP01 | |
| T004 | Per-stanza assertion helper wired into contract test | WP01 | |
| T005 | Verify byte-unchanged good path; ruff+mypy | WP01 | |
| T006 | Red-first predicate truth-table + decision-shape test | WP02 | |
| T007 | `empty_charter.py::resolve_generic_fallback` (composite predicate) | WP02 | |
| T008 | Wire executor auto-route branch + `empty_charter_fallback` payload flag | WP02 | |
| T009 | Widen `RouterDecision.confidence` Literal | WP02 | |
| T010 | One-shot empty-charter warning in `dispatch.py` (getattr-safe) | WP02 | |
| T011 | Dispatch test: routing→generic-agent, --json, explicit-profile bypass, software-dev | WP02 | |
| T012 | Red-first governance-agreement test (Directive IDs block empty) | WP03 | |
| T013 | Empty-charter governance scoping (suppress project resolver on fallback) | WP03 | |
| T014 | Ship `charter_scaffold_minimal.yml` + `.asset.yaml` sidecar | WP03 | |
| T015 | Asset mime guard + resolvability test | WP03 | |
| T016 | Asset activatability test (temp repo, user charter untouched) | WP03 | |
| T017 | Capture non-trivial parity baseline (token-budget + miss + first-load) post-US1 | WP04 | |
| T018 | Extract `catalog_diagnosis.py` (leaf) | WP04 | |
| T019 | Consolidate `token_budget.py` (`_budget_estimate`, limit, `_enforce_token_budget`) | WP04 | |
| T020 | Consolidate `reference_pointers.py` + new `charter_md_parsing.py` | WP04 | |
| T021 | New `artifact_bodies.py` + `context_state.py` | WP04 | |
| T022 | Dissolve `profile_sections` import cycle (top-level imports, drop noqa) | WP04 | |
| T023 | Verify parity green + seam unit tests + ruff/mypy | WP04 | |
| T024 | Extract `template_include.py` | WP05 | |
| T025 | Extract `selection_block.py` | WP05 | |
| T026 | Extract `activation_block.py` | WP05 | |
| T027 | Extract `bootstrap_text.py` + `compact_governance.py` | WP05 | |
| T028 | FR-009 shim updates + parity green + seam tests | WP05 | |
| T029 | Extract `context_json.py` + `org_pack_discovery.py` + `action_doctrine_bundle.py` | WP06 | |
| T030 | Extract `profile_resolution.py` (caches + `_reset_agent_profile_cache`) | WP06 | |
| T031 | Extract `doctrine_service_builder.py` (US1-frozen region) | WP06 | |
| T032 | Thin `context.py` to residual + FR-009 re-export block + FR-007 note | WP06 | |
| T033 | Wire completion test (seam manifest + LOC ≤600); verify all gates green | WP06 | |

---

## WP01 — US2: fetch-stanza when-clause prose (#3082)
**Priority**: P2 · **Prompt**: [tasks/WP01-fetch-stanza-prose.md](tasks/WP01-fetch-stanza-prose.md) · **~300 lines** · **Deps**: none
**Goal**: Make every generated `When you …` disclosure line grammatical across all clause shapes while keeping the closed-6-verb prompt-governance contract green (per-stanza).
**Independent test**: Feed gerund / full-sentence / `STATED_DEFAULT_WHEN` / well-formed clauses → each emitted stanza grammatical AND matches `_WHEN_DOING_RE`/`_FETCH_CMD_RE`.
Subtasks: T001 T002 T003 T004 T005 · **Requirements**: FR-001, NFR-003

## WP02 — US1: empty-charter routing fallback + warning (#3064)
**Priority**: P1 · **Prompt**: [tasks/WP02-empty-charter-routing.md](tasks/WP02-empty-charter-routing.md) · **~420 lines** · **Deps**: none
**Goal**: Auto-route dispatch under a wholly-empty charter to the `generic-agent` (composite predicate) with a one-shot warning, without touching the shared gate/`ProfileRegistry`.
**Independent test**: empty charter + no `--profile` → `generic-agent` + warning + `--json` flag; explicit `--profile` bypasses; any activation → no fallback.
Subtasks: T006 T007 T008 T009 T010 T011 · **Requirements**: FR-002, FR-003, FR-004, FR-006

## WP03 — US1: empty-charter governance scoping + default charter asset (#3064)
**Priority**: P1 · **Prompt**: [tasks/WP03-governance-scoping-and-asset.md](tasks/WP03-governance-scoping-and-asset.md) · **~360 lines** · **Deps**: WP02
**Goal**: Ensure the empty-charter dispatch governance block leaks no doctrine (suppress the project catalog-fallback directives), and ship the minimal charter scaffold asset.
**Independent test**: empty-charter dispatch `Directive IDs:` block empty; `doctrine asset path common-charter-scaffold-minimal` resolves + activates to a valid charter without touching a user charter.
Subtasks: T012 T013 T014 T015 T016 · **Requirements**: FR-010, FR-005

## WP04 — US3: context.py leaf/pure extraction + cycle dissolution + parity baseline (#2532)
**Priority**: P3 · **Prompt**: [tasks/WP04-context-leaf-extraction.md](tasks/WP04-context-leaf-extraction.md) · **~480 lines** · **Deps**: WP01, WP02, WP03
**Goal**: Capture the non-trivial parity baseline, extract the low-risk pure/leaf seams, and dissolve the `profile_sections` import cycle — byte-parity preserved.
**Independent test**: parity fixture (token-budget + miss + first-load) byte-identical; cycle dissolved (no `noqa: PLC0415`); seam unit tests green.
Subtasks: T017 T018 T019 T020 T021 T022 T023 · **Requirements**: FR-007, FR-008, FR-009, NFR-001

## WP05 — US3: context.py render-seam extraction (#2532)
**Priority**: P3 · **Prompt**: [tasks/WP05-context-render-extraction.md](tasks/WP05-context-render-extraction.md) · **~420 lines** · **Deps**: WP04
**Goal**: Extract the render seams (template-include, selection-block, activation-block, bootstrap-text, compact-governance) — byte-parity preserved.
**Independent test**: parity fixture byte-identical; each new render module has focused unit tests.
Subtasks: T024 T025 T026 T027 T028 · **Requirements**: FR-008, FR-009

## WP06 — US3: context.py service extraction + residual + completion (#2532)
**Priority**: P3 · **Prompt**: [tasks/WP06-context-service-and-completion.md](tasks/WP06-context-service-and-completion.md) · **~460 lines** · **Deps**: WP05
**Goal**: Extract the service/profile-resolution seams (LAST — US1-frozen region), thin `context.py` to residual orchestration, and wire the non-fakeable completion test.
**Independent test**: `test_context_decomposition_completion.py` (seam manifest + `wc -l ≤ 600`) green; layer-rule/`__all__`/dead-symbol/parity all green.
Subtasks: T029 T030 T031 T032 T033 · **Requirements**: FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-005

---

## MVP

WP01 + WP02 (each independently shippable, no deps) deliver the two highest-value user-visible slices (grammatical guidance + governed empty-charter dispatch). WP03 completes US1. WP04→WP06 pay down the `context.py` god-module last.
