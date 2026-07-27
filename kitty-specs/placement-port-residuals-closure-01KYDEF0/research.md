# Research — Placement-Port Residuals Closure

All open decisions were resolved before planning: two by operator design-fork
answers, the rest by the post-spec adversarial squad (architect-alphonso,
reviewer-renata, debugger-debbie, planner-priti; profile-loaded, evidence-grounded).
This file records the decisions; no NEEDS CLARIFICATION remain.

## D-01 — A3 remedy: read `tasks/` from the PRIMARY leg (not a fail-closed abort)

- **Decision**: Move only the `tasks/` frontmatter READ (`_seed_phase`/`_verify_phase`) to the PRIMARY leg; keep the seed-event WRITE on the COORD leg and the `status_phase` flip on PRIMARY.
- **Rationale**: Operator chose "heal, don't abort." Squad (architect + debbie) proved a naive `status_dir → feature_dir` swap would push `status.events.jsonl` (STATUS_STATE = COORD) onto PRIMARY — wrong partition. The fix must decouple `backfill_runtime_state`'s read-dir from its event write-dir.
- **Alternatives rejected**: (a) fail-closed abort guard — operator declined; halts rather than heals. (b) naive leg swap — moves the split instead of closing it.

## D-02 — B2 remedy: degrade `_load_traces` to `[]`

- **Decision**: Wrap `read_dir(TRACER_FILE)` in `except (CoordinationBranchDeleted, StatusReadPathNotFound): return []`.
- **Rationale**: Operator chose to preserve the documented best-effort contract. `CoordinationBranchDeleted` subclasses `StatusReadPathNotFound`, so the except set is exact; do not widen to bare `Exception` (Edge Case: unexpected errors stay loud).
- **Alternatives rejected**: make the raise explicit — contradicts the best-effort docstring; scoped narrow to one call site to avoid #2922 collision (C-003).

## D-03 — C-001 corrected: FR-003 is A1-independent (BLOCKER fix)

- **Decision**: Remove the "A1-before-A2 hard sequence." Gate greenness depends on FR-008/FR-012 (the `executor.py` coord-seed call site), not on routing `_flip_phase`.
- **Rationale**: Adjudicated from source — the write-side gate scans only `CommitTarget`/`safe_commit`; `_flip_phase` writes via `write_meta(<dir>)` (invisible), and `grep` shows the entire `migration/` subtree has zero `CommitTarget`/`safe_commit` calls, so dropping its prefix reds nothing. See [[reference-write-side-rederivation-gate-grammar]].
- **Consequence**: FR-001's PRIMARY-correctness is enforced by a runtime assert, not a static gate. C-007 keeps the FRs in one lane for file-ownership (not correctness) reasons.

## D-04 — FR-008 + FR-012 resolution: allow-list, not seam-route / not STANDARD

- **Decision**: Extend both gate allow-lists (`BOUNDARY_SANCTIONED_MODULES` for write-side; `_PROTECTED_FLOW_ALLOWLISTS["MERGE_BOOKKEEPING"]` for guard-capability) to include `merge/executor.py`'s coord-seed call site with one dated rationale.
- **Rationale**: The coord-seed commit writes `status.events.jsonl` (STATUS_STATE → COORD) to the captured `pre_target_coord_ref` from the COORD worktree, on a best-effort merge path that must never abort. Seam-routing adds merge-window resolvability coupling (`ActionContextError`); STANDARD would refuse the protected coord destination. Allow-list is the partition-correct, non-destabilizing resolution.
- **Alternatives rejected**: seam-route (couples best-effort path to resolvability); assert STANDARD (breaks the legitimate protected-destination write — the exact PR #1850 regression the guard test names, but inverted).

## D-05 — FR-004 scope: `migration/`-subtree only; `upgrade/migrations/` retained

- **Decision**: Narrow only `src/specify_cli/migration/`; keep `src/mission_runtime/` and `src/specify_cli/upgrade/migrations/` as justified prefixes; scope the guarantee wording accordingly.
- **Rationale**: The merged NFR-001 deferred BOTH `migration*` subtrees. Narrowing only one and claiming an un-qualified "any module" guarantee would be a documented lie while `upgrade/migrations/` remains a prefix. `upgrade/migrations/` holds sanctioned version-migration drivers.

## D-06 — FR-005 helper home: `src/mission_runtime/`

- **Decision**: New `resolve_write_target_or_degrade(repo_root, mission_slug, kind, *, degrade_ref)` lives in `mission_runtime` (owns `resolve_placement_only` + `candidate_feature_dir_for_mission`); import-legal for all three call sites.
- **Rationale**: Keeps the degrade policy beside the authority; `decision_log`/`git` are not coordination modules, so `mission_runtime` beats `coordination/`.
- **Constraint**: kind-parameterized — coord kinds degrade to the coord ref (C-004).

## D-07 — Tracker shape

- **Decision**: Mint a parent epic; native-link #2923 + #2924 + #2926 (all orphaned, `parent: null`); mint a Part-C issue for FR-009/010/011; one issue-matrix row per issue.
- **Rationale**: A mission is not an issue; #2923's body covers A1/A2/A3 only, so the CLI/merge reds need their own tracked home for a clean 1:1 terminal matrix.

## Live-evidence baseline (debbie)

All six Part C tests confirmed RED on the merge-base for the stated reasons
(`PWHEADLESS=1 pytest`): write-side-rederivation @ `executor.py:1056`,
guard-capability[MERGE_BOOKKEEPING] @ `executor.py`, raw-mission-spec-path @
`mission_repair.py:65`, golden-contract 9≠8, and the two `status.events.jsonl`
merge tests. FR-011's tests encode the real FR-019/FR-020 durability invariant →
fix the product. `test_repair_command_registered_on_mission_app` passed locally /
failed CI → parked as verify-on-CI.
