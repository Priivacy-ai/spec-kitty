# Design Decisions

> Capture the rationale that would otherwise evaporate.
> **Implementers: append here whenever you make a per-site kind decision, resolve a
> read/write divergence, or pick between routing options.** 1–3 sentences per entry.
> Full rationale trail: `research.md` (D1–D12) and `spec.md` (C-001…C-007).

**Prompting questions**
- What decision was made?
- What alternatives were considered?
- What was the rationale — why this option over the others?

---

## Entries

- **2026-07-08 — [planning] Seeded at planning time (post-plan, pre-/tasks).** Unlike the
  sibling write-side mission (coord-primary-01KWZ46V), which seeded its tracers late at
  implement-start, this mission seeds at the correct point-cut. Rationale: #2462 has landed,
  the base is settled, and the design decisions below are now evidence-backed rather than
  provisional.
- **2026-07-08 — Binding invariants inherited from the landed #2462 seam.** C-001: the
  topology-aware `PlacementSeam` (`src/mission_runtime/resolution.py`) is the SINGLE access
  point — a PRIMARY answer from `read_dir(kind)` is NOT license to bypass the seam.
  C-002: the kind→partition mapping is a HARD invariant — do NOT flip any kind. The #2462
  second-opinion squad confirmed the mapping landed "byte-for-byte preserved, no kind flipped."
- **2026-07-08 — `read_dir` is NOT a uniform projection (PR-review finding H-1).** Confirmed
  landed shape: every kind routes through `resolve_planning_read_dir` EXCEPT `RETROSPECTIVE`,
  which delegates to `resolve_retrospective_home` (the dedicated single authority, #2119).
  Decision: Thread-A routing must go through `PlacementSeam.read_dir(kind)`, never assume one
  delegate for all kinds. Alternative (route all kinds to one resolver) rejected — would
  re-introduce a shadow authority for RETROSPECTIVE.
- **2026-07-08 — #2404 (Thread C) closes at the SEAM, not per-caller (C-006 / Directive-043).**
  Confirmed target intact: `commit_for_mission` (`coordination/commit_router.py:152`) still
  resolves ONE `kind` per invocation via `resolve_placement_only(...)`. Make it per-file
  partition-aware there; that fixes `spec_commit_cmd` + `mission_finalize.py` (kind=TASKS_INDEX
  caller) BY CONSTRUCTION. Alternative (flip ACCEPTANCE_MATRIX/ANALYSIS_REPORT to PRIMARY — the
  sibling's shelved "swappable-locus" question) rejected: it violates C-002 and #2462 proved
  nothing needs flipping. NOTE: `_planning_commit_worktree` was RENAMED by #2462 →
  `_resolve_commit_worktree_for_kind` (backward alias kept) — refer to the new name.
- **2026-07-08 — Thread A census must count by TOKEN, not line number.** The landed
  `resolution_gate_allowlist.yaml` pins the review write sites at STALE locators (2633/2670)
  which are token-authoritative, line-non-authoritative. Re-pin the census on tokens.
- **2026-07-08 — Thread B (#2100) inherits a BREAKING base: legacy meta-less missions now
  hard-fail.** #2462's #2091 guard drops pre-3.2.x legacy-mission support (error points to
  `spec-kitty migrate backfill-identity`). Routing inline `json.loads(meta)` reads onto
  `load_meta`/`load_meta_strict`/`load_meta_or_empty` must NOT re-introduce a
  fallback-on-missing-meta path — that era is intentionally gone. Full legacy-bridge removal is
  tracked separately in **#2463** (do NOT fold).
- **2026-07-08 — [planning] #2462 follow-up fold adjudication (Priti, profile-loaded).** FOLD
  nothing new. #2463 (legacy-bridge removal, BREAKING), #2464 (workflow.py degod), #2465 (resolver-
  primitive consolidation — C-001 scopes primitives OUT), #2475/#2476 (CI-infra) all verified
  SEPARATE. Only paula's fail-open-fallback folds (Thread A/FR-004, red-first). Renata's
  `contextlib.suppress`@`mission_creation.py:469` VERIFIED out of IC-04 footprint (wraps a
  create-time write; 0 read-routing sites) → deferred campsite NOTE, NOT folded (DIRECTIVE_025
  out-of-domain). Post-adjudication mission stays 15–17 WPs, read-side domain intact.
- **2026-07-08 — [planning] Re-grounding squad (3 lenses, profile-loaded) vs merged base → LAND, no re-scope.**
  Inventory (randy): Thread A 32/7/25 + 4 slug sites EXACT; Thread C exact incl. line refs;
  cross-thread = **8/9 genuine collisions** (`orchestrator_api/commands.py` is FR-004-only, no B-read
  → loosened to FR-004-only set); Thread B counts directional (63/43 vs prose 50/60 — IC-06 scanner
  is tie-breaker). Sequencing (priti): all edges SAFE (IC-01→02→03, FR-003→FR-002, IC-05→06), C-003
  satisfied, no deadlock; reuse #2462's golden-path integration fixture. Constraint (alphonso): C-001/
  C-002/C-006 HOLD, but **NFR-001 wording was factually wrong** — kind-aware `read_dir` legitimately
  moves PRIMARY-kind reads coord→primary under coord topology (that IS the #2453 fix); reframed NFR-001
  to forbid pinning the old kind-blind coord dir + require a coord-topology divergence regression.
  Also sharpened FR-007 (`None`-classified files keep caller-`kind` fallback) + FR-005 (post-#2091
  `allow_missing` semantics, no masking the guard). All edits are wording/contract precision, not scope.
- **2026-07-08 — [tasks] Post-tasks anti-laziness squad (3 lenses) → 1 BLOCKER fixed, else LAND.**
  Coverage (randy): COMPLETE — every A/B site + 8 collisions has one WP home, no orphans at FILE level.
  Constraint (alphonso): INTACT — all 8 binding constraints enforceably encoded, 0 HIGH.
  Sizing (renata): **found the blocker the file-level lens couldn't** — WP04 owned workflow.py but
  routed only the 2 `review` sites (@2710/@2747), ORPHANING the 2 `implement` reads (@1468 feedback-
  context, @1663 dossier-sync). Both are in the coord_authority allowlist (4 workflow.py entries + 1
  implement.py + 2 keepers = 7); leaving them unrouted → WP11 could only drain to 4, not 2 → SC-001
  fails. FIX: WP04 T017 now routes ALL 3 reads (@1468/@1663/@2710) + T018 the @2747 write. Also
  enriched WP13/WP14 with per-site enumeration-first instructions (~22–25 sites each). Claim fidelity
  100% (all cited line refs exact). Lesson: file-level coverage ≠ site-level coverage on god-modules.
- **2026-07-08 — WP12 (T037/T038): status/* + merge/* + sync/emitter.py per-site FR-005 adjudication.**
  Census of the 9 owned files found 5 genuine `meta.json` reads and 8 lookalikes (JSONL event-log
  lines in `lifecycle_events.py`/`store.py`/`conflict_resolver.py`/`preflight.py`; `status.json` in
  `preflight.py:424`; `.kittify/merge-state.json` in `state.py:213`; a JSON schema file in
  `emitter.py:188`) — none of the lookalikes were routed.
  - `status/aggregate.py::_read_meta` (@414) and `status/identity_audit.py::classify_mission` (@132):
    both pre-check `meta_path.exists()` then hand-rolled a `try/except (OSError, JSONDecodeError)` +
    a separate `isinstance(..., dict)` guard with a bespoke "expected object" message. Routed to
    `load_meta(dir, on_malformed="raise")`, which folds BOTH checks into one `ValueError` — a real
    LOC/branch reduction, not just a call-site swap. `on_malformed="raise"`'s message is "Expected
    JSON object in {path}, got {type}" (capital E, includes the path) instead of the old ad-hoc
    "expected object, got {type}" — updated the two pinned test assertions
    (`test_mission_status_aggregate.py:325`, and `store.py`'s below) to match the canonical wording;
    this is a consolidation-driven test sync, not a weakened assertion (both still assert a
    "non-dict fails closed with a descriptive message" invariant).
  - `status/store.py::_SlugResolver.resolve` (@235): same fold (`on_malformed="raise"`), but the
    non-dict warning is emitted from ONE `except ValueError` arm now (message text absorbed from
    the canonical reader) instead of a dedicated `else: isinstance(...)` warning branch — updated
    `test_slug_resolver_returns_none_for_non_dict_meta` to check for "Expected JSON object" instead
    of "is not an object" (same rationale as above).
  - `merge/ordering.py::_compute_next_mission_number_or_none` (@299, `target_meta_path`) and
    `merge/ordering.py::_write_mission_number_to_branch` (@393, `meta_path`): both are best-effort
    "peek/bake mission_number" helpers on a detached scan/mission-branch worktree — NEITHER is a
    #2091 identity-guard site (they touch `mission_number`, not `mission_id`/`coordination_branch`).
    Original code tolerated a non-dict top level locally but let a raw JSON-syntax error propagate
    UNCAUGHT (an omission, not a deliberate hard-fail contract — no test pins the crash-on-malformed-
    syntax path). Routed both to `load_meta(dir, on_malformed="none")`: absorbs missing/malformed-
    syntax/non-dict uniformly to `None`, so a corrupt meta.json on a merge target/mission branch now
    degrades to the SAME "skip, don't crash the merge" outcome the non-dict branch already had,
    instead of aborting the whole merge on a stray JSON typo. Disclosed as a deliberate refinement,
    not a masked #2091 guard.
  - `merge/baseline.py::_read_committed_meta_json` (@150, `json.loads(out)`): EXCLUDED — reads
    `git show <branch>:<meta_rel>` subprocess output (a string), not a `Path.read_text()` off a real
    on-disk `feature_dir`; `load_meta` requires a filesystem directory and has no git-blob-scoped
    variant. `merge/baseline.py` already routes its ONE working-tree meta read through `load_meta`
    (`_recorded_baseline_from_working_meta` @122, pre-existing, untouched here). Same carve-out
    class as the `transaction.py` git-ref reads noted in spec.md FR-005.
  - Integration check: all 4 routed call sites (`_read_meta`, `classify_mission`,
    `_SlugResolver.resolve`, both ordering.py helpers) are internal/private with a single production
    caller each (grep-verified) — no external consumer depends on the old exception TYPE or on the
    exact pre-consolidation log wording besides the two tests updated above.

## WP05 — collision cluster 1: `implement.py` + `_identity_audit.py` (A+B co-owned)

- **`implement.py`@~1169 (A) — `SPEC` kind, full cascade collapse, not a partial patch.**
  The pre-fix site was a THREE-step meta.json-existence cascade
  (`resolve_feature_dir_for_mission` → `candidate_feature_dir_for_mission` fallback →
  `primary_feature_dir_for_mission` fallback), which existed ONLY to paper over the kind-blind
  resolver's coord-husk-shadows-primary defect (#2453). `SPEC` is a PRIMARY-partition kind
  (`mission_runtime.artifacts._PRIMARY_ARTIFACT_KINDS`), so `read_dir(SPEC)` resolves the
  topology-blind primary dir directly and NEVER returns the meta-less coord husk — the entire
  cascade collapses to one call. Considered keeping the cascade as a defensive no-op after
  swapping only the first call; rejected as leaving dead, confusing code the WP prompt's
  "do not opportunistically refactor" guidance does not require (removing it IS the site's fix,
  not an unrelated refactor) — verified no test depended on the fallback's intermediate
  candidates (only on the final resolved dir), confirmed by the full green re-run.
- **`implement.py`@~975 `_ensure_vcs_in_meta` (B) — `load_meta(allow_missing=False,
  on_malformed="raise")`.** POST-#2091 contract: this site HARD-FAILS on both missing meta
  (prints an error, `typer.Exit(1)`) and malformed meta (prints an error, `typer.Exit(1)`) — the
  textbook "hard-failing site" FR-005 requires `allow_missing=False` for. Used `load_meta`
  directly (not `load_meta_strict`) because `load_meta_strict` hardcodes
  `on_malformed="empty"` (silently coerces malformed JSON to `{}`), which would MASK the
  malformed-JSON error this site must surface — exactly the FR-005 guard-masking hazard, just via
  the wrong adapter instead of `allow_missing=True`. `meta = meta or {}` after the try/except
  narrows the `dict[str, Any] | None` signature for mypy (mirrors `load_meta_strict`'s own
  narrowing idiom) — the `None` leg is unreachable at that point (both `None`-producing branches
  raise, above) but mypy cannot see that across a try/except.
- **`_identity_audit.py`@~55 `_scope_to_mission` + @~280 `_collect_topology_rows` (A) —
  `PRIMARY_METADATA` kind, not `SPEC`.** Both sites resolve a mission dir purely to read/probe
  `meta.json` (identity classification, stored-topology audit) — no spec/plan/tasks content is
  touched. `PRIMARY_METADATA` is the artifact kind named for exactly this (also a
  `_PRIMARY_ARTIFACT_KINDS` member, so it resolves identically to `SPEC` in practice, but the
  label is more precise and matches `artifact_home_for`'s dedicated `PRIMARY_METADATA` branch).
  NOTE: this file (`cli/commands/_identity_audit.py`) is DISTINCT from `status/identity_audit.py`
  (WP12's `classify_mission` above) — no overlap despite the similar name.
- **`_identity_audit.py`@~261 `_read_stored_topology` (B) — `load_meta(allow_missing=True,
  on_malformed="raise")`, the OPPOSITE contract from `implement.py`'s B site.** This site does
  NOT hard-fail on missing meta — it softly degrades to an informative row
  (`error: "meta.json not found"`) so the topology-audit table still renders one row per mission.
  FR-005's "never `allow_missing=True` on a hard-failing site" guard does not apply here: there is
  no #2091 guard being masked, because the pre-existing code never raised on missing meta in the
  first place (the soft-degrade IS the pre-existing, intended contract). Malformed JSON keeps a
  distinct "corrupt json: ..." message via `on_malformed="raise"` + a local `except ValueError`
  catch, rather than folding into `on_malformed="empty"` (which would collapse the missing- and
  malformed-JSON cases into one indistinguishable `{}`, losing the diagnostic split the existing
  tests (`test_read_stored_topology_missing_meta` vs `_corrupt` vs `_non_object`) pin.
- **Collision-cluster gate fallout — `tests/architectural/resolution_gate_allowlist.yaml` +
  `test_resolution_authority_gates.py` + `test_coord_read_residuals_closeout.py` needed a
  shrink-only re-pin.** Draining `implement.py`'s A-site removed its `coord_authority` allowlist
  entry (7→6 entries; `COORD_AUTHORITY_WRITE_FLOOR` 7→6) AND one
  `primary_feature_dir_for_mission(...)` anchor from the deleted fallback cascade
  (`CANONICALIZER_FLOOR` 45→44) — both floors lowered to the re-measured live census per the
  gate's own SHRINK-ONLY discipline, PLUS a companion "recorded census" pin in a past mission's
  test file (`test_coord_read_residuals_closeout.py::test_routed_canonicalizer_floor_matches_recorded_census`)
  hardcoding the same `CANONICALIZER_FLOOR == 45` constant. `test_routed_count_floor` needed no
  change (41 routed sites still clears `39 + margin(4)`).
  `tests/agent/test_implement_command.py::test_lanes_json_read_from_coord_dir_not_primary`
  patched the now-removed `implement.resolve_feature_dir_for_mission` /
  `candidate_feature_dir_for_mission` module attributes — updated to rely on the seam's real
  topology-blind resolution instead of stubbing the retired fallback (the test's actual assertion,
  that `_lanes_feature_dir` independently anchors on coord while `feature_dir` anchors on primary,
  is unchanged and still green). Lesson for remaining Thread A/B WPs: draining ANY census site
  needs a full-repo grep for `CANONICALIZER_FLOOR`/`COORD_AUTHORITY_WRITE_FLOOR` usages, not just
  the one gate test file — a second, unrelated past mission's test independently pinned the same
  integer.
