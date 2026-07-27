# Data Model & Landmines

This mission is mostly *removal* + one *behavioral* fix, so the "data model" is the set of
code surfaces changing and the invariants/landmines that constrain them.

## Surfaces changing

| Surface | Change | Concern | Kind |
|---------|--------|---------|------|
| `src/charter/generator.py` | delete | IC-01 | dead-code |
| `src/charter/__init__.py` | remove generator import + `__all__` entries (31, 108-110) | IC-01 | dead-code |
| `tests/charter/test_generator.py` | drop generator import + 4 generator tests; KEEP 4 compiler tests | IC-01 | test-retirement |
| `src/charter/extractor.py` | delete | IC-02 | dead-code |
| `tests/architectural/_baselines.yaml` | `category_5_wp_in_flight_adapters` 1 → 0 | IC-02 | baseline-shrink |
| `tests/architectural/test_no_dead_modules.py` | remove `"charter.extractor"` allowlist entry | IC-02 | gate |
| `tests/architectural/test_no_dead_symbols.py` | remove `Extractor` SymbolKey frozenset + union term | IC-02 | gate |
| `tests/charter/test_chokepoint_coverage.py` | drop `"src/charter/extractor.py"` `_CARVE_OUTS` entry (:61) | IC-02 | gate (squad-added) |
| `tests/charter/test_extractor*.py`, `test_sync_*` (+ reconstruct 2 incidental) | retire / de-Extractor | IC-02 | test-retirement |
| `tests/charter/test_context_noop_stability.py` | add render-cleanliness guard | IC-03 | test (guard) |
| `tests/specify_cli/charter_runtime/test_preflight_noop_stability.py` | preflight no-op guard (G2/G3) + INV-2 | IC-04 | test (guard-only; NO src change) |

## Invariants (must hold at close)

- **INV-1 (no-op cleanliness, #1914/NFR-001):** any governed charter read/gate run twice on an
  unchanged, doctrine-tracked tree leaves `git status --porcelain` empty.
- **INV-2 (genuine staleness survives):** a real `charter.yaml`/pack edit STILL triggers
  synthesize — the fix suppresses no-op churn only, never legitimate regeneration.
- **INV-3 (baselines monotone down):** dead-code baselines only decrease; no green-wash upward.
- **INV-4 (coverage preserved):** the 4 `write_compiled_charter` symlink-guard tests survive;
  no live test is deleted to go green (C-003).
- **INV-5 (layer boundary, C-002):** no new `src/charter/ → specify_cli` import; the freshness
  fix stays in `specify_cli.charter_runtime`.
- **INV-6 (materialized doctrine, C-005):** `.kittify/doctrine/**` stays on disk; regeneration is
  confined to explicit write / genuine-change gating, not on-demand-only.
- **INV-7 (no #2773 regression, C-001):** charter.yaml authority, FLAT activation, `charter:`
  pointer, manifest v2, fail-loud — all untouched.

## LANDMINES (pin before any WP cuts code)

### LM-1 — The checkout masks the #2373 reproduction
A local, uncommitted `.git/info/exclude` entry (`.kittify/doctrine/`) hides doctrine churn in this
working tree; the committed `.gitignore` tracks those artifacts. **A green `git status` here is a
false negative.** IC-04's red-first repro MUST run in a doctrine-tracked checkout (fresh clone, or
temporarily remove the local exclude) or the "fix" will be static-fixed, not proven. Assert the RED
first, then the GREEN.

### LM-2 — Delete module + allowlist entries together, or the gate goes red
Deleting `charter.extractor` while leaving any of the three allowlist entries flips
`test_no_dead_modules` (stale-entry assert, `:596-598`) and `test_no_dead_symbols` (dangling assert,
`:1753-1790`) RED. The module deletion, the `_baselines.yaml` 1→0 edit, and both gate-file edits are
one atomic change within IC-02 — never split across WPs that could land separately.

### LM-3 — `test_generator.py` is NOT wholesale-deletable
It hosts the 4 surviving `write_compiled_charter` symlink-guard tests (live compiler coverage).
Remove only the line-10 generator import and the 4 generator-API tests; deleting the file drops real
coverage and violates C-003.

### LM-4 — `charter.md` scaffold is NOT a gap (confirmed, do not "restore" it)
`build_charter_draft` once built an initial `charter.md` draft. Post-#2773 there is no live
initial-`charter.md`-generation path (`charter generate` emits `charter.yaml`; `charter.md` is
hand-authored). Removing generator leaves NO gap. If a WP *thinks* it found a scaffold gap, that is a
separate concern — surface it, do not silently reintroduce a writer.

### LM-5 — Suppress no-op churn only, never genuine staleness
The freshness fix's failure mode is over-suppression: if `synthesized_drg` is forced "fresh" too
broadly, a real `charter.yaml` change stops regenerating doctrine (silent staleness — worse than the
churn). INV-2 must be tested explicitly alongside INV-1.

## Post-tasks squad amendments (2026-07-19)

A 3-lens adversarial squad (paula-patterns / reviewer-renata / debugger-debbie) reviewed the WP
decomposition against live HEAD. Three material findings, all folded in:

1. **WP02 — a FOURTH extractor gate (paula, CRITICAL).** `tests/charter/test_chokepoint_coverage.py:61`
   lists `"src/charter/extractor.py"` in a `_CARVE_OUTS` frozenset whose existence is asserted at
   `:251`. Deleting the module without dropping that line fails the carve-out gate. Added to WP02
   `owned_files` + T007 + T008 verify. LM-2 now covers **four** gate surfaces, not three.

2. **WP02 T006 — incidental fixtures must be RECONSTRUCTED, not stripped (renata, MEDIUM).** In
   `test_activate_resolves_no_answers_edit.py:213` and `test_charter_context_spdd_reasons.py:459`, the
   `Extractor().extract(...)` output feeds live `is_spdd_reasons_active` assertions. "Remove only the
   usage" → NameError or dropped coverage. T006 now says reconstruct `GovernanceConfig`/`DirectivesConfig`
   inline from `interview.selected_directives`/`compiled.selected_tactics`.

3. **WP04 — the #2373 residual is ALREADY FIXED at HEAD (debbie, high-confidence REFUTE).** The
   `synthesized_drg` signal is a content-hash of `charter.yaml` alone (#2732, `4c5fb725c`) → a no-op
   is `fresh` → synthesize never runs; and `write_pipeline.promote` has four `_substantively_equal`
   no-op guards (#1912). This checkout is `built_in_only` + doctrine-masked, so the red-first repro
   cannot reproduce. The proposed T013 signal re-homing would *cause* over-suppression (INV-2/LM-5).
   **Operator decision: collapse WP04 to a guard-only WP** (no behavioral change; preflight G2/G3 +
   INV-2/G4 guard; provenance #2773/#2732/#1912). **FR-006 reinterpreted** from "fix the misfire" to
   "verify + regression-guard the already-no-op-stable surface"; **FR-007 reinterpreted** from
   "red-first reproduce the churn" to "guards use a real-synthesized doctrine-tracked fixture."
   #2373 verdict → `verified-already-fixed` (+ regression-guarded).

Campsite notes (LOW, fold opportunistically in the owning WP): stale prose referencing
generator/extractor in `docs/plans/user_journey/init-doctrine-flow.md` (contradicts LM-4),
`test_no_dead_symbols.py:1386` docstring example, and `test_user_doctrine_artifact_lifecycle.py:375`
docstring — none gate-bearing.
