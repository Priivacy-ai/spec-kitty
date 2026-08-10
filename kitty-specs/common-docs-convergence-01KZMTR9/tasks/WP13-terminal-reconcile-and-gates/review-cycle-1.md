---
affected_files: []
cycle_number: 1
mission_slug: common-docs-convergence-01KZMTR9
reproduction_command:
reviewed_at: '2026-08-10T13:54:59Z'
reviewer_agent: user
wp_id: WP13
---

# WP13 Review — REJECT (one blocking finding)

Reviewer: independent WP13 reviewer, integrated tree `lane-m`.
Verdict: **REJECT** — one genuine, WP13-introduced test red that ships to the primary branch.

Almost everything in WP13 verifies clean (details at the bottom). The mission does **not** merge
with a red test on `docs/common-docs-cleanup`, so this must be resolved before re-review.

---

## BLOCKING: stale dual-read test left red by the charter authority-path collapse

**Test:** `tests/docs/test_runtime_read_resolution.py::TestGovernanceAuthorityPathsRepointed::test_charter_retains_old_homes_dual_read`

```
assert "glossary/contexts/" in paths
AssertionError: assert 'glossary/contexts/' in ['docs/context/', 'docs/adr/3.x/']
```

### Why this is real (not the occurrence_map split artifact)

This failure is **charter-driven, not occurrence_map-driven**. I re-ran it with the primary
branch's full reconciled `occurrence_map.yaml` staged in — it **still fails**. It reads the
tracked `.kittify/charter/charter.md` `authority_paths:` block, which WP13 (commit `83ce52f9`)
correctly collapsed to the 2 canonical homes. Because `charter.md` is tracked and merges to
`docs/common-docs-cleanup`, this test stays **RED post-merge on the primary branch**. Unlike the
two `redirect_*` failures (which are the documented occurrence_map-on-primary split artifact and go
green post-merge), this one does not self-resolve.

### Why the collapse is correct — the test is stale, not the charter

The charter collapse is the intended, required behaviour:

- Base charter comment (at `kitty/mission-common-docs-convergence-01KZMTR9`, charter.md ~L560):
  *"Mission B dual-read (C-003): legacy + new homes listed together ... The legacy branches are
  dropped in WP08's reference sweep."* — the dual-read window is designed to close.
- WP11 T032 explicitly repairs the three dead authority paths in `charter.yaml`/`governance.yaml`
  (removing `glossary/contexts/`, `architecture/3.x/adr/`, `architecture/adrs/`) and adds an
  FR-019 resolution test asserting every declared path **exists on disk**. That test
  (`test_charter_declared_new_homes_resolve_through_renderer`) passes.
- On disk the legacy homes are now **empty/absent** (`glossary/contexts/` and
  `architecture/3.x/adr/` have no content); content lives in `docs/context/` and `docs/adr/3.x/`.
  Retaining them in `authority_paths` would be exactly the dead paths the mission forbids.

So `test_charter_retains_old_homes_dual_read` is the **transitional guard that had to flip** when
the dual-read window closed. Its sibling `test_charter_lists_new_homes` (new homes present) was
kept and passes; this one asserts the opposite and was never updated. It was last touched by WP08's
sweep (`424f4d63`) during the dual-read phase and left behind.

### Required fix (same-change companion to the charter collapse)

In `tests/docs/test_runtime_read_resolution.py`, update the
`TestGovernanceAuthorityPathsRepointed` class so it matches the closed dual-read window — either:

- **Invert** `test_charter_retains_old_homes_dual_read` into a "dual-read window closed" guard that
  asserts the legacy homes (`glossary/contexts/`, `architecture/3.x/adr/`) are **no longer** in the
  charter `authority_paths` (mirroring the on-disk reality and all three collapsed charter files), **or**
- **Delete** it, since `test_charter_lists_new_homes` + the FR-019 resolution test already cover the
  post-collapse invariant.

Keep it a same-change edit with the charter collapse. After the fix, re-run:

```
PYTHONPATH=<lane-m>:<lane-m>/src python -m pytest tests/docs/test_runtime_read_resolution.py -q
```

---

## Everything else PASSED (for the re-review record)

- **T037 redirect coverage (NFR-010):** `scripts/docs/redirect_baseline_urls.json` unchanged vs base
  (immutable — empty diff). `test_redirect_spine.py` = **8/8 pass when regenerated from the primary
  branch's full occurrence_map** (the lane-only failure of `test_non_archive_prior_values_are_stable`
  is the documented occurrence_map-on-primary split — goes green post-merge). Coverage-specific tests
  (`test_regen_reproduces_every_prior_baseline_redirect`, `test_coverage_reports_zero_dead_targets`)
  are green even in lane-m. Reverse rename-reconcile gate (no published page dropped) = **0**.
- **T038:** `docs/docfx.json` has no dead `reference/**.md`/`apidoc/**.md` globs;
  `test_description_length_gate.py` 26/26; inventory/freshness/lockfile 155/155.
- **T039:** `audience_resolver.py --strict` = **0 dangling / 138 examined**;
  `relative_link_fixer.py --check` = **0 dead**; `test_related_validator` + `test_asset_howto`
  (repointed to `docs/development/how-to/create-a-doctrine-artifact.md`) + `test_published_pages`
  (canary → `docs/guides/how-to/installation/install-spec-kitty.md`) = 21/21. Charter integrity:
  no dead paths in charter.yaml/governance.yaml/charter.md (all collapsed to the 2 canonical homes);
  `spec-kitty doctor doctrine` healthy (profile_health.healthy=True, 25/25 profiles, exit 0).
- **T040:** nested-dir prefix-match fix in `docs_structural_lint.py` (`_under_non_content_dir`) with
  dedicated positive+negative fixtures; `docs-build-pr.yml` present, valid YAML, pull_request DocFX
  build + redirect coverage + seo_verify; FR-022 = 4 markdown redirect stubs carry
  `description: "Redirect stub: …"`; OB-2 respected (`run()` excludes structural invariants;
  `run_extended()` enforces them, `--extended` = **716 pages, 0 violations**).
- **Residuals confirmed non-blocking:** rename_reconcile 114 forward findings are all unpublished
  collapsed-spine intermediates (ADR renumbers, mover subdivisions) with no baseline URL — by design;
  touched_set_gates pytest 19/19 pass (strict-mode script output is advisory).
- **Final green:** `tests/docs/` + `test_no_legacy_terminology` + `test_schema_generation_integrity`
  = **1477 passed, 3 failed**. Of the 3: 2 are the benign occurrence_map split artifact
  (`test_redirect_spine::test_non_archive_prior_values_are_stable`,
  `test_redirect_stub_generator::test_committed_redirect_map_is_diff_stable` — both pass with the
  primary occurrence_map, green post-merge); 1 is the blocking charter dual-read red above.
