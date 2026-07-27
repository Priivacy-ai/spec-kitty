# Research — Activation-refresh seam grounding

**Source**: architect-alphonso design-seam lens, read-only on `main` @ `7bc635aa7`, 2026-07-17.
Captured verbatim-in-substance into the mission at spec time (charter Standing Order: research is stored in the mission).

## 1. The seam today — a single write chokepoint feeding disjoint ledgers

- `charter activate`/`deactivate` (`cli/commands/charter/activate.py:303`, `deactivate.py:208`)
  → `CharterPackManager.activate/deactivate` (`charter/pack_manager.py:387,463`)
  → pure `plan_activation`/`plan_deactivation`
  → **`commit_plan` (`charter/activation_engine.py:359`)** → `_save_config`.
- `commit_plan` writes **exactly one file: `.kittify/config.yaml`** (`activation_engine.py:392`).
  Every activation write — direct, cascade (`activate.py:200`), and the `promote_activations`
  fan-in from `interview.py:111`, `doctrine/org_charter.py:425`, and the
  `m_unify_charter_activation.py:313` upgrade migration — routes through this one chokepoint.
- **Activation does NOT**: run `sync` (→ governance/directives/metadata.yaml), run
  `generate`/`compile_charter` (→ references.yaml, `compiler.py:278/424`), run
  `synthesize`/`regenerate-graph` (→ shipped + `.kittify/doctrine/graph.yaml`), or re-stamp
  the manifest `bundle_content_hash`.

### Freshness computed vs consumed
- **Computed (write-side stamp)**: `charter.bundle.compute_bundle_content_hash` (`bundle.py:133`)
  hashes **four** files — `governance/directives/references/metadata.yaml` (`bundle.py:47-52`) —
  stamped at `write_pipeline.py:685` and `resynthesize_pipeline.py:205`.
- **Consumed (read-side)**: `freshness/computer.py::_compute_synthesized_drg` (`:349`) recomputes
  the hash (`:426`) and compares vs `manifest.bundle_content_hash` (`:427-433`) → `stale` on
  mismatch/None.
- **Structural blindness**: activation mutates `config.yaml`, which is **not** among the four
  hashed files. The content-identity signal is blind to activation by construction. That is #2759.

### Gates consuming freshness (the #2157 substrate — two distinct surfaces)
- Charter preflight: `next_cmd.py:104/319` → `compute_freshness` → `_attempt_auto_refresh`
  (`preflight/runner.py:327`), which already sequences `sync → synthesize → bundle validate`.
- Implement boundary: `_require_current_analysis_report` (`agent/workflow.py:835`) — a **separate**
  analyzer-freshness gate hashing charter+spec+plan+tasks, `Exit(1)` on the first stale input
  (`:877`). Different subsystem from charter freshness (this is #2157b, fenced OUT).
- Parity guard (already built, currently unwired): `run_consistency_check`
  (`consistency_check.py:645`) with `_check_reference_id_parity` (config↔references, `:455`) and
  `_check_graph_kind_parity` (config↔graph, `:562`). **This is the epic's "consistency_check
  asserts parity" shape — already implemented.**

## 2. Design fork — recommendation

**Recommended: (c) `--resynthesize` opt-in + wire the existing `consistency_check` parity into
freshness, made whole with a fail-closed gate — explicitly NOT eager-always regen.**

| Design | Blast radius | Hot-path | Verdict |
|---|---|---|---|
| (a) regenerate-on-activate | Cannot live in `commit_plan` (pure charter, C-001 — cannot import `specify_cli`); the regen pipeline is `specify_cli`-orchestrated. Must be duplicated at every CLI + `promote_activations` call-site. | High — a routine `activate` triggers sync+generate+regenerate-graph+synthesize; the `spec-kitty upgrade` migration must not pay this. | **Reject** (layering inversion + hot-path + migration harm). |
| (b) fail-closed only | Small; activate stays fast. | Low. | **Necessary but insufficient** — needs the signal made visible first, and no ergonomic path recreates the #2157 gauntlet. |
| (c) `--resynthesize` + consistency_check parity | Small write-through + wire an already-built check. | Low. | **Recommend** — matches the epic's stated shape. |

**Concrete reconciler, four parts, sequenced:**
1. **#2758 first** — fix the signal's input-set (`references.yaml` in the hashed four but never
   written by `sync`): narrow-to-triad OR fail-closed synthesize preflight. (DIRECTIVE_043
   "close by construction".)
2. **#2759 core** — make config-activation visible: wire the existing config↔references/graph
   parity into the freshness/preflight signal so an un-derived activation reports **stale by
   construction**. Keeps activate fast; gives the fail-closed gate a true signal.
3. **#2157a** — extend the implement-boundary preflight to compute the full owed-set in one pass
   (`_attempt_auto_refresh` is the natural home).
4. **#2770** — regenerate the shipped graph + wire the charter citation + re-freeze the baseline;
   acceptance = un-pin the 4 tests.

`commit_plan` stays the single write chokepoint; the parity assertion is the by-construction guard.

## 3. Composition — one seam, distinct concern-axes

| Issue | Concern | In-seam? |
|---|---|---|
| #2759 | Config-mutation visibility (write-through / signal invalidation) | **Seam core** |
| #2758 | Freshness-signal definitional correctness (hash input-set) | **Prerequisite — do first** |
| #2770 | Doctrine-**source**-mutation regen (shipped graph + charter citation) | **Adjacent trigger** — own risk profile (fixture-entangled), concrete acceptance (4 tests) |
| #2157 | Gate aggregation UX | **Partial** — 2157a (charter-owed aggregation) IN; 2157b (analyzer-freshness coupling) is a different subsystem, OUT |

**Sequence**: #2758 → #2759 → #2157a → #2770.

## 4. #2760 — OUT

Concerns a **built-in-DRG upgrade** (`spec-kitty upgrade`) invalidating a previously-valid project
overlay via URN collision — a DRG-model *validation* concern owned by #2721 (which ships the new
built-in `NodeKind`s that create the collision). This mission is the **activation ⇒ refresh** seam;
#2760 is **upgrade ⇒ overlay-revalidation**. Concur with carla's DRG-model-lane routing: **OUT**.

## 5. Blast radius, preserve-constraints, riskiest unknowns

- **One write chokepoint** (`commit_plan`), ~6 call-sites (pack_manager activate/deactivate;
  CLI activate direct+cascade; CLI deactivate; `promote_activations` in interview/org_charter/migration).
- **Hard constraint against eager-always**: `m_unify_charter_activation.py` (upgrade migration) and
  `org_charter.py` (`required_*` union) drive `promote_activations` and must stay lightweight — no synthesis.
- **#2732 must-not-regress**: content-identity hash (`compute_bundle_content_hash`, per-file
  BOM-strip/CRLF recipe = C-005 of #2732), write-side stamps (`write_pipeline.py:685`,
  `resynthesize_pipeline.py:205`), the mtime→content-identity move (`4c5fb725c`), `built_in_only`
  read-time normalization + fresh-seed early-exit (`computer.py:367-408`). Any new invalidation
  marker must **compose with** content-identity, not replace it.
- **Acceptance signal**: un-pin the 4 `@regression` tests — `test_no_new_charter_reference_danglers`,
  `TestDRGZeroDelta::{test_regenerated_graph_matches_baseline_counts, test_shipped_graph_is_fresh_and_byte_identical}`,
  `test_check_reports_committed_graph_fresh`. Requires regenerating the shipped graph, wiring the
  charter→citation into compiled references, and re-freezing the zero-delta baseline (currently
  `289` nodes / `765` edges / `11` orphans at `test_extractor_projection.py:52-54`).

### Riskiest unknowns → spec Q1–Q4
1. `references.yaml`'s status in the content-hash (narrow-to-triad vs fail-closed-require-four). → Q1
2. Where to make config-activation visible (content-hash vs marker vs parity-in-freshness). → Q2
3. Layer placement of the reconciler given C-001. → Q3
4. #2770's home (in-mission WP vs sibling slice; fixture-entangled). → Q4
5. #2157 scope fence: 2157b OUT (recommend), only 2157a IN. → C-004

### Key files (absolute)
- `src/charter/activation_engine.py` (chokepoint `commit_plan:359`)
- `src/charter/bundle.py` (`compute_bundle_content_hash:133`, hash input-set `:47-52` — #2758)
- `src/charter/sync.py` (`_SYNC_OUTPUT_FILES:46`, triad omits references.yaml)
- `src/specify_cli/charter_runtime/freshness/computer.py` (`_compute_synthesized_drg:349` — #2759 blind spot)
- `src/specify_cli/charter_runtime/preflight/runner.py` (`_attempt_auto_refresh:327` — #2157a home)
- `src/charter/consistency_check.py` (`run_consistency_check:645` — the built-but-unwired guard)
- `src/specify_cli/cli/commands/agent/workflow.py` (`_require_current_analysis_report:835` — serial implement gate; 2157b)
- `src/charter/synthesizer/write_pipeline.py` (`promote:455`, stamp `:685`) + `resynthesize_pipeline.py` (`:205`) — #2732 write-side to preserve.
