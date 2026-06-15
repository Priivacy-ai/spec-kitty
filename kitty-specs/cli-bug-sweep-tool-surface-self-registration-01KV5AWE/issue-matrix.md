# Issue matrix — cli-bug-sweep-tool-surface-self-registration-01KV5AWE

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1947 | Dogfooding: host-CLI source drift silently flips in-process gate verdicts (no provenance contract) | deferred-with-followup | Follow-up: #1983 (dedicated provenance-contract mission); out of scope for this CLI bug sweep |
| #1949 | charter bundle validate fails on tracked provenance sidecars whose generated artifacts are gitignored | fixed | WP02 (merged): T007 built_in_only early-exit, T005/T006 singular kind subdirs, T004 stale sidecar removal; test_bundle_validate_fresh_seed.py passes |
| #1950 | branch_naming: mission_branch_name double-appends mid8 when slug already carries it (creator≠recorder) | verified-already-fixed | WP01 T002+T003: guard was already in place; added invariant docstring and regression tests for mission_branch_name and lane_branch_name pathological cases |
| #1951 | tool_surface: service.py has no provider-discovery seam — parallel lanes always conflict on registration | fixed | WP03 (merged): registry infrastructure (_registry.py, _discovery.py, service.py); WP04 (merged): 7 provider self-registrations + Directive-030 conformance test |
| #1953 | spec-kitty init prompts for agent strategy despite --ai/--script/--mission flags (stale xfail in test_distribution) | fixed | WP01 T001: removed @pytest.mark.xfail(strict=False) from test_upgrade_updates_templates |
| #1981 | map-requirements resolves spec.md from coord worktree instead of main checkout | fixed | WP05 T020: resolve_feature_dir_for_slug replaces resolve_feature_dir_for_mission in map_requirements |
| #1982 | finalize-tasks --validate-only gives no hint for create_intent on planned-new-files | fixed | WP05 T021: create_intent hint appended unconditionally after nearest-match suggestion in ownership/validation.py |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
