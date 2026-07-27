# Implementation Plan: Relocation-Hardened Dead-Code Scanners

**Branch**: `analysis/test-change-coupling` | **Date**: 2026-07-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/relocation-hardened-dead-code-scanners-01KX958P/spec.md`
**Mission**: `relocation-hardened-dead-code-scanners-01KX958P` (#2546, under #2071; coordinates #2293)

## Summary

Re-key the 394-entry `module::Name` dead-symbol allow-list in
`tests/architectural/test_no_dead_symbols.py` onto a **relocation-tolerant symbol
identity** — content-only `(bare_name, body_hash)` by default, escalating to a
`module_path` tier (or fail-closed) **only for `bare_name`s whose content resolves to
≥2 live locations, recomputed live at gate time** — so a behaviour-preserving symbol
relocation no longer forces a hand-edit, **without re-blinding the T004
no-false-negative invariant** and preserving the gate's full bite. Additionally,
census + root-remediate the ~40 arch/integration-suite warnings (mostly intentional
`warnings.warn(UserWarning)` report-only diagnostics). The design is pre-hardened by
the WP06 spike + two post-spec adversarial squads (bite/T004 + encoding/over-promise);
their defects are already folded into the spec.

## Technical Context

**Language/Version**: Python 3.11+ (test infrastructure; 3.11↔3.12 body-hash parity required)
**Primary Dependencies**: `pytest`, `ast` (stdlib), `src/specify_cli/contracts/anchoring.py` (`code_tokens_by_line` — interpreter-independent body-hash; `enclosing_qualname`), the merged WS1 substrate `tests/architectural/_ratchet_keys.py`
**Storage**: N/A (frozensets + AST scans over the repo `src/` tree)
**Testing**: pytest; the gate itself IS a test — the (a–k) bite battery drives assertions through the **production `_compute_offenders`/stale path** (C-007), plus focused unit tests for the new key module
**Target Platform**: Linux/macOS CI + local dev
**Project Type**: single (Python CLI + its architectural test suite)
**Performance Goals**: the live collision classifier (FR-005) must not materially slow `test_no_dead_symbols.py` — one `(bare_name → [locations])` index built once per run, not per-entry rescans
**Constraints**: full `tests/architectural/` finishes **0 failed** (baseline **887** on this branch); the 4 T004 detector tests + `known_modules`/`_record_*_edges`/`_imports_by_target` stay **byte-unchanged** (C-005); the merged meta-guard `test_ratchet_positional_anchor_ban.py` stays green (new key is all-strings, no int-line anchor); do NOT edit the approved+merged WP06 spike files
**Scale/Scope**: 394 allow-list entries across 19 category frozensets; known forfeit floor ~100+ (68 named re-export/shim + 8 facade-dict + 33 multi-target `ImportFrom`); 214-entry `GRANDFATHERED_LEGACY` swing bucket; ~40 suite warnings across ~6 test files + 1 src schema-skip

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* (charter context mode: **compact**)

- **Single canonical authority** — the relocation key is ONE new module (`_symbol_key.py`); the gate consumes it. No parallel key definitions. ✅
- **Architectural alignment / DDD-tiered rigour** — this is test-infra (glue tier), but the key is safety-critical (re-blinding = false-negative on dead code), so it carries core-tier rigour: exhaustive bite battery, fail-closed defaults, no silent fallback. ✅
- **ATDD-first** — every FR has an acceptance path in the (a–k) bite battery / NFR thresholds; the battery is authored red-first through the production path. ✅
- **Terminology adherence** — "Mission" canon; no `feature*` aliases introduced. ✅
- **Canonical sources** — reuse `anchoring.code_tokens_by_line` (do NOT fork a second body-hash normalizer); reuse the gate's caller-side facade machinery for the FR-003 KEY-side resolver. ✅
- **No legacy resolver fallback** ([[no_legacy_resolver_paths]]) — the key fail-closes on undecidable identity; NO `if key is None: <silent-exempt>` branch. ✅

No charter violations. Complexity Tracking not required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/relocation-hardened-dead-code-scanners-01KX958P/
├── plan.md              # This file
├── research.md          # Phase 0 output — 8 design decisions
├── data-model.md        # Phase 1 output — SymbolKey / AllowlistEntry / CollisionSet / DanglingEntry / AutoExemptCategory
├── quickstart.md        # Phase 1 output — how to run the bite battery + motion battery + warnings census
├── contracts/
│   ├── symbol-key-resolver.md      # the key + live collision classifier contract
│   └── warning-remediation.md      # the census + root-remediation-vs-followup contract
├── tracers/
│   ├── relocation-key.md
│   ├── live-collision-classifier.md
│   └── warning-remediation.md
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/contracts/anchoring.py      # SUBSTRATE (reused, not owned): code_tokens_by_line, enclosing_qualname
src/doctrine/base.py                          # src schema-skip warning source (IC-WARNINGS: fix-or-file)
tests/architectural/
├── _symbol_key.py                            # NEW — the relocation key + live collision classifier (IC-KEY)
├── test_no_dead_symbols.py                   # RE-KEYED (IC-REKEY, single-owner) — 394-entry allow-list + categories + ratchet
├── test_no_dead_modules.py                   # relocation-harden-or-preserve (IC-MODULES)
├── test_ratchet_positional_anchor_ban.py     # PRESERVE green (merged meta-guard) — not owned
├── _symbol_identity.py                       # WP06 spike — DO NOT EDIT (corpus reference)
├── test_migration_chain_integrity.py         # IC-WARNINGS: ~13 patch-skip report-only warnings
├── test_gate_coverage.py                     # IC-WARNINGS: duplicate-selection report-only warning
└── _baselines.yaml                           # NOT owned by any WS2 WP — count deltas routed via note (C-004)
tests/unit/
├── test_symbol_key.py                        # NEW — focused unit tests for _symbol_key.py (IC-KEY)
└── test_symbol_identity_spike.py             # WP06 spike test — DO NOT EDIT
tests/contract/test_example_round_trip.py     # IC-WARNINGS: ~13 legacy-contract-backfill warnings (tracked follow-up candidate)
```

**Structure Decision**: single-project Python test-infra. The relocation key is a new
`_`-prefixed, non-collected, **non-`src/`** module (a `src/` module imported only by
tests would red `test_no_dead_modules`). `test_no_dead_symbols.py` is single-owned.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-KEY — Relocation-tolerant symbol key + live collision classifier

- **Purpose**: The keystone — a NEW `tests/architectural/_symbol_key.py` producing a relocation-tolerant `SymbolKey`: content-only `(bare_name, body_hash)` default, `(bare_name, module_path, body_hash)` for the collision tier, `None` for undecidable. Body-hash reuses `anchoring.code_tokens_by_line`.
- **Relevant requirements**: FR-001, FR-002 (AnnAssign — HIGHEST, spike has no AnnAssign branch), FR-003 (facade-dict KEY-side resolver — **see the refuted-reuse note below**), FR-004 (single-alias `ImportFrom` hash scoping), FR-005 (**live gate-time collision classifier** — build a `(bare_name → [live locations])` index once/run; ≥2 → escalate/fail-close; the content/forfeit split is runtime-recomputed), FR-009 (fail-closed for `None`-key AND ≥2-resolution).
- **Affected surfaces**: `tests/architectural/_symbol_key.py` (new), `tests/unit/test_symbol_key.py` (new). May lift the spike's proven `ClassDef`/`FunctionDef` logic; **adds its own AnnAssign + single-alias stability proofs** (the spike proved neither).
- **Sequencing/depends-on**: none (keystone). Every symbol-side concern consumes it.
- **FR-003 refuted-reuse (post-plan code-feasibility squad — REQUIRED rescope)**: the gate has **two** facade dict shapes — `sync/__init__.py _LAZY_IMPORTS` `{name:(module,attr)}` (2-tuple) and `runtime/__init__.py _EXPORT_MODULES` `{name:module_const}` (1-value). `_record_facade_edges` (L1143) handles ONLY the 2-tuple (its guard L1183 `len!=2: continue` **skips every runtime entry** — the **6** `specify_cli.runtime::*` entries: `AssetDisposition`/`MigrationReport`/`OriginEntry`/`ResolutionResult`/`ResolutionTier`/`classify_asset`), is **byte-frozen** (C-005 `_record_*_edges`), and is caller-graph-shaped (mutates `per_symbol`, discards the name). So the KEY side **re-derives** the dict-parse (including the `{name:module_const}` shape) and reuses ONLY the two **pure** helpers `_find_facade_lazy_dict_name` (L1103) + `_resolve_relative_module` (L1126). Enumerate facades **by shape** (sync 2-tuple + runtime 1-value), not "all 8" (src has 12 `__getattr__` modules but only 2 named-dict facades). This resolves the C-005↔FR-003 tension: reimplement-not-edit keeps C-005 intact.
- **Ownership pin (LOW-5)**: `_find_facade_lazy_dict_name` + `_resolve_relative_module` live in `test_no_dead_symbols.py` (IC-REKEY's file) and are **NOT** in the C-005 byte-frozen set — IC-KEY imports them across the test tree, so WP-REKEY-A/B MUST NOT mutate their signatures. Pin them (or, if a signature must change, hoist all three facade helpers into a shared `_`-module). Name this coupling in the WP prompts.
- **Perf (code-feasibility Claim 4)**: no new AST walk (reuses `_walk_modules`' cached trees), BUT a **net-new tokenize pass** — the current gate makes ZERO `tokenize` calls; `code_tokens_by_line(source)` re-tokenizes every `__all__` symbol in the corpus once/run. Bounded/linear; add a perf-budget assertion to the gate self-test so a regression is visible.
- **Risks**: S3776 — isolate the body-hash normalizer + each definition-shape resolver into small helpers (reuse `code_tokens_by_line`, do not fork). Build the collision index once, not per-entry. AnnAssign span is the re-introduced T001 bug — highest-priority correctness (real entries are all annotated-with-value → hashable; true AnnAssign count is likely **≤14** — several apparent constants are plain `Assign` already handled).

### IC-REKEY — Re-key the 394-entry allow-list + symbol-granular categories (single-owner, **TWO sequential same-owner WPs**)

- **Purpose**: Re-key all 394 entries off `module::Name` onto the IC-KEY `SymbolKey`; thread `source`/AST into `_compute_offenders`; drop the 2 stale entries; auto-derive symbol-granular exempt categories; add the third ratchet direction; run the bite battery through the production path.
- **SIZING (post-plan squad HIGH-1): this concern is ~15 subtasks — too large for one WP.** `/tasks` MUST split it into **two SEQUENTIAL, dependency-chained, same-owner WPs** of `test_no_dead_symbols.py`. C-003 forbids *concurrent* owners, NOT a sequential chain — WP-B depends on WP-A, so they never run at the same time and single-ownership holds.
  - **WP-REKEY-A (re-key + bite/T004 preservation)** — FR-007 (re-key 394) + FR-006 (drop 2 stale) + the `_compute_offenders` signature change + **FR-005 live-collision classifier consumption + FR-009 ≥2-escalation/fail-close** (MUST be here — without it the re-key re-blinds T004 on the ArtifactKind trio) + FR-010 (symbol-granular categories + disjointness meta-test) + DoD **(a,c,e,f,h,i,k)** + full-suite 0-failed. Also updates the human-maintained `_baselines.yaml` doc count `test_no_dead_symbols.category_b_grandfathered_legacy` 215→213 (hygiene only — **not machine-enforced by `test_ratchet_baselines`**, which maps only `test_no_dead_modules` CATEGORY_1..7 + fixed single-ratchets; verified — so this is a doc edit, NOT a C-004 exception, and trips NO shrink-warn). Depends: IC-KEY.
  - **WP-REKEY-B (new ratchet directions)** — FR-008 (tier-specific dangling ratchet: module_path-tier `(bare_name, module_path)`→0 decls; content-tier `(bare_name, body_hash)`→0 locations) + body-sensitivity one-signal reconciliation + DoD **(b,d,g)** + the gate-side (j) 0-false-red proof through the production path. Depends: WP-REKEY-A.
- **Relevant requirements**: FR-006, FR-007, FR-008, FR-010, FR-013 + DoD (a)-(k) via `_compute_offenders`/stale.
- **Affected surfaces**: `tests/architectural/test_no_dead_symbols.py` (**single-owned across BOTH WPs**, C-003) + the human-maintained `_baselines.yaml` symbol doc-count (WP-REKEY-A, hygiene).
- **Sequencing/depends-on**: IC-KEY → WP-REKEY-A → WP-REKEY-B.
- **Implementation notes (post-plan code-feasibility squad)**: `_compute_offenders` current signature `(decls, per_symbol, star_targets, allowlist)` at L1327; **all 4 call sites are in this file** (L1368 prod + L1568/1575/1581 teeth test) — the signature change is genuinely contained. The caller `test_no_public_symbol_in_all_is_unimported` already holds `path_to_tree`/`path_to_dotted` from `_walk_modules` (L1364, 1201-1227); extend `_walk_modules` (NOT C-005-frozen) to ALSO retain **source text** (needed — `code_tokens_by_line(source)` needs the source string, currently only the tree is kept) and invert the map to dotted→(tree, source). Category auto-derivation must be symbol-granular. Keep the bite battery on the production path (C-007).
- **DoD (j) split (post-plan squad MED-3)**: the **key-invariance** probe (body_hash stable under AnnAssign whitespace / single-alias / 3.11↔3.12) is a legitimate IC-KEY **unit** test (`tests/unit/test_symbol_key.py`); the **gate-level 0-false-red** DoD (j) folds into **WP-REKEY-B** through the production path (C-007 binds every (a-k) item to the gate path — a unit-only (j) is the self-validation loophole C-007 forbids). Two tests, not either/or.

### IC-MODULES — Relocation-harden-or-preserve `test_no_dead_modules.py`

- **Purpose**: Relocation-harden `test_no_dead_modules.py` IF it carries a relocatable anchor; ELSE downgrade to explicit-preserve (byte-unchanged) and say so — no unmeasured scope-add.
- **Relevant requirements**: FR-011 (measurable: relocate a sanctioned dead module's anchor → green + genuinely-dead-at-new-path caught; OR downgrade-to-preserve), FR-012 (preserve cross-module `__all__` deadness + 4 detectors + test-not-caller + bidirectional ratchet byte-unchanged).
- **Affected surfaces**: `tests/architectural/test_no_dead_modules.py`.
- **Sequencing/depends-on**: none for the code (independent of the symbol key) — can parallel IC-KEY. First subtask = determine whether a relocatable anchor exists.
- **Risks**: over-scoping — if there's no relocatable anchor, resist inventing one; downgrade cleanly.

### IC-WARNINGS — Census + root-remediate the ~40 suite warnings

- **Purpose**: Eliminate the ~40 first-party warnings by remediating each at root, NOT blanket-suppressing. **Census result (done):** they are almost all intentional `warnings.warn(UserWarning)` report-only diagnostics: ~13 migration-chain patch-skips (`test_migration_chain_integrity.py`), duplicate-CI-gate-selection (`test_gate_coverage.py`), ~13 legacy-contract-backfill (`tests/contract/test_example_round_trip.py`), template-governance/charter-references/wp-prompt-latency; PLUS 1 genuine **src schema-skip** (`src/doctrine/base.py:108` skips an invalid `terminology-guard.toolguide.yaml` — pydantic `extra_forbidden` on `references`).
- **Relevant requirements**: FR-016, NFR-006 (0 first-party warnings from `tests/architectural` — **arch-scoped**), SC-005.
- **Affected surfaces (ENUMERATED — pinned per post-plan squad, drop open-ended "+ any other")**: `tests/architectural/test_migration_chain_integrity.py`, `tests/architectural/test_gate_coverage.py`, and the other arch emitters the census named (`test_template_governance_payload_contract.py`, `test_charter_references_resolve.py`, `test_wp_prompt_build_latency.py`) — **in-mission, owned**. **`src/doctrine/base.py` + the invalid `terminology-guard.toolguide.yaml` → IN-MISSION, owned** (post-plan squad MED-4: the census confirms `base.py:108` fires DURING `tests/architectural` collection, so a mere follow-up leaves NFR-006 unmet; it is disjoint — no other IC touches `src/doctrine/base.py`). `tests/contract/test_example_round_trip.py` (~13 legacy-backfill) is **OUT of `tests/architectural` scope → tracked follow-up** in `issue-matrix.md` (does not affect the arch-scoped NFR-006), named, never suppressed. **Caveat**: if the census finds a warning emitter *inside* an IC-KEY/IC-REKEY/IC-MODULES file, its fix folds into that file's owner (not IC-WARNINGS) to keep ownership disjoint.
- **Sequencing/depends-on**: none — ZERO dependency on the key work; can land FIRST/parallel. NFR-006 verifies as a **whole-suite property at merge time**, not per-lane.
- **Risks**: scope creep into `tests/contract/`. The policy decision (route report-only diagnostics off the `warnings` channel via `record_property`/logging, vs register expected-warnings with rationale) is a research item — decided in research.md (D-8) before touching files. Do NOT weaken a real diagnostic (the migration patch-skip / duplicate-gate signals are load-bearing — preserve the signal, change only the channel). The `base.py` fix is a genuine schema/data fix (the toolguide YAML's `references` field trips pydantic `extra_forbidden`) — fix the YAML/schema, don't suppress.

## Sequencing & Ownership (disjoint — C-002/003/004/005) — ~6 WP forecast

```
IC-KEY (keystone, new file) ──> WP-REKEY-A (single-owner test_no_dead_symbols.py) ──> WP-REKEY-B (SAME owner, sequential)
                                                                                       (C-003: sequential chain, never concurrent)
IC-MODULES (independent) ───────────────────────────────  (parallel)
IC-WARNINGS (independent) ──────────────────────────────  (parallel, land first)
```

- `tests/architectural/_symbol_key.py` + `tests/unit/test_symbol_key.py` — IC-KEY only (new, non-`src/`; hosts the key-invariance (j) unit probe).
- `tests/architectural/test_no_dead_symbols.py` — WP-REKEY-A **then** WP-REKEY-B (single-owner, sequential chain — never two concurrent owners; C-003 honored). WP-REKEY-A also edits the human-maintained `_baselines.yaml` symbol doc-count (215→213, hygiene, non-enforced).
- `tests/architectural/test_no_dead_modules.py` — IC-MODULES only.
- IC-WARNINGS owns the ENUMERATED arch emitters (`test_migration_chain_integrity.py`, `test_gate_coverage.py`, `test_template_governance_payload_contract.py`, `test_charter_references_resolve.py`, `test_wp_prompt_build_latency.py`) **+ `src/doctrine/base.py` + the invalid toolguide YAML** (in-mission, disjoint); `tests/contract/test_example_round_trip.py` → tracked follow-up.
- `_baselines.yaml` — the `test_no_dead_modules` machine-enforced counts stay unowned (C-004); ONLY the human-maintained `test_no_dead_symbols` doc-count is edited (WP-REKEY-A). `test_ratchet_baselines` does NOT enforce the symbol counts (verified L200-329) — no shrink-warn on the 2-stale drop. Coordinate #2293.
- `_find_facade_lazy_dict_name` / `_resolve_relative_module` — imported by IC-KEY, live in IC-REKEY's file, NOT C-005-frozen → WP-REKEY-A/B must not mutate their signatures (LOW-5 pin).
- `known_modules`/`_record_*_edges`/`_imports_by_target` — BYTE-UNCHANGED (C-005). `_walk_modules` is NOT frozen — extend it to retain source.
- WP06 spike files — DO NOT EDIT.

## Definition of Done (per gate)

The (a–k) bite battery through the production `_compute_offenders`/stale path + the
motion battery (NFR-001: module move + sibling reorder + blank/comment + **AnnAssign
annotation-whitespace** + **single-alias `ImportFrom`** + 3.11↔3.12) + full
`tests/architectural/` **0 failed** (baseline 887) + meta-guard green + 4 T004 tests
byte-unchanged + **0 first-party warnings** (NFR-006). Complexity is not the gate —
the batteries are.
