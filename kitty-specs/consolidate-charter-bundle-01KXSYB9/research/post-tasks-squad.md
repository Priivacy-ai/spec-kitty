# Post-tasks adversarial squad (2026-07-18) — findings + resolutions

3 profile-loaded read-only lenses on the WP decomposition. Verdicts: paula SOUND-WITH-FIXES, renata READY-WITH-FIXES, carla campsite-mapped. The slice geometry (one-concern-per-WP, non-overlapping literals, tidy-first DAG) held; fixes were additive `owned_files` + reassignments + line-refs. All applied (finalize commit `8814fe87`).

## Resolved findings

| # | Lens | Finding | Resolution |
|---|------|---------|-----------|
| paula BLOCKER-1 | anti-laziness | **Two unowned activation WRITERS** — `interview.py:97,111 _append_promote_selections` + `org_charter.py:421-429 _promote_org_required_to_config` write activation into config.yaml; post-relocation they'd write to a surface nothing reads (silent split-brain; parity guard blind) | Added both to **WP02** owned_files + T008 re-point to charter.yaml via shared helper |
| renata B1 / paula MAJOR-2 | claims/anti-laziness | **#2758 removal mis-scoped** — `first_missing_bundle_file` is in `bundle.py:187` (not computer.py); caller `_charter_bundle_preflight` in `_synthesis.py:519` unowned; tests in `test_references_missing_failclosed.py` (WP04) | KEEP `first_missing_bundle_file` (auto-narrows to a charter.yaml existence check = the desired fail-loud guard) → WP01 owns disposition; `_synthesis.py` → WP03 (re-message the guard); #2758 test assertion → WP04 (`"references.yaml"`→`"charter.yaml"`); WP06 T026 corrected to #2759-only |
| renata M1 / carla OUT | claims/campsite | **Orphaned by extractor retirement** — `src/charter/__init__.py` (re-exports `post_save_hook`), `tests/charter/test_extractor.py` (~20 scraper tests), `tests/charter/test_integration.py` (post_save_hook ref) unowned → ImportError/red at aggregate | Added all three to **WP04** owned_files + T017/T020 (fix `__init__`/`extractor.py:38 __all__`; retire spent scraper tests) |
| paula MAJOR-3 | anti-laziness | **versioning symbol drift** — real symbol is `get_bundle_schema_version:165` (not `read_bundle_schema_version:166`); rc35 migrations use it as a `detect()` gate | WP07 T030 corrected + re-verify-rc35-detect note |
| paula MINOR-5 | anti-laziness | **WP08 tier-1 also breaks** — `_read_compiled_languages:44` reads references.yaml (deleted by WP07) | WP08 T032/T033 explicit: repoint BOTH tier-1 (:44) + tier-3 (:101-103) to `charter.yaml.catalog.languages` |
| renata m1 / paula MINOR-4,6 | claims | **Line-ref drift** — consistency_check `_load_reference_ids_by_kind:406`(not:420)/config-read:200; spdd `clear_activation_cache:49`(not:10),`_GOVERNANCE:41`,`_compute_active:92`; mission_type_profiles `_project_has_doctrine_overrides:954`(caller:479); language_scope `_read_compiled_languages:44`; computer `_compute_synced_bundle:324`; #2759 `_activation_parity_drift_reason:499` | Corrected across WP04/WP06/WP07/WP08 |
| renata m2 | claims | charter_hash-retired landmine had a reviewer check but no test | WP06 T027 adds a `charter.yaml.metadata has no charter_hash` assertion |
| carla campsite | sonar/campsite | `generate.py:205 generate()`=cx15 (WP03 edit region) + `context.py:971 _render_bootstrap_text`=cx15 (WP05 edit region) — at the C901/S3776 ceiling | Campsite notes added to WP03/WP05 (extract a helper if adding a branch); "consume the shared `CHARTER_YAML` const, do not re-scatter" reinforced across WPs |

## Confirmed correct (held up under audit)
- owned_files literal non-overlap PASS (finalizer + semantic verify); `resolver.py:310`/`_status_collectors.py:122` correctly UNowned (auto-follow signature-stable loaders); no hidden WP04↔WP05 context.py write overlap.
- consistency_check dual-read real (activation :200 + catalog :406) — WP04 T018 re-points BOTH.
- DAG acyclic, no deadlock; WP04 gated on WP02+WP03; WP07 last.
- ATDD entry points all real callable seams. FR→WP coverage complete + correct. Landmine test obligations present. Both tidy-first hazards (WP02↔WP04 transient-parity; WP04 loaders-before-scrape) documented + reviewable. spec-kitty-own-charter.yaml regen dependency wired.
- `extract_with_ai` genuinely dead (zero product callers) — retire confirmed safe.
- Sonar MCP unreachable (wrong org for `Priivacy-ai_spec-kitty`) → carla census is ruff C901 + grep; all owned files pass C901 ≤15 (two functions AT 15, flagged).

## Net
9 WPs / 9 lanes; DAG WP01→{WP02,WP03,WP06}→{WP04,WP08}→{WP05,WP07,WP09}. Split-brain gaps closed; decomposition READY for the implement-review loop.
