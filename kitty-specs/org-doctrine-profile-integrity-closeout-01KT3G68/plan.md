# Implementation Plan: Org Doctrine Profile Integrity — Review Close-Out

**Branch**: `mission/org-doctrine-profile-integrity-activation-closure` (base = target = merge = coordination) | **Date**: 2026-06-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/org-doctrine-profile-integrity-closeout-01KT3G68/spec.md`
**Source of record**: parent mission's [adversarial-review-debrief.md](../org-doctrine-profile-integrity-activation-closure-01KT1TV1/adversarial-review-debrief.md) (findings I-1..I-12)

## Summary

Hardening close-out of the parent org-doctrine-profile-integrity mission. No new features. Remediate 12 adversarial-review findings across four classes: (1) a functional regression where `doctor doctrine` can report a pack healthy while a profile is invalid (I-1, the #1584 class) plus its consistency twin (I-9); (2) CI-gate/quality-gate correctness (I-2 unmarked tests, I-3 mypy-strict in `merge.py`); (3) architectural boundary + operator-trust hygiene (I-4 charter-facade routing + allowlist→0, I-5 stale cascade warnings, I-6 dead-symbol claim accuracy); (4) completion-proof + documentation accuracy (I-7 acceptance matrix, I-8 CLAUDE.md, I-12 pre-existing-failure tracking) plus optional debt (I-10 doctor modularity, I-11 provenance typing). Technical approach: small, surgical, ATDD-first edits to existing modules, each behavioral fix landing with a RED→GREEN test; everything commits onto the parent branch so parent + hardening merge as one change.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic v2, pytest (existing — no new dependencies introduced)
**Storage**: Filesystem only (doctrine YAML packs, `graph.yaml` DRG, `.kittify/` config, `kitty-specs/` mission artifacts); no database
**Testing**: pytest with marker-based CI profiles (`-m fast`/`-m contract`/`-m architectural`/`-m integration`); ATDD-first per charter C-011; `ruff` lint + `mypy --strict` (advisory) quality gates; architectural ratchet suites under `tests/architectural/`
**Target Platform**: Linux/macOS developer + CI (spec-kitty CLI)
**Project Type**: single (CLI library — `src/specify_cli/`, `src/charter/`, `src/doctrine/`)
**Performance Goals**: `doctor doctrine` health report must stay within its existing ≤2s NFR budget; no new hot-path cost
**Constraints**: Strict layering `kernel ← doctrine ← charter ← specify_cli` (C-006/C-008); runtime→charter→doctrine boundary allowlist capped at 2 and must trend to 0 (C-004); append-only DRG / DRG-as-source-of-truth (C-009); `__all__`/dead-symbol gate (C-007); no regression to the parent mission's 36 FRs
**Scale/Scope**: ~10-14 source/test files touched; no schema or public-API change; surgical hardening only

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **C-011 ATDD-first** — every behavioral fix (FR-001/005/008) lands with a test proven RED before, GREEN after. ✅ planned.
- **C-006/C-008 layering** — FR-006 *strengthens* the boundary (routes CLI imports through charter facades, adds `charter.template_catalog`). ✅ no violation; net-positive.
- **C-004 boundary allowlist ≤2, trend to 0** — FR-007 drives the allowlist from 2 → 0. ✅ improves the ratchet.
- **C-007 `__all__`/dead-symbol** — FR-009 makes the dead-symbol surface accurate; new facade gets `__all__`. ✅.
- **C-009 DRG source of truth** — no change to the cutover; I-1/I-9 only fix the *diagnostics* read of profile-load failures. ✅.
- **DIRECTIVE_030 test+typecheck gate** — FR-004 (markers) + FR-005 (mypy) restore gate cleanliness. ✅.
- **DIRECTIVE_037 living docs** — FR-011 syncs CLAUDE.md. ✅.
- **DIRECTIVE_013 pre-existing failures** — FR-014 files a tracker. ✅.
- No charter conflicts; no Complexity-Tracking violations. Charter present at `.kittify/charter/`.

## Project Structure

### Documentation (this feature)

```
kitty-specs/org-doctrine-profile-integrity-closeout-01KT3G68/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions for the 4 ambiguous fixes
├── data-model.md        # Phase 1 — the (small) state/contract touched (health report, inline-ref contract)
├── quickstart.md        # Phase 1 — how to verify each FR
├── contracts/           # Phase 1 — behavioral contracts for I-1 health + I-5 cascade output
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── specify_cli/
│   └── cli/commands/
│       ├── doctor.py                     # FR-001 (consumer): _collect_profile_health reports healthy:false; FR-012 (opt) extract render helpers
│       └── _doctrine_health.py           # FR-001: DoctrineHealthReport.healthy invariant (all([])==True green-on-empty mechanism, line ~112)
│       └── charter/
│           ├── activate.py               # FR-006: route ArtifactKind/MissionTypeNotAnArtifactKind via charter facade
│           └── list_cmd.py               # FR-006: route CHARTER_KIND_TOKENS/ResolutionTier/template_catalog via charter facades
├── charter/
│   ├── template_catalog.py               # FR-006: NEW thin re-export facade for doctrine.template_catalog
│   ├── pack_manager.py                   # FR-008: remove stale "cascade not yet implemented" warnings
│   └── kind_vocabulary.py / resolution.py # FR-006: existing facades reused (no change expected)
└── doctrine/
    ├── agent_profiles/
    │   ├── repository.py                 # FR-001 (PRIMARY edit): _load_layer catches InlineReferenceRejectedError -> _record_skip
    │   └── diagnostics.py                # FR-003: docstring reconciled to "surfaced skip"
    ├── drg/merge.py                      # FR-005: _tag_source generic over BaseModel; FR-013 (opt) provenance typing
    └── (events) specify_cli/next/_internal_runtime/events.py  # FR-009: drop redundant re-exports OR scope claim

tests/
├── specify_cli/test_doctor_doctrine.py          # FR-002: integration test for the raising _collect_profile_health seam
├── charter/{test_kind_vocabulary,test_operational_context}.py   # FR-004: add pytestmark
├── doctrine/{test_drg_merge,test_relationship_migration}.py     # FR-004: add pytestmark
├── specify_cli/test_operational_context_wiring.py               # FR-004: add pytestmark
├── charter/test_charter_*cli / cascade output test              # FR-008: assert no "not yet implemented" string
└── architectural/{_baselines.yaml,test_runtime_charter_doctrine_boundary,test_no_dead_symbols}.py  # FR-007/009

CLAUDE.md                                  # FR-011: new charter-activation/kind-vocabulary/specializes_from section
kitty-specs/<parent>/acceptance-matrix.json # FR-010: populate per-FR criteria + evidence
```

**Structure Decision**: Single-project CLI layout; all edits land in the existing `src/{specify_cli,charter,doctrine}` modules and their `tests/` mirrors plus two repo-root docs (`CLAUDE.md`, the parent's `acceptance-matrix.json`). No new packages beyond the one-file `charter/template_catalog.py` facade.

## Implementation Approach (by finding)

- **I-1/I-2 (merge blockers, do first):** per R1 (revised after review), fix at the **load layer** — `repository._load_layer` catches `InlineReferenceRejectedError` → `_record_skip` so valid sibling profiles still load and the skip carries `{path, id, error_summary}`; `_collect_profile_health` then reports `healthy:false`. A consumer-only catch is insufficient (loading is eager/all-or-nothing; can't keep valid profiles visible — alphonso A1 / debbie DD-1). Per the operator directive (NFR-005), `doctor doctrine` also **exits RC=1 when unhealthy** (`Exit(0 if report.healthy else 1)`) and the surfaced skip carries a readable error — a loud RC=1 is preferred over a hidden RC=0 (reverses the earlier A3 scoping). Add the integration test driving `doctor doctrine` against a `tactic_refs` org profile (RED→GREEN); it proves C1 + C2 (no fail-to-green) + valid siblings visible + exit_code==1. Add `pytestmark` to the 5 named test files, **with correct per-file markers** (P-3/P-4): `integration` for the I/O-heavy `test_operational_context_wiring.py` and the new doctor test; `fast`/`unit` for the 4 pure files (the convention gate only checks presence, not correctness).
  **Structural (survey H2/debbie):** I-1 is one mask of a fail-to-green *class* — `DoctrineHealthReport.healthy` is vacuously true on empty AND ignores `org_drg["errors"]`. WP01 also: makes `healthy` honor `bool(packs)` + `org_drg.errors`; has `_collect_profile_health` record its crash (not silently empty); defaults the renderer to degraded. The FR-002 test pins the `--json` keys + RC mapping (#645) and covers the collector-crash and org_drg-errors cases (DIRECTIVE_030).
- **I-3:** `_tag_source[T: BaseModel](obj: T) -> T`; verify `mypy --strict src/doctrine/drg/merge.py` clean.
- **I-4/I-7-boundary:** add `charter/template_catalog.py` facade; repoint the **module-level** `activate.py`/`list_cmd.py` imports to `charter.*`; empty `_BASELINE_ALLOWLIST` (boundary baseline is already 0 on upstream — WP03 does not edit `_baselines.yaml`). NOTE (renata R-2): the boundary gate counts **module-level imports only** — the surviving lazy `mission_type_repository`/`MissionTemplateRepository` imports are boundary-invisible; leave them but **annotate** them as deliberately-not-facaded (survey A4, protects the #1111 allowlist→0 win).
- **I-5:** per R3 (revised) — **delete both** stale `pack_manager` warning branches (the `if cascade:` and the `if not cascade:` blocks for activate, plus the deactivate equivalent); passing `cascade=False` does NOT work (fires the other "deferred" branch — A2/P-2/DD-3). Test asserts "not yet implemented"/"deferred" absent from activate AND deactivate `--cascade` output; **update** existing `test_activate_cascade_calls_with_true` + `test_activate_cascade_flag_accepted` (DD-4).
- **I-6 (re-scoped — survey H1, load-bearing):** make `test_no_dead_symbols` **fully green**, not just the 2 `events.py` re-exports. The parent's WP15 allowlist (~13 mission charter/doctrine symbols) was dropped in the rebase. WP04: re-add the ~13 in the `runtime.*` namespace; remove the 5 now-wired stale entries; drop the 2 `events.py` re-exports (keep imports; path is `src/runtime/next/_internal_runtime/events.py` — H3); allowlist-with-tracker the 5 upstream `status_service` symbols; update `_baselines.yaml` (WP04 owns it). WP04 depends on WP03.
- **I-7/I-8/I-12:** populate `acceptance-matrix.json` with real per-FR criteria + test IDs; add CLAUDE.md section + **ADR `2026-05-16-1` cross-link** (A5, #1040); file DIRECTIVE_013 trackers for the **4** (corrected) `git_repo` gaps + the upstream `status_service` debt + FR-012/013 deferrals. **Absorb (A7):** `ceremony`→"status commit" (FR-015, closes #1563).
- **I-9:** reconcile `diagnostics.py` docstring with `repository.py` in lockstep with I-1.
- **I-10/I-11 (optional):** extract doctor health-render helpers; type the `provenance` sidecar — each either done or tracker-filed.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
