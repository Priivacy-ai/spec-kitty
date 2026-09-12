# Implementation Plan: Frozen-baseline toll reduction

**Branch**: `fix/frozen-baseline-toll-reduction` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/frozen-baseline-toll-reduction-01M0A42D/spec.md`

## Summary

Drain the narrow set of genuine-toll frozen-absolute-baseline gates (dead-symbol hash-refresh, skip-marker growth, redundant migration count, an inert baseline key) while leaving every load-bearing gate untouched. Design decisions settled by an architect pass (see [research.md](./research.md)), all counts re-verified against `main`: FR-003's review-forcing teeth are **structural** (the mandatory co-located `# round-trip: skip: <reason>` diff line), not a gate output; FR-004 **keeps** the `_CATEGORY_1` frozenset change-detector and derives only the redundant count; FR-002 uses a **fail-closed, existing-entry-only** match algorithm reusing the gate's own resolver as the single hashing authority.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest (built-in `record_property`, `ast`, `hashlib`); `ruamel.yaml`/`pydantic` already in-tree. **No new dependency is added** (a new hashing/parsing lib would violate the single-hashing-authority design — see research.md).
**Storage**: N/A — test-config surfaces only (`tests/architectural/_baselines.yaml`, allowlists inside gate `.py` files).
**Testing**: pytest architectural gates; ATDD red-first; the NFR-001/SC-006 regression **runs the helper** over a constructed tree (non-fakeable), including the `bare_name`-collision case.
**Target Platform**: Linux CI (`arch-adversarial` tier) + local developer runs (`-m fast`).
**Project Type**: single (test-infrastructure + one migration-count derivation)
**Performance Goals**: each `fast`-marked gate < 1 s per test **call, warm** (NFR-002; verified: `test_ratchet_baselines` ≤ 0.32 s, `test_ratchet_positional_anchor_ban` ≤ 0.52 s).
**Constraints**: no new CI job, no external-service integration (C-002 cost ceiling); zero load-bearing-gate regression (NFR-003); ruff + mypy `--strict` clean, zero new suppressions, complexity ≤ 15 (NFR-004).
**Scale/Scope**: ~4 WPs across two file-disjoint lanes; surfaces are `tests/architectural/` + the `test_no_dead_modules` dead-migration predicate.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`.kittify/charter/charter.md`). Relevant gates and status:

- **Single canonical authority** — ✅ the refresh helper reuses `_symbol_key.resolve_symbol_key`/`key_tier`/`classify_collisions` as the *single* hashing authority; no private recompute. FR-004 derives the count from the gate's own dead-migration predicate (one authority for "dead auto-discovered migration").
- **ATDD-first / tests for new behaviour (DIR-005)** — ✅ NFR-001/SC-006 mandate a red-first, helper-executing regression; each new branch is tested directly.
- **Quality & tech-debt standing orders** — ✅ this mission *is* tech-debt reduction; it removes toll without weakening load-bearing gates (C-001 fence, NFR-003).
- **mypy `--strict` / no suppressions (DIR-006, NFR-004)** — ✅ committed to.
- **No supply-chain change** — ✅ no dependency added (dependency-hygiene tactic).

No violations → Complexity Tracking is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/frozen-baseline-toll-reduction-01M0A42D/
├── plan.md              # This file
├── research.md          # Design decisions (C-002a/b, FR-002, merge-coupling, NFR-002) + re-verified values + risks
├── data-model.md        # Entities: SymbolKey tiers, allowlist entry, dead-migration, baseline key, refresh candidate
├── quickstart.md        # How to run the helper + the fast gates locally
├── contracts/
│   └── gate-behavior-contracts.md   # FR-002 helper contract + FR-003/FR-004 gate-behavior contracts
└── tasks.md             # (created later by /spec-kitty.tasks)
```

### Source Code (repository root)

```
tests/architectural/
├── _symbol_key.py                       # (read) single hashing authority: resolve_symbol_key / key_tier / classify_collisions
├── test_no_dead_symbols.py              # (edit) membership gate; hosts the dead-symbol allowlist
├── _refresh_dead_symbol_hashes.py       # (NEW) fail-closed refresh helper — `_`-prefixed test-infra scaffolding
├── test_ratchet_baselines.py            # (edit) FR-003 skip-marker extraction, FR-004 derive count, FR-005 grandfather drain
├── _baselines.yaml                      # (edit) FR-003 skip_marker key, FR-004 category_1 key, FR-005 delete inert block
├── test_ratchet_positional_anchor_ban.py# (edit) FR-006 fast marker
└── test_no_dead_modules.py              # (read) source of the dead-migration predicate FR-004 derives against
```

**Structure Decision**: Single project, test-infrastructure-scoped. The new helper is `_`-prefixed so it is not itself flagged by `test_no_dead_modules`. Two file-disjoint lanes (see Implementation Concern Map) merge independently.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Dead-symbol refresh helper (safe by construction)

- **Purpose**: Let a maintainer refresh the `body_hash` of a *still-dead* allowlisted symbol after a body edit, without ever admitting a *new* dead symbol — the mission's safety-critical concern.
- **Relevant requirements**: FR-001, FR-002, NFR-001, SC-002, SC-006; US1 (all three acceptance scenarios).
- **Affected surfaces**: NEW `tests/architectural/_refresh_dead_symbol_hashes.py`; `tests/architectural/test_no_dead_symbols.py` (regression + possibly provenance-comment normalization); reads `_symbol_key.py`.
- **Sequencing/depends-on**: none across lanes — file-disjoint from IC-02. Split into **WP01a** (mandatory provenance-comment normalization — 3 live formats) then **WP01b** (helper + fail-closed match + non-fakeable regression), so review can isolate the ~329-entry big diff from the algorithm.
- **Risks**: **(highest)** content-tier `module_path` recovery is the AC2 safety hinge and is source-only (the comment is not a `SymbolKey` attribute — parse via `tokenize`); it has **3 live formats** (trailing `::Name`, preceding-line, `# mod`-only). Normalization is **mandatory** (not optional), plus a test asserting every content-tier entry is parseable — else a missing comment must **refuse**, and an implementer falling back to a bare-name-only match would **silently admit** a new dead symbol (debbie's HIGH). Still-dead authority is `_compute_offenders(..., frozenset())`, not the resolver. Root fix (a non-hashing `source_module` field) is a deferred follow-on.

### IC-02 — Frozen-baseline gate restructure (toll drain, load-bearing untouched)

- **Purpose**: Stop the count/skip/inert-key gates from hard-failing on legitimate additive change, and shorten the feedback loop, without weakening any load-bearing sibling.
- **Relevant requirements**: FR-003, FR-004, FR-005, FR-006, NFR-002, NFR-003; US2, US3, US4, US5.
- **Affected surfaces**: `tests/architectural/_baselines.yaml`, `test_ratchet_baselines.py` (all three FR-003/04/05 touch it), `test_ratchet_positional_anchor_ban.py` (FR-006).
- **Sequencing/depends-on**: none across lanes; **internally sequenced** (FR-004 → FR-003 → FR-005+FR-006) because all edit the same two files — parallel worktrees would textually collide with no logical conflict (a known repo footgun).
- **Risks**: (1) NFR-003 surgical-extraction — FR-003/FR-005 edit regions near the load-bearing `legacy_contract_allowlist=151` and `_GRANDFATHERED_UNREGISTERED_KEYS`; mitigate with an explicit NFR-003 assertion. (2) FR-004/FR-003 each touch **two** loop arms (`:269`+`:405`; `:307`+`:441`) — edit both or a stale arm survives. (3) **FR-006 CI-routing** — `fast` is a routed-by-marker marker; dual-marking `fast`+`architectural` could silently drop the two gates from the `arch-adversarial` job if its `-m` selector excludes `fast`. WP04 must verify the selector before landing (not the trivial one-liner the count of edits suggests).
