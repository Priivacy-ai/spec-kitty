# Tracer: design decisions

Key decisions + rationale (append as decisions are made).

- **D1 — membership + live-floor over LOC tolerance band.** The three teeth are
  membership changes; exact LOC/order add only false-positive cost. A tolerance band
  (option a) keeps a drifting stored number and still reds at boundaries. Chose to remove
  exact LOC from the comparison surface entirely.
- **D2 — drop `loc` at the derivation, not just the test.** Fixing only the test
  assertion would leave `--verify-census` LOC-sensitive and keep a stale `loc` committed.
  Dropping it in `live_derived_worklist` fixes both surfaces and stores no drifting number.
- **D3 — keep the LOC floor, move it live.** `test_every_worklist_dir_meets_loc_floor`
  re-points from the stored `entry["loc"]` snapshot to live `src_package_loc()` — a
  strictly stronger check that also proves membership stays honest.
- **D4 — sort committed worklist by `dir`.** LOC-independent, diff-stable ordering; the
  freshness compare is a dir-keyed index so order is irrelevant to the verdict, but a
  deterministic on-disk order keeps regen diffs clean.
- **D5 — defer `arch_blind_groups` de-LOC.** Unfalsifiable on the empty,
  structurally-pinned-empty surface (post-spec gate finding). Deferred, not silently
  applied — keeps every mission claim non-vacuous.
- **D7 — durable, shape-independent C-001 guard (post-tasks gate fold).** After T003 the
  freshness test is loc-blind (the dir-keyed index), so C-001 ("no stale loc committed")
  is not enforced by it. Added `test_committed_census_carries_no_loc` asserting
  `all("loc" not in e for e in census["worklist"])` — a direct guard that reds on a
  skipped regen or a future reintroduction of the field regardless of the freshness
  test's shape. Also corrected the WP/tasks Risk note that falsely claimed the index
  freshness test reds on stale loc. Added a worklist-membership precondition to the
  red-first test for defense-in-depth (the hardcoded tracker/doctrine pair).
- **D6 — dynamic `t_high` in the floor-crossing tooth (post-plan gate polish).** The
  self-mutation floor-crossing test derives its raised floor as
  `t_high = min(live loc of committed worklist members) + 1` rather than the magic `600`,
  so the tooth stays non-vacuous even if `task_utils`/`saas_client`/`events`/`paths`
  grow past 600 later. Post-plan gate verdict was clean (all findings refuted); this is
  the one drift-proofing nit worth adopting.
