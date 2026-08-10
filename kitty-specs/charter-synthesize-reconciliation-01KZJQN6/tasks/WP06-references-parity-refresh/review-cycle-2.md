---
affected_files: []
cycle_number: 2
mission_slug: charter-synthesize-reconciliation-01KZJQN6
reproduction_command:
reviewed_at: '2026-08-10T07:59:28Z'
reviewer_agent: claude
wp_id: WP06
---

Approved by claude: APPROVE (cycle 2). MAJOR-1 resolved: runner._attempt_auto_refresh (runner.py:492-517) now re-runs flagless synthesize after generate fires (references_refreshed==True) to re-stamp bundle_content_hash before freshness recompute; refresh_references_if_needed returns bool (references_refresh.py:158). MAJOR-3 resolved: test_boundary_heal.py::test_references_parity_heal_recompiles_with_real_generate_and_stays_manifest_coherent drives run_charter_preflight(auto_refresh=True) with REAL in-process generate (_invoke_generate_in_process, not stubbed), asserts passed=True/synthesized_drg=fresh/non-empty catalog/charter.md 0-byte/second run not re-blocked. MAJOR-2 (#3292) genuinely fixed in 5083f548e: compile_charter routes through single authority infer_repo_languages(repo_root, interview=...) (compiler.py:384); empty->None not [] (schemas.py CharterCatalog.languages nullable; language_scope.py tier-2 returns declared only if non-empty) breaks the admit-none feedback loop; tier-1 test_language_scope pinned test unchanged+passing; doctrine_service_builder change docstring-only (no DoctrineService internals reach, FR-010 intact); idempotency proven by 2-run+3-run RED-first tests. Gates: 95 passed scoped pytest, ruff clean, mypy clean (no new issues), terminology 10 passed.
