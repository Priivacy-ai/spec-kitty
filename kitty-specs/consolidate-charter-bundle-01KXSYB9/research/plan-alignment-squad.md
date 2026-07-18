# Plan/spec alignment squad (2026-07-18) — findings + resolutions

Run after the activation-ownership + config-pointer + tier refinements. 3 profile-loaded read-only lenses. Verdicts: renata ALIGNED-WITH-FIXES, alphonso SOUND-WITH-MITIGATIONS, paula GROUNDED-WITH-GAPS. All findings below are RESOLVED in the artifacts (this commit).

## Resolved findings

| # | Lens | Finding | Resolution |
|---|------|---------|-----------|
| paula BLOCKER-1 | code-state | activation in `default.yaml` is **FLAT at root**, not a nested `activation:` section; my schema framed it nested → would break `_read_activated_*` + `commit_plan` + overlay | data-model + charter-yaml-schema: activation = FLAT root keys; `CharterYaml` nests only governance/directives |
| paula MAJOR-4 | code-state | tier **superset/accumulation** claim (INV-8/AR6) FALSIFIED as "existing pack_roots" — `pack_roots` overlays artifact *definitions*, not activation tiers; activation is a single flat set | data-model INV-8 (subset REAL) + INV-8b (accumulation FORWARD-INTENT, C-008); contract AR6 + tier-section marked target-not-current; research Decision 8; ADR point 1 |
| renata M2 / alphonso MAJOR-1 | align/soundness | manifest put `charter.yaml` in both tracked+derived while claiming `_validate` (which forbids that) passes | distinct **`content_hash_files`** field = `[charter.yaml]`; `derived_files=[]`; `_validate` untouched (data-model LM1, manifest-v2 M1/M2, IC-02) |
| alphonso MAJOR-2 | soundness | **#2772 clobber reborn inside charter.yaml** — full-file overwrite writer would destroy authored governance/activation on recompile | NEW **Landmine 3**: partial/merge writes (refresh only derived catalog+metadata; preserve authored byte-for-byte); regression test; IC-03 |
| alphonso MAJOR-3 | soundness | three writers (commit_plan/merge_defaults/compiler) mutate one tracked file; section-preservation only conventional | NEW **INV-9**: single shared `load→mutate-owned-section→round-trip-save` helper owned by IC-02; round-trip tests |
| paula MAJOR-1 | code-state | `activation_engine.py:359 commit_plan` (the real write primitive) owned by NO IC | added to IC-01 affected surfaces + source layout (diagnostics re-word; data-source-agnostic so flat-root needs no functional change) |
| paula MAJOR-2 | code-state | `consistency_check._load_raw_activation_lists:199` reads config activation DIRECTLY; IC-04 named only the catalog | IC-04 now re-points BOTH :199 (activation) and :420 (catalog) |
| paula MAJOR-3 | code-state | 3 existing migrations write activation INTO config (`m_unify_charter_activation`, rc35 pair); unreferenced; `m_unify` encodes the now-reversed "config is authority" | IC-07 + migration-contract MG6: fold sequences strictly AFTER the seed migrations, reconcile/annotate `m_unify`, idempotent vs re-seeding |
| alphonso MINOR-3 | soundness | spurious authoring-staleness — authored-only edit trips whole-file hash though catalog unchanged | Landmine 2 extension: IC-06 decides catalog↔activation parity vs documented-stale, with test |
| alphonso MINOR-1 / paula MINOR-1 | both | `from_config` is a two-file read (org_packs stay in config); `_load_config` absent→{} must not swallow a dangling pointer | data-model config entity + charter-yaml-schema G7 + IC-01 note (distinguish missing-charter=raise from no-config=default) |
| paula MINOR-2 | code-state | fold must copy activation lists VERBATIM (absent stays absent, never →`[]`) | migration-contract MG1 + test obligation |
| alphonso MINOR-2 | soundness | multi-tier freshness gap (hash of repo-tier file misses higher-tier drift) | noted for the C-008 fenced follow-up (INV-8b / contract) |
| renata m3 | align | FR-015 orphaned from ICM; "~14 FRs" undercount | FR-015 added to IC-01 requirements; count → 15 |
| renata m4 | align | SC-004 typo `#2767`→`#2759` | fixed |
| renata M1 | align | ADR said FR-009 (language tier-3) is a follow-up; spec/plan fold it IN | ADR Neutral note updated: FR-009/IC-08 folded |
| renata m5 | align | research Decision 8/9 out of order | reordered + added Decision 10 |

## Passed clean (no defect)
FR↔IC coverage (all FR mapped, no FR-less IC); SC↔gate coverage; schema consistency across data-model/contracts/diagram; Landmine-2 consistency; config-pointer consistency; C-008 fence consistency; NFR-005/C-006 DAG ordering; no stale "config is authority"/"charter.md authored"/"#2772 OUT" residue; the C-008 seam is clean (runtime consumes PackContext attributes, not config directly).
