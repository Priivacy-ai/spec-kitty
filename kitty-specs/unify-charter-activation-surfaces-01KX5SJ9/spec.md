# Mission Specification: Unify charter activation surfaces

**Mission**: unify-charter-activation-surfaces-01KX5SJ9
**Type**: software-dev
**Closes**: #2526 (Slice 0 / foundation of epic #2519) · unblocks #2522 (C) and #2521 (B)
**Status**: Draft

## Purpose (stakeholder-facing)

**TL;DR**: Make an activated doctrine artefact consistently active across all four charter surfaces (config, answers, references, graph) — no dangling.

Today `charter activate` updates only the runtime ledger (`.kittify/config.yaml activated_*`), while the compiled reference set (`.kittify/charter/references.yaml`) and the DRG graph derive from a *separate* authoring ledger (`.kittify/charter/interview/answers.yaml selected_*`). The two are disjoint with no reconciler, so an activated artefact is a live DRG node yet **dangles** in the compiled reference set until `answers.yaml` is hand-edited and synthesis re-runs. This concretely broke PR #2524 (`test_no_new_charter_reference_danglers` failed until `DIRECTIVE_046` was hand-added to `answers.yaml`). This mission makes **`config.activated_*` the single activation authority** and derives the compiled reference set + graph from it, retiring `answers.selected_*` as an activation source and adding a fail-closed parity guard. It is the prerequisite that de-conflicts the authoring (#2522) and preflight (#2521) follow-ups.

## Decision on record

**Reconciliation direction (resolved at spec time, DM 01KX5SK7):** *config as single authority.* `config.activated_*` is THE activation authority; `references.yaml` + graph + the compiled reference set derive from it; `answers.selected_*` is retired as an activation source (interview-record only); `consistency_check` asserts derived-vs-config parity and fails closed on divergence. This aligns with the charter's governing principle of a single canonical authority.

## Context & Motivation

Two unreconciled representations of "which artefact is active":
- **`config.yaml activated_*`** — runtime activation state, written by `charter activate`/`deactivate` through `charter.activation_engine.commit_plan` (single config write), read authoritatively by `PackContext.from_config()`.
- **`answers.yaml selected_*`** — authoring/compile state, compiled by `src/charter/compiler.py` into `references.yaml` + `src/doctrine/graph.yaml` via `charter generate`/`synthesize`.

No code reconciles them (grep-confirmed empty). The guardrails are themselves split-brained: `consistency_check.py` sees only config; `freshness/computer.py` sees only references/graph. Observed today: `config.yaml` carried 25 activated directives while the answers-derived `references.yaml` carried 24 — config is already the superset/runtime SSOT, making it the natural single authority.

## User Scenarios & Testing

**Primary actor**: a Spec Kitty maintainer running `charter activate`/`deactivate` (and, transitively, every agent/harness that relies on the compiled reference set resolving activated artefacts).

**Primary scenario (happy path)**: A maintainer runs `charter activate <kind> <id>`. The artefact is added to `config.activated_*`; the compiled reference set and graph derive from config, so the artefact **resolves in `references.yaml` with no manual `answers.yaml` edit and no separate step**. The `#2524`-style dangler cannot occur.

**Deactivate**: `charter deactivate <kind> <id>` removes it from `config.activated_*`; the derived surfaces drop it symmetrically; no orphaned reference remains.

**Divergence guard**: If the derived surfaces (`references.yaml`/graph) are stale or inconsistent with `config.activated_*` (e.g. config edited without re-derivation), `consistency_check` **fails closed** — surfacing the divergence before CI.

**Migration**: An existing project whose compiled set was answers-derived reconciles to config-derived using `config.activated_*` as the seed, with **no active artefact dropped**.

**Rule that must always hold**: after any activate/deactivate, the four surfaces (config authority + answers record + derived references + derived graph) are consistent: every entry in `config.activated_*` resolves in the compiled reference set, and nothing resolves that is not in `config.activated_*`.

### Acceptance Scenarios

1. **Activate resolves (the #2524 regression)**: `charter activate directive <id>` → the artefact resolves in the compiled reference set; a regression test reproducing `test_no_new_charter_reference_danglers`'s failure passes after a plain activate, with no `answers.yaml` edit.
2. **Deactivate drops**: `charter deactivate` → the artefact no longer resolves; no dangling reference remains.
3. **Answers is inert for activation**: editing `answers.selected_*` without a corresponding `config.activated_*` change has **no effect** on the compiled reference set (proves answers is retired as an activation source).
4. **Fail-closed parity guard**: a planted divergence (an entry in `config.activated_*` absent from the derived reference set, or vice-versa) makes `consistency_check` fail with a clear, actionable message.
5. **Migration preserves the active set**: on an existing project, switching the derivation to config drops zero previously-active artefacts (config-superset seed).

### Edge Cases

- **Interview → activation path**: `charter interview` still captures selections into `answers.yaml`; those selections must land in `config.activated_*` (the authority) so a fresh charter's interview selections are active. The interview record persists; it is no longer the derivation source.
- **Empty/first-run project** (`built_in_only`): config-derived resolution must behave identically to today for a project with no project-layer activations. **Absent-key semantics (resolved — squad, 2026-07-10):** an absent `activated_<kind>` key means "all built-ins active" (`PackContext.from_config` is three-state). The promotion primitive (FR-007) must therefore, on an absent key, **preserve the all-built-ins-active set** (union the built-ins for that kind, then append the promoted ids) — it must NOT write a bare restrictive list, which would flip runtime resolution from all-built-ins to only-selected and drop the remaining built-ins (violating NFR-004/C-005). A first-run regression pins this.
- **Graph freshness**: the config-derived synthesis must keep `src/doctrine/graph.yaml` byte-fresh (the deterministic `generate_graph` freshness gate stays green).
- **Deactivate of a shared/referenced artefact**: must not strand a reference held by another active artefact (existing shared-reference safety, C-005 of the activation engine, is preserved).

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `config.activated_*` (the per-kind activation lists in `.kittify/config.yaml`) is the **single declared authority** for which doctrine artefacts are active. | Draft |
| FR-002 | The compiled reference set (`references.yaml`) and the DRG-graph derivation resolve activated artefacts from `config.activated_*`, **not** from `answers.selected_*`. | Draft |
| FR-003 | `answers.selected_*` is **retired as an activation source** — it is an interview record only and no longer feeds the compiled reference set / graph derivation. | Draft |
| FR-004 | `charter activate`/`deactivate` leave the compiled reference set coherent **with no manual `answers.yaml` edit and no separate synthesis step** — the artefact resolves (activate) or stops resolving (deactivate) as a direct consequence of the config write. | Draft |
| FR-005 | `consistency_check` asserts derived-vs-config parity (`config.activated_*` ⇔ compiled reference set ⇔ graph) and **fails closed** on divergence, with an actionable message. This is the regression guard for the #2524 dangler class. | Draft |
| FR-006 | **Migration**: existing projects whose compiled set was answers-derived reconcile to config-derived using `config.activated_*` as the seed, dropping **zero** previously-active artefacts. | Draft |
| FR-007 | The interview flow's selections are **promoted into `config.activated_*`** (the authority) via a shared append-promotion primitive, so a freshly-interviewed charter's selections are active; `answers.yaml` remains the captured interview record. **In-slice** (the same primitive the migration FR-006 needs — indivisible; splitting it would regress fresh charters, esp. paradigms). Only the *re-interview replace/deselect* refinement (deactivating dropped selections) is deferred to a follow-up; append-only promotion is the in-slice behaviour. | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | No dangling introduced by activation. | 0 danglers: after `charter activate`, 100% of `config.activated_*` entries resolve in the compiled reference set (regression test green). | Draft |
| NFR-002 | The parity guard is enforced in the doctrine/fast test tier and is non-vacuous. | A planted config↔derived divergence is flagged (self-test proves the guard bites); guard runs in the doctrine suite. | Draft |
| NFR-003 | Layer + quality gates preserved. | `charter` package does not import `specify_cli` (`test_charter_does_not_import_specify_cli` green); ruff + mypy zero issues; complexity ≤15 on new/changed functions. | Draft |
| NFR-004 | No regression to runtime resolution already reading config. | `PackContext`/`DoctrineService` runtime resolution behaviour unchanged; full `tests/doctrine/` + graph-freshness + terminology guard green. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Reconciliation/derivation logic lives in the `charter` package; CLI orchestration lives in the `specify_cli` charter command layer. The `charter` package must not import `specify_cli` (layer rule). | Draft |
| C-002 | The single config write chokepoint is `charter.activation_engine.commit_plan`. Do **not** build the cascade engine — the accepted-and-forwarded `cascade` param stays a reserved seam. | Draft |
| C-003 | The `generate_graph` freshness gate stays green — the config-derived synthesis must keep `src/doctrine/graph.yaml` byte-deterministic. | Draft |
| C-004 | Migration must not silently drop active artefacts; `config.activated_*` is the authoritative migration seed. | Draft |
| C-005 | Behaviour-preserving for consumers that already read `config.activated_*` (`PackContext.from_config`); only the answers→derived pipeline changes source. | Draft |
| C-006 | **ID-form normalization must be lossless.** `config.activated_*` holds slug-stems (`001-…`) while the compiler/DRG use canonical URNs (`DIRECTIVE_001` / `directive:DIRECTIVE_001`). The derivation must map stems→canonical exactly as the live `DoctrineService` does; a stem that fails to normalize must be **rejected, never silently dropped** (a silent drop removes the directive + its whole transitive closure — the #2524 class in reverse). | Draft |
| C-007 | **Three ledgers stay distinct.** `answers.selected_*` (interview, retired as activation source), `config.activated_*` (authority), and `governance.yaml doctrine.selected_*` (a THIRD, separate compiled ledger) must not be conflated; this mission touches only the first two. `spdd_reasons/activation.py` reads governance/directives, not answers — leave it alone. | Draft |
| C-008 | Switching the derivation source changes the *content* of the committed `references.yaml` + `src/doctrine/graph.yaml` (config adds paradigms + direct styleguides/toolguides). They must be regenerated and re-committed, and the `test_dangling_baseline_is_shrink_only` baseline shrunk to empty (the intended #2380 outcome) — a required in-mission test edit. | Draft |

## Key Entities

- **Activation ledger** — `config.activated_*` (per-kind lists in `.kittify/config.yaml`); the single activation authority.
- **Compiled reference set** — `references.yaml`; DERIVED from the activation ledger.
- **DRG graph** — `src/doctrine/graph.yaml` (built-in) / induced charter graph; DERIVED.
- **Interview record** — `answers.yaml selected_*`; captured interview selections; NO longer an activation authority.

## Success Criteria

| ID | Criterion | Measure |
|----|-----------|---------|
| SC-001 | Activation no longer dangles. | `charter activate <kind> <id>` with no manual step → artefact resolves in `references.yaml`; the #2524 regression test passes. |
| SC-002 | Divergence is caught before CI. | A config↔derived divergence fails `consistency_check` locally (fail-closed). |
| SC-003 | Migration preserves the active set. | On existing projects, 0 previously-active artefacts dropped by the authority switch. |
| SC-004 | Answers is inert for activation. | Editing `answers.selected_*` without a config change has no effect on the compiled reference set. |

## Assumptions

- `config.activated_*` is already the runtime SSOT (`PackContext.from_config`) and today a superset of the answers-derived set (25 vs 24 directives observed), so it is a safe, lossless migration seed.
- The interview → config promotion (FR-007) is in scope as the minimal path to keep fresh-charter interview selections active; if the interview rewrite proves large, the core authority move (FR-001–FR-005) can land first with FR-007 as an explicit follow-up rather than blocking the slice.
- No change to the *set* of artefacts a given project has active — this is a source-of-derivation change, not a re-selection.

## Out of Scope

- Emitting `CharterCreated`/`CharterUpdated` events (child A, #2520).
- The `charter author` scaffold command (child C, #2522).
- Making `mission-type` an activatable kind (#2468 / epic #2466 — `MissionTypeNotAnArtifactKind` is deliberate).
- Implementing the cascade engine (reserved seam only).
- The harness-freshness preflight / deterministic intake (child B, #2521).
