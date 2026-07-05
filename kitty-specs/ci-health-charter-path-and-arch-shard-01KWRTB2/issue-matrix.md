# Issue matrix — ci-health-charter-path-and-arch-shard-01KWRTB2

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #2397 | Red-main `fast-tests-docs` charter-path hotfix + arch-adversarial matrix-shard | fixed | Both concerns closed. Concern A: WP01, commit `599c949f3` (`docs/guides/contributing.md` now references `.kittify/charter/charter.md`; guard `tests/docs/test_current_charter_paths.py` green). Concern B: WP02+WP03 shipped the 3-shard `arch_shard_1/2/3` marker-routed matrix (FR-003–FR-006); all 5 of #2397's invariant-safety criteria re-verified and recorded in `acceptance-record.md`; issue assigned to HiC (`stijn-dejongh`) per DIR-012 and closed at mission merge (mission #164, commit `c85fc2326`). |
| #2391 | De-serialize arch-adversarial pole (docs-only trim) — merged PR | verified-already-fixed | Not an open issue — already-merged PR. Its docs-only-trim behavior (skip the arch pole on docs-only changes) must be preserved through the WP02/WP03 arch-shard split (C-003) rather than fixed by this mission; preservation is checked via the acceptance walkthrough (SC-004), not tracked as a separate fix here. |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
