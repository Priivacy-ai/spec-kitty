# Implementation Plan: Charter Delivery Finish and Context Degod

**Branch**: `feat/charter-delivery-finish-context-degod` | **Date**: 2026-07-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/charter-delivery-finish-context-degod-01KYT4BY/spec.md`

## Summary

Land the three doctrine-delivery follow-ups — #3082 (fetch-stanza prose), #3064 (empty-charter dispatch → generic agent + warning + default charter asset), #2532 (full `charter/context.py` decomposition) — as **one mission, all complete**. Two profile-loaded research passes ([research.md](research.md)) validated the seams and corrected two load-bearing points: (1) the #3064 fix is a surgical pre-check at the executor auto-route branch (a new `invocation/empty_charter.py`), leaving the shared activation gate, `ProfileRegistry`, and all gate/parity fixtures **untouched** — governance context already agrees by construction; (2) #2532 is a *consolidation* into the existing `context_renderers/` package, dissolving the `profile_sections` import cycle by pinning 4 symbols to leaf homes, with a residual-LOC ceiling as the non-fakeable completion signal. Load-bearing ordering: US2+US1 land before the US3 parity baseline is captured; US3's profile-resolution/doctrine-service seams extract last against the frozen US1 wrapper region.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (existing; no new runtime deps)
**Storage**: N/A (charter config is file-based `.kittify/config.yaml`; doctrine assets on disk)
**Testing**: pytest (targeted packages per charter §Testing — `tests/specify_cli/invocation/`, `tests/charter/`, `tests/specify_cli/next/`, `tests/architectural/`); mypy --strict; ruff
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows)
**Project Type**: single (CLI library)
**Performance Goals**: no regression; charter-context resolution stays < 2s per charter CLI budget
**Constraints**: charter→doctrine layering (no `specify_cli` import under `src/charter/`); prompt-governance wire contract intact; byte-parity on the three public `build_charter_context*` entry points; User Customization Preservation (never overwrite a user charter); no version-number prescription in scope
**Scale/Scope**: 3 workstreams; `context.py` 3243 → ≤500 LOC across ~17 seam homes; ~2 new invocation modules + 2 new asset files; new tests only for US1 (no gate/parity re-baseline)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter rule | Status | Note |
|---|---|---|
| Single canonical authority (DIR-044) | ✅ | US1 keys on the existing `charter_activated_urns` authority (composite); no new "empty" definition. US3 consolidates into existing `context_renderers/` homes, not parallel ones. |
| Architectural alignment / layering (DIR-001) | ✅ | No `specify_cli` import added under `src/charter/`; US1 change lives in `specify_cli/invocation/`, reading the charter authority down-layer (legal). |
| DDD + tiered rigour | ✅ | Core render/decision logic gets focused unit tests; glue (service construction) extracted as thin seams. |
| ATDD-first (C-011) | ✅ | Each WP lands a red-first test through the pre-existing entry point before implementation. |
| Terminology canon | ✅ | Warning copy + asset content use canonical terms; `test_no_legacy_terminology.py` in the pre-push gate. |
| `__all__` convention (C-007) | ✅ | Every new `src/charter/` seam declares `__all__`. |
| Campsite-first (DIR-025) | ✅ | US3 *is* the campsite paydown for `context.py`; US1/US2 clean their touched surfaces first. |
| No version prescription | ✅ | No patch numbers assigned. |
| Reviewer ≠ implementer | ✅ | Enforced at review. |

**Post-design re-check**: no new violations introduced by the seam map; the only contract-widening candidate (`_WHEN_DOING_RE`) is avoided by default (normalize, not widen).

## Project Structure

### Documentation (this mission)
```
kitty-specs/charter-delivery-finish-context-degod-01KYT4BY/
├── plan.md              # this file
├── spec.md
├── research.md          # Phase 0 — validated seams + decisions
├── data-model.md        # Phase 1 — seam→home map + invariants
├── quickstart.md        # Phase 1 — verification commands
├── contracts/           # Phase 1 — behavioural contracts
│   ├── empty-charter-fallback.md
│   ├── fetch-stanza-normalization.md
│   └── context-decomposition-parity.md
├── notes/post-spec-squad-findings.md
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)
```
src/charter/
├── context.py                     # → thin orchestration surface (≤500 LOC) + FR-009 re-export shim
├── context_renderers/             # existing package — CONSOLIDATE + add render seams
│   ├── token_budget.py            # + _enforce_token_budget, _budget_estimate, _PROFILE_INLINE_BODY_LIMIT_CHARS
│   ├── fetch_stanza.py            # + fold _render_fetch_stanza; US2 normalization lands here
│   ├── reference_pointers.py      # + _load_references
│   ├── profile_sections.py        # + profile-cited render half; cycle imports go top-level
│   ├── catalog_diagnosis.py       # NEW leaf (dissolves cycle)
│   ├── artifact_bodies.py         # NEW render
│   ├── template_include.py        # NEW render
│   ├── selection_block.py         # NEW render
│   ├── activation_block.py        # NEW
│   ├── compact_governance.py      # NEW render
│   └── bootstrap_text.py          # NEW render
├── charter_md_parsing.py          # NEW (non-render)
├── context_state.py               # NEW (non-render)
├── context_json.py                # NEW (non-render)
├── org_pack_discovery.py          # NEW (non-render)
├── action_doctrine_bundle.py      # NEW (non-render)
├── profile_resolution.py          # NEW — LAST (caches + _reset_agent_profile_cache)
└── doctrine_service_builder.py    # NEW — LAST (US1-frozen region)

src/specify_cli/invocation/
├── empty_charter.py               # NEW — resolve_generic_fallback (composite predicate)
├── executor.py                    # auto-route branch call + empty_charter_fallback payload flag
├── router.py                      # RouterDecision.confidence Literal += "generic_fallback"
└── ...

src/specify_cli/cli/commands/dispatch.py   # one-shot warning panel in _render_rich_payload
src/doctrine/assets/built-in/
├── charter_scaffold_minimal.yml            # NEW — minimal curated starter
└── charter_scaffold_minimal.yml.asset.yaml # NEW — sidecar (id: common-charter-scaffold-minimal)

tests/specify_cli/invocation/test_empty_charter_fallback.py     # NEW (predicate truth table + decision)
tests/specify_cli/invocation/cli/test_dispatch.py               # extend (routing+governance agreement, warning, --json)
tests/charter/test_context_decomposition_completion.py          # NEW (seam manifest + LOC ≤600)
tests/charter/...                                               # seam unit tests (US3) + non-trivial parity fixture
```

**Structure Decision**: single-project CLI library; changes span the charter render layer (`src/charter/`), the invocation/dispatch layer (`src/specify_cli/invocation/`, `.../cli/commands/dispatch.py`), and the doctrine asset tier (`src/doctrine/assets/built-in/`). No new top-level packages.

## Complexity Tracking

No Charter Check violations — table intentionally empty.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Fetch-stanza when-clause normalization (US2 / #3082)
- **Purpose**: Make generated `When you …` disclosure lines grammatical for all clause shapes without breaking the closed-verb prompt-governance contract.
- **Relevant requirements**: FR-001; NFR-003; SC-003.
- **Affected surfaces**: `src/charter/activation/context_renderers/fetch_stanza.py`; `tests/specify_cli/next/test_wp_prompt_governance_contract.py` (per-stanza assertion helper).
- **Sequencing/depends-on**: none (isolated; lands early — feeds the US3 parity baseline).
- **Risks**: `_WHEN_DOING_RE` is a closed 6-verb set — normalize into it; widening the regex is a documented contract change, avoided by default.

### IC-02 — Empty-charter generic-agent fallback + governance scoping + warning (US1 / #3064)
- **Purpose**: Route unconfigured-charter auto-dispatch to a warned generic agent using **no doctrine in either routing or governance context**, without disturbing the shared activation gate or explicit-profile dispatch.
- **Relevant requirements**: FR-002, FR-010, FR-003, FR-004, FR-006; C-003; SC-001.
- **Affected surfaces**: NEW `src/specify_cli/invocation/empty_charter.py`; `invocation/executor.py` (auto-route branch + `empty_charter_fallback` payload flag, threaded at the single construction site); `invocation/router.py` (`RouterDecision.confidence` Literal += `generic_fallback`); the **governance-scoping** for the fallback path (e.g. a `build_charter_context(..., suppress_project_resolver=True)` param — bounded to the fallback, `src/charter/`); `cli/commands/dispatch.py` (one-shot warning via `getattr`); NEW `tests/specify_cli/invocation/test_empty_charter_fallback.py` + extend `.../cli/test_dispatch.py` (incl. **red-first governance-agreement** assertion on the `Directive IDs:` block).
- **Sequencing/depends-on**: none (independent of IC-01/IC-03). Lands before the IC-04 parity baseline.
- **Risks**: composite predicate spans ALL activatable dimensions (URNs ∅ **and** agent_profiles/mission_step_contracts/glossary_packs all None **and** no org packs) — a narrow predicate false-fallbacks on a configured repo; governance does NOT agree for free (compact view catalog-falls-back to the full `DIR-###` canon under empty charter) so FR-010 is in scope; gate/`ProfileRegistry` fixtures must stay green (not owned); explicit `--profile` must bypass the fallback.

### IC-03 — Default charter asset (US1 / #3064)
- **Purpose**: Ship a resolvable/copyable default `charter.yml` so a user can skip authoring a charter.
- **Relevant requirements**: FR-005; C-002; SC-002.
- **Affected surfaces**: NEW `src/doctrine/assets/built-in/charter_scaffold_minimal.yml` + `.asset.yaml` sidecar (`id: common-charter-scaffold-minimal`); a `pack_validator` mime guard test; an **activatability** test (activate in a temp repo → valid charter, user charter untouched).
- **Sequencing/depends-on**: none (parallelizable with IC-02).
- **Risks**: content is a **minimal curated starter** (not `packs/default.yaml`, which activates all — operator-visible decision, non-blocking); named to avoid "default charter" collision (cross-ref both files); `mime: application/yaml` (guard, not a 3.13-only fix); resolve/copy-only, never overwrite a user charter.

### IC-04 — context.py seam extraction: pure/leaf cluster (US3 / #2532)
- **Purpose**: Extract the low-risk, pure-transform seams and dissolve the `profile_sections` import cycle.
- **Relevant requirements**: FR-007, FR-008 (partial), FR-009; NFR-001, NFR-004; SC-004.
- **Affected surfaces**: `catalog_diagnosis.py` (new leaf), `token_budget.py`/`fetch_stanza.py`/`reference_pointers.py` (consolidate), `artifact_bodies.py`, `charter_md_parsing.py`, `context_state.py`, `template_include.py`, `selection_block.py`, `activation_block.py`, `bootstrap_text.py`, `compact_governance.py`, `context_json.py`; seam unit tests.
- **Sequencing/depends-on**: after the parity baseline is captured (which is after IC-01+IC-02 merge). Follow the low→high extraction order in research.md Decision 7.
- **Risks**: parity corpus must be non-trivial (token-budget + catalog-miss + first-load); FR-009 re-export shim for the ~40 test-only privates; each new module declares `__all__`.

### IC-05 — context.py seam extraction: service/profile-resolution cluster + completion (US3 / #2532)
- **Purpose**: Extract the entangled, US1-adjacent seams last and prove decomposition completion.
- **Relevant requirements**: FR-008 (completion), FR-009; NFR-001, NFR-002, NFR-005; SC-004.
- **Affected surfaces**: `profile_resolution.py` (caches + `_reset_agent_profile_cache`), `doctrine_service_builder.py` (`_build_activation_aware_doctrine_service`, the ~L1550-1566 US1-frozen region), `org_pack_discovery.py`, `action_doctrine_bundle.py`; residual `context.py` orchestration + FR-007 retrospective note; NEW `tests/charter/test_context_decomposition_completion.py` (seam-existence manifest **+** `wc -l context.py ≤ 600`).
- **Sequencing/depends-on**: **after IC-02 approved and the IC-04 parity baseline is frozen** (US1∩US3 collision region). Extract this cluster last.
- **Risks**: this is the exact region US1 mutates — freeze the wrapper boundary before relocating; seam-existence manifest is the primary completion signal, `≤600` is the LOC gate (floor ≈500–540; ≤500 stretch; 400 dropped); missing `≤600` is a BLOCKER needing operator re-sign-off, not an implementer ceiling tweak.
