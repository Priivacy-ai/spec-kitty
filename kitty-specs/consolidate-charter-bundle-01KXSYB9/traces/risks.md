# Tracer: Risks

Seeded at planning; append as risks surface/resolve during implement; assess at close.

## Seeded (planning)
- **R1 (HIGH) — NFR-005 half-inverted ordering.** If the extractor retires (IC-04) before the loaders re-point, `sync()` stops writing the triad and un-re-pointed loaders return empty `GovernanceConfig()` SILENTLY — governance lost, no error. Mitigation: strict IC-03→IC-04 ordering; loader signatures stay stable; red-first test asserting non-empty governance through the pre-existing loader entry point.
- **R2 (HIGH) — activation-engine blast radius (IC-01).** Relocating `activated_*` touches `commit_plan`/`merge_defaults`/`PackContext.from_config`. Mitigation: behavior-preserving; `tests/doctrine/test_activation_parity_guard.py` + pack_context/activation_engine suites must stay green; preserve fail-closed + default-pack fallback.
- **R3 (HIGH) — schema/git-class reversibility (Landmine 1).** Wrong tracked/derived semantics → a second C-004 schema bump. Mitigation: pinned in data-model.md; charter.yaml tracked; derived_files = content-hash input set.
- **R4 (MED) — two `metadata.yaml`.** Migration must touch only `.kittify/charter/metadata.yaml`, never `.kittify/metadata.yaml` (project identity). Mitigation: explicit path guard + test.
- **R5 (MED) — charter_hash self-reference (Landmine 2).** Mitigation: retire/re-home; no self-hash field.
- **R6 (MED) — content-identity regression (#2732).** Mitigation: single `BUNDLE_CONTENT_HASH_FILES` point; existing content-identity suite must pass unchanged.
- **R7 (LOW) — dangling `charter:` pointer.** Mitigation: fail-loud (C-003), no fallback; test.
- **R8 (LOW) — docs drift.** charter-overview.md / governance-files.md assert "charter.md is THE source"; must flip in the same PR (C-006). Mitigation: IC-09 docs WP + terminology guard pre-push.
- **R9 (process) — scout-agent git-checkout hazard** (hit during the pre-plan squad; recovered). Mitigation: isolate or forbid HEAD-moving commands in future scouts.

## Appended (implement)
_(implementers append newly-surfaced risks + resolutions)_
