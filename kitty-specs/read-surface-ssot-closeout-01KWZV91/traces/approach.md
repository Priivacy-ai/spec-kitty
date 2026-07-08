# Approach Evolution

> Track how your approach changed as the mission progressed.
> **Implementers: append a dated entry whenever the approach shifts** (a WP is re-sliced,
> a routing strategy changes, a thread is re-scoped). 1–3 sentences.

**Prompting questions**
- What approach did you start with (as stated in the spec or plan)?
- What changed during implementation, and why?
- What would you try differently on a similar mission?

---

## Entries

- **2026-07-08 — [planning] Initial approach.** Read-side counterpart to the landed #2462
  write-side placement lock. Four threads, single mission (functional/behavioural overlap):
  A (#2453 feature_dir read sweep + coord_authority allowlist drain 7→2), B (#2100 inline
  meta.json → `load_meta` sweep + non-vacuous ratchet), C (#2404 seam-level per-file
  write-routing class-closure), D (#2088 closeout — already fixed on main). ~15–17 WPs.
  Route BOTH reads and writes through the one topology-aware seam.
- **2026-07-08 — Shift 1 (pre-spec 3-scout squad).** Corrected all four thread scopes:
  #2088 already fixed (69dd1fa46 — 0 WPs), #2404 is write-routing NOT a partition flip,
  #2453 is 36-not-71 sites, #2100 is 60 sites. Sized to 15–17 WPs.
- **2026-07-08 — Shift 2 (post-spec 3-lens squad).** Elevated #2404 to seam-level
  class-closure (per-file partition-aware `commit_for_mission`, C-006); added the 3rd site
  (`mission_finalize`) + accept dirty-detection reconciliation (M2); made the meta ratchet
  non-vacuous (routed-count floor); named the 9-file cross-thread A/B linearization set;
  ordered FR-003 (predicate-widen by-design writes) before FR-002 (floor re-pin).
- **2026-07-08 — Shift 3 (post-#2462-landing PR review + rebase).** #2462 landed EXACTLY as
  assumed (seam `read_dir` present, allowlist floor = 7, drain-to-2 valid, no ADR redirect) →
  **no spec revisit**, only MINOR plan edits. C-007 census **re-run green on the rebased base:
  32 live / 7 allowlisted / 25 to-route, gate 45/45 — UNCHANGED, drain 7→2 valid.** The
  PR-review's "subtract two pre-routed sites" was a class-conflation: the two `_planning_read_dir`
  helpers #2462 touched are the separate `resolve_planning_read_dir` delegate class, NOT the
  `resolve_feature_dir_for_mission` census Thread A targets — nothing to subtract (the re-run
  caught it). The reviewer folded two extra items into Thread A/#2453: paula's fail-open-fallback
  finding and renata's `contextlib.suppress` NOTE at `mission_creation.py:469`.
- **2026-07-08 — Sequencing (settled).** Thread C (IC-01 seam commit foundation) is the
  foundation everything routes through → first. Threads A/C depended on #2462 merging (now
  done; branch rebased onto merged upstream/main, 0 behind). Threads B/D are independent.
  Implementers sonnet, reviewers opus.
