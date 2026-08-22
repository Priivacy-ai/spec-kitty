# Research: M5 — Canonical mission-type reader

**Phase 0 output.** Re-grounds the spec's Appendix census against the current
branch base (`rc3-canonical-mission-type-reader-01M0GGWM`, cut from the
accumulated rc3 state: upstream/main + M0/M1/M2/M3/M7). The spec census was
verified against `main` on 2026-08-20; several landed missions have since
shifted the ground. **Line numbers below are re-verified; every census line is
re-classified converge / already-equivalent / write-boundary / exempt.**

## Landed-mission deltas (verify-first — these SHRINK the mission)

- **M0 `backfill-mission-type` is fully wired and correct (FR-007 = verify-and-sequence).**
  `src/specify_cli/migration/backfill_mission_type.py` reads legacy `mission`
  (line 147), canonicalizes via `canonical_mission_type_key`, writes
  `mission_type` (line 170) **only** when a governance profile resolves at any
  layer, and reports `needs_manual_resolution` otherwise — it never manufactures
  an M3-breaker. CLI: `spec-kitty migrate backfill-mission-type`
  (`migrate_cmd.py:475`). **Do NOT stand up a new backfill.** `backfill-identity`
  mints `mission_id` only — confirmed it does not touch `mission_type` (AC-5 gap
  documented).
- **M3 already converged the charter read path (the load-bearing M3↔M5 reconciliation).**
  `charter/mission_type_profiles.py` now exposes `resolve_mission_type_key`
  (688) → `_resolve_type_key` (733) → `_read_meta_mission_type` (748). This path
  is **already canonical-only** (reads only `mission_type`, line 762), does the
  file I/O, then calls `canonical_mission_type_key`. M5's job here is *not* to
  change behavior but to make it delegate the field-extract+canon to M5's shared
  `read_mission_type(dict)` so the two readers cannot re-diverge.
- **`canonical_mission_type_key` is the pure, layer-legal seam (FR-004 confirmed viable).**
  `src/charter/mission_type_key.py` — pure, no I/O, no baked default, strip-only.
  `read_mission_type(meta: dict)` lands beside it. No `charter → specify_cli` edge.
- **#2901 fold is PARTIALLY LANDED.** `status/wp_metadata.py` (29 KB) already
  exists as the tolerant reader (`read_wp_frontmatter`,
  `read_authored_wp_frontmatter_lenient`). `status/bootstrap.py:51`,
  `dossier/indexer.py:64`, `sync/history_import/scan.py:46` already route through
  it. **FR-008 shrinks to the residual divergent sites only.**

## Re-grounded reader census

Legend: **CONVERGE** = route through `read_mission_type`, drop legacy + default ·
**EQUIV** = already canonical-only, route for shared-authority parity ·
**WRITE-BOUNDARY** = constructs/echoes/infers meta, not a runtime type-resolution
read; classify at its own boundary · **EXEMPT** = field-aware by design or frozen.

| # | Reader (re-verified) | Current behavior | M5 action |
|---|----------------------|------------------|-----------|
| C | `mission.py:542` `_canonical_meta_mission_type` | reads `("mission_type","mission")`, no default | **CONVERGE** — collapse to `read_mission_type` delegate; drop legacy `mission` |
| 1 | `charter/mission_type_profiles.py:748` `_read_meta_mission_type` + `_resolve_type_key:733` | **already canonical-only** (M3) | **EQUIV** — delegate field-extract+canon to shared `read_mission_type(dict)` (M3↔M5 reconciliation) |
| 2 | `dashboard/handlers/features.py:68` | `meta.get("mission","software-dev")` — legacy-only + default | **CONVERGE** — visible change (typeless/true type shown) |
| 3 | `mission_metadata.py:255` (read path) | `mission_type or mission or "" → "software-dev"` | **CONVERGE** — drop legacy + default |
| 4 | `retrospective/generator.py:1319` | `mission_type or "software-dev"` | **CONVERGE** — drop default (coordinate w/ M8: different lines, one file) |
| 6 | `context/resolver.py:94` | `mission_type or mission or "" → None` | **CONVERGE** — drop legacy read (default already neutral) |
| 8 | `verify_enhanced.py:28/31` | reads both fields, neutral | **CONVERGE** — drop legacy read |
| 9 | `dashboard/diagnostics.py:31/34` | reads both fields, neutral | **CONVERGE** — drop legacy read |
| 10 | `retrospective/reader.py:312` & `writer.py:408` | `mission_type`, default `""` | **EQUIV** — already canonical-only; route for parity |
| 5 | `charter/interview.py:225` | `data.get("mission","software-dev")` on **interview payload** (`self.mission`, line 209) | **WRITE-BOUNDARY / EXEMPT** — reads the interview form field, not `meta.json`'s `mission_type`; not a runtime meta reader. Confirm & exempt-with-rationale |
| 7 | `cli/commands/agent/mission_create.py:374` | `meta.get("mission_type", meta.get("mission",""))` echo into result | **WRITE-BOUNDARY** — echoes at create-time; converge the field set to canonical-only, drop legacy echo |
| 11 | `upgrade/feature_meta.py:95` `infer_mission` | reads `mission_type` only; returns `"software-dev"` default (line 101) on `_set_if_blank` WRITE | **WRITE-BOUNDARY** — inference-on-upgrade backfill; evaluate default vs. neutral (writer, not reader) |
| — | `mission_metadata.py:216` (build path) | `str(mission_type or "").strip() or "software-dev"` at create | **WRITE-BOUNDARY** — create-time default, not a meta read |
| 12 | `cli/commands/_mission_type_audit.py` | reads both fields **by design** (classifies legacy-only as its own bucket) | **EXEMPT** — the census/audit tool; must stay field-aware. Encoded allow-list w/ rationale |

## FR-009 — frozen migrations + charter-layer inline reads (#2477–#2480)

| Site | Reads | Disposition |
|------|-------|-------------|
| `m_0_13_0_research_csv_schema_check.py:57/114` | `meta.get("mission") != "research"` | **EXEMPT** — reads legacy field *by design* (operates on pre-migration historical state); converging to canonical-only would break its replay. Encoded allow-list, cites #2477 |
| `m_0_13_5_add_commit_workflow_to_templates.py:74` | `meta.get("mission_name","software-dev")` on **project** `.kittify/meta.json` | **EXEMPT** — different field (`mission_name`), different file; not a mission-type reader |
| `m_0_13_8_target_branch.py` | reads meta for `target_branch` | **OUT OF SCOPE** — no mission-type read |
| `migration/mission_state.py:1617` | `meta["mission_type"] = mission_type or mission or "software-dev"` WRITE | **WRITE / evaluate** — a legacy→canonical backfill *write* with default; frozen migration step. Exempt-or-align; M0 command is the operator-facing backfill |

**Conclusion:** FR-009 lands predominantly as **encoded `inline_meta_read_allowlist.yaml` exemptions with rationale** (historical/different-field), NOT byte-for-byte conversions — matching AC-6's "OR carry an exemption." No silent path-exclude.

## FR-008 — #2901 residual divergent sites (verify-first)

| Site | Current | Disposition |
|------|---------|-------------|
| `status/wp_metadata.py` | tolerant reader (LANDED) | **the target** |
| `status/bootstrap.py`, `dossier/indexer.py`, `sync/history_import/scan.py` | already route through it | **DONE** — pin with parity assertion |
| `audit/classifiers/wp_files.py:58` | raw `FrontmatterManager().read()` | **ROUTE** through tolerant reader (coordinate w/ M6: `_TERMINAL_LANES:16` is a different symbol, one file) |
| `mission_v1/guards.py` | own `_read_lane_from_frontmatter` | **EVALUATE** — route if it duplicates the tolerant classification; else exempt |
| `review/prompt_metadata.py` | `read_frontmatter` on **review-prompt** frontmatter | **OUT OF SCOPE** — reads review prompts, not WP frontmatter |

## Same-file cross-mission coordination (assign per-symbol at tasks time)

- `audit/classifiers/wp_files.py` — **M5 (#2901 fold)** routes the WP-frontmatter reader; **M6** retires `_TERMINAL_LANES` (`:16`). Different symbols.
- `retrospective/generator.py` — **M5** touches the mission-type reader (`:1319`); **M8** migrates a read-side degrade site (`:271`). Different lines.

## Net effect of re-grounding

The mission is **smaller than the spec's census implies**: the charter path (#1)
and retrospective reader/writer (#10) are already canonical-only; #2901's reader
and three of its consumers already landed; FR-007's backfill is built and correct;
FR-009 is mostly exemptions, not conversions. The load-bearing new work is: the
shared `read_mission_type` seam + M3 delegation, the ~8 legacy/default-dropping
read converters (dashboard is the one visible change), the FR-010 structural
gate, routing `audit/classifiers/wp_files.py`, the exemption allow-list, and the
ADR + per-surface changelog.
