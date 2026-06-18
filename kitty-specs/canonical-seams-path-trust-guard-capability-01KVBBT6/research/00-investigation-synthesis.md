# Investigation squad synthesis — Canonical seams: path-trust + guard-capability (pre-spec)
Date: 2026-06-17. Squad: randy-reducer (census), debugger-debbie (feasibility+CI forensics),
paula-patterns (coherence/grain), planner-priti (tracker). All profile-loaded, verified vs on-main code.

## Goal A — slug validation at the path primitive  [SAFE-TO-MOVE, reshaped]
- randy: ~75–143 call sites route mission_slug→path through `primary_feature_dir_for_mission`(_read_path_resolver.py:397)
  / `candidate_feature_dir_for_mission`(:370). Only 2 are guarded today; the primitives do ZERO validation.
  Single-safe-segment validation is NON-BREAKING for all current call sites.
- debbie: SAFE-TO-MOVE. Raise `ValueError` (matches existing contract + test match="single safe path segment");
  ensure the dry-run/abort sites (merge.py:3253-3265, only catch MissingLanesError/CorruptLanesError) catch it.
  `_resolve_mission_slug` returns RAW handles in 2 branches but only malformed operator input would now raise
  (today it silently builds kitty-specs/foo/bar → confusing MissingLanesError).
- paula: THREE divergent validators exist — merge.py:774 `_validate_mission_slug_path_segment` (^[A-Za-z0-9_-]+$, no dots),
  coordination/transaction.py:168 `_validate_safe_segment` (^[A-Za-z0-9][A-Za-z0-9._-]*$, dots), status/aggregate.py `_validate_mission_slug`.
  Canonical KEBAB_CASE (core/mission_creation.py:65) is a subset of both. Put ONE validator in core/paths.py (Shared Kernel),
  call it inside primary_feature_dir_for_mission + once in resolve_mission_read_path; migrate merge.py + transaction.py to delegate.
  REGEX RECONCILIATION IS A REAL DECISION (the `.`/`..` traversal guard must survive). Require a test that the union of
  currently-valid real-format slugs still validates.
- NON-GOAL (binding): validate the segment at the seam; do NOT re-route the ~143 callers or merge the two primitives
  (that is read-path-adoption mission 01KV8NPC / naming-rider 01KV7SFD work).

## Goal B — collapse containment helpers  [coherent, delegate to kernel]
- randy: 3 helpers in merge.py + `ensure_within_directory`(core/utils.py:29). 3-of-4 collapse cleanly. Holdouts:
  * `_assert_status_surface_path_is_trusted`(merge.py:837) does CONDITIONAL XOR root-selection (worktrees XOR kitty-specs by
    `is_under_worktrees_segment`) — only fits a union if WIDENED (behavior change). Keep as a conditional caller, do not fold blindly.
  * `_assert_bookkeeping_snapshot_path_is_trusted`(merge.py:865) needs an `exact_files` arm (.kittify/merge-state.json), beyond roots.
- paula: delegate to a KERNEL util `ensure_within_any(path, roots, files)` beside `ensure_within_directory` in core/utils.py
  (NOT a merge.py-local util). Standardize on resolve(strict=False). The 3 merge helpers become thin slug/topology-aware callers.
- A+B = ONE coherent mission (same root cause: duplicated path-trust logic that should live in core/ and be inherited).

## Goal C — guard-capability (#2017 B8)  [NARROW: unblocked CI-mask slice only; defer the rest]
- debbie: CI-MASK CONFIRMED and worse than described. Not a missing trigger — a hardcoded short-circuit at
  ci-quality.yml:1357-1371 runs ONLY test_execution_context_parity.py for execution_context-only changes and `exit`s,
  skipping the rest of tests/architectural/** (incl. test_no_write_side_rederivation). Asymmetry: the ratchet runs when you
  edit the GUARD (tests/architectural/** is in core_misc) but NOT when you edit the GUARDED SURFACE (status/** is in
  execution_context only). This is exactly the live failure this session (the _repo_root_for_lifecycle_log fallback).
  Minimal invariant: the architectural shard must run the FULL tests/architectural/** whenever any guarded surface OR an
  architectural guard's scan-root/allow-list changes. Cheapest fix: add status/**, coordination/**, core/worktree.py to the
  core_misc filter (ci-quality.yml:174-195), OR exempt the architectural shard from the 1357 short-circuit.
- randy/debbie: line-number pins are concentrated — test_no_worktree_name_guess.py (doctor.py:3074/:3166 + invocation/executor.py
  + count baselines) and test_no_write_side_rederivation.py:81 (_ALLOW_LIST status_transition.py:295). A +1 line drift flips them
  silently. Re-key to AST/qualname + normalized-token-line composite (machinery already exists in the sibling test).
- paula (grain authority): C is CI/test-infra, NOT the #1868 runtime-authority spine. The ONE genuine line-keyed ratchet
  (test_no_write_side_rederivation._ALLOW_LIST:295) is a DELIBERATE paula-reviewed choice BLOCKED on the deferred #1716 ladder
  line — DO NOT touch it from a path-trust mission. migration-chain `_KNOWN_LINE_JUMPS` is semver-keyed (misnomer, not a target).
  Recommend: fold ONLY the unblocked CI-mask fix + AST-rekey of the non-#1716 pins; defer/split the rest to #1914/#1931.

## Tracker (priti)
- Only B8 folds. A1→#1734, A2/A4→#1914, A3→#1979, B5→#1795, B6→#1862(homed), B7→#582 stay in #2017.
- #2022 body says "Parent: #1868" in PROSE but native sub-issue link is MISSING → wire at specify.
- #1796 is CLOSED (don't file under it); #1479 is META-TRACKER (never canonical parent).
- B8 fix → scoped child under #1931 (Test quality & suite hygiene), not under #2017/#1796.
- Post fresh B8 occurrence comment on #2017 now. Claim #2022 (primary) + B8 facet; comment #2022/#2017/#1868 at specify.

## MVP cut (recommended)
A-core (kernel validator + 2 primitive call-ins + merge/transaction delegate, regex reconciled w/ union test)
+ B-core (ensure_within_any(roots, files) in core/utils.py; collapse the 2 root-set helpers + the file-arm helper; keep the XOR caller)
+ C-narrow (ci-quality.yml architectural-gate un-masking + AST-rekey the non-#1716 line pins).
Defer: caller re-routing, primitive unification, test_no_write_side_rederivation:295 rekey (#1716-blocked).
